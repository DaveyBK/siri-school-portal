"""
Password hashing utilities using bcrypt.
Provides secure password hashing and verification.
"""

from typing import Union

# Try to import bcrypt, but make it optional
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("WARNING: bcrypt not installed. Password hashing disabled.")
    print("Install it with: C:\\Python313\\python.exe -m pip install bcrypt")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password as a UTF-8 string. Raises RuntimeError when bcrypt is not installed:
        a password is never handed back as its own "hash".
    """
    if not password:
        raise ValueError("Password cannot be empty")

    if not BCRYPT_AVAILABLE:
        raise RuntimeError(
            "bcrypt is not installed, so passwords cannot be hashed. "
            "Install it with: C:\\Python313\\python.exe -m pip install bcrypt")

    # Generate salt and hash password
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds is a good balance of security and speed
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: Union[str, bytes]) -> bool:
    """
    Verify a password against a hashed password.

    Args:
        password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    if not password or not hashed_password:
        return False

    if not BCRYPT_AVAILABLE:
        return False  # no plain-text comparison without bcrypt

    try:
        # Convert hashed password to bytes if it's a string
        if isinstance(hashed_password, str):
            hashed_bytes = hashed_password.encode('utf-8')
        else:
            hashed_bytes = hashed_password

        return bcrypt.checkpw(password.encode('utf-8'), hashed_bytes)
    except (ValueError, TypeError):
        return False


def is_password_hashed(password: str) -> bool:
    """
    Check if a password string is already hashed (bcrypt format).

    Args:
        password: Password string to check

    Returns:
        True if the password appears to be a bcrypt hash, False otherwise
    """
    if not password:
        return False

    if not BCRYPT_AVAILABLE:
        # Without bcrypt, assume all passwords are plaintext
        return False

    # Bcrypt hashes start with $2a$, $2b$, or $2y$ and are 60 characters long
    return (
        password.startswith(('$2a$', '$2b$', '$2y$')) and
        len(password) == 60
    )
