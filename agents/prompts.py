"""
agents/prompts.py
─────────────────
System and user prompt templates for the ReAct agent loop.

The LLM is constrained to produce ONLY valid JSON on every turn.
We inject the current working memory into the user prompt so the
LLM can reason about what data it already has and what is missing.
"""

import json
from typing import List, Dict, Any

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
You are a financial research agent.  Your job is to gather data about a \
company or financial topic by calling tools, then signal when you have \
enough information to produce a comprehensive analysis.

### Available tools
| name         | description                                  | required args                        |
|------------- |----------------------------------------------|--------------------------------------|
| sec          | SEC EDGAR financial facts (revenue, EPS …)   | ticker: str                          |
| transcript   | Earnings-call transcript with sentiment      | ticker: str, quarters_back: int      |
| news         | Recent news headlines + sentiment score       | ticker: str, days_back: int (opt)    |

### Output format — STRICT JSON only
You MUST respond with a single JSON object matching this schema.  \
Do NOT wrap it in markdown code fences.  Do NOT add any text before or after.

{
  "thought":     "<your reasoning about current state>",
  "action":      "tool" | "done",
  "tool_name":   "<tool name from table above, or null if action is done>",
  "tool_args":   {<keyword arguments for the tool, or null if action is done>},
  "confidence":  <float 0.0-1.0, how confident you are this step is useful>
}

### Rules
1. Call ONE tool per turn.  Never call multiple.
2. Once you believe you have gathered sufficient data, set action to "done".
3. Do NOT hallucinate data — only reference data that was returned by tools.
4. If a tool returned an error, note it in your thought and decide whether \
   to retry with different args or move on.
5. Keep your "thought" concise — under 120 words.
"""


# ── User prompt builder ─────────────────────────────────────────────────────
def build_user_prompt(query: str, memory: List[Dict[str, Any]]) -> str:
    """
    Builds the per-iteration user prompt that injects the research query
    and the accumulated working memory into the conversation.

    Args:
        query:  The original research question from the user.
        memory: A list of dicts — each entry is one prior iteration's
                result containing the LLM decision + tool output.

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

    return (
        f"Research query: {query}\n\n"
        f"{memory_block}\n\n"
        f"Decide your next action.  Respond with JSON only."
    )
