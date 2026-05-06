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

MAX ITERATIONS = 8
──────────────────
Why 8?
  • We have 3 core tools.  A typical run calls each tool once (3 iters)
    plus perhaps a retry or a second call with different args (+2).
  • 8 gives ~60% headroom over the happy path while preventing runaway
    loops from rogue LLM behaviour or retry storms.
  • At 8 × $0.005 per call ≈ $0.04 hard ceiling — acceptable for dev/demo.
"""

import json
import logging
import time
import asyncio
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from memory.vector_store import VectorStore

from .prompts import SYSTEM_PROMPT, build_user_prompt

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
    max_iterations: int = MAX_ITERATIONS,
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

    for iteration in range(1, max_iterations + 1):
        logger.info("── Iteration %d / %d ──", iteration, max_iterations)

        # ── 1. Build messages ────────────────────────────────────────────
        user_prompt = build_user_prompt(query, memory)

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

        logger.info("  → Calling tool '%s' with args %s", tool_name, tool_args)

        try:
            tool_result = await tool_registry[tool_name](**tool_args)
        except Exception as exc:
            logger.error("  → Tool '%s' raised: %s", tool_name, exc)
            tool_result = {"error": str(exc)}

        memory.append({
            "iteration": iteration,
            "decision": parsed,
            "tool_output": tool_result,
        })

        # ── Phase 3: Store successful tool results in semantic memory ────
        if vector_store is not None and not tool_result.get("error"):
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
