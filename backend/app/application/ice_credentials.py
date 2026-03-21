"""Application services for ICE/Filebrowser credentials."""

from sqlalchemy.orm import Session

from ..errors import not_found
from ..models import IceCredentials
from ..schemas import IceCredentialsCreate, IceCredentialsUpdate


def list_credentials(db: Session) -> list[IceCredentials]:
    return db.query(IceCredentials).all()


def get_credentials(db: Session, cred_id: int) -> IceCredentials:
    credentials = db.query(IceCredentials).filter(IceCredentials.id == cred_id).first()
    if credentials is None:
        raise not_found("Credentials not found")
    return credentials


def create_credentials(db: Session, data: IceCredentialsCreate) -> IceCredentials:
    payload = data.model_dump()
    credentials = IceCredentials(
        alias=payload["alias"],
        ice_instance=payload["ice_instance"],
        ice_token_client=payload["ice_token_client"],
        ice_token=payload["ice_token"],
        file_browser_instance=payload["file_browser_instance"],
        file_browser_user=payload["file_browser_user"],
        file_browser_password=payload["file_browser_password"],
    )
    db.add(credentials)
    db.commit()
    db.refresh(credentials)
    return credentials


def update_credentials(
    db: Session,
    cred_id: int,
    data: IceCredentialsUpdate,
) -> IceCredentials:
    credentials = get_credentials(db, cred_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(credentials, key, value)
    db.commit()
    db.refresh(credentials)
    return credentials


def delete_credentials(db: Session, cred_id: int) -> None:
    credentials = get_credentials(db, cred_id)
    db.delete(credentials)
    db.commit()
