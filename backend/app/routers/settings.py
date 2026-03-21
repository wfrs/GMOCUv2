"""Settings API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..application import settings as settings_service
from ..models import get_db
from ..schemas import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return settings_service.get_settings(db)


@router.patch("/", response_model=SettingsOut)
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    return settings_service.update_settings(db, data)
