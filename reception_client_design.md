# Reception Client — Phase 1 Design Specification

**Version:** 1.0  
**Date:** 2026-03-11  
**Status:** Draft — for David's review before any code is written

---

## 1. What This Document Covers

Phase 1 delivers three things:

1. **A FastAPI server** running on the ProDesk alongside the existing Tkinter portal, serving as the single gatekeeper to `inventory.db`
2. **A lightweight reception client** (Tkinter) running on the reception PC, connecting to the ProDesk over LAN
3. **Two workflows:** QR scan → mark attendance, and reschedule a missed lesson

Nothing in the existing portal changes. The Tkinter portal continues to read/write `inventory.db` directly as it always has.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  ProDesk (Zone A)                                           │
│                                                             │
│  ┌──────────────────┐     ┌──────────────────────────────┐  │
│  │  Tkinter Portal  │     │  FastAPI Server               │  │
│  │  (main_window.py)│     │  (reception_api.py)           │  │
│  │                  │     │  port 8100                    │  │
│  │  Reads/writes    │     │  Reads/writes                 │  │
│  │  inventory.db    │     │  inventory.db                 │  │
│  │  directly        │     │  (WAL mode, busy_timeout)     │  │
│  └──────────────────┘     └──────────────────────────────┘  │
│           │                          │                      │
│           └──────── both on ─────────┘                      │
│                  D:\AI_phase\school\apps\                    │
│                  school_portal\data\inventory.db             │
└─────────────────────────────────────────────────────────────┘
                               │
                        LAN (192.168.50.x)
                               │
┌─────────────────────────────────────────────────────────────┐
│  Reception PC                                               │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Reception Client (Tkinter)                          │   │
│  │  (reception_client.py)                               │   │
│  │                                                      │   │
│  │  - QR scan attendance                                │   │
│  │  - View today's schedule                             │   │
│  │  - Reschedule missed lessons                         │   │
│  │                                                      │   │
│  │  Talks to ProDesk via HTTP → http://192.168.50.x:8100│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  USB QR Scanner (reads S:<student_id>)                      │
└─────────────────────────────────────────────────────────────┘
```

### Why FastAPI?

- Serialises all writes through one process — no SQLite locking conflicts
- WAL mode + `busy_timeout=3000` handles the case where the Tkinter portal is also writing
- Lightweight: single Python file, no external DB server needed
- Easy to extend later (Phase 2: book checkout, inventory lookup)

### Why not just share `inventory.db` over the network?

SQLite over SMB/network shares is unreliable and risks corruption. The FastAPI layer is the minimum viable protection for your canonical Zone A data.

---

## 3. Database Context

### Existing Schema (no changes)

**`students`** — 51 rows

| Column | Type | Notes |
|--------|------|-------|
| student_id | TEXT PK | e.g. `20000101` |
| first_name | TEXT | |
| last_name | TEXT | |
| level | TEXT | e.g. `SM4` |
| status | TEXT | `active` / `archived` |
| qr_code | TEXT UNIQUE | e.g. `S:20000101` |
| created_at | TEXT | |
| updated_at | TEXT | |

**`class_def`** — 35 rows

| Column | Type | Notes |
|--------|------|-------|
| class_id | TEXT PK | e.g. `mon_1710_sm4` |
| class_name | TEXT | e.g. `SM4 Monday` |
| day_of_week | INTEGER | 0=Mon, 6=Sun |
| start_time | TEXT | e.g. `17:10` |
| end_time | TEXT | e.g. `18:10` |
| level | TEXT | |
| teacher | TEXT | Default `David` |
| is_active | INTEGER | |

**`class_roster`** — 56 rows

| Column | Type | Notes |
|--------|------|-------|
| roster_id | INTEGER PK | Auto |
| class_id | TEXT FK | → class_def |
| student_id | TEXT FK | → students |
| enrolled_at | TEXT | |
| removed_at | TEXT | |

**`attendance`** — existing table

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto |
| student_id | TEXT FK | → students |
| class_id | TEXT FK | → class_def |
| date | TEXT | ISO date `YYYY-MM-DD` |
| status | TEXT | `present` / `absent` / `late` |
| scan_time | TEXT | ISO datetime |
| method | TEXT | `qr` / `manual` |

### New Table: `reschedule_log`

Tracks when a missed lesson is rescheduled to a different slot.

```sql
CREATE TABLE IF NOT EXISTS reschedule_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      TEXT NOT NULL,
    original_class_id   TEXT NOT NULL,
    original_date       TEXT NOT NULL,       -- YYYY-MM-DD
    rescheduled_class_id TEXT NOT NULL,
    rescheduled_date     TEXT NOT NULL,      -- YYYY-MM-DD
    reason          TEXT DEFAULT 'missed',
    created_by      TEXT DEFAULT 'reception',
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (original_class_id) REFERENCES class_def(class_id),
    FOREIGN KEY (rescheduled_class_id) REFERENCES class_def(class_id)
);
```

**Design decision:** This is a log table, not a mutation of the schedule. The original missed lesson stays as `absent` in attendance. The rescheduled lesson will generate a new `attendance` row when the student actually shows up and scans in at the rescheduled class.

---

## 4. API Endpoints

Base URL: `http://<prodesk_ip>:8100/api/v1`

