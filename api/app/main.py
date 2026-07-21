from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .models import AuditEvent, MemoryRecord
from .policy import can_delete_subject, can_read, can_view_audit, normalize_role
from .schemas import AuditOut, DeleteResponse, MemoryCreate, MemoryOut, MemorySearch, SearchResponse, SearchResult

settings = get_settings()
app = FastAPI(
    title="NT MemoryVault API",
    version="0.1.0",
    description="Sovereign persistent memory and governance for enterprise AI agents.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def actor_context(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")],
    agent_id: Annotated[str, Header(alias="X-Agent-ID")],
    agent_role: Annotated[str, Header(alias="X-Agent-Role")],
) -> tuple[str, str, str]:
    return tenant_id.strip(), agent_id.strip(), normalize_role(agent_role)


def memory_to_out(memory: MemoryRecord) -> MemoryOut:
    return MemoryOut(
        id=memory.id,
        tenant_id=memory.tenant_id,
        subject_id=memory.subject_id,
        agent_id=memory.agent_id,
        scope=memory.scope,
        type=memory.memory_type,
        content=memory.content,
        source=memory.source,
        confidence=memory.confidence,
        sensitivity=memory.sensitivity,
        allowed_roles=memory.allowed_roles,
        metadata=memory.memory_metadata,
        valid_from=memory.valid_from,
        expires_at=memory.expires_at,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )


def audit_to_out(event: AuditEvent) -> AuditOut:
    return AuditOut(
        id=event.id,
        tenant_id=event.tenant_id,
        actor_agent_id=event.actor_agent_id,
        actor_role=event.actor_role,
        action=event.action,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        subject_id=event.subject_id,
        outcome=event.outcome,
        reason=event.reason,
        metadata=event.event_metadata,
        created_at=event.created_at,
    )


def add_audit(
    db: Session,
    actor: tuple[str, str, str],
    *,
    action: str,
    outcome: str,
    resource_id: str | None = None,
    subject_id: str | None = None,
    reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    tenant_id, agent_id, agent_role = actor
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_agent_id=agent_id,
            actor_role=agent_role,
            action=action,
            resource_id=resource_id,
            subject_id=subject_id,
            outcome=outcome,
            reason=reason,
            event_metadata=metadata or {},
        )
    )


def lexical_score(query: str, content: str, confidence: float) -> float:
    terms = {term for term in re.findall(r"[\w\u0E00-\u0E7F]+", query.lower()) if len(term) > 1}
    if not terms:
        return round(float(confidence), 4)
    haystack = content.lower()
    matches = sum(1 for term in terms if term in haystack)
    return round((matches / len(terms)) * 0.8 + float(confidence) * 0.2, 4)


@app.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "principle": "Remember only what is allowed. Forget when ordered.",
        "docs": "/docs",
    }


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}


@app.post("/v1/memories", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryCreate,
    actor: tuple[str, str, str] = Depends(actor_context),
    db: Session = Depends(get_db),
) -> MemoryOut:
    tenant_id, agent_id, agent_role = actor
    allowed_roles = sorted({normalize_role(role) for role in payload.allowed_roles if role.strip()})
    if not allowed_roles:
        allowed_roles = [agent_role]

    valid_from = payload.valid_from or datetime.now(timezone.utc)
    if payload.expires_at and payload.expires_at <= valid_from:
        raise HTTPException(status_code=422, detail="expires_at must be after valid_from")

    memory = MemoryRecord(
        tenant_id=tenant_id,
        subject_id=payload.subject_id,
        agent_id=agent_id,
        scope=payload.scope,
        memory_type=payload.type,
        content=payload.content,
        source=payload.source,
        confidence=payload.confidence,
        sensitivity=payload.sensitivity,
        allowed_roles=allowed_roles,
        memory_metadata=payload.metadata,
        valid_from=valid_from,
        expires_at=payload.expires_at,
    )
    db.add(memory)
    db.flush()
    add_audit(
        db,
        actor,
        action="WRITE",
        outcome="allowed",
        resource_id=memory.id,
        subject_id=memory.subject_id,
        metadata={"scope": memory.scope, "type": memory.memory_type, "sensitivity": memory.sensitivity},
    )
    db.commit()
    db.refresh(memory)
    return memory_to_out(memory)


