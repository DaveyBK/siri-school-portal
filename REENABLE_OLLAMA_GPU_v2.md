# RE-ENABLE OLLAMA GPU INFERENCE FOR LANGEXTRACT

## Persona
**Systems Engineer / Performance Tuner** — you are carefully re-enabling GPU inference for Ollama on an RTX 2060 Super (8GB VRAM). This was previously disabled due to GPU crashes (Kernel-Power Event 41) caused by VRAM contention when Whisper + Ollama + portal all competed for GPU simultaneously. You move cautiously with verification at every step.

## Direct Aim
Two things:
1. Change Ollama's langextract processing from CPU-only (`"num_gpu": 0`) back to GPU inference
2. Enforce a VRAM budget so that Ollama + Whisper can NEVER exceed safe VRAM limits — preventing the exact contention scenario that caused the original crashes

## Overall Aim
LangExtract is accumulating timeout errors (3 in the last 2 days) because `gemma3:4b` on CPU is too slow for longer transcripts. The full pipeline is bottlenecked at langextract. Restoring GPU inference with VRAM safety caps will bring processing time back to seconds instead of minutes, without risking the crashes that forced CPU-only mode in the first place.

---

## BACKGROUND (DO NOT RE-INVESTIGATE — THIS IS CONFIRMED)

- **GPU:** NVIDIA GeForce RTX 2060 Super, 8192 MB VRAM
- **PSU:** 650W (adequate — not a power issue)
- **Current VRAM at idle:** ~759 MB (9%)
- **Ollama model:** gemma3:4b +2
- **Current config:** `"num_gpu": 0` in langextract_processor.py (forced CPU-only)
- **Why CPU was forced:** Kernel-Power Event 41 crashes — most likely caused by VRAM overallocation triggering an unrecoverable driver fault (Windows logs this as a power event). Happened when Whisper + Ollama + portal all used GPU simultaneously, pushing VRAM to or beyond 8GB.
- **Why it's now safe to restore:** Portal is closed during processing. But we add VRAM caps as belt-and-suspenders protection.
- **Timeout value:** Unknown — you will find this in Step 1.

### VRAM BUDGET (TARGET)

| Component | Max VRAM | Notes |
|-----------|----------|-------|
| System/driver | ~750 MB | Always present |
| Whisper (transcription) | ~1.5-2 GB | Runs first, then releases |
| Ollama (langextract) | ~3 GB | Runs after Whisper |
| **Safety headroom** | **~1.5 GB** | **Must always remain free** |
| **Hard ceiling** | **~6.5 GB** | **Never exceed this** |

Whisper and Ollama should NOT run simultaneously — the pipeline processes sequentially (transcribe → diarize → langextract). But if they ever overlap due to a bug or race condition, the hard cap prevents a crash.

---

## MANDATORY READ-FIRST PHASE

### Step 1: Find the current langextract configuration

```powershell
# Read the langextract processor to find:
# 1. Where "num_gpu": 0 is set
# 2. What the timeout value is
# 3. How Ollama is called (API endpoint, model name, parameters)
# 4. Any num_ctx or context window settings (affects VRAM)
type D:\zone_b\pc_ingest\langextract_processor.py
```

Also check for any config file that might override these:
```powershell
type D:\zone_b\pc_ingest\config.py
Get-ChildItem D:\zone_b\pc_ingest\ -Include *.json,*.yaml,*.yml,*.ini | ForEach-Object { Write-Host "--- $($_.Name) ---"; type $_.FullName }
```

### Step 2: Check the timeout errors in jobs.db

```powershell
sqlite3 D:\zone_b\jobs.db "
SELECT id, job_type, status, error_message, 
       created_at, started_at, completed_at,
       ROUND((julianday(completed_at) - julianday(started_at)) * 86400) as duration_seconds
FROM jobs 
WHERE job_type = 'langextract' 
ORDER BY created_at DESC 
LIMIT 15;
"
```

This tells us:
- How long successful langextract jobs take on CPU
- How long the timeouts ran before being killed
- What the timeout threshold is

### Step 3: Check current Ollama status and GPU allocation

```powershell
# Is Ollama running?
Get-Process ollama* | Format-Table Id, ProcessName, StartTime

# What models are loaded?
curl http://localhost:11434/api/tags 2>$null

# Check Ollama environment variables already set
[System.Environment]::GetEnvironmentVariable("OLLAMA_MAX_VRAM", "User")
[System.Environment]::GetEnvironmentVariable("OLLAMA_MAX_VRAM", "Machine")
$env:OLLAMA_MAX_VRAM

# Current GPU state
nvidia-smi
```

### Step 4: Find ALL GPU-related settings across the codebase

