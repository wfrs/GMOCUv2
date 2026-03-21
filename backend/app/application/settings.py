"""Settings application services."""

from sqlalchemy.orm import Session

from ..errors import not_found
from ..models import Settings
from ..schemas import SettingsUpdate


def get_settings(db: Session) -> Settings:
    settings = db.query(Settings).first()
    if settings is None:
        raise not_found("Settings not found")
    return settings


def update_settings(db: Session, data: SettingsUpdate) -> Settings:
    settings = get_settings(db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings
