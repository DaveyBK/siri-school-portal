# D:\ Drive Audit — Claude Code Instruction

**Prepared:** 11 March 2026  
**Target machine:** Halo (Windows 11, PowerShell)  
**Scope:** Full inventory of `D:\` — classify everything, delete nothing

---

## Persona

Systems archivist. You catalogue, classify, and report. You do not delete, move, rename, or modify anything. You do not make assumptions about what is safe to remove — you flag uncertainty for David to decide.

---

## Direct Aim

Produce a complete inventory of everything on `D:\`, classified by status (active, legacy, archive-candidate, unknown). Flag anything ambiguous for human inspection.

## Overall Aim

After months of rapid development, debugging, and iteration, the D:\ drive has accumulated files, folders, specs, and artefacts that may no longer be needed. This audit creates visibility so David can make informed decisions about what to archive or delete.

---

## Mandatory Read-First

Before starting the audit, read these files to understand what SHOULD exist:

1. `D:\zone_b\ZONE_B_BACKEND_INSTRUCTION_MANUAL.md`
2. `D:\zone_b\PROGRAM_MAP.md`

These define the known-good structure for Zone B. Everything documented there is **active** unless explicitly marked deprecated in the document itself.

---

## What NOT To Do

- Do NOT delete, move, rename, or modify any file or folder.
- Do NOT open or read `.env` files (they contain secrets).
- Do NOT read database files (`.db`, `.sqlite`) beyond checking they exist and their size.
- Do NOT descend into `.git` directories — just note they exist.
- Do NOT descend into `__pycache__` directories — just note they exist.
- Do NOT descend into `node_modules` directories — just note they exist.
- Do NOT list individual WAV files — just count them and report total size per folder.
- Do NOT list individual files inside `envs\` (venv) — just confirm the venv exists and report its size.

---

## Execution

### Step 1 — Top-level inventory

List everything at `D:\` root level (files and folders, one level deep only).

For each item, report:
- Name
- Type (file or folder)
- Size (for files; for folders, total size if quick to calculate)
- Last modified date
- Your initial classification (see categories below)

```powershell
Get-ChildItem D:\ -Force | Select-Object Name, LastWriteTime, @{N='Type';E={if($_.PSIsContainer){'FOLDER'}else{'FILE'}}}, @{N='SizeMB';E={if($_.PSIsContainer){[math]::Round((Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB, 1)}else{[math]::Round($_.Length / 1MB, 1)}}}
```

**Note:** If any folder is very large (>10 GB), skip the size calculation for it and note "LARGE — skipped size calc". Do not hang on a slow recursive size check.

**⛔ STOP GATE 1:** Present the top-level inventory with initial classifications. Do not proceed deeper until David confirms.

---

### Step 2 — Classify each top-level item

Use these categories:

| Category | Meaning | Examples |
|----------|---------|---------|
| **ACTIVE** | Currently used by the running system | `zone_b`, `AI_COORD`, `envs` |
| **ACTIVE-RELATED** | Supports the active system but not part of the pipeline itself | `AI_phase` (school portal, c-test app) |
| **LEGACY** | Superseded by current system, documented as deprecated | `ai_worker` if it exists |
| **ARCHIVE-CANDIDATE** | Likely no longer needed but not confirmed | `_TRASH_*` folders, old spec files at root |
| **UNKNOWN** | Cannot determine status — needs David's input | Anything not documented or not obviously categorisable |
| **INFRASTRUCTURE** | System/tool folders not project-specific | `.claude`, venv folders |

For items classified as **UNKNOWN** or **ARCHIVE-CANDIDATE**, add a one-line note explaining why.

---

### Step 3 — Deep dive into ACTIVE and ACTIVE-RELATED folders

For each folder classified as ACTIVE or ACTIVE-RELATED, go one or two levels deeper and look for:

1. **Files/folders not documented** in the instruction manual or PROGRAM_MAP
2. **Duplicate or overlapping content** (e.g. multiple README files covering the same thing)
3. **Legacy/deprecated items** inside active folders (e.g. `pc_ingest/worker.py` which is documented as legacy)
4. **Orphaned files** — loose files that don't belong to any clear structure
5. **Empty folders**
6. **Very old files** — anything with a last-modified date before December 2024 that isn't a stable config file

For each finding, report:
- Path
- What it is (if you can tell)
- Last modified
- Recommended classification
- Confidence level (HIGH / MEDIUM / LOW)

---

### Step 4 — Check for cross-references

Look for files or folders that are referenced in the instruction manual or PROGRAM_MAP but might not exist:

```powershell
# Check documented paths exist
$paths = @(
    "D:\zone_b\jobs.db",
    "D:\zone_b\control.py",
    "D:\zone_b\schema\pipeline_v1.sql",
    "D:\AI_COORD\CLAWDBOT\clawdbot.py",
    "D:\AI_COORD\SCRIPTS\PYANNOTE_SAFELOAD.py",
    "D:\AI_COORD\INVARIANTS\DIARIZATION_GUARDRAILS.md",
    "D:\AI_phase\school\apps\school_portal\",
    "D:\AI_phase\school\apps\c_test_app\",
    "D:\AI_phase\school\services\zone_sync\",
    "D:\envs\siri_worker\Scripts\python.exe",
    "D:\zoneb_private_repo\"
)

foreach ($p in $paths) {
    if (Test-Path $p) { Write-Host "EXISTS: $p" }
    else { Write-Host "MISSING: $p" -ForegroundColor Red }
}
```

Also check for paths documented as deprecated that still exist:

```powershell
$deprecated = @(
    "D:\ai_worker\",
    "D:\AI_phase\school\services\pc_ingest\",
    "D:\zone_b\data\siri_audio_pipeline.db"
)

foreach ($p in $deprecated) {
    if (Test-Path $p) { Write-Host "STILL EXISTS (deprecated): $p" -ForegroundColor Yellow }
    else { Write-Host "GONE (good): $p" }
}
```

---

### Step 5 — Loose files at D:\ root

For every file sitting directly at `D:\` root (not in a folder), report:
- Filename
- Size
- Last modified
- First few lines of content (if text file, max 5 lines)
- Best guess at what it is and whether it belongs somewhere or is orphaned

---

### Step 6 — Produce the final report

Compile everything into a single structured report with these sections:

```
## 1. Top-Level Summary
   - Total items at D:\ root
   - Breakdown by classification

## 2. Active System Map
   - Confirmed active paths and their purpose

## 3. Archive Candidates
   - Items recommended for archiving/deletion with rationale
   - Confidence level for each

## 4. Items Requiring David's Decision
   - UNKNOWN items that need human judgment
   - Ambiguous cases where classification could go either way
   - Include enough context for David to decide without having to go look

## 5. Legacy Items Still Present
   - Deprecated paths that still exist on disk

## 6. Loose Files at Root
   - Files sitting at D:\ that should probably be moved or deleted

## 7. Missing References
   - Documented paths that don't exist

## 8. Findings Inside Active Folders
   - Undocumented, orphaned, or legacy items found inside active directories
```

**⛔ STOP GATE 2 (FINAL):** Present the complete report. Do not suggest or execute any changes. David decides what to do with the findings.

---

## Output

Save the final report as:

```
D:\zone_b\D_DRIVE_AUDIT_2026-03-11.md
```

This location keeps it with the operational docs. It is a point-in-time snapshot.

---

## Effort Level

This is a read-only discovery task. Medium effort. Take your time reading the reference docs, be thorough in the inventory, but don't overthink classifications — flag anything uncertain rather than guessing.
