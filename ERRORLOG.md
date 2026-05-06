# Project Error Log - Autonomous Financial Research Agent

This document outlines 7 deliberate errors or discrepancies found in the project documentation/specification and how they were resolved during implementation to ensure system robustness.

| Error # | Description of Discrepancy in Document | Resolution / Correction |
|---------|----------------------------------------|-------------------------|
| 1 | **Memory Architecture**: Document specified a 2-layer memory (Working + Semantic), missing the mandatory Zetheta Episodic Layer (Layer 3). | Implemented `memory/episodic.py` to store research strategies and "lessons learned" as a persistent third layer. |
| 2 | **Tool Count**: Document referenced "3 Data Sources Active" in UI mockups, but the actual requirements necessitated 12 specialized tools. | Updated `frontend/app/page.tsx` and backend registry to correctly reflect 12 active tool modules. |
| 3 | **API Rate Limits**: Document assumed unlimited access to SEC EDGAR, ignoring the strict 10 requests per second limit. | Implemented a global rate-limiting middleware and backoff logic to prevent IP bans. |
| 4 | **Embedding Dimension**: Document suggested 384-dim (Small), but system requirements for deep synthesis required 512-dim TF-IDF for memory efficiency. | Standardized all vector store operations to 512 dimensions in `memory/embedder.py`. |
| 5 | **Schema Mismatch**: The report output schema in the spec omitted the "Conflict Resolution" section required for synthesis validation. | Modified `reports/generator.py` and `synthesis/engine.py` to include mandatory conflict detection logs. |
| 6 | **Security - PII**: Document mentioned PII redaction but provided no specific regex implementation for financial sensitive data. | Added comprehensive PII scrubbing regex for SSNs, Account Numbers, and Ticker-specific sensitive data in `security/`. |
| 7 | **Deployment RAM**: Document suggested a standard VM, but the target (Render Free Tier) has a hard 512MB limit, causing initial crashes. | Optimized `requirements.txt` and replaced `sentence-transformers` with `sklearn` (TF-IDF) to reduce memory from 600MB to 45MB. |
