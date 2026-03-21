"""Helper wrapper functions for GMOCU operations."""

import os
import sys
import sqlite3

import PySimpleGUI as sg
import pandas as pd

from src.gmocu import core as gmocu_core
from src.gmocu import database as gmocu_db
from src.gmocu.services import gsheets as gmocu_gsheets
from src.gmocu.services import ice as gmocu_ice
from src.gmocu.services import fileservers as gmocu_fileservers


def read_settings(database):
    s = gmocu_db.read_settings(database)
    return (s['user_name'], s['initials'], s['email'], s['institution'],
            s['ice'], s['duplicate_gmos'], s['upload_completed'],
            s['upload_abi'], s['scale'], s['font_size'], s['style'],
            s['ice_instance'], s['ice_token'], s['ice_token_client'],
            s['horizontal_layout'], s['filebrowser_instance'],
            s['filebrowser_user'], s['filebrowser_pwd'],
            s['use_ice'], s['use_filebrowser'], s['use_gdrive'],
            s['zip_files'], s['autosync'])


def autocomp(database):
    try:
        return gmocu_core.get_feature_annotations(database)
    except Exception as e:
        sg.popup(e)


def select_orga(database):
    try:
        return gmocu_core.get_organism_short_names(database)
    except Exception as e:
        sg.popup(e)


def insertBLOB(database, plasmidId, file, filename):
    try:
        gmocu_core.insert_attachment(database, plasmidId, file, filename)
    except Exception as error:
        print("Failed to insert blob data into sqlite table", error)


def readBlobData(database, attId, attName, path):
    try:
        gmocu_core.read_attachment(database, attId, attName, path)
    except FileNotFoundError:
        sg.popup("There is no attachment to download.")
    except Exception as error:
        print("Failed to read blob data from sqlite table", error)


def add_to_features(database, db, wb):
    added, skipped = gmocu_core.add_features_from_dataframe(database, wb)
    if skipped:
        sg.popup('The following entries already exist and will not be imported:\n\n{}'.format(', '.join(skipped)))
    if added:
        sg.popup('Adding: {}'.format(', '.join(added)))
    db['Features'].requery()


def add_to_organisms(database, db, wb):
    added = gmocu_core.add_organisms_from_dataframe(database, wb)
    if added:
        sg.popup('Adding: {}'.format(', '.join(added)))
    db['Organisms'].requery()


def update_cassettes(database, old2new_annot_dict):
    gmocu_core.update_cassettes(database, old2new_annot_dict)


def update_alias(database, db, old2new_annot_dict):
    gmocu_core.update_aliases(database, old2new_annot_dict)
    db['Plasmids'].requery()


