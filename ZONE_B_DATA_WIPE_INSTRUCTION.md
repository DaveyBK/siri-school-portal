# Zone B Data Wipe — Claude Code Instruction

**Prepared:** 11 March 2026  
**Target machine:** Halo (Windows 11, PowerShell)  
**Venv:** `D:\envs\siri_worker\Scripts\python.exe`  
**Database:** `D:\zone_b\jobs.db` (SQLite)  
**Schema version:** v1 + migrations 002–008

---

## Persona

Systems engineer performing a controlled data wipe. You are methodical, cautious, and verify at every step. You do not improvise. You do not skip verification. You do not touch structure.

---

## Direct Aim

Remove all audio-derived data from Zone B on Halo so the system is clean for fresh recording. After this wipe, the pipeline should look as if it was freshly installed — all structural elements intact, zero data rows, zero audio files, zero logs from previous runs.

## Overall Aim

The pipeline has been stabilised after a debugging period. Old data includes artefacts from broken chunking, stalled workers, timeout errors, and test runs. This data must not contaminate the clean operational baseline going forward.

---

## Mandatory Read-First

Before doing anything, read these two files and confirm you have done so:

1. `D:\zone_b\ZONE_B_BACKEND_INSTRUCTION_MANUAL.md`
2. `D:\zone_b\PROGRAM_MAP.md`

**⛔ STOP GATE 1:** Report what you found in those files. List every database table you see documented and every folder that holds audio or audio-derived files. Do not proceed until David confirms.

---

## What NOT To Do

- Do NOT use DROP TABLE on anything. DELETE FROM only.
- Do NOT touch any `.py`, `.sql`, `.env`, `.md` source or config file.
- Do NOT touch `D:\zone_b\data\siri_audio_pipeline.db` (legacy DB — leave it).
- Do NOT touch anything in `D:\zone_b\schema\`.
- Do NOT touch anything on Zone A (Pi5) or the school portal database.
- Do NOT touch `D:\AI_phase\` or `D:\AI_COORD\` paths.
- Do NOT delete any folder — only delete files within folders.
- Do NOT run any pipeline code (no processor.py, no db_worker.py, no control.py).
- Do NOT modify the database schema in any way.
- Do NOT vacuum the database (David will decide on that separately).

---

## Execution Sequence

### Step 1 — Stop all services

Stop the worker, watcher, and Ollama. Leave the Flask portal running for post-wipe verification.

```powershell
cd D:\zone_b
D:\envs\siri_worker\Scripts\python.exe control.py watcher stop
D:\envs\siri_worker\Scripts\python.exe control.py worker stop
```

Verify both are stopped:

```powershell
D:\envs\siri_worker\Scripts\python.exe control.py status
```

Also stop Ollama if running:

```powershell
tasklist | findstr ollama
# If found:
taskkill /F /IM ollama.exe
```

**⛔ STOP GATE 2:** Confirm all services are stopped. Show output of `control.py status` and `tasklist | findstr ollama`. Do not proceed until David confirms.

---

### Step 2 — Clear audio files from all pipeline folders

Delete all files (not folders) in each of these locations:

| Folder | What's in it |
|--------|-------------|
| `D:\zone_b\pc_ingest\incoming\` | Unprocessed WAV files (the 28 files currently sitting here) |
| `D:\zone_b\pc_ingest\work\` | Files mid-processing |
| `D:\zone_b\pc_ingest\transcripts\` | Legacy file-based transcript output |
| `D:\zone_b\archive\` | Date-organised subfolders containing processed WAVs and TXTs — delete everything including subfolders |
| `D:\zone_b\quarantine_outside_lesson\` | WAVs received outside lesson gate |

PowerShell commands:

```powershell
# Incoming WAVs
Remove-Item "D:\zone_b\pc_ingest\incoming\*" -Force -ErrorAction SilentlyContinue

# Work directory
Remove-Item "D:\zone_b\pc_ingest\work\*" -Force -ErrorAction SilentlyContinue

# Legacy transcripts
Remove-Item "D:\zone_b\pc_ingest\transcripts\*" -Force -ErrorAction SilentlyContinue

# Archive (date subfolders and all contents)
Remove-Item "D:\zone_b\archive\*" -Recurse -Force -ErrorAction SilentlyContinue

