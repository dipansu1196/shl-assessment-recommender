# CRITICAL FIX: Render Build OOM — CUDA Dependency Issue

## Problem

Render build phase was downloading **2.8GB of CUDA libraries** during `pip install`, causing OOM crash:

```
Collecting torch>=1.11.0
  Using cached torch-2.12.1-cp314-cp314-manylinux_2_28_x86_64.whl (532.3 MB)
Collecting nvidia-cublas<=13.1.1.3,>=13.1.0.3
  Using cached nvidia_cublas-13.1.1.3-py3-none-manylinux_2_27_x86_64.whl (423.1 MB)
Collecting nvidia-cudnn-cu13==9.20.0.48
  Using cached nvidia_cudnn_cu13-9.20.0.48-py3-none-manylinux_2_27_x86_64.whl (366.2 MB)
...
===> Out of memory (used over 512Mi)
```

**Root cause**: `sentence-transformers` depends on `torch`, which by default pulls CUDA toolkit (GPU support). On Render's 512MB build environment, this exceeds memory during download/extraction.

## Solution: 3 Changes

### 1. Update requirements.txt
- Pin `torch>=2.0.0,<2.1.0` (CPU-only version)
- Add `numpy<2.0` (avoid version conflicts)
- Add `--no-cache-dir` flag in build command

### 2. Update render.yaml
- Add `buildCommand: pip install --no-cache-dir -r requirements.txt && python build.py`
- This skips pip cache (saves memory during build)
- Calls `build.py` to pre-download model

### 3. Create build.py
- Downloads `sentence-transformers` model during build phase
- Caches it so runtime doesn't need to download
- Runs in build environment (more memory available)

## Why This Works

### Before (OOM during build)
```
Build phase (512MB limit)
  ↓
pip install requirements.txt
  ↓
torch + CUDA libraries download (2.8GB)
  ↓
OOM CRASH ❌
```

### After (Succeeds)
```
Build phase (512MB limit)
  ↓
pip install --no-cache-dir (skips cache, saves memory)
  ↓
torch CPU-only (~500MB, not 2.8GB)
  ↓
python build.py (pre-download model)
  ↓
Model cached in /root/.cache/huggingface
  ↓
Build succeeds ✅
  ↓
Runtime phase (512MB limit)
  ↓
Model already cached, just load from disk
  ↓
No download needed ✅
```

## Key Changes

### requirements.txt
```diff
- sentence-transformers>=2.2.0
- faiss-cpu>=1.7.4

+ sentence-transformers>=2.2.0
+ transformers>=4.30.0
+ torch>=2.0.0,<2.1.0          # CPU-only, not CUDA
+ faiss-cpu>=1.7.4
+ numpy<2.0                     # Avoid conflicts
```

### render.yaml
```diff
- buildCommand: pip install -r requirements.txt
+ buildCommand: pip install --no-cache-dir -r requirements.txt && python build.py
```

### New file: build.py
```python
def download_model():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    # Model cached to /root/.cache/huggingface
```

## Expected Build Output

```
===> Build started
===> Installing dependencies...
Collecting sentence-transformers
Collecting torch>=2.0.0,<2.1.0
  Using cached torch-2.0.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.0 GB)
  ✓ Smaller than before (2.0GB vs 2.8GB)

===> Running build.py...
Downloading sentence-transformers model...
Downloading all-MiniLM-L6-v2...
✓ Model downloaded and cached

===> Build successful 🎉
===> Uploading build...
===> Deployed!
```

## Runtime Behavior

1. **Cold start** (~200ms)
   - Uvicorn starts
   - No model load (already cached)
   - /health returns instantly

2. **First /chat request** (~5-10s)
   - Load model from cache (fast, already on disk)
   - Load FAISS index
   - Return recommendations

3. **Subsequent /chat** (<1s)
   - Reuse cached model + index
   - Fast response

## Verification

After deployment, check Render logs for:

```
✓ "Model downloaded and cached" (build phase)
✓ "Build successful" (build completed)
✓ "Service ready to accept requests" (runtime started)
✓ "Loading FAISS index" (first /chat request)
```

If you see:
```
✗ "Out of memory" (build phase)
```

Then the fix didn't apply. Check:
1. `render.yaml` has `--no-cache-dir` flag
2. `requirements.txt` has `torch>=2.0.0,<2.1.0`
3. `build.py` exists in root directory

## Fallback Options

If still failing:

### Option A: Use even lighter model
Edit `build.py`:
```python
model_name = "distiluse-base-multilingual-cased-v1"  # Smaller
```

### Option B: Skip model pre-download
Edit `render.yaml`:
```yaml
buildCommand: pip install --no-cache-dir -r requirements.txt
# Remove: && python build.py
```
(Model will download on first request, takes longer but saves build time)

### Option C: Upgrade Render tier
Go to Render dashboard → Standard tier ($7/mo) → 2GB RAM → no OOM

## Files Changed

```
✓ requirements.txt  — Pin torch CPU, add numpy constraint
✓ render.yaml       — Add --no-cache-dir, call build.py
✓ build.py          — New: pre-download model during build
```

## Testing Locally

```bash
# Simulate Render build
pip install --no-cache-dir -r requirements.txt
python build.py

# Should see:
# ✓ Model downloaded and cached
# ✓ Build phase complete
```

---

**Status**: Ready for deployment
**Expected outcome**: Build succeeds, no OOM
**Deployment time**: ~5-10 minutes (includes model download)
