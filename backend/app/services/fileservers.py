"""Filebrowser and Google Drive upload services."""

import asyncio
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
try:
    from filebrowser_client import FilebrowserClient
except ImportError:
    FilebrowserClient = None
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

from ..application.attachments import read_attachment


def prepare_local_files(
    db_path: str,
    user_data: str,
    settings: dict,
    plasmid_name: Optional[str] = None,
) -> str:
    """Export plasmid data to local folders for upload. Returns the base path."""
    initials = settings["initials"]
    user_name = settings["user_name"]
    email = settings["email"]

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

    if plasmid_name:
        path = os.sep.join([user_data, initials, plasmid_name])
    else:
        path = os.sep.join([user_data, initials])
    if os.path.isdir(path):
        shutil.rmtree(path)
    Path(path).mkdir(parents=True, exist_ok=True)

    for _, plasmid in local_plasmids.iterrows():
        if plasmid['name'] == 'p' + initials + '000' or '(Copy)' in plasmid['name']:
            continue

        if plasmid_name:
            subfolder = path
        else:
            subfolder = os.sep.join([path, plasmid['name']])
        Path(subfolder).mkdir(parents=True, exist_ok=True)

        data = "\n".join([
            'Plasmid name: ' + str(plasmid['name']),
            'Clone: ' + str(plasmid['clone']),
            'Alias: ' + str(plasmid['alias']),
            'Status: ' + status_values['name'][plasmid['status_id'] - 1],
            'Short description: ' + str(plasmid['purpose']),
            'Cloning: ' + str(plasmid['summary']),
            'Backbone: ' + str(plasmid['backbone_vector']),
            'Creator: ' + user_name,
            'Creator email: ' + email,
            'Entry date: ' + str(plasmid['recorded_on']),
        ])

        my_cassettes = cassettes[
            cassettes['plasmid_id'] == plasmid['id']
        ]['content']
        for cidx, cassette in enumerate(my_cassettes):
            data += f"\nCassette {cidx + 1}: {cassette}"

        with open(os.sep.join([subfolder, plasmid['name'] + ".txt"]), "w") as f:
            f.write(data)

        if plasmid['genbank_content'] not in ('', None):
            with open(os.sep.join([subfolder, plasmid['name'] + ".gb"]), "w") as f:
                f.write(plasmid['genbank_content'])

        att_ids = pd.read_sql_query(
            'SELECT id AS attach_id, filename AS Filename FROM attachments WHERE plasmid_id = ?',
            conn, params=(plasmid['id'],)
        )
        for _, row in att_ids.iterrows():
            read_attachment(db_path, row['attach_id'], row['Filename'], subfolder)

    conn.close()
    return path


def upload_filebrowser(
    path: str,
    settings: dict,
    plasmid_name: Optional[str] = None,
) -> None:
    """Upload prepared files to a Filebrowser server."""
    initials = settings["initials"]
    client = FilebrowserClient(
        settings["filebrowser_instance"],
        settings["filebrowser_user"],
        settings["filebrowser_pwd"],
    )
    asyncio.run(client.connect())

    delete_path = os.sep.join([initials, plasmid_name]) if plasmid_name else initials
    try:
        asyncio.run(client.delete(delete_path))
    except Exception:
        pass

    asyncio.run(client.upload(path, initials, override=True))


def upload_gdrive(
    path: str,
    user_data: str,
    settings: dict,
    gdrive_folder_id: str,
    credits_path: str,
    plasmid_name: Optional[str] = None,
    zip_files: bool = True,
    progress_callback=None,
) -> None:
    """Upload prepared files to Google Drive."""
    initials = settings["initials"]

    gauth = GoogleAuth()
    scope = ["https://www.googleapis.com/auth/drive"]
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        credits_path, scope
    )
    drive = GoogleDrive(gauth)

    folderlist = drive.ListFile({
        'q': f"'{gdrive_folder_id}' in parents and "
             "mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()

    initials_folder_id = None
    if folderlist:
        for folder in folderlist:
            if folder['title'] == initials:
                initials_folder_id = folder['id']
                if not plasmid_name:
                    drive.CreateFile({'id': folder['id']}).Delete()

    if not plasmid_name:
        new_folder = drive.CreateFile({
            'title': initials,
            'parents': [{'id': gdrive_folder_id}],
            'mimeType': 'application/vnd.google-apps.folder',
        })
        new_folder.Upload()
        initials_folder_id = new_folder['id']

    if not plasmid_name:
        dir_list = sorted(os.listdir(os.sep.join([user_data, initials])))
    else:
        dir_list = [plasmid_name]

    # delete existing plasmid folder/zip if updating single
    if plasmid_name:
        items = drive.ListFile({
            'q': f"'{initials_folder_id}' in parents and trashed=false"
        }).GetList()
        for item in items:
            if os.path.splitext(item['title'])[0] == plasmid_name:
                drive.CreateFile({'id': item['id']}).Delete()

    for count, file in enumerate(dir_list):
        if progress_callback:
            progress_callback(file, count + 1, len(dir_list))

        if zip_files:
            zip_path = shutil.make_archive(
                os.sep.join([user_data, initials, file]),
                'zip',
                os.sep.join([user_data, initials, file]),
            )
            gfile = drive.CreateFile({'parents': [{'id': initials_folder_id}]})
            gfile.SetContentFile(zip_path)
            gfile.Upload()
        else:
            subfolder = drive.CreateFile({
                'title': file,
                'parents': [{'id': initials_folder_id}],
                'mimeType': 'application/vnd.google-apps.folder',
            })
            subfolder.Upload()
            subfolder_id = subfolder['id']
            for root, _, fnames in os.walk(
                os.sep.join([user_data, initials, file])
            ):
                for item in fnames:
                    gfile = drive.CreateFile({
                        'parents': [{'id': subfolder_id}]
                    })
                    gfile.SetContentFile(os.sep.join([root, item]))
                    gfile.Upload()
