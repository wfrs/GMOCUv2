#!/usr/bin/python3
"""GMOCU - Genetically Modified Organisms Cloning Utility."""

# TODO:
### Future features
# Implement generating GMOs with multiple plasmids
# Better implementation for uploading new/modified plasmid entries

### Bugs
# Better progress bar for Filebrowser upload?
# Check what setting 'upload completed' does

import PySimpleGUI as sg
import pysimplesqlmod as ss
import os, sys
import ssl
import sqlite3
import pandas as pd
import numpy as np
import logging
import shutil
from pathlib import Path
from datetime import date
from multiprocessing import freeze_support

from constants import (
    appname, version_no, vdate, database as database_name,
    os_font_size, os_scale_factor, img_base64, img2_base64, get_ui_constants,
)
from migrations import run_migrations
from helpers import (
    read_settings, autocomp, select_orga, insertBLOB, readBlobData,
    add_to_features, add_to_organisms, update_cassettes, update_alias,
    sync_gsheets, generate_formblatt, generate_plasmidlist,
    upload_ice, upload_file_servers, add_organism,
    check_plasmids, check_features, check_organisms,
    export_all_features, export_all_organisms,
    export_used_features, export_used_organisms,
)
from autocomplete import (
    handler as _ac_handler, clear_combo_tooltip, autocomplete,
)
from import_data import import_data
from layouts import build_layout

database = database_name

logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# Pyinstaller fix preventing reopening windows
freeze_support()

# get right path for pyinstaller
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)
logging.debug('CWD: ' + os.getcwd())

# set appdir path
user_data = os.sep.join([str(Path.home()), 'GMOCU'])

# copy template files if path does not yet exist
try:
    source = os.sep.join([os.getcwd(), 'Downloads', 'templates'])
    target = os.sep.join([user_data, 'templates'])
    templates_path = shutil.copytree(source, target, dirs_exist_ok=False)
except FileExistsError:
    pass

# set settings path
SETTINGS_PATH = user_data
sg.user_settings_filename(path=SETTINGS_PATH)

### autocomplete ###
orga_selection = []

# PySimpleGUI layout code
font_size = sg.user_settings_get_entry('-FONTSIZE-', os_font_size)
scale_factor = sg.user_settings_get_entry('-SCALE-', os_scale_factor)
if sys.platform.startswith("linux"):
    horizontal_layout = sg.user_settings_get_entry('-HORIZONTAL-', 0)
else:
    horizontal_layout = sg.user_settings_get_entry('-HORIZONTAL-', 1)
sg.set_options(font=("Helvetica", font_size))
sg.theme(sg.user_settings_get_entry('-THEME-', 'Reddit'))

# Build layout
ui = get_ui_constants(horizontal_layout)
layout = build_layout(ui, horizontal_layout, orga_selection, img_base64, img2_base64)

##### Window #####
win=sg.Window('GMOCU - GMO Documentation', layout, scaling=scale_factor, return_keyboard_events=True, finalize=True)
win['Plasmids.gb_name'].update(disabled=True)
win['Plasmids.gb'].update(disabled=True)
win['Plasmids.genebank'].update(visible=False)
win['Settings.style'].update(visible=False)
win['-ATTACHFRAME-'].expand(True, True)
win['-GENEBANKFRAME-'].expand(True, True)
win.refresh()
win['-ATTACHCOL-'].expand(True, True)
win['-ATTACHCOL-'].contents_changed()
win['-GENEBANKCOL-'].expand(True, True)
win.refresh()
win.move_to_center()
win.refresh()

# update database path for use with appdirs
database = os.sep.join([user_data, database])
# check if database file already exists for version maintainance below
database_file_exists = os.path.isfile(database)

sql_script ='gmocu.sql'
# generate database
db=ss.Database(database, win,  sql_script=sql_script) #<=== Here is the magic!
# Note:  sql_script is only run if *.db does not exist!  This has the effect of creating a new blank
# database as defined by the sql_script file if the database does not yet exist, otherwise it will use the database!

# Maintain db changes in version updates
if database_file_exists == True:
    run_migrations(database, db, win, version_no, user_data)


#db['Plasmids'].set_order_clause('ORDER BY id ASC')
db['Cassettes'].set_order_clause('ORDER BY cassette_id ASC')
db['Plasmids'].set_search_order(['name','alias']) # the search box will search in both the name and example columns
db['Features'].set_search_order(['annotation','alias', 'organism']) # the search box will search in both the name and example columns
db.edit_protect()
selected_plasmid=db['Plasmids']['id']
db['Plasmids'].set_by_pk(selected_plasmid)

