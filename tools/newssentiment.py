import logging
from typing import Dict, List
from .news_tool import fetch_news_async

logger = logging.getLogger(__name__)

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    analyzer = SentimentIntensityAnalyzer()
except ImportError:
    try:
        import nltk
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        # Try to download if not present
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            nltk.download('vader_lexicon')
        analyzer = SentimentIntensityAnalyzer()
    except ImportError:
        logger.warning("VADER analyzer not found. Falling back to simple sentiment logic.")
        analyzer = None

def get_vader_sentiment(text: str) -> float:
    """Helper to get compound score from VADER."""
    if not analyzer:
        # Fallback to a very basic logic if VADER is missing
        return 0.0
    scores = analyzer.polarity_scores(text)
    return scores['compound']

def score_to_label(score: float) -> str:
    if score >= 0.5: return "very_positive"
    if score >= 0.05: return "positive"
    if score <= -0.5: return "very_negative"
    if score <= -0.05: return "negative"
    return "neutral"

async def analyze_sentiment(query: str, num_articles: int = 10, lookback_days: int = 7) -> Dict:
    """
    Analyzes sentiment of news articles related to the query.
    """
    try:
        # Step 1: Fetch articles (Reusing existing tool)
        # Note: fetch_news_async expects ticker, but it uses it as a query 'q' in NewsAPI
        news_data = await fetch_news_async(query, days_back=lookback_days)
        
        if news_data.get("error"):
            return {"error": f"news_fetch_failed: {news_data['error']}"}

        headlines = news_data.get("data", {}).get("headlines", [])
        if not headlines:
            return {"error": "no_articles_found", "fallback_score": 0.0}

        # Step 2: Analyze sentiment
        article_level = []
        total_compound = 0.0
        
        # Limit to num_articles
        target_articles = headlines[:num_articles]
        
        for article in target_articles:
            title = article.get("title", "")
            score = get_vader_sentiment(title)
            total_compound += score
            article_level.append({
                "title": title,
                "url": article.get("url", "N/A"),
                "sentiment": score_to_label(score),
                "compound": round(score, 4)
            })

        avg_compound = total_compound / len(article_level) if article_level else 0.0
        
        return {
            "query": query,
            "articles_analyzed": len(article_level),
            "overall_sentiment": score_to_label(avg_compound),
            "compound_score": round(avg_compound, 4),
            "article_level": article_level,
            "lookback_days": lookback_days
        }
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        return {"error": "sentiment_analysis_failed", "fallback_score": 0.0}
