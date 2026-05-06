"""
memory/embedder.py
──────────────────
Thin wrapper around sentence-transformers embedding API.

Model: all-MiniLM-L6-v2
  • Output dimension: 384
  • Runs locally, free, no API key needed
  • Quality: sufficient for financial text similarity (we're matching tickers,
    time periods, and financial concepts — not nuanced literary analysis)

All vectors are L2-normalised before returning so they can be used directly
with FAISS IndexFlatIP for cosine similarity (see vector_store.py for details).
"""

import os
import math
import logging
from typing import List

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_model_instance = None

def _get_embedding_model():
    """Lazy-import and instantiate the sentence-transformers model."""
    global _model_instance
    if _model_instance is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("pip install sentence-transformers  — required for embeddings")
        _model_instance = SentenceTransformer(EMBEDDING_MODEL)
    return _model_instance


# ── L2 normalisation ───────────────────────────────────────────────────────
def normalize_vector(vec: List[float]) -> List[float]:
    """
    L2-normalise a vector in-place style (returns new list).

    WHY: FAISS IndexFlatIP computes inner product (dot product).
    For unit-length vectors, dot product == cosine similarity.
    So normalising before insertion lets us use the faster IP index
    while getting cosine semantics — no need for IndexFlatL2 + post-hoc
    conversion, and no need for the heavier IndexIVF variants.
    """
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec  # zero vector — nothing to normalise
    return [x / norm for x in vec]


# ── Single embedding ───────────────────────────────────────────────────────
def embed(text: str) -> List[float]:
    """
    Embed a single text string and return the L2-normalised vector.

    Args:
        text: The input text to embed.

    Returns:
        A list of 384 floats (unit-length).
    """
    model = _get_embedding_model()
    raw_vec = model.encode(text).tolist()
    return normalize_vector(raw_vec)


# ── Batch embedding ─────────────────────────────────────────────────────────
def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Embed multiple texts in a single API call (more efficient than looping).

    The sentence-transformers endpoint accepts a list of inputs natively.

    Args:
        texts: List of strings to embed.

    Returns:
        List of L2-normalised vectors, one per input text.
    """
    if not texts:
        return []

    model = _get_embedding_model()
    raw_vectors = model.encode(texts).tolist()
    normalised = [normalize_vector(v) for v in raw_vectors]

    logger.debug("Embedded batch of %d texts → %d vectors", len(texts), len(normalised))
    return normalised
