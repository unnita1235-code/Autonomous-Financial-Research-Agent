import pytest
import json
from unittest.mock import AsyncMock, MagicMock

SEC_RESPONSE = {
    "source": "sec_edgar", "ticker": "AAPL",
    "data": {
        "revenue_quarterly": [{"period": "2024-Q3", "value": 85_777_000_000}],
        "net_income_quarterly": [{"period": "2024-Q3", "value": 21_448_000_000}],
        "eps_quarterly": [{"period": "2024-Q3", "value": 1.40}]
    },
    "fetched_at": "2026-01-01T00:00:00+00:00", "error": None
}

NEWS_RESPONSE = {
    "source": "news", "ticker": "AAPL",
    "data": {"headlines": [{"title": "Apple beats", "published_at": "2024-08-01T00:00:00Z", "sentiment_score": 1.0}],
             "sentiment_score": 0.72, "article_count": 1},
    "fetched_at": "2026-01-01T00:00:00+00:00", "error": None
}

LLM_RESPONSES = [
    json.dumps({"thought": "Start with SEC data", "action": "tool", "tool_name": "sec", "tool_args": {"ticker": "AAPL"}, "confidence": 0.9}),
    json.dumps({"thought": "Get news sentiment", "action": "tool", "tool_name": "news", "tool_args": {"ticker": "AAPL", "days_back": 30}, "confidence": 0.8}),
    json.dumps({"thought": "Have revenue, income, EPS, sentiment. Done.", "action": "done", "tool_name": None, "tool_args": None, "confidence": 1.0}),
]

@pytest.mark.asyncio
async def test_agent_reaches_done():
    from agents.react_loop import run_agent
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = LLM_RESPONSES
    registry = {
        "sec": AsyncMock(return_value=SEC_RESPONSE),
        "news": AsyncMock(return_value=NEWS_RESPONSE),
    }
    result = await run_agent(query="Analyze Apple Q3 2024", tool_registry=registry, llm_client=mock_llm, max_iterations=8)
    assert result["status"] == "done"

@pytest.mark.asyncio
async def test_synthesis_quality():
    from synthesis.engine import synthesize
    memory = [{"tool_output": SEC_RESPONSE}, {"tool_output": NEWS_RESPONSE}]
    result = synthesize(memory)
    assert result["synthesis_quality"] > 0.0