# disable extra elements
extra_el_disabled = True
win['-DUPLICATE-'].update(disabled=True)
win['-THISICE-'].update(disabled=True)
win['-ALIAS_IN-'].update(disabled=True)
win['insGb'].update(disabled=True)
win['insElement'].update(disabled=True)
win['-down_att-'].update(disabled=True)
win['-down_gb-'].update(disabled=True)
win['-ADDORGA-'].update(disabled=True)
win['-DESTROYORGA-'].update(disabled=True)
win['-ADDFEATURE-'].update(disabled=True)
win['-FEATURECOMBO-'].update(disabled=True)
win['Features.organism'].update(disabled=True)
win['-APPROVAL-'].update(disabled=True)
win['Settings.name'].update(disabled=True)
win['Settings.initials'].update(disabled=True)
win['Settings.email'].update(disabled=True)
win['Settings.institution'].update(disabled=True)
win['Settings.ice'].update(disabled=True)
win['Settings.gdrive_glossary'].update(disabled=True)
win['Settings.gdrive_id'].update(disabled=True)
win['Settings.style'].update(disabled=True)
win['-SETSTYLE-'].update(disabled=True)
win['Settings.scale'].update(disabled=True)
win['Settings.font_size'].update(disabled=True)
win['Settings.horizontal_layout'].update(disabled=True)
win['Settings.duplicate_gmos'].update(disabled=True)
win['Settings.upload_completed'].update(disabled=True)
#win['Settings.upload_abi'].update(disabled=True)
win['Settings.use_ice'].update(disabled=True)
win['Settings.use_filebrowser'].update(disabled=True)
win['Settings.use_gdrive'].update(disabled=True)
win['Settings.zip_files'].update(disabled=True)
win['Settings.autosync'].update(disabled=True)
win['-SETSELORGA-'].update(disabled=True)
win['-ADDSELORGA-'].update(disabled=True)
win['-COPYFAVORGA-'].update(disabled=True)
win['-ADDFAV-'].update(disabled=True)

# keyboard navigation
win.bind('<Down>', '-DOWNKEY-')
win.bind('<Up>', '-UPKEY-')
win.bind('<Return>', '-ENTERKEY-')
win.bind('<Escape>', '-ESCAPEKEY-')
win.bind('<Button-1>', '-LEFTCLICK-')
win.bind('<Control-KeyPress-e>', '-CTRL-E-') # trigger event with key press combination

### read settings ###
user_name, initials, email, institution, ice, duplicate_gmos, upload_completed, upload_abi, scale, font_size, style, ice_instance, ice_token, ice_token_client, horizontal_layout, filebrowser_instance, filebrowser_user, filebrowser_pwd, use_ice, use_filebrowser, use_gdrive, zip_files, autosync = read_settings(database)

### GUI settings ###
if scale == '__':
    scale = os_scale_factor
if font_size == '__':
    font_size = os_font_size
    win['Settings.font_size'].update(font_size)
    win['Settings.scale'].update(scale)
    if not sys.platform.startswith("linux"):
        win['Settings.horizontal_layout'].update(1)
    else:
        win['Settings.horizontal_layout'].update(0)
    db['Settings'].save_record(display_message=False)

sg.user_settings_set_entry('-THEME-', style)
sg.user_settings_set_entry('-SCALE-', float(scale))
sg.user_settings_set_entry('-FONTSIZE-', int(font_size))
sg.user_settings_set_entry('-HORIZONTAL_LAYOUT-', int(win['Settings.horizontal_layout'].get()))

### autocomplete ###
choices = autocomp(database)
orga_selection = select_orga(database)
win['-FEATURECOMBO-'].Update(values = orga_selection)
win['-SETSELORGA-'].Update(values = orga_selection)

autocomp_el_keys = ['-AIN-', '-FEATURECOMBO-']
autocomp_options = {}
def refresh_autocomp_options():
    global autocomp_options
    autocomp_options = {'-AIN-': {'values': choices, 'show_on_empty': False},
                        '-FEATURECOMBO-': {'values': orga_selection, 'show_on_empty': True}}
refresh_autocomp_options()
active_element = win[[i for i in win.AllKeysDict.keys()][0]]
active_element.set_focus()
space_ref = win['-SPACEREF-']
text_len = win['-TEXTLEN-']
text_len.update(text_color=text_len.BackgroundColor)
sg.PySimpleGUI.TOOLTIP_BACKGROUND_COLOR = win['-AIN-'].BackgroundColor
sg.set_options(tooltip_font=(('Helvetica', font_size)))
win.refresh()

# Create handler closure that captures win and active_element
def _handler(event):
    _ac_handler(event, win, active_element)

def _autocomplete(event, values):
    autocomplete(event, values, auto_options=autocomp_options[active_element.key],
                 ui_handle=active_element, space_ref=space_ref, text_len=text_len,
                 win=win, handler_func=_handler)

# call initials on first start, changing initals later is not allowed because it might create a mess when updating plasmids on ice as a new folder would be created
initials_value = db['Settings']['initials']
if initials_value == '__':
    initials_set = sg.popup_get_text('Please enter your initials. This name will be used as folder name when uploading plasmids to ice.\nPlease note that you cannot change the name anymore at a later time.')
    win['Settings.initials'].update(initials_set)
    db['Settings'].save_record(display_message=False)


# WHILE
#-------------------------------------------------------
if autosync == 1:
    sync_gsheets(database, db, user_data, initials)
    choices = autocomp(database)
    orga_selection = select_orga(database)
    win['-FEATURECOMBO-'].Update(values = orga_selection)
    win['-SETSELORGA-'].Update(values = orga_selection)
    refresh_autocomp_options()
check_plasmids(database)
check_features(database)
check_organisms(database)

while True:
    event, values = win.read()
    print('event:', event)
    for key in autocomp_el_keys:
        clear_combo_tooltip(ui_handle=win[key])

    if event == 'featureActions.db_save':
        old_annotation = db['Features']['annotation'] or ''

### Let PySimpleSQL process its own events! Simple! ###
    if  db.process_events(event, values):
        logger.info(f'PySimpleDB event handler handled the event {event}!')

