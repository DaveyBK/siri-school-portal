# STARTUP PATH INVESTIGATION — SCANNER vs MANUAL

## Persona
**Systems Diagnostician** — you are mapping the full startup chain of the Siri English classroom system to understand what the QR scanner startup path initializes versus what happens when David opens the portal manually. You change NOTHING.

## Direct Aim
Map every service, process, and initialization step that occurs when:
- **Path A:** A lesson is started via the QR scanner
- **Path B:** David opens the Tkinter portal manually and navigates to System Control

Identify what Path B skips that Path A triggers, and whether this leaves the system in a partial or degraded state.

## Overall Aim
David has observed that the system sometimes comes up in a partially ready state — Ollama stopped, Flask Portal stopped, pipeline idle — and suspects that bypassing the scanner startup path leaves things uninitialized. We need to understand the full dependency chain so we know what needs to run at boot vs what runs on-demand vs what the scanner triggers.

---

## ABSOLUTE CONSTRAINT

**YOU MUST NOT CHANGE, EDIT, RESTART, OR MODIFY ANYTHING.**

---

## INVESTIGATION STEPS

### 1. Map the QR scanner startup chain

Find the scanner entry point and trace what it triggers:

```powershell
# Find scanner-related code
Get-ChildItem -Recurse D:\AI_phase\school\apps\school_portal\ -Include *.py | Select-String -Pattern "scan|qr|barcode|camera|lesson.*start|start.*lesson" -List

# Also check Zone B for scanner hooks
Get-ChildItem -Recurse D:\zone_b\ -Include *.py | Select-String -Pattern "scan|qr|barcode|start.*lesson" -List
```

Read every file found. For each, document:
- What does it import/call?
- What services does it start?
- What database records does it create?
- What signals does it send?

### 2. Trace the "Start Lesson" button

The Lesson Gate in System Control has a "Start Lesson" button. Is this the same code path as the scanner, or different?

```powershell
# Find the Start Lesson button handler
Get-ChildItem -Recurse D:\AI_phase\school\apps\school_portal\ -Include *.py | Select-String -Pattern "Start.Lesson|start_lesson|lesson_start|begin_lesson|StartLesson" -List
```

Read the handler code and trace what it calls.

### 3. Map the full service dependency chain

For each of these services, document: who starts it, when, and what depends on it.

```powershell
# control.py — what does it manage?
type D:\zone_b\control.py | findstr "def.*start\|def.*stop\|def.*launch\|ollama\|flask\|watcher\|worker"

# Check if Ollama has its own startup logic
Get-ChildItem -Recurse D:\zone_b\ -Include *.py | Select-String -Pattern "ollama.*start\|start.*ollama\|launch.*ollama\|ollama.*serve" -List

# Check if Flask Portal has its own startup logic  
Get-ChildItem -Recurse D:\zone_b\ -Include *.py | Select-String -Pattern "flask.*start\|start.*flask\|launch.*flask\|portal.*start" -List

# Check the portal's main entry point
Get-ChildItem D:\AI_phase\school\apps\school_portal\ -Include main*.py,app*.py,__main__.py,run*.py | ForEach-Object { Write-Host "--- $($_.Name) ---"; type $_.FullName }
```

### 4. Check what the Tkinter portal does on launch

```powershell
# Find the main window / root initialization
Get-ChildItem -Recurse D:\AI_phase\school\apps\school_portal\ -Include *.py | Select-String -Pattern "def __init__|mainloop|Tk()|root\s*=|class.*App|def main" -List
```

Read the main app class. Does it:
- Start Ollama?
- Start Flask Portal?
- Start Worker/Watcher?
- Call control.py?
- Check service status?
- Auto-start anything that's not running?

### 5. Check what happens at scan time

```powershell
# QR scan typically triggers attendance + lesson start
# Find the scan event handler
Get-ChildItem -Recurse D:\AI_phase\school\apps\school_portal\ -Include *.py | Select-String -Pattern "on_scan|scan_callback|process_scan|handle_scan|scan_result" -List
```

Trace the full chain from scan → lesson creation → service startup.

### 6. Check Task Scheduler tasks (what's auto-started)

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -match "ZoneB|Siri|siri|zone" } | Format-List TaskName, State, Description, Actions
```

### 7. Check if there's a "morning startup" or "boot" script

```powershell
# Check for any startup orchestration
Get-ChildItem -Recurse D:\zone_b\ -Include *.bat,*.ps1,*.cmd | Select-String -Pattern "start|launch|boot|init" -List
Get-ChildItem D:\zone_b\scripts\ 2>$null
Get-ChildItem -Recurse D:\AI_phase\school\ -Include *.bat,*.ps1,*.cmd | ForEach-Object { Write-Host "--- $($_.FullName) ---" }
```

---

## REPORT FORMAT

```
=== STARTUP PATH ANALYSIS ===

SERVICES AND THEIR STARTUP TRIGGERS:

┌──────────────┬───────────────┬──────────────┬──────────────┬──────────────┐
│ Service      │ Task Sched?   │ Portal Open? │ Scanner?     │ Start Lesson?│
├──────────────┼───────────────┼──────────────┼──────────────┼──────────────┤
│ Worker       │ ?             │ ?            │ ?            │ ?            │
│ Watcher      │ ?             │ ?            │ ?            │ ?            │
│ Flask Portal │ ?             │ ?            │ ?            │ ?            │
│ Ollama       │ ?             │ ?            │ ?            │ ?            │
│ Pi5 capture  │ ?             │ ?            │ ?            │ ?            │
└──────────────┴───────────────┴──────────────┴──────────────┴──────────────┘

PATH A — SCANNER STARTUP:
  Step 1: [what happens]
  Step 2: [what happens]
  ...

PATH B — MANUAL PORTAL OPEN:
  Step 1: [what happens]
  Step 2: [what happens]
  ...

GAP ANALYSIS (what Path B skips):
  1. [service/step missing]
  2. [service/step missing]
  ...

DEPENDENCY CHAIN:
  [Which services depend on which others?]
  [What's the correct startup order?]

CURRENT AUTO-START COVERAGE:
  - Task Scheduler: [what's registered]
  - Missing: [what should be auto-started but isn't]

RECOMMENDATIONS:
  [What needs to change so the system comes up fully ready regardless of how David starts it]
```

---

## WHAT NOT TO DO

- Do NOT modify any files
- Do NOT start or stop any services
- Do NOT run any scripts
- Do NOT create any files
- Report only — David will decide what to change
