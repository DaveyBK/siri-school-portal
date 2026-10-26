# Portal Changelog

Dated record of changes to the School Portal desktop app (Zone A).
Known defects live in `PORTAL_UI_ISSUES.md`; this file records what changed.

---

## Session 2026-09-19 — House-style pilot on the System tab

**Status: VERIFIED** by `py_compile` under `C:\Python313\python.exe` and by geometry
measurement on an off-screen Tk root. **The GUI was not launched by the assistant** — David
launches and reviews.

### What changed

- **New `ui/theme.py`** — house palette, DPI awareness, named ttk styles, button factory.
  Plain `ttk.Style` on the **`clam`** base theme. **No ttkbootstrap**: the package was
  evaluated and declined, because the native Windows ttk themes ignore button background
  colours, which the Start/Stop status mapping depends on, and clam does not.
- **Palette in `ui/design_system.py`** as the single source of truth — primary green
  `#035737`, accent orange `#F59221`, fill-only yellow `#FED600`, deep red `#B02020`, cream
  panels `#F5F1E4`. Status mapping preserved: RUNNING/UP/Start green, STOPPED/DOWN/Stop red,
  warnings orange. Existing constants left untouched so other tabs are unaffected.
- **DPI awareness** set process-wide before the first Tk root (system-aware, level 1).
- **Segoe UI** for UI text, **Georgia** for the header title only, Consolas for the error log.
- **Two-column responsive layout** on the System tab, replacing a fixed 515px column that
  left 73% of the window empty.
- **Mousewheel drift fix.** `bind_all("<MouseWheel>")` is application-wide and had no
  "content fits" guard, so a wheel event anywhere in the portal could push the tab's content
  down and leave a blank band under the header. Guarded.
- **Visible neutral buttons.** Log/Browse/Refresh/dialog-toggle were cream on cream with no
  border — invisible. Now a 1px `#D8D3C4` outline with a white fill and green outline on hover.
- **Dark mode retired.** The View-menu entry was removed. It only ever restyled ttk frames,
  listboxes and menus, leaving every tk panel light, and was never persisted across launches.
  `toggle_dark_mode()` and `DARK_THEME` remain in the code, unreachable.
- **`PI5_IP` corrected** in `ui/system_tab.py` to `192.168.10.31`.

### Off switch

Set `PORTAL_THEME=classic`, or choose **option [6]** in `Launch_Pear_Advanced.bat`. This
restores the pre-2026-09-19 appearance exactly, DPI awareness included — verified by comparing
measured geometry against the backup files. Options [1] and [2] clear the variable, so you can
switch back within one launcher session.

### Backups

`.bak-2026-09-19` (pilot) and `.bak-2026-09-19b` (layout and button fixes) alongside each
edited file. A full revert is: restore the backups and delete `ui/theme.py`.

### Not done

Phase 4 — rolling the house style out to the remaining tabs — was proposed but **not started**.
`main_window.py` is the notable one: 67 ttk widgets pick up the theme while 213 tk widgets keep
their hard-coded flat-UI colours, so it will look mixed until it is done.
