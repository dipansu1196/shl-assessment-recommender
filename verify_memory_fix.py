#!/usr/bin/env python3
"""
Memory validation script for SHL Recommender.

Verifies that lazy loading and single-worker mode keep memory under control.
Run this before deploying to Render to confirm the fix works.

Usage:
    python verify_memory_fix.py
"""

import subprocess
import time
import os
import sys
import signal
import psutil
import json
from pathlib import Path

# Configuration
STARTUP_TIMEOUT = 10  # seconds to wait for uvicorn to start
MEMORY_THRESHOLD = 700  # MB - warn if exceeding this
PORT = 8888

def get_process_memory(pid: int) -> float:
    """Get process memory usage in MB."""
    try:
        proc = psutil.Process(pid)
        return proc.memory_info().rss / (1024 * 1024)  # Convert to MB
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0

def test_health_endpoint(port: int) -> bool:
    """Test /health endpoint response time."""
    import requests
    start = time.time()
    try:
        resp = requests.get(f"http://localhost:{port}/health", timeout=5)
        elapsed = (time.time() - start) * 1000  # ms
        print(f"✓ /health: {resp.status_code} ({elapsed:.0f}ms)")
        return resp.status_code == 200
    except Exception as e:
        print(f"✗ /health: Failed - {e}")
        return False

def test_warmup_endpoint(port: int) -> bool:
    """Test /warmup endpoint (triggers index load)."""
    import requests
    start = time.time()
    try:
        resp = requests.get(f"http://localhost:{port}/warmup", timeout=30)
        elapsed = (time.time() - start) * 1000  # ms
        print(f"✓ /warmup: {resp.status_code} ({elapsed:.0f}ms)")
        return resp.status_code == 200
    except Exception as e:
        print(f"✗ /warmup: Failed - {e}")
        return False

