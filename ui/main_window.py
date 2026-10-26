import datetime
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from shutil import copy2
from typing import Optional
from datetime import date, datetime, timezone

from PIL import Image, ImageTk  # for student photo preview

from inventory.db import DB_PATH
from inventory import models, qr_utils, runmode, events as event_bus
from inventory.validation import ValidationError
from inventory import auth
from ui.tutorial_system_simple import SimpleTutorialManager
from ui.schedule_tab import ScheduleTab
from ui import theme
from ui import design_system as ds
from ui.side_menu import SideMenu, build_panel, WIDTH as SIDE_MENU_WIDTH
from ui import attendance_cards

# Paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STUDENT_PHOTOS_DIR = DATA_DIR / "photos" / "students"
STUDENT_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
_CTEST_MAIN = ROOT.parent / "c_test_app" / "main.py"
_CTEST_DB = ROOT.parent / "c_test_app" / "data" / "c_test.db"

# Translation dictionary
TRANSLATIONS = {
    "EN": {
        # Tabs
        "students": "Students",
        "items": "Items",
        "books": "Books",
        "attendance": "Attendance",
        "schedule": "Schedule",
        "roster": "Roster",
        "lessons": "Lessons",
        "system": "System",
        "admin_log": "Admin Log",
        "dev_login": "Dev Login",
        
        # Menu
        "file": "File",
        "data": "Data",
        "qr": "QR",
        "view": "View",
        "backup_now": "Backup Now",
        "change_passwords": "Change passwords…",
        "logout": "Logout",
        "exit": "Exit",
        "import_students": "📥 Import Students from CSV",
        "export_items": "Export Items to CSV",
        "export_students": "Export Students to CSV",
        "export_assignments": "Export Assignments to CSV",
        "export_attendance": "Export Attendance (date shown)…",
        "scan_qr": "Lend by scan: book, then student card…",          # QR menu: book, then card (5c, decision 4)
        "scan_student_card": "Scan student card",                      # Books tab button: picks a student
        "open_scan": "Open Scan Mode",
        "generate_items_qr": "Generate QR for All Items",
        "generate_students_qr": "Generate QR for All Students",
        "toggle_dark": "Toggle Dark Mode",
        "english": "🌐 English",
        "thai": "🌐 ไทย (Thai)",
        
        # Common buttons
        "search": "Search",
        "clear": "Clear",
        "last_mark": "Last mark",
        "all_dates": "All dates",
        "refresh": "Refresh",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "save": "Save",
        "cancel": "Cancel",
        "close": "Close",
        "today": "Today",
        "filter": "Filter",
        "all_fields": "All Fields",
        
        # Specific buttons
        "add_student": "➕ Add Student",
        "add_item": "➕ Add Item",
        "add_book": "➕ Assign Book",
        "scan_qr_btn": "📷 Scan QR",
        "download_csv": "📥 Download Books CSV",
        "import_csv": "📤 Import Books CSV",
        "load_schedule": "📥 Load Schedule",
        "manual_entry": "✏️ Manual Entry",
        "clear_filter": "Clear Filter",
        "fullscreen": "Fullscreen",
        "mass_delete": "Mass Delete Students",
        "unlock": "Unlock",
        "import_books_csv": "Import Loans CSV",
        "scan_book": "Scan Book to Register",
        "book_assignments": "Book Loans (out and returned)",
        "book_id": "Book ID",
        "book": "Book",
        "weekly_schedule": "Weekly Class Schedule",
        "monday": "Monday",
        "tuesday": "Tuesday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
        "friday": "Friday",
        "saturday": "Saturday",
        "sunday": "Sunday",
        
        # Headers
        "daily_attendance": "📋 Daily Attendance",
        "student_list": "📋 Student List",
        "student_id": "Student ID",
        "first_name": "First Name",
        "last_name": "Last Name",
        "name": "Name",
        "level": "Level",
        "status": "Status",
        "timestamp": "Timestamp",
        "action": "Action",
        "entity_type": "Entity Type",
        "entity_id": "Entity ID",
        "details": "Details",
        "context": "Context",
        "qr_code": "QR Code",
        "student": "Student",
        "item": "Item",
        
        # Column headers
        "item_id": "Item ID",
        "category": "Category",
        "location": "Location",
        "total": "Total",
        "available": "Available",
        "assigned_date": "Assigned Date",
        "returned_date": "Returned Date",
        
        # Footer
        "settings": "⚙ Settings",
        
        # Messages
        "language_en": "Language set to English",
        "language_th": "ภาษาเปลี่ยนเป็นภาษาไทย\nLanguage set to Thai",
    },
    "TH": {
        # Tabs
        "students": "นักเรียน",
        "items": "สิ่งของ",
        "books": "หนังสือ",
        "attendance": "เช็คชื่อ",
        "schedule": "ตารางเรียน",
        "roster": "รายชื่อ",
        "lessons": "บทเรียน",
        "system": "ระบบ",
        "admin_log": "บันทึกผู้ดูแล",
        "dev_login": "เข้าสู่ระบบผู้พัฒนา",
        
        # Menu
        "file": "ไฟล์",
        "data": "ข้อมูล",
        "qr": "คิวอาร์",
        "view": "มุมมอง",
        "backup_now": "สำรองข้อมูลทันที",
        "change_passwords": "เปลี่ยนรหัสผ่าน…",
        "logout": "ออกจากระบบ",
        "exit": "ออกจากโปรแกรม",
        "import_students": "📥 นำเข้านักเรียนจาก CSV",
        "export_items": "ส่งออกสิ่งของเป็น CSV",
        "export_students": "ส่งออกนักเรียนเป็น CSV",
        "export_assignments": "ส่งออกการมอบหมายเป็น CSV",
        "export_attendance": "ส่งออกการเช็คชื่อ (วันที่แสดง)…",
        "scan_qr": "ยืมด้วยการสแกน: หนังสือ แล้วบัตรนักเรียน…",
        "scan_student_card": "สแกนบัตรนักเรียน",
        "open_scan": "เปิดโหมดสแกน",
        "generate_items_qr": "สร้าง QR สำหรับสิ่งของทั้งหมด",
        "generate_students_qr": "สร้าง QR สำหรับนักเรียนทั้งหมด",
        "toggle_dark": "สลับโหมดมืด",
        "english": "🌐 English",
        "thai": "🌐 ไทย (Thai)",
        
        # Common buttons
        "search": "ค้นหา",
        "clear": "ล้าง",
        "last_mark": "การเช็คชื่อล่าสุด",
        "all_dates": "ทุกวัน",
        "refresh": "รีเฟรช",
        "add": "เพิ่ม",
        "edit": "แก้ไข",
        "delete": "ลบ",
        "save": "บันทึก",
        "cancel": "ยกเลิก",
        "close": "ปิด",
        "today": "วันนี้",
        "filter": "กรอง",
        "all_fields": "ทุกฟิลด์",
        
        # Specific buttons
        "add_student": "➕ เพิ่มนักเรียน",
        "add_item": "➕ เพิ่มสิ่งของ",
        "add_book": "➕ มอบหมายหนังสือ",
        "scan_qr_btn": "📷 สแกน QR",
        "download_csv": "📥 ดาวน์โหลด CSV หนังสือ",
        "import_csv": "📤 นำเข้า CSV หนังสือ",
        "load_schedule": "📥 โหลดตารางเรียน",
        "manual_entry": "✏️ กรอกข้อมูลด้วยตนเอง",
        "clear_filter": "ล้างตัวกรอง",
        "fullscreen": "เต็มจอ",
        "mass_delete": "ลบนักเรียนหลายคน",
        "unlock": "ปลดล็อค",
        "import_books_csv": "นำเข้า CSV การยืม",
        "scan_book": "สแกนหนังสือเพื่อลงทะเบียน",
        "book_assignments": "รายการยืม-คืนหนังสือ",
        "book_id": "รหัสหนังสือ",
        "book": "หนังสือ",
        "weekly_schedule": "ตารางเรียนประจำสัปดาห์",
        "monday": "จันทร์",
        "tuesday": "อังคาร",
        "wednesday": "พุธ",
        "thursday": "พฤหัสบดี",
        "friday": "ศุกร์",
        "saturday": "เสาร์",
        "sunday": "อาทิตย์",
        
        # Headers
        "daily_attendance": "📋 เช็คชื่อประจำวัน",
        "student_list": "📋 รายชื่อนักเรียน",
        "student_id": "รหัสนักเรียน",
        "first_name": "ชื่อ",
        "last_name": "นามสกุล",
        "name": "ชื่อ",
        "level": "ระดับ",
        "status": "สถานะ",
        "timestamp": "เวลา",
        "action": "การกระทำ",
        "entity_type": "ประเภทเอนทิตี้",
        "entity_id": "รหัสเอนทิตี้",
        "details": "รายละเอียด",
        "context": "บริบท",
        "qr_code": "คิวอาร์โค้ด",
        "student": "นักเรียน",
        "item": "สิ่งของ",
        
        # Column headers
        "item_id": "รหัสสิ่งของ",
        "category": "หมวดหมู่",
        "location": "ที่ตั้ง",
        "total": "ทั้งหมด",
        "available": "ว่าง",
        "assigned_date": "วันที่มอบหมาย",
        "returned_date": "วันที่คืน",
        
        # Footer
        "settings": "⚙ ตั้งค่า",
        
        # Messages
        "language_en": "Language set to English",
        "language_th": "ภาษาเปลี่ยนเป็นภาษาไทย\nLanguage set to Thai",
    }
}

# Theme colors
LIGHT_THEME = {
    "bg": "#ffffff",
    "fg": "#000000",
    "selectbg": "#0078d7",
    "selectfg": "#ffffff",
}

DARK_THEME = {
    "bg": "#2d2d2d",
    "fg": "#e0e0e0",
    "selectbg": "#0078d7",
    "selectfg": "#ffffff",
}

COLORS = {
    'primary': '#2c3e50',
    'secondary': '#3498db',
    'success': '#27ae60',
    'danger': '#e74c3c',
    'warning': '#f39c12',
    'light': '#ecf0f1',
    'dark': '#34495e',
    'white': '#ffffff',
}
if not theme.CLASSIC:
    # New look N1: the same keys on the house tokens (ui/design_system.py HOUSE). Classic keeps the values above.
    COLORS = {
        'primary': theme.HOUSE['side'],         # the dark header bands
        'secondary': theme.HOUSE['primary'],
        'success': theme.HOUSE['primary'],
        'danger': theme.HOUSE['danger'],
        'warning': theme.HOUSE['warning'],
        'light': theme.HOUSE['ground'],
        'dark': theme.HOUSE['ink'],
        'white': theme.HOUSE['card'],
    }

def _parse_att_date(text):
    """The Date-box text as a date, or None. The check itself is models.parse_session_date, the one used everywhere."""
    try:
        return models.parse_session_date((text or "").strip())
    except ValueError:
        return None


def _card_student_id(text):
    """A scanned or typed student code as a student ID: trimmed, a leading 'S:' (any case) dropped, and only letters,
    digits and . - _ kept (scanner artefacts such as a stray symbol go). A bare typed ID comes back as it is."""
    text = (text or "").strip()
    if text[:2].upper() == "S:":
        text = text[2:].strip()
    return ''.join(c for c in text if c.isalnum() or c in '.-_')


def _card_item_id(text):
    """A scanned book code as an item ID, or None if it does not start with 'I:' (any case). Cleaned as student IDs."""
    text = (text or "").strip()
    if text[:2].upper() != "I:":
        return None
    return ''.join(c for c in text[2:].strip() if c.isalnum() or c in '.-_')


def _plural(n, word):
    """'1 error', '2 errors'."""
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _local_time(text):
    """A time stored by SQLite's datetime('now') or CURRENT_TIMESTAMP ('YYYY-MM-DD HH:MM:SS', UTC), shown in this PC's
    local time. Anything else (a date only, another form) is shown as stored. Display only: nothing stored changes."""
    try:
        stamp = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return text or ""
    return stamp.replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


# What the Attendance list shows for a student with no mark on the date shown (never "absent": absent is a mark).
NOT_MARKED = "— not marked"
NO_CURRENT_STUDENT = "(no current student)"    # a mark whose student ID has no student row


def _rename_student_extras(old, new, ctest_db=None, photos_dir=None):
    """After a student rename has committed: move the photo, and update c_test.db in its own transaction.

    Safe to run again: it only does what is still missing and never moves anything twice.
    Never raises. Returns {"photo": file name or None, "photo_state": "moved" | "already" | "none",
    "ctest": {table: rows moved}, "errors": [text]}.
    """
    import sqlite3 as _sql
    ctest_db = Path(ctest_db) if ctest_db else _CTEST_DB
    photos_dir = Path(photos_dir) if photos_dir else STUDENT_PHOTOS_DIR
    out = {"photo": None, "photo_state": "none", "ctest": {}, "errors": []}
    for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
        src = photos_dir / f"{old}{ext}"
        dst = photos_dir / f"{new}{ext}"
        if src.exists():
            if dst.exists():
                out["errors"].append(f"Photo not renamed: {dst.name} already exists next to {src.name}.")
            else:
                try:
                    src.rename(dst)
                    out["photo"], out["photo_state"] = dst.name, "moved"
                except OSError as e:
                    out["errors"].append(f"Photo not renamed: {e}")
            break
        if dst.exists():  # done by an earlier run
            out["photo"], out["photo_state"] = dst.name, "already"
            break
    if ctest_db.exists():
        conn = _sql.connect(str(ctest_db), timeout=3)
        try:
            present = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            conn.execute("BEGIN")
            for table, col in (("c_test_results", "student_id"), ("cefr_suggestions", "student_id"),
                               ("temp_sessions", "claimed_by_student_id"), ("students_cache", "student_id")):
                if table not in present:
                    continue
                if table == "students_cache" and conn.execute(
                        "SELECT 1 FROM students_cache WHERE student_id = ?", (new,)).fetchone():
                    # the new ID is already cached (C-Test's own loading did it): drop the old row instead
                    out["ctest"][table] = conn.execute(
                        "DELETE FROM students_cache WHERE student_id = ?", (old,)).rowcount
                else:
                    out["ctest"][table] = conn.execute(
                        f"UPDATE {table} SET {col} = ? WHERE {col} = ?", (new, old)).rowcount
            conn.commit()
        except Exception as e:
            conn.rollback()
            out["ctest"] = {}
            text = str(e).lower()
            if isinstance(e, _sql.OperationalError) and ("locked" in text or "busy" in text):
                out["errors"].append(
                    "c_test.db is busy or locked (is C-Test open?). Close C-Test, then run Rename student... again "
                    "with the same two IDs. Nothing was changed in c_test.db.")
            else:
                out["errors"].append(f"c_test.db was not updated: {e}")
        finally:
            conn.close()
    try:
        import json as _json
        models.log_admin_action(
            "RENAME_FOLLOWUP", "student", entity_id=new,
            details=_json.dumps({"old": old, "new": new,
                                 "photo": {"state": out["photo_state"], "file": out["photo"]},
                                 "ctest": {t: n for t, n in out["ctest"].items() if n},
                                 "errors": out["errors"]}, ensure_ascii=False),
            status="failed" if out["errors"] else "success")
    except Exception as e:
        print(f"Warning: Failed to log the rename follow-up: {e}")
    return out


def _report_rename_extras(title, old, new, extras):
    """Tell the user exactly what the second step did and what is left."""
    done = [f"The student ID change ('{old}' to '{new}') is complete in the database."]
    if extras["photo_state"] == "moved":
        done.append(f"Photo renamed to {extras['photo']}.")
    elif extras["photo_state"] == "already":
        done.append(f"Photo was already named {extras['photo']}.")
    moved = {t: n for t, n in extras["ctest"].items() if n}
    if moved:
        done.append("C-Test rows updated: " + ", ".join(f"{t} {n}" for t, n in moved.items()) + ".")
    if extras["errors"]:
        messagebox.showerror(title, "\n".join(
            done + ["", "NOT DONE:"] + [f"  {e}" for e in extras["errors"]]
            + ["", "To finish, choose Rename student... again with the same two IDs. "
                   "It only does what is still missing."]))
    else:
        done.append(f"Reprint the QR card: it still says S:{old}.")
        messagebox.showinfo(title, "\n".join(done))


def _ctest_panel_data(conn, student_id):
    """What the C-Test Placement panel shows for a student (B4-3), read through `conn` (rows by name).

    level, percentage, date, result_id: the newest result. A run saves a Part 1 row, a Part 2 row and then its
    final row (variant ADAPTIVE), so the newest row of a current run is the final one. For an older run whose final
    row was never recorded the newest row is a Part row (variant P1_* or P2_*): it is shown, with
    final_recorded False.
    banner: the newest pending suggestion linked to that result (result_id equals its id), else None.
    older: the other pending suggestions, newest first (unlinked, or linked to an older result).
    history: up to 5 rows, final and single-passage rows first, then Part rows.
    Superseded, confirmed and dismissed suggestions are never listed.
    """
    sid = str(student_id)
    is_part = ("(COALESCE(variant, '') LIKE 'P1\\_%' ESCAPE '\\' "
               "OR COALESCE(variant, '') LIKE 'P2\\_%' ESCAPE '\\')")
    latest = conn.execute(
        f"""SELECT id, test_date, placement_level, percentage, {is_part} AS is_part
            FROM c_test_results WHERE student_id = ? AND COALESCE(deleted, 0) = 0
            ORDER BY test_date DESC, id DESC LIMIT 1""", (sid,)).fetchone()
    history = conn.execute(
        f"""SELECT id, test_date, placement_level, percentage, {is_part} AS is_part
            FROM c_test_results WHERE student_id = ? AND COALESCE(deleted, 0) = 0
            ORDER BY is_part, test_date DESC, id DESC LIMIT 5""", (sid,)).fetchall()
    try:
        pending = conn.execute(
            """SELECT id, suggested_band, result_id FROM cefr_suggestions
               WHERE student_id = ? AND status = 'pending_review'
               ORDER BY created_at DESC, id DESC""", (sid,)).fetchall()
    except Exception:
        pending = []
    banner, older = None, []
    for row in pending:
        entry = {"id": row["id"], "band": row["suggested_band"], "result_id": row["result_id"]}
        if banner is None and latest is not None and row["result_id"] == latest["id"]:
            banner = entry
        else:
            older.append(entry)
    return {
        "level": latest["placement_level"] if latest else None,
        "percentage": (latest["percentage"] or 0) if latest else None,
        "date": (latest["test_date"] or "")[:10] if latest else "",
        "result_id": latest["id"] if latest else None,
        "final_recorded": bool(latest) and not latest["is_part"],
        "banner": banner,
        "older": older,
        "history": [{"id": r["id"], "date": (r["test_date"] or "")[:10], "level": r["placement_level"],
                     "percentage": r["percentage"] or 0, "is_part": bool(r["is_part"])} for r in history],
    }


