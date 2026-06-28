"""
reports/__init__.py
───────────────────
Public API for the report generator.

Usage:
    from reports import generate_report, save_report, compute_verdict

    report = generate_report(query, ticker, synthesis, llm_client)
    save_report(report, db_engine)
"""

from .generator import generate_report
from .db_writer import save_report, save_findings
from .verdict_logic import compute_verdict

__all__ = [
    "generate_report",
    "save_report",
    "save_findings",
    "compute_verdict",
]
