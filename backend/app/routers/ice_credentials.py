"""IceCredentials API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..application import ice_credentials as credentials_service
from ..models import get_db
from ..schemas import IceCredentialsCreate, IceCredentialsOut, IceCredentialsUpdate

router = APIRouter(prefix="/ice-credentials", tags=["ice-credentials"])


@router.get("/", response_model=list[IceCredentialsOut])
def list_credentials(db: Session = Depends(get_db)):
    return credentials_service.list_credentials(db)


@router.post("/", response_model=IceCredentialsOut, status_code=201)
def create_credentials(data: IceCredentialsCreate, db: Session = Depends(get_db)):
    return credentials_service.create_credentials(db, data)


@router.patch("/{cred_id}", response_model=IceCredentialsOut)
def update_credentials(cred_id: int, data: IceCredentialsUpdate, db: Session = Depends(get_db)):
    return credentials_service.update_credentials(db, cred_id, data)


@router.delete("/{cred_id}", status_code=204)
def delete_credentials(cred_id: int, db: Session = Depends(get_db)):
    credentials_service.delete_credentials(db, cred_id)