def sync_gsheets(database, db, user_data, initials):
    sheet_id = db['Settings']['gdrive_glossary']
    error = gmocu_gsheets.validate_sync_prerequisites(database, user_data, sheet_id)
    if error:
        sg.popup(error)
        return

    try:
        result = gmocu_gsheets.sync_gsheets(database, user_data, sheet_id, initials)
    except Exception as e:
        sg.popup(e)
        return

    if result.errors:
        for err in result.errors:
            sg.popup(err)
    if result.imported_features:
        sg.popup('The following features were imported:\n', ', '.join(result.imported_features))
    if result.imported_organisms:
        sg.popup('The following organisms were imported:\n', ', '.join(result.imported_organisms))
    if result.repeated_annotations:
        sg.popup('The following locally stored features have an annotation name that already exists in the Google Sheets glossary:\n\n' + ', '.join(result.repeated_annotations) + '\n\nThese features will therefore not be uploaded nor synced.')
    if result.repeated_organisms:
        sg.popup('The following locally stored organisms have a short name that already exists in the Google Sheets glossary:\n\n' + ', '.join(result.repeated_organisms) + '\n\nThese organisms will therefore not be uploaded nor synced.')
    if result.uploaded_features:
        sg.popup('The following features were uploaded:\n', ', '.join(result.uploaded_features))
    if result.uploaded_organisms:
        sg.popup('The following organisms were uploaded:\n', ', '.join(result.uploaded_organisms))
    if result.updated_features:
        sg.popup('The following features were updated:', ', '.join(result.updated_features))
    if result.updated_organisms:
        sg.popup('The following organisms were updated:', ', '.join(result.updated_organisms))
    if result.deleted_features:
        del_invalid = sg.popup_yes_no('The following Nucleic acid Features were set as "invalid" in the Google Sheet master glossary and will be deleted.\n\n{}\n\nProceed?'.format(', '.join(result.deleted_features)))
        if del_invalid == 'Yes':
            conn = sqlite3.connect(database)
            cursor = conn.cursor()
            uids = []
            for name in result.deleted_features:
                cursor.execute("SELECT uid FROM Features WHERE annotation=?", (name,))
                row = cursor.fetchone()
                if row:
                    uids.append(row[0])
            conn.close()
            gmocu_gsheets.apply_deletions(database, uids, [])
    if result.deleted_organisms:
        del_invalid = sg.popup_yes_no('The following Organisms were set as "invalid" in the Google Sheet master glossary and will be deleted.\n\n{}\n\nProceed?'.format(', '.join(result.deleted_organisms)))
        if del_invalid == 'Yes':
            conn = sqlite3.connect(database)
            cursor = conn.cursor()
            uids = []
            for name in result.deleted_organisms:
                cursor.execute("SELECT uid FROM Organisms WHERE short_name=?", (name,))
                row = cursor.fetchone()
                if row:
                    uids.append(row[0])
            conn.close()
            gmocu_gsheets.apply_deletions(database, [], uids)

    db['Features'].requery()
    db['Organisms'].requery()
    db['Cassettes'].requery()
    db['Plasmids'].requery()


def generate_formblatt(database, lang):
    try:
        return gmocu_core.generate_formblatt(database, lang)
    except Exception as e:
        trace_back = sys.exc_info()[2]
        line = trace_back.tb_lineno
        sg.popup("Line: ", line, e)


def generate_plasmidlist(database):
    return gmocu_core.generate_plasmid_list(database)


def upload_ice(database, values, thisice, use_ice):
    if use_ice == 0 and thisice == '':
        return
    try:
        settings = gmocu_db.read_settings(database)
        gmocu_ice.upload_to_ice(
            database, settings,
            plasmid_name=thisice if thisice else None,
            only_new=values.get('-ONLYNEW-', False) if thisice == '' else False,
        )
        sg.popup('Upload completed.')
    except Exception as e:
        sg.popup(e)


def upload_file_servers(database, db, user_data, thisfile, use_filebrowser, use_gdrive, zip_files):
    try:
        settings = gmocu_db.read_settings(database)
        path = gmocu_fileservers.prepare_local_files(
            database, user_data, settings,
            plasmid_name=thisfile if thisfile else None,
        )

        if use_filebrowser == 1:
            gmocu_fileservers.upload_filebrowser(
                path, settings, plasmid_name=thisfile if thisfile else None,
            )
            sg.popup('Upload to Filebrowser server completed.')

        if use_gdrive == 1:
            gdrive_folder_id = db['Settings']['gdrive_id']
            credits_path = os.sep.join([user_data, 'gmocu_gdrive_credits.json'])
            gmocu_fileservers.upload_gdrive(
                path, user_data, settings, gdrive_folder_id, credits_path,
                plasmid_name=thisfile if thisfile else None,
                zip_files=bool(zip_files),
            )
            sg.popup('Upload to GDrive server completed.')

        if use_filebrowser == 0 and use_gdrive == 0:
            sg.popup('Files were only stored locally and not uploaded.')

    except Exception as e:
        sg.popup(e)


