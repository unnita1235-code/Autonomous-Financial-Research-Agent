import os
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


def _simple_sentiment(text: str) -> str:
    """
    Rule-based sentiment label for a block of transcript text.

    Returns:
        One of ``"positive"``, ``"negative"``, or ``"neutral"``.
    """
    if not text:
        return "neutral"

    lower = text.lower()
    positive_words = {
        "great", "grew", "grow", "growth", "optimistic", "record",
        "strong", "beat", "exceeded", "momentum", "robust", "accelerat",
        "outperform", "upside", "tailwind", "confident", "profit",
        "surge", "increase", "improve", "opportunity",
    }
    negative_words = {
        "headwinds", "decline", "declined", "impacted", "weakness",
        "down", "miss", "missed", "challenge", "pressure", "uncertain",
        "loss", "layoff", "slower", "decelerat", "risk", "concern",
        "shortfall", "restructur",
    }

    pos = sum(1 for w in positive_words if w in lower)
    neg = sum(1 for w in negative_words if w in lower)

    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"


async def fetch_transcript_async(ticker: str, quarters_back: int = 3) -> Dict[str, Any]:
    """
    Fetches earnings call transcript data from the Alpha Vantage
    ``EARNINGS_CALL_TRANSCRIPT`` endpoint.

    Args:
        ticker: Company ticker symbol (e.g. ``"AAPL"``).
        quarters_back: Number of recent quarters to retrieve (max 4).

    Returns:
        Structured dict with transcript segments, speakers, and sentiment.
    """
    result: Dict[str, Any] = {
        "source": "transcript",
        "ticker": ticker.upper(),
        "data": [],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }

    api_key = os.environ.get("ALPHA_VANTAGE_KEY")
    if not api_key:
        result["error"] = "ALPHA_VANTAGE_KEY environment variable is not set."
        return result

    try:
        # Step 1: Get the list of available earnings dates via EARNINGS endpoint
        earnings_params = {
            "function": "EARNINGS",
            "symbol": ticker.upper(),
            "apikey": api_key,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch the earnings calendar to discover available quarters
            earnings_resp = await client.get(ALPHA_VANTAGE_URL, params=earnings_params)
            earnings_resp.raise_for_status()
            earnings_data = earnings_resp.json()

            # Check for API errors / rate limits
            if "Note" in earnings_data:
                result["error"] = f"Alpha Vantage rate limit: {earnings_data['Note']}"
                return result
            if "Error Message" in earnings_data:
                result["error"] = f"Alpha Vantage error: {earnings_data['Error Message']}"
                return result
            if "Information" in earnings_data:
                result["error"] = f"Alpha Vantage info: {earnings_data['Information']}"
                return result

            quarterly_earnings = earnings_data.get("quarterlyEarnings", [])

            if not quarterly_earnings:
                result["error"] = "No quarterly earnings data available from Alpha Vantage."
                return result

            transcript_entries: List[Dict[str, Any]] = []

            # Step 2: For each of the most recent quarters, fetch the transcript
            quarters_to_fetch = quarterly_earnings[:quarters_back]

            for q in quarters_to_fetch:
                fiscal_date = q.get("fiscalDateEnding", "")
                reported_eps = q.get("reportedEPS", "N/A")
                estimated_eps = q.get("estimatedEPS", "N/A")
                surprise = q.get("surprise", "N/A")
                surprise_pct = q.get("surprisePercentage", "N/A")

                # Derive year and quarter from the fiscal date ending
                if not fiscal_date:
                    continue

                try:
                    fd = datetime.strptime(fiscal_date, "%Y-%m-%d")
                    year = fd.year
                    quarter = (fd.month - 1) // 3 + 1
                except (ValueError, TypeError):
                    continue

                # Fetch the actual transcript for this quarter
                transcript_params = {
                    "function": "EARNINGS_CALL_TRANSCRIPT",
                    "symbol": ticker.upper(),
                    "year": str(year),
                    "quarter": str(quarter),
                    "apikey": api_key,
                }

                tx_resp = await client.get(ALPHA_VANTAGE_URL, params=transcript_params)
                tx_resp.raise_for_status()
                tx_data = tx_resp.json()

                # Handle rate-limit or missing data
                if "Note" in tx_data or "Information" in tx_data:
                    # Rate limited — still include earnings data without transcript text
                    transcript_entries.append({
                        "quarter": f"{year}-Q{quarter}",
                        "fiscal_date_ending": fiscal_date,
                        "reported_eps": reported_eps,
                        "estimated_eps": estimated_eps,
                        "surprise": surprise,
                        "surprise_percentage": surprise_pct,
                        "transcript_available": False,
                        "segments": [],
                        "sentiment_label": "neutral",
                    })
                    continue

                # Parse transcript content
                transcript_text = tx_data.get("transcript", "")
                segments: List[Dict[str, str]] = []

                if isinstance(transcript_text, list):
                    # Alpha Vantage sometimes returns a list of speaker segments
                    for seg in transcript_text:
                        speaker = seg.get("speaker", "Unknown")
                        text = seg.get("text", seg.get("content", ""))
                        segments.append({
                            "speaker": speaker,
                            "text": text,
                            "sentiment_label": _simple_sentiment(text),
                        })
                elif isinstance(transcript_text, str) and transcript_text.strip():
                    # Single block of text — treat as one segment
                    segments.append({
                        "speaker": "Full Transcript",
                        "text": transcript_text[:2000],  # Truncate for memory
                        "sentiment_label": _simple_sentiment(transcript_text),
                    })

                overall_sentiment = _simple_sentiment(
                    " ".join(s.get("text", "") for s in segments)
                )

                transcript_entries.append({
                    "quarter": f"{year}-Q{quarter}",
                    "fiscal_date_ending": fiscal_date,
                    "reported_eps": reported_eps,
                    "estimated_eps": estimated_eps,
                    "surprise": surprise,
                    "surprise_percentage": surprise_pct,
                    "transcript_available": len(segments) > 0,
                    "segments": segments,
                    "sentiment_label": overall_sentiment,
                })

            result["data"] = transcript_entries

    except Exception as e:
        result["error"] = str(e)

    return result


def fetch_transcript(ticker: str, quarters_back: int = 3) -> Dict[str, Any]:
    """
    Synchronous wrapper to fetch earnings call transcripts via Alpha Vantage.

    Args:
        ticker: Company ticker symbol.
        quarters_back: Number of quarters to retrieve. Defaults to 3.

    Returns:
        Structured output adhering to the common schema.

    Raises:
        None: Errors are captured in the 'error' field of the return dictionary.
    """
    return asyncio.run(fetch_transcript_async(ticker, quarters_back))


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_transcript("AAPL"), indent=2))
