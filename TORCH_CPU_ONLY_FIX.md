# 🔴 CRITICAL FIX: CPU-Only PyTorch Installation

## Problem

Build succeeded BUT runtime crashed with OOM because:
- `torch>=2.12.0` still pulled CUDA libraries (~1.5GB of nvidia packages)
- `sentence-transformers` dependency on torch forced CUDA version
- Runtime memory: ~850MB CUDA libs + model + index = crash at 512MB

## Root Cause

PyPI's default torch package includes CUDA support. Even specifying `torch>=2.12.0` pulls:
- nvidia-cuda-runtime
- nvidia-cublas
- nvidia-cudnn
- nvidia-nccl
- ... and 20+ other CUDA packages (~1.5GB total)

## Solution

Install CPU-only torch **explicitly** from PyTorch's official index:

```bash
pip install torch==2.12.1 --index-url https://download.pytorch.org/whl/cpu
```

Then install remaining deps from PyPI without torch:

```bash
pip install -r requirements.txt
```

## Changes Made

### requirements.txt
- REMOVED: `torch>=2.12.0`
- NOW: Only includes `sentence-transformers` and other non-torch deps
- Torch will be installed separately via render.yaml

### render.yaml buildCommand
```bash
# OLD:
pip install --no-cache-dir -r requirements.txt && python build.py

# NEW:
pip install --no-cache-dir torch==2.12.1 --index-url https://download.pytorch.org/whl/cpu && \
pip install --no-cache-dir -r requirements.txt && \
python build.py
```

## Expected Build Output

```
Installing torch from https://download.pytorch.org/whl/cpu
Downloading torch-2.12.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (~100MB)
✓ No nvidia packages installed
✓ No CUDA libraries
✓ Memory stays low during build
```

## Memory Comparison

| Component | CUDA Version | CPU-Only |
|-----------|--------------|----------|
| torch | 500MB | 100MB |
| nvidia libraries | 1500MB | 0MB |
| sentence-transformers | 100MB | 100MB |
| Other deps | 100MB | 100MB |
| **Total** | **2.2GB** | **300MB** ✅ |

## Why This Works

PyTorch's official index (`https://download.pytorch.org/whl/cpu`) provides:
- CPU-only compiled binaries
- No CUDA dependencies
- ~100MB instead of 500MB+
- Exact version control (2.12.1)
- Official, maintained repository

## Status

✅ Build command updated  
✅ Requirements cleaned  
✅ CPU-only torch indexed  
✅ Ready for next deploy  

Next Render deploy should:
1. Clone repo (~100MB)
2. Install CPU-only torch (~100MB)
3. Install other deps (~300MB)
4. Download model during build
5. Start service successfully ✅