# Quarantine
Remove-Item "D:\zone_b\quarantine_outside_lesson\*" -Force -ErrorAction SilentlyContinue
```

**Verify each folder is empty:**

```powershell
Get-ChildItem "D:\zone_b\pc_ingest\incoming\" -Recurse | Measure-Object
Get-ChildItem "D:\zone_b\pc_ingest\work\" -Recurse | Measure-Object
Get-ChildItem "D:\zone_b\pc_ingest\transcripts\" -Recurse | Measure-Object
Get-ChildItem "D:\zone_b\archive\" -Recurse | Measure-Object
Get-ChildItem "D:\zone_b\quarantine_outside_lesson\" -Recurse | Measure-Object
```

All counts should be 0.

**⛔ STOP GATE 3:** Show folder verification output. Do not proceed until David confirms.

---

### Step 3 — Clear log files

Delete all log, PID, and meta files from the control logs directory:

```powershell
# Control logs, PIDs, and meta files
Remove-Item "D:\zone_b\logs\control\*.log" -Force -ErrorAction SilentlyContinue
Remove-Item "D:\zone_b\logs\control\*.pid" -Force -ErrorAction SilentlyContinue
Remove-Item "D:\zone_b\logs\control\*.meta.json" -Force -ErrorAction SilentlyContinue

# Pipeline logs
Remove-Item "D:\zone_b\pc_ingest\logs\*" -Force -ErrorAction SilentlyContinue
```

**Verify:**

```powershell
Get-ChildItem "D:\zone_b\logs\control\" | Measure-Object
Get-ChildItem "D:\zone_b\pc_ingest\logs\" | Measure-Object
```

---

### Step 4 — Count database rows before deletion

This step counts rows in every table that will be wiped. It does NOT delete anything.

```powershell
D:\envs\siri_worker\Scripts\python.exe -c "
import sqlite3

db = sqlite3.connect(r'D:\zone_b\jobs.db')
c = db.cursor()

tables_to_wipe = [
    'parent_messages',
    'lesson_extractions',
    'transcript_segment',
    'transcript',
    'diarisation_metrics',
    'summary',
    'model_run',
    'audio_vad',
    'audio_environment',
    'job',
    'audio_clip',
    'notification_outbox',
    'worker_status',
    'ops_daily',
    'lesson_session',
    'session',
]

print('=== PRE-WIPE ROW COUNTS ===')
for t in tables_to_wipe:
    try:
        count = c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        print(f'  {t}: {count}')
    except Exception as e:
        print(f'  {t}: TABLE NOT FOUND ({e})')

# Also show device table (will NOT be wiped)
count = c.execute('SELECT COUNT(*) FROM device').fetchone()[0]
print(f'  device: {count} (STRUCTURAL — will NOT be deleted)')

db.close()
print()
print('Counts reported. Waiting for confirmation before deleting.')
"
```

**⛔ STOP GATE 4:** Show the pre-wipe row counts. Do not execute any DELETE statements until David confirms. This is the point of no return.

---

### Step 5 — Execute the deletion

Only after David confirms Step 4:

```powershell
D:\envs\siri_worker\Scripts\python.exe -c "
import sqlite3

db = sqlite3.connect(r'D:\zone_b\jobs.db')
c = db.cursor()

# Disable FK checks during bulk delete to avoid ordering issues
c.execute('PRAGMA foreign_keys = OFF')

tables_to_wipe = [
    'parent_messages',
    'lesson_extractions',
    'transcript_segment',
    'transcript',
    'diarisation_metrics',
    'summary',
    'model_run',
    'audio_vad',
    'audio_environment',
    'job',
    'audio_clip',
    'notification_outbox',
    'worker_status',
    'ops_daily',
    'lesson_session',
    'session',
]

print('=== EXECUTING DATA WIPE ===')
for t in tables_to_wipe:
    try:
        c.execute(f'DELETE FROM {t}')
        print(f'  CLEARED: {t} ({c.rowcount} rows deleted)')
    except Exception as e:
        print(f'  SKIPPED: {t} ({e})')

c.execute('PRAGMA foreign_keys = ON')
db.commit()
db.close()
print()
print('Database content wipe complete.')
"
```

**The `device` table is NOT in this list.** It holds pi5/pc device definitions and is structural.

---

### Step 6 — Verify the database is clean

```powershell
D:\envs\siri_worker\Scripts\python.exe -c "
import sqlite3

