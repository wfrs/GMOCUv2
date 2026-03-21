"""Report and export application services."""

import re
import sqlite3

import pandas as pd


def _parse_cassette_features(content: str) -> list[str]:
    cleaned = re.sub(r"\[.*?\]", "", content)
    return [feature for feature in cleaned.split("-") if feature]


def generate_formblatt(db_path: str, lang: str = "de") -> pd.DataFrame:
    """Generate Formblatt-Z data as a DataFrame."""
    columns = [
        "Nr.", "Spender Bezeichnung", "Spender RG",
        "Empfänger Bezeichnung", "Empfänger RG",
        "Ausgangsvektor Bezeichnung",
        "Übertragene Nukleinsäure Bezeichnung",
        "Übertragene Nukleinsäure Gefährdungspotential",
        "GVO Bezeichnung", "GVO RG", "GVO Zulassung",
        "GVO erzeugt/erhalten am", "GVO entsorgt am",
        "Datum des Eintrags",
    ]
    formblatt = pd.DataFrame(columns=columns)

    conn = sqlite3.connect(db_path)
    try:
        gmo_data = pd.read_sql_query("SELECT * FROM gmos", conn)

        for idx, gmo in gmo_data.iterrows():
            plasmid_id = gmo["plasmid_id"]
            cassettes = pd.read_sql_query(
                "SELECT content FROM cassettes WHERE plasmid_id = ?",
                conn,
                params=(plasmid_id,),
            )

            used_features = cassettes["content"].tolist()
            used_features = [re.sub(r"\[.*?\]", "", feature) for feature in used_features]
            used_features = "-".join(used_features).split("-")

            cursor = conn.cursor()
            feature_organisms = []
            feature_risk = []
            for feature in used_features:
                cursor.execute(
                    "SELECT organism FROM features WHERE annotation = ?",
                    (feature,),
                )
                feature_organisms.append(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT risk FROM features WHERE annotation = ?",
                    (feature,),
                )
                risk = cursor.fetchone()[0]
                feature_risk.append(risk if risk else "None")

            source_rg = []
            for organism in feature_organisms:
                cursor.execute(
                    "SELECT risk_group FROM organisms WHERE short_name = ?",
                    (organism,),
                )
                source_rg.append(cursor.fetchone()[0])

            cursor.execute(
                "SELECT risk_group FROM organisms WHERE short_name = ?",
                (gmo["organism_name"],),
            )
            recipient_rg = cursor.fetchone()[0]

            cursor.execute(
                "SELECT full_name FROM organisms WHERE short_name = ?",
                (gmo["organism_name"],),
            )
            recipient_full = cursor.fetchone()[0]

            plasmid_frame = pd.read_sql_query(
                "SELECT name, backbone_vector FROM plasmids WHERE id = ?",
                conn,
                params=(plasmid_id,),
            )
            plasmid_name = plasmid_frame["name"][0]
            original_plasmid = plasmid_frame["backbone_vector"][0]

            row = {
                "Nr.": str(idx + 1),
                "Spender Bezeichnung": "|".join(feature_organisms),
                "Spender RG": "|".join(source_rg),
                "Empfänger Bezeichnung": recipient_full,
                "Empfänger RG": recipient_rg,
                "Ausgangsvektor Bezeichnung": original_plasmid,
                "Übertragene Nukleinsäure Bezeichnung": "|".join(used_features),
                "Übertragene Nukleinsäure Gefährdungspotential": "|".join(feature_risk),
                "GVO Bezeichnung": f"{gmo['organism_name']}-{plasmid_name}",
                "GVO RG": gmo["target_risk_group"],
                "GVO Zulassung": gmo["approval"],
                "GVO erzeugt/erhalten am": gmo["created_on"],
                "GVO entsorgt am": gmo["destroyed_on"],
                "Datum des Eintrags": gmo["created_on"],
            }
            formblatt = pd.concat(
                [formblatt, pd.DataFrame.from_records([row])],
                ignore_index=True,
            )
    finally:
        conn.close()

    if lang == "en":
        formblatt.columns = [
            "No", "Donor designation", "Donor RG",
            "Recipient designation", "Recipient RG",
            "Source vector designation",
            "Transferred nucleic acid designation",
            "Transferred nucleic acid risk potential",
            "GMO name", "GMO RG", "GMO approval",
            "GMO generated", "GMO disposal", "Entry date",
        ]
    else:
        formblatt.columns = [
            "Nr.", "Spender Bezeichnung", "Spender RG",
            "Empfänger Bezeichnung", "Empfänger RG",
            "Ausgangsvektor Bezeichnung",
            "Übertragene Nukleinsäure Bezeichnung",
            "Übertragene Nukleinsäure Gefährdungspotential",
            "GVO Bezeichnung", "GVO RG", "GVO Zulassung",
            "GVO erzeugt/erhalten am", "GVO entsorgt am",
            "Datum des Eintrags",
        ]

    return formblatt


