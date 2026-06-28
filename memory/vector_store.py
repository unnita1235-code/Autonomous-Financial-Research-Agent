"""
memory/vector_store.py
──────────────────────
FAISS-backed semantic memory for the financial research agent.

Architecture:
  Layer 1 — Working Memory: Python list in react_loop.py (per-session, volatile)
  Layer 2 — Semantic Memory: This module (persisted to disk, survives restarts)

Index choice: FAISS IndexFlatIP
──────────────────────────────
WHY IndexFlatIP + L2 normalisation == cosine similarity:

  Cosine similarity is defined as:
      cos(a, b) = (a · b) / (‖a‖ × ‖b‖)

  If both vectors are already L2-normalised (‖a‖ = ‖b‖ = 1), then:
      cos(a, b) = a · b  (just the inner product)

  IndexFlatIP computes the inner product directly.  So by normalising
  all vectors before insertion (see embedder.py), we get exact cosine
  similarity rankings from FAISS without needing IndexFlatL2 or any
  post-processing.

  We chose IndexFlatIP over HNSW (IndexHNSWFlat) because:
    • Our index will have < 100k vectors for a long time (financial research)
    • Flat index gives exact results — no approximate recall trade-offs
    • HNSW adds memory overhead (graph structure) and build-time complexity
    • At this scale, brute-force search is fast enough (< 10ms for 100k vectors)

Persistence:
  • FAISS index → memory/faiss_index.bin  (binary, portable)
  • Metadata    → memory/metadata.json    (human-readable, parallel list)
  Position i in the FAISS index corresponds to position i in the metadata list.

Score threshold: 0.75
─────────────────────
Results with cosine similarity < 0.75 are filtered out.  This is an
empirically tuned value — in testing with financial text, scores below
0.75 tend to be topically unrelated (e.g., AAPL revenue vs TSLA
production numbers).  Scores 0.85+ are usually direct hits.  0.75 is
conservative enough to surface tangentially related data without
flooding the prompt with noise.  Adjust if retrieval precision/recall
needs tuning in production.
"""

import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

import numpy as np

from .chunker import chunk_text
from .embedder import embed, embed_batch, EMBEDDING_DIM

logger = logging.getLogger(__name__)

# ── Defaults ────────────────────────────────────────────────────────────────
_DEFAULT_INDEX_PATH = os.path.join("memory", "faiss_index.bin")
_DEFAULT_METADATA_PATH = os.path.join("memory", "metadata.json")
_SCORE_THRESHOLD = 0.75


