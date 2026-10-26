"""
Design System for Siri English School Management System

This module centralizes all visual design constants including colors, fonts,
spacing, and theme definitions. Based on the student portal mockup design.

Created: November 28, 2025
"""

# ============================================================================
# COLOR PALETTE
# ============================================================================

COLORS = {
    # Primary Brand Colors
    'primary': '#2c3e50',           # Dark blue-gray (headers, primary actions)
    'secondary': '#3498db',         # Light blue (secondary actions, links)

    # Status Colors
    'success': '#27ae60',           # Green (success states, confirmations)
    'danger': '#e74c3c',            # Red (errors, deletions, warnings)
    'warning': '#f39c12',           # Orange (warnings, alerts)
    'info': '#3498db',              # Blue (informational messages)

    # Accent Colors (from mockup)
    'accent': '#FFFF00',            # Bright yellow (schedule highlights, focus)
    'accent_muted': '#FFE700',      # Slightly darker yellow (hover states)
    'purple': '#9b59b6',            # Purple (special actions)
    'pink': '#e75480',              # Pink (special categories)

    # Neutral Colors
    'light': '#ecf0f1',             # Light gray (backgrounds)
    'dark': '#34495e',              # Dark gray (text, borders)
    'white': '#ffffff',             # White (backgrounds, text on dark)
    'black': '#000000',             # Black (text, grid lines)

    # Grid & Table Colors
    'grid_border': '#000000',       # Black (grid lines)
    'grid_bg': '#ffffff',           # White (primary grid background)
    'grid_bg_alt': '#D3D3D3',       # Light gray (alternate rows)
    'grid_header': '#2c3e50',       # Dark blue-gray (header backgrounds)
}

# ============================================================================
# THEME DEFINITIONS
# ============================================================================

LIGHT_THEME = {
    "bg": "#ffffff",                # White background
    "fg": "#000000",                # Black text
    "selectbg": "#0078d7",          # Windows blue selection
    "selectfg": "#ffffff",          # White selected text
    "accent_bg": "#FFFF00",         # Yellow highlights
    "accent_fg": "#000000",         # Black text on yellow
    "header_bg": "#2c3e50",         # Dark blue-gray headers
    "header_fg": "#ffffff",         # White text on headers
    "grid_border": "#000000",       # Black grid lines
    "grid_alt": "#D3D3D3",          # Light gray alternate rows
}

DARK_THEME = {
    "bg": "#2d2d2d",                # Dark gray background
    "fg": "#e0e0e0",                # Light gray text
    "selectbg": "#0078d7",          # Windows blue selection
    "selectfg": "#ffffff",          # White selected text
    "accent_bg": "#FFE700",         # Slightly muted yellow for dark mode
    "accent_fg": "#000000",         # Black text on yellow
    "header_bg": "#1a252f",         # Darker blue-gray headers
    "header_fg": "#e0e0e0",         # Light gray text on headers
    "grid_border": "#555555",       # Gray grid lines
    "grid_alt": "#3a3a3a",          # Slightly lighter gray alternate rows
}

# ============================================================================
# TYPOGRAPHY
# ============================================================================

FONTS = {
    'title': ('Arial', 16, 'bold'),         # Main window titles
    'header': ('Arial', 14, 'bold'),        # Section headers
    'subheader': ('Arial', 12, 'bold'),     # Subsection headers
    'section': ('Arial', 10, 'bold'),       # Section labels
    'body': ('Arial', 9),                   # Body text, buttons
    'body_bold': ('Arial', 9, 'bold'),      # Bold labels
    'small': ('Arial', 8),                  # Small text, captions
}

# ============================================================================
# SPACING & SIZING
# ============================================================================

SPACING = {
    'xs': 2,        # Extra small padding
    'sm': 5,        # Small padding
    'md': 10,       # Medium padding (default)
    'lg': 15,       # Large padding
    'xl': 20,       # Extra large padding
}

BUTTON_SIZES = {
    'small': {'width': 10, 'padding': 5},
    'medium': {'width': 15, 'padding': 8},
    'large': {'width': 20, 'padding': 10},
}

# ============================================================================
# BUTTON COLOR MAPPINGS
# ============================================================================

BUTTON_STYLES = {
    'primary': {
        'bg': COLORS['primary'],
        'fg': COLORS['white'],
        'active_bg': '#34495e',
    },
    'success': {
        'bg': COLORS['success'],
        'fg': COLORS['white'],
        'active_bg': '#229954',
    },
    'danger': {
        'bg': COLORS['danger'],
        'fg': COLORS['white'],
        'active_bg': '#c0392b',
    },
    'warning': {
        'bg': COLORS['warning'],
        'fg': COLORS['white'],
        'active_bg': '#d68910',
    },
    'secondary': {
        'bg': COLORS['secondary'],
        'fg': COLORS['white'],
        'active_bg': '#2980b9',
    },
    'purple': {
        'bg': COLORS['purple'],
        'fg': COLORS['white'],
        'active_bg': '#8e44ad',
    },
    'pink': {
        'bg': COLORS['pink'],
        'fg': COLORS['white'],
        'active_bg': '#d63865',
    },
    'light': {
        'bg': COLORS['light'],
        'fg': COLORS['dark'],
        'active_bg': '#d5dbdb',
    },
}

# ============================================================================
# SCHEDULE SPECIFIC COLORS (from mockup students2.png)
# ============================================================================

