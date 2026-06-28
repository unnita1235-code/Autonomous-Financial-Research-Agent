# Architecture Specification - Autonomous Financial Research Agent

## 1. Overview
The system is an agentic AI designed to perform deep quantitative and qualitative financial research. It utilizes a ReAct (Reasoning and Acting) loop to dynamically use tools and synthesize information.

## 2. Core Components
- **Agentic Loop (`agents/`):** Orchestrates tool use and reasoning.
- **Memory System (`memory/`):** Two-layer memory (Working + Semantic FAISS).
- **Tool Registry (`tools/`):** 10+ specialized tools for SEC data, News, Earnings Transcripts, and Web Search.
- **Synthesis Engine (`synthesis/`):** Resolves conflicts and builds professional narratives.

## 3. Data Flow
1. **Query Entry:** User submits a research request via FastAPI.
2. **Analysis:** `QueryAnalyzer` classifies intent and identifies tickers.
3. **Execution:** `react_loop` iteratively calls tools and observes results.
4. **Retrieval:** Semantic memory provides context from past sessions.
5. **Synthesis:** Engine integrates findings, resolves conflicts, and generates a Markdown report.

## 4. Security & Hardening
- **PII Redaction:** Scrubbing sensitive data from tool outputs using regex-based sanitization.
- **Injection Shield:** Guarding against prompt injection attacks using heuristic pattern matching.
- **Audit Logging:** Every API transaction is logged to PostgreSQL with IP and request ID tracking.
- **Rate Limiting:** SlowAPI prevents API abuse and resource exhaustion.
- **Circuit Breaker:** Prevents cascading failures when external APIs (e.g., NewsAPI) are down.

## 5. Evaluation Framework
- **Metrics:** 20+ automated scores for structural integrity, data fidelity, and performance.
- **Dashboard:** Automated Jinja2-based HTML dashboard reflecting all agent scores.
