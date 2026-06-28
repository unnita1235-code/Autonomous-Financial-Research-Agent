"""
reports/section_generators.py
─────────────────────────────
Section-by-section report generators.

Three LLM-powered sections (executive summary, management insights,
risk assessment) and three deterministic sections (financial metrics,
data conflicts, final verdict).

LLM STRATEGY:
  Every LLM call uses temperature=0.2 for high factual adherence.
  Every prompt injects the actual synthesised data — the LLM is
  constrained to rewrite facts, NOT generate new claims.
  If the LLM is unavailable, each function produces a deterministic
  fallback so the pipeline never crashes.
"""

import logging
import json
from typing import Any, Dict, List, Optional

from .verdict_logic import compute_verdict, _compute_data_quality

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════

def _avg_confidence(metrics: Dict[str, Dict], keys: Optional[List[str]] = None) -> float:
    """
    Compute average confidence across selected metrics.
    If keys is None, use all metrics.
    """
    if keys:
        values = [
            metrics[k]["confidence"]
            for k in keys
            if k in metrics and "confidence" in metrics[k]
        ]
    else:
        values = [
            m["confidence"]
            for m in metrics.values()
            if isinstance(m, dict) and "confidence" in m
        ]
    return round(sum(values) / len(values), 2) if values else 0.0


def _format_metric_value(value: Any, metric_name: str = "") -> str:
    """Format a metric value for display in the report."""
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        if "sentiment" in metric_name.lower():
            return f"{value:.2f}"
        abs_val = abs(value)
        if abs_val >= 1e12:
            return f"${value / 1e12:,.1f}T"
        elif abs_val >= 1e9:
            return f"${value / 1e9:,.1f}B"
        elif abs_val >= 1e6:
            return f"${value / 1e6:,.1f}M"
        elif abs_val >= 1e3:
            return f"${value / 1e3:,.1f}K"
        elif abs_val < 10:
            return f"${value:,.2f}"
        else:
            return f"${value:,.0f}"
    return str(value)


def _format_source(source: str) -> str:
    """Format source name for display."""
    return source.replace("_", " ").title()


def _llm_chat_text(llm_client: Any, messages: List[Dict[str, str]]) -> str:
    """
    Call LLM with text response format (not JSON).
    Handles the response_format parameter for OpenAI.
    """
    return llm_client.chat(messages, response_format="text")


# ════════════════════════════════════════════════════════════════════════
# Section 1: Executive Summary (LLM-powered)
# ════════════════════════════════════════════════════════════════════════

_EXEC_SUMMARY_PROMPT = """\
Write a 150-word executive summary for a financial research report on {ticker}.
Use ONLY these facts:
{facts}
Mention {num_conflicts} data conflict(s) were detected.
Overall synthesis quality: {quality}%.

Rules:
- Do NOT include any information not listed above.
- Do NOT speculate or add opinions.
- Do NOT exceed 150 words.
- Reference confidence levels where relevant.
- Use professional financial analyst tone."""


