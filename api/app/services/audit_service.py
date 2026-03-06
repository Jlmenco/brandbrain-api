from sqlmodel import Session
from app.models.audit import AuditLog


def log_action(
    db: Session,
    org_id: str,
    cost_center_id: str | None,
    actor_user_id: str,
    action: str,
    target_type: str,
    target_id: str,
    metadata_json: dict | None = None,
) -> AuditLog:
    """Log an action to the audit log."""
    if metadata_json is None:
        metadata_json = {}

    audit_log = AuditLog(
        org_id=org_id,
        cost_center_id=cost_center_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=metadata_json,
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log
