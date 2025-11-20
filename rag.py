"""
RAG (Retrieval-Augmented Generation) module using FAISS for semantic search
on ecommerce FAQ data.

Features:
- Persistent embeddings (saves to disk, loads on restart)
- FAISS vector search with L2 distance
- Sentence Transformers for embedding generation
"""

import json
import os
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import pickle

# Global variables for the index and data
_index = None
_questions_data = None
_model = None
_is_initialized = False

# Cache directory for persisted embeddings
CACHE_DIR = Path(__file__).parent / "embeddings_cache"
INDEX_FILE = CACHE_DIR / "faiss_index.bin"
METADATA_FILE = CACHE_DIR / "metadata.pkl"


def _save_index_to_disk():
    """Save FAISS index and metadata to disk for persistence."""
    CACHE_DIR.mkdir(exist_ok=True)
    
    # Save FAISS index
    faiss.write_index(_index, str(INDEX_FILE))
    
    # Save metadata (questions data)
    with open(METADATA_FILE, 'wb') as f:
        pickle.dump(_questions_data, f)
    
    print(f"✓ Embeddings saved to {CACHE_DIR}")


def _load_index_from_disk():
    """Load FAISS index and metadata from disk if available."""
    global _index, _questions_data
    
    if not INDEX_FILE.exists() or not METADATA_FILE.exists():
        return False
    
    try:
        # Load FAISS index
        _index = faiss.read_index(str(INDEX_FILE))
        
        # Load metadata
        with open(METADATA_FILE, 'rb') as f:
            _questions_data = pickle.load(f)
        
        print(f"✓ Loaded persisted embeddings from cache ({len(_questions_data)} entries)")
        return True
    except Exception as e:
        print(f"⚠ Failed to load cached embeddings: {e}")
        return False


def _initialize():
    """Initialize the FAISS index and load the ecommerce data."""
    global _index, _questions_data, _model, _is_initialized
    
    if _is_initialized:
        return
    
    print("Initializing RAG system...")
    
    # Load the sentence transformer model for embeddings
    _model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Try to load from cache first
    if _load_index_from_disk():
        _is_initialized = True
        return
    
    # If cache doesn't exist, create embeddings from scratch
    print("No cache found. Creating embeddings from scratch...")
    
    # Load the ecommerce JSON data
    data_path = Path(__file__).parent / "data" / "ecommerce.json"
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    _questions_data = data['questions']
    
    # Create embeddings for all questions
    questions = [item['question'] for item in _questions_data]
    print(f"Embedding {len(questions)} questions...")
    embeddings = _model.encode(questions, convert_to_numpy=True, show_progress_bar=True)
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    _index = faiss.IndexFlatL2(dimension)  # L2 distance (Euclidean)
    _index.add(embeddings.astype('float32'))
    
    # Save to disk for next time
    _save_index_to_disk()
    
    _is_initialized = True
    print(f"✓ RAG system initialized with {len(_questions_data)} FAQ entries")


def search(query: str, top_k: int = 3) -> str:
    """
    Search for relevant FAQ answers based on the query.
    
    Args:
        query: The user's question
        top_k: Number of top results to return (default: 3)
    
    Returns:
        A formatted string with the most relevant FAQ answers
    """
    # Initialize if not already done
    if not _is_initialized:
        _initialize()
    
    # Encode the query
    query_embedding = _model.encode([query], convert_to_numpy=True)
    
    # Search the index
    distances, indices = _index.search(query_embedding.astype('float32'), top_k)
    
    # Format the results
    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(_questions_data):
            item = _questions_data[idx]
            results.append(f"Q: {item['question']}\nA: {item['answer']}")
    
    if results:
        return "\n\n---\n\n".join(results)
    else:
        return "No relevant information found in the FAQ database."


def get_stats() -> dict:
    """Get statistics about the RAG system."""
    if not _is_initialized:
        _initialize()
    
    return {
        "total_faqs": len(_questions_data),
        "model": "all-MiniLM-L6-v2",
        "index_type": "FAISS IndexFlatL2",
        "cache_dir": str(CACHE_DIR),
        "cached": INDEX_FILE.exists(),
    }


def clear_cache():
    """Clear the persisted embeddings cache. Next search will rebuild from scratch."""
    import shutil
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print("✓ Cache cleared. Next search will rebuild embeddings.")
    else:
        print("No cache to clear.")


def rebuild_cache():
    """Force rebuild of embeddings cache from the source JSON file."""
    global _is_initialized
    clear_cache()
    _is_initialized = False
    _initialize()
    print("✓ Cache rebuilt successfully.")


if __name__ == "__main__":
    # Test the RAG system
    print("Testing RAG system...")
    print("\n" + "="*50)
    
    # Test query 1
    result = search("How do I track my order?")
    print("Query: How do I track my order?")
    print(f"\nResults:\n{result}")
    print("\n" + "="*50)
    
    # Test query 2
    result = search("What is your return policy?")
    print("\nQuery: What is your return policy?")
    print(f"\nResults:\n{result}")
    print("\n" + "="*50)
    
    # Print stats
    stats = get_stats()
    print(f"\nRAG Stats: {stats}")
