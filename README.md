# Autonomous Financial Research Agent

## Live Demo
- Frontend: https://autonomous-financial-research-agent.vercel.app
- Backend API: https://autonomous-financial-research-agent.onrender.com

A production-grade autonomous agent that gathers and synthesises financial data using a **ReAct** (Reason + Act) loop with semantic memory.

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

The agent uses a **two-layer memory architecture** to avoid redundant research across sessions:

### Layer 1: Working Memory (per-session)
- A Python `list` that accumulates tool results during a single agent run.
- Injected into the LLM prompt each iteration so the model knows what data it already has.
- **Volatile** — cleared when the session ends.

### Layer 2: Semantic Memory (persistent)
- A **FAISS vector index** that stores embeddings of past tool results and report chunks.
- Enables **similarity search** across all past research sessions.
- Survives restarts — persisted to `memory/faiss_index.bin` + `memory/metadata.json`.

### How the two layers interact

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
├── agents/
│   ├── __init__.py
│   ├── llm_client.py      # OpenAI / Anthropic chat client
│   ├── prompts.py          # System prompt + user prompt builder
│   └── react_loop.py       # Core ReAct loop with semantic memory
├── memory/
│   ├── __init__.py
│   ├── chunker.py          # Token-aware text chunking (tiktoken)
│   ├── embedder.py         # OpenAI embedding + L2 normalisation
│   └── vector_store.py     # FAISS IndexFlatIP vector store
├── tools/
│   ├── __init__.py
│   ├── sec_tool.py         # SEC EDGAR financial data
│   ├── transcript_tool.py  # Earnings call transcripts
│   └── news_tool.py        # News sentiment analysis
├── test_agent.py            # Agent integration test
├── test_memory.py           # Memory system tests
└── README.md
```
