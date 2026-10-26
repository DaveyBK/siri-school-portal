# Portal UI — known issues

Recorded during the UI modernisation pilot, 2026-09-19. **Nothing here was
fixed by the pilot.** These are notes for the tab-by-tab rollout.

---

## 1. System tab is identified by a hard-coded index

`ui/main_window.py`, in `_build_notebook()`:

```python
idx = notebook.index(notebook.select())
if idx == 7 and hasattr(self, 'system_tab'):
    self.system_tab.on_tab_selected()
```

Index 7 happens to be the System tab today (students 0, items 1, books 2,
attendance 3, roster 4, schedule 5, lessons 6, **system 7**).

Reordering, adding or removing a tab silently stops the System tab
refreshing when you switch to it. There is no error — the tab just shows
stale data until you press Refresh.

Should compare against `notebook.index(system_frame)` instead of a literal.
Left alone deliberately: it is behaviour, not appearance.

## 2. `COLORS` is declared three times

- `ui/design_system.py` — the intended single source
- `ui/main_window.py` — its own copy of the same eight flat-UI colours
- `ui/system_tab.py` — a third copy

The pilot fixed the third (it now reads from `design_system` via
`ui/theme.py`). The `main_window.py` copy is still a duplicate, and it is
the one the other tabs use.

## 3. `design_system` is imported but barely used

- `ui/roster_tab.py` imports it as `ds` and never uses it — dead import.
- `ui/main_window.py` uses it 5 times, all `ds.FONTS[...]`, never the colours.

## 4. Window centring runs before the content exists

`ui/login.py` used to call `update_idletasks()` and read `winfo_width()`
*before* `_build_login_form()` had run, so it centred against the requested
geometry rather than the real content size.

Fixed in the pilot as a side effect of the DPI work, but recorded because
the same pattern may exist in other dialogs.

## 5. Dark mode is half-implemented

`_apply_theme_recursive()` only touches `tk.Listbox` and `tk.Menu`. The
several hundred hard-coded `bg=`/`fg=` arguments on `tk.Frame`, `tk.Label`
and `tk.Button` are never touched, so dark mode produced dark ttk frames
with light tk panels. It was also never persisted across launches.

The View-menu entry was removed on 2026-09-19. `toggle_dark_mode()` and
`DARK_THEME` remain in the file, unreachable. A real dark mode needs every
hard-coded colour site to become theme-driven first.

## 6. Action buttons are too narrow for their own labels

`ui/system_tab.py` created the service action buttons at `width=8`
characters, but sets `"Starting..."` and `"Stopping..."` (11 characters) on
them at runtime, so the text was clipped.

Fixed for the System tab by the pilot's measured column widths. Worth
checking for the same pattern elsewhere during the rollout.

## 7. Mousewheel handler is bound application-wide and never unbound

`ui/system_tab.py`, in `_build_ui()`:

```python
canvas.bind_all("<MouseWheel>", _on_mousewheel)
```

`bind_all` installs the handler on the whole application, not just this tab,
and it is re-bound every time `_build_ui()` runs. `set_language()`
(`ui/main_window.py:477`) rebuilds the entire notebook, so a new handler is
added on every language switch and the old ones are never removed. Each one
still closes over its own canvas, which by then may have been destroyed.

The 2026-09-19b fix added guards inside the handler (`winfo_ismapped()` and a
"content fits" check), which stops the visible symptom. It did **not** remove
the accumulation. The real fix is to bind `<MouseWheel>` to the canvas and its
children, or to unbind on `<Destroy>`.

## 8. db_schema.py does not match the live database (items, assignments)

Found 2026-09-21 while fixing book checkout. **Recorded, not fixed.**

`inventory/db_schema.py` declares columns and constraints that the live
`data/inventory.db` does not have:

| Table | `db_schema.py` declares | Live database |
|---|---|---|
| `assignments` | `created_at`, `updated_at`, FK to `students`, FK to `items`, `CHECK (status IN ('assigned','returned','lost','damaged'))` | none of the extra columns; both FKs present; **no CHECK** |
| `items` | `created_at`, `updated_at`, `archived_at` | absent — has `qr_code` and `date_added` instead |

A query on `items.archived_at` raises `no such column`.

**Cause.** Both tables were created at schema_version 1 (2025-11-24), before
the `@migration(N)` system existed. `create_assignments_table()`
(`db_schema.py:58`) and the `items` DDL (`:42`) both use
`CREATE TABLE IF NOT EXISTS`, which silently does nothing when the table is
already there — so later edits to the DDL never reached the real database.

**Impact today: none.** The loan functions in `inventory/models.py`
(`assign_item_to_student`, `mark_assignment_returned`,
`get_active_assignments_for_item`, `get_all_assignments`) touch only columns
present in both, and were verified against a copy of the live database on
2026-09-21.

**Risk.** Any new code written from `db_schema.py` rather than from the real
table will fail at runtime. The missing `CHECK` on `assignments.status` also
means an invalid status can be written without complaint.

**Fix, when someone takes it on:** a migration that `ALTER TABLE`s the missing
columns in, rather than further edits to the `CREATE TABLE` blocks, which
cannot take effect on an existing database.
