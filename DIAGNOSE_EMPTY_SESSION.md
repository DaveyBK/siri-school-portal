# DIAGNOSE_EMPTY_SESSION.md

## Persona
**Systems Diagnostician** — methodical, evidence-first, no speculation without logs.

## Direct Aim
Determine why lesson session `b8e6f2ca-fd79-4c44-b428-eb643eebf87a` (2026-03-12, ~11:38–12:15 Bangkok time / 04:38–05:15 UTC) produced 0 recordings, 0 transcripts, and 0 summaries.

## Overall Aim
Identify the exact break point in the Pi5 → Halo pipeline so we can fix it and prevent silent data loss on future lessons.

## Symptom Summary
- Flask portal (localhost:5555) shows the session exists but: Summaries (0), Lesson Transcript (0 recordings), Teacher Lesson Record says "No chunk summaries available — run the pipeline first."
- System Control panel shows: Watcher RUNNING, Worker RUNNING, Pi5 UP (4ms), Ollama RUNNING, Flask Portal RUNNING.
- Pipeline queue: 0 incoming WAV files. Previous job counts (9 langextract, 20 summarise_lesson, 32 transcribe) appear to be from earlier sessions, not today.
- The lesson was an extra lesson (Extra [student1], Phonics 2, 11:30–12:30) with audio from a YouTube demo playing through the classroom speaker.

## Mandatory Read-First
Before doing ANYTHING, read these two files completely:
1. `D:\zone_b\ZONE_B_BACKEND_INSTRUCTION_MANUAL.md`
2. `D:\zone_b\PROGRAM_MAP.md`

## STOP GATE 1 — After reading docs
Tell me what you found. Do NOT proceed to investigation until I confirm.

---

## Investigation Plan (execute in order after STOP GATE 1 clearance)

### Step 1: Check Pi5 (SSH from Halo)

SSH to `audiocapture@192.168.50.250` and run:

```bash
# 1a. Was classroom-record.service running during the lesson?
journalctl -u classroom-record.service --since "2026-03-12 11:00" --until "2026-03-12 13:00" --no-pager

# 1b. What's in staging right now?
ls -la /var/lib/siri/audio/staging/

# 1c. What's in outgoing right now?
ls -la /var/lib/siri/audio/outgoing/

# 1d. Staging mover log — did it move anything today?
grep "2026-03-12" /var/log/siri-staging-mover.log

# 1e. Transfer log — did anything transfer to Halo today?
grep "2026-03-12" /var/log/siri-transfer.log

# 1f. Are there files stuck anywhere?
find /var/lib/siri/audio/ -name "2026-03-12*" -ls
```

### Step 2: Check Halo incoming directory

```powershell
# 2a. Is anything in incoming?
dir D:\zone_b\pc_ingest\incoming\

# 2b. Was anything quarantined today?
dir D:\zone_b\quarantine_outside_lesson\ | Where-Object { $_.LastWriteTime -gt "2026-03-12" }

# 2c. Check the watcher log for today
Get-Content D:\zone_b\logs\control\watcher.out.log -Tail 50
Get-Content D:\zone_b\logs\control\watcher.err.log -Tail 50

# 2d. Check the worker log for today
Get-Content D:\zone_b\logs\control\worker.out.log -Tail 50
Get-Content D:\zone_b\logs\control\worker.err.log -Tail 50
```

### Step 3: Check DB state for this session

```powershell
python -c "
import sqlite3
conn = sqlite3.connect('D:/zone_b/jobs.db')
c = conn.cursor()

# Session details
print('=== SESSION ===')
for r in c.execute('SELECT * FROM lesson_session WHERE session_id = ?', ('b8e6f2ca-fd79-4c44-b428-eb643eebf87a',)):
    print(r)

# Any jobs linked to this session?
print('\n=== JOBS FOR THIS SESSION ===')
for r in c.execute('SELECT * FROM jobs WHERE session_id = ?', ('b8e6f2ca-fd79-4c44-b428-eb643eebf87a',)):
    print(r)

# Most recent jobs regardless of session
print('\n=== LAST 10 JOBS ===')
for r in c.execute('SELECT job_id, session_id, wav_path, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10'):
    print(r)

# Any recent sessions
print('\n=== LAST 5 SESSIONS ===')
for r in c.execute('SELECT session_id, started_at, stopped_at, is_active FROM lesson_session ORDER BY started_at DESC LIMIT 5'):
    print(r)
"
```

## STOP GATE 2 — After all investigation steps
Present ALL findings. Do NOT attempt any fixes. Just report what you found.

---

## What NOT To Do
- Do NOT modify any files.
- Do NOT restart any services.
- Do NOT create, delete, or move any WAV files.
- Do NOT alter the database.
- Do NOT guess — if a log is empty or a command fails, report exactly what happened.
- Do NOT run the pipeline or trigger any processing.

## Rollback
This is a read-only diagnostic. Nothing to roll back.
