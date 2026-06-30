"""
Retrieval module for SHL Assessment Recommender.

This module lazily loads retrieval resources and can auto-build FAISS artifacts
from catalog.json when they are missing. It will auto-download the catalog if needed.
"""

import json
import pickle
import urllib.request
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# Module-level paths
_BASE_DIR = Path(__file__).parent.parent / "data"
_FAISS_PATH = _BASE_DIR / "catalog.faiss"
_METADATA_PATH = _BASE_DIR / "catalog_meta.pkl"
_CATALOG_PATH = _BASE_DIR / "catalog.json"

# Lazily initialized resources
_index = None
_metadata = None
_model = None
_index_loaded = False  # Track if we've attempted to load index


def _map_keys_to_test_type(keys: List[str]) -> str:
    """Map catalog keys to one-letter test type codes."""
    key_mapping = {
        "Knowledge & Skills": "K",
        "Personality & Behavior": "P",
        "Ability & Aptitude": "A",
        "Simulations": "S",
        "Biodata & Situational Judgment": "B",
        "Competencies": "C",
        "Development & 360": "D",
        "Assessment Exercises": "E",
    }
    if not keys:
        return ""
    return ",".join(code for key in keys if (code := key_mapping.get(key)))


def _download_catalog() -> None:
    """Download catalog from SHL if not present."""
    try:
        url = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json"
        print(f"Downloading catalog from SHL (2.7GB)...")
        _BASE_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, str(_CATALOG_PATH))
        print(f"Catalog downloaded successfully to {_CATALOG_PATH}")
    except Exception as e:
        print(f"Failed to download catalog: {e}")
        raise


def _create_embedding_text(record: Dict[str, Any]) -> str:
    """Create embedding text from a catalog record."""
    name = record.get("name", "")
    description = record.get("description", "")
    keys = record.get("keys", [])
    keys_text = " ".join(keys) if isinstance(keys, list) else str(keys)
    return f"{name} {description} {keys_text}".strip()


def _ensure_model_loaded() -> None:
    """Load embedding model on first use."""
    global _model
    if _model is None:
        print("Loading sentence-transformers model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")


def _build_index_from_catalog() -> None:
    """Build FAISS index/metadata artifacts from catalog.json and persist them."""
    if not _CATALOG_PATH.exists():
        print("Catalog not found, downloading from SHL...")
        _download_catalog()

    if not _CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Failed to download catalog. Please download manually from: "
            f"https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json "
            f"and save to {_CATALOG_PATH}"
        )

    print(f"Building retrieval artifacts from {_CATALOG_PATH}...")
    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    texts: List[str] = []
    metadata: List[Dict[str, Any]] = []
    for record in catalog:
        texts.append(_create_embedding_text(record))
        metadata.append(
            {
                "entity_id": record.get("entity_id", ""),
                "name": record.get("name", ""),
                "url": record.get("link", ""),
                "test_type": _map_keys_to_test_type(record.get("keys", [])),
                "keys": record.get("keys", []),
                "description": record.get("description", ""),
                "duration": record.get("duration", ""),
                "job_levels": record.get("job_levels", []),
                "languages": record.get("languages", []),
            }
        )

    _ensure_model_loaded()
    embeddings = _model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    embeddings = np.array(embeddings).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(_FAISS_PATH))
    with open(_METADATA_PATH, "wb") as f:
        pickle.dump(metadata, f)
    print("Retrieval artifacts built successfully")


def _ensure_index_and_metadata_loaded() -> None:
    """Load FAISS index + metadata; build artifacts from catalog if needed."""
    global _index, _metadata, _index_loaded
    if _index is not None and _metadata is not None:
        return

    # Prevent repeated load attempts if index doesn't exist
    if _index_loaded:
        return

    if not _FAISS_PATH.exists() or not _METADATA_PATH.exists():
        print("Index artifacts missing, building from catalog...")
        _build_index_from_catalog()

    # Only load if artifacts now exist
    if _FAISS_PATH.exists() and _METADATA_PATH.exists():
        print("Loading FAISS index and metadata...")
        try:
            _index = faiss.read_index(str(_FAISS_PATH))
            with open(_METADATA_PATH, "rb") as f:
                _metadata = pickle.load(f)
            print(f"Loaded index with {_index.ntotal} vectors and {len(_metadata)} metadata records")
        except Exception as e:
            print(f"Error loading index artifacts: {e}")
            _index = None
            _metadata = None

    _index_loaded = True


def search(query: str, k: int = 15) -> List[Dict[str, Any]]:
    """
    Search the catalog using semantic similarity.

    Args:
        query: Free-text search query
        k: Number of top results to return (default: 15)

    Returns:
        List of metadata dictionaries with added 'score' field,
        ordered by relevance (highest score first)
    """
    _ensure_index_and_metadata_loaded()
    _ensure_model_loaded()

    # Embed the query using the same model
    query_embedding = _model.encode([query], normalize_embeddings=True)
    query_embedding = np.array(query_embedding).astype("float32")

    # Search FAISS index
    effective_k = min(k, len(_metadata))
    scores, indices = _index.search(query_embedding, effective_k)

    # Build results with metadata and scores
    results = []
    for idx, score in zip(indices[0], scores[0]):
        # Copy metadata to avoid modifying the cached version
        result = _metadata[idx].copy()
        result["score"] = float(score)  # Add similarity score
        results.append(result)

    return results


def get_by_name(name: str) -> Dict[str, Any]:
    """
    Find a catalog item by exact name match.

    Args:
        name: Exact assessment name

    Returns:
        Metadata dictionary or None if not found
    """
    _ensure_index_and_metadata_loaded()

    for meta in _metadata:
        if meta["name"] == name:
            return meta.copy()
    return None


def get_metadata_count() -> int:
    """
    Get total number of items in the catalog.

    Returns:
        Number of catalog items
    """
    _ensure_index_and_metadata_loaded()
    return len(_metadata)