def generate_plasmid_list(db_path: str) -> pd.DataFrame:
    """Generate a plasmid list as a DataFrame."""
    conn = sqlite3.connect(db_path)
    try:
        plasmid_data = pd.read_sql_query("SELECT * FROM plasmids", conn)
        status_values = pd.read_sql_query("SELECT * FROM plasmid_statuses", conn)
    finally:
        conn.close()

    rows = []
    for idx, plasmid in plasmid_data.iterrows():
        rows.append(
            {
                "No.": idx + 1,
                "Plasmid name": plasmid["name"],
                "Alias": plasmid["alias"],
                "Clone": plasmid["clone"],
                "Original vector": plasmid["backbone_vector"],
                "Purpose": plasmid["purpose"],
                "Cloning summary": plasmid["summary"],
                "Status": status_values["name"][plasmid["status_id"] - 1],
                "Entry date": plasmid["recorded_on"],
            }
        )

    return pd.DataFrame(rows)


def export_all_features(db_path: str, output_path: str) -> None:
    """Export all features to Excel."""
    conn = sqlite3.connect(db_path)
    try:
        pd.read_sql_query("SELECT * FROM features", conn).to_excel(
            output_path,
            index=False,
            engine="xlsxwriter",
        )
    finally:
        conn.close()


def export_all_organisms(db_path: str, output_path: str) -> None:
    """Export all organisms to Excel."""
    conn = sqlite3.connect(db_path)
    try:
        pd.read_sql_query("SELECT * FROM organisms", conn).to_excel(
            output_path,
            index=False,
            engine="xlsxwriter",
        )
    finally:
        conn.close()


def get_used_features_df(db_path: str) -> pd.DataFrame:
    """Return a DataFrame of features that are actually used in cassettes."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM cassettes")
        all_features: list[str] = []
        for (content,) in cursor.fetchall():
            all_features.extend(_parse_cassette_features(content))
        cursor.close()

        if len(all_features) < 2:
            raise ValueError("Need more than one element used in cassettes for export.")

        return pd.read_sql_query(
            "SELECT annotation, alias, risk, organism, uid "
            f"FROM features WHERE annotation IN {str(tuple(all_features))}",
            conn,
        )
    finally:
        conn.close()


def get_used_organisms_df(db_path: str) -> pd.DataFrame:
    """Return a DataFrame of organisms that are actually used."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM cassettes")
        feature_names: list[str] = []
        for (content,) in cursor.fetchall():
            feature_names.extend(_parse_cassette_features(content))

        cursor.execute("SELECT organism_name FROM gmos")
        gmo_orgs = [row[0] for row in cursor.fetchall()]

        if gmo_orgs:
            cursor.execute(
                "SELECT short_name FROM organisms WHERE full_name IN "
                f"{str(tuple(gmo_orgs))}"
            )
            org_shorts_from_gmos = [row[0] for row in cursor.fetchall()]
        else:
            org_shorts_from_gmos = []

        if feature_names:
            cursor.execute(
                "SELECT organism FROM features WHERE annotation IN "
                f"{str(tuple(feature_names))}"
            )
            org_shorts_from_features = [row[0] for row in cursor.fetchall()]
        else:
            org_shorts_from_features = []

        all_shorts = set(org_shorts_from_gmos + org_shorts_from_features)
        cursor.close()

        if len(all_shorts) < 2:
            raise ValueError("Need more than one element for the organism export.")

        return pd.read_sql_query(
            "SELECT full_name, short_name, risk_group AS RG, uid FROM organisms "
            f"WHERE short_name IN {str(tuple(all_shorts))}",
            conn,
        )
    finally:
        conn.close()
