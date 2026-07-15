[![Live Demo](https://img.shields.io/badge/Live%20Demo-Frontend-brightgreen?style=for-the-badge)](https://autonomous-financial-research-agent.vercel.app) [![API](https://img.shields.io/badge/API-Render-46E3B7?style=for-the-badge)](https://autonomous-financial-research-agent.onrender.com) [![Stack](https://img.shields.io/badge/Stack-Python%20%7C%20FastAPI%20%7C%20FAISS-black?style=for-the-badge)](https://github.com/unnita1235-code/Autonomous-Financial-Research-Agent)

## Live Preview

[![Autonomous Financial Research Agent](https://image.thum.io/get/width/1280/https://autonomous-financial-research-agent.vercel.app)](https://autonomous-financial-research-agent.vercel.app)

# Autonomous Financial Research Agent

**Live Demo**
- Frontend: https://autonomous-financial-research-agent.vercel.app
- Backend API: https://autonomous-financial-research-agent.onrender.com

A production-grade autonomous agent that gathers and synthesizes financial data using a **ReAct** (Reason + Act) loop with semantic memory.

## Quick Start

### Prerequisites
- Python 3.11+ and pip
- Node.js 20+ and npm
- A free [Groq API key](https://console.groq.com) (default LLM provider)
- A free [NewsAPI key](https://newsapi.org)

### 1. Install
```bash
git clone https://github.com/unnita1235-code/Autonomous-Financial-Research-Agent
cd Autonomous-Financial-Research-Agent
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env — minimum required: GROQ_API_KEY + NEWS_API_KEY
```

### 3. Run with Docker (recommended)
```bash
docker-compose up
```

### 4. Or run locally
```bash
# Backend (terminal 1)
python database/migrate.py   # optional — needs DATABASE_URL
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend && npm install && npm run dev
```

### 5. Verify
```bash
bash verify_all.sh
```

## Honest performance metrics
| Metric | Actual |
|--------|--------|
| Avg pipeline duration | 130–180 seconds |
| Agent stop condition | max_iter (8) in most cases; "done" when data is sufficient |
| Synthesis quality | 70–81% depending on API availability |
| Cold start (Render free tier) | ~60–90 seconds |
| LLM providers supported | Groq (default), OpenAI, Anthropic, Gemini |
| Embedding backend | TF-IDF (free tier default), sentence-transformers or OpenAI (opt-in) |


## Architecture

```mermaid
graph TD
    User([User Query]) --> QA[Query Analyzer]
    QA --> DL[Disambiguation Layer]
    DL --> Agent{ReAct Agent Loop}
    
    subgraph "Reasoning Core"
        Agent --> Thought[Thought]
        Thought --> Action[Action]
        Action --> Tool[Tool Dispatch]
        Tool --> Observation[Observation]
        Observation --> Thought
    end
    
    subgraph "Memory Systems"
        Agent <--> WM[Working Memory - L1]
        Agent <--> SM[(Semantic Memory - L2)]
    end
    
    Agent --> Synthesis[Synthesis Engine]
    Synthesis --> Resolver[Conflict Resolver]
    Resolver --> Report[Final Report]
    Report --> Eval[Evaluation Framework]
    Eval --> Dash[HTML Dashboard]
```

## Core Modules

| Module | Purpose | Key Features |
|--------|---------|--------------|
| `agent/` | Reasoning Intelligence | Query Analysis, Ticker Disambiguation, Circuit Breakers |
| `synthesis/` | Data Harmonization | Priority-based conflict resolution (SEC > Transcript > News) |
| `security/` | System Hardening | PII Redaction, Prompt Injection Shield |
| `evaluation/` | Quality Assurance | 20+ Automated Metrics, HTML Dashboard Generation |
| `memory/` | Knowledge Retention | FAISS-backed Semantic Memory (Layer 2) |
| `tools/` | Data Ingestion | 12+ High-Fidelity tool implementations |

## High-Fidelity Tooling Suite

The agent utilizes a registry of specialized tools for deep financial analysis:
- **SEC EDGAR**: Direct extraction of facts from 10-K, 10-Q, and 8-K filings.
- **Transcripts**: Processing and summarization of earnings call transcripts.
- **News & Sentiment**: Real-time news aggregation with VADER-based sentiment scoring.
- **Financial Data API**: Quantitative metrics retrieval (Revenue, EPS, Multiples).
- **Peer Comparison**: Automated benchmarking against industry cohorts.
- **Fact Checker**: Cross-references claims against known data points.
- **Calculation Engine**: Deterministic arithmetic to prevent LLM hallucination.

---

## Memory System — How It Works

The agent uses a **three-layer memory architecture** to avoid redundant research across sessions:

### Layer 1: Working Memory (per-session)
- A Python `list` that accumulates tool results during a single agent run.
- Injected into the LLM prompt each iteration so the model knows what data it already has.
- **Volatile** — cleared when the session ends.

### Layer 2: Semantic Memory (persistent)
- A **FAISS vector index** that stores embeddings of past tool results and report chunks.
- Enables **similarity search** across all past research sessions.
- Survives restarts — persisted to `memory/faiss_index.bin` + `memory/metadata.json`.

### Layer 3: Episodic Memory (JSON-persisted)
- A JSON-persisted episodic store that records structured episodes from each research run, tracking tool reliability, strategy effectiveness, and error patterns to improve future sessions.

### How the three layers interact

```
Session Start
    │
    ▼
┌──────────────────────────────────────────────┐
│  1. RETRIEVE from Semantic Memory (Layer 2)  │
│     query → embed → FAISS search → top-k     │
│     Inject "RELEVANT PAST RESEARCH" section  │
└──────────────────┬───────────────────────────┘
                   │
    ┌──────────────▼──────────────┐
    │  2. ReAct Loop iterations   │
    │     Working Memory (Layer 1)│◀──┐
    │     accumulates tool results│   │
    └──────────────┬──────────────┘   │
                   │                  │
    ┌──────────────▼──────────────┐   │
    │  3. STORE after each tool   │   │
    │     Tool result → chunk →   │───┘
    │     embed → FAISS insert    │
    │     Also into Layer 2       │
    └──────────────┬──────────────┘
                   │
    ┌──────────────▼──────────────┐
    │  4. SAVE on session end     │
    │     Persist FAISS + metadata│
    └─────────────────────────────┘
```

### Embedding Model
- **Model**: `text-embedding-3-small` (1536 dimensions)
- **Cost**: $0.02 per 1M tokens — cheapest production-grade option
- **Normalisation**: All vectors are L2-normalised so that FAISS inner-product search produces cosine similarity scores

### FAISS Index Type
- **IndexFlatIP** (flat inner product)
- With L2-normalised vectors, `dot(a, b) = cosine(a, b)` — exact cosine similarity
- Brute-force search is fast enough for < 100k vectors (sub-10ms)
- No approximate indexes (HNSW, IVF) needed at this scale

### Chunking Strategy
- **Max tokens**: 400 per chunk
- **Overlap**: 50 tokens between consecutive chunks
- **Tokeniser**: `tiktoken` with `cl100k_base` encoding
- **Rationale**: Overlap preserves context at boundaries (e.g., a revenue figure mentioned in one sentence with its breakdown in the next)

### Score Threshold
- Results with cosine similarity < **0.75** are filtered out
- **Empirically tuned**: scores below 0.75 are typically topically unrelated in financial text
- Scores 0.85+ are usually direct semantic matches

### Metadata Schema
Each stored chunk carries parallel metadata:
```json
{
  "source": "sec_edgar",
  "ticker": "AAPL",
  "period": "2024-Q3",
  "type": "revenue",
  "chunk_text": "Apple Q3 2024 revenue was $85.8B..."
}
```

---

## Setup

### Requirements
```
Python 3.11+
```

### Install Dependencies
```bash
pip install openai httpx beautifulsoup4 faiss-cpu tiktoken numpy
```

For Anthropic LLM support (optional):
```bash
pip install anthropic
```

### Environment Variables
Create a `.env` file based on `.env.example`:
```bash
# API Keys
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
TAVILY_API_KEY="tvly-..."
DATABASE_URL="postgresql://user:pass@host:port/db"

# Configuration
LLM_PROVIDER="openai" # openai, anthropic, gemini, groq
LLM_MODEL="gpt-4o"
ALLOWED_ORIGINS="http://localhost:3000"
```

## Security & Compliance
- **PII Redaction**: All tool outputs are scrubbed for sensitive data before memory storage.
- **Prompt Injection Shield**: Incoming queries are scanned for malicious heuristic patterns.
- **Audit Logs**: Every API interaction is logged with IP tracking for security auditing.
- **Rate Limiting**: Built-in protection against DDoS and API abuse.

## Usage

### Run the Agent
```python
from tools import TOOL_REGISTRY
from agents import run_agent, LLMClient
from memory import VectorStore

llm = LLMClient()
store = VectorStore()  # loads or creates memory/faiss_index.bin

result = run_agent(
    query="Analyze Apple Q3 2024 performance",
    tool_registry=TOOL_REGISTRY,
    llm_client=llm,
    vector_store=store,  # enables semantic memory
)
```

### Run Tests
```bash
# Full test suite (requires OPENAI_API_KEY)
python test_memory.py

# Agent integration test
python test_agent.py
```

## Project Structure
```
├── agent/
│   ├── circuit_breaker.py
│   ├── core.py
│   ├── disambiguation.py
│   ├── error_handler.py
│   ├── fallback_chains.py
│   └── query_analyzer.py
├── agents/
│   ├── llm_client.py
│   ├── prompts.py
│   └── react_loop.py
├── tools/
│   ├── calculation_engine.py
│   ├── company_profile.py
│   ├── fact_checker.py
│   ├── financial_data_api.py
│   ├── news_sentiment.py
│   ├── news_tool.py
│   ├── peer_comparison.py
│   ├── report_generator.py
│   ├── sec_tool.py
│   ├── transcript_tool.py
│   ├── vector_db_search.py
│   └── web_search.py
├── synthesis/
│   ├── conflict_detector.py
│   ├── engine.py
│   ├── extractor.py
│   ├── normalizer.py
│   ├── resolver.py
│   └── narrative.py
├── evaluation/
│   ├── dashboard.py
│   └── metrics.py
├── memory/
│   ├── chunker.py
│   ├── embedder.py
│   ├── episodic.py
│   └── vector_store.py
└── README.md
```
