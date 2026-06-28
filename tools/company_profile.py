import yfinance as yf
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

async def get_company_profile(ticker: str) -> Dict:
    """
    Fetches company profile and basic market data using yfinance.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            "ticker": ticker.upper(),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap"),
            "description": info.get("longBusinessSummary", "N/A"),
            "ceo": info.get("companyOfficers", [{}])[0].get("name", "N/A") if info.get("companyOfficers") else "N/A",
            "employees": info.get("fullTimeEmployees"),
            "headquarter": f"{info.get('city', '')}, {info.get('state', '')}, {info.get('country', '')}".strip(", "),
            "website": info.get("website", "N/A"),
            "latest_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
            "exchange": info.get("exchange", "N/A"),
            "currency": info.get("currency", "N/A"),
            "profile_fetched_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Company profile fetch failed for {ticker}: {e}")
        return {"error": "company_profile_failed"}