def add_organism(database, db, values, organism_index):
    selected_organism_index = organism_index
    choosen_target_RG = db['Plasmids']['target_RG']
    approval = values['-APPROVAL-']
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    cursor.execute("SELECT organism_name FROM OrganismSelection WHERE orga_sel_id = ?", (selected_organism_index,))
    out = cursor.fetchone()
    value = "'{0}'".format(out[0])
    db['GMOs'].insert_record(column='organism_name', value=value)
    if db['Plasmids']['destroyed'] == '':
        destroyed = 'tbd'
    else:
        destroyed = db['Plasmids']['destroyed']
    gmo_summary = 'RG ' + str(choosen_target_RG) + '   |   ' + 'Approval: ' + approval + '   |   ' + str(db['Plasmids']['generated']) + '   -   ' + str(destroyed) + '   |   ' + db['GMOs']['organism_name'].ljust(30)
    cursor.execute("UPDATE GMOs SET (target_RG, GMO_summary, date_generated, date_destroyed, approval) = (?, ?, ?, ?, ?) WHERE organism_id = (SELECT MAX(organism_id) FROM GMOs)", (choosen_target_RG, gmo_summary, db['Plasmids']['generated'], db['Plasmids']['destroyed'], approval))
    connection.commit()
    cursor.close()
    connection.close()


def check_plasmids(database):
    try:
        result = gmocu_core.check_plasmids(database)
        return [result['duplicates'], result['no_backbone'],
                result['no_cassettes'], result['no_gmos']]
    except Exception as e:
        sg.popup(e)


def check_features(database):
    try:
        result = gmocu_core.check_features(database)
        if result['has_empty_fields']:
            sg.popup("Empty fields in the Nucleic acid features glossary detected. Please fill all fields.")
        if not result['complete']:
            sg.popup('The following features are used in the cassettes of the listed plasmids, but missing in the "Nucleic acids" feature glossary:\n', '\n'.join(result['missing']), '\nPlease check if there are no misspells and, if not, add them to the glossary!', title='Features missing!')
        return [result['complete'], result['redundant'], result['duplicates']]
    except Exception as e:
        trace_back = sys.exc_info()[2]
        line = trace_back.tb_lineno
        sg.popup("Line: ", line, e)


def check_organisms(database):
    try:
        result = gmocu_core.check_organisms(database)
        if not result['complete']:
            sg.popup('The following organisms are associated with used Nucleic Acids features, but missing in the "Organisms" glossary:\n', "\n".join(result['missing_pairs']), '\nPlease check if there are no misspells and, if not, add them to the glossary!', title='Organisms missing!')
        return [result['complete'], result['redundant'], result['duplicates']]
    except Exception as e:
        sg.popup(e)


def export_all_features(database, user_data):
    connection = sqlite3.connect(database)
    pd.read_sql_query('SELECT * FROM Features', connection).to_excel(
        os.sep.join([user_data, 'ALL_nucleic_acid_features.xlsx']), index=False, engine='xlsxwriter')
    connection.close()
    sg.popup('Done.')


def export_all_organisms(database, user_data):
    connection = sqlite3.connect(database)
    pd.read_sql_query('SELECT * FROM Organisms', connection).to_excel(
        os.sep.join([user_data, 'ALL_organisms.xlsx']), index=False, engine='xlsxwriter')
    connection.close()
    sg.popup('Done.')