```powershell
# Search for num_gpu in all Zone B Python files
Get-ChildItem -Recurse D:\zone_b\ -Include *.py | Select-String -Pattern "num_gpu" -List

# Search for any VRAM or GPU limit settings
Get-ChildItem -Recurse D:\zone_b\ -Include *.py,*.env,*.json,*.yaml | Select-String -Pattern "OLLAMA_MAX_VRAM|num_ctx|CUDA_VISIBLE|gpu_memory|max_memory" -List

# Check Whisper's GPU config too — how does it allocate?
Get-ChildItem -Recurse D:\zone_b\ -Include *.py | Select-String -Pattern "device.*cuda|torch\.device|whisper.*model|compute_type" -List
```

### Step 5: Check the Ollama model's actual layer count

```powershell
# This tells us exactly how many layers gemma3:4b has
# so we can make an informed num_gpu decision
curl -s http://localhost:11434/api/show -d '{"name":"gemma3:4b"}' | python -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({k:v for k,v in d.get('model_info',{}).items() if 'layer' in k.lower() or 'block' in k.lower() or 'param' in k.lower()}, indent=2))"
```

If that fails, try:
```powershell
ollama show gemma3:4b --modelfile
```

---

## >>> STOP GATE 1 <<<
**Present your findings:**
1. Exact file and line where `"num_gpu": 0` is set
2. The timeout value for langextract jobs
3. Duration of recent successful vs failed langextract jobs
4. Current VRAM usage from nvidia-smi
5. Any existing OLLAMA_MAX_VRAM or VRAM cap settings
6. The model's total layer count
7. Any `num_ctx` (context window) setting — this significantly affects VRAM
8. How Whisper allocates GPU (device setting, model size, compute type)

**Wait for David's confirmation before making changes.**

---

## THE FIX (THREE CHANGES)

### Change 1: Set OLLAMA_MAX_VRAM environment variable (system-wide hard cap)

This is the belt-and-suspenders protection. It caps Ollama's total VRAM usage regardless of what any script requests.

```powershell
# Set as system environment variable (persists across reboots)
# Cap at 4GB — enough for gemma3:4b (~3GB) with margin, 
# but leaves 4GB+ for Whisper/system even in worst case
[System.Environment]::SetEnvironmentVariable("OLLAMA_MAX_VRAM", "4294967296", "Machine")
```

**NOTE:** If `OLLAMA_MAX_VRAM` is not supported by the installed Ollama version, use `OLLAMA_GPU_MEMORY_FRACTION` or document that the per-request `num_gpu` cap is the only available control. Check Ollama docs:
```powershell
ollama --version
```

**After setting, Ollama must be restarted to pick up the new environment variable.**

### Change 2: Re-enable GPU with conservative layer offload

In the file identified in Step 4, change `"num_gpu": 0` to a controlled value.

**Do NOT use `"num_gpu": -1` (full auto).** Auto mode lets Ollama claim as much VRAM as it wants, which is what caused the original crash.

Instead, use a calculated value:
- If model has ~32 layers → set `"num_gpu": 26` (offload ~80%, keeps ~4 layers on CPU as buffer)
- If model has ~24 layers → set `"num_gpu": 20`
- Adjust based on actual layer count from Step 5

This gives ~90% of full GPU speed while ensuring Ollama never tries to load the entire model plus KV cache into VRAM.

### Change 3: Verify or set num_ctx (context window cap)

Context window size directly affects VRAM — a large `num_ctx` with full GPU offload can push VRAM well beyond the model weight size. Check what's currently set:

- If `num_ctx` is not set → Ollama defaults to 2048, which is fine
- If `num_ctx` is set to something large (8192+) → this multiplies VRAM usage. Consider capping at 4096 for langextract tasks (lesson transcripts shouldn't need more)
- If `num_ctx` is reasonable (2048-4096) → leave it alone

**Only change num_ctx if it's set to an unusually large value.**

---

## >>> STOP GATE 2 <<<
**Show the exact changes you plan to make:**
1. OLLAMA_MAX_VRAM value and how it will be set
2. The `num_gpu` line — before and after
3. Any `num_ctx` change (if needed)
4. Calculated VRAM budget: model layers on GPU × per-layer size + KV cache estimate

**Wait for David's confirmation before saving any changes.**

---

## VERIFICATION

### Test 1: Confirm OLLAMA_MAX_VRAM is active

```powershell
# Restart Ollama to pick up environment variable
# (check how Ollama runs — service? manual? Ollama app?)
Get-Process ollama* | Stop-Process -Force
Start-Sleep -Seconds 3
# Restart however it's normally started
ollama serve &
Start-Sleep -Seconds 5

# Verify environment is picked up
nvidia-smi
```

### Test 2: Quick inference test with VRAM monitoring

Open a second terminal for monitoring:
```powershell
# Terminal 2: Watch VRAM continuously
nvidia-smi -l 2
```

In the first terminal:
```powershell
# Send a test prompt
$body = '{"model":"gemma3:4b","prompt":"Summarise this lesson excerpt: The students practiced past tense verbs. Most students confused went and gone. Teacher corrected with examples.","stream":false}'
Measure-Command { curl -s http://localhost:11434/api/generate -d $body }
```

**Record:**
- VRAM before inference: ___ MB
- VRAM peak during inference: ___ MB
- VRAM after inference: ___ MB
- Time to complete: ___ seconds

**FAIL conditions (stop immediately if any occur):**
- Peak VRAM exceeds 5000 MB (Ollama alone)
- Total VRAM exceeds 6500 MB
- System becomes unresponsive
- Any driver error in Event Viewer

### Test 3: Process a real langextract job

```powershell
# Check if there are any errored langextract jobs to requeue
sqlite3 D:\zone_b\jobs.db "SELECT id, status, error_message FROM jobs WHERE job_type='langextract' AND status='error' LIMIT 5;"

# Requeue one for testing:
# sqlite3 D:\zone_b\jobs.db "UPDATE jobs SET status='queued', error_message=NULL WHERE id=<JOB_ID>;"

# Monitor VRAM while it processes (in second terminal)
# Then check result:
sqlite3 D:\zone_b\jobs.db "
SELECT id, status, 
       ROUND((julianday(completed_at) - julianday(started_at)) * 86400) as duration_seconds
FROM jobs 
WHERE job_type = 'langextract' 
ORDER BY completed_at DESC 
LIMIT 5;
"
```

**Expected:** Completes in under 30 seconds on GPU (was timing out on CPU at several minutes).

### Test 4: Simulate worst-case VRAM (Whisper + Ollama awareness)

This doesn't run them simultaneously — it checks that the sequential pipeline leaves VRAM clean between stages:

```powershell
# After a langextract job completes, check VRAM released
nvidia-smi

# VRAM should return close to idle (~750-1000 MB)
# If Ollama holds the model in VRAM (warm cache), that's normal
# but it should be within the OLLAMA_MAX_VRAM cap
```

---

## >>> STOP GATE 3 <<<
**Present verification results:**
1. OLLAMA_MAX_VRAM confirmed active? (Y/N)
2. Test prompt — VRAM peak: ___ MB, time: ___ seconds
3. Real langextract job — duration: ___ seconds, status: ___
4. VRAM after job: ___ MB (did it release?)
5. Any errors or instability?

**Wait for David's confirmation before declaring success.**

---

## ROLLBACK

If GPU crashes return (Kernel-Power Event 41) or any instability:

### Immediate (within seconds):
```powershell
# Kill Ollama to stop GPU usage
Get-Process ollama* | Stop-Process -Force
```

### Revert code change:
1. Change `"num_gpu"` back to `0` in langextract_processor.py
2. Restart the worker: `C:\Python313\python.exe D:\zone_b\control.py worker restart`

### Remove VRAM cap (optional — it's harmless to leave):
```powershell
[System.Environment]::SetEnvironmentVariable("OLLAMA_MAX_VRAM", $null, "Machine")
```

---

## WHAT NOT TO DO

- Do NOT use `"num_gpu": -1` (full auto) — this is what caused the original crash
- Do NOT set num_gpu higher than 80% of total layers — leave a CPU buffer
- Do NOT change the Ollama model (stay on gemma3:4b)
- Do NOT change the timeout value (GPU speed should resolve this)
- Do NOT modify Whisper configuration
- Do NOT upgrade Ollama or PyTorch
- Do NOT modify control.py, db_worker.py, or processor.py
- Do NOT run langextract while the Tkinter portal is open

---

## POST-FIX: UPDATE PROGRAM_MAP.md

Add to the GPU/VRAM section (or create one):

```markdown
### GPU VRAM Budget

| Component | Max VRAM | Control |
|-----------|----------|---------|
| System/driver | ~750 MB | N/A |
| Whisper | ~1.5-2 GB | model size + compute_type |
| Ollama (gemma3:4b) | ~3 GB | num_gpu=[value], OLLAMA_MAX_VRAM=4GB |
| Safety headroom | ~1.5 GB | MUST remain free |
| **Hard ceiling** | **6.5 GB** | **Enforced by OLLAMA_MAX_VRAM** |

CRITICAL: Never set num_gpu to -1 (auto). Always use explicit layer count.
CRITICAL: Never run GPU inference with portal open during batch processing.
History: Kernel-Power Event 41 crashes occurred when VRAM contention hit ~8GB.
Resolved by: CPU-only mode (2026-02), then controlled GPU restore (2026-03).
```
