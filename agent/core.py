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

logger = logging.getLogger(__name__)
cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

class FinancialAgent:
    """
    High-level wrapper for the autonomous financial research agent.
    Integrates query analysis, disambiguation, and the ReAct loop.
    """
    def __init__(self, model_name: Optional[str] = None):
        self.llm_client = LLMClient(model=model_name)
        self.analyzer = QueryAnalyzer()

    async def execute_research(self, query: str, vector_store: Optional[Any] = None) -> Dict[str, Any]:
        """
        Executes a research task with pre-processing and the ReAct loop.
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

            # 3. Run ReAct Loop
            logger.info(f"Executing agent loop for: {query}")
            result = await run_agent(
                query=query,
                tool_registry=TOOL_REGISTRY,
                llm_client=self.llm_client,
                vector_store=vector_store
            )
            
            cb.record_success()
            return result

        except Exception as e:
            cb.record_failure()
            logger.error(f"FinancialAgent execution failed: {e}", exc_info=True)
            return await handle_agent_error(e, query)
