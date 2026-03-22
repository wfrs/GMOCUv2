"""Activity log service — records create/update/delete events."""

from sqlalchemy.orm import Session

from ..models import ActivityLog


def log_action(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int,
    entity_name: str | None,
    *,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    """Add an activity entry to the session without committing."""
    db.add(ActivityLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        field=field,
        old_value=old_value,
        new_value=new_value,
    ))


def list_activity_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    limit: int = 200,
) -> list[ActivityLog]:
    q = db.query(ActivityLog)
    if entity_type:
        q = q.filter(ActivityLog.entity_type == entity_type)
    return q.order_by(ActivityLog.id.desc()).limit(limit).all()
