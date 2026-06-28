import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def handle_agent_error(error: Exception, query: str) -> Dict[str, Any]:
    """
    Analyzes agent errors and provides a recovery or fallback response.
    """
    error_msg = str(error)
    logger.error(f"Handling agent error: {error_msg} for query: {query}")
    
    if "rate limit" in error_msg.lower():
        return {
            "status": "error",
            "error_type": "rate_limit_exceeded",
            "message": "We've hit a rate limit with the AI provider. Please try again in a few minutes.",
            "retry_recommended": True
        }
    
    if "context_length_exceeded" in error_msg.lower():
        return {
            "status": "error",
            "error_type": "context_window_exceeded",
            "message": "The research task became too large for the current model. Try a more specific query.",
            "retry_recommended": False
        }

    return {
        "status": "error",
        "error_type": "internal_error",
        "message": f"An unexpected error occurred: {error_msg}",
        "retry_recommended": True
    }
