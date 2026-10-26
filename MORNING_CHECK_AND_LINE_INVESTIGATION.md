# MORNING PIPELINE CHECK + LINE ID ENTRY POINT

## Persona
**Systems Diagnostician** — you are auditing a classroom audio processing pipeline across a Raspberry Pi 5 (audio capture) and a Windows 11 Zone B machine (processing). You are read-only unless explicitly told otherwise. You report what you find.

## Direct Aim
Three tasks:
1. **Morning pipeline check** — determine how many chunks were captured, sent, and processed from the previous lesson(s). Establish what completed and what didn't.
2. **LINE ID entry point** — investigate whether there is currently any way to enter a parent's LINE user ID into the system. If there is, document where. If there isn't, document where it *should* go.
3. **Processing stall investigation** — look for evidence that the Zone B worker/watcher stalls when the Tkinter portal is not open, and only resumes when the portal is launched.

## Overall Aim
David needs a reliable morning-start routine to confirm yesterday's pipeline health, and needs to understand whether LINE integration has a complete data path or a gap.

---

## ABSOLUTE CONSTRAINT

**YOU MUST NOT CHANGE, EDIT, RESTART, OR MODIFY ANYTHING unless David explicitly tells you to.**

---

# TASK 1: MORNING PIPELINE CHECK

## On the Pi5 (SSH to audiocapture@192.168.50.250)

### How many chunks were recorded?
```bash
# Check staging — should be empty if everything moved
ls -la /var/lib/siri/audio/staging/

# Check outgoing — should be empty if everything transferred
ls -la /var/lib/siri/audio/outgoing/

# Check sent — successfully transferred chunks land here
ls -la /var/lib/siri/audio/sent/
ls /var/lib/siri/audio/sent/ | wc -l

# Check failed — anything that failed to transfer
ls -la /var/lib/siri/audio/failed/
ls /var/lib/siri/audio/failed/ | wc -l
```

### Summary counts
```bash
echo "=== PI5 AUDIO SUMMARY ==="
echo "Staging (stuck):   $(ls /var/lib/siri/audio/staging/ 2>/dev/null | wc -l) files"
echo "Outgoing (waiting): $(ls /var/lib/siri/audio/outgoing/ 2>/dev/null | wc -l) files"
echo "Sent (complete):    $(ls /var/lib/siri/audio/sent/ 2>/dev/null | wc -l) files"
echo "Failed:             $(ls /var/lib/siri/audio/failed/ 2>/dev/null | wc -l) files"
```

### Check timestamps of sent files (to confirm they're from yesterday/today)
```bash
ls -lt /var/lib/siri/audio/sent/ | head -20
```

## On Zone B (Windows — D:\zone_b\)

### How many chunks arrived?
```powershell
# Check incoming — should be empty if all were picked up
Get-ChildItem D:\zone_b\incoming\ | Measure-Object
Get-ChildItem D:\zone_b\incoming\ | Sort-Object LastWriteTime -Descending | Select-Object -First 10

# If there's a processed/archive folder, check that too
Get-ChildItem D:\zone_b\processed\ 2>$null | Measure-Object
```

### Check jobs.db for pipeline status
```powershell
# Open jobs.db and check job counts by status and type
sqlite3 D:\zone_b\jobs.db "
SELECT job_type, status, COUNT(*) as count 
FROM jobs 
GROUP BY job_type, status 
ORDER BY job_type, status;
"
```

### Check for errors in recent jobs
```powershell
sqlite3 D:\zone_b\jobs.db "
SELECT job_type, status, error_message, created_at 
FROM jobs 
WHERE status = 'error' 
ORDER BY created_at DESC 
LIMIT 10;
"

```

### Check most recent completed jobs
```powershell
sqlite3 D:\zone_b\jobs.db "
SELECT job_type, status, created_at, completed_at 
FROM jobs 
WHERE status = 'done' 
ORDER BY completed_at DESC 
LIMIT 10;
"
```

### Present the report
```
=== MORNING PIPELINE REPORT ===

PI5 SIDE:
  Chunks recorded (in sent/):  ___
  Stuck in staging:            ___
  Waiting in outgoing:         ___
  Failed:                      ___

ZONE B SIDE:
  Chunks in incoming (unprocessed): ___
  Jobs by type and status:
    transcribe:    queued ___ | running ___ | done ___ | error ___
    langextract:   queued ___ | running ___ | done ___ | error ___
    summarise:     queued ___ | running ___ | done ___ | error ___

  Recent errors: [list any]

VERDICT:
  [Pipeline healthy / partial failure / stalled at ___]
```

---

# TASK 2: LINE ID ENTRY POINT INVESTIGATION

## What to look for

A parent's LINE user ID (or LINE display name) needs to be stored somewhere and linked to a student so that the summarise_lesson output can be sent to the right parent. The question is: **does this entry point exist?**

### Check the school portal database schema
```powershell
sqlite3 D:\AI_phase\school\apps\school_portal\data\inventory.db ".schema" | findstr -i "line\|parent\|contact\|phone\|message"
```

If nothing found:
```powershell
sqlite3 D:\AI_phase\school\apps\school_portal\data\inventory.db ".tables"
sqlite3 D:\AI_phase\school\apps\school_portal\data\inventory.db ".schema students"
sqlite3 D:\AI_phase\school\apps\school_portal\data\inventory.db ".schema"
```

