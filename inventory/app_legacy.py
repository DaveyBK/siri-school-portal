"""
LEGACY FILE - NOT USED
This is an older version of the app.py entry point.
The main entry point is now: /app.py (root directory)
Kept for reference only.
"""

from inventory.db import init_db, db_exists
from ui.login import LoginWindow
from ui.main_window import MainWindow
from inventory import auth
import tkinter as tk


def check_login_required():
    """Whether the login is shown. inventory/auth.py decides; any problem with the password file means yes."""
    return auth.login_required()


def main():
    # Ensure DB exists
    if not db_exists():
        print("Database not found. Creating a new one...")
        init_db()
    else:
        print("Database found. Ready to go.")

    # Check if login is required
    login_required = check_login_required()
    authenticated = False

    # Only show login window if login is required
    if login_required:
        while True:
            login = LoginWindow()
            login.mainloop()
            
            # If authenticated, show main app
            if login.authenticated:
                authenticated = True
                break
            else:
                # User closed login without authenticating
                break
    else:
        # Login not required, proceed directly to main app
        authenticated = True
    
    # Show main app if authenticated
    if authenticated:
        app = MainWindow()

        # --- Set Siri English icon ---
        try:
            app.iconbitmap("siri_english_clean_circle.ico")
        except Exception as e:
            print("Could not load icon:", e)

        app.mainloop()


if __name__ == "__main__":
    main()
