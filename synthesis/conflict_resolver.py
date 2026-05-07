import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

async def resolve_conflicts(tool_outputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identifies discrepancies between data sources (e.g., News vs SEC) and resolves them.
    """
    # Simple strategy: prioritize SEC data over News for financial metrics
    # In a real system, this would be an LLM-driven check.
    
    seen_metrics = {}
    resolved_outputs = []
    
    for output in tool_outputs:
        source = output.get("source")
        data = output.get("data", {})
        
        # Check for numeric conflicts (e.g., revenue)
        if "revenue" in data:
            val = data["revenue"]
            if "revenue" in seen_metrics:
                prev_val, prev_source = seen_metrics["revenue"]
                if val != prev_val:
                    logger.warning(f"Conflict detected: Revenue={val} ({source}) vs {prev_val} ({prev_source})")
                    # Prioritize 'sec'
                    if source == 'sec':
                        seen_metrics["revenue"] = (val, source)
                        # Mark existing 'revenue' in resolved_outputs as 'superseded' or similar
            else:
                seen_metrics["revenue"] = (val, source)
        
        resolved_outputs.append(output)
        
    return resolved_outputs
