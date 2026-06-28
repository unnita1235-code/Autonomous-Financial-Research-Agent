# DEPLOYMENT NOTE: This uses TF-IDF (sklearn) instead of sentence-transformers.
# Reason: sentence-transformers requires ~600MB RAM; Render free tier has 512MB.
# TF-IDF uses ~20MB RAM with acceptable quality for financial term matching.
# To restore neural embeddings on a paid tier: replace with all-MiniLM-L6-v2.

"""
Lightweight TF-IDF based embedder for memory-constrained deployments.
Replaces sentence-transformers to reduce memory usage from ~600MB to ~20MB.
Interface is identical — embed() and embed_batch() return fixed-size vectors.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
import pickle
import os
import logging

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 512  # Fixed output dimension for FAISS compatibility

# Global vectorizer — fitted lazily on first use
_vectorizer: TfidfVectorizer | None = None
_vectorizer_path = "memory/tfidf_vectorizer.pkl"

# Seed corpus so the vectorizer has a vocabulary from the start
# These are common financial terms that will appear in research data
_SEED_CORPUS = [
    "revenue quarterly earnings income financial performance",
    "apple microsoft tesla google amazon stock market",
    "SEC EDGAR filing 10-K 10-Q annual report earnings",
    "EPS earnings per share dividend growth forecast guidance",
    "sentiment positive negative neutral market analyst",
    "risk assessment conflict data quality synthesis",
]


def _get_vectorizer() -> TfidfVectorizer:
    """Get or initialize the TF-IDF vectorizer."""
    global _vectorizer
    if _vectorizer is not None:
        return _vectorizer
    
    # Try to load saved vectorizer
    if os.path.exists(_vectorizer_path):
        try:
            with open(_vectorizer_path, "rb") as f:
                _vectorizer = pickle.load(f)
            logger.info("Loaded existing TF-IDF vectorizer")
            return _vectorizer
        except Exception:
            pass
    
    # Create new vectorizer fitted on seed corpus
    _vectorizer = TfidfVectorizer(
        max_features=EMBEDDING_DIM,
        ngram_range=(1, 2),
        sublinear_tf=True,
        strip_accents="unicode",
    )
    _vectorizer.fit(_SEED_CORPUS)
    _save_vectorizer()
    logger.info("Created new TF-IDF vectorizer with %d features", EMBEDDING_DIM)
    return _vectorizer


def _save_vectorizer():
    """Persist the vectorizer so it survives restarts."""
    global _vectorizer
    if _vectorizer is None:
        return
    os.makedirs("memory", exist_ok=True)
    try:
        with open(_vectorizer_path, "wb") as f:
            pickle.dump(_vectorizer, f)
    except Exception as e:
        logger.warning("Could not save vectorizer: %s", e)


def _text_to_vector(text: str) -> list[float]:
    """Convert text to a fixed-size normalized float vector."""
    vec = _get_vectorizer()
    # Transform returns sparse matrix — convert to dense
    sparse = vec.transform([text])
    dense = sparse.toarray().flatten()
    # Ensure fixed size (pad or truncate to EMBEDDING_DIM)
    if len(dense) < EMBEDDING_DIM:
        dense = np.pad(dense, (0, EMBEDDING_DIM - len(dense)))
    else:
        dense = dense[:EMBEDDING_DIM]
    # L2 normalize for cosine similarity via FAISS IndexFlatIP
    norm = np.linalg.norm(dense)
    if norm > 0:
        dense = dense / norm
    return dense.tolist()


def embed(text: str) -> list[float]:
    """
    Embed a single text string into a fixed-size vector.
    
    Args:
        text: Input text to embed
    Returns:
        List of floats of length EMBEDDING_DIM (512), L2 normalized
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM
    return _text_to_vector(text)


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple texts efficiently.
    
    Args:
        texts: List of input strings
    Returns:
        List of embedding vectors, each of length EMBEDDING_DIM
    """
    return [embed(t) for t in texts]


def normalize_vector(vec: list[float]) -> list[float]:
    """
    L2 normalize a vector (for cosine similarity via FAISS IndexFlatIP).
    
    Args:
        vec: Input vector
    Returns:
        L2 normalized vector
    """
    arr = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()
