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
