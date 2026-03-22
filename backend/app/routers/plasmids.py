"""Plasmid CRUD API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..application import plasmids as plasmid_service
from ..models import get_db
from ..schemas import (
    AttachmentMeta,
    CassetteOut,
    CassetteUpdate,
    GMOCreate,
    GMOOut,
    GMOUpdate,
    GenBankUpload,
    PlasmidCreate,
    PlasmidListOut,
    PlasmidOut,
    PlasmidUpdate,
)

router = APIRouter(prefix="/plasmids", tags=["plasmids"])


@router.get("/", response_model=list[PlasmidListOut])
def list_plasmids(
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100000,
    db: Session = Depends(get_db),
):
    return plasmid_service.list_plasmids(db, search=search, skip=skip, limit=limit)


@router.get("/{plasmid_id}", response_model=PlasmidOut)
def get_plasmid(plasmid_id: int, db: Session = Depends(get_db)):
    return plasmid_service.get_plasmid(db, plasmid_id)


@router.post("/", response_model=PlasmidOut, status_code=201)
def create_plasmid(data: PlasmidCreate, db: Session = Depends(get_db)):
    return plasmid_service.create_plasmid(db, data)


@router.patch("/{plasmid_id}", response_model=PlasmidOut)
def update_plasmid(plasmid_id: int, data: PlasmidUpdate, db: Session = Depends(get_db)):
    return plasmid_service.update_plasmid(db, plasmid_id, data)


@router.post("/{plasmid_id}/duplicate", response_model=PlasmidOut, status_code=201)
def duplicate_plasmid(plasmid_id: int, db: Session = Depends(get_db)):
    return plasmid_service.duplicate_plasmid(db, plasmid_id)


@router.delete("/{plasmid_id}", status_code=204)
def delete_plasmid(plasmid_id: int, db: Session = Depends(get_db)):
    plasmid_service.delete_plasmid(db, plasmid_id)


@router.get("/{plasmid_id}/cassettes", response_model=list[CassetteOut])
def list_cassettes(plasmid_id: int, db: Session = Depends(get_db)):
    return plasmid_service.list_cassettes(db, plasmid_id)


@router.post("/{plasmid_id}/cassettes", response_model=CassetteOut, status_code=201)
def add_cassette(plasmid_id: int, db: Session = Depends(get_db)):
    return plasmid_service.add_cassette(db, plasmid_id)


@router.patch("/cassettes/{cassette_id}", response_model=CassetteOut)
def update_cassette(cassette_id: int, data: CassetteUpdate, db: Session = Depends(get_db)):
    return plasmid_service.update_cassette(db, cassette_id, data.content)


@router.delete("/cassettes/{cassette_id}", status_code=204)
def delete_cassette(cassette_id: int, db: Session = Depends(get_db)):
    plasmid_service.delete_cassette(db, cassette_id)


@router.get("/{plasmid_id}/gmos", response_model=list[GMOOut])
def list_gmos(plasmid_id: int, db: Session = Depends(get_db)):
    return plasmid_service.list_gmos(db, plasmid_id)


@router.post("/{plasmid_id}/gmos", response_model=GMOOut, status_code=201)
def add_gmo(plasmid_id: int, data: GMOCreate, db: Session = Depends(get_db)):
    return plasmid_service.add_gmo(db, plasmid_id, data)


@router.patch("/gmos/{gmo_id}", response_model=GMOOut)
def update_gmo(gmo_id: int, data: GMOUpdate, db: Session = Depends(get_db)):
    return plasmid_service.update_gmo(db, gmo_id, data)


@router.delete("/gmos/{gmo_id}", status_code=204)
def delete_gmo(gmo_id: int, db: Session = Depends(get_db)):
    plasmid_service.delete_gmo(db, gmo_id)


@router.patch("/gmos/{gmo_id}/destroy", response_model=GMOOut)
def destroy_gmo(gmo_id: int, db: Session = Depends(get_db)):
    return plasmid_service.destroy_gmo(db, gmo_id)


# --- GenBank ---

@router.get("/{plasmid_id}/genbank")
def download_genbank(plasmid_id: int, db: Session = Depends(get_db)):
    payload = plasmid_service.get_genbank_download(db, plasmid_id)
    return Response(
        content=payload.content,
        media_type=payload.media_type,
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )


@router.put("/{plasmid_id}/genbank", response_model=PlasmidOut)
def upload_genbank(plasmid_id: int, data: GenBankUpload, db: Session = Depends(get_db)):
    return plasmid_service.upload_genbank(db, plasmid_id, data)


@router.delete("/{plasmid_id}/genbank", response_model=PlasmidOut)
def delete_genbank(plasmid_id: int, db: Session = Depends(get_db)):
    return plasmid_service.delete_genbank(db, plasmid_id)


# --- Attachments ---

@router.get("/{plasmid_id}/attachments", response_model=list[AttachmentMeta])
def list_attachments(plasmid_id: int, db: Session = Depends(get_db)):
    return plasmid_service.list_attachments(db, plasmid_id)


@router.post("/{plasmid_id}/attachments", response_model=AttachmentMeta, status_code=201)
async def upload_attachment(plasmid_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return plasmid_service.upload_attachment(
        db,
        plasmid_id,
        filename=file.filename,
        content=await file.read(),
    )


@router.get("/attachments/{attach_id}/download")
def download_attachment(attach_id: int, db: Session = Depends(get_db)):
    payload = plasmid_service.get_attachment_download(db, attach_id)
    return Response(
        content=payload.content,
        media_type=payload.media_type,
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )


@router.delete("/attachments/{attach_id}", status_code=204)
def delete_attachment(attach_id: int, db: Session = Depends(get_db)):
    plasmid_service.delete_attachment(db, attach_id)
