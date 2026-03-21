"""Database schema inspection and migration helpers."""

from __future__ import annotations

import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .models import Base, get_engine

CURRENT_SCHEMA_VERSION = 10

LEGACY_TABLE_RENAMES = {
    "SelectionValues": "legacy_selection_values",
    "Plasmids": "legacy_plasmids",
    "Attachments": "legacy_attachments",
    "Cassettes": "legacy_cassettes",
    "GMOs": "legacy_gmos",
    "OrganismSelection": "legacy_organism_selections",
    "OrganismFavourites": "legacy_organism_favourites",
    "Features": "legacy_features",
    "Organisms": "legacy_organisms",
    "Settings": "legacy_settings",
    "IceCredentials": "legacy_ice_credentials",
    "SchemaMeta": "legacy_schema_meta",
}

V2_TABLES = {
    "plasmid_statuses",
    "plasmids",
    "attachments",
    "cassettes",
    "gmos",
    "organism_selections",
    "organism_favourites",
    "features",
    "organisms",
    "app_settings",
    "ice_credentials",
    "schema_meta",
}


@dataclass(frozen=True)
class DatabaseInspection:
    kind: str
    legacy_version: str | None = None
    schema_version: int | None = None


@dataclass(frozen=True)
class MigrationResult:
    migrated: bool
    inspection: DatabaseInspection
    backup_path: str | None = None


def inspect_database(db_path: str) -> DatabaseInspection:
    db_file = Path(db_path)
    if not db_file.exists():
        return DatabaseInspection(kind="missing")

    conn = sqlite3.connect(db_path)
    try:
        table_names = _get_table_names(conn)
        if not table_names:
            return DatabaseInspection(kind="empty")

        if _is_v2_schema(table_names):
            return DatabaseInspection(
                kind="current",
                schema_version=_read_v2_schema_version(conn),
            )

        if _has_legacy_schema(table_names):
            return DatabaseInspection(
                kind="legacy",
                legacy_version=_infer_legacy_version(conn),
            )

        return DatabaseInspection(kind="unknown")
    finally:
        conn.close()


def needs_schema_migration(db_path: str) -> bool:
    inspection = inspect_database(db_path)
    if inspection.kind in {"missing", "empty"}:
        return False
    if inspection.kind == "current":
        return (inspection.schema_version or 0) < CURRENT_SCHEMA_VERSION
    return True


