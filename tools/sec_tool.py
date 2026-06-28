import asyncio
import httpx
from datetime import datetime, timezone, date
from typing import Dict, Any, Optional, List

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
USER_AGENT = "FinancialResearchBot/1.0 (contact@example.com)"

# Revenue concepts in priority order (modern → legacy).
# Apple switched from SalesRevenueNet to RevenueFromContractWithCustomerExcludingAssessedTax
# around 2018 when ASC 606 took effect.  Many other filers use Revenues directly.
REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]


def _end_date_to_quarter_label(end_str: str) -> str:
    """
    Derives a human-readable calendar quarter label from the XBRL ``end`` date.

    The SEC ``end`` field is the last day of the fiscal quarter.  We map the
    calendar month of that date to a calendar quarter (Q1-Q4).

    Args:
        end_str: ISO date string, e.g. ``"2026-03-28"``.

    Returns:
        Label like ``"2026-Q1"``.
    """
    d = date.fromisoformat(end_str)
    cal_quarter = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{cal_quarter}"


def _is_single_quarter(entry: Dict) -> bool:
    """
    Returns True when the XBRL entry covers a single fiscal quarter
    (~80–100 days) rather than a cumulative year-to-date period.

    The SEC XBRL data often contains both:
      - A cumulative entry (start=fiscal-year-start → end)
      - A single-quarter entry (start ≈ end − 90 days → end)

    We keep only entries whose duration is ≤ 120 days to avoid
    cumulative / annual figures.
    """
    start_str = entry.get("start")
    end_str = entry.get("end")
    if not start_str or not end_str:
        return False
    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
        duration = (end - start).days
        return duration <= 120  # single quarter is ~90 days
    except (ValueError, TypeError):
        return False


async def ticker_to_cik(ticker: str) -> Optional[str]:
    """
    Resolves a ticker symbol to a zero-padded CIK string.

    Args:
        ticker (str): The company ticker symbol (e.g., 'AAPL').

    Returns:
        Optional[str]: The 10-digit zero-padded CIK string if found, otherwise None.

    Raises:
        httpx.HTTPError: If the SEC tickers endpoint fails.
    """
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient() as client:
        response = await client.get(SEC_TICKERS_URL, headers=headers)
        response.raise_for_status()
        data = response.json()

        for entry in data.values():
            if entry["ticker"] == ticker.upper():
                # SEC CIKs are 10 digits zero-padded
                return str(entry["cik_str"]).zfill(10)
    return None


async def fetch_sec_facts_async(ticker: str) -> Dict[str, Any]:
    """
    Fetches and parses SEC financial facts for a given ticker asynchronously.

    Args:
        ticker (str): The company ticker symbol.

    Returns:
        Dict[str, Any]: Structured data containing revenue, net income, and EPS
                        for the last 3 single-quarter filings.
    """
    result = {
        "source": "sec_edgar",
        "ticker": ticker.upper(),
        "data": {},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "error": None
    }

    try:
        cik = await ticker_to_cik(ticker)
        if not cik:
            raise ValueError(f"Could not resolve CIK for ticker {ticker}")

        url = SEC_FACTS_URL.format(cik=cik)
        headers = {"User-Agent": USER_AGENT}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            facts = response.json()

            def extract_concept(us_gaap_dict: Dict, concept_names: List[str]) -> list:
                """
                Try each concept name in priority order. For the first one found,
                extract the last 3 single-quarter entries with correct period labels.
                """
                for concept_name in concept_names:
                    if concept_name not in us_gaap_dict:
                        continue

                    units = us_gaap_dict[concept_name].get("units", {})
                    if not units:
                        continue

                    # Usually USD or USD/shares
                    primary_unit = list(units.keys())[0]
                    entries = units[primary_unit]

                    # Filter: 10-Q filings only, single-quarter duration only
                    quarterly = [
                        e for e in entries
                        if e.get("form") == "10-Q" and _is_single_quarter(e)
                    ]

                    if not quarterly:
                        continue

                    # Sort by end date descending → most recent first
                    quarterly.sort(key=lambda x: x.get("end", ""), reverse=True)

                    res = []
                    for q in quarterly[:3]:
                        period = _end_date_to_quarter_label(q["end"])
                        res.append({"period": period, "value": q.get("val")})
                    return res

                return []

            us_gaap = facts.get("facts", {}).get("us-gaap", {})

            data = {
                "revenue_quarterly": extract_concept(us_gaap, REVENUE_CONCEPTS),
                "net_income_quarterly": extract_concept(us_gaap, ["NetIncomeLoss"]),
                "eps_quarterly": extract_concept(us_gaap, ["EarningsPerShareBasic"]),
            }

            result["data"] = data

    except Exception as e:
        result["error"] = str(e)

    return result


def fetch_sec_facts(ticker: str) -> Dict[str, Any]:
    """
    Fetches and parses SEC financial facts for a given ticker.

    Args:
        ticker (str): The company ticker symbol.

    Returns:
        Dict[str, Any]: Structured output adhering to the common schema.

    Raises:
        None: Errors are captured in the 'error' field of the return dictionary.
    """
    return asyncio.run(fetch_sec_facts_async(ticker))


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_sec_facts("AAPL"), indent=2))
