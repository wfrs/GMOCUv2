"""GMOCU application constants and OS-specific UI settings."""

import sys

appname = 'GMOCU'
version_no = float(0.73)
vdate = '2025-04-07'
database = 'gmocu.db'

# PySimpleGUI standard font size
os_font_size = 13
os_scale_factor = 1

# Base64 encoded button images
img_base64 = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAABeAAAAXgH42Q/5AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAPtJREFUOI3tkjFKAwEQRd/fDZZCMCcQRFRCCi1SWdmksNDCC1jmAlmt0mRbsbDyAKKQQkstbAVtXG3EIwhpDRi/jcuuWTesvb+bYd5n+DOyTZl0+NzlEzteOymdKTNQL9kk0DUQYHccN28qGyhKFgl0h2l8t0YwaXvQepmeDQpw/3Ue6SoHA9RxeKkoqc800N5FyPv4DFgtrsUy0rn6t7XyDZZWjpE7BTjTFuOFox++aQY6eNoHTmfAmaxuehnZzic+V8kAPtLLiN7jdOJVNYJJu0agHdAQpeu5AeyWQEOkt6wMtwt/oChZR7r/Fbc3HDcf8q3CH/xV/wbwBe0pVw+ecPjyAAAAAElFTkSuQmCC'
img2_base64 = b'iVBORw0KGgoAAAANSUhEUgAAAA8AAAAUCAYAAABSx2cSAAAACXBIWXMAAAJhAAACYQHBMFX6AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAOhJREFUOI3tz79OwlAUx/HvJTe1gW5iOqohcZHJuLv6Gs6uLvgADsbFGGZeQx+ADafqoEhiY4wabUyg/PFAexl0acCLneU3npzPOfkpaoEhT8RZM2dbHwAawNWKyqpjNeHnmFjSzEwDbPsurcOKFe83Hrlqx7MYIBokrJ/e/YpHk592KxKq4xuTwcZAX1JcrfA9Pf/Cd4ovvQmSGGa29jZLXB5sWCvs1jtcPw8pWLcWZIn/EQ5eR+xcPOTGGuhLYnjqjhVQzIXNSdUDUEf3ZRx5z/s5k2Y4oHretqJOJPNxLCm3b19/+jwFyitLV/vbA1oAAAAASUVORK5CYII='


def get_ui_constants(horizontal_layout):
    """Return OS-specific UI constants based on platform and layout mode."""
    headings = [' ID ', '  Name  ', '                     Alias                       ', '  Status  ', 'G ']
    features_headings = ['ID   ', '   Annotation    ', '                 Alias                 ', '   Risk   ', 'Organism']
    organisms_headings = ['ID   ', '                  Full name                    ', '      Short name     ', 'RG    ']
    alias_length = 59
    plasmid_titles_size = 14
    features_titles_size = 15

    if horizontal_layout == 0:
        plasmid_table_rows = 12
        features_table_rows = 38
        organisms_table_rows = 40
        plasmid_summary_lines = 4
        plasmid_purpose_lines = 4
    else:
        plasmid_table_rows = 47
        features_table_rows = 40
        organisms_table_rows = 42
        plasmid_summary_lines = 8
        plasmid_purpose_lines = 5

    if sys.platform == "win32":
        headings = ['ID', ' Name ', '            Alias            ', 'Status', 'G ']
        features_headings = ['ID ', 'Annotation', '        Alias        ', 'Risk', 'Organism']
        organisms_headings = ['ID', '           Full name          ', 'Short name ', 'RG']
        alias_length = 59
        plasmid_titles_size = 14
        features_titles_size = 15
        if horizontal_layout == 1:
            plasmid_table_rows = 40
            features_table_rows = 33
            organisms_table_rows = 35
            plasmid_summary_lines = 5
            plasmid_purpose_lines = 3

    elif sys.platform.startswith("linux"):
        headings = ['ID', '       Name       ', '                                                      Alias                                                    ', '        Status        ', ' G   ']
        features_headings = ['ID ', '         Annotation               ', '                                        Alias                                      ', '       Risk       ', '     Organism         ']
        organisms_headings = ['ID', '                                                          Full name                                                       ', '   Short name             ', ' RG      ']
        plasmid_titles_size = 16
        features_titles_size = 17
        alias_length = 57
        if horizontal_layout == 1:
            plasmid_table_rows = 40
            features_table_rows = 35
            organisms_table_rows = 36
            plasmid_summary_lines = 6
            plasmid_purpose_lines = 5

    return {
        'headings': headings,
        'features_headings': features_headings,
        'organisms_headings': organisms_headings,
        'alias_length': alias_length,
        'plasmid_titles_size': plasmid_titles_size,
        'features_titles_size': features_titles_size,
        'plasmid_table_rows': plasmid_table_rows,
        'features_table_rows': features_table_rows,
        'organisms_table_rows': organisms_table_rows,
        'plasmid_summary_lines': plasmid_summary_lines,
        'plasmid_purpose_lines': plasmid_purpose_lines,
    }
