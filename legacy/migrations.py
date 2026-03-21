"""Database schema migrations for GMOCU version updates."""

import os
import sys
import sqlite3

import PySimpleGUI as sg
from datetime import date


def run_migrations(database, db, win, version_no, user_data):
    """Run database schema migrations if needed.

    Args:
        database: Path to the SQLite database file.
        db: PySimpleSQL Database instance.
        win: PySimpleGUI Window instance.
        version_no: Current application version number.
        user_data: Path to user data directory.
    """
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    database_was_changed = False
    try:
        db_saved_version = db['Settings']['version']
    except:
        db_saved_version = 0
    try:
        if db_saved_version < 0.5:
            settings_columns = [i[1] for i in cursor.execute('PRAGMA table_info(Settings)')]
            if not "version" in settings_columns:
                cursor.execute("ALTER TABLE Settings ADD COLUMN version FLOAT DEFAULT 0;")
                database_was_changed = True
            if not "horizontal_layout" in settings_columns:
                cursor.execute("ALTER TABLE Settings ADD COLUMN horizontal_layout INTEGER DEFAULT 0;")
                database_was_changed = True
                if sys.platform == "win32":
                    win['Settings.horizontal_layout'].update(1)
                    db['Settings'].save_record(display_message=False)
                    cursor.execute("UPDATE Settings SET horizontal_layout = 1;")

        if db_saved_version < 0.6:
            credentials_columns = [i[1] for i in cursor.execute('PRAGMA table_info(IceCredentials)')]
            if not "filebrowser_instance" in credentials_columns:
                add_columns = ['filebrowser_instance', 'filebrowser_user', 'filebrowser_pwd']
                for i in add_columns:
                    cursor.execute("ALTER TABLE IceCredentials ADD COLUMN {} TEXT;".format(i))
                database_was_changed = True
            settings_columns = [i[1] for i in cursor.execute('PRAGMA table_info(Settings)')]
            if not "use_ice" in settings_columns:
                cursor.execute("ALTER TABLE Settings ADD COLUMN use_ice INTEGER DEFAULT 1;")
                database_was_changed = True
            if not "use_filebrowser" in settings_columns:
                cursor.execute("ALTER TABLE Settings ADD COLUMN use_filebrowser INTEGER DEFAULT 1;")
                database_was_changed = True

        if db_saved_version < 0.7:
            features_columns = [i[1] for i in cursor.execute('PRAGMA table_info(Features)')]
            organisms_columns = [i[1] for i in cursor.execute('PRAGMA table_info(Organisms)')]
            settings_columns = [i[1] for i in cursor.execute('PRAGMA table_info(Settings)')]
            if not "uid" in features_columns or not "uid" in organisms_columns:
                # make a backup
                name = 'gmocu_backup_{}.db'.format(str(date.today().strftime("%Y-%m-%d")))
                path = os.sep.join([user_data, name])

                def progress(status, remaining, total):
                    print(f'Copied {total-remaining} of {total} pages...')

                dst = sqlite3.connect(path)
                with dst:
                    connection.backup(dst, pages=1, progress=progress)
                dst.close()
            if not "uid" in features_columns:
                cursor.execute("CREATE TABLE Features_new(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, annotation TEXT, alias TEXT, risk TEXT DEFAULT 'No Risk', organism TEXT, uid CHAR(16) NOT NULL DEFAULT (lower(hex(randomblob(16)))));")
                decision = sg.popup_yes_no('The table with the Nucleic acid features is being modified to work with Google Sheets. It is recommended to import them fresh from the shared glossary. Do you still want to keep your entries and assign them uniqe IDs (you will find a backup in the GMOCU folder in any case)?')
                if decision == 'Yes':
                    cursor.execute("INSERT INTO Features_new(id, annotation, alias, risk, organism) SELECT id, annotation, alias, risk, organism FROM Features;")
                cursor.execute("DROP TABLE Features;")
                cursor.execute("ALTER TABLE Features_new RENAME TO Features;")
                database_was_changed = True
            if not "synced" in features_columns:
                cursor.execute("ALTER TABLE Features ADD COLUMN synced INTEGER DEFAULT 0;")
                database_was_changed = True
            if not "uid" in organisms_columns:
                cursor.execute("CREATE TABLE Organisms_new(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, full_name TEXT, short_name TEXT, RG TEXT, uid CHAR(16) NOT NULL DEFAULT (lower(hex(randomblob(16)))));")
                decision = sg.popup_yes_no('The table with the Organisms definitions is being modified to work with Google Sheets. It is recommended to import them fresh from the shared glossary. Do you still want to keep your entries and assign them uniqe IDs (you will find a backup in the GMOCU folder in any case)?')
                if decision == 'Yes':
                    cursor.execute("INSERT INTO Organisms_new(id, full_name, short_name, RG) SELECT id, full_name, short_name, RG FROM Organisms;")
                cursor.execute("DROP TABLE Organisms;")
                cursor.execute("ALTER TABLE Organisms_new RENAME TO Organisms;")
                database_was_changed = True
            if not "synced" in organisms_columns:
                cursor.execute("ALTER TABLE Organisms ADD COLUMN synced INTEGER DEFAULT 0;")
                database_was_changed = True
            if not "use_gdrive" in settings_columns:
                cursor.execute("ALTER TABLE Settings ADD COLUMN use_gdrive INTEGER DEFAULT 0;")
                database_was_changed = True
            if not "gdrive_id" in settings_columns:
                cursor.execute("ALTER TABLE Settings ADD COLUMN gdrive_id TEXT DEFAULT 'ID from link';")
                database_was_changed = True
            if not "zip_files" in settings_columns:
                cursor.execute("ALTER TABLE Settings ADD COLUMN zip_files INTEGER DEFAULT 1;")
                database_was_changed = True
            if not "autosync" in settings_columns:
                cursor.execute("ALTER TABLE Settings ADD COLUMN autosync INTEGER DEFAULT 0;")
                database_was_changed = True

        if database_was_changed:
            sg.popup('The database file structure has been updated. Please restart GMOCU.')

        # write current version to db file
        if db_saved_version < version_no:
            if db_saved_version < 0.5:
                cursor.execute("UPDATE Settings SET version = {};".format(version_no))
            else:
                win['Settings.version'].update(version_no)
                db['Settings'].save_record(display_message=False)

    except Exception as e:
        sg.popup(e)
        pass
    finally:
        cursor.close()
        connection.commit()
        connection.close()
