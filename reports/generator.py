"""
reports/generator.py
────────────────────
Main report orchestrator.

Calls all 6 section generators, renders Jinja2 template,
and returns both a structured dict and a Markdown string.

This module is the single entry point for report generation.
The output dict is designed to be:
  1. Served via GET /report/{id} (JSON API)
  2. Persisted to PostgreSQL via db_writer.save_report()
  3. Rendered in the frontend via the markdown field
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader

from .section_generators import (
    generate_executive_summary,
    generate_financial_section,
    generate_management_insights,
    generate_risk_section,
    generate_conflicts_section,
    generate_verdict,
)

logger = logging.getLogger(__name__)

# ── Template setup ──────────────────────────────────────────────────────
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_TEMPLATE_NAME = "report.md.j2"


def _load_template():
    """Load the Jinja2 report template from the templates directory."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template(_TEMPLATE_NAME)


def generate_report(
    query: str,
    ticker: str,
    synthesis: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Generate a complete financial research report.

    Orchestrates all 6 section generators, renders Markdown via Jinja2,
    and returns a structured dict ready for API serving and DB persistence.

    Args:
        query:      The original user research query.
        ticker:     Stock ticker symbol (e.g. "AAPL").
        synthesis:  The full output dict from synthesis.synthesize().
        llm_client: Optional LLM client for narrative sections.
                    If None, all sections fall back to deterministic output.

    Returns:
        Report dict with keys:
            report_id, ticker, query, created_at, sections,
            markdown, synthesis_quality, status
    """
    report_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Generating report: id=%s, ticker=%s, query=%s",
        report_id, ticker, query[:50],
    )

    # ── 1. Generate all sections ────────────────────────────────────────
    sections = {}

    # Section 1: Executive Summary (LLM)
    try:
        sections["executive_summary"] = generate_executive_summary(synthesis, llm_client)
    except Exception as exc:
        logger.error("Executive summary generation failed: %s", exc)
        sections["executive_summary"] = {
            "content": "Executive summary generation failed.",
            "data_quality": "low",
        }

    # Section 2: Financial Metrics (deterministic)
    try:
        sections["financial_metrics"] = generate_financial_section(synthesis)
    except Exception as exc:
        logger.error("Financial section generation failed: %s", exc)
        sections["financial_metrics"] = {
            "content": "Financial metrics generation failed.",
            "rows": [],
            "data_quality": "low",
        }

    # Section 3: Management Insights (LLM)
    try:
        sections["management_insights"] = generate_management_insights(synthesis, llm_client)
    except Exception as exc:
        logger.error("Management insights generation failed: %s", exc)
        sections["management_insights"] = {
            "content": "Management insights generation failed.",
            "data_quality": "low",
        }

    # Section 4: Risk Assessment (LLM)
    try:
        sections["risk_assessment"] = generate_risk_section(synthesis, llm_client)
    except Exception as exc:
        logger.error("Risk section generation failed: %s", exc)
        sections["risk_assessment"] = {
            "content": "Risk assessment generation failed.",
            "data_quality": "low",
        }

    # Section 5: Data Conflicts (deterministic)
    try:
        sections["data_conflicts"] = generate_conflicts_section(synthesis)
    except Exception as exc:
        logger.error("Conflicts section generation failed: %s", exc)
        sections["data_conflicts"] = {
            "content": "Conflicts section generation failed.",
            "conflict_items": [],
            "narrative": None,
            "data_quality": "low",
        }

    # Section 6: Final Verdict (deterministic)
    try:
        sections["final_verdict"] = generate_verdict(synthesis)
    except Exception as exc:
        logger.error("Verdict generation failed: %s", exc)
        sections["final_verdict"] = {
            "content": "Verdict generation failed.",
            "signal": "Insufficient Data",
            "reason": "Verdict generation encountered an error.",
            "data_quality": "low",
            "confidence": "0%",
        }

    # ── 2. Render Markdown via Jinja2 ───────────────────────────────────
    synthesis_quality = synthesis.get("synthesis_quality", 0.0)
    markdown = ""

    try:
        template = _load_template()
        markdown = template.render(
            ticker=ticker,
            query=query,
            report_id=report_id,
            report_date=created_at,
            synthesis_quality=synthesis_quality,
            sections=sections,
            conflicts=synthesis.get("conflicts_detected", []),
        )
    except Exception as exc:
        logger.error("Jinja2 rendering failed: %s", exc)
        markdown = f"# Report Generation Error\n\nTemplate rendering failed: {exc}"

    # ── 3. Assemble output dict ─────────────────────────────────────────
    report = {
        "report_id": report_id,
        "ticker": ticker,
        "query": query,
        "created_at": created_at,
        "sections": sections,
        "markdown": markdown,
        "synthesis_quality": synthesis_quality,
        "status": "complete",
    }

    logger.info(
        "Report generated: id=%s, ticker=%s, quality=%.2f, status=%s",
        report_id, ticker, synthesis_quality, report["status"],
    )

    return report
