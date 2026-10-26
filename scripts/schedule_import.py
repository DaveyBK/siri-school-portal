import csv
from pathlib import Path
from typing import Dict, List, Optional

from inventory.db import get_connection
from inventory import models


# Project root (Pear v2)
ROOT = Path(__file__).resolve().parent

# Folder where you drop weekly schedule CSVs
# You said: C:\inventory\Pear v2\imports\student atten
SCHEDULE_DIR = ROOT / "imports" / "student atten"
SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)


def get_latest_schedule_csv() -> Optional[Path]:
    """
    Return the most recently modified CSV in the schedule folder,
    or None if there are no CSVs.
    """
    csv_files = list(SCHEDULE_DIR.glob("*.csv"))
    if not csv_files:
        return None
    return max(csv_files, key=lambda p: p.stat().st_mtime)


def _parse_schedule_csv(path: Path) -> List[Dict[str, str]]:
    """
    Parse the schedule CSV into a list of dicts.

    Expected columns (case-insensitive):
        date          -> '2025-11-03' (YYYY-MM-DD)
        student_id    -> must match students.student_id

    Optional but useful:
        start_time, end_time, level, group_name, class, lesson, student_name, etc.
    """
    rows: List[Dict[str, str]] = []

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            # normalise keys to lowercase, strip whitespace
            row: Dict[str, str] = {}
            for k, v in raw.items():
                key = (k or "").strip().lower()
                val = (v or "").strip()
                if key:
                    row[key] = val
            if row:
                rows.append(row)

    return rows


def scheduled_student_ids(session_date: str) -> List[str]:
    """
    IDs of the students the latest schedule CSV lists for this date, in file order.

    Read-only: it writes nothing. The Attendance tab shows these students as "not marked" until someone marks them;
    an "absent" mark is never inserted from a schedule.

    - Looks in imports\\student atten for the newest .csv
    - Reads rows where date (or session_date) == session_date
    - Takes the student id from student_id, id, student or student code
    """
    csv_path = get_latest_schedule_csv()
    if not csv_path:
        return []

    ids: List[str] = []
    for r in _parse_schedule_csv(csv_path):
        row_date = r.get("date") or r.get("session_date")
        if row_date != session_date:
            continue
        sid = (
            r.get("student_id")
            or r.get("id")
            or r.get("student")
            or r.get("student code")
            or ""
        ).strip()
        if sid and sid not in ids:
            ids.append(sid)
    return ids
