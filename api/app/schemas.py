from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryCreate(BaseModel):
    subject_id: str = Field(min_length=1, max_length=128)
    scope: str = Field(min_length=1, max_length=128)
    type: str = "fact"
    content: str = Field(min_length=1, max_length=20000)
    source: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    sensitivity: str = "internal"
    allowed_roles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    valid_from: datetime | None = None
    expires_at: datetime | None = None


class MemoryOut(BaseModel):
    id: str
    tenant_id: str
    subject_id: str
    agent_id: str
    scope: str
    type: str
    content: str
    source: str | None
    confidence: float
    sensitivity: str
    allowed_roles: list[str]
    metadata: dict[str, Any]
    valid_from: datetime
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemorySearch(BaseModel):
    query: str = ""
    subject_id: str | None = None
    scopes: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    memory: MemoryOut
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    denied_count: int


class AuditOut(BaseModel):
    id: str
    tenant_id: str
    actor_agent_id: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None
    subject_id: str | None
    outcome: str
    reason: str | None
    metadata: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeleteResponse(BaseModel):
    subject_id: str
    deleted_count: int
