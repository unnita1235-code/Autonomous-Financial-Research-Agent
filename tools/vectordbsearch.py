import time
import logging
from typing import Dict, Any, Optional
from memory.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Singleton instance for the tool
_store = None

def get_store():
    global _store
    if _store is None:
        _store = VectorStore()
    return _store

async def vector_search(query: str, top_k: int = 5, filter_dict: Dict = None) -> Dict:
    """
    Searches the semantic memory for relevant chunks.
    """
    start_time = time.time()
    try:
        store = get_store()
        results = store.retrieve(query, top_k=top_k)
        
        # Apply filters if provided
        if filter_dict:
            filtered = []
            for res in results:
                match = True
                for k, v in filter_dict.items():
                    if res["metadata"].get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(res)
            results = filtered

        return {
            "query": query,
            "results": results,
            "total_hits": len(results),
            "search_time_sec": round(time.time() - start_time, 4)
        }
    except Exception as e:
        logger.error(f"Vector search tool failed: {e}")
        return {
            "query": query,
            "results": [],
            "total_hits": 0,
            "search_time_sec": round(time.time() - start_time, 4),
            "error": str(e)
        }
