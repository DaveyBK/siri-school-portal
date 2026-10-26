# Handover — Schedule form and class_def rebuild

Completed 2026-09-16. Spec: `student_photos/BUILD_SCHEDULE_FORM.md`.
Classes are now entered in the portal (Schedule tab → Classes), not by CSV seed.

## Migrations (`inventory/db_schema.py`)
- **9 — `add_class_level_table`**: new table `class_level (level_code PK, level_name, series, sort_order, is_active)`, seeded with 16 levels, sort 1–16: SM1–SM6, OP1–OP4, EF-ELEM, EF-PRE, EF-INT, EF-INTP, IELTS-A, IELTS-G. Unlike migrations 2–8, a failure raises and is not recorded as applied.
- **10 — `add_standalone_class_levels`**: WRITE (Writing), READ (Reading), PRE (Pre-school), sort 17–19. These are standalone class types, not tiers.
- Both use `INSERT OR IGNORE` and are safe to re-run. `class_def` / `class_roster` columns are unchanged.

## class_id scheme
`{level_code}-{NN}` — e.g. `SM1-02`, `EF-INT-01`, `PRE-01`. The number is the highest existing one for that level + 1, counting inactive rows, so an ID is never reused. Day and time are not in the ID: a class keeps its ID when rescheduled. Level is fixed at creation; changing level creates a new class (Move Up a Level). Pre-rebuild IDs such as `sat_1000_sm1` are "old-style" (`is_legacy_class`).

## Model functions (`inventory/models.py`)
| Function | Purpose |
|---|---|
| `list_class_levels`, `next_class_id` | Level dropdown; preview of the next ID |
| `create_class` | Class + roster in one transaction; `teacher` defaults to 'David' |
| `update_class` | Day, time, label, teacher, optional roster — in place; never changes ID or level |
| `set_class_roster` | Reconcile roster: removals set `removed_at`, re-adding reuses the row |
| `deactivate_class` | `is_active = 0`; never deletes |
| `promote_class` | New class at a new level, same day/time/active roster; old one deactivated, its roster untouched |
| `is_legacy_class`, `can_move_up`, `STANDALONE_LEVELS` | Old-style rows and standalone types can't be edited/moved up; nothing moves up into a standalone type |
| `check_class_times`, `list_classes_with_counts`, `find_clashes` | Strict `HH:MM` (leading zero, end after start); list with student counts; overlap warning (ignores old-style rows) |

`update_class_def` was removed (it had no callers). Unchanged by this build: `add_class_def`, `delete_class_def`, `seed_classes_from_csv` (its grid path still has a pre-existing broken `list_students(active_only=True)` call), and both `get_class_for_now()`.
UI: `ui/schedule_tab.py` — `ClassDialog`, `PromoteDialog`, Classes section of `ScheduleTab`.

## Old rows: retired, not deleted
All 36 old-style `class_def` rows were deactivated through the form on 2026-09-15 (12:54–15:19 UTC). The rows and their 58 `class_roster` rows remain as attendance/lesson history. The 9 `class_cancellations` rows reference old IDs, were all expired, and were not migrated. There is no UI to reactivate a class.

## Known defect — pre-existing, Zone B
`D:\zone_b\portal\school_db.py` `get_class_for_now()` picks the class whose midpoint is nearest (±30 min buffer). On **Sunday 10:00–10:15** it returns **EF-PRE-01** (09:00–10:00) instead of **EF-INT-02** (10:00–12:00), because a 2-hour class's midpoint is an hour in. The old rows had the same times and the same fault. `data/roster_bridge.py` is wrong only at exactly 10:00. Not changed here (spec constraint). Recordings made in that window may be filed against EF-PRE-01.

## Backups (`data/`)
- **`inventory.db.post_schedule_rebuild_20260916`** — restore point for the schedule. SHA-256 `40beabbc1cf3d05d4e70dd15d8b214e148902d7f0a323b85798c609c1b593122`, schema 10, 73 class_def (36 active), 124 class_roster, 70 students. It predates the student edits made from 2026-09-15 17:50 UTC (below); restoring it would undo them. Take a fresh backup once the remaining students are placed.
- `inventory.db.pre010` — before the build (schema 8). **Do not restore**: it would erase the new schedule and the student changes of 2026-09-15.

## Open data items (checked 2026-09-16)
- Resolved: [student1] (`20000101`) now SM6, in SM6-03. [student2], [student3] and [student4] set inactive. [student5]'s level OP2 → SM1 and [student6]'s PRE → OP1, now matching their classes. No class or roster rows changed.
- **Still open:** 4 active students are on no class — [student7] (SM1), [student8] (SM5), [student9] (OP2), [student10] (IELTS-A). Their old classes (`sat_0800_sm1`, `sat_1600_sm4`, `mon_1610_phonics2`, `sat_1400_ielts`) have no new equivalent.
