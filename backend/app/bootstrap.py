"""Application bootstrap helpers.

These functions make database initialization explicit and idempotent so the
runtime can open a fresh database file and still expose a usable API.
"""

import shutil
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import DEFAULT_DATABASE_PATH, LEGACY_DATABASE_PATH
from .models import (
    AppSettings,
    Base,
    IceCredentials,
    PlasmidStatus,
    SchemaMeta,
    get_engine,
    get_session,
    init_engine,
)
from .migrations import CURRENT_SCHEMA_VERSION, inspect_database, migrate_database_if_needed

DEFAULT_SELECTION_VALUES = {
    1: "Complete",
    2: "In Progress",
    3: "Abandoned",
    4: "Planned",
}

DEFAULT_ICE_CREDENTIALS = {
    "id": 1,
    "alias": "ICE-lab.local",
    "ice_instance": "https://public-registry.jbei.org/",
    "ice_token_client": "X-ICE-API-Token-Client",
    "ice_token": "X-ICE-API-Token",
    "file_browser_instance": "",
    "file_browser_user": "",
    "file_browser_password": "",
}

DEFAULT_SETTINGS = {
    "id": 1,
    "name": "Name",
    "initials": "__",
    "email": "xxx@xxx.com",
    "institution": "Az.: xxx / Anlage Nr.: xxx",
    "glossary_sheet_id": "ID from link",
    "duplicate_gmos": 0,
    "upload_completed": 0,
    "upload_abi": 0,
    "scale": 1,
    "font_size": 13,
    "theme": "Reddit",
    "horizontal_layout": 1,
    "use_ice": 0,
    "use_file_browser": 0,
    "use_gdrive": 0,
    "drive_folder_id": "ID from link",
    "zip_files": 1,
    "autosync": 0,
    "date_format": "eu",
    "reduce_motion": 0,
    "mono_genbank": 0,
}


_APP_SETTINGS_NEW_COLUMNS = [
    ("date_format",   "TEXT    DEFAULT 'eu'"),
    ("reduce_motion", "INTEGER DEFAULT 0"),
    ("mono_genbank",  "INTEGER DEFAULT 0"),
]

_PLASMIDS_NEW_COLUMNS = [
    ("ice_part_id", "TEXT"),
]


def _ensure_app_settings_columns(engine) -> None:
    """Add new columns to app_settings for existing databases that predate them."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(app_settings)"))}
        for col, definition in _APP_SETTINGS_NEW_COLUMNS:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE app_settings ADD COLUMN {col} {definition}"))
        conn.commit()


def _ensure_plasmids_columns(engine) -> None:
    """Add new columns to plasmids for existing databases that predate them."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(plasmids)"))}
        for col, definition in _PLASMIDS_NEW_COLUMNS:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE plasmids ADD COLUMN {col} {definition}"))
        conn.commit()


def ensure_database_ready(db_path: str) -> None:
    """Create tables and required default rows for the target database."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    migrate_database_if_needed(db_path)
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    _ensure_app_settings_columns(engine)
    _ensure_plasmids_columns(engine)

    session = get_session(db_path)
    try:
        _ensure_seed_data(session)
        session.commit()
    finally:
        session.close()


def prepare_runtime_database(db_path: str) -> None:
    """Initialize the database file and runtime SQLAlchemy engine."""
    _adopt_existing_v2_database(db_path)
    ensure_database_ready(db_path)
    init_engine(db_path)


def _adopt_existing_v2_database(db_path: str) -> None:
    """Copy a previously migrated v2 DB away from the legacy default path.

    This avoids collisions with the old app while preserving an already-upgraded
    runtime DB for the new app.
    """
    target = Path(db_path)
    if target.exists() or target != DEFAULT_DATABASE_PATH:
        return

    legacy_path = LEGACY_DATABASE_PATH
    if not legacy_path.exists() or legacy_path == target:
        return

    inspection = inspect_database(str(legacy_path))
    if inspection.kind != "current":
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy_path, target)


def _ensure_seed_data(session: Session) -> None:
    _ensure_selection_values(session)
    default_credentials = _ensure_default_credentials(session)
    _ensure_settings(session, default_credentials.id)
    _ensure_schema_meta(session)


def _ensure_selection_values(session: Session) -> None:
    existing_ids = {
        selection_id
        for (selection_id,) in session.query(PlasmidStatus.id).all()
    }
    for selection_id, label in DEFAULT_SELECTION_VALUES.items():
        if selection_id not in existing_ids:
            session.add(PlasmidStatus(id=selection_id, name=label))


def _ensure_default_credentials(session: Session) -> IceCredentials:
    credentials = (
        session.query(IceCredentials)
        .filter_by(id=DEFAULT_ICE_CREDENTIALS["id"])
        .first()
    )
    if credentials is None:
        credentials = IceCredentials(**DEFAULT_ICE_CREDENTIALS)
        session.add(credentials)
        session.flush()
    return credentials


def _ensure_settings(session: Session, credentials_id: int) -> None:
    settings = session.query(AppSettings).first()
    if settings is None:
        session.add(AppSettings(ice_credentials_id=credentials_id, **DEFAULT_SETTINGS))
        return

    if settings.ice_credentials_id is None:
        settings.ice_credentials_id = credentials_id


def _ensure_schema_meta(session: Session) -> None:
    metadata = session.query(SchemaMeta).order_by(SchemaMeta.id.desc()).first()
    if metadata is None:
        session.add(
            SchemaMeta(
                schema_version=CURRENT_SCHEMA_VERSION,
                migrated_from="native",
            )
        )
        return

    if metadata.schema_version < CURRENT_SCHEMA_VERSION:
        metadata.schema_version = CURRENT_SCHEMA_VERSION
