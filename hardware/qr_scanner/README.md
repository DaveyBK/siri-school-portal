# QR Scanner Hardware Integration Module

**Module Type:** Hardware Interface
**Scanner Type:** USB HID Keyboard Wedge
**Status:** Production Ready

## Overview

This module provides hardware QR scanner integration for the School Portal system. It enables automatic scanning of QR codes using physical USB barcode/QR scanner devices that function as keyboard wedges.

## Architecture

```
hardware/
└── qr_scanner/
    ├── __init__.py              # Module exports
    ├── scanner_interface.py     # Main interface (facade)
    ├── hid_scanner.py          # HID keyboard wedge handler
    ├── scanner_config.json     # Configuration
    └── README.md               # This file
```

## Module Communication

### INPUTS
- **Physical Device**: USB HID keyboard wedge scanner
- **Tkinter Widget**: Root window for event binding
- **Callback Function**: QR code processor from main application
- **Configuration**: scanner_config.json settings

### OUTPUTS
- **Scanned QR Codes**: Passed to application's `process_qr_code()` method
- **Context String**: Always "hardware_scanner" to distinguish from manual entry
- **Status Information**: Enable/disable state, scan logs
- **Console Logs**: Scan events, errors, status changes

### DATA FLOW

```
Physical QR Code
    ↓
Scanner Device (USB)
    ↓
HID Keyboard Events (rapid typing)
    ↓
HIDScannerHandler (accumulates characters)
    ↓
ScannerInterface (validates & processes)
    ↓
MainWindow.process_qr_code(content, "hardware_scanner")
    ↓
Application Logic (select student/item)
```

## How It Works

### HID Keyboard Wedge Scanners

These scanners:
1. Connect via USB (no drivers needed)
2. Act as a keyboard device
3. When you scan a QR code, they "type" the content very rapidly
4. Send a terminator key (usually Enter/Return) when done

### Detection Algorithm

The handler distinguishes scanner input from human typing by:
- **Speed Detection**: Characters arrive < 100ms apart (configurable)
- **Terminator Detection**: Enter/Return key completes the scan
- **Validation**: Checks length and optional prefix requirements

### Auto-Processing

When enabled (default), scanned codes are automatically:
1. Captured from keyboard events
2. Validated against configuration rules
3. Passed to the main application's QR processor
4. Logged for audit purposes

## Configuration

Edit `scanner_config.json` to customize behavior:

```json
{
  "scanner_type": "hid_keyboard_wedge",
  "enabled": true,
  "auto_process": true,
  "input_settings": {
    "terminator": "Return",
    "debounce_ms": 100,
    "min_length": 3,
    "max_length": 100
  },
  "validation": {
    "require_prefix": false,
    "valid_prefixes": ["I:", "S:"]
  }
}
```

### Key Settings

- **debounce_ms**: Time threshold to detect rapid scanner input (default: 100ms)
- **terminator**: Key that ends a scan (usually "Return" or "Enter")
- **require_prefix**: Enforce QR code format (I: for items, S: for students)
- **auto_process**: Automatically process scans vs. manual trigger

## Usage

### For End Users

1. **Enable Scanner**: Go to `QR → Toggle Hardware Scanner`
2. **Check Status**: Go to `QR → Scanner Status`
3. **Scan QR Codes**: Point scanner at code and press trigger
4. **Auto-Processing**: System automatically selects student/item

### For Developers

#### Initialize Scanner

```python
from hardware.qr_scanner import ScannerInterface

scanner = ScannerInterface(
    root=tkinter_root_window,
    qr_processor=your_callback_function
)
```

#### Toggle Scanner

```python
scanner.toggle()  # Enable/disable
scanner.enable()  # Force enable
scanner.disable() # Force disable
```

#### Check Status

```python
status = scanner.get_status()
# Returns: {"enabled": bool, "scanner_type": str, ...}
```

#### Cleanup

```python
scanner.cleanup()  # Call before closing app
```

## Integration Points

### Main Application

The scanner integrates with `ui/main_window.py`:

1. **Import**: `from hardware.qr_scanner import ScannerInterface`
2. **Initialize**: In `MainWindow.__init__()`
3. **Process**: Calls `self.process_qr_code(content, "hardware_scanner")`
4. **Cleanup**: In `on_closing()` method
5. **Menu**: Toggle and status in QR menu

### Existing QR System

The scanner works seamlessly with existing QR code features:
- **Generation**: Existing `qr_utils.py` generates QR code images
- **Processing**: Existing `process_qr_code()` handles both manual and hardware scans
- **Format**: Uses same format (I:item_id, S:student_id)
- **Logging**: Integrated with existing `models.log_qr_scan()`

## Troubleshooting

### Scanner Not Working

1. **Check Connection**: Ensure USB scanner is plugged in
2. **Check Status**: Use `QR → Scanner Status` menu
3. **Enable Scanner**: Use `QR → Toggle Hardware Scanner`
4. **Check Console**: Look for "Scanner:" log messages

### Wrong Characters Scanned

1. **Check Debounce**: Increase `debounce_ms` in config
2. **Check Terminator**: Verify scanner sends correct terminator key
3. **Test Manually**: Type a code slowly vs. scanner speed

### Scans Ignored

1. **Check Validation**: Review `validation` settings in config
2. **Check Length**: Ensure scans meet `min_length` / `max_length`
3. **Check Prefix**: If `require_prefix` is true, scan must start with I: or S:

## Hardware Compatibility

### Tested Scanners
- Generic USB barcode/QR scanners (HID mode)
- Honeywell Voyager series
- Zebra DS2208
- Symbol LS2208

### Requirements
- USB connection
- HID keyboard wedge mode (not serial mode)
- Configurable terminator character
- No special drivers needed (uses built-in HID driver)

## Future Enhancements

Potential additions:
- [ ] Serial port scanner support
- [ ] Webcam/camera-based scanning (OpenCV + pyzbar)
- [ ] Mobile device scanner integration
- [ ] Bluetooth scanner support
- [ ] Multi-scanner support (multiple devices)
- [ ] Custom audio feedback (beep on scan)
- [ ] Visual scan indicator in UI

## Modular Design Principles

This module follows the **Modular Architect (SIRI)** approach:

1. **Standalone**: No tight coupling to main application
2. **JSON Communication**: Configuration via JSON file
3. **Event-Based**: Uses callbacks, not imports
4. **Documented I/O**: Clear inputs and outputs
5. **Graceful Degradation**: App works without scanner
6. **Clean Separation**: Hardware logic separate from business logic

## Support

For issues or questions:
1. Check scanner status via menu
2. Review console logs for "Scanner:" messages
3. Verify configuration in scanner_config.json
4. Test with manual QR entry first to isolate hardware issues