def generate_executive_summary(
    synthesis: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Generate a 150-word executive summary.

    LLM-powered with strict fact injection.
    Falls back to template if LLM unavailable.
    """
    metrics = synthesis.get("metrics", {})
    conflicts = synthesis.get("conflicts_detected", [])
    quality = synthesis.get("synthesis_quality", 0.0)
    ticker = synthesis.get("ticker", "UNKNOWN")

    # Build fact list for injection
    facts = []
    for name, data in metrics.items():
        if isinstance(data, dict) and data.get("value") is not None:
            conf_pct = f"{data.get('confidence', 0) * 100:.0f}%"
            source = _format_source(data.get("winning_source", "unknown"))
            val = _format_metric_value(data["value"], name)
            facts.append(f"- {name.replace('_', ' ').title()}: {val} "
                        f"[Source: {source}, Confidence: {conf_pct}]")

    facts_str = "\n".join(facts) if facts else "- No metrics available"

    avg_conf = _avg_confidence(metrics)
    data_quality = _compute_data_quality(avg_conf)

    if llm_client is None:
        # Deterministic fallback
        content = (
            f"Financial analysis of {ticker} based on {len(metrics)} metrics "
            f"with {quality:.0%} overall synthesis quality. "
            f"{len(conflicts)} data conflict(s) detected across sources. "
            f"Key findings: {facts_str}"
        )
        return {"content": content, "data_quality": data_quality}

    prompt = _EXEC_SUMMARY_PROMPT.format(
        ticker=ticker,
        facts=facts_str,
        num_conflicts=len(conflicts),
        quality=f"{quality * 100:.0f}",
    )

    messages = [
        {"role": "system", "content": "You are a senior financial analyst writing a research report."},
        {"role": "user", "content": prompt},
    ]

    try:
        content = _llm_chat_text(llm_client, messages)
        return {"content": content.strip(), "data_quality": data_quality}
    except Exception as exc:
        logger.warning("Executive summary LLM failed: %s — using fallback", exc)
        content = (
            f"Financial analysis of {ticker} based on {len(metrics)} metrics "
            f"with {quality:.0%} overall synthesis quality. "
            f"{len(conflicts)} data conflict(s) detected across sources. "
            f"Key findings: {facts_str}"
        )
        return {"content": content, "data_quality": data_quality}


# ════════════════════════════════════════════════════════════════════════
# Section 2: Financial Metrics (deterministic — NO LLM)
# ════════════════════════════════════════════════════════════════════════

def generate_financial_section(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate the financial metrics table.

    Fully deterministic — builds structured rows from synthesis metrics.
    Returns rows for Jinja2 table rendering, NOT a Markdown string.
    """
    metrics = synthesis.get("metrics", {})
    rows = []

    for name, data in sorted(metrics.items()):
        if not isinstance(data, dict):
            continue
        rows.append({
            "metric": name.replace("_", " ").title(),
            "value": _format_metric_value(data.get("value"), name),
            "source": _format_source(data.get("winning_source", "unknown")),
            "confidence": f"{data.get('confidence', 0) * 100:.0f}%",
        })

    avg_conf = _avg_confidence(metrics)
    data_quality = _compute_data_quality(avg_conf)

    return {
        "content": f"{len(rows)} metrics extracted and reconciled.",
        "rows": rows,
        "data_quality": data_quality,
    }


# ════════════════════════════════════════════════════════════════════════
# Section 3: Management Insights (LLM-powered)
# ════════════════════════════════════════════════════════════════════════

_MGMT_INSIGHTS_PROMPT = """\
Analyze the following management commentary data from an earnings transcript for {ticker}.
Write 2-3 paragraphs of management insights.

Guidance data:
{guidance_data}

Qualitative metrics:
{qualitative_data}

Transcript-sourced numeric data:
{transcript_data}

Rules:
- ONLY use the data provided above. Do NOT add external information.
- Focus on what management communicated about company direction.
- Note confidence levels for any claims.
- If no transcript data is available, state that clearly.
- Professional financial analyst tone."""


def generate_management_insights(
    synthesis: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Generate management insights from transcript data only.

    LLM-powered with transcript data injection.
    Falls back to template if LLM unavailable.
    """
    metrics = synthesis.get("metrics", {})

    # Extract transcript-sourced data
    transcript_metrics = {
        k: v for k, v in metrics.items()
        if isinstance(v, dict) and v.get("winning_source") == "transcript"
    }
    guidance = metrics.get("guidance", {})

    # Build data strings
    guidance_str = "N/A"
    if guidance and guidance.get("value"):
        guidance_str = str(guidance["value"])

    qualitative = []
    transcript_nums = []
    for name, data in transcript_metrics.items():
        val = _format_metric_value(data.get("value"), name)
        conf = f"{data.get('confidence', 0) * 100:.0f}%"
        transcript_nums.append(f"- {name.replace('_', ' ').title()}: {val} [Confidence: {conf}]")

    if guidance.get("value"):
        qualitative.append(f"- Guidance: {guidance['value']}")

    transcript_str = "\n".join(transcript_nums) if transcript_nums else "No numeric data from transcripts."
    qualitative_str = "\n".join(qualitative) if qualitative else "No qualitative data available."

    # Compute data quality from transcript metrics only
    transcript_keys = list(transcript_metrics.keys())
    if "guidance" in metrics:
        transcript_keys.append("guidance")
    avg_conf = _avg_confidence(metrics, transcript_keys) if transcript_keys else 0.0
    data_quality = _compute_data_quality(avg_conf)

    if llm_client is None or (not transcript_metrics and not guidance.get("value")):
        content = "No transcript data available for management insights analysis."
        if transcript_nums:
            content = f"Transcript data available: {transcript_str}"
        return {"content": content, "data_quality": data_quality}

    prompt = _MGMT_INSIGHTS_PROMPT.format(
        ticker=synthesis.get("ticker", "UNKNOWN"),
        guidance_data=guidance_str,
        qualitative_data=qualitative_str,
        transcript_data=transcript_str,
    )

    messages = [
        {"role": "system", "content": "You are a senior financial analyst specialising in earnings call analysis."},
        {"role": "user", "content": prompt},
    ]

    try:
        content = _llm_chat_text(llm_client, messages)
        return {"content": content.strip(), "data_quality": data_quality}
    except Exception as exc:
        logger.warning("Management insights LLM failed: %s — using fallback", exc)
        content = f"Transcript data: {transcript_str}\nGuidance: {guidance_str}"
        return {"content": content, "data_quality": data_quality}


# ════════════════════════════════════════════════════════════════════════
# Section 4: Risk Assessment (LLM-powered)
# ════════════════════════════════════════════════════════════════════════

_RISK_PROMPT = """\
Write a risk assessment section for a financial research report on {ticker}.
Use ONLY the following data:

Sentiment Score: {sentiment_value} (Source: {sentiment_source}, Confidence: {sentiment_conf}%)
Number of data conflicts: {num_conflicts}
Conflict details:
{conflict_details}

Synthesis quality: {quality}%

Rules:
- Identify specific risks based ONLY on the data above.
- Categorize risks as: Data Risk, Market Sentiment Risk, or Conflict Risk.
- Do NOT speculate about risks not evidenced in the data.
- Note confidence levels for each risk factor.
- Professional financial analyst tone.
- Keep to 2-3 paragraphs."""


def generate_risk_section(
    synthesis: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Generate risk assessment from sentiment + conflicts.

    LLM-powered with sentiment and conflict data injection.
    Falls back to template if LLM unavailable.
    """
    metrics = synthesis.get("metrics", {})
    conflicts = synthesis.get("conflicts_detected", [])
    quality = synthesis.get("synthesis_quality", 0.0)

    sentiment = metrics.get("sentiment_score", {})
    sentiment_value = sentiment.get("value", "N/A")
    sentiment_source = _format_source(sentiment.get("winning_source", "unknown"))
    sentiment_conf = f"{sentiment.get('confidence', 0) * 100:.0f}"

    # Build conflict details
    conflict_lines = []
    for c in conflicts:
        values_str = ", ".join(
            f"{v['source']}: {_format_metric_value(v.get('value'), c['metric'])}"
            for v in c.get("values", [])
        )
        conflict_lines.append(
            f"- {c['metric']} ({c.get('period', 'unknown')}): "
            f"{values_str} — {c.get('max_diff_pct', 0):.1f}% variance"
        )
    conflict_str = "\n".join(conflict_lines) if conflict_lines else "No conflicts detected."

    # Data quality based on sentiment + conflict metrics
    risk_keys = ["sentiment_score"]
    avg_conf = _avg_confidence(metrics, risk_keys)
    data_quality = _compute_data_quality(avg_conf)

    if llm_client is None:
        parts = [f"Sentiment score: {sentiment_value} (Confidence: {sentiment_conf}%)."]
        if conflicts:
            parts.append(f"{len(conflicts)} data conflict(s) detected: {conflict_str}")
        else:
            parts.append("No data conflicts detected.")
        parts.append(f"Overall synthesis quality: {quality:.0%}.")
        return {"content": " ".join(parts), "data_quality": data_quality}

    prompt = _RISK_PROMPT.format(
        ticker=synthesis.get("ticker", "UNKNOWN"),
        sentiment_value=sentiment_value,
        sentiment_source=sentiment_source,
        sentiment_conf=sentiment_conf,
        num_conflicts=len(conflicts),
        conflict_details=conflict_str,
        quality=f"{quality * 100:.0f}",
    )

    messages = [
        {"role": "system", "content": "You are a senior financial risk analyst."},
        {"role": "user", "content": prompt},
    ]

    try:
        content = _llm_chat_text(llm_client, messages)
        return {"content": content.strip(), "data_quality": data_quality}
    except Exception as exc:
        logger.warning("Risk section LLM failed: %s — using fallback", exc)
        parts = [f"Sentiment score: {sentiment_value} (Confidence: {sentiment_conf}%)."]
        if conflicts:
            parts.append(f"{len(conflicts)} data conflict(s) detected.")
        return {"content": " ".join(parts), "data_quality": data_quality}


# ════════════════════════════════════════════════════════════════════════
# Section 5: Data Conflicts (deterministic — NO LLM)
# ════════════════════════════════════════════════════════════════════════

def generate_conflicts_section(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate the data conflicts section.

    Fully deterministic — lists detected conflicts with resolution details.
    """
    conflicts = synthesis.get("conflicts_detected", [])
    metrics = synthesis.get("metrics", {})
    narrative = synthesis.get("conflict_narrative")

    items = []
    for c in conflicts:
        metric_name = c.get("metric", "unknown")
        resolved = metrics.get(metric_name, {})

        # Build detail string showing all values
        values_str = " vs ".join(
            f"{_format_source(v['source'])}: {_format_metric_value(v.get('value'), metric_name)}"
            for v in c.get("values", [])
        )
        resolution = ""
        if resolved.get("winning_source"):
            resolution = f" → Resolved: {_format_source(resolved['winning_source'])} prioritised"

        items.append({
            "metric": metric_name.replace("_", " ").title(),
            "period": c.get("period", "unknown"),
            "detail": f"{values_str}{resolution}",
            "diff_pct": c.get("max_diff_pct", 0),
        })

    # Data quality: if there are conflicts, quality is lower
    if conflicts:
        # Use confidence of conflicted metrics
        conflict_keys = [c["metric"] for c in conflicts if c["metric"] in metrics]
        avg_conf = _avg_confidence(metrics, conflict_keys) if conflict_keys else 0.5
    else:
        avg_conf = 1.0  # No conflicts = perfect on this dimension
    data_quality = _compute_data_quality(avg_conf)

    content = (
        f"{len(conflicts)} conflict(s) detected."
        if conflicts
        else "No data conflicts detected across sources."
    )

    return {
        "content": content,
        "conflict_items": items,
        "narrative": narrative,
        "data_quality": data_quality,
    }


# ════════════════════════════════════════════════════════════════════════
# Section 6: Final Verdict (deterministic — NO LLM)
# ════════════════════════════════════════════════════════════════════════

def generate_verdict(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate the final verdict section.

    Delegates to verdict_logic.compute_verdict() — fully deterministic.
    """
    verdict = compute_verdict(synthesis)

    return {
        "content": verdict["reason"],
        "signal": verdict["signal"],
        "reason": verdict["reason"],
        "data_quality": verdict["data_quality"],
        "confidence": f"{verdict['confidence_used']:.0%}",
    }
