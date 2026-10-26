import csv
import json
import re
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, timedelta

from .db import get_connection
from .validation import (
    validate_student_id,
    validate_item_id,
    validate_name,
    validate_line_id,
    sanitize_input,
    ValidationError
)


# ---------- Helpers ----------

def _row_to_dict(row) -> Dict[str, Any]:
    """Convert sqlite3.Row to a plain dict."""
    return dict(row) if row is not None else {}


def display_name(row: Dict[str, Any],
                 first_key: str = "first_name",
                 last_key: str = "last_name") -> str:
    """Human-readable student name, tolerating NULL or missing name columns.

    dict.get(key, "") returns None when the column exists but is NULL, which
    is how "<first> None" reached the UI. Coerce both halves explicitly.
    """
    first = (row.get(first_key) or "").strip()
    last = (row.get(last_key) or "").strip()
    return f"{first} {last}".strip()


# ---------- ITEMS ----------

def get_item(item_id: str) -> Dict[str, Any]:
    """Return a single item by ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items WHERE item_id = ?", (item_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row)


def list_items() -> List[Dict[str, Any]]:
    """Return all items ordered by name."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def search_items(term: str) -> List[Dict[str, Any]]:
    """Simple search by id, name or category."""
    like = f"%{term}%"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM items
        WHERE item_id LIKE ?
           OR name LIKE ?
           OR category LIKE ?
        ORDER BY name ASC
        """,
        (like, like, like),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def add_item(
    item_id: str,
    name: str,
    category: Optional[str] = None,
    description: Optional[str] = None,
    quantity: int = 1,
    condition: str = "good",
) -> None:
    """Insert a new item with validation."""
    # Validate item_id
    valid, error = validate_item_id(item_id)
    if not valid:
        raise ValidationError(f"Invalid item ID: {error}")

    # Validate name
    valid, error = validate_name(name, "Item name")
    if not valid:
        raise ValidationError(f"Invalid item name: {error}")

    # Sanitize optional fields
    if category:
        category = sanitize_input(category, max_length=100)
    if description:
        description = sanitize_input(description, max_length=500)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO items (item_id, name, category, description, quantity, condition)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (item_id, name, category, description, quantity, condition),
    )
    conn.commit()
    conn.close()
    try:
        log_admin_action("CREATE", "item", entity_id=item_id, details=f"name={name}")
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")  # Log failures don't break the app


def update_item(
    item_id: str,
    name: str,
    category: Optional[str] = None,
    description: Optional[str] = None,
    quantity: Optional[int] = None,
    condition: Optional[str] = None,
) -> None:
    """Update an existing item. quantity and condition are left as they are unless given."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE items
        SET name = ?,
            category = ?,
            description = ?,
            quantity = COALESCE(?, quantity),
            condition = COALESCE(?, condition)
        WHERE item_id = ?
        """,
        (name, category, description, quantity, condition, item_id),
    )
    conn.commit()
    conn.close()
    try:
        log_admin_action("UPDATE", "item", entity_id=item_id, details=f"name={name}")
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")


def delete_item(item_id: str) -> None:
    """Delete an item. Refused when the item has any loan, active or returned: that history would go with it."""
    conn = get_connection()
    cur = conn.cursor()
    total, active = cur.execute(
        "SELECT COUNT(*), COALESCE(SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END), 0) "
        "FROM assignments WHERE item_id = ?",
        (item_id,),
    ).fetchone()
    if total:
        conn.close()
        raise ValidationError(
            f"Cannot delete item '{item_id}': it has loan history "
            f"({active} active and {total - active} returned loans). Deleting it would erase that history."
        )
    cur.execute("DELETE FROM items WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()
    try:
        log_admin_action("DELETE", "item", entity_id=item_id)
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")


# ---------- STUDENTS ----------

def list_students() -> List[Dict[str, Any]]:
    """Return all students ordered by last name, first name."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM students
        ORDER BY last_name ASC, first_name ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def search_students(term: str) -> List[Dict[str, Any]]:
    """Search by ID, first name, last name or level."""
    like = f"%{term}%"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM students
        WHERE student_id LIKE ?
           OR first_name LIKE ?
           OR last_name LIKE ?
           OR level LIKE ?
        ORDER BY last_name ASC, first_name ASC
        """,
        (like, like, like, like),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_student(student_id: str) -> Dict[str, Any]:
    """Return a single student by ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row)


def add_student(
    student_id: str,
    first_name: str,
    last_name: Optional[str] = None,
    level: Optional[str] = None,
    status: str = "active",
    parent_line_id: Optional[str] = None,
) -> None:
    """Insert a new student with validation."""
    # Validate student_id
    valid, error = validate_student_id(student_id)
    if not valid:
        raise ValidationError(f"Invalid student ID: {error}")

    # Validate first_name
    valid, error = validate_name(first_name, "First name")
    if not valid:
        raise ValidationError(f"Invalid first name: {error}")

    # Validate last_name if provided
    if last_name:
        valid, error = validate_name(last_name, "Last name")
        if not valid:
            raise ValidationError(f"Invalid last name: {error}")

    # Sanitize optional fields
    if level:
        level = sanitize_input(level, max_length=50)
    if parent_line_id:
        parent_line_id = sanitize_input(parent_line_id, max_length=100)
        valid, error = validate_line_id(parent_line_id)
        if not valid:
            raise ValidationError(error)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO students
            (student_id, first_name, last_name, level, status, parent_line_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (student_id, first_name, last_name, level, status, parent_line_id),
    )
    conn.commit()
    conn.close()
    try:
        log_admin_action("CREATE", "student", entity_id=student_id, details=f"name={first_name} {last_name or ''}")
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")


def update_student(
    student_id: str,
    first_name: str,
    last_name: Optional[str] = None,
    level: Optional[str] = None,
    status: Optional[str] = None,
    parent_line_id: Optional[str] = None,
) -> None:
    """Update an existing student. A value of None or "" (or only spaces) keeps what is stored, for every field: this
    function never blanks a first name, last name, level, status or LINE ID (use update_student_fields to clear one on
    purpose)."""
    if parent_line_id:
        parent_line_id = sanitize_input(parent_line_id, max_length=100)
        valid, error = validate_line_id(parent_line_id)
        if not valid:
            raise ValidationError(error)

    values = tuple((v or "").strip() or None for v in (first_name, last_name, level, status, parent_line_id))
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    cur.execute(
        """
        UPDATE students
        SET first_name = COALESCE(?, first_name),
            last_name = COALESCE(?, last_name),
            level = COALESCE(?, level),
            status = COALESCE(?, status),
            parent_line_id = COALESCE(?, parent_line_id)
        WHERE student_id = ?
        """,
        values + (student_id,),
    )
    conn.commit()
    conn.close()
    # Log what actually changed, old -> new, LINE ID masked: the same shape as update_student_fields (None kept the value)
    diff = {k: [row[k], v] for k, v in zip(_STUDENT_FIELDS, values)
            if row is not None and v is not None and (row[k] or None) != v}
    logged = {
        k: ([_mask_line_id(o), _mask_line_id(n)] if k == "parent_line_id" else [o, n])
        for k, (o, n) in diff.items()
    }
    try:
        log_admin_action("UPDATE", "student", entity_id=student_id, details=json.dumps(logged, ensure_ascii=False))
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")


STUDENT_STATUSES = ("active", "inactive")
_STUDENT_FIELDS = ("first_name", "last_name", "level", "status", "parent_line_id")


def _mask_line_id(value):
    """Log form of a parent LINE ID: only the last four characters (owner decision O4)."""
    value = (value or "").strip()
    return ("\u2026" + value[-4:]) if value else None


def update_student_fields(student_id: str, changes: Dict[str, Any]) -> Dict[str, list]:
    """Write only the fields that differ, set updated_at, and log old -> new. Returns {field: [old, new]}."""
    unknown = set(changes) - set(_STUDENT_FIELDS)
    if unknown:
        raise ValidationError(f"Unknown student field(s): {sorted(unknown)}")
    clean = {}
    for key, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
        if key == "first_name":
            if not value:
                raise ValidationError("First name is required")
        elif key == "status":
            value = (value or "").lower()
            if value not in STUDENT_STATUSES:
                raise ValidationError("Status must be 'active' or 'inactive'")
        elif key == "level":
            value = sanitize_input(value, max_length=50) or None
        elif key == "parent_line_id":
            value = sanitize_input(value, max_length=100) or None
        else:  # last_name
            value = value or None
        clean[key] = value

    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
        if row is None:
            raise ValidationError(f"Student '{student_id}' not found")
        diff = {k: [row[k], v] for k, v in clean.items() if (row[k] or None) != (v or None)}
        if not diff:
            return {}
        if diff.get("parent_line_id", [None, None])[1]:        # a LINE ID is checked only when it is changed
            valid, error = validate_line_id(diff["parent_line_id"][1])
            if not valid:
                raise ValidationError(error)
        sets = ", ".join(f"{k} = ?" for k in diff) + ", updated_at = datetime('now')"
        conn.execute(f"UPDATE students SET {sets} WHERE student_id = ?", [v[1] for v in diff.values()] + [student_id])
        conn.commit()
    finally:
        conn.close()
    logged = {
        k: ([_mask_line_id(o), _mask_line_id(n)] if k == "parent_line_id" else [o, n])
        for k, (o, n) in diff.items()
    }
    try:
        log_admin_action("UPDATE", "student", entity_id=student_id, details=json.dumps(logged, ensure_ascii=False))
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")
    return diff


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _student_id_tables(conn) -> List[str]:
    """Every table (except students) with a student_id column, found from the file itself."""
    out = []
    for (t,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall():
        if t != "students" and any(c[1] == "student_id" for c in conn.execute(f"PRAGMA table_info({_quote(t)})")):
            out.append(t)
    return out


def _rename_checked(conn, old: str, new: str):
    """Validate a rename. Returns (old, new, tables, counts_under_old). Raises ValidationError."""
    old, new = (old or "").strip(), (new or "").strip()
    valid, error = validate_student_id(new)
    if not valid:
        raise ValidationError(f"Invalid new student ID: {error}")
    if new == old:
        raise ValidationError("The new ID is the same as the old one.")
    if new.lower() == old.lower():
        raise ValidationError("Changing only the capital letters of an ID is not allowed. Use a different ID.")
    if conn.execute("SELECT 1 FROM students WHERE student_id = ?", (old,)).fetchone() is None:
        raise ValidationError(f"Student '{old}' not found.")
    if conn.execute("SELECT 1 FROM students WHERE student_id = ?", (new,)).fetchone() is not None:
        raise ValidationError(f"Student ID '{new}' already exists.")
    tables = _student_id_tables(conn)
    for t in tables:  # rows left behind by an earlier ID change must not be merged in
        n = conn.execute(f"SELECT COUNT(*) FROM {_quote(t)} WHERE student_id = ?", (new,)).fetchone()[0]
        if n:
            raise ValidationError(
                f"'{new}' already appears in {t} ({n} row(s)) although no student has that ID. "
                f"Renaming to it would attach those rows to this student."
            )
    counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {_quote(t)} WHERE student_id = ?", (old,)).fetchone()[0]
        for t in tables
    }
    return old, new, tables, counts


def _table_counts(conn) -> Dict[str, int]:
    """Row count of every table (sqlite's own tables excluded)."""
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {t: conn.execute(f"SELECT COUNT(*) FROM {_quote(t)}").fetchone()[0] for t in names}


