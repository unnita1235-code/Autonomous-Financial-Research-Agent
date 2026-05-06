"""
synthesis/engine.py
───────────────────
Main orchestrator for the synthesis pipeline.

Pipeline: extract → normalize → detect_conflicts → resolve → assemble

Called AFTER the agent loop exits with accumulated memory.
Output feeds directly into the report generator (Phase 5).

SYNTHESIS_QUALITY METRIC:
  Arithmetic mean of all resolved metric confidence scores.
    0.85–1.0 : All metrics corroborated — high-quality synthesis
    0.70–0.85: Mostly single-source — acceptable
    0.50–0.70: Significant conflicts or missing data — treat with caution
    < 0.50   : Major data gaps or errors — needs manual review
"""

import logging
from typing import Any, Dict, List, Optional
from collections import defaultdict

from .extractor import extract_metrics
from .conflict_detector import detect_conflicts
from .resolver import resolve_metric
from .narrative import generate_conflict_narrative

logger = logging.getLogger(__name__)


def _extract_tool_outputs(memory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Pull tool_output dicts from the agent's working memory.

    The memory format from run_agent() is:
        [{"iteration": int, "decision": {...}, "tool_output": {...}}, ...]

    We skip entries with no tool_output or where tool_output has an error.
    Error entries are still collected separately for confidence scoring.
    """
    outputs = []
    for entry in memory:
        tool_out = entry.get("tool_output")
        if tool_out and isinstance(tool_out, dict):
            outputs.append(tool_out)
    return outputs


def _detect_ticker(memory: List[Dict[str, Any]], tool_outputs: List[Dict]) -> str:
    """Auto-detect ticker from memory entries."""
    for out in tool_outputs:
        ticker = out.get("ticker")
        if ticker:
            return ticker.upper()
    # Fallback: check decision args
    for entry in memory:
        decision = entry.get("decision", {})
        args = decision.get("tool_args", {})
        if args and isinstance(args, dict):
            ticker = args.get("ticker")
            if ticker:
                return ticker.upper()
    return "UNKNOWN"


def _has_errors(tool_outputs: List[Dict]) -> bool:
    """Check if any tool output contains an error."""
    return any(out.get("error") for out in tool_outputs)


def synthesize(
    memory: List[Dict[str, Any]],
    ticker: Optional[str] = None,
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Main synthesis entry point.

    Takes the agent's accumulated memory and produces a structured
    findings dict with confidence scores per metric.

    Args:
        memory:     The "memory" list from run_agent() output.
        ticker:     Override ticker symbol. If None, auto-detected.
        llm_client: Optional LLM client for conflict narrative.

    Returns:
        Structured synthesis dict (see module docstring for schema).
    """
    # ── 0. Handle empty input ───────────────────────────────────────
    if not memory:
        return {
            "ticker": ticker or "UNKNOWN",
            "metrics": {},
            "conflicts_detected": [],
            "conflict_narrative": None,
            "synthesis_quality": 0.0,
        }

    # ── 1. Extract tool outputs from memory ─────────────────────────
    tool_outputs = _extract_tool_outputs(memory)
    resolved_ticker = ticker or _detect_ticker(memory, tool_outputs)

    logger.info(
        "Synthesis started: ticker=%s, %d tool outputs",
        resolved_ticker, len(tool_outputs),
    )

    # ── 2. Extract metrics from each source ─────────────────────────
    all_metrics: List[Dict[str, Any]] = []
    error_sources = []

    for out in tool_outputs:
        if out.get("error"):
            error_sources.append(out.get("source", "unknown"))
            continue
        extracted = extract_metrics(out)
        all_metrics.extend(extracted)

    logger.info("Extracted %d metrics from %d sources", len(all_metrics), len(tool_outputs))

    # ── 3. Detect conflicts ─────────────────────────────────────────
    conflicts = detect_conflicts(all_metrics)
    flagged_conflicts = [c for c in conflicts if c["flagged"]]

    logger.info(
        "Conflicts: %d total, %d flagged",
        len(conflicts), len(flagged_conflicts),
    )

    # ── 4. Group metrics and resolve ────────────────────────────────
    # Build a lookup: conflict by (metric, period)
    conflict_lookup: Dict[tuple, Dict] = {}
    for c in conflicts:
        key = (c["metric"], c["period"])
        conflict_lookup[key] = c

    # Group all metrics by metric_name (pick the most recent period)
    metric_groups: Dict[str, List[Dict]] = defaultdict(list)
    for m in all_metrics:
        metric_groups[m["metric_name"]].append(m)

    # Resolve each metric
    resolved_metrics: Dict[str, Dict[str, Any]] = {}

    for metric_name, entries in metric_groups.items():
        # Find the relevant conflict record (if any)
        # Use the first entry's period as the lookup key
        periods = {e.get("period", "unknown") for e in entries}
        conflict = None
        for p in periods:
            c = conflict_lookup.get((metric_name, p))
            if c is not None:
                conflict = c
                break

        resolution = resolve_metric(metric_name, entries, conflict)
        resolved_metrics[metric_name] = {
            "value": resolution["value"],
            "confidence": resolution["confidence"],
            "conflict": resolution["conflict_flagged"],
            "winning_source": resolution["winning_source"],
            "period": resolution["period"],
            "conflict_detail": resolution.get("conflict_detail"),
        }

    # ── 5. Handle error sources (add with low confidence) ───────────
    for src in error_sources:
        # Don't override existing metrics — just note the error
        logger.warning("Source '%s' returned an error", src)

    # ── 6. Compute synthesis quality ────────────────────────────────
    confidences = [m["confidence"] for m in resolved_metrics.values()]
    synthesis_quality = (
        round(sum(confidences) / len(confidences), 2)
        if confidences else 0.0
    )

    # ── 7. Generate conflict narrative (optional) ───────────────────
    narrative = None
    if flagged_conflicts:
        narrative = generate_conflict_narrative(flagged_conflicts, llm_client)

    # ── 8. Assemble final output ────────────────────────────────────
    result = {
        "ticker": resolved_ticker,
        "metrics": resolved_metrics,
        "conflicts_detected": flagged_conflicts,
        "conflict_narrative": narrative,
        "synthesis_quality": synthesis_quality,
    }

    logger.info(
        "Synthesis complete: ticker=%s, %d metrics, quality=%.2f",
        resolved_ticker, len(resolved_metrics), synthesis_quality,
    )

    return result