### 4.1 Health Check

```
GET /health
```

Returns: `{"status": "ok", "db": "connected", "timestamp": "..."}`

Purpose: Reception client checks this on startup and shows a green/red connection indicator.

### 4.2 Scan Attendance

```
POST /attendance/scan
Body: {
    "qr_code": "S:20000101"
}
```

**Server-side logic:**

1. Strip known scanner artifacts (`♪`, `\r`, `\n`, non-printable chars)
2. Look up student by `qr_code` in `students` table
3. If not found → return `404` with `{"error": "unknown_qr", "qr_code": "..."}`
4. Find today's class for this student:
   - Get current day of week and time
   - Join `class_roster` → `class_def` to find which class this student should be in right now (within a ±15 min window of `start_time`)
   - If no class found → return `200` with `{"status": "no_class_now", "student": {...}}`
5. Check for duplicate: if attendance row already exists for this student + class + today → return `200` with `{"status": "already_marked", ...}`
6. Insert attendance row: `status='present'`, `method='qr'`, `scan_time=now`
7. Return `200`:

```json
{
    "status": "marked",
    "student": {
        "student_id": "20000101",
        "first_name": "[student1]",
        "level": "SM4"
    },
    "class": {
        "class_id": "tue_1610_sm4",
        "class_name": "SM4 Tuesday",
        "start_time": "16:10"
    },
    "scan_time": "2026-03-11T16:05:32"
}
```

**The ±15 min window:** A student scanning at 16:05 should match their 16:10 class. A student scanning at 15:30 should not. This is configurable in the API config.

### 4.3 Today's Schedule

```
GET /schedule/today
```

Returns all active classes for today's day of week, with enrolled students and attendance status:

```json
{
    "date": "2026-03-11",
    "day_of_week": 1,
    "classes": [
        {
            "class_id": "tue_1610_sm2",
            "class_name": "SM2 Tuesday",
            "start_time": "16:10",
            "end_time": "17:10",
            "level": "SM2",
            "students": [
                {
                    "student_id": "20000102",
                    "first_name": "[student2]",
                    "status": "present",
                    "scan_time": "16:05:32"
                },
                {
                    "student_id": "20000103",
                    "first_name": "[student3]",
                    "status": null
                }
            ]
        }
    ]
}
```

### 4.4 Student Missed Lessons

```
GET /students/{student_id}/missed?from=2026-03-01&to=2026-03-11
```

Returns classes where the student was expected (in roster) but has no `present` attendance record:

```json
{
    "student_id": "20000101",
    "first_name": "[student1]",
    "missed": [
        {
            "class_id": "mon_1710_sm4",
            "class_name": "SM4 Monday",
            "date": "2026-03-10",
            "already_rescheduled": false
        }
    ]
}
```

