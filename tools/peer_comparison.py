import logging
from typing import List, Dict, Optional
from .company_profile import get_company_profile
from .financial_data_api import fetch_financial_data

logger = logging.getLogger(__name__)

async def get_peer_comparison(ticker: str, num_peers: int = 4, metrics: List[str] = None) -> Dict:
    """
    Compares the target company with peers in the same sector.
    """
    try:
        # Step 1: Get target profile
        target_profile = await get_company_profile(ticker)
        if "error" in target_profile:
            return target_profile
            
        sector = target_profile.get("sector")
        industry = target_profile.get("industry")
        
        # Step 2: Get target metrics
        target_fin_data = await fetch_financial_data(ticker, "income", "annual", 1)
        target_ratios = target_fin_data.get("derived_ratios", {})
        
        # In a real scenario, we'd search for peers in the same industry.
        # For this tool, we'll use a hardcoded list of common peers or simulate discovery.
        # Peer discovery logic (simplified):
        peer_map = {
            "AAPL": ["MSFT", "GOOGL", "META", "AMZN"],
            "TSLA": ["F", "GM", "RIVN", "LCID"],
            "MSFT": ["AAPL", "GOOGL", "ORCL", "SAP"],
            "NVDA": ["AMD", "INTC", "AVGO", "QCOM"]
        }
        
        peers = peer_map.get(ticker.upper(), ["MSFT", "AAPL", "GOOGL", "AMZN"]) # Default fallback
        peers = [p for p in peers if p != ticker.upper()][:num_peers]
        
        default_metrics = ["revenue", "market_cap", "pe_ratio", "roe", "debt_to_equity", "gross_margin"]
        selected_metrics = metrics or default_metrics
        
        comparison_matrix = {m: [] for m in selected_metrics}
        
        # Add target to matrix
        for m in selected_metrics:
            val = target_ratios.get(m) or target_profile.get(m)
            comparison_matrix[m].append({"ticker": ticker.upper(), "value": val})
            
        # Step 4: Fetch metrics for peers
        for peer in peers:
            peer_profile = await get_company_profile(peer)
            peer_fin = await fetch_financial_data(peer, "income", "annual", 1)
            peer_ratios = peer_fin.get("derived_ratios", {})
            
            for m in selected_metrics:
                val = peer_ratios.get(m) or peer_profile.get(m)
                comparison_matrix[m].append({"ticker": peer.upper(), "value": val})

        # Step 5: Compute rankings
        target_ranking = {}
        for m, results in comparison_matrix.items():
            # Filter out None values for sorting
            valid_results = [r for r in results if r["value"] is not None]
            # Sort descending for most metrics (revenue, margin, roe), ascending for some (debt/equity)
            reverse = True
            if m in ["debt_to_equity", "pe_ratio"]: # Lower is often considered 'better' rank-wise for some investors
                 reverse = False
            
            sorted_results = sorted(valid_results, key=lambda x: x["value"], reverse=reverse)
            
            # Update ranks
            for idx, res in enumerate(sorted_results):
                res["rank"] = idx + 1
                if res["ticker"] == ticker.upper():
                    target_ranking[m] = idx + 1

        insights = f"{ticker.upper()} is being compared against {', '.join(peers)} within the {industry} industry. "
        insights += f"It ranks {target_ranking.get('pe_ratio', 'N/A')} in P/E ratio and {target_ranking.get('roe', 'N/A')} in ROE among its peers."

        return {
            "target_ticker": ticker.upper(),
            "sector": sector,
            "peers": peers,
            "comparison_matrix": comparison_matrix,
            "target_ranking": target_ranking,
            "insights": insights
        }
    except Exception as e:
        logger.error(f"Peer comparison failed: {e}")
        return {"error": "peer_comparison_failed"}