@app.post("/v1/memories/search", response_model=SearchResponse)
def search_memories(
    payload: MemorySearch,
    actor: tuple[str, str, str] = Depends(actor_context),
    db: Session = Depends(get_db),
) -> SearchResponse:
    tenant_id, _, _ = actor
    statement = select(MemoryRecord).where(
        MemoryRecord.tenant_id == tenant_id,
        MemoryRecord.is_deleted.is_(False),
    )
    if payload.subject_id:
        statement = statement.where(MemoryRecord.subject_id == payload.subject_id)
    if payload.scopes:
        statement = statement.where(MemoryRecord.scope.in_(payload.scopes))
    if payload.types:
        statement = statement.where(MemoryRecord.memory_type.in_(payload.types))

    candidates = db.scalars(statement.order_by(desc(MemoryRecord.created_at)).limit(250)).all()
    allowed_results: list[SearchResult] = []
    denied_count = 0

    for memory in candidates:
        allowed, reason = can_read(memory, actor[2])
        if not allowed:
            denied_count += 1
            add_audit(
                db,
                actor,
                action="READ",
                outcome="denied",
                resource_id=memory.id,
                subject_id=memory.subject_id,
                reason=reason,
                metadata={"scope": memory.scope, "sensitivity": memory.sensitivity},
            )
            continue

        score = lexical_score(payload.query, memory.content, memory.confidence)
        if payload.query and score <= 0.2:
            continue
        allowed_results.append(SearchResult(memory=memory_to_out(memory), score=score))
        add_audit(
            db,
            actor,
            action="READ",
            outcome="allowed",
            resource_id=memory.id,
            subject_id=memory.subject_id,
            metadata={"scope": memory.scope, "score": score},
        )

    allowed_results.sort(key=lambda item: (item.score, item.memory.created_at), reverse=True)
    db.commit()
    return SearchResponse(results=allowed_results[: payload.limit], denied_count=denied_count)


@app.get("/v1/audit", response_model=list[AuditOut])
def list_audit(
    actor: tuple[str, str, str] = Depends(actor_context),
    db: Session = Depends(get_db),
    subject_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditOut]:
    tenant_id, _, agent_role = actor
    if not can_view_audit(agent_role):
        add_audit(db, actor, action="AUDIT_READ", outcome="denied", reason="role_not_allowed")
        db.commit()
        raise HTTPException(status_code=403, detail="Audit access denied")

    statement = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if subject_id:
        statement = statement.where(AuditEvent.subject_id == subject_id)
    events = db.scalars(statement.order_by(desc(AuditEvent.created_at)).limit(limit)).all()
    return [audit_to_out(event) for event in events]


@app.delete("/v1/subjects/{subject_id}/memories", response_model=DeleteResponse)
def delete_subject_memories(
    subject_id: str,
    actor: tuple[str, str, str] = Depends(actor_context),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    tenant_id, _, agent_role = actor
    if not can_delete_subject(agent_role):
        add_audit(
            db,
            actor,
            action="DELETE_SUBJECT",
            outcome="denied",
            subject_id=subject_id,
            reason="role_not_allowed",
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Subject deletion denied")

    memories = db.scalars(
        select(MemoryRecord).where(
            MemoryRecord.tenant_id == tenant_id,
            MemoryRecord.subject_id == subject_id,
            MemoryRecord.is_deleted.is_(False),
        )
    ).all()
    for memory in memories:
        memory.is_deleted = True
        memory.updated_at = datetime.now(timezone.utc)

    add_audit(
        db,
        actor,
        action="DELETE_SUBJECT",
        outcome="allowed",
        subject_id=subject_id,
        metadata={"deleted_count": len(memories)},
    )
    db.commit()
    return DeleteResponse(subject_id=subject_id, deleted_count=len(memories))