def test_chat_endpoint(port: int) -> bool:
    """Test /chat endpoint (full flow)."""
    import requests
    start = time.time()
    try:
        payload = {
            "messages": [
                {"role": "user", "content": "Senior Java developer"}
            ]
        }
        resp = requests.post(
            f"http://localhost:{port}/chat",
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        elapsed = (time.time() - start) * 1000  # ms
        if resp.status_code == 200:
            data = resp.json()
            recs = len(data.get("recommendations", []))
            print(f"✓ /chat: {resp.status_code} ({elapsed:.0f}ms, {recs} recommendations)")
            return True
        else:
            print(f"✗ /chat: {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ /chat: Failed - {e}")
        return False

def main():
    """Main validation flow."""
    print("=" * 70)
    print("SHL Recommender Memory Fix Validation")
    print("=" * 70)
    
    # Check dependencies
    print("\n[1] Checking dependencies...")
    try:
        import requests
        import psutil
        print("✓ Required packages installed")
    except ImportError as e:
        print(f"✗ Missing package: {e}")
        print("  Run: pip install requests psutil")
        return False
    
    # Check .env file
    print("\n[2] Checking environment...")
    if not Path(".env").exists():
        print("✗ .env file not found")
        print("  Copy .env.example to .env and fill in GROQ_API_KEY")
        return False
    print("✓ .env file exists")
    
    # Check data files
    print("\n[3] Checking data files...")
    if not Path("data/catalog.faiss").exists():
        print("✗ data/catalog.faiss not found")
        print("  Run: cd data && python build_index.py")
        return False
    if not Path("data/catalog_meta.pkl").exists():
        print("✗ data/catalog_meta.pkl not found")
        print("  Run: cd data && python build_index.py")
        return False
    print("✓ Index files exist")
    
    # Start server
    print(f"\n[4] Starting server on port {PORT} (memory-optimized mode)...")
    cmd = [
        "python", "-m", "uvicorn",
        "app.main:app",
        "--host", "localhost",
        f"--port", str(PORT),
        "--workers", "1",
        "--loop", "uvloop",
        "--http", "httptools",
    ]
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except Exception as e:
        print(f"✗ Failed to start server: {e}")
        return False
    
    # Wait for startup
    print("  Waiting for startup...")
    startup_time = time.time()
    while time.time() - startup_time < STARTUP_TIMEOUT:
        try:
            import requests
            requests.get(f"http://localhost:{PORT}/health", timeout=1)
            break
        except:
            time.sleep(0.1)
    
    if time.time() - startup_time >= STARTUP_TIMEOUT:
        print(f"✗ Server failed to start within {STARTUP_TIMEOUT}s")
        proc.terminate()
        return False
    
    startup_elapsed = time.time() - startup_time
    print(f"✓ Server started in {startup_elapsed*1000:.0f}ms")
    
    # Measure memory at startup
    mem_startup = get_process_memory(proc.pid)
    print(f"  Memory at startup: {mem_startup:.0f}MB")
    
    if mem_startup > MEMORY_THRESHOLD:
        print(f"  ⚠ WARNING: Startup memory {mem_startup:.0f}MB > threshold {MEMORY_THRESHOLD}MB")
    
    try:
        # Test endpoints
        print("\n[5] Testing endpoints...")
        
        # Health check (should be instant, no index load)
        print("  Testing /health (no index load)...")
        if not test_health_endpoint(PORT):
            raise RuntimeError("/health test failed")
        
        mem_after_health = get_process_memory(proc.pid)
        print(f"  Memory after /health: {mem_after_health:.0f}MB (Δ {mem_after_health - mem_startup:+.0f}MB)")
        
        # Warmup (triggers index load)
        print("\n  Testing /warmup (triggers index load)...")
        if not test_warmup_endpoint(PORT):
            raise RuntimeError("/warmup test failed")
        
        mem_after_warmup = get_process_memory(proc.pid)
        print(f"  Memory after /warmup: {mem_after_warmup:.0f}MB (Δ {mem_after_warmup - mem_startup:+.0f}MB)")
        
        if mem_after_warmup > MEMORY_THRESHOLD:
            print(f"  ⚠ WARNING: Memory {mem_after_warmup:.0f}MB > threshold {MEMORY_THRESHOLD}MB")
            print(f"    Consider: --workers 1 --loop uvloop in render.yaml")
        
        # Chat endpoint
        print("\n  Testing /chat endpoint...")
        if not test_chat_endpoint(PORT):
            raise RuntimeError("/chat test failed")
        
        mem_after_chat = get_process_memory(proc.pid)
        print(f"  Memory after /chat: {mem_after_chat:.0f}MB (Δ {mem_after_chat - mem_startup:+.0f}MB)")
        
        # Results
        print("\n" + "=" * 70)
        print("MEMORY PROFILE SUMMARY")
        print("=" * 70)
        print(f"Startup memory:      {mem_startup:6.0f}MB")
        print(f"After /health:       {mem_after_health:6.0f}MB (Δ {mem_after_health - mem_startup:+.0f}MB)")
        print(f"After /warmup:       {mem_after_warmup:6.0f}MB (Δ {mem_after_warmup - mem_startup:+.0f}MB)")
        print(f"After /chat:         {mem_after_chat:6.0f}MB (Δ {mem_after_chat - mem_startup:+.0f}MB)")
        print(f"Peak memory:         {max(mem_startup, mem_after_health, mem_after_warmup, mem_after_chat):.0f}MB")
        print("=" * 70)
        
        # Assessment
        peak = max(mem_startup, mem_after_health, mem_after_warmup, mem_after_chat)
        if peak > 700:
            print("\n⚠  MEMORY USAGE HIGH (>700MB)")
            print("   Recommendation: Use distiluse model or upgrade Render tier")
            success = False
        elif peak > 512:
            print("\n⚠  MEMORY USAGE MARGINAL (>512MB)")
            print("   May fail on Render 512MB tier")
            print("   Recommendation: Test with distiluse model")
            success = True
        else:
            print("\n✓ MEMORY USAGE OK (<512MB)")
            print("  Ready for Render deployment")
            success = True
        
        return success
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False
    
    finally:
        # Cleanup
        print("\n[6] Cleaning up...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("✓ Server stopped")

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
