"""JBEI/ICE integration service."""
from __future__ import annotations

import sqlite3
import os
from typing import Optional

import pandas as pd
try:
    import icebreaker
except ImportError:
    icebreaker = None


def upload_to_ice(
    db_path: str,
    settings: dict,
    plasmid_name: Optional[str] = None,
    only_new: bool = False,
) -> list[str]:
    """Upload/update plasmid entries on JBEI/ICE.

    Args:
        db_path: Path to the SQLite database.
        settings: Dict from database.read_settings().
        plasmid_name: If set, only upload this specific plasmid.
        only_new: If True, only upload newly created entries.

    Returns:
        List of newly added plasmid names.
    """
    if settings.get("use_ice") == 0 and not plasmid_name:
        return []

    configuration = {
        "root": settings["ice_instance"],
        "token": settings["ice_token"],
        "client": settings["ice_token_client"],
    }
    ice = icebreaker.IceClient(configuration)
    initials = settings["initials"]
    user_name = settings["user_name"]
    email = settings["email"]
    upload_completed = settings["upload_completed"]
    use_filebrowser = settings["use_filebrowser"]
    filebrowser_instance = settings["filebrowser_instance"]

    # get/create folder
    ice_folders = ice.get_collection_folders("PERSONAL")
    folderlist = [f['folderName'] for f in ice_folders]
    folder_ids = [f['id'] for f in ice_folders]

    folder_id = None
    for name, fid in zip(folderlist, folder_ids):
        if name == initials:
            folder_id = fid
    if initials not in folderlist:
        new_folder = ice.create_folder(initials)
        folder_id = new_folder['id']

    ice_plasmids = ice.get_folder_entries(folder_id)
    ice_plasmid_names = [p['name'] for p in ice_plasmids]

    conn = sqlite3.connect(db_path)
    if plasmid_name:
        local_plasmids = pd.read_sql_query(
            "SELECT * FROM plasmids WHERE name = (?)", conn,
            params=(plasmid_name,)
        )
    else:
        local_plasmids = pd.read_sql_query("SELECT * FROM plasmids", conn)
    status_values = pd.read_sql_query("SELECT * FROM plasmid_statuses", conn)
    cassettes = pd.read_sql_query("SELECT * FROM cassettes", conn)
    conn.close()

    newly_added = []

    for _, plasmid in local_plasmids.iterrows():
        if upload_completed == 1 and plasmid['status_id'] != 1:
            continue
        if plasmid['name'] == 'p' + initials + '000' or '(Copy)' in plasmid['name']:
            continue

        if plasmid['name'] not in ice_plasmid_names:
            new = ice.create_plasmid(name=plasmid['name'])
            newly_added.append(plasmid['name'])
            new_part_id = new['id']
            fetched = ice.get_part_infos(new_part_id)
            ice_plasmids.append(fetched)
            ice_plasmid_names.append(plasmid['name'])

        should_update = False
        if only_new and plasmid['name'] in newly_added:
            should_update = True
        elif not only_new:
            should_update = True
        if plasmid_name:
            should_update = True

        if plasmid['name'] in ice_plasmid_names and should_update:
            for ice_p in ice_plasmids:
                if plasmid['name'] == ice_p['name']:
                    d = {
                        "type": "PLASMID",
                        "alias": plasmid['alias'],
                        "status": status_values['name'][plasmid['status_id'] - 1],
                        "shortDescription": plasmid['purpose'],
                        "creator": user_name,
                        "creatorEmail": email,
                        "plasmidData": {
                            "backbone": plasmid['backbone_vector'],
                            "circular": "true",
                        },
                    }
                    ice.request("PUT", "parts/" + str(ice_p['id']), data=d)

                    ice.set_part_custom_field(ice_p['id'], 'Clone', plasmid['clone'])
                    ice.set_part_custom_field(ice_p['id'], 'Cloning', plasmid['summary'])
                    ice.set_part_custom_field(ice_p['id'], 'Entry date', plasmid['recorded_on'])

                    my_cassettes = cassettes[
                        cassettes['plasmid_id'] == plasmid['id']
                    ]['content']
                    for cidx, cassette in enumerate(my_cassettes):
                        ice.set_part_custom_field(
                            ice_p['id'], f'Cassette {cidx + 1}', cassette
                        )

                    if use_filebrowser == 1:
                        link = os.sep.join([
                            filebrowser_instance, initials, ice_p['name']
                        ])
                        ice.set_part_custom_field(
                            ice_p['id'], 'Filebrowser link', link
                        )

                    if plasmid['genbank_content'] not in ('', None):
                        try:
                            ice.delete_part_record(ice_p['id'])
                        except Exception:
                            pass
                        ice.attach_record_to_part(
                            ice_part_id=ice_p['id'],
                            filename=plasmid['name'] + '.gb',
                            record_text=plasmid['genbank_content'],
                        )

                    ice.add_to_folder(
                        [ice_p['id']], folders_ids=[folder_id]
                    )

    return newly_added
