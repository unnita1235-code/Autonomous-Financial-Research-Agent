"""
Tool-level fallback chains for the Financial Research Agent.
When a primary data tool fails, the system tries alternative tools in priority order.
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Each primary tool maps to ordered fallback alternatives
FALLBACK_CHAINS: Dict[str, List[str]] = {
    "sec": ["financial_data", "websearch", "vector_search"],
    "news": ["websearch", "vector_search"],
    "transcript": ["websearch", "vector_search"],
    "financial_data": ["sec", "websearch", "calculate"],
    "sentiment": ["websearch", "calculate"],
    "profile": ["financial_data", "websearch", "vector_search"],
    "peer_comparison": ["financial_data", "websearch", "calculate"],
    "websearch": ["news", "vector_search"],
    "fact_check": ["websearch", "sec", "vector_search"],
    "calculate": ["financial_data", "websearch"],
    "vector_search": ["websearch"],
    "report_gen": [],
}


async def execute_with_fallback(
    primary_tool: str,
    query: str,
    tool_registry: dict,
    circuit_breaker=None
) -> Dict[str, Any]:
    """
    Execute a tool with automatic fallback to alternatives on failure.
    
    Returns:
        dict with keys:
            - "data": the tool result (or None if all failed)
            - "metadata": dict with primary_tool, tool_used, fallback_depth, errors
    """
    errors = []
    chain = [primary_tool] + FALLBACK_CHAINS.get(primary_tool, [])
    
    for depth, tool_name in enumerate(chain):
        if tool_name not in tool_registry:
            errors.append({"tool": tool_name, "error": "not_registered"})
            continue
            
        try:
            # Check circuit breaker
            if circuit_breaker and hasattr(circuit_breaker, 'is_open'):
                if circuit_breaker.is_open(tool_name):
                    errors.append({"tool": tool_name, "error": "circuit_breaker_open"})
                    logger.warning(f"Circuit breaker open for {tool_name}, skipping")
                    continue
            
            # Execute the tool
            tool_func = tool_registry[tool_name]
            if callable(tool_func):
                result = await tool_func(query) if asyncio.iscoroutinefunction(tool_func) else tool_func(query)
            elif hasattr(tool_func, 'execute'):
                result = await tool_func.execute(query)
            elif hasattr(tool_func, 'run'):
                result = tool_func.run(query)
            else:
                result = tool_func(query)
            
            # Check for empty results
            if result is None or (isinstance(result, dict) and not result.get("data")):
                errors.append({"tool": tool_name, "error": "empty_result"})
                logger.info(f"Tool {tool_name} returned empty, trying fallback")
                continue
            
            if depth > 0:
                logger.info(f"Fallback success: {primary_tool} -> {tool_name} (depth={depth})")
            
            return {
                "data": result,
                "metadata": {
                    "primary_tool": primary_tool,
                    "tool_used": tool_name,
                    "fallback_depth": depth,
                    "used_fallback": depth > 0,
                    "errors_encountered": errors
                }
            }
            
        except Exception as e:
            error_info = {
                "tool": tool_name,
                "error": str(e),
                "error_type": type(e).__name__
            }
            errors.append(error_info)
            logger.error(f"Tool {tool_name} failed: {type(e).__name__}: {e}")
            
            # Record failure in circuit breaker
            if circuit_breaker and hasattr(circuit_breaker, 'record_failure'):
                circuit_breaker.record_failure(tool_name)
            continue
    
    # All tools failed
    logger.error(f"All fallbacks exhausted for {primary_tool}: {errors}")
    return {
        "data": None,
        "metadata": {
            "primary_tool": primary_tool,
            "tool_used": None,
            "fallback_depth": len(chain),
            "used_fallback": True,
            "all_failed": True,
            "errors_encountered": errors
        }
    }


def get_fallback_chain(tool_name: str) -> List[str]:
    """Return the fallback chain for a given tool."""
    return [tool_name] + FALLBACK_CHAINS.get(tool_name, [])
