"""§18.7 — Audit logging.

Every doctor action (view, accept, edit, reject) and every export must be
recorded so clinics can audit access to patient data.
"""

from app.models import AuditAction, AuditLogEntry


def record(
    actor_id: str,
    actor_role: str,
    target_type: str,
    target_id: str,
    action: AuditAction,
) -> AuditLogEntry:
    raise NotImplementedError
