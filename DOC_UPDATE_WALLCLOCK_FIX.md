# DOC_UPDATE_WALLCLOCK_FIX.md

## Persona
**Technical Writer / Systems Cartographer** — precise, minimal, evidence-based documentation updates only.

## Direct Aim
Update Zone B documentation to record today's fix: the `-use_wallclock_as_timestamps 1` flag added to `record_start.sh` on the Pi5 to resolve the ffmpeg segmentation failure.

## Overall Aim
Ensure the Pi5 capture node documentation accurately reflects the live system so future redeployments or audits don't reintroduce the chunking bug.

## Mandatory Read-First
Before doing ANYTHING, read these two files completely:
1. `D:\zone_b\ZONE_B_BACKEND_INSTRUCTION_MANUAL.md`
2. `D:\zone_b\PROGRAM_MAP.md`

## STOP GATE 1 — After reading docs
Tell me:
- Where the Pi5 section is in each doc
- What `record_start.sh` currently says in the docs
- Whether the staging mover service (`siri-staging-mover.service`) is documented

Do NOT make any edits until I confirm.

---

## What Changed (2026-03-12)

### Root Cause
The ReSpeaker 4-Mic Array's ALSA driver produces non-monotonic DTS (decoding timestamps) after extended Pi5 uptime. ffmpeg's `-f segment -segment_time 600` relies on stream timestamps to determine segment boundaries. When DTS jumps backwards repeatedly, the internal segment timer never reaches 600 seconds, so ffmpeg writes one continuous file instead of 10-minute chunks.

### Symptom
- Single WAV file growing indefinitely in `/var/lib/siri/audio/staging/`
- Staging mover never moves it (needs >1 file to act — skips the "active" file)
- No files reach `outgoing/`, no transfers to Halo, pipeline starves
- Lesson session exists in DB but has 0 clips, 0 jobs, 0 transcripts

### Fix Applied
Added `-use_wallclock_as_timestamps 1` before the ALSA input in `record_start.sh`. This tells ffmpeg to use system wallclock time instead of device-reported timestamps for segment timing.

### Current `record_start.sh` (LIVE as of 2026-03-12)
```bash
#!/usr/bin/env bash
set -euo pipefail
STAGEDIR="/var/lib/siri/audio/staging"
mkdir -p "$STAGEDIR"
exec /usr/bin/ffmpeg -hide_banner -loglevel warning \
  -use_wallclock_as_timestamps 1 \
  -f alsa -thread_queue_size 512 -ac 2 -ar 16000 -i plughw:CARD=ArrayUAC10,DEV=0 \
  -c:a pcm_s16le \
  -f segment -segment_time 600 -reset_timestamps 1 -strftime 1 \
  "${STAGEDIR}/%Y-%m-%d_%H-%M-%S.wav"
```

### Pi5 Services (current full list, all enabled)
| Service | Purpose | Status |
|---------|---------|--------|
| `classroom-record.service` | ffmpeg recording (10-min WAV chunks) | LIVE |
| `siri-staging-mover.service` | Moves completed chunks from staging → outgoing | LIVE |
| `siri-transfer.timer` | scp files from outgoing → Halo every ~5 min | LIVE |
| `siri-audio-cleanup.timer` | Daily cleanup of old files | LIVE |
| `siri-remote.service` | BLE remote (ESP32 SiriRemote) — not in use | DISABLED (2026-03-12) |

### BT Remote Disabled
`siri-remote.service` was stopped and disabled on 2026-03-12. The ESP32 SiriRemote (MAC: `08:92:72:9B:2B:02`) has not been connecting — the service was stuck in a scan/retry loop consuming resources for no benefit. The remote is not currently used to trigger recording start/stop.

Commands run:
```bash
sudo systemctl stop siri-remote.service
sudo systemctl disable siri-remote.service
```

To re-enable when the remote is needed again:
```bash
sudo systemctl enable --now siri-remote.service
```

---

## Edits Required

### Edit 1: ZONE_B_BACKEND_INSTRUCTION_MANUAL.md
Find the Pi5 section. Update:
- The `record_start.sh` script content to include `-use_wallclock_as_timestamps 1`
- Add `siri-staging-mover.service` to the Pi5 services table if not already there
- Update `siri-remote.service` status to DISABLED (not in use, stopped/disabled 2026-03-12)
- Add a "Known Issues / Fixes" note about the ALSA DTS bug and the wallclock workaround

### Edit 2: PROGRAM_MAP.md
Find the Pi5 scripts table. Update:
- The description for `record_start.sh` to mention the wallclock flag
- Add `staging_mover.sh` to the scripts table if not already there
- Update the Pi5 services table to include `siri-staging-mover.service` if missing
- Update `siri-remote.service` status to DISABLED (not in use, stopped/disabled 2026-03-12)

### Edit 3: Add audit timestamp headers
Any section you edit must have its verification date updated to `2026-03-12`.

---

## STOP GATE 2 — After edits
Show me a diff summary of every change you made. List each file, each section edited, and the before/after.

## What NOT To Do
- Do NOT rewrite sections that don't need updating — surgical edits only.
- Do NOT change any Zone B (Halo-side) documentation — this is Pi5 only.
- Do NOT alter any code files, scripts, configs, or database.
- Do NOT remove or restructure existing content — only add/update.
- Do NOT invent information — only document what is stated in this instruction.

## Rollback
If anything goes wrong: `git checkout -- ZONE_B_BACKEND_INSTRUCTION_MANUAL.md PROGRAM_MAP.md`
