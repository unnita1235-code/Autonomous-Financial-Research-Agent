"""
reports/verdict_logic.py
────────────────────────
Deterministic verdict computation — NO LLM.

Produces a buy/hold/sell-style signal based on synthesis quality,
metric confidence, and sentiment scores.  All thresholds are
documented with rationale.

THRESHOLD RATIONALE:
  0.75 (synthesis_quality gate):
    Below this, the synthesis has significant data gaps or conflicts.
    Any signal would be unreliable.  Academic research on analyst
    confidence shows <75% agreement correlates with random outcomes.

  0.80 (revenue_confidence):
    Revenue is the top-line metric.  0.80 means either multi-source
    agreement (0.90) or at minimum a single high-priority source (0.70)
    without conflict.  We require 0.80 to ensure at least partial
    corroboration.

  0.60 (sentiment_score):
    News sentiment is scored 0.0–1.0.  0.60 represents net-positive
    market reception.  Below 0.50 is neutral; below 0.40 is
    net-negative.  The 0.60 threshold ensures clear positive signal.

  0.40 (sentiment_caution):
    Below this, market reception is actively negative.  Combined with
    a revenue conflict, this warrants a "Caution" signal.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── Threshold constants (see docstring for rationale) ───────────────────
QUALITY_GATE = 0.75          # Min synthesis_quality to emit any signal
REVENUE_CONFIDENCE_MIN = 0.80  # Min revenue confidence for "Positive"
SENTIMENT_POSITIVE = 0.60    # Min sentiment for "Positive"
SENTIMENT_CAUTION = 0.40     # Max sentiment for "Caution"


def _compute_data_quality(confidence: float) -> str:
    """
    Map a confidence score to a human-readable quality label.

    Thresholds:
      ≥ 0.80 → "high"    — multi-source corroboration or high-priority single source
      ≥ 0.60 → "medium"  — single source or partial corroboration
      < 0.60 → "low"     — significant gaps, conflicts, or errors
    """
    if confidence >= 0.80:
        return "high"
    elif confidence >= 0.60:
        return "medium"
    else:
        return "low"


def compute_verdict(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute an investment signal from synthesis output.

    This is FULLY DETERMINISTIC — no LLM, no randomness.
    The signal is a function of synthesis_quality, revenue confidence,
    revenue conflict status, and news sentiment score.

    Args:
        synthesis: The full output dict from synthesize().

    Returns:
        {
            "signal": str,           # "Positive" | "Caution" | "Neutral" | "Insufficient Data"
            "reason": str,           # Human-readable explanation
            "data_quality": str,     # "high" | "medium" | "low"
            "confidence_used": float # The synthesis_quality score used
        }
    """
    quality = synthesis.get("synthesis_quality", 0.0)
    metrics = synthesis.get("metrics", {})

    # ── Gate: insufficient data ─────────────────────────────────────────
    if quality < QUALITY_GATE:
        return {
            "signal": "Insufficient Data",
            "reason": (
                f"Synthesis quality ({quality:.0%}) is below the {QUALITY_GATE:.0%} "
                "threshold required for actionable signals. This typically means "
                "multiple data sources were unavailable or returned errors. "
                "Collect more data before drawing conclusions."
            ),
            "data_quality": _compute_data_quality(quality),
            "confidence_used": quality,
        }

    # ── Extract key inputs ──────────────────────────────────────────────
    revenue = metrics.get("revenue", {})
    revenue_confidence = revenue.get("confidence", 0.0)
    revenue_conflict = revenue.get("conflict", False)

    sentiment = metrics.get("sentiment_score", {})
    sentiment_value = sentiment.get("value", 0.5)  # default neutral

    # ── Signal: Positive ────────────────────────────────────────────────
    if revenue_confidence > REVENUE_CONFIDENCE_MIN and sentiment_value > SENTIMENT_POSITIVE:
        reasons = []
        if revenue_confidence >= 0.90:
            reasons.append("Revenue confirmed by multiple corroborating sources")
        else:
            reasons.append(
                f"Revenue confidence ({revenue_confidence:.0%}) exceeds "
                f"{REVENUE_CONFIDENCE_MIN:.0%} threshold"
            )

        reasons.append(
            f"Positive market sentiment ({sentiment_value:.2f}) "
            f"above {SENTIMENT_POSITIVE} threshold"
        )

        if revenue.get("winning_source") == "sec_edgar":
            reasons.append("Revenue anchored to SEC EDGAR filings (highest fidelity)")

        return {
            "signal": "Positive",
            "reason": ". ".join(reasons) + ".",
            "data_quality": _compute_data_quality(quality),
            "confidence_used": quality,
        }

    # ── Signal: Caution ─────────────────────────────────────────────────
    if revenue_conflict and sentiment_value < SENTIMENT_CAUTION:
        return {
            "signal": "Caution",
            "reason": (
                f"Revenue data conflict detected between sources "
                f"({revenue.get('conflict_detail', 'details unavailable')}). "
                f"Combined with negative market sentiment ({sentiment_value:.2f}), "
                "this warrants caution. Verify revenue figures independently "
                "before making decisions."
            ),
            "data_quality": _compute_data_quality(quality),
            "confidence_used": quality,
        }

    # ── Signal: Neutral (default) ───────────────────────────────────────
    reasons = []
    if revenue_confidence <= REVENUE_CONFIDENCE_MIN:
        reasons.append(
            f"Revenue confidence ({revenue_confidence:.0%}) does not exceed "
            f"{REVENUE_CONFIDENCE_MIN:.0%} threshold for a positive signal"
        )
    if sentiment_value <= SENTIMENT_POSITIVE:
        reasons.append(
            f"Sentiment ({sentiment_value:.2f}) is at or below the "
            f"{SENTIMENT_POSITIVE} positive threshold"
        )
    if not reasons:
        reasons.append("Mixed signals — not enough conviction in either direction")

    return {
        "signal": "Neutral",
        "reason": ". ".join(reasons) + ". Holding is the prudent course.",
        "data_quality": _compute_data_quality(quality),
        "confidence_used": quality,
    }