def migrate_database_if_needed(db_path: str) -> MigrationResult:
    inspection = inspect_database(db_path)

    if inspection.kind in {"missing", "empty"}:
        return MigrationResult(migrated=False, inspection=inspection)

    if inspection.kind == "current" and (inspection.schema_version or 0) >= CURRENT_SCHEMA_VERSION:
        return MigrationResult(migrated=False, inspection=inspection)

    if inspection.kind != "legacy":
        raise RuntimeError(f"Unsupported database format for {db_path}")

    backup_path = _backup_database_file(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=OFF;")
        _rename_legacy_tables(conn)
        conn.commit()

        engine = get_engine(db_path)
        Base.metadata.create_all(engine)

        _copy_legacy_data(conn, inspection.legacy_version)
        _drop_legacy_tables(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return MigrationResult(
        migrated=True,
        inspection=inspect_database(db_path),
        backup_path=backup_path,
    )


def _copy_legacy_data(conn: sqlite3.Connection, legacy_version: str | None) -> None:
    _copy_statuses(conn)
    _copy_credentials(conn)
    _copy_settings(conn)
    _copy_features(conn)
    _copy_organisms(conn)
    _copy_organism_selections(conn)
    _copy_organism_favourites(conn)
    _copy_plasmids(conn)
    _copy_cassettes(conn)
    _copy_gmos(conn)
    _copy_attachments(conn)
    _write_schema_meta(conn, legacy_version)


def _copy_statuses(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query(
        "SELECT id, value AS name FROM legacy_selection_values",
        conn,
    )
    frame.to_sql("plasmid_statuses", conn, if_exists="append", index=False)


def _copy_credentials(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query("SELECT * FROM legacy_ice_credentials", conn)
    for column in ("filebrowser_instance", "filebrowser_user", "filebrowser_pwd"):
        if column not in frame.columns:
            frame[column] = ""

    frame = frame.rename(
        columns={
            "filebrowser_instance": "file_browser_instance",
            "filebrowser_user": "file_browser_user",
            "filebrowser_pwd": "file_browser_password",
        }
    )
    frame = frame[
        [
            "id",
            "alias",
            "ice_instance",
            "ice_token_client",
            "ice_token",
            "file_browser_instance",
            "file_browser_user",
            "file_browser_password",
        ]
    ]
    frame.to_sql("ice_credentials", conn, if_exists="append", index=False)


def _copy_settings(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query("SELECT * FROM legacy_settings", conn)
    if frame.empty:
        return

    defaults = {
        "horizontal_layout": 1,
        "use_ice": 0,
        "use_filebrowser": 0,
        "use_gdrive": 0,
        "gdrive_id": "ID from link",
        "gdrive_glossary": "ID from link",
        "zip_files": 1,
        "autosync": 0,
        "upload_abi": 0,
        "style": "Reddit",
    }
    for column, default in defaults.items():
        if column not in frame.columns:
            frame[column] = default

    frame = frame.rename(
        columns={
            "ice": "ice_credentials_id",
            "gdrive_glossary": "glossary_sheet_id",
            "style": "theme",
            "use_filebrowser": "use_file_browser",
            "gdrive_id": "drive_folder_id",
        }
    )
    frame = frame[
        [
            "id",
            "name",
            "initials",
            "email",
            "institution",
            "ice_credentials_id",
            "glossary_sheet_id",
            "duplicate_gmos",
            "upload_completed",
            "upload_abi",
            "scale",
            "font_size",
            "theme",
            "horizontal_layout",
            "use_ice",
            "use_file_browser",
            "use_gdrive",
            "drive_folder_id",
            "zip_files",
            "autosync",
        ]
    ]
    frame.to_sql("app_settings", conn, if_exists="append", index=False)


def _copy_features(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query("SELECT * FROM legacy_features", conn)
    if "uid" not in frame.columns:
        frame["uid"] = [uuid.uuid4().hex for _ in range(len(frame))]
    if "synced" not in frame.columns:
        frame["synced"] = 0
    frame["risk"] = frame["risk"].replace({"None": "No Risk"}).fillna("No Risk")
    frame = frame[["id", "annotation", "alias", "risk", "organism", "uid", "synced"]]
    frame.to_sql("features", conn, if_exists="append", index=False)


def _copy_organisms(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query("SELECT * FROM legacy_organisms", conn)
    if "uid" not in frame.columns:
        frame["uid"] = [uuid.uuid4().hex for _ in range(len(frame))]
    if "synced" not in frame.columns:
        frame["synced"] = 0
    frame = frame.rename(columns={"RG": "risk_group"})
    frame = frame[["id", "full_name", "short_name", "risk_group", "uid", "synced"]]
    frame.to_sql("organisms", conn, if_exists="append", index=False)


def _copy_organism_selections(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query(
        "SELECT orga_sel_id AS id, organism_name FROM legacy_organism_selections",
        conn,
    )
    frame.to_sql("organism_selections", conn, if_exists="append", index=False)


def _copy_organism_favourites(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query(
        """
        SELECT orga_fav_id AS id, organism_fav_name AS organism_name
        FROM legacy_organism_favourites
        """,
        conn,
    )
    frame.to_sql("organism_favourites", conn, if_exists="append", index=False)


def _copy_plasmids(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query("SELECT * FROM legacy_plasmids", conn)
    defaults = {
        "gb": None,
        "genebank": None,
        "gb_name": None,
        "FKattachment": None,
        "organism_selector": None,
        "target_RG": 1,
        "generated": None,
        "destroyed": None,
        "date": None,
    }
    for column, default in defaults.items():
        if column not in frame.columns:
            frame[column] = default

    frame = frame.rename(
        columns={
            "status": "status_id",
            "gb": "genbank_flag",
            "genebank": "genbank_content",
            "gb_name": "genbank_filename",
            "FKattachment": "attachment_id",
            "organism_selector": "target_organism_selection_id",
            "target_RG": "target_risk_group",
            "generated": "created_on",
            "destroyed": "destroyed_on",
            "date": "recorded_on",
        }
    )
    frame = frame[
        [
            "id",
            "name",
            "alias",
            "status_id",
            "genbank_flag",
            "purpose",
            "summary",
            "genbank_content",
            "genbank_filename",
            "attachment_id",
            "clone",
            "backbone_vector",
            "marker",
            "target_organism_selection_id",
            "target_risk_group",
            "created_on",
            "destroyed_on",
            "recorded_on",
        ]
    ]
    frame.to_sql("plasmids", conn, if_exists="append", index=False)


def _copy_cassettes(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query(
        "SELECT cassette_id AS id, content, plasmid_id FROM legacy_cassettes",
        conn,
    )
    frame.to_sql("cassettes", conn, if_exists="append", index=False)


def _copy_gmos(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query("SELECT * FROM legacy_gmos", conn)
    defaults = {
        "GMO_summary": None,
        "target_RG": 1,
        "date_generated": None,
        "date_destroyed": None,
        "entry_date": None,
    }
    for column, default in defaults.items():
        if column not in frame.columns:
            frame[column] = default

    frame = frame.rename(
        columns={
            "organism_id": "id",
            "GMO_summary": "summary",
            "target_RG": "target_risk_group",
            "date_generated": "created_on",
            "date_destroyed": "destroyed_on",
        }
    )
    frame = frame[
        [
            "id",
            "summary",
            "organism_name",
            "approval",
            "plasmid_id",
            "target_risk_group",
            "created_on",
            "destroyed_on",
            "entry_date",
        ]
    ]
    frame.to_sql("gmos", conn, if_exists="append", index=False)


def _copy_attachments(conn: sqlite3.Connection) -> None:
    frame = pd.read_sql_query("SELECT * FROM legacy_attachments", conn)
    frame = frame.rename(
        columns={
            "attach_id": "id",
            "file": "file_blob",
            "Filename": "filename",
        }
    )
    frame = frame[["id", "file_blob", "filename", "plasmid_id"]]
    frame.to_sql("attachments", conn, if_exists="append", index=False)


def _write_schema_meta(conn: sqlite3.Connection, legacy_version: str | None) -> None:
    conn.execute(
        """
        INSERT INTO schema_meta(schema_version, migrated_from)
        VALUES (?, ?)
        """,
        (CURRENT_SCHEMA_VERSION, f"legacy:{legacy_version or 'unknown'}"),
    )


def _rename_legacy_tables(conn: sqlite3.Connection) -> None:
    for old_name, temp_name in LEGACY_TABLE_RENAMES.items():
        if _table_exists(conn, old_name):
            conn.execute(f'ALTER TABLE "{old_name}" RENAME TO "{temp_name}"')


def _drop_legacy_tables(conn: sqlite3.Connection) -> None:
    for temp_name in LEGACY_TABLE_RENAMES.values():
        conn.execute(f'DROP TABLE IF EXISTS "{temp_name}"')


def _get_table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table';"
    ).fetchall()
    return {name for (name,) in rows}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?;",
        (table_name,),
    ).fetchone()
    return row is not None


def _is_v2_schema(table_names: set[str]) -> bool:
    lowered = {name.lower() for name in table_names}
    return V2_TABLES.issubset(lowered)


def _has_legacy_schema(table_names: set[str]) -> bool:
    return "Plasmids" in table_names and "Settings" in table_names


def _read_v2_schema_version(conn: sqlite3.Connection) -> int | None:
    table_name = _resolve_table_name(conn, "schema_meta")
    if table_name is None:
        return None
    row = conn.execute(
        f'SELECT schema_version FROM "{table_name}" ORDER BY id DESC LIMIT 1;'
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return int(row[0])


def _resolve_table_name(conn: sqlite3.Connection, lower_name: str) -> str | None:
    for name in _get_table_names(conn):
        if name.lower() == lower_name:
            return name
    return None


def _infer_legacy_version(conn: sqlite3.Connection) -> str:
    settings_table = _resolve_table_name(conn, "settings")
    if settings_table is None:
        return "legacy"

    columns = {
        row[1] for row in conn.execute(f'PRAGMA table_info("{settings_table}");').fetchall()
    }
    if "version" in columns:
        row = conn.execute(f'SELECT version FROM "{settings_table}" LIMIT 1;').fetchone()
        if row is not None and row[0] not in (None, ""):
            return str(row[0])

    if "horizontal_layout" not in columns:
        return "pre-0.5"
    if "use_ice" not in columns or "use_filebrowser" not in columns:
        return "0.5"
    if "use_gdrive" not in columns:
        return "0.6"
    return "legacy"


def _backup_database_file(db_path: str) -> str:
    path = Path(db_path)
    backup_path = path.with_suffix(path.suffix + ".pre-v2-schema.bak")
    if not backup_path.exists():
        shutil.copy2(path, backup_path)
    return str(backup_path)
