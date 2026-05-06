from .sec_tool import fetch_sec_facts_async
from .transcript_tool import fetch_transcript_async
from .news_tool import fetch_news_async

TOOL_REGISTRY = {
    "sec": fetch_sec_facts_async,
    "transcript": fetch_transcript_async,
    "news": fetch_news_async
}

__all__ = ["TOOL_REGISTRY"]
