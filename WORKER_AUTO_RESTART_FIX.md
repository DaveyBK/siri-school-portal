# WORKER AUTO-RESTART VIA TASK SCHEDULER

## Persona
**Windows Systems Engineer** — you are configuring automatic startup for two critical background processes on a Windows 11 machine. You treat this as production infrastructure. You are precise, minimal, and you verify everything.

## Direct Aim
Register the Zone B worker (db_worker.py) and watcher (processor.py) as Windows Task Scheduler tasks that start automatically on user login, so they survive reboots, sleep/wake, and crashes without requiring manual intervention.

## Overall Aim
The Zone B pipeline stalls for hours when the worker dies because nothing restarts it. David currently has to manually run `control.py` to bring it back. This fix ensures the pipeline is always running when the machine is on, eliminating the 13-35 hour gaps observed in the jobs table.

---

## MANDATORY READ-FIRST PHASE

**Read these files before doing anything:**

```powershell
# Understand how processes are currently launched
type D:\zone_b\control.py
type D:\zone_b\ZONE_B_BACKEND_INSTRUCTION_MANUAL.md 2>$null
type D:\zone_b\PROGRAM_MAP.md 2>$null
```

**Answer these questions from the code before proceeding:**

1. What is the exact Python executable path used? (system Python? venv? conda?)
2. What is the exact command `control.py` uses to start the worker? (look for subprocess.Popen or similar)
3. What is the exact command `control.py` uses to start the watcher?
4. Are there any environment variables, working directory requirements, or .env files that must be present?
5. Does `control.py` use `DETACHED_PROCESS` or `CREATE_NO_WINDOW` flags? Note them.
6. Does the worker write a PID file or register itself anywhere?
7. Is there any existing auto-start mechanism you can see? (Check Task Scheduler first: `schtasks /query /fo LIST | findstr -i "siri\|zone\|worker\|watcher"`)

---

## >>> STOP GATE 1 <<<
**Present your findings from the read-first phase. Do NOT proceed until David confirms.**

---

## THE FIX

