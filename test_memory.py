"""
test_memory.py
──────────────
Integration test for the semantic memory system (Phase 3).

Tests the full pipeline:
  1. Chunker splits text correctly
  2. Embedder produces normalised vectors
  3. VectorStore.store() writes to FAISS + metadata
  4. VectorStore.retrieve() returns ranked results
  5. Metadata fields are preserved through the round-trip

Requirements:
    export OPENAI_API_KEY="sk-..."
    pip install faiss-cpu tiktoken openai numpy

Usage:
    python test_memory.py
"""

import json
import logging
import math
import os
import shutil
import sys
import tempfile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("test_memory")


def test_chunker():
    """Test the text chunker with various inputs."""
    from memory.chunker import chunk_text

    logger.info("─── Testing chunker ───")

    # Edge case: empty string
    assert chunk_text("") == [], "Empty string should return empty list"
    assert chunk_text("   ") == [], "Whitespace-only should return empty list"

    # Short text: should return as single chunk
    short = "Apple revenue was $85.8B in Q3 2024."
    chunks = chunk_text(short)
    assert len(chunks) == 1, f"Short text should be 1 chunk, got {len(chunks)}"
    assert chunks[0] == short, "Single chunk should equal original text"

    # Longer text: generate a text that exceeds 400 tokens
    # ~1600 tokens of financial text
    long_text = " ".join([
        f"In Q{q} {year}, the company reported revenue of ${85 + q}B, "
        f"representing a {5 + q}% year-over-year increase. "
        f"Operating margins expanded to {28 + q}% driven by cost efficiencies. "
        f"The services segment grew {12 + q}% to reach ${25 + q}B in annual run rate."
        for year in range(2022, 2026)
        for q in range(1, 5)
    ])
    chunks = chunk_text(long_text, max_tokens=400, overlap=50)
    assert len(chunks) > 1, f"Long text should produce multiple chunks, got {len(chunks)}"

    logger.info("  ✅ Chunker: %d chunks from long text", len(chunks))
    logger.info("  ✅ Chunker: all edge cases passed")


def test_embedder():
    """Test the embedder produces valid normalised vectors."""
    from memory.embedder import embed, embed_batch, normalize_vector, EMBEDDING_DIM

    logger.info("─── Testing embedder ───")

    # Test normalize_vector
    raw = [3.0, 4.0]
    normed = normalize_vector(raw)
    length = math.sqrt(sum(x * x for x in normed))
    assert abs(length - 1.0) < 1e-6, f"Normalised vector length should be 1.0, got {length}"

    # Zero vector edge case
    zero = normalize_vector([0.0, 0.0, 0.0])
    assert zero == [0.0, 0.0, 0.0], "Zero vector should remain zero"

    logger.info("  ✅ normalize_vector: unit length confirmed")

    # Test single embedding (requires API key)
    vec = embed("Apple Q3 2024 revenue was $85.8B")
    assert len(vec) == EMBEDDING_DIM, f"Expected dim {EMBEDDING_DIM}, got {len(vec)}"

    # Verify L2 normalisation
    vec_length = math.sqrt(sum(x * x for x in vec))
    assert abs(vec_length - 1.0) < 1e-4, f"Embedding should be normalised, length={vec_length}"

    logger.info("  ✅ embed(): dim=%d, normalised (length=%.6f)", len(vec), vec_length)

    # Test batch embedding
    texts = [
        "Apple revenue grew 5% year-over-year",
        "Tesla delivered 1.8M vehicles in 2024",
    ]
    vecs = embed_batch(texts)
    assert len(vecs) == 2, f"Batch should return 2 vectors, got {len(vecs)}"
    for i, v in enumerate(vecs):
        assert len(v) == EMBEDDING_DIM, f"Vector {i} has wrong dim"

    logger.info("  ✅ embed_batch(): %d vectors returned", len(vecs))