class VectorStore:
    """
    Semantic memory backed by a FAISS flat inner-product index.

    Thread-safe: all mutations to the index + metadata are guarded by a lock.
    Read-only retrieve() does NOT acquire the lock — FAISS flat index search
    is safe for concurrent reads as long as no write is in progress, and we
    accept the (extremely unlikely) race of reading stale data for one query.

    Usage:
        store = VectorStore()
        store.store("Apple Q3 revenue was $85.8B", {"ticker": "AAPL", ...})
        results = store.retrieve("Apple revenue growth")
        store.save()
    """

    def __init__(
        self,
        index_path: str = _DEFAULT_INDEX_PATH,
        metadata_path: str = _DEFAULT_METADATA_PATH,
    ):
        """
        Load an existing FAISS index and metadata from disk, or create new
        ones if the files don't exist.

        Args:
            index_path:    Path to the FAISS binary index file.
            metadata_path: Path to the JSON metadata file.
        """
        try:
            import faiss  # type: ignore
        except ImportError:
            raise ImportError("pip install faiss-cpu  — required for vector store")

        self._faiss = faiss
        self._index_path = index_path
        self._metadata_path = metadata_path
        self._lock = threading.Lock()

        # ── Load or create ──────────────────────────────────────────────
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            logger.info("Loading existing FAISS index from %s", index_path)
            self._index = faiss.read_index(index_path)
            with open(metadata_path, "r", encoding="utf-8") as f:
                self._metadata: List[Dict[str, Any]] = json.load(f)

            # Sanity check: index size must match metadata length
            if self._index.ntotal != len(self._metadata):
                logger.warning(
                    "Index size (%d) != metadata length (%d) — rebuilding from scratch",
                    self._index.ntotal, len(self._metadata),
                )
                self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
                self._metadata = []
        else:
            logger.info("Creating new FAISS IndexFlatIP (dim=%d)", EMBEDDING_DIM)
            self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self._metadata = []

    # ── Public API ──────────────────────────────────────────────────────

    def store(self, text: str, metadata: Dict[str, Any]) -> None:
        """
        Chunk, embed, and store text with associated metadata.

        If the text is longer than 400 tokens it will be split into
        overlapping chunks.  Each chunk gets its own entry in the index
        and its own metadata record (with a "chunk_text" field added).

        Args:
            text:     The text content to store (e.g., a tool response).
            metadata: Dict with context — typically includes:
                      {"source": str, "ticker": str, "period": str, "type": str}
        """
        if not text or not text.strip():
            logger.warning("store() called with empty text — skipping")
            return

        # ── Chunk ───────────────────────────────────────────────────────
        chunks = chunk_text(text)
        if not chunks:
            return

        # ── Embed ───────────────────────────────────────────────────────
        vectors = embed_batch(chunks)
        vec_array = np.array(vectors, dtype=np.float32)

        # ── Build per-chunk metadata ────────────────────────────────────
        chunk_metas = []
        for chunk in chunks:
            entry = dict(metadata)  # shallow copy per chunk
            entry["chunk_text"] = chunk
            chunk_metas.append(entry)

        # ── Write to index (thread-safe) ────────────────────────────────
        with self._lock:
            self._index.add(vec_array)
            self._metadata.extend(chunk_metas)

        logger.info(
            "Stored %d chunk(s) — index now has %d vectors",
            len(chunks), self._index.ntotal,
        )

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find the top-k most similar chunks to the query.

        Args:
            query: Natural language query string.
            top_k: Maximum number of results to return (default 5).

        Returns:
            List of dicts sorted by descending similarity:
            [
                {
                    "text":     str,   # the stored chunk text
                    "metadata": dict,  # the stored metadata (source, ticker, ...)
                    "score":    float, # cosine similarity score (0.0 - 1.0)
                },
                ...
            ]
            Results with score < 0.75 are filtered out.
        """
        if self._index.ntotal == 0:
            logger.debug("retrieve() called on empty index — returning []")
            return []

        # ── Embed the query ─────────────────────────────────────────────
        query_vec = embed(query)
        query_array = np.array([query_vec], dtype=np.float32)

        # ── Search ──────────────────────────────────────────────────────
        # FAISS returns (distances, indices) arrays of shape (1, top_k)
        actual_k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_array, actual_k)

        # ── Build results, filtering by score threshold ─────────────────
        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue  # FAISS padding for sparse results
            if score < _SCORE_THRESHOLD:
                continue  # too dissimilar — would add noise to the prompt

            meta = dict(self._metadata[idx])  # copy to avoid mutation
            chunk_text_val = meta.pop("chunk_text", "")

            results.append({
                "text": chunk_text_val,
                "metadata": meta,
                "score": round(float(score), 4),
            })

        logger.debug(
            "retrieve(%r) → %d results above threshold (searched %d vectors)",
            query[:60], len(results), self._index.ntotal,
        )
        return results

    def save(self) -> None:
        """
        Persist the FAISS index and metadata to disk.

        Should be called after the agent loop exits to ensure all data
        from the session is durably stored.
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self._index_path) or ".", exist_ok=True)

        with self._lock:
            self._faiss.write_index(self._index, self._index_path)
            with open(self._metadata_path, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, indent=2, ensure_ascii=False)

        logger.info(
            "Saved FAISS index (%d vectors) → %s  |  metadata → %s",
            self._index.ntotal, self._index_path, self._metadata_path,
        )

    @property
    def size(self) -> int:
        """Return the number of vectors currently in the index."""
        return self._index.ntotal
