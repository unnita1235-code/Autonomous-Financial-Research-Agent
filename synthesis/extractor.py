"""
synthesis/extractor.py
──────────────────────
Metric extraction from each tool's raw output.

Each tool returns data in a different shape:
  • SEC EDGAR  → structured XBRL arrays (high fidelity)
  • Transcript → unstructured speaker text (best-effort regex)
  • News       → sentiment score only (no hard numbers)

This module normalizes all of them into a common metric format
that the downstream conflict detector and resolver can consume.

IMPORTANT: Transcript numeric extraction is best-effort.
Values extracted from natural language (e.g., "approximately $84 billion")
are inherently less reliable than SEC XBRL data.  The resolver accounts
for this via the source priority hierarchy.
"""

import re
import logging
from typing import Any, Dict, List, Optional

from .normalizer import normalize_value

logger = logging.getLogger(__name__)

# ── Canonical metric names ──────────────────────────────────────────────────
# These are the metric keys the rest of the pipeline expects.
METRIC_REVENUE = "revenue"
METRIC_NET_INCOME = "net_income"
METRIC_EPS = "eps"
METRIC_GUIDANCE = "guidance"
METRIC_SENTIMENT = "sentiment_score"

# ── SEC XBRL key → canonical metric mapping ────────────────────────────────
_SEC_KEY_MAP = {
    "revenue_quarterly":    METRIC_REVENUE,
    "net_income_quarterly": METRIC_NET_INCOME,
    "eps_quarterly":        METRIC_EPS,
}

# ── Transcript regex patterns ──────────────────────────────────────────────
# Each pattern maps a regex to a canonical metric name.
# We look for phrases like:
#   "revenue of $85.8 billion"
#   "EPS of $2.18"
#   "net income was $20.5 billion"
#   "earnings per share of $1.46"
#
# The regex captures the numeric portion (including $ sign and suffix),
# which is then fed through normalize_value().
_TRANSCRIPT_PATTERNS = [
    # Revenue patterns
    (re.compile(
        r"revenue[s]?\s+(?:of|was|were|reached|totaled|came in at)?\s*"
        r"(\$?\s*[\d,]+\.?\d*\s*(?:billion|million|trillion|[BMT])?)",
        re.IGNORECASE,
    ), METRIC_REVENUE),

    # EPS patterns
    (re.compile(
        r"(?:earnings?\s+per\s+share|EPS)\s+(?:of|was|were|reached|came in at)?\s*"
        r"(\$?\s*[\d,]+\.?\d*)",
        re.IGNORECASE,
    ), METRIC_EPS),

    # Net income patterns
    (re.compile(
        r"net\s+income\s+(?:of|was|were|reached|totaled|came in at)?\s*"
        r"(\$?\s*[\d,]+\.?\d*\s*(?:billion|million|trillion|[BMT])?)",
        re.IGNORECASE,
    ), METRIC_NET_INCOME),
]

# Guidance detection — qualitative, not numeric
_GUIDANCE_REGEX = re.compile(
    r"(?:guidance|outlook|expect|forecast|anticipate|project)[^.]*\.",
    re.IGNORECASE,
)


