import logging
from typing import Dict, Any, List
from agents.llm_client import LLMClient

logger = logging.getLogger(__name__)

class FallbackSystem:
    """
    Manages fallback logic between different LLM providers.
    """
    def __init__(self, primary_model: str = "gpt-4-turbo-preview", fallbacks: List[str] = None):
        self.primary = primary_model
        self.fallbacks = fallbacks or ["claude-3-opus-20240229", "gpt-3.5-turbo"]
        self.client = LLMClient()

    async def call_with_fallback(self, messages: List[Dict[str, str]]) -> str:
        """
        Attempts to call the primary model, then falls back to others in order.
        """
        models_to_try = [self.primary] + self.fallbacks
        
        for model in models_to_try:
            try:
                logger.info(f"Attempting LLM call with model: {model}")
                response = await self.client.complete(messages, model=model)
                return response
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}. Trying next fallback...")
                continue
        
        raise Exception("All models in the fallback chain failed.")
