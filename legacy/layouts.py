"""GUI layout definitions for GMOCU."""

import PySimpleGUI as sg
import pysimplesqlmod as ss


def build_layout(ui, horizontal_layout, orga_selection, img_base64, img2_base64):
    """Build and return the complete application layout.

    Args:
        ui: Dict of UI constants from get_ui_constants().
        horizontal_layout: 0 for vertical, 1 for horizontal layout.
        orga_selection: List of organism short names for combo boxes.
        img_base64: Base64 encoded image for add feature button.
        img2_base64: Base64 encoded image for duplicate button.

    Returns:
        The complete layout list for the main window.
    """
    headings = ui['headings']
    features_headings = ui['features_headings']
    organisms_headings = ui['organisms_headings']
    alias_length = ui['alias_length']
    plasmid_titles_size = ui['plasmid_titles_size']
    features_titles_size = ui['features_titles_size']
    plasmid_table_rows = ui['plasmid_table_rows']
    features_table_rows = ui['features_table_rows']
    organisms_table_rows = ui['organisms_table_rows']
    plasmid_summary_lines = ui['plasmid_summary_lines']
    plasmid_purpose_lines = ui['plasmid_purpose_lines']

    ##### Plasmid data #####
    visible = [0, 1, 1, 1, 1]

    record_columns = [
        [sg.Column([
            [sg.Text('Plasmid name:', size=(plasmid_titles_size, 1))],
            [sg.Text('          ', key='-SPACEREF-')],
            [sg.Text('', key='-TEXTLEN-')]
        ], vertical_alignment='top', pad=(0, 0))] +
        [sg.Column([
            ss.record('Plasmids.name', no_label=True, size=(35, 10)) +
            [sg.T("Clone:")] +
            ss.record('Plasmids.clone', no_label=True, size=(5, 10)) +
            ss.record('Plasmids.gb', no_label=True, visible=False, size=(0, 10)) +
            ss.record('Plasmids.date', no_label=True, readonly=True, size=(10, 10)),
            ss.selector('cassettesSelector', 'Cassettes', size=(61, 4)),
        ], pad=(0, 0))],
        [sg.Column([
            [sg.Text('Cassette:', size=(plasmid_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        [sg.Column([
            ss.record('Cassettes.content', no_label=True, size=(46, 10),) +
            [sg.Button('!', key='-info-', size=(1, 1)),] +
            ss.actions('cassettesActions', 'Cassettes', edit_protect=False, navigation=False, save=True, search=False),
        ], pad=(0, 0))],
        # autocomplete
        [sg.Column([
            [sg.Text('Add Feature:', size=(plasmid_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        [sg.Column([
            [sg.Combo(size=(25, 1), enable_events=True, key='-AIN-', values=[], disabled=True)] +
            [sg.Text('Variant:')] +
            [sg.Input(size=(20, 1), key='-VARIANT-', disabled=True)] +
            [sg.Button(' ', image_data=img_base64, button_color=(sg.theme_background_color(), sg.theme_background_color()), key='-ADDFEATURE-')],
        ], pad=(0, 0))],
        [sg.Column([
            [sg.Text('Alias:', size=(plasmid_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        ss.record('Plasmids.alias', no_label=True, size=(alias_length, 10)) + [sg.Button('+', key='-ALIAS_IN-', size=(1, 1)),],
        [sg.Column([
            [sg.Text('Purpose:', size=(plasmid_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        ss.record('Plasmids.purpose', sg.MLine, (61, plasmid_purpose_lines), no_label=True),
        [sg.Column([
            [sg.Text('Cloning summary:', size=(plasmid_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        ss.record('Plasmids.summary', sg.MLine, (61, plasmid_summary_lines), no_label=True),
        [sg.Column([
            [sg.Text('Orig. vector:', size=(plasmid_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        ss.record('Plasmids.backbone_vector', no_label=True, size=(29, 10)) +
        [sg.Text('Status:', pad=(1, 0), justification='center')] + ss.record('Plasmids.status', no_label=True, element=sg.Combo, quick_editor=False, size=(18, 10)) +
        ss.actions('plasmidActions', 'Plasmids', edit_protect=False, navigation=False, save=True, search=False, insert=False, delete=False),

        [sg.Column([
            [sg.Text('GMOs:', size=(plasmid_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        ss.selector('gmoSelector', 'GMOs', size=(61, 5)),
        [sg.Column([
            [sg.Text('Organism selector:', size=(plasmid_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        [sg.Column([
            ss.record('Plasmids.organism_selector', element=sg.Combo, quick_editor=False, no_label=True, size=(24, 10),) +
            [sg.T('Target RG:'),] +
            ss.record('Plasmids.target_RG', size=(3, 10), no_label=True) +
            [sg.T('Approval: '),] + [sg.Input('-', size=(9, 10), key='-APPROVAL-')],
            [sg.T('Made / Destroyed:'),] + ss.record('Plasmids.generated', size=(10, 10), no_label=True) +
            ss.record('Plasmids.destroyed', size=(10, 10), no_label=True) +
            [sg.Button('Add', key='-ADDORGA-', size=(3, 1)),] +
            [sg.Button(':)', key='-ADDFAV-', size=(1, 1)),] +
            ss.actions('GMOActions', 'GMOs', edit_protect=False, navigation=False, save=False, search=False, insert=False) +
            [sg.Button('Destroy', key='-DESTROYORGA-', size=(6, 1)),],
        ], pad=(0, 0))],
    ]

    selectors = [
        ss.actions('plasmidActions', 'Plasmids', search_size=(27, 1)) + [sg.Button('', image_data=img2_base64, button_color=(sg.theme_background_color(), sg.theme_background_color()), key='-DUPLICATE-')] +
        [sg.Button('UP', key='-THISICE-', size=(3, 1)),],
        ss.selector('tableSelector', 'Plasmids', element=sg.Table, headings=headings, visible_column_map=visible, num_rows=plasmid_table_rows),
    ]

    sub_genebank = [
        [sg.Text(size=(plasmid_titles_size - 1, 1))] +
        ss.record('Plasmids.gb_name', no_label=True, size=(42, 10)) +
        [sg.Col([[sg.Button('+', key='insGb', size=(1, 1))]], element_justification="center", key='-GENEBANKCOL-')] +
        [sg.Button('Download', key='-down_gb-', size=(8, 1))] +
        ss.record('Plasmids.genebank', no_label=True, size=(1, 10)),
    ]

    tablayout_attach = [
        [sg.T(size=(plasmid_titles_size - 1, 1))] +
        ss.selector('attachmentSelector', 'Attachments', size=(39, 4)) +
        [sg.Col([], size=(0, 0), element_justification="center", vertical_alignment="center", key='-ATTACHCOL-')] +
        [sg.Button('+', key='insElement', size=(1, 1))] +
        ss.actions('attachmentActions', 'Attachments', edit_protect=False, navigation=False, save=False, search=False, insert=False) +
        [sg.Button('Download', key='-down_att-', size=(8, 1))]
    ]

    record_columns += [[sg.Frame('Genebank', sub_genebank, key='-GENEBANKFRAME-')]]
    record_columns += [[sg.Frame('Attachments', tablayout_attach, key='-ATTACHFRAME-')]]

    if horizontal_layout == 0:
        tablayout_plasmid = selectors + record_columns
    else:
        tablayout_plasmid = [[sg.Column(selectors, vertical_alignment='top'), sg.VSeparator(), sg.Column(record_columns, vertical_alignment='center')]]

    ##### GMO #####
    tablayout_GMO = [
        [sg.Text('Maintenance')],
        [sg.Button('Run', key='-CHECKFEATURES-'),] + [sg.Text('Check Nucleic acid feature glossary completeness')],
        [sg.Button('Run', key='-CHECKORGANISMS-'),] + [sg.Text('Check Organisms glossary completeness')],
        [sg.Button('Run', key='-CHECKPLASMIDS-'),] + [sg.Text('Check for plasmid duplications and completeness')],
        [sg.Text('')],
        [sg.Text('JBEI/ice, Filebrowser, GDrive')],
        [sg.Button('Run', key='-SERVERS-')] + [sg.Text('Upload/update all plasmid information, gb files to JBEI/ice, and with attachements to\nGDrive, Filebrowser server, as configured.')] + [sg.CB('Only new plasmids', default=False, k='-ONLYNEW-', visible=False)],
        [sg.Text('')],
        [sg.Text('GMO')],
        [sg.Button('Run', key='-PLASMIDLIST-'),] + [sg.Text('Generate plasmid list')],
        [sg.Button('Run', key='-FORMBLATT-'),] + [sg.Text('Generate Formblatt Z')],
        [sg.Text('')],
        [sg.Text('Data import')],
        [sg.Button('Run', key='-IMPORTGMOCU-'),] + [sg.Text('Import data from another gmocu database file')],
    ]

    ##### Features #####
    tablayout_Features = [
        ss.selector('featureSelector', 'Features', element=sg.Table, headings=features_headings, visible_column_map=[0, 1, 1, 1, 1], num_rows=features_table_rows),
        ss.actions('featureActions', 'Features'),
        [sg.Column([
            [sg.Text('Annotation:', size=(features_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        ss.record('Features.annotation', no_label=True, enable_events=True, size=(62, 10)),
        [sg.Column([
            [sg.Text('Alias:', size=(features_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        ss.record('Features.alias', no_label=True, size=(62, 10)),
        [sg.Column([
            [sg.Text('Risk:', size=(features_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        ss.record('Features.risk', no_label=True, size=(62, 10)),
        [sg.Column([
            [sg.Text('Organism:', size=(features_titles_size, 1))]
        ], vertical_alignment='top', pad=(0, 0))] +
        [sg.Combo(orga_selection, size=(26, 10), enable_events=True, key='-FEATURECOMBO-')] +
        ss.record('Features.organism', no_label=True, size=(32, 10))]

    tablayout_Features_controls = [
        [sg.Button('Export all to Excel', key='-ALLEXCEL-')] +
        [sg.Button('Export used to Excel', key='-USEDEXCEL-')] +
        [sg.Button('Import from Excel', key='-ADDFEATURESEXCEL-')] +
        [sg.Button('Online sync', key='-FEATURESYNC-')] +
        [sg.Button('!', key='-FEATUREINFO-')],
    ]
    if horizontal_layout == 0:
        tablayout_Features += tablayout_Features_controls
    else:
        tablayout_Features = [[sg.Column(tablayout_Features, vertical_alignment='top'), sg.VSeparator(), sg.Column(tablayout_Features_controls, vertical_alignment='top')]]

    ##### Organisms #####
    tablayout_Organisms = [
        ss.selector('organismSelector', 'Organisms', element=sg.Table, headings=organisms_headings, visible_column_map=[0, 1, 1, 1], num_rows=organisms_table_rows),
        ss.actions('organismActions', 'Organisms'),
        ss.record('Organisms.full_name', label='Full name:', size=(62, 10)),
        ss.record('Organisms.short_name', label='Short name:', size=(62, 10)),
        ss.record('Organisms.RG', label='RG:', size=(62, 10))]
    tablayout_Organisms_controls = [
        [sg.Button('Export all to Excel', key='-ALLEXCELORGA-')] +
        [sg.Button('Export used to Excel', key='-USEDEXCELORGA-')] +
        [sg.Button('Import from Excel', key='-ADDEXCELORGA-')] +
        [sg.Button('Online sync', key='-ORGASYNC-')],
    ]
    if horizontal_layout == 0:
        tablayout_Organisms += tablayout_Organisms_controls
    else:
        tablayout_Organisms = [[sg.Column(tablayout_Organisms, vertical_alignment='top'), sg.VSeparator(), sg.Column(tablayout_Organisms_controls, vertical_alignment='top')]]

    ##### Settings #####
    tablayout_Settings_1 = [
        ss.record('Settings.name', label='Name:', size=(62, 10)),
        ss.record('Settings.initials', label='Initials:', size=(62, 10)),
        ss.record('Settings.email', label='Email:', size=(62, 10)),
        ss.record('Settings.institution', label='GMO institute:', size=(62, 10)),
        ss.record('Settings.ice', label='Server credentials:', element=sg.Combo, size=(56, 10)),
        ss.record('Settings.gdrive_glossary', label='GDrive Sheet ID:', size=(62, 10)),
        ss.record('Settings.gdrive_id', label='GDrive Folder ID:', size=(62, 10)),
        [sg.Text("Style*:                   ")] + [sg.Col([[sg.Combo(['Reddit', 'DarkBlack', 'Black', 'BlueMono', 'BrownBlue', 'DarkBlue', 'LightBlue', 'LightGrey6'], default_value=sg.user_settings_get_entry('-THEME-', 'Reddit'), size=(60, 10), enable_events=True, key='-SETSTYLE-')]], vertical_alignment='t')],
        ss.record('Settings.style', no_label=True, size=(29, 10)),
    ]

    tablayout_Settings_2 = [
        ss.record('Settings.scale', label='Scale factor*:', size=(62, 10)),
        ss.record('Settings.font_size', label='Font size*:', size=(62, 10)),
        [sg.Col([
            ss.record('Settings.horizontal_layout', label='Horizontal layout*:', element=sg.CBox, size=(1, 1)),
            ss.record('Settings.duplicate_gmos', label='Duplicate GMOs:', element=sg.CBox, size=(1, 1)),
            ss.record('Settings.upload_completed', label='Upload completed:', element=sg.CBox, size=(1, 1)),
            ss.record('Settings.autosync', label='Autosync GSheets:', element=sg.CBox, size=(1, 1))
        ], pad=(0, 0), expand_x=True)] +
        [sg.Col([
            ss.record('Settings.use_ice', label='Use JEBI/ice:', element=sg.CBox, size=(1, 1)),
            ss.record('Settings.use_filebrowser', label='Use Filebrowser:', element=sg.CBox, size=(1, 1)),
            ss.record('Settings.use_gdrive', label='Use GDrive Folder:', element=sg.CBox, size=(1, 1)),
            ss.record('Settings.zip_files', label='    Zip files (faster):', element=sg.CBox, size=(1, 1))
        ], pad=(0, 0), expand_x=True)],
        [sg.Text('If both JBEI/ice and Filebrowser are used, a link to the Filebrowser folder will be added to each\n JBEI/ice entry.')],
        [sg.Text('*Restart required')],
    ]

    tablayout_Settings_TargetOrganisms = [
        [sg.Text('Target organisms: ')] +
        [sg.Col([ss.selector('organismselectionSelector', 'OrganismSelection', size=(60, 7)),
        [sg.Combo(orga_selection, size=(30, 10), enable_events=True, key='-SETSELORGA-')] +
        [sg.Button('Add', key='-ADDSELORGA-')] +
        ss.actions('organismselectionActions', 'OrganismSelection', edit_protect=False, navigation=False, save=False, search=False, insert=False)], vertical_alignment='t')],
    ]

    tablayout_Settings_FavOrganisms = [
        [sg.Text('Fav. organisms:    ')] +
        [sg.Col([ss.selector('favouritesSelector', 'OrganismFavourites', size=(60, 6)),
        [sg.Button('Copy', key='-COPYFAVORGA-')] +
        ss.actions('favouritesselectionActions', 'OrganismFavourites', edit_protect=False, navigation=False, save=False, search=False, insert=False)], vertical_alignment='t')],
        [sg.Text('                                  All listed organisms must also exist in Target organisms.')],
    ]

    if horizontal_layout == 0:
        tablayout_Settings = [ss.actions('settingsActions', 'Settings', edit_protect=True, navigation=False, save=True, search=False, insert=False, delete=False) + [sg.Button('Info', key='-SETTINGSINFO-'),] + ss.record('Settings.version', no_label=True, readonly=True, visible=False, size=(0, 0))] + tablayout_Settings_1 + tablayout_Settings_2 + tablayout_Settings_TargetOrganisms + tablayout_Settings_FavOrganisms
    else:
        tablayout_Settings = [
            ss.actions('settingsActions', 'Settings', edit_protect=True, navigation=False, save=True, search=False, insert=False, delete=False) + [sg.Button('Info', key='-SETTINGSINFO-'),] + ss.record('Settings.version', no_label=True, readonly=True, visible=False, size=(0, 0)),
            [sg.Column(tablayout_Settings_1, vertical_alignment='top')] + [sg.Column(tablayout_Settings_2, vertical_alignment='top')],
            [sg.Column(tablayout_Settings_TargetOrganisms, vertical_alignment='top')] + [sg.Column(tablayout_Settings_FavOrganisms, vertical_alignment='top')],
        ]

    ##### Tabs #####
    layout = [[sg.TabGroup([[sg.Tab('Plasmid data', tablayout_plasmid, key='-pldata-'),
                             sg.Tab('GMO', tablayout_GMO),
                             sg.Tab('Nucleic acids', tablayout_Features),
                             sg.Tab('Organisms', tablayout_Organisms),
                             sg.Tab('Settings', tablayout_Settings),
                             ]], key='-tabs-', tab_location='top', selected_title_color='purple')],
                             ]

    return layout
