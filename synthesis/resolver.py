"""
synthesis/resolver.py
─────────────────────
Resolves conflicting metrics using a priority hierarchy and
computes confidence scores.

PRIORITY HIERARCHY:
  SEC EDGAR (1) > Transcript (2) > News (3)

  SEC = audited XBRL filings, machine-readable, highest fidelity
  Transcript = management's own words, verbal approximations
  News = third-party reporting, often repackaged, lowest reliability

CONFIDENCE SCORES:
  0.90 = Multiple sources agree within 5%  → high trust
  0.70 = Single source only               → moderate trust
  0.65 = Conflict resolved by priority     → lower trust
  0.30 = Source returned error             → data may be missing
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Priority: lower number = higher priority
SOURCE_PRIORITY = {
    "sec_edgar":   1,
    "transcript":  2,
    "news":        3,
}

CONFIDENCE_MULTI_AGREE = 0.90
CONFIDENCE_BASE_REAL_DATA = 0.75
CONFIDENCE_NEWS_HIGH_VOLUME = 0.80
CONFIDENCE_LOW_RELIABILITY_SINGLE = 0.70
CONFIDENCE_CONFLICT_RESOLVED = 0.65
CONFIDENCE_ERROR = 0.30


def _get_single_source_confidence(entry: Dict[str, Any]) -> float:
    """Determine confidence for a single source based on its reliability."""
    if entry["source"] == "sec_edgar":
        return CONFIDENCE_BASE_REAL_DATA
    elif entry["source"] == "news" and entry.get("metric_name") == "sentiment_score":
        if entry.get("article_count", 0) >= 30:
            return CONFIDENCE_NEWS_HIGH_VOLUME
    return CONFIDENCE_LOW_RELIABILITY_SINGLE


def _format_value_short(value: float) -> str:
    """Format a large number for human-readable conflict detail strings."""
    abs_val = abs(value)
    if abs_val >= 1e12:
        return f"${value / 1e12:.1f}T"
    elif abs_val >= 1e9:
        return f"${value / 1e9:.1f}B"
    elif abs_val >= 1e6:
        return f"${value / 1e6:.1f}M"
    elif abs_val >= 1e3:
        return f"${value / 1e3:.1f}K"
    else:
        return f"${value:.2f}"


def resolve_metric(
    metric_name: str,
    entries: List[Dict[str, Any]],
    conflict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Resolve a single metric across sources.

    Args:
        metric_name: Canonical metric key (e.g. "revenue").
        entries:     List of metric dicts for this metric from all sources.
        conflict:    Conflict record from detect_conflicts(), or None.

    Returns:
        {
            "value": float | str | None,
            "winning_source": str,
            "confidence": float,
            "conflict_flagged": bool,
            "conflict_detail": str | None,
            "period": str,
        }
    """
    if not entries:
        return {
            "value": None,
            "winning_source": "none",
            "confidence": CONFIDENCE_ERROR,
            "conflict_flagged": False,
            "conflict_detail": None,
            "period": "unknown",
        }

    # Filter to entries with non-None values
    valid = [e for e in entries if e.get("value") is not None]
    if not valid:
        return {
            "value": None,
            "winning_source": entries[0].get("source", "unknown"),
            "confidence": CONFIDENCE_ERROR,
            "conflict_flagged": False,
            "conflict_detail": None,
            "period": entries[0].get("period", "unknown"),
        }

    # Handle qualitative metrics (guidance) — no numeric resolution
    if any(e.get("is_qualitative") for e in valid):
        # Pick highest-priority source
        best = min(valid, key=lambda e: SOURCE_PRIORITY.get(e["source"], 99))
        confidence = _get_single_source_confidence(best)
        return {
            "value": best["value"],
            "winning_source": best["source"],
            "confidence": confidence,
            "conflict_flagged": False,
            "conflict_detail": None,
            "period": best.get("period", "latest"),
        }

    # ── Single source ───────────────────────────────────────────────
    unique_sources = {e["source"] for e in valid}
    if len(unique_sources) == 1:
        best = valid[0]
        confidence = _get_single_source_confidence(best)
        return {
            "value": best["value"],
            "winning_source": best["source"],
            "confidence": confidence,
            "conflict_flagged": False,
            "conflict_detail": None,
            "period": best.get("period", "unknown"),
        }

    # ── Multiple sources — check for conflict ───────────────────────
    is_flagged = conflict is not None and conflict.get("flagged", False)

    if is_flagged:
        # Conflict: pick highest-priority source
        best = min(valid, key=lambda e: SOURCE_PRIORITY.get(e["source"], 99))
        # Build human-readable detail
        parts = []
        for e in valid:
            src = e["source"].replace("_", " ").upper()
            val_str = _format_value_short(e["value"]) if isinstance(e["value"], (int, float)) else str(e["value"])
            parts.append(f"{src}: {val_str}")
        diff_pct = conflict.get("max_diff_pct", 0)
        detail = f"{' vs '.join(parts)} ({diff_pct:.1f}% diff)"

        return {
            "value": best["value"],
            "winning_source": best["source"],
            "confidence": CONFIDENCE_CONFLICT_RESOLVED,
            "conflict_flagged": True,
            "conflict_detail": detail,
            "period": best.get("period", "unknown"),
        }
    else:
        # Sources agree (within 5%) — average numeric values
        numeric_vals = [e["value"] for e in valid if isinstance(e["value"], (int, float))]
        avg_value = sum(numeric_vals) / len(numeric_vals) if numeric_vals else None
        best = min(valid, key=lambda e: SOURCE_PRIORITY.get(e["source"], 99))

        return {
            "value": avg_value,
            "winning_source": best["source"],
            "confidence": CONFIDENCE_MULTI_AGREE,
            "conflict_flagged": False,
            "conflict_detail": None,
            "period": best.get("period", "unknown"),
        }
