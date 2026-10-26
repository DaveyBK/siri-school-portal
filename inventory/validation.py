"""
Input validation utilities for security and data integrity.
"""

import re
from typing import Tuple, Optional


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate username format.

    Rules:
    - Must be 3-50 characters
    - Alphanumeric, underscore, hyphen only
    - Must start with letter or number

    Returns:
        (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 50:
        return False, "Username must be 50 characters or less"

    # Allow alphanumeric, underscore, hyphen
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', username):
        return False, "Username can only contain letters, numbers, underscore, and hyphen"

    return True, None


def validate_password(password: str, min_length: int = 6) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength.

    Rules:
    - Must meet minimum length (default 6)
    - Maximum 128 characters (bcrypt limit)
    - Cannot be empty or only whitespace

    Returns:
        (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"

    if password != password.strip():
        return False, "Password cannot start or end with whitespace"

    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters"

    if len(password) > 128:
        return False, "Password must be 128 characters or less"

    return True, None


def validate_student_id(student_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate student ID format.

    Rules:
    - Must be 1-50 characters
    - Alphanumeric, underscore, hyphen only
    - Cannot be empty or only whitespace

    Returns:
        (is_valid, error_message)
    """
    if not student_id:
        return False, "Student ID cannot be empty"

    student_id = student_id.strip()

    if len(student_id) < 1:
        return False, "Student ID cannot be empty"

    if len(student_id) > 50:
        return False, "Student ID must be 50 characters or less"

    # Allow alphanumeric, underscore, hyphen
    if not re.match(r'^[a-zA-Z0-9_-]+$', student_id):
        return False, "Student ID can only contain letters, numbers, underscore, and hyphen"

    return True, None


def validate_item_id(item_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate item ID format.

    Rules:
    - Must be 1-50 characters
    - Alphanumeric, underscore, hyphen only
    - Cannot be empty or only whitespace

    Returns:
        (is_valid, error_message)
    """
    if not item_id:
        return False, "Item ID cannot be empty"

    item_id = item_id.strip()

    if len(item_id) < 1:
        return False, "Item ID cannot be empty"

    if len(item_id) > 50:
        return False, "Item ID must be 50 characters or less"

    # Allow alphanumeric, underscore, hyphen
    if not re.match(r'^[a-zA-Z0-9_-]+$', item_id):
        return False, "Item ID can only contain letters, numbers, underscore, and hyphen"

    return True, None


def validate_name(name: str, field_name: str = "Name") -> Tuple[bool, Optional[str]]:
    """
    Validate person/item name.

    Rules:
    - Must be 1-100 characters
    - Cannot be empty or only whitespace
    - Allow letters, numbers, spaces, basic punctuation

    Returns:
        (is_valid, error_message)
    """
    if not name:
        return False, f"{field_name} cannot be empty"

    name = name.strip()

    if len(name) < 1:
        return False, f"{field_name} cannot be empty"

    if len(name) > 100:
        return False, f"{field_name} must be 100 characters or less"

    # Allow letters, numbers, spaces, and common punctuation
    if not re.match(r'^[a-zA-Z0-9\s\.,\-\']+$', name):
        return False, f"{field_name} contains invalid characters"

    return True, None


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize general text input.

    - Strips leading/trailing whitespace
    - Removes null bytes
    - Truncates to max_length

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace('\x00', '')

    # Strip whitespace
    text = text.strip()

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]

    return text


_LINE_ID_SHAPE = re.compile(r"^U[0-9a-f]{32}$")


def validate_line_id(line_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a parent's LINE user ID: "U" followed by 32 lowercase hex digits (the shape Zone B expects).

    Returns:
        (is_valid, error_message)
    """
    if isinstance(line_id, str) and _LINE_ID_SHAPE.match(line_id):
        return True, None
    return False, ("A LINE user ID starts with U followed by 32 characters (0-9, a-f). "
                   "The chat ID from LINE Official Account Manager is a different ID.")
