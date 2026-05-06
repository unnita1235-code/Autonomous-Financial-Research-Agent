import os
import httpx
import logging
from typing import List, Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"

async def fetch_web_results(query: str, num_results: int = 10, date_range: str = None) -> List[Dict]:
    """
    Fetches web search results using the Tavily API.
    
    Returns: List of {url, title, snippet, published_date}
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.error("TAVILY_API_KEY not found in environment")
        return [{"error": "websearch_failed", "fallback": "use_sec_tool"}]

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "smart",
        "include_answer": False,
        "include_images": False,
        "include_raw_content": False,
        "max_results": num_results,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(TAVILY_API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for res in data.get("results", []):
                results.append({
                    "url": res.get("url"),
                    "title": res.get("title"),
                    "snippet": res.get("content"),
                    "published_date": res.get("published_date", "N/A")
                })
            return results
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return [{"error": "websearch_failed", "fallback": "use_sec_tool"}]
