"""
synthesis/conflict_detector.py
──────────────────────────────
Detects conflicts between metrics from different sources.

CONFLICT THRESHOLD: 5%
Why 5%?
  • GAAP vs non-GAAP revenue differs by 1–3%
  • Transcript rounding introduces 1–2%
  • >5% signals genuine discrepancy, not rounding
"""

import logging
from typing import Any, Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)

CONFLICT_THRESHOLD_PCT = 5.0


def _pct_diff(a: float, b: float) -> float:
    """Symmetric percentage difference. Returns 0.0 if both are zero."""
    denom = max(abs(a), abs(b))
    if denom == 0:
        return 0.0
    return abs(a - b) / denom * 100.0


def detect_conflicts(all_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect conflicts between metrics from different sources.

    Groups by (metric_name, period), computes pairwise % diffs.
    Flags groups where max diff > CONFLICT_THRESHOLD_PCT.

    Args:
        all_metrics: Flat list of metric dicts from extract_metrics().

    Returns:
        List of conflict records with metric, period, values, max_diff_pct, flagged.
    """
    groups: Dict[tuple, List[Dict]] = defaultdict(list)

    for m in all_metrics:
        if m.get("is_qualitative", False):
            continue
        if m.get("value") is None:
            continue
        if not isinstance(m["value"], (int, float)):
            continue
        key = (m["metric_name"], m.get("period", "unknown"))
        groups[key].append(m)

    conflicts = []

    for (metric_name, period), entries in groups.items():
        if len(entries) < 2:
            continue

        # Deduplicate by source
        seen_sources = set()
        unique_entries = []
        for entry in entries:
            if entry["source"] not in seen_sources:
                seen_sources.add(entry["source"])
                unique_entries.append(entry)

        if len(unique_entries) < 2:
            continue

        max_diff = 0.0
        values_list = []
        for entry in unique_entries:
            values_list.append({
                "value": entry["value"],
                "source": entry["source"],
                "raw": entry.get("raw", str(entry["value"])),
            })

        for i in range(len(unique_entries)):
            for j in range(i + 1, len(unique_entries)):
                diff = _pct_diff(unique_entries[i]["value"], unique_entries[j]["value"])
                max_diff = max(max_diff, diff)

        conflict_record = {
            "metric": metric_name,
            "period": period,
            "values": values_list,
            "max_diff_pct": round(max_diff, 2),
            "flagged": max_diff > CONFLICT_THRESHOLD_PCT,
        }
        conflicts.append(conflict_record)

        if conflict_record["flagged"]:
            logger.info(
                "Conflict flagged: %s [%s] — %.2f%% diff",
                metric_name, period, max_diff,
            )

    return conflicts
