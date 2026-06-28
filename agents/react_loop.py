"""
agents/react_loop.py
────────────────────
Core ReAct (Reason + Act) agent loop for the financial research agent.

TOKEN BUDGET STRATEGY
─────────────────────
The total prompt per iteration consists of:
  • System prompt           ≈  450 tokens  (fixed)
  • User prompt (query)     ≈   50 tokens  (fixed)
  • Semantic memory hits    ≤  800 tokens  (top-5 × ~160 tokens each)
  • Working memory blob     ≤ 3 000 tokens (capped in prompts.py)
  • LLM response headroom   ≈ 1 024 tokens (max_tokens setting)
                             ──────────────
  Worst-case per call       ≈ 5 324 tokens

Over 8 iterations that is ≈ 43k tokens total (input + output).
At GPT-4o pricing ($2.50 / 1M input, $10 / 1M output) this caps a
single research run at roughly $0.05 — well within budget for a
prototype.  Claude Sonnet 4 is comparable.

SEMANTIC MEMORY (Phase 3)
─────────────────────────
Before the first iteration, we query the FAISS vector store for past
research that is semantically similar to the user's query.  Relevant
hits are injected into the prompt so the LLM can reference prior
findings without re-calling tools for repeat queries.

After each successful tool call, the tool's response text is chunked,
embedded, and stored in the vector index for future retrieval.

MAX_ITERATIONS = 8
──────────────────
Why 8?
  • We have 12 core tools. A typical research run may call multiple tools (e.g., profile, 
    financial_data, peer_comparison) across several iterations.
  • 8 gives sufficient headroom for multi-step reasoning while preventing runaway
    loops or excessive API costs.
  • At 8 × $0.005 per call ≈ $0.04 hard ceiling — acceptable for dev/demo.
"""

import json
import logging
import time
import asyncio
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from memory.vector_store import VectorStore
    from memory.episodic import EpisodicMemory

from .prompts import build_user_prompt

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
| websearch       | General web search for financial information                                | query: str                                                                       |
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

from security.pii_redactor import redact_pii
from agent.fallback_chains import execute_with_fallback

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8


# ── JSON parsing helpers ────────────────────────────────────────────────────

