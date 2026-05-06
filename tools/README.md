# Financial Research Agent Tools

This module provides three atomic, stateless Python tools designed for gathering financial data and feeding a ReAct agent loop. The tools have zero external LLM dependencies and prioritize reliability and predictable schema output.

## Included Tools

1. **`sec`** (`sec_tool.py`): Fetches and parses real SEC EDGAR financial filings to extract Revenue, Net Income, and EPS data for the last 3 quarters.
2. **`transcript`** (`transcript_tool.py`): Parses earnings call transcripts to extract speaker names, text segments, and basic rule-based sentiment labels.
3. **`news`** (`news_tool.py`): Interfaces with the NewsAPI `/everything` endpoint to fetch recent headlines and compute an aggregate sentiment score based on financial keywords.

## Common Output Schema

All tools conform to a strict dictionary format:

```python
{
  "source": str,         # "sec_edgar" | "transcript" | "news"
  "ticker": str,         # E.g., "AAPL"
  "data": dict | list,   # The specific data extracted
  "fetched_at": str,     # ISO 8601 UTC timestamp
  "error": str | None    # Contains the error message if a failure occurs, else None
}
```

## Setup & Environment

Ensure you are running Python 3.11+ and install the dependencies:
```bash
pip install httpx beautifulsoup4
```

### Environment Variables

- `NEWS_API_KEY`: Required by the `news` tool. You must obtain an API key from [NewsAPI](https://newsapi.org/) and set it in your environment:
  ```bash
  export NEWS_API_KEY="your_api_key_here"
  ```

## Usage and Testing

The tools can be imported and executed programmatically:

```python
from tools import TOOL_REGISTRY

# Execute tools by name
sec_data = TOOL_REGISTRY["sec"]("AAPL")
news_data = TOOL_REGISTRY["news"]("MSFT")
transcript_data = TOOL_REGISTRY["transcript"]("NVDA")
```

You can also run each tool module as a standalone script for quick testing and debugging. They will output a JSON representation of the fetched data.

```bash
python -m tools.sec_tool
python -m tools.transcript_tool
python -m tools.news_tool
```
