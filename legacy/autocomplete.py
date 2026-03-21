"""Autocomplete UI logic for GMOCU."""

import PySimpleGUI as sg
from fuzzywuzzy import process, fuzz


def handler(event, win, active_element):
    """Handle mouse click events on autocomplete tooltip items.
    
    Calculates which option was clicked based on mouse position and updates the combo element.
    
    Args:
        event: The triggering event.
        win: The PySimpleGUI window object.
        active_element: The combo element with an active tooltip.
    """
    num_opt = int((win.mouse_location()[1] - active_element.TooltipObject.tipwindow.winfo_y()) / (active_element.TooltipObject.tipwindow.winfo_height()/len(active_element.Values)))
    active_element.set_focus()
    active_element.Widget.event_generate('<Down>')
    active_element.update(set_to_index=num_opt)


def clear_combo_tooltip(ui_handle: sg.Element) -> None:
    """Clear and hide the tooltip from a combo element.
    
    Args:
        ui_handle: The PySimpleGUI combo element to clear the tooltip from.
    """
    if tt := ui_handle.TooltipObject:
        tt.hidetip()
        ui_handle.TooltipObject = None


def show_combo_tooltip(win, ui_handle: sg.Element, tooltip: list[str], space_ref: sg.Element, text_len: sg.Element, handler_func) -> None:
    """Display an autocomplete tooltip with clickable options below a combo element.
    
    Calculates the maximum width needed for tooltip items and displays them with proper spacing.
    The tooltip is positioned below the combo element and binds click events.
    
    Args:
        win: The PySimpleGUI window object.
        ui_handle: The combo element to attach the tooltip to.
        tooltip: List of string options to display in the tooltip.
        space_ref: Reference element used to calculate space width.
        text_len: Temporary text element used to measure text dimensions.
        handler_func: Callback function to handle click events on tooltip items.
    """
    max_len = 0
    for i in tooltip:
        text_len.update(i)
        win.refresh()
        if text_len.get_size()[0] > max_len:
            max_len = text_len.get_size()[0]
    text_len.update('')
    win.refresh()

    handle_width = ui_handle.get_size()[0]
    space_size = space_ref.get_size()[0]
    space_width = space_size / 10 if space_size is not None else 1
    tooltip_text = "\n".join([i + " "*round((handle_width - max_len)/space_width) for i in tooltip])
    ui_handle.set_tooltip(tooltip_text)
    tt = ui_handle.TooltipObject
    tt.widget.unbind("<Enter>")
    tt.widget.unbind("<Leave>")
    tt.y += 40
    tt.showtip()
    tt.tipwindow.bind('<Button-1>', handler_func)


def autocomplete(event: str, event_data: dict, auto_options: dict, ui_handle: sg.Element,
                 space_ref: sg.Element, text_len: sg.Element, win=None, handler_func=None) -> None:
    """Perform fuzzy autocomplete matching and display results in a tooltip.
    
    Uses fuzzy string matching to find and display autocomplete suggestions as the user types.
    Handles special keys like Tab (complete with first match) and Down arrow.
    
    Args:
        event: The triggering event (keyboard key or event identifier).
        event_data: Dictionary containing event data including current input value.
        auto_options: Dictionary with 'values' (list of possible completions) and 'show_on_empty' (bool).
        ui_handle: The combo element being autocompleted.
        space_ref: Reference element used to calculate space width for tooltip formatting.
        text_len: Temporary text element used to measure text dimensions.
        win: The PySimpleGUI window object (optional).
        handler_func: Callback function to handle click events on tooltip items (optional).
    """
    new_text = event_data[ui_handle.key]
    if new_text == '':
        if auto_options['show_on_empty']:
            sym = auto_options['values']
        else:
            sym = []
    else:
        matches = process.extractBests(new_text, auto_options['values'], scorer=lambda x,y:fuzz.ratio(x,y)+40*y.lower().startswith(x.lower()), score_cutoff=45, limit=10)
        sym = [m[0] for m in matches]
    clear_combo_tooltip(ui_handle=ui_handle)
    ui_handle.update(new_text, values=sym)

    if event == '	' and len(sym):
        ui_handle.update(sym[0])
    elif event == "-DOWNKEY-" or (len(sym) and sym[0] == new_text) or not len(sym) or new_text == '':
        return
    else:
        show_combo_tooltip(win=win, ui_handle=ui_handle, tooltip=sym, space_ref=space_ref, text_len=text_len, handler_func=handler_func)
