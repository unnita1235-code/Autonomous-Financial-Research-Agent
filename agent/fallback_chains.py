"""
Tool-level fallback chains for the Financial Research Agent.
When a primary data tool fails, the system tries alternative tools in priority order.
"""
import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Union

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


def _coerce_tool_args(tool_args: Union[str, Dict[str, Any], None]) -> Dict[str, Any]:
    """Accept legacy query string or full kwargs dict from the ReAct loop."""
    if tool_args is None:
        return {}
    if isinstance(tool_args, str):
        s = tool_args.strip()
        if not s:
            return {}
        # Ticker-like token vs free-text query
        if s.isupper() and len(s) <= 6 and s.isalpha():
            return {"ticker": s}
        return {"query": s}
    return dict(tool_args)


def _normalize_args(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Fill required fields when the LLM omits optional/required kwargs."""
    args = dict(tool_args)
    ticker = args.get("ticker")
    query = args.get("query") or args.get("claim") or ticker

    if tool_name in ("sec", "profile", "peer_comparison", "news", "transcript", "financial_data"):
        if ticker:
            args.setdefault("ticker", ticker)
        elif query and tool_name != "financial_data":
            args.setdefault("ticker", str(query).upper()[:6] if str(query).isupper() else str(query))

    if tool_name == "financial_data":
        args.setdefault("statement_type", "income")
        args.setdefault("period", "quarterly")
        args.setdefault("years", 3)
        if not args.get("ticker") and query:
            args["ticker"] = str(query).upper()

    if tool_name == "transcript":
        args.setdefault("quarters_back", 3)

    if tool_name == "news":
        args.setdefault("days_back", 30)

    if tool_name == "calculate":
        args.setdefault("calculation_type", "pe_ratio")
        args.setdefault("inputs", args.get("inputs") or {})

    if tool_name in ("websearch", "sentiment", "vector_search", "fact_check"):
        if not args.get("query") and query:
            args["query"] = str(query)
        if tool_name == "sentiment":
            args.setdefault("num_articles", 10)
            args.setdefault("lookback_days", 7)
        if tool_name == "vector_search":
            args.setdefault("top_k", 5)

    if tool_name == "peer_comparison":
        args.setdefault("num_peers", 4)

    if tool_name == "fact_check" and not args.get("claim") and query:
        args["claim"] = str(query)

    return args


def _is_failed_result(result: Any) -> bool:
    """True if the tool output should trigger the next fallback in the chain."""
    if result is None:
        return True
    if isinstance(result, list):
        return len(result) == 0
    if isinstance(result, str):
        return not result.strip()
    if isinstance(result, dict):
        if result.get("error"):
            return True
        if "data" in result:
            data = result["data"]
            return data is None or data == {} or data == []
        if "result" in result:
            return False
        return result == {}
    return False


async def _invoke_tool(tool_name: str, tool_func: Callable, tool_args: Dict[str, Any]) -> Any:
    args = _normalize_args(tool_name, tool_args)
    ticker = args.get("ticker") or args.get("query", "")
    query  = args.get("query") or args.get("claim") or ticker

    if tool_name == "sec":
        return await _call(tool_func, ticker or query)

    if tool_name == "financial_data":
        return await _call(
            tool_func,
            ticker or query,
            args.get("statement_type", "income"),
            args.get("period", "quarterly"),
            args.get("years", 3),
        )

    if tool_name == "transcript":
        return await _call(tool_func, ticker or query, args.get("quarters_back", 3))

    if tool_name == "news":
        return await _call(tool_func, ticker or query, args.get("days_back", 30))

    if tool_name in ("websearch", "web_search"):
        return await _call(tool_func, query, args.get("num_results", 10), args.get("date_range"))

    if tool_name == "sentiment":
        return await _call(tool_func, query, args.get("num_articles", 10), args.get("lookback_days", 7))

    if tool_name == "profile":
        return await _call(tool_func, ticker or query)

    if tool_name == "peer_comparison":
        return await _call(tool_func, ticker or query, args.get("num_peers", 4), args.get("metrics"))

    if tool_name == "calculate":
        return await _call(tool_func, args.get("calculation_type", "pe_ratio"), args.get("inputs", {}))

    if tool_name in ("vector_search", "vector_db_search"):
        return await _call(tool_func, query, args.get("top_k", 5), args.get("filter_dict"))

    if tool_name == "fact_check":
        return await _call(tool_func, args.get("claim") or query, args.get("sources"))

    if tool_name == "report_gen":
        return await _call(
            tool_func,
            args.get("template_name", "standard"),
            args.get("sections", {}),
            args.get("sources", []),
        )

    sig = inspect.signature(tool_func)
    bound = {}
    for param_name in sig.parameters:
        if param_name in args:
            bound[param_name] = args[param_name]
        elif param_name in ("query", "claim") and query:
            bound[param_name] = query
        elif param_name == "ticker" and ticker:
            bound[param_name] = ticker
    return await _call(tool_func, **bound)


async def _call(func: Callable, *args, **kwargs):
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return await asyncio.to_thread(lambda: func(*args, **kwargs))


async def execute_with_fallback(
    primary_tool: str,
    tool_args: Union[str, Dict[str, Any], None],
    tool_registry: dict,
    circuit_breaker=None,
) -> Dict[str, Any]:
    """
    Execute a tool with automatic fallback to alternatives on failure.

    Args:
        primary_tool: Tool name from the ReAct loop.
        tool_args: Dict of kwargs from the LLM (or legacy query string).
        tool_registry: TOOL_REGISTRY mapping.
        circuit_breaker: Optional circuit breaker instance.

    Returns:
        dict with keys:
            - "data": the tool result (or None if all failed)
            - "metadata": dict with primary_tool, tool_used, fallback_depth, errors
    """
    errors: List[Dict[str, Any]] = []
    chain = [primary_tool] + FALLBACK_CHAINS.get(primary_tool, [])
    normalized = _coerce_tool_args(tool_args)

    for depth, tool_name in enumerate(chain):
        if tool_name not in tool_registry:
            errors.append({"tool": tool_name, "error": "not_registered"})
            continue

        try:
            if circuit_breaker and hasattr(circuit_breaker, "is_open"):
                if circuit_breaker.is_open(tool_name):
                    errors.append({"tool": tool_name, "error": "circuit_breaker_open"})
                    logger.warning("Circuit breaker open for %s, skipping", tool_name)
                    continue

            tool_func = tool_registry[tool_name]
            result = await _invoke_tool(tool_name, tool_func, normalized)

            if _is_failed_result(result):
                errors.append({"tool": tool_name, "error": "empty_result"})
                logger.info("Tool %s returned empty/error, trying fallback", tool_name)
                continue

            if depth > 0:
                logger.info("Fallback success: %s -> %s (depth=%d)", primary_tool, tool_name, depth)

            return {
                "data": result,
                "metadata": {
                    "primary_tool": primary_tool,
                    "tool_used": tool_name,
                    "fallback_depth": depth,
                    "used_fallback": depth > 0,
                    "errors_encountered": errors,
                },
            }

        except Exception as e:
            error_info = {
                "tool": tool_name,
                "error": str(e),
                "error_type": type(e).__name__,
            }
            errors.append(error_info)
            logger.error("Tool %s failed: %s: %s", tool_name, type(e).__name__, e)

            if circuit_breaker and hasattr(circuit_breaker, "record_failure"):
                circuit_breaker.record_failure(tool_name)
            continue

    logger.error("All fallbacks exhausted for %s: %s", primary_tool, errors)
    return {
        "data": None,
        "metadata": {
            "primary_tool": primary_tool,
            "tool_used": None,
            "fallback_depth": len(chain),
            "used_fallback": True,
            "all_failed": True,
            "errors_encountered": errors,
        },
    }


def get_fallback_chain(tool_name: str) -> List[str]:
    """Return the fallback chain for a given tool."""
    return [tool_name] + FALLBACK_CHAINS.get(tool_name, [])