### Fix display ###
    if event == 'cassettesActions.table_insert':
        db['Plasmids'].save_record(display_message=False)
        selected_plasmid=db['Plasmids']['id']
        db['Plasmids'].set_by_pk(selected_plasmid)
    elif event == 'cassettesActions.db_save':
        check_features(database)
        check_organisms(database)
    elif event == 'featureActions.db_save':
        corrected_value = db['Features']['annotation']
        corrected_value = corrected_value.replace('-', '_')
        corrected_value = corrected_value.replace('[', '(')
        corrected_value = corrected_value.replace(']', ')')
        corrected_value = corrected_value.replace(' ', '_')
        win['Features.annotation'].update(corrected_value)
        db['Features'].save_record(display_message=False)
        choices = autocomp(database)
        if choices.count(corrected_value) > 1:
            sg.popup('There already exists a feature with the same annotation: ' + corrected_value + '.\n The entry is invalid, please enter a new annotation name!')
            win['Features.annotation'].update('')
            db['Features'].save_record(display_message=False)
            choices = autocomp(database)
        elif db['Settings']['autosync'] == 1:
            sync_gsheets(database, db, user_data, initials)
            choices = autocomp(database)
            orga_selection = select_orga(database)
            win['-FEATURECOMBO-'].Update(values = orga_selection)
            win['-SETSELORGA-'].Update(values = orga_selection)
        if old_annotation and old_annotation != corrected_value:
            update_cassettes(database, {old_annotation:corrected_value})
            update_alias(database, db, {old_annotation:corrected_value})
        refresh_autocomp_options()
        check_features(database)
        check_organisms(database)

    elif event == 'settingsActions.db_save':
        db['Settings'].save_record(display_message=False)
        user_name, initials, email, institution, ice, duplicate_gmos, upload_completed, upload_abi, scale, font_size, style, ice_instance, ice_token, ice_token_client, horizontal_layout, filebrowser_instance, filebrowser_user, filebrowser_pwd, use_ice, use_filebrowser, use_gdrive, zip_files, autosync = read_settings(database)
        sg.user_settings_set_entry('-THEME-', (values['Settings.style']))
        sg.user_settings_set_entry('-SCALE-', (values['Settings.scale']))
        sg.user_settings_set_entry('-FONTSIZE-', (values['Settings.font_size']))
        win['Settings.style'].update(disabled=True) # not a perfect solution
        win['Settings.style'].update(value=values['-SETSTYLE-'])
        win['Settings.initials'].update(disabled=True)
    elif event == 'Settings.ice.quick_edit':
        db['Settings'].save_record(display_message=False)
    elif event in ['settingsActions.edit_protect', 'featureActions.edit_protect', 'plasmidActions.edit_protect']:
        # enable extra elements
        extra_el_disabled = not extra_el_disabled
        win['-DUPLICATE-'].update(disabled=extra_el_disabled)
        win['-THISICE-'].update(disabled=extra_el_disabled)
        win['-ADDFEATURE-'].update(disabled=extra_el_disabled)
        win['-ALIAS_IN-'].update(disabled=extra_el_disabled)
        win['insGb'].update(disabled=extra_el_disabled)
        win['insElement'].update(disabled=extra_el_disabled)
        win['-down_att-'].update(disabled=extra_el_disabled)
        win['-down_gb-'].update(disabled=extra_el_disabled)
        win['-ADDORGA-'].update(disabled=extra_el_disabled)
        win['-DESTROYORGA-'].update(disabled=extra_el_disabled)
        win['-APPROVAL-'].update(disabled=extra_el_disabled)
        win['-ADDFAV-'].update(disabled=extra_el_disabled)
        win['-AIN-'].update(disabled=extra_el_disabled)
        win['-VARIANT-'].update(disabled=extra_el_disabled)
        win['-FEATURECOMBO-'].update(disabled=extra_el_disabled)
        #win['Features.organism'].update(disabled=True) #always disabled, not working?
        win['Settings.name'].update(disabled=extra_el_disabled)
        win['Settings.initials'].update(disabled=True)
        win['Settings.email'].update(disabled=extra_el_disabled)
        win['Settings.institution'].update(disabled=extra_el_disabled)
        win['Settings.ice'].update(disabled=extra_el_disabled)
        win['Settings.gdrive_glossary'].update(disabled=extra_el_disabled)
        win['Settings.gdrive_id'].update(disabled=extra_el_disabled)
        win['Settings.style'].update(disabled=extra_el_disabled)
        win['-SETSTYLE-'].update(disabled=extra_el_disabled)
        win['Settings.scale'].update(disabled=True)
        win['Settings.font_size'].update(disabled=True)
        win['Settings.horizontal_layout'].update(disabled=extra_el_disabled)
        win['Settings.duplicate_gmos'].update(disabled=extra_el_disabled)
        #win['Settings.upload_completed'].update(disabled=extra_el_disabled) # disabled for now
        #win['Settings.upload_abi'].update(disabled=True) # disabled for now
        win['Settings.use_ice'].update(disabled=extra_el_disabled)
        if sys.platform != "win32":
            win['Settings.use_filebrowser'].update(disabled=extra_el_disabled)
        win['Settings.use_gdrive'].update(disabled=extra_el_disabled)
        win['Settings.zip_files'].update(disabled=extra_el_disabled)
        win['Settings.autosync'].update(disabled=extra_el_disabled)
        win['-SETSELORGA-'].update(disabled=extra_el_disabled)
        win['-ADDSELORGA-'].update(disabled=extra_el_disabled)
        win['-COPYFAVORGA-'].update(disabled=extra_el_disabled)

        # protect synced entries (Features, Organisms)
        feature_protection = db['Features']['synced']
        organism_protection = db['Organisms']['synced']
        if feature_protection == 1:
            win['Features.annotation'].update(disabled=True)
            win['Features.alias'].update(disabled=True)
            win['Features.risk'].update(disabled=True)
            win['Features.organism'].update(disabled=True)
            win['-FEATURECOMBO-'].update(disabled=True)
        if organism_protection == 1:
            win['Organisms.full_name'].update(disabled=True)
            win['Organisms.short_name'].update(disabled=True)
            win['Organisms.RG'].update(disabled=True)

    elif event == 'plasmidActions.table_insert':
        selected_plasmid=db['Plasmids']['id']
        newname = 'p' + initials + '000'
        newname_input = sg.popup_get_text('Enter the name for the new plasmid', default_text=newname)
        win['Plasmids.name'].update(newname_input)
        db['Plasmids'].save_record(display_message=False)
        db['Plasmids'].set_by_pk(selected_plasmid)

    elif event == 'featureActions.table_delete':
        choices = autocomp(database)
        refresh_autocomp_options()

    elif event == 'organismActions.table_delete':
        orga_selection = select_orga(database)
        refresh_autocomp_options()
        win['-FEATURECOMBO-'].Update(values = orga_selection)
        win['-SETSELORGA-'].Update(values = orga_selection)

    elif event == 'organismActions.db_save':
        orga_selection = select_orga(database)
        refresh_autocomp_options()
        win['-FEATURECOMBO-'].Update(values = orga_selection)
        win['-SETSELORGA-'].Update(values = orga_selection)
        if orga_selection.count(db['Organisms']['short_name']) > 1:
            sg.popup('There already exists an organism with the same short name: ' + db['Organisms']['short_name'] + '.\n The entry is invalid, please enter a new annotation name!')
            win['Organisms.short_name'].update('')
            db['Organisms'].save_record(display_message=False)
            choices = autocomp(database)
        elif db['Settings']['autosync'] == 1:
            sync_gsheets(database, db, user_data, initials)
            choices = autocomp(database)
            orga_selection = select_orga(database)
            win['-FEATURECOMBO-'].Update(values = orga_selection)
            win['-SETSELORGA-'].Update(values = orga_selection)
        refresh_autocomp_options()
        check_organisms(database)

