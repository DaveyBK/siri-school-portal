# FIX: Lesson Gate "Stopping..." Button Hang

**Persona:** UI bug-fixer (Tkinter threading specialist)
**Direct aim:** Fix the lesson gate stop button getting permanently stuck on "Stopping..." in `system_tab.py`
**Overall aim:** Ensure lesson sessions can be stopped and restarted without closing/reopening the portal

---

## READ FIRST — Mandatory Diagnostic Phase

Before changing ANY code, read and confirm you understand:

1. `D:\AI_phase\school\apps\school_portal\ui\system_tab.py` — the ONLY file you will edit
2. Confirm the line numbers below still match the current file (they may have drifted)

**STOP GATE 1:** State your understanding of the bug below before proceeding to the fix.

---

## Bug Analysis

### Symptom
When the teacher clicks "Stop Lesson" in the System Control tab, the button changes to "Stopping..." (disabled) and **never recovers**. The lesson gate stays in this state until the entire portal is closed and reopened.

### Root Cause — Two interacting issues

**Issue 1: Button state never reset on refresh**

In `_update_lesson_gate()` (~line 608), when the lesson is no longer active, the code does:
```python
self._lesson_stop_btn.pack_forget()   # hides the button
self._lesson_start_btn.pack(...)       # shows start button
```
But it **never resets** the stop button's `text` back to `"Stop Lesson"` or its `state` back to `tk.NORMAL`. So the button remains internally stuck as "Stopping..." / DISABLED. If any subsequent refresh sees the lesson as still active (stale read, timing), the button reappears in its broken state.

**Issue 2: Refresh blocked by `_busy` flag**

`_run_control()` (~line 731) sets `self._busy = True` at the start and `False` in the `finally` block, then schedules `self.after(3000, self._refresh)`. But `_refresh()` (~line 306) **exits immediately** if `_busy` is True:
```python
def _refresh(self):
    if self._busy:
        return  # <-- silently drops the refresh
```
If `_busy` is still True when the 3-second timer fires (e.g., another operation started, or a threading race), the post-stop refresh never happens and the UI is never updated.

**Issue 3: No timeout safety net**

There is no fallback mechanism. If the scheduled refresh fails for any reason, the button stays stuck forever.

### Why closing/reopening fixes it
A fresh `SystemTab` instance starts with `_busy = False` and buttons at their default state. The initial `on_tab_selected()` → `_refresh()` queries the DB, sees `is_active = 0`, and correctly shows "No active lesson" with the Start button.

---

## The Fix

**STOP GATE 2:** Before editing, verify you can see the current content of these specific sections in `system_tab.py`. Do NOT proceed from memory.

### Fix 1: Reset button state in `_update_lesson_gate` (REQUIRED)

In `_update_lesson_gate()`, add button state resets in BOTH branches:

```python
def _update_lesson_gate(self, results):
    lesson = results.get('active_lesson')
    if lesson:
        class_id = lesson.get('class_id') or ''
        started = lesson.get('started_at', '')
        display = _format_class(class_id)
        time_part = ""
        if started:
            try:
                dt = datetime.fromisoformat(started)
                dt_bkk = dt + timedelta(hours=7)
                time_part = dt_bkk.strftime("%H:%M")
            except ValueError:
                if 'T' in started:
                    time_part = started.split('T')[1][:5]
        self._lesson_label.config(text=f"{display} — started {time_part}")
        # === FIX: Always reset stop button to ready state ===
        self._lesson_stop_btn.config(text="Stop Lesson", state=tk.NORMAL)
        self._lesson_stop_btn.pack(side=tk.RIGHT, padx=5)
        self._lesson_start_btn.pack_forget()
    else:
        self._lesson_label.config(text="No active lesson")
        # === FIX: Reset both buttons to default state ===
        self._lesson_stop_btn.config(text="Stop Lesson", state=tk.NORMAL)
        self._lesson_stop_btn.pack_forget()
        self._lesson_start_btn.config(text="Start Lesson", state=tk.NORMAL)
        self._lesson_start_btn.pack(side=tk.RIGHT, padx=5)
```

### Fix 2: Add safety-net timeout in `_stop_lesson` (REQUIRED)

Replace `_stop_lesson` with a version that schedules a forced refresh even if the normal one fails:

```python
def _stop_lesson(self):
    self._lesson_stop_btn.config(text="Stopping...", state=tk.DISABLED)
    self._run_control(["lesson", "stop"], "Lesson stop")
    # Safety net: force a refresh after 8s even if _busy blocked the 3s one
    self.after(8000, self._force_refresh_lesson)
```

Add this new method nearby:

```python
def _force_refresh_lesson(self):
    """Safety net: if lesson gate is still showing Stopping, force a refresh."""
    if self._lesson_stop_btn.cget("text") == "Stopping...":
        self._busy = False  # Clear stuck busy flag
        self._refresh()
```

### Fix 3: Apply the same pattern to `_start_lesson_dialog` (RECOMMENDED)

In the `_ok()` closure inside `_start_lesson_dialog`, after `self._lesson_start_btn.config(text="Starting...", state=tk.DISABLED)`, add:

```python
self.after(8000, self._force_refresh_lesson_start)
```

And add:

```python
def _force_refresh_lesson_start(self):
    """Safety net for lesson start."""
    if self._lesson_start_btn.cget("text") == "Starting...":
        self._busy = False
        self._refresh()
```

---

## Verification

After applying the fix:

1. Start a lesson via the dialog
2. Confirm "Stop Lesson" button appears with lesson info
3. Click "Stop Lesson" — should show "Stopping..." briefly
4. Within 3-8 seconds, should update to "No active lesson" + "Start Lesson" button
5. Repeat 3 times to confirm no hangs
6. Test: start a lesson, then immediately toggle to another tab and back — confirm refresh still works

---

## Scope Boundaries — DO NOT VIOLATE

- **ONLY edit** `system_tab.py`
- **DO NOT** modify `control.py`, `app.py`, `main_window.py`, or any database schema
- **DO NOT** change the threading model or add new threads
- **DO NOT** add imports
- **DO NOT** change the `_run_control` method's structure (it works fine for services)
