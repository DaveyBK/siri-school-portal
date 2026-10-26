# INSTRUCTION: Add Extra Lesson to School Portal

**Audit timestamp:** 2026-03-12  
**Author:** David (via Claude conversation)  
**Status:** Ready for Claude Code

---

## Persona

**UI-aware database engineer** — you understand Tkinter layout, SQLite schema migration, and how the school portal's existing tabs and models work together.

---

## Direct Aim

Add a UI function to the school portal (Tkinter) that lets the teacher schedule a **one-off extra lesson** on a specific date and time, assign students to it, and persist it to `inventory.db` so that Zone B can also read it.

## Overall Aim

The weekly schedule in `class_def` represents the recurring timetable. But the teacher sometimes needs to add a single extra lesson outside the regular pattern — a makeup class, a special session, a test prep group. This must not contaminate the recurring schedule. It must be visible to Zone B's `roster_bridge.py` so the audio pipeline can match recordings to lessons on that date.

---

## Mandatory Read-First

Before writing any code, read these files completely:

1. `ZONE_B_BACKEND_INSTRUCTION_MANUAL.md`
2. `PROGRAM_MAP.md`
3. `inventory/db_schema.py` — understand the current migration system
4. `inventory/models.py` — understand existing CRUD patterns
5. `data/roster_bridge.py` — understand `get_class_for_now()` logic
6. `ui/schedule_tab.py` — understand the current schedule UI
7. `ui/main_window.py` — understand tab registration

**STOP after reading. Confirm to David what you found before making any changes.**

---

## Schema Design

### New table: `extra_lesson`

```sql
CREATE TABLE IF NOT EXISTS extra_lesson (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,                  -- Teacher-entered label, e.g. "SM2 Makeup"
    lesson_date TEXT NOT NULL,            -- ISO date: "2026-03-15"
    start_time TEXT NOT NULL,             -- "14:00"
    end_time TEXT NOT NULL,               -- "15:00"
    level TEXT,                           -- Optional: "SM2", "P5", etc.
    notes TEXT,                           -- Optional: teacher notes
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
```

### New table: `extra_lesson_student`

```sql
CREATE TABLE IF NOT EXISTS extra_lesson_student (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extra_lesson_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    FOREIGN KEY (extra_lesson_id) REFERENCES extra_lesson(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id),
    UNIQUE(extra_lesson_id, student_id)
);
```

### Migration

Add this as a new migration step in `db_schema.py`, following the existing migration pattern. Do NOT alter existing tables or migrations.

---

## Models (inventory/models.py)

Add these functions, following the naming and docstring conventions already in the file:

1. `create_extra_lesson(label, lesson_date, start_time, end_time, level=None, notes=None) -> int`
   - Returns the new `extra_lesson.id`

2. `get_extra_lessons_for_date(lesson_date: str) -> list[dict]`
   - Returns all extra lessons on that date

3. `get_extra_lesson_by_id(lesson_id: int) -> dict | None`

4. `delete_extra_lesson(lesson_id: int) -> bool`

5. `assign_student_to_extra_lesson(extra_lesson_id: int, student_id: int) -> bool`

6. `remove_student_from_extra_lesson(extra_lesson_id: int, student_id: int) -> bool`

7. `get_students_for_extra_lesson(extra_lesson_id: int) -> list[dict]`
   - Returns student records (id, first_name, last_name, level) for the given extra lesson

8. `get_extra_lesson_for_datetime(dt: datetime) -> dict | None`
   - Given a datetime, find any extra_lesson where `lesson_date` matches the date AND `start_time <= time <= end_time` (with 15-min buffer either side, matching the buffer logic in `roster_bridge.py`)
   - This is the function Zone B will call

---

## UI: Add to Schedule Tab

Add an "Extra Lessons" section to the existing schedule tab (`ui/schedule_tab.py`). Do NOT create a new tab.

### Layout

Below the existing weekly schedule display, add:

1. **Section header:** "Extra Lessons"
2. **List/treeview** showing upcoming extra lessons: date, time, label, student count
3. **"Add Extra Lesson" button** → opens a dialog:
   - Date picker (or simple entry: YYYY-MM-DD)
   - Start time entry (HH:MM)
   - End time entry (HH:MM)
   - Label entry (free text)
   - Level dropdown (optional, values from existing `class_def` levels)
   - Student picker: two-list transfer pattern:
     - Left list: all active students (from `students` table), filterable by level
     - Right list: assigned students for this lesson
     - Add → / ← Remove buttons between them
   - **Shortcut: "Copy from class" dropdown** — select an existing `class_def` entry, auto-populates the right list with that class's roster from `class_roster`
   - Save / Cancel buttons
4. **"Delete" button** on selected extra lesson (with confirmation dialog)

### Refresh

After add/delete, refresh the extra lessons list. The weekly schedule display must NOT be affected.

---

## Zone B Integration: roster_bridge.py

Modify `get_class_for_now()` (or add a wrapper) so it checks `extra_lesson` FIRST, then falls back to `class_def`.

Logic:
```
1. Get current date + time
2. Query extra_lesson where lesson_date = today AND time is within start_time–end_time (± 15 min buffer)
3. If found: return extra lesson info + students from extra_lesson_student
4. If not found: fall back to existing class_def weekly matching
```

This means if the teacher has both a regular class and an extra lesson at the same time, the extra lesson wins. That's intentional — the extra lesson is the override.

**STOP after implementing roster_bridge.py changes. Confirm to David before proceeding.**

---

## What NOT To Do

- Do NOT modify the `class_def` table or its schema
- Do NOT modify the `class_roster` table or its schema
- Do NOT create a new tab — this lives inside `schedule_tab.py`
- Do NOT change how the existing weekly schedule is displayed or loaded
- Do NOT modify any Zone B files other than `roster_bridge.py`
- Do NOT add recurring/repeat functionality — this is strictly one-off lessons
- Do NOT auto-delete past extra lessons — the teacher may want to see history

---

## Verification

1. Migration runs cleanly on existing `inventory.db` without affecting other tables
2. Can create an extra lesson with date, time, label, and assigned students
3. Extra lesson appears in the schedule tab's extra lessons list
4. Can delete an extra lesson
5. `get_extra_lesson_for_datetime()` correctly returns the lesson during its time window
6. `get_class_for_now()` (or wrapper) returns extra lesson students when one is active
7. Regular weekly schedule still works when no extra lesson is active
8. "Copy from class" shortcut correctly populates students from an existing class roster

---

## Rollback

If anything goes wrong:
- The new tables (`extra_lesson`, `extra_lesson_student`) can be dropped without affecting any existing functionality
- All changes to `models.py` are additive functions — removing them breaks nothing existing
- The `roster_bridge.py` change is a single addition to `get_class_for_now()` — revert that one block
- The schedule tab changes are contained in one section — remove that section

---

## Files Changed

| File | Action | What |
|------|--------|------|
| `inventory/db_schema.py` | MODIFY | Add migration for 2 new tables |
| `inventory/models.py` | MODIFY | Add 8 new functions |
| `data/roster_bridge.py` | MODIFY | Add extra_lesson check to get_class_for_now() |
| `ui/schedule_tab.py` | MODIFY | Add Extra Lessons section with add/delete UI |

No new files. No deleted files.
