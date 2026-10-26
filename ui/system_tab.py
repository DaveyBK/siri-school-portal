"""
ui/system_tab.py — System Control tab for the school portal.

Spec: D:/AI_phase/school/docs/SYSTEM_CONTROL_TAB_SPEC.md

Safety rules (non-negotiable):
  - Every external call (subprocess, DB, HTTP, ping) runs in a daemon thread.
  - All UI updates from threads use self.after(0, callback).
  - No auto-refresh by default. Optional 30s auto-refresh checkbox, default OFF.
  - All subprocess calls use explicit Python path: D:\envs\siri_worker\Scripts\python.exe
  - All jobs.db reads use read-only URI with busy_timeout.
  - Does NOT import control.py directly.
  - CWD for all control.py calls: D:\zone_b
"""
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import threading
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

from inventory import runmode
from ui import theme

# ── Constants ────────────────────────────────────────────────────────────────

PYTHON_EXE = r"D:\envs\siri_worker\Scripts\python.exe"
CONTROL_PY = r"D:\zone_b\control.py"
PORTAL_APP = r"D:\zone_b\portal\app.py"
JOBS_DB = r"D:\zone_b\jobs.db"
INCOMING_DIR = r"D:\zone_b\pc_ingest\incoming"
OLLAMA_URL = "http://127.0.0.1:11434/api/tags"
PI5_IP = "192.168.10.31"
PORTAL_PORT = 5555
PORTAL_PID_FILE = r"D:\zone_b\logs\control\portal.pid"
LOG_DIR = r"D:\zone_b\logs\control"
CONTROL_CWD = r"D:\zone_b"

# control.py cmd_status prints exactly:
#   [watcher] running=False pid=None
#   [worker ] running=True pid=13100
# Parse the fields. Do NOT substring-match "running": it is also
# present inside "running=False", which made both rows read RUNNING
# whatever the real state was.
_SVC_LINE = re.compile(r"^\[(watcher|worker)\s*\]\s+running=(\S+)\s+pid=(\S+)\s*$")

# Windows process creation flags
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

# The house palette lives in ui/design_system.py and is the single source of
# truth. theme.system_colors() hands back today's flat-UI values instead when
# PORTAL_THEME=classic. The status mapping survives either way:
#   RUNNING/UP/Start -> success, STOPPED/DOWN/Stop -> danger, warnings -> warning
COLORS = theme.system_colors()


# ── DB helper ────────────────────────────────────────────────────────────────

def _query(sql, params=(), timeout_ms=2000):
    """Read-only query against jobs.db. Returns list of dicts."""
    conn = sqlite3.connect(
        f"file:{JOBS_DB}?mode=ro", uri=True, timeout=timeout_ms / 1000
    )
    conn.execute(f"PRAGMA busy_timeout = {timeout_ms}")
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


# ── Main class ───────────────────────────────────────────────────────────────

