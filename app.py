from inventory import auth, runmode
from inventory.db import init_db, db_exists
from ui import theme
from ui.login import LoginWindow
from ui.main_window import MainWindow
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

# Built from this file, not the working folder, so the icon is found however the portal is started (B5b-17)
_ICON = Path(__file__).resolve().parent / "siri_english_clean_circle.ico"


def check_login_required():
    """Whether the startup login is shown. inventory\\auth.py decides; any problem with the password file means yes."""
    return auth.login_required()


def _set_icon(window):
    """The Siri English icon on this window and, as its default, on every dialog it opens (B5b-17)."""
    try:
        window.iconbitmap(default=str(_ICON))
    except Exception as e:
        print("Could not load icon:", e)


def _refuse_to_start(message):
    """Say why the app will not start, then exit."""
    print(f"{runmode.MODE_NAME}: refusing to start.\n" + message, file=sys.stderr)
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(f"{runmode.MODE_NAME}: refusing to start", message, parent=root)
        root.destroy()
    except Exception:
        pass
    sys.exit(1)


def _enforce_run_mode():
    """Test mode only: guard 1 (marker in the live folder) and guard 2 (every data path inside the sandbox)."""
    if not runmode.TEST_MODE:
        return
    try:
        runmode.check(())
        from inventory import db as inventory_db
        from ui import lessons_tab, main_window, tutorial_system_simple
        ctest_config = runmode.load_ctest_config()
        runmode.check([
            inventory_db.DB_PATH,
            main_window._CTEST_DB,
            main_window._CTEST_MAIN,
            lessons_tab._SCHOOL_DB,
            ctest_config.DB_PATH,
            ctest_config.INVENTORY_DB_PATH,
            tutorial_system_simple.progress_file_path(),
        ])
    except runmode.RunModeError as e:
        _refuse_to_start(str(e))


def main():
    _enforce_run_mode()

    # Make the process DPI aware before any Tk root exists. No-op when
    # PORTAL_THEME=classic. See ui/theme.py.
    theme.enable_dpi_awareness()

    # Ensure DB exists
    if not db_exists():
        print("Database not found. Creating a new one...")
        init_db()
    else:
        print("Database found. Ready to go.")

    # One pass per login: Logout comes back here; Exit, the window's X or a closed login window ends the program
    # (B5b-4). Each window is its own Tk root and is gone before the next one is built.
    first_pass = True
    while True:
        # Read on every pass, so a setting changed in the portal counts at the next Logout
        if check_login_required():
            login = LoginWindow()
            _set_icon(login)
            login.mainloop()
            if not getattr(login, "authenticated", False):
                return                          # closed without logging in
        elif not first_pass:
            return                              # no login needed: Logout behaves as Exit (David, 13 Oct)
        first_pass = False

        app = MainWindow()
        _set_icon(app)
        app.mainloop()
        if not getattr(app, "logged_out", False):
            return                              # Exit or the window's X


if __name__ == "__main__":
    main()