def _fk_children_text(conn, student_id: str) -> str:
    """Which other tables still point at this student through a foreign key, e.g. 'note_ref_now.ref (1 row)'."""
    parts = []
    for (t,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
        for fk in conn.execute(f"PRAGMA foreign_key_list({_quote(t)})").fetchall():
            if fk[2] == "students":
                n = conn.execute(f"SELECT COUNT(*) FROM {_quote(t)} WHERE {_quote(fk[3])} = ?", (student_id,)).fetchone()[0]
                if n:
                    parts.append(f"{t}.{fk[3]} ({n} row(s))")
    return ", ".join(parts)


def rename_logged(old: str, new: str) -> bool:
    """True if admin_logs holds a RENAME row for exactly old -> new (a rename done by this portal)."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT details FROM admin_logs WHERE action = 'RENAME'").fetchall()
    finally:
        conn.close()
    for (details,) in rows:
        try:
            d = json.loads(details or "")
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("old") == old and d.get("new") == new:
            return True
    return False


def preview_rename(old: str, new: str) -> Dict[str, int]:
    """Read-only: validate a rename and return {table: rows} that would move. Raises ValidationError."""
    conn = get_connection()
    try:
        return _rename_checked(conn, old, new)[3]
    finally:
        conn.close()


def rename_student(old: str, new: str) -> Dict[str, Any]:
    """Change a student's ID in one transaction (foreign keys ON). Everything keyed to the old ID moves.

    Any error, or any row left under the old ID, rolls everything back. Returns
    {"old", "new", "tables": {table: rows moved}, "qr_code": the stored QR text, copied across unchanged}.
    """
    _ensure_admin_logs_table()  # before BEGIN: it opens its own connection
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        old, new, tables, _ = _rename_checked(conn, old, new)
        breaks_before = {tuple(r) for r in conn.execute("PRAGMA foreign_key_check")}
        counts_before = _table_counts(conn)
        row = conn.execute("SELECT * FROM students WHERE student_id = ?", (old,)).fetchone()
        cols = row.keys()
        old_qr = row["qr_code"] if "qr_code" in cols else None
        # qr_code is UNIQUE: the copy starts without it and receives it after the old row is gone
        values = [new if c == "student_id" else None if c == "qr_code" else row[c] for c in cols]
        conn.execute(
            f"INSERT INTO students ({', '.join(_quote(c) for c in cols)}) VALUES ({', '.join('?' * len(cols))})",
            values,
        )
        moved = {}
        for t in tables:
            moved[t] = conn.execute(
                f"UPDATE {_quote(t)} SET student_id = ? WHERE student_id = ?", (new, old)
            ).rowcount
        conn.execute("DELETE FROM students WHERE student_id = ?", (old,))
        if old_qr is not None:
            conn.execute("UPDATE students SET qr_code = ? WHERE student_id = ?", (old_qr, new))
        new_breaks = {tuple(r) for r in conn.execute("PRAGMA foreign_key_check")} - breaks_before
        if new_breaks:
            raise ValidationError(
                f"Rename refused: it would create {len(new_breaks)} new broken link(s), e.g. {next(iter(new_breaks))}.")
        for t in tables:
            n = conn.execute(f"SELECT COUNT(*) FROM {_quote(t)} WHERE student_id = ?", (old,)).fetchone()[0]
            if n:
                raise ValidationError(f"Rename refused: {n} row(s) would be left under '{old}' in {t}.")
        counts_after = _table_counts(conn)
        for t, n_before in counts_before.items():
            if counts_after.get(t) != n_before:
                raise ValidationError(
                    f"Rename refused: {t} changed from {n_before} to {counts_after.get(t)} row(s), which a rename must not do "
                    f"(a trigger or another rule touched it). Nothing was changed.")
        # The log row is part of the rename: the re-run gate (rename_logged) must never depend on a later write.
        try:
            conn.execute(
                "INSERT INTO admin_logs (action, entity_type, entity_id, details, status) VALUES (?, ?, ?, ?, ?)",
                ("RENAME", "student", new,
                 json.dumps({"old": old, "new": new, "tables": {t: n for t, n in moved.items() if n}}), "success"))
        except sqlite3.Error as e:
            raise ValidationError(
                f"Rename refused: its log row could not be written ({e}). Nothing was changed.") from e
        conn.commit()
    except ValidationError:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as e:
        children = _fk_children_text(conn, old)
        conn.rollback()
        if "FOREIGN KEY" in str(e):
            raise ValidationError(
                f"Rename refused: another table still points at '{old}' and would break"
                f"{': ' + children if children else ''}. Nothing was changed.") from e
        raise ValidationError(f"Rename refused by the database: {e}. Nothing was changed.") from e
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"old": old, "new": new, "tables": moved, "qr_code": old_qr}


# Tables whose rows BLOCK a student delete, and what to call them in the refusal. Any other table with a foreign key to
# students that has no ON DELETE action blocks it too (the database would refuse anyway).
_DELETE_BLOCKERS = {"assignments": ("loan", "loans"), "extra_lesson_student": ("extra lesson", "extra lessons")}


def delete_student_preview(student_id: str) -> Dict[str, Any]:
    """Read-only: what deleting this student would do. Raises ValidationError if there is no such student.

    Returns {"student_id", "name", "refused": None | message, "deleted_with": {table: rows}, "left_behind": {table: rows},
    "line_id_tail": the masked parent LINE ID ("..." + last 4) or None}.
    refused is set when the student has any loan (active or returned) or is in an extra lesson: that is checked
    before anything else. deleted_with are the tables that follow the student (ON DELETE CASCADE), left_behind the
    tables that keep their rows under the old ID (no foreign key, so the delete does not touch them).
    """
    conn = get_connection()
    try:
        st = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
        if st is None:
            raise ValidationError(f"Student '{student_id}' not found")
        name = display_name(dict(st))
        line_id_tail = _mask_line_id(st["parent_line_id"])     # the masked form only: never the full ID (O4)
        blocking, deleted_with, left_behind = {}, {}, {}
        for t in _student_id_tables(conn):
            n = conn.execute(f"SELECT COUNT(*) FROM {_quote(t)} WHERE student_id = ?", (student_id,)).fetchone()[0]
            rule = None
            for fk in conn.execute(f"PRAGMA foreign_key_list({_quote(t)})").fetchall():
                if fk[2] == "students" and fk[3] == "student_id":
                    rule = (fk[6] or "NO ACTION").upper()
            if t in _DELETE_BLOCKERS or rule in ("NO ACTION", "RESTRICT"):
                if n:
                    blocking[t] = n
            elif rule == "CASCADE":
                deleted_with[t] = n
            else:                                              # no foreign key (or SET NULL): the rows stay behind
                left_behind[t] = n
    finally:
        conn.close()
    refused = None
    if blocking:
        what = []
        for t, n in blocking.items():
            one, many = _DELETE_BLOCKERS.get(t, (t, t))
            what.append(f"{n} {one if n == 1 else many}")
        refused = (f"{name} ({student_id}) has {' and '.join(what)}, so the student cannot be deleted: "
                   "deleting would erase that history (or the database would refuse).\n\n"
                   "To stop using the student, set the Status to inactive in Edit Student.")
    return {"student_id": student_id, "name": name, "refused": refused,
            "deleted_with": deleted_with, "left_behind": left_behind, "line_id_tail": line_id_tail}


def delete_student(student_id: str) -> None:
    """Delete a student. Refused with a clear ValidationError, before anything is changed, if the student has any
    loan (active or returned) or an extra lesson. Class places, overrides and C-Test copies go with the student;
    attendance marks, QR scans and other rows without a foreign key stay behind under the old ID."""
    plan = delete_student_preview(student_id)
    if plan["refused"]:
        raise ValidationError(plan["refused"])
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()
    try:
        left = {t: n for t, n in plan["left_behind"].items() if n}
        log_admin_action("DELETE", "student", entity_id=student_id,
                         details=json.dumps({"name": plan["name"], "left_behind": left}, ensure_ascii=False))
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")


# ---------- ASSIGNMENTS (who has what) ----------

def assign_item_to_student(
    item_id: str,
    student_id: str,
    notes: Optional[str] = None,
) -> int:
    """
    Create an 'assigned' record.
    Returns the new assignment_id.
    Refused (ValidationError, nothing written) if the student is inactive, or if the item already has an open loan:
    every lending path goes through here.
    """
    conn = get_connection()
    cur = conn.cursor()
    st = cur.execute("SELECT status FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if st and (st[0] or "").strip().lower() == "inactive":
        conn.close()
        raise ValidationError(f"Student '{student_id}' is inactive, so the book was not lent. "
                              "Set the Status to active in Edit Student first.")
    open_loan = cur.execute("SELECT assigned_date FROM assignments WHERE item_id = ? AND status = 'assigned' "
                            "ORDER BY assigned_date DESC LIMIT 1", (item_id,)).fetchone()
    if open_loan:
        conn.close()
        raise ValidationError(f"Book '{item_id}' is already lent out (since {(open_loan[0] or '')[:10]}). "
                              "It must come back before it can go out again.")
    cur.execute(
        """
        INSERT INTO assignments (item_id, student_id, status, notes)
        VALUES (?, ?, 'assigned', ?)
        """,
        (item_id, student_id, notes),
    )
    assignment_id = cur.lastrowid
    conn.commit()
    conn.close()
    try:
        log_admin_action("ASSIGN", "assignment", entity_id=str(assignment_id), details=f"item={item_id}, student={student_id}")
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")
    return assignment_id


def mark_assignment_returned(
    assignment_id: int,
    notes: Optional[str] = None,
) -> None:
    """Mark an assignment as 'returned'."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE assignments
        SET status = 'returned',
            returned_date = CURRENT_TIMESTAMP,
            notes = COALESCE(?, notes)
        WHERE assignment_id = ?
        """,
        (notes, assignment_id),
    )
    conn.commit()
    conn.close()
    try:
        log_admin_action("RETURN", "assignment", entity_id=str(assignment_id))
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")


def get_assignment(assignment_id: int) -> Dict[str, Any]:
    """Return a single assignment by id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM assignments WHERE assignment_id = ?", (assignment_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row)


def get_active_assignments_for_item(item_id: str) -> List[Dict[str, Any]]:
    """Assignments for an item that are still 'assigned'."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.*, s.first_name, s.last_name
        FROM assignments a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.item_id = ? AND a.status = 'assigned'
        ORDER BY a.assigned_date DESC
        """,
        (item_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_all_assignments() -> List[Dict[str, Any]]:
    """All assignments (history), newest first."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.*,
               i.name AS item_name,
               s.first_name AS student_first_name,
               s.last_name AS student_last_name
        FROM assignments a
        JOIN items i     ON a.item_id = i.item_id
        JOIN students s  ON a.student_id = s.student_id
        ORDER BY a.assigned_date DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------- ATTENDANCE ----------

def _ensure_attendance_table() -> None:
    """Create attendance table if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id      TEXT NOT NULL,
            session_date    TEXT NOT NULL,
            status          TEXT CHECK(status IN ('present','absent')) NOT NULL,
            notes           TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT,
            UNIQUE(student_id, session_date),
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
        """
    )
    conn.commit()
    conn.close()


def parse_session_date(text):
    """The ONE check for a date the attendance code accepts: a real calendar date written exactly YYYY-MM-DD.

    Returns a datetime.date. Raises ValueError for anything else, including '20261005', '2026-10-5' and
    '2026-10-05T09:00', which datetime.fromisoformat would accept.
    """
    from datetime import datetime as _datetime
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError(f"'{text}' is not a valid date (expected YYYY-MM-DD).")
    try:
        return _datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"'{text}' is not a valid date (expected YYYY-MM-DD).") from None


def _check_session_date(session_date) -> str:
    """Raise ValidationError unless session_date passes parse_session_date; returns it."""
    try:
        parse_session_date(session_date)
    except ValueError as e:
        raise ValidationError(str(e)) from None
    return session_date


def mark_attendance(
    student_id: str,
    session_date: Optional[str] = None,
    status: str = "present",
    notes: Optional[str] = None,
) -> None:
    """
    Mark a student as present/absent for a given date.
    If a record already exists for that student+date, it's updated.
    """
    _ensure_attendance_table()

    if session_date is None:
        session_date = date.today().isoformat()
    _check_session_date(session_date)
    student_id = str(student_id)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO attendance (student_id, session_date, status, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(student_id, session_date) DO UPDATE SET
            status = excluded.status,
            notes  = excluded.notes
        """,
        (student_id, session_date, status, notes),
    )
    conn.commit()
    conn.close()


def set_attendance_status(student_id: str, session_date: str, status: str) -> None:
    """Quick mark: upsert status only. Notes, scanned_at and every other column are left alone.
    (The live attendance table has no updated_at, so none is written.)"""
    if status not in ("present", "absent"):
        raise ValidationError(f"Attendance status must be 'present' or 'absent', not {status!r}")
    _check_session_date(session_date)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO attendance (student_id, session_date, status) VALUES (?, ?, ?)
            ON CONFLICT(student_id, session_date) DO UPDATE SET status = excluded.status
            """,
            (str(student_id), session_date, status),
        )
        conn.commit()
    finally:
        conn.close()


def get_marks_for_date(session_date: str) -> Dict[str, Dict[str, Any]]:
    """Every mark saved for a date, as {student_id: {"status", "notes"}}. No join: a mark whose student_id has no
    student row is included too."""
    conn = get_connection()
    try:
        return {r["student_id"]: {"status": r["status"], "notes": r["notes"]}
                for r in conn.execute("SELECT student_id, status, notes FROM attendance WHERE session_date = ? "
                                      "ORDER BY student_id", (session_date,))}
    finally:
        conn.close()


def get_latest_marks() -> Dict[str, Dict[str, Any]]:
    """Each student's newest mark, as {student_id: {"status", "session_date"}}."""
    conn = get_connection()
    try:
        return {r["student_id"]: {"status": r["status"], "session_date": r["session_date"]}
                for r in conn.execute(
                    "SELECT a.student_id, a.status, a.session_date FROM attendance a "
                    "WHERE a.session_date = (SELECT MAX(b.session_date) FROM attendance b WHERE b.student_id = a.student_id)")}
    finally:
        conn.close()


def toggle_attendance_status(student_id: str, session_date: str) -> str:
    """Space: flip the mark saved for this student on this date, read from the database now, never from what a row
    on screen says. present -> absent; absent or no mark -> present. Returns the new status. Notes and every other
    column are left alone. Raises ValidationError for a date that is not YYYY-MM-DD."""
    _check_session_date(session_date)
    student_id = str(student_id)
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT status FROM attendance WHERE student_id = ? AND session_date = ?",
                           (student_id, session_date)).fetchone()
        new_status = "absent" if row is not None and row["status"] == "present" else "present"
        conn.execute(
            """
            INSERT INTO attendance (student_id, session_date, status) VALUES (?, ?, ?)
            ON CONFLICT(student_id, session_date) DO UPDATE SET status = excluded.status
            """,
            (student_id, session_date, new_status),
        )
        conn.commit()
        return new_status
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def clear_attendance(student_id: str, session_date: str) -> bool:
    """Delete one attendance mark and log the old status and whether a note existed (never the note text).
    Returns False, and logs nothing, if there was no mark."""
    _check_session_date(session_date)
    student_id = str(student_id)
    conn = get_connection()
    try:
        row = conn.execute("SELECT status, notes FROM attendance WHERE student_id = ? AND session_date = ?",
                           (student_id, session_date)).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM attendance WHERE student_id = ? AND session_date = ?", (student_id, session_date))
        conn.commit()
    finally:
        conn.close()
    try:
        log_admin_action("CLEAR_MARK", "attendance", entity_id=student_id, details=json.dumps(
            {"session_date": session_date, "status": row["status"], "note_existed": bool((row["notes"] or "").strip())}))
    except (sqlite3.Error, OSError) as e:
        print(f"Warning: Failed to log admin action: {e}")
    return True


