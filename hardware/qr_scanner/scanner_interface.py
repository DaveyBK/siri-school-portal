"""
Scanner Interface

Main interface for QR scanner hardware integration.
Provides a clean abstraction layer between hardware and application.

INPUTS:
  - Tkinter root widget (for event binding)
  - QR code processor callback function
  - Configuration file path

OUTPUTS:
  - Scanned QR codes passed to callback
  - Status updates (enabled/disabled/error)
  - Scan logs (optional)

RESPONSIBILITIES:
  - Initialize appropriate scanner handler based on config
  - Manage scanner enable/disable state
  - Provide status information
  - Handle errors gracefully
  - Log scans if configured
"""

import json
from pathlib import Path
from typing import Callable, Optional, Dict, Any
import tkinter as tk
from datetime import datetime


class ScannerInterface:
    """
    Main interface for QR scanner hardware.

    This class acts as a facade, hiding hardware-specific details
    from the main application.
    """

    def __init__(self, root: tk.Widget, qr_processor: Callable[[str, str], None],
                 config_path: Optional[Path] = None):
        """
        Initialize scanner interface.

        Args:
            root: Tkinter root window
            qr_processor: Function to process scanned QR codes
                          Signature: qr_processor(content: str, context: str)
            config_path: Path to scanner_config.json
        """
        self.root = root
        self.qr_processor = qr_processor
        self.scanner_handler = None
        self.enabled = False
        self.config: Dict[str, Any] = {}

        # Determine config path
        if config_path is None:
            config_path = Path(__file__).parent / "scanner_config.json"

        self.config_path = Path(config_path)

        # Load configuration
        self._load_config()

        # Initialize scanner if enabled
        if self.config.get('enabled', True):
            self._initialize_scanner()

    def _load_config(self) -> None:
        """Load scanner configuration."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    if isinstance(loaded_config, dict):
                        self.config = loaded_config
                    else:
                        raise ValueError("Config file must contain a JSON object")
            else:
                # Default configuration
                self.config = {
                    "scanner_type": "hid_keyboard_wedge",
                    "enabled": True,
                    "auto_process": True,
                    "logging": {
                        "enabled": True,
                        "log_all_scans": True
                    }
                }
                # Save default config
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Scanner: Error loading config: {e}")
            self.config = {"enabled": False}

    def _initialize_scanner(self):
        """Initialize the appropriate scanner handler based on config."""
        scanner_type = self.config.get('scanner_type', 'hid_keyboard_wedge')

        try:
            print(f"Scanner: Attempting to initialize {scanner_type} scanner...")

            if scanner_type == 'hid_keyboard_wedge':
                from .hid_scanner import HIDScannerHandler

                # Create scanner handler with callback
                self.scanner_handler = HIDScannerHandler(
                    widget=self.root,
                    callback=self._on_scan,
                    config_path=self.config_path
                )
                self.enabled = True
                print(f"Scanner: ✅ HID keyboard wedge scanner initialized successfully")
                print(f"Scanner: Handler type: {type(self.scanner_handler)}")
                print(f"Scanner: Enabled: {self.enabled}")

            else:
                print(f"Scanner: ❌ Unsupported scanner type: {scanner_type}")
                self.enabled = False

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Scanner: ❌ Error initializing scanner: {e}")
            print(f"Scanner: Full error details:\n{error_details}")
            self.enabled = False
            self.scanner_handler = None

    def _on_scan(self, scanned_content: str):
        """
        Internal callback when QR code is scanned.

        Args:
            scanned_content: The scanned QR code content
        """
        # Log scan if enabled
        if self.config.get('logging', {}).get('log_all_scans', True):
            self._log_scan(scanned_content)

        # Auto-process if enabled
        if self.config.get('auto_process', True):
            try:
                # Call the main application's QR processor
                # Pass context='hardware_scanner' to distinguish from manual entry
                self.qr_processor(scanned_content, context='hardware_scanner')
            except Exception as e:
                print(f"Scanner: Error processing QR code: {e}")
                if self.config.get('logging', {}).get('log_errors', True):
                    self._log_error(scanned_content, str(e))

    def _log_scan(self, content: str):
        """Log a successful scan."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Scanner: Scanned QR code: {content}")

        # Could also write to file if needed
        # log_file = Path(__file__).parent.parent.parent / "logs" / "scanner.log"
        # with open(log_file, 'a') as f:
        #     f.write(f"[{timestamp}] SCAN: {content}\n")

    def _log_error(self, content: str, error: str):
        """Log a scan error."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Scanner: ERROR processing '{content}': {error}")

    def enable(self):
        """Enable the scanner."""
        if self.scanner_handler:
            self.scanner_handler.enable()
            self.enabled = True
            print("Scanner: Enabled")
        else:
            print("Scanner: Cannot enable - not initialized")

    def disable(self):
        """Disable the scanner."""
        if self.scanner_handler:
            self.scanner_handler.disable()
            self.enabled = False
            print("Scanner: Disabled")

    def toggle(self):
        """Toggle scanner enabled state."""
        if self.enabled:
            self.disable()
        else:
            self.enable()

    def is_enabled(self) -> bool:
        """Check if scanner is enabled."""
        return self.enabled

    def get_status(self) -> dict:
        """
        Get scanner status information.

        Returns:
            dict: Status information including enabled state, type, etc.
        """
        return {
            "enabled": self.enabled,
            "scanner_type": self.config.get('scanner_type', 'unknown'),
            "initialized": self.scanner_handler is not None,
            "auto_process": self.config.get('auto_process', True)
        }

    def cleanup(self):
        """Cleanup scanner resources."""
        if self.scanner_handler:
            try:
                self.scanner_handler.unbind()
            except:
                pass
        print("Scanner: Cleaned up")