class SystemTab(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)
        self._app = app
        self._busy = False  # True while a start/stop operation is running
        self._auto_refresh_var = tk.BooleanVar(value=False)
        self._auto_refresh_id = None

        if runmode.TEST_MODE:
            # Test mode: no Zone B, D:\ or network calls, and no refresh timer.
            tk.Label(self, text=f"Disabled in {runmode.MODE_NAME}: Zone B is not connected",
                     font=theme.font(12, bold=True), pady=40).pack(fill=tk.BOTH, expand=True)
            return

        self._build_ui()

    # ══════════════════════════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Header bar
        header_h = theme.scale(40)
        header = tk.Frame(self, bg=COLORS['primary'], height=header_h)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Siri diamond S-mark, drawn only when ui/assets/siri_mark.png exists.
        # Missing or unreadable asset falls back to a text-only header.
        mark = theme.header_mark(header, COLORS['primary'], header_h)
        if mark is not None:
            mark.pack(side=tk.LEFT, padx=(12, 0))

        tk.Label(header, text="SYSTEM CONTROL",
                 font=theme.font(12, bold=True, header=True),
                 bg=COLORS['primary'], fg=COLORS['white']).pack(side=tk.LEFT, padx=12)

        # Right side controls
        theme.button(header, 'neutral', text="Refresh", command=self._refresh,
                     classic=dict(bg=COLORS['dark'], fg='white',
                                  font=('Arial', 9), padx=8, pady=2)
                     ).pack(side=tk.RIGHT, padx=5, pady=5)

        tk.Checkbutton(header, text="Auto-refresh", variable=self._auto_refresh_var,
                       bg=COLORS['primary'], fg='white', selectcolor=COLORS['dark'],
                       activebackground=COLORS['primary'], activeforeground='white',
                       font=theme.font(9),
                       command=self._toggle_auto_refresh).pack(side=tk.RIGHT, padx=5)

        # Scrollable body
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self._body = tk.Frame(canvas)
        if not theme.CLASSIC:
            canvas.configure(bg=COLORS['white'])
            self._body.configure(bg=COLORS['white'])

        body_item = canvas.create_window((0, 0), window=self._body, anchor="nw")

        def _pin_top():
            """Hold the content against the top of the canvas.

            Tk lets the view drift above a scrollregion that is shorter than
            the viewport -- confine does not clamp at 0 in that case -- which
            pushed the whole tab down and left a blank band under the header.
            """
            if self._body.winfo_height() <= canvas.winfo_height():
                canvas.yview_moveto(0)

        def _on_body_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            if not theme.CLASSIC:
                _pin_top()

        def _on_canvas_configure(event):
            # Stretch the content to the canvas width. Without this the body
            # keeps its requested width and stays pinned to the left.
            canvas.itemconfigure(body_item, width=event.width)
            _pin_top()

        self._body.bind("<Configure>", _on_body_configure)
        if not theme.CLASSIC:
            canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel scrolling. Deliberately NOT gated on theme.CLASSIC: the
        # unguarded handler is a real bug in both modes, and these guards are
        # invisible unless they fire.
        def _on_mousewheel(event):
            # bind_all is application-wide, so a wheel event on any tab or
            # dialog reaches this canvas. Ignore it unless this tab is showing.
            if not self.winfo_ismapped():
                return
            # Nothing to scroll: scrolling here would only drift the view above
            # the content and open a blank band under the header bar.
            if self._body.winfo_height() <= canvas.winfo_height():
                return
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        if not theme.CLASSIC:
            # Two equal, responsive columns. Panels are placed by _place_panel().
            self._body.grid_columnconfigure(0, weight=1, uniform="syscol")
            self._body.grid_columnconfigure(1, weight=1, uniform="syscol")

        self._build_services_section()
        self._build_lesson_gate_section()
        self._build_gpu_section()
        self._build_queue_section()
        self._build_disk_section()
        self._build_errors_section()

    def _place_panel(self, lf, row, col, classic_pady):
        """Place a section panel.

        House mode: a cell in the two-column grid, pinned to the top of its
        cell at natural height. Classic mode: packed exactly as before.
        """
        if theme.CLASSIC:
            lf.pack(fill=tk.X, padx=10, pady=classic_pady)
            return
        padx = (10, 5) if col == 0 else (5, 10)
        pady = (10, 5) if row == 0 else ((5, 10) if row == 2 else 5)
        lf.grid(row=row, column=col, sticky="new", padx=padx, pady=pady)

    # ── Section 1: Services ──────────────────────────────────────────────────

    def _build_services_section(self):
        lf = theme.panel(self._body, " SERVICES ", padx=8, pady=8)
        self._place_panel(lf, 0, 0, (10, 5))

        # The header and every service row share ONE grid, so the columns line
        # up structurally. They used to be separate frames that happened to
        # carry matching character widths, which drifts on any font change.
        grid = tk.Frame(lf, **theme.on_panel())
        grid.pack(fill=tk.X)

        cols = ("Service", "Status", "Detail", "", "")
        if theme.CLASSIC:
            cell_w = (15, 12, 25, 8, 8)   # today's character widths, exactly
        else:
            cell_w = (None,) * 5
            # Measured from the live font against the widest text each column
            # actually shows -- including "Stopping...", which never fitted the
            # old 8-character action buttons.
            for i, px in enumerate((
                theme.measure(grid, "Flask Portal"),
                theme.measure(grid, "RUNNING", "STOPPED", "DOWN", bold=True),
                theme.measure(grid, "llama3.1:8b-instruct +3"),
                theme.measure(grid, "Stopping...", "Starting...", pad=28),
                theme.measure(grid, "Browse", "Log", pad=28),
            )):
                grid.grid_columnconfigure(i, minsize=px)

        def _cell(index):
            return {"width": cell_w[index]} if cell_w[index] else {}

        btn_sticky = "" if theme.CLASSIC else "ew"
        btn_classic = dict(font=("Arial", 8), width=8)

        for i, col in enumerate(cols):
            tk.Label(grid, text=col, font=theme.font(9, bold=True), anchor="w",
                     **_cell(i), **theme.on_panel()).grid(
                         row=0, column=i, padx=2, sticky="w")

        self._svc_rows = {}
        services = [
            ("watcher", "Watcher", True, False),
            ("worker", "Worker", True, False),
            ("portal", "Flask Portal", True, True),
            ("ollama", "Ollama", False, False),
            ("pi5", "Pi5", False, False),
        ]

        for idx, (key, label, has_action, has_browse) in enumerate(services):
            row = idx + 1

            lbl_name = tk.Label(grid, text=label, font=theme.font(9), anchor="w",
                                **_cell(0), **theme.on_panel())
            lbl_name.grid(row=row, column=0, padx=2, pady=1, sticky="w")

            lbl_status = tk.Label(grid, text="--", font=theme.font(9, bold=True),
                                  anchor="w", **_cell(1), **theme.on_panel())
            lbl_status.grid(row=row, column=1, padx=2, pady=1, sticky="w")

            lbl_detail = tk.Label(grid, text="", font=theme.font(9), anchor="w",
                                  **_cell(2), **theme.on_panel())
            lbl_detail.grid(row=row, column=2, padx=2, pady=1, sticky="w")

            btn_action = None
            btn_extra = None

            if has_action:
                btn_action = theme.button(grid, 'neutral', text="Start",
                                          state=tk.DISABLED, classic=btn_classic)
                btn_action.grid(row=row, column=3, padx=2, pady=1, sticky=btn_sticky)

            if has_browse:
                btn_extra = theme.button(grid, 'neutral', text="Browse",
                                         command=lambda: webbrowser.open(
                                             f"http://localhost:{PORTAL_PORT}"),
                                         classic=btn_classic)
                btn_extra.grid(row=row, column=4, padx=2, pady=1, sticky=btn_sticky)
            elif key in ("watcher", "worker"):
                log_file = f"{key}.out.log"
                btn_extra = theme.button(grid, 'neutral', text="Log",
                                         command=lambda f=log_file: self._open_log(f),
                                         classic=btn_classic)
                btn_extra.grid(row=row, column=4, padx=2, pady=1, sticky=btn_sticky)

            self._svc_rows[key] = {
                "status": lbl_status,
                "detail": lbl_detail,
                "action": btn_action,
                "running": None,
            }

    # ── Section 2: Lesson Gate ───────────────────────────────────────────────

    def _build_lesson_gate_section(self):
        lf = theme.panel(self._body, " LESSON GATE ", padx=8, pady=8)
        self._place_panel(lf, 1, 0, 5)

        self._lesson_label = tk.Label(lf, text="--", font=theme.font(10),
                                      anchor="w", **theme.on_panel())
        self._lesson_label.pack(side=tk.LEFT, padx=5)
        # Start Lesson removed 2026-09-25 (Zone B audit F46): it stopped every
        # active session and did not change clip routing, which follows the
        # schedule. Stop Lesson restored 2026-09-26 (F46): it closes the one
        # auto-routed session once its lesson has ended, so extraction can run.
        self._lesson_stop_btn = theme.button(
            lf, 'danger', text="Stop Lesson", command=self._stop_lesson,
            classic=dict(bg=COLORS['danger'], fg='white',
                         font=('Arial', 9), padx=8, pady=2))
        # Hidden until a session is active
        self._lesson_stop_btn.pack(side=tk.RIGHT, padx=5)
        self._lesson_stop_btn.pack_forget()

    # ── Section 3: GPU ───────────────────────────────────────────────────────

    def _build_gpu_section(self):
        lf = theme.panel(self._body, " GPU ", padx=8, pady=8)
        self._place_panel(lf, 0, 1, 5)

        self._gpu_info_label = tk.Label(lf, text="--", font=theme.font(10),
                                        anchor="w", **theme.on_panel())
        self._gpu_info_label.pack(fill=tk.X)

        self._gpu_bar = ttk.Progressbar(lf, length=theme.scale(400),
                                        mode='determinate')
        self._gpu_bar.pack(fill=tk.X, pady=(4, 0))

        self._gpu_bar_label = tk.Label(lf, text="", font=theme.font(8),
                                       anchor="w", **theme.on_panel())
        self._gpu_bar_label.pack(fill=tk.X)

    # ── Section 4: Pipeline Queue ────────────────────────────────────────────

    def _build_queue_section(self):
        lf = theme.panel(self._body, " PIPELINE QUEUE ", padx=8, pady=8)
        self._place_panel(lf, 1, 1, 5)

        self._incoming_label = tk.Label(lf, text="Incoming: --", font=theme.font(9),
                                        anchor="w", **theme.on_panel())
        self._incoming_label.pack(fill=tk.X, pady=(0, 5))

        # Job counts table
        cols = ("Job Type", "Queued", "Running", "Done", "Error")
        self._queue_tree = ttk.Treeview(lf, columns=cols, show="headings", height=3,
                                         selectmode="none")
        for col in cols:
            self._queue_tree.heading(col, text=col)
            w = theme.scale(140) if col == "Job Type" else theme.scale(80)
            self._queue_tree.column(col, width=w, anchor="center" if col != "Job Type" else "w")
        self._queue_tree.pack(fill=tk.X)

        # Stale jobs warning banner. Fill-only yellow: #FED600 is never text or
        # a thin line. Ink on it is 14.8:1, where the orange would be 2.3:1.
        stale_kw = {} if theme.CLASSIC else {'bg': theme.HOUSE['fill_only']}
        self._stale_frame = tk.Frame(lf, **stale_kw)
        self._stale_label = tk.Label(self._stale_frame, text="",
                                      font=theme.font(9, bold=True),
                                      fg=COLORS['warning'] if theme.CLASSIC else COLORS['ink'],
                                      anchor="w", **stale_kw)
        self._stale_label.pack(side=tk.LEFT, padx=5)
        self._stale_btn = theme.button(
            self._stale_frame, 'warning', text="Recover Stale Jobs",
            command=self._recover_stale_jobs,
            classic=dict(bg=COLORS['warning'], fg='white',
                         font=('Arial', 8), padx=6, pady=2))
        self._stale_btn.pack(side=tk.LEFT, padx=5)
        # Hidden by default
        self._stale_frame.pack(fill=tk.X, pady=(5, 0))
        self._stale_frame.pack_forget()

    # ── Section 5: Disk ──────────────────────────────────────────────────────

    def _build_disk_section(self):
        lf = theme.panel(self._body, " DISK ", padx=8, pady=8)
        self._place_panel(lf, 2, 1, 5)

        self._disk_label = tk.Label(lf, text="--", font=theme.font(9),
                                    anchor="w", **theme.on_panel())
        self._disk_label.pack(fill=tk.X)

        self._disk_bar = ttk.Progressbar(lf, length=theme.scale(400),
                                         mode='determinate')
        self._disk_bar.pack(fill=tk.X, pady=(4, 0))

    # ── Section 6: Recent Errors ─────────────────────────────────────────────

    def _build_errors_section(self):
        lf = theme.panel(self._body, " RECENT ERRORS ", padx=8, pady=8)
        self._place_panel(lf, 2, 0, (5, 10))

        self._errors_label = tk.Label(lf, text="--", font=theme.font(9, mono=True),
                                       anchor="w", justify=tk.LEFT,
                                       **theme.on_panel())
        self._errors_label.pack(fill=tk.X)

    # ══════════════════════════════════════════════════════════════════════════
    #  REFRESH
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh(self):
        """Kick off a single background thread that gathers ALL data."""
        if runmode.TEST_MODE or self._busy:
            return
        threading.Thread(target=self._gather_all, daemon=True).start()

    def _toggle_auto_refresh(self):
        if self._auto_refresh_var.get():
            self._schedule_auto_refresh()
        else:
            if self._auto_refresh_id is not None:
                self.after_cancel(self._auto_refresh_id)
                self._auto_refresh_id = None

    def _schedule_auto_refresh(self):
        if not self._auto_refresh_var.get():
            return
        self._auto_refresh_id = self.after(30000, self._auto_refresh_tick)

    def _auto_refresh_tick(self):
        if not self._auto_refresh_var.get():
            return
        if not self._busy:
            self._refresh()
        self._schedule_auto_refresh()

    def on_tab_selected(self):
        """Called when this tab becomes visible. Triggers one refresh."""
        self._refresh()

    # ══════════════════════════════════════════════════════════════════════════
    #  DATA GATHERING (runs in background thread)
    # ══════════════════════════════════════════════════════════════════════════

    def _gather_all(self):
        results = {}

        # ── Services: watcher & worker via control.py status ─────────────
        try:
            r = subprocess.run(
                [PYTHON_EXE, CONTROL_PY, "status"],
                capture_output=True, text=True, timeout=10,
                cwd=CONTROL_CWD
            )
            results['control_stdout'] = r.stdout
            results['control_stderr'] = r.stderr
        except subprocess.TimeoutExpired:
            results['control_stdout'] = ""
            results['control_error'] = "Timed out"
        except Exception as e:
            results['control_stdout'] = ""
            results['control_error'] = str(e)

        # ── Ollama ───────────────────────────────────────────────────────
        try:
            import urllib.request
            req = urllib.request.Request(OLLAMA_URL)
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read())
            models = [m['name'] for m in data.get('models', [])]
            results['ollama'] = {'running': True, 'models': models}
        except Exception:
            results['ollama'] = {'running': False, 'models': []}

        # ── Flask Portal ─────────────────────────────────────────────────
        portal_running = False
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        try:
            s.connect(('127.0.0.1', PORTAL_PORT))
            portal_running = True
        except (ConnectionRefusedError, socket.timeout, OSError):
            pass
        finally:
            s.close()

        # Check for stale portal PID file
        portal_pid = None
        if Path(PORTAL_PID_FILE).exists():
            try:
                portal_pid = int(Path(PORTAL_PID_FILE).read_text().strip())
            except Exception:
                pass
            if not portal_running and portal_pid:
                # Stale PID file — clean up
                try:
                    Path(PORTAL_PID_FILE).unlink(missing_ok=True)
                except Exception:
                    pass
                portal_pid = None

        results['portal'] = {'running': portal_running, 'pid': portal_pid}

        # ── Pi5 ──────────────────────────────────────────────────────────
        try:
            r = subprocess.run(
                ['ping', '-n', '1', '-w', '1500', PI5_IP],
                capture_output=True, text=True, timeout=5
            )
            results['pi5'] = {'reachable': r.returncode == 0, 'output': r.stdout}
        except Exception:
            results['pi5'] = {'reachable': False, 'output': ''}

        # ── GPU ──────────────────────────────────────────────────────────
        try:
            r = subprocess.run(
                ['nvidia-smi',
                 '--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu',
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            parts = [p.strip() for p in r.stdout.strip().split(',')]
            results['gpu'] = {
                'name': parts[0], 'mem_used': int(parts[1]),
                'mem_total': int(parts[2]), 'util': int(parts[3]),
                'temp': int(parts[4])
            }
        except Exception:
            results['gpu'] = None

        # ── Jobs queue ───────────────────────────────────────────────────
        try:
            rows = _query(
                "SELECT job_type, status, COUNT(*) as n "
                "FROM job GROUP BY job_type, status ORDER BY job_type, status"
            )
            results['job_counts'] = rows
        except Exception as e:
            results['job_counts'] = None
            results['job_counts_error'] = str(e)

        # ── Stale running job count ──────────────────────────────────────
        try:
            rows = _query("SELECT COUNT(*) as n FROM job WHERE status='running'")
            results['stale_running'] = rows[0]['n'] if rows else 0
        except Exception:
            results['stale_running'] = 0

        # ── Incoming folder ──────────────────────────────────────────────
        try:
            wavs = list(Path(INCOMING_DIR).glob("*.wav"))
            count = len(wavs)
            size_mb = sum(f.stat().st_size for f in wavs) / (1024 * 1024)
            results['incoming'] = {'count': count, 'size_mb': size_mb}
        except Exception:
            results['incoming'] = {'count': 0, 'size_mb': 0}

        # ── Lesson gate ──────────────────────────────────────────────────
        try:
            rows = _query(
                "SELECT session_id, class_id, started_at "
                "FROM lesson_session WHERE is_active = 1 ORDER BY started_at DESC"
            )
            results['active_lesson'] = rows[0] if rows else None      # the newest
            results['active_lesson_count'] = len(rows)
        except Exception:
            results['active_lesson'] = None
            results['active_lesson_count'] = 0

        # ── Disk ─────────────────────────────────────────────────────────
        try:
            usage = shutil.disk_usage("D:\\")
            results['disk'] = {
                'used_gb': usage.used / (1024 ** 3),
                'total_gb': usage.total / (1024 ** 3),
                'free_gb': usage.free / (1024 ** 3),
            }
        except Exception:
            results['disk'] = None

        # ── Recent errors ────────────────────────────────────────────────
        try:
            rows = _query(
                "SELECT job_id, job_type, error_message, finished_at "
                "FROM job WHERE status = 'error' "
                "ORDER BY finished_at DESC LIMIT 5"
            )
            results['errors'] = rows
        except Exception:
            results['errors'] = []

        # Post to UI
        self.after(0, lambda: self._update_ui(results))

    # ══════════════════════════════════════════════════════════════════════════
    #  UI UPDATE (runs on main thread via self.after)
    # ══════════════════════════════════════════════════════════════════════════

    def _update_ui(self, results):
        self._update_services(results)
        self._update_lesson_gate(results)
        self._update_gpu(results)
        self._update_queue(results)
        self._update_disk(results)
        self._update_errors(results)

    def _update_services(self, results):
        # Parse control.py status output
        stdout = results.get('control_stdout', '')
        watcher_running = False
        worker_running = False
        watcher_pid = ""
        worker_pid = ""

        if 'control_error' in results:
            watcher_detail = results['control_error']
            worker_detail = results['control_error']
        else:
            watcher_detail = ""
            worker_detail = ""
            matched = set()
            for line in stdout.splitlines():
                m = _SVC_LINE.match(line.strip())
                if not m:
                    continue
                name, running_s, pid_s = m.group(1), m.group(2), m.group(3)
                is_running = (running_s.lower() == 'true')
                detail = f"PID {pid_s}" if pid_s.isdigit() else ""
                matched.add(name)
                if name == 'watcher':
                    watcher_running, watcher_detail = is_running, detail
                else:
                    worker_running, worker_detail = is_running, detail

            # If control.py produced no parseable status line at all, say so
            # rather than showing STOPPED as though we had actually checked.
            if 'watcher' not in matched:
                watcher_detail = "status unreadable"
            if 'worker' not in matched:
                worker_detail = "status unreadable"

        # Watcher row
        self._set_service_row("watcher", watcher_running, watcher_detail,
                              self._start_watcher, self._stop_watcher)
        # Worker row
        self._set_service_row("worker", worker_running, worker_detail,
                              self._start_worker, self._stop_worker)

        # Portal
        portal = results.get('portal', {})
        portal_running = portal.get('running', False)
        portal_detail = ""
        if portal_running:
            portal_detail = f"port {PORTAL_PORT}"
        self._set_service_row("portal", portal_running, portal_detail,
                              self._start_portal, self._stop_portal)

        # Ollama
        ollama = results.get('ollama', {})
        ollama_running = ollama.get('running', False)
        models = ollama.get('models', [])
        ollama_detail = ""
        if models:
            ollama_detail = models[0]
            if len(models) > 1:
                ollama_detail += f" +{len(models) - 1}"
        row = self._svc_rows["ollama"]
        row["running"] = ollama_running
        row["status"].config(
            text="RUNNING" if ollama_running else "STOPPED",
            fg=COLORS['success'] if ollama_running else COLORS['danger']
        )
        row["detail"].config(text=ollama_detail)

        # Pi5
        pi5 = results.get('pi5', {})
        reachable = pi5.get('reachable', False)
        pi5_detail = ""
        if reachable:
            # Extract ping time from output
            output = pi5.get('output', '')
            for tok in output.replace('=', ' ').split():
                if tok.endswith('ms'):
                    pi5_detail = tok
                    break
        row = self._svc_rows["pi5"]
        row["running"] = reachable
        row["status"].config(
            text="UP" if reachable else "DOWN",
            fg=COLORS['success'] if reachable else COLORS['danger']
        )
        row["detail"].config(text=pi5_detail)

    def _set_service_row(self, key, running, detail, start_cmd, stop_cmd):
        row = self._svc_rows[key]
        row["running"] = running
        row["status"].config(
            text="RUNNING" if running else "STOPPED",
            fg=COLORS['success'] if running else COLORS['danger']
        )
        row["detail"].config(text=detail)

        btn = row["action"]
        if btn:
            # ttk buttons ignore bg=, so the Start/Stop flip goes through
            # theme.set_button(). The meaning is unchanged:
            # running -> danger (offer Stop), stopped -> success (offer Start).
            if running:
                theme.set_button(btn, 'danger', text="Stop",
                                 state=tk.NORMAL, command=stop_cmd)
            else:
                theme.set_button(btn, 'success', text="Start",
                                 state=tk.NORMAL, command=start_cmd)

    def _update_lesson_gate(self, results):
        lesson = results.get('active_lesson')
        if lesson:
            class_id = lesson.get('class_id') or ''
            started = lesson.get('started_at', '')
            display = _format_class(class_id)
            # Format started time — convert UTC to Bangkok (UTC+7)
            time_part = ""
            date_part = ""
            if started:
                try:
                    dt = datetime.fromisoformat(started)
                    dt_bkk = dt + timedelta(hours=7)
                    time_part = dt_bkk.strftime("%H:%M")
                    today_bkk = (datetime.now(timezone.utc) + timedelta(hours=7)).date()
                    if dt_bkk.date() != today_bkk:               # a lesson from another day must not look current
                        date_part = dt_bkk.strftime("%Y-%m-%d") + " "
                except ValueError:
                    if 'T' in started:
                        time_part = started.split('T')[1][:5]
                        date_part = started.split('T')[0] + " "
            text = f"{display} — started {date_part}{time_part}"
            count = results.get('active_lesson_count') or 1
            if count > 1:
                text += f" — {count} lessons marked active — newest shown"
            self._lesson_label.config(text=text)
            # Always reset stop button to ready state
            self._lesson_stop_btn.config(text="Stop Lesson", state=tk.NORMAL)
            self._lesson_stop_btn.pack(side=tk.RIGHT, padx=5)
        else:
            self._lesson_label.config(text="No active lesson")
            self._lesson_stop_btn.config(text="Stop Lesson", state=tk.NORMAL)
            self._lesson_stop_btn.pack_forget()

    def _update_gpu(self, results):
        gpu = results.get('gpu')
        if gpu is None:
            self._gpu_info_label.config(text="GPU: unavailable")
            self._gpu_bar['value'] = 0
            self._gpu_bar_label.config(text="")
            return

        pct = (gpu['mem_used'] / gpu['mem_total'] * 100) if gpu['mem_total'] > 0 else 0
        temp = gpu['temp']
        temp_color = COLORS['success']
        if temp > 85:
            temp_color = COLORS['danger']
        elif temp > 70:
            temp_color = COLORS['warning']

        self._gpu_info_label.config(
            text=f"{gpu['name']}  |  {gpu['util']}% util  |  {temp}\u00b0C",
        )
        self._gpu_info_label.config(fg=temp_color if temp > 70 else COLORS['ink'])
        self._gpu_bar['value'] = pct
        self._gpu_bar_label.config(
            text=f"{gpu['mem_used']}/{gpu['mem_total']} MB ({pct:.0f}%)"
        )

    def _update_queue(self, results):
        # Incoming
        inc = results.get('incoming', {})
        self._incoming_label.config(
            text=f"Incoming: {inc.get('count', 0)} WAV files ({inc.get('size_mb', 0):.0f} MB)"
        )

        # Job counts table
        for item in self._queue_tree.get_children():
            self._queue_tree.delete(item)

        job_counts = results.get('job_counts')
        if job_counts is None:
            err = results.get('job_counts_error', 'Database busy — try again')
            self._queue_tree.insert("", tk.END, values=(err, "", "", "", ""))
        else:
            # Pivot: group by job_type
            pivot = {}
            for row in job_counts:
                jt = row['job_type']
                if jt not in pivot:
                    pivot[jt] = {'queued': 0, 'running': 0, 'done': 0, 'error': 0}
                status = row['status']
                if status in pivot[jt]:
                    pivot[jt][status] = row['n']

            for jt in sorted(pivot.keys()):
                d = pivot[jt]
                running_str = str(d['running'])
                self._queue_tree.insert("", tk.END, values=(
                    jt, d['queued'], running_str, d['done'], d['error']
                ))

        # Stale running jobs
        stale = results.get('stale_running', 0)
        worker_running = self._svc_rows.get("worker", {}).get("running", False)
        if stale > 0 and not worker_running:
            self._stale_label.config(text=f"\u26a0 {stale} stale running jobs (worker stopped)")
            self._stale_frame.pack(fill=tk.X, pady=(5, 0))
        else:
            self._stale_frame.pack_forget()

    def _update_disk(self, results):
        disk = results.get('disk')
        if disk is None:
            self._disk_label.config(text="Disk: unavailable")
            self._disk_bar['value'] = 0
            return
        pct = (disk['used_gb'] / disk['total_gb'] * 100) if disk['total_gb'] > 0 else 0
        self._disk_label.config(
            text=f"D: {disk['used_gb']:.0f} GB / {disk['total_gb']:.0f} GB used "
                 f"({disk['free_gb']:.0f} GB free)"
        )
        self._disk_bar['value'] = pct

    def _update_errors(self, results):
        errors = results.get('errors', [])
        if not errors:
            self._errors_label.config(text="No recent errors")
            return
        lines = []
        for err in errors:
            ts = err.get('finished_at', '')[:16].replace('T', ' ')
            jt = err.get('job_type', '')
            msg = err.get('error_message', '') or ''
            if len(msg) > 60:
                msg = msg[:60] + "..."
            lines.append(f"{ts}  {jt}  \"{msg}\"")
        self._errors_label.config(text="\n".join(lines))

    # ══════════════════════════════════════════════════════════════════════════
    #  SERVICE ACTIONS (each runs in a daemon thread)
    # ══════════════════════════════════════════════════════════════════════════

    def _run_control(self, args, label=""):
        """Run a control.py command in a background thread. Auto-refresh after 3s."""
        def _work():
            self._busy = True
            try:
                subprocess.run(
                    [PYTHON_EXE, CONTROL_PY] + args,
                    capture_output=True, text=True, timeout=15,
                    cwd=CONTROL_CWD
                )
            except subprocess.TimeoutExpired:
                self.after(0, lambda: messagebox.showwarning(
                    "Timeout", f"{label} timed out — check manually"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Error", f"{label} failed: {e}"))
            finally:
                self._busy = False
                self.after(3000, self._refresh)

        threading.Thread(target=_work, daemon=True).start()

    def _start_watcher(self):
        self._svc_rows["watcher"]["action"].config(text="Starting...", state=tk.DISABLED)
        self._run_control(["watcher", "start"], "Watcher start")

    def _stop_watcher(self):
        self._svc_rows["watcher"]["action"].config(text="Stopping...", state=tk.DISABLED)
        self._run_control(["watcher", "stop"], "Watcher stop")

    def _start_worker(self):
        self._svc_rows["worker"]["action"].config(text="Starting...", state=tk.DISABLED)
        self._run_control(["worker", "start"], "Worker start")

    def _stop_worker(self):
        self._svc_rows["worker"]["action"].config(text="Stopping...", state=tk.DISABLED)
        self._run_control(["worker", "stop"], "Worker stop")

    def _start_portal(self):
        """Spawn Flask portal detached, save PID file."""
        self._svc_rows["portal"]["action"].config(text="Starting...", state=tk.DISABLED)

        def _work():
            self._busy = True
            try:
                proc = subprocess.Popen(
                    [PYTHON_EXE, PORTAL_APP],
                    cwd=CONTROL_CWD,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                Path(PORTAL_PID_FILE).parent.mkdir(parents=True, exist_ok=True)
                with open(PORTAL_PID_FILE, 'w') as f:
                    f.write(str(proc.pid))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Error", f"Portal start failed: {e}"))
            finally:
                self._busy = False
                self.after(3000, self._refresh)

        threading.Thread(target=_work, daemon=True).start()

    def _stop_portal(self):
        """Kill Flask portal via PID file."""
        self._svc_rows["portal"]["action"].config(text="Stopping...", state=tk.DISABLED)

        def _work():
            self._busy = True
            try:
                pid_path = Path(PORTAL_PID_FILE)
                if pid_path.exists():
                    pid = int(pid_path.read_text().strip())
                    subprocess.run(
                        ['taskkill', '/PID', str(pid), '/T', '/F'],
                        capture_output=True, text=True, timeout=10
                    )
                    pid_path.unlink(missing_ok=True)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Error", f"Portal stop failed: {e}"))
            finally:
                self._busy = False
                self.after(3000, self._refresh)

        threading.Thread(target=_work, daemon=True).start()

    def _open_log(self, filename):
        path = os.path.join(LOG_DIR, filename)
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showinfo("Log", f"Log file not found:\n{path}")

    # ── Lesson Gate Actions ──────────────────────────────────────────────────

    def _stop_lesson(self):
        # A press mid-lesson cuts the summary short and later clips of that
        # class are quarantined (F46), so confirm the lesson has ended.
        if not messagebox.askyesno(
                "Stop Lesson",
                f"{self._lesson_label.cget('text')}\n\n"
                "Stop only if this lesson has finished. Audio recorded after "
                "the stop will not be added to this lesson.\n\nStop it now?",
                icon='warning', default='no'):
            return
        self._lesson_stop_btn.config(text="Stopping...", state=tk.DISABLED)
        self._run_control(["lesson", "stop"], "Lesson stop")
        # Safety net: force a refresh after 8s even if _busy blocked the 3s one
        self.after(8000, self._force_refresh_lesson)

    def _force_refresh_lesson(self):
        """Safety net: if lesson gate is still showing Stopping, force a refresh."""
        if self._lesson_stop_btn.cget("text") == "Stopping...":
            self._busy = False
            self._refresh()

    # ── Stale Jobs Recovery ──────────────────────────────────────────────────

    def _recover_stale_jobs(self):
        self._stale_btn.config(text="Recovering...", state=tk.DISABLED)
        self._run_control(["jobs", "requeue-expired"], "Recover stale jobs")


# ── Helper ───────────────────────────────────────────────────────────────────

def _format_class(class_id):
    """Format class_id like 'mon_1510_sm2' → 'SM2 (15:10)'."""
    if not class_id:
        return "Unassigned Class"
    parts = class_id.split('_')
    if len(parts) >= 3:
        label = '_'.join(parts[2:]).upper()
        t = parts[1]
        return f"{label} ({t[:2]}:{t[2:]})"
    return class_id
