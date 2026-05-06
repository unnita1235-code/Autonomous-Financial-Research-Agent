"""
memory/chunker.py
─────────────────
Token-aware text chunking for the semantic memory pipeline.

Chunking strategy:
  • Max 400 tokens per chunk, 50 token overlap between consecutive chunks.
  • Uses tiktoken with cl100k_base encoding (same tokeniser used by
    text-embedding-3-small and GPT-4o).

WHY 50-TOKEN OVERLAP?
  Overlap preserves context at chunk boundaries.  Financial statements
  often have figures that span sentences ("Revenue was $85.8B, driven
  primarily by iPhone sales of $46.2B").  Without overlap, the second
  chunk would lose the revenue context.  50 tokens ≈ 35-40 words —
  enough to capture a full transitional sentence without bloating the
  index with near-duplicate content.

WHY 400 TOKENS?
  text-embedding-3-small can handle up to 8191 tokens, but embedding
  quality degrades on very long inputs (the model averages over all
  token representations).  400 tokens is the sweet spot:
    • Long enough to capture a coherent financial thought
    • Short enough for precise similarity matching
    • Keeps FAISS index manageable in size
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

# ── Tokeniser ───────────────────────────────────────────────────────────────
# Lazy-loaded to avoid paying the import cost when not needed.
_encoder = None


def _get_encoder():
    """Return a cached tiktoken encoder (cl100k_base)."""
    global _encoder
    if _encoder is None:
        try:
            import tiktoken  # type: ignore
        except ImportError:
            raise ImportError("pip install tiktoken  — required for token counting")
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


# ── Public API ──────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    max_tokens: int = 400,
    overlap: int = 50,
) -> List[str]:
    """
    Split text into token-bounded chunks with overlap.

    Args:
        text:       The input text to chunk.
        max_tokens: Maximum number of tokens per chunk (default 400).
        overlap:    Number of overlapping tokens between consecutive chunks
                    (default 50).  Set to 0 for no overlap.

    Returns:
        A list of text strings, each ≤ max_tokens when re-tokenised.
        If the input is shorter than max_tokens, returns [text] as-is.
    """
    if not text or not text.strip():
        return []

    enc = _get_encoder()
    tokens = enc.encode(text)

    # ── Edge case: text fits in a single chunk ──────────────────────────
    if len(tokens) <= max_tokens:
        return [text]

    # ── Sliding window chunking ─────────────────────────────────────────
    chunks: List[str] = []
    start = 0
    step = max_tokens - overlap  # how far the window advances each time

    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text_str = enc.decode(chunk_tokens)
        chunks.append(chunk_text_str)

        # If we've consumed all tokens, stop
        if end == len(tokens):
            break

        start += step

    logger.debug(
        "Chunked %d tokens → %d chunks (max=%d, overlap=%d)",
        len(tokens), len(chunks), max_tokens, overlap,
    )
    return chunks
