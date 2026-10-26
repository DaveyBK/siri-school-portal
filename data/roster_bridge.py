"""
Roster Bridge Module — connects class roster data with live attendance.

Provides helper functions for Zone B teacher portal integration:
- Which class is happening right now?
- Who is enrolled in that class?
- Who has already checked in today?
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from inventory.db import get_connection
from inventory import models


# Day-of-week mapping: Python weekday() -> DB day_of_week (both 0=Monday)

def get_class_for_now(lookahead_minutes: int = 15) -> Optional[Dict[str, Any]]:
    """
    Find the active lesson for right now.

    Checks extra_lesson table FIRST (one-off overrides), then falls back
    to the recurring class_def weekly schedule.

    Includes a lookahead window so the roster loads slightly before class starts.

    Returns:
        Matching class_def or extra_lesson dict, or None if nothing is scheduled now.
        Extra lesson dicts include an 'is_extra_lesson' key set to True.
    """
    now = datetime.now()

    # --- Check extra lessons first (one-off overrides) ---
    extra = models.get_extra_lesson_for_datetime(now)
    if extra:
        extra['is_extra_lesson'] = True
        return extra

    # --- Fall back to recurring weekly schedule ---
    current_day = now.weekday()  # 0=Monday
    current_time = now.strftime("%H:%M")
    lookahead_time = (now + timedelta(minutes=lookahead_minutes)).strftime("%H:%M")

    models._ensure_class_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM class_def
        WHERE day_of_week = ?
          AND is_active = 1
          AND start_time <= ?
          AND end_time >= ?
        ORDER BY start_time
        LIMIT 1
        """,
        (current_day, lookahead_time, current_time),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        cls = dict(row)
        # Skip if this class is cancelled today
        if models.is_class_cancelled(cls['class_id']):
            return None
        return cls
    return None


def get_active_lesson_roster(class_id, is_extra_lesson: bool = False) -> List[Dict[str, Any]]:
    """
    Get the roster for a class (or extra lesson) with today's attendance status merged in.

    Args:
        class_id: class_def.class_id or extra_lesson.id
        is_extra_lesson: If True, fetch from extra_lesson_student instead of class_roster

    Returns:
        List of dicts: {student_id, first_name, last_name, level, checked_in, scanned_at}
    """
    if is_extra_lesson:
        roster = models.get_students_for_extra_lesson(int(class_id))
    else:
        roster = models.get_roster_for_class(class_id)
    today = datetime.now().strftime("%Y-%m-%d")

    # Get today's attendance records
    checked_in = _get_attendance_map_for_today(today)

    result = []
    for entry in roster:
        sid = entry.get('student_id', '')
        att = checked_in.get(sid)
        result.append({
            'student_id': sid,
            'first_name': entry.get('first_name', ''),
            'last_name': entry.get('last_name', ''),
            'level': entry.get('level', ''),
            'checked_in': att is not None,
            'scanned_at': att.get('created_at') if att else None,
        })

    return result


def _get_attendance_map_for_today(today: str) -> Dict[str, Dict]:
    """Return {student_id: attendance_row} for all present students today."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM attendance
        WHERE session_date = ? AND status = 'present'
        """,
        (today,),
    )
    rows = cur.fetchall()
    conn.close()
    return {dict(r)['student_id']: dict(r) for r in rows}


def get_checked_in_students_today() -> List[Dict[str, Any]]:
    """Get all students who checked in (present) today, joined with student info."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.student_id, a.session_date, a.status, a.created_at,
               s.first_name, s.last_name, s.level
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.session_date = ? AND a.status = 'present'
        ORDER BY a.created_at DESC
        """,
        (today,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def match_student_name(name: str) -> Optional[str]:
    """
    Case-insensitive first_name match against students table.

    Returns:
        student_id if found, else None.
    """
    if not name:
        return None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_id FROM students WHERE LOWER(first_name) = LOWER(?) AND status = 'active' LIMIT 1",
        (name.strip(),),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None
