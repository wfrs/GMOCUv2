"""Database initialization helpers and compatibility utilities."""

import sqlite3
from pathlib import Path
from datetime import date

from .bootstrap import ensure_database_ready
from .migrations import needs_schema_migration
from .models import AppSettings, SchemaMeta, get_session


def init_db(db_path: str) -> None:
    """Create tables and seed required defaults for a database file."""
    ensure_database_ready(db_path)


def read_settings(db_path: str) -> dict:
    """Read settings and associated ICE credentials into a flat dict."""
    session = get_session(db_path)
    try:
        settings = session.query(AppSettings).first()
        if settings is None:
            return {}
        creds = settings.credentials

        return {
            "user_name": settings.name,
            "initials": settings.initials,
            "email": settings.email,
            "institution": settings.institution,
            "ice": settings.ice,
            "duplicate_gmos": settings.duplicate_gmos,
            "upload_completed": settings.upload_completed,
            "upload_abi": settings.upload_abi,
            "scale": settings.scale,
            "font_size": settings.font_size,
            "style": settings.style,
            "horizontal_layout": settings.horizontal_layout,
            "use_ice": settings.use_ice,
            "use_filebrowser": settings.use_filebrowser,
            "use_gdrive": settings.use_gdrive,
            "zip_files": settings.zip_files,
            "autosync": settings.autosync,
            "ice_instance": creds.ice_instance if creds else None,
            "ice_token": str(creds.ice_token) if creds else None,
            "ice_token_client": creds.ice_token_client if creds else None,
            "filebrowser_instance": creds.filebrowser_instance if creds else None,
            "filebrowser_user": creds.filebrowser_user if creds else None,
            "filebrowser_pwd": creds.filebrowser_pwd if creds else None,
        }
    finally:
        session.close()


def needs_migration(db_path: str, current_version: float) -> bool:
    """Check whether the database needs a schema migration.

    The ``current_version`` argument is retained for compatibility with the
    legacy API, but schema migration decisions are now based on structural
    inspection rather than the old ``Settings.version`` field.
    """
    del current_version
    return needs_schema_migration(db_path)


def get_db_version(db_path: str) -> float:
    """Return the native schema version stored in ``schema_meta``, or 0."""
    if not Path(db_path).exists():
        return 0
    session = get_session(db_path)
    try:
        metadata = session.query(SchemaMeta).order_by(SchemaMeta.id.desc()).first()
        return float(metadata.schema_version) if metadata else 0
    finally:
        session.close()


def backup_database(db_path: str, user_data: str) -> str:
    """Create a backup of the database. Returns the backup path."""
    name = f"gmocu_backup_{date.today().strftime('%Y-%m-%d')}.db"
    backup_path = str(Path(user_data) / name)

    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(backup_path)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    return backup_path
