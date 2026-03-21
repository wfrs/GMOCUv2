"""Glossary and cross-database import workflows."""

import re
import sqlite3

import pandas as pd

from ..models import Feature, Organism, get_session
from .normalization import sanitize_annotation


def _parse_cassette_features(content: str) -> list[str]:
    cleaned = re.sub(r"\[.*?\]", "", content)
    return [feature for feature in cleaned.split("-") if feature]


def _sanitize_annotations(frame: pd.DataFrame) -> pd.DataFrame:
    sanitized = frame.copy()
    sanitized["annotation"] = sanitized["annotation"].map(sanitize_annotation)
    return sanitized


def add_features_from_dataframe(
    db_path: str,
    frame: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    """Import features from a DataFrame, skipping existing annotations."""
    session = get_session(db_path)
    try:
        existing = {row[0] for row in session.query(Feature.annotation).all()}
        sanitized = _sanitize_annotations(frame)

        skipped = sanitized[sanitized["annotation"].isin(existing)]["annotation"].tolist()
        new_rows = sanitized[~sanitized["annotation"].isin(existing)].fillna("None").reset_index(drop=True)
        added = new_rows["annotation"].tolist()

        for _, row in new_rows.iterrows():
            session.add(
                Feature(
                    annotation=row["annotation"],
                    alias=row["alias"],
                    risk=row["risk"],
                    organism=row["organism"],
                )
            )
        session.commit()
        return added, skipped
    finally:
        session.close()


def add_organisms_from_dataframe(db_path: str, frame: pd.DataFrame) -> list[str]:
    """Import organisms from a DataFrame, skipping existing short names."""
    session = get_session(db_path)
    try:
        existing = {row[0] for row in session.query(Organism.short_name).all()}
        new_rows = frame[~frame["short_name"].isin(existing)].reset_index(drop=True)
        added = new_rows["short_name"].tolist()
        risk_group_column = "risk_group" if "risk_group" in frame.columns else "RG"

        for _, row in new_rows.iterrows():
            session.add(
                Organism(
                    short_name=row["short_name"],
                    full_name=row["full_name"],
                    risk_group=str(row[risk_group_column]),
                )
            )
        session.commit()
        return added
    finally:
        session.close()


def get_importable_plasmids(db_path: str, import_file: str) -> list[str]:
    """Return plasmid names in the import file that do not exist locally."""
    conn = sqlite3.connect(db_path)
    try:
        existing = set(pd.read_sql_query("SELECT name FROM plasmids", conn)["name"])
        conn.execute("ATTACH DATABASE ? AS other", (import_file,))
        imported = pd.read_sql_query("SELECT name FROM other.Plasmids", conn)
        return [name for name in imported["name"] if name not in existing]
    finally:
        conn.close()


def import_plasmids(db_path: str, import_file: str, selected_names: list[str]) -> dict:
    """Import selected plasmids from another GMOCU database."""
    conn = sqlite3.connect(db_path, timeout=60)
    cursor = conn.cursor()
    existing_names = set(pd.read_sql_query("SELECT name FROM plasmids", conn)["name"])

    try:
        cursor.execute("ATTACH DATABASE ? AS other", (import_file,))
        imported_plasmids = pd.read_sql_query("SELECT * FROM other.Plasmids", conn)

        added_cassette_ids: list[int] = []
        imported_plasmid_ids: list[int] = []

        for _, plasmid in imported_plasmids.iterrows():
            if plasmid["name"] not in existing_names and plasmid["name"] in selected_names:
                imported_plasmid_ids.append(plasmid["id"])
                cursor.execute(
                    "INSERT INTO plasmids (name, alias, status_id, genbank_flag, purpose, summary, "
                    "genbank_content, genbank_filename, attachment_id, clone, backbone_vector, marker, "
                    "target_organism_selection_id, target_risk_group, created_on, destroyed_on, recorded_on) "
                    "SELECT name, alias, status, gb, purpose, summary, genebank, "
                    "gb_name, FKattachment, clone, backbone_vector, marker, "
                    "organism_selector, target_RG, generated, destroyed, date "
                    "FROM other.Plasmids WHERE other.Plasmids.id = ?",
                    (plasmid["id"],),
                )
                cursor.execute("SELECT MAX(id) FROM plasmids")
                max_id = cursor.fetchone()[0]

                cursor.execute(
                    "INSERT INTO cassettes (content) SELECT content "
                    "FROM other.Cassettes WHERE other.Cassettes.plasmid_id = ?",
                    (plasmid["id"],),
                )
                cursor.execute("SELECT id FROM cassettes WHERE plasmid_id IS NULL")
                for (cassette_id,) in cursor.fetchall():
                    cursor.execute(
                        "UPDATE cassettes SET plasmid_id = ? WHERE id = ?",
                        (max_id, cassette_id),
                    )
                    added_cassette_ids.append(cassette_id)

                cursor.execute(
                    "INSERT INTO gmos (summary, organism_name, approval, "
                    "target_risk_group, created_on, destroyed_on, entry_date) "
                    "SELECT GMO_summary, organism_name, approval, target_RG, "
                    "date_generated, date_destroyed, entry_date "
                    "FROM other.GMOs WHERE other.GMOs.plasmid_id = ?",
                    (plasmid["id"],),
                )
                cursor.execute("SELECT id FROM gmos WHERE plasmid_id IS NULL")
                for (organism_id,) in cursor.fetchall():
                    cursor.execute(
                        "UPDATE gmos SET plasmid_id = ? WHERE id = ?",
                        (max_id, organism_id),
                    )

                cursor.execute(
                    "INSERT INTO attachments (file_blob, filename) "
                    "SELECT file, Filename FROM other.Attachments "
                    "WHERE other.Attachments.plasmid_id = ?",
                    (plasmid["id"],),
                )
                cursor.execute("SELECT id FROM attachments WHERE plasmid_id IS NULL")
                for (attachment_id,) in cursor.fetchall():
                    cursor.execute(
                        "UPDATE attachments SET plasmid_id = ? WHERE id = ?",
                        (max_id, attachment_id),
                    )

        conn.commit()

        unique_features: set[str] = set()
        cassettes = pd.read_sql_query("SELECT * FROM cassettes", conn)
        for _, row in cassettes.iterrows():
            if row["id"] in added_cassette_ids:
                for feature in _parse_cassette_features(row["content"]):
                    unique_features.add(feature)

        existing_features = set(pd.read_sql_query("SELECT annotation FROM features", conn)["annotation"])
        features_columns = [item[1] for item in cursor.execute("PRAGMA other.table_info(Features)")]
        missing_features = list(unique_features - existing_features)

        nouid = False
        for feature_name in missing_features:
            if "uid" not in features_columns:
                nouid = True
                cursor.execute(
                    "INSERT INTO features (annotation, alias, risk, organism) "
                    "SELECT annotation, alias, risk, organism "
                    "FROM other.Features WHERE other.Features.annotation = ?",
                    (feature_name,),
                )
            else:
                cursor.execute(
                    "INSERT INTO features (annotation, alias, risk, organism, uid) "
                    "SELECT annotation, alias, risk, organism, uid "
                    "FROM other.Features WHERE other.Features.annotation = ?",
                    (feature_name,),
                )
        if missing_features:
            cursor.execute("UPDATE features SET risk = REPLACE(risk, 'None', 'No Risk')")
        conn.commit()

        missing_org_from_features = pd.DataFrame(columns=["organism"])
        missing_org_from_gmos = pd.DataFrame(columns=["organism_name"])

        if missing_features:
            if len(missing_features) > 1:
                missing_org_from_features = pd.read_sql_query(
                    f"SELECT organism FROM features WHERE annotation IN {str(tuple(missing_features))}",
                    conn,
                )
            else:
                missing_org_from_features = pd.read_sql_query(
                    "SELECT organism FROM features WHERE annotation = ?",
                    conn,
                    params=(missing_features[0],),
                )

        if imported_plasmid_ids:
            if len(imported_plasmid_ids) > 1:
                missing_org_from_gmos = pd.read_sql_query(
                    "SELECT organism_name FROM other.GMOs WHERE plasmid_id IN "
                    f"{str(tuple(imported_plasmid_ids))}",
                    conn,
                )
            else:
                missing_org_from_gmos = pd.read_sql_query(
                    "SELECT organism_name FROM other.GMOs WHERE plasmid_id = ?",
                    conn,
                    params=(imported_plasmid_ids[0],),
                )

        missing_org_from_gmos = missing_org_from_gmos.rename(columns={"organism_name": "organism"})
        all_missing = set(
            pd.concat(
                [missing_org_from_features["organism"], missing_org_from_gmos["organism"]],
                ignore_index=True,
            )
        )

        local_orgs = set(pd.read_sql_query("SELECT short_name FROM organisms", conn)["short_name"])
        missing_organisms = list(all_missing - local_orgs)

        organisms_columns = [item[1] for item in cursor.execute("PRAGMA other.table_info(Organisms)")]
        for organism_name in missing_organisms:
            if "uid" not in organisms_columns:
                nouid = True
                cursor.execute(
                    "INSERT INTO organisms (full_name, short_name, risk_group) "
                    "SELECT full_name, short_name, RG "
                    "FROM other.Organisms WHERE other.Organisms.short_name = ?",
                    (organism_name,),
                )
            else:
                cursor.execute(
                    "INSERT INTO organisms (full_name, short_name, risk_group, uid) "
                    "SELECT full_name, short_name, RG, uid "
                    "FROM other.Organisms WHERE other.Organisms.short_name = ?",
                    (organism_name,),
                )
        conn.commit()

        return {
            "imported_count": len(imported_plasmid_ids),
            "missing_features": missing_features,
            "missing_organisms": missing_organisms,
            "nouid": nouid,
        }
    finally:
        conn.close()
