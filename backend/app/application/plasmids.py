"""Plasmid application services.

This module owns the primary plasmid workflows so the API layer can stay thin
and HTTP-specific while the behavior remains reusable and testable.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..errors import not_found
from ..models import Attachment, Cassette, GMO, Plasmid
from ..schemas import GMOCreate, GMOUpdate, GenBankUpload, PlasmidCreate, PlasmidUpdate
from .activity_logs import log_action


@dataclass
class DownloadPayload:
    content: bytes | str
    filename: str
    media_type: str = "application/octet-stream"


def list_plasmids(
    db: Session,
    *,
    search: str | None = None,
    skip: int = 0,
    limit: int = 1000,
) -> list[Plasmid]:
    query = db.query(Plasmid)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Plasmid.name.ilike(pattern),
                Plasmid.alias.ilike(pattern),
                Plasmid.purpose.ilike(pattern),
                Plasmid.backbone_vector.ilike(pattern),
            )
        )
    return query.offset(skip).limit(limit).all()


def get_plasmid(db: Session, plasmid_id: int) -> Plasmid:
    plasmid = db.query(Plasmid).filter(Plasmid.id == plasmid_id).first()
    if plasmid is None:
        raise not_found("Plasmid not found")
    return plasmid


def create_plasmid(db: Session, data: PlasmidCreate) -> Plasmid:
    payload = data.model_dump()
    plasmid = Plasmid(
        name=payload["name"],
        alias=payload["alias"],
        status_id=payload["status_id"],
        purpose=payload["purpose"],
        summary=payload["summary"],
        genbank_content=payload["genbank_content"],
        genbank_filename=payload["genbank_filename"],
        clone=payload["clone"],
        backbone_vector=payload["backbone_vector"],
        marker=payload["marker"],
        target_organism_selection_id=payload["target_organism_selection_id"],
        target_risk_group=payload["target_risk_group"],
        recorded_on=payload["recorded_on"],
    )
    db.add(plasmid)
    db.flush()
    db.add(Cassette(content="Empty", plasmid_id=plasmid.id))
    log_action(db, "create", "plasmid", plasmid.id, plasmid.name)
    db.commit()
    db.refresh(plasmid)
    return plasmid


def update_plasmid(db: Session, plasmid_id: int, data: PlasmidUpdate) -> Plasmid:
    plasmid = get_plasmid(db, plasmid_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        old = getattr(plasmid, key, None)
        if str(old) != str(value):
            log_action(db, "update", "plasmid", plasmid.id, plasmid.name,
                       field=key, old_value=str(old) if old is not None else None, new_value=str(value) if value is not None else None)
        setattr(plasmid, key, value)
    db.commit()
    db.refresh(plasmid)
    return plasmid


def duplicate_plasmid(db: Session, plasmid_id: int) -> Plasmid:
    source = get_plasmid(db, plasmid_id)
    plasmid_copy = Plasmid(
        name=f"{source.name} (copy)",
        alias=source.alias,
        status_id=source.status_id,
        purpose=source.purpose,
        summary=source.summary,
        clone=source.clone,
        backbone_vector=source.backbone_vector,
        marker=source.marker,
        target_risk_group=source.target_risk_group,
    )
    db.add(plasmid_copy)
    db.flush()
    for cassette in source.cassettes:
        db.add(Cassette(content=cassette.content, plasmid_id=plasmid_copy.id))
    log_action(db, "duplicate", "plasmid", plasmid_copy.id, plasmid_copy.name,
               old_value=source.name)
    db.commit()
    db.refresh(plasmid_copy)
    return plasmid_copy


def delete_plasmid(db: Session, plasmid_id: int) -> None:
    plasmid = get_plasmid(db, plasmid_id)
    log_action(db, "delete", "plasmid", plasmid.id, plasmid.name)
    db.delete(plasmid)
    db.commit()


def list_cassettes(db: Session, plasmid_id: int) -> list[Cassette]:
    get_plasmid(db, plasmid_id)
    return db.query(Cassette).filter(Cassette.plasmid_id == plasmid_id).all()


def add_cassette(db: Session, plasmid_id: int) -> Cassette:
    get_plasmid(db, plasmid_id)
    cassette = Cassette(content="Empty", plasmid_id=plasmid_id)
    db.add(cassette)
    db.commit()
    db.refresh(cassette)
    return cassette


def update_cassette(db: Session, cassette_id: int, content: str) -> Cassette:
    cassette = db.query(Cassette).filter(Cassette.id == cassette_id).first()
    if cassette is None:
        raise not_found("Cassette not found")
    cassette.content = content
    db.commit()
    db.refresh(cassette)
    return cassette


def delete_cassette(db: Session, cassette_id: int) -> None:
    cassette = db.query(Cassette).filter(Cassette.id == cassette_id).first()
    if cassette is None:
        raise not_found("Cassette not found")
    db.delete(cassette)
    db.commit()


def list_gmos(db: Session, plasmid_id: int) -> list[GMO]:
    get_plasmid(db, plasmid_id)
    return db.query(GMO).filter(GMO.plasmid_id == plasmid_id).all()


def add_gmo(db: Session, plasmid_id: int, data: GMOCreate) -> GMO:
    get_plasmid(db, plasmid_id)
    created_on = data.created_on or str(date.today())
    gmo = GMO(
        organism_name=data.organism_name,
        approval=data.approval,
        target_risk_group=data.target_risk_group,
        plasmid_id=plasmid_id,
        summary=_build_gmo_summary(
            organism_name=data.organism_name,
            approval=data.approval,
            target_risk_group=data.target_risk_group,
            created_on=created_on,
            destroyed_on=data.destroyed_on,
        ),
        created_on=created_on,
        destroyed_on=data.destroyed_on,
    )
    db.add(gmo)
    db.commit()
    db.refresh(gmo)
    return gmo


def update_gmo(db: Session, gmo_id: int, data: GMOUpdate) -> GMO:
    gmo = db.query(GMO).filter(GMO.id == gmo_id).first()
    if gmo is None:
        raise not_found("GMO not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(gmo, key, value)

    gmo.summary = _build_gmo_summary(
        organism_name=gmo.organism_name,
        approval=gmo.approval,
        target_risk_group=gmo.target_risk_group,
        created_on=gmo.created_on,
        destroyed_on=gmo.destroyed_on,
    )
    db.commit()
    db.refresh(gmo)
    return gmo


def delete_gmo(db: Session, gmo_id: int) -> None:
    gmo = db.query(GMO).filter(GMO.id == gmo_id).first()
    if gmo is None:
        raise not_found("GMO not found")
    db.delete(gmo)
    db.commit()


def destroy_gmo(db: Session, gmo_id: int) -> GMO:
    gmo = db.query(GMO).filter(GMO.id == gmo_id).first()
    if gmo is None:
        raise not_found("GMO not found")
    gmo.destroyed_on = str(date.today())
    gmo.summary = _build_gmo_summary(
        organism_name=gmo.organism_name,
        approval=gmo.approval,
        target_risk_group=gmo.target_risk_group,
        created_on=gmo.created_on,
        destroyed_on=gmo.destroyed_on,
    )
    db.commit()
    db.refresh(gmo)
    return gmo


def _build_gmo_summary(
    *,
    organism_name: str | None,
    approval: str | None,
    target_risk_group: int | None,
    created_on: str | None,
    destroyed_on: str | None,
) -> str:
    created_label = created_on or "tbd"
    destroyed_label = destroyed_on or "tbd"
    organism_label = organism_name or "-"
    approval_label = approval or "-"
    rg_label = target_risk_group if target_risk_group is not None else "-"
    return (
        f"RG {rg_label}   |   Approval: {approval_label}   |   "
        f"{created_label}   -   {destroyed_label}   |   {organism_label}"
    )


def get_genbank_download(db: Session, plasmid_id: int) -> DownloadPayload:
    plasmid = get_plasmid(db, plasmid_id)
    if not plasmid.genbank_content:
        raise not_found("No GenBank file")
    filename = plasmid.genbank_filename or f"{plasmid.name}.gb"
    return DownloadPayload(content=plasmid.genbank_content, filename=filename)


def upload_genbank(db: Session, plasmid_id: int, data: GenBankUpload) -> Plasmid:
    plasmid = get_plasmid(db, plasmid_id)
    plasmid.genbank_filename = data.genbank_filename
    plasmid.genbank_content = data.genbank_content
    plasmid.genbank_flag = "•"
    db.commit()
    db.refresh(plasmid)
    return plasmid


def delete_genbank(db: Session, plasmid_id: int) -> Plasmid:
    plasmid = get_plasmid(db, plasmid_id)
    plasmid.genbank_filename = None
    plasmid.genbank_content = None
    plasmid.genbank_flag = None
    db.commit()
    db.refresh(plasmid)
    return plasmid


def list_attachments(db: Session, plasmid_id: int) -> list[Attachment]:
    get_plasmid(db, plasmid_id)
    return db.query(Attachment).filter(Attachment.plasmid_id == plasmid_id).all()


def upload_attachment(
    db: Session,
    plasmid_id: int,
    *,
    filename: str | None,
    content: bytes,
) -> Attachment:
    get_plasmid(db, plasmid_id)
    attachment = Attachment(file_blob=content, filename=filename, plasmid_id=plasmid_id)
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def get_attachment_download(db: Session, attach_id: int) -> DownloadPayload:
    attachment = db.query(Attachment).filter(Attachment.id == attach_id).first()
    if attachment is None:
        raise not_found("Attachment not found")
    return DownloadPayload(
        content=attachment.file_blob or b"",
        filename=attachment.filename or "file",
    )


def delete_attachment(db: Session, attach_id: int) -> None:
    attachment = db.query(Attachment).filter(Attachment.id == attach_id).first()
    if attachment is None:
        raise not_found("Attachment not found")
    db.delete(attachment)
    db.commit()
