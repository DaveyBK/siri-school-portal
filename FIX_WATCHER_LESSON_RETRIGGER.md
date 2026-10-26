# FIX_WATCHER_LESSON_RETRIGGER.md

## Persona
Systems diagnostician — you are investigating a specific runtime bug in the watcher's lesson scheduling logic and applying a minimal, targeted fix.

## Direct Aim
Stop the watcher from re-triggering a lesson that has already been completed and stopped by the user. Currently, when a lesson is stopped via the Lesson Gate (Stop Lesson button), the watcher's next polling cycle sees the scheduled lesson still in the timetable and restarts it. This keeps happening until the watcher itself is stopped. The bug is most visible on the last lesson of the day.

## Overall Aim
The Lesson Gate must respect user intent. When a teacher stops a lesson, it stays stopped. The watcher should never override an explicit user action.

## Mandatory Read-First Phase
**STOP. Before doing anything else, read these two documents in full:**
1. `ZONE_B_BACKEND_INSTRUCTION_MANUAL.md`
2. `PROGRAM_MAP.md`

Confirm you have read both before proceeding.

## Investigation Phase (STOP GATE 1)
Before making ANY code changes, investigate and report back on ALL of the following:

1. **Watcher polling logic**: What code in the watcher checks the schedule and decides to start a lesson? Show the relevant function(s) and the decision flow.
2. **Lesson Gate start trigger**: What function or method actually starts a lesson via the Lesson Gate? What parameters does it use (schedule time, class ID, etc.)?
3. **Lesson Gate stop behaviour**: When the user clicks "Stop Lesson", what state changes occur? Is anything written to the database? Is a flag set in memory? Or does it just kill a process?
4. **Schedule lookup**: How does the watcher determine "there is a lesson that should be running now"? Is there a time window? Does it compare against current time? What is the matching logic?
5. **Existing "completed" or "finished" state**: Is there ANY existing mechanism (DB column, file flag, in-memory variable) that records a lesson has already been run today?

**Report your findings. Do NOT proceed to the fix until David confirms.**

## Fix Phase (STOP GATE 2)
Once David confirms the investigation findings, propose a fix. The fix should:

1. **Record completion**: When a lesson is stopped via the Lesson Gate, record that this lesson (identified by schedule slot + date) has been completed. This could be:
   - A database record (preferred — survives restarts)
   - An in-memory set (acceptable if a DB change is disproportionate)

2. **Check before triggering**: Before the watcher triggers a lesson start, it must check whether that lesson has already been completed today. If it has, skip it.

3. **Time window cutoff**: Add a maximum window after the scheduled start time beyond which the watcher will not start the lesson. Suggested: if current time is more than the lesson duration + 30 minutes past the scheduled start, do not trigger. This prevents zombie lessons at end of day.

4. **Daily reset**: Whatever completion tracking is used, it must reset for the next day so lessons work normally tomorrow.

**Present the proposed fix (files to change, logic to add) and wait for David's approval before writing any code.**

## Implementation Phase (STOP GATE 3)
After David approves the fix design:

1. Implement the changes
2. List every file modified and what changed
3. Confirm no other logic paths were altered

## What NOT To Do
- Do NOT refactor the watcher beyond this specific fix
- Do NOT change the Lesson Gate UI
- Do NOT modify the schedule/timetable system
- Do NOT touch the worker, transcription pipeline, or any downstream processing
- Do NOT change database schema without explicit approval
- Do NOT remove or rename existing functions
- Do NOT make changes to more than the minimum files needed

## Rollback
If anything goes wrong, the fix should be revertible by removing the added completion check. Note the exact lines/blocks added so they can be cleanly removed.