### Duplicate plasmid ###
    elif event == '-DUPLICATE-':
        duplicate_plasmid = sg.popup_yes_no('Do you wish to duplicate the plasmid entry?')
        if duplicate_plasmid == 'Yes':
            user_name, initials, email, institution, ice, duplicate_gmos, upload_completed, upload_abi, scale, font_size, style, ice_instance, ice_token, ice_token_client, horizontal_layout, filebrowser_instance, filebrowser_user, filebrowser_pwd, use_ice, use_filebrowser, use_gdrive, zip_files, autosync = read_settings(database)
            today = date.today()
            selected_plasmid = db['Plasmids']['id']
            connection = sqlite3.connect(database)
            cursor = connection.cursor()
            cursor.execute("INSERT INTO Plasmids (name, alias, purpose, summary, clone, backbone_vector) SELECT name, alias, purpose, summary, clone, backbone_vector FROM Plasmids WHERE Plasmids.id = ?", (selected_plasmid,))
            cursor.execute("SELECT MAX(id) FROM Plasmids")
            out = cursor.fetchone()[0]
            connection.commit()
            # duplicate cassettes
            cursor.execute("SELECT content, plasmid_id FROM Cassettes WHERE plasmid_id = ?", (selected_plasmid,))
            cas = cursor.fetchall()
            for i in cas:
                db['Cassettes'].insert_record(column='plasmid_id', value=out)
                cursor.execute("UPDATE Cassettes SET content = ? WHERE cassette_id = (SELECT MAX(cassette_id) FROM Cassettes)", (i[0],))
                connection.commit()
            # duplicate GMOs if selected in settings but with current date
            if duplicate_gmos == 1:
                cursor.execute("SELECT organism_name, plasmid_id, target_RG, approval FROM GMOs WHERE plasmid_id = ?", (selected_plasmid,))
                gmos = cursor.fetchall()
                for i in gmos:
                    db['GMOs'].insert_record(column='plasmid_id', value=out)
                    gmo_summary = 'RG ' + str(i[2]) + '   |   ' + 'Approval: ' + i[3] + '   |   ' + str(today.strftime("%Y-%m-%d")) + '   -   ' + 'tbd' + '   |   ' + i[0].ljust(30)
                    cursor.execute("UPDATE GMOs SET (organism_name, target_RG, GMO_summary, approval) = (?, ?, ?, ?) WHERE organism_id = (SELECT MAX(organism_id) FROM GMOs)", (i[0], i[2], gmo_summary, i[3]))
                    connection.commit()
            cursor.close()
            connection.close()
            db['Plasmids'].save_record(display_message=False)
            db['Plasmids'].set_by_pk(out)
            win['Plasmids.name'].update(db['Plasmids']['name'] + ' (Copy)')
            db['Plasmids'].save_record(display_message=False)
            db['Plasmids'].set_by_pk(out)

