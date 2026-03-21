"""Application services for target and favourite organism lists."""

from sqlalchemy.orm import Session

from ..errors import conflict, not_found
from ..models import OrganismFavourite, OrganismSelection


def list_selections(db: Session) -> list[OrganismSelection]:
    return db.query(OrganismSelection).all()


def create_selection(db: Session, organism_name: str) -> OrganismSelection:
    existing = (
        db.query(OrganismSelection)
        .filter(OrganismSelection.organism_name == organism_name)
        .first()
    )
    if existing is not None:
        raise conflict("Organism already in target list")
    selection = OrganismSelection(organism_name=organism_name)
    db.add(selection)
    db.commit()
    db.refresh(selection)
    return selection


def delete_selection(db: Session, item_id: int) -> None:
    selection = (
        db.query(OrganismSelection)
        .filter(OrganismSelection.id == item_id)
        .first()
    )
    if selection is None:
        raise not_found("Target organism not found")
    db.delete(selection)
    db.commit()


def list_favourites(db: Session) -> list[OrganismFavourite]:
    return db.query(OrganismFavourite).all()


def create_favourite(db: Session, organism_name: str) -> OrganismFavourite:
    existing = (
        db.query(OrganismFavourite)
        .filter(OrganismFavourite.organism_name == organism_name)
        .first()
    )
    if existing is not None:
        raise conflict("Organism already in favourites")
    favourite = OrganismFavourite(organism_name=organism_name)
    db.add(favourite)
    db.commit()
    db.refresh(favourite)
    return favourite


def delete_favourite(db: Session, item_id: int) -> None:
    favourite = (
        db.query(OrganismFavourite)
        .filter(OrganismFavourite.id == item_id)
        .first()
    )
    if favourite is None:
        raise not_found("Favourite organism not found")
    db.delete(favourite)
    db.commit()
