"""Validation and maintenance checks for glossary and plasmid completeness."""

import re
import sqlite3

import numpy as np
import pandas as pd


def check_plasmids(db_path: str) -> dict:
    """Check for duplicate names, missing backbones, cassettes, and GMOs."""
    conn = sqlite3.connect(db_path)
    try:
        plasmids = pd.read_sql_query("SELECT name, id FROM plasmids", conn)
        names = list(plasmids["name"])
        ids = list(plasmids["id"])

        seen = set()
        duplicates = [name for name in names if name in seen or seen.add(name)]

        no_backbone = pd.read_sql_query(
            "SELECT name FROM plasmids WHERE backbone_vector = ''",
            conn,
        )["name"].tolist()

        cassette_pids = set(
            pd.read_sql_query("SELECT plasmid_id FROM cassettes", conn)["plasmid_id"]
        )
        no_cassettes = [
            plasmids[plasmids["id"] == plasmid_id]["name"].values[0]
            for plasmid_id in ids
            if plasmid_id not in cassette_pids
        ]

        gmo_pids = set(pd.read_sql_query("SELECT plasmid_id FROM gmos", conn)["plasmid_id"])
        no_gmos = [
            plasmids[plasmids["id"] == plasmid_id]["name"].values[0]
            for plasmid_id in ids
            if plasmid_id not in gmo_pids
        ]

        return {
            "duplicates": duplicates,
            "no_backbone": no_backbone,
            "no_cassettes": no_cassettes,
            "no_gmos": no_gmos,
        }
    finally:
        conn.close()


def check_features(db_path: str) -> dict:
    """Check feature glossary completeness."""
    conn = sqlite3.connect(db_path)
    try:
        glossary = pd.read_sql_query("SELECT * FROM features", conn)
        has_empty = glossary.isnull().any().any() or (glossary.eq("")).any().any()

        annotation_list = list(glossary["annotation"])
        seen = set()
        duplicates = [name for name in annotation_list if name in seen or seen.add(name)]

        cassettes_data = pd.read_sql_query("SELECT content, plasmid_id FROM cassettes", conn)
        plasmid_ids = list(cassettes_data["plasmid_id"])
        used_cassettes = list(cassettes_data["content"])
        used_cassettes = [re.sub(r"\[.*?\]", "", cassette) for cassette in used_cassettes]

        total_used: list[str] = []
        missing: list[str] = []
        for index, cassette_str in enumerate(used_cassettes):
            features = cassette_str.split("-")
            total_used += features
            diff = np.setdiff1d(features, annotation_list)
            plasmid_row = pd.read_sql_query(
                "SELECT name FROM plasmids WHERE id = ?",
                conn,
                params=(plasmid_ids[index],),
            )
            if plasmid_row.empty:
                continue
            plasmid_name = plasmid_row["name"].iloc[0]
            for element in diff:
                missing.append(f"{plasmid_name}: {element}")

        redundant = [str(x) for x in np.setdiff1d(annotation_list, total_used)]

        return {
            "complete": len(missing) == 0,
            "missing": missing,
            "redundant": redundant,
            "duplicates": duplicates,
            "has_empty_fields": bool(has_empty),
        }
    finally:
        conn.close()


def check_organisms(db_path: str) -> dict:
    """Check organism glossary completeness."""
    conn = sqlite3.connect(db_path)
    try:
        feature_orgs = pd.read_sql_query("SELECT annotation, organism FROM features", conn)
        gmo_orgs = pd.read_sql_query("SELECT organism_name FROM gmos", conn)
        used = list(feature_orgs["organism"]) + list(gmo_orgs["organism_name"])

        glossary = pd.read_sql_query("SELECT short_name FROM organisms", conn)
        glossary_list = list(glossary["short_name"])

        seen = set()
        duplicates = [name for name in glossary_list if name in seen or seen.add(name)]

        missing_orgs = np.setdiff1d(used, glossary_list)
        missing_pairs = []
        for _, row in feature_orgs.iterrows():
            if row["organism"] in missing_orgs:
                missing_pairs.append(f"{row['annotation']}: {row['organism']}")

        redundant = [str(x) for x in np.setdiff1d(glossary_list, used)]

        return {
            "complete": len(missing_orgs) == 0,
            "missing_pairs": missing_pairs,
            "redundant": redundant,
            "duplicates": duplicates,
        }
    finally:
        conn.close()