def test_vector_store():
    """Test the full store → retrieve → save cycle."""
    from memory.vector_store import VectorStore

    logger.info("─── Testing VectorStore ───")

    # Use a temp directory so tests don't pollute the real index
    tmp_dir = os.path.join("memory", "_test_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    index_path = os.path.join(tmp_dir, "faiss_index.bin")
    metadata_path = os.path.join(tmp_dir, "metadata.json")

    try:
        store = VectorStore(index_path=index_path, metadata_path=metadata_path)
        assert store.size == 0, "New store should be empty"

        # ── Store 3 sample financial text chunks ────────────────────────
        samples = [
            {
                "text": (
                    "Apple Q3 2024 revenue was $85.8B, up 5% YoY. "
                    "iPhone revenue was $46.2B. Services revenue hit $24.2B, "
                    "a new all-time record. Gross margin expanded to 46.3%."
                ),
                "metadata": {
                    "source": "sec_edgar",
                    "ticker": "AAPL",
                    "period": "2024-Q3",
                    "type": "revenue",
                },
            },
            {
                "text": (
                    "Tesla delivered 443,956 vehicles in Q3 2024, below the "
                    "consensus estimate of 462,000. Revenue was $25.2B. "
                    "Automotive gross margin declined to 17.1% due to price cuts. "
                    "Energy storage deployments grew 152% to 6.9 GWh."
                ),
                "metadata": {
                    "source": "sec_edgar",
                    "ticker": "TSLA",
                    "period": "2024-Q3",
                    "type": "deliveries",
                },
            },
            {
                "text": (
                    "Microsoft Azure revenue grew 29% in Q1 FY2025. "
                    "Total cloud revenue exceeded $38.9B. AI services contribution "
                    "added 12 percentage points to Azure growth. "
                    "Operating income was $30.6B, up 14% YoY."
                ),
                "metadata": {
                    "source": "sec_edgar",
                    "ticker": "MSFT",
                    "period": "2025-Q1",
                    "type": "cloud_revenue",
                },
            },
        ]

        for s in samples:
            store.store(s["text"], s["metadata"])

        logger.info("  Stored %d samples → index size: %d", len(samples), store.size)
        assert store.size >= 3, f"Index should have ≥ 3 vectors, has {store.size}"

        # ── Retrieve with a related query ───────────────────────────────
        results = store.retrieve("Apple revenue growth this year", top_k=3)
        logger.info("  Retrieved %d results for 'Apple revenue growth'", len(results))

        assert len(results) > 0, "Should find at least 1 result"

        # Top result should be about Apple
        top = results[0]
        logger.info("  Top result: score=%.4f  ticker=%s", top["score"], top["metadata"].get("ticker"))
        assert top["score"] > 0.75, f"Top score should be > 0.75, got {top['score']}"
        assert "AAPL" in top["metadata"].get("ticker", ""), "Top result should be about AAPL"

        # ── Verify metadata fields are preserved ────────────────────────
        assert "source" in top["metadata"], "Metadata should contain 'source'"
        assert "ticker" in top["metadata"], "Metadata should contain 'ticker'"
        assert "period" in top["metadata"], "Metadata should contain 'period'"
        assert "type" in top["metadata"], "Metadata should contain 'type'"
        assert isinstance(top["text"], str) and len(top["text"]) > 0, "text should be non-empty string"

        logger.info("  ✅ Metadata fields preserved: %s", list(top["metadata"].keys()))

        # ── Test cross-domain query (Tesla) ─────────────────────────────
        tesla_results = store.retrieve("Tesla vehicle deliveries", top_k=3)
        if tesla_results:
            assert tesla_results[0]["metadata"].get("ticker") == "TSLA", \
                "Tesla query should surface TSLA data first"
            logger.info(
                "  ✅ Tesla query → top hit: ticker=%s score=%.4f",
                tesla_results[0]["metadata"]["ticker"], tesla_results[0]["score"],
            )

        # ── Test save/load persistence ──────────────────────────────────
        store.save()
        assert os.path.exists(index_path), "FAISS index file should exist after save"
        assert os.path.exists(metadata_path), "Metadata file should exist after save"

        # Reload and verify
        store2 = VectorStore(index_path=index_path, metadata_path=metadata_path)
        assert store2.size == store.size, f"Reloaded index size mismatch: {store2.size} vs {store.size}"

        # Re-query to verify loaded index works
        reload_results = store2.retrieve("Apple revenue", top_k=1)
        assert len(reload_results) > 0, "Reloaded store should still return results"
        logger.info("  ✅ Save/load round-trip: index persisted and reloaded (%d vectors)", store2.size)

        # ── Test empty query on fresh store ─────────────────────────────
        empty_store = VectorStore(
            index_path=os.path.join(tmp_dir, "empty_index.bin"),
            metadata_path=os.path.join(tmp_dir, "empty_meta.json"),
        )
        empty_results = empty_store.retrieve("anything", top_k=5)
        assert empty_results == [], "Empty store should return empty list"
        logger.info("  ✅ Empty store retrieve: returned []")

    finally:
        # Clean up temp files
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
            logger.info("  Cleaned up temp directory: %s", tmp_dir)


def main():
    logger.info("=" * 60)
    logger.info("  PHASE 3 — Semantic Memory System Tests")
    logger.info("=" * 60)

    # ── Step 1: Test chunker (no API key needed) ─────────────────────────
    test_chunker()

    # ── Step 2: Test embedder (needs OPENAI_API_KEY) ─────────────────────
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning(
            "OPENAI_API_KEY not set — skipping embedder and vector store tests. "
            "Set the key and re-run for full coverage."
        )
        logger.info("=" * 60)
        logger.info("  ⚠️  Partial pass (chunker only)")
        logger.info("=" * 60)
        return

    test_embedder()

    # ── Step 3: Test vector store (needs OPENAI_API_KEY + faiss) ──────────
    test_vector_store()

    logger.info("=" * 60)
    logger.info("  ✅  All Phase 3 tests passed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
