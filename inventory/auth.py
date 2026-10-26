r"""
The only code that reads or writes the portal's password file (data\credentials.json).

Passwords are stored as bcrypt hashes and checked with bcrypt only. There are no built-in passwords: if the file
is missing, unreadable, incomplete, not hashed, or bcrypt is not installed for this interpreter, every check
fails closed (CredentialsError, or False for login_required()'s "yes, log in").

Recovery when locked out: scripts\set_portal_password.py, run by hand in a terminal (see PASSWORD_RECOVERY.md in the
school_portal folder).
"""

import json
import os
import sys
from pathlib import Path

from inventory import password_utils
from inventory.validation import validate_password, validate_username

CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "data" / "credentials.json"

LOCKED_MESSAGE = (
    "The portal is locked: the password file is missing or unreadable. "
    "See PASSWORD_RECOVERY.md in the school_portal folder."
)

SAME_PASSWORD_MESSAGE = "The login password and the admin password must be different."

# bcrypt only looks at the first 72 bytes; a longer password is refused rather than silently cut.
MAX_PASSWORD_BYTES = 72


class CredentialsError(Exception):
    """The password file cannot be used. str(e) is the technical reason; e.user_message is for the screen."""

    def __init__(self, reason, user_message=LOCKED_MESSAGE):
        super().__init__(reason)
        self.user_message = user_message


def _read_raw():
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise CredentialsError("the password file is missing")
    except (OSError, ValueError) as e:
        raise CredentialsError(f"the password file cannot be read ({type(e).__name__})")
    if not isinstance(data, dict):
        raise CredentialsError("the password file is not a JSON object")
    return data


def _need_bcrypt():
    if not password_utils.BCRYPT_AVAILABLE:
        raise CredentialsError(
            "bcrypt is not installed",
            user_message=f"bcrypt is not installed for {sys.executable}. The portal cannot check passwords. "
                         "See PASSWORD_RECOVERY.md in the school_portal folder.",
        )


def load():
    """The password file as a dict, or CredentialsError. Both passwords must be bcrypt hashes."""
    _need_bcrypt()
    data = _read_raw()
    for key in ("username", "password", "admin_password"):
        if not isinstance(data.get(key), str) or not data[key]:
            raise CredentialsError(f"'{key}' is missing from the password file")
    for key in ("password", "admin_password"):
        if not password_utils.is_password_hashed(data[key]):
            raise CredentialsError(f"'{key}' in the password file is not a bcrypt hash")
    return data


def verify(kind, password):
    """True if `password` is the stored one. kind is "login" or "admin". Raises CredentialsError when locked."""
    if kind not in ("login", "admin"):
        raise ValueError(f"kind must be 'login' or 'admin', not {kind!r}")
    data = load()
    if not isinstance(password, str) or not password:
        return False
    return password_utils.verify_password(password, data["password" if kind == "login" else "admin_password"])


def login_required():
    """Whether the startup login is shown. True on any problem with the file (fail closed)."""
    try:
        return load().get("login_required", True) is not False
    except CredentialsError:
        return True


def _write_atomic(data):
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CREDENTIALS_PATH.with_name(CREDENTIALS_PATH.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, CREDENTIALS_PATH)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _checked(label, password):
    ok, message = validate_password(password, min_length=6)
    if not ok:
        raise ValueError(f"{label}: {message}")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"{label}: must be {MAX_PASSWORD_BYTES} bytes or fewer")


def set_passwords(login_pw, admin_pw=None, username=None):
    """Validate, hash and write the password file. Raises ValueError (nothing written) or CredentialsError.

    admin_pw empty or None keeps the current admin hash. username None keeps the current one. The login and admin
    passwords must differ (ValueError). login_required is always written true, whatever the old file said; only
    set_login_required() turns it off. Works when the file is missing or plain text, which is how the recovery
    tool replaces it. OSError (a file that cannot be written) is not caught here: nothing has changed on disk.
    """
    _need_bcrypt()
    try:
        old = _read_raw()
    except CredentialsError:
        old = {}
    if username is None:
        username = old.get("username") if isinstance(old.get("username"), str) else ""
    ok, message = validate_username(username)
    if not ok:
        raise ValueError(f"Username: {message}")
    _checked("Login password", login_pw)
    if admin_pw:
        _checked("Admin password", admin_pw)
        if admin_pw == login_pw:
            raise ValueError(SAME_PASSWORD_MESSAGE)
        admin_hash = password_utils.hash_password(admin_pw)
    else:
        admin_hash = old.get("admin_password")
        if not (isinstance(admin_hash, str) and password_utils.is_password_hashed(admin_hash)):
            raise ValueError("Admin password: there is no current admin password to keep, so one is needed")
        if password_utils.verify_password(login_pw, admin_hash):
            raise ValueError(SAME_PASSWORD_MESSAGE)
    _write_atomic({
        "username": username,
        "password": password_utils.hash_password(login_pw),
        "admin_password": admin_hash,
        "login_required": True,
    })


def set_login_required(flag):
    """Change only login_required. Never creates the file: CredentialsError if it is not a usable one."""
    data = load()
    data["login_required"] = bool(flag)
    _write_atomic(data)
