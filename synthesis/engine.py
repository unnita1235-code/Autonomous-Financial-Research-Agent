"""
synthesis/engine.py
───────────────────
Main synthesis entry point. 

Orchestrates:
1. Metric Extraction (via extractor.py)
2. Conflict Detection (via conflict_detector.py)
3. Priority Resolution (via resolver.py)
"""

import logging
from typing import Any, Dict, List, Optional
from collections import defaultdict

from .extractor import extract_metrics
from .conflict_detector import detect_conflicts
from .resolver import resolve_metric
from .narrative import generate_conflict_narrative

logger = logging.getLogger(__name__)


def _infer_ticker(memory: List[Dict[str, Any]]) -> str:
    """Extract ticker from agent memory tool outputs, or UNKNOWN."""
    for item in memory:
        decision = item.get("decision") or {}
        tool_args = decision.get("tool_args") or {}
        if tool_args.get("ticker"):
            return str(tool_args["ticker"]).upper()
        output = item.get("tool_output") or item.get("output") or {}
        if isinstance(output, dict) and output.get("ticker"):
            return str(output["ticker"]).upper()
    return "UNKNOWN"


def synthesize(memory: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Synthesize raw agent memory (tool outputs) into a resolved dict.

    This is the core "Synthesis Engine" that resolves conflicts between
    SEC data, transcripts, and news.

    Args:
        memory: List of agent memory items from run_agent().
                Expected to contain {"tool": str, "output": Dict, ...}.

    Returns:
        Synthesis dict with:
            metrics:            Dict of resolved canonical metrics.
            conflicts_detected: List of all conflict records (resolved or not).
            synthesis_quality:  Float [0, 1] representing data fidelity.
    """
    logger.info("Starting synthesis on %d memory items", len(memory))
    ticker = _infer_ticker(memory)

    # ── 1. Extract all raw metrics ──────────────────────────────────────
    all_raw_metrics = []
    for item in memory:
        # We only care about tool outputs
        output = item.get("tool_output") or item.get("output")
        if output and isinstance(output, dict):
            raw_metrics = extract_metrics(output)
            all_raw_metrics.extend(raw_metrics)

    if not all_raw_metrics:
        logger.warning("No metrics extracted during synthesis")
        return {
            "ticker": ticker,
            "metrics": {},
            "conflicts_detected": [],
            "synthesis_quality": 0.0,
        }

    # ── 2. Detect conflicts ─────────────────────────────────────────────
    conflicts = detect_conflicts(all_raw_metrics)

    conflict_narrative = None
    flagged_conflicts = [c for c in conflicts if c.get("flagged")]
    if flagged_conflicts:
        try:
            conflict_narrative = generate_conflict_narrative(flagged_conflicts, llm_client=None)
        except Exception:
            conflict_narrative = None

    # Create a map for fast lookup during resolution
    conflict_map = { (c["metric"], c["period"]): c for c in conflicts }

    # ── 3. Resolve metrics ──────────────────────────────────────────────
    # Group raw metrics by (name, period)
    metric_groups = defaultdict(list)
    for m in all_raw_metrics:
        key = (m["metric_name"], m.get("period", "unknown"))
        metric_groups[key].append(m)

    resolved_metrics = {}
    for (metric_name, period), entries in metric_groups.items():
        conflict = conflict_map.get((metric_name, period))
        resolved = resolve_metric(metric_name, entries, conflict)
        resolved["conflict"] = resolved.get("conflict_flagged", False)

        # Save to final dict (using canonical metric name as key)
        # If multiple periods exist for one metric, we prioritize "latest"
        if metric_name not in resolved_metrics or period == "latest" or period == "FY":
             resolved_metrics[metric_name] = resolved

    # ── 4. Compute overall quality ──────────────────────────────────────
    # Simple heuristic: average confidence of all resolved metrics
    total_conf = sum(m["confidence"] for m in resolved_metrics.values())
    avg_conf = total_conf / len(resolved_metrics) if resolved_metrics else 0.0

    result = {
        "ticker": ticker,
        "metrics": resolved_metrics,
        "conflicts_detected": conflicts,
        "conflict_narrative": conflict_narrative,
        "synthesis_quality": round(avg_conf, 2),
    }

    logger.info(
        "Synthesis complete: %d metrics resolved, quality=%.2f",
        len(resolved_metrics), result["synthesis_quality"],
    )

    return result
