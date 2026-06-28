from .sec_tool import fetch_sec_facts_async
from .transcript_tool import fetch_transcript_async
from .news_tool import fetch_news_async
from .web_search import fetch_web_results
from .financial_data_api import fetch_financial_data
from .news_sentiment import analyze_sentiment
from .company_profile import get_company_profile
from .peer_comparison import get_peer_comparison
from .report_generator import generate_report
from .fact_checker import verify_claim
from .calculation_engine import calculate
from .vector_db_search import vector_search

TOOL_REGISTRY = {
    "sec": fetch_sec_facts_async,
    "transcript": fetch_transcript_async,
    "news": fetch_news_async,
    "websearch": fetch_web_results,
    "financial_data": fetch_financial_data,
    "sentiment": analyze_sentiment,
    "profile": get_company_profile,
    "peer_comparison": get_peer_comparison,
    "report_gen": generate_report,
    "fact_check": verify_claim,
    "calculate": calculate,
    "vector_search": vector_search
}

__all__ = ["TOOL_REGISTRY"]
