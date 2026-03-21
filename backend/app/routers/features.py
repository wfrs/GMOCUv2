"""Feature CRUD API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..application import features as feature_service
from ..models import get_db
from ..schemas import FeatureOut, FeatureCreate, FeatureUpdate

router = APIRouter(prefix="/features", tags=["features"])


@router.get("/", response_model=list[FeatureOut])
def list_features(
    skip: int = 0,
    limit: int = 500,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    return feature_service.list_features(db, skip=skip, limit=limit, search=search)


@router.get("/{feature_id}", response_model=FeatureOut)
def get_feature(feature_id: int, db: Session = Depends(get_db)):
    return feature_service.get_feature(db, feature_id)


@router.post("/", response_model=FeatureOut, status_code=201)
def create_feature(data: FeatureCreate, db: Session = Depends(get_db)):
    return feature_service.create_feature(db, data)


@router.patch("/{feature_id}", response_model=FeatureOut)
def update_feature(feature_id: int, data: FeatureUpdate, db: Session = Depends(get_db)):
    return feature_service.update_feature(db, feature_id, data)


@router.delete("/{feature_id}", status_code=204)
def delete_feature(feature_id: int, db: Session = Depends(get_db)):
    feature_service.delete_feature(db, feature_id)
