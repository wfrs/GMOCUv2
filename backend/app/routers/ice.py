"""JBEI/ICE sync API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..models import Plasmid, get_db
from ..services import ice as ice_service

router = APIRouter(prefix="/ice", tags=["ice"])


@router.post("/test")
def test_connection(db: Session = Depends(get_db)):
    """Test the stored ICE credentials by connecting to the server."""
    result = ice_service.test_connection(db)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Connection failed"))
    return result


@router.post("/sync/{plasmid_id}")
def sync_plasmid(plasmid_id: int, db: Session = Depends(get_db)):
    """Sync a single plasmid to ICE and return the result."""
    plasmid = db.query(Plasmid).filter(Plasmid.id == plasmid_id).first()
    if plasmid is None:
        raise HTTPException(status_code=404, detail="Plasmid not found")
    result = ice_service.sync_plasmid(db, plasmid)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Sync failed"))
    return result


@router.post("/sync")
def sync_all(db: Session = Depends(get_db)):
    """Sync all eligible plasmids to ICE. Returns per-plasmid results."""
    return ice_service.sync_all(db)
