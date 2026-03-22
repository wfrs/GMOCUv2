"""Organism application services."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..errors import conflict, not_found
from ..models import Organism
from ..schemas import OrganismCreate, OrganismUpdate
from .activity_logs import log_action


def list_organisms(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 500,
    search: str | None = None,
) -> list[Organism]:
    query = db.query(Organism)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Organism.short_name.ilike(pattern),
                Organism.full_name.ilike(pattern),
            )
        )
    return query.offset(skip).limit(limit).all()


def get_organism(db: Session, organism_id: int) -> Organism:
    organism = db.query(Organism).filter(Organism.id == organism_id).first()
    if organism is None:
        raise not_found("Organism not found")
    return organism


def create_organism(db: Session, data: OrganismCreate) -> Organism:
    existing = db.query(Organism).filter(Organism.short_name == data.short_name).first()
    if existing is not None:
        raise conflict("Organism with this short name already exists")
    organism = Organism(
        full_name=data.full_name,
        short_name=data.short_name,
        risk_group=data.risk_group,
    )
    db.add(organism)
    db.flush()
    log_action(db, "create", "organism", organism.id, organism.short_name)
    db.commit()
    db.refresh(organism)
    return organism


def update_organism(db: Session, organism_id: int, data: OrganismUpdate) -> Organism:
    organism = get_organism(db, organism_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        old = getattr(organism, key, None)
        if str(old) != str(value):
            log_action(db, "update", "organism", organism.id, organism.short_name,
                       field=key, old_value=str(old) if old is not None else None, new_value=str(value) if value is not None else None)
        setattr(organism, key, value)
    db.commit()
    db.refresh(organism)
    return organism


def delete_organism(db: Session, organism_id: int) -> None:
    organism = get_organism(db, organism_id)
    log_action(db, "delete", "organism", organism.id, organism.short_name)
    db.delete(organism)
    db.commit()
