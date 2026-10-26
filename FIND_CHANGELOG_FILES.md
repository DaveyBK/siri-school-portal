# TASK: Find Existing Changelog / Change Record Files

**Persona:** File system detective
**Direct aim:** Find any existing file that tracks changes, versions, history, or updates across both repos
**Overall aim:** Avoid creating a duplicate changelog when one may already exist under a different name

---

## Search Scope

Search these directories recursively:

1. `D:\zone_b\` (Zone B repo)
2. `D:\AI_phase\school\apps\school_portal\` (School portal repo)
3. `D:\AI_phase\school\docs\` (if it exists)

## What to Search For

### Pass 1: Filename patterns
Search for any file matching these patterns (case-insensitive):
```
*changelog*
*change_log*
*changes*
*history*
*version*
*release*
*updates*
*log.md
*log.txt
*log.yaml
*record*
*tracker*
*fixes*
*resolved*
*milestones*
*ops_ready*
*patch*
*notes*
*whatsnew*
```

Command:
```powershell
Get-ChildItem -Path D:\zone_b, D:\AI_phase\school -Recurse -File -Include *.md,*.txt,*.yaml,*.yml,*.json |
  Where-Object { $_.Name -match '(?i)(changelog|change_log|changes|history|version|release|updates|record|tracker|fixes|resolved|milestones|ops_ready|patch|notes|whatsnew)' } |
  Select-Object FullName, LastWriteTime, Length |
  Format-Table -AutoSize
```

### Pass 2: Content search
Search inside .md and .txt files for changelog-like content:
```powershell
Get-ChildItem -Path D:\zone_b, D:\AI_phase\school -Recurse -File -Include *.md,*.txt |
  Select-String -Pattern '(?i)(version history|change log|what changed|bug fix|resolved|patch notes|release notes|## v\d|## \d{4}-\d{2})' -List |
  Select-Object Path, LineNumber, Line |
  Format-Table -AutoSize
```

### Pass 3: Check ZONE_B_BACKEND_INSTRUCTION_MANUAL.md specifically
```powershell
Select-String -Path "D:\zone_b\ZONE_B_BACKEND_INSTRUCTION_MANUAL.md" -Pattern '(?i)(version|history|change|update|fix|resolved)' |
  Select-Object LineNumber, Line |
  Format-Table -AutoSize
```

---

## Output

Report ALL findings in a table:

| File Path | Type | Last Modified | Description |
|-----------|------|---------------|-------------|
| ... | ... | ... | What it contains / how it's used |

If nothing is found, say so clearly. Do NOT create any files.

**STOP after reporting. Do not create, modify, or suggest anything.**
