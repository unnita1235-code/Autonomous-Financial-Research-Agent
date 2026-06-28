import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

async def build_narrative(tool_outputs: List[Dict[str, Any]], query: str) -> Dict[str, str]:
    """
    Organizes tool outputs into logical sections for the final report.
    """
    sections = {
        "Executive Summary": "",
        "Financial Performance": "",
        "Market Sentiment": "",
        "Risk Analysis": "",
        "Conclusion": ""
    }
    
    for output in tool_outputs:
        source = output.get("source")
        data = str(output.get("data", ""))
        
        if source == "sec":
            sections["Financial Performance"] += f"\n- SEC Data: {data}"
        elif source == "news":
            sections["Market Sentiment"] += f"\n- News Summary: {data}"
        elif source == "transcript":
            sections["Executive Summary"] += f"\n- Earnings Call Insights: {data}"
        else:
            sections["Risk Analysis"] += f"\n- Additional Data ({source}): {data}"
            
    return sections


def generate_conflict_narrative(
    conflicts: List[Dict[str, Any]],
    llm_client: Any = None,
) -> str:
    """
    Produce a short narrative describing resolved metric conflicts.
    Uses the LLM when provided; otherwise returns a deterministic fallback.
    """
    if not conflicts:
        return "No conflicts detected in synthesized metrics."

    if llm_client is not None:
        try:
            lines = []
            for c in conflicts:
                metric = c.get("metric", "unknown")
                period = c.get("period", "")
                pct = c.get("max_diff_pct", 0)
                lines.append(f"- {metric} ({period}): {pct}% variance across sources")
            prompt = (
                "Summarize these financial data conflicts in 2-3 sentences, "
                "mentioning GAAP reporting where relevant:\n" + "\n".join(lines)
            )
            reply = llm_client.chat(
                [
                    {"role": "system", "content": "You are a financial analyst."},
                    {"role": "user", "content": prompt},
                ]
            )
            if reply and reply.strip():
                return reply.strip()
        except Exception as exc:
            logger.warning("LLM conflict narrative failed, using fallback: %s", exc)

    parts = []
    for c in conflicts:
        metric = c.get("metric", "metric")
        period = c.get("period", "")
        pct = c.get("max_diff_pct", 0)
        parts.append(
            f"A conflict was detected for {metric} ({period}) with up to {pct}% "
            "variance between sources; SEC GAAP filings are prioritized when resolving."
        )
    return " ".join(parts)