class MainWindow(tk.Tk):
    # How often a running C-Test is checked, in milliseconds (B4-2)
    _CTEST_POLL_MS = 2000

    def __init__(self):
        super().__init__()

        if runmode.PRACTICE_MODE:
            self.title("NestMind Portal — PRACTICE")
        else:
            self.title("NestMind Portal — TEST MODE" if runmode.TEST_MODE else "NestMind Portal")

        # Style / theme. Must come before any pixel geometry so that
        # theme.scale() is live. Returns a plain ttk.Style in classic mode.
        self.style = theme.init_root(self)

        if theme.CLASSIC:
            self.geometry(f"{theme.scale(1150)}x{theme.scale(680)}")
        else:
            # The side panel's width is added, so every page keeps today's 1150 px (N2 addendum E-c); the window
            # never opens wider or taller than the screen (David, 20 Oct).
            width = min(theme.scale(1150) + theme.scale(SIDE_MENU_WIDTH), self.winfo_screenwidth())
            self.geometry(f"{width}x{min(theme.scale(680), self.winfo_screenheight())}")
        self.state('zoomed')  # Maximize window by default
        
        # Language setting - initialize FIRST
        self.current_language = tk.StringVar(value="EN")
        
        self.dark_mode = False
        self._apply_theme(self.dark_mode)

        # Scan mode state
        self.scan_window: Optional[tk.Toplevel] = None
        self.scan_entry: Optional[ttk.Entry] = None
        self.scan_log_widget: Optional[tk.Listbox] = None
        self.scan_last_student_id: Optional[str] = None
        self.scan_last_item_id: Optional[str] = None
        self.scan_last_student_name: Optional[str] = None     # for the log only (5c)
        self.scan_last_item_name: Optional[str] = None

        # Set by Logout; app.py then shows the login window again (B5b-4). Exit and the window's X leave it False.
        self.logged_out = False

        # Attendance UI refs
        self.att_date_var: Optional[tk.StringVar] = None
        self.att_tree: Optional[ttk.Treeview] = None
        self._att_view = ("records",)   # what the list shows: ("day",), ("class", id), ("search",) or ("records",)
        self._att_ids = {}              # tree row -> student ID, as the string that was stored ("0042", not 42)
        self._att_shown_date = None     # the date the rows on screen were drawn for
        self._att_blank_meant_today = True   # the Date box was emptied while today was shown (the tick follows midnight)
        self._att_reloading = False
        self._att_last_visible = False  # whether the "Last mark" column is shown (search view only)
        self._att_tick_id = None
        self.att_strip = None           # the lessons strip (N3), filled from _att_day_cards()
        self._att_cards = []            # the cards the strip shows now
        self.att_scan_entry = None      # the page's scan box (N3): the first focusable widget of the page
        self.att_bar_note = None        # the marks bar's note (N3)
        self._att_cancel_btn = None     # Cancel a lesson, in the band (N3)

        # A running C-Test, so its end can refresh the panel (B4-2): the process, its student, one poll job
        self._ctest_proc = None
        self._ctest_proc_sid = None
        self._ctest_poll_job = None

        # Student photo UI refs
        self.student_photo_label: Optional[ttk.Label] = None
        self.student_photo_image: Optional[ImageTk.PhotoImage] = None
        self.student_photo_caption: Optional[ttk.Label] = None

        # QR code UI refs
        self.student_qr_label: Optional[ttk.Label] = None
        self.student_qr_image: Optional[ImageTk.PhotoImage] = None

        if runmode.TEST_MODE:
            self._build_test_banner()
        self._build_menu()
        self._build_footer()  # before the notebook, so the Settings button keeps its strip
        self._build_notebook()
        self.load_items()
        self.load_students()
        self.load_assignments()
        self.load_attendance()  # today's attendance view
        self.load_admin_logs()  # Load admin logs on startup
        self.notebook.select(3)  # the portal opens on Attendance, the top row of the side menu (N2, D4)
        
        # Initialize tutorial system
        self.tutorial_manager = SimpleTutorialManager(self)

    def _build_test_banner(self):
        """Red strip at the top of the window: this is test mode (sandbox data only), or the practice copy."""
        text = ("PRACTICE MODE — nothing here is real. Use the real portal for real students."
                if runmode.PRACTICE_MODE else "TEST MODE — sandbox data only. Nothing here is live.")
        self._test_banner = tk.Label(
            self, text=text,
            bg="#c62828", fg="white", font=("Arial", 11, "bold"), pady=4)
        self._test_banner.pack(side=tk.TOP, fill=tk.X)

    # ---------- THEME / DARK MODE ----------

    def _apply_theme(self, dark: bool):
        """Apply light or dark theme to the application."""
        self.dark_mode = dark
        theme_colors = DARK_THEME if dark else LIGHT_THEME

        if not theme.CLASSIC:
            # House theme: ui/theme.py owns the base theme and the named
            # styles. Deliberately no theme_use("clam") here -- the call
            # below used to overwrite whatever theme had been installed.
            theme.apply(self.style)
            self.config(bg=theme.HOUSE['ground'])
            self._apply_theme_recursive(self, theme_colors)
            return

        # Configure ttk styles
        if dark:
            self.style.theme_use("clam")
        else:
            self.style.theme_use("clam")

        # Treeview colors
        self.style.configure(
            "Treeview",
            background=theme_colors["bg"],
            foreground=theme_colors["fg"],
            fieldbackground=theme_colors["bg"],
        )
        self.style.configure(
            "Treeview.Heading",
            background=theme_colors["bg"],
            foreground=theme_colors["fg"],
        )
        self.style.map(
            "Treeview",
            background=[("selected", theme_colors["selectbg"])],
            foreground=[("selected", theme_colors["selectfg"])],
        )

        # Listbox colors
        self.style.configure(
            "Listbox",
            background=theme_colors["bg"],
            foreground=theme_colors["fg"],
        )

        # Frame colors
        self.style.configure(
            "TFrame",
            background=theme_colors["bg"],
        )

        # Label colors
        self.style.configure(
            "TLabel",
            background=theme_colors["bg"],
            foreground=theme_colors["fg"],
        )

        # Button colors
        self.style.configure(
            "TButton",
            background=theme_colors["bg"],
            foreground=theme_colors["fg"],
        )

        # Entry colors
        self.style.configure(
            "TEntry",
            background=theme_colors["bg"],
            foreground=theme_colors["fg"],
            fieldbackground=theme_colors["bg"],
        )

        # Global Treeview defaults. These used to arrive from the attendance
        # tab's own ttk.Style() and leak to every tree in the app; keeping
        # them here preserves that appearance. See PORTAL_UI_ISSUES.md.
        theme.treeview_defaults(self.style)

        # Apply to main window
        self.config(bg=theme_colors["bg"])
        self._apply_theme_recursive(self, theme_colors)

    def _apply_theme_recursive(self, widget, theme_colors):
        """Recursively apply theme colors to all child widgets."""
        if isinstance(widget, tk.Listbox):
            widget.config(bg=theme_colors["bg"], fg=theme_colors["fg"])
        elif isinstance(widget, tk.Menu):
            widget.config(bg=theme_colors["bg"], fg=theme_colors["fg"])

        # Process children
        try:
            for child in widget.winfo_children():
                self._apply_theme_recursive(child, theme_colors)
        except tk.TclError:
            pass

    def toggle_dark_mode(self):
        """Toggle between light and dark mode."""
        self.dark_mode = not self.dark_mode
        self._apply_theme(self.dark_mode)
        messagebox.showinfo(
            "Theme Changed",
            f"Switched to {'Dark' if self.dark_mode else 'Light'} mode.",
        )

    # ---------- MENU BAR ----------

    def _build_menu(self):
        self._rebuild_menu()

    # ---------- FOOTER ----------

    def _build_footer(self):
        """Build footer with version and settings button.
        House mode (N2): the dark side panel instead, with Tutorials, Settings and Log out at its foot."""
        if not theme.CLASSIC:
            self.side_panel = build_panel(self)
            return
        footer_frame = ttk.Frame(self)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        ttk.Label(footer_frame, text="NestMind Portal", font=("Arial", 9)).pack(side=tk.LEFT)
        theme.flat_button(footer_frame, 'secondary', text="📚 Tutorials", bg='#9b59b6', fg='white', font=('Arial', 9, 'bold'), padx=10, pady=4, command=self.open_tutorials).pack(side=tk.LEFT, padx=10)
        theme.flat_button(footer_frame, 'secondary', text="⚙ Settings", bg=COLORS['primary'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_change_passwords).pack(side=tk.RIGHT, padx=5)

    def t(self, key):
        """Get translation for current language."""
        lang = self.current_language.get() if hasattr(self, 'current_language') else "EN"
        return TRANSLATIONS.get(lang, TRANSLATIONS["EN"]).get(key, key)

    def set_language(self, lang):
        """Set the application language and rebuild UI."""
        old_lang = self.current_language.get()
        self.current_language.set(lang)
        
        # Rebuild UI components
        self._rebuild_menu()
        self._rebuild_tabs()
        
        # Destroy and rebuild all tab contents
        if hasattr(self, 'notebook'):
            # Store current tab
            current_tab = self.notebook.index(self.notebook.select())
            
            # Clear all tabs
            for tab in self.notebook.tabs():
                self.notebook.forget(tab)
            
            # Rebuild notebook with new translations
            self._build_notebook()
            
            # Restore selected tab
            try:
                self.notebook.select(current_tab)
            except:
                pass
            
            # Reload data
            self.load_items()
            self.load_students()
            self.load_assignments()
            self.load_attendance()
        
        # Show confirmation message AFTER changing language
        if lang == "TH":
            messagebox.showinfo("ภาษา", "ภาษาเปลี่ยนเป็นภาษาไทยแล้ว")
        else:
            messagebox.showinfo("Language", "Language changed to English")

    def _rebuild_menu(self):
        """Rebuild menu bar with current language."""
        menubar = tk.Menu(self)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=self.t("backup_now"), command=self.on_backup_now)
        file_menu.add_command(label=self.t("change_passwords"), command=self.on_change_passwords)
        file_menu.add_separator()
        file_menu.add_command(label=self.t("logout"), command=self.on_logout)
        file_menu.add_separator()
        file_menu.add_command(label=self.t("exit"), command=self.on_exit)
        menubar.add_cascade(label=self.t("file"), menu=file_menu)

        # Data menu
        data_menu = tk.Menu(menubar, tearoff=0)
        data_menu.add_command(label=self.t("import_students"), command=self.on_import_csv)
        data_menu.add_separator()
        data_menu.add_command(label=self.t("export_items"), command=self.on_export_items_csv)
        data_menu.add_command(label=self.t("export_students"), command=self.on_export_students_csv)
        data_menu.add_command(label=self.t("export_assignments"), command=self.on_export_assignments_csv)
        data_menu.add_command(label=self.t("export_attendance"), command=self.on_export_today_attendance_csv)
        menubar.add_cascade(label=self.t("data"), menu=data_menu)

        # QR menu
        qr_menu = tk.Menu(menubar, tearoff=0)
        qr_menu.add_command(label=self.t("scan_qr"), command=self.on_scan_qr)
        qr_menu.add_command(label=self.t("open_scan"), command=self.open_scan_mode)
        qr_menu.add_separator()
        qr_menu.add_command(label=self.t("generate_items_qr"), command=self.on_bulk_qr_items)
        qr_menu.add_command(label=self.t("generate_students_qr"), command=self.on_bulk_qr_students)
        menubar.add_cascade(label=self.t("qr"), menu=qr_menu)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        # Dark mode retired 2026-09-19 (UI modernisation pilot). It only ever
        # restyled ttk frames, listboxes and menus, leaving every tk panel,
        # label and button light, and it was never persisted across launches.
        # toggle_dark_mode() and DARK_THEME remain in place, unreachable.
        view_menu.add_radiobutton(label=self.t("english"), variable=self.current_language, value="EN", command=lambda: self.set_language("EN"))
        view_menu.add_radiobutton(label=self.t("thai"), variable=self.current_language, value="TH", command=lambda: self.set_language("TH"))
        menubar.add_cascade(label=self.t("view"), menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="📚 Interactive Tutorials", command=self.open_tutorials)
        help_menu.add_separator()
        help_menu.add_command(label="About NestMind Portal", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _rebuild_tabs(self):
        """Update tab labels with current language."""
        if hasattr(self, 'notebook'):
            self.notebook.tab(0, text=self.t("students"))
            self.notebook.tab(1, text=self.t("items"))
            self.notebook.tab(2, text=self.t("books"))
            self.notebook.tab(3, text=self.t("attendance"))
            self.notebook.tab(4, text=self.t("roster"))
            self.notebook.tab(5, text=self.t("schedule"))
            self.notebook.tab(6, text=self.t("lessons"))
            self.notebook.tab(7, text=self.t("system"))
            self.notebook.tab(8, text=self.t("admin_log"))
            self.notebook.tab(9, text=self.t("dev_login"))

    def _rebuild_footer_buttons(self):
        """Update footer button text."""
        # This would update the Settings button text if it was stored as a reference
        pass

    def on_change_passwords(self):
        """Open password change dialog."""
        settings_window = tk.Toplevel(self)
        settings_window.title("Settings - Change Passwords")
        settings_window.resizable(False, False)
        settings_window.config(bg=COLORS['light'])

        # Blue band at top
        top_band = tk.Frame(settings_window, bg=COLORS['primary'], height=60)
        top_band.pack(side=tk.TOP, fill=tk.X)
        top_band.pack_propagate(False)
        
        top_label = tk.Label(top_band, text="Change Passwords", font=("Arial", 14, "bold"), bg=COLORS['primary'], fg='white')
        top_label.pack(pady=15)

        frame = tk.Frame(settings_window, bg=COLORS['light'])
        frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)

        # ===== LOGIN PASSWORD GROUP =====
        login_frame = tk.Frame(frame, bg=COLORS['white'], relief='solid', borderwidth=1)
        login_frame.pack(fill=tk.X, pady=(0, 15))
        
        login_header = tk.Frame(login_frame, bg=COLORS['secondary'], height=35)
        login_header.pack(fill=tk.X)
        login_header.pack_propagate(False)
        login_label = tk.Label(login_header, text="Login Password", bg=COLORS['secondary'], fg='white', font=('Arial', 10, 'bold'), padx=12, pady=8)
        login_label.pack(anchor="w")
        
        login_content = tk.Frame(login_frame, bg=COLORS['white'])
        login_content.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        # Current Login Password (with blue background label)
        current_login_label = tk.Label(login_content, text="Current Login Password:", bg=COLORS['secondary'], fg='white', font=('Arial', 9, 'bold'), padx=8, pady=4)
        current_login_label.pack(anchor="w", pady=(0, 5))
        current_password_var = tk.StringVar()
        ttk.Entry(login_content, textvariable=current_password_var, width=50, show="•").pack(fill=tk.X, pady=(0, 12))

        # New Login Password (with blue background label)
        new_login_label = tk.Label(login_content, text="New Login Password:", bg=COLORS['secondary'], fg='white', font=('Arial', 9, 'bold'), padx=8, pady=4)
        new_login_label.pack(anchor="w", pady=(0, 5))
        new_login_password_var = tk.StringVar()
        ttk.Entry(login_content, textvariable=new_login_password_var, width=50, show="•").pack(fill=tk.X)

        # ===== ADMIN PASSWORD GROUP =====
        admin_frame = tk.Frame(frame, bg=COLORS['white'], relief='solid', borderwidth=1)
        admin_frame.pack(fill=tk.X, pady=(0, 20))
        
        admin_header = tk.Frame(admin_frame, bg=COLORS['success'], height=35)
        admin_header.pack(fill=tk.X)
        admin_header.pack_propagate(False)
        admin_label = tk.Label(admin_header, text="Admin Password", bg=COLORS['success'], fg='white', font=('Arial', 10, 'bold'), padx=12, pady=8)
        admin_label.pack(anchor="w")
        
        admin_content = tk.Frame(admin_frame, bg=COLORS['white'])
        admin_content.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        # Current Admin Password (with green background label)
        current_admin_label = tk.Label(admin_content, text="Current Admin Password:", bg=COLORS['success'], fg='white', font=('Arial', 9, 'bold'), padx=8, pady=4)
        current_admin_label.pack(anchor="w", pady=(0, 5))
        current_admin_password_var = tk.StringVar()
        ttk.Entry(admin_content, textvariable=current_admin_password_var, width=50, show="•").pack(fill=tk.X, pady=(0, 12))

        # New Admin Password (with green background label)
        new_admin_label = tk.Label(admin_content, text="New Admin Password (leave empty to keep it):", bg=COLORS['success'], fg='white', font=('Arial', 9, 'bold'), padx=8, pady=4)
        new_admin_label.pack(anchor="w", pady=(0, 5))
        new_admin_password_var = tk.StringVar()
        ttk.Entry(admin_content, textvariable=new_admin_password_var, width=50, show="•").pack(fill=tk.X)

        # Buttons
        button_frame = tk.Frame(frame, bg=COLORS['light'])
        button_frame.pack(fill=tk.X, pady=(20, 0))

        def save_passwords():
            current_password = current_password_var.get().strip()
            current_admin_password = current_admin_password_var.get().strip()
            new_login_password = new_login_password_var.get().strip()
            new_admin_password = new_admin_password_var.get().strip()

            if not current_password or not current_admin_password or not new_login_password:
                messagebox.showwarning("Missing", "Fill in both current passwords and the new login password. "
                                                  "Leave the new admin password empty to keep the current one.")
                return

            try:
                login_ok = auth.verify("login", current_password)
                admin_ok = auth.verify("admin", current_admin_password)
            except auth.CredentialsError as e:
                messagebox.showerror("Locked", e.user_message)
                return
            if not login_ok:
                messagebox.showerror("Error", "Current login password is incorrect!")
                current_password_var.set("")
                return
            if not admin_ok:
                messagebox.showerror("Error", "Current admin password is incorrect!")
                current_admin_password_var.set("")
                return

            try:
                auth.set_passwords(new_login_password, new_admin_password or None)
            except (ValueError, auth.CredentialsError) as e:
                messagebox.showerror("Error", f"Could not save passwords: {e}")
                return
            except OSError as e:
                messagebox.showerror("Error", f"Could not save passwords: {e.strerror or e}")
                return
            try:
                user = auth.load()["username"]
            except auth.CredentialsError:
                user = "?"
            messagebox.showinfo("Success", f"Passwords updated for user '{user}'. Start-up login is on.")
            settings_window.destroy()

        save_btn = theme.flat_button(button_frame, 'primary', text="💾 Save", bg=COLORS['success'], fg='white', font=('Arial', 10, 'bold'), padx=15, pady=6, command=save_passwords)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))

        cancel_btn = theme.flat_button(button_frame, 'secondary', text="✕ Cancel", bg=COLORS['danger'], fg='white', font=('Arial', 10, 'bold'), padx=15, pady=6, command=settings_window.destroy)
        cancel_btn.pack(side=tk.LEFT)

        # Sized by its content, never smaller than the old 500x580: Save and Cancel always show, whatever the display
        # scaling (B5b-9; the old fixed 500x580 cut them off at 125%; the floor: b5c_fix1, David 13 Oct)
        settings_window.update_idletasks()
        settings_window.minsize(max(500, settings_window.winfo_reqwidth()), max(580, settings_window.winfo_reqheight()))

    # ---------- NOTEBOOK & TABS ----------

    def _build_notebook(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        students_frame = ttk.Frame(notebook)
        items_frame = ttk.Frame(notebook)
        assignments_frame = ttk.Frame(notebook)
        attendance_frame = ttk.Frame(notebook)
        schedule_frame = ttk.Frame(notebook)
        logs_frame = ttk.Frame(notebook)
        admin_logs_frame = ttk.Frame(notebook)

        notebook.add(students_frame, text=self.t("students"))
        notebook.add(items_frame, text=self.t("items"))
        notebook.add(assignments_frame, text=self.t("books"))
        notebook.add(attendance_frame, text=self.t("attendance"))

        roster_frame = ttk.Frame(notebook)
        lessons_frame = ttk.Frame(notebook)
        system_frame = ttk.Frame(notebook)

        notebook.add(roster_frame, text=self.t("roster"))
        notebook.add(schedule_frame, text=self.t("schedule"))
        notebook.add(lessons_frame, text=self.t("lessons"))
        notebook.add(system_frame, text=self.t("system"))
        notebook.add(admin_logs_frame, text=self.t("admin_log"))
        notebook.add(logs_frame, text=self.t("dev_login"))

        self._build_students_tab(students_frame)
        self._build_items_tab(items_frame)
        self._build_assignments_tab(assignments_frame)
        self._build_attendance_tab(attendance_frame)
        self._build_roster_tab(roster_frame)
        self._build_schedule_tab(schedule_frame)
        self._build_lessons_tab(lessons_frame)
        self._build_system_tab(system_frame)
        self._build_admin_logs_tab(admin_logs_frame)
        self._build_logs_tab(logs_frame)

        self.notebook = notebook

        # Bind tab change to refresh auth button and system tab
        def _on_tab_changed(event):
            try:
                idx = notebook.index(notebook.select())
                side = getattr(self, 'side_menu', None)
                if side is not None:
                    side.highlight(idx)      # the side menu follows every select, from a click or from code (N2)
                if idx == 7 and hasattr(self, 'system_tab'):
                    self.system_tab.on_tab_selected()
                if (idx == notebook.index(lessons_frame)
                        and hasattr(self, 'lessons_tab')):
                    self.lessons_tab.on_tab_selected()
            except Exception:
                pass
        notebook.bind("<<NotebookTabChanged>>", _on_tab_changed)
        self._build_side_menu()

    def _build_side_menu(self):
        """The side menu in place of the tab strip (new look N2). The strip is hidden, not removed: every tab keeps
        its index, text and page. Classic mode, and a host without the panel, keep today's strip."""
        panel = getattr(self, 'side_panel', None)
        if theme.CLASSIC or panel is None:
            return
        self.style.layout("Side.TNotebook.Tab", [])
        self.style.configure("Side.TNotebook", tabmargins=0, padding=0)
        self.notebook.configure(style="Side.TNotebook", takefocus=0)   # never a Tab-key stop on an invisible strip
        menu = getattr(self, 'side_menu', None)
        if menu is None:                                                # set_language builds a new notebook: refresh
            menu = SideMenu(panel, self)
            menu.pack(side=tk.TOP, fill=tk.X)
            self.side_menu = menu
        menu.refresh()

    def _on_side_menu_click(self, index):
        """A user's click on a side-menu row (N2 addendum A). Shows the page, then does what a click on the old
        tab strip did (Tk's ttk::notebook::ActivateTab): the keyboard focus moves to the page now shown.
        Selects made by code (scan, Roster -> Schedule, tutorial, set_language) never come here."""
        nb = self.notebook
        if nb.index("current") == index:
            return                                      # a click on the current row changes nothing (T1)
        grab = self.grab_current()
        if grab is not None and grab is not self:
            return                                      # a modal window (Scan Mode, Manual Entry) holds the grab:
                                                        # neither the page nor the focus changes (David, 20 Oct)
        nb.select(index)
        self._focus_page_after_menu_click(index)

    def _focus_page_after_menu_click(self, index):
        """The one focus site N2 adds to this file (design 3.4 as amended by the addendum)."""
        page = self.nametowidget(self.notebook.tabs()[index])
        self.update_idletasks()                         # ttk::focusFirst sees only mapped widgets, as ActivateTab does
        first = str(self.tk.call("ttk::focusFirst", str(page)))
        if first:
            self.tk.call("ttk::traverseTo", first)      # focus + <<TraverseIn>>, exactly what the strip sent
        else:
            page.focus_set()                            # label-only page (Lessons, System in TEST/PRACTICE): the page
                                                        # frame, which has no key binding, not the hidden notebook

    # ---------- ADMIN LOGS TAB ----------

    def _build_admin_logs_tab(self, parent):
        # Password protection for admin logs
        self.admin_logs_unlocked = False
        
        # Locked view
        self.admin_logs_locked_frame = ttk.Frame(parent)
        self.admin_logs_locked_frame.pack(fill=tk.BOTH, expand=True)
        
        locked_inner = ttk.Frame(self.admin_logs_locked_frame)
        locked_inner.pack(expand=True)
        
        ttk.Label(locked_inner, text="🔒 Admin Log Tab is Password Protected", font=("Arial", 14, "bold")).pack(pady=20)
        ttk.Label(locked_inner, text="Enter the admin password to view admin logs:").pack(pady=10)
        
        password_var = tk.StringVar()
        password_entry = ttk.Entry(locked_inner, textvariable=password_var, width=25, show="•")
        password_entry.pack(pady=10)
        password_entry.focus()
        
        def unlock_admin_logs():
            try:
                ok = auth.verify("admin", password_var.get())
            except auth.CredentialsError as e:
                messagebox.showerror("Locked", e.user_message)
                password_var.set("")
                return
            if ok:
                self.admin_logs_unlocked = True
                self.admin_logs_locked_frame.pack_forget()
                self.admin_logs_unlocked_frame.pack(fill=tk.BOTH, expand=True)
                self.load_admin_logs()
            else:
                messagebox.showerror("Incorrect", "Wrong password!")
                password_var.set("")
        
        password_entry.bind("<Return>", lambda e: unlock_admin_logs())
        theme.flat_button(locked_inner, 'primary', text=f"🔓 {self.t('unlock')}", bg=COLORS['success'], fg='white', font=('Arial', 9), padx=8, pady=4, command=unlock_admin_logs).pack(pady=10)
        
        # Unlocked view
        self.admin_logs_unlocked_frame = ttk.Frame(parent)
        
        top = ttk.Frame(self.admin_logs_unlocked_frame)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        ttk.Label(top, text=f"{self.t('search')}:").pack(side=tk.LEFT)
        self.admin_logs_search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=self.admin_logs_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind("<Return>", lambda e: self.load_admin_logs())

        btn_search = theme.flat_button(top, 'secondary', text=self.t('search'), bg=COLORS['secondary'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.load_admin_logs)
        btn_search.pack(side=tk.LEFT, padx=5)

        btn_clear = theme.flat_button(top, 'secondary', text=self.t('clear'), bg=COLORS['danger'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_admin_logs_clear)
        btn_clear.pack(side=tk.LEFT, padx=5)

        btn_refresh = theme.flat_button(top, 'secondary', text=self.t('refresh'), bg=COLORS['dark'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.load_admin_logs)
        btn_refresh.pack(side=tk.LEFT, padx=5)
        
        # Filter dropdown
        ttk.Label(top, text=f"{self.t('filter')}:").pack(side=tk.LEFT, padx=(10, 0))
        self.admin_logs_filter_var = tk.StringVar(value="All")
        filter_options = ["All", "Authentication", "Student", "Item", "Assignment"]
        filter_combo = ttk.Combobox(top, textvariable=self.admin_logs_filter_var, 
                                    values=filter_options, state="readonly", width=15)
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.load_admin_logs())
        
        btn_mass_delete = theme.flat_button(top, 'danger', text=f"⚠️ {self.t('mass_delete')}", bg='#c0392b', fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_mass_delete_students)
        btn_mass_delete.pack(side=tk.LEFT, padx=5)

        btn_rename = theme.flat_button(top, 'warning', text="\u270F\uFE0F Rename student\u2026", bg=COLORS['secondary'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_rename_student)
        btn_rename.pack(side=tk.LEFT, padx=5)
        
        columns = ("timestamp", "action", "entity_type", "entity_id", "details", "status")
        tree = ttk.Treeview(self.admin_logs_unlocked_frame, columns=columns, show="headings", selectmode="browse")
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)

        headers = ["Timestamp", "Action", "Entity Type", "Entity ID", "Details", "Status"]
        for col, text in zip(columns, headers):
            tree.heading(col, text=text)

        tree.column("timestamp", width=180)
        tree.column("action", width=80)
        tree.column("entity_type", width=100)
        tree.column("entity_id", width=100)
        tree.column("details", width=200)
        tree.column("status", width=80)

        scrollbar = ttk.Scrollbar(self.admin_logs_unlocked_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=10)

        self.admin_logs_tree = tree

    def load_admin_logs(self):
        """Load admin action logs, optionally filtered by search term and entity type."""
        if not hasattr(self, "admin_logs_tree"):
            return
        
        # Clear existing rows
        for row in self.admin_logs_tree.get_children():
            self.admin_logs_tree.delete(row)

        term = self.admin_logs_search_var.get().strip()
        filter_type = self.admin_logs_filter_var.get() if hasattr(self, "admin_logs_filter_var") else "All"
        
        # Use a smaller limit (100 instead of 500) to prevent freeze
        if term:
            logs = models.search_admin_logs(term, limit=100)
        else:
            logs = models.list_admin_logs(limit=100)

        # Apply filter by entity type
        if filter_type != "All":
            filter_map = {
                "Authentication": "authentication",
                "Student": "student",
                "Item": "item",
                "Assignment": "assignment"
            }
            entity_type = filter_map.get(filter_type, "")
            logs = [log for log in logs if log.get("entity_type") == entity_type]

        # Load in batches to prevent UI freeze
        batch_size = 50
        for i in range(0, len(logs), batch_size):
            batch = logs[i:i + batch_size]
            for log in batch:
                self.admin_logs_tree.insert(
                    "",
                    tk.END,
                    values=(
                        _local_time(log.get("timestamp")),          # stored as UTC; shown in local time
                        log.get("action") or "",
                        log.get("entity_type") or "",
                        log.get("entity_id") or "",
                        log.get("details") or "",
                        log.get("status") or "",
                    ),
                )
            self.admin_logs_tree.update()  # Refresh UI after each batch

    def on_admin_logs_clear(self):
        """Clear the search filter and reload all admin logs."""
        self.admin_logs_search_var.set("")
        self.load_admin_logs()

    # ---------- SHARED QR HANDLER ----------

    def process_qr_code(self, content: str, context: str = "dialog"):
        """
        Core logic for QR handling.
        content examples:
          I:BOOK1
          S:PAN001
        context: "dialog" or "scan_mode"
        """
        content = (content or "").strip()
        if not content:
            if context == "dialog":
                messagebox.showwarning("Empty", "No code provided.")
            return

        try:
            # ITEM QR
            if content[:2].upper() == "I:":                     # "I:" or "i:"
                original_item_id = content[2:].strip()

                # Sanitize input - remove non-alphanumeric except dots, dashes, and underscores
                item_id = _card_item_id(content)

                # Log warning if we had to clean the input
                if item_id != original_item_id:
                    print(f"Scanner: Cleaned item ID '{original_item_id}' → '{item_id}'")
                    if context != "dialog":
                        self._scan_log(f"⚠️ Scanner sent extra characters (auto-cleaned)")

                item = models.get_item(item_id)
                if not item:
                    if context == "dialog":
                        messagebox.showerror("Not found", f"Item '{item_id}' not found.")
                    else:
                        self._scan_log(f"❌ Item '{item_id}' not found.")
                        self._scan_reset(note=True)                 # never pair a later scan with an earlier one (5c)
                    return

                models.log_qr_scan(content, student_id=None, item_id=item_id,
                                   scan_context=f"{context}_item")
                event_bus.log_event(
                    event_name=f"qr_scan_item_{context}",
                    student_id=None,
                    item_id=item_id,
                    payload={"qr_code": content},
                )

                self._focus_item_in_ui(item_id)

                if context == "dialog":
                    messagebox.showinfo("QR Scan", f"Item '{item_id}' found and selected.")
                else:
                    self._scan_log(f"✅ Item scanned: {item_id} – {item.get('name', '')}")
                    self._handle_scan_pairing(item_id=item_id, student_id=None, context=context,
                                              name=item.get('name') or item_id)
                return

            # STUDENT QR
            if content[:2].upper() == "S:":                     # "S:" or "s:"
                original_student_id = content[2:].strip()

                # Sanitize input - remove non-alphanumeric except dots, dashes and underscores
                # This handles scanner artifacts like "♪" automatically
                student_id = _card_student_id(content)

                # Log warning if we had to clean the input (scanner configuration issue)
                if student_id != original_student_id:
                    print(f"Scanner: Cleaned student ID '{original_student_id}' → '{student_id}'")
                    if context != "dialog":
                        self._scan_log(f"⚠️ Scanner sent extra characters (auto-cleaned)")

                st = models.get_student(student_id)
                if not st:
                    if context == "dialog":
                        messagebox.showerror("Not found", f"Student '{student_id}' not found.")
                    else:
                        self._scan_log(f"❌ Student '{student_id}' not found.")
                        self._scan_reset(note=True)
                    return

                models.log_qr_scan(content, student_id=student_id, item_id=None,
                                   scan_context=f"{context}_student")
                event_bus.log_event(
                    event_name=f"qr_scan_student_{context}",
                    student_id=student_id,
                    item_id=None,
                    payload={"qr_code": content},
                )

                self._focus_student_in_ui(student_id)

                full_name = f"{st.get('first_name', '')} {st.get('last_name', '')}".strip()

                if context == "dialog":
                    messagebox.showinfo("QR Scan", f"Student '{student_id}' ({full_name}) selected.")
                else:
                    self._scan_log(f"✅ Student scanned: {student_id} – {full_name}")
                    self._handle_scan_pairing(item_id=None, student_id=student_id, context=context,
                                              name=models.display_name(st) or student_id)
                return

            # Unrecognised
            if context == "dialog":
                messagebox.showwarning(
                    "Unrecognised format",
                    "QR content should start with 'I:' (item) or 'S:' (student).",
                )
            else:
                self._scan_log("❓ Unrecognised code (must start with I: or S:)")
                self._scan_reset(note=True)
        except Exception as e:
            if context == "dialog":
                messagebox.showerror("Error", f"Error handling QR:\n{e}")
            else:
                self._scan_log(f"💥 Error handling QR: {e}")
                self._scan_reset(note=True)                         # David, 13 Oct: a scan that errors counts as failed

    def on_scan_qr(self):
        """Simple dialog-based scanning with automatic student linking for books."""
        content = simpledialog.askstring(
            "Scan Book QR",
            "Scan or type book QR (e.g. I:BOOK1):",
            parent=self,
        )
        if not content:
            return
        
        content = content.strip()
        
        # If it's a book (item), ask for student next
        item_id = _card_item_id(content)                     # "I:" or "i:", cleaned as process_qr_code does
        if item_id:
            item = models.get_item(item_id)
            if not item:
                messagebox.showerror("Not found", f"Book '{item_id}' not found.")
                return
            
            # Now ask for student
            student_input = simpledialog.askstring(
                "Link to Student",
                f"Book '{item_id}' scanned.\nNow scan student QR (e.g. S:PAN001):",
                parent=self,
            )
            if not student_input:
                self.process_qr_code(content, context="dialog")
                return
            
            student_input = student_input.strip()
            if student_input[:2].upper() == "S:":                # "S:" or "s:" from a card or a keyboard
                # Clean the ID as process_qr_code does (scanner artefacts such as a stray symbol)
                student_id = _card_student_id(student_input)
                student = models.get_student(student_id)
                if not student:
                    messagebox.showerror("Not found", f"Student '{student_id}' not found.")
                    self.process_qr_code(content, context="dialog")
                    return
                
                if self._lend_book(item_id, student_id,
                                   notes="Scanned checkout"):
                    # Switch to the Books tab so the new loan is visible
                    self.notebook.select(2)
            else:
                messagebox.showwarning("Invalid", "Student QR must start with 'S:'")
                self.process_qr_code(content, context="dialog")
        else:
            # Not a book, use normal QR processing
            self.process_qr_code(content, context="dialog")

    # ---------- SCAN MODE ----------

    def open_scan_mode(self):
        """Open or focus the Scan Mode window."""
        self._scan_reset()                                          # every opening starts with nothing remembered (5c)
        if self.scan_window is not None and self.scan_window.winfo_exists():
            self.scan_window.deiconify()
            self.scan_window.lift()
            if self.scan_entry is not None:
                self.scan_entry.focus_set()
            return

        win = tk.Toplevel(self)
        win.title("Scan Mode")
        win.geometry("520x360")
        win.transient(self)
        win.grab_set()

        self.scan_window = win

        def on_close():
            self._scan_reset()                                      # nothing remembered survives the window (5c)
            self.scan_window = None
            self.scan_entry = None
            self.scan_log_widget = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

        label = ttk.Label(
            win,
            text=(
                "Scan Mode (USB scanner or keyboard)\n"
                "- Scan student QR (S:...) to select student\n"
                "- Scan item QR (I:...) to select item\n"
                "- Using both can auto-assign items"
            ),
            justify="center",
        )
        label.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        entry = ttk.Entry(win, font=("Segoe UI", 16))
        entry.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        entry.focus_set()
        entry.bind("<Return>", self.on_scan_mode_enter)
        self.scan_entry = entry

        log_frame = ttk.Frame(win)
        log_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        log_list = tk.Listbox(log_frame)
        # Long lines scroll sideways (B5b-20); packed before the list so it keeps the bottom row
        xscrollbar = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=log_list.xview)
        xscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        log_list.configure(xscrollcommand=xscrollbar.set)
        log_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_list.yview)
        log_list.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.scan_log_widget = log_list
        self._scan_log("📡 Scan Mode ready.")

        # Never smaller than its content: with the sideways scrollbar (B5b-20) it needs more than 360 px at 150%
        win.update_idletasks()
        win.minsize(win.winfo_reqwidth(), win.winfo_reqheight())

    def on_scan_mode_enter(self, event):
        if self.scan_entry is None:
            return
        content = self.scan_entry.get().strip()
        self.scan_entry.delete(0, tk.END)
        if not content:
            return
        self.process_qr_code(content, context="scan_mode")

    def _scan_log(self, message: str):
        if self.scan_log_widget is None:
            return
        self.scan_log_widget.insert(tk.END, message)
        self.scan_log_widget.see(tk.END)

    def _scan_reset(self, note: bool = False):
        """Forget the remembered book and student card, so a later scan is never paired with them (5c, item a).
        note=True also says so in the Scan Mode log, after a scan that failed."""
        self.scan_last_student_id = None
        self.scan_last_item_id = None
        self.scan_last_student_name = None
        self.scan_last_item_name = None
        if note:
            self._scan_log("↩ Start again with the student card")

    def _handle_scan_pairing(self, item_id: Optional[str], student_id: Optional[str], context: str = "scan_mode",
                             name: Optional[str] = None):
        """
        Track the last scanned student/item. If running in scan_mode and both an item and student
        have been scanned, automatically create an assignment, log it and refresh the UI.
        name: the book's or student's name from the row already fetched, for the log.
        """
        if student_id is not None:
            self.scan_last_student_id = student_id
            self.scan_last_student_name = name or student_id
        if item_id is not None:
            self.scan_last_item_id = item_id
            self.scan_last_item_name = name or item_id

        # Only perform automatic pairing when in scan mode
        if context != "scan_mode":
            return

        # A card with no book yet: say what comes next
        if student_id is not None and not self.scan_last_item_id:
            self._scan_log(f"⏳ Waiting for a book for {self.scan_last_student_name}")

        # If both available, attempt to assign and clear the last scanned ids
        if self.scan_last_student_id and self.scan_last_item_id:
            sid = self.scan_last_student_id
            iid = self.scan_last_item_id
            book, who = self.scan_last_item_name, self.scan_last_student_name
            try:
                # Create assignment
                models.assign_item_to_student(item_id=iid, student_id=sid, notes="Auto-assigned via Scan Mode")

                # Log and notify in scan log
                self._scan_log(f"🔗 LENT '{book}' to {who}")
                # Refresh assignments list
                try:
                    self.load_assignments()
                except Exception:
                    # non-fatal UI refresh failure; keep scan mode usable
                    pass

                # Optionally emit event for other listeners
                try:
                    event_bus.log_event(
                        event_name="auto_assign_scan_mode",
                        student_id=sid,
                        item_id=iid,
                        payload={"note": "auto-assigned via scan mode"},
                    )
                except Exception:
                    pass
            except Exception as e:
                self._scan_log(f"❌ Auto-assign failed: {e}")
            finally:
                # clear pairing state so next scans start fresh
                self._scan_reset()

    # ---------- ITEM / STUDENT FOCUS HELPERS ----------

    def _focus_item_in_ui(self, item_id: str):
        self.notebook.select(1)  # Items tab (index 1)
        self.load_items()
        for row in self.items_tree.get_children():
            values = self.items_tree.item(row, "values")
            if values and values[0] == item_id:
                self.items_tree.selection_set(row)
                self.items_tree.see(row)
                break

    def _focus_student_in_ui(self, student_id: str):
        current_tab_index = self.notebook.index(self.notebook.select())
        
        # If on the Books tab (index 2), auto-select the student there for lending
        if current_tab_index == 2:
            student = models.get_student(student_id)
            if student:
                self._select_student_for_assignment(student)
            return
        
        # Otherwise, switch to Students tab and select the student
        self.notebook.select(0)  # Students tab (index 0)
        self.load_students()
        for row in self.students_tree.get_children():
            values = self.students_tree.item(row, "values")
            if values and values[0] == student_id:
                self.students_tree.selection_set(row)
                self.students_tree.see(row)
                self._load_student_photo(student_id)
                break

    # ---------- ITEMS TAB ----------

    def _build_items_tab(self, parent):
        # Main container
        main_container = tk.Frame(parent, bg=COLORS['light'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Blue toolbar band
        toolbar = tk.Frame(main_container, bg=COLORS['primary'], height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)
        
        # Buttons in toolbar
        btn_add = theme.flat_button(toolbar, 'primary', text=f"➕ {self.t('add')}", bg=COLORS['success'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_add_item)
        btn_edit = theme.flat_button(toolbar, 'secondary', text=f"✏️ {self.t('edit')}", bg=COLORS['secondary'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_edit_item)
        btn_delete = theme.flat_button(toolbar, 'danger', text=f"🗑️ {self.t('delete')}", bg=COLORS['danger'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_delete_item)
        btn_refresh = theme.flat_button(toolbar, 'secondary', text=f"🔄 {self.t('refresh')}", bg=COLORS['dark'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_items_refresh)

        btn_add.pack(side=tk.LEFT, padx=5, pady=10)
        btn_edit.pack(side=tk.LEFT, padx=5, pady=10)
        btn_delete.pack(side=tk.LEFT, padx=5, pady=10)
        btn_refresh.pack(side=tk.LEFT, padx=5, pady=10)

        # Search in toolbar (right side)
        search_frame = tk.Frame(toolbar, bg=COLORS['primary'])
        search_frame.pack(side=tk.RIGHT, padx=15, pady=10)
        
        ttk.Label(search_frame, text=f"{self.t('search')}:").pack(side=tk.LEFT)
        self.items_search_var = tk.StringVar()
        entry = ttk.Entry(search_frame, textvariable=self.items_search_var, width=30)
        entry.pack(side=tk.LEFT, padx=5)
        btn_search = theme.flat_button(search_frame, 'secondary', text=self.t('search'), bg=COLORS['secondary'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_items_search)
        btn_search.pack(side=tk.LEFT, padx=5)

        # Treeview in main area
        columns = ("item_id", "name", "category", "quantity", "condition")
        tree = ttk.Treeview(main_container, columns=columns, show="headings", selectmode="browse")
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)

        for col, text in zip(columns, [self.t("item_id"), self.t("name"), self.t("category"), "Qty", "Condition"]):
            tree.heading(col, text=text)

        tree.column("item_id", width=150)
        tree.column("name", width=250)
        tree.column("category", width=140)
        tree.column("quantity", width=60, anchor=tk.CENTER)
        tree.column("condition", width=100)

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=10)

        self.items_tree = tree

        menu = tk.Menu(parent, tearoff=0)
        menu.add_command(label="Generate QR for Item", command=self.on_generate_item_qr)
        menu.add_command(label="Export Selected Item to CSV", command=self.on_export_selected_item_csv)
        self.items_menu = menu
        tree.bind("<Button-3>", self.on_items_right_click)

    def on_items_right_click(self, event):
        iid = self.items_tree.identify_row(event.y)
        if iid:
            self.items_tree.selection_set(iid)
            try:
                self.items_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.items_menu.grab_release()

    def load_items(self, term: Optional[str] = None):
        if not hasattr(self, "items_tree"):
            return
        for row in self.items_tree.get_children():
            self.items_tree.delete(row)

        if term:
            items = models.search_items(term)
        else:
            items = models.list_items()

        for item in items:
            self.items_tree.insert(
                "",
                tk.END,
                values=(
                    item["item_id"],
                    item["name"],
                    item.get("category") or "",
                    item.get("quantity") or 0,
                    item.get("condition") or "",
                ),
            )

    def get_selected_item_id(self):
        selection = self.items_tree.selection()
        if not selection:
            return None
        values = self.items_tree.item(selection[0], "values")
        return values[0]

    def on_add_item(self):
        from inventory.validation import validate_item_id, validate_name

        # Loop until valid item_id
        while True:
            item_id = simpledialog.askstring("New Item", "Item ID:", parent=self)
            if not item_id:
                return

            # Validate ID immediately
            valid, error = validate_item_id(item_id)
            if not valid:
                retry = messagebox.askyesno(
                    "Invalid Item ID",
                    f"{error}\n\nWould you like to try again?",
                    icon='warning'
                )
                if not retry:
                    return
                continue  # Ask for ID again
            break  # ID is valid, proceed

        # Loop until valid name
        while True:
            name = simpledialog.askstring("New Item", "Name:", parent=self)
            if not name:
                retry = messagebox.askyesno(
                    "Missing Name",
                    "Item name is required.\n\nWould you like to try again?",
                    icon='warning'
                )
                if not retry:
                    return
                continue  # Ask for name again

            # Validate name immediately
            valid, error = validate_name(name, "Item name")
            if not valid:
                retry = messagebox.askyesno(
                    "Invalid Name",
                    f"{error}\n\nWould you like to try again?",
                    icon='warning'
                )
                if not retry:
                    return
                continue  # Ask for name again
            break  # Name is valid, proceed

        category = simpledialog.askstring("New Item", "Category (optional):", parent=self) or None
        description = simpledialog.askstring("New Item", "Description (optional):", parent=self) or None

        try:
            models.add_item(
                item_id=item_id,
                name=name,
                category=category,
                description=description,
            )
            self.load_items()
        except Exception as e:
            messagebox.showerror("Error", f"Could not add item:\n{e}")

    def on_edit_item(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            messagebox.showinfo("No selection", "Please select an item to edit.")
            return

        item = models.get_item(item_id)
        if not item:
            messagebox.showerror("Error", "Selected item not found in database.")
            return

        new_name = simpledialog.askstring(
            "Edit Item",
            "Name:",
            initialvalue=item["name"],
            parent=self,
        )
        if new_name is None:
            messagebox.showinfo("Edit Item", "Cancelled. Nothing was changed.")
            return
        if not new_name.strip():
            messagebox.showwarning("Missing", "Item name is required.")
            return

        new_category = simpledialog.askstring(
            "Edit Item",
            "Category:",
            initialvalue=item.get("category") or "",
            parent=self,
        )
        if new_category is None:
            messagebox.showinfo("Edit Item", "Cancelled. Nothing was changed.")
            return
        new_description = simpledialog.askstring(
            "Edit Item",
            "Description:",
            initialvalue=item.get("description") or "",
            parent=self,
        )
        if new_description is None:
            messagebox.showinfo("Edit Item", "Cancelled. Nothing was changed.")
            return

        try:
            # quantity and condition are not asked here, so update_item leaves them as they are
            models.update_item(
                item_id=item_id,
                name=new_name.strip(),
                category=new_category.strip() or None,
                description=new_description.strip() or None,
            )
            self.load_items()
        except Exception as e:
            messagebox.showerror("Error", f"Could not update item:\n{e}")

    def on_delete_item(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            messagebox.showinfo("No selection", "Please select an item to delete.")
            return

        if not messagebox.askyesno("Confirm delete", f"Delete item '{item_id}'?"):
            return

        try:
            models.delete_item(item_id)
            self.load_items()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete item:\n{e}")

    def on_generate_item_qr(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            messagebox.showinfo("No selection", "Please select an item first.")
            return
        try:
            path = qr_utils.generate_item_qr(item_id)
            messagebox.showinfo(
                "QR Generated",
                f"QR code for item '{item_id}' saved to:\n{Path(path)}",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate item QR:\n{e}")

    def on_export_selected_item_csv(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            messagebox.showinfo("No selection", "Please select an item first.")
            return

        item = models.get_item(item_id)
        if not item:
            messagebox.showerror("Error", "Selected item not found in database.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export selected item to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"item_{item_id}.csv",
        )
        if not file_path:
            return

        try:
            from csv import writer
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                w = writer(f)
                w.writerow(["item_id", "name", "category", "description", "quantity", "condition"])
                w.writerow([
                    item.get("item_id", ""),
                    item.get("name", ""),
                    item.get("category", ""),
                    item.get("description", ""),
                    item.get("quantity", ""),
                    item.get("condition", ""),
                ])
            messagebox.showinfo("Export complete", f"Item exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export failed", f"Could not export item:\n{e}")

    def on_items_search(self):
        term = self.items_search_var.get().strip()
        if term:
            self.load_items(term)
        else:
            self.load_items()

    def on_items_refresh(self):
        self.items_search_var.set("")
        self.load_items()

        # ---------- STUDENTS TAB ----------

    def _build_students_tab(self, parent):
        """Enhanced students tab with modern styling"""
        
        # ==== MAIN CONTAINER ====
        main_container = tk.Frame(parent, bg=COLORS['light'])
        main_container.pack(fill=tk.BOTH, expand=True)
    
        # ==== TOP TOOLBAR ====
        toolbar = tk.Frame(main_container, bg=COLORS['primary'], height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)
    
        # Left buttons
        left_buttons = tk.Frame(toolbar, bg=COLORS['primary'])
        left_buttons.pack(side=tk.LEFT, padx=15, pady=10)
    
        # Button style
        btn_style = {
            'font': ('Arial', 9),
            'cursor': 'hand2',
            'relief': 'flat',
            'padx': 8,
            'pady': 4
        }
    
        theme.flat_button(left_buttons, 'primary', text=f"➕ {self.t('add')}", bg=COLORS['success'], 
                  fg='white', command=self.on_add_student, **btn_style).pack(side=tk.LEFT, padx=2)
    
        theme.flat_button(left_buttons, 'secondary', text=f"✏️ {self.t('edit')}", bg=COLORS['secondary'],
                  fg='white', command=self.on_edit_student, **btn_style).pack(side=tk.LEFT, padx=2)
    
        theme.flat_button(left_buttons, 'danger', text=f"🗑️ {self.t('delete')}", bg=COLORS['danger'],
                  fg='white', command=self.on_delete_student, **btn_style).pack(side=tk.LEFT, padx=2)
        
        theme.flat_button(left_buttons, 'secondary', text=f"🔄 {self.t('refresh')}", bg=COLORS['dark'],
              fg='white', command=self.on_students_refresh, **btn_style).pack(side=tk.LEFT, padx=2)
    
        # Right search
        search_frame = tk.Frame(toolbar, bg=COLORS['primary'])
        search_frame.pack(side=tk.RIGHT, padx=15, pady=10)
    
        tk.Label(search_frame, text="🔍", bg=COLORS['primary'],
                 fg='white', font=('Arial', 12)).pack(side=tk.LEFT, padx=5)
    
        self.students_search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.students_search_var,
                               width=25, font=('Arial', 10), relief='flat', bg=COLORS['white'])
        search_entry.pack(side=tk.LEFT, padx=5, ipady=5)
        search_entry.bind('<Return>', lambda e: self.on_students_search())
    
        theme.flat_button(search_frame, 'secondary', text=self.t("search"), bg=COLORS['secondary'], fg='white',
                  command=self.on_students_search, font=('Arial', 9, 'bold'),
                  cursor='hand2', relief='flat', padx=12, pady=5).pack(side=tk.LEFT, padx=3)
    
        # ==== CONTENT AREA ====
        content = tk.Frame(main_container, bg=COLORS['light'])
        content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=15, pady=15)
    
        # Left panel - Student list
        left_panel = tk.Frame(content, bg=COLORS['white'], relief='solid', borderwidth=1)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
    
        # List header
        list_header = tk.Frame(left_panel, bg=COLORS['primary'], height=40)
        list_header.pack(fill=tk.X)
        list_header.pack_propagate(False)
    
        tk.Label(list_header, text=self.t('student_list'), bg=COLORS['primary'],
                 fg='white', font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)
    
        # Treeview
        tree_frame = tk.Frame(left_panel, bg=COLORS['white'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        columns = ("student_id", "first_name", "last_name", "level", "status")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
        # Column headers with sorting
        tree.heading("student_id", text=self.t("student_id"), command=lambda: self.sort_students_tree("student_id", tree))
        tree.heading("first_name", text=self.t("first_name"), command=lambda: self.sort_students_tree("first_name", tree))
        tree.heading("last_name", text=self.t("last_name"), command=lambda: self.sort_students_tree("last_name", tree))
        tree.heading("level", text=self.t("level"), command=lambda: self.sort_students_tree("level", tree))
        tree.heading("status", text=self.t("status"), command=lambda: self.sort_students_tree("status", tree))
    
        # Column widths
        tree.column("student_id", width=120)
        tree.column("first_name", width=150)
        tree.column("last_name", width=150)
        tree.column("level", width=80)
        tree.column("status", width=80)
    
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        self.students_tree = tree
        tree.bind("<<TreeviewSelect>>", self.on_student_select)
        # A click on empty space below the rows, or Escape, clears the selection
        tree.bind("<Button-1>", lambda e: tree.selection_remove(tree.selection())
                  if tree.identify_region(e.x, e.y) == "nothing" else None, add="+")
        tree.bind("<Escape>", lambda e: tree.selection_remove(tree.selection()), add="+")
    
        # Right panel - Profile
        right_panel = tk.Frame(content, bg=COLORS['white'], width=280, relief='solid', borderwidth=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)
    
        # Profile header
        profile_header = tk.Frame(right_panel, bg=COLORS['primary'], height=50)
        profile_header.pack(fill=tk.X)
        profile_header.pack_propagate(False)
    
        tk.Label(profile_header, text="👤 Student Profile", bg=COLORS['primary'],
                 fg='white', font=('Arial', 13, 'bold')).pack(pady=13, padx=15)
    
        # Profile content - use grid for better layout control
        profile_content = tk.Frame(right_panel, bg=COLORS['white'])
        profile_content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Configure grid - only books row expands vertically
        profile_content.grid_rowconfigure(0, weight=0)  # Photo row - fixed
        profile_content.grid_rowconfigure(1, weight=0)  # QR row - fixed
        profile_content.grid_rowconfigure(2, weight=1)  # Spacer - expands
        profile_content.grid_rowconfigure(3, weight=0)  # Books row - fixed
        profile_content.grid_columnconfigure(0, weight=1)
    
        # Photo - using Canvas for precise pixel sizing with resizing
        photo_frame = tk.Frame(profile_content, bg=COLORS['white'])
        photo_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
    
        self.student_photo_label = tk.Canvas(photo_frame, bg=COLORS['light'], 
                                            relief='solid', borderwidth=1)
        self.student_photo_label.pack(fill=tk.BOTH, expand=True)
        self.student_photo_label.create_text(120, 120, text="No photo selected",
                                            fill=COLORS['dark'], font=('Arial', 9), tags="text")
        # Bind resize event to redraw photo
        self.student_photo_label.bind("<Configure>", self._on_photo_canvas_resize)
    
        self.student_photo_caption = tk.Label(photo_frame, text="", bg=COLORS['white'],
                                         fg=COLORS['dark'], font=('Arial', 9, 'bold'))
        self.student_photo_caption.pack(pady=(5, 0))
    
        # QR Code - using Canvas for precise pixel sizing with resizing
        qr_frame = tk.Frame(profile_content, bg=COLORS['white'])
        qr_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
    
        tk.Label(qr_frame, text="QR Code", bg=COLORS['white'], fg=COLORS['dark'],
                 font=('Arial', 9, 'bold')).pack()
    
        self.student_qr_label = tk.Canvas(qr_frame, bg=COLORS['light'],
                                         relief='solid', borderwidth=1)
        self.student_qr_label.pack(fill=tk.BOTH, expand=True, pady=5)
        self.student_qr_label.create_text(100, 100, text="No QR", fill=COLORS['dark'], 
                                         font=('Arial', 9), tags="text")
        self.student_qr_image = None
        # Bind resize event to redraw QR
        self.student_qr_label.bind("<Configure>", self._on_qr_canvas_resize)
        
        # Configure grid row weights for resizing
        profile_content.grid_rowconfigure(0, weight=1)  # Photo expands
        profile_content.grid_rowconfigure(1, weight=1)  # QR expands
        
        # Spacer - expands to fill middle space
        spacer = tk.Frame(profile_content, bg=COLORS['white'])
        spacer.grid(row=2, column=0, sticky="nsew")
    
        # Books section - fixed at bottom
        books_frame = ttk.LabelFrame(profile_content, text="📖 Books Out", padding=3)
        books_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    
        self.student_books_tree = ttk.Treeview(
            books_frame,
            columns=("assignment_id", "book_name", "status", "days"),
            show="headings", height=2,
            displaycolumns=("book_name", "status", "days"))
        self.student_books_tree.pack(fill=tk.X, expand=False)

        self.student_books_tree.heading("book_name", text=self.t("book"))
        self.student_books_tree.heading("status", text=self.t("status"))
        self.student_books_tree.heading("days", text="Days")

        self.student_books_tree.column("book_name", width=100)
        self.student_books_tree.column("status", width=40, anchor='center')
        self.student_books_tree.column("days", width=30, anchor='center')

        theme.flat_button(books_frame, 'primary', text="\u21a9 Return Book",
                  bg=COLORS['secondary'], fg='white',
                  font=('Arial', 9, 'bold'), padx=8, pady=3,
                  command=self.on_return_selected_book).pack(
                      side=tk.LEFT, pady=(4, 2))

        self.books_out_menu = tk.Menu(books_frame, tearoff=0)
        self.books_out_menu.add_command(label="\u21a9 Return this book",
                                        command=self.on_return_selected_book)
        self.student_books_tree.bind("<Button-3>",
                                     self.on_books_out_right_click)

        # C-Test Placement section
        ctest_frame = ttk.LabelFrame(profile_content, text="C-Test Placement", padding=3)
        ctest_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))

        # CEFR confirmation banner (populated dynamically)
        self._cefr_banner_frame = tk.Frame(ctest_frame, bg=theme.colour('notice_bg', '#FFF3CD'))
        self._cefr_banner_frame.pack(fill=tk.X, padx=5, pady=(2, 2))
        self._cefr_banner_frame.pack_forget()  # hidden by default

        self._ctest_status_var = tk.StringVar(value="No student selected.")
        tk.Label(ctest_frame, textvariable=self._ctest_status_var,
                 bg=COLORS['white'], fg=COLORS['dark'],
                 font=ds.FONTS['body'], anchor='w').pack(fill=tk.X, padx=5, pady=(2, 2))

        self._ctest_history_tree = ttk.Treeview(
            ctest_frame, columns=("id", "date", "level", "score"),
            show="headings", height=3)
        self._ctest_history_tree.heading("id", text="ID")
        self._ctest_history_tree.heading("date", text="Date")
        self._ctest_history_tree.heading("level", text="Level")
        self._ctest_history_tree.heading("score", text="Score %")
        self._ctest_history_tree.column("id", width=35, anchor='center')
        self._ctest_history_tree.column("date", width=80)
        self._ctest_history_tree.column("level", width=70, anchor='center')
        self._ctest_history_tree.column("score", width=55, anchor='center')
        self._ctest_history_tree.pack(fill=tk.X, padx=5, pady=(0, 2))

        # Older pending suggestions, one grey line each (populated dynamically)
        self._ctest_older_frame = tk.Frame(ctest_frame, bg=COLORS['white'])
        self._ctest_older_frame.pack(fill=tk.X, padx=5, pady=(0, 2))

        # Button row: Start C-Test + Refresh + Delete result
        ctest_btn_frame = tk.Frame(ctest_frame, bg=COLORS['white'])
        ctest_btn_frame.pack(fill=tk.X, padx=5, pady=(0, 3))

        self._ctest_delete_btn = theme.flat_button(
            ctest_btn_frame, 'danger', text="Delete Result",
            font=('Arial', 9), relief='flat', cursor='hand2',
            bg='#dc3545', fg='white', padx=6, pady=2,
            state=tk.DISABLED,
            command=self._on_delete_ctest_result,
        )
        self._ctest_delete_btn.pack(side=tk.LEFT)

        self._ctest_start_btn = theme.flat_button(
            ctest_btn_frame, 'primary', text="Start C-Test",
            font=ds.FONTS['body_bold'], relief='flat', cursor='hand2',
            bg=COLORS['primary'], fg='white', padx=8, pady=2,
            state=tk.DISABLED,
            command=self._on_start_ctest_clicked,
        )
        self._ctest_start_btn.pack(side=tk.RIGHT)

        self._ctest_refresh_btn = theme.flat_button(
            ctest_btn_frame, 'secondary', text="Refresh",
            font=('Arial', 9), relief='flat', cursor='hand2',
            bg=COLORS['secondary'], fg='white', padx=6, pady=2,
            command=lambda: self._update_ctest_panel(self.get_selected_student_id()),
        )
        self._ctest_refresh_btn.pack(side=tk.RIGHT, padx=(0, 4))

        # Enable/disable delete button on tree selection
        self._ctest_history_tree.bind('<<TreeviewSelect>>', self._on_ctest_tree_select)

        # Dev wipe button (hidden by default, shown only for DEV001)
        self._ctest_dev_wipe_btn = theme.flat_button(
            ctest_frame, 'danger', text="Wipe DEV Results",
            font=('Arial', 9), relief='flat', cursor='hand2',
            bg='#6c757d', fg='white', padx=6, pady=2,
            command=self._on_wipe_dev_results,
        )
        # Not packed by default — shown conditionally in _update_ctest_panel

        # Unclaimed temp sessions sub-frame (populated dynamically)
        self._ctest_temp_frame = tk.Frame(ctest_frame, bg=COLORS['white'])
        self._ctest_temp_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Context menu
        menu = tk.Menu(parent, tearoff=0)
        menu.add_command(label="Generate QR for Student", command=self.on_generate_student_qr)
        menu.add_command(label="Set / Update Photo", command=self.on_set_student_photo)
        menu.add_command(label="Export Selected Student to CSV", command=self.on_export_selected_student_csv)
        self.students_menu = menu
        self.students_tree.bind("<Button-3>", self.on_students_right_click)

    def _get_ctest_conn(self):
        """Return a sqlite3 connection to the C-Test database, or None."""
        import sqlite3 as _sql
        try:
            if not _CTEST_DB.exists():
                return None
            conn = _sql.connect(str(_CTEST_DB))
            conn.row_factory = _sql.Row
            return conn
        except Exception:
            return None

    def _update_ctest_panel(self, student_id):
        """Refresh the C-Test Placement panel for the given student."""
        if not hasattr(self, '_ctest_status_var'):
            return

        # Clear history tree
        for item in self._ctest_history_tree.get_children():
            self._ctest_history_tree.delete(item)

        # Clear temp session widgets
        for w in self._ctest_temp_frame.winfo_children():
            w.destroy()

        for w in self._ctest_older_frame.winfo_children():
            w.destroy()

        # Hide CEFR banner & dev wipe by default
        self._cefr_banner_frame.pack_forget()
        for w in self._cefr_banner_frame.winfo_children():
            w.destroy()
        self._ctest_dev_wipe_btn.pack_forget()

        if not student_id:
            self._ctest_status_var.set("No student selected.")
            if hasattr(self, '_ctest_start_btn'):
                self._ctest_start_btn.config(state=tk.DISABLED)
            if hasattr(self, '_ctest_delete_btn'):
                self._ctest_delete_btn.config(state=tk.DISABLED)
            return

        # Enable the Start C-Test button when a student is selected
        if hasattr(self, '_ctest_start_btn'):
            self._ctest_start_btn.config(state=tk.NORMAL)

        conn = self._get_ctest_conn()
        if conn is None:
            self._ctest_status_var.set("C-Test data unavailable")
            return

        try:
            data = _ctest_panel_data(conn, student_id)

            # ---- CEFR suggestion banner: only the suggestion linked to the result shown (B4-3) ----
            cefr_row = data["banner"]
            if cefr_row:
                self._cefr_banner_frame.pack(fill=tk.X, padx=5, pady=(2, 4))
                banner_text = f"  C-Test suggests {cefr_row['band']}"
                tk.Label(self._cefr_banner_frame, text=banner_text,
                         bg=theme.colour('notice_bg', '#FFF3CD'), fg=theme.colour('notice_ink', '#856404'),
                         font=ds.FONTS['body_bold'], anchor='w'
                         ).pack(side=tk.LEFT, fill=tk.X, expand=True)
                sug_id = cefr_row['id']
                theme.flat_button(self._cefr_banner_frame, 'primary', text="Confirm",
                          font=('Arial', 8), relief='flat', cursor='hand2',
                          bg='#28a745', fg='white', padx=4, pady=1,
                          command=lambda sid=str(student_id), sid2=sug_id:
                              self._cefr_action(sid, sid2, 'confirmed')
                          ).pack(side=tk.RIGHT, padx=2)
                theme.flat_button(self._cefr_banner_frame, 'secondary', text="Adjust",
                          font=('Arial', 8), relief='flat', cursor='hand2',
                          bg=COLORS['secondary'], fg='white', padx=4, pady=1,
                          command=lambda sid=str(student_id), sid2=sug_id:
                              self._cefr_adjust(sid, sid2)
                          ).pack(side=tk.RIGHT, padx=2)
                theme.flat_button(self._cefr_banner_frame, 'secondary', text="Dismiss",
                          font=('Arial', 8), relief='flat', cursor='hand2',
                          bg='#6c757d', fg='white', padx=4, pady=1,
                          command=lambda sid=str(student_id), sid2=sug_id:
                              self._cefr_action(sid, sid2, 'dismissed')
                          ).pack(side=tk.RIGHT, padx=2)

            # ---- Older pending suggestions: a small grey line each, with Dismiss ----
            for old in data["older"][:3]:
                line = tk.Frame(self._ctest_older_frame, bg=COLORS['white'])
                line.pack(fill=tk.X)
                tk.Label(line, text=f"Older suggestion: {old['band']}", bg=COLORS['white'], fg=theme.colour('ink_muted', '#6c757d'),
                         font=ds.FONTS['small'], anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)
                theme.flat_button(line, 'secondary', text="Dismiss", font=('Arial', 8), relief='flat', cursor='hand2',
                          bg='#6c757d', fg='white', padx=4, pady=0,
                          command=lambda sid=str(student_id), sid2=old['id']:
                              self._cefr_action(sid, sid2, 'dismissed')
                          ).pack(side=tk.RIGHT)
            if len(data["older"]) > 3:
                tk.Label(self._ctest_older_frame, text=f"(+{len(data['older']) - 3} more older suggestions)",
                         bg=COLORS['white'], fg=theme.colour('ink_muted', '#6c757d'), font=ds.FONTS['small'], anchor='w').pack(fill=tk.X)

            # ---- Last placement result ----
            if data["level"] is not None:
                note = "" if data["final_recorded"] else "  (final not recorded)"
                self._ctest_status_var.set(
                    f"Level: {data['level']}  |  "
                    f"{data['percentage']:.0f}%  |  {data['date']}{note}"
                )
            else:
                self._ctest_status_var.set("No C-Test results yet.")

            # ---- Last 5 results (excluding soft-deleted), final and single-passage rows first ----
            for r in data["history"]:
                self._ctest_history_tree.insert("", "end", values=(
                    r["id"], r["date"], r["level"], f"{r['percentage']:.0f}%"
                ))

            # ---- Dev wipe button (only for DEV001) ----
            if str(student_id) == "DEV001":
                self._ctest_dev_wipe_btn.pack(fill=tk.X, padx=5, pady=(0, 3))

            # ---- Unclaimed temp sessions ----
            temps = conn.execute(
                """SELECT temp_id, test_date, placement_level, percentage
                   FROM temp_sessions
                   WHERE claimed_by_student_id IS NULL AND archived = 0
                   ORDER BY created_at DESC"""
            ).fetchall()

            if temps:
                tk.Label(self._ctest_temp_frame, text="Unclaimed sessions:",
                         bg=COLORS['white'], fg=COLORS['dark'],
                         font=ds.FONTS['body_bold'], anchor='w').pack(fill=tk.X)

                for t in temps:
                    row_frame = tk.Frame(self._ctest_temp_frame, bg=COLORS['white'])
                    row_frame.pack(fill=tk.X, pady=1)

                    date_str = (t["test_date"] or "")[:10]
                    info = f"{t['temp_id']} ({date_str}, {t['placement_level']})"
                    tk.Label(row_frame, text=info, bg=COLORS['white'],
                             fg=COLORS['dark'], font=ds.FONTS['small'],
                             anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)

                    temp_id = t["temp_id"]
                    sid = str(student_id)
                    theme.flat_button(
                        row_frame, 'warning', text="Link",
                        font=('Arial', 8), relief='flat', cursor='hand2',
                        bg=COLORS['secondary'], fg='white', padx=4, pady=1,
                        command=lambda tid=temp_id, s=sid: self._link_temp_session(tid, s)
                    ).pack(side=tk.RIGHT)

        except Exception:
            self._ctest_status_var.set("C-Test data unavailable")
        finally:
            conn.close()

    def _on_start_ctest_clicked(self):
        """Launch the C-Test CLI for the selected student; when it ends, refresh the panel (B4-2)."""
        if runmode.PRACTICE_MODE:
            messagebox.showinfo("C-Test", f"Disabled in {runmode.MODE_NAME}")
            return
        if runmode.TEST_MODE:
            # B4-5: only a C-Test that lives inside this sandbox, with its Zone B writer off
            try:
                cfg = runmode.load_ctest_config()
                runmode.check([_CTEST_MAIN, _CTEST_DB, cfg.DB_PATH, cfg.INVENTORY_DB_PATH])
                if not cfg.TEST_MODE:
                    raise runmode.RunModeError("C-Test's own test mode is off, so its Zone B writer would not be disabled.")
            except runmode.RunModeError as e:
                messagebox.showerror("C-Test", f"Not started: {e}")
                return
        import subprocess
        sid = self.get_selected_student_id()
        if not sid:
            messagebox.showinfo("C-Test", "Select a student first.")
            return
        proc = getattr(self, "_ctest_proc", None)
        if proc is not None and proc.poll() is None:
            messagebox.showinfo("C-Test", "A C-Test is already running. Finish it or close its window first.")
            return
        main_py = str(_CTEST_MAIN)
        if not _CTEST_MAIN.exists():
            messagebox.showerror("C-Test", f"C-Test main.py not found:\n{main_py}")
            return
        popen_kwargs = {}
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        try:
            proc = subprocess.Popen(
                [sys.executable, main_py,
                 "--student", str(sid),
                 "--mode", "adaptive"],
                cwd=str(_CTEST_MAIN.parent),
                **popen_kwargs,
            )
        except OSError as e:
            messagebox.showerror("C-Test", f"Could not start the C-Test:\n{e}")
            return
        self._ctest_proc = proc
        self._ctest_proc_sid = str(sid)
        self._schedule_ctest_poll()

    def _schedule_ctest_poll(self):
        """One polling loop at most: any pending check is cancelled before the next is set."""
        if self._ctest_poll_job is not None:
            try:
                self.after_cancel(self._ctest_poll_job)
            except tk.TclError:
                pass
        self._ctest_poll_job = self.after(self._CTEST_POLL_MS, self._ctest_poll)

    def _ctest_poll(self):
        """Check the running C-Test; when it has exited, refresh the panel if its student is still selected."""
        self._ctest_poll_job = None
        proc = self._ctest_proc
        if proc is None:
            return
        if proc.poll() is None:
            self._schedule_ctest_poll()
            return
        sid = self._ctest_proc_sid
        self._ctest_proc = None
        self._ctest_proc_sid = None
        if str(self.get_selected_student_id() or "") == str(sid):
            self._update_ctest_panel(sid)

    def destroy(self):
        """Closing the window ends the C-Test polling loop."""
        job = getattr(self, "_ctest_poll_job", None)
        if job is not None:
            self._ctest_poll_job = None
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        super().destroy()

    def _link_temp_session(self, temp_id: str, student_id: str):
        """Link an unclaimed temp session to the selected student."""
        conn = self._get_ctest_conn()
        if conn is None:
            messagebox.showerror("Error", "Cannot connect to C-Test database.")
            return
        try:
            now = datetime.now().isoformat()
            ts = conn.execute(
                "SELECT * FROM temp_sessions WHERE temp_id = ?", (temp_id,)
            ).fetchone()
            if not ts:
                messagebox.showwarning("Not found", f"Temp session {temp_id} not found.")
                conn.close()
                return
            st = models.get_student(student_id)
            name = models.display_name(st) if st else student_id
            if not messagebox.askyesno(
                    "Link guest session",
                    f"Link guest session {temp_id} ({(ts['test_date'] or '')[:10]}, level {ts['placement_level']}) "
                    f"to {name} ({student_id})?\n\n"
                    "The same unclaimed sessions are listed under every student: check this is the Temp ID the C-Test "
                    "showed at the end of this child's guest test. The portal has no way to unlink it."):
                conn.close()
                return
            conn.execute(
                """INSERT INTO c_test_results
                   (student_id, test_version, test_date, num_items, num_correct,
                    percentage, score, placement_level, completed)
                   VALUES (?, ?, ?, 0, 0, ?, ?, ?, 1)""",
                (student_id, ts["test_version"], ts["test_date"],
                 ts["percentage"], ts["score"], ts["placement_level"])
            )
            conn.execute(
                """UPDATE temp_sessions
                   SET claimed_by_student_id = ?, claimed_at = ?
                   WHERE temp_id = ?""",
                (student_id, now, temp_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Linked",
                                f"Session {temp_id} linked to student {student_id}.")
            self._update_ctest_panel(student_id)
        except Exception as e:
            conn.close()
            messagebox.showerror("Error", f"Failed to link session: {e}")

    def _on_ctest_tree_select(self, event=None):
        """Enable/disable delete button based on tree selection."""
        sel = self._ctest_history_tree.selection()
        state = tk.NORMAL if sel else tk.DISABLED
        if hasattr(self, '_ctest_delete_btn'):
            self._ctest_delete_btn.config(state=state)

    def _on_delete_ctest_result(self):
        """Soft-delete the selected C-Test result."""
        sel = self._ctest_history_tree.selection()
        if not sel:
            return
        values = self._ctest_history_tree.item(sel[0], "values")
        result_id = values[0]
        if not messagebox.askyesno("Delete Result",
                                   "Hide this result? It disappears from this panel. It is kept in the C-Test "
                                   "database marked as deleted, and the portal has no button to bring it back."):
            return
        conn = self._get_ctest_conn()
        if conn is None:
            messagebox.showerror("Error", "Cannot connect to C-Test database.")
            return
        try:
            now = datetime.now().isoformat()
            conn.execute(
                "UPDATE c_test_results SET deleted = 1, deleted_at = ? WHERE id = ?",
                (now, int(result_id))
            )
            conn.commit()
            conn.close()
            sid = self.get_selected_student_id()
            self._update_ctest_panel(sid)
        except Exception as e:
            conn.close()
            messagebox.showerror("Error", f"Failed to delete result: {e}")

    def _on_wipe_dev_results(self):
        """Soft-delete all C-Test results for DEV001."""
        if not messagebox.askyesno("Wipe DEV Results",
                                   "Wipe all DEV001 test results?"):
            return
        conn = self._get_ctest_conn()
        if conn is None:
            messagebox.showerror("Error", "Cannot connect to C-Test database.")
            return
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """UPDATE c_test_results
                   SET deleted = 1, deleted_at = ?
                   WHERE student_id = 'DEV001' AND COALESCE(deleted, 0) = 0""",
                (now,)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Done", "All DEV001 results soft-deleted.")
            self._update_ctest_panel("DEV001")
        except Exception as e:
            conn.close()
            messagebox.showerror("Error", f"Failed to wipe DEV results: {e}")

    def _cefr_action(self, student_id, suggestion_id, action):
        """Confirm or dismiss a CEFR suggestion."""
        conn = self._get_ctest_conn()
        if conn is None:
            return
        try:
            now = datetime.now().isoformat()
            if action == 'confirmed':
                conn.execute(
                    """UPDATE cefr_suggestions
                       SET status = 'confirmed', confirmed_by = 'teacher',
                           confirmed_at = ?
                       WHERE id = ?""",
                    (now, suggestion_id)
                )
            else:
                conn.execute(
                    """UPDATE cefr_suggestions
                       SET status = 'dismissed', dismissed_at = ?
                       WHERE id = ?""",
                    (now, suggestion_id)
                )
            conn.commit()
            conn.close()
            self._update_ctest_panel(student_id)
        except Exception as e:
            conn.close()
            messagebox.showerror("Error", f"CEFR action failed: {e}")

    def _cefr_adjust(self, student_id, suggestion_id):
        """Let teacher pick a different CEFR level, then confirm."""
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        chosen = simpledialog.askstring(
            "Adjust CEFR Level",
            f"Enter new level ({', '.join(levels)}):",
            parent=self
        )
        if not chosen or chosen.upper() not in levels:
            return
        conn = self._get_ctest_conn()
        if conn is None:
            return
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """UPDATE cefr_suggestions
                   SET suggested_band = ?, status = 'confirmed',
                       confirmed_by = 'teacher', confirmed_at = ?
                   WHERE id = ?""",
                (chosen.upper(), now, suggestion_id)
            )
            conn.commit()
            conn.close()
            self._update_ctest_panel(student_id)
        except Exception as e:
            conn.close()
            messagebox.showerror("Error", f"CEFR adjust failed: {e}")

    def on_students_right_click(self, event):
        iid = self.students_tree.identify_row(event.y)
        if iid:
            self.students_tree.selection_set(iid)
            try:
                self.students_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.students_menu.grab_release()

    def sort_students_tree(self, column, tree):
        """Sort students treeview by column alphabetically"""
        # Get all items in tree
        items = [(tree.set(k, column), k) for k in tree.get_children('')]
        
        # Check if this column is already sorted in this direction
        if hasattr(self, '_student_sort_column') and self._student_sort_column == column:
            # Toggle sort direction
            self._student_sort_reverse = not getattr(self, '_student_sort_reverse', False)
        else:
            # New column selected, sort ascending
            self._student_sort_reverse = False
        
        # Store current sort state
        self._student_sort_column = column
        
        # Sort items
        items.sort(reverse=self._student_sort_reverse)
        
        # Rearrange items in tree
        for index, (val, k) in enumerate(items):
            tree.move(k, '', index)
        
        # Update heading to show sort direction
        sort_indicator = " ▼" if self._student_sort_reverse else " ▲"
        for col in tree["columns"]:
            if col == column:
                tree.heading(col, text=tree.heading(col)['text'].split(" ")[0] + sort_indicator,
                           command=lambda: self.sort_students_tree(column, tree))
            else:
                heading_text = tree.heading(col)['text']
                # Remove sort indicators from other columns
                heading_text = heading_text.replace(" ▲", "").replace(" ▼", "")
                tree.heading(col, text=heading_text,
                           command=lambda c=col: self.sort_students_tree(c, tree))

    def on_student_select(self, event=None):
        sid = self.get_selected_student_id()
        if not sid:
            self._clear_student_photo()
            self._update_ctest_panel(None)
            return
        self._load_student_photo(sid)
        self._load_student_qr(sid)
        self._load_student_books(sid)
        self._update_ctest_panel(sid)

    def _clear_student_photo(self):
        if self.student_photo_label is not None:
            self.student_photo_label.delete("all")
            self.student_photo_label.create_text(120, 120, text="No photo selected",
                                               fill=COLORS['dark'], font=('Arial', 9))
        if self.student_photo_caption is not None:
            self.student_photo_caption.config(text="")
        self.student_photo_image = None
        if self.student_qr_label is not None:
            self.student_qr_label.delete("all")
            self.student_qr_label.create_text(100, 100, text="No QR", fill=COLORS['dark'])
        self.student_qr_image = None

    def _on_photo_canvas_resize(self, event):
        """Redraw photo when canvas resizes."""
        if hasattr(self, 'current_student_id') and self.current_student_id:
            self._load_student_photo(self.current_student_id)
    
    def _on_qr_canvas_resize(self, event):
        """Redraw QR code when canvas resizes."""
        if hasattr(self, 'current_student_id') and self.current_student_id:
            self._load_student_qr(self.current_student_id)

    def _load_student_photo(self, student_id: str):
        if self.student_photo_label is None:
            return

        photo_path = None
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            candidate = STUDENT_PHOTOS_DIR / f"{student_id}{ext}"
            if candidate.exists():
                photo_path = candidate
                break

        if not photo_path:
            self._clear_student_photo()
            if self.student_photo_caption is not None:
                self.student_photo_caption.config(text=f"ID: {student_id}")
            return

        try:
            img = Image.open(photo_path)
            img = img.convert("RGB")
            # Get canvas size
            canvas_width = self.student_photo_label.winfo_width()
            canvas_height = self.student_photo_label.winfo_height()
            if canvas_width < 50:
                canvas_width = 240
            if canvas_height < 50:
                canvas_height = 240
            # Resize image to fit canvas
            img.thumbnail((canvas_width - 10, canvas_height - 10), Image.Resampling.LANCZOS)
            self.student_photo_image = ImageTk.PhotoImage(img)
            self.student_photo_label.delete("all")
            self.student_photo_label.create_image(canvas_width // 2, canvas_height // 2, image=self.student_photo_image)
            if self.student_photo_caption is not None:
                self.student_photo_caption.config(text=f"ID: {student_id}")
        except Exception as e:
            self._clear_student_photo()
            messagebox.showerror("Photo error", f"Could not load photo for {student_id}:\n{e}")
        
        # Load and display QR code
        self._load_student_qr(student_id)

    def _load_student_qr(self, student_id: str):
        """Generate and display QR code for student."""
        if self.student_qr_label is None:
            return
        
        try:
            from PIL import Image as PILImage
            qr_path = qr_utils.generate_student_qr(student_id)
            
            if qr_path and Path(qr_path).exists():
                qr_img = PILImage.open(qr_path)
                # Get canvas size and resize dynamically
                canvas_width = self.student_qr_label.winfo_width()
                canvas_height = self.student_qr_label.winfo_height()
                if canvas_width < 50:
                    canvas_width = 200
                if canvas_height < 50:
                    canvas_height = 200
                qr_img.thumbnail((canvas_width - 10, canvas_height - 10), PILImage.Resampling.LANCZOS)
                self.student_qr_image = ImageTk.PhotoImage(qr_img)
                self.student_qr_label.delete("all")
                self.student_qr_label.create_image(canvas_width // 2, canvas_height // 2, image=self.student_qr_image)
            else:
                self.student_qr_label.delete("all")
                self.student_qr_label.create_text(100, 100, text="No QR", fill=COLORS['dark'])
        except Exception as e:
            self.student_qr_label.delete("all")
            self.student_qr_label.create_text(100, 100, text="Error", fill=COLORS['dark'])

    def _load_student_books(self, student_id: str):
        """Load and display books checked out to this student."""
        from datetime import datetime
        
        if not hasattr(self, "student_books_tree"):
            return
        
        # Clear existing rows
        for row in self.student_books_tree.get_children():
            self.student_books_tree.delete(row)
        
        # Get all assignments for this student
        conn = models.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT a.assignment_id, i.name, a.status, a.assigned_date
            FROM assignments a
            JOIN items i ON a.item_id = i.item_id
            WHERE a.student_id = ? AND a.status = 'assigned'
            ORDER BY a.assigned_date DESC
        """, (student_id,))
        rows = cur.fetchall()
        conn.close()
        
        # Display each book
        for row in rows:
            assignment_id, book_name, status, assigned_date = row
            
            # Calculate status and days
            if assigned_date:
                try:
                    assigned_dt = datetime.fromisoformat(assigned_date.replace("Z", "+00:00"))
                    days_out = (datetime.now(assigned_dt.tzinfo) - assigned_dt).days
                    status_label = "Late" if days_out >= 30 else "Out"
                except:
                    status_label = "Out"
                    days_out = 0
            else:
                status_label = "Out"
                days_out = 0
            
            self.student_books_tree.insert(
                "",
                tk.END,
                values=(assignment_id, book_name, status_label, str(days_out))
            )

    def load_students(self, term: Optional[str] = None):
        if not hasattr(self, "students_tree"):
            return
        for row in self.students_tree.get_children():
            self.students_tree.delete(row)

        if term:
            students = models.search_students(term)
        else:
            students = models.list_students()

        for st in students:
            self.students_tree.insert(
                "",
                tk.END,
                values=(
                    st["student_id"],
                    st["first_name"],
                    st.get("last_name") or "",
                    st.get("level") or "",
                    st.get("status") or "",
                ),
            )
        self._clear_student_photo()

    def on_students_search(self):
        term = self.students_search_var.get().strip()
        if term:
            self.load_students(term)
        else:
            self.load_students()

    def on_students_refresh(self):
        self.students_search_var.set("")
        self.load_students()

    def filter_students_by_day(self, day_name):
        """Filter students list to show only those attending classes on the selected day"""
        if not hasattr(self, "students_tree"):
            return
        
        # Get all students
        all_students = models.list_students()
        
        # Get class names for this day and clean them
        classes_today = self.schedule_classes_by_day.get(day_name, [])
        
        if not classes_today:
            # No classes for this day, clear students tree
            for row in self.students_tree.get_children():
                self.students_tree.delete(row)
            return
        
        # Clean class names: remove newlines and extra whitespace
        cleaned_classes = []
        for class_name in classes_today:
            clean_name = class_name.replace('\n', ' ').strip()
            if clean_name:
                cleaned_classes.append(clean_name)
        
        # Extract level names and student names from class descriptions
        levels_today = set()
        student_names_today = set()
        
        for class_name in cleaned_classes:
            # Extract level (text in parentheses)
            if '(' in class_name and ')' in class_name:
                level = class_name.split('(')[1].split(')')[0].strip()
                if level:
                    levels_today.add(level)
            
            # Also look for level patterns at the end like "SM1", "SM2", "PN1"
            parts = class_name.split()
            for part in parts[-3:]:  # Check last 3 parts
                part_lower = part.lower()
                if any(c.isdigit() for c in part):  # Has numbers
                    levels_today.add(part_lower)
            
            # Extract student names (text before parentheses or separated by commas)
            if '(' in class_name:
                names_part = class_name.split('(')[0].strip()
            else:
                # Take everything except last part if it looks like a level
                parts = class_name.split()
                last_part = parts[-1].lower() if parts else ""
                if any(c.isdigit() for c in last_part):
                    names_part = ' '.join(parts[:-1])
                else:
                    names_part = class_name
            
            # Split by comma and ampersand to get individual names
            for name in names_part.replace('&', ',').split(','):
                name = name.strip().lower()
                # Remove level codes
                for i in range(10):
                    name = name.replace(f'sm{i}', '').replace(f'pn{i}', '').replace(f'p{i}', '')
                name = name.replace('and', '').strip()
                if name and len(name) > 1:
                    student_names_today.add(name)
        
        # Clear the tree
        for row in self.students_tree.get_children():
            self.students_tree.delete(row)
        
        # Filter students by name OR level match
        matching_students = []
        for student in all_students:
            student_level = student.get("level", "").strip().lower()
            student_first = student.get("first_name", "").strip().lower()
            student_last = student.get("last_name", "").strip().lower()
            full_name = f"{student_first} {student_last}".strip()
            
            # Check if student matches any extracted level OR name
            is_match = False
            
            # Check level match (exact)
            if student_level and student_level in levels_today:
                is_match = True
            
            # Check name match (partial/contains for flexibility)
            if not is_match:
                for target_name in student_names_today:
                    if target_name in student_first or target_name in student_last or target_name in full_name:
                        is_match = True
                        break
            
            if is_match:
                matching_students.append(student)
        
        # Display filtered students
        for st in matching_students:
            self.students_tree.insert(
                "",
                tk.END,
                values=(
                    st["student_id"],
                    st["first_name"],
                    st.get("last_name") or "",
                    st.get("level") or "",
                    st.get("status") or "",
                ),
            )
        
        self._clear_student_photo()

    def get_selected_student_id(self):
        selection = self.students_tree.selection()
        if not selection:
            return None
        values = self.students_tree.item(selection[0], "values")
        return values[0]

    def _one_selected_student_id(self, action, none_text="Please select a student first."):
        """The ID if exactly one student is selected. Otherwise say why (none, or several: these actions have no
        several-student version) and return None."""
        sel = self.students_tree.selection()
        if not sel:
            messagebox.showinfo("No selection", none_text)
            return None
        if len(sel) > 1:
            messagebox.showinfo("Several students selected",
                                f"Several students are selected. Select one student to {action}.")
            return None
        return self.students_tree.item(sel[0], "values")[0]

    def on_add_student(self):
        from inventory.validation import validate_student_id, validate_name, validate_line_id

        # Loop until valid student_id
        while True:
            sid = simpledialog.askstring("New Student", "Student ID:", parent=self)
            if not sid:
                return

            # Validate ID immediately
            valid, error = validate_student_id(sid)
            if not valid:
                retry = messagebox.askyesno(
                    "Invalid Student ID",
                    f"{error}\n\nWould you like to try again?",
                    icon='warning'
                )
                if not retry:
                    return
                continue  # Ask for ID again
            break  # ID is valid, proceed

        # Loop until valid first name
        while True:
            fname = simpledialog.askstring("New Student", "First name:", parent=self)
            if not fname:
                retry = messagebox.askyesno(
                    "Missing First Name",
                    "First name is required.\n\nWould you like to try again?",
                    icon='warning'
                )
                if not retry:
                    return
                continue  # Ask for name again

            # Validate first name immediately
            valid, error = validate_name(fname, "First name")
            if not valid:
                retry = messagebox.askyesno(
                    "Invalid First Name",
                    f"{error}\n\nWould you like to try again?",
                    icon='warning'
                )
                if not retry:
                    return
                continue  # Ask for name again
            break  # Name is valid, proceed

        # Optional last name with validation
        while True:
            lname = simpledialog.askstring("New Student", "Last name (optional):", parent=self) or None
            if not lname:
                break  # Optional, skip validation

            # Validate last name if provided
            valid, error = validate_name(lname, "Last name")
            if not valid:
                retry = messagebox.askyesno(
                    "Invalid Last Name",
                    f"{error}\n\nWould you like to try again?",
                    icon='warning'
                )
                if not retry:
                    lname = None
                    break
                continue  # Ask again
            break  # Valid or skipped

        level = simpledialog.askstring("New Student", "Level (SM3, SM4, etc.):", parent=self) or None

        # Optional parent LINE ID: a bad shape is refused here, before anything is saved
        while True:
            line_id = simpledialog.askstring("New Student", "Parent LINE ID (optional):", parent=self) or None
            if not line_id:
                line_id = None
                break
            valid, error = validate_line_id(line_id.strip())
            if valid:
                break
            if not messagebox.askyesno(
                    "Invalid LINE ID",
                    f"{error}\n\nTry again? (No cancels adding this student.)",
                    icon='warning'
            ):
                messagebox.showinfo("New Student", "Cancelled. The student was not added.")
                return

        try:
            models.add_student(
                student_id=sid,
                first_name=fname,
                last_name=lname,
                level=level,
                parent_line_id=line_id,
            )
            self.load_students()
        except Exception as e:
            messagebox.showerror("Error", f"Could not add student:\n{e}")

    def on_edit_student(self):
        sid = self._one_selected_student_id("edit", "Please select a student to edit.")
        if not sid:
            return

        st = models.get_student(sid)
        if not st:
            messagebox.showerror("Error", "Selected student not found in database.")
            return

        # The student ID is not editable here: changing it is "Rename student..." on the admin page.
        answers = {}
        for key, prompt, initial in (
            ("first_name", "First name:", st["first_name"]),
            ("last_name", "Last name:", st.get("last_name") or ""),
            ("level", "Level:", st.get("level") or ""),
            ("status", "Status (active/inactive):", st.get("status") or ""),
        ):
            value = simpledialog.askstring("Edit Student", prompt, initialvalue=initial, parent=self)
            if value is None:
                messagebox.showinfo("Edit Student", "Cancelled. Nothing was changed.")
                return
            answers[key] = value.strip()

        if not answers["first_name"]:
            messagebox.showwarning("Missing", "First name is required. Nothing was changed.")
            return
        kept_invalid = None
        if answers["status"] != (st.get("status") or "").strip():  # changed: must be one of the two values
            if answers["status"].lower() not in models.STUDENT_STATUSES:
                messagebox.showwarning(
                    "Edit Student", "Status must be 'active' or 'inactive'. Nothing was changed.")
                return
            answers["status"] = answers["status"].lower()
        else:  # unchanged: accepted as it is, whatever its value
            answers["status"] = st.get("status") or None
            stored = st.get("status") or ""
            if stored.strip().lower() not in models.STUDENT_STATUSES:     # kept as it is, but said after saving (D5 b)
                kept_invalid = f"'{stored}'" if stored.strip() else "blank"

        # The parent LINE ID is never shown in full (and so never edited in place): it changes only on an explicit Yes.
        from inventory.validation import validate_line_id
        current = (st.get("parent_line_id") or "").strip()
        answers["parent_line_id"] = current              # unchanged unless the steps below say otherwise
        if current:
            question = f"Change the parent LINE ID? (now \u2026{current[-4:]})"
        else:
            question = "This student has no parent LINE ID. Add one?"
        if messagebox.askyesno("Edit Student", question):
            typed = simpledialog.askstring(
                "Edit Student", "New parent LINE ID (type CLEAR to remove it):", parent=self)
            if typed is None:
                messagebox.showinfo("Edit Student", "Cancelled. Nothing was changed.")
                return
            typed = typed.strip()
            if typed.upper() == "CLEAR":
                if current:
                    if not messagebox.askyesno(
                            "Clear parent LINE ID?",
                            "This removes the parent's LINE ID. It cannot be typed back from memory.\n\nRemove it?"):
                        messagebox.showinfo("Edit Student", "Cancelled. Nothing was changed.")
                        return
                    answers["parent_line_id"] = ""
            elif typed:                                   # an empty box keeps the stored ID
                valid, error = validate_line_id(typed)
                if not valid:
                    messagebox.showwarning("Invalid LINE ID", f"{error}\n\nNothing was changed.")
                    return
                answers["parent_line_id"] = typed

        changes = {k: (v or None) for k, v in answers.items() if (v or None) != (st.get(k) or None)}
        try:
            if changes:
                models.update_student_fields(sid, changes)
            self.load_students()
        except Exception as e:
            messagebox.showerror("Error", f"Could not update student:\n{e}")
            return
        if kept_invalid:
            messagebox.showwarning(
                "Edit Student",
                f"Saved. Note: this student's status is {kept_invalid}, which is neither 'active' nor 'inactive', "
                "so it was left as it is. Edit the student again and type active or inactive.")

    def on_rename_student(self):
        """Admin page: change a student's ID safely. One transaction; everything keyed to the old ID moves."""
        if not self._check_admin_password():
            return
        title = "Rename student"
        old = simpledialog.askstring(
            title, "Student ID to rename:", initialvalue=self.get_selected_student_id() or "", parent=self)
        if old is None:
            messagebox.showinfo(title, "Cancelled. Nothing was changed.")
            return
        new = simpledialog.askstring(title, "New student ID:", parent=self)
        if new is None:
            messagebox.showinfo(title, "Cancelled. Nothing was changed.")
            return
        old, new = old.strip(), new.strip()
        if not models.get_student(old) and models.get_student(new):
            # the new ID is a real student and the old one is gone: only a rename done here may be finished
            if not models.rename_logged(old, new):
                messagebox.showerror(
                    title,
                    f"'{old}' to '{new}': not a rename done here; reattaching left-behind rows is a separate data repair. "
                    "Nothing was moved.")
                return
            if not messagebox.askyesno(
                    title, f"'{old}' is already '{new}' in the database.\n\n"
                           "Run the photo and C-Test step again? It only does what is still missing."):
                return
            _report_rename_extras(title, old, new, _rename_student_extras(old, new))
            return
        try:
            counts = models.preview_rename(old, new)
        except Exception as e:
            messagebox.showerror(title, f"Cannot rename:\n{e}")
            return

        st = models.get_student(old)
        moving = [f"  {t}: {n}" for t, n in counts.items() if n] or ["  (no other records)"]
        lines = [f"Rename {models.display_name(st)} from '{old}' to '{new}'?", "",
                 "Records that move to the new ID:", *moving,
                 "  C-Test results (c_test.db) and the photo file follow too.", ""]
        if st.get("qr_code"):
            lines += [f"The stored QR code text ({st['qr_code']}) is copied across unchanged, so it will be stale.", ""]
        lines += [f"Printed QR cards carry the old ID (S:{old}) and must be reprinted.",
                  "Zone B keeps the old ID in its own data (jobs.db, messages); that is not changed.",
                  "", "There is no undo."]
        if not messagebox.askyesno(title, "\n".join(lines)):
            return

        try:
            models.rename_student(old, new)
        except Exception as e:
            messagebox.showerror(title, f"Nothing was changed.\n{e}")
            return
        self.load_students()
        _report_rename_extras(title, old, new, _rename_student_extras(old, new))

    @staticmethod
    def _delete_student_text(plan):
        """The confirmation for one delete: who, what goes with the student, what stays behind."""
        known_with = (("class_roster", "class places"), ("student_overrides", "overrides"),
                      ("c_test_results", "C-Test copies in inventory.db"))
        known_left = (("attendance", "attendance marks"), ("qr_scans", "QR scans"))

        def lines(found, known):
            out = [f"  {label}: {found.get(t, 0)}" for t, label in known]
            out += [f"  {t}: {n}" for t, n in found.items() if n and t not in dict(known)]
            return out

        line_id = []
        if plan.get("line_id_tail"):
            line_id = [f"Parent LINE ID {plan['line_id_tail']} is deleted with the student. "
                       "It cannot be typed back from memory.", ""]
        return "\n".join(
            [f"Delete {plan['name']} ({plan['student_id']})?", "", "Deleted with the student:",
             *lines(plan["deleted_with"], known_with), "",
             "Stays behind under the old ID, and no longer shows for any student:",
             *lines(plan["left_behind"], known_left), "", *line_id, "There is no undo."])

    def on_delete_student(self):
        if len(self.students_tree.selection()) > 1:
            return self.on_mass_delete_students()
        sid = self.get_selected_student_id()
        if not sid:
            messagebox.showinfo("No selection", "Please select a student to delete.")
            return

        # A student with a loan or an extra lesson is refused first, in plain words, before any password or question
        try:
            plan = models.delete_student_preview(sid)
        except Exception as e:
            messagebox.showerror("Error", f"Could not check the student:\n{e}")
            return
        if plan["refused"]:
            messagebox.showwarning("Cannot delete", plan["refused"])
            return

        # Check password first
        if not self._check_admin_password():
            return

        if not messagebox.askyesno("Confirm delete", self._delete_student_text(plan)):
            return

        try:
            models.delete_student(sid)
            self.load_students()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete student:\n{e}")

    def on_mass_delete_students(self):
        """Mass delete students with password protection"""
        # Get students_tree which is in Students tab
        if not hasattr(self, 'students_tree'):
            messagebox.showerror("Error", "Students tab not initialized")
            return
        self.notebook.select(0)          # the selection is made on the Students tab: show it behind every dialog
        
        selected_items = self.students_tree.selection()
        
        if not selected_items:
            messagebox.showinfo(
                "No selection",
                "Select the students to delete on the Students tab (Ctrl+click for several), "
                "then press Mass Delete again.")
            return
        
        # Check password first
        if not self._check_admin_password():
            return

        # Who would be deleted, and who would be refused (a loan or an extra lesson)
        doomed, refused = [], []          # (student_id, "Name (ID)"[, reason])
        with_line_id = 0                  # how many of the doomed have a parent LINE ID
        for item in selected_items:
            values = self.students_tree.item(item, 'values')
            if not values:
                continue
            student_id = str(values[0])
            try:
                plan = models.delete_student_preview(student_id)
            except Exception as e:
                refused.append((student_id, student_id, str(e)))
                continue
            label = f"{plan['name']} ({student_id})"
            if plan["refused"]:
                refused.append((student_id, label, plan["refused"]))
            else:
                doomed.append((student_id, label))
                if plan.get("line_id_tail"):
                    with_line_id += 1

        def listed(entries):
            shown = [f"  {e[1]}" for e in entries[:10]]
            if len(entries) > 10:
                shown.append(f"  ...and {len(entries) - 10} more")
            return "\n".join(shown)

        if not doomed:
            messagebox.showwarning(
                "Cannot delete",
                "None of the selected students can be deleted: each has a loan or an extra lesson.\n\n" + listed(refused))
            return

        text = f"These {len(doomed)} student(s) will be deleted:\n{listed(doomed)}\n\n"
        if with_line_id:
            text += (f"{with_line_id} of them {'has' if with_line_id == 1 else 'have'} a parent LINE ID, "
                     "which is deleted too.\n\n")
        if refused:
            text += (f"{len(refused)} selected student(s) would be refused (a loan or an extra lesson) "
                     f"and stay:\n{listed(refused)}\n\n")
        text += f"Permanently delete these {len(doomed)} student(s)? This action CANNOT be undone."
        if not messagebox.askyesno("FINAL CONFIRMATION", text, icon=messagebox.WARNING):
            return

        # Delete them one at a time; say what could not be deleted instead of hiding it
        deleted_count, failed = 0, []
        for student_id, label in doomed:
            try:
                models.delete_student(student_id)
                deleted_count += 1
            except Exception as e:
                failed.append(f"{label}: {e}")
        failed += [e[1] for e in refused]

        message = f"Deleted {deleted_count} student(s)."
        if failed:
            message += f"\n\n{len(failed)} could not be deleted:\n" + "\n".join(f"  {f}" for f in failed[:10])
        messagebox.showinfo("Success" if not failed else "Done", message)
        self.load_students()
        self.notebook.select(0)

    def on_generate_student_qr(self):
        sid = self._one_selected_student_id("make a QR for")
        if not sid:
            return
        try:
            path = qr_utils.generate_student_qr(sid)
            messagebox.showinfo(
                "QR Generated",
                f"QR code for student '{sid}' saved to:\n{Path(path)}",
            )
            # Refresh the QR display in the profile
            self._load_student_qr(sid)
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate student QR:\n{e}")

    def on_export_selected_student_csv(self):
        sid = self._one_selected_student_id("export")
        if not sid:
            return

        # Check password first
        if not self._check_admin_password():
            return

        st = models.get_student(sid)
        if not st:
            messagebox.showerror("Error", "Selected student not found in database.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export selected student to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"student_{sid}.csv",
        )
        if not file_path:
            return

        try:
            from csv import writer
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                w = writer(f)
                w.writerow(["student_id", "first_name", "last_name", "level", "status", "parent_line_id"])
                w.writerow([
                    st.get("student_id", ""),
                    st.get("first_name", ""),
                    st.get("last_name", ""),
                    st.get("level", ""),
                    st.get("status", ""),
                    st.get("parent_line_id", ""),
                ])
            messagebox.showinfo("Export complete", f"Student exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export failed", f"Could not export student:\n{e}")

    # ---------- ASSIGNMENTS TAB ----------

    def _build_assignments_tab(self, parent):
        # Main container
        main_container = tk.Frame(parent, bg=COLORS['light'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Blue toolbar band
        toolbar = tk.Frame(main_container, bg=COLORS['primary'], height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)
        
        # Search student section in toolbar - single search bar
        search_frame = tk.Frame(toolbar, bg=COLORS['primary'])
        search_frame.pack(side=tk.LEFT, padx=15, pady=10)
        
        tk.Label(search_frame, text=f"{self.t('search')} {self.t('student')}:", bg=COLORS['primary'], fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.assignments_search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.assignments_search_var, width=30, font=('Arial', 9))
        search_entry.pack(side=tk.LEFT, padx=5, pady=10)
        search_entry.bind('<Return>', lambda e: self.on_assignments_search())
        
        # Search button
        btn_search = theme.flat_button(search_frame, 'secondary', text=self.t('search'), bg=COLORS['secondary'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_assignments_search)
        btn_search.pack(side=tk.LEFT, padx=3)

        # Scan student QR button
        btn_scan_student = theme.flat_button(search_frame, 'primary', text=f"📱 {self.t('scan_student_card')}", bg=COLORS['success'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_scan_student_qr)
        btn_scan_student.pack(side=tk.LEFT, padx=3)
        
        # Clear and refresh buttons
        btn_clear_selection = theme.flat_button(search_frame, 'secondary', text=self.t('clear'), bg=COLORS['danger'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_clear_student_selection)
        btn_clear_selection.pack(side=tk.LEFT, padx=3)
        
        btn_refresh = theme.flat_button(search_frame, 'secondary', text=self.t('refresh'), bg=COLORS['dark'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.load_assignments)
        btn_refresh.pack(side=tk.LEFT, padx=3)
        
        btn_download_books = theme.flat_button(search_frame, 'secondary', text=f"📥 {self.t('download_csv')}", bg=COLORS['secondary'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_export_books_csv)
        btn_download_books.pack(side=tk.LEFT, padx=3)
        
        btn_upload_books = theme.flat_button(search_frame, 'warning', text=f"📤 {self.t('import_books_csv')}", bg=COLORS['success'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_import_books_csv)
        btn_upload_books.pack(side=tk.LEFT, padx=3)
        
        # Store search variables internally (not visible)
        self.assignments_search_id_var = tk.StringVar()
        self.assignments_search_first_var = tk.StringVar()
        self.assignments_search_last_var = tk.StringVar()
        self.assignments_search_level_var = tk.StringVar()

        # Content area with two panels
        content = tk.Frame(main_container, bg=COLORS['light'])
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Left panel - Student search and photo
        left_panel = tk.Frame(content, bg=COLORS['white'], relief='solid', borderwidth=1)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        left_panel.config(width=300)
        left_panel.pack_propagate(False)
        
        # Student info header
        info_header = tk.Frame(left_panel, bg=COLORS['primary'], height=40)
        info_header.pack(fill=tk.X)
        info_header.pack_propagate(False)
        
        tk.Label(info_header, text=f"📚 {self.t('student')} Info", bg=COLORS['primary'], fg='white', font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)
        
        # Student photo canvas
        self.assignment_student_photo = tk.Canvas(left_panel, bg=COLORS['light'], relief='solid', borderwidth=1, width=250, height=250)
        self.assignment_student_photo.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.assignment_student_photo.create_text(125, 125, text="No student selected", fill=COLORS['dark'], font=('Arial', 10))
        
        # Student name label
        self.assignment_student_name = tk.Label(left_panel, text="", font=('Arial', 11, 'bold'), fg=COLORS['primary'], wraplength=280)
        self.assignment_student_name.pack(pady=10)
        
        # Scan book button
        theme.flat_button(left_panel, 'primary', text=f"📱 {self.t('scan_book')}", bg=COLORS['success'], fg='white', font=('Arial', 10, 'bold'), padx=10, pady=8, command=self.on_scan_book_for_student).pack(pady=10, padx=10, fill=tk.X)
        
        # Right panel - Active assignments list
        right_panel = tk.Frame(content, bg=COLORS['white'], relief='solid', borderwidth=1)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # List header
        list_header = tk.Frame(right_panel, bg=COLORS['primary'], height=40)
        list_header.pack(fill=tk.X)
        list_header.pack_propagate(False)
        
        tk.Label(list_header, text=f"📖 {self.t('book_assignments')}", bg=COLORS['primary'], fg='white', font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)

        theme.flat_button(list_header, 'primary', text="\u21a9 Return Book",
                  bg=COLORS['success'], fg='white',
                  font=('Arial', 10, 'bold'), padx=10, pady=4,
                  command=self.on_mark_returned).pack(
                      side=tk.RIGHT, padx=15, pady=6)
        
        # Assignments treeview
        tree_frame = tk.Frame(right_panel, bg=COLORS['white'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = (
            "assignment_id",
            "book_id",
            "book_name",
            "student_id",
            "student_name",
            "status",
            "checkout_date",
            "checkin_date",
        )
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        headers = [
            "ID",
            self.t("book_id"),
            self.t("book"),
            self.t("student_id"),
            self.t("student"),
            self.t("status"),
            "Checked Out",
            "Checked In",
        ]
        for col, text in zip(columns, headers):
            tree.heading(col, text=text)

        tree.column("assignment_id", width=60, anchor=tk.CENTER)
        tree.column("book_id", width=100)
        tree.column("book_name", width=160)
        tree.column("student_id", width=100)
        tree.column("student_name", width=160)
        tree.column("status", width=100, anchor=tk.CENTER)
        tree.column("checkout_date", width=140)
        tree.column("checkin_date", width=140)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.assignments_tree = tree
        self.selected_student_id = None  # Track selected student for book scanning

    def on_book_student_click(self, event):
        """Navigate to student profile when double-clicking a book assignment."""
        selection = self.assignments_tree.selection()
        if not selection:
            return
        
        item = self.assignments_tree.item(selection[0])
        student_id = item["values"][3]  # student_id column
        
        if student_id:
            # Switch to Students tab and focus the student
            self.notebook.select(0)  # Students tab is now at index 0
            self._focus_student_in_ui(student_id)

    def load_assignments(self):
        from datetime import datetime, timedelta
        
        if not hasattr(self, "assignments_tree"):
            return
        for row in self.assignments_tree.get_children():
            self.assignments_tree.delete(row)

        assns = models.get_all_assignments()
        for a in assns:
            full_name = models.display_name(a, "student_first_name", "student_last_name")
            
            # Determine status: Out, Late (30+ days), or Returned
            status = a.get("status") or ""
            if status.lower() == "assigned":
                assigned_date = a.get("assigned_date")
                if assigned_date:
                    try:
                        assigned_dt = datetime.fromisoformat(assigned_date.replace("Z", "+00:00"))
                        days_out = (datetime.now(assigned_dt.tzinfo) - assigned_dt).days
                        status = "Late" if days_out >= 30 else "Out"
                    except:
                        status = "Out"
                else:
                    status = "Out"
            elif status.lower() == "returned":
                status = "Returned"
            
            self.assignments_tree.insert(
                "",
                tk.END,
                values=(
                    a["assignment_id"],
                    a["item_id"],
                    a.get("item_name") or "",
                    a["student_id"],
                    full_name,
                    status,
                    _local_time(a.get("assigned_date")),        # stored as UTC; shown in local time
                    _local_time(a.get("returned_date")),
                ),
            )

    def get_selected_assignment_id(self):
        selection = self.assignments_tree.selection()
        if not selection:
            return None
        values = self.assignments_tree.item(selection[0], "values")
        return int(values[0])

    def on_assign_item(self):
        item_id = simpledialog.askstring("Assign Item", "Item ID:", parent=self)
        if not item_id:
            return
        student_id = simpledialog.askstring("Assign Item", "Student ID:", parent=self)
        if not student_id:
            return

        item = models.get_item(item_id)
        if not item:
            messagebox.showerror("Error", f"Item '{item_id}' not found.")
            return
        student = models.get_student(student_id)
        if not student:
            messagebox.showerror("Error", f"Student '{student_id}' not found.")
            return

        notes = simpledialog.askstring("Assign Item", "Notes (optional):", parent=self) or None

        try:
            models.assign_item_to_student(item_id=item_id, student_id=student_id, notes=notes)
            self.load_assignments()
        except Exception as e:
            messagebox.showerror("Error", f"Could not assign item:\n{e}")

    def _refresh_books_out(self):
        """Re-render the Students tab 'Books Out' panel, if a student is shown."""
        try:
            sid = self.get_selected_student_id()
            if sid:
                self._load_student_books(sid)
        except Exception as e:
            print(f"[books] could not refresh Books Out: {e}")

    def _lend_book(self, item_id, student_id, notes=None):
        """Lend one book to one student, with an 'already lent' guard.

        Shared by the Books tab scan and the QR-menu scan so both behave
        identically. Returns True only if the loan was recorded.
        """
        book = models.get_item(item_id)
        if not book:
            messagebox.showerror(
                "Book not found",
                f"No book with the code '{item_id}' is in the system.\n\n"
                "Check the label, or add the book on the Items tab first.")
            return False
        book_name = book.get("name") or item_id

        student = models.get_student(student_id)
        if not student:
            messagebox.showerror(
                "Student not found",
                f"No student with the ID '{student_id}' is in the system.")
            return False

        if (student.get("status") or "").strip().lower() == "inactive":
            messagebox.showwarning(
                "Student is inactive",
                f"{models.display_name(student)} is marked inactive, so '{book_name}' was not lent.\n\n"
                "To lend to this student, set the Status to active in Edit Student.")
            return False

        try:
            open_loans = models.get_active_assignments_for_item(item_id)
        except Exception as e:
            print(f"[books] could not check loans for {item_id}: {e}")
            messagebox.showerror(
                "Could not check the book",
                "The book's current status could not be read, so it has "
                "not been lent.\n\nPlease try again.")
            return False

        if open_loans:
            loan = open_loans[0]
            holder = models.display_name(loan) or loan.get("student_id", "someone")
            since = (loan.get("assigned_date") or "")[:10]
            since_txt = f" since {since}" if since else ""
            if loan.get("student_id") == student_id:
                messagebox.showinfo(
                    "Already lent to this student",
                    f"'{book_name}' is already lent to {holder}{since_txt}.")
            else:
                messagebox.showwarning(
                    "Book is already lent out",
                    f"'{book_name}' is already lent to {holder}{since_txt}.\n\n"
                    "It must come back before it can go out to someone else.")
            return False

        try:
            models.assign_item_to_student(
                item_id=item_id, student_id=student_id, notes=notes)
        except ValidationError as e:                 # a refusal (B5a-2, B5a-11): its own words say why
            messagebox.showerror("Could not lend the book", str(e))
            return False
        except Exception as e:
            print(f"[books] lend failed ({item_id} -> {student_id}): {e}")
            messagebox.showerror(
                "Could not lend the book",
                f"'{book_name}' was not lent out and nothing was saved.\n\n"
                "Please try again, or tell David if it keeps happening.")
            return False

        self.load_assignments()
        self._refresh_books_out()
        messagebox.showinfo(
            "Book lent",
            f"'{book_name}' is now lent to {models.display_name(student)}.")
        return True

    def _return_book(self, assignment_id, book_name="This book"):
        """Record one book coming back. Returns True if it was saved."""
        notes = simpledialog.askstring(
            "Return Book",
            "Anything to note? (e.g. damaged, late) - leave blank if fine:",
            parent=self,
        )
        if notes is None:
            return False  # Cancel: nothing is recorded
        notes = notes.strip() or None

        try:
            models.mark_assignment_returned(assignment_id, notes=notes)
        except Exception as e:
            print(f"[books] return failed (assignment {assignment_id}): {e}")
            messagebox.showerror(
                "Could not record the return",
                "The return was not saved. Please try again, or tell David "
                "if it keeps happening.")
            return False

        self.load_assignments()
        self._refresh_books_out()
        messagebox.showinfo(
            "Book returned", f"'{book_name}' is back in the library.")
        return True

    def on_mark_returned(self):
        """Return the book selected in the Books tab list."""
        assignment_id = self.get_selected_assignment_id()
        if not assignment_id:
            messagebox.showinfo(
                "No book selected",
                "Click the book being brought back, then press Return Book.")
            return

        values = self.assignments_tree.item(
            self.assignments_tree.selection()[0], "values")
        book_name = values[2] or values[1]
        status = (values[5] or "").strip().lower()
        if status == "returned":
            messagebox.showinfo(
                "Already returned",
                f"'{book_name}' is already marked as returned.")
            return

        if not messagebox.askyesno(
                "Return book", f"Mark '{book_name}' as returned?"):
            return
        self._return_book(assignment_id, book_name)

    def on_return_selected_book(self):
        """Return the book selected in the Students tab 'Books Out' panel."""
        sel = self.student_books_tree.selection()
        if not sel:
            messagebox.showinfo(
                "No book selected",
                "Click the book the student is bringing back, then press "
                "Return Book.")
            return

        values = self.student_books_tree.item(sel[0], "values")
        try:
            assignment_id = int(values[0])
        except (TypeError, ValueError):
            messagebox.showerror(
                "Could not read that row",
                "This book row could not be identified. Refresh the student "
                "and try again.")
            return
        book_name = values[1]

        if not messagebox.askyesno(
                "Return book", f"Mark '{book_name}' as returned?"):
            return
        self._return_book(assignment_id, book_name)

    def on_books_out_right_click(self, event):
        """Right-click menu on the Students tab 'Books Out' rows."""
        iid = self.student_books_tree.identify_row(event.y)
        if iid:
            self.student_books_tree.selection_set(iid)
            try:
                self.books_out_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.books_out_menu.grab_release()

    def on_export_books_csv(self):
        """Export all books (assignments) to CSV with password protection"""
        # Check password first
        if not self._check_admin_password():
            return

        file_path = filedialog.asksaveasfilename(
            title="Export Books to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="books.csv",
        )
        if not file_path:
            return

        try:
            from csv import writer
            assignments = models.get_all_assignments()
            
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                w = writer(f)
                w.writerow(["assignment_id", "student_id", "item_id", "assigned_date", "returned_date", "status", "notes"])
                for assign in assignments:
                    w.writerow([
                        assign.get("assignment_id", ""),
                        assign.get("student_id", ""),
                        assign.get("item_id", ""),
                        assign.get("assigned_date", ""),
                        assign.get("returned_date", ""),
                        assign.get("status", ""),
                        assign.get("notes", ""),
                    ])
            messagebox.showinfo("Export complete", f"Books exported to:\n{file_path}")
        except Exception as e:
            print(f"[books] export failed: {e}")
            messagebox.showerror("Export failed",
                "The book list could not be saved to that file.\n\n"
                "Check the folder is writable and try again.")

    def on_import_books_csv(self):
        """Import books (assignments) from CSV with password protection"""
        # Check password first
        if not self._check_admin_password():
            return

        file_path = filedialog.askopenfilename(
            title="Import Books from CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            from csv import reader
            imported_count = 0
            skipped_closed = 0
            errors = []
            
            with open(file_path, "r", encoding="utf-8") as f:
                csv_reader = reader(f)
                header = next(csv_reader, None)
                
                if not header:
                    messagebox.showerror("Import failed", "CSV file is empty")
                    return
                
                for row_num, row in enumerate(csv_reader, start=2):
                    try:
                        if len(row) < 3:
                            errors.append(f"Row {row_num}: Insufficient columns")
                            continue
                        
                        student_id = row[1].strip()
                        item_id = row[2].strip()
                        assigned_date = row[3].strip() if len(row) > 3 else ""
                        returned_date = row[4].strip() if len(row) > 4 else None
                        status = row[5].strip() if len(row) > 5 else "active"
                        notes = row[6].strip() if len(row) > 6 else ""
                        
                        # Validate student and item exist
                        student = models.get_student(student_id)
                        item = models.get_item(item_id)
                        
                        if not student:
                            errors.append(f"Row {row_num}: Student ID {student_id} not found")
                            continue
                        if not item:
                            errors.append(f"Row {row_num}: Item ID {item_id} not found")
                            continue
                        
                        # Only open loans can be recreated. A returned loan is
                        # history the model layer cannot reconstruct, so it is
                        # counted and skipped rather than silently invented.
                        if (status or "").strip().lower() in (
                                "returned", "lost", "damaged"):
                            skipped_closed += 1
                            continue
                        models.assign_item_to_student(
                            item_id=item_id,
                            student_id=student_id,
                            notes=notes or None,
                        )
                        imported_count += 1
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
            
            # Show result
            result_msg = f"Imported {imported_count} loan(s)."
            if skipped_closed:
                result_msg += (
                    f"\n\n{skipped_closed} row(s) skipped: already returned, "
                    "lost or damaged, so there is no loan to open.")
            if errors:
                result_msg += f"\n\n{_plural(len(errors), 'error')} encountered:\n"
                result_msg += "\n".join(errors[:10])  # Show first 10 errors
                if len(errors) > 10:
                    result_msg += f"\n... and {_plural(len(errors) - 10, 'more error')}"
            
            if imported_count > 0:
                self.load_assignments()  # Refresh display
                messagebox.showinfo("Import complete", result_msg)
            else:
                messagebox.showwarning("Import failed", result_msg if errors else "No books imported")
                
        except Exception as e:
            messagebox.showerror("Import failed", f"Could not import books:\n{e}")

    def on_scan_book_assignment(self):
        """Old method - deprecated. Use on_scan_book_for_student instead."""
        pass

    def on_assignments_search(self):
        """Search for a student across all fields (ID, first name, last name, level)."""
        search_term = self.assignments_search_var.get().strip().lower()
        
        if not search_term:
            messagebox.showwarning("Empty", "Please enter a search term")
            return
        
        students = models.list_students()
        matching_students = []
        
        for student in students:
            if not student:  # Skip None entries
                continue
                
            # Check all fields, handling None values
            student_id = (student.get("student_id") or "").lower()
            first_name = (student.get("first_name") or "").lower()
            last_name = (student.get("last_name") or "").lower()
            level = (student.get("level") or "").lower()
            
            # Match if search term is found in any field
            if (search_term == student_id or  # Exact ID match takes priority
                search_term in first_name or
                search_term in last_name or
                search_term in level):
                matching_students.append((student, search_term == student_id))  # Mark exact matches
        
        if not matching_students:
            messagebox.showwarning("Not Found", "No students match your search")
            self.on_clear_student_selection()
            return
        
        # Sort by exact matches first
        matching_students.sort(key=lambda x: x[1], reverse=True)
        matching_students = [s[0] for s in matching_students]
        
        if len(matching_students) > 1:
            # Show selection dialog if multiple matches
            student_options = [f"ID: {s.get('student_id')} | {s.get('first_name')} {s.get('last_name')} | Level: {s.get('level')}".strip() for s in matching_students]
            selection_window = tk.Toplevel(self)
            selection_window.title("Select Student")
            selection_window.geometry("500x300")
            selection_window.transient(self)
            selection_window.grab_set()
            
            ttk.Label(selection_window, text="Multiple students found. Select one:", font=('Arial', 10)).pack(pady=10)
            
            listbox = tk.Listbox(selection_window, font=('Arial', 9))
            listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            for option in student_options:
                listbox.insert(tk.END, option)
            
            def select_student():
                selection = listbox.curselection()
                if selection:
                    selected_student = matching_students[selection[0]]
                    self._select_student_for_assignment(selected_student)
                    selection_window.destroy()
            
            theme.flat_button(selection_window, 'primary', text="Select", bg=COLORS['success'], fg='white', command=select_student).pack(pady=10)
        else:
            # Single match - select automatically
            self._select_student_for_assignment(matching_students[0])

    def _select_student_for_assignment(self, student):
        """Helper to select a student and display their info."""
        student_id = student.get("student_id")
        
        # Store selected student
        self.selected_student_id = student_id
        
        # Display student name
        first_name = student.get("first_name", "")
        last_name = student.get("last_name", "")
        student_name = f"{first_name} {last_name}".strip()
        self.assignment_student_name.config(text=student_name)
        
        # Load and display student photo
        self._load_assignment_student_photo(student_id)
        
        messagebox.showinfo("Found", f"Student '{student_name}' selected. Scan a book to register.")

    def on_clear_student_selection(self):
        """Clear the selected student and all search fields."""
        self.selected_student_id = None
        self.assignments_search_id_var.set("")
        self.assignments_search_first_var.set("")
        self.assignments_search_last_var.set("")
        self.assignments_search_level_var.set("")
        self.assignment_student_name.config(text="")
        self.assignment_student_photo.delete("all")
        self.assignment_student_photo.create_text(125, 125, text="No student selected", fill=COLORS['dark'], font=('Arial', 10))

    def on_scan_student_qr(self):
        """Scan a student QR code to select the student."""
        student_id = simpledialog.askstring(
            "Scan Student QR",
            "Scan the student QR code or enter student ID:"
        )
        
        if not student_id:
            return
        
        student_id = _card_student_id(student_id)        # a card's "S:<ID>" or a typed ID
        
        # Find student by ID
        students = models.list_students()
        selected_student = None
        
        for student in students:
            if student and student.get("student_id") == student_id:
                selected_student = student
                break
        
        if not selected_student:
            messagebox.showerror("Not Found", f"Student ID '{student_id}' not found")
            return
        
        # Select the student
        self._select_student_for_assignment(selected_student)

    def _load_assignment_student_photo(self, student_id: str):
        """Load and display student photo in assignment tab."""
        if self.assignment_student_photo is None:
            return
        
        self.assignment_student_photo.delete("all")
        
        photo_path = None
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            candidate = STUDENT_PHOTOS_DIR / f"{student_id}{ext}"
            if candidate.exists():
                photo_path = candidate
                break
        
        if not photo_path:
            self.assignment_student_photo.create_text(125, 125, text="No photo", fill=COLORS['dark'], font=('Arial', 10))
            return
        
        try:
            img = Image.open(photo_path)
            img.thumbnail((250, 250), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.assignment_student_photo.create_image(125, 125, image=photo)
            self.assignment_student_photo.image = photo
        except Exception as e:
            self.assignment_student_photo.create_text(125, 125, text=f"Error loading photo", fill=COLORS['danger'], font=('Arial', 9))

    def on_scan_book_for_student(self):
        """Scan a book and assign it to the selected student."""
        if not self.selected_student_id:
            messagebox.showwarning("No Student", "Please select a student first")
            return
        
        content = simpledialog.askstring(
            "Scan Book",
            f"Scan book QR for {self.assignment_student_name.cget('text')}:",
            parent=self,
        )
        if not content:
            return
        
        item_id = _card_item_id(content)                 # "I:" or "i:", stray scanner characters cleaned
        if not item_id:
            messagebox.showwarning(
                "Not a book code",
                "That does not look like a book code.\n\n"
                "Scan the label on the book - its code starts with 'I:'.")
            return
        
        self._lend_book(item_id, self.selected_student_id,
                        notes="Scanned checkout")

    # ---------- ATTENDANCE TAB ----------

    def _build_attendance_tab(self, parent):
        """The Attendance page (new look N3, design work\\n3\\N3_DESIGN_FABLE_2026-10-22.md section 2).

        Creation order is how the scanner finds its box: after a side-menu click Tk's ttk::focusFirst gives the
        keyboard focus to the first focusable widget created on this page, so the band (with the scan box) is built
        before the Date box and every other entry, combobox and the tree. Do not create a focusable widget above it."""
        S, F = theme.scale, theme.font
        ground, card_bg = COLORS['light'], COLORS['white']
        ink, muted = COLORS['dark'], theme.colour('ink_muted', "#7f8c8d")

        # Main container
        main_container = tk.Frame(parent, bg=ground)
        main_container.pack(fill=tk.BOTH, expand=True)

        # ===== HEADER BAND: today's date over "Attendance", as high as the panel's title block (no fixed height) =====
        band = tk.Frame(main_container, bg=COLORS['primary'])
        band.pack(side=tk.TOP, fill=tk.X)
        band_left = tk.Frame(band, bg=COLORS['primary'])
        band_left.pack(side=tk.LEFT, padx=(S(22), 0))
        self._att_today_label = tk.Label(band_left, text=date.today().strftime("%A %d %B %Y"), bg=COLORS['primary'],
                                         fg=theme.colour('side_text', 'white'), font=F(9), anchor='w')
        self._att_today_label.pack(side=tk.TOP, anchor='w', pady=(S(14), 0))
        tk.Label(band_left, text="Attendance", bg=COLORS['primary'], fg='white', font=F(14, bold=True),
                 anchor='w').pack(side=tk.TOP, anchor='w', pady=(0, S(12)))
        self._att_band_right = tk.Frame(band, bg=COLORS['primary'])
        self._att_band_right.pack(side=tk.RIGHT, padx=(0, S(20)))
        # The scan box: a card scanned here opens Manual Entry with the card in its ID box (design 2.9)
        tk.Label(self._att_band_right, text="Scan student card", bg=COLORS['primary'], fg='white',
                 font=F(9, bold=True)).pack(side=tk.LEFT, padx=(0, S(6)))
        self.att_scan_var = tk.StringVar()
        self.att_scan_entry = ttk.Entry(self._att_band_right, textvariable=self.att_scan_var, width=16, font=F(9))
        self.att_scan_entry.pack(side=tk.LEFT)
        self.att_scan_entry.bind("<Return>", self.on_attendance_scan_enter)
        # Opens the Roster's own Cancel Class dialog for the class the list shows: light grey (design 2.10)
        self._att_cancel_btn = theme.flat_button(self._att_band_right, 'secondary', text="Cancel a lesson",
                bg='#95a5a6', fg='white', font=F(9, bold=True), padx=S(12), pady=S(5), state=tk.DISABLED,
                disabledforeground=theme.colour('secondary_disabled', '#bdc3c7'),
                command=self.on_attendance_cancel_lesson)
        self._att_cancel_btn.pack(side=tk.LEFT, padx=(S(12), 0))

        # ===== ROW A: the date =====
        row_a = tk.Frame(main_container, bg=ground, padx=S(20))
        row_a.pack(side=tk.TOP, fill=tk.X, pady=(S(10), S(4)))

        self.att_date_var = tk.StringVar(value=date.today().isoformat())

        tk.Label(row_a, text="📅 Date:", bg=ground, fg=ink, font=F(10, bold=True)).pack(side=tk.LEFT, padx=(0, S(8)))

        date_entry = ttk.Entry(row_a, textvariable=self.att_date_var, width=12, font=F(10))
        date_entry.pack(side=tk.LEFT, padx=(0, S(10)))

        # Says which day a mark will go to, and warns when that is not today
        self.att_date_note = tk.Label(row_a, text="", bg=COLORS['primary'], fg='white',
                font=F(9, bold=True), padx=S(8), pady=S(2))
        self.att_date_note.pack(side=tk.LEFT, padx=(0, S(10)))
        self.att_date_var.trace_add("write", lambda *a: self._update_att_date_note())
        self._update_att_date_note()
        # The label must notice midnight: recompute whenever the tab is shown or the window gets the focus
        parent.bind("<Map>", lambda e: self._update_att_date_note(), add="+")
        self.bind("<FocusIn>", lambda e: self._update_att_date_note(), add="+")
        # Changing the Date box reloads the view for that date; a one-minute timer covers midnight
        self.att_date_var.trace_add("write", lambda *a: self._on_att_date_changed())
        if self._att_tick_id is not None:                       # a rebuilt tab must not leave the old timer running
            try:
                self.after_cancel(self._att_tick_id)
            except Exception:
                pass
        self._att_tick_id = self.after(60000, self._att_date_tick)

        # Reload or reselect a view and write nothing: light grey (David's colour rule, 14 Oct)
        btn_today = theme.flat_button(row_a, 'secondary', text=f"📍 {self.t('today')}", bg=COLORS['secondary'], fg='white',
                font=F(9, bold=True), padx=S(12), pady=S(5), command=self.set_att_today)
        btn_today.pack(side=tk.LEFT, padx=S(3))

        btn_refresh = theme.flat_button(row_a, 'secondary', text=f"🔄 {self.t('refresh')}", bg=COLORS['dark'], fg='white',
                font=F(9, bold=True), padx=S(12), pady=S(5), command=self.load_attendance)
        btn_refresh.pack(side=tk.LEFT, padx=S(3))

        btn_load_schedule = theme.flat_button(row_a, 'secondary', text=self.t('load_schedule'), bg='#8e44ad', fg='white',
                font=F(9, bold=True), padx=S(12), pady=S(5), command=self.on_load_schedule_attendance)
        btn_load_schedule.pack(side=tk.LEFT, padx=S(3))

        # ===== ROW B: the class, then the search (on screen again: the fixed band hid it, design 2.13) =====
        row_b = tk.Frame(main_container, bg=ground, padx=S(20))
        row_b.pack(side=tk.TOP, fill=tk.X, pady=(0, S(8)))

        tk.Label(row_b, text="📚 Class:", bg=ground, fg=ink,
                font=F(9, bold=True)).pack(side=tk.LEFT, padx=(0, S(5)))

        self.att_class_filter_var = tk.StringVar(value="All Classes")
        self.att_class_combo = ttk.Combobox(row_b, textvariable=self.att_class_filter_var,
                                            width=20, state="readonly", font=F(9))
        self.att_class_combo.pack(side=tk.LEFT, padx=(0, S(5)))
        self.att_class_combo.bind("<<ComboboxSelected>>", lambda e: self.on_attendance_filter_by_class())

        # Button to refresh class list from schedule
        btn_refresh_classes = theme.flat_button(row_b, 'secondary', text="🔄", bg=COLORS['secondary'], fg='white',
                font=F(8), padx=S(6), pady=S(4), command=self.refresh_attendance_class_list)
        btn_refresh_classes.pack(side=tk.LEFT, padx=S(3))

        tk.Label(row_b, text=f"🔍 {self.t('search')} ({self.t('all_dates')}):", bg=ground, fg=ink,
                font=F(10, bold=True)).pack(side=tk.LEFT, padx=(S(24), S(8)))

        # Search filter dropdown
        tk.Label(row_b, text="By:", bg=ground, fg=ink,
                font=F(9)).pack(side=tk.LEFT, padx=(0, S(5)))

        self.att_search_filter_var = tk.StringVar(value="All Fields")
        filter_combo = ttk.Combobox(row_b, textvariable=self.att_search_filter_var,
                                    values=["All Fields", "Student ID", "Name", "Level"],
                                    width=15, state="readonly", font=F(9))
        filter_combo.pack(side=tk.LEFT, padx=(0, S(15)))
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.on_attendance_search())

        self.att_search_var = tk.StringVar()
        search_entry = tk.Entry(row_b, textvariable=self.att_search_var, width=25, font=F(10))
        search_entry.pack(side=tk.LEFT, padx=(0, S(10)))
        search_entry.bind('<Return>', lambda e: self.on_attendance_search())
        search_entry.bind('<KeyRelease>', lambda e: self.on_attendance_search())

        btn_search = theme.flat_button(row_b, 'secondary', text=self.t('search'), bg=COLORS['secondary'], fg='white',
                font=F(9, bold=True), padx=S(10), pady=S(4), command=self.on_attendance_search)
        btn_search.pack(side=tk.LEFT, padx=S(2))

        # Clears a text box and writes nothing: light grey, not red
        btn_clear = theme.flat_button(row_b, 'secondary', text=self.t('clear'), bg=COLORS['danger'], fg='white',
                font=F(9, bold=True), padx=S(10), pady=S(4), command=self.on_attendance_clear_search)
        btn_clear.pack(side=tk.LEFT, padx=S(2))

        # ===== TODAY'S LESSONS STRIP (ui/attendance_cards.py): the dropdown's classes as cards =====
        self.att_strip = attendance_cards.make_strip(main_container)
        self.att_strip.pack(side=tk.TOP, fill=tk.X)

        # ===== CONTENT CARD: class header, what was saved, the marks bar, the list =====
        content = tk.Frame(main_container, bg=card_bg, highlightthickness=1,
                           highlightbackground=theme.colour('line', '#bdc3c7'), padx=S(14))
        content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=S(15), pady=S(15))

        header_line = tk.Frame(content, bg=card_bg)
        header_line.pack(side=tk.TOP, fill=tk.X, pady=(S(10), 0))     # the card's top pad (gate 0 P0-3)
        self.att_class_header = tk.Label(header_line, text="", bg=card_bg, fg=ink, font=F(12, bold=True), anchor='w')
        self.att_class_header.pack(side=tk.LEFT)
        # The counts; text unchanged (pinned), now at the right of the class header
        self.att_status_label = tk.Label(header_line, text="", bg=card_bg, fg=muted, font=F(9))
        self.att_status_label.pack(side=tk.RIGHT, padx=(S(12), 0))

        # What was just saved: after any mark this says which student, which mark and which date
        self.att_mark_line = tk.Label(content, text="", bg=card_bg, fg=COLORS['primary'],
                font=F(10, bold=True), anchor='w')
        self.att_mark_line.pack(side=tk.TOP, fill=tk.X)

        # The marks bar, packed before the list so the list can never push it out (the B5b-14 rule)
        self.att_bar = tk.Frame(content, bg=card_bg)
        self.att_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(S(8), S(8)))   # the card's bottom pad (gate 0 P0-3)
        # Opens a dialog and writes nothing by itself: light grey
        btn_manual = theme.flat_button(self.att_bar, 'secondary', text=self.t('manual_entry'), bg=COLORS['success'],
                fg='white', font=F(9, bold=True), padx=S(12), pady=S(5), command=self.on_attendance_manual_entry)
        btn_manual.pack(side=tk.RIGHT, padx=(S(6), 0))
        # The two mark buttons write the selected rows at once, as Space does (design 2.8 and 3)
        self.att_btn_present = theme.flat_button(self.att_bar, 'primary', text="Mark Present", bg=COLORS['success'],
                fg='white', font=F(9, bold=True), padx=S(16), pady=S(7), state=tk.DISABLED,
                disabledforeground=theme.colour('primary_disabled', '#bdc3c7'), command=self.on_mark_selected_present)
        self.att_btn_absent = theme.flat_button(self.att_bar, 'warning', text="Mark Absent", bg=COLORS['warning'],
                fg='white', font=F(9, bold=True), padx=S(16), pady=S(7), state=tk.DISABLED,
                disabledforeground=theme.colour('warning_disabled', '#bdc3c7'), command=self.on_mark_selected_absent)
        self.att_btn_present.pack(side=tk.RIGHT, padx=(S(6), 0), before=btn_manual)   # gap to Mark Absent (decision 2)
        self.att_btn_absent.pack(side=tk.RIGHT, padx=(S(6), 0), before=btn_manual)
        # What the buttons will do: how many rows are selected, or why marking is off
        self.att_bar_note = tk.Label(self.att_bar, text="", bg=card_bg, fg=muted, font=F(9), anchor='w')
        self.att_bar_note.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Treeview with enhanced styling. "last_mark" is shown in the search view only.
        columns = ("student_id", "name", "level", "status", "last_mark")
        tree = ttk.Treeview(content, columns=columns, show="headings", selectmode="extended", height=4,
                            style="Attendance.Treeview", displaycolumns=columns[:4])

        # Configure headers with better styling
        headers = [self.t("student_id"), self.t("name"), self.t("level"), self.t("status"), self.t("last_mark")]
        for col, text in zip(columns, headers):
            tree.heading(col, text=text)
            tree.column(col, anchor="w")

        # Measured widths: only the name column stretches, so Tk never cuts Status when the list is narrow
        status_w = theme.measure(tree, headers[3], NOT_MARKED, "present", "absent", pad=28)
        tree.column("student_id", width=theme.measure(tree, headers[0], "0000000000", pad=24), anchor="center",
                    stretch=False)
        tree.column("name", width=S(200), anchor="w", stretch=True)
        tree.column("level", width=theme.measure(tree, headers[2], "SM3", "PRE", pad=24), anchor="center",
                    stretch=False)
        tree.column("status", width=status_w, minwidth=status_w, anchor="center", stretch=False)
        tree.column("last_mark", width=theme.measure(tree, headers[4], "present (2026-10-22)", pad=24),
                    anchor="center", stretch=False)

        # Named style, scoped to this tree so it stops overriding "Treeview" for every other tab in the app
        style = self.style
        style.configure("Attendance.Treeview", rowheight=S(34), font=F(10), background=card_bg,
                        fieldbackground=card_bg, foreground=theme.colour('ink', COLORS['primary']))
        style.configure("Attendance.Treeview.Heading", font=F(10, bold=True), relief="flat",
                        background=theme.colour('panel', COLORS['white']),
                        foreground=theme.colour('primary', COLORS['primary']), padding=S(6))

        # The mark in its colour (text colour, not a button)
        tree.tag_configure("present", background=card_bg, foreground=theme.colour('primary', COLORS['primary']))
        tree.tag_configure("absent", background=card_bg, foreground=theme.colour('danger', COLORS['primary']))
        tree.tag_configure("unmarked", background=card_bg, foreground=muted)

        # Packed before the list, at the right, so a narrow card narrows the list and never hides the scrollbar
        # (gate 2 G2-4 A, David 23 Oct: packed after it, the scrollbar was lost at 1320x760)
        scrollbar = ttk.Scrollbar(content, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.att_tree = tree
        # Bind interactions
        tree.bind("<Double-1>", self.on_attendance_student_selected)
        tree.bind("<Button-3>", self.on_attendance_right_click)
        tree.bind("<space>", self.on_attendance_toggle_status)
        tree.bind("<<TreeviewSelect>>", lambda e: self._att_update_bar())   # the marks bar follows the selection
        
        # Create context menu
        self.att_context_menu = tk.Menu(parent, tearoff=0)
        self.att_context_menu.add_command(label="✓ Mark Present", command=self.on_mark_present)
        self.att_context_menu.add_command(label="✗ Mark Absent", command=self.on_mark_absent)
        self.att_context_menu.add_command(label="🗑 Clear mark", command=self.on_clear_mark)
        self.att_context_menu.add_separator()
        self.att_context_menu.add_command(label="📋 View History", command=self.on_view_history)

    def set_att_today(self):
        if self.att_date_var is not None:
            today_str = date.today().isoformat()
            self.att_date_var.set(today_str)
            self.on_load_schedule_attendance()
            self._update_att_status()

    # ---------- attendance list helpers ----------

    def _att_session_date(self):
        """The date in the Date box; today when it is blank. The views and the export use this one date; a mark uses
        _att_marking_date, which refuses a blank box."""
        return ((self.att_date_var.get() if self.att_date_var else "") or "").strip() or date.today().isoformat()

    def _att_marking_date(self, done="marked"):
        """The Date-box date if it is a real YYYY-MM-DD date; otherwise say so and return None, so nothing is marked or
        cleared under a date that is not a date. A blank box is refused too: after B5b-25 an emptied box can still
        show a past date's rows, and a mark taken as today would go to the wrong day (b5b_fix1)."""
        self._update_att_date_note()
        if not ((self.att_date_var.get() if self.att_date_var else "") or "").strip():
            messagebox.showerror("No date", f"Type a date first — the Date box is empty.\n\nNothing was {done}.")
            return None
        text = self._att_session_date()
        if _parse_att_date(text) is None:
            messagebox.showerror(
                "Invalid Date",
                f"'{text}' is not a valid date. Use YYYY-MM-DD, for example {date.today().isoformat()}.\n\n"
                f"Nothing was {done}.")
            return None
        return text

    def _update_att_date_note(self):
        """The label next to the Date box: which day marks go to, in red when it is not today."""
        note = getattr(self, "att_date_note", None)
        if note is None or self.att_date_var is None:
            return
        today_line = getattr(self, "_att_today_label", None)
        if today_line is not None:                              # the band's date: today, whatever the Date box says
            today_line.config(text=date.today().strftime("%A %d %B %Y"))
        text = (self.att_date_var.get() or "").strip()
        if not text:
            # A mark needs a date since b5b_fix1, so an empty box no longer reads as today here either (5c, David 13 Oct)
            note.config(text="No date: type a date to mark", bg=COLORS['warning'], fg=COLORS['dark'])
            self._att_update_bar()
            return
        day = _parse_att_date(text)
        if day is None:
            note.config(text="Not a valid date (use YYYY-MM-DD)", bg=COLORS['danger'], fg='white')
            self._att_update_bar()
            return
        label = f"Marking for {day.strftime('%a %d %b %Y')}"
        if day == date.today():
            note.config(text=label, bg=COLORS['primary'], fg='white')
        else:
            note.config(text=f"{label} - NOT TODAY", bg=COLORS['danger'], fg='white')
        self._att_update_bar()

    def _att_update_bar(self):
        """The marks bar (N3): both mark buttons on only with a real YYYY-MM-DD date in the Date box and at least one
        row selected; the note says how many rows, or why marking is off. The handlers check again (design 3)."""
        note = getattr(self, "att_bar_note", None)
        if note is None or self.att_tree is None or self.att_date_var is None:
            return
        if not (note.winfo_exists() and self.att_tree.winfo_exists()):    # the page is being rebuilt (View → ไทย)
            return
        text = (self.att_date_var.get() or "").strip()
        n = len(self.att_tree.selection())
        if not text:
            say, on = "No date: marks are off", False
        elif _parse_att_date(text) is None:
            say, on = "Not a valid date: marks are off", False
        elif n == 0:
            say, on = "No student selected", False
        else:
            say, on = ("1 selected · click a row, or use ↑↓ and Space" if n == 1 else f"{n} selected"), True
        note.config(text=say)
        for btn in (self.att_btn_present, self.att_btn_absent):
            btn.config(state=tk.NORMAL if on else tk.DISABLED)

    @staticmethod
    def _att_tag(status):
        s = (status or "").lower()
        return "present" if s == "present" else "absent" if s == "absent" else "unmarked"

    def _att_insert(self, student_id, name, level, status, last_mark=""):
        """One row of the list. status None (no mark) shows as NOT_MARKED. last_mark: text for the search view's
        "Last mark" column."""
        iid = self.att_tree.insert("", tk.END, values=(student_id, name, level, status or NOT_MARKED, last_mark),
                                   tags=(self._att_tag(status),))
        self._att_ids[iid] = str(student_id)

    def _att_clear(self):
        """Start a redraw: empty list, "Last mark" column hidden, and remember which date the rows are drawn for."""
        for row in self.att_tree.get_children():
            self.att_tree.delete(row)
        self._att_ids = {}
        self._att_shown_date = self._att_session_date()
        self._att_show_last_mark(False)

    def _att_show_last_mark(self, visible):
        cols = ("student_id", "name", "level", "status", "last_mark")
        self.att_tree.configure(displaycolumns=cols if visible else cols[:4])
        self._att_last_visible = visible

    def _att_confirm(self, entries, session_date):
        """The line under the header: the last mark that was saved (not the selected row). entries: [(student_id,
        status or None)]."""
        line = getattr(self, "att_mark_line", None)
        if line is None or not entries:
            return
        text = "Last marked: " + "; ".join(
            f"{sid} → {status or 'not marked'} on {session_date}" for sid, status in entries[:3])
        if len(entries) > 3:
            text += f"; +{len(entries) - 3} more"
        not_today = session_date != date.today().isoformat()
        if not_today:
            text += "  (NOT TODAY)"
        line.config(text=text, fg=COLORS['danger'] if not_today else COLORS['success'])

    def _att_add_marked_strangers(self, session_date):
        """Rows for anyone with a mark on this date who is not listed yet (a manual entry, or a day with no
        classes), so the list is the day's scheduled students PLUS everyone marked that day."""
        marks = models.get_marks_for_date(session_date)
        shown = set(self._att_shown_ids())
        strangers = [sid for sid in marks if sid not in shown]
        if not strangers:
            return
        students = {s["student_id"]: s for s in models.list_students()}
        for sid in strangers:
            st = students.get(sid)
            self._att_insert(sid, models.display_name(st) if st else NO_CURRENT_STUDENT,
                             (st or {}).get("level") or "", marks[sid]["status"])

    def _att_ensure_rows(self, student_ids):
        """Make sure each of these students has a row (in any view), showing the Date-box date's mark."""
        shown = set(self._att_shown_ids())
        missing = [s for s in dict.fromkeys(student_ids) if s not in shown]
        if not missing:
            return
        marks = models.get_marks_for_date(self._att_session_date())
        latest = models.get_latest_marks() if self._att_last_visible else {}
        for sid in missing:
            st = models.get_student(sid)
            lm = latest.get(sid)
            self._att_insert(sid, models.display_name(st) if st else NO_CURRENT_STUDENT, (st or {}).get("level") or "",
                             (marks.get(sid) or {}).get("status"),
                             f"{lm['status']} ({lm['session_date']})" if lm else "")
        self._update_att_status()

    def _on_att_date_changed(self, blank_means_today=False):
        """The Date box was edited: once it holds a real date, reload the view for it (half a date is ignored).
        An emptied box is ignored too, so the rows stay while another date is typed; only the minute tick reloads a
        blank box (blank_means_today), and only after midnight."""
        if self._att_reloading or self.att_tree is None or self.att_date_var is None:
            return
        if not blank_means_today and not (self.att_date_var.get() or "").strip():
            self._att_blank_meant_today = self._att_shown_date == date.today().isoformat()
            return
        text = self._att_session_date()
        if _parse_att_date(text) is None or text == self._att_shown_date:
            return
        self._att_reloading = True
        try:
            if self._att_view[0] == "records":
                self.load_attendance()          # membership too: marked plus scheduled students for the new date
            else:
                self._refresh_att_view()
                self.refresh_attendance_class_list(show_message=False)          # the new weekday's classes
                if self._att_view[0] == "class":                                # a remembered class keeps its name
                    cid = self._att_view[1]                                     # only if it still meets that day
                    self.att_class_filter_var.set(
                        next((d for d, c in self._att_class_id_lookup.items() if c == cid), ""))
        finally:
            self._att_reloading = False

    def _att_date_tick(self):
        """Every minute: keep the date label right (NOT TODAY at midnight). A blank box that was emptied while today
        was shown means today, so after midnight it reloads for the new day; a box emptied to type another date is left."""
        try:
            self._update_att_date_note()
            if (self.att_date_var is not None and not (self.att_date_var.get() or "").strip()
                    and self._att_blank_meant_today):
                self._on_att_date_changed(blank_means_today=True)
        finally:                                                # re-armed whatever happened above
            try:
                self._att_tick_id = self.after(60000, self._att_date_tick)
            except tk.TclError:
                pass

    def _att_row_id(self, iid):
        """The student ID of a row, as the string that was stored. (Treeview.item(iid, "values") turns "0042" into
        the number 42, so nothing here reads IDs from item().)"""
        return self._att_ids.get(iid) or str(self.att_tree.set(iid, "student_id"))

    def _att_row_values(self, iid):
        """(student_id, name, level, status) of a row, all strings."""
        return (self._att_row_id(iid),) + tuple(str(self.att_tree.set(iid, c)) for c in ("name", "level", "status"))

    def _att_shown_ids(self):
        return [self._att_row_id(i) for i in self.att_tree.get_children()]

    def _att_selected_ids(self):
        return [self._att_row_id(i) for i in self.att_tree.selection()]

    def _refresh_att_view(self, select=None, ensure=None):
        """Redraw the list the user is looking at after a mark, without pop-ups, so it does not shrink to the marked
        students. select: student IDs to keep selected (default: whatever is selected now). ensure: student IDs that
        must have a row afterwards, whatever the view (the ones just marked)."""
        if self.att_tree is None or self.att_date_var is None:
            return
        self._update_att_date_note()
        keep = list(select) if select else self._att_selected_ids()
        try:                                                    # does the tree have the keyboard now?
            had_focus = self.focus_get() is self.att_tree
        except (KeyError, tk.TclError):
            had_focus = False
        kind = self._att_view[0]
        if kind == "day":
            self.on_load_schedule_attendance(quiet=True)
        elif kind == "class":
            self.on_attendance_filter_by_class(quiet=True, class_id=self._att_view[1])   # the remembered class
        elif kind == "search":
            self.on_attendance_search()
        else:
            self._redraw_records()
        if ensure:
            self._att_ensure_rows(ensure)
        wanted = set(keep)
        items = [i for i in self.att_tree.get_children() if self._att_row_id(i) in wanted]
        if items:
            self.att_tree.selection_set(items)
            self.att_tree.focus(items[0])                       # the focus item too, so Down/Up carry on from here
            self.att_tree.see(items[0])
        elif had_focus and self.att_tree.get_children():
            self.att_tree.focus(self.att_tree.get_children()[0])
        if had_focus:
            self.att_tree.focus_set()                           # the redraw must not take the keyboard away

    def _att_redraw_after_write(self, select, ensure, entries, session_date):
        """After a mark was SAVED: redraw and say what was saved. A redraw that fails must not read as a failed save."""
        try:
            self._refresh_att_view(select=select, ensure=ensure)
            self._update_att_status()
        except Exception as e:
            messagebox.showwarning("Saved", "Saved, but the list could not refresh — press Refresh.\n\n"
                                            f"({e})")
        self._att_confirm(entries, session_date)

    def _redraw_records(self):
        """The default list: the same students as now, plus anyone newly marked, with the date's marks applied."""
        session_date = self._att_session_date()
        shown = self._att_shown_ids()
        students = {s["student_id"]: s for s in models.list_students()}
        marks = {r["student_id"]: r for r in models.get_attendance_for_date(session_date)}
        order = shown + [sid for sid in marks if sid not in shown]
        self._att_clear()
        for sid in order:
            st = students.get(sid)
            if st is not None:
                self._att_insert(sid, models.display_name(st), st.get("level") or "", (marks.get(sid) or {}).get("status"))
        self._update_att_status()

    def on_load_schedule_attendance(self, quiet=False):
        """Load the day's classes and their enrolled students for the selected date.

        Reads the same tables the pipeline uses (class_def + extra_lesson +
        class_cancellations, as in roster_bridge.get_class_for_now), so the
        portal has one version of the schedule. No CSV fallback. The list itself
        comes from models.get_day_roster, which the export uses too.

        quiet=True redraws the same list without the pop-ups (used after a mark).
        """
        if self.att_date_var is None or self.att_tree is None:
            return

        session_date = self._att_session_date()

        session_dt = _parse_att_date(session_date)      # strict YYYY-MM-DD, the same check as everywhere
        if session_dt is None:
            messagebox.showerror(
                "Invalid Date",
                f"'{session_date}' is not a valid date (expected YYYY-MM-DD).")
            return

        day_name = session_dt.strftime('%A')

        try:
            day = models.get_day_roster(session_date)
            classes = day["classes"]

            if not classes:
                # The list follows the date: nothing from another day's roster stays on screen under this date.
                self._att_view = ("day",)
                self._att_clear()
                self._att_add_marked_strangers(session_date)      # anyone marked that date is still listed
                self._update_att_status()
                if not quiet:
                    messagebox.showinfo("No Classes",
                        f"No classes scheduled for {day_name} ({session_date}).\n\n"
                        f"Add or re-activate classes in the Schedule tab.")
                return

            self._att_view = ("day",)
            self._att_clear()
            for st in day["students"]:
                self._att_insert(st['student_id'], models.display_name(st), st.get('level') or '', st.get('status'))
            empty_classes = day["empty_classes"]
            self._att_add_marked_strangers(session_date)
            count = len(self.att_tree.get_children())               # every row shown, marked strangers included
            strangers = count - len(day["students"])

            loaded = len(classes) - len(empty_classes)
            summary = (f"✓ Loaded {count} student(s) from {loaded} of "
                       f"{len(classes)} {day_name} class(es) for {session_date}")
            if strangers:
                summary += f"\n\n{strangers} marked but not scheduled."
            dups = day["duplicates"]
            if dups:
                when = "today" if session_dt == date.today() else f"on {session_date}"
                summary += (f"\n\n{len(dups)} student{' is' if len(dups) == 1 else 's are'} in two classes {when}; "
                            "one mark covers both.")
            if empty_classes:
                summary += ("\n\nNo students enrolled in:\n• "
                            + "\n• ".join(empty_classes))
            if not quiet:
                messagebox.showinfo("Loaded", summary)
            self._update_att_status()

        except Exception as e:
            messagebox.showerror("Error", f"Could not load schedule:\n{e}")

    def _update_att_status(self):
        """Update attendance status label with counts"""
        if self.att_tree is None:
            return
        
        present_count = 0
        absent_count = 0
        unmarked_count = 0
        
        for item in self.att_tree.get_children():
            status = str(self.att_tree.set(item, "status")).lower()
            if status == 'present':
                present_count += 1
            elif status == 'absent':
                absent_count += 1
            else:
                unmarked_count += 1
        
        total = present_count + absent_count + unmarked_count
        if total > 0:
            percentage = (present_count / total) * 100
            self.att_status_label.config(
                text=f"✓ {present_count}/{total} Present ({percentage:.0f}%) · {absent_count} absent · {unmarked_count} not marked")
        else:
            self.att_status_label.config(text="No attendance data")
        # Every view and every write ends here (_att_redraw_after_write calls this last): the strip's counts and its
        # highlight, then the class header, follow the list (N3)
        self._att_refresh_strip()
        self._att_update_class_header()
        self._att_update_bar()

    # ---------- attendance lessons strip and class header (N3) ----------

    def _att_day_cards(self):
        """The Date-box day's lessons as the strip shows them, read the way refresh_attendance_class_list reads the
        dropdown's (the same two reads, in the same order; blank = today, not a date = None). Reads only."""
        text = ((self.att_date_var.get() if self.att_date_var is not None else "") or "").strip()
        day = _parse_att_date(text) if text else date.today()
        if day is None:
            return None
        iso = day.isoformat()
        cards = []

        def counts(class_id):
            roster = models.get_roster_with_attendance(class_id, iso)
            return len(roster), sum(1 for s in roster if (s.get('status') or '').lower() in ('present', 'absent'))

        for c in models.get_classes_for_day_of_week(day.weekday()):
            n, marked = counts(c['class_id'])
            cards.append({"class_id": c['class_id'], "display": f"{c['class_name']} ({c['start_time']})",
                          "name": c['class_name'], "time": f"{c['start_time']}–{c.get('end_time') or ''}",
                          "cancelled": models.is_class_cancelled(c['class_id'], day), "n": n, "marked": marked})
        for el in models.get_extra_lessons_for_date(iso):
            cid = f"extra:{el['id']}"
            n, marked = counts(cid)
            cards.append({"class_id": cid, "display": f"Extra: {el['label']} ({el['start_time']}–{el['end_time']})",
                          "name": f"Extra: {el['label']}", "time": f"{el['start_time']}–{el['end_time']}",
                          "cancelled": False, "n": n, "marked": marked})
        return cards

    def _att_refresh_strip(self):
        """Redraw the lessons strip for the Date-box day; the card of the class the list shows is highlighted.
        Never shows a message box."""
        strip = getattr(self, "att_strip", None)
        if strip is None or self.att_date_var is None:
            return
        self._att_update_cancel_button()
        try:
            cards = self._att_day_cards()
        except Exception:
            cards = []
        if cards is None:
            self._att_cards = []
            attendance_cards.show_message(strip, attendance_cards.NO_DATE)
            return
        self._att_cards = cards
        selected = self._att_view[1] if self._att_view[0] == "class" else None
        attendance_cards.show_cards(strip, cards, selected, self.on_attendance_card_click)

    def _att_update_cancel_button(self):
        """Cancel a lesson: on only while the list shows one weekly class (an extra lesson cannot be cancelled and
        "All Classes" names no lesson); it says "Cancellations…" when that class has some, as the Roster's does."""
        btn = getattr(self, "_att_cancel_btn", None)
        if btn is None or not btn.winfo_exists():
            return
        cid =self._att_view[1] if self._att_view[0] == "class" else None
        weekly = bool(cid) and not str(cid).startswith("extra:")
        upcoming = False
        if weekly:
            try:
                upcoming = bool(models.list_upcoming_cancellations(cid))
            except Exception:
                pass
        btn.config(text="Cancellations\u2026" if upcoming else "Cancel a lesson",
                   state=tk.NORMAL if weekly else tk.DISABLED)

    def on_attendance_cancel_lesson(self):
        """Cancel a lesson (N3): the Roster's own dialog for the class the list shows; when it closes, the strip and
        the list are redrawn. The dialog, its checks and its words are the Roster's (design 2.10)."""
        cid = self._att_view[1] if self._att_view[0] == "class" else None
        roster = getattr(self, "roster_tab", None)
        if not cid or str(cid).startswith("extra:") or roster is None:
            return
        dialog = roster.open_cancel_for(cid)
        if dialog is not None:
            self.wait_window(dialog)
            self._att_refresh_strip()
            self._refresh_att_view()

    def on_attendance_card_click(self, class_id):
        """A card is the dropdown entry of its class: the same lookup, the same method. The selected card clicked
        again is "All Classes"."""
        if self._att_view == ("class", class_id):
            self.att_class_filter_var.set("All Classes")
        else:
            display = next((d for d, c in self._att_class_id_lookup.items() if c == class_id), None)
            if display is None:
                return
            self.att_class_filter_var.set(display)
        self.on_attendance_filter_by_class()

    def _att_update_class_header(self):
        """The line at the top of the list card: which class, or which view, and for which date."""
        header = getattr(self, "att_class_header", None)
        if header is None:
            return
        day = _parse_att_date(self._att_session_date())
        shown = day.strftime('%a %d %b %Y') if day else self._att_session_date()
        kind = self._att_view[0]
        if kind == "class":
            card = next((c for c in self._att_cards if c["class_id"] == self._att_view[1]), None)
            text = f"{card['name']} · {card['time']}" if card else str(self._att_view[1])
        elif kind == "day":
            text = f"All classes · {shown}"
        elif kind == "search":
            text = "Search results"
        else:
            text = f"Attendance records · {shown}"
        header.config(text=text)

    def refresh_attendance_class_list(self, show_message=True):
        """Refresh class dropdown with classes for the selected date from class_def DB table.
        A Date box that is not a real YYYY-MM-DD date (blank means today) shows no classes."""
        text = ((self.att_date_var.get() if self.att_date_var is not None else "") or "").strip()
        selected_date = _parse_att_date(text) if text else date.today()
        if selected_date is None:
            self.att_class_combo['values'] = []
            self.att_class_filter_var.set("")
            self._att_class_id_lookup = {}
            self._att_refresh_strip()                       # the strip follows the dropdown: "No date"
            return

        day_dow = selected_date.weekday()  # Python weekday: 0=Mon, 6=Sun
        day_name = selected_date.strftime('%A')

        classes = models.get_classes_for_day_of_week(day_dow)

        # Also fetch extra lessons for the selected date
        selected_date_str = selected_date.strftime("%Y-%m-%d")
        extra_lessons = models.get_extra_lessons_for_date(selected_date_str)

        if not classes and not extra_lessons:
            if show_message:
                messagebox.showinfo("No Classes", f"No classes found for {day_name} in the database")
            self.att_class_combo['values'] = ["All Classes"]
            self.att_class_filter_var.set("All Classes")
            self._att_class_id_lookup = {}
            self._att_refresh_strip()                       # "No lessons on this day"
            return

        # Build lookup: display text -> class_id
        self._att_class_id_lookup = {}
        display_list = []
        for c in classes:
            display = f"{c['class_name']} ({c['start_time']})"
            display_list.append(display)
            self._att_class_id_lookup[display] = c['class_id']

        for el in extra_lessons:
            display = f"Extra: {el['label']} ({el['start_time']}–{el['end_time']})"
            display_list.append(display)
            self._att_class_id_lookup[display] = f"extra:{el['id']}"

        class_list = ["All Classes"] + display_list
        self.att_class_combo['values'] = class_list
        self.att_class_filter_var.set("All Classes")

        self._att_refresh_strip()                           # the same classes as cards (N3)

        if show_message:
            messagebox.showinfo("Classes Loaded", f"Loaded {len(classes)} classes for {day_name}")

    def on_attendance_filter_by_class(self, quiet=False, class_id=None):
        """Filter attendance view by selected class using class_roster.

        quiet=True is the form used to redraw after a mark; this view has no pop-ups except a real error. A redraw
        passes class_id, the class remembered in _att_view, so the dropdown (which the refresh button resets) is
        not consulted.
        """
        if class_id is None:
            selected = self.att_class_filter_var.get()

            if not selected or selected == "All Classes":
                self.load_attendance()
                return

            # Resolve class_id from the display text
            lookup = getattr(self, '_att_class_id_lookup', {})
            class_id = lookup.get(selected)
            if not class_id:
                self.load_attendance()
                return

        session_date = self._att_session_date()

        try:
            students = models.get_roster_with_attendance(class_id, session_date)
        except Exception as e:
            messagebox.showerror("Error", f"Class filter error: {e}")
            return

        # Clear and repopulate the treeview
        self._att_view = ("class", class_id)
        self._att_clear()

        for s in students:
            self._att_insert(s['student_id'], models.display_name(s), s['level'] or '', s['status'])

        self._update_att_status()

    def on_attendance_toggle_status(self, event):
        """Toggle attendance status with spacebar.

        The new status is decided inside models.toggle_attendance_status from the mark saved in the database for the
        Date-box date, never from the text of a row (which may be from another date, or from before the box was
        edited). No mark: present. Over several rows it stops at the first failure and shows it; then the list is
        redrawn either way.
        """
        selection = self.att_tree.selection()
        if not selection:
            return
        
        session_date = self._att_marking_date()
        if session_date is None:
            return
        chosen = [self._att_row_id(item) for item in selection]
        done = []
        for student_id in chosen:
            try:
                done.append((student_id, models.toggle_attendance_status(student_id, session_date)))
            except Exception as e:
                messagebox.showerror("Could not mark", f"{student_id}: {e}\n\n"
                                                       "Stopped here. The students after it were not changed.")
                break
        
        # Refresh display: the same list, with the marks applied, and say what was saved (the write is already done)
        self._att_redraw_after_write(chosen, [sid for sid, _ in done], done, session_date)

    def on_mark_selected_present(self):
        self._att_mark_selected("present")

    def on_mark_selected_absent(self):
        self._att_mark_selected("absent")

    def _att_mark_selected(self, status):
        """The marks bar (N3): the selected rows get `status` on the Date-box date, one write each, through the
        function the right-click menu and Manual Entry use, behind the gate Space uses. No pop-up on success:
        the "Last marked" line says what was saved, as after Space."""
        selection = self.att_tree.selection()
        if not selection:
            self._att_update_bar()                      # the button should have been disabled; say so and stop
            return
        session_date = self._att_marking_date()         # blank or invalid date -> its error box, None
        if session_date is None:
            return
        chosen = [self._att_row_id(item) for item in selection]
        done = []
        for student_id in chosen:
            try:
                models.set_attendance_status(student_id, session_date, status)   # as on_mark_present / Manual Entry
                done.append((student_id, status))
            except Exception as e:
                messagebox.showerror("Could not mark", f"{student_id}: {e}\n\n"
                                                       "Stopped here. The students after it were not changed.")
                break
        self._att_redraw_after_write(chosen, [sid for sid, _ in done], done, session_date)

    def on_attendance_search(self):
        """Search attendance records across all dates with filter options"""
        if self.att_tree is None:
            return
        
        search_term = self.att_search_var.get().strip().lower()
        search_filter = self.att_search_filter_var.get() if hasattr(self, 'att_search_filter_var') else "All Fields"
        
        # If no search term, reload current date
        if not search_term:
            self.load_attendance()
            self._update_att_status()
            return

        # Clear current display
        self._att_view = ("search",)
        self._att_clear()
        self._att_show_last_mark(True)
        
        # Get ALL students for searching
        students = models.list_students()
        matched_records = []
        
        # Build all student records and search based on filter
        for st in students:
            sid = st["student_id"]
            full_name = models.display_name(st)
            level = st.get("level") or ""
            
            # Apply filter logic
            match = False
            if search_filter == "All Fields":
                match = (search_term in sid.lower() or
                        search_term in full_name.lower() or
                        search_term in level.lower())
            elif search_filter == "Student ID":
                match = search_term in sid.lower()
            elif search_filter == "Name":
                match = search_term in full_name.lower()
            elif search_filter == "Level":
                match = search_term in level.lower()
            
            if match:
                matched_records.append((sid, full_name, level, st))
        
        # Matches: the status column is the mark for the Date-box date (the date a mark will go to), and the
        # "Last mark" column is the student's newest mark, whatever its date.
        if matched_records:
            date_marks = models.get_marks_for_date(self._att_session_date())
            latest = models.get_latest_marks()
            for sid, full_name, level, st in matched_records:
                lm = latest.get(sid)
                self._att_insert(sid, full_name, level, (date_marks.get(sid) or {}).get("status"),
                                 f"{lm['status']} ({lm['session_date']})" if lm else "")
        
        self._update_att_status()
    
    def on_attendance_clear_search(self):
        """Clear search and reload current date attendance"""
        self.att_search_var.set("")
        self.load_attendance()
        self._update_att_status()

    def on_attendance_scan_enter(self, event=None):
        """A card scanned into the Attendance page's scan box (N3). The box is only a door to Manual Entry: the
        text goes into Manual Entry's ID box, which looks the card up as it does today (5c); only its Save saves."""
        text = (self.att_scan_var.get() or "").strip()
        self.att_scan_var.set("")                       # the box is always empty afterwards
        if text:
            self.on_attendance_manual_entry(prefill=text)
        return "break"

    def on_attendance_manual_entry(self, prefill=None):
        """Manual student entry for attendance (in case QR reader fails)"""
        session_date = self._att_marking_date()
        if session_date is None:
            return
        manual_window = tk.Toplevel(self)
        manual_window.title("Manual Attendance Entry")
        manual_window.transient(self)
        manual_window.grab_set()
        manual_window.resizable(True, True)       # no fixed size: sized by its content below (B5a-13)
        
        # Header
        header = tk.Frame(manual_window, bg=COLORS['primary'], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="📝 Manual Attendance Entry", bg=COLORS['primary'], fg='white', 
                font=('Arial', 13, 'bold')).pack(pady=12)
        
        # Content
        content = tk.Frame(manual_window, bg=COLORS['light'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Student ID input
        tk.Label(content, text="Student ID:", bg=COLORS['light'], fg=COLORS['dark'], 
                font=('Arial', 10)).pack(anchor="w", pady=(0, 5))
        student_id_var = tk.StringVar()
        student_id_entry = ttk.Entry(content, textvariable=student_id_var, width=30, font=('Arial', 10))
        student_id_entry.pack(fill=tk.X, pady=(0, 15))
        student_id_entry.focus_set()
        
        # Student name display (read-only)
        tk.Label(content, text="Student Name:", bg=COLORS['light'], fg=COLORS['dark'], 
                font=('Arial', 10)).pack(anchor="w", pady=(0, 5))
        student_name_display = tk.Label(content, text="", bg=COLORS['white'], fg=COLORS['primary'], 
                font=('Arial', 10, 'bold'), relief='solid', borderwidth=1)
        student_name_display.pack(fill=tk.X, pady=(0, 15), ipady=8)
        
        # Date display
        tk.Label(content, text="Date:", bg=COLORS['light'], fg=COLORS['dark'], 
                font=('Arial', 10)).pack(anchor="w", pady=(0, 5))
        date_display = tk.Label(content, text=session_date, bg=COLORS['white'], fg=COLORS['primary'], 
                font=('Arial', 10, 'bold'), relief='solid', borderwidth=1)
        date_display.pack(fill=tk.X, pady=(0, 15), ipady=8)
        
        # Status selection
        tk.Label(content, text="Attendance Status:", bg=COLORS['light'], fg=COLORS['dark'], 
                font=('Arial', 10)).pack(anchor="w", pady=(0, 5))
        
        status_var = tk.StringVar(value="present")
        status_frame = tk.Frame(content, bg=COLORS['light'])
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Radiobutton(status_frame, text="✓ Present", variable=status_var, value="present",
                      bg=COLORS['light'], fg=COLORS['success'], font=('Arial', 10, 'bold'),
                      selectcolor=COLORS['light']).pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(status_frame, text="✗ Absent", variable=status_var, value="absent",
                      bg=COLORS['light'], fg=COLORS['danger'], font=('Arial', 10, 'bold'),
                      selectcolor=COLORS['light']).pack(side=tk.LEFT)
        
        # Notes
        tk.Label(content, text="Notes (optional):", bg=COLORS['light'], fg=COLORS['dark'], 
                font=('Arial', 10)).pack(anchor="w", pady=(0, 5))
        notes_text = tk.Text(content, height=4, width=40, font=('Arial', 9))
        notes_text.pack(fill=tk.BOTH, expand=True, pady=(0, theme.scale(15)))   # four lines; grows when the window does (N3)
        
        def on_student_id_change(*args):
            """Update student name when ID changes"""
            sid = _card_student_id(student_id_var.get())          # a scanned card (S:..., stray end character) too (5c)
            if sid:
                student = models.get_student(sid)
                if student:
                    full_name = models.display_name(student)
                    student_name_display.config(text=full_name, fg=COLORS['success'])
                else:
                    student_name_display.config(text="[Student not found]", fg=COLORS['danger'])
            else:
                student_name_display.config(text="")
        
        student_id_var.trace("w", on_student_id_change)
        if prefill:                                     # a card from the page's scan box: looked up, selected (N3)
            student_id_var.set(prefill)
            student_id_entry.selection_range(0, tk.END)
        
        def save_attendance():
            """Save the manual attendance entry"""
            sid = _card_student_id(student_id_var.get())          # the same ID the lookup above showed; box left as typed
            if not sid:
                messagebox.showwarning("Missing", "Please enter a Student ID")
                return
            
            student = models.get_student(sid)
            if not student:
                messagebox.showerror("Error", f"Student '{sid}' not found in database")
                return
            
            status = status_var.get()
            notes = notes_text.get("1.0", tk.END).strip()
            
            try:
                if notes:
                    models.mark_attendance(
                        student_id=sid,
                        session_date=session_date,
                        status=status,
                        notes=notes
                    )
                else:
                    models.set_attendance_status(sid, session_date, status)      # keeps any stored note
            except Exception as e:
                messagebox.showerror("Error", f"Could not save attendance:\n{e}")
                return

            full_name = models.display_name(student)
            messagebox.showinfo("Success", 
                f"✓ {full_name} marked as {status.upper()} for {session_date}")
            
            # Refresh the attendance tab: the same list, with this mark applied, and say what was saved
            self._att_redraw_after_write([sid], [sid], [(sid, status)], session_date)
            
            # Clear form and keep focus on student ID for next entry
            student_id_var.set("")
            student_name_display.config(text="")
            notes_text.delete("1.0", tk.END)
            status_var.set("present")
            student_id_entry.focus_set()
        
        # Buttons
        button_frame = tk.Frame(content, bg=COLORS['light'])
        button_frame.pack(fill=tk.X)
        
        save_btn = theme.flat_button(button_frame, 'primary', text="💾 Save & Next", bg=COLORS['success'], fg='white',
                           font=('Arial', 10, 'bold'), padx=15, pady=6, command=save_attendance)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = theme.flat_button(button_frame, 'secondary', text="✕ Close", bg=COLORS['danger'], fg='white',
                           font=('Arial', 10, 'bold'), padx=15, pady=6, command=manual_window.destroy)
        close_btn.pack(side=tk.LEFT)
        
        # Enter looks the student up and moves to the Save button; only Save saves (owner decision O10)
        def on_student_id_enter(event=None):
            on_student_id_change()
            save_btn.focus_set()
            return "break"
        student_id_entry.bind("<Return>", on_student_id_enter)

        # Sized by its content, at least the old 500 px wide: it cannot be made smaller than that, so Notes and Save
        # always show, whatever the display scaling (B5a-13)
        manual_window.update_idletasks()
        manual_window.minsize(max(500, manual_window.winfo_reqwidth()), manual_window.winfo_reqheight())

    def on_attendance_right_click(self, event):
        """Show context menu on right-click in attendance tree"""
        iid = self.att_tree.identify_row(event.y)
        if iid:
            self.att_tree.selection_set(iid)
            try:
                self.att_context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.att_context_menu.grab_release()

    def get_selected_attendance_row(self):
        """Get the currently selected student from attendance tree"""
        if not self.att_tree:
            return None
        selection = self.att_tree.selection()
        if not selection:
            return None
        return self._att_row_values(selection[0])

    def on_mark_present(self):
        """Mark selected student as present"""
        values = self.get_selected_attendance_row()
        if not values:
            messagebox.showinfo("No selection", "Please select a student first.")
            return
        
        student_id = values[0]
        student_name = values[1]
        session_date = self._att_marking_date()
        if session_date is None:
            return
        
        try:
            models.set_attendance_status(student_id, session_date, "present")
        except Exception as e:
            messagebox.showerror("Error", f"Could not mark attendance:\n{e}")
            return
        messagebox.showinfo("Success", f"✓ {student_name} marked as PRESENT for {session_date}")
        # Refresh the attendance tab with current date: the same list, with this mark applied
        self.att_date_var.set(session_date)
        self._att_redraw_after_write([str(student_id)], [str(student_id)], [(str(student_id), "present")], session_date)
        # Switch to attendance tab to show refresh
        self.notebook.select(3)

    def on_mark_absent(self):
        """Mark selected student as absent"""
        values = self.get_selected_attendance_row()
        if not values:
            messagebox.showinfo("No selection", "Please select a student first.")
            return
        
        student_id = values[0]
        student_name = values[1]
        session_date = self._att_marking_date()
        if session_date is None:
            return
        
        try:
            models.set_attendance_status(student_id, session_date, "absent")
        except Exception as e:
            messagebox.showerror("Error", f"Could not mark attendance:\n{e}")
            return
        messagebox.showinfo("Success", f"✗ {student_name} marked as ABSENT for {session_date}")
        # Refresh the attendance tab with current date: the same list, with this mark applied
        self.att_date_var.set(session_date)
        self._att_redraw_after_write([str(student_id)], [str(student_id)], [(str(student_id), "absent")], session_date)
        # Switch to attendance tab to show refresh
        self.notebook.select(3)

    def on_clear_mark(self):
        """Delete the selected student's mark for the date shown, after asking."""
        values = self.get_selected_attendance_row()
        if not values:
            messagebox.showinfo("No selection", "Please select a student first.")
            return
        student_id, student_name = values[0], values[1]
        session_date = self._att_marking_date("cleared")
        if session_date is None:
            return
        if not messagebox.askyesno(
                "Clear mark",
                f"Clear the attendance mark for {student_name} ({student_id}) on {session_date}?\n\n"
                "The mark and any note on it are deleted. There is no undo."):
            return
        try:
            cleared = models.clear_attendance(student_id, session_date)
        except Exception as e:
            messagebox.showerror("Error", f"Could not clear the mark:\n{e}")
            try:                                                # redraw anyway: show what is really saved
                self._refresh_att_view(select=[str(student_id)], ensure=[str(student_id)])
            except Exception:
                pass
            return
        if not cleared:
            messagebox.showinfo("Clear mark", "There was no mark to clear.")
            self._att_redraw_after_write([str(student_id)], [str(student_id)], [], session_date)
            self.att_mark_line.config(text=f"Nothing to clear: {student_id} has no mark on {session_date}",
                                      fg=COLORS['primary'])
        else:
            self._att_redraw_after_write([str(student_id)], [str(student_id)], [(str(student_id), None)], session_date)

    def on_view_history(self):
        """View attendance history for selected student"""
        values = self.get_selected_attendance_row()
        if not values:
            messagebox.showinfo("No selection", "Please select a student first.")
            return
        
        student_id = values[0]
        student_name = values[1]
        self.show_attendance_history(student_id, student_name)

    def load_attendance(self):
        """
        Load attendance for the selected date.

        Behaviour with schedules:
            - If there is a schedule CSV in imports\\student atten, the students it lists for
              that date are shown (read-only: nothing is written), as "not marked" until marked.
            - Students who have a mark for that date are shown with it (scheduled or manually added).
            - If there is neither a mark nor a scheduled student for that date, all students
              are shown, not marked.
        """
        if self.att_tree is None or self.att_date_var is None:
            return

        session_date = self.att_date_var.get().strip() or date.today().isoformat()
        self.att_date_var.set(session_date)
        self._att_view = ("records",)

        # 1) Students a schedule CSV lists for this date (if configured). Read-only: no mark is ever inserted.
        scheduled = []
        try:
            from scripts import schedule_import
            scheduled = schedule_import.scheduled_student_ids(session_date)
        except Exception:
            # If the module or CSV isn't there, just ignore quietly.
            pass

        # 2) Clear the tree
        self._att_clear()

        # 3) Fetch data
        students = models.list_students()
        records = models.get_attendance_for_date(session_date)
        record_by_id = {r["student_id"]: r for r in records}

        by_id = {s["student_id"]: s for s in students}
        scheduled = [sid for sid in scheduled if sid in by_id and sid not in record_by_id]
        if records or scheduled:
            # Students with a mark, then scheduled students with none (not marked).
            for rec in records:
                sid = rec["student_id"]
                full_name = models.display_name(rec)
                level = rec.get("level") or ""
                self._att_insert(sid, full_name, level, rec.get("status"))
            for sid in scheduled:
                st = by_id[sid]
                self._att_insert(sid, models.display_name(st), st.get("level") or "", None)
        else:
            # No marks and nobody scheduled → fallback: show all students, not marked
            for st in students:
                sid = st["student_id"]
                full_name = models.display_name(st)
                level = st.get("level") or ""
                self._att_insert(sid, full_name, level, None)
        
        # Update status counts
        self._update_att_status()

        # Auto-populate class dropdown for the selected date
        try:
            self.refresh_attendance_class_list(show_message=False)
        except Exception:
            pass


    def on_attendance_student_selected(self, event=None):
        """Open attendance history window when student is double-clicked"""
        if self.att_tree is None:
            return
        
        selection = self.att_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self._att_row_values(item)
        student_id = values[0]
        student_name = values[1]
        
        self.show_attendance_history(student_id, student_name)
    
    def show_attendance_history(self, student_id: str, student_name: str):
        """Show attendance history for a specific student"""
        # Create a new window
        history_window = tk.Toplevel(self)
        history_window.title(f"Attendance History - {student_name}")
        
        # Header
        header = tk.Frame(history_window, bg=COLORS['primary'], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text=f"📊 Attendance History for {student_name} ({student_id})",
                bg=COLORS['primary'], fg='white', font=('Arial', 13, 'bold')).pack(pady=12)
        
        # Bottom buttons frame, packed before the content so the list can never push Close out of the window (B5b-14)
        button_frame = tk.Frame(history_window, bg=COLORS['light'], height=50)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)
        button_frame.pack_propagate(False)

        theme.flat_button(button_frame, 'secondary', text="✕ Close", bg=COLORS['danger'], fg='white',
                 font=('Arial', 10, 'bold'), padx=25, pady=8, relief='flat', cursor='hand2',
                 command=history_window.destroy).pack(side=tk.RIGHT, padx=5, pady=5)

        # Content frame
        content = tk.Frame(history_window, bg=COLORS['light'])
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Stats frame
        stats_frame = tk.Frame(content, bg=COLORS['white'], relief='solid', borderwidth=1)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        try:
            # Get all attendance records for this student
            all_records = models.get_attendance_for_student(student_id) or []
            
            # Calculate statistics
            total_records = len(all_records)
            present_count = sum(1 for r in all_records if r.get('status') == 'present')
            absent_count = sum(1 for r in all_records if r.get('status') == 'absent')
            
            # Calculate attendance percentage
            attendance_pct = (present_count / total_records * 100) if total_records > 0 else 0
            
            # Display stats
            stats_text = f"Total Sessions: {total_records} | Present: {present_count} | Absent: {absent_count} | Attendance Rate: {attendance_pct:.1f}%"
            tk.Label(stats_frame, text=stats_text, bg=COLORS['white'], fg=COLORS['dark'],
                    font=('Arial', 10, 'bold')).pack(fill=tk.X, padx=15, pady=10)
        except Exception as e:
            tk.Label(stats_frame, text=f"Error loading stats: {e}", bg=COLORS['white'], fg=COLORS['danger']).pack(padx=15, pady=10)
        
        # History treeview frame
        tree_frame = tk.Frame(content, bg=COLORS['white'], relief='solid', borderwidth=1)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview
        columns = ("date", "status", "notes")
        history_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Column headers
        history_tree.heading("date", text="Date")
        history_tree.heading("status", text=self.t("status"))
        history_tree.heading("notes", text="Notes")
        
        history_tree.column("date", width=150)
        history_tree.column("status", width=100)
        history_tree.column("notes", width=350)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=history_tree.yview)
        history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        
        # Populate with records
        try:
            all_records = models.get_attendance_for_student(student_id) or []
            
            for record in all_records:
                date_str = record.get('session_date', 'Unknown')
                status = record.get('status', 'absent').capitalize()
                notes = record.get('notes', '')
                
                # Color code based on status
                tag = 'present' if status.lower() == 'present' else 'absent' if status.lower() == 'absent' else 'neutral'
                history_tree.insert("", tk.END, values=(date_str, status, notes), tags=(tag,))
            
            # Configure tag colors
            history_tree.tag_configure('present', foreground=theme.colour('primary', '#27ae60'))  # Green
            history_tree.tag_configure('absent', foreground=theme.colour('danger', '#e74c3c'))   # Red
            history_tree.tag_configure('neutral', foreground=theme.colour('ink_muted', '#7f8c8d'))  # Gray
            
        except Exception as e:
            history_tree.insert("", tk.END, values=("Error", str(e), ""))
        
        # Sized by its content, never smaller than the old 700x500; extra height goes to the list (B5b-14, b5c_fix1)
        history_window.update_idletasks()
        history_window.minsize(max(700, history_window.winfo_reqwidth()), max(500, history_window.winfo_reqheight()))

    # ---------- ROSTER TAB ----------

    def _build_roster_tab(self, parent):
        """Build roster tab using modular RosterTab class"""
        from ui.roster_tab import RosterTab
        self.roster_tab = RosterTab(parent, self.t, COLORS, models, admin_check=self._check_admin_password)

    # ---------- SCHEDULE TAB ----------

    def _build_schedule_tab(self, parent):
        """Build schedule tab using new modular ScheduleTab class"""
        # Instantiate the new ScheduleTab module
        self.schedule_tab = ScheduleTab(parent, self.t, COLORS, models, on_students_changed=self.load_students)

    # ---------- LESSONS TAB ----------

    def _build_lessons_tab(self, parent):
        from ui.lessons_tab import LessonsTab
        self.lessons_tab = LessonsTab(parent, self)

    # ---------- SYSTEM TAB ----------

    def _build_system_tab(self, parent):
        from ui.system_tab import SystemTab
        self.system_tab = SystemTab(parent, self)

    # ---------- LOGS TAB ----------

    def _build_logs_tab(self, parent):
        # Password protection for dev logs
        self.dev_logs_unlocked = False
        
        # Locked view
        self.dev_logs_locked_frame = ttk.Frame(parent)
        self.dev_logs_locked_frame.pack(fill=tk.BOTH, expand=True)
        
        locked_inner = ttk.Frame(self.dev_logs_locked_frame)
        locked_inner.pack(expand=True)
        
        ttk.Label(locked_inner, text="🔒 Dev Login Tab is Password Protected", font=("Arial", 14, "bold")).pack(pady=20)
        ttk.Label(locked_inner, text="Enter the admin password to view dev logs:").pack(pady=10)
        
        password_var = tk.StringVar()
        password_entry = ttk.Entry(locked_inner, textvariable=password_var, width=25, show="•")
        password_entry.pack(pady=10)
        password_entry.focus()
        
        def unlock_dev_logs():
            try:
                ok = auth.verify("admin", password_var.get())
            except auth.CredentialsError as e:
                messagebox.showerror("Locked", e.user_message)
                password_var.set("")
                return
            if ok:
                self.dev_logs_unlocked = True
                self.dev_logs_locked_frame.pack_forget()
                self.dev_logs_unlocked_frame.pack(fill=tk.BOTH, expand=True)
                self.load_logs()
            else:
                messagebox.showerror("Incorrect", "Wrong password!")
                password_var.set("")
        
        password_entry.bind("<Return>", lambda e: unlock_dev_logs())
        theme.flat_button(locked_inner, 'primary', text=f"🔓 {self.t('unlock')}", bg=COLORS['success'], fg='white', font=('Arial', 9), padx=8, pady=4, command=unlock_dev_logs).pack(pady=10)
        
        # Unlocked view
        self.dev_logs_unlocked_frame = ttk.Frame(parent)
        
        # Main container
        main_container = tk.Frame(self.dev_logs_unlocked_frame, bg=COLORS['light'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Blue toolbar band
        toolbar = tk.Frame(main_container, bg=COLORS['primary'], height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)
        
        # Search and buttons in toolbar
        search_label = tk.Label(toolbar, text=f"{self.t('search')}:", bg=COLORS['primary'], fg='white', font=('Arial', 9))
        search_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.logs_search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.logs_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5, pady=10)
        search_entry.bind("<Return>", lambda e: self.load_logs())

        btn_search = theme.flat_button(toolbar, 'secondary', text=self.t('search'), bg=COLORS['secondary'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.load_logs)
        btn_search.pack(side=tk.LEFT, padx=5, pady=10)

        btn_clear = theme.flat_button(toolbar, 'secondary', text=self.t('clear'), bg=COLORS['danger'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.on_logs_clear)
        btn_clear.pack(side=tk.LEFT, padx=5, pady=10)

        btn_refresh = theme.flat_button(toolbar, 'secondary', text=self.t('refresh'), bg=COLORS['dark'], fg='white', font=('Arial', 9), padx=8, pady=4, command=self.load_logs)
        btn_refresh.pack(side=tk.LEFT, padx=5, pady=10)

        # Treeview in main area
        columns = ("timestamp", "scan_context", "qr_code", "student_name", "item_name")
        tree = ttk.Treeview(main_container, columns=columns, show="headings", selectmode="browse")
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)

        headers = [self.t("timestamp"), self.t("context"), self.t("qr_code"), self.t("student"), self.t("item")]
        for col, text in zip(columns, headers):
            tree.heading(col, text=text)

        tree.column("timestamp", width=180)
        tree.column("scan_context", width=120)
        tree.column("qr_code", width=120)
        tree.column("student_name", width=150)
        tree.column("item_name", width=180)

        scrollbar = ttk.Scrollbar(self.dev_logs_unlocked_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=10)

        self.logs_tree = tree

    def load_logs(self):
        """Load QR scan logs, optionally filtered by search term."""
        if not hasattr(self, "logs_tree"):
            return
        for row in self.logs_tree.get_children():
            self.logs_tree.delete(row)

        term = self.logs_search_var.get().strip()
        if term:
            scans = models.search_qr_scans(term)
        else:
            scans = models.list_qr_scans()

        for scan in scans:
            student_name = ""
            if scan.get("student_first_name") or scan.get("student_last_name"):
                student_name = models.display_name(scan, "student_first_name", "student_last_name")
            
            item_name = scan.get("item_name") or ""
            
            self.logs_tree.insert(
                "",
                tk.END,
                values=(
                    scan.get("timestamp") or "",
                    scan.get("scan_context") or "",
                    scan.get("qr_code") or "",
                    student_name,
                    item_name,
                ),
            )

    def on_logs_clear(self):
        """Clear the search filter and reload all logs."""
        self.logs_search_var.set("")
        self.load_logs()

    # ---------- FILE & DATA MENU ACTIONS ----------

    def on_logout(self):
        """Logout and return to login screen."""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.logged_out = True              # app.py shows the login window again (B5b-4)
            self.destroy()

    def on_backup_now(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_root = DATA_DIR / "backups"
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_dir = backup_root / f"backup_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)

            if DB_PATH.exists():
                copy2(DB_PATH, backup_dir / "inventory.db")

            models.export_items_to_csv(str(backup_dir / "items.csv"))
            models.export_students_to_csv(str(backup_dir / "students.csv"), include_line_id=False)   # D1: the .db copy has them
            models.export_assignments_to_csv(str(backup_dir / "assignments.csv"))
            today_str = date.today().isoformat()
            models.export_attendance_to_csv(today_str, str(backup_dir / f"attendance_{today_str}.csv"))

            messagebox.showinfo("Backup complete", f"Backup saved to:\n{backup_dir}")
        except Exception as e:
            messagebox.showerror("Backup failed", f"Could not complete backup:\n{e}")

    def on_exit(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.destroy()

    def open_tutorials(self):
        """Open the tutorial selector dialog"""
        print("open_tutorials called")  # DEBUG
        if hasattr(self, 'tutorial_manager'):
            print("Tutorial manager exists, showing selector")  # DEBUG
            try:
                self._show_simple_tutorial_selector()
            except Exception as e:
                print(f"ERROR: {e}")
                messagebox.showerror("Error", f"Failed to show tutorials: {e}")
        else:
            print("Tutorial manager NOT found")  # DEBUG
            messagebox.showinfo("Tutorials", "Tutorial system is not available.")
    
    def _show_simple_tutorial_selector(self):
        """Show simple tutorial selection dialog"""
        print("Creating tutorial selector dialog")  # DEBUG
        
        try:
            dialog = tk.Toplevel(self)
            dialog.title("📚 Interactive Tutorials")
            dialog.transient(self)
            
            # Header
            header = tk.Frame(dialog, bg=theme.colour('side', '#3498db'), height=60)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            
            tk.Label(header, text="📚 Learn How to Use NestMind Portal", 
                    bg=theme.colour('side', '#3498db'), fg='white', font=('Arial', 16, 'bold')).pack(pady=15)
            
            # Content frame with scrollbar
            main_content = tk.Frame(dialog, bg=COLORS['white'])
            main_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Create canvas and scrollbar
            canvas = tk.Canvas(main_content, bg=COLORS['white'], highlightthickness=0)
            scrollbar = tk.Scrollbar(main_content, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=COLORS['white'])
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            tk.Label(scrollable_frame, text="Choose a tutorial to get started:", 
                    bg=COLORS['white'], font=('Arial', 11), anchor='w').pack(fill=tk.X, pady=(0, 10))
            
            # Tutorial list
            print("Getting tutorial list...")  # DEBUG
            tutorials = self.tutorial_manager.get_tutorial_list()
            print(f"Found {len(tutorials)} tutorials")  # DEBUG
            
            for tutorial in tutorials:
                print(f"Adding tutorial: {tutorial.name}")  # DEBUG
                btn_frame = tk.Frame(scrollable_frame, bg=COLORS['white'])
                btn_frame.pack(fill=tk.X, pady=5)
                
                is_completed = self.tutorial_manager.is_tutorial_completed(tutorial.tutorial_id)
                
                btn = theme.flat_button(btn_frame, 'primary' if not is_completed else 'secondary', 
                              text=f"{tutorial.icon} {tutorial.name}",
                              bg='#27ae60' if not is_completed else '#95a5a6',
                              fg='white',
                              font=('Arial', 11, 'bold'),
                              width=30,
                              anchor='w',
                              padx=15,
                              pady=10,
                              command=lambda tid=tutorial.tutorial_id: self._start_tutorial(tid, dialog))
                btn.pack(side=tk.LEFT)
                
                if is_completed:
                    tk.Label(btn_frame, text="✓ Completed", 
                            bg=COLORS['white'], fg=theme.colour('primary', '#27ae60'), font=('Arial', 9)).pack(side=tk.LEFT, padx=10)
                
                tk.Label(scrollable_frame, text=tutorial.description, 
                        bg=COLORS['white'], fg=theme.colour('ink_muted', '#7f8c8d'), font=('Arial', 9),
                        wraplength=500, justify='left').pack(fill=tk.X, padx=20, pady=(0, 10))
            
            # Close button
            theme.flat_button(dialog, 'secondary', text="Close", bg='#e74c3c', fg='white',
                     font=('Arial', 10, 'bold'), padx=20, pady=8,
                     command=dialog.destroy).pack(pady=15)
            
            # NOW center it relative to main window after everything is created
            dialog.update_idletasks()
            
            # Sized by its content, never smaller than the old 600x450: Close always shows, whatever the display scaling
            # (5c, David 13 Oct; the fixed 600x450 cut it short at 150%)
            window_width = max(600, dialog.winfo_reqwidth())
            window_height = max(450, dialog.winfo_reqheight())
            dialog.minsize(window_width, window_height)
            
            # Get main window position
            main_x = self.winfo_rootx()
            main_y = self.winfo_rooty()
            main_width = self.winfo_width()
            main_height = self.winfo_height()
            
            # Center dialog on main window
            x = main_x + (main_width - window_width) // 2
            y = main_y + (main_height - window_height) // 2
            
            # Make sure it's on screen
            if x < 0:
                x = 50
            if y < 0:
                y = 50
            
            dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
            dialog.deiconify()  # Make sure it's visible
            dialog.lift()  # Bring to front
            dialog.focus_force()  # Give it focus
            dialog.grab_set()
            
            print("Tutorial selector created successfully")  # DEBUG
            
        except Exception as e:
            import traceback
            print(f"ERROR in _show_simple_tutorial_selector: {e}")
            print(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to show tutorials:\n{e}")
    
    def _start_tutorial(self, tutorial_id, dialog):
        """Start a tutorial"""
        dialog.destroy()
        self.tutorial_manager.start_tutorial(tutorial_id)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """NestMind Portal - School Inventory Management System
        
Version: 2.0
Developed for: Siri English School

Features:
• Student Management
• Book/Item Checkout System
• QR Code Generation & Scanning
• Attendance Tracking
• Schedule Management
• Admin Logging

For help, use the Interactive Tutorials from the Help menu!"""
        
        messagebox.showinfo("About NestMind Portal", about_text)

    def on_import_csv(self):
        """Launch CSV importer window - requires password authentication"""
        # Check password first
        if not self._check_admin_password():
            return
        
        try:
            import sys
            import os
            
            # Import CSV importer from scripts folder
            from scripts.csv_importer_gui import CSVImporterGUI
            
            # Create import window (self IS the root, it inherits from tk.Tk)
            import_window = tk.Toplevel(self)
            import_window.title("Import Student Data from CSV")
            import_window.geometry("1000x700")
            
            # Ensure the window is properly initialized
            import_window.update_idletasks()
            
            # Import the CSV importer GUI - pass the models and callback
            importer = CSVImporterGUI(import_window, models, self.on_import_complete)
            
            # Focus on import window
            import_window.transient(self)
            import_window.grab_set()
            self.wait_window(import_window)
            
        except ImportError as e:
            messagebox.showerror("Import Error", f"Could not load CSV importer: {e}")
        except Exception as e:
            import traceback
            messagebox.showerror("Error", f"Failed to open CSV importer:\n{str(e)}\n\n{traceback.format_exc()}")
    
    def _log_password_attempt(self, success: bool, context: str = "unknown"):
        """Log password attempts to admin logs"""
        try:
            action = "Password Check - SUCCESS" if success else "Password Check - FAILED"
            models.log_admin_action(
                action=action,
                entity_type="authentication",
                entity_id="system",
                details=f"Context: {context}",
                status="success" if success else "failed"
            )
        except Exception:
            pass  # Silently fail - don't interrupt user workflow
    
    def _check_admin_password(self):
        """Ask for the admin password. True only if it is right; Cancel, Escape or a locked portal give False."""
        while True:
            pwd_window = tk.Toplevel(self)
            pwd_window.title("Password Required")
            pwd_window.geometry("450x220")
            pwd_window.resizable(False, False)
            pwd_window.grab_set()
            pwd_window.transient(self)
            
            # Position at mouse cursor
            pwd_window.update_idletasks()
            mouse_x = pwd_window.winfo_pointerx()
            mouse_y = pwd_window.winfo_pointery()
            pwd_window.geometry(f"+{mouse_x-225}+{mouse_y-110}")
            
            tk.Label(pwd_window, text="Enter admin password:", 
                    font=('Arial', 10, 'bold')).pack(pady=15)
            
            pwd_var = tk.StringVar()
            pwd_entry = ttk.Entry(pwd_window, textvariable=pwd_var, show="*", width=40)
            pwd_entry.pack(pady=5, padx=20, fill=tk.X)
            pwd_entry.focus()
            
            result = [None]
            
            def cancel():
                result[0] = None
                pwd_window.destroy()
            
            # Bind Escape key to cancel
            pwd_window.bind("<Escape>", lambda e: cancel())
            
            def check():
                password = pwd_var.get()
                if not password:
                    messagebox.showwarning("Empty", "Password cannot be empty!", parent=pwd_window)
                    return
                try:
                    if not auth.verify("admin", password):
                        self._log_password_attempt(False, "export_or_delete")
                        messagebox.showerror("Error", "Incorrect password!", parent=pwd_window)
                        pwd_entry.delete(0, tk.END)
                        pwd_entry.focus()
                        result[0] = False
                        return
                except auth.CredentialsError as e:
                    messagebox.showerror("Locked", e.user_message, parent=pwd_window)
                    result[0] = None
                    pwd_window.destroy()
                    return
                self._log_password_attempt(True, "export_or_delete")
                result[0] = True
                pwd_window.destroy()
            
            btn_frame = tk.Frame(pwd_window)
            btn_frame.pack(pady=15)
            ok_btn = theme.flat_button(btn_frame, 'primary', text="OK", bg=COLORS['success'], fg='white',
                     command=check, width=12, font=('Arial', 9, 'bold'))
            ok_btn.pack(side=tk.LEFT, padx=5)
            theme.flat_button(btn_frame, 'secondary', text="Cancel", bg=COLORS['danger'], fg='white',
                     command=cancel, width=12, font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
            
            pwd_entry.bind("<Return>", lambda e: check())
            pwd_window.wait_window()
            if result[0] is None:
                return False
            if result[0] is True:
                return True
    
    def on_import_complete(self):
        """Callback after CSV import completes"""
        self.load_students()
        self.notebook.select(0)  # Switch to Students tab to show new data

    def on_export_items_csv(self):
        """Export items CSV - requires admin authentication"""
        if not self._check_admin_password():
            return
        try:
            path = models.export_items_to_csv()
            messagebox.showinfo("Export complete", f"Items exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", f"Could not export items:\n{e}")

    def on_export_students_csv(self):
        """Export students CSV - requires admin authentication"""
        if not self._check_admin_password():
            return
        try:
            path = models.export_students_to_csv()
            messagebox.showinfo("Export complete", f"Students exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", f"Could not export students:\n{e}")

    def on_export_assignments_csv(self):
        """Export assignments CSV - requires admin authentication"""
        if not self._check_admin_password():
            return
        try:
            path = models.export_assignments_to_csv()
            messagebox.showinfo("Export complete", f"Assignments exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", f"Could not export assignments:\n{e}")

    def on_export_today_attendance_csv(self):
        """Export the attendance for the date in the Date box (IDs only) - requires admin authentication"""
        if not self._check_admin_password():
            return
        try:
            session_date = self._att_session_date()
            path = models.export_attendance_to_csv(session_date)
            messagebox.showinfo("Export complete", f"Attendance for {session_date} exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", f"Could not export attendance:\n{e}")

    # ---------- BULK QR GENERATION ----------

    def on_bulk_qr_items(self):
        try:
            items = models.list_items()
            count = 0
            for item in items:
                item_id = item.get("item_id")
                if not item_id:
                    continue
                qr_utils.generate_item_qr(item_id)
                count += 1
            messagebox.showinfo("QR Generation", f"Generated QR codes for {count} items.")
        except Exception as e:
            messagebox.showerror("QR Error", f"Could not generate item QR codes:\n{e}")

    def on_bulk_qr_students(self):
        try:
            students = models.list_students()
            count = 0
            for st in students:
                sid = st.get("student_id")
                if not sid:
                    continue
                qr_utils.generate_student_qr(sid)
                count += 1
            messagebox.showinfo("QR Generation", f"Generated QR codes for {count} students.")
            
            # Refresh the current student QR display if one is selected
            sid = self.get_selected_student_id()
            if sid:
                self._load_student_qr(sid)
        except Exception as e:
            messagebox.showerror("QR Error", f"Could not generate student QR codes:\n{e}")

    # ---------- STUDENT PHOTO SUPPORT ----------

    def on_set_student_photo(self):
        sid = self._one_selected_student_id("set a photo for")
        if not sid:
            return

        file_path = filedialog.askopenfilename(
            title="Select student photo",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            src = Path(file_path)
            ext = src.suffix.lower() or ".jpg"
            dest = STUDENT_PHOTOS_DIR / f"{sid}{ext}"
            copy2(src, dest)
            self._load_student_photo(sid)
            messagebox.showinfo("Photo saved", f"Photo saved for student '{sid}' at:\n{dest}")
        except Exception as e:
            messagebox.showerror("Photo error", f"Could not save photo:\n{e}")