### Approach
Create two Windows Task Scheduler tasks using `schtasks` or PowerShell `Register-ScheduledTask`. Each task:
- Triggers on user login (not system boot — these run as David's user)
- Runs the same command that `control.py` uses internally
- Has restart-on-failure enabled (restart after 1 minute, up to 3 retries)
- Does NOT replace or modify `control.py` — that remains the manual override
- Runs hidden (no window popup on login)

### Step 1: Create launcher scripts

Create two small .bat files that `control.py` won't interfere with. These are what Task Scheduler will call.

```powershell
# Worker launcher
# Replace <PYTHON_PATH> and <EXACT_ARGS> with what you found in the read-first phase
@echo off
cd /d D:\zone_b
<PYTHON_PATH> db_worker.py
```

```powershell
# Watcher launcher  
@echo off
cd /d D:\zone_b
<PYTHON_PATH> processor.py
```

Save these as:
- `D:\zone_b\scripts\start_worker.bat`
- `D:\zone_b\scripts\start_watcher.bat`

**IMPORTANT:** The commands inside these .bat files must be IDENTICAL to what `control.py` uses. Do not improvise. Copy the exact Python path, exact script name, exact arguments.

### Step 2: Test the launcher scripts manually

Before registering with Task Scheduler, verify the scripts work:

```powershell
# Start worker manually via the new script
D:\zone_b\scripts\start_worker.bat

# In another terminal, check it's running
Get-Process | Where-Object { $_.ProcessName -match "python" }

# Check jobs.db — worker should register
sqlite3 D:\zone_b\jobs.db "SELECT * FROM workers ORDER BY last_seen DESC LIMIT 3;"

# Kill it
taskkill /F /PID <pid_from_above>
```

Repeat for watcher.

---

## >>> STOP GATE 2 <<<
**Both launcher scripts must work manually before proceeding to Task Scheduler registration. Present evidence and wait for David's confirmation.**

---

### Step 3: Register Task Scheduler tasks

```powershell
# Worker task
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
    -ExecutionTimeLimit (New-TimeSpan -Days 0)  # No timeout — runs indefinitely

Register-ScheduledTask `
    -TaskName "ZoneB-Worker" `
    -Action $workerAction `
    -Trigger $loginTrigger `
    -Settings $settings `
    -Description "Zone B pipeline worker (db_worker.py) — auto-start on login"
```

```powershell
# Watcher task
$watcherAction = New-ScheduledTaskAction `
    -Execute "D:\zone_b\scripts\start_watcher.bat" `
    -WorkingDirectory "D:\zone_b"

Register-ScheduledTask `
    -TaskName "ZoneB-Watcher" `
    -Action $watcherAction `
    -Trigger $loginTrigger `
    -Settings $settings `
    -Description "Zone B pipeline watcher (processor.py) — auto-start on login"
```

### Step 4: Handle duplicate prevention

The worker and watcher must not double-launch if `control.py` also starts them. Check how `control.py` handles an already-running process:

- If it checks PID / lock file → Task Scheduler and control.py can coexist safely
- If it blindly launches → you'll get duplicates

**If duplicates are possible**, add a guard to the .bat files:
```bat
@echo off
REM Check if worker is already running
tasklist /FI "WINDOWTITLE eq db_worker*" 2>NUL | find /I "python" >NUL
if %ERRORLEVEL% EQU 0 (
    echo Worker already running, exiting.
    exit /b 0
)
cd /d D:\zone_b
<PYTHON_PATH> db_worker.py
```

**Better approach:** Check what `control.py` does. If it queries `workers` table in jobs.db for a heartbeat, the duplicate detection may already be handled at the application level. Document what you find.

---

## >>> STOP GATE 3 <<<
**Tasks are registered. Present the Task Scheduler configuration and wait for David to confirm before testing.**

---

### Step 5: Verify

```powershell
# Confirm tasks exist
Get-ScheduledTask | Where-Object { $_.TaskName -match "ZoneB" } | Format-List TaskName, State, Description

# Manually trigger to test (without logging out)
Start-ScheduledTask -TaskName "ZoneB-Worker"
Start-ScheduledTask -TaskName "ZoneB-Watcher"

# Check they're running
Get-Process | Where-Object { $_.ProcessName -match "python" }
sqlite3 D:\zone_b\jobs.db "SELECT * FROM workers ORDER BY last_seen DESC LIMIT 3;"
```

### Step 6: Confirm portal compatibility

```powershell
# With Task Scheduler processes running, open the Tkinter portal normally
# Then check control.py's System Control panel:
# - Worker should show RUNNING
# - Watcher should show RUNNING
# - Stop buttons should still work
# - If you Stop via portal, Task Scheduler won't re-launch until next login
#   (this is expected — manual override wins during a session)
```

---

## ROLLBACK

If anything goes wrong:

```powershell
# Remove both tasks
Unregister-ScheduledTask -TaskName "ZoneB-Worker" -Confirm:$false
Unregister-ScheduledTask -TaskName "ZoneB-Watcher" -Confirm:$false

# Delete launcher scripts
Remove-Item D:\zone_b\scripts\start_worker.bat
Remove-Item D:\zone_b\scripts\start_watcher.bat

# Everything reverts to manual control.py management
```

---

## WHAT NOT TO DO

- Do NOT modify `control.py` — it stays as the manual control interface
- Do NOT modify `db_worker.py` or `processor.py`
- Do NOT create Windows Services (overkill, harder to debug, needs NSSM)
- Do NOT use startup folder shortcuts (no restart-on-failure capability)
- Do NOT change how the Tkinter portal launches — it remains independent
- Do NOT set tasks to run as SYSTEM — they must run as David's user account (same permissions, same paths, same .env access)

---

## SUCCESS CRITERIA

After a machine reboot:
1. Log in to Windows
2. Do NOT open the portal or run control.py
3. Wait 30 seconds
4. Check: `sqlite3 D:\zone_b\jobs.db "SELECT * FROM workers ORDER BY last_seen DESC LIMIT 3;"`
5. Worker and watcher should both be registered and running
6. Open the portal — System Control should show both as RUNNING
7. Pipeline should process any queued audio without manual intervention