def _extract_from_sec(tool_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract metrics from SEC EDGAR structured XBRL data.

    SEC data is the highest-fidelity source — values come directly from
    audited filings in machine-readable format.  No parsing ambiguity.

    Args:
        tool_output: The full tool result dict with source="sec_edgar".

    Returns:
        List of metric dicts in the common format.
    """
    metrics = []
    data = tool_output.get("data", {})

    if not data or tool_output.get("error"):
        return metrics

    for sec_key, metric_name in _SEC_KEY_MAP.items():
        entries = data.get(sec_key, [])
        for entry in entries:
            raw_value = entry.get("value")
            normalized = normalize_value(raw_value)

            metrics.append({
                "metric_name": metric_name,
                "value": normalized,
                "raw": str(raw_value) if raw_value is not None else None,
                "source": "sec_edgar",
                "period": entry.get("period", "unknown"),
                "is_qualitative": False,
            })

    return metrics


def _extract_from_transcript(tool_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract metrics from earnings transcript text via regex.

    WARNING: This extraction is best-effort.  Transcripts contain
    natural language with verbal approximations ("about $84 billion"),
    rounding, and context-dependent phrasing.  Values extracted here
    should be treated with lower confidence than SEC XBRL data.

    Args:
        tool_output: The full tool result dict with source="transcript".

    Returns:
        List of metric dicts.  Values may be None if regex fails.
    """
    metrics = []
    data = tool_output.get("data", [])

    if not data or tool_output.get("error"):
        return metrics

    # The transcript data is a list of speaker segments
    segments = data if isinstance(data, list) else []

    # Collect all text into one blob for metric extraction
    all_text = " ".join(seg.get("text", "") for seg in segments if seg.get("text"))

    if not all_text:
        return metrics

    # Try to extract a period from the transcript title/context
    # The transcript tool includes the quarter in the HTML title
    period = "latest"  # default fallback
    ticker = tool_output.get("ticker", "")

    # Track which metrics we've already found to avoid duplicates
    found_metrics = set()

    # ── Numeric metric extraction via regex ─────────────────────────────
    for pattern, metric_name in _TRANSCRIPT_PATTERNS:
        if metric_name in found_metrics:
            continue

        match = pattern.search(all_text)
        if match:
            raw_str = match.group(1).strip()
            normalized = normalize_value(raw_str)

            metrics.append({
                "metric_name": metric_name,
                "value": normalized,
                "raw": raw_str,
                "source": "transcript",
                "period": period,
                "is_qualitative": False,
            })
            found_metrics.add(metric_name)

    # ── Guidance extraction (qualitative) ───────────────────────────────
    guidance_match = _GUIDANCE_REGEX.search(all_text)
    if guidance_match:
        guidance_text = guidance_match.group(0).strip()
        metrics.append({
            "metric_name": METRIC_GUIDANCE,
            "value": guidance_text,
            "raw": guidance_text,
            "source": "transcript",
            "period": period,
            "is_qualitative": True,
        })

    return metrics


def _extract_from_news(tool_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract sentiment score from news data.

    We do NOT extract hard numbers from news headlines — they are
    third-party reporting that is often repackaged, rounded, or
    out-of-date.  Sentiment is the only reliable signal from news.

    Args:
        tool_output: The full tool result dict with source="news".

    Returns:
        List containing a single sentiment_score metric (or empty if error).
    """
    metrics = []
    data = tool_output.get("data", {})

    if not data or tool_output.get("error"):
        return metrics

    sentiment = data.get("sentiment_score")
    article_count = data.get("article_count", 0)
    if sentiment is not None:
        metrics.append({
            "metric_name": METRIC_SENTIMENT,
            "value": float(sentiment),
            "raw": str(sentiment),
            "source": "news",
            "period": "latest",
            "is_qualitative": False,
            "article_count": article_count,
        })

    return metrics


def _extract_from_yfinance(tool_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract metrics from yfinance-derived financial data.
    """
    metrics = []
    data = tool_output.get("data", {})
    ratios = tool_output.get("derived_ratios", {})

    # Extract from raw data (latest year)
    if data:
        latest_year = sorted(data.keys())[-1]
        year_data = data[latest_year]
        
        # Mapping yfinance keys to canonical keys
        mapping = {
            "Total Revenue": "revenue",
            "Net Income": "net_income",
            "Diluted EPS": "eps",
            "Total Assets": "total_assets",
            "Total Liabilities Net Minority Interest": "total_liabilities"
        }
        
        for yf_key, canonical in mapping.items():
            if yf_key in year_data:
                metrics.append({
                    "metric_name": canonical,
                    "value": year_data[yf_key],
                    "raw": str(year_data[yf_key]),
                    "source": "yfinance",
                    "period": latest_year,
                    "is_qualitative": False
                })

    # Extract ratios
    for ratio_name, value in ratios.items():
        if value is not None:
            metrics.append({
                "metric_name": ratio_name,
                "value": value,
                "raw": str(value),
                "source": "yfinance",
                "period": "latest",
                "is_qualitative": False
            })

    return metrics


# ── Source → extractor dispatch ─────────────────────────────────────────────
_EXTRACTORS = {
    "sec_edgar":      _extract_from_sec,
    "sec":            _extract_from_sec,
    "transcript":     _extract_from_transcript,
    "news":           _extract_from_news,
    "yfinance":       _extract_from_yfinance,
    "financial_data": _extract_from_yfinance,
}


def extract_metrics(tool_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract comparable metrics from a single tool result.

    Routes extraction to the appropriate handler based on the tool's
    source field.  Unknown sources are logged and skipped.

    Args:
        tool_result: A dict with at least {"source": str, "data": ..., "error": ...}
                     as returned by the tool functions in tools/.

    Returns:
        List of metric dicts in the common format:
        {
            "metric_name": str,       # canonical key (revenue, eps, etc.)
            "value": float | str | None,
            "raw": str | None,        # original text for audit trail
            "source": str,            # provenance tag
            "period": str,            # fiscal period or "latest"
            "is_qualitative": bool,   # True for guidance text
        }
    """
    source = tool_result.get("source", "")

    extractor_fn = _EXTRACTORS.get(source)
    if extractor_fn is None:
        logger.warning("No extractor for source '%s' — skipping", source)
        return []

    try:
        return extractor_fn(tool_result)
    except Exception as exc:
        logger.error("Extraction failed for source '%s': %s", source, exc)
        return []