def get_attendance_for_date(session_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return attendance records for a given date, joined with student info.
    Only returns students that have some attendance entry for that date.
    """
    _ensure_attendance_table()

    if session_date is None:
        session_date = date.today().isoformat()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.*,
               s.first_name,
               s.last_name,
               s.level,
               s.status AS student_status
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.session_date = ?
        ORDER BY s.last_name, s.first_name
        """,
        (session_date,),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_roster_with_attendance(class_id: str, session_date: str = None) -> list:
    """
    Get all active enrolled students for a class, with their attendance
    status for the given date (defaults to today).
    Returns list of dicts: student_id, first_name, last_name, level, status, notes
    status is None when there is no attendance record for that date (not marked); it is never invented.
    """
    if session_date is None:
        from datetime import date as _date
        session_date = _date.today().isoformat()

    conn = get_connection()
    try:
        if class_id.startswith("extra:"):
            extra_id = int(class_id.split(":")[1])
            rows = conn.execute("""
                SELECT
                    s.student_id,
                    s.first_name,
                    s.last_name,
                    s.level,
                    a.status AS status,
                    a.notes
                FROM extra_lesson_student els
                JOIN students s ON els.student_id = s.student_id
                LEFT JOIN attendance a
                    ON a.student_id = s.student_id
                    AND a.session_date = ?
                WHERE els.extra_lesson_id = ?
                  AND s.status = 'active'
                ORDER BY s.last_name, s.first_name
            """, (session_date, extra_id)).fetchall()
        else:
            rows = conn.execute("""
                SELECT
                    s.student_id,
                    s.first_name,
                    s.last_name,
                    s.level,
                    a.status AS status,
                    a.notes
                FROM class_roster cr
                JOIN students s ON s.student_id = cr.student_id
                LEFT JOIN attendance a
                    ON a.student_id = s.student_id
                    AND a.session_date = ?
                WHERE cr.class_id = ?
                  AND cr.removed_at IS NULL
                  AND s.status = 'active'
                ORDER BY s.last_name, s.first_name
            """, (session_date, class_id)).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_day_roster(session_date: str) -> Dict[str, Any]:
    """The day's classes and their students, each with that date's mark. The Attendance tab and the export both use it.

    Same rules as Load Schedule: the active weekly classes for that weekday minus any cancelled that date, plus that
    date's extra lessons; each class's active roster with its mark (status None = not marked). A student who is in
    two of the day's classes is listed once, under the first.

    Returns {"classes": [(class_id, label)], "students": [{student_id, first_name, last_name, level, status, notes}],
    "empty_classes": [label of a class with no students], "duplicates": [student_id listed in more than one class]}.
    Raises ValueError if session_date is not YYYY-MM-DD (parse_session_date).
    """
    session_dt = parse_session_date(session_date)
    classes = []
    for cls in get_classes_for_day_of_week(session_dt.weekday()):
        if is_class_cancelled(cls["class_id"], session_dt):
            continue
        classes.append((cls["class_id"], f"{cls['class_name']} ({cls['start_time']})"))
    for el in get_extra_lessons_for_date(session_date):
        classes.append((f"extra:{el['id']}", f"Extra: {el['label']} ({el['start_time']}\u2013{el['end_time']})"))
    students, empty_classes, duplicates, seen = [], [], [], set()
    for class_id, label in classes:
        roster = get_roster_with_attendance(class_id, session_date)
        if not roster:
            empty_classes.append(label)
            continue
        for st in roster:
            if st["student_id"] in seen:
                if st["student_id"] not in duplicates:
                    duplicates.append(st["student_id"])
                continue
            seen.add(st["student_id"])
            students.append(st)
    return {"classes": classes, "students": students, "empty_classes": empty_classes, "duplicates": duplicates}


def get_classes_for_day_of_week(day_of_week: int) -> list:
    """
    Get all active classes for a given day of the week (0=Mon, 6=Sun).
    Returns list of dicts with class_id, class_name, start_time, end_time, level, teacher.
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT class_id, class_name, start_time, end_time, level, teacher
            FROM class_def
            WHERE day_of_week = ? AND is_active = 1
            ORDER BY start_time
        """, (day_of_week,)).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_attendance_for_student(student_id: str) -> List[Dict[str, Any]]:
    """All attendance records for one student, newest first."""
    _ensure_attendance_table()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.*, s.first_name, s.last_name, s.level
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.student_id = ?
        ORDER BY a.session_date DESC
        """,
        (student_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------- CSV EXPORT HELPERS ----------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EXPORTS_DIR = DATA_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def export_items_to_csv(csv_path: Optional[str] = None) -> str:
    """
    Export all items to a CSV file.
    Returns the path to the CSV file as a string.
    """
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if csv_path is None:
        today_str = date.today().isoformat()
        csv_file = EXPORTS_DIR / f"items_{today_str}.csv"
    else:
        csv_file = Path(csv_path)

    conn = get_connection()
    cur = conn.cursor()
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "name", "category", "description", "quantity", "condition"])
        for row in cur.execute(
            """
            SELECT item_id, name, category, description, quantity, condition
            FROM items
            ORDER BY name ASC
            """
        ):
            writer.writerow(row)

    conn.close()
    return str(csv_file)


def export_students_to_csv(csv_path: Optional[str] = None, include_line_id: bool = True) -> str:
    """
    Export all students to a CSV file.
    include_line_id=False leaves the parent_line_id column out (Backup Now, D1).
    """
    columns = ["student_id", "first_name", "last_name", "level", "status"] + (["parent_line_id"] if include_line_id else [])
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if csv_path is None:
        today_str = date.today().isoformat()
        csv_file = EXPORTS_DIR / f"students_{today_str}.csv"
    else:
        csv_file = Path(csv_path)

    conn = get_connection()
    cur = conn.cursor()
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in cur.execute(
            f"""
            SELECT {", ".join(columns)}
            FROM students
            ORDER BY last_name, first_name
            """
        ):
            writer.writerow(row)

    conn.close()
    return str(csv_file)


def export_assignments_to_csv(csv_path: Optional[str] = None) -> str:
    """
    Export all assignments (with item & student names) to a CSV file.
    Returns the path to the CSV file as a string.
    """
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if csv_path is None:
        today_str = date.today().isoformat()
        csv_file = EXPORTS_DIR / f"assignments_{today_str}.csv"
    else:
        csv_file = Path(csv_path)

    conn = get_connection()
    cur = conn.cursor()
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "assignment_id",
                "item_id",
                "item_name",
                "student_id",
                "student_first_name",
                "student_last_name",
                "status",
                "assigned_date",
                "returned_date",
                "notes",
            ]
        )
        for row in cur.execute(
            """
            SELECT a.assignment_id,
                   a.item_id,
                   i.name AS item_name,
                   a.student_id,
                   s.first_name,
                   s.last_name,
                   a.status,
                   a.assigned_date,
                   a.returned_date,
                   a.notes
            FROM assignments a
            JOIN items i   ON a.item_id = i.item_id
            JOIN students s ON a.student_id = s.student_id
            ORDER BY a.assigned_date DESC
            """
        ):
            writer.writerow(row)

    conn.close()
    return str(csv_file)


def export_attendance_to_csv(
    session_date: Optional[str] = None,
    csv_path: Optional[str] = None,
) -> str:
    """
    Export one date's attendance to a CSV of student IDs only (no names, no level, no notes: owner decision O12).

    Columns: attendance_id, student_id, session_date, status, student_check. Every saved mark for the date is
    included, ordered by student_id; a mark whose student_id has no student row has student_check "no current
    student". The day's roster students with no mark are added with status "not marked" and an empty attendance_id.
    Without csv_path the file is exports\\attendance_<date>_<HHMMSS>.csv, and never overwrites an earlier one.
    """
    from datetime import datetime as _datetime
    _ensure_attendance_table()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if session_date is None:
        session_date = date.today().isoformat()
    _check_session_date(session_date)           # before anything is created, whatever file name was given
    roster = get_day_roster(session_date)

    if csv_path is None:
        stamp = _datetime.now().strftime("%H%M%S")
        csv_file = EXPORTS_DIR / f"attendance_{session_date}_{stamp}.csv"
        n = 2
        while csv_file.exists():
            csv_file = EXPORTS_DIR / f"attendance_{session_date}_{stamp}-{n}.csv"
            n += 1
    else:
        csv_file = Path(csv_path)

    conn = get_connection()
    try:
        marked = conn.execute(
            """
            SELECT a.attendance_id, a.student_id, a.session_date, a.status,
                   CASE WHEN NOT EXISTS (SELECT 1 FROM students s WHERE s.student_id = a.student_id)
                        THEN 'no current student' ELSE '' END AS student_check
            FROM attendance a
            WHERE a.session_date = ?
            ORDER BY a.student_id
            """,
            (session_date,),
        ).fetchall()
    finally:
        conn.close()
    lines = [tuple(r) for r in marked]
    lines += [("", st["student_id"], session_date, "not marked", "")
              for st in roster["students"] if st["status"] is None]
    lines.sort(key=lambda row: row[1])

    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["attendance_id", "student_id", "session_date", "status", "student_check"])
        writer.writerows(lines)
    return str(csv_file)


# ---------- QR SCAN LOGS (for Logs tab) ----------

def _ensure_qr_scans_table() -> None:
    """Create qr_scans table if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS qr_scans (
            scan_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_code      TEXT NOT NULL,
            student_id   TEXT,
            item_id      TEXT,
            scan_context TEXT,
            timestamp    TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (item_id)   REFERENCES items(item_id)
        )
        """
    )
    conn.commit()
    conn.close()


def log_qr_scan(
    qr_code: str,
    student_id: Optional[str] = None,
    item_id: Optional[str] = None,
    scan_context: Optional[str] = None,
) -> int:
    """
    Insert a record into qr_scans.
    Returns the new scan_id.
    """
    _ensure_qr_scans_table()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO qr_scans (qr_code, student_id, item_id, scan_context)
        VALUES (?, ?, ?, ?)
        """,
        (qr_code, student_id, item_id, scan_context),
    )
    scan_id = cur.lastrowid
    conn.commit()
    conn.close()
    return scan_id


