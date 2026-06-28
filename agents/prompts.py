"""
agents/prompts.py
─────────────────
System and user prompt templates for the ReAct agent loop.

The LLM is constrained to produce ONLY valid JSON on every turn.
We inject the current working memory into the user prompt so the
LLM can reason about what data it already has and what is missing.
"""

import json
from typing import List, Dict, Any, Optional

# ── Approximate token budget ────────────────────────────────────────────────
# We cap the serialised memory blob at ~3 000 tokens (~12 000 chars at the
# 1:4 char-to-token heuristic).  This keeps total prompt size well under 8k
# even after adding the system prompt + instructions, leaving ~4k headroom
# for the LLM's JSON response on models with 8k-16k context windows.
# For GPT-4o / Claude Sonnet this is extremely conservative — they support
# 128k+ context — but keeping prompts lean is a best-practice for latency
# and cost control.
_MEMORY_CHAR_LIMIT = 12_000  # ≈ 3 000 tokens


# ── System prompt ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an autonomous financial research agent. Your goal is to gather enough data to produce a complete financial analysis, then stop.

AVAILABLE TOOLS:
| name            | purpose                             | key args                                                |
|-----------------|-------------------------------------|---------------------------------------------------------|
| sec             | SEC EDGAR filings (revenue, EPS)    | ticker: str                                             |
| news            | Recent headlines + sentiment score  | ticker: str, days_back: int                             |
| financial_data  | Ratios, income, balance sheet       | ticker: str, statement_type: str, period: str           |
| transcript      | Earnings call transcripts           | ticker: str, quarters_back: int                         |
| web_search      | Web search for any financial topic  | query: str                                              |
| sentiment       | Sentiment score from text/ticker    | query: str                                              |
| profile         | Company sector, market cap          | ticker: str                                             |
| peer_comparison | Industry benchmark comparison       | ticker: str, num_peers: int                             |
| calculate       | Financial ratio calculations        | calculation_type: str, inputs: dict                     |
| vector_search   | Search past research memory         | query: str, top_k: int                                  |
| fact_check      | Verify a specific financial claim   | claim: str                                              |

STOPPING RULES — set action="done" when ANY of these conditions is true:
1. You have revenue AND net_income AND EPS data from at least one source
2. You have called 3 or more different tools successfully
3. You have tried the same tool twice with the same ticker and it failed both times

LOOP RULES:
- Never call the same tool with identical arguments twice in a row
- If a tool returns an error, switch to a different tool on the next iteration
- You have a maximum of 8 iterations — plan from the start

OUTPUT FORMAT — respond ONLY with a single valid JSON object. No markdown, no explanation, no text before or after:
{
  "thought": "<your reasoning, under 60 words>",
  "action": "tool" or "done",
  "tool_name": "<tool name from table above, or null if done>",
  "tool_args": {"key": "value"},
  "confidence": 0.0
}
"""


# ── User prompt builder ─────────────────────────────────────────────────────
def build_user_prompt(query: str, memory: List[Dict[str, Any]], episodic_guidance: Optional[str] = None) -> str:
    """
    Builds the per-iteration user prompt that injects the research query,
    accumulated working memory, and episodic learning into the conversation.

    Args:
        query:  The original research question from the user.
        memory: A list of dicts — each entry is one prior iteration's
                result containing the LLM decision + tool output.
        episodic_guidance: Optional string containing lessons and metrics from past episodes.

    Returns:
        A formatted string ready to be sent as the user message.
    """
    # ── Serialise and truncate memory ────────────────────────────────────
    if memory:
        memory_json = json.dumps(memory, default=str, ensure_ascii=False)
        if len(memory_json) > _MEMORY_CHAR_LIMIT:
            # Truncate oldest entries first — keep the most recent context
            truncated = list(memory)
            while len(json.dumps(truncated, default=str)) > _MEMORY_CHAR_LIMIT and len(truncated) > 1:
                truncated.pop(0)
            memory_json = json.dumps(truncated, default=str, ensure_ascii=False)
            # If a single entry still exceeds the limit, hard-truncate
            if len(memory_json) > _MEMORY_CHAR_LIMIT:
                memory_json = memory_json[:_MEMORY_CHAR_LIMIT] + "…[truncated]"
        memory_block = f"Working memory (previous tool results):\n{memory_json}"
    else:
        memory_block = "Working memory: empty — no tools have been called yet."

    prompt_parts = []
    if episodic_guidance:
        prompt_parts.append(episodic_guidance)
    
    prompt_parts.append(f"Research query: {query}")
    prompt_parts.append(memory_block)
    prompt_parts.append("Decide your next action.  Respond with JSON only.")

    return "\n\n".join(prompt_parts)
