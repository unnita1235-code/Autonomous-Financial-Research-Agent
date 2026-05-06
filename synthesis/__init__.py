"""
synthesis/__init__.py
─────────────────────
Public API for the synthesis engine.

Usage:
    from synthesis import synthesize
    result = synthesize(agent_memory)
"""

from .engine import synthesize
from .normalizer import normalize_value
from .extractor import extract_metrics
from .conflict_detector import detect_conflicts
from .resolver import resolve_metric
from .narrative import generate_conflict_narrative

__all__ = [
    "synthesize",
    "normalize_value",
    "extract_metrics",
    "detect_conflicts",
    "resolve_metric",
    "generate_conflict_narrative",
]
