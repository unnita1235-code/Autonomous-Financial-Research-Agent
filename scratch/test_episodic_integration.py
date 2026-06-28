import asyncio
import json
import os
import sys
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())

from memory.episodic import EpisodicMemory
from agents.react_loop import run_agent

# Mock LLM Client
class MockLLM:
    def __init__(self):
        self.iteration = 0
    
    def chat(self, messages, **kwargs):
        self.iteration += 1
        if self.iteration == 1:
            return json.dumps({
                "thought": "I need to check SEC filings first.",
                "action": "tool",
                "tool_name": "sec",
                "tool_args": {"ticker": "AAPL"},
                "confidence": 0.9
            })
        # Second turn: finish
        return json.dumps({
            "thought": "I have enough information about AAPL earnings. SEC filings and transcripts confirmed $85.8B revenue.",
            "action": "done",
            "tool_name": None,
            "tool_args": None,
            "confidence": 1.0
        })

# Mock Tool Registry
async def mock_tool(*args, **kwargs):
    return {"data": "mock tool result", "metadata": {"fallback_used": False}}

TOOL_REGISTRY = {
    "sec": mock_tool,
    "transcript": mock_tool
}

async def test_episodic_flow():
    print("Starting episodic memory integration test...")
    
    # Initialize episodic memory with a test path
    test_path = "database/test_episodic_memory.json"
    if os.path.exists(test_path):
        os.remove(test_path)
    
    memory = EpisodicMemory(storage_path=test_path)
    
    # 1. First run (no history)
    print("\n--- First Run (No History) ---")
    query = "Analyze Apple Q3 2024 earnings"
    result = await run_agent(
        query=query,
        tool_registry=TOOL_REGISTRY,
        llm_client=MockLLM(),
        episodic_memory=memory,
        query_type="earnings_analysis",
        max_iterations=2
    )
    
    print(f"Status: {result['status']}")
    
    # Check if file was created
    with open(test_path, 'r') as f:
        data = json.load(f)
        print(f"Recorded Episodes: {len(data)}")
        print(f"Episode ID: {data[0]['episode_id']}")
        print(f"Lessons: {data[0]['lessons']}")

    # 2. Second run (should show reliability/lessons)
    print("\n--- Second Run (With History) ---")
    # We don't actually run the loop again here, we just check what get_relevant_lessons returns
    lessons = memory.get_relevant_lessons(query, query_type="earnings_analysis")
    print("Retrieved Lessons for Prompt:")
    print(lessons)

    if "Tool Reliability" in lessons and "earnings_analysis" in lessons:
        print("\nSUCCESS: Episodic guidance correctly generated.")
    else:
        print("\nFAILURE: Episodic guidance missing metrics.")

    # Cleanup
    if os.path.exists(test_path):
        os.remove(test_path)

if __name__ == "__main__":
    asyncio.run(test_episodic_flow())
