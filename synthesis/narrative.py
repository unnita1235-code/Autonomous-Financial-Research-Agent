"""
synthesis/narrative.py
──────────────────────
Optional LLM-powered conflict narrative generation.

Only called when conflicts exist.  Returns 2-3 sentence explanation
of why sources disagree.  If the LLM call fails, returns a fallback
template string — this module NEVER crashes the pipeline.
"""

import logging
import json
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_NARRATIVE_PROMPT = """\
You are a financial data analyst. Below are data conflicts detected \
between different sources for the same financial metrics.

Conflicts:
{conflicts_json}

Write a concise 2-3 sentence explanation of WHY these sources might \
report different values. Consider factors like GAAP vs non-GAAP \
accounting, rounding in earnings calls, reporting lag, or different \
fiscal period definitions. Be factual and specific — do not speculate."""


def _build_fallback(conflicts: List[Dict[str, Any]]) -> str:
    """Build a template-based fallback when the LLM is unavailable."""
    n = len(conflicts)
    metrics = ", ".join(sorted({c["metric"] for c in conflicts}))
    return (
        f"{n} conflict(s) detected across metric(s): {metrics}. "
        "Differences may stem from GAAP vs non-GAAP accounting, "
        "rounding in earnings transcripts, or reporting lag between sources."
    )


def generate_conflict_narrative(
    conflicts: List[Dict[str, Any]],
    llm_client: Optional[Any] = None,
) -> str:
    """
    Generate a brief narrative explaining detected conflicts.

    Args:
        conflicts:  List of conflict records from detect_conflicts().
        llm_client: An object with a `.chat(messages) -> str` method
                    (e.g. agents.llm_client.LLMClient). If None, returns
                    a deterministic fallback string.

    Returns:
        A 2-3 sentence plain-text explanation.
    """
    if not conflicts:
        return "No conflicts detected."

    if llm_client is None:
        logger.info("No LLM client provided — using fallback narrative")
        return _build_fallback(conflicts)

    # Build a clean JSON summary for the LLM
    conflict_summary = []
    for c in conflicts:
        conflict_summary.append({
            "metric": c["metric"],
            "period": c.get("period", "unknown"),
            "values": c.get("values", []),
            "diff_pct": c.get("max_diff_pct", 0),
        })

    prompt = _NARRATIVE_PROMPT.format(
        conflicts_json=json.dumps(conflict_summary, indent=2)
    )

    messages = [
        {"role": "system", "content": "You are a financial data analyst."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = llm_client.chat(messages)
        # Strip any markdown fencing the LLM might add
        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        return text
    except Exception as exc:
        logger.warning("LLM narrative generation failed: %s — using fallback", exc)
        return _build_fallback(conflicts)
