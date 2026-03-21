"""Organism CRUD API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..application import organisms as organism_service
from ..models import get_db
from ..schemas import OrganismOut, OrganismCreate, OrganismUpdate

router = APIRouter(prefix="/organisms", tags=["organisms"])


@router.get("/", response_model=list[OrganismOut])
def list_organisms(
    skip: int = 0,
    limit: int = 500,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    return organism_service.list_organisms(db, skip=skip, limit=limit, search=search)


@router.get("/{organism_id}", response_model=OrganismOut)
def get_organism(organism_id: int, db: Session = Depends(get_db)):
    return organism_service.get_organism(db, organism_id)


@router.post("/", response_model=OrganismOut, status_code=201)
def create_organism(data: OrganismCreate, db: Session = Depends(get_db)):
    return organism_service.create_organism(db, data)


@router.patch("/{organism_id}", response_model=OrganismOut)
def update_organism(organism_id: int, data: OrganismUpdate, db: Session = Depends(get_db)):
    return organism_service.update_organism(db, organism_id, data)


@router.delete("/{organism_id}", status_code=204)
def delete_organism(organism_id: int, db: Session = Depends(get_db)):
    organism_service.delete_organism(db, organism_id)
