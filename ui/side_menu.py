"""
ui/side_menu.py -- the dark side menu that stands in for the notebook's tab strip (new look N2).

Appearance and navigation only. No data, no files, no print. The rows are tk.Labels, so they never take keyboard focus
and the scanner's box keeps it. A click goes to MainWindow._on_side_menu_click, which shows the page and moves the
keyboard focus there as a click on the old tab did; select() is the code path and moves no focus. The highlight
follows the notebook (MainWindow._on_tab_changed calls highlight), so a click and a select from code look the same.
Design: work\\n2\\N2_DESIGN_FABLE_2026-10-19.md section 2, as amended by work\\n2\\addendum\\ (sections A and E.3).
"""

import tkinter as tk
import tkinter.font as tkfont

from ui import theme
from ui.design_system import HOUSE

# Tab index of each row, top to bottom; None is a separator (design D1).
# Tabs: Students 0, Items 1, Books 2, Attendance 3, Roster 4, Schedule 5, Lessons 6, System 7, Admin Log 8, Dev Login 9.
ENTRIES = (3, 0, 2, 1, None, 4, 5, None, 6, 7, None, 8, 9)

WIDTH = 220        # px at 96 DPI, through theme.scale()
ROW_HEIGHT = 36    # the menu fits the un-maximised window at every scaling (N2 addendum E.3)
BAR_WIDTH = 3
WHITE = "#FFFFFF"


def _line_colour():
    return theme._mix(HOUSE["side"], HOUSE["side_text"], 0.2)


def _separator(parent):
    line = tk.Frame(parent, bg=_line_colour(), height=1, takefocus=0)
    line.pack(side=tk.TOP, fill=tk.X, padx=theme.scale(14), pady=theme.scale(4))
    return line


def _row(parent, on_click, is_active, text=""):
    """One row: a narrow accent bar and a Label. Returns (bar, label)."""
    side = HOUSE["side"]
    frame = tk.Frame(parent, bg=side, takefocus=0)
    frame.pack(side=tk.TOP, fill=tk.X)
    bar = tk.Frame(frame, bg=side, width=theme.scale(BAR_WIDTH), takefocus=0)
    bar.pack(side=tk.LEFT, fill=tk.Y)
    font = theme.font(10)
    # Tall enough for Thai tone marks in either weight (View -> Thai), and never under ROW_HEIGHT.
    linespace = max(tkfont.Font(root=parent, font=f).metrics("linespace") for f in (font, theme.font(10, bold=True)))
    pady = max(0, (theme.scale(ROW_HEIGHT) - linespace + 1) // 2)
    label = tk.Label(frame, text=text, anchor="w", bg=side, fg=HOUSE["side_text"], font=font,
                     padx=theme.scale(16), pady=pady, bd=0, highlightthickness=0, takefocus=0)
    label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    label.bind("<Button-1>", lambda e: on_click())
    label.bind("<Enter>", lambda e: label.config(bg=HOUSE["side_active"]))
    label.bind("<Leave>", lambda e: label.config(bg=HOUSE["side_active"] if is_active() else side))
    return bar, label


def build_panel(window):
    """The dark panel down the left of the main window: the title at the top and the action rows at the bottom.
    The SideMenu rows go in between (MainWindow._build_side_menu). Returns the panel."""
    side = HOUSE["side"]
    panel = tk.Frame(window, bg=side, width=theme.scale(WIDTH), takefocus=0)
    panel.pack(side=tk.LEFT, fill=tk.Y)
    panel.pack_propagate(False)              # the content never widens the panel

    panel.title_label = tk.Label(panel, text="NestMind", anchor="w", bg=side, fg=WHITE,
                                 font=theme.font(14, bold=True), takefocus=0)
    panel.title_label.pack(side=tk.TOP, fill=tk.X, padx=(theme.scale(22), 0), pady=(theme.scale(14), 0))
    panel.subtitle_label = tk.Label(panel, text="Siri English", anchor="w", bg=side, fg=HOUSE["side_text"],
                                    font=theme.font(9), takefocus=0)
    panel.subtitle_label.pack(side=tk.TOP, fill=tk.X, padx=(theme.scale(22), 0), pady=(0, theme.scale(12)))

    bottom = tk.Frame(panel, bg=side, takefocus=0)
    bottom.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, theme.scale(8)))
    tk.Frame(panel, bg=_line_colour(), height=1, takefocus=0).pack(
        side=tk.BOTTOM, fill=tk.X, padx=theme.scale(14), pady=(0, theme.scale(6)))

    # The footer's two buttons and File -> Logout, as rows. Looked up at click time, so a later patch is honoured.
    panel.bottom_rows = {}
    for name, text, handler in (("tutorials", "📚 Tutorials", "open_tutorials"),
                                ("settings", "⚙ Settings", "on_change_passwords"),
                                ("logout", "Log out", "on_logout")):
        _bar, label = _row(bottom, lambda h=handler: getattr(window, h)(), lambda: False, text)
        panel.bottom_rows[name] = label
    return panel


class SideMenu(tk.Frame):
    """The ten page rows. Reads the notebook through the window each time (set_language builds a new one)."""

    def __init__(self, parent, window, entries=ENTRIES):
        super().__init__(parent, bg=HOUSE["side"], takefocus=0)
        self.window = window
        self.order = []
        self.rows = {}
        self.bars = {}
        self.separators = []
        self._active = None
        for index in entries:
            if index is None:
                self.separators.append(_separator(self))
                continue
            bar, label = _row(self, lambda i=index: self.window._on_side_menu_click(i),
                              lambda i=index: self._active == i)
            self.order.append(index)
            self.rows[index] = label
            self.bars[index] = bar

    def refresh(self):
        """Re-read every label from the current notebook (it follows View -> Thai) and re-mark the current tab."""
        for index, label in self.rows.items():
            label.config(text=self.window.notebook.tab(index, "text"))
        self.highlight(self.window.notebook.index("current"))

    def highlight(self, index):
        """Mark the row of tab `index`: dark band, accent bar, white bold text."""
        self._active = index
        for i, label in self.rows.items():
            on = i == index
            label.config(bg=HOUSE["side_active"] if on else HOUSE["side"], fg=WHITE if on else HOUSE["side_text"],
                         font=theme.font(10, bold=on))
            self.bars[i].config(bg=HOUSE["accent"] if on else HOUSE["side"])

    def select(self, index):
        """Show tab `index` (code and tests; a user's click goes to MainWindow._on_side_menu_click). The current tab is
        left alone; nothing else is touched."""
        if self.window.notebook.index("current") == index:
            return
        self.window.notebook.select(index)
