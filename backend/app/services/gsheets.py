"""Google Sheets glossary synchronization service."""
from __future__ import annotations

import os
import sqlite3
from datetime import date
from dataclasses import dataclass, field

import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe

from ..application.legacy_mutations import update_cassettes, update_aliases


@dataclass
class SyncResult:
    """Result of a Google Sheets sync operation."""
    imported_features: list[str] = field(default_factory=list)
    imported_organisms: list[str] = field(default_factory=list)
    uploaded_features: list[str] = field(default_factory=list)
    uploaded_organisms: list[str] = field(default_factory=list)
    updated_features: list[str] = field(default_factory=list)
    updated_organisms: list[str] = field(default_factory=list)
    deleted_features: list[str] = field(default_factory=list)
    deleted_organisms: list[str] = field(default_factory=list)
    repeated_annotations: list[str] = field(default_factory=list)
    repeated_organisms: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def validate_sync_prerequisites(
    db_path: str, user_data: str, sheet_id: str
) -> str | None:
    """Check prerequisites for sync. Returns error message or None."""
    credits = os.sep.join([user_data, 'gmocu_gdrive_credits.json'])
    if not os.path.isfile(credits) or not sheet_id or sheet_id == 'ID from link':
        return (
            "Please setup the access to the Google Sheets online glossaries.\n\n"
            "Follow the instructions at https://github.com/beyerh/gmocu. "
            "Add the Sheet ID in the Settings and save the file "
            "'gmocu_gdrive_credits.json' to your GMOCU folder."
        )

    conn = sqlite3.connect(db_path)
    features = pd.read_sql_query("SELECT * FROM features", conn)
    organisms = pd.read_sql_query(
        "SELECT id, full_name, short_name, risk_group AS RG, uid, synced FROM organisms",
        conn,
    )
    conn.close()

    if features.isnull().any().any() or (features.eq("")).any().any():
        return (
            "Empty fields in the Nucleic acids features glossary detected. "
            "Please fill all fields first to sync complete data."
        )
    if organisms.isnull().any().any() or (organisms.eq("")).any().any():
        return (
            "Empty fields in the Organisms glossary detected. "
            "Please fill all fields first to sync complete data."
        )
    return None


