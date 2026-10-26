# Hardware Scanner Testing Guide

## Quick Start

### 1. Run the Application

```bash
cd "D:\school_portal"
python app.py
```

### 2. Check Scanner Status

- Go to menu: **QR → Scanner Status**
- You should see:
  - Scanner Type: hid_keyboard_wedge
  - Initialized: Yes
  - Enabled: Yes
  - Status: 🟢 ACTIVE

### 3. Test Without Hardware (Manual Test)

Before connecting your physical scanner, test the detection logic:

1. Click anywhere in the application window
2. Rapidly type a test QR code: `I:BOOK001` (type very fast!)
3. Press Enter
4. Watch the console for: `Scanner: Valid scan detected: I:BOOK001`

If you type slowly (normal human speed), it should be ignored.

### 4. Test With Hardware Scanner

Once you have your USB scanner:

1. **Plug in Scanner**: Connect USB barcode/QR scanner
2. **Print Test QR Code**:
   - Generate QR for a student: `QR → Generate QR for All Students`
   - Find the QR code in: `D:\school_portal\data\qr\students\`
   - Print or display on another screen
3. **Scan QR Code**: Point scanner at QR and press trigger
4. **Verify**: Student should be automatically selected

### 5. Test with Items

1. Generate item QR codes: `QR → Generate QR for All Items`
2. Print a QR code from: `D:\school_portal\data\qr\items\`
3. Scan with hardware scanner
4. Item should be selected in Items tab

## Console Output

Watch for these messages in the console:

### Successful Initialization
```
Scanner: HID keyboard wedge scanner initialized
Hardware scanner initialized successfully
```

### Successful Scan
```
Scanner: Valid scan detected: I:BOOK001
[2025-11-28 12:34:56] Scanner: Scanned QR code: I:BOOK001
```

### Scanner Toggle
```
Scanner: Enabled
Scanner: Disabled
```

## Configuration Testing

### Test 1: Disable Auto-Process

Edit `hardware/qr_scanner/scanner_config.json`:
```json
{
  "auto_process": false
}
```

Restart app. Scans should be logged but not processed.

### Test 2: Require Prefix Validation

Edit config:
```json
{
  "validation": {
    "require_prefix": true,
    "valid_prefixes": ["I:", "S:"]
  }
}
```

Now only codes starting with I: or S: will be accepted.

### Test 3: Adjust Debounce Time

If scanner input is missed:
```json
{
  "input_settings": {
    "debounce_ms": 200
  }
}
```

Increase if your scanner types slower.

## Troubleshooting Tests

### Problem: Scanner Not Initialized

**Check:**
```python
# In console, you should see:
Hardware scanner initialized successfully
```

**If not:**
- Check import error messages
- Verify `hardware/qr_scanner/` directory exists
- Verify all module files are present

### Problem: Scans Not Detected

**Test 1: Check if scanner is enabled**
```
QR → Scanner Status
```
Status should show: 🟢 ACTIVE

**Test 2: Manual rapid typing**
Type `I:TEST123` very fast and press Enter.
If detected, scanner works but hardware may need configuration.

**Test 3: Check console for rejections**
```
Scanner: Rejected scan (invalid length): ...
Scanner: Rejected scan (invalid prefix): ...
```

### Problem: Wrong Characters Captured

**Cause:** Scanner might be sending extra characters or different terminator.

**Solution:**
1. Test what scanner actually sends by disabling auto-process
2. Look at console logs to see exact string
3. Adjust `terminator` in config if scanner uses different key
4. Check scanner manual for configuration options

## Test Scenarios

### Scenario 1: Book Checkout Workflow

1. Enable hardware scanner
2. Open Books tab → "Assign Book"
3. Scan book QR code (I:BOOK001)
4. Book should be selected
5. Scan student QR code (S:PAN001)
6. Student should be selected
7. Click Assign

### Scenario 2: Student Attendance

1. Open Attendance tab
2. Scan student QR codes one by one
3. Each scan should select the student
4. Mark attendance for each

### Scenario 3: Quick Item Lookup

1. Open Items tab
2. Scan item QR code
3. Item details should be displayed
4. Can immediately edit or view checkout history

## Performance Testing

### Rapid Scanning Test

1. Generate multiple QR codes
2. Scan them rapidly one after another
3. Verify each scan is processed correctly
4. Check console for any dropped scans

### Expected Speed
- Scan detection: < 100ms
- Processing time: < 200ms per scan
- No dropped scans at 1 scan per second

## Integration Tests

### Test 1: Scanner + Manual Entry

1. Scan a QR code with hardware
2. Then use `QR → Scan QR (dialog)` for manual entry
3. Both methods should work

### Test 2: Scanner + Tutorial System

1. Start a tutorial (e.g., "Check Out a Book")
2. Use hardware scanner during tutorial
3. Verify tutorial progresses correctly

### Test 3: Scanner + Multiple Tabs

1. Switch between tabs
2. Scan QR codes in different tabs
3. Verify scans work in all tabs

## Validation Tests

### Valid QR Codes

Should be accepted:
- `I:BOOK001` (item)
- `S:PAN001` (student)
- `I:123456789` (numeric ID)
- `S:ABC-XYZ-123` (alphanumeric with dashes)

### Invalid QR Codes

Should be rejected if validation is enabled:
- `INVALID` (no prefix)
- `X:TEST` (wrong prefix)
- `I:` (too short)
- Very long strings > max_length

## Cleanup Test

1. Run application
2. Verify scanner initialized
3. Close application
4. Check console for: `Hardware scanner cleaned up`
5. No error messages should appear

## Success Criteria

All tests pass if:
- ✅ Scanner initializes without errors
- ✅ Manual rapid typing is detected
- ✅ Hardware scanner scans are captured
- ✅ Scans are processed correctly (student/item selected)
- ✅ Toggle enable/disable works
- ✅ Status shows correct information
- ✅ Configuration changes take effect
- ✅ Cleanup happens without errors
- ✅ No conflicts with existing features

## Next Steps After Testing

1. Configure scanner settings for your specific device
2. Print commonly-used QR codes for quick access
3. Train users on hardware scanner workflow
4. Monitor logs for any issues
5. Adjust debounce/validation settings as needed

## Support

If tests fail, provide this information:
1. Console output (copy all "Scanner:" messages)
2. Scanner model and brand
3. Operating system
4. Steps to reproduce the issue
5. Configuration file contents
