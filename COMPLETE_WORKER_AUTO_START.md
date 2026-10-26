# COMPLETE WORKER AUTO-START SETUP

## Persona
**Windows Systems Engineer** — you are completing a Task Scheduler setup that was investigated but not yet applied. The diagnostic work is done. You are here to build and verify.

## Direct Aim
Create launcher scripts and register Windows Task Scheduler tasks so that the Zone B worker and watcher start automatically on user login. This was fully investigated in a previous session — all findings are provided below. You are picking up from STOP GATE 1 (confirmed).

## Overall Aim
Without auto-start, the pipeline stalls for hours after reboots or sleep. David has to manually open the portal or run control.py to restart processing. This fix eliminates that gap permanently.

---

## CONTEXT FROM PREVIOUS SESSION (CONFIRMED — DO NOT RE-INVESTIGATE)

The following was verified by reading control.py, PROGRAM_MAP.md, and the instruction manual:

- **Python path:** `C:\Python313\python.exe` (system Python, not venv)
- **Worker start command:** `C:\Python313\python.exe D:\zone_b\control.py worker start`
- **Watcher start command:** `C:\Python313\python.exe D:\zone_b\control.py watcher start`
- **Working directory:** `D:\zone_b`
- **Duplicate detection:** `control.py` checks PID file and verifies process is alive before spawning. Safe to call when already running — it exits cleanly.
- **PID files:** `D:\zone_b\logs\control\worker.pid` and `watcher.pid`
- **Meta files:** `worker.meta.json`, `watcher.meta.json`
- **.env:** `D:\zone_b\pc_ingest\.env` (loaded by python-dotenv inside the scripts)
- **Current auto-start:** NONE. PROGRAM_MAP Section 3.3 confirms all processes managed manually.
- **Process flags:** `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (control.py handles this internally)

**Key design decision (confirmed):** The .bat files call `control.py worker start` / `control.py watcher start` rather than the scripts directly. This preserves duplicate detection, PID management, and meta file updates.

---

## CURRENT STATE (AS OF THIS MORNING)

David turned off the PC last night. This morning he opened the portal manually and the pipeline woke up. The Task Scheduler tasks have NOT been created yet. Worker and watcher are currently running (started manually via portal). You can verify this but do NOT restart them.

---

## STEP 1: CREATE LAUNCHER SCRIPTS

Create the directory and scripts:

```powershell
# Create scripts directory if it doesn't exist
New-Item -ItemType Directory -Path "D:\zone_b\scripts" -Force
```

Create `D:\zone_b\scripts\start_worker.bat`:
```bat
@echo off
cd /d D:\zone_b
C:\Python313\python.exe D:\zone_b\control.py worker start
```

Create `D:\zone_b\scripts\start_watcher.bat`:
```bat
@echo off
cd /d D:\zone_b
C:\Python313\python.exe D:\zone_b\control.py watcher start
```

### Verify scripts exist and content is correct:
```powershell
type D:\zone_b\scripts\start_worker.bat
type D:\zone_b\scripts\start_watcher.bat
```

---

## STEP 2: TEST LAUNCHER SCRIPTS (SAFE — duplicate detection protects us)

Since worker and watcher are already running, calling the scripts should detect the existing PID and exit without launching a duplicate. This IS the test.

```powershell
# Run worker script — should detect existing process and exit
D:\zone_b\scripts\start_worker.bat

# Run watcher script — should detect existing process and exit
D:\zone_b\scripts\start_watcher.bat
```

**Expected:** Each script either says the process is already running or exits silently. No duplicate processes.

**Verify no duplicates were created:**
```powershell
Get-Process python* | Format-Table Id, ProcessName, StartTime
```

The count of Python processes should be the SAME as before running the scripts.

---

## >>> STOP GATE <<<
**Present the test results. If duplicates were created, STOP and report. Do NOT proceed to Task Scheduler registration until duplicate-safe behaviour is confirmed. Wait for David's go-ahead.**

---

## STEP 3: REGISTER TASK SCHEDULER TASKS

```powershell
# --- Worker Task ---
$workerAction = New-ScheduledTaskAction `
    -Execute "D:\zone_b\scripts\start_worker.bat" `
    -WorkingDirectory "D:\zone_b"

$loginTrigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)

Register-ScheduledTask `
    -TaskName "ZoneB-Worker" `
    -Action $workerAction `
    -Trigger $loginTrigger `
    -Settings $settings `
    -Description "Zone B pipeline worker — auto-start on login via control.py"


# --- Watcher Task ---
$watcherAction = New-ScheduledTaskAction `
    -Execute "D:\zone_b\scripts\start_watcher.bat" `
    -WorkingDirectory "D:\zone_b"

Register-ScheduledTask `
    -TaskName "ZoneB-Watcher" `
    -Action $watcherAction `
    -Trigger $loginTrigger `
    -Settings $settings `
    -Description "Zone B pipeline watcher — auto-start on login via control.py"
```

### Verify registration:
```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -match "ZoneB" } | Format-List TaskName, State, Description
```

Both tasks should appear with State = Ready.

---

## STEP 4: CONFIRM PORTAL COMPATIBILITY

With Task Scheduler tasks registered, verify the portal still works normally:

1. Open the Tkinter portal (if not already open)
2. Go to System tab
3. Worker and Watcher should both show RUNNING
4. Stop buttons should still work
5. If you Stop via portal, Task Scheduler won't re-launch until next login (this is correct)

---

## STEP 5: UPDATE PROGRAM_MAP.md

Add to Section 3.3 (or wherever auto-start is documented):

```markdown
### 3.3 Auto-Start (Task Scheduler)

Worker and watcher are registered as Windows Task Scheduler tasks:
- **ZoneB-Worker** — triggers on user login, calls `control.py worker start`
- **ZoneB-Watcher** — triggers on user login, calls `control.py watcher start`

Launcher scripts: `D:\zone_b\scripts\start_worker.bat`, `start_watcher.bat`

Duplicate-safe: control.py checks PID before spawning. If already running, exits cleanly.

Manual override: Portal Stop buttons still work. Task Scheduler only re-launches on next login.

Rollback: `Unregister-ScheduledTask -TaskName "ZoneB-Worker" -Confirm:$false`
          `Unregister-ScheduledTask -TaskName "ZoneB-Watcher" -Confirm:$false`
```

---

## ROLLBACK (if anything goes wrong)

```powershell
Unregister-ScheduledTask -TaskName "ZoneB-Worker" -Confirm:$false
Unregister-ScheduledTask -TaskName "ZoneB-Watcher" -Confirm:$false
Remove-Item D:\zone_b\scripts\start_worker.bat -ErrorAction SilentlyContinue
Remove-Item D:\zone_b\scripts\start_watcher.bat -ErrorAction SilentlyContinue
```

---

## WHAT NOT TO DO

- Do NOT modify control.py
- Do NOT modify db_worker.py or processor.py
- Do NOT stop the currently running worker or watcher
- Do NOT use Windows Services or NSSM
- Do NOT set tasks to run as SYSTEM — must run as current user
- Do NOT re-investigate what was already confirmed above

---

## SUCCESS CRITERIA (for David to test later)

After next reboot:
1. Log in to Windows
2. Do NOT open the portal or run control.py
3. Wait 30 seconds
4. Run: `sqlite3 D:\zone_b\jobs.db "SELECT * FROM worker_status ORDER BY last_seen DESC LIMIT 3;"`
5. Worker should be registered and active
6. Open portal — System Control should show Worker and Watcher as RUNNING
7. Pipeline processes any queued audio without manual intervention
