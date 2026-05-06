import os
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

NEWS_API_URL = "https://newsapi.org/v2/everything"

def calculate_sentiment(text: str) -> float:
    """
    Calculates a simple sentiment score between -1 and 1 based on financial keywords.
    
    Args:
        text (str): The text to analyze.
        
    Returns:
        float: Sentiment score from -1.0 to 1.0.
    """
    if not text:
        return 0.0
        
    text = text.lower()
    positive_words = {"surge", "jump", "record", "profit", "beat", "up", "bull", "growth", "dividend"}
    negative_words = {"plunge", "drop", "miss", "loss", "down", "bear", "decline", "layoff", "bankrupt"}
    
    words = set(text.split())
    pos_count = len(words.intersection(positive_words))
    neg_count = len(words.intersection(negative_words))
    
    total = pos_count + neg_count
    if total == 0:
        return 0.0
        
    return (pos_count - neg_count) / total

async def fetch_news_async(ticker: str, days_back: int = 30) -> Dict[str, Any]:
    """
    Fetches recent news headlines and extracts sentiment signal using NewsAPI.
    
    Args:
        ticker (str): The company ticker symbol.
        days_back (int): The number of past days to query news for.
        
    Returns:
        Dict[str, Any]: Structured news data with headlines and sentiment score.
    """
    result = {
        "source": "news",
        "ticker": ticker.upper(),
        "data": {},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "error": None
    }
    
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        result["error"] = "NEWS_API_KEY environment variable is not set."
        return result
        
    try:
        from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        params = {
            "q": ticker,
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": api_key,
            "pageSize": 50  # Fetch up to 50 recent articles
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(NEWS_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = data.get("articles", [])
            headlines = []
            total_sentiment = 0.0
            valid_sentiment_count = 0
            
            for article in articles:
                title = article.get("title", "")
                description = article.get("description", "")
                
                # Combine title and description for sentiment analysis
                text_to_analyze = f"{title} {description}"
                score = calculate_sentiment(text_to_analyze)
                
                headlines.append({
                    "title": title,
                    "published_at": article.get("publishedAt"),
                    "sentiment_score": round(score, 2)
                })
                
                total_sentiment += score
            
            avg_sentiment = total_sentiment / len(headlines) if headlines else 0.0
            
            result["data"] = {
                "headlines": headlines,
                "sentiment_score": round(avg_sentiment, 2),
                "article_count": len(headlines)
            }
            
    except Exception as e:
        result["error"] = str(e)
        
    return result

def fetch_news(ticker: str, days_back: int = 30) -> Dict[str, Any]:
    """
    Synchronous wrapper to fetch recent news and extract sentiment.
    
    Args:
        ticker (str): The company ticker symbol.
        days_back (int, optional): Number of past days to query. Defaults to 30.
        
    Returns:
        Dict[str, Any]: Structured output adhering to the common schema.
        
    Raises:
        None: Errors are captured in the 'error' field of the return dictionary.
    """
    return asyncio.run(fetch_news_async(ticker, days_back))

if __name__ == "__main__":
    import json
    print(json.dumps(fetch_news("AAPL"), indent=2))
