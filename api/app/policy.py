from datetime import datetime, timezone

from .models import MemoryRecord


ADMIN_ROLES = {"admin", "memory-admin"}
AUDIT_ROLES = {"admin", "memory-admin", "auditor"}


def normalize_role(role: str) -> str:
    return role.strip().lower()


def can_read(memory: MemoryRecord, actor_role: str) -> tuple[bool, str | None]:
    role = normalize_role(actor_role)

    if memory.is_deleted:
        return False, "memory_deleted"

    if memory.expires_at and memory.expires_at <= datetime.now(timezone.utc):
        return False, "memory_expired"

    if role in ADMIN_ROLES:
        return True, None

    allowed_roles = {normalize_role(item) for item in memory.allowed_roles}
    if role not in allowed_roles:
        return False, "role_not_allowed"

    return True, None


def can_view_audit(actor_role: str) -> bool:
    return normalize_role(actor_role) in AUDIT_ROLES


def can_delete_subject(actor_role: str) -> bool:
    return normalize_role(actor_role) in ADMIN_ROLES
