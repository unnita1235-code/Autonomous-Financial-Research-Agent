import logging
import json
from typing import Dict, Any, List
from agents.llm_client import LLMClient

logger = logging.getLogger(__name__)

class QueryAnalyzer:
    """
    Analyzes and classifies user queries to optimize research strategy.
    """
    def __init__(self):
        self.client = LLMClient()

    async def analyze(self, query: str) -> Dict[str, Any]:
        """
        Classifies the query into intent, ticker, and required tools.
        """
        prompt = f"""
        Analyze the following financial research query and classify it.
        Return ONLY a JSON object.
        
        Query: "{query}"
        
        JSON Schema:
        {{
          "intent": "company_profile" | "earnings_analysis" | "risk_assessment" | "comparison",
          "ticker": string | null,
          "is_ambiguous": boolean,
          "suggested_tools": string[]
        }}
        """
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.client.chat(messages, response_format="json_object")
            return json.loads(response)
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            # Robust fallback
            return {
                "intent": "earnings_analysis",
                "ticker": None,
                "is_ambiguous": True,
                "suggested_tools": ["web_search", "sec", "transcript"]
            }
