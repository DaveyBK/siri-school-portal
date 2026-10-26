r"""
Set the School Portal's username and passwords. Run by hand in a terminal, from the school_portal folder:

    C:\Python313\python.exe scripts\set_portal_password.py

Use it after installing bcrypt (first time), or when the portal says it is locked (see PASSWORD_RECOVERY.md). It
says which Python it is running under, then asks for the username, the login password twice and the admin password
twice. The two passwords must differ. Nothing you type is shown, and no password or hash is ever printed. It
writes data\credentials.json through inventory\auth.py (bcrypt hashes, login required). If the file cannot be
written it says so and changes nothing.

This replaces scripts\migrate_passwords.py, which looked in the wrong folder.
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from inventory import auth


def _twice(label):
    first = getpass.getpass(f"{label}: ")
    second = getpass.getpass(f"{label} again: ")
    return first if first == second else None


def main():
    print(f"Python: {sys.executable}")
    print(f"Password file: {auth.CREDENTIALS_PATH}")
    username = input("Username: ").strip()
    login_pw = _twice("Login password")
    if login_pw is None:
        print("The login passwords did not match. Nothing was written.")
        return 1
    admin_pw = _twice("Admin password")
    if not admin_pw:
        print("The admin passwords did not match, or were empty. Nothing was written.")
        return 1
    try:
        auth.set_passwords(login_pw, admin_pw, username=username)
    except ValueError as e:
        print(f"Nothing was written: {e}")
        return 1
    except auth.CredentialsError as e:
        print(f"Nothing was written: {e.user_message}")
        return 1
    except OSError as e:
        print(f"Nothing was written: the password file could not be saved ({e.strerror or e}). "
              "Close the portal, check that the password file in the data folder is not read-only, then run this again.")
        return 1
    print("Done. The password file now holds hashed passwords. Start the portal and log in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
