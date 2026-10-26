"""
ui/lessons_tab.py — Lesson Day Browser tab for the school portal.

Spec: D:/LESSON_DAY_BROWSER_SPEC.md

Safety rules (non-negotiable):
  - Every jobs.db query runs in a daemon thread.
  - All UI updates from threads use self.after(0, callback).
  - No polling, no auto-refresh, no self.after(interval, ...).
  - Queries fire only on user action. Selecting this tab and the
    Refresh button both count as user actions; neither is a timer.
  - Read-only connection: file:...?mode=ro
  - 2-second busy timeout, then graceful error message.
  - Does NOT import pc_ingest_connection or pipeline_launcher.
"""
import sqlite3
import subprocess
import threading
import webbrowser
from datetime import date, timedelta, datetime
import tkinter as tk
from tkinter import ttk

from inventory import db as _inventory_db
from inventory import runmode

JOBS_DB = r"D:\zone_b\jobs.db"

# ── SQL ───────────────────────────────────────────────────────────────────────

_DAY_QUERY = """
SELECT
    ls.session_id,
    ls.class_id,
    ls.started_at,
    ls.stopped_at,
    ls.is_active,
    ls.processing_state,
    COUNT(DISTINCT ac.clip_id)                                                        AS chunk_count,
    SUM(CASE WHEN j.job_type = 'transcribe' AND j.status = 'done' THEN 1 ELSE 0 END) AS transcribed_count,
    SUM(CASE WHEN j.job_type IN ('summarize','diarize') AND j.status = 'done'
             THEN 1 ELSE 0 END)                                                       AS other_done,
    SUM(CASE WHEN j.status = 'error' THEN 1 ELSE 0 END)                              AS error_count
FROM lesson_session ls
LEFT JOIN audio_clip ac
    ON ac.session_id = ls.session_id
LEFT JOIN job j ON j.clip_id = ac.clip_id
WHERE date(ls.started_at, '+7 hours') = ?
GROUP BY ls.session_id
ORDER BY ls.started_at ASC
"""

_EXTRACTION_PRESENCE_QUERY = """
SELECT COUNT(*) AS cnt FROM lesson_extractions WHERE session_id = ?
"""

_MESSAGES_QUERY = """
SELECT
    COUNT(*)                                                  AS total_messages,
    SUM(CASE WHEN status = 'draft'      THEN 1 ELSE 0 END)   AS draft,
    SUM(CASE WHEN status = 'approved'   THEN 1 ELSE 0 END)   AS approved,
    SUM(CASE WHEN status = 'no_line_id' THEN 1 ELSE 0 END)   AS no_line
FROM parent_messages
WHERE session_id = ?
"""

_EXTRACTION_DETAIL_QUERY = """
SELECT extraction_id, topic, grammar, vocabulary, skills, homework, summary, created_at
FROM lesson_extractions
WHERE session_id = ?
"""

# ── DB helper ─────────────────────────────────────────────────────────────────

def _query(sql, params=(), timeout_ms=2000):
    """Read-only query against jobs.db. Returns list of dicts. Raises on error/timeout."""
    conn = sqlite3.connect(
        f"file:{JOBS_DB}?mode=ro", uri=True, timeout=timeout_ms / 1000
    )
    conn.execute(f"PRAGMA busy_timeout = {timeout_ms}")
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

# ── Pure helpers ──────────────────────────────────────────────────────────────

def _bangkok_today():
    return (datetime.utcnow() + timedelta(hours=7)).date()


def _format_date_header(d):
    return d.strftime("%A %d %b %Y")


_SCHOOL_DB = str(_inventory_db.DB_PATH)

def _format_class(class_id):
    if not class_id:
        return "Unassigned Class"
    if class_id.startswith("extra:"):
        extra_id = class_id.split(":")[1]
        try:
            conn = sqlite3.connect(f"file:{_SCHOOL_DB}?mode=ro", uri=True, timeout=1)
            row = conn.execute(
                "SELECT label, start_time, end_time FROM extra_lesson WHERE id = ?",
                (extra_id,)
            ).fetchone()
            conn.close()
            if row:
                return f"{row[0]} ({row[1]}–{row[2]})"
        except Exception:
            pass
        return f"Extra Lesson #{extra_id}"
    parts = class_id.split('_')
    if len(parts) >= 3:
        label = '_'.join(parts[2:]).upper()
        t = parts[1]
        return f"{label} ({t[:2]}:{t[2:]})"
    return class_id