def export_used_features(database, user_data, user_name, initials):
    from datetime import date
    try:
        connection = sqlite3.connect(database)
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM Cassettes')
        lst = []
        for i in cursor.fetchall():
            lst.append(i[1])
        lst = '-'.join(lst).split('-')
        cursor.close()

        today = date.today()
        target = os.sep.join([user_data, 'USED_nucleic_acid_features' + '_' + user_name + '_' + str(today.strftime("%Y-%m-%d")) + '.xlsx'])
        writer = pd.ExcelWriter(target, engine='xlsxwriter')
        pd.read_sql_query('SELECT annotation, alias, risk, organism, uid FROM Features WHERE annotation IN {}'.format(str(tuple(lst))), connection).to_excel(writer, sheet_name='Sheet1', index=False, startrow=0)
        connection.close()

        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'align': 'center', 'border': 1, 'bg_color': '#D3D3D3'})
        fmt = workbook.add_format({'text_wrap': True, 'border': 1})
        worksheet = writer.sheets['Sheet1']

        worksheet.write(0, 0, 'Annotation', header_format)
        worksheet.write(0, 1, 'Alias', header_format)
        worksheet.write(0, 2, 'Risk', header_format)
        worksheet.write(0, 3, 'Organism', header_format)
        worksheet.write(0, 4, 'UID', header_format)

        footer = initials + ' List of used nucleic acid features'
        worksheet.set_footer(footer)
        worksheet.set_portrait()
        worksheet.repeat_rows(0)
        worksheet.set_paper(9)
        worksheet.fit_to_pages(1, 0)

        worksheet.set_column(0, 0, 20, fmt)
        worksheet.set_column(1, 1, 60, fmt)
        worksheet.set_column(2, 2, 10, fmt)
        worksheet.set_column(3, 3, 10, fmt)
        worksheet.set_column(4, 3, 34, fmt)

        writer.close()
        sg.popup('Done.')
    except:
        sg.popup('There must be more than one element in the list and used in Cassettes in order to use the export function.')


def export_used_organisms(database, user_data, user_name, initials):
    from datetime import date
    try:
        connection = sqlite3.connect(database)
        cursor = connection.cursor()

        cursor.execute('SELECT * FROM Cassettes')
        lst = []
        for i in cursor.fetchall():
            lst.append(i[1])
        lst = '-'.join(lst).split('-')

        cursor.execute('SELECT * FROM GMOs')
        lst2 = []
        for i in cursor.fetchall():
            lst2.append(i[2])

        cursor.execute('SELECT short_name FROM Organisms WHERE full_name IN {}'.format(str(tuple(lst2))))
        lst3 = []
        for i in cursor.fetchall():
            lst3.append(i[0])

        cursor.execute('SELECT organism FROM Features WHERE annotation IN {}'.format(str(tuple(lst))))
        lst4 = []
        for i in cursor.fetchall():
            lst4.append(i[0])

        lst5 = lst3 + lst4

        today = date.today()
        target = os.sep.join([user_data, 'USED_organisms' + '_' + user_name + '_' + str(today.strftime("%Y-%m-%d")) + '.xlsx'])
        writer = pd.ExcelWriter(target, engine='xlsxwriter')

        pd.read_sql_query('SELECT full_name, short_name, RG, uid FROM Organisms WHERE short_name IN {}'.format(str(tuple(lst5))), connection).to_excel(writer, sheet_name='Sheet1', index=False, startrow=0)
        cursor.close()
        connection.close()

        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'align': 'center', 'border': 1, 'bg_color': '#D3D3D3'})
        fmt = workbook.add_format({'text_wrap': True, 'border': 1})
        worksheet = writer.sheets['Sheet1']

        worksheet.write(0, 0, 'Full name', header_format)
        worksheet.write(0, 1, 'Short name', header_format)
        worksheet.write(0, 2, 'Risk group', header_format)
        worksheet.write(0, 3, 'UID', header_format)

        footer = initials + ' List of used organisms'
        worksheet.set_footer(footer)
        worksheet.set_portrait()
        worksheet.repeat_rows(0)
        worksheet.set_paper(9)
        worksheet.fit_to_pages(1, 0)

        worksheet.set_column(0, 0, 50, fmt)
        worksheet.set_column(1, 1, 20, fmt)
        worksheet.set_column(2, 2, 10, fmt)
        worksheet.set_column(3, 2, 34, fmt)

        writer.close()
        sg.popup('Done.')
    except:
        sg.popup('There must be more than one element in the list in order to use the export function.')
