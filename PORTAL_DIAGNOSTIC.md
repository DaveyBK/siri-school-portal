# PORTAL DIAGNOSTIC — School Portal State Check

**Persona:** Systems diagnostician — read-only first, then targeted fix

**Direct Aim:** Diagnose the current state of the School Portal app — what's working, what's broken, what tabs exist, and fix the scanner error: `module 'inventory.events' has no attribute 'log_event'`.

**Overall Aim:** Get a clear picture of the portal's current state after the Feb 25 reset to baseline `6ef1121`, and fix the one blocking error so the USB scanner works for attendance.

**Context:**
- Portal is at `D:\AI_phase\school\apps\school_portal\`
- It was reset to commit `6ef1121` (Nov 26 baseline) on ~Feb 25
- Some features may have been re-applied from backup at `D:\AI_phase\school\apps\school_portal_backup_20260225\`
- The scanner IS detected and working physically — it scans, extra characters are auto-cleaned
- But processing the QR fails with: `module 'inventory.events' has no attribute 'log_event'`

---

## PHASE 1 — READ ONLY. Change nothing. Report everything.

### 1a. Git status
```powershell
cd D:\AI_phase\school\apps\school_portal
git log --oneline -5
git status --short
git diff --stat
```
Report: What commit are we on? Any uncommitted changes?

### 1b. List all portal tabs
```powershell
grep -n "notebook.add\|_build_.*tab\|ttk.Frame" ui/main_window.py
```
Report: Which tabs exist in the current build?

### 1c. Check which files exist vs baseline
List all `.py` files under `ui/`, `data/`, `inventory/`, `hardware/` and note which ones are NOT in the baseline commit:
```powershell
git ls-files ui/ data/ inventory/ hardware/
dir /s /b ui\*.py data\*.py inventory\*.py
```
Compare and report any files present on disk but not tracked by git.

### 1d. Check the events module
```powershell
type inventory\events.py
```
Report: Does `log_event` exist? What functions ARE in this file?

### 1e. Check where log_event is called
```powershell
findstr /s /n "log_event" *.py ui\*.py inventory\*.py data\*.py
```
Report: Every file and line that calls `log_event`.

### 1f. Check if backup has the fix
```powershell
findstr /n "log_event" D:\AI_phase\school\apps\school_portal_backup_20260225\inventory\events.py
```
Report: Does the backup version of `events.py` have `log_event`?

### 1g. Check roster and lessons tab status
```powershell
if exist ui\roster_tab.py (echo ROSTER TAB EXISTS) else (echo ROSTER TAB MISSING)
if exist ui\lessons_tab.py (echo LESSONS TAB EXISTS) else (echo LESSONS TAB MISSING)
if exist data\roster_bridge.py (echo ROSTER BRIDGE EXISTS) else (echo ROSTER BRIDGE MISSING)
```

### 1h. Check inventory.db schema
```powershell
python -c "import sqlite3; conn=sqlite3.connect(r'data\inventory.db'); [print(r[0]) for r in conn.execute(\"SELECT sql FROM sqlite_master WHERE type='table'\").fetchall()]; conn.close()"
```
Report: Do `class_def` and `class_roster` tables exist (roster system), or just baseline tables?

---

## ⛔ STOP — Report findings to David before proceeding.

Present a summary table:

| Feature | Status | Notes |
|---------|--------|-------|
| Portal launches | ✅ / ❌ | |
| Scanner detection | ✅ / ❌ | |
| Scanner QR processing | ✅ / ❌ | |
| Roster tab | ✅ / ❌ | |
| Lessons tab | ✅ / ❌ | |
| Roster bridge | ✅ / ❌ | |
| class_def/class_roster tables | ✅ / ❌ | |
| Events module complete | ✅ / ❌ | |
| Git state | clean / dirty | |

---

## PHASE 2 — Fix scanner error (ONLY after David approves)

Based on Phase 1 findings, the fix for `log_event` will be one of:

**Option A** — If `log_event` exists in the backup `events.py`:
Copy the function from `school_portal_backup_20260225\inventory\events.py` into the current `inventory\events.py`. Copy ONLY the `log_event` function and any imports it needs. Do not copy the entire file.

**Option B** — If `log_event` doesn't exist anywhere:
Add a minimal `log_event` function to `inventory\events.py`:
```python
def log_event(event_type: str, detail: str = "", student_id: int = None):
    """Log a portal event to the admin log."""
    # Minimal implementation — logs to admin_log table if it exists
    import sqlite3
    from pathlib import Path
    db_path = Path(__file__).parent.parent / "data" / "inventory.db"
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO admin_log (event_type, detail, student_id, timestamp) VALUES (?, ?, ?, datetime('now'))",
            (event_type, detail, student_id)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Don't crash the portal over a logging failure
```

**Verify after fix:**
1. Launch portal
2. Open Scan Mode
3. Scan a QR code
4. Confirm no error dialog — scan processes correctly

---

## DO NOT
- Do NOT modify any Zone B files
- Do NOT add new tabs or features
- Do NOT refactor anything
- Do NOT commit to git without David's approval
- Do NOT touch any file other than `inventory\events.py` (in Phase 2)
