"""OrganismSelection and OrganismFavourites API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..application import organism_lists as organism_list_service
from ..models import get_db
from ..schemas import (
    OrganismFavouriteCreate,
    OrganismFavouriteOut,
    OrganismSelectionCreate,
    OrganismSelectionOut,
)

router = APIRouter(tags=["organism-selections"])


# --- Target Organisms ---

@router.get("/organism-selections/", response_model=list[OrganismSelectionOut])
def list_selections(db: Session = Depends(get_db)):
    return organism_list_service.list_selections(db)


@router.post("/organism-selections/", response_model=OrganismSelectionOut, status_code=201)
def create_selection(data: OrganismSelectionCreate, db: Session = Depends(get_db)):
    return organism_list_service.create_selection(db, data.organism_name)


@router.delete("/organism-selections/{item_id}", status_code=204)
def delete_selection(item_id: int, db: Session = Depends(get_db)):
    organism_list_service.delete_selection(db, item_id)


# --- Favourite Organisms ---

@router.get("/organism-favourites/", response_model=list[OrganismFavouriteOut])
def list_favourites(db: Session = Depends(get_db)):
    return organism_list_service.list_favourites(db)


@router.post("/organism-favourites/", response_model=OrganismFavouriteOut, status_code=201)
def create_favourite(data: OrganismFavouriteCreate, db: Session = Depends(get_db)):
    return organism_list_service.create_favourite(db, data.organism_name)


@router.delete("/organism-favourites/{item_id}", status_code=204)
def delete_favourite(item_id: int, db: Session = Depends(get_db)):
    organism_list_service.delete_favourite(db, item_id)
