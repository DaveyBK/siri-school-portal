# WIRE_LINE_ID_TO_TEACHER_PORTAL.md

## Persona
Integration engineer — minimal, precise wiring between two existing systems.

## Direct Aim
Wire the `parent_line_id` column (now in `inventory.db`) into the Zone B teacher portal so that:
1. `get_roster_for_class()` returns the LINE ID with each student
2. `resolve_line_recipient()` can look up a student's LINE ID
3. Parent messages get real LINE IDs instead of always showing `no_line_id`

## Overall Aim
Close the last gap in the LINE messaging pipeline. The column now exists in `inventory.db`, the school portal can populate it — this instruction wires the read path so the teacher portal actually uses it.

## Mandatory Read-First
Before making ANY changes, read these files in full:
1. `D:\zone_b\portal\school_db.py` — the read-only bridge to inventory.db
2. `D:\zone_b\langextract_processor.py` — lines 325–370, the message generation loop
3. Confirm `D:\zone_b\line_recipient_resolver.py` does NOT exist (it doesn't — that's the problem)

---

## STOP GATE 1
After reading, report:
- Current SELECT columns in `get_roster_for_class()` (should be: student_id, first_name, last_name, level — NO parent_line_id yet)
- How `resolve_line_recipient` is imported (line 327: inside try block, fails silently)
- Confirm `line_recipient_resolver.py` is missing

Wait for human confirmation before proceeding.

---

## Task 1 — Update school_db.py

In `D:\zone_b\portal\school_db.py`, function `get_roster_for_class()`:

Change the SELECT from:
```sql
SELECT s.student_id, s.first_name, s.last_name, s.level
FROM class_roster cr
JOIN students s ON s.student_id = cr.student_id
WHERE cr.class_id = ? AND cr.removed_at IS NULL
ORDER BY s.first_name
```

To:
```sql
SELECT s.student_id, s.first_name, s.last_name, s.level, s.parent_line_id
FROM class_roster cr
JOIN students s ON s.student_id = cr.student_id
WHERE cr.class_id = ? AND cr.removed_at IS NULL
ORDER BY s.first_name
```

One column added. Nothing else changes.

---

## Task 2 — Create line_recipient_resolver.py

Create `D:\zone_b\line_recipient_resolver.py` with this content:

```python
"""
line_recipient_resolver.py — Resolve parent LINE ID for a student.

Reads from inventory.db (read-only) via school_db helper.
Returns the parent_line_id string or None if not set.
"""
import sqlite3
import os
from pathlib import Path


def _school_db_path() -> Path:
    """Return inventory.db path, respecting environment override."""
    default = (
        r"D:\AI_phase\school\apps\school_portal\data\inventory.db"
        if os.name == "nt"
        else "/mnt/d/AI_phase/school/apps/school_portal/data/inventory.db"
    )
    return Path(os.environ.get("SCHOOL_DB_PATH", default))


def resolve_line_recipient(student_id: str) -> str | None:
    """
    Look up parent_line_id for a given student_id from inventory.db.

    Returns:
        The parent LINE ID string, or None if not found / not set / db unavailable.
    """
    db_path = _school_db_path()
    if not db_path.exists():
        return None

    try:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5)
        conn.execute("PRAGMA busy_timeout = 3000")
        row = conn.execute(
            "SELECT parent_line_id FROM students WHERE student_id = ?",
            (str(student_id),)
        ).fetchone()
        conn.close()

        if row and row[0]:
            return row[0].strip()
        return None

    except Exception as exc:
        print(f"  [line_resolver] Failed for {student_id}: {type(exc).__name__}: {exc}")
        return None
```

This is intentionally simple — one function, one query, returns a string or None. It matches the import at line 327 of `langextract_processor.py`:
```python
from line_recipient_resolver import resolve_line_recipient
```

No changes needed in `langextract_processor.py` — the import and call already exist.

---

## STOP GATE 2
Report:
- `school_db.py` SELECT now includes `parent_line_id`
- `line_recipient_resolver.py` created at `D:\zone_b\`
- No changes made to `langextract_processor.py` (confirm import still matches)

Wait for human confirmation.

---

## Verification

1. Start the Flask portal:
   ```powershell
   D:\envs\siri_worker\Scripts\python.exe D:\zone_b\portal\app.py
   ```
   Confirm no import errors.

2. Test the resolver manually:
   ```powershell
   D:\envs\siri_worker\Scripts\python.exe -c "import sys; sys.path.insert(0, r'D:\zone_b'); from line_recipient_resolver import resolve_line_recipient; print(resolve_line_recipient('20000101'))"
   ```
   Should return None (no LINE IDs populated yet) — but should NOT throw an error.

3. Test roster includes new column:
   ```powershell
   D:\envs\siri_worker\Scripts\python.exe -c "import sys; sys.path.insert(0, r'D:\zone_b\portal'); from school_db import get_roster_for_class; r = get_roster_for_class('tue_1610_sm2'); print(r[0] if r else 'empty')"
   ```
   Should show a dict with `parent_line_id` key (value will be None until populated).

4. Once you add a LINE ID to a student via the school portal edit dialog, re-run step 2 with that student's ID — it should return the LINE ID.

---

## What NOT To Do
- Do NOT modify `langextract_processor.py` — the import and call already work
- Do NOT modify `jobs.db` or any Zone B database tables
- Do NOT modify any school portal files (those changes are already done)
- Do NOT add any new dependencies or packages
- Do NOT create a separate database or cache for LINE IDs
- Do NOT modify any other function in `school_db.py` besides `get_roster_for_class()`
