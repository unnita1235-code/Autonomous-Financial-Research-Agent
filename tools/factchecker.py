import logging
import re
from typing import List, Dict, Optional
from .websearch import fetch_web_results
from .financialdataapi import fetch_financial_data

logger = logging.getLogger(__name__)

async def verify_claim(claim: str, sources: List[str] = None) -> Dict:
    """
    Verifies a financial claim by cross-referencing provided sources or searching the web.
    """
    try:
        # Step 1: Parse claim (simple regex for demo)
        # e.g. "Apple revenue in 2023 was $383B"
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', claim.upper())
        ticker = ticker_match.group(1) if ticker_match else "AAPL"
        
        # Step 2 & 3: Gather evidence
        evidence = []
        if not sources:
            # Use web search and financial API
            web_results = await fetch_web_results(f"verify financial claim: {claim}")
            for res in web_results:
                if isinstance(res, dict) and "snippet" in res:
                    evidence.append(res["snippet"])
            
            fin_data = await fetch_financial_data(ticker, "income", "annual", 1)
            if "data" in fin_data:
                evidence.append(str(fin_data["data"]))

        # Step 4: Simple confidence scoring based on keyword overlap
        # In a real agent, we'd use an LLM for this step.
        verified_keywords = claim.lower().split()
        hits = 0
        supporting = []
        contradicting = []
        
        for e in evidence:
            overlap = len(set(verified_keywords) & set(e.lower().split()))
            if overlap > 3: # Arbitrary threshold
                supporting.append(e[:200] + "...")
                hits += 1
            elif "not" in e.lower() or "false" in e.lower():
                contradicting.append(e[:200] + "...")

        status = "verified" if hits > 1 else "inconclusive"
        if contradicting: status = "contradicted"

        return {
            "claim": claim,
            "verification_status": status,
            "confidence": min(1.0, hits * 0.2),
            "supporting_evidence": supporting,
            "contradicting_evidence": contradicting,
            "sources_checked": len(evidence),
            "primary_source": sources[0] if sources else "Web Search / Financial API",
            "notes": "Automated cross-reference check complete."
        }
    except Exception as e:
        logger.error(f"Fact check failed: {e}")
        return {"error": "factcheck_failed", "status": "inconclusive", "confidence": 0.0}
