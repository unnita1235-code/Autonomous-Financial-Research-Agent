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
| name            | description                                                                 | required args                                                                    |
|-----------------|-----------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| sec             | Search SEC EDGAR filings (10-K, 10-Q, 8-K, etc.)                            | ticker: str                                                                      |
| transcript      | Search and retrieve earnings call transcripts                               | ticker: str, quarters_back: int                                                  |
| news            | Search financial news articles                                              | ticker: str, days_back: int (opt)                                                |
| web_search       | General web search for financial information                                | query: str                                                                       |
| financial_data  | Retrieve financial metrics, ratios, and stock prices from APIs              | ticker: str, statement_type: str ("income"|"balance"|"cashflow"), period: str ("annual"|"quarterly") |
| sentiment       | Analyze sentiment of text (positive/negative/neutral with score)            | query: str                                                                       |
| profile         | Get company profile (sector, industry, market cap, description)             | ticker: str                                                                      |
| peer_comparison | Compare a company against industry peers on financial metrics               | ticker: str                                                                      |
| report_gen      | Generate formatted research report sections                                 | template_name: str, sections: dict, sources: list                                |
| fact_check      | Cross-reference claims against known financial data sources                 | claim: str                                                                       |
| calculate       | Perform financial calculations (ratios, growth rates, valuations)            | calculation_type: str, inputs: dict                                              |
| vector_search   | Search the semantic memory (FAISS vector store) for past research           | query: str                                                                       |

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
