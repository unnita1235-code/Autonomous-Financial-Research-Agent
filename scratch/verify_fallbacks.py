import asyncio
import logging
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.fallback_chains import execute_with_fallback
from agent.circuit_breaker import CircuitBreaker

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_fallbacks():
    # Mock tool registry
    async def mock_fail_tool(**kwargs):
        return {"error": "API Error", "code": 500}

    async def mock_success_tool(**kwargs):
        return {"data": "Success result"}

    async def mock_empty_tool(**kwargs):
        return {}

    registry = {
        "sec": mock_fail_tool,
        "financial_data": mock_fail_tool,
        "web_search": mock_success_tool,
        "vector_search": mock_fail_tool,
        "news": mock_empty_tool
    }

    cb = CircuitBreaker(failure_threshold=2)

    logger.info("--- Testing SEC fallback: sec -> financial_data -> web_search ---")
    # sec fails, financial_data fails, web_search succeeds
    result = await execute_with_fallback("sec", {"ticker": "AAPL"}, registry, cb)
    
    print("\nSEC Fallback Result:")
    print(f"Tool used: {result['metadata']['tool_used']}")
    print(f"Fallback depth: {result['metadata']['fallback_depth']}")
    print(f"Used fallback: {result['metadata']['used_fallback']}")
    print(f"Errors: {result['metadata']['errors_encountered']}")

    assert result['metadata']['tool_used'] == "web_search"
    assert result['metadata']['fallback_depth'] == 2
    assert result['metadata']['used_fallback'] is True

    logger.info("\n--- Testing News fallback: news -> web_search ---")
    # news returns empty {}, web_search succeeds
    result = await execute_with_fallback("news", {"ticker": "TSLA"}, registry, cb)
    
    print("\nNews Fallback Result:")
    print(f"Tool used: {result['metadata']['tool_used']}")
    print(f"Fallback depth: {result['metadata']['fallback_depth']}")
    print(f"Errors: {result['metadata']['errors_encountered']}")

    assert result['metadata']['tool_used'] == "web_search"
    assert result['metadata']['fallback_depth'] == 1

    logger.info("\n--- Testing Circuit Breaker ---")
    # After 2 failures of 'sec', circuit should be open
    # 'sec' failed in the first test once.
    # Let's fail 'sec' again.
    await execute_with_fallback("sec", {"ticker": "AAPL"}, registry, cb)
    
    print(f"Is SEC circuit open? {cb.is_open('sec')}")
    assert cb.is_open('sec') is True

    # Now trying 'sec' should skip it immediately
    result = await execute_with_fallback("sec", {"ticker": "AAPL"}, registry, cb)
    print("\nSEC Result with Open Circuit:")
    print(f"First error encountered: {result['metadata']['errors_encountered'][0]['error']}")
    assert result['metadata']['errors_encountered'][0]['error'] == "circuit_breaker_open"

    logger.info("\nVerification Successful!")

if __name__ == "__main__":
    asyncio.run(test_fallbacks())