def _parse_llm_json(raw: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse the LLM's response as JSON.

    Handles common failure modes:
      • Leading/trailing whitespace or newlines
      • Markdown code fences (```json ... ```)
    """
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _validate_action(parsed: Dict[str, Any]) -> bool:
    """
    Validate the parsed LLM response matches the expected ReAct schema.
    Returns True if valid, False otherwise.
    """
    required_keys = {"thought", "action", "confidence"}
    if not required_keys.issubset(parsed.keys()):
        return False

    if parsed["action"] not in ("tool", "done"):
        return False

    if parsed["action"] == "tool":
        if not parsed.get("tool_name") or parsed.get("tool_args") is None:
            return False

    if not isinstance(parsed.get("confidence"), (int, float)):
        return False

    return True


# ── Main agent loop ─────────────────────────────────────────────────────────

async def run_agent(
    query: str,
    tool_registry: Dict[str, Callable],
    llm_client: Any,
    vector_store: Optional["VectorStore"] = None,
    episodic_memory: Optional["EpisodicMemory"] = None,
    query_type: str = "generic",
    max_iterations: int = MAX_ITERATIONS,
    circuit_breaker: Optional[Any] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Execute the ReAct agent loop.

    The loop:
      1. Builds a prompt from the query + accumulated memory.
      2. Asks the LLM to decide which tool to call (or to stop).
      3. Dispatches the tool call and stores the result.
      4. Repeats until the LLM says "done" or max iterations is hit.

    Args:
        query:           The user's research question.
        tool_registry:   Dict mapping tool names → callable functions.
        llm_client:      An object with a `.chat(messages) -> str` method.
        vector_store:    Optional VectorStore for semantic memory. When
                         provided, past research is retrieved before tool
                         calls and new results are stored after.
        max_iterations:  Hard cap on loop iterations (default 8).

    Returns:
        {
            "query":       str,
            "iterations":  int,
            "memory":      list[dict],   # full working memory
            "status":      "done" | "max_iter" | "error",
            "elapsed_sec": float,
        }
    """
    memory: List[Dict[str, Any]] = []
    status = "max_iter"
    start_time = time.time()

    logger.info("═══ ReAct agent started ═══  query=%r  max_iter=%d", query, max_iterations)

    # ── Phase 3: Retrieve relevant past research from semantic memory ────
    semantic_context = ""
    if vector_store is not None:
        try:
            past_results = vector_store.retrieve(query, top_k=5)
            if past_results:
                lines = []
                for r in past_results:
                    meta = r["metadata"]
                    source = meta.get("source", "unknown")
                    ticker = meta.get("ticker", "N/A")
                    period = meta.get("period", "N/A")
                    lines.append(
                        f"[score={r['score']:.2f} | source={source} | "
                        f"ticker={ticker} | period={period}]\n{r['text']}"
                    )
                semantic_context = (
                    "RELEVANT PAST RESEARCH (from semantic memory):\n"
                    + "\n---\n".join(lines)
                )
                logger.info(
                    "  Semantic memory: injecting %d past results into prompt",
                    len(past_results),
                )
            else:
                logger.info("  Semantic memory: no relevant past results found")
        except Exception as exc:
            logger.warning("  Semantic memory retrieval failed: %s", exc)

    # ── Layer 3: Retrieve episodic guidance ─────────────────────────────────
    episodic_guidance = ""
    if episodic_memory is not None:
        try:
            summary = episodic_memory.get_summary()
            if summary.get("total_episodes", 0) > 0:
                best_strat = episodic_memory.get_best_strategy(query_type)
                guidance_parts = ["### EPISODIC MEMORY (Layer 3 Learning)"]
                
                if best_strat:
                    guidance_parts.append(f"Recommended Strategy for '{query_type}': {best_strat['strategy']}")
                
                relevant = episodic_memory.get_relevant_episodes(query_type, limit=3)
                if relevant:
                    guidance_parts.append("Lessons from past research:")
                    for ep in relevant:
                        lessons = ep.get("lessons", [])
                        lesson_str = "; ".join(lessons) if isinstance(lessons, list) else str(lessons)
                        guidance_parts.append(f"- Task: {ep['query']} | Lesson: {lesson_str}")
                
                episodic_guidance = "\n".join(guidance_parts)
                logger.info("  Episodic memory: retrieved lessons and strategy guidance")
        except Exception as exc:
            logger.warning("  Episodic memory retrieval failed: %s", exc)

    # Episode tracking state
    tools_used = []
    tools_succeeded = []
    tools_failed = []
    fallbacks_triggered = []
    error_patterns = []

    for iteration in range(1, max_iterations + 1):
        logger.info("── Iteration %d / %d ──", iteration, max_iterations)

        # ── 1. Build messages ────────────────────────────────────────────
        user_prompt = build_user_prompt(query, memory, episodic_guidance=episodic_guidance)

        # Inject semantic memory context before the main prompt
        if semantic_context:
            user_prompt = semantic_context + "\n\n" + user_prompt

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ]

        # ── 2. Call the LLM ──────────────────────────────────────────────
        try:
            raw_response = llm_client.chat(messages)
            await asyncio.sleep(3)
        except Exception as exc:
            logger.error("LLM call failed at iteration %d: %s", iteration, exc)
            memory.append({
                "iteration": iteration,
                "error": f"LLM call failed: {exc}",
            })
            status = "error"
            break

        # ── 3. Parse + validate JSON ─────────────────────────────────────
        parsed = _parse_llm_json(raw_response)

        if parsed is None or not _validate_action(parsed):
            # Retry once with a corrective nudge
            logger.warning(
                "Iteration %d — malformed JSON, retrying.  Raw: %.200s",
                iteration, raw_response,
            )
            retry_messages = messages + [
                {"role": "assistant", "content": raw_response},
                {"role": "user", "content": (
                    "Your output was not valid JSON matching the required schema. "
                    "Please respond again with ONLY the JSON object — no markdown, no prose."
                )},
            ]
            try:
                raw_response = llm_client.chat(retry_messages)
                await asyncio.sleep(3)
            except Exception as exc:
                logger.error("LLM retry call failed at iteration %d: %s", iteration, exc)
                memory.append({
                    "iteration": iteration,
                    "error": f"LLM retry failed: {exc}",
                })
                continue

            parsed = _parse_llm_json(raw_response)
            if parsed is None or not _validate_action(parsed):
                logger.error(
                    "Iteration %d — JSON still invalid after retry.  Skipping.",
                    iteration,
                )
                memory.append({
                    "iteration": iteration,
                    "error": "LLM produced invalid JSON twice",
                    "raw": raw_response[:500],
                })
                continue

        logger.info(
            "  thought   : %s", parsed["thought"][:120],
        )
        logger.info(
            "  action    : %s  tool=%s  confidence=%.2f",
            parsed["action"],
            parsed.get("tool_name"),
            parsed["confidence"],
        )

        # ── 4. Handle "done" ─────────────────────────────────────────────
        if parsed["action"] == "done":
            memory.append({
                "iteration": iteration,
                "decision": parsed,
                "tool_output": None,
            })
            status = "done"
            logger.info("  → Agent decided to stop.  status=done")
            break

        # ── 5. Dispatch tool call ────────────────────────────────────────
        tool_name = parsed["tool_name"]
        tool_args = parsed.get("tool_args") or {}

        if tool_name not in tool_registry:
            logger.warning(
                "  → Unknown tool '%s' — skipping this iteration.", tool_name,
            )
            memory.append({
                "iteration": iteration,
                "decision": parsed,
                "tool_output": {"error": f"Unknown tool: {tool_name}"},
            })
            continue

        logger.info("  → Calling tool '%s' with args %s (via fallback chain)", tool_name, tool_args)
        tools_used.append(tool_name)

        try:
            fallback_result = await execute_with_fallback(
                primary_tool=tool_name,
                tool_args=tool_args,
                tool_registry=tool_registry,
                circuit_breaker=circuit_breaker,
            )
            
            tool_result = fallback_result.get("data")
            fallback_metadata = fallback_result.get("metadata")

            if tool_result is None:
                tool_result = {"error": "All tools in fallback chain failed", "fallback_details": fallback_metadata}
                tools_failed.append(tool_name)
                error_patterns.append(f"{tool_name}_chain_failure")
            else:
                tools_succeeded.append(tool_name)
                # Check if fallbacks were actually used
                if fallback_metadata.get("used_fallback"):
                    fallbacks_triggered.append({
                        "from": tool_name,
                        "to": fallback_metadata.get("tool_used"),
                        "success": True
                    })

            # Redact PII from tool result strings recursively
            def _redact_obj(obj):
                if isinstance(obj, str): return redact_pii(obj)
                if isinstance(obj, dict): return {k: _redact_obj(v) for k, v in obj.items()}
                if isinstance(obj, list): return [_redact_obj(i) for i in obj]
                return obj
            tool_result = _redact_obj(tool_result)
        except Exception as exc:
            logger.error("  → Fallback execution for '%s' raised: %s", tool_name, exc)
            tool_result = {"error": str(exc)}
            fallback_metadata = {"error": str(exc), "primary_tool": tool_name}
            tools_failed.append(tool_name)
            error_patterns.append(f"{tool_name}_exception")

        memory.append({
            "iteration": iteration,
            "decision": parsed,
            "tool_output": tool_result,
            "fallback_metadata": fallback_metadata
        })

        # ── Phase 3: Store successful tool results in semantic memory ────
        is_error = isinstance(tool_result, dict) and tool_result.get("error")
        if vector_store is not None and not is_error:
            try:
                # Build a flat text representation of the tool result for embedding
                store_text = json.dumps(tool_result, default=str, ensure_ascii=False)
                store_meta = {
                    "source": tool_name,
                    "ticker": tool_args.get("ticker", "N/A"),
                    "period": tool_args.get("quarters_back", tool_args.get("days_back", "N/A")),
                    "type": "tool_result",
                }
                vector_store.store(store_text, store_meta)
            except Exception as exc:
                logger.warning(
                    "  Semantic memory store failed for tool '%s': %s",
                    tool_name, exc,
                )

        logger.info(
            "  → Tool '%s' returned.  error=%s",
            tool_name,
            tool_result.get("error"),
        )

    # ── Phase 3: Persist semantic memory to disk ─────────────────────────
    if vector_store is not None:
        try:
            vector_store.save()
            logger.info("  Semantic memory saved to disk")
        except Exception as exc:
            logger.warning("  Semantic memory save failed: %s", exc)

    elapsed = round(time.time() - start_time, 2)
    
    # ── Layer 3: Record the episode ─────────────────────────────────────────
    if episodic_memory is not None:
        try:
            # Simple effectiveness score: 1.0 if done, scaled by iterations
            # If it took more iterations, effectiveness is slightly lower
            effectiveness = 1.0 if status == "done" else 0.5
            effectiveness -= (len(memory) / max_iterations) * 0.2
            effectiveness = max(0.0, round(effectiveness, 2))

            # Strategy is the sequence of tools called
            strategy_str = " -> ".join(tools_used) if tools_used else "direct_answer"

            # Extract final lessons from the last "thought" if status is done
            lessons = []
            if status == "done" and memory:
                final_thought = memory[-1]["decision"].get("thought", "")
                if final_thought:
                    lessons.append(final_thought)
            
            if not lessons:
                lessons = ["Standard research path completed."]

            episode_data = {
                "query_type": query_type,
                "query": query,
                "tools_used": tools_used,
                "tools_succeeded": tools_succeeded,
                "tools_failed": tools_failed,
                "fallbacks_triggered": fallbacks_triggered,
                "strategy": strategy_str,
                "strategy_effectiveness": effectiveness,
                "synthesis_conflicts_found": 0, # Could be expanded with more logic
                "synthesis_conflicts_resolved": 0,
                "total_duration_seconds": elapsed,
                "error_patterns": list(set(error_patterns)),
                "lessons": lessons
            }
            episodic_memory.record_episode(episode_data)
        except Exception as exc:
            logger.warning("  Episodic memory record failed: %s", exc)

    logger.info(
        "═══ ReAct agent finished ═══  status=%s  iterations=%d  elapsed=%.2fs",
        status, len(memory), elapsed,
    )

    return {
        "query": query,
        "iterations": len(memory),
        "memory": memory,
        "status": status,
        "elapsed_sec": elapsed,
    }