def sync_gsheets(
    db_path: str,
    user_data: str,
    sheet_id: str,
    initials: str,
) -> SyncResult:
    """Perform bidirectional sync with Google Sheets glossary.

    Steps:
    1. Import new online entries into local DB
    2. Upload new local entries to online sheet
    3. Update local entries that changed online
    4. Delete local entries marked invalid online
    """
    result = SyncResult()
    credits = os.sep.join([user_data, 'gmocu_gdrive_credits.json'])

    try:
        gc = gspread.service_account(filename=credits)
        sheet = gc.open_by_key(sheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        result.errors.append(
            f"The spreadsheet with ID {sheet_id} could not be found."
        )
        return result

    # ensure worksheets exist
    try:
        features_sheet = sheet.worksheet("features")
    except gspread.exceptions.WorksheetNotFound:
        features_sheet = sheet.add_worksheet(title="features", rows=1000, cols=5)
        headers = pd.DataFrame(
            columns=['annotation', 'alias', 'risk', 'organism', 'uid', 'valid']
        )
        features_sheet.update([headers.columns.values.tolist()])

    try:
        organisms_sheet = sheet.worksheet("organisms")
    except gspread.exceptions.WorksheetNotFound:
        organisms_sheet = sheet.add_worksheet(title="organisms", rows=1000, cols=4)
        headers = pd.DataFrame(
            columns=['full_name', 'short_name', 'RG', 'uid', 'valid']
        )
        organisms_sheet.update([headers.columns.values.tolist()])

    try:
        logging_sheet = sheet.worksheet("logging")
    except gspread.exceptions.WorksheetNotFound:
        logging_sheet = sheet.add_worksheet(title="logging", rows=5000, cols=4)
        headers = pd.DataFrame(columns=['item', 'user', 'date', 'action'])
        logging_sheet.update([headers.columns.values.tolist()])

    # get online data
    online_features = get_as_dataframe(features_sheet).dropna(how='all')
    valid_online_features = online_features[online_features['valid'] == 1]
    online_organisms = get_as_dataframe(organisms_sheet).dropna(how='all')
    valid_online_organisms = online_organisms[online_organisms['valid'] == 1]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # --- Step 1: Import new online entries ---
    try:
        local_features = pd.read_sql_query('SELECT * FROM features', conn)
        local_organisms = pd.read_sql_query(
            'SELECT id, full_name, short_name, risk_group AS RG, uid, synced FROM organisms',
            conn,
        )

        new_online_f = online_features[
            ~online_features['uid'].isin(local_features['uid'])
        ].reset_index(drop=True)
        new_online_f = new_online_f[new_online_f['valid'] == 1]

        new_online_o = online_organisms[
            ~online_organisms['uid'].isin(local_organisms['uid'])
        ].reset_index(drop=True)
        new_online_o = new_online_o[new_online_o['valid'] == 1]

        for _, feat in new_online_f.iterrows():
            cursor.execute(
                "INSERT INTO features (annotation, alias, risk, organism, uid, synced) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (feat['annotation'], feat['alias'], feat['risk'],
                 feat['organism'], feat['uid'], 1)
            )
        conn.commit()
        result.imported_features = new_online_f['annotation'].tolist() if len(new_online_f) > 0 else []

        for _, org in new_online_o.iterrows():
            cursor.execute(
                "INSERT INTO organisms (full_name, short_name, risk_group, uid, synced) "
                "VALUES (?, ?, ?, ?, ?)",
                (org['full_name'], org['short_name'], str(org['RG']),
                 org['uid'], 1)
            )
        conn.commit()
        result.imported_organisms = new_online_o['short_name'].tolist() if len(new_online_o) > 0 else []

    except Exception as e:
        result.errors.append(str(e))

    # --- Step 2: Upload new local entries ---
    try:
        local_features = pd.read_sql_query('SELECT * FROM features', conn)
        local_organisms = pd.read_sql_query(
            'SELECT id, full_name, short_name, risk_group AS RG, uid, synced FROM organisms',
            conn,
        )

        # warn on repeated annotations
        repeated_f = list(local_features[
            local_features['annotation'].isin(online_features['annotation'])
            & (local_features['synced'] == 0)
        ]['annotation'])
        result.repeated_annotations = repeated_f

        repeated_o = list(local_organisms[
            local_organisms['short_name'].isin(online_organisms['short_name'])
            & (local_organisms['synced'] == 0)
        ]['short_name'])
        result.repeated_organisms = repeated_o

        new_local_f = local_features[
            ~(local_features['uid'].isin(online_features['uid'])
              | local_features['annotation'].isin(online_features['annotation']))
        ].reset_index(drop=True).drop('id', axis=1)

        new_local_o = local_organisms[
            ~(local_organisms['uid'].isin(online_organisms['uid'])
              | local_organisms['short_name'].isin(online_organisms['short_name']))
        ].reset_index(drop=True).drop('id', axis=1)

        new_local_f.loc[:, 'synced'] = 1
        new_local_o.loc[:, 'synced'] = 1

        features_sheet.append_rows(new_local_f.values.tolist())
        organisms_sheet.append_rows(new_local_o.values.tolist())

        # log
        log_rows = []
        today_str = date.today().strftime('%Y-%m-%d')
        for name in new_local_f['annotation'].tolist():
            log_rows.append([name, initials, today_str, 'added'])
        for name in new_local_o['short_name'].tolist():
            log_rows.append([name, initials, today_str, 'added'])
        if log_rows:
            logging_sheet.append_rows(log_rows)

        # mark synced locally
        for _, feat in new_local_f.iterrows():
            cursor.execute(
                'UPDATE features SET synced=? WHERE uid=?', (1, feat['uid'])
            )
        conn.commit()
        for _, org in new_local_o.iterrows():
            cursor.execute(
                'UPDATE organisms SET synced=? WHERE uid=?', (1, org['uid'])
            )
        conn.commit()

        result.uploaded_features = new_local_f['annotation'].tolist() if len(new_local_f) > 0 else []
        result.uploaded_organisms = new_local_o['short_name'].tolist() if len(new_local_o) > 0 else []

    except Exception as e:
        result.errors.append(str(e))

    # --- Step 3: Update modified entries ---
    try:
        local_features = pd.read_sql_query('SELECT * FROM features', conn)
        local_organisms = pd.read_sql_query(
            'SELECT id, full_name, short_name, risk_group AS RG, uid, synced FROM organisms',
            conn,
        )

        local_f_cmp = local_features.drop(
            columns=['id', 'synced'], axis=1
        ).sort_values(by=['uid'], ignore_index=True)
        online_f_cmp = valid_online_features.drop(
            'valid', axis=1
        ).sort_values(by=['uid'], ignore_index=True)

        local_o_cmp = local_organisms.drop(
            columns=['id', 'synced'], axis=1
        ).sort_values(by=['uid'], ignore_index=True)
        online_o_cmp = valid_online_organisms.drop(
            'valid', axis=1
        ).sort_values(by=['uid'], ignore_index=True)
        online_o_cmp[['RG']] = online_o_cmp[['RG']].astype(str)

        # features
        if not online_f_cmp.equals(local_f_cmp):
            online_f_cmp_idx = online_f_cmp.set_index(list(online_f_cmp.columns))
            local_f_cmp_idx = local_f_cmp.set_index(list(local_f_cmp.columns))
            modified_f = online_f_cmp_idx[
                ~online_f_cmp_idx.index.isin(local_f_cmp_idx.index)
            ].reset_index()

            for _, row in modified_f.iterrows():
                result.updated_features.append(row['annotation'])
                cursor.execute(
                    'UPDATE features SET annotation=?, alias=?, risk=?, organism=? '
                    'WHERE uid=?',
                    (row['annotation'], row['alias'], row['risk'],
                     row['organism'], row['uid'])
                )
            conn.commit()

            # propagate renames to cassettes/aliases
            prev = local_features[
                local_features['uid'].isin(modified_f['uid'])
            ]
            rename_dict = dict(zip(prev['annotation'], modified_f['annotation']))
            update_cassettes(db_path, rename_dict)
            update_aliases(db_path, rename_dict)

        # organisms
        if not online_o_cmp.equals(local_o_cmp):
            online_o_cmp_idx = online_o_cmp.set_index(list(online_o_cmp.columns))
            local_o_cmp_idx = local_o_cmp.set_index(list(local_o_cmp.columns))
            modified_o = online_o_cmp_idx[
                ~online_o_cmp_idx.index.isin(local_o_cmp_idx.index)
            ].reset_index()
            modified_o[['RG']] = modified_o[['RG']].astype(str)

            for _, row in modified_o.iterrows():
                result.updated_organisms.append(row['short_name'])
                cursor.execute(
                    'UPDATE organisms SET full_name=?, short_name=?, risk_group=? '
                    'WHERE uid=?',
                    (row['full_name'], row['short_name'], row['RG'], row['uid'])
                )
            conn.commit()

    except Exception as e:
        result.errors.append(str(e))

    # --- Step 4: Delete invalid entries ---
    try:
        local_features = pd.read_sql_query('SELECT * FROM features', conn)
        local_organisms = pd.read_sql_query(
            'SELECT id, full_name, short_name, risk_group AS RG, uid, synced FROM organisms',
            conn,
        )

        invalid_online_f = online_features[
            online_features['valid'] != 1
        ].drop('valid', axis=1).sort_values(by=['uid'], ignore_index=True)

        local_f_all = local_features.drop(
            columns=['id', 'synced'], axis=1
        ).sort_values(by=['uid'], ignore_index=True)

        invalid_local_f = []
        for _, row in local_f_all.iterrows():
            if row['uid'] in invalid_online_f.uid.values:
                invalid_local_f.append(row)
        result.deleted_features = [r['annotation'] for r in invalid_local_f]

        invalid_online_o = online_organisms[
            online_organisms['valid'] != 1
        ].drop('valid', axis=1).sort_values(by=['uid'], ignore_index=True)

        local_o_all = local_organisms.drop(
            columns=['id', 'synced'], axis=1
        ).sort_values(by=['uid'], ignore_index=True)

        invalid_local_o = []
        for _, row in local_o_all.iterrows():
            if row['uid'] in invalid_online_o.uid.values:
                invalid_local_o.append(row)
        result.deleted_organisms = [r['short_name'] for r in invalid_local_o]

    except Exception as e:
        result.errors.append(str(e))
    finally:
        conn.close()

    return result


def apply_deletions(
    db_path: str, feature_uids: list[str], organism_uids: list[str]
) -> None:
    """Delete features/organisms by UID (after user confirmation)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for uid in feature_uids:
        cursor.execute("DELETE FROM features WHERE uid=?", (uid,))
    for uid in organism_uids:
        cursor.execute("DELETE FROM organisms WHERE uid=?", (uid,))
    conn.commit()
    conn.close()
