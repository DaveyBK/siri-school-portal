"""
Roster Tab Module — Two-panel class roster management UI.

Left panel:  Day-grouped class cards (scrollable)
Right panel: Student roster for selected class (Treeview) + add/remove controls
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
import sqlite3
from datetime import date, timedelta
from ui import design_system as ds, theme


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _long(iso):
    """'2026-10-05' -> 'Mon 5 Oct 2026'."""
    d = date.fromisoformat(iso)
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')} {d.year}"


def _short(day):
    """A date (or ISO text) -> 'Mon 5 Oct'."""
    d = day if isinstance(day, date) else date.fromisoformat(day)
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


DAY_COLORS = {
    0: '#3498db',  # Monday — blue
    1: '#e74c3c',  # Tuesday — red
    2: '#27ae60',  # Wednesday — green
    3: '#f39c12',  # Thursday — orange
    4: '#9b59b6',  # Friday — purple
    5: '#e75480',  # Saturday — pink
    6: '#1abc9c',  # Sunday — teal
}


class RosterTab:
    """Two-panel roster management tab"""

    def __init__(self, parent, translation_func, colors, models_module, admin_check=None):
        self.parent = parent
        self.admin_check = admin_check  # callable: asks for the admin password, True if correct
        self.t = translation_func
        self.colors = colors
        self.models = models_module
        self.selected_class_id = None
        self._selected_card = None  # reference to currently highlighted card frame

        self._build_ui()
        self.load_classes()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        main = tk.Frame(self.parent, bg=self.colors.get('light', '#ecf0f1'))
        main.pack(fill=tk.BOTH, expand=True)

        self._build_toolbar(main)

        # Paned window for left/right split
        paned = tk.PanedWindow(main, orient=tk.HORIZONTAL, sashwidth=6,
                               bg=self.colors.get('light', '#ecf0f1'))
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        left_frame = tk.Frame(paned, bg=theme.colour('card', 'white'), relief='solid', borderwidth=1)
        right_frame = tk.Frame(paned, bg=theme.colour('card', 'white'), relief='solid', borderwidth=1)

        paned.add(left_frame, width=360, minsize=250)
        paned.add(right_frame, minsize=400)

        self._build_class_panel(left_frame)
        self._build_roster_panel(right_frame)

    def _build_toolbar(self, parent):
        toolbar = tk.Frame(parent, bg=self.colors.get('primary', '#2c3e50'), height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text=self.t("roster"),
                 bg=self.colors.get('primary', '#2c3e50'), fg='white',
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)

        btn_frame = tk.Frame(toolbar, bg=self.colors.get('primary', '#2c3e50'))
        btn_frame.pack(side=tk.RIGHT, padx=5, pady=10)

        theme.flat_button(btn_frame, 'warning', text="Seed from CSV",
                  bg=self.colors.get('warning', '#f39c12'), fg='white',
                  font=('Arial', 9), padx=10, pady=4,
                  command=self._on_seed_csv).pack(side=tk.LEFT, padx=3)

        theme.flat_button(btn_frame, 'primary', text="+ Add Class",
                  bg=self.colors.get('success', '#27ae60'), fg='white',
                  font=('Arial', 9), padx=10, pady=4,
                  command=self._on_add_class).pack(side=tk.LEFT, padx=3)

        theme.flat_button(btn_frame, 'secondary', text="Refresh",
                  bg=self.colors.get('secondary', '#3498db'), fg='white',
                  font=('Arial', 9), padx=10, pady=4,
                  command=self.load_classes).pack(side=tk.LEFT, padx=3)

    # ---- Left panel: day-grouped class cards ----
    def _build_class_panel(self, parent):
        header = tk.Frame(parent, bg=self.colors.get('primary', '#2c3e50'), height=35)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Classes", bg=self.colors.get('primary', '#2c3e50'),
                 fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)

        # Scrollable canvas area
        canvas_frame = tk.Frame(parent, bg=theme.colour('card', 'white'))
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self._class_canvas = tk.Canvas(canvas_frame, bg=theme.colour('ground', '#f8f9fa'), highlightthickness=0)
        self._class_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                                               command=self._class_canvas.yview)
        self._class_canvas.configure(yscrollcommand=self._class_scrollbar.set)

        self._class_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._class_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._class_inner = tk.Frame(self._class_canvas, bg=theme.colour('ground', '#f8f9fa'))
        self._canvas_window = self._class_canvas.create_window(
            (0, 0), window=self._class_inner, anchor='nw'
        )

        # Resize inner frame width to match canvas
        def _on_canvas_configure(event):
            self._class_canvas.itemconfig(self._canvas_window, width=event.width)

        self._class_canvas.bind('<Configure>', _on_canvas_configure)

        # Update scroll region when inner frame changes
        self._class_inner.bind('<Configure>',
            lambda e: self._class_canvas.configure(scrollregion=self._class_canvas.bbox('all')))

        # Mousewheel scrolling
        def _on_mousewheel(event):
            self._class_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux(event):
            if event.num == 4:
                self._class_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self._class_canvas.yview_scroll(1, "units")

        self._class_canvas.bind('<MouseWheel>', _on_mousewheel)
        self._class_canvas.bind('<Button-4>', _on_mousewheel_linux)
        self._class_canvas.bind('<Button-5>', _on_mousewheel_linux)

        # Bottom buttons: Delete, and Cancel Class / Cancellations... (the label follows the class, see _refresh_cancel_button)
        bottom = tk.Frame(parent, bg=self.colors.get('light', '#ecf0f1'))
        bottom.pack(fill=tk.X, padx=5, pady=5)
        theme.flat_button(bottom, 'danger', text="Delete Class",
                  bg=self.colors.get('danger', '#e74c3c'), fg='white',
                  font=('Arial', 9), padx=8, pady=3,
                  command=self._on_delete_class).pack(side=tk.RIGHT)

        self._cancel_btn = theme.flat_button(bottom, 'warning', text="Cancel Class",
                  bg='#e67e22', fg='white',
                  font=('Arial', 9), padx=8, pady=3,
                  command=self._on_cancel_class)
        self._cancel_btn.pack(side=tk.RIGHT, padx=(0, 5))

    # ---- Right panel: student roster ----
    def _build_roster_panel(self, parent):
        # Header area showing selected class info
        self.roster_header = tk.Frame(parent, bg=self.colors.get('secondary', '#3498db'), height=55)
        self.roster_header.pack(fill=tk.X)
        self.roster_header.pack_propagate(False)

        self.roster_title = tk.Label(self.roster_header, text="Select a class",
                                     bg=self.colors.get('secondary', '#3498db'), fg='white',
                                     font=('Arial', 11, 'bold'))
        self.roster_title.pack(side=tk.LEFT, padx=10, pady=5)

        self.roster_subtitle = tk.Label(self.roster_header, text="",
                                        bg=self.colors.get('secondary', '#3498db'), fg=theme.colour('side_text', '#dfe6e9'),
                                        font=('Arial', 9))
        self.roster_subtitle.pack(side=tk.LEFT, padx=5, pady=5)

        # Student treeview
        tree_frame = tk.Frame(parent, bg=theme.colour('card', 'white'))
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("student_id", "first_name", "last_name", "level", "enrolled_at")
        self.roster_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=20)
        self.roster_tree.heading("student_id", text="Student ID")
        self.roster_tree.heading("first_name", text="First Name")
        self.roster_tree.heading("last_name", text="Last Name")
        self.roster_tree.heading("level", text="Level")
        self.roster_tree.heading("enrolled_at", text="Enrolled")

        self.roster_tree.column("student_id", width=90, minwidth=70)
        self.roster_tree.column("first_name", width=100, minwidth=70)
        self.roster_tree.column("last_name", width=100, minwidth=70)
        self.roster_tree.column("level", width=80, minwidth=60)
        self.roster_tree.column("enrolled_at", width=120, minwidth=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.roster_tree.yview)
        self.roster_tree.configure(yscrollcommand=scrollbar.set)
        self.roster_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom buttons
        bottom = tk.Frame(parent, bg=self.colors.get('light', '#ecf0f1'))
        bottom.pack(fill=tk.X, padx=5, pady=5)

        theme.flat_button(bottom, 'primary', text="+ Add Student",
                  bg=self.colors.get('success', '#27ae60'), fg='white',
                  font=('Arial', 9), padx=10, pady=3,
                  command=self._on_add_student).pack(side=tk.LEFT, padx=3)

        theme.flat_button(bottom, 'danger', text="- Remove Student",
                  bg=self.colors.get('danger', '#e74c3c'), fg='white',
                  font=('Arial', 9), padx=10, pady=3,
                  command=self._on_remove_student).pack(side=tk.LEFT, padx=3)

    # --------------------------------------------------------- Data loading
    def load_classes(self):
        """Populate the left panel with day-grouped class cards."""
        # Clear existing cards
        for widget in self._class_inner.winfo_children():
            widget.destroy()
        self._selected_card = None

        try:
            classes = self.models.list_class_defs(active_only=True)
        except Exception as e:
            print(f"Error loading classes: {e}")
            return

        # Group by day_of_week
        by_day = {}
        for cls in classes:
            day = cls.get('day_of_week', 0)
            by_day.setdefault(day, []).append(cls)

        # Render each day that has classes (sorted Mon–Sun)
        for day_num in sorted(by_day.keys()):
            day_classes = by_day[day_num]
            day_color = DAY_COLORS.get(day_num, '#95a5a6')
            day_name = DAY_NAMES[day_num] if 0 <= day_num < 7 else f"Day {day_num}"

            # Day header
            day_header = tk.Frame(self._class_inner, bg=theme.colour('ground', '#f8f9fa'))
            day_header.pack(fill=tk.X, padx=8, pady=(12, 4))

            accent = tk.Frame(day_header, bg=day_color, width=4)
            accent.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

            tk.Label(day_header, text=day_name.upper(), bg=theme.colour('ground', '#f8f9fa'),
                     fg=day_color, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, pady=4)

            # Class cards for this day
            for cls in day_classes:
                self._render_class_card(cls, day_num, day_color)

        # Re-highlight selected card if it still exists
        if self.selected_class_id:
            self._highlight_card_by_id(self.selected_class_id)
        self._refresh_cancel_button()

    def _refresh_cancel_button(self):
        """The button says what it will do for the selected class: "Cancellations..." (look at them, give lessons back,
        or cancel more) if it has any cancellation that has not ended (current or coming), otherwise "Cancel Class". Called after every change, and when a card is picked."""
        btn = getattr(self, '_cancel_btn', None)
        if btn is None:
            return
        upcoming = False
        if self.selected_class_id:
            try:
                upcoming = bool(self.models.list_upcoming_cancellations(self.selected_class_id))
            except Exception:
                pass
        if upcoming:
            btn.configure(text="Cancellations\u2026")
            theme.set_flat(btn, 'primary', bg='#27ae60')        # opens the list of this class's cancellations
        else:
            btn.configure(text="Cancel Class")
            theme.set_flat(btn, 'warning', bg='#e67e22')

    def _card_wraplength(self):
        """Where a card's text wraps before the card has its real width: the pane's width less the card's own margins."""
        try:
            width = self._class_canvas.winfo_width()
        except tk.TclError:
            width = 1
        return max(120, width - 44) if width > 1 else 300

    def _render_class_card(self, cls, day_num, day_color):
        """Create a single clickable class card."""
        class_id = cls['class_id']
        class_name = cls.get('class_name', class_id)
        start = cls.get('start_time', '')
        end = cls.get('end_time', '')
        time_str = f"{start}–{end}" if start and end else ""

        # Check cancellation status
        is_cancelled = False
        cancel_info = ""
        try:
            cancellations = self.models.get_active_cancellations(class_id)
            if cancellations:
                is_cancelled = True
                cancel_end = cancellations[0].get('cancel_end', '')
                cancel_info = f"  (Cancelled until {cancel_end})"
        except Exception:
            pass

        # Upcoming cancelled lessons (also those that have not started yet): up to three dates, then "+N more"
        cancel_lines = ""
        try:
            upcoming = self.models.list_upcoming_cancellations(class_id)
            dates = sorted({x for c in upcoming for x in c['upcoming_lesson_dates']})
            if dates:
                cancel_lines = "Cancelled: " + ", ".join(_short(x) for x in dates[:3])
                if len(dates) > 3:
                    cancel_lines += f", +{len(dates) - 3} more"
        except Exception:
            pass

        try:
            roster = self.models.get_roster_for_class(class_id)
            count = len(roster)
        except Exception:
            count = 0

        # Outer wrapper for padding
        wrapper = tk.Frame(self._class_inner, bg=theme.colour('ground', '#f8f9fa'))
        wrapper.pack(fill=tk.X, padx=8, pady=2)

        # Card frame
        card = tk.Frame(wrapper, bg=theme.colour('card', 'white'), relief='solid', borderwidth=1,
                        cursor='hand2')
        card.pack(fill=tk.X, ipady=6)

        # Left accent bar
        accent = tk.Frame(card, bg=day_color, width=4)
        accent.pack(side=tk.LEFT, fill=tk.Y)

        # Content area
        content = tk.Frame(card, bg=theme.colour('card', 'white'), cursor='hand2')
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 10), pady=4)

        card_bg = theme.colour('ground', '#f0f0f0') if is_cancelled else theme.colour('card', 'white')
        name_fg = theme.colour('ink_muted', '#999999') if is_cancelled else theme.colour('ink', '#2c3e50')
        card.configure(bg=card_bg)
        content.configure(bg=card_bg)

        name_label = tk.Label(content, text=class_name + cancel_info, bg=card_bg,
                              fg=name_fg, font=('Arial', 10, 'bold'),
                              anchor='w', justify=tk.LEFT, wraplength=self._card_wraplength(), cursor='hand2')
        name_label.pack(fill=tk.X)

        cancel_label = None
        if cancel_lines:
            cancel_label = tk.Label(content, text=cancel_lines, bg=card_bg, fg=theme.colour('danger', '#c0392b'),
                                    font=('Arial', 8, 'bold'), anchor='w', justify=tk.LEFT,
                                    wraplength=self._card_wraplength(), cursor='hand2')
            cancel_label.pack(fill=tk.X)
        extras = (cancel_label,) if cancel_label is not None else ()

        def _fit_text(event):
            """Wrap the title (and the cancelled dates) at the width the card really has, as the pane is resized."""
            wrap = max(120, event.width - 4)
            name_label.configure(wraplength=wrap)
            if cancel_label is not None:
                cancel_label.configure(wraplength=wrap)
        content.bind('<Configure>', _fit_text)

        detail_text = time_str
        if count > 0:
            detail_text += f"  \u00b7  {count} students"
        else:
            detail_text += "  \u00b7  0 students"

        detail_label = tk.Label(content, text=detail_text, bg=card_bg,
                                fg=theme.colour('ink_muted', '#7f8c8d'), font=('Arial', 8),
                                anchor='w', cursor='hand2')
        detail_label.pack(fill=tk.X)

        # Store class_id and cancel state on the card for lookup
        card._class_id = class_id
        card._is_cancelled = is_cancelled
        card._default_bg = card_bg

        # Click handler
        def on_click(event, cid=class_id, c=card):
            self._select_card(c, cid)

        # Bind click to card and all children
        for widget in (card, accent, content, name_label, detail_label, *extras):
            widget.bind('<Button-1>', on_click)

        # Hover effects
        def on_enter(event, c=card, cont=content, nl=name_label, dl=detail_label):
            if c != self._selected_card:
                hover_bg = theme.colour('tag_next_bg', '#eef2f7')
                c.configure(bg=hover_bg)
                cont.configure(bg=hover_bg)
                nl.configure(bg=hover_bg)
                dl.configure(bg=hover_bg)
                for x in extras:
                    x.configure(bg=hover_bg)

        def on_leave(event, c=card, cont=content, nl=name_label, dl=detail_label, dbg=card_bg):
            if c != self._selected_card:
                c.configure(bg=dbg)
                cont.configure(bg=dbg)
                nl.configure(bg=dbg)
                dl.configure(bg=dbg)
                for x in extras:
                    x.configure(bg=dbg)

        for widget in (card, accent, content, name_label, detail_label, *extras):
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)

        # Propagate mousewheel from card widgets to canvas
        def _forward_scroll(event):
            self._class_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _forward_scroll_linux(event):
            if event.num == 4:
                self._class_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self._class_canvas.yview_scroll(1, "units")

        for widget in (card, accent, content, name_label, detail_label, wrapper, *extras):
            widget.bind('<MouseWheel>', _forward_scroll)
            widget.bind('<Button-4>', _forward_scroll_linux)
            widget.bind('<Button-5>', _forward_scroll_linux)

    def _select_card(self, card, class_id):
        """Highlight the clicked card and load its roster."""
        # Deselect previous
        if self._selected_card and self._selected_card.winfo_exists():
            self._reset_card_style(self._selected_card)

        # Highlight new
        self._selected_card = card
        self.selected_class_id = class_id
        self._apply_selected_style(card)
        self._load_roster(class_id)

        self._refresh_cancel_button()

    def _apply_selected_style(self, card):
        """Apply visual highlight to selected card."""
        sel_bg = theme.colour('tag_soft_bg', '#dbeafe')
        card.configure(bg=sel_bg, relief='solid', borderwidth=2)
        for child in card.winfo_children():
            if child.cget('bg') != card.winfo_children()[0].cget('bg'):
                # Skip the accent bar (it keeps its color)
                child.configure(bg=sel_bg)
                for sub in child.winfo_children():
                    sub.configure(bg=sel_bg)

    def _reset_card_style(self, card):
        """Reset card to default style."""
        default_bg = getattr(card, '_default_bg', theme.colour('card', 'white'))
        card.configure(bg=default_bg, relief='solid', borderwidth=1)
        for child in card.winfo_children():
            try:
                # Skip accent bar (width=4 frame with colored bg)
                if child.winfo_reqwidth() <= 5:
                    continue
            except Exception:
                pass
            try:
                child.configure(bg=default_bg)
                for sub in child.winfo_children():
                    sub.configure(bg=default_bg)
            except Exception:
                pass

    def _highlight_card_by_id(self, class_id):
        """Find and highlight the card matching class_id after a reload."""
        for wrapper in self._class_inner.winfo_children():
            for child in wrapper.winfo_children():
                if hasattr(child, '_class_id') and child._class_id == class_id:
                    self._selected_card = child
                    self._apply_selected_style(child)
                    return

    def _load_roster(self, class_id: str):
        """Load roster for the selected class into the right panel."""
        for item in self.roster_tree.get_children():
            self.roster_tree.delete(item)

        cls = self.models.get_class_def(class_id)
        if not cls:
            self.roster_title.config(text="Class not found")
            self.roster_subtitle.config(text="")
            return

        day_num = cls.get('day_of_week', 0)
        day_str = DAY_NAMES[day_num] if 0 <= day_num < 7 else str(day_num)
        self.roster_title.config(text=cls.get('class_name', class_id))
        self.roster_subtitle.config(
            text=f"{day_str} {cls.get('start_time', '')}-{cls.get('end_time', '')}  |  Level: {cls.get('level', '-')}  |  Teacher: {cls.get('teacher', '-')}"
        )

        try:
            roster = self.models.get_roster_for_class(class_id)
        except Exception as e:
            print(f"Error loading roster: {e}")
            return

        for entry in roster:
            self.roster_tree.insert("", tk.END, values=(
                entry.get('student_id', ''),
                entry.get('first_name', ''),
                entry.get('last_name', ''),
                entry.get('level', ''),
                (entry.get('enrolled_at') or '')[:10],
            ))

    # --------------------------------------------------------- Event handlers
    def _on_add_class(self):
        """Classes are made in the Schedule tab, so they get a proper ID and can be edited later.

        (This form used to build day_time_level IDs through add_class_def, which count as old-style classes that
        cannot be edited. add_class_def itself stays, for the CSV seeding path.)"""
        messagebox.showinfo(
            "Add Class",
            "Add classes in the Schedule tab, so they get a proper ID and can be edited.")
        self._go_to_schedule_tab()

    def _go_to_schedule_tab(self):
        try:
            notebook = self.parent.master
            label = self.t("schedule")
            for tab in notebook.tabs():
                if notebook.tab(tab, "text") == label:
                    notebook.select(tab)
                    return
        except Exception:
            pass

    def _on_delete_class(self):
        """Delete the selected class after confirmation."""
        if not self.selected_class_id:
            messagebox.showinfo("Select", "Select a class first.")
            return

        class_id = self.selected_class_id
        try:
            roster_n, cancel_n = self.models.class_history_counts(class_id)
        except Exception as e:
            messagebox.showerror("Error", f"Could not check the class:\n{e}")
            return
        if roster_n or cancel_n:
            messagebox.showwarning(
                "Cannot delete",
                f"'{class_id}' has {roster_n} roster row(s) and {cancel_n} cancellation(s).\n\n"
                "Use Deactivate in the Schedule tab; it keeps the history.")
            return
        if self.admin_check is None:
            messagebox.showerror("Cannot delete", "Deleting a class needs the admin password check, which is not set up here.")
            return
        if not self.admin_check():
            return
        if not messagebox.askyesno(
                "Confirm",
                f"Delete class '{class_id}'?\n\nIt has no roster and no cancellations, so nothing is lost from the portal.\n"
                "Zone B may hold recordings filed under this class ID; the portal cannot see them, "
                "and they will no longer match a class.\n\nThere is no undo."):
            return

        try:
            self.models.delete_class_def(class_id)
            self.selected_class_id = None
            self._selected_card = None
            self.roster_title.config(text="Select a class")
            self.roster_subtitle.config(text="")
            for item in self.roster_tree.get_children():
                self.roster_tree.delete(item)
            self.load_classes()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete class:\n{e}")

    def _on_cancel_class(self):
        """Cancel lessons of the selected class, or give cancelled lessons back."""
        if not self.selected_class_id:
            messagebox.showinfo("Select", "Select a class first.")
            return
        self.open_cancel_for(self.selected_class_id)

    def open_cancel_for(self, class_id):
        """The Cancel Class dialog for class_id, or the give-back dialog when it has cancellations that have not
        ended. Returns the dialog, or None when none opened (the Attendance page waits on it, N3)."""
        # Any cancellation that has not ended (current or still to come) goes to the give-back dialog
        try:
            upcoming = self.models.list_upcoming_cancellations(class_id)
        except Exception as e:
            messagebox.showerror("Error", f"Could not look up the cancellations of this class:\n{e}")
            return None
        if upcoming:
            return self._open_uncancel_dialog(class_id, upcoming)
        return self._open_cancel_dialog(class_id)

    def _class_label(self, class_id):
        cls = self.models.get_class_def(class_id)
        return cls.get('class_name', class_id) if cls else class_id

    def _open_cancel_dialog(self, class_id):
        """Pick the first lesson to cancel and how many lessons (1 to 8), with a preview of the dates."""
        class_label = self._class_label(class_id)
        try:
            dates = self.models.next_lesson_dates(class_id, 8)
        except Exception as e:
            messagebox.showerror("Error", f"Could not work out the lesson dates:\n{e}")
            return
        shown = [_long(d) for d in dates]

        dialog = tk.Toplevel(self.parent)
        dialog.title("Cancel Class")
        dialog.geometry("380x330")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=theme.colour('card', 'white'), padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=f"Cancel \"{class_label}\"",
                 bg=theme.colour('card', 'white'), font=('Arial', 10, 'bold'), wraplength=320).pack(anchor='w', pady=(0, 10))

        tk.Label(frame, text="First lesson to cancel:", bg=theme.colour('card', 'white'), font=('Arial', 9)).pack(anchor='w')
        first_var = tk.StringVar(value=shown[0])
        first_combo = ttk.Combobox(frame, textvariable=first_var, values=shown, state='readonly', width=26)
        first_combo.pack(anchor='w', pady=(0, 8))

        tk.Label(frame, text="Number of lessons:", bg=theme.colour('card', 'white'), font=('Arial', 9)).pack(anchor='w')
        lessons_var = tk.IntVar(value=1)
        tk.Spinbox(frame, from_=1, to=8, textvariable=lessons_var, width=5,
                   font=('Arial', 10)).pack(anchor='w', pady=(0, 8))

        preview = tk.Label(frame, text="", bg=theme.colour('card', 'white'), fg=theme.colour('danger', '#c0392b'), font=('Arial', 9, 'bold'),
                           wraplength=320, justify=tk.LEFT)
        preview.pack(anchor='w', pady=(0, 8))

        def chosen():
            """(first date, number of lessons, the list of dates), or None while the number is not 1 to 8."""
            try:
                n = int(lessons_var.get())
            except (tk.TclError, ValueError):
                return None
            if not 1 <= n <= 8 or first_var.get() not in shown:
                return None
            iso = dates[shown.index(first_var.get())]        # by the text shown: current() is -1 until a pick is made
            first = date.fromisoformat(iso)
            return iso, n, [first + timedelta(days=7 * k) for k in range(n)]

        def update_preview(*_):
            c = chosen()
            preview.config(text="Cancels: " + ", ".join(_short(d) for d in c[2]) if c
                           else "Cancels: (the number of lessons must be 1 to 8)")

        first_var.trace_add('write', update_preview)
        lessons_var.trace_add('write', update_preview)
        first_combo.bind('<<ComboboxSelected>>', update_preview)
        update_preview()

        tk.Label(frame, text="Reason (optional):", bg=theme.colour('card', 'white'), font=('Arial', 9)).pack(anchor='w')
        reason_var = tk.StringVar()
        ttk.Entry(frame, textvariable=reason_var, width=35).pack(fill=tk.X, pady=(0, 10))

        def do_cancel():
            c = chosen()
            if c is None:
                messagebox.showwarning("Number of lessons", "Choose 1 to 8 lessons.", parent=dialog)
                return
            first_iso, n, days = c
            reason = reason_var.get().strip() or None
            try:
                self.models.cancel_class(class_id, first_iso, n, reason)
            except self.models.ValidationError as e:
                messagebox.showwarning("Cannot cancel", str(e), parent=dialog)
                return
            except Exception as e:
                messagebox.showerror("Error", f"Could not cancel class:\n{e}", parent=dialog)
                return
            messagebox.showinfo("Cancelled",
                f"\"{class_label}\" cancelled: " + ", ".join(_short(d) for d in days) + ".")
            dialog.destroy()
            self.load_classes()

        btn_frame = tk.Frame(frame, bg=theme.colour('card', 'white'))
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        theme.flat_button(btn_frame, 'warning', text="Cancel Class", bg='#e67e22', fg='white',
                  font=('Arial', 9, 'bold'), padx=12, pady=4,
                  command=do_cancel).pack(side=tk.LEFT, padx=3)
        theme.flat_button(btn_frame, 'secondary', text="Close", bg='#95a5a6', fg='white',
                  font=('Arial', 9), padx=12, pady=4,
                  command=dialog.destroy).pack(side=tk.LEFT, padx=3)
        return dialog

    def _open_uncancel_dialog(self, class_id, upcoming):
        """List the lessons still cancelled; remove all of them, or restore from one lesson on."""
        class_label = self._class_label(class_id)

        dialog = tk.Toplevel(self.parent)
        dialog.title("Cancellations")
        dialog.resizable(True, True)          # no fixed size: it takes what its content needs, and can be made larger
        dialog.transient(self.parent)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=theme.colour('card', 'white'), padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        heading = tk.Label(frame, text=f"\"{class_label}\" has lessons that are still cancelled.",
                           bg=theme.colour('card', 'white'), font=('Arial', 10, 'bold'), wraplength=380, justify=tk.LEFT)
        heading.pack(anchor='w')
        hint = tk.Label(frame, text="Choose a lesson to restore it and every later lesson of that cancellation, "
                                    "or remove all of them.",
                        bg=theme.colour('card', 'white'), font=('Arial', 9), wraplength=380, justify=tk.LEFT)
        hint.pack(anchor='w', pady=(2, 8))

        def fit_text(event):
            """The two texts wrap at the width the dialog has now (less the frame's 20 px padding either side)."""
            wrap = max(200, event.width - 40)
            heading.configure(wraplength=wrap)
            hint.configure(wraplength=wrap)
        frame.bind('<Configure>', fit_text)

        listbox = tk.Listbox(frame, selectmode=tk.SINGLE, height=8, exportselection=False, font=('Arial', 10))
        listbox.pack(fill=tk.BOTH, expand=True)
        rows = []            # (cancellation id, ISO lesson date or None), one per list row
        for c in upcoming:
            reason = f"   ({c['reason']})" if c.get('reason') else ""
            if c['upcoming_lesson_dates']:
                for iso in c['upcoming_lesson_dates']:
                    listbox.insert(tk.END, _long(iso) + reason)
                    rows.append((c['id'], iso))
            else:
                listbox.insert(tk.END, f"(no lesson left to restore, until {c['cancel_end']})" + reason)
                rows.append((c['id'], None))

        # Two rows, so all four buttons fit at any text length: (Remove all, Restore) and (Cancel more, Close)
        btn_frame = tk.Frame(frame, bg=theme.colour('card', 'white'))
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        btn_row1 = tk.Frame(btn_frame, bg=theme.colour('card', 'white'))
        btn_row1.pack(fill=tk.X)
        btn_row2 = tk.Frame(btn_frame, bg=theme.colour('card', 'white'))
        btn_row2.pack(fill=tk.X, pady=(6, 0))

        def remove_all():
            comes_back, stays = [], []
            try:
                for c in upcoming:
                    plan = self.models.give_back_preview(c['id'])
                    comes_back += plan['restored']
                    stays += plan['kept']
            except Exception as e:
                messagebox.showerror("Error", f"Could not work out what would come back:\n{e}", parent=dialog)
                return
            text = f"Remove all {len(upcoming)} cancellation(s) of \"{class_label}\"?\n\n"
            text += ("These lessons come back on: " + ", ".join(_short(x) for x in comes_back) + "."
                     if comes_back else "No lesson comes back on: every lesson in them has already ended.")
            if stays:
                text += ("\n\nLessons that have already ended stay cancelled: "
                         + ", ".join(_short(x) for x in stays) + ".")
            if not messagebox.askyesno("Remove all", text, parent=dialog):
                return
            kept = changed = False
            try:
                for c in upcoming:
                    action = self.models.remove_cancellation_from_today(c['id'])['action']
                    if action in ('shortened', 'unchanged'):
                        kept = True
                    if action != 'unchanged':
                        changed = True
            except Exception as e:
                messagebox.showerror("Error", f"Could not change the cancellation:\n{e}\n\nSome cancellations may already have been "
                                              "removed. The list is shown again as it is now.", parent=dialog)
                dialog.destroy()                  # stop part-way: show what is still cancelled, not the old list
                self.load_classes()
                self._on_cancel_class()
                return
            if not changed:
                done = "No change: every lesson in it has already ended, so it all stays cancelled."
            elif kept:
                done = "Cancellation removed. Lessons that have already ended stay cancelled."
            else:
                done = "Cancellation removed."
            messagebox.showinfo("Done", done)
            dialog.destroy()
            self.load_classes()

        def restore():
            sel = listbox.curselection()
            if not sel or rows[sel[0]][1] is None:
                return
            cid, iso = rows[sel[0]]
            was = next(c for c in upcoming if c['id'] == cid)
            try:
                res = self.models.restore_cancelled_lessons(cid, iso)
            except Exception as e:
                messagebox.showerror("Error", f"Could not restore the lessons:\n{e}", parent=dialog)
                return
            span = f"{_short(was['cancel_start'])} to {_short(was['cancel_end'])}"
            if res['action'] == 'deleted':
                what = f"The cancellation {span} was removed: no lesson was left in it."
            else:
                what = f"The cancellation {span} now ends on {_short(res['cancel_end'])}."
            messagebox.showinfo("Restored", f"{what}\nThe lessons from {_long(iso)} on are back on.")
            dialog.destroy()
            self.load_classes()

        remove_btn = theme.flat_button(btn_row1, 'warning', text="Remove all", bg='#e67e22', fg='white',
                               font=('Arial', 9, 'bold'), padx=12, pady=4, command=remove_all)
        remove_btn.pack(side=tk.LEFT, padx=3)
        restore_btn = theme.flat_button(btn_row1, 'warning', text="Restore from selected lesson", bg='#27ae60', fg='white',
                                font=('Arial', 9, 'bold'), padx=12, pady=4, state=tk.DISABLED, command=restore)
        restore_btn.pack(side=tk.LEFT, padx=3)
        def cancel_more():
            dialog.destroy()
            self._open_cancel_dialog(class_id)

        theme.flat_button(btn_row2, 'warning', text="Cancel more lessons\u2026", bg='#e67e22', fg='white',
                  font=('Arial', 9, 'bold'), padx=12, pady=4, command=cancel_more).pack(side=tk.LEFT, padx=3)
        theme.flat_button(btn_row2, 'secondary', text="Close", bg='#95a5a6', fg='white',
                  font=('Arial', 9), padx=12, pady=4, command=dialog.destroy).pack(side=tk.LEFT, padx=3)

        def on_select(_event=None):
            sel = listbox.curselection()
            if sel and rows[sel[0]][1] is not None:
                restore_btn.config(text=f"Restore from {_short(rows[sel[0]][1])}", state=tk.NORMAL)
            else:
                restore_btn.config(text="Restore from selected lesson", state=tk.DISABLED)

        listbox.bind('<<ListboxSelect>>', on_select)

        # Sized by its content; it cannot be made smaller than that, so no button or line is ever cut off
        dialog.update_idletasks()
        dialog.minsize(dialog.winfo_reqwidth(), dialog.winfo_reqheight())
        return dialog

    def _on_add_student(self):
        """Open student picker dialog."""
        if not self.selected_class_id:
            messagebox.showinfo("Select", "Select a class first.")
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title("Add Student to Roster")
        dialog.transient(self.parent)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=theme.colour('card', 'white'), padx=15, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Search bar
        search_frame = tk.Frame(frame, bg=theme.colour('card', 'white'))
        search_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(search_frame, text="Search:", bg=theme.colour('card', 'white'), font=('Arial', 9)).pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)

        # Student list
        cols = ("student_id", "first_name", "last_name", "level")
        pick_tree = ttk.Treeview(frame, columns=cols, show='headings', height=10)
        pick_tree.heading("student_id", text="ID")
        pick_tree.heading("first_name", text="First Name")
        pick_tree.heading("last_name", text="Last Name")
        pick_tree.heading("level", text="Level")
        pick_tree.column("student_id", width=80)
        pick_tree.column("first_name", width=100)
        pick_tree.column("last_name", width=100)
        pick_tree.column("level", width=80)

        # The button row is packed first, at the bottom, so the list can never push it out of the window (B5b-13)
        btn_frame = tk.Frame(frame, bg=theme.colour('card', 'white'))
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=8)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=pick_tree.yview)
        pick_tree.configure(yscrollcommand=sb.set)
        pick_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Get currently enrolled student IDs to exclude
        current_roster = self.models.get_roster_for_class(self.selected_class_id)
        enrolled_ids = {e['student_id'] for e in current_roster}

        def populate(filter_text=""):
            for item in pick_tree.get_children():
                pick_tree.delete(item)
            try:
                if filter_text:
                    students = self.models.search_students(filter_text)
                else:
                    students = self.models.list_students()
            except Exception as e:
                # Never fail silently again. These two calls passed an
                # active_only= keyword that models.search_students(term) and
                # models.list_students() do not accept; the resulting
                # TypeError was swallowed here, so the picker was always
                # empty and typing a name did nothing at all.
                students = []
                print(f"[roster] student lookup failed: {type(e).__name__}: {e}")
                messagebox.showerror(
                    "Roster", f"Could not load students:\n{e}", parent=dialog)

            # models.* have no active_only parameter; filter here instead.
            students = [s for s in students
                        if (s.get('status') or 'active') == 'active']

            for s in students:
                if s['student_id'] in enrolled_ids:
                    continue
                pick_tree.insert("", tk.END, values=(
                    s['student_id'], s.get('first_name', ''),
                    s.get('last_name', ''), s.get('level', ''),
                ))

        populate()

        def on_search(*_):
            populate(search_var.get().strip())

        search_var.trace_add('write', on_search)
        search_entry.focus()

        def add_selected():
            sel = pick_tree.selection()
            if not sel:
                messagebox.showinfo("Select", "Select a student.", parent=dialog)
                return
            failed = []
            for iid in sel:
                vals = pick_tree.item(iid, 'values')
                student_id = vals[0]
                try:
                    self.models.add_student_to_roster(self.selected_class_id, student_id)
                except Exception as e:
                    text = str(e).lower()
                    if isinstance(e, sqlite3.OperationalError) and ("locked" in text or "busy" in text):
                        failed.append(f"  {student_id}: the database is busy (another window or program is using "
                                      "it). Close it and add this student again.")
                    else:
                        failed.append(f"  {student_id}: {e}")
            if failed:
                messagebox.showerror(
                    "Roster", f"{len(failed)} of {len(sel)} students were not added:\n" + "\n".join(failed),
                    parent=dialog)

            dialog.destroy()
            self._load_roster(self.selected_class_id)
            self.load_classes()  # refresh student count

        theme.flat_button(btn_frame, 'primary', text="Add Selected", bg=self.colors.get('success', '#27ae60'), fg='white',
                  font=('Arial', 9, 'bold'), padx=12, pady=4, command=add_selected).pack(side=tk.LEFT, padx=3)
        theme.flat_button(btn_frame, 'secondary', text="Cancel", bg=self.colors.get('danger', '#e74c3c'), fg='white',
                  font=('Arial', 9), padx=12, pady=4, command=dialog.destroy).pack(side=tk.LEFT, padx=3)

        # Sized by its content, never smaller than the old 500x450; extra height goes to the list (B5b-13, b5c_fix1)
        dialog.update_idletasks()
        dialog.minsize(max(500, dialog.winfo_reqwidth()), max(450, dialog.winfo_reqheight()))

    def _on_remove_student(self):
        """Remove selected student from roster (soft-remove)."""
        if not self.selected_class_id:
            messagebox.showinfo("Select", "Select a class first.")
            return

        sel = self.roster_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a student to remove.")
            return

        vals = self.roster_tree.item(sel[0], 'values')
        student_id = vals[0]
        student_name = f"{vals[1]} {vals[2]}".strip()

        if not messagebox.askyesno("Confirm", f"Remove '{student_name}' from this class?"):
            return

        try:
            self.models.remove_student_from_roster(self.selected_class_id, student_id)
            self._load_roster(self.selected_class_id)
            self.load_classes()  # refresh student count
        except Exception as e:
            messagebox.showerror("Error", f"Could not remove student:\n{e}")

    def _on_seed_csv(self):
        """Open file dialog, seed classes from CSV, show results."""
        file_path = filedialog.askopenfilename(
            title="Select Schedule CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        try:
            classes_created, enrollments_created, unmatched = self.models.seed_classes_from_csv(file_path)

            msg = f"Seeding complete!\n\nClasses created: {classes_created}\nEnrollments created: {enrollments_created}"
            if unmatched:
                msg += f"\n\nUnmatched names ({len(unmatched)}):\n" + "\n".join(f"  - {n}" for n in unmatched[:15])
                if len(unmatched) > 15:
                    msg += f"\n  ... and {len(unmatched) - 15} more"

            messagebox.showinfo("Seed Results", msg)
            self.load_classes()
        except Exception as e:
            messagebox.showerror("Seed Error", f"Could not seed from CSV:\n{e}")
