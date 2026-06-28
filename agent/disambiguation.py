import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

async def resolve_ambiguity(query: str, possible_tickers: List[str]) -> str:
    """
    Helps resolve ambiguity in user queries, specifically around tickers.
    """
    if not possible_tickers:
        return query
        
    if len(possible_tickers) == 1:
        return f"{query} (Ticker: {possible_tickers[0]})"
    
    # Simple strategy: append common knowledge or ask for clarification (simulated)
    # In a real UI, this would trigger a user selection
    return f"{query} (Clarification required: Did you mean {', '.join(possible_tickers)}?)"

def extract_potential_tickers(query: str) -> List[str]:
    """Simple extraction of potential ticker-like strings."""
    import re
    return re.findall(r'\b[A-Z]{1,5}\b', query.upper())
