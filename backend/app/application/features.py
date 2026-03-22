"""Feature application services."""

from sqlalchemy.orm import Session

from ..errors import conflict, not_found
from ..models import Feature
from ..schemas import FeatureCreate, FeatureUpdate
from .activity_logs import log_action


def list_features(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 500,
    search: str | None = None,
) -> list[Feature]:
    query = db.query(Feature)
    if search:
        query = query.filter(Feature.annotation.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()


def get_feature(db: Session, feature_id: int) -> Feature:
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if feature is None:
        raise not_found("Feature not found")
    return feature


def create_feature(db: Session, data: FeatureCreate) -> Feature:
    existing = db.query(Feature).filter(Feature.annotation == data.annotation).first()
    if existing is not None:
        raise conflict("Feature with this annotation already exists")
    feature = Feature(**data.model_dump())
    db.add(feature)
    db.flush()
    log_action(db, "create", "feature", feature.id, feature.annotation)
    db.commit()
    db.refresh(feature)
    return feature


def update_feature(db: Session, feature_id: int, data: FeatureUpdate) -> Feature:
    feature = get_feature(db, feature_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        old = getattr(feature, key, None)
        if str(old) != str(value):
            log_action(db, "update", "feature", feature.id, feature.annotation,
                       field=key, old_value=str(old) if old is not None else None, new_value=str(value) if value is not None else None)
        setattr(feature, key, value)
    db.commit()
    db.refresh(feature)
    return feature


def delete_feature(db: Session, feature_id: int) -> None:
    feature = get_feature(db, feature_id)
    log_action(db, "delete", "feature", feature.id, feature.annotation)
    db.delete(feature)
    db.commit()
