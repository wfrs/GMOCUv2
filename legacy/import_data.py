"""Data import functionality for GMOCU."""

import os
import re
import sqlite3

import PySimpleGUI as sg
import pandas as pd
import numpy as np
from datetime import date


def import_data(database, user_data):
    """Import plasmids from another GMOCU database file."""
    file = sg.popup_get_file("Select file")
    if not file:
        return
    connection = sqlite3.connect(database, timeout=60)
    cursor = connection.cursor()
    existing_plasmids = pd.read_sql_query("SELECT name, id FROM Plasmids", connection)
    existing_plasmid_names = existing_plasmids['name'].tolist()

    try:
        if file == '' or file == None:
            raise ValueError('No file selected.')
        cursor.execute("ATTACH DATABASE ? AS other", (file,))
        imp_plasmids = pd.read_sql_query("SELECT * FROM other.Plasmids", connection)
        imp_plasmids_names = imp_plasmids['name'].tolist()

        plasmids_to_import = np.setdiff1d(imp_plasmids_names, existing_plasmid_names)
        plasmids_to_import_copy = plasmids_to_import

        selected_plasmids = []
        plasmids_to_import = plasmids_to_import.tolist()
        layout = [[sg.Text("The following plasmids do not yet exist and can be imported:")],
                        [sg.Listbox(values=plasmids_to_import, size=(30,6), enable_events=True, key="-LIST-"), sg.Button("Add", enable_events=True, key="-BUTTON-"), sg.Button("Remove", enable_events=True, key="-BUTTON2-"), sg.Listbox(values=selected_plasmids, size=(30,6), key="-LIST2-")],
                        [sg.Button("Import selected", enable_events=True, key="-BUTTON3-")]+ [sg.Button("Import all", enable_events=True, key="-BUTTON4-")],
                        ]

        selwin = sg.Window("Import selection", layout=layout)

        while True:
            event, values = selwin.read()
            try:
                if event == sg.WIN_CLOSED:
                    selected_plasmids = []
                    break

                if event == "-BUTTON-":
                    INDEX = int(''.join(map(str, selwin["-LIST-"].get_indexes())))
                    selected_plasmids.append(plasmids_to_import.pop(INDEX))
                    selwin["-LIST2-"].update(selected_plasmids)
                    selwin["-LIST-"].update(plasmids_to_import)

                if event == "-BUTTON2-":
                    INDEX = int(''.join(map(str, selwin["-LIST2-"].get_indexes())))
                    plasmids_to_import.append(selected_plasmids.pop(INDEX))
                    selwin["-LIST2-"].update(selected_plasmids)
                    selwin["-LIST-"].update(plasmids_to_import)

                if event == "-BUTTON3-":
                    break

                if event == "-BUTTON4-":
                    selected_plasmids = plasmids_to_import_copy
                    break
            except:
                pass

        selwin.close()

    except Exception as e:
        sg.popup(e)

    try:
        if len(selected_plasmids) > 0:
            name = 'gmocu_backup_{}.db'.format(str(date.today().strftime("%Y-%m-%d")))
            backup = sg.popup_yes_no('Shall we make a backup of the current database in the Download folder as {}'.format(name))
            if backup == 'Yes':
                path = os.sep.join([user_data, name])

                def progress(status, remaining, total):
                    print(f'Copied {total-remaining} of {total} pages...')

                src = sqlite3.connect(database)
                dst = sqlite3.connect(path)
                with dst:
                    src.backup(dst, pages=1, progress=progress)
                dst.close()
                src.close()

        added_cassette_ids = []
        imported_plasmid_ids = []

        for idx, plasmid in imp_plasmids.iterrows():
            if plasmid['name'] not in existing_plasmid_names and plasmid['name'] in selected_plasmids:
                print('Importing plasmid ', plasmid['name'])
                imported_plasmid_ids.append(plasmid['id'])
                cursor.execute("INSERT INTO Plasmids (name, alias, status, purpose, gb, summary, genebank, gb_name, FKattachment, clone, backbone_vector, marker, organism_selector, target_RG, generated, destroyed, date) SELECT name, alias, status, purpose, gb, summary, genebank, gb_name, FKattachment, clone, backbone_vector, marker, organism_selector, target_RG, generated, destroyed, date FROM other.Plasmids WHERE other.Plasmids.id = ?", (plasmid['id'],))
                cursor.execute("SELECT MAX(id) FROM Plasmids")
                max_plasmid_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO Cassettes (content) SELECT content FROM other.Cassettes WHERE other.Cassettes.plasmid_id = ?", (plasmid['id'],))
                cursor.execute("SELECT cassette_id FROM Cassettes WHERE plasmid_id IS NULL")
                cassette_ids = cursor.fetchall()
                for i in cassette_ids:
                    cursor.execute("UPDATE Cassettes SET plasmid_id = ? WHERE cassette_id = ?", (max_plasmid_id, i[0]))
                    added_cassette_ids.append(i[0])

                cursor.execute("INSERT INTO GMOs (GMO_summary, organism_name, approval, target_RG, date_generated, date_destroyed, entry_date) SELECT GMO_summary, organism_name, approval, target_RG, date_generated, date_destroyed, entry_date FROM other.GMOs WHERE other.GMOs.plasmid_id = ?", (plasmid['id'],))
                cursor.execute("SELECT organism_id FROM GMOs WHERE plasmid_id IS NULL")
                organism_ids = cursor.fetchall()
                for i in organism_ids:
                    cursor.execute("UPDATE GMOs SET plasmid_id = ? WHERE organism_id = ?", (max_plasmid_id, i[0]))

                cursor.execute("INSERT INTO Attachments (file, Filename) SELECT file, Filename FROM other.Attachments WHERE other.Attachments.plasmid_id = ?", (plasmid['id'],))
                cursor.execute("SELECT attach_id FROM Attachments WHERE plasmid_id IS NULL")
                attach_ids = cursor.fetchall()
                for i in attach_ids:
                    cursor.execute("UPDATE Attachments SET plasmid_id = ? WHERE attach_id = ?", (max_plasmid_id, i[0]))

        connection.commit()

        unique_imported_features = set()
        cassettes = pd.read_sql_query("SELECT * FROM Cassettes", connection)
        for idx, added_cassette in cassettes.iterrows():
            if added_cassette['cassette_id'] in added_cassette_ids:
                added_cassette_elements = added_cassette['content']
                added_cassette_elements = re.sub('[\[].*?[\]]', '', added_cassette_elements)
                added_cassette_elements = added_cassette_elements.split('-')
                for i in added_cassette_elements:
                    unique_imported_features.add(i)

        unique_imported_features = list(unique_imported_features)
        features = pd.read_sql_query("SELECT annotation FROM Features", connection)
        features_list = features['annotation'].tolist()
        features_columns = [i[1] for i in cursor.execute('PRAGMA other.table_info(Features)')]

        missing_features = np.setdiff1d(unique_imported_features, features_list)
        nouid = False
        if len(missing_features) > 0:
            sg.popup('The following Nucleic acid features are missing and will be imported:\n', ', '.join(missing_features))
            for i in missing_features:
                print('Adding nucleic acid feature ', i)
                if not "uid" in features_columns:
                    nouid = True
                    cursor.execute("INSERT INTO Features (annotation, alias, risk, organism) SELECT annotation, alias, risk, organism FROM other.Features WHERE other.Features.annotation = ?", (i,))
                else:
                    cursor.execute("INSERT INTO Features (annotation, alias, risk, organism, uid) SELECT annotation, alias, risk, organism, uid FROM other.Features WHERE other.Features.annotation = ?", (i,))
            connection.commit()
            cursor.execute("UPDATE Features SET risk = REPLACE(risk, 'None', 'No Risk')"),
            connection.commit()

        missing_organisms_from_features = pd.DataFrame(columns=['organism'])
        missing_organisms_from_gmos = pd.DataFrame(columns=['organism_name'])
        if len(missing_features) > 0:
            if len(missing_features) > 1:
                missing_organisms_from_features = pd.read_sql_query('SELECT organism FROM Features WHERE annotation IN {}'.format(str(tuple(missing_features))), connection)
            else:
                missing_organisms_from_features = pd.read_sql_query('SELECT organism FROM Features WHERE annotation = {}'.format(str(missing_features[0])), connection)
            if len(imported_plasmid_ids) > 1:
                missing_organisms_from_gmos = pd.read_sql_query('SELECT organism_name FROM other.GMOs WHERE plasmid_id IN {}'.format(str(tuple(imported_plasmid_ids))), connection)
            else:
                missing_organisms_from_gmos = pd.read_sql_query('SELECT organism_name FROM other.GMOs WHERE plasmid_id = {}'.format(str(imported_plasmid_ids[0])), connection)
        missing_organisms_from_gmos = missing_organisms_from_gmos.rename(columns={'organism_name': 'organism'})
        missing_organisms = pd.concat([missing_organisms_from_features['organism'], missing_organisms_from_gmos['organism']], ignore_index=True)
        unique_missing_organisms = set()
        for idx, orga in missing_organisms.items():
            unique_missing_organisms.add(orga)

        unique_missing_organisms = list(unique_missing_organisms)
        local_organisms = pd.read_sql_query('SELECT short_name FROM Organisms', connection)
        for organism in unique_missing_organisms[:]:
            if organism in local_organisms.short_name.values:
                unique_missing_organisms.remove(organism)

        organisms_columns = [i[1] for i in cursor.execute('PRAGMA other.table_info(Organisms)')]
        if len(unique_missing_organisms) > 0:
            sg.popup('The following Organisms are used by the imported nucleic acid features and generated GMOs but are missing and will be added:\n', ', '.join(unique_missing_organisms))
            for i in unique_missing_organisms:
                print('Adding organism ', i)
                if not "uid" in organisms_columns:
                    nouid = True
                    cursor.execute("INSERT INTO Organisms (full_name, short_name, RG) SELECT full_name, short_name, RG FROM other.Organisms WHERE other.Organisms.short_name = ?", (i,))
                else:
                    cursor.execute("INSERT INTO Organisms (full_name, short_name, RG, uid) SELECT full_name, short_name, RG, uid FROM other.Organisms WHERE other.Organisms.short_name = ?", (i,))
            connection.commit()

        if nouid:
            sg.popup('Features/Organisms were imported with new unique identifiers.')

        cursor.close()
        connection.close()

    except Exception as e:
        sg.popup(e)
