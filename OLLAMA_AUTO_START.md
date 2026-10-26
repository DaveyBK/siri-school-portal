# ADD OLLAMA AUTO-START TO TASK SCHEDULER

## Persona
**Windows Systems Engineer** — small, scoped task. Same pattern as the existing ZoneB-Worker and ZoneB-Watcher tasks.

## Direct Aim
Add a Task Scheduler entry that runs `ollama serve` at login, before the worker and watcher start. Without Ollama running, langextract jobs fail silently.

## Overall Aim
Complete the auto-start coverage so the full pipeline is ready after a reboot without manual intervention.

---

## CONTEXT (CONFIRMED — DO NOT RE-INVESTIGATE)

- Ollama is currently started manually or not at all
- Worker depends on Ollama for langextract (HTTP API on localhost:11434)
- Worker and Watcher already have Task Scheduler entries (ZoneB-Worker, ZoneB-Watcher)
- Ollama must start BEFORE the worker attempts langextract jobs
- `ollama serve` is the command that starts the Ollama server
- OLLAMA_MAX_VRAM is set as a user-level environment variable (4GB cap) — Ollama will pick this up automatically

---

## STEP 1: FIND OLLAMA EXECUTABLE PATH

```powershell
# Find where ollama.exe lives
Get-Command ollama | Format-List Source
# Or
where.exe ollama
```

## STEP 2: CREATE LAUNCHER SCRIPT

Create `D:\zone_b\scripts\start_ollama.bat`:

```bat
@echo off
REM Check if Ollama is already running
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %ERRORLEVEL% EQU 0 (
    echo Ollama already running, exiting.
    exit /b 0
)
start "" /B "<OLLAMA_PATH>\ollama.exe" serve
```

Replace `<OLLAMA_PATH>` with the actual path from Step 1.

## STEP 3: TEST THE SCRIPT

```powershell
# If Ollama is already running, the script should no-op
D:\zone_b\scripts\start_ollama.bat

# If Ollama is not running, stop it first to test the start path
# Get-Process ollama* | Stop-Process -Force
# Start-Sleep 3
# D:\zone_b\scripts\start_ollama.bat
# curl -s http://localhost:11434/api/tags
```

---

## >>> STOP GATE <<<
**Confirm the script works (both the already-running and fresh-start cases) before registering with Task Scheduler.**

---

## STEP 4: REGISTER TASK SCHEDULER TASK

```powershell
$ollamaAction = New-ScheduledTaskAction `
    -Execute "D:\zone_b\scripts\start_ollama.bat" `
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
    -TaskName "ZoneB-Ollama" `
    -Action $ollamaAction `
    -Trigger $loginTrigger `
    -Settings $settings `
    -Description "Ollama server — auto-start on login (must run before Worker)"
```

### Verify:
```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -match "ZoneB" } | Format-List TaskName, State
```

Should show three tasks: ZoneB-Ollama, ZoneB-Worker, ZoneB-Watcher.

## STEP 5: UPDATE PROGRAM_MAP.md

Add Ollama to the auto-start section:

```markdown
- **ZoneB-Ollama** — triggers on user login, calls `ollama serve` (must start before Worker)
```

---

## ROLLBACK

```powershell
Unregister-ScheduledTask -TaskName "ZoneB-Ollama" -Confirm:$false
Remove-Item D:\zone_b\scripts\start_ollama.bat -ErrorAction SilentlyContinue
```

---

## WHAT NOT TO DO

- Do NOT modify Ollama's configuration
- Do NOT change the OLLAMA_MAX_VRAM setting
- Do NOT modify the worker or watcher tasks
- Do NOT modify control.py