def list_qr_scans(limit: int = 500) -> List[Dict[str, Any]]:
    """
    Return latest QR scans, joined with student and item names.
    """
    _ensure_qr_scans_table()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.*,
               s.first_name AS student_first_name,
               s.last_name AS student_last_name,
               i.name       AS item_name
        FROM qr_scans q
        LEFT JOIN students s ON q.student_id = s.student_id
        LEFT JOIN items    i ON q.item_id   = i.item_id
        ORDER BY q.timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def search_qr_scans(term: str, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Search QR scans by qr_code, student name, item name, or scan_context.
    """
    _ensure_qr_scans_table()

    like = f"%{term}%"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.*,
               s.first_name AS student_first_name,
               s.last_name AS student_last_name,
               i.name       AS item_name
        FROM qr_scans q
        LEFT JOIN students s ON q.student_id = s.student_id
        LEFT JOIN items    i ON q.item_id   = i.item_id
        WHERE q.qr_code LIKE ?
           OR COALESCE(s.first_name,'') || ' ' || COALESCE(s.last_name,'') LIKE ?
           OR COALESCE(i.name,'') LIKE ?
           OR COALESCE(q.scan_context,'') LIKE ?
        ORDER BY q.timestamp DESC
        LIMIT ?
        """,
        (like, like, like, like, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------- ADMIN ACTION LOGS ----------

def _ensure_admin_logs_table() -> None:
    """Create admin_logs table if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_logs (
            log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT DEFAULT CURRENT_TIMESTAMP,
            action       TEXT NOT NULL,
            entity_type  TEXT NOT NULL,
            entity_id    TEXT,
            details      TEXT,
            status       TEXT DEFAULT 'success'
        )
        """
    )
    conn.commit()
    conn.close()


def log_admin_action(
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[str] = None,
    status: str = "success",
) -> int:
    """
    Log an admin action to the audit log.
    Returns the log_id.
    """
    _ensure_admin_logs_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO admin_logs (action, entity_type, entity_id, details, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (action, entity_type, entity_id, details, status),
    )
    log_id = cur.lastrowid
    conn.commit()
    conn.close()
    return log_id


def list_admin_logs(limit: int = 500) -> List[Dict[str, Any]]:
    """Return latest admin action logs."""
    _ensure_admin_logs_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM admin_logs
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def search_admin_logs(term: str, limit: int = 500) -> List[Dict[str, Any]]:
    """Search admin logs by action, entity_type, entity_id, or details."""
    _ensure_admin_logs_table()
    like = f"%{term}%"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM admin_logs
        WHERE action LIKE ?
           OR entity_type LIKE ?
           OR entity_id LIKE ?
           OR details LIKE ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (like, like, like, like, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------- CLASS ROSTER ----------

def _ensure_class_tables() -> None:
    """Create class_def and class_roster tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS class_def (
            class_id TEXT PRIMARY KEY,
            class_name TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            level TEXT,
            teacher TEXT DEFAULT 'David',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS class_roster (
            roster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            enrolled_at TEXT DEFAULT (datetime('now')),
            removed_at TEXT,
            FOREIGN KEY (class_id) REFERENCES class_def(class_id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            UNIQUE(class_id, student_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_class_def_day ON class_def(day_of_week)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_class_def_active ON class_def(is_active)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_class_roster_class ON class_roster(class_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_class_roster_student ON class_roster(student_id)")
    conn.commit()
    conn.close()


def list_class_defs(active_only: bool = True) -> List[Dict[str, Any]]:
    """Return all class definitions ordered by day_of_week, start_time."""
    _ensure_class_tables()
    conn = get_connection()
    cur = conn.cursor()
    if active_only:
        cur.execute(
            "SELECT * FROM class_def WHERE is_active = 1 ORDER BY day_of_week, start_time"
        )
    else:
        cur.execute("SELECT * FROM class_def ORDER BY day_of_week, start_time")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_class_def(class_id: str) -> Dict[str, Any]:
    """Return a single class definition by ID."""
    _ensure_class_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM class_def WHERE class_id = ?", (class_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row)


def add_class_def(
    class_id: str,
    class_name: str,
    day_of_week: int,
    start_time: str,
    end_time: str,
    level: Optional[str] = None,
    teacher: str = "David",
) -> None:
    """Insert a new class definition."""
    _ensure_class_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO class_def (class_id, class_name, day_of_week, start_time, end_time, level, teacher)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (class_id, class_name, day_of_week, start_time, end_time, level, teacher),
    )
    conn.commit()
    conn.close()
    try:
        log_admin_action("CREATE", "class_def", entity_id=class_id, details=f"name={class_name}, day={day_of_week}")
    except Exception as e:
        print(f"Warning: Failed to log admin action: {e}")


# ---------- SCHEDULE (level-coded classes) ----------
# class_id is "{level_code}-{NN}" and never encodes day or time, so a class keeps its ID when rescheduled.

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def list_class_levels(active_only: bool = True) -> List[Dict[str, Any]]:
    """Return class_level rows in display order."""
    conn = get_connection()
    cur = conn.cursor()
    if active_only:
        cur.execute("SELECT * FROM class_level WHERE is_active = 1 ORDER BY sort_order")
    else:
        cur.execute("SELECT * FROM class_level ORDER BY sort_order")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def check_class_times(start_time: str, end_time: str) -> None:
    """Raise ValidationError unless both times are zero-padded HH:MM and end is after start."""
    # Zone B's get_class_for_now() int-parses these outside its error handling, and roster_bridge compares them as strings.
    for value, name in ((start_time, "Start time"), (end_time, "End time")):
        if not isinstance(value, str) or not _HHMM_RE.match(value):
            raise ValidationError(f"{name} must be HH:MM with a leading zero (e.g. 09:00), got {value!r}")
    if end_time <= start_time:
        raise ValidationError(f"End time {end_time} must be after start time {start_time}")


def _validate_schedule_fields(cur, level_code: str, day_of_week: int, start_time: str, end_time: str) -> str:
    """Raise ValidationError on bad input; return the level_name for level_code."""
    row = cur.execute("SELECT level_name FROM class_level WHERE level_code = ?", (level_code,)).fetchone()
    if row is None:
        raise ValidationError(f"Unknown level: {level_code!r}")
    if isinstance(day_of_week, bool) or not isinstance(day_of_week, int) or not 0 <= day_of_week <= 6:
        raise ValidationError(f"Day must be 0 (Monday) to 6 (Sunday), got {day_of_week!r}")
    check_class_times(start_time, end_time)
    return row[0]


def list_classes_with_counts(active_only: bool = True) -> List[Dict[str, Any]]:
    """Return class_def rows plus student_count (size of the active roster)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT cd.*,
               (SELECT COUNT(*) FROM class_roster cr
                WHERE cr.class_id = cd.class_id AND cr.removed_at IS NULL) AS student_count
        FROM class_def cd
        {"WHERE cd.is_active = 1" if active_only else ""}
        ORDER BY cd.day_of_week, cd.start_time
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def find_clashes(
    day_of_week: int,
    start_time: str,
    end_time: str,
    exclude_class_id: Optional[str] = None,
    include_legacy: bool = False,
) -> List[Dict[str, Any]]:
    """Active classes on the same day whose time overlaps start_time-end_time.

    Times are compared as minutes since midnight, so an old-style '9:00' equals '09:00'. A compared class whose
    time cannot be read is refused by name rather than guessed at.
    """
    check_class_times(start_time, end_time)
    start, end = _minutes(start_time), _minutes(end_time)
    clashes = []
    for c in list_classes_with_counts():
        if (c["day_of_week"] != day_of_week or c["class_id"] == exclude_class_id
                or (is_legacy_class(c) and not include_legacy)):
            continue
        c_start, c_end = _minutes(c["start_time"]), _minutes(c["end_time"])
        if c_start is None or c_end is None:
            note = (" This is an old-style class, and its time cannot be edited in the portal, so it needs a data fix."
                    if is_legacy_class(c) else "")
            raise ValidationError(
                f"Cannot check for clashes: class {c['class_id']} has a time that cannot be read "
                f"({c['start_time']!r}-{c['end_time']!r}). Fix that class's time first.{note}")
        if c_start < end and start < c_end:
            clashes.append(c)
    return clashes


def _next_class_id(cur, level_code: str) -> str:
    # Scans inactive rows too, so a deactivated class's ID is never handed out again.
    pattern = re.compile(rf"^{re.escape(level_code)}-(\d+)$")
    cur.execute("SELECT class_id FROM class_def WHERE class_id LIKE ?", (f"{level_code}-%",))
    used = [int(m.group(1)) for r in cur.fetchall() if (m := pattern.match(r[0]))]
    return f"{level_code}-{max(used, default=0) + 1:02d}"


def next_class_id(level_code: str) -> str:
    """Return the class_id create_class would assign next for this level."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if cur.execute("SELECT 1 FROM class_level WHERE level_code = ?", (level_code,)).fetchone() is None:
            raise ValidationError(f"Unknown level: {level_code!r}")
        return _next_class_id(cur, level_code)
    finally:
        conn.close()


def _auto_class_name(label: Optional[str], level_name: str, class_id: str) -> str:
    label = (label or "").strip()
    return label or f"{level_name} ({class_id})"


def _reconcile_roster(cur, class_id: str, student_ids) -> Dict[str, List[str]]:
    wanted = list(dict.fromkeys(student_ids))
    wanted_set = set(wanted)
    cur.execute("SELECT student_id, removed_at FROM class_roster WHERE class_id = ?", (class_id,))
    existing = {r["student_id"]: r["removed_at"] for r in cur.fetchall()}

    result = {"added": [], "reenrolled": [], "removed": []}
    for sid, removed_at in existing.items():
        if removed_at is None and sid not in wanted_set:
            cur.execute(
                "UPDATE class_roster SET removed_at = datetime('now') WHERE class_id = ? AND student_id = ?",
                (class_id, sid),
            )
            result["removed"].append(sid)
    for sid in wanted:
        if sid not in existing:
            cur.execute("INSERT INTO class_roster (class_id, student_id) VALUES (?, ?)", (class_id, sid))
            result["added"].append(sid)
        elif existing[sid] is not None:
            # UNIQUE(class_id, student_id) allows one row per pair, so re-enrolling reuses the removed row.
            cur.execute(
                "UPDATE class_roster SET removed_at = NULL, enrolled_at = datetime('now') "
                "WHERE class_id = ? AND student_id = ?",
                (class_id, sid),
            )
            result["reenrolled"].append(sid)
    return result


def create_class(
    level_code: str,
    day_of_week: int,
    start_time: str,
    end_time: str,
    label: Optional[str] = None,
    student_ids=(),
    teacher: str = "David",
) -> str:
    """Create a class and its roster in one transaction. Returns the generated class_id."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        level_name = _validate_schedule_fields(cur, level_code, day_of_week, start_time, end_time)
        class_id = _next_class_id(cur, level_code)
        cur.execute(
            """
            INSERT INTO class_def (class_id, class_name, day_of_week, start_time, end_time, level, teacher)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (class_id, _auto_class_name(label, level_name, class_id), day_of_week, start_time, end_time,
             level_code, (teacher or "").strip() or "David"),
        )
        roster = _reconcile_roster(cur, class_id, student_ids)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    try:
        log_admin_action("CREATE", "class_def", entity_id=class_id,
                         details=f"level={level_code}, day={day_of_week}, {start_time}-{end_time}, "
                                 f"students={roster['added']}")
    except Exception as e:
        print(f"Warning: Failed to log admin action: {e}")
    return class_id


def is_legacy_class(cls) -> bool:
    """True for rows not created through the schedule form (class_id not '{level}-NN')."""
    level = cls["level"] or ""
    return not (level and re.fullmatch(rf"{re.escape(level)}-\d+", cls["class_id"] or ""))


# Standalone class types are not tiers: a class of one never moves up a level, and nothing moves up into one.
STANDALONE_LEVELS = frozenset({"WRITE", "READ", "PRE"})


def can_move_up(cls) -> bool:
    """True if promote_class may be used on this class."""
    return not is_legacy_class(cls) and cls["level"] not in STANDALONE_LEVELS


def update_class(
    class_id: str,
    day_of_week: int,
    start_time: str,
    end_time: str,
    label: Optional[str] = None,
    teacher: Optional[str] = None,
    student_ids=None,
) -> None:
    """Update day, time, label, teacher and (if given) the roster in one transaction; class_id and level never change."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        old = cur.execute("SELECT * FROM class_def WHERE class_id = ?", (class_id,)).fetchone()
        if old is None:
            raise ValidationError(f"No class with ID {class_id!r}")
        if is_legacy_class(old):
            raise ValidationError(f"{class_id!r} is an old-style class and cannot be edited")
        level_name = _validate_schedule_fields(cur, old["level"], day_of_week, start_time, end_time)
        new_teacher = (teacher or "").strip() or old["teacher"]
        cur.execute(
            """
            UPDATE class_def
            SET class_name = ?, day_of_week = ?, start_time = ?, end_time = ?, teacher = ?,
                updated_at = datetime('now')
            WHERE class_id = ?
            """,
            (_auto_class_name(label, level_name, class_id), day_of_week, start_time, end_time, new_teacher, class_id),
        )
        roster = _reconcile_roster(cur, class_id, student_ids) if student_ids is not None else None
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    try:
        log_admin_action("UPDATE", "class_def", entity_id=class_id,
                         details=f"was day={old['day_of_week']}, {old['start_time']}-{old['end_time']}, "
                                 f"teacher={old['teacher']}; now day={day_of_week}, {start_time}-{end_time}, "
                                 f"teacher={new_teacher}; roster={roster}")
    except Exception as e:
        print(f"Warning: Failed to log admin action: {e}")


def set_class_roster(class_id: str, student_ids) -> Dict[str, List[str]]:
    """Make the active roster exactly student_ids. Removals set removed_at; nothing is deleted."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        if cur.execute("SELECT 1 FROM class_def WHERE class_id = ?", (class_id,)).fetchone() is None:
            raise ValidationError(f"No class with ID {class_id!r}")
        result = _reconcile_roster(cur, class_id, student_ids)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if any(result.values()):
        try:
            log_admin_action("ROSTER", "class_roster", entity_id=class_id, details=str(result))
        except Exception as e:
            print(f"Warning: Failed to log admin action: {e}")
    return result


def deactivate_class(class_id: str) -> None:
    """Set is_active = 0. The row and its roster are kept."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE class_def SET is_active = 0, updated_at = datetime('now') WHERE class_id = ?",
            (class_id,),
        )
        if cur.rowcount == 0:
            raise ValidationError(f"No class with ID {class_id!r}")
        conn.commit()
    finally:
        conn.close()
    try:
        log_admin_action("DEACTIVATE", "class_def", entity_id=class_id)
    except Exception as e:
        print(f"Warning: Failed to log admin action: {e}")


def _promote_checked(cur, class_id: str, new_level_code: str):
    """The checks a Move Up must pass. Returns (old class row, new level name). Raises ValidationError."""
    old = cur.execute("SELECT * FROM class_def WHERE class_id = ?", (class_id,)).fetchone()
    if old is None:
        raise ValidationError(f"No class with ID {class_id!r}")
    if is_legacy_class(old):
        raise ValidationError(f"{class_id!r} is an old-style class and cannot be moved up a level")
    if old["level"] in STANDALONE_LEVELS:
        raise ValidationError(f"{class_id!r} is a standalone class type ({old['level']}) "
                              f"and cannot be moved up a level")
    if new_level_code in STANDALONE_LEVELS:
        raise ValidationError(f"{new_level_code} is a standalone class type; add it as a new class instead")
    if not old["is_active"]:
        raise ValidationError(f"Class {class_id!r} is not active")
    if old["level"] == new_level_code:
        raise ValidationError(f"Class {class_id!r} is already at level {new_level_code}")
    level_name = _validate_schedule_fields(
        cur, new_level_code, old["day_of_week"], old["start_time"], old["end_time"]
    )
    return old, level_name


def promote_preview(class_id: str, new_level_code: str) -> Dict[str, Any]:
    """Read-only summary of a Move Up, for its confirmation. Raises ValidationError as promote_class would."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        old, level_name = _promote_checked(cur, class_id, new_level_code)
        today = date.today().isoformat()
        students = cur.execute(
            "SELECT COUNT(*) FROM class_roster WHERE class_id = ? AND removed_at IS NULL", (class_id,)).fetchone()[0]
        cancellations = cur.execute(
            "SELECT COUNT(*) FROM class_cancellations WHERE class_id = ? AND cancel_end >= ?",
            (class_id, today)).fetchone()[0]
        old_level_name = cur.execute(
            "SELECT level_name FROM class_level WHERE level_code = ?", (old["level"],)).fetchone()
        custom = old_level_name is None or old["class_name"] != _auto_class_name(None, old_level_name[0], class_id)
        return {"old_id": class_id, "old_level": old["level"], "new_id": _next_class_id(cur, new_level_code),
                "students": students, "cancellations": cancellations,
                "label": old["class_name"] if custom else None}
    finally:
        conn.close()


def moved_students_level_split(class_id: str, old_level_code: str):
    """(ids whose Level equals old_level_code, ignoring case and spaces; how many others) among a class's active roster."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT s.student_id, s.level FROM class_roster cr JOIN students s ON s.student_id = cr.student_id "
            "WHERE cr.class_id = ? AND cr.removed_at IS NULL ORDER BY s.student_id", (class_id,)).fetchall()
    finally:
        conn.close()
    want = (old_level_code or "").strip().upper()
    match = [r[0] for r in rows if (r[1] or "").strip().upper() == want]
    return match, len(rows) - len(match)


def set_student_levels(student_ids, new_level: str, expected_old: str) -> Dict[str, str]:
    """Set Level for the given students in one transaction, only where it still equals expected_old
    (ignoring case and spaces). Sets updated_at and logs the old values. Returns {student_id: old Level}."""
    new_level = sanitize_input(new_level, max_length=50)
    if not new_level:
        raise ValidationError("New level is required")
    want = (expected_old or "").strip().upper()
    changed = {}
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        for sid in student_ids:
            row = conn.execute("SELECT level FROM students WHERE student_id = ?", (sid,)).fetchone()
            if row is None or (row[0] or "").strip().upper() != want:
                continue
            conn.execute("UPDATE students SET level = ?, updated_at = datetime('now') WHERE student_id = ? AND level = ?",
                         (new_level, sid, row[0]))
            changed[sid] = row[0]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if changed:
        try:
            log_admin_action("SET_LEVELS", "student", details=json.dumps(
                {"expected_old": expected_old, "new": new_level, "students": changed}, ensure_ascii=False))
        except (sqlite3.Error, OSError) as e:
            print(f"Warning: Failed to log admin action: {e}")
    return changed


def promote_class(class_id: str, new_level_code: str) -> str:
    """Move a class to a new level as a new class (same day, time, active roster); deactivate the old one.

    The old class's roster rows are left untouched as history. Returns the new class_id.
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        old, level_name = _promote_checked(cur, class_id, new_level_code)
        new_id = _next_class_id(cur, new_level_code)
        # a custom label is carried unchanged; an automatic name is regenerated for the new level
        old_level_name = cur.execute("SELECT level_name FROM class_level WHERE level_code = ?", (old["level"],)).fetchone()
        custom = old_level_name is None or old["class_name"] != _auto_class_name(None, old_level_name[0], class_id)
        new_name = old["class_name"] if custom else _auto_class_name(None, level_name, new_id)
        cur.execute(
            """
            INSERT INTO class_def (class_id, class_name, day_of_week, start_time, end_time, level, teacher)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id, new_name, old["day_of_week"],
             old["start_time"], old["end_time"], new_level_code, old["teacher"]),
        )
        cur.execute("SELECT student_id FROM class_roster WHERE class_id = ? AND removed_at IS NULL", (class_id,))
        student_ids = [r[0] for r in cur.fetchall()]
        _reconcile_roster(cur, new_id, student_ids)
        # cancellations that have not ended move to the new ID, starting no earlier than today; old rows stay as history
        today = date.today().isoformat()
        carried = cur.execute(
            """INSERT INTO class_cancellations (class_id, cancel_start, cancel_end, reason)
               SELECT ?, MAX(cancel_start, ?), cancel_end, COALESCE(reason, '') || ' [carried from ' || ? || ']'
               FROM class_cancellations WHERE class_id = ? AND cancel_end >= ?""",
            (new_id, today, class_id, class_id, today),
        ).rowcount
        cur.execute("UPDATE class_def SET is_active = 0, updated_at = datetime('now') WHERE class_id = ?", (class_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    try:
        log_admin_action("PROMOTE", "class_def", entity_id=class_id,
                         details=f"{class_id} ({old['level']}) -> {new_id} ({new_level_code}), students={student_ids}, "
                                 f"cancellations carried={carried}")
    except Exception as e:
        print(f"Warning: Failed to log admin action: {e}")
    return new_id


def class_history_counts(class_id: str):
    """(roster rows, cancellations) for a class: rows that a delete would take with it."""
    _ensure_class_tables()
    _ensure_cancellations_table()
    conn = get_connection()
    try:
        return (
            conn.execute("SELECT COUNT(*) FROM class_roster WHERE class_id = ?", (class_id,)).fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM class_cancellations WHERE class_id = ?", (class_id,)).fetchone()[0],
        )
    finally:
        conn.close()


def _pad_hhmm(value):
    """'9:00' -> '09:00'; None if it can't be read as a time."""
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", value or "")
    if m and int(m.group(1)) <= 23 and int(m.group(2)) <= 59:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return None


def _minutes(value):
    """'9:00' or '09:00' -> minutes since midnight; None if it can't be read as a time."""
    padded = _pad_hhmm(value) if isinstance(value, str) else None
    return None if padded is None else int(padded[:2]) * 60 + int(padded[3:])


def reactivate_class(class_id: str) -> None:
    """Set is_active = 1 again. Refused if another active class holds the same day and time."""
    _ensure_class_tables()
    row = get_class_def(class_id)
    if not row:
        raise ValidationError(f"No class with ID {class_id!r}")
    if row["is_active"]:
        raise ValidationError(f"Class {class_id!r} is already active")
    for label, value in (("start", row["start_time"]), ("end", row["end_time"])):
        if not (isinstance(value, str) and _HHMM_RE.match(value)):
            fixed = _pad_hhmm(value)
            how = (f"Set the {label} time to {fixed} first." if fixed else
                   f"Set the {label} time to a time written HH:MM with a leading zero (for example 09:00) first.")
            note = (" This is an old-style class, and its time cannot be edited in the portal, so it needs a data fix."
                    if is_legacy_class(row) else "")
            raise ValidationError(
                f"Cannot reactivate {class_id}: its {label} time {value!r} is not written HH:MM with a leading zero. {how}{note}")
    clashes = find_clashes(row["day_of_week"], row["start_time"], row["end_time"],
                           exclude_class_id=class_id, include_legacy=True)
    if clashes:
        names = ", ".join(c["class_id"] for c in clashes)
        raise ValidationError(
            f"Cannot reactivate {class_id}: {names} already holds that day and time "
            f"({row['start_time']}-{row['end_time']}). Two active classes in one slot would confuse the recording lookup.")
    conn = get_connection()
    try:
        conn.execute("UPDATE class_def SET is_active = 1, updated_at = datetime('now') WHERE class_id = ?", (class_id,))
        conn.commit()
    finally:
        conn.close()
    try:
        log_admin_action("REACTIVATE", "class_def", entity_id=class_id)
    except Exception as e:
        print(f"Warning: Failed to log admin action: {e}")


def delete_class_def(class_id: str) -> None:
    """Delete a class definition. Refused if the class has any roster row (active or removed) or any cancellation."""
    _ensure_class_tables()
    roster_n, cancel_n = class_history_counts(class_id)
    if roster_n or cancel_n:
        raise ValidationError(
            f"Cannot delete class {class_id!r}: it has {roster_n} roster row(s) and {cancel_n} cancellation(s). "
            f"Use Deactivate in the Schedule tab; it keeps the history.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM class_roster WHERE class_id = ?", (class_id,))
    cur.execute("DELETE FROM class_def WHERE class_id = ?", (class_id,))
    conn.commit()
    conn.close()
    try:
        log_admin_action("DELETE", "class_def", entity_id=class_id)
    except Exception as e:
        print(f"Warning: Failed to log admin action: {e}")


def add_student_to_roster(class_id: str, student_id: str) -> None:
    """Add a student to a class roster (upsert — re-enrolls if previously removed)."""
    _ensure_class_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO class_roster (class_id, student_id)
        VALUES (?, ?)
        ON CONFLICT(class_id, student_id) DO UPDATE SET
            removed_at = NULL,
            enrolled_at = datetime('now')
        """,
        (class_id, student_id),
    )
    conn.commit()
    conn.close()
    try:
        log_admin_action("ENROLL", "class_roster", entity_id=f"{class_id}/{student_id}",
                         details=f"class={class_id}, student={student_id}")
    except Exception as e:
        print(f"Warning: Failed to log admin action: {e}")


def remove_student_from_roster(class_id: str, student_id: str) -> None:
    """Soft-remove a student from a class roster by setting removed_at."""
    _ensure_class_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE class_roster SET removed_at = datetime('now') WHERE class_id = ? AND student_id = ?",
        (class_id, student_id),
    )
    conn.commit()
    conn.close()
    try:
        log_admin_action("REMOVE", "class_roster", entity_id=f"{class_id}/{student_id}",
                         details=f"class={class_id}, student={student_id}")
    except Exception as e:
        print(f"Warning: Failed to log admin action: {e}")


def get_roster_for_class(class_id: str) -> List[Dict[str, Any]]:
    """Get active roster for a class, joined with student info."""
    _ensure_class_tables()
    conn = get_connection()
    cur = conn.cursor()
    if class_id.startswith("extra:"):
        extra_id = int(class_id.split(":")[1])
        cur.execute(
            """
            SELECT NULL AS roster_id, ? AS class_id, els.student_id, NULL AS enrolled_at,
                   s.first_name, s.last_name, s.level, s.status AS student_status
            FROM extra_lesson_student els
            JOIN students s ON els.student_id = s.student_id
            WHERE els.extra_lesson_id = ?
            ORDER BY s.first_name, s.last_name
            """,
            (class_id, extra_id),
        )
    else:
        cur.execute(
            """
            SELECT cr.roster_id, cr.class_id, cr.student_id, cr.enrolled_at,
                   s.first_name, s.last_name, s.level, s.status AS student_status
            FROM class_roster cr
            JOIN students s ON cr.student_id = s.student_id
            WHERE cr.class_id = ? AND cr.removed_at IS NULL
            ORDER BY s.first_name, s.last_name
            """,
            (class_id,),
        )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_classes_for_day(day_of_week: int) -> List[Dict[str, Any]]:
    """Return active class_def rows for a given day number (0=Mon..6=Sun)."""
    _ensure_class_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM class_def WHERE day_of_week = ? AND is_active = 1 ORDER BY start_time",
        (day_of_week,),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_classes_for_student(student_id: str) -> List[Dict[str, Any]]:
    """Get all active classes a student is enrolled in."""
    _ensure_class_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cd.*, cr.enrolled_at
        FROM class_roster cr
        JOIN class_def cd ON cr.class_id = cd.class_id
        WHERE cr.student_id = ? AND cr.removed_at IS NULL AND cd.is_active = 1
        ORDER BY cd.day_of_week, cd.start_time
        """,
        (student_id,),
    )
    rows = cur.fetchall()

    # Also include extra lessons this student is enrolled in
    _ensure_extra_lesson_tables()
    cur.execute(
        """
        SELECT 'extra:' || el.id AS class_id, el.label AS class_name,
               NULL AS day_of_week, el.start_time, el.end_time,
               el.level, NULL AS teacher, 1 AS is_active,
               el.lesson_date, NULL AS enrolled_at
        FROM extra_lesson_student els
        JOIN extra_lesson el ON els.extra_lesson_id = el.id
        WHERE els.student_id = ?
        ORDER BY el.lesson_date, el.start_time
        """,
        (student_id,),
    )
    extra_rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows] + [_row_to_dict(r) for r in extra_rows]


