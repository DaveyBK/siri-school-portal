"""
Event logging system for inventory operations.

Provides event tracking for QR scans, assignments, and other operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any


def log_event(
    event_name: str,
    student_id: Optional[str] = None,
    item_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an event in the system.

    Args:
        event_name: Name of the event (e.g., "qr_scan_student_hardware_scanner")
        student_id: Optional student ID associated with event
        item_id: Optional item ID associated with event
        payload: Optional additional data for the event
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # For now, just print to console
    # In the future, this could write to a database or log file
    event_info = f"[{timestamp}] EVENT: {event_name}"

    if student_id:
        event_info += f" | Student: {student_id}"

    if item_id:
        event_info += f" | Item: {item_id}"

    if payload:
        event_info += f" | Data: {payload}"

    print(event_info)


# Future expansion: Could add event listeners, database logging, analytics, etc.