def _compute_status(session, has_extraction, msg_counts):
    """Return (overall_str, steps) where steps = list of (name, ok, detail_str_or_None)."""
    steps = []
    n     = session.get('chunk_count') or 0
    trans = session.get('transcribed_count') or 0
    err   = session.get('error_count') or 0

    steps.append(('Audio', n > 0, f"{n} chunks"))

    all_trans = (trans == n and n > 0)
    steps.append(('Transcribed', all_trans, f"{trans}/{n}"))

    steps.append(('Summary', has_extraction, None))

    steps.append(('Extraction', has_extraction, None))

    total = (msg_counts or {}).get('total_messages') or 0
    has_msgs = total > 0
    msg_detail = None
    if has_msgs:
        mc = msg_counts
        parts = []
        if mc.get('draft'):    parts.append(f"{mc['draft']} draft")
        if mc.get('approved'): parts.append(f"{mc['approved']} approved")
        if mc.get('no_line'):  parts.append(f"{mc['no_line']} no LINE ID")
        msg_detail = ', '.join(parts)
    steps.append(('Messages', has_msgs, msg_detail))

    # Core pipeline is complete when audio, transcription, and extraction are done.
    # Messages are optional (depend on roster/LINE setup).
    core_done = (n > 0 and all_trans and has_extraction)
    if session.get('is_active'):
        # A lesson in progress is neither COMPLETE nor STALLED.
        overall = 'LIVE'
    elif core_done:
        overall = 'COMPLETE'
    elif err > 0:
        overall = 'ERROR'
    elif all_trans and not has_extraction:
        overall = 'STALLED'
    else:
        overall = 'PENDING'

    return overall, steps


_ICON = {'COMPLETE': '✅', 'PENDING': '⏳', 'STALLED': '❌',
         'ERROR': '⚠️', 'LIVE': '🔴'}


def _step_icon(name, ok, msg_counts):
    """Choose ✅ / ⚠️ / ❌ for a pipeline step."""
    if ok:
        # Messages that exist but are all no_line_id → warn instead of tick
        if (name == 'Messages' and msg_counts
                and msg_counts.get('no_line', 0) == msg_counts.get('total_messages', 0)):
            return '⚠️'
        return '✅'
    return '❌'


# ── Tab class ─────────────────────────────────────────────────────────────────