### GMOs ###
    elif event == '-THISICE-':
        thisice = db['Plasmids']['name']
        upload = sg.popup_yes_no('Updating plasmid {} on servers. Proceed?'.format(thisice))
        if upload == 'Yes':
            if use_ice == 1:
                upload_ice(database, values, thisice, use_ice=use_ice)
            if use_filebrowser == 1 or use_gdrive == 1:
                upload_file_servers(database, db, user_data, thisfile=thisice, use_filebrowser=use_filebrowser, use_gdrive=use_gdrive, zip_files=zip_files)

    elif event == '-ADDORGA-':
        try:
            db['Plasmids'].save_record(display_message=False)
            selected_plasmid = db['Plasmids']['id']
            organism_index = db['Plasmids']['organism_selector']
            add_organism(database, db, values, organism_index)

        except TypeError:
            sg.popup("Choose an organism.")
        finally:
            win["Plasmids.organism_selector"]('')
            db['Plasmids'].save_record(display_message=False)
            db['Plasmids'].set_by_pk(selected_plasmid)

    elif event == '-ADDFAV-':
        addfav = sg.popup_yes_no('Adding all favourite organisms as GMOs. Proceed?')
        if addfav == 'Yes':
            try:
                db['Plasmids'].save_record(display_message=False)
                selected_plasmid = db['Plasmids']['id']
                connection = sqlite3.connect(database)
                cursor = connection.cursor()
                favs = pd.read_sql_query("SELECT * FROM OrganismFavourites", connection)
                target_orgas = pd.read_sql_query("SELECT * FROM OrganismSelection", connection)
                comparison = np.setdiff1d(list(favs['organism_fav_name']), list(target_orgas['organism_name']))
                if len(comparison) > 0:
                    sg.popup('Settings: Not all elements in Favourite organisms are present in Target organisms. Please fix!')
                else:
                    for idx, fav in favs.iterrows():
                        cursor.execute("SELECT orga_sel_id FROM OrganismSelection WHERE organism_name = ?", (fav['organism_fav_name'],))
                        orga_id = cursor.fetchone()[0]
                        add_organism(database, db, values, orga_id)
            except Exception as e:
                sg.popup(e)
            finally:
                cursor.close()
                connection.close()
                win["Plasmids.organism_selector"]('')
                db['Plasmids'].save_record(display_message=False)
                db['Plasmids'].set_by_pk(selected_plasmid)

    elif event == '-DESTROYORGA-':
        if values['Plasmids.destroyed'] == '':
            pass
        else:
            destruction_date = values['Plasmids.destroyed']
            selected_GMO = db['GMOs']['organism_id']
            gmo_summary = db['GMOs']['GMO_summary']
            selected_plasmid = db['Plasmids']['id']
            gmo_summary = gmo_summary.replace('tbd', destruction_date)
            connection = sqlite3.connect(database)
            cursor = connection.cursor()
            cursor.execute("UPDATE GMOs SET GMO_summary = ? WHERE organism_id = ?", (gmo_summary, selected_GMO))
            connection.commit()
            cursor.close()
            connection.close()
            db['GMOs'].save_record(display_message=False)
            db['Plasmids'].set_by_pk(selected_plasmid)

### Attachments ###
    elif event == 'insElement':
        db['Plasmids'].save_record(display_message=False)
        selected_plasmid = db['Plasmids']['id']
        db['Plasmids'].set_by_pk(selected_plasmid)
        attachment_path = sg.popup_get_file('Select a file')
        if attachment_path == '' or attachment_path == None:
            pass
        else:
            filename = os.path.basename(attachment_path)
            selected_plasmid=db['Plasmids']['id']
            if filename == '':
                sg.popup('Select a file.')
                db['Plasmids'].set_by_pk(selected_plasmid)
            else:
                insertBLOB(database, selected_plasmid, attachment_path, filename)
                db['Plasmids'].set_by_pk(selected_plasmid)
    elif event == '-ALIAS_IN-':
        selected_plasmid = db['Plasmids']['id']
        selected_cassette = db['Cassettes']['content']
        win['Plasmids.alias'].update(selected_cassette)
        db['Plasmids'].save_record(display_message=False)
        db['Plasmids'].set_by_pk(selected_plasmid)

### Genebank ###
    elif event == 'insGb':
        gb_path = sg.popup_get_file('Please choose a gb file.')
        if gb_path == '' or gb_path == None:
            pass
        else:
            Gb_filename = os.path.basename(gb_path)
            selected_plasmid=db['Plasmids']['id']
            if Gb_filename == '':
                sg.popup('Select a Gb file.')
            else:
                filename, file_extension = os.path.splitext(Gb_filename)
                if file_extension != '.gb' and file_extension != '.gbk':
                    sg.popup('File must have .gb or .gbk extension.')
                else:
                    try:
                        with open(gb_path, "r") as f:
                            data = f.read()
                        db['Plasmids'].set_by_pk(selected_plasmid)
                        win['Plasmids.genebank'](data)
                        win["Plasmids.gb_name"](Gb_filename)
                        win["Plasmids.gb"]('•')
                        db['Plasmids'].save_record(display_message=False)
                        db['Plasmids'].set_by_pk(selected_plasmid)
                    except Exception as e:
                        sg.popup(e)
                        print('Choose a text file.')
    elif event == '-info-':
        sg.popup('The names for the cassette elements must adhere to the entries in the glossary. They are case sensitive.\n\nThe only accepted seperator is "-" which must not be used in the glossary entries.',keep_on_top=True)

    ### File download ###
    elif event == '-down_gb-':
        name_file = db['Plasmids']['gb_name']
        if name_file == '':
            sg.popup("There is no Genebank file to download.")
        else:
            try:
                download_path = user_data
                output_path = os.sep.join([download_path, name_file])
                genebank_content = db['Plasmids']['genebank'] or ''
                with open(output_path, 'w', encoding='utf-8') as fh:
                    fh.write(str(genebank_content))
            except IsADirectoryError:
                sg.popup("There is no Genebank file to download.")
            except Exception as e:
                sg.popup(e)
    elif event == '-down_att-':
        try:
            att_id = db['Attachments']['attach_id']
            att_name = db['Attachments']['Filename']
            readBlobData(database, att_id, att_name, user_data)
        except Exception as e:
            sg.popup(e)

