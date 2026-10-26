"""
Schedule Tab Module - Displays weekly class schedule with proper column highlighting
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from pathlib import Path
from datetime import datetime, timedelta
import shutil

from ui import theme


def _plural(n, noun):
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


class ClassDialog:
    """Add a class, or edit the day, time, label and students of an existing one."""

    HOURS = tuple(f"{h:02d}:00" for h in range(8, 21))

    def __init__(self, tab, cls=None):
        self.tab = tab
        self.models = tab.models
        self.cls = cls
        self.saved_id = None
        self.top = None

        try:
            all_levels = self.models.list_class_levels(active_only=False)
            roster_ids = ({r['student_id'] for r in self.models.get_roster_for_class(cls['class_id'])}
                          if cls else set())
            students = self.models.list_students()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load levels and students:\n{e}")
            return
        self.level_by_name = {l['level_name']: l for l in all_levels if l['is_active']}
        # Keep rostered students even if no longer active, so saving an edit doesn't silently drop them.
        self.students = sorted(
            (s for s in students if s.get('status') == 'active' or s['student_id'] in roster_ids),
            key=lambda s: ((s.get('first_name') or '').lower(), (s.get('last_name') or '').lower(), s['student_id']),
        )
        self.chosen = set(roster_ids)

        bg = tab.colors.get('light', '#f5f5f5')
        font = ('Arial', 10)
        self.top = top = tk.Toplevel(tab.parent)
        top.title(f"Edit Class {cls['class_id']}" if cls else "Add Class")
        top.geometry("900x700")
        top.minsize(760, 560)
        top.configure(bg=bg)
        top.transient(tab.parent.winfo_toplevel())
        top.grab_set()

        form = tk.Frame(top, bg=bg)
        form.pack(fill=tk.X, padx=12, pady=(12, 4))

        def label(row, text):
            tk.Label(form, text=text, bg=bg, font=font).grid(row=row, column=0, sticky='w', pady=4)

        label(0, "Day:")
        self.day_var = tk.StringVar(value=tab.DAYS[cls['day_of_week']] if cls else tab._last_class_day)
        ttk.Combobox(form, textvariable=self.day_var, values=tab.DAYS, state='readonly',
                     width=14, font=font).grid(row=0, column=1, sticky='w', padx=6)

        label(1, "Start time:")
        time_row = tk.Frame(form, bg=bg)
        time_row.grid(row=1, column=1, sticky='w', padx=6)
        self.start_var = tk.StringVar()
        self.end_var = tk.StringVar()
        self.different_var = tk.BooleanVar()
        start_holder = tk.Frame(time_row, bg=bg)
        start_holder.pack(side=tk.LEFT)
        self.start_combo = ttk.Combobox(start_holder, textvariable=self.start_var, values=self.HOURS,
                                        state='readonly', width=7, font=font)
        self.start_entry = ttk.Entry(start_holder, textvariable=self.start_var, width=8, font=font)
        tk.Label(time_row, text="End time:", bg=bg, font=font).pack(side=tk.LEFT, padx=(16, 4))
        self.end_entry = ttk.Entry(time_row, textvariable=self.end_var, width=8, font=font)
        self.end_entry.pack(side=tk.LEFT)
        tk.Checkbutton(time_row, text="Different time", variable=self.different_var, bg=bg,
                       activebackground=bg, font=font, command=self.apply_time_mode).pack(side=tk.LEFT, padx=(16, 0))
        self.time_hint = tk.Label(form, text="", bg=bg, fg=theme.colour('ink_muted', '#7f8c8d'), font=('Arial', 9))
        self.time_hint.grid(row=2, column=1, sticky='w', padx=6)

        if cls:
            self.different_var.set(cls['start_time'] not in self.HOURS
                                   or cls['end_time'] != self._plus_hour(cls['start_time']))
            self.start_var.set(cls['start_time'])
            self.end_var.set(cls['end_time'])
        self.start_var.trace_add('write', lambda *a: self._sync_end())
        self.apply_time_mode()

        label(3, "Level:")
        if cls:
            level = next((l for l in all_levels if l['level_code'] == cls['level']), None)
            level_name = level['level_name'] if level else cls['level']
            self.level_var = None
            tk.Label(form, text=f"{level_name}      (to change the level, use Move Up a Level)", bg=bg,
                     font=font).grid(row=3, column=1, sticky='w', padx=6)
        else:
            self.level_var = tk.StringVar()
            ttk.Combobox(form, textvariable=self.level_var, values=list(self.level_by_name), state='readonly',
                         width=32, font=font).grid(row=3, column=1, sticky='w', padx=6)
            self.level_var.trace_add('write', lambda *a: self._update_id_preview())

        label(4, "Label (optional):")
        label_value = ""
        if cls and cls['class_name'] != f"{level_name} ({cls['class_id']})":
            label_value = cls['class_name']
        self.label_var = tk.StringVar(value=label_value)
        ttk.Entry(form, textvariable=self.label_var, width=40, font=font).grid(row=4, column=1, sticky='w', padx=6)

        label(5, "Class ID:")
        self.id_var = tk.StringVar(
            value=f"{cls['class_id']}   (stays the same when the day or time changes)" if cls
            else "choose a level to see the new ID")
        tk.Label(form, textvariable=self.id_var, bg=bg, fg=tab.colors.get('primary', '#2c3e50'),
                 font=('Arial', 11, 'bold')).grid(row=5, column=1, sticky='w', padx=6, pady=(4, 0))

        btn_bar = tk.Frame(top, bg=bg)
        btn_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(4, 12))
        theme.flat_button(btn_bar, 'primary', text="Save Class", bg=tab.colors.get('success', '#27ae60'), fg='white',
                  font=('Arial', 10, 'bold'), padx=20, pady=4, command=self.save).pack(side=tk.RIGHT, padx=5)
        theme.flat_button(btn_bar, 'secondary', text="Cancel", bg=tab.colors.get('danger', '#e74c3c'), fg='white',
                  font=('Arial', 10), padx=15, pady=4, command=top.destroy).pack(side=tk.RIGHT, padx=5)

        picker = tk.LabelFrame(top, text="Students", bg=bg, font=('Arial', 10, 'bold'))
        picker.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        left = tk.Frame(picker, bg=bg)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        search_row = tk.Frame(left, bg=bg)
        search_row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(search_row, text="Search first name:", bg=bg, font=('Arial', 9)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=18)
        search_entry.pack(side=tk.LEFT, padx=4)
        search_entry.bind('<Return>', lambda e: self._add_single_match())
        self.avail_tree = self._student_tree(left)

        mid = tk.Frame(picker, bg=bg)
        mid.pack(side=tk.LEFT, padx=4)
        tk.Button(mid, text="Add →", width=10, command=self.add_selected).pack(pady=3)
        tk.Button(mid, text="← Remove", width=10, command=self.remove_selected).pack(pady=3)

        right = tk.Frame(picker, bg=bg)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.count_var = tk.StringVar()
        tk.Label(right, textvariable=self.count_var, bg=bg, font=('Arial', 9, 'bold'),
                 anchor='w').pack(fill=tk.X, pady=(0, 4))
        self.chosen_tree = self._student_tree(right)

        self.avail_tree.bind('<Double-1>', lambda e: self.add_selected()
                             if self.avail_tree.identify_region(e.x, e.y) == 'cell' else None)
        self.chosen_tree.bind('<Double-1>', lambda e: self.remove_selected()
                              if self.chosen_tree.identify_region(e.x, e.y) == 'cell' else None)
        self.search_var.trace_add('write', lambda *a: self._refresh_students())
        self._refresh_students()

    @staticmethod
    def _plus_hour(hhmm):
        try:
            return (datetime.strptime(hhmm, "%H:%M") + timedelta(hours=1)).strftime("%H:%M")
        except ValueError:
            return ""

    def _sync_end(self):
        if not self.different_var.get():
            self.end_var.set(self._plus_hour(self.start_var.get()))

    def apply_time_mode(self):
        """Switch between the hourly start dropdown and free-text start and end times."""
        if self.different_var.get():
            self.start_combo.pack_forget()
            self.start_entry.pack(side=tk.LEFT)
            self.end_entry.config(state='normal')
            self.time_hint.config(text="Type times as HH:MM with a leading zero, e.g. 09:30")
        else:
            self.start_entry.pack_forget()
            self.start_combo.pack(side=tk.LEFT)
            start = self.start_var.get()
            if start and start not in self.HOURS:
                snapped = f"{start[:2]}:00"
                self.start_var.set(snapped if snapped in self.HOURS else "")
            self._sync_end()
            self.end_entry.config(state='readonly')
            self.time_hint.config(text="Classes are 1 hour. Tick 'Different time' for anything else.")

    def _update_id_preview(self):
        level = self.level_by_name.get(self.level_var.get())
        if level is None:
            self.id_var.set("choose a level to see the new ID")
            return
        try:
            self.id_var.set(f"{self.models.next_class_id(level['level_code'])}   (will be created)")
        except Exception as e:
            self.id_var.set(f"could not work out the ID: {e}")

    def _student_tree(self, parent):
        frame = tk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(frame, columns=('first', 'last', 'level', 'id'), show='headings',
                            selectmode='extended', height=12)
        for col, text, width in (('first', 'First name', 95), ('last', 'Last name', 75),
                                 ('level', 'Level', 95), ('id', 'ID', 75)):
            tree.heading(col, text=text)
            tree.column(col, width=width, minwidth=50, anchor='w', stretch=True)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def _refresh_students(self):
        term = self.search_var.get().strip().lower()
        for tree in (self.avail_tree, self.chosen_tree):
            tree.delete(*tree.get_children())
        for s in self.students:
            values = (s.get('first_name') or '', s.get('last_name') or '', s.get('level') or '', s['student_id'])
            if s['student_id'] in self.chosen:
                self.chosen_tree.insert('', 'end', iid=s['student_id'], values=values)
            elif term in (s.get('first_name') or '').lower():
                self.avail_tree.insert('', 'end', iid=s['student_id'], values=values)
        self.count_var.set(f"In this class: {len(self.chosen)}")

    def add_selected(self):
        self.chosen.update(self.avail_tree.selection())
        self._refresh_students()

    def remove_selected(self):
        self.chosen.difference_update(self.chosen_tree.selection())
        self._refresh_students()

    def _add_single_match(self):
        matches = self.avail_tree.get_children()
        if len(matches) == 1:
            self.chosen.add(matches[0])
            self.search_var.set("")

    def save(self):
        top = self.top
        day = self.day_var.get()
        start = self.start_var.get().strip()
        end = self.end_var.get().strip()
        if day not in self.tab.DAYS:
            messagebox.showwarning("Missing", "Choose a day.", parent=top)
            return
        if not start:
            messagebox.showwarning("Missing", "Choose a start time.", parent=top)
            return
        level = None
        if self.cls is None:
            level = self.level_by_name.get(self.level_var.get())
            if level is None:
                messagebox.showwarning("Missing", "Choose a level.", parent=top)
                return
        try:
            self.models.check_class_times(start, end)
        except self.models.ValidationError as e:
            messagebox.showwarning("Check the time", str(e), parent=top)
            return

        day_num = self.tab.DAYS.index(day)
        student_ids = sorted(self.chosen)
        if not student_ids and not messagebox.askyesno(
                "No students",
                "No students are selected.\n\nA class with no students is usually a mistake. Save it anyway?",
                icon='warning', parent=top):
            return

        try:
            clashes = self.models.find_clashes(
                day_num, start, end, exclude_class_id=self.cls['class_id'] if self.cls else None)
        except Exception as e:
            messagebox.showerror("Error", f"Could not check for clashes:\n{e}", parent=top)
            return
        if clashes:
            lines = "\n".join(f"  •  {c['class_id']}   {c['start_time']}-{c['end_time']}   "
                              f"({_plural(c['student_count'], 'student')})" for c in clashes)
            if not messagebox.askyesno(
                    "Time clash",
                    f"Another class already runs on {day} at an overlapping time:\n\n{lines}\n\n"
                    "Parallel classes are fine if that is intended. Save anyway?",
                    icon='warning', parent=top):
                return

        label = self.label_var.get().strip() or None
        try:
            if self.cls:
                saved_id = self.cls['class_id']
                self.models.update_class(saved_id, day_num, start, end, label=label, student_ids=student_ids)
            else:
                saved_id = self.models.create_class(level['level_code'], day_num, start, end, label, student_ids)
        except self.models.ValidationError as e:
            messagebox.showwarning("Cannot save", str(e), parent=top)
            return
        except Exception as e:
            messagebox.showerror("Error", f"Could not save the class. Nothing was changed.\n\n{e}", parent=top)
            return

        self.saved_id = saved_id
        self.tab._last_class_day = day
        top.destroy()
        self.tab._refresh_classes(select=saved_id)
        messagebox.showinfo("Saved", f"{'Updated' if self.cls else 'Created'} class {saved_id}\n"
                                     f"{day} {start}-{end}, {_plural(len(student_ids), 'student')}.")


class PromoteDialog:
    """Move a class up a level: a new class with the same day, time and students replaces it."""

    def __init__(self, tab, cls):
        self.tab = tab
        self.models = tab.models
        self.cls = cls
        self.new_id = None
        self.top = None

        try:
            levels = self.models.list_class_levels()
            current = next((l for l in self.models.list_class_levels(active_only=False)
                            if l['level_code'] == cls['level']), None)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load levels:\n{e}")
            return
        self.choices = {l['level_name']: l for l in levels
                        if l['level_code'] != cls['level'] and l['level_code'] not in self.models.STANDALONE_LEVELS}
        default = None
        if current:
            default = next((l for l in levels if l['series'] == current['series']
                            and l['sort_order'] > current['sort_order']), None)

        bg = tab.colors.get('light', '#f5f5f5')
        font = ('Arial', 10)
        self.top = top = tk.Toplevel(tab.parent)
        top.title(f"Move Up a Level - {cls['class_id']}")
        top.geometry("580x320")
        top.resizable(False, False)
        top.configure(bg=bg)
        top.transient(tab.parent.winfo_toplevel())
        top.grab_set()

        body = tk.Frame(top, bg=bg)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(14, 4))
        tk.Label(body, text=f"{cls['class_id']}  -  {current['level_name'] if current else cls['level']}",
                 bg=bg, font=('Arial', 12, 'bold')).pack(anchor='w')
        tk.Label(body, text=f"{tab._day_name(cls['day_of_week'])} {cls['start_time']}-{cls['end_time']}, "
                            f"{_plural(cls['student_count'], 'student')}", bg=bg, font=font).pack(anchor='w', pady=(0, 10))

        row = tk.Frame(body, bg=bg)
        row.pack(anchor='w')
        tk.Label(row, text="Move up to:", bg=bg, font=font).pack(side=tk.LEFT)
        self.level_var = tk.StringVar(value=default['level_name'] if default else "")
        ttk.Combobox(row, textvariable=self.level_var, values=list(self.choices), state='readonly',
                     width=30, font=font).pack(side=tk.LEFT, padx=6)

        self.preview_var = tk.StringVar()
        tk.Label(body, textvariable=self.preview_var, bg=bg, fg=tab.colors.get('primary', '#2c3e50'),
                 font=('Arial', 11, 'bold')).pack(anchor='w', pady=(12, 4))
        tk.Label(body, text=f"The new class gets the same day, time and students.\n"
                            f"{cls['class_id']} is deactivated; its roster and history are kept.",
                 bg=bg, fg=theme.colour('ink_muted', '#555555'), font=('Arial', 9), justify='left').pack(anchor='w')

        btn_bar = tk.Frame(top, bg=bg)
        btn_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(4, 14))
        self.confirm_btn = theme.flat_button(btn_bar, 'warning', text="Move Up", bg=tab.colors.get('purple', '#9b59b6'), fg='white',
                                     disabledforeground=theme.colour('warning_disabled', '#bdc3c7'),
                                     font=('Arial', 10, 'bold'), padx=20, pady=4,
                                     command=self.confirm)
        self.confirm_btn.pack(side=tk.RIGHT, padx=5)
        theme.flat_button(btn_bar, 'secondary', text="Cancel", bg=tab.colors.get('danger', '#e74c3c'), fg='white',
                  font=('Arial', 10), padx=15, pady=4, command=top.destroy).pack(side=tk.RIGHT, padx=5)

        self.level_var.trace_add('write', lambda *a: self._update_preview())
        self._update_preview()

    def _update_preview(self):
        level = self.choices.get(self.level_var.get())
        if level is None:
            self.preview_var.set("Choose the new level.")
            self.confirm_btn.config(state=tk.DISABLED, text="Move Up")
            return
        try:
            new_id = self.models.next_class_id(level['level_code'])
        except Exception as e:
            self.preview_var.set(f"Could not work out the new ID: {e}")
            self.confirm_btn.config(state=tk.DISABLED, text="Move Up")
            return
        self.preview_var.set(f"New class ID: {new_id}")
        self.confirm_btn.config(state=tk.NORMAL, text=f"Create {new_id}")

    def confirm(self):
        level = self.choices.get(self.level_var.get())
        if level is None:
            return
        try:
            preview = self.models.promote_preview(self.cls['class_id'], level['level_code'])
        except self.models.ValidationError as e:
            messagebox.showwarning("Cannot move up", str(e), parent=self.top)
            return
        except Exception as e:
            messagebox.showerror("Error", f"Could not check the move. Nothing was changed.\n\n{e}", parent=self.top)
            return
        lines = [f"Create {preview['new_id']} ({level['level_name']}) and move {self.cls['class_id']} up?", "",
                 f"{_plural(preview['students'], 'student')} move to {preview['new_id']}.",
                 f"{_plural(preview['cancellations'], 'cancellation')} carried over."]
        if preview['label']:
            lines.append(f"The label '{preview['label']}' is kept. Edit it afterwards if it names the old level.")
        lines += [f"{self.cls['class_id']} will be deactivated; its roster and history are kept.", "",
                  "There is no undo."]
        if not messagebox.askyesno("Move Up a Level", "\n".join(lines), parent=self.top):
            return
        try:
            new_id = self.models.promote_class(self.cls['class_id'], level['level_code'])
        except self.models.ValidationError as e:
            messagebox.showwarning("Cannot move up", str(e), parent=self.top)
            return
        except Exception as e:
            messagebox.showerror("Error", f"Could not move the class up. Nothing was changed.\n\n{e}",
                                 parent=self.top)
            return
        self.new_id = new_id
        self.top.destroy()
        self.tab._refresh_classes(select=new_id)
        messagebox.showinfo("Moved up", f"Created {new_id} ({level['level_name']}).\n"
                                        f"{self.cls['class_id']} has been deactivated.")
        self._offer_level_update(new_id, level)

    def _offer_level_update(self, new_id, level):
        """Offer to change the moved students' own Level, only where it equals the old level."""
        old_code = self.cls['level']
        try:
            match, others = self.models.moved_students_level_split(new_id, old_code)
        except Exception as e:
            messagebox.showwarning("Level not offered", f"Could not check the students' Level:\n{e}")
            return
        if not match:
            return
        text = f"Also change Level from {old_code} to {level['level_code']} for these {_plural(len(match), 'student')}?"
        if others:
            text += (f" {others} other{' has' if others == 1 else 's have'} a different Level and "
                     f"{'is' if others == 1 else 'are'} left alone.")
        if not messagebox.askyesno("Change students' Level", text):
            return
        try:
            changed = self.models.set_student_levels(match, level['level_code'], expected_old=old_code)
        except Exception as e:
            messagebox.showerror("Error", f"Could not change the Level. Nothing was changed.\n\n{e}")
            return
        messagebox.showinfo("Level changed", f"Level changed to {level['level_code']} for {_plural(len(changed), 'student')}.")
        refresh = getattr(self.tab, 'on_students_changed', None)
        if refresh:
            try:
                refresh()
            except Exception as e:
                print(f"Warning: could not refresh the Students tab: {e}")