### 4.5 Available Reschedule Slots

```
GET /schedule/available?student_id=20000101&level=SM4
```

Returns upcoming classes at the same level that the student is NOT already enrolled in, within the next 7 days:

```json
{
    "slots": [
        {
            "class_id": "wed_1610_sm4",
            "class_name": "SM4 Wednesday",
            "date": "2026-03-12",
            "start_time": "16:10",
            "current_count": 3,
            "max_capacity": 6
        }
    ]
}
```

### 4.6 Reschedule a Lesson

```
POST /reschedule
Body: {
    "student_id": "20000101",
    "original_class_id": "mon_1710_sm4",
    "original_date": "2026-03-10",
    "rescheduled_class_id": "wed_1610_sm4",
    "rescheduled_date": "2026-03-12"
}
```

**Server-side logic:**

1. Validate student exists and is active
2. Validate both class_ids exist
3. Check the original lesson was indeed missed (no `present` attendance)
4. Check not already rescheduled (no existing `reschedule_log` entry)
5. Insert into `reschedule_log`
6. Return `200` with confirmation

**Important:** This does NOT temporarily add the student to the rescheduled class's roster. When they scan in at the rescheduled class, the `/attendance/scan` endpoint will need a secondary lookup: "is this student rescheduled into this class today?" This is handled by checking `reschedule_log` alongside `class_roster`.

---

## 5. Reception Client UI

### Layout: Single-window Tkinter app with tabs

**Tab 1: Scan Attendance (default, always focused)**

```
┌─────────────────────────────────────────────────┐
│  [QR Scan Field — auto-focused, hidden cursor]  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  [student1] — SM4 Tuesday (16:10) ✓ MARKED │  │ ← Last scan result
│  └───────────────────────────────────────────┘  │   (large font, green bg)
│                                                 │
│  Today's Scans:                                 │
│  16:05  [student1]  SM4 Tuesday    ✓            │
│  16:03  [student2]  SM2 Tuesday    ✓            │
│  15:58  [student4]  SM1 Tuesday    ✓            │
│                                                 │
│  ● Connected to ProDesk           11 Mar 2026   │
└─────────────────────────────────────────────────┘
```

- QR scan field is always focused (refocuses after every scan)
- Handles the `♪` terminator character from the USB scanner
- Large, clear feedback: green for success, yellow for "already marked", red for error
- Scan log shows today's history (scrollable)

**Tab 2: Today's Schedule**

```
┌─────────────────────────────────────────────────┐
│  Tuesday 11 March 2026                          │
│                                                 │
│  16:10–17:10  SM2 Tuesday                       │
│    ✓ [student2]    ✓ [student4]    ○ [student3] │
│                                                 │
│  17:10–18:10  SM2 Tuesday                       │
│    ○ [student3]    ○ [student5]                 │
│                                                 │
│  17:10–18:10  SM4 Monday  ← rescheduled         │
│    ○ [student1] (rescheduled from Mon 10 Mar)   │
│                                                 │
│  ● Connected to ProDesk           11 Mar 2026   │
└─────────────────────────────────────────────────┘
```

- ✓ = scanned present, ○ = not yet scanned
- Auto-refreshes every 30 seconds
- Shows rescheduled students with a visual indicator

**Tab 3: Reschedule**

```
┌─────────────────────────────────────────────────┐
│  Student: [dropdown or scan QR]                 │
│                                                 │
│  Missed Lessons (last 14 days):                 │
│  ┌───────────────────────────────────────────┐  │
│  │ ○ SM4 Monday — 10 Mar 2026               │  │
│  │ ○ SM4 Monday — 3 Mar 2026  (rescheduled) │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  Reschedule to:                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ ○ SM4 Wednesday — 12 Mar (3 students)     │  │
│  │ ○ SM4 Thursday — 13 Mar (2 students)      │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  [Confirm Reschedule]                           │
│                                                 │
│  ● Connected to ProDesk           11 Mar 2026   │
└─────────────────────────────────────────────────┘
```

