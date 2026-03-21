"""Application bootstrap helpers.

These functions make database initialization explicit and idempotent so the
runtime can open a fresh database file and still expose a usable API.
"""

from pathlib import Path

from sqlalchemy.orm import Session

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
from .migrations import CURRENT_SCHEMA_VERSION, migrate_database_if_needed

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
}


def ensure_database_ready(db_path: str) -> None:
    """Create tables and required default rows for the target database."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    migrate_database_if_needed(db_path)
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    session = get_session(db_path)
    try:
        _ensure_seed_data(session)
        session.commit()
    finally:
        session.close()


def prepare_runtime_database(db_path: str) -> None:
    """Initialize the database file and runtime SQLAlchemy engine."""
    ensure_database_ready(db_path)
    init_engine(db_path)


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
