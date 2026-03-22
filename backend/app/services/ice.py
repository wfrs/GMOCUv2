"""JBEI/ICE integration service."""
from __future__ import annotations

try:
    import icebreaker
except ImportError:
    icebreaker = None

from sqlalchemy.orm import Session

from ..models import AppSettings, IceCredentials, Plasmid


def _build_client(creds: IceCredentials):
    if icebreaker is None:
        raise RuntimeError(
            "icebreaker package is not installed. "
            "Run: pip install icebreaker"
        )
    return icebreaker.IceClient({
        "root": creds.ice_instance,
        "token": creds.ice_token,
        "client": creds.ice_token_client,
    })


def _get_settings_and_creds(db: Session) -> tuple[AppSettings, IceCredentials]:
    settings = db.query(AppSettings).first()
    if not settings:
        raise ValueError("No app settings found")
    creds = db.query(IceCredentials).filter_by(id=settings.ice_credentials_id).first()
    if not creds:
        raise ValueError("No ICE credentials configured")
    return settings, creds


def _ensure_folder(ice, initials: str) -> int:
    """Return the ICE folder ID for the given initials, creating it if needed."""
    folders = ice.get_collection_folders("PERSONAL")
    for f in folders:
        if f["folderName"] == initials:
            return f["id"]
    new = ice.create_folder(initials)
    return new["id"]


def test_connection(db: Session) -> dict:
    """Test ICE credentials. Returns {ok: bool, error?: str}."""
    try:
        settings, creds = _get_settings_and_creds(db)
        ice = _build_client(creds)
        ice.get_collection_folders("PERSONAL")
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def sync_plasmid(db: Session, plasmid: Plasmid) -> dict:
    """Sync one plasmid to ICE. Returns {name, status, ice_part_id?, error?}."""
    try:
        settings, creds = _get_settings_and_creds(db)
        ice = _build_client(creds)
    except Exception as exc:
        return {"name": plasmid.name, "status": "error", "error": str(exc)}

    initials = settings.initials or ""

    # Skip template / copy entries (matches legacy behaviour)
    if plasmid.name == f"p{initials}000" or "(Copy)" in (plasmid.name or ""):
        return {"name": plasmid.name, "status": "skipped", "error": "Template or copy"}

    # Honour "upload completed only" setting
    if settings.upload_completed == 1 and plasmid.status_id != 1:
        return {"name": plasmid.name, "status": "skipped", "error": "Not marked complete"}

    try:
        folder_id = _ensure_folder(ice, initials)

        # Resolve existing ICE entry by name
        ice_entries = ice.get_folder_entries(folder_id)
        ice_part = next((e for e in ice_entries if e["name"] == plasmid.name), None)

        if ice_part is None:
            new = ice.create_plasmid(name=plasmid.name)
            ice_part = ice.get_part_infos(new["id"])
            action = "created"
        else:
            action = "updated"

        ice_id = str(ice_part["id"])

        # Resolve status label
        status_label = (
            plasmid.status_ref.name if plasmid.status_ref else "Planned"
        ) or "Planned"

        # Core fields
        ice.request("PUT", f"parts/{ice_id}", data={
            "type": "PLASMID",
            "alias": plasmid.alias,
            "status": status_label,
            "shortDescription": plasmid.purpose,
            "creator": settings.name,
            "creatorEmail": settings.email,
            "plasmidData": {
                "backbone": plasmid.backbone_vector,
                "circular": "true",
            },
        })

        # Custom fields
        ice.set_part_custom_field(ice_id, "Clone", plasmid.clone)
        ice.set_part_custom_field(ice_id, "Cloning", plasmid.summary)
        ice.set_part_custom_field(ice_id, "Entry date", plasmid.recorded_on)

        for idx, cassette in enumerate(plasmid.cassettes):
            ice.set_part_custom_field(ice_id, f"Cassette {idx + 1}", cassette.content)

        # Filebrowser link — use / not os.sep so it's always a valid URL
        if settings.use_file_browser == 1 and creds.file_browser_instance:
            base = creds.file_browser_instance.rstrip("/")
            ice.set_part_custom_field(
                ice_id, "Filebrowser link", f"{base}/{initials}/{plasmid.name}"
            )

        # GenBank attachment
        if plasmid.genbank_content:
            try:
                ice.delete_part_record(ice_id)
            except Exception:
                pass
            ice.attach_record_to_part(
                ice_part_id=ice_id,
                filename=f"{plasmid.name}.gb",
                record_text=plasmid.genbank_content,
            )

        ice.add_to_folder([ice_id], folders_ids=[folder_id])

        # Persist ICE part ID back to the plasmid row
        plasmid.ice_part_id = ice_id
        db.commit()

        return {"name": plasmid.name, "status": action, "ice_part_id": ice_id}

    except Exception as exc:
        db.rollback()
        return {"name": plasmid.name, "status": "error", "error": str(exc)}


def sync_all(db: Session) -> list[dict]:
    """Sync all eligible plasmids. Returns per-plasmid result list."""
    settings = db.query(AppSettings).first()
    if not settings or not settings.use_ice:
        return []

    plasmids = db.query(Plasmid).all()
    return [sync_plasmid(db, p) for p in plasmids]
