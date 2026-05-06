import yfinance as yf
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def fetch_financial_data(ticker: str, statement_type: str, period: str, years: int = 3) -> Dict:
    """
    Fetches financial data and derives key ratios using yfinance.
    statement_type: "income" | "balance" | "cashflow"
    period: "annual" | "quarterly"
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Determine statement fetching
        if statement_type == "income":
            data = stock.income_stmt if period == "annual" else stock.quarterly_income_stmt
        elif statement_type == "balance":
            data = stock.balance_sheet if period == "annual" else stock.quarterly_balance_sheet
        elif statement_type == "cashflow":
            data = stock.cashflow if period == "annual" else stock.quarterly_cashflow
        else:
            return {"error": "invalid_statement_type"}

        # Extract data for specified years
        raw_data = {}
        for col in data.columns[:years]:
            year_str = col.strftime("%Y")
            raw_data[year_str] = data[col].to_dict()

        # Derive 10 key ratios (using latest annual data if possible)
        ratios = {}
        try:
            info = stock.info
            # P/E, P/S, P/B
            ratios["pe_ratio"] = info.get("trailingPE")
            ratios["ps_ratio"] = info.get("priceToSalesTrailing12Months")
            ratios["pb_ratio"] = info.get("priceToBook")
            
            # ROE, ROA
            ratios["roe"] = info.get("returnOnEquity")
            ratios["roa"] = info.get("returnOnAssets")
            
            # Debt/Equity, Current Ratio
            ratios["debt_to_equity"] = info.get("debtToEquity")
            ratios["current_ratio"] = info.get("currentRatio")
            
            # Margins
            ratios["gross_margin"] = info.get("grossMargins")
            ratios["net_margin"] = info.get("profitMargins")
            ratios["operating_margin"] = info.get("operatingMargins")
            
        except Exception as e:
            logger.warning(f"Failed to derive some ratios for {ticker}: {e}")

        return {
            "ticker": ticker,
            "statement_type": statement_type,
            "data": raw_data,
            "derived_ratios": ratios,
            "periods": period,
            "fetched_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Financial data fetch failed for {ticker}: {e}")
        return {"error": "financial_api_failed"}