class ScheduleTab:
    """Schedule tab with proper column highlighting and import functionality"""

    def __init__(self, parent, translation_func, colors, models_module=None, on_students_changed=None):
        """
        Initialize schedule tab

        Args:
            parent: Parent frame
            translation_func: Translation function for i18n
            colors: Color scheme dictionary
            models_module: The models module for database access
        """
        self.parent = parent
        self.t = translation_func
        self.colors = colors
        self.models = models_module
        self.on_students_changed = on_students_changed  # called after a change to students' own data
        self.schedule_data = []  # List of [time, mon, tue, wed, thu, fri, sat, sun]
        self.highlighted_day = None
        self.schedule_file_path = None

        self._build_ui()
        self.load_schedule()

    def _build_ui(self):
        """Build the schedule tab UI"""
        # Main container
        main_container = tk.Frame(self.parent, bg=self.colors.get('light', '#f5f5f5'))
        main_container.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        self._build_toolbar(main_container)

        # Scrollable content area
        outer = tk.Frame(main_container, bg=self.colors.get('light', '#f5f5f5'))
        outer.pack(fill=tk.BOTH, expand=True)

        content = tk.Frame(outer, bg=self.colors.get('light', '#f5f5f5'))
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Schedule display frame
        self._build_schedule_display(content)

        # Classes (class_def) section
        self._build_classes_section(content)

        # Extra Lessons section
        self._build_extra_lessons_section(content)

    # ---------- CLASSES SECTION ----------

    DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')

    def _build_classes_section(self, parent):
        """Build the class list with Add, Edit, Move Up a Level and Deactivate."""
        self._classes = []
        self._class_sort = 'day'
        self._last_class_day = 'Monday'
        header_bg = theme.colour('side', self.colors.get('secondary', '#34495e'))   # dark, so its buttons show

        section = tk.Frame(parent, bg=theme.colour('card', 'white'), relief='solid', borderwidth=2)
        section.pack(fill=tk.X, pady=(10, 0))

        header = tk.Frame(section, bg=header_bg, height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header, text="Classes", bg=header_bg, fg='white',
            font=('Arial', 11, 'bold'), padx=15
        ).pack(side=tk.LEFT, pady=8)

        self.class_show_inactive_var = tk.BooleanVar(value=False)
        self.class_inactive_check = tk.Checkbutton(
            header, text="Show inactive", variable=self.class_show_inactive_var, command=self._refresh_classes,
            bg=header_bg, fg='white', selectcolor=header_bg, activebackground=header_bg,
            activeforeground='white', font=('Arial', 9))
        self.class_inactive_check.pack(side=tk.LEFT, padx=10)

        btn_frame = tk.Frame(header, bg=header_bg)
        btn_frame.pack(side=tk.RIGHT, padx=5, pady=5)

        def button(text, kind, color, command):
            b = theme.flat_button(btn_frame, kind, text=text, bg=color, fg='white',
                                  disabledforeground=theme.colour(kind + '_disabled', '#bdc3c7'),
                                  font=('Arial', 9), padx=10, pady=2, command=command)
            b.pack(side=tk.LEFT, padx=3)
            return b

        button("+ Add Class", 'primary', self.colors.get('success', '#27ae60'), self._open_class_dialog)
        self.class_edit_btn = button(
            "Edit", 'secondary', self.colors.get('primary', '#2c3e50'), lambda: self._open_class_dialog(edit=True))
        self.class_promote_btn = button(
            "Move Up a Level", 'primary', self.colors.get('purple', '#9b59b6'), self._open_promote_dialog)
        self.class_deactivate_btn = button(
            "Deactivate", 'danger', self.colors.get('danger', '#e74c3c'), self._deactivate_selected_class)
        self.class_reactivate_btn = button(
            "Reactivate", 'warning', self.colors.get('success', '#27ae60'), self._reactivate_selected_class)

        tree_frame = tk.Frame(section, bg=theme.colour('card', 'white'))
        tree_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        cols = ('day', 'time', 'level', 'class_id', 'students', 'kind')
        tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=8, selectmode='browse')
        for col, text, width, anchor in (
            ('day', 'Day', 100, 'w'),
            ('time', 'Time', 110, 'center'),
            ('level', 'Level', 120, 'center'),
            ('class_id', 'Class ID', 170, 'w'),
            ('students', 'Students', 70, 'center'),
            ('kind', '', 170, 'w'),
        ):
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor)
        tree.heading('day', command=lambda: self._sort_classes('day'))
        tree.heading('time', command=lambda: self._sort_classes('time'))
        tree.tag_configure('legacy', foreground=theme.colour('ink_muted', '#7f8c8d'))
        tree.tag_configure('inactive', foreground=theme.colour('ink_muted', '#95a5a6'))
        tree.bind('<<TreeviewSelect>>', lambda e: self._update_class_buttons())
        tree.bind('<Double-1>', lambda e: self._open_class_dialog(edit=True)
                  if tree.identify_region(e.x, e.y) == 'cell' else None)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.class_tree = tree

        self.class_hint = tk.Label(section, text="", bg=theme.colour('card', 'white'), fg=theme.colour('ink_muted', '#7f8c8d'), font=('Arial', 9), anchor='w')
        self.class_hint.pack(fill=tk.X, padx=8, pady=(2, 5))

        self._refresh_classes()

    def _refresh_classes(self, select=None):
        """Reload active classes from class_def, keeping the selection unless select is given."""
        if not self.models:
            return
        if select is None:
            sel = self.class_tree.selection()
            select = sel[0] if sel else None
        error = None
        try:
            self._classes = self.models.list_classes_with_counts(active_only=not self.class_show_inactive_var.get())
        except Exception as e:
            self._classes = []
            error = e
        self._render_classes(select)
        if error:
            self.class_hint.config(text=f"Could not load classes: {error}",
                                   fg=self.colors.get('danger', '#e74c3c'))

    def _render_classes(self, select=None):
        tree = self.class_tree
        tree.delete(*tree.get_children())
        if self._class_sort == 'time':
            key = lambda c: (c['start_time'], c['day_of_week'], c['class_id'])
        else:
            key = lambda c: (c['day_of_week'], c['start_time'], c['class_id'])
        for c in sorted(self._classes, key=key):
            legacy = self.models.is_legacy_class(c)
            inactive = not c.get('is_active')
            tree.insert('', 'end', iid=c['class_id'],
                        tags=tuple(t for t, on in (('legacy', legacy), ('inactive', inactive)) if on), values=(
                self._day_name(c['day_of_week']),
                f"{c['start_time']} - {c['end_time']}",
                c.get('level') or '',
                c['class_id'],
                c['student_count'],
                ' - '.join(t for t, on in (('inactive', inactive), ('old - not editable', legacy)) if on),
            ))
        tree.heading('day', text='Day ▲' if self._class_sort == 'day' else 'Day')
        tree.heading('time', text='Time ▲' if self._class_sort == 'time' else 'Time')
        if select and tree.exists(select):
            tree.selection_set(select)
            tree.see(select)
        self._update_class_buttons()

    def _sort_classes(self, column):
        self._class_sort = column
        sel = self.class_tree.selection()
        self._render_classes(sel[0] if sel else None)

    def _day_name(self, day_of_week):
        return self.DAYS[day_of_week] if isinstance(day_of_week, int) and 0 <= day_of_week <= 6 else '?'

    def _describe_class(self, cls):
        return (f"{cls['class_id']} - {cls.get('level') or ''}, {self._day_name(cls['day_of_week'])} "
                f"{cls['start_time']}-{cls['end_time']}, {_plural(cls['student_count'], 'student')}")

    def _selected_class(self):
        sel = self.class_tree.selection()
        if not sel:
            return None
        return next((c for c in self._classes if c['class_id'] == sel[0]), None)

    def _update_class_buttons(self):
        cls = self._selected_class()
        inactive = cls is not None and not cls.get('is_active')
        editable = cls is not None and not inactive and not self.models.is_legacy_class(cls)
        movable = cls is not None and not inactive and self.models.can_move_up(cls)
        self.class_edit_btn.config(state=tk.NORMAL if editable else tk.DISABLED)
        self.class_promote_btn.config(state=tk.NORMAL if movable else tk.DISABLED)
        self.class_deactivate_btn.config(state=tk.NORMAL if cls and not inactive else tk.DISABLED)
        self.class_reactivate_btn.config(state=tk.NORMAL if inactive else tk.DISABLED)
        if cls is None:
            hint = f"Classes shown: {len(self._classes)}. Click Day or Time to sort. Select a class to edit it."
        elif inactive:
            hint = f"{self._describe_class(cls)} is inactive. Reactivate brings it back if its day and time are free."
        elif not editable:
            hint = "Old-style class (from the CSV import): it can't be edited or moved up. Add its replacement with + Add Class."
        elif not movable:
            hint = (f"{self._describe_class(cls)}. Double-click to edit. "
                    "This is a standalone class type, so it can't be moved up a level.")
        else:
            hint = f"{self._describe_class(cls)}. Double-click to edit."
        self.class_hint.config(text=hint, fg=theme.colour('ink_muted', '#7f8c8d'))

    def _open_class_dialog(self, edit=False):
        """Open Add Class, or Edit for the selected class. Returns the dialog, or None if not opened."""
        cls = None
        if edit:
            cls = self._selected_class()
            if cls is None or self.models.is_legacy_class(cls):
                return None
        return ClassDialog(self, cls)

    def _open_promote_dialog(self):
        """Open Move Up a Level for the selected class. Returns the dialog, or None if not opened."""
        cls = self._selected_class()
        if cls is None or not self.models.can_move_up(cls):
            return None
        return PromoteDialog(self, cls)

    def _deactivate_selected_class(self):
        cls = self._selected_class()
        if cls is None:
            return
        msg = (f"Deactivate {self._describe_class(cls)}?\n\n"
               "It will be removed from the class list and recordings will no longer be matched to it. "
               "Its roster and history are kept.")
        if self.models.is_legacy_class(cls):
            msg += ("\n\nThis is an old-style class that the audio pipeline may still be using. "
                    "Only deactivate it if its replacement is already in the list.")
        if not messagebox.askyesno("Deactivate Class", msg, icon='warning'):
            return
        try:
            self.models.deactivate_class(cls['class_id'])
        except Exception as e:
            messagebox.showerror("Error", f"Could not deactivate {cls['class_id']}:\n{e}")
            return
        self._refresh_classes()

    def _reactivate_selected_class(self):
        cls = self._selected_class()
        if cls is None or cls.get('is_active'):
            return
        try:
            self.models.reactivate_class(cls['class_id'])
        except self.models.ValidationError as e:
            messagebox.showwarning("Cannot reactivate", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Could not reactivate {cls['class_id']}:\n{e}")
            return
        self._refresh_classes()

    def _build_toolbar(self, parent):
        """Build toolbar with buttons"""
        toolbar = tk.Frame(parent, bg=self.colors.get('primary', '#3498db'), height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)

        # Title
        tk.Label(
            toolbar,
            text=f"📅 {self.t('schedule')}",
            bg=self.colors.get('primary', '#3498db'),
            fg='white',
            font=('Arial', 12, 'bold')
        ).pack(side=tk.LEFT, padx=15, pady=10)

        # Button frame
        button_frame = tk.Frame(toolbar, bg=self.colors.get('primary', '#3498db'))
        button_frame.pack(side=tk.RIGHT, padx=5, pady=10)

        # Import button
        theme.flat_button(
            button_frame, 'warning',          # replaces the weekly-grid picture
            text=f"📥 Import Schedule",
            bg=self.colors.get('success', '#27ae60'),
            fg='white',
            font=('Arial', 9),
            padx=10,
            pady=4,
            command=self.import_schedule
        ).pack(side=tk.LEFT, padx=3)

        # Clear highlight button
        theme.flat_button(
            button_frame, 'secondary',
            text=f"🔵 Clear Filter",
            bg=self.colors.get('danger', '#e74c3c'),
            fg='white',
            font=('Arial', 9),
            padx=8,
            pady=4,
            command=self.clear_highlight
        ).pack(side=tk.LEFT, padx=3)

        # Refresh button
        theme.flat_button(
            button_frame, 'secondary',
            text=f"🔄 Refresh",
            bg=self.colors.get('secondary', '#34495e'),
            fg='white',
            font=('Arial', 9),
            padx=8,
            pady=4,
            command=self.load_schedule
        ).pack(side=tk.LEFT, padx=3)

    def _build_schedule_display(self, parent):
        """Build the schedule display using Canvas for proper cell highlighting"""
        # Container frame
        display_frame = tk.Frame(parent, bg=theme.colour('card', 'white'), relief='solid', borderwidth=2)
        display_frame.pack(fill=tk.BOTH, expand=True)

        # Title with current day indicator
        title_frame = tk.Frame(display_frame, bg=self.colors.get('secondary', '#34495e'), height=40)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text=f"📋 Weekly Class Schedule — picture of the imported CSV",
            bg=self.colors.get('secondary', '#34495e'),
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=15
        ).pack(side=tk.LEFT, pady=8)

        # Status label
        self.status_label = tk.Label(
            title_frame,
            text=f"Today: {datetime.now().strftime('%A')}",
            bg=self.colors.get('secondary', '#34495e'),
            fg=theme.colour('side_text', '#e8f4f8'),
            font=('Arial', 9),
            padx=15
        )
        self.status_label.pack(side=tk.RIGHT, pady=8)

        # D2 (c), decided 2 Oct: the grid is only a picture; say where classes and attendance really come from
        tk.Label(
            display_frame,
            text="This grid only shows the newest imported file. Classes, rosters and attendance come from the "
                 "Classes list below.",
            bg=theme.colour('card', 'white'),
            fg=theme.colour('ink_muted', '#7f8c8d'),
            font=('Arial', 9),
            anchor='w',
            padx=15
        ).pack(fill=tk.X)

        # Canvas with vertical scrollbar only (no horizontal scroll)
        canvas_frame = tk.Frame(display_frame, bg=theme.colour('card', 'white'))
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Create canvas
        self.canvas = tk.Canvas(canvas_frame, bg=theme.colour('card', 'white'), highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Vertical scrollbar only
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=v_scrollbar.set)

        # Frame inside canvas for the grid
        self.grid_frame = tk.Frame(self.canvas, bg=theme.colour('card', 'white'))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor='nw')

        # Bind canvas resize
        self.grid_frame.bind('<Configure>', self._on_grid_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

    def _on_grid_configure(self, event):
        """Update canvas scroll region when grid changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        """Update canvas window width when canvas resizes"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def import_schedule(self):
        """Open file dialog to import schedule CSV"""
        file_path = filedialog.askopenfilename(
            title="Select Schedule CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )

        if not file_path:
            return  # User cancelled

        # Copy file to imports/student atten folder
        try:
            import_dir = Path(__file__).resolve().parent.parent / "imports" / "student atten"
            import_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_file = import_dir / f"schedule_{timestamp}.csv"

            shutil.copy2(file_path, dest_file)

            messagebox.showinfo(
                "Import Successful",
                f"Schedule imported successfully!\n\nSaved to: {dest_file.name}\n\n"
                "This changes the picture only; it does not change classes or attendance."
            )

            # Load the new schedule
            self.schedule_file_path = dest_file
            self.load_schedule()

        except Exception as e:
            messagebox.showerror("Import Failed", f"Could not import schedule:\n{e}")

    def load_schedule(self):
        """Load schedule from CSV file"""
        # Find schedule file
        schedule_dir = Path(__file__).resolve().parent.parent / "imports" / "student atten"

        if not schedule_dir.exists():
            schedule_dir.mkdir(parents=True, exist_ok=True)

        # Get latest schedule file
        schedule_files = sorted(schedule_dir.glob("*.csv"))

        if not schedule_files:
            self._display_no_schedule()
            return

        latest_schedule = schedule_files[-1]
        self.schedule_file_path = latest_schedule

        try:
            with open(latest_schedule, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                all_rows = list(reader)

            if not all_rows:
                self._display_no_schedule()
                return

            # Parse schedule data
            self._parse_schedule_data(all_rows)

            # Render the schedule
            self._render_schedule()

            # Auto-highlight today's column
            self._auto_highlight_today()

        except Exception as e:
            messagebox.showerror("Error", f"Could not load schedule:\n{e}")
            self._display_no_schedule()

    def _parse_schedule_data(self, rows):
        """Parse CSV rows into schedule data.

        Handles three CSV layouts:
        - Grid with leading empty cols (9+ cols): time at col 1, days at cols 2-8
        - Grid 8-col (Time + 7 days): time at col 0, days at cols 1-7
        - Roster flat list (class_id,class_name,day_of_week,...): converted to grid
        """
        self.schedule_data = []

        if not rows:
            return

        # Detect format from header row
        header = [str(c).strip().lower() for c in rows[0]]

        # Roster format detection: header contains 'class_id'
        if 'class_id' in header:
            self._parse_roster_to_grid(rows)
            return

        # Grid format — detect column offset
        # Check if first column is empty or non-time (leading empty cols)
        has_leading_empty = False
        if len(rows) > 1 and len(rows[0]) >= 9:
            first_col = str(rows[0][0]).strip().lower()
            if not first_col or first_col not in ('time', 'time slot'):
                has_leading_empty = True

        if has_leading_empty:
            time_col = 1
            day_start = 2
            day_end = 9
            min_cols = 9
        else:
            time_col = 0
            day_start = 1
            day_end = 8
            min_cols = 8

        # Find start of time data (look for rows with time format)
        start_row = 0
        for i, row in enumerate(rows):
            for cell in row:
                if ':' in str(cell) and ('AM' in str(cell).upper() or 'PM' in str(cell).upper()):
                    start_row = i
                    break
            if start_row > 0:
                break

        if start_row == 0:
            start_row = min(1, len(rows))  # skip header

        # Extract data rows
        for row in rows[start_row:]:
            if len(row) >= min_cols:
                time_slot = str(row[time_col]).strip() if len(row) > time_col else ""
                schedule_row = [time_slot]

                for i in range(day_start, day_end):
                    schedule_row.append(str(row[i]).strip() if len(row) > i else "")

                # Skip empty rows
                if time_slot or any(schedule_row[1:]):
                    self.schedule_data.append(schedule_row)

    def _parse_roster_to_grid(self, rows):
        """Convert roster-format CSV rows into a visual schedule grid."""
        day_map = {'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7}
        header = [str(c).strip().lower() for c in rows[0]]

        # Build index map from header
        idx = {col: i for i, col in enumerate(header)}

        # Group classes by time slot — use plain dict, we sort afterwards
        time_slots = {}

        for row in rows[1:]:
            if len(row) < len(header):
                continue
            class_name = str(row[idx.get('class_name', idx.get('class_id', 0))]).strip()
            day_text = str(row[idx.get('day_of_week', 2)]).strip()
            start = str(row[idx.get('start_time', 3)]).strip()
            end = str(row[idx.get('end_time', 4)]).strip()

            time_key = f"{start} - {end}"
            day_idx = day_map.get(day_text.lower()[:3], 0)
            if day_idx == 0:
                continue

            if time_key not in time_slots:
                time_slots[time_key] = ["", "", "", "", "", "", ""]  # Mon-Sun

            # Append class name to the day cell
            existing = time_slots[time_key][day_idx - 1]
            if existing:
                time_slots[time_key][day_idx - 1] = existing + "\n" + class_name
            else:
                time_slots[time_key][day_idx - 1] = class_name

        # Sort time slots chronologically by start_time
        def parse_time_for_sort(time_key):
            """Extract start_time from 'HH:MM - HH:MM' and return sortable value."""
            start_str = time_key.split('-')[0].strip()
            try:
                return datetime.strptime(start_str, "%H:%M")
            except ValueError:
                try:
                    return datetime.strptime(start_str, "%H:%M:%S")
                except ValueError:
                    return datetime.max  # push unparseable times to the end

        sorted_keys = sorted(time_slots.keys(), key=parse_time_for_sort)

        # Convert to schedule_data format: [time, mon, tue, wed, thu, fri, sat, sun]
        for time_key in sorted_keys:
            self.schedule_data.append([time_key] + time_slots[time_key])

    def _display_no_schedule(self):
        """Display message when no schedule is available"""
        self.schedule_data = [["No schedule found", "-", "-", "-", "-", "-", "-", "-"]]
        self._render_schedule()

    def _render_schedule(self):
        """Render the schedule grid on canvas"""
        # Clear existing widgets
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        if not self.schedule_data:
            return

        # Column headers
        headers = ["⏰ Time", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_keys = [None, "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        # Colors
        header_bg = self.colors.get('primary', '#3498db')
        odd_row_bg = '#b3b3b3'
        even_row_bg = '#ffffff'
        highlight_bg = '#ffeb3b'  # Yellow highlight

        # Cell dimensions — row height only, widths are proportional
        row_height = 70

        # Configure grid columns to distribute width evenly
        # Time column gets weight 1, day columns get weight 2
        self.grid_frame.columnconfigure(0, weight=1)
        for ci in range(1, 8):
            self.grid_frame.columnconfigure(ci, weight=2)

        # Create header row
        for col_idx, header in enumerate(headers):
            # Header frame
            header_frame = tk.Frame(
                self.grid_frame,
                bg=header_bg,
                height=40,
                relief='raised',
                borderwidth=1
            )
            header_frame.grid(row=0, column=col_idx, sticky='nsew')
            header_frame.pack_propagate(False)

            # Header label with click binding
            header_label = tk.Label(
                header_frame,
                text=header,
                bg=header_bg,
                fg='white',
                font=('Arial', 11, 'bold'),
                cursor='hand2'
            )
            header_label.pack(expand=True)

            # Bind click to highlight column (skip time column)
            if col_idx > 0:
                day_key = day_keys[col_idx]
                header_label.bind('<Button-1>', lambda e, day=day_key: self.highlight_day(day))

        # Create data rows
        for row_idx, row_data in enumerate(self.schedule_data):
            bg_color = even_row_bg if row_idx % 2 == 0 else odd_row_bg
            fg_color = '#000000' if row_idx % 2 == 0 else '#ffffff'

            for col_idx, cell_data in enumerate(row_data):
                # Check if this column should be highlighted
                day_key = day_keys[col_idx] if col_idx > 0 else None
                cell_bg = highlight_bg if day_key == self.highlighted_day else bg_color
                cell_fg = '#000000' if day_key == self.highlighted_day else fg_color

                # Cell frame
                cell_frame = tk.Frame(
                    self.grid_frame,
                    bg=cell_bg,
                    height=row_height,
                    relief='solid',
                    borderwidth=1
                )
                cell_frame.grid(row=row_idx + 1, column=col_idx, sticky='nsew')
                cell_frame.pack_propagate(False)

                # Cell label
                cell_label = tk.Label(
                    cell_frame,
                    text=cell_data,
                    bg=cell_bg,
                    fg=cell_fg,
                    font=('Arial', 10),
                    wraplength=120,
                    justify=tk.CENTER
                )
                cell_label.pack(expand=True)

                # Store reference for re-highlighting
                cell_frame.day_key = day_key
                cell_frame.default_bg = bg_color
                cell_frame.default_fg = fg_color

    def highlight_day(self, day):
        """Highlight entire column for the selected day"""
        # Toggle: if same day clicked, clear highlight
        if self.highlighted_day == day:
            self.highlighted_day = None
            self.status_label.config(text=f"Today: {datetime.now().strftime('%A')}")
        else:
            self.highlighted_day = day
            self.status_label.config(text=f"Filtering: {day.capitalize()}")

        # Re-render to apply highlighting
        self._render_schedule()

    def clear_highlight(self):
        """Clear day column highlighting"""
        self.highlighted_day = None
        self.status_label.config(text=f"Today: {datetime.now().strftime('%A')}")
        self._render_schedule()

    def _auto_highlight_today(self):
        """Automatically highlight today's column"""
        today = datetime.now().strftime('%A').lower()  # e.g., 'monday'

        # Only auto-highlight if it's a weekday
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        if today in valid_days:
            self.highlighted_day = today
            self.status_label.config(text=f"Today: {today.capitalize()} (Auto-highlighted)")
            self._render_schedule()

    def get_classes_for_day(self, day):
        """Get list of classes for a specific day"""
        import re

        day_index_map = {
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6,
            'sunday': 7
        }

        day_idx = day_index_map.get(day.lower())
        if day_idx is None:
            return []

        classes = []
        for row in self.schedule_data:
            if len(row) > day_idx:
                cell_content = row[day_idx].strip()
                if not cell_content or cell_content == "-":
                    continue

                # Skip day names and time stamps
                day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                if cell_content.lower() in day_names or re.match(r'^\d{1,2}:\d{2}', cell_content):
                    continue

                # Extract class codes from the cell content
                # Pattern 1: Class code in parentheses like "[student1] (SM2)" or "[student2],[student3] [student4]! (Genis+Phonics)"
                matches = re.findall(r'\(([^)]+)\)', cell_content)
                for match in matches:
                    # Clean up the match and extract class codes
                    for part in match.split(','):
                        class_code = part.strip()
                        # Check if it's a valid class code pattern
                        if re.match(r'^(SM\d+|Phonics\s*\d*|Beginner|IELTS|Elementary|Genis.*Phonics.*|Intermediate)$', class_code, re.IGNORECASE):
                            # Normalize the format to match student levels
                            class_code = re.sub(r'\s*\+\s*', ' + ', class_code)  # Normalize + spacing
                            if class_code not in classes:
                                classes.append(class_code)

                # Pattern 2: Class code at start like "SM2 [student5] & [student6]"
                words = cell_content.split()
                for word in words:
                    word_clean = word.strip('.,;:!?')
                    if re.match(r'^SM\d+$', word_clean, re.IGNORECASE):
                        if word_clean not in classes:
                            classes.append(word_clean)

        return classes

    # ---------- EXTRA LESSONS SECTION ----------

    def _build_extra_lessons_section(self, parent):
        """Build the Extra Lessons section below the weekly schedule."""
        section = tk.Frame(parent, bg=theme.colour('card', 'white'), relief='solid', borderwidth=2)
        section.pack(fill=tk.X, pady=(10, 0))

        # Section header
        band = theme.colour('side', self.colors.get('secondary', '#34495e'))   # dark, so its buttons show
        header = tk.Frame(section, bg=band, height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header, text="Extra Lessons",
            bg=band, fg='white',
            font=('Arial', 11, 'bold'), padx=15
        ).pack(side=tk.LEFT, pady=8)

        btn_frame = tk.Frame(header, bg=band)
        btn_frame.pack(side=tk.RIGHT, padx=5, pady=5)

        theme.flat_button(
            btn_frame, 'primary', text="+ Add Extra Lesson",
            bg=self.colors.get('success', '#27ae60'), fg='white',
            font=('Arial', 9), padx=10, pady=2,
            command=self._open_add_extra_lesson_dialog
        ).pack(side=tk.LEFT, padx=3)

        theme.flat_button(
            btn_frame, 'danger', text="Delete Selected",
            bg=self.colors.get('danger', '#e74c3c'), fg='white',
            font=('Arial', 9), padx=10, pady=2,
            command=self._delete_selected_extra_lesson
        ).pack(side=tk.LEFT, padx=3)

        # Treeview for extra lessons list
        tree_frame = tk.Frame(section, bg=theme.colour('card', 'white'))
        tree_frame.pack(fill=tk.X, padx=5, pady=5)

        cols = ('id', 'date', 'time', 'label', 'level', 'students')
        self.extra_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=6)
        self.extra_tree.heading('id', text='ID')
        self.extra_tree.heading('date', text='Date')
        self.extra_tree.heading('time', text='Time')
        self.extra_tree.heading('label', text='Label')
        self.extra_tree.heading('level', text='Level')
        self.extra_tree.heading('students', text='Students')

        self.extra_tree.column('id', width=40, anchor='center')
        self.extra_tree.column('date', width=100, anchor='center')
        self.extra_tree.column('time', width=120, anchor='center')
        self.extra_tree.column('label', width=200)
        self.extra_tree.column('level', width=80, anchor='center')
        self.extra_tree.column('students', width=60, anchor='center')

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.extra_tree.yview)
        self.extra_tree.configure(yscrollcommand=scrollbar.set)
        self.extra_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_extra_lessons()

    def _refresh_extra_lessons(self):
        """Reload the extra lessons treeview."""
        if not self.models:
            return
        for item in self.extra_tree.get_children():
            self.extra_tree.delete(item)

        # Show upcoming + recent (last 7 days)
        today = datetime.now().strftime("%Y-%m-%d")
        past = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        try:
            from inventory.db import get_connection
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM extra_lesson WHERE lesson_date >= ? ORDER BY lesson_date, start_time",
                (past,),
            )
            rows = cur.fetchall()
            conn.close()

            for row in rows:
                r = dict(row)
                students = self.models.get_students_for_extra_lesson(r['id'])
                self.extra_tree.insert('', 'end', values=(
                    r['id'],
                    r['lesson_date'],
                    f"{r['start_time']} - {r['end_time']}",
                    r['label'],
                    r.get('level', '') or '',
                    len(students),
                ))
        except Exception:
            pass

    def _delete_selected_extra_lesson(self):
        """Delete the selected extra lesson after confirmation."""
        sel = self.extra_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an extra lesson to delete.")
            return
        values = self.extra_tree.item(sel[0], 'values')
        lesson_id = int(values[0])
        label = values[3]
        if not messagebox.askyesno("Confirm Delete", f"Delete extra lesson \"{label}\" (ID {lesson_id})?"):
            return
        self.models.delete_extra_lesson(lesson_id)
        self._refresh_extra_lessons()

    def _open_add_extra_lesson_dialog(self):
        """Open a dialog to create a new extra lesson and assign students."""
        dlg = tk.Toplevel(self.parent)
        dlg.title("Add Extra Lesson")
        dlg.geometry("700x620")
        dlg.resizable(True, True)
        dlg.grab_set()

        bg = self.colors.get('light', '#f5f5f5')
        dlg.configure(bg=bg)

        # --- Top form fields ---
        form = tk.Frame(dlg, bg=bg)
        form.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        tk.Label(form, text="Date (YYYY-MM-DD):", bg=bg, font=('Arial', 10)).grid(row=row, column=0, sticky='w', pady=2)
        date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        tk.Entry(form, textvariable=date_var, width=14, font=('Arial', 10)).grid(row=row, column=1, sticky='w', padx=5)

        row += 1
        tk.Label(form, text="Start Time (HH:MM):", bg=bg, font=('Arial', 10)).grid(row=row, column=0, sticky='w', pady=2)
        start_var = tk.StringVar()
        tk.Entry(form, textvariable=start_var, width=8, font=('Arial', 10)).grid(row=row, column=1, sticky='w', padx=5)

        tk.Label(form, text="End Time (HH:MM):", bg=bg, font=('Arial', 10)).grid(row=row, column=2, sticky='w', pady=2, padx=(10, 0))
        end_var = tk.StringVar()
        tk.Entry(form, textvariable=end_var, width=8, font=('Arial', 10)).grid(row=row, column=3, sticky='w', padx=5)

        row += 1
        tk.Label(form, text="Label:", bg=bg, font=('Arial', 10)).grid(row=row, column=0, sticky='w', pady=2)
        label_var = tk.StringVar()
        tk.Entry(form, textvariable=label_var, width=30, font=('Arial', 10)).grid(row=row, column=1, columnspan=3, sticky='w', padx=5)

        row += 1
        tk.Label(form, text="Level (optional):", bg=bg, font=('Arial', 10)).grid(row=row, column=0, sticky='w', pady=2)
        level_var = tk.StringVar()
        # Gather existing levels from class_def for the dropdown
        level_values = ['']
        try:
            class_defs = self.models.list_class_defs(active_only=True)
            seen = set()
            for cd in class_defs:
                lv = cd.get('level', '')
                if lv and lv not in seen:
                    seen.add(lv)
                    level_values.append(lv)
        except Exception:
            pass
        level_combo = ttk.Combobox(form, textvariable=level_var, values=level_values, width=12, font=('Arial', 10))
        level_combo.grid(row=row, column=1, sticky='w', padx=5)

        row += 1
        tk.Label(form, text="Notes (optional):", bg=bg, font=('Arial', 10)).grid(row=row, column=0, sticky='w', pady=2)
        notes_var = tk.StringVar()
        tk.Entry(form, textvariable=notes_var, width=40, font=('Arial', 10)).grid(row=row, column=1, columnspan=3, sticky='w', padx=5)

        # --- Copy from class shortcut ---
        row += 1
        tk.Label(form, text="Copy from class:", bg=bg, font=('Arial', 10)).grid(row=row, column=0, sticky='w', pady=2)
        copy_class_var = tk.StringVar()
        class_options = ['']
        class_map = {}
        try:
            for cd in (class_defs if 'class_defs' in dir() else self.models.list_class_defs(active_only=True)):
                day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                day_str = day_names[cd['day_of_week']] if 0 <= cd['day_of_week'] <= 6 else '?'
                display = f"{cd['class_name']} ({day_str} {cd['start_time']}-{cd['end_time']})"
                class_options.append(display)
                class_map[display] = cd['class_id']
        except Exception:
            pass

        # --- Student picker: two-list transfer ---
        picker_frame = tk.LabelFrame(dlg, text="Assign Students", bg=bg, font=('Arial', 10, 'bold'))
        picker_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left: available students
        left_frame = tk.Frame(picker_frame, bg=bg)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Filter by level
        filter_frame = tk.Frame(left_frame, bg=bg)
        filter_frame.pack(fill=tk.X)
        tk.Label(filter_frame, text="Filter level:", bg=bg, font=('Arial', 9)).pack(side=tk.LEFT)
        filter_var = tk.StringVar()
        filter_combo = ttk.Combobox(filter_frame, textvariable=filter_var, values=level_values, width=10, font=('Arial', 9))
        filter_combo.pack(side=tk.LEFT, padx=3)

        tk.Label(left_frame, text="Available Students", bg=bg, font=('Arial', 9, 'bold')).pack()
        avail_listbox = tk.Listbox(left_frame, selectmode=tk.EXTENDED, font=('Arial', 9), height=12)
        avail_listbox.pack(fill=tk.BOTH, expand=True)

        # Middle: buttons
        mid_frame = tk.Frame(picker_frame, bg=bg)
        mid_frame.pack(side=tk.LEFT, padx=5, pady=5)

        tk.Button(mid_frame, text="Add →", width=10, command=lambda: _add_students()).pack(pady=3)
        tk.Button(mid_frame, text="← Remove", width=10, command=lambda: _remove_students()).pack(pady=3)

        # Right: assigned students
        right_frame = tk.Frame(picker_frame, bg=bg)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(right_frame, text="Assigned Students", bg=bg, font=('Arial', 9, 'bold')).pack()
        assigned_listbox = tk.Listbox(right_frame, selectmode=tk.EXTENDED, font=('Arial', 9), height=12)
        assigned_listbox.pack(fill=tk.BOTH, expand=True)

        # Internal data. avail_ids / assigned_rows hold the student ID of every row in the two lists, by row number:
        # a row is mapped back by its position, never by its text (two students can have the same name and level).
        all_students = []
        assigned_ids = set()
        avail_ids = []
        assigned_rows = []

        def _load_all_students():
            nonlocal all_students
            try:
                all_students = [s for s in self.models.list_students() if s.get('status') == 'active']
            except Exception as e:
                all_students = []
                messagebox.showerror("Students", f"Could not load the student list:\n{e}\n\n"
                                                 "You can still save the lesson, but no students can be added.",
                                     parent=dlg)

        def _refresh_available():
            avail_listbox.delete(0, tk.END)
            del avail_ids[:]
            level_filter = filter_var.get().strip()
            for s in all_students:
                if s['student_id'] in assigned_ids:
                    continue
                if level_filter and (s.get('level') or '').lower() != level_filter.lower():
                    continue
                display = f"{self.models.display_name(s)} [{s.get('level') or ''}]"
                avail_listbox.insert(tk.END, display)
                avail_ids.append(s['student_id'])

        def _refresh_assigned():
            assigned_listbox.delete(0, tk.END)
            del assigned_rows[:]
            for s in all_students:
                if s['student_id'] in assigned_ids:
                    display = f"{self.models.display_name(s)} [{s.get('level') or ''}]"
                    assigned_listbox.insert(tk.END, display)
                    assigned_rows.append(s['student_id'])

        def _add_students():
            for idx in avail_listbox.curselection():
                if idx < len(avail_ids):
                    assigned_ids.add(avail_ids[idx])
            _refresh_available()
            _refresh_assigned()

        def _remove_students():
            for sid in [assigned_rows[idx] for idx in assigned_listbox.curselection() if idx < len(assigned_rows)]:
                assigned_ids.discard(sid)
            _refresh_available()
            _refresh_assigned()

        def _copy_from_class(*args):
            display = copy_class_var.get()
            cid = class_map.get(display)
            if not cid:
                return
            try:
                roster = self.models.get_roster_for_class(cid)
                for entry in roster:
                    assigned_ids.add(entry['student_id'])
                _refresh_available()
                _refresh_assigned()
            except Exception:
                pass

        copy_combo = ttk.Combobox(form, textvariable=copy_class_var, values=class_options, width=40, font=('Arial', 9))
        copy_combo.grid(row=row, column=1, columnspan=3, sticky='w', padx=5)
        copy_class_var.trace_add('write', _copy_from_class)

        filter_var.trace_add('write', lambda *a: _refresh_available())

        _load_all_students()
        _refresh_available()

        # --- Save / Cancel ---
        btn_bar = tk.Frame(dlg, bg=bg)
        btn_bar.pack(fill=tk.X, padx=10, pady=8)

        def _save():
            lbl = label_var.get().strip()
            dt = date_var.get().strip()
            st = start_var.get().strip()
            et = end_var.get().strip()

            if not lbl:
                messagebox.showwarning("Missing", "Label is required.", parent=dlg)
                return
            if not dt or not st or not et:
                messagebox.showwarning("Missing", "Date, start time, and end time are required.", parent=dlg)
                return
            # The same checks the model makes, so the user is told before anything is saved
            try:
                self.models.parse_session_date(dt)
            except ValueError:
                messagebox.showwarning("Invalid Date", "Date must be YYYY-MM-DD.", parent=dlg)
                return
            try:
                self.models.check_class_times(st, et)
            except self.models.ValidationError as e:
                messagebox.showwarning("Check the time", str(e), parent=dlg)
                return

            allow_past = False
            if self.models.is_past_date(dt):
                if not messagebox.askyesno(
                        "Past date", f"{dt} is in the past.\n\nSave an extra lesson on a date that has already gone?",
                        icon='warning', parent=dlg):
                    return
                allow_past = True

            try:
                conflicts = self.models.extra_lesson_conflicts(dt, st, et)
            except Exception as e:
                messagebox.showerror("Error", f"Could not check for overlaps:\n{e}", parent=dlg)
                return
            if conflicts:
                lines = []
                for c in conflicts:
                    what = f"class {c['id']}" if c['kind'] == 'class' else f"extra lesson {c['id']}"
                    when = "time cannot be read" if c['unreadable'] else f"{c['start_time']}-{c['end_time']}"
                    line = f"  \u2022  {what}  \"{c['label']}\"  ({when})"
                    if c['kind'] == 'extra':
                        line += f"\n      against this one alone, recordings go to extra lesson {c['id']} (it was made first)"
                    lines.append(line)
                # Window by window, because the winner can change inside one overlap (a class and an earlier extra lesson,
                # or two extra lessons that end at different times)
                footer_lines = []
                for seg in self.models.extra_lesson_recording_split(st, et, conflicts):
                    if seg['owner'] is None:
                        who = "recordings are filed under this extra lesson"
                    else:
                        who = f"recordings go to extra lesson {seg['owner']} \"{seg['label']}\", not to this one"
                    footer_lines.append(f"  {seg['from']}-{seg['to']}: {who}")
                if any(c['unreadable'] for c in conflicts):
                    footer_lines.append("  A lesson whose time cannot be read may overlap too; who gets those recordings "
                                        "cannot be worked out.")
                footer = "In the overlap:\n" + "\n".join(footer_lines)
                if not messagebox.askyesno(
                        "Overlap",
                        f"This extra lesson overlaps:\n\n" + "\n".join(lines) + "\n\n" + footer + "\n\nSave anyway?",
                        icon='warning', parent=dlg):
                    return

            # The students that will actually be saved (active, and in the list that was loaded), not assigned_ids:
            # if the student list failed to load, "Copy from class" fills assigned_ids but nothing can be saved.
            picked = [s['student_id'] for s in all_students if s['student_id'] in assigned_ids]
            if not picked and not messagebox.askyesno(
                    "No students", "No students will be saved with this extra lesson.\n\nSave it anyway?",
                    icon='warning', parent=dlg):
                return

            lv = level_var.get().strip() or None
            nt = notes_var.get().strip() or None

            # The lesson and all its students are saved together, or not at all
            try:
                self.models.create_extra_lesson(lbl, dt, st, et, level=lv, notes=nt,
                                                student_ids=picked, allow_past=allow_past)
            except Exception as e:
                messagebox.showerror("Could not save", f"{e}", parent=dlg)
                return

            dlg.destroy()
            self._refresh_extra_lessons()

        theme.flat_button(
            btn_bar, 'primary', text="Save", bg=self.colors.get('success', '#27ae60'), fg='white',
            font=('Arial', 10, 'bold'), padx=20, pady=4, command=_save
        ).pack(side=tk.RIGHT, padx=5)

        theme.flat_button(
            btn_bar, 'secondary', text="Cancel", bg=self.colors.get('danger', '#e74c3c'), fg='white',
            font=('Arial', 10), padx=15, pady=4, command=dlg.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def get_students_for_date(self, session_date):
        """
        Get list of student IDs scheduled for a specific date.

        Args:
            session_date: Date string in ISO format (YYYY-MM-DD)

        Returns:
            List of student IDs whose level/class matches the schedule for that day
        """
        # Check if schedule is loaded
        if not self.schedule_data or (len(self.schedule_data) == 1 and "No schedule found" in str(self.schedule_data[0])):
            return []

        # Convert date to day name
        try:
            from datetime import datetime as dt
            date_obj = dt.fromisoformat(session_date)
            day_name = date_obj.strftime('%A').lower()  # e.g., 'monday'
        except:
            return []

        # Get classes scheduled for this day
        classes_today = self.get_classes_for_day(day_name)

        if not classes_today:
            return []

        # Get all students whose level matches one of today's classes
        if not self.models:
            return []

        try:
            all_students = self.models.list_students()

            scheduled_student_ids = []
            for student in all_students:
                student_level = (student.get('level') or '').strip()
                # Check if student's level matches any of today's classes
                for class_name in classes_today:
                    if student_level and class_name and student_level.lower() == class_name.lower():
                        scheduled_student_ids.append(student['student_id'])
                        break

            return scheduled_student_ids
        except Exception:
            return []