db = sqlite3.connect(r'D:\zone_b\jobs.db')
c = db.cursor()

tables_to_check = [
    'parent_messages',
    'lesson_extractions',
    'transcript_segment',
    'transcript',
    'diarisation_metrics',
    'summary',
    'model_run',
    'audio_vad',
    'audio_environment',
    'job',
    'audio_clip',
    'notification_outbox',
    'worker_status',
    'ops_daily',
    'lesson_session',
    'session',
    'device',
]

print('=== POST-WIPE ROW COUNTS ===')
all_clean = True
for t in tables_to_check:
    try:
        count = c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        if t == 'device':
            print(f'  {t}: {count} device records retained (STRUCTURAL — correct)')
        elif count == 0:
            print(f'  {t}: 0 (clean)')
        else:
            print(f'  {t}: WARNING — {count} rows remain!')
            all_clean = False
    except Exception as e:
        print(f'  {t}: TABLE NOT FOUND ({e})')

print()
if all_clean:
    print('All data tables are clean. Device table retained.')
else:
    print('WARNING: Some tables still have data. Investigate before proceeding.')

db.close()
"
```

**Expected result:** Every table shows 0 rows except `device` which should retain its existing records.

**⛔ STOP GATE 5:** Show post-wipe verification. Do not proceed until David confirms.

---

### Step 7 — Restart services

```powershell
cd D:\zone_b

# Start Ollama first (needed for langextract)
Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden

# Wait for Ollama to be ready
Start-Sleep -Seconds 5

# Start watcher and worker
D:\envs\siri_worker\Scripts\python.exe control.py watcher start
D:\envs\siri_worker\Scripts\python.exe control.py worker start

# Verify
D:\envs\siri_worker\Scripts\python.exe control.py status
```

---

### Step 8 — Final verification via Flask portal

Open the Flask portal at http://localhost:5555 and check:

- Pipeline queue: 0 incoming, 0 queued, 0 running, 0 done, 0 error
- Recent errors: empty
- Services: watcher RUNNING, worker RUNNING, Ollama RUNNING, Pi5 UP

**⛔ STOP GATE 6 (FINAL):** Report the portal state. Confirm the system is clean, running, and ready for fresh data.

---

## Rollback

There is no rollback for this operation. The audio files and derived data cannot be recovered once deleted. This is intentional — the data being wiped is debug-era artefacts that should not be retained.

If the database schema is accidentally damaged (it should not be — no DROP or ALTER commands are used), reinitialise with:

```powershell
D:\envs\siri_worker\Scripts\python.exe D:\zone_b\pc_ingest\db_init.py
```

This recreates the schema from `pipeline_v1.sql` + migrations. But this should NOT be needed.

---

## Post-Wipe Notes

After confirming the wipe is clean, David should:

1. Run a test lesson capture through the full pipeline to verify end-to-end function
2. Check `nvidia-smi` to confirm VRAM has dropped back to normal (~300-600 MB) after the worker restart
3. Consider whether to VACUUM the database to reclaim disk space (optional, can be done later)

---

## Summary of Tables

| Table | Action | Reason |
|-------|--------|--------|
| `parent_messages` | DELETE FROM | Audio-derived LINE message drafts |
| `lesson_extractions` | DELETE FROM | LangExtract output |
| `transcript_segment` | DELETE FROM | Per-segment transcript data |
| `transcript` | DELETE FROM | Full transcripts |
| `diarisation_metrics` | DELETE FROM | Diarization stats |
| `summary` | DELETE FROM | Per-clip class summaries |
| `model_run` | DELETE FROM | Model execution logs |
| `audio_vad` | DELETE FROM | VAD metrics |
| `audio_environment` | DELETE FROM | Audio quality metrics |
| `job` | DELETE FROM | All job queue records |
| `audio_clip` | DELETE FROM | Ingested file metadata |
| `notification_outbox` | DELETE FROM | Notification queue |
| `worker_status` | DELETE FROM | Worker heartbeat records |
| `ops_daily` | DELETE FROM | Daily ops rollup |
| `lesson_session` | DELETE FROM | Lesson session history |
| `session` | DELETE FROM | Legacy recording sessions |
| `device` | **KEEP** | Structural — device definitions |