class LessonsTab(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)
        self._app          = app
        self._current_date = _bangkok_today()
        self._cards        = {}   # session_id → (LabelFrame, session_dict)
        self._expanded     = set()

        if runmode.TEST_MODE:
            # Test mode: this tab reads the live jobs.db and can start a live re-extraction.
            ttk.Label(self, text=f"Disabled in {runmode.MODE_NAME}: Zone B is not connected",
                      font=("TkDefaultFont", 12, "bold")).pack(fill=tk.BOTH, expand=True, pady=40)
            return

        self._build_nav()
        self._build_scroll()
        self._load_day(self._current_date.isoformat())

    # ── Navigation bar ────────────────────────────────────────────────────────

    def _build_nav(self):
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=8, pady=(6, 2))

        ttk.Button(bar, text="◀ Prev",  command=self._go_prev ).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Next ▶",  command=self._go_next ).pack(side=tk.LEFT, padx=2)

        self._lbl_date = ttk.Label(bar, font=("TkDefaultFont", 11, "bold"))
        self._lbl_date.pack(side=tk.LEFT, padx=12)
        self._refresh_date_label()

        ttk.Button(bar, text="Today", command=self._go_today).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="📅",    command=self._pick_date).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="⟳ Refresh",
                   command=self.refresh).pack(side=tk.LEFT, padx=(12, 2))

    def _refresh_date_label(self):
        self._lbl_date.config(text=_format_date_header(self._current_date))

    def _go_prev(self):
        self._current_date -= timedelta(days=1)
        self._refresh_date_label()
        self._load_day(self._current_date.isoformat())

    def _go_next(self):
        self._current_date += timedelta(days=1)
        self._refresh_date_label()
        self._load_day(self._current_date.isoformat())

    def _go_today(self):
        self._current_date = _bangkok_today()
        self._refresh_date_label()
        self._load_day(self._current_date.isoformat())

    def refresh(self):
        """Reload the day currently shown. Safe to call from the notebook."""
        self._load_day(self._current_date.isoformat())

    # Called by MainWindow when this tab is selected.
    on_tab_selected = refresh

    def _pick_date(self):
        dlg = _DatePickerDialog(self, self._current_date)
        self.wait_window(dlg)
        if dlg.result:
            self._current_date = dlg.result
            self._refresh_date_label()
            self._load_day(self._current_date.isoformat())

    # ── Scroll canvas ─────────────────────────────────────────────────────────

    def _build_scroll(self):
        outer = ttk.Frame(self)
        outer.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)

        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._inner = ttk.Frame(self._canvas)
        self._win   = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfig(self._win, width=e.width)
        )
        self._canvas.bind(
            "<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        )

    # ── Loading / error states ────────────────────────────────────────────────

    def _clear(self):
        for w in self._inner.winfo_children():
            w.destroy()
        self._cards.clear()
        self._expanded.clear()

    def _show_loading(self):
        self._clear()
        ttk.Label(self._inner, text="Loading…", foreground="gray").pack(pady=20)

    def _show_error(self, msg):
        self._clear()
        lo = msg.lower()
        if "unable to open" in lo or "no such file" in lo:
            text = r"Zone B database not found at D:\zone_b\jobs.db"
        elif "locked" in lo or "busy" in lo:
            text = "Zone B database is busy — try again in a moment"
        else:
            text = f"Error: {msg}"
        ttk.Label(self._inner, text=text, foreground="#b71c1c").pack(pady=20)

    # ── Day load ──────────────────────────────────────────────────────────────

    def _load_day(self, date_str):
        if runmode.TEST_MODE:
            return
        self._show_loading()

        def _fetch():
            try:
                sessions = _query(_DAY_QUERY, (date_str,))
                for s in sessions:
                    sid = s['session_id']
                    presence = _query(_EXTRACTION_PRESENCE_QUERY, (sid,))
                    s['_has_extraction'] = bool(presence and presence[0].get('cnt'))
                    msg_rows = _query(_MESSAGES_QUERY, (sid,))
                    s['_msg_counts'] = msg_rows[0] if msg_rows else None
                self.after(0, lambda: self._render_day(sessions))
            except Exception as exc:
                err = str(exc)
                self.after(0, lambda: self._show_error(err))

        threading.Thread(target=_fetch, daemon=True).start()

    # ── Day render ────────────────────────────────────────────────────────────

    def _render_day(self, sessions):
        self._clear()
        if not sessions:
            ttk.Label(
                self._inner,
                text=f"No lessons recorded for {_format_date_header(self._current_date)}",
                foreground="gray"
            ).pack(pady=20)
            return

        for s in sessions:
            self._build_card(s)

        ttk.Label(
            self._inner,
            text="── No other lessons recorded for this day ──",
            foreground="gray"
        ).pack(pady=(8, 4))

    # ── Card builder ──────────────────────────────────────────────────────────

    def _build_card(self, session):
        sid         = session['session_id']
        has_ext     = session['_has_extraction']
        msg_counts  = session['_msg_counts']
        overall, steps = _compute_status(session, has_ext, msg_counts)
        class_label = _format_class(session['class_id'])

        card = ttk.LabelFrame(
            self._inner,
            text=f"  {class_label}  —  {_ICON[overall]} {overall}  "
        )
        card.pack(fill=tk.X, padx=4, pady=4)
        self._cards[sid] = (card, session)

        # Pipeline step rows
        for name, ok, detail in steps:
            row = ttk.Frame(card)
            row.pack(fill=tk.X, padx=10, pady=1)
            icon = _step_icon(name, ok, msg_counts)
            text = f"{icon}  {name}"
            if detail:
                text += f": {detail}"
            ttk.Label(row, text=text).pack(side=tk.LEFT)

        # Detail area — populated lazily on expand click
        card._detail_frame = ttk.Frame(card)
        card._detail_frame.pack(fill=tk.X, padx=10, pady=(2, 0))

        # Button bar
        btn_bar = ttk.Frame(card)
        btn_bar.pack(anchor="w", padx=10, pady=(4, 8))

        expand_btn = ttk.Button(
            btn_bar, text="▶ Details",
            command=lambda s=session, c=card: self._on_expand(s, c)
        )
        expand_btn.pack(side=tk.LEFT, padx=(0, 4))
        card._expand_btn = expand_btn

        if overall == 'STALLED':
            gen_btn = ttk.Button(btn_bar, text="Generate Summary")
            gen_btn.configure(command=lambda: self._generate_summary(sid, gen_btn))
            gen_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_bar, text="Open in Portal ↗",
            command=lambda: webbrowser.open(f"http://localhost:5555/lesson/{sid}")
        ).pack(side=tk.LEFT, padx=2)

    # ── Expand / detail load ──────────────────────────────────────────────────

    def _on_expand(self, session, card):
        sid = session['session_id']
        if sid in self._expanded:
            return
        self._expanded.add(sid)
        card._expand_btn.config(text="⏳ Loading…", state='disabled')

        def _fetch():
            try:
                rows = _query(_EXTRACTION_DETAIL_QUERY, (sid,))
                ext  = rows[0] if rows else None
                self.after(0, lambda: self._render_detail(sid, card, ext))
            except Exception as exc:
                err = str(exc)
                self.after(0, lambda: self._show_card_error(sid, card, err))

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_detail(self, session_id, card, extraction):
        card._expand_btn.config(text="▶ Details (loaded)", state='disabled')
        frame = card._detail_frame

        if extraction:
            shown = False
            for label, key in [
                ('Topic',      'topic'),
                ('Grammar',    'grammar'),
                ('Vocabulary', 'vocabulary'),
                ('Skills',     'skills'),
                ('Homework',   'homework'),
                ('Summary',    'summary'),
            ]:
                val = extraction.get(key)
                if val:
                    shown = True
                    row = ttk.Frame(frame)
                    row.pack(fill=tk.X, pady=1)
                    ttk.Label(
                        row, text=f"  ▶ {label}:", width=14, anchor="w",
                        font=("TkDefaultFont", 9, "bold")
                    ).pack(side=tk.LEFT)
                    ttk.Label(
                        row, text=val, wraplength=460, justify="left"
                    ).pack(side=tk.LEFT, fill=tk.X, expand=True)
            if not shown:
                ttk.Label(
                    frame, text="  Extraction exists but all fields are empty — re-run extraction",
                    foreground="gray"
                ).pack(anchor="w")
        else:
            ttk.Label(
                frame, text="  No extraction data yet — click 'Generate Summary' to create one",
                foreground="gray"
            ).pack(anchor="w")

    def _show_card_error(self, session_id, card, msg):
        self._expanded.discard(session_id)
        card._expand_btn.config(text="▶ Details", state='normal')
        ttk.Label(
            card._detail_frame, text=f"Error: {msg}", foreground="#b71c1c"
        ).pack(anchor="w")

    # ── Generate Summary ──────────────────────────────────────────────────────

    def _generate_summary(self, session_id, btn):
        btn.config(text="⏳ Generating…", state='disabled')

        def _worker():
            try:
                result = subprocess.run(
                    [r'D:\envs\siri_worker\Scripts\python.exe',
                     r'D:\zone_b\langextract_processor.py',
                     session_id],
                    capture_output=True, text=True, timeout=120
                )
                rc, err = result.returncode, result.stderr
                if rc == 0:
                    self.after(0, lambda: self._load_day(self._current_date.isoformat()))
                else:
                    self.after(0, lambda: self._show_gen_error(btn, err))
            except subprocess.TimeoutExpired:
                self.after(0, lambda: self._show_gen_error(btn, "Timed out after 120s"))
            except Exception as exc:
                msg = str(exc)
                self.after(0, lambda: self._show_gen_error(btn, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_gen_error(self, btn, stderr):
        btn.config(text="Generate Summary", state='normal')
        ttk.Label(
            btn.master,
            text=f"Failed: {stderr[:100]}",
            foreground="#b71c1c"
        ).pack(side=tk.LEFT, padx=4)


# ── Date picker dialog ────────────────────────────────────────────────────────

class _DatePickerDialog(tk.Toplevel):

    def __init__(self, parent, current_date):
        super().__init__(parent)
        self.title("Pick a date")
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        ttk.Label(self, text="Year:") .grid(row=0, column=0, padx=8, pady=6, sticky="e")
        ttk.Label(self, text="Month:").grid(row=1, column=0, padx=8, pady=4, sticky="e")
        ttk.Label(self, text="Day:")  .grid(row=2, column=0, padx=8, pady=4, sticky="e")

        self._year  = ttk.Spinbox(self, from_=2020, to=2030, width=6)
        self._month = ttk.Spinbox(self, from_=1,    to=12,   width=4)
        self._day   = ttk.Spinbox(self, from_=1,    to=31,   width=4)

        self._year.set(current_date.year)
        self._month.set(current_date.month)
        self._day.set(current_date.day)

        self._year .grid(row=0, column=1, padx=4)
        self._month.grid(row=1, column=1, padx=4)
        self._day  .grid(row=2, column=1, padx=4)

        bbar = ttk.Frame(self)
        bbar.grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(bbar, text="OK",     command=self._ok    ).pack(side=tk.LEFT, padx=4)
        ttk.Button(bbar, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=4)

    def _ok(self):
        try:
            self.result = date(
                int(self._year.get()),
                int(self._month.get()),
                int(self._day.get())
            )
        except ValueError:
            pass
        self.destroy()