### Check Zone B database for LINE references
```powershell
sqlite3 D:\zone_b\jobs.db ".schema" | findstr -i "line\|parent\|recipient\|notify"
```

### Search codebase for LINE-related code
```powershell
# In the school portal code
Get-ChildItem -Recurse D:\AI_phase\school\apps\school_portal\ -Include *.py | Select-String -Pattern "line_id|line_user|LINE|line_notify|parent.*id" -List

# In Zone B code
Get-ChildItem -Recurse D:\zone_b\ -Include *.py | Select-String -Pattern "line_id|line_user|LINE|line_notify|parent.*id|send.*message|push.*message" -List
```

### Check the Tkinter portal UI code for any parent/LINE fields
```powershell
# Look for form fields, entry widgets, or tabs related to parents or LINE
Get-ChildItem -Recurse D:\AI_phase\school\apps\school_portal\ -Include *.py | Select-String -Pattern "parent|LINE|contact|Entry\(|ttk.Entry|line_id" -List
```

### Check for LINE bot/API configuration
```powershell
Get-ChildItem -Recurse D:\zone_b\ -Include *.py,*.env,*.ini,*.json,*.yaml,*.yml | Select-String -Pattern "LINE_CHANNEL|LINE_TOKEN|line.*api|messaging.*api" -List
```

### Present the report
```
=== LINE ID ENTRY POINT REPORT ===

DATABASE:
  Column for LINE ID exists: YES / NO
  Table: ___ Column: ___
  Currently populated: ___ of ___ students have LINE IDs

UI ENTRY POINT:
  Portal has LINE ID field: YES / NO
  Location: [which tab/screen, or "none found"]

LINE API CONFIG:
  Bot token configured: YES / NO
  Send message code exists: YES / NO
  Location: ___

GAP ANALYSIS:
  [What's missing? e.g. "Column exists but no UI to enter it" or "No column, no UI, no API config — full gap"]

RECOMMENDATION:
  [Where should the LINE ID entry point live? Likely: Students tab in Tkinter portal, with a field per student linked to parent LINE user ID]
```

---

# TASK 3: PROCESSING STALL INVESTIGATION

## What to look for

David suspects the Zone B worker/watcher stalls when the Tkinter portal is not running, and only resumes when the portal is opened. This would mean the worker is not truly independent.

### Check if worker/watcher are separate processes from the portal
```powershell
# Are they launched by the portal, or by independent services/scripts?
Get-ChildItem -Recurse D:\zone_b\ -Include *.py | Select-String -Pattern "watcher|worker|subprocess|Thread|start_worker|start_watcher" -List
```

### Check how the portal starts the worker
```powershell
# Read the main portal entry point
# Look for: does closing the portal kill the worker?
Get-ChildItem D:\zone_b\ -Include *.py | Select-String -Pattern "def main|if __name__|launch|start" -List
```

### Read the worker and watcher code
```powershell
# Find and read these files
Get-ChildItem -Recurse D:\zone_b\ -Include *worker*,*watcher* -Name
# Then cat/type each one
```

### Check for polling mechanism
Look for:
- Does the worker poll jobs.db on a timer? (independent = good)
- Does the worker respond to signals from the Flask portal? (coupled = explains stalling)
- Is the worker a thread inside the Tkinter main loop? (coupled = explains stalling)
- Does the worker check if the portal is running before processing? (gate = explains stalling)

### Check Windows services / Task Scheduler
```powershell
# Are worker/watcher registered as Windows services?
Get-Service | Where-Object { $_.Name -match "siri|zone" }

# Or in Task Scheduler?
schtasks /query /fo LIST | findstr -i "siri\|zone\|worker\|watcher"
```

### Check process tree when portal IS running
```powershell
# When the portal is open, check what processes are running
Get-Process | Where-Object { $_.ProcessName -match "python|flask|worker|watcher" } | Format-Table Id, ProcessName, StartTime, Path
```

### Present the report
```
=== PROCESSING STALL REPORT ===

ARCHITECTURE:
  Worker is: [independent process / thread inside portal / subprocess of portal]
  Watcher is: [independent process / thread inside portal / subprocess of portal]
  Flask portal is: [independent / launched by Tkinter portal]

COUPLING EVIDENCE:
  [Does closing the portal kill the worker? Evidence for/against]
  [Does the worker poll independently or wait for portal signals?]

STALL MECHANISM (if found):
  [Describe exactly why processing stops when portal is closed]

VERDICT:
  [Confirmed: worker depends on portal / Not confirmed / Inconclusive — needs runtime test]
```

---

## >>> STOP — PRESENT ALL THREE REPORTS <<<

Do not suggest fixes. Present the reports and let David decide next steps.

---

## CONTEXT

- Pi5: `audiocapture@192.168.50.250`
- Zone B: `D:\zone_b\`
- Jobs DB: `D:\zone_b\jobs.db`
- School portal DB: `D:\AI_phase\school\apps\school_portal\data\inventory.db`
- Portal code: `D:\AI_phase\school\apps\school_portal\`
- Key programs: `ZONE_B_BACKEND_INSTRUCTION_MANUAL.md`, `PROGRAM_MAP.md` — read these first if they exist
