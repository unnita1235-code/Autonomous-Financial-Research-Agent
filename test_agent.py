"""
test_agent.py
─────────────
Integration test for the ReAct agent loop.

Runs a full end-to-end agent session against the real LLM + tool registry
and prints each iteration's thought / action for inspection.

Usage:
    # Ensure your API key is set
    export OPENAI_API_KEY="sk-..."        # or ANTHROPIC_API_KEY
    export LLM_PROVIDER="openai"          # or "anthropic"

    python test_agent.py
"""

import asyncio
import json
import logging
import sys

# ── Configure logging to stdout ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("test_agent")


async def main():
    # ── Import project modules ───────────────────────────────────────────
    from tools import TOOL_REGISTRY
    from agents.llm_client import LLMClient
    from agents.react_loop import run_agent

    logger.info("=" * 60)
    logger.info("  INTEGRATION TEST — ReAct Financial Research Agent")
    logger.info("=" * 60)
    logger.info("Available tools: %s", list(TOOL_REGISTRY.keys()))

    # ── Initialise LLM client ────────────────────────────────────────────
    try:
        llm_client = LLMClient()
    except Exception as exc:
        logger.error("Failed to initialise LLM client: %s", exc)
        logger.error(
            "Make sure OPENAI_API_KEY or ANTHROPIC_API_KEY is set, and "
            "the corresponding provider SDK is installed."
        )
        sys.exit(1)

    # ── Run the agent ────────────────────────────────────────────────────
    query = "Analyze Apple Q3 2024 performance"
    logger.info("Query: %r", query)
    logger.info("-" * 60)

    result = await run_agent(query=query, tool_registry=TOOL_REGISTRY, llm_client=llm_client)

    # ── Pretty-print results ─────────────────────────────────────────────
    logger.info("-" * 60)
    logger.info("RESULT SUMMARY")
    logger.info("-" * 60)
    logger.info("  Status      : %s", result["status"])
    logger.info("  Iterations  : %d", result["iterations"])
    logger.info("  Elapsed     : %.2f s", result["elapsed_sec"])

    for entry in result["memory"]:
        i = entry.get("iteration", "?")
        decision = entry.get("decision", {})
        thought = decision.get("thought", entry.get("error", "N/A"))
        action = decision.get("action", "N/A")
        tool = decision.get("tool_name", "—")
        conf = decision.get("confidence", "—")

        logger.info(
            "  [Iter %s]  action=%-5s  tool=%-12s  confidence=%s  thought=%s",
            i, action, tool, conf, thought[:100],
        )

    # ── Assertions ───────────────────────────────────────────────────────
    assert result["status"] in ("done", "max_iter"), (
        f"Unexpected status: {result['status']}"
    )
    assert isinstance(result["memory"], list), "Memory should be a list"
    assert result["iterations"] >= 1, "Agent should run at least 1 iteration"

    logger.info("-" * 60)
    logger.info("✅  All assertions passed.")
    logger.info("-" * 60)

    # ── Dump full memory to JSON for inspection ──────────────────────────
    output_path = "agent_run_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Full output written to %s", output_path)


if __name__ == "__main__":
    asyncio.run(main())
