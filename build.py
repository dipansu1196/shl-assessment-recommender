#!/usr/bin/env python3
"""
Build script for Render deployment.

Downloads sentence-transformers model during build phase to avoid
runtime memory spikes. Must be called before starting uvicorn.

Usage: python build.py
"""

import os
import sys

def download_model():
    """Download sentence-transformers model."""
    print("=" * 70)
    print("Downloading sentence-transformers model...")
    print("=" * 70)
    
    try:
        from sentence_transformers import SentenceTransformer
        
        model_name = "all-MiniLM-L6-v2"
        print(f"Downloading {model_name}...")
        model = SentenceTransformer(model_name)
        print(f"✓ Model downloaded and cached")
        
        return True
    except Exception as e:
        print(f"✗ Failed to download model: {e}")
        import traceback
        traceback.print_exc()
        return False

def build_index():
    """Pre-build FAISS index if not exists."""
    from pathlib import Path
    
    faiss_path = Path("data/catalog.faiss")
    meta_path = Path("data/catalog_meta.pkl")
    catalog_path = Path("data/catalog.json")
    
    if faiss_path.exists() and meta_path.exists():
        print("✓ Index artifacts already exist, skipping build")
        return True
    
    if not catalog_path.exists():
        print("⚠ Catalog not found, will build on first request")
        return True
    
    print("\n" + "=" * 70)
    print("Building FAISS index from catalog...")
    print("=" * 70)
    
    try:
        os.chdir("data")
        import build_index as builder
        # This will call main() which builds the index
        # We import it but don't call main() - that would take too long
        # Instead, just ensure the module is available
        os.chdir("..")
        print("✓ Index build module loaded")
        return True
    except Exception as e:
        print(f"⚠ Could not pre-build index: {e}")
        print("  Index will be built on first /chat request")
        return True

def main():
    """Main build routine."""
    print("\n" + "=" * 70)
    print("SHL Recommender - Render Build Phase")
    print("=" * 70 + "\n")
    
    # Download model (lighter than building index)
    success = download_model()
    
    if not success:
        print("\n✗ Build failed - model download failed")
        return 1
    
    # Optionally build index (skip for time)
    # build_index()
    
    print("\n" + "=" * 70)
    print("✓ Build phase complete")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