def seed_classes_from_csv(csv_path: str) -> Tuple[int, int, List[str]]:
    """
    Parse a schedule CSV and create class_def + class_roster entries.
    Returns: (classes_created, enrollments_created, unmatched_names)
    """
    import re as _re
    _ensure_class_tables()
    all_rows = None
    for encoding in ('utf-8-sig', 'utf-8', 'latin1'):
        try:
            with open(csv_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read().lstrip('\ufeff')
                content = content.replace('\r\n', '\n').replace('\r', '\n')
                lines = content.split('\n')
                reader = csv.reader(lines)
                all_rows = list(reader)
                break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if not all_rows or len(all_rows) < 2:
        return (0, 0, ["Could not read CSV or file is empty"])
    header = [cell.strip().lower() for cell in all_rows[0]]
    is_template = ('class_id' in header and 'day_of_week' in header)
    if is_template:
        return _seed_from_template_csv(all_rows, header)
    else:
        return _seed_from_grid_csv(all_rows, header)


def _seed_from_template_csv(all_rows: list, header: list) -> Tuple[int, int, List[str]]:
    """Import classes from template format CSV (one row per class)."""
    import re as _re
    col_map = {name: idx for idx, name in enumerate(header)}
    day_abbrev_map = {
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
        'fri': 4, 'sat': 5, 'sun': 6,
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6,
    }
    classes_created = 0
    skipped = []
    conn = get_connection()
    cur = conn.cursor()
    try:
        for row_num, row in enumerate(all_rows[1:], start=2):
            if not row or len(row) < 4:
                continue
            def cell(name):
                idx = col_map.get(name)
                if idx is not None and idx < len(row):
                    return str(row[idx]).strip()
                return ''
            class_id = cell('class_id')
            class_name = cell('class_name')
            day_raw = cell('day_of_week')
            start_time = cell('start_time')
            end_time = cell('end_time')
            level = cell('level')
            teacher = cell('teacher') or 'David'
            if not class_id or not start_time:
                continue
            if class_id.upper().startswith('INSTRUCTION'):
                continue
            day_num = day_abbrev_map.get(day_raw.lower())
            if day_num is None:
                skipped.append(f"Row {row_num}: unknown day '{day_raw}' for {class_id}")
                continue
            if not class_name:
                day3 = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][day_num]
                class_name = f"{level or 'Class'} {day3} {start_time}"
            try:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO class_def
                        (class_id, class_name, day_of_week, start_time, end_time, level, teacher)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (class_id, class_name, day_num, start_time, end_time, level, teacher),
                )
                if cur.rowcount > 0:
                    classes_created += 1
            except Exception as e:
                skipped.append(f"Row {row_num}: {e}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error seeding classes from template CSV: {e}")
    finally:
        conn.close()
    try:
        log_admin_action("SEED", "class_def",
                         details=f"csv={all_rows[0]}, classes={classes_created}, skipped={len(skipped)}")
    except Exception:
        pass
    return (classes_created, 0, skipped)


