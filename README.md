# Autonomous Financial Research Agent

A production-grade autonomous agent that gathers and synthesises financial data using a **ReAct** (Reason + Act) loop with semantic memory.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Query                             │
│              "Analyze Apple Q3 2024 performance"            │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   ReAct Agent Loop                          │
│                 (agents/react_loop.py)                       │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   THOUGHT    │───▶│   ACTION     │───▶│  OBSERVE     │  │
│  │  (LLM JSON)  │    │ (tool call)  │    │ (tool result) │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│          ▲                                       │          │
│          └───────────────────────────────────────┘          │
└───────────┬─────────────────────────────────┬───────────────┘
            │                                 │
   ┌────────▼────────┐              ┌────────▼────────┐
   │  Layer 1:       │              │  Layer 2:       │
   │  Working Memory │              │  Semantic Memory│
   │  (Python list)  │              │  (FAISS index)  │
   │  Per-session    │              │  Persisted       │
   └─────────────────┘              └─────────────────┘
```

## Modules

| Module | Description |
|--------|-------------|
| `agents/` | ReAct loop, LLM client (OpenAI/Anthropic), system prompts |
| `tools/` | SEC EDGAR, earnings transcripts, news sentiment tools |
| `memory/` | Semantic memory: embedder, chunker, FAISS vector store |

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
```bash
export OPENAI_API_KEY="sk-..."         # Required for embeddings + LLM (if using OpenAI)
export ANTHROPIC_API_KEY="..."         # Required if LLM_PROVIDER=anthropic
export LLM_PROVIDER="openai"           # "openai" or "anthropic"
export NEWS_API_KEY="..."              # Required by news tool
```

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
