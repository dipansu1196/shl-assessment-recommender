"""
Build FAISS index for SHL product catalog.

This script:
1. Loads data/catalog.json
2. Embeds each record using sentence-transformers (all-MiniLM-L6-v2)
3. Builds a FAISS flat index (IndexFlatIP with normalized embeddings for cosine similarity)
4. Saves to data/catalog.faiss
5. Saves aligned metadata to data/catalog_meta.pkl
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


def load_catalog(catalog_path: str) -> List[Dict[str, Any]]:
    """Load catalog JSON file."""
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    return catalog


def create_embedding_text(record: Dict[str, Any]) -> str:
    """
    Create text for embedding by concatenating name + description + keys.
    
    Args:
        record: Catalog record
        
    Returns:
        String suitable for embedding
    """
    name = record.get('name', '')
    description = record.get('description', '')
    keys = record.get('keys', [])
    
    # Join keys with spaces
    keys_text = ' '.join(keys) if isinstance(keys, list) else str(keys)
    
    # Concatenate with spaces
    text = f"{name} {description} {keys_text}"
    return text.strip()


def map_keys_to_test_type(keys: List[str]) -> str:
    """
    Map keys to test type letter codes.
    
    Args:
        keys: List of key strings
        
    Returns:
        Comma-separated letter codes (e.g., "K", "P", "K,S")
    """
    key_mapping = {
        "Knowledge & Skills": "K",
        "Personality & Behavior": "P",
        "Ability & Aptitude": "A",
        "Simulations": "S",
        "Biodata & Situational Judgment": "B",
        "Competencies": "C",
        "Development & 360": "D",
        "Assessment Exercises": "E"
    }
    
    if not keys:
        return ""
    
    codes = []
    for key in keys:
        if key in key_mapping:
            codes.append(key_mapping[key])
    
    return ",".join(codes)


def build_index(catalog: List[Dict[str, Any]], model: SentenceTransformer) -> tuple:
    """
    Build FAISS index and metadata.
    
    Args:
        catalog: List of catalog records
        model: SentenceTransformer model
        
    Returns:
        Tuple of (faiss_index, metadata_list)
    """
    # Prepare texts for embedding
    texts = []
    metadata = []
    
    for record in catalog:
        # Create embedding text
        text = create_embedding_text(record)
        texts.append(text)
        
        # Create metadata entry
        meta = {
            'entity_id': record.get('entity_id', ''),
            'name': record.get('name', ''),
            'url': record.get('link', ''),  # Note: 'link' in JSON, 'url' in metadata
            'test_type': map_keys_to_test_type(record.get('keys', [])),
            'keys': record.get('keys', []),
            'description': record.get('description', ''),
            'duration': record.get('duration', ''),
            'job_levels': record.get('job_levels', []),
            'languages': record.get('languages', [])
        }
        metadata.append(meta)
    
    print(f"Embedding {len(texts)} records...")
    
    # Generate embeddings
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings).astype('float32')
    
    # Build FAISS index (IndexFlatIP for cosine similarity with normalized embeddings)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    
    # Add embeddings to index
    index.add(embeddings)
    
    print(f"Built FAISS index with {index.ntotal} vectors of dimension {dimension}")
    
    return index, metadata


def main():
    """Main execution function."""
    # Set up paths
    base_dir = Path(__file__).parent
    catalog_path = base_dir / 'catalog.json'
    faiss_path = base_dir / 'catalog.faiss'
    metadata_path = base_dir / 'catalog_meta.pkl'
    
    # Check if catalog exists
    if not catalog_path.exists():
        print(f"Error: {catalog_path} not found!")
        print("Please download the catalog from:")
        print("https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json")
        return
    
    # Load catalog
    print(f"Loading catalog from {catalog_path}...")
    catalog = load_catalog(str(catalog_path))
    print(f"Loaded {len(catalog)} records")
    
    # Load embedding model
    print("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Build index
    index, metadata = build_index(catalog, model)
    
    # Save FAISS index
    print(f"Saving FAISS index to {faiss_path}...")
    faiss.write_index(index, str(faiss_path))
    
    # Save metadata
    print(f"Saving metadata to {metadata_path}...")
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    
    print("\n✓ Index build complete!")
    print(f"  - FAISS index: {faiss_path}")
    print(f"  - Metadata: {metadata_path}")
    
    # Smoke test
    print("\n" + "="*60)
    print("SMOKE TEST: Query 'Java developer with stakeholder management'")
    print("="*60)
    
    query = "Java developer with stakeholder management"
    query_embedding = model.encode([query], normalize_embeddings=True)
    query_embedding = np.array(query_embedding).astype('float32')
    
    # Search top 5
    k = 5
    scores, indices = index.search(query_embedding, k)
    
    print(f"\nTop {k} matches:")
    print("-" * 60)
    for rank, (idx, score) in enumerate(zip(indices[0], scores[0]), 1):
        meta = metadata[idx]
        print(f"\n{rank}. {meta['name']}")
        print(f"   Score: {score:.4f}")
        print(f"   Type: {meta['test_type']}")
        print(f"   Description: {meta['description'][:100]}...")
    
    print("\n" + "="*60)
    print("Smoke test complete. Check relevance above.")


if __name__ == '__main__':
    main()
