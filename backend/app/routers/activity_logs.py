"""Activity log API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..application import activity_logs as activity_log_service
from ..models import get_db
from ..schemas import ActivityLogOut

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/", response_model=list[ActivityLogOut])
def list_activity(
    entity_type: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    return activity_log_service.list_activity_logs(db, entity_type=entity_type, limit=limit)