### autocomplete ###
    # pressing down arrow will trigger event -AIN- then aftewards event Down:
    elif event == '-LEFTCLICK-':
        try:
            clear_combo_tooltip(ui_handle=active_element)
        except:
            pass
        try:
            active_element = win.FindElementWithFocus()
            if active_element.key in ['cassettesSelector', 'gmoSelector', 'attachmentSelector', 'organismselectionSelector', 'favouritesSelector']:
                win.write_event_value(active_element.key, values[active_element.key])
                active_element.block_focus()
        except:
            pass
    elif event == '-ENTERKEY-':
        clear_combo_tooltip(ui_handle=active_element)
    elif event == '	' or event == '-DOWNKEY-':
        if active_element.key in autocomp_el_keys:
            _autocomplete(event, values)
    elif event == '-DROPDOWN-':
        if active_element.key in autocomp_el_keys:
            print("hj")
            win[values['-DROPDOWN-']].Widget.event_generate('<Down>')
    elif event == '-ADDFEATURE-':
        selected_feature = values['-AIN-']
        if selected_feature[2:-3] in choices: # the truncation of values['-AIN-'][2:-3] is a hack to deal with the shape of 'choices' such as: ('Feature1'),
            selected_feature = selected_feature[2:-3]
        if selected_feature == "":
            pass
        else:
            variant = '['+values['-VARIANT-']+']'
            if db['Cassettes']['content'] == 'Empty' or db['Cassettes']['content'] == '':
                if values['-VARIANT-'] != '':
                    win['Cassettes.content'].update(selected_feature + variant)
                else:
                    win['Cassettes.content'].update(selected_feature)
            elif values['-VARIANT-'] != '':
                win['Cassettes.content'].update(db['Cassettes']['content'] + '-' + selected_feature + variant)
            else:
                win['Cassettes.content'].update(db['Cassettes']['content'] + '-' + selected_feature)
            db['Cassettes'].save_record(display_message=False)
            win['-AIN-'].update('')
            win['-VARIANT-'].update('')
            check_features(database)
            check_organisms(database)

    elif event == '-ALLEXCEL-':
        export_all_features(database, user_data)
    elif event == '-ALLEXCELORGA-':
        export_all_organisms(database, user_data)
    elif event == '-USEDEXCEL-':
        export_used_features(database, user_data, user_name, initials)
    elif event == '-USEDEXCELORGA-':
        export_used_organisms(database, user_data, user_name, initials)

    elif event == '-ADDFEATURESEXCEL-':
        excel_feature_file_path = sg.popup_get_file('Select the template *.xlsx file containing feature definitions to import.\nWe will only add new entries which not exist yet with the same name.')
        if excel_feature_file_path == '' or excel_feature_file_path == None:
            pass
        else:
            filename = os.path.basename(excel_feature_file_path)
            if filename == '':
                sg.popup('Select a file.')
            else:
                try:
                    wb = pd.read_excel(excel_feature_file_path, sheet_name = 0)
                    add_to_features(database, db, wb)
                    choices = autocomp(database)
                except FileNotFoundError:
                    sg.popup("File " + excel_feature_file_path + " does not exist.")

    elif event == '-ADDGOOGLE-': #to be removed
        try:
            ssl._create_default_https_context = ssl._create_unverified_context #monkeypatch
            sheet_id = db['Settings']['gdrive_glossary']
            sheet_name = 'features'
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
            wb = pd.read_csv(url)
            add_to_features(database, db, wb)
            choices = autocomp(database)
            refresh_autocomp_options()
        except Exception as e:
            sg.popup(e)

    elif event == '-ADDEXCELORGA-':
        file = sg.popup_get_file("Select file")
        if file:
            try:
                wb = pd.read_excel(file, sheet_name = 0)
                add_to_organisms(database, db, wb)
                orga_selection = select_orga(database)
                refresh_autocomp_options()
                win['-FEATURECOMBO-'].Update(values = orga_selection)
                win['-SETSELORGA-'].Update(values = orga_selection)
            except FileNotFoundError:
                sg.popup("File " + file + " does not exist. You might have to rename it.")
            except Exception as e:
                sg.popup(e)

    elif event == '-FEATURESYNC-' or event == '-ORGASYNC-':
        try:
            sync_gsheets(database, db, user_data, initials)
            choices = autocomp(database)
            orga_selection = select_orga(database)
            win['-FEATURECOMBO-'].Update(values = orga_selection)
            win['-SETSELORGA-'].Update(values = orga_selection)
            refresh_autocomp_options()

        except Exception as e:
            sg.popup(e)

    elif event == '-ADDGOOGLEORGA-':
        try:
            sheet_id = db['Settings']['gdrive_glossary']
            sheet_name = 'organisms'
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
            wb = pd.read_csv(url)
            add_to_organisms(database, db, wb)
            choices = autocomp(database)
            orga_selection = select_orga(database)
            refresh_autocomp_options()
            win['-FEATURECOMBO-'].Update(values = orga_selection)
            win['-SETSELORGA-'].Update(values = orga_selection)
        except Exception as e:
            sg.popup(e)

    elif event == '-FEATUREINFO-':
        sg.popup('Dashes and brackets "-, [, ]" in annotation names are not allowed and will be replaces by underscores and parentheses "_, (, )".')
    elif event == '-FEATURECOMBO-':
            orga_selection = select_orga(database)
            refresh_autocomp_options()
            win['-FEATURECOMBO-'].Update(values = orga_selection)
            win['Features.organism'].update(disabled=True) # not a perfect solution
            win['Features.organism'].update(value=values['-FEATURECOMBO-'])
    elif event == '-ADDSELORGA-':
            orga_selection = select_orga(database)
            refresh_autocomp_options()
            win['-SETSELORGA-'].Update(values = orga_selection)
            if values['-SETSELORGA-'] != '':
                value="'{}'".format(values['-SETSELORGA-'])
                db['OrganismSelection'].insert_record(column='organism_name', value=value)
    elif event == '-COPYFAVORGA-':
        selected_orga = db['OrganismSelection']['organism_name']
        value="'{0}'".format(selected_orga)
        db['OrganismFavourites'].insert_record(column='organism_fav_name', value=value)

