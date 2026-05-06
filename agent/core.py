import logging
from typing import Dict, Any, Optional
from agents.react_loop import run_agent
from agents.llm_client import LLMClient
from tools import TOOL_REGISTRY
from .errorhandler import handle_agent_error
from .circuitbreaker import CircuitBreaker
from .queryanalyzer import QueryAnalyzer
from .disambiguation import resolve_ambiguity, extract_potential_tickers
from security.prompt_injection_shield import shield
from memory.episodic import EpisodicMemory

logger = logging.getLogger(__name__)
cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

class FinancialAgent:
    """
    High-level wrapper for the autonomous financial research agent.
    Integrates query analysis, disambiguation, and the 3-layer memory system.
    """
    def __init__(self, model_name: Optional[str] = None):
        self.llm_client = LLMClient(model=model_name)
        self.analyzer = QueryAnalyzer()
        self.episodic_memory = EpisodicMemory()

    async def execute_research(self, query: str, vector_store: Optional[Any] = None) -> Dict[str, Any]:
        """
        Executes a research task with 3-layer memory integration.
        """
        if not cb.can_execute():
            return {"status": "error", "message": "Circuit breaker is open. System cooling down."}

        # Security Check: Prompt Injection
        if not shield.is_safe(query):
            return {"status": "error", "message": "Security violation: Potential prompt injection detected."}

        try:
            # 1. Analyze Query
            analysis = await self.analyzer.analyze(query)
            
            # 2. Handle Ambiguity
            if analysis.get("is_ambiguous"):
                potential = extract_potential_tickers(query)
                query = await resolve_ambiguity(query, potential)

            # 3. Retrieve Layer 3 (Episodic) Context
            episodic_context = self.episodic_memory.get_relevant_lessons(query)
            logger.info(f"Retrieved episodic context: {episodic_context[:100]}...")

            # 4. Run ReAct Loop
            logger.info(f"Executing agent loop for: {query}")
            result = await run_agent(
                query=query,
                tool_registry=TOOL_REGISTRY,
                llm_client=self.llm_client,
                vector_store=vector_store,
                episodic_context=episodic_context
            )
            
            # 5. Save Episode to Layer 3
            if result.get("status") == "success":
                self.episodic_memory.save_episode(
                    query=query,
                    strategy=result.get("tools_used", []),
                    outcome=result.get("summary", "Success"),
                    lessons=result.get("lessons", "Standard path successful.")
                )

            cb.record_success()
            return result

        except Exception as e:
            cb.record_failure()
            logger.error(f"FinancialAgent execution failed: {e}", exc_info=True)
            return await handle_agent_error(e, query)