SCHEDULE_COLORS = {
    'highlight': '#FFFF00',         # Bright yellow for current/selected day
    'grid_border': '#000000',       # Black grid lines
    'header_bg': '#D3D3D3',         # Light gray header background
    'cell_bg': '#ffffff',           # White cell background
    'cell_alt_bg': '#F5F5F5',       # Very light gray alternate
    'time_column_bg': '#E8E8E8',    # Light gray for time column
    'text': '#000000',              # Black text
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_button_style(style_name):
    """
    Get button styling configuration by name.

    Args:
        style_name (str): One of 'primary', 'success', 'danger', 'warning',
                         'secondary', 'purple', 'pink', 'light'

    Returns:
        dict: Button style configuration with bg, fg, active_bg keys
    """
    return BUTTON_STYLES.get(style_name, BUTTON_STYLES['primary'])

def get_theme_colors(dark_mode=False):
    """
    Get theme colors based on current mode.

    Args:
        dark_mode (bool): True for dark theme, False for light theme

    Returns:
        dict: Theme color configuration
    """
    return DARK_THEME if dark_mode else LIGHT_THEME


# ============================================================================
# HOUSE PALETTE  (added by the UI modernisation pilot, 2026-09-19)
# ============================================================================
#
# Single source of truth for the house style. The constants above are left
# untouched; they are not the house palette.
#
# New look N1 (2026-10-14): the palette of the chosen design
# (work\newlook\R2_dark_side_menu.html). Status mapping, which carries
# meaning and must survive any restyle:
#     RUNNING / UP / Start  -> primary  #0F6E66
#     STOPPED / DOWN / Stop -> danger   #B02020
#     warnings              -> warning  #F59221  (not the teal accent)
#
# Contrast (WCAG 2.1):
#     white on #0F6E66  6.1:1  ok
#     white on #B02020  6.8:1  ok
#     #F59221  2.3:1 against white: FAILS as text, and white on it fails
#              too -- use ink (#1B2228 on #F59221 is 6.9:1)
#     #FED600  fill only, never text and never thin lines

HOUSE = {
    'primary':        '#0F6E66',   # teal   -- RUNNING/UP/Start, primary buttons
    'primary_dark':   '#0A4F49',   # pressed primary; dark teal text on soft teal
    'accent':         '#5FC4B8',   # light teal -- the active-row mark; text on dark bands
    'warning':        '#F59221',   # orange -- warnings
    'warning_active': '#DD8019',   # pressed warning
    'fill_only':      '#FED600',   # yellow -- fills only
    'danger':         '#B02020',   # deep red -- STOPPED/DOWN/Stop, deletes
    'danger_active':  '#8E1A1A',   # pressed danger
    'panel':          '#FFFFFF',   # panels are white cards
    'card':           '#FFFFFF',   # cards, lists, secondary buttons
    'ground':         '#F4F6F6',   # page ground
    'ink':            '#1B2228',   # body text
    'ink_muted':      '#56616B',   # secondary text, disabled
    'line':           '#E1E4E7',   # hairlines, card borders
    'btn_secondary':        '#E1E4E7',   # secondary button fill: shows on white and on ground
    'btn_secondary_active': '#C5CCD2',   # pressed secondary button
    # Disabled button text per kind, about 3:1 or better on its fill (n1fix1):
    'primary_disabled':   '#9FC5C2',   # 3.26:1 on primary
    'secondary_disabled': '#74797E',   # 3.44:1 on btn_secondary
    'warning_disabled':   '#724F25',   # 3.15:1 on warning
    'danger_disabled':    '#DFA6A6',   # 3.30:1 on danger
    'side':           '#123B37',   # dark band: side menu, header bars
    'side_text':      '#C9DBD8',   # text on the dark band
    'side_active':    '#2A4F4A',   # active side-menu row (Tk has no rgba)
    'notice_bg':      '#FBE3B8',   # pale amber notice box
    'notice_ink':     '#6B3D00',   # text on the notice box
    'tag_now_bg':       '#0F6E66', 'tag_now_fg':       '#FFFFFF',
    'tag_next_bg':      '#EEF1F4', 'tag_next_fg':      '#2F3A43',
    'tag_cancelled_bg': '#FDE7E4', 'tag_cancelled_fg': '#9B1C12',
    'tag_soft_bg':      '#E4F1EF', 'tag_soft_fg':      '#0A4F49',
}

# The System tab's colour map, in both modes. ui/theme.py picks between them
# from the PORTAL_THEME env var; system_tab.py no longer declares its own.

SYSTEM_COLORS_CLASSIC = {
    'primary':   '#2c3e50',
    'secondary': '#3498db',
    'success':   '#27ae60',
    'danger':    '#e74c3c',
    'warning':   '#f39c12',
    'light':     '#ecf0f1',
    'dark':      '#34495e',
    'white':     '#ffffff',
    'ink':       'black',
}

SYSTEM_COLORS_HOUSE = {
    'primary':   HOUSE['primary'],
    'secondary': HOUSE['ink_muted'],
    'success':   HOUSE['primary'],
    'danger':    HOUSE['danger'],
    'warning':   HOUSE['warning'],
    'light':     HOUSE['panel'],
    'dark':      HOUSE['primary_dark'],   # darker teal, for the header's own controls
    'white':     HOUSE['ground'],
    'ink':       HOUSE['ink'],
}