### Check features completeness ###
    elif event == '-CHECKFEATURES-':
        check = check_features(database)
        if check[0] == True:
            sg.popup('All used nucleic acid features are present in the glossary.')
        if len(check[1]) > 0:
            sg.popup('The following features in the Nucleic acids feature glossary are redundant (not used):\n', ", ".join(check[1]), '\n You can keep them or remove them.')
        if len(check[2]) > 0:
            sg.popup('The following duplications were found in the Nucleic acids feature glossary:\n', ", ".join(check[2]), '\n Please remove duplicated items!')

### Check organisms completeness ###
    elif event == '-CHECKORGANISMS-':
        check = check_organisms(database)
        if check[0] == True:
            sg.popup('All used organisms are present in the glossary.')
        if len(check[1]) > 0:
            sg.popup('The following organisms in the Organism glossary are redundant (not used):\n', ", ".join(check[1]), '\n You can keep them or remove them.')
        if len(check[2]) > 0:
            sg.popup('The following duplications were found in the Organism glossary:\n', " ,".join(check[2]), '\n Please remove duplicated items!')

### Check for duplicated plasmid names ###
    elif event == '-CHECKPLASMIDS-':
        check = check_plasmids(database)
        if len(check[0]) > 0:
            sg.popup('The following duplicated plasmid names were found:\n', ", ".join(check[0]), '\n Please fix!')
        if len(check[1]) > 0:
            sg.popup('The following plasmids have no original vector:\n', ", ".join(check[1]), '\n Please fix!')
        if len(check[2]) > 0:
            sg.popup('The following plasmids have no cassettes:\n', ", ".join(check[2]), '\n Please fix!')
        if len(check[3]) > 0:
            sg.popup('The following plasmids have no GMOs:\n', ", ".join(check[3]), '\n Please fix!')
        else:
            sg.popup('All good!')

### Upload to ICE, Filebrowser, GDrive ###
    elif event == '-SERVERS-':
        configured_services = []
        if use_ice == 1:
            configured_services.append('JBEI/ice')
        if use_gdrive == 1:
            configured_services.append('GDrive')
        if use_filebrowser == 1:
            configured_services.append('Filebrowser')
        if len(configured_services) == 0:
            configured_services = ['NONE']
        upload = sg.popup_yes_no('Depending on database size and network, the upload may take some time. Currently enabled data upload servers: "{}". In any case, data will be exported locally. Proceed?'.format(" and ".join(configured_services)))
        if upload == 'Yes':
            upload_ice(database, values, thisice='', use_ice=use_ice)
            upload_file_servers(database, db, user_data, thisfile='', use_filebrowser=use_filebrowser, use_gdrive=use_gdrive, zip_files=zip_files)