- Select student → see their missed lessons → pick a new slot → confirm
- Already-rescheduled lessons are greyed out
- Shows class size so reception knows if there's room

---

## 6. QR Code Format

**Existing format:** `S:<student_id>` (e.g. `S:20000101`)

QR PNGs already exist at `D:\AI_phase\school\apps\school_portal\data\qr\students\`. No changes needed.

**Scanner handling:** The API strips the `S:` prefix and any trailing artifacts (`♪`, `\r`, `\n`, non-ASCII) before looking up the student. The client also pre-strips before sending, as a belt-and-braces measure.

---

## 7. Deployment

### On the ProDesk

```
D:\AI_phase\school\apps\school_portal\
├── data\
│   └── inventory.db              ← existing, unchanged
├── reception_api\
│   ├── reception_api.py          ← FastAPI server
│   ├── config.py                 ← IP, port, scan window, etc.
│   └── requirements.txt          ← fastapi, uvicorn
└── (existing portal files unchanged)
```

**Startup:** The FastAPI server runs as a separate process. It can be:
- Started manually: `python reception_api.py`
- Auto-started via Windows Task Scheduler on login
- Eventually wrapped as a Windows service

**It does NOT interfere with the Tkinter portal.** Both access `inventory.db` but SQLite in WAL mode with `busy_timeout` handles this safely when both are local processes on the same machine.

### On the Reception PC

```
C:\SiriReception\
├── reception_client.py           ← Tkinter app
├── config.py                     ← ProDesk IP, port
└── requirements.txt              ← requests (only dependency)
```

**Startup:** Shortcut on desktop, or auto-start on login via Task Scheduler.

**Network:** Reception PC must be on the same LAN segment (192.168.50.x). The Omada network should already handle this.

---

## 8. Security Considerations

Phase 1 is LAN-only with no authentication. This is acceptable because:
- The network is a controlled school environment behind the Omada router
- The API only exposes attendance and scheduling — no PII beyond first names
- `inventory.db` writes are limited to attendance rows and reschedule logs

**Phase 2 consideration:** If the API ever faces the internet or handles sensitive data, add API key auth (simple bearer token in the header).

---

## 9. Open Questions for David

1. **Class capacity:** Is there a max students per class? The reschedule endpoint needs to know whether to enforce limits. If so, where is this defined — in `class_def` or is it implicit?

2. **Reschedule window:** How far ahead can reception reschedule? 7 days? 14 days? Current term only?

3. **Multiple reschedules:** Can the same missed lesson be rescheduled more than once (e.g. they miss the rescheduled class too)?

4. **Scan window:** ±15 minutes before/after class start_time for matching a scan to a class — does that feel right, or should it be wider/narrower?

5. **ProDesk IP:** Is the ProDesk on a static IP on the Omada network? If not, we should assign one.

6. **Reception PC specs:** What OS and Python version is available on the reception PC? Do we need to bundle Python?

7. **Thai language:** Should the reception UI have Thai labels/buttons for the Thai reception staff, or is English fine?

---

## 10. What This Does NOT Cover (Future Phases)

- **Phase 2:** Book checkout/return at reception, inventory lookup
- **Phase 2:** Student profile viewer (read-only) at reception
- **Phase 3:** Browser-based reception UI (replacing Tkinter client)
- **Phase 3:** Tablet/phone check-in for parents at the door
- **Future:** Authentication, audit logging, multi-teacher support

---

## 11. Build Sequence

Once David approves this design:

1. **Claude Code Instruction 1:** Create `reschedule_log` migration in existing `db_schema.py`
2. **Claude Code Instruction 2:** Build `reception_api.py` (FastAPI server + all endpoints)
3. **Claude Code Instruction 3:** Build `reception_client.py` (Tkinter client)
4. **Testing:** Run both on the ProDesk first (client pointing to localhost), verify with real QR scanner
5. **Deploy:** Copy client to reception PC, point config at ProDesk IP

Each instruction will follow your SANE_ENGINEER format with persona, direct aim, overall aim, read-first diagnostics, and STOP gates.
