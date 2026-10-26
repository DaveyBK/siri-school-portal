"""
HID Keyboard Wedge Scanner Handler

Handles USB barcode/QR scanners that act as HID keyboard devices.
These scanners "type" the scanned content as if it were keyboard input.

INPUT: Keyboard events from Tkinter widget (scanner types characters)
OUTPUT: Complete scanned QR code string after terminator (usually Enter key)

How it works:
1. Scanner is plugged in via USB (no drivers needed, works as keyboard)
2. When QR code is scanned, scanner rapidly types the content
3. Scanner sends terminator key (usually Enter/Return)
4. This handler accumulates the characters and triggers callback on terminator
"""

import tkinter as tk
import time
from typing import Callable, Optional
import json
from pathlib import Path


class HIDScannerHandler:
    """
    Handles HID keyboard wedge scanner input.

    This class binds to a Tkinter widget and captures rapid keyboard input
    from the scanner device, distinguishing it from regular user typing.
    """

    def __init__(self, widget: tk.Widget, callback: Callable[[str], None],
                 config_path: Optional[Path] = None):
        """
        Initialize HID scanner handler.

        Args:
            widget: Tkinter widget to bind keyboard events to (usually root window)
            callback: Function to call with scanned QR code content
            config_path: Path to scanner_config.json (optional)
        """
        self.widget = widget
        self.callback = callback
        self.enabled = True

        # Load configuration
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            # Default configuration
            self.config = {
                "input_settings": {
                    "terminator": "Return",
                    "debounce_ms": 100,
                    "min_length": 3,
                    "max_length": 100,
                    "min_scan_duration_ms": 50
                },
                "validation": {
                    "require_prefix": False,
                    "valid_prefixes": ["I:", "S:"]
                }
            }

        # Scanner input buffer
        self.buffer = ""
        self.last_char_time = 0
        self.scan_start_time = 0

        # Bind keyboard events
        self._bind_events()

    def _bind_events(self):
        """Bind keyboard events to widget."""
        # Bind key press event with high priority
        # Use bind_all to capture even when focus is elsewhere
        self.widget.bind_all('<Key>', self._on_key_press, add='+')

    def _on_key_press(self, event):
        """
        Handle key press event.

        Scanner characteristics:
        - Very rapid input (< 50ms between characters)
        - Consistent terminator key (usually Return/Enter)
        - No modifier keys (Ctrl, Alt, etc.)
        """
        if not self.enabled:
            return

        current_time = time.time() * 1000  # milliseconds

        # Get the key that was pressed
        key = event.keysym
        char = event.char

        # Ignore modifier keys
        if key in ('Shift_L', 'Shift_R', 'Control_L', 'Control_R',
                   'Alt_L', 'Alt_R', 'Super_L', 'Super_R'):
            return

        # Check for terminator key
        terminator = self.config['input_settings'].get('terminator', 'Return')
        if key == terminator:
            if self.buffer:
                self._process_scan()
            return

        # Ignore empty characters, non-printable, and non-ASCII characters
        # This filters out special characters like "♪" and control characters
        if not char or char == '' or not char.isprintable() or ord(char) > 127:
            return

        # Check if this is part of a rapid scan
        debounce_ms = self.config['input_settings'].get('debounce_ms', 100)

        if self.buffer == "":
            # Starting new scan
            self.scan_start_time = current_time
            self.buffer = char if char else ""
        else:
            # Check if characters are coming in rapidly (likely scanner)
            time_since_last = current_time - self.last_char_time

            if time_since_last < debounce_ms:
                # Rapid input - likely from scanner, continue accumulating
                self.buffer += char if char else ""
            else:
                # Slow input detected - check if we should reset or continue
                scan_duration = current_time - self.scan_start_time

                # If scan is very short (< 500ms) or buffer is very small, likely human typing
                if scan_duration < 500 or len(self.buffer) < 3:
                    # Reset for new input sequence
                    self.buffer = char if char else ""
                    self.scan_start_time = current_time
                else:
                    # Long scan with slow input - might be legitimate but slow scanner
                    # Continue accumulating but log the timing anomaly
                    self.buffer += char if char else ""
                    print(f"Scanner: Slow input detected in ongoing scan ({time_since_last}ms gap)")

        self.last_char_time = current_time

    def _process_scan(self):
        """Process the accumulated scan buffer."""
        scanned_content = self.buffer.strip()
        self.buffer = ""

        # Strip configured scanner suffixes (common scanner artifacts)
        suffix_filter = self.config['input_settings'].get('suffix_filter', '')
        if suffix_filter:
            for suffix_char in suffix_filter:
                scanned_content = scanned_content.rstrip(suffix_char)

        # Remove any remaining non-ASCII characters as a safety measure
        scanned_content = ''.join(c for c in scanned_content if ord(c) < 128)

        # Validate scan duration (prevent extremely fast "scans" that might be noise)
        scan_duration = time.time() * 1000 - self.scan_start_time
        min_scan_duration = self.config['input_settings'].get('min_scan_duration_ms', 50)  # Default 50ms

        if scan_duration < min_scan_duration:
            print(f"Scanner: Rejected scan (too fast, {scan_duration:.0f}ms): {scanned_content}")
            return

        # Validate length
        min_len = self.config['input_settings'].get('min_length', 3)
        max_len = self.config['input_settings'].get('max_length', 100)

        if len(scanned_content) < min_len or len(scanned_content) > max_len:
            print(f"Scanner: Rejected scan (invalid length): {scanned_content}")
            return

        # Validate prefix if required
        if self.config['validation'].get('require_prefix', False):
            valid_prefixes = self.config['validation'].get('valid_prefixes', [])
            if not any(scanned_content.startswith(p) for p in valid_prefixes):
                print(f"Scanner: Rejected scan (invalid prefix): {scanned_content}")
                return

        # Valid scan - call callback
        print(f"Scanner: Valid scan detected: {scanned_content}")
        try:
            self.callback(scanned_content)
        except Exception as e:
            print(f"Scanner: Error in callback: {e}")

    def enable(self):
        """Enable scanner input."""
        self.enabled = True
        print("Scanner: Enabled")

    def disable(self):
        """Disable scanner input."""
        self.enabled = False
        self.buffer = ""
        print("Scanner: Disabled")

    def unbind(self):
        """Unbind all events (cleanup)."""
        try:
            self.widget.unbind_all('<Key>')
        except:
            pass
