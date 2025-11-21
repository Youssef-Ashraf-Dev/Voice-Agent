"""
RAG (Retrieval-Augmented Generation) module using FAISS for semantic search
on ecommerce FAQ data.

Features:
- Persistent embeddings (saves to disk, loads on restart)
- FAISS vector search with L2 distance
- Sentence Transformers for embedding generation
"""

import json
import pickle
import re
from difflib import SequenceMatcher
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

# Global variables for the index and data
_index = None
_questions_data = None
_model = None
_is_initialized = False

CACHE_VERSION = 2

_WORD_RE = re.compile(r"\b\w+\b")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "for",
    "how",
    "i",
    "if",
    "in",
    "is",
    "my",
    "of",
    "on",
    "the",
    "to",
    "what",
    "your",
}
_EXACT_MATCH_RATIO = 0.78
_MIN_OVERLAP_SCORE = 0.35
_SEMANTIC_WEIGHT = 0.6
_LEXICAL_WEIGHT = 0.25
_OVERLAP_WEIGHT = 0.15

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
    metadata = {
        "version": CACHE_VERSION,
        "questions": _questions_data,
    }
    with open(METADATA_FILE, 'wb') as f:
        pickle.dump(metadata, f)
    
    print(f"[INFO] Embeddings saved to {CACHE_DIR}")


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
            metadata = pickle.load(f)

        if isinstance(metadata, dict):
            if metadata.get("version") != CACHE_VERSION:
                print("[WARN] Cache version mismatch. Rebuilding required.")
                return False
            _questions_data = metadata.get("questions", [])
        else:
            print("[WARN] Legacy cache format detected. Rebuilding required.")
            return False
        
        print(f"[INFO] Loaded persisted embeddings from cache ({len(_questions_data)} entries)")
        return True
    except Exception as e:
        print(f"[WARN] Failed to load cached embeddings: {e}")
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
    documents = [f"{item['question']} {item['answer']}" for item in _questions_data]
    print(f"Embedding {len(documents)} FAQ entries...")
    embeddings = _model.encode(documents, convert_to_numpy=True, show_progress_bar=True)
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    _index = faiss.IndexFlatL2(dimension)  # L2 distance (Euclidean)
    _index.add(embeddings.astype('float32'))
    
    # Save to disk for next time
    _save_index_to_disk()
    
    _is_initialized = True
    print(f"[INFO] RAG system initialized with {len(_questions_data)} FAQ entries")


def _tokenize(text: str):
    if not text:
        return []
    return [token for token in _WORD_RE.findall(text.lower()) if token not in _STOPWORDS]


def _overlap_score(query_tokens, candidate_tokens):
    if not query_tokens or not candidate_tokens:
        return 0.0
    matches = sum(1 for token in query_tokens if token in candidate_tokens)
    return matches / len(query_tokens)


def _keyword_fallback(query_tokens):
    best_item = None
    best_score = 0.0
    for item in _questions_data or []:
        question_tokens = set(_tokenize(item['question']))
        answer_tokens = set(_tokenize(item['answer']))
        candidate_tokens = question_tokens | answer_tokens
        score = _overlap_score(query_tokens, candidate_tokens)
        if score > best_score:
            best_item = item
            best_score = score
    if best_item and best_score >= 0.2:
        return best_item
    return None


def search(query: str, top_k: int = 5, similarity_threshold: float = 1.35) -> str:
    """
    Search for relevant FAQ answers based on the query.
    
    Args:
        query: The user's question
        top_k: Number of top results to return (default: 3)
        similarity_threshold: Maximum L2 distance to consider relevant (default: 1.3)
                            Optimized for VOICE queries which are more varied and conversational
                            than text. 1.3 allows natural speech variations while filtering
                            completely unrelated topics (weather, jokes, etc.)
    
    Returns:
        A formatted string with the most relevant FAQ answers, or a message
        indicating no relevant information was found.
    """
    # Initialize if not already done
    if not _is_initialized:
        _initialize()
    
    # Encode the query
    query_embedding = _model.encode([query], convert_to_numpy=True)
    query_tokens = _tokenize(query)
    
    # Search the index
    distances, indices = _index.search(query_embedding.astype('float32'), top_k)

    candidates = []
    for i, idx in enumerate(indices[0]):
        distance = distances[0][i]
        if distance > similarity_threshold or idx >= len(_questions_data):
            continue

        item = _questions_data[idx]
        question = item['question']
        answer = item['answer']
        question_tokens = set(_tokenize(question))
        answer_tokens = set(_tokenize(answer))
        candidate_tokens = question_tokens | answer_tokens
        lexical_ratio = SequenceMatcher(None, query.lower(), question.lower()).ratio()
        overlap = _overlap_score(query_tokens, candidate_tokens)
        semantic = max(0.0, (similarity_threshold - distance) / similarity_threshold)
        score = (
            (lexical_ratio * _LEXICAL_WEIGHT)
            + (overlap * _OVERLAP_WEIGHT)
            + (semantic * _SEMANTIC_WEIGHT)
        )
        candidates.append({
            "question": question,
            "answer": answer,
            "distance": distance,
            "lexical_ratio": lexical_ratio,
            "overlap": overlap,
            "semantic": semantic,
            "score": score,
        })

    if not candidates:
        fallback_item = _keyword_fallback(query_tokens)
        if fallback_item:
            return f"Q: {fallback_item['question']}\nA: {fallback_item['answer']}"
        return "No relevant information found in the FAQ database."

    ranked = sorted(candidates, key=lambda item: item["score"], reverse=True)
    top_candidate = ranked[0]

    if top_candidate["lexical_ratio"] >= _EXACT_MATCH_RATIO or top_candidate["overlap"] >= 0.6:
        selected = [top_candidate]
    else:
        selected = [item for item in ranked if item["overlap"] >= _MIN_OVERLAP_SCORE][:2]
        if not selected:
            selected = [top_candidate]
        elif top_candidate not in selected:
            selected = [top_candidate] + selected[:1]

    formatted = [f"Q: {item['question']}\nA: {item['answer']}" for item in selected]
    return "\n\n---\n\n".join(formatted)


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
        print("[INFO] Cache cleared. Next search will rebuild embeddings.")
    else:
        print("No cache to clear.")


def rebuild_cache():
    """Force rebuild of embeddings cache from the source JSON file."""
    global _is_initialized
    clear_cache()
    _is_initialized = False
    _initialize()
    print("[INFO] Cache rebuilt successfully.")


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