### Formblatt Z ###
    elif event == '-FORMBLATT-':
        features_check = check_features(database)
        organisms_check = check_organisms(database)
        if features_check[0] == True and organisms_check[0] == True:
            event, values = sg.Window('Choose', [[sg.T('Choose a language')],[sg.LBox(['de','en'],size=(10,3))],[sg.OK()]]).read(close=True)
            if len(values[0]) > 0:
                lang = values[0][0]
            else:
                lang = 'de'
            formblatt = generate_formblatt(database, lang)
            today = date.today()
            target = os.sep.join([user_data, 'Formblatt-Z' + '_' + user_name + '_' + str(today.strftime("%Y-%m-%d")) + '.xlsx'])

            #formatted
            writer = pd.ExcelWriter(target, engine='xlsxwriter')
            formblatt.to_excel(writer, sheet_name='Sheet1', header=False, index=False, startrow=1)
            # write header
            for colx, value in enumerate(formblatt.columns.values):
                writer.sheets['Sheet1'].write(0, colx, value)

            workbook  = writer.book
            worksheet = writer.sheets['Sheet1']

            footer = 'Formblatt Z, ' + institution
            worksheet.set_footer(footer)
            worksheet.set_landscape()
            worksheet.repeat_rows(0)
            worksheet.set_paper(9)
            worksheet.fit_to_pages(1, 0)  # 1 page wide and as long as necessary.

            header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'align': 'center', 'border': 1, 'bg_color': '#D3D3D3'})
            format = workbook.add_format({'text_wrap': True, 'border': 1})

            for col_num, value in enumerate(formblatt.columns.values):
                worksheet.write(0, col_num, value, header_format)

            worksheet.set_column(0, 0, 4, format)
            worksheet.set_column(1, 1, 30, format)
            worksheet.set_column(2, 2, 12, format)
            worksheet.set_column(3, 3, 16, format)
            worksheet.set_column(4, 4, 9, format)
            worksheet.set_column(5, 5, 13, format)
            worksheet.set_column(6, 6, 28, format)
            worksheet.set_column(7, 7, 25, format)
            worksheet.set_column(8, 8, 15, format)
            worksheet.set_column(9, 9, 5, format)
            worksheet.set_column(10, 10, 9, format)
            worksheet.set_column(11, 11, 15, format)
            worksheet.set_column(12, 12, 13, format)
            worksheet.set_column(13, 13, 10, format)

            writer.close()
            sg.popup('Done.')

### Plasmid list ###
    elif event == '-PLASMIDLIST-':
        plasmidlist = generate_plasmidlist(database)
        today = date.today()
        target = os.sep.join([user_data, 'Plasmidlist' + '_' + user_name + '_' + str(today.strftime("%Y-%m-%d")) + '.xlsx'])
        writer = pd.ExcelWriter(target, engine='xlsxwriter')
        plasmidlist.to_excel(writer, sheet_name='Sheet1', index=False)
        workbook  = writer.book
        header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'align': 'center', 'border': 1, 'bg_color': '#D3D3D3'})
        format = workbook.add_format({'text_wrap': True, 'border': 1})
        worksheet = writer.sheets['Sheet1']
        footer = initials +' Plasmidlist, date: ' + str(today.strftime("%Y-%m-%d"))
        worksheet.set_footer(footer)
        worksheet.set_landscape()
        worksheet.repeat_rows(0)
        worksheet.set_paper(9)
        worksheet.fit_to_pages(1, 0)  # 1 page wide and as long as necessary.

        # format header
        for col_num, value in enumerate(plasmidlist.columns.values):
            worksheet.write(0, col_num, value, header_format)

        worksheet.set_column(0, 0, 6, format)
        worksheet.set_column(1, 1, 14, format)
        worksheet.set_column(2, 2, 60, format)
        worksheet.set_column(3, 3, 6, format)
        worksheet.set_column(4, 4, 14, format)
        worksheet.set_column(5, 5, 60, format)
        worksheet.set_column(6, 6, 60, format)
        worksheet.set_column(7, 7, 10, format)
        worksheet.set_column(8, 8, 10, format)

        writer.close()
        sg.popup('Done.')

### Import data ###
    elif event == '-IMPORTGMOCU-':
        import_data(database, user_data)
        db=ss.Database(database, win,  sql_script=sql_script)
        choices = autocomp(database)
        orga_selection = select_orga(database)
        refresh_autocomp_options()
        win['-FEATURECOMBO-'].Update(values = orga_selection)
        win['-SETSELORGA-'].Update(values = orga_selection)

### Info in settings ###
    elif event == '-SETTINGSINFO-':
        sg.popup(appname + ' ' + str(version_no) + ', ' + vdate)

    elif event == '-CTRL-E-':
        win['Settings.scale'].update(disabled=False)
        win['Settings.font_size'].update(disabled=False)

### Exit ###
    elif event == sg.WIN_CLOSED or event == 'Exit':
        user_name, initials, email, institution, ice, duplicate_gmos, upload_completed, upload_abi, scale, font_size, style, ice_instance, ice_token, ice_token_client, horizontal_layout, filebrowser_instance, filebrowser_user, filebrowser_pwd, use_ice, use_filebrowser, use_gdrive, zip_files, autosync = read_settings(database)
        sg.user_settings_set_entry('-THEME-', style)
        sg.user_settings_set_entry('-SCALE-', float(scale))
        sg.user_settings_set_entry('-FONTSIZE-', int(font_size))
        sg.user_settings_set_entry('-HORIZONTAL-', int(horizontal_layout))
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        active_element = win.FindElementWithFocus()
        if active_element and active_element.key in autocomp_el_keys:
            _autocomplete(event, values)
            # protect editing already synced Features, Organisms
        feature_protection = db['Features']['synced']
        organism_protection = db['Organisms']['synced']
        if feature_protection == 1:
            win['Features.annotation'].update(disabled=True)
            win['Features.alias'].update(disabled=True)
            win['Features.risk'].update(disabled=True)
            win['Features.organism'].update(disabled=True)
        if organism_protection == 1:
            win['Organisms.full_name'].update(disabled=True)
            win['Organisms.short_name'].update(disabled=True)
            win['Organisms.RG'].update(disabled=True)