def _seed_from_grid_csv(all_rows: list, header: list) -> Tuple[int, int, List[str]]:
    """Import classes + enrollments from grid-style schedule CSV (days as columns)."""
    import re as _re
    day_names_map = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    day3_map = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}
    day_columns = {}
    for col_idx, cell in enumerate(header):
        for day_name, day_num in day_names_map.items():
            if day_name in cell:
                day_columns[col_idx] = day_num
                break
    if not day_columns:
        return (0, 0, ["Could not detect day columns in header"])
    all_students = [s for s in list_students()
                    if (s.get('status') or 'active') == 'active']
    name_lookup = {}
    for s in all_students:
        fname = (s.get('first_name') or '').strip().lower()
        if fname:
            name_lookup[fname] = s['student_id']
    classes_created = 0
    enrollments_created = 0
    unmatched_names = []
    conn = get_connection()
    cur = conn.cursor()
    try:
        for row in all_rows[1:]:
            if not row or len(row) < 2:
                continue
            time_slot = None
            for cell in row:
                cell_str = str(cell).strip()
                time_match = _re.search(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', cell_str)
                if time_match:
                    time_slot = (time_match.group(1), time_match.group(2))
                    break
            if not time_slot:
                continue
            start_time, end_time = time_slot
            for col_idx, day_num in day_columns.items():
                if col_idx >= len(row):
                    continue
                cell_content = str(row[col_idx]).strip()
                if not cell_content or cell_content == '-':
                    continue
                level_matches = _re.findall(r'\(([^)]+)\)', cell_content)
                level = None
                if level_matches:
                    level = level_matches[0].strip()
                else:
                    for word in _re.findall(r'\b\w+\b', cell_content):
                        if _re.match(r'^(SM\d+|Phonics\d*|Beginner|Intermediate|Advanced|IELTS|Elementary)$', word, _re.IGNORECASE):
                            level = word
                            break
                if not level:
                    level = "General"
                level_slug = _re.sub(r'[^a-z0-9]', '', level.lower())
                hhmm = start_time.replace(':', '')
                day3 = day3_map[day_num]
                class_id = f"{day3}_{hhmm}_{level_slug}"
                class_name = f"{level} ({day3.capitalize()} {start_time})"
                try:
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO class_def
                            (class_id, class_name, day_of_week, start_time, end_time, level, teacher)
                        VALUES (?, ?, ?, ?, ?, ?, 'David')
                        """,
                        (class_id, class_name, day_num, start_time, end_time, level),
                    )
                    if cur.rowcount > 0:
                        classes_created += 1
                except Exception:
                    pass
                names_text = _re.sub(r'\([^)]*\)', '', cell_content).strip()
                raw_names = _re.split(r'[,&]', names_text)
                for raw_name in raw_names:
                    name = raw_name.strip().rstrip('!').strip()
                    if not name or _re.match(r'^(SM\d+|Phonics\d*|Beginner|Intermediate|Advanced|IELTS|Elementary)$', name, _re.IGNORECASE):
                        continue
                    student_id = name_lookup.get(name.lower())
                    if student_id:
                        try:
                            cur.execute(
                                """
                                INSERT OR IGNORE INTO class_roster (class_id, student_id)
                                VALUES (?, ?)
                                """,
                                (class_id, student_id),
                            )
                            if cur.rowcount > 0:
                                enrollments_created += 1
                        except Exception:
                            pass
                    else:
                        if name and name not in unmatched_names:
                            unmatched_names.append(name)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error seeding classes from CSV: {e}")
    finally:
        conn.close()
    try:
        log_admin_action("SEED", "class_roster",
                         details=f"classes={classes_created}, enrollments={enrollments_created}, unmatched={len(unmatched_names)}")
    except Exception:
        pass
    return (classes_created, enrollments_created, unmatched_names)


# ---------- EXTRA LESSONS ----------

def _ensure_extra_lesson_tables() -> None:
    """Create extra_lesson and extra_lesson_student tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS extra_lesson (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            lesson_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            level TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_extra_lesson_date ON extra_lesson(lesson_date)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS extra_lesson_student (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extra_lesson_id INTEGER NOT NULL,
            student_id TEXT NOT NULL,
            FOREIGN KEY (extra_lesson_id) REFERENCES extra_lesson(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            UNIQUE(extra_lesson_id, student_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_extra_lesson_student_lesson ON extra_lesson_student(extra_lesson_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_extra_lesson_student_student ON extra_lesson_student(student_id)")
    conn.commit()
    conn.close()


_DATE = date          # the real date class, as imported (a test may rebind the name `date` to freeze today)


def _as_iso(value):
    """A date object becomes its ISO text; anything else is returned as it is (parse_session_date then judges it)."""
    return value.isoformat() if isinstance(value, _DATE) else value


def is_past_date(lesson_date: str) -> bool:
    """True if lesson_date (YYYY-MM-DD) is before today. ValueError if it is not a date."""
    return parse_session_date(lesson_date) < date.today()


def create_extra_lesson(label: str, lesson_date: str, start_time: str, end_time: str,
                        level: str = None, notes: str = None, student_ids=(), allow_past: bool = False) -> int:
    """Create a one-off extra lesson and its students in ONE transaction. Returns the new extra_lesson.id.

    Raises ValidationError, and saves nothing, if: the times are not zero-padded HH:MM with the end after the start
    (check_class_times); the date is not YYYY-MM-DD; the date is before today and allow_past is not set (the caller
    asks first); or any student cannot be added (the message names the student and says nothing was saved).
    """
    _ensure_extra_lesson_tables()
    check_class_times(start_time, end_time)
    lesson_date = _as_iso(lesson_date)
    try:
        day = parse_session_date(lesson_date)
    except ValueError as e:
        raise ValidationError(str(e)) from None
    lesson_date = day.isoformat()                      # stored normalised, as cancel_class stores its dates
    if day < date.today() and not allow_past:
        raise ValidationError(f"{lesson_date} is in the past.")
    ids = list(dict.fromkeys(str(s) for s in student_ids))
    conn = get_connection()
    current = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO extra_lesson (label, lesson_date, start_time, end_time, level, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (label, lesson_date, start_time, end_time, level, notes),
        )
        new_id = cur.lastrowid
        for current in ids:
            cur.execute("INSERT INTO extra_lesson_student (extra_lesson_id, student_id) VALUES (?, ?)",
                        (new_id, current))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        who = f" while adding {current}" if current else ""
        raise ValidationError(f"Could not save the extra lesson{who}: {e}. Nothing was saved.") from e
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    try:
        log_admin_action("CREATE", "extra_lesson", entity_id=str(new_id),
                         details=f"label={label}, date={lesson_date}, {start_time}-{end_time}"
                                 + (f", students={ids}" if ids else ""))
    except Exception:
        pass
    return new_id


def extra_lesson_conflicts(lesson_date: str, start_time: str, end_time: str) -> List[Dict[str, Any]]:
    """What an extra lesson at this date and time would overlap: active classes that are not cancelled that date, and
    other extra lessons that day. Each is {"kind": "class" | "extra", "id", "label", "start_time", "end_time",
    "unreadable", "new_lesson_gets_recordings"}; a class or lesson whose time cannot be read is listed with unreadable
    True, not hidden.

    Two lessons clash when the windows in which a recording is filed under them touch: each lesson's own time widened
    by RECORDING_BUFFER_MINUTES either side (the window the recording lookup uses), so back-to-back lessons clash.

    Who gets the recordings in an overlap: an extra lesson always beats a class (owner decision O13, Zone B checks
    extra lessons first). Between two extra lessons the one made first, the lower id, does (David's decision, 1 Oct:
    the portal mirrors Zone B, whose lookup takes the first match in creation order). The lesson being created is the
    newest, so an existing extra lesson that overlaps it always wins; new_lesson_gets_recordings is True only against a
    class.
    Raises ValidationError for bad times or a date that is not YYYY-MM-DD.
    """
    check_class_times(start_time, end_time)
    lesson_date = _as_iso(lesson_date)
    try:
        day = parse_session_date(lesson_date)
    except ValueError as e:
        raise ValidationError(str(e)) from None
    s, e_ = _minutes(start_time), _minutes(end_time)
    buf = RECORDING_BUFFER_MINUTES

    def entry(kind, ident, label, start, end):
        a, b = _minutes(start), _minutes(end)
        if a is None or b is None:
            return {"kind": kind, "id": ident, "label": label, "start_time": start, "end_time": end,
                    "unreadable": True, "new_lesson_gets_recordings": kind == "class"}
        if a - buf <= e_ + buf and s - buf <= b + buf:        # the two recording windows touch or overlap
            return {"kind": kind, "id": ident, "label": label, "start_time": start, "end_time": end,
                    "unreadable": False, "new_lesson_gets_recordings": kind == "class"}
        return None

    found = []
    for cls in get_classes_for_day_of_week(day.weekday()):
        if is_class_cancelled(cls["class_id"], day):
            continue
        found.append(entry("class", cls["class_id"], cls["class_name"], cls["start_time"], cls["end_time"]))
    for el in get_extra_lessons_for_date(lesson_date):
        found.append(entry("extra", el["id"], el["label"], el["start_time"], el["end_time"]))
    return [f for f in found if f is not None]


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def extra_lesson_recording_split(start_time: str, end_time: str, conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Who gets the recordings while a new extra lesson overlaps others, window by window. `conflicts` is what
    extra_lesson_conflicts returned for this lesson. Returns [{"from": "HH:MM", "to": "HH:MM", "owner": None | extra
    lesson id, "label": its label}] in time order: owner None means the new lesson, otherwise the extra lesson that
    wins those minutes. Only the minutes where some other lesson's recording window (its own time +-
    RECORDING_BUFFER_MINUTES) meets the new lesson's are listed. A class never wins against an extra lesson; among
    extra lessons the lowest id (made first) wins, whatever the start times (the rule of get_extra_lesson_for_datetime,
    as in Zone B), and the new lesson counts as the latest made. A lesson whose time cannot be read is left out (it has no window)."""
    s, e_ = _minutes(start_time), _minutes(end_time)
    buf = RECORDING_BUFFER_MINUTES
    windows = []
    for c in conflicts:
        a, b = _minutes(c["start_time"]), _minutes(c["end_time"])
        if c["unreadable"] or a is None or b is None:
            continue
        windows.append((a - buf, b + buf, c))
    out, current = [], None
    for minute in range(max(s - buf, 0), min(e_ + buf, 24 * 60 - 1) + 1):
        covering = [c for lo, hi, c in windows if lo <= minute <= hi]
        if not covering:
            current = None
            continue
        ahead = [c for c in covering if c["kind"] == "extra" and not c["new_lesson_gets_recordings"]]
        owner = min(ahead, key=lambda c: c["id"]) if ahead else None
        owner_id = owner["id"] if owner else None
        if current is not None and current["owner"] == owner_id and current["_end"] == minute - 1:
            current["_end"] = minute
            current["to"] = _hhmm(minute)
        else:
            current = {"from": _hhmm(minute), "to": _hhmm(minute), "owner": owner_id,
                       "label": owner["label"] if owner else None, "_end": minute}
            out.append(current)
    for seg in out:
        del seg["_end"]
    return out


def get_extra_lessons_for_date(lesson_date: str) -> List[Dict[str, Any]]:
    """Return all extra lessons on a given date (ISO format YYYY-MM-DD)."""
    _ensure_extra_lesson_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM extra_lesson WHERE lesson_date = ? ORDER BY start_time",
        (lesson_date,),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_extra_lesson_by_id(lesson_id: int) -> Optional[Dict[str, Any]]:
    """Return a single extra lesson by ID, or None."""
    _ensure_extra_lesson_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM extra_lesson WHERE id = ?", (lesson_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def delete_extra_lesson(lesson_id: int) -> bool:
    """Delete an extra lesson and its student assignments. Returns True on success."""
    _ensure_extra_lesson_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM extra_lesson_student WHERE extra_lesson_id = ?", (lesson_id,))
    cur.execute("DELETE FROM extra_lesson WHERE id = ?", (lesson_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    try:
        log_admin_action("DELETE", "extra_lesson", entity_id=str(lesson_id))
    except Exception:
        pass
    return deleted


def assign_student_to_extra_lesson(extra_lesson_id: int, student_id: str) -> bool:
    """Assign a student to an extra lesson. Returns True on success."""
    _ensure_extra_lesson_tables()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR IGNORE INTO extra_lesson_student (extra_lesson_id, student_id) VALUES (?, ?)",
            (extra_lesson_id, student_id),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def remove_student_from_extra_lesson(extra_lesson_id: int, student_id: str) -> bool:
    """Remove a student from an extra lesson. Returns True on success."""
    _ensure_extra_lesson_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM extra_lesson_student WHERE extra_lesson_id = ? AND student_id = ?",
        (extra_lesson_id, student_id),
    )
    removed = cur.rowcount > 0
    conn.commit()
    conn.close()
    return removed


def get_students_for_extra_lesson(extra_lesson_id: int) -> List[Dict[str, Any]]:
    """Return student records (student_id, first_name, last_name, level) for an extra lesson."""
    _ensure_extra_lesson_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.student_id, s.first_name, s.last_name, s.level
        FROM extra_lesson_student els
        JOIN students s ON els.student_id = s.student_id
        WHERE els.extra_lesson_id = ?
        ORDER BY s.first_name
        """,
        (extra_lesson_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


RECORDING_BUFFER_MINUTES = 30
"""How far either side of a lesson a recording is still filed under it. get_extra_lesson_for_datetime and the
extra-lesson clash check both use this one number. It is Zone B's own recording buffer (portal/school_db.py:122 and
pc_ingest/tools/backfill_recovered.py:88 use 30 minutes), by David's decision of 30 Sep; if Zone B's buffer changes,
this is the one place to follow it."""


def _now():
    """The current date and time; the tests replace this."""
    from datetime import datetime as _dt
    return _dt.now()


def get_extra_lesson_for_datetime(dt=None) -> Optional[Dict[str, Any]]:
    """
    Find an extra_lesson active at the given datetime (default: now).

    Uses the RECORDING_BUFFER_MINUTES buffer (30) either side of the lesson.
    Returns the extra_lesson dict or None.
    """
    if dt is None:
        dt = _now()

    _ensure_extra_lesson_tables()
    lesson_date = dt.strftime("%Y-%m-%d")
    current_time = dt.strftime("%H:%M")
    early_time = (dt - timedelta(minutes=RECORDING_BUFFER_MINUTES)).strftime("%H:%M")
    late_time = (dt + timedelta(minutes=RECORDING_BUFFER_MINUTES)).strftime("%H:%M")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM extra_lesson
        WHERE lesson_date = ?
          AND start_time <= ?
          AND end_time >= ?
        ORDER BY id
        LIMIT 1
        """,
        (lesson_date, late_time, early_time),
    )
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


# ---------- Class Cancellations ----------

def _ensure_cancellations_table() -> None:
    """Safety guard: ensure class_cancellations table exists."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS class_cancellations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id TEXT NOT NULL,
            cancel_start DATE NOT NULL,
            cancel_end DATE NOT NULL,
            reason TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (class_id) REFERENCES class_def(class_id)
        )
    """)
    conn.commit()
    conn.close()


_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _lesson_dates_between(day_of_week, start: date, end: date) -> List[date]:
    """Every date from start to end (inclusive) that falls on the class's weekday."""
    out, d = [], start
    while d <= end:
        if d.weekday() == day_of_week:
            out.append(d)
        d += timedelta(days=1)
    return out


def _lesson_has_ended(cls, lesson_day: date) -> bool:
    """True if the class's lesson on lesson_day is over: the day is before today, or it is today and the lesson's end
    time has passed. An end time that cannot be read counts as not ended (nothing is hidden or kept on a guess)."""
    today = date.today()
    if lesson_day < today:
        return True
    if lesson_day > today:
        return False
    ends = _minutes(cls.get("end_time"))
    now = _now()
    return ends is not None and now.hour * 60 + now.minute >= ends


def next_lesson_dates(class_id: str, count: int = 8) -> List[str]:
    """The next `count` dates (ISO) the class meets. Today comes first only if it is the class's weekday and the
    lesson has not ENDED yet (David's decision: a lesson under way can still be cancelled, so the recording mic
    is not started for it). An end time that cannot be read does not hide today."""
    cls = get_class_def(class_id)
    if not cls:
        raise ValidationError(f"No class with ID {class_id!r}")
    today = date.today()
    first = today + timedelta(days=(cls["day_of_week"] - today.weekday()) % 7)
    if first == today and _lesson_has_ended(cls, today):
        first += timedelta(days=7)
    return [(first + timedelta(days=7 * i)).isoformat() for i in range(count)]


def cancel_class(class_id: str, first_date: str, lessons: int, reason: str = None) -> Dict[str, Any]:
    """Cancel `lessons` lessons of a class (1 to 8), starting with the lesson on first_date.

    first_date must be YYYY-MM-DD, not in the past, and the class's own weekday. The stored range is first_date to
    first_date + 7 x (lessons - 1), inclusive, so 1 lesson is one date. (Rows made before this stay as stored;
    Zone B reads the same inclusive range.) A range that overlaps an existing cancellation of the class (old rows
    included) is refused with a message naming it. Raises ValidationError and writes nothing otherwise.
    """
    _ensure_cancellations_table()
    cls = get_class_def(class_id)
    if not cls:
        raise ValidationError(f"No class with ID {class_id!r}")
    try:
        first = parse_session_date(first_date)
    except ValueError as e:
        raise ValidationError(str(e)) from None
    if isinstance(lessons, bool) or not isinstance(lessons, int) or not 1 <= lessons <= 8:
        raise ValidationError("Number of lessons must be a whole number from 1 to 8")
    if first < date.today():
        raise ValidationError(f"{first_date} is in the past")
    if first.weekday() != cls["day_of_week"]:
        raise ValidationError(f"{first_date} is a {first.strftime('%A')}, but {class_id} meets on "
                              f"{_DAY_NAMES[cls['day_of_week']]}")
    cancel_start = first.isoformat()
    cancel_end = (first + timedelta(days=7 * (lessons - 1))).isoformat()

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        clash = conn.execute(
            "SELECT cancel_start, cancel_end FROM class_cancellations "
            "WHERE class_id = ? AND cancel_start <= ? AND cancel_end >= ? ORDER BY cancel_start LIMIT 1",
            (class_id, cancel_end, cancel_start)).fetchone()
        if clash is not None:
            raise ValidationError(
                f"This overlaps an existing cancellation of {class_id} ({clash['cancel_start']} to "
                f"{clash['cancel_end']}). Remove or shorten that one first, or pick lessons after {clash['cancel_end']}.")
        cur = conn.execute(
            """INSERT INTO class_cancellations (class_id, cancel_start, cancel_end, reason)
               VALUES (?, ?, ?, ?)""",
            (class_id, cancel_start, cancel_end, reason),
        )
        new_id = cur.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM class_cancellations WHERE id = ?", (new_id,)).fetchone()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    try:
        log_admin_action("cancel_class", "class_def", class_id,
                         details=f"Cancelled {lessons} lesson(s), {cancel_start} to {cancel_end}: {reason or ''}")
    except Exception:
        pass

    return _row_to_dict(row)


def uncancel_class(cancellation_id: int) -> bool:
    """Remove a cancellation by its id."""
    _ensure_cancellations_table()
    conn = get_connection()
    cur = conn.cursor()

    # Get info before deleting for audit log
    cur.execute("SELECT * FROM class_cancellations WHERE id = ?", (cancellation_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    info = _row_to_dict(row)
    cur.execute("DELETE FROM class_cancellations WHERE id = ?", (cancellation_id,))
    conn.commit()
    conn.close()

    try:
        log_admin_action("uncancel_class", "class_def", info.get('class_id', ''),
                         details=f"Removed cancellation {cancellation_id}")
    except Exception:
        pass

    return True


def list_upcoming_cancellations(class_id: str) -> List[Dict[str, Any]]:
    """The class's cancellations that have not ended (cancel_end today or later), oldest first, each with
    lesson_dates (every lesson date inside its stored range) and upcoming_lesson_dates (those from today on whose
    lesson has not ended: today's lesson drops out once its end time has passed)."""
    _ensure_cancellations_table()
    cls = get_class_def(class_id)
    dow = cls.get("day_of_week") if cls else None
    today = date.today().isoformat()
    conn = get_connection()
    try:
        rows = [_row_to_dict(r) for r in conn.execute(
            "SELECT * FROM class_cancellations WHERE class_id = ? AND cancel_end >= ? ORDER BY cancel_start, id",
            (class_id, today))]
    finally:
        conn.close()
    for r in rows:
        try:
            dates = ([d.isoformat() for d in _lesson_dates_between(
                dow, date.fromisoformat(r["cancel_start"]), date.fromisoformat(r["cancel_end"]))]
                if dow is not None else [])
        except ValueError:
            dates = []
        r["lesson_dates"] = dates
        r["upcoming_lesson_dates"] = [d for d in dates if d >= today and not _lesson_has_ended(cls, date.fromisoformat(d))]
    return rows


def shorten_cancellation(cancellation_id: int, last_cancelled_date: str) -> Dict[str, Any]:
    """Give lessons back: the last date that stays cancelled becomes last_cancelled_date. If that is before the
    cancellation's start, nothing is left and the row is deleted. Refused if it would not shorten the range.
    Returns {"action": "shortened" | "deleted", "id", "class_id", "cancel_end"}."""
    _ensure_cancellations_table()
    try:
        last = parse_session_date(last_cancelled_date)
    except ValueError as e:
        raise ValidationError(str(e)) from None
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM class_cancellations WHERE id = ?", (cancellation_id,)).fetchone()
        if row is None:
            raise ValidationError(f"No cancellation with id {cancellation_id!r}")
        start, end = date.fromisoformat(row["cancel_start"]), date.fromisoformat(row["cancel_end"])
        if last >= end:
            raise ValidationError(f"The cancellation already ends on {row['cancel_end']}; there is nothing to give back")
        if last < start:
            conn.execute("DELETE FROM class_cancellations WHERE id = ?", (cancellation_id,))
            result = {"action": "deleted", "cancel_end": None}
        else:
            conn.execute("UPDATE class_cancellations SET cancel_end = ? WHERE id = ?", (last.isoformat(), cancellation_id))
            result = {"action": "shortened", "cancel_end": last.isoformat()}
        conn.commit()
    finally:
        conn.close()
    result.update(id=cancellation_id, class_id=row["class_id"])
    try:
        log_admin_action("shorten_cancellation", "class_def", row["class_id"],
                         details=f"Cancellation {cancellation_id} ({row['cancel_start']} to {row['cancel_end']}): "
                                 f"{result['action']}, now ends {result['cancel_end']}")
    except Exception:
        pass
    return result


def _give_back_plan(row) -> Dict[str, Any]:
    """What "Remove all" does to one cancellation row (nothing is written): lessons that have ended (by date, and for
    today by end time) stay cancelled; every other lesson in the range comes back."""
    cls = get_class_def(row["class_id"])
    dow = cls.get("day_of_week") if cls else None
    start, end = date.fromisoformat(row["cancel_start"]), date.fromisoformat(row["cancel_end"])
    lessons = _lesson_dates_between(dow, start, end) if dow is not None else []
    kept = [x for x in lessons if _lesson_has_ended(cls, x)]
    restored = [x for x in lessons if x not in kept]
    today = date.today()
    keep_through = today if (dow is not None and today.weekday() == dow and _lesson_has_ended(cls, today)) \
        else today - timedelta(days=1)
    if end <= keep_through:
        action = "unchanged"
    elif kept:
        action = "shortened"
    else:
        action = "deleted"
    return {"id": row["id"], "class_id": row["class_id"], "action": action, "keep_through": keep_through,
            "kept": [x.isoformat() for x in kept], "restored": [x.isoformat() for x in restored]}


def _cancellation_row(cancellation_id):
    _ensure_cancellations_table()
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM class_cancellations WHERE id = ?", (cancellation_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValidationError(f"No cancellation with id {cancellation_id!r}")
    return row


def give_back_preview(cancellation_id: int) -> Dict[str, Any]:
    """What "Remove all" would do to this cancellation, without doing it: {"action": "shortened" | "deleted" |
    "unchanged", "kept": [ISO lesson dates that have ended and stay cancelled], "restored": [ISO lesson dates that
    come back], "id", "class_id"}."""
    plan = _give_back_plan(_cancellation_row(cancellation_id))
    plan.pop("keep_through")
    return plan


def remove_cancellation_from_today(cancellation_id: int) -> Dict[str, Any]:
    """"Remove all": give back every lesson that has not ended, and keep the lessons that have ended cancelled (by
    date and, for today's lesson, by its end time). The range is shortened to the last day that has ended; if no
    lesson in it has ended the row is deleted. Returns {"action": "shortened" | "deleted" | "unchanged", ...}."""
    row = _cancellation_row(cancellation_id)
    plan = _give_back_plan(row)
    if plan["action"] == "unchanged":
        return {"action": "unchanged", "id": cancellation_id, "class_id": row["class_id"], "cancel_end": row["cancel_end"]}
    if plan["action"] == "shortened":
        return shorten_cancellation(cancellation_id, plan["keep_through"].isoformat())
    uncancel_class(cancellation_id)
    return {"action": "deleted", "id": cancellation_id, "class_id": row["class_id"], "cancel_end": None}


def restore_cancelled_lessons(cancellation_id: int, from_date: str) -> Dict[str, Any]:
    """Restore the lesson on from_date and every later lesson of one cancellation; the lessons before it stay
    cancelled. from_date must be one of the cancellation's lesson dates. Uses shorten_cancellation."""
    _ensure_cancellations_table()
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM class_cancellations WHERE id = ?", (cancellation_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValidationError(f"No cancellation with id {cancellation_id!r}")
    cls = get_class_def(row["class_id"])
    dow = cls.get("day_of_week") if cls else None
    start, end = date.fromisoformat(row["cancel_start"]), date.fromisoformat(row["cancel_end"])
    dates = [d.isoformat() for d in _lesson_dates_between(dow, start, end)] if dow is not None else []
    if from_date not in dates:
        raise ValidationError(f"{from_date} is not one of this cancellation's lessons ({', '.join(dates) or 'none'})")
    if _lesson_has_ended(cls, date.fromisoformat(from_date)):
        raise ValidationError(f"The lesson on {from_date} has already ended, so it stays cancelled.")
    before = [d for d in dates if d < from_date]
    last = before[-1] if before else (start - timedelta(days=1)).isoformat()
    return shorten_cancellation(cancellation_id, last)


def get_active_cancellations(class_id: str = None) -> List[Dict[str, Any]]:
    """Get cancellations where today is between cancel_start and cancel_end."""
    _ensure_cancellations_table()
    today = date.today().isoformat()
    conn = get_connection()
    cur = conn.cursor()

    if class_id:
        cur.execute(
            """SELECT * FROM class_cancellations
               WHERE class_id = ? AND cancel_start <= ? AND cancel_end >= ?
               ORDER BY cancel_end DESC""",
            (class_id, today, today),
        )
    else:
        cur.execute(
            """SELECT * FROM class_cancellations
               WHERE cancel_start <= ? AND cancel_end >= ?
               ORDER BY cancel_end DESC""",
            (today, today),
        )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def is_class_cancelled(class_id: str, check_date: date = None) -> bool:
    """Return True if any active cancellation covers the given date (default: today)."""
    _ensure_cancellations_table()
    if check_date is None:
        check_date = date.today()
    d = check_date.isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT 1 FROM class_cancellations
           WHERE class_id = ? AND cancel_start <= ? AND cancel_end >= ?
           LIMIT 1""",
        (class_id, d, d),
    )
    found = cur.fetchone() is not None
    conn.close()
    return found


def get_all_cancellations() -> List[Dict[str, Any]]:
    """Get all cancellations (active and expired), ordered by cancel_end DESC."""
    _ensure_cancellations_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT cc.*, cd.class_name
           FROM class_cancellations cc
           LEFT JOIN class_def cd ON cc.class_id = cd.class_id
           ORDER BY cc.cancel_end DESC"""
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]
