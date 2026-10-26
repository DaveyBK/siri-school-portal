"""
QR Scanner Hardware Integration Module

This module provides hardware QR scanner integration for the School Portal system.
Currently supports USB HID keyboard wedge scanners.

Module Architecture:
- scanner_interface.py: Main interface for connecting scanner to UI
- hid_scanner.py: HID keyboard wedge scanner implementation
- scanner_config.json: Configuration settings

Input: Physical QR code scans from hardware device
Output: Scanned QR code content passed to application's process_qr_code() handler

Communication: Event-based callbacks, no tight coupling to main application
"""

from .scanner_interface import ScannerInterface
from .hid_scanner import HIDScannerHandler

__all__ = ['ScannerInterface', 'HIDScannerHandler']
