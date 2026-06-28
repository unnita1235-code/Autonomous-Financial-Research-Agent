# ERROR LOG — 7 Deliberate Errors in ZeTheta PDF Specification

**Student:** Unnita  
**Date:** 2026-05-07  
**Project:** Agentic AI — Autonomous Financial Research Agent  
**Specification:** 463548A_Agentic-AI_Autonomous_Financial_Research_Agent  

---

## Error 1: Source Reliability Hierarchy Inversion

**Location:** Part B, ~Page 21, Source Reliability Framework  
**Category:** Flawed Logic  

**What the PDF says:** Social media and forums (Tier 4) are ranked above major financial news outlets such as Reuters, Bloomberg, and Financial Times (Tier 5).

**Why this is wrong:** Professional financial journalism from Reuters, Bloomberg, and the Financial Times undergoes editorial review, fact-checking, and is subject to regulatory accountability. Anonymous social media posts and forum comments have none of these safeguards. Tier 4 should not outrank Tier 5 — the hierarchy is inverted.

**Correct ranking:** Major financial news outlets (Reuters, Bloomberg, FT) should be Tier 2 or 3. Social media/forums should be Tier 4 or 5 (lower reliability).

**Impact on agent:** An agent using this hierarchy would prioritize a Reddit post over a Bloomberg article when resolving conflicting data, producing unreliable output.

---

## Error 2: AB-4 Memory Utilization Formula

**Location:** Part A, ~Page 19, Analytical Balance Metrics  
**Category:** Incorrect Formula  

**What the PDF says:** AB-4 is described as "the ratio of memory hits to total API calls" but then states it is "calculated as memory_hits *multiplied by* total_api_calls."

**Why this is wrong:** A ratio is computed by division, not multiplication. memory_hits × total_api_calls would produce an ever-increasing number (e.g., 50 × 200 = 10,000) rather than a bounded ratio between 0 and 1 (e.g., 50 / 200 = 0.25).

**Correct formula:** AB-4 = memory_hits / total_api_calls

**Impact on agent:** Using multiplication would produce meaningless metrics that grow unbounded, making evaluation impossible.

---

## Error 3: SCAP and Dodd-Frank Timeline

**Location:** Part C, ~Page 24, Case Study on US Bank Stress Tests  
**Category:** Factual Inaccuracy  

**What the PDF says:** "The first US bank stress tests under SCAP were conducted in 2007 following the Dodd-Frank Act."

**Why this is wrong:** Two errors in one sentence. (1) The Supervisory Capital Assessment Program (SCAP) was conducted in 2009, not 2007. (2) The Dodd-Frank Wall Street Reform and Consumer Protection Act was enacted in July 2010, after SCAP — not before it. SCAP preceded Dodd-Frank; the PDF claims the reverse.

**Correct statement:** SCAP stress tests were conducted in 2009. The Dodd-Frank Act was enacted in 2010 and subsequently formalized ongoing stress testing requirements (CCAR/DFAST).

**Impact on agent:** An agent citing this would produce factually wrong regulatory history that would fail any compliance review.

---

## Error 4: Indian Company Filings — Form 20-F

**Location:** Part D, ~Page 42, International Filings Guide  
**Category:** Wrong API/Filing Specification  

**What the PDF says:** Indian companies file annual returns using "Form 20-F" with the Ministry of Corporate Affairs (MCA).

**Why this is wrong:** Form 20-F is a US SEC filing form used by foreign private issuers listed on American stock exchanges. It is filed with the SEC, not the Indian MCA. Indian companies filing with MCA use entirely different forms: Form MGT-7 for annual returns and Form AOC-4 for financial statements.

**Correct statement:** Indian companies file Form MGT-7 (annual return) and Form AOC-4 (financial statements) with the MCA. Form 20-F is only relevant if an Indian company is cross-listed on US exchanges, and it is filed with the SEC.

**Impact on agent:** The agent would search for non-existent "20-F" filings on the MCA portal, returning no results and wasting tool calls.

---

## Error 5: Tool Count Mismatch

**Location:** Part B, ~Page 34, Gamification — Full Stack Badge  
**Category:** Internal Inconsistency  

**What the PDF says:** The Full Stack Badge is awarded for using "all 12 tools."

**Why this is wrong:** The tool registry defined in the specification (Pages 7-9) only lists 11 tools. There is no 12th tool defined anywhere in the document.

**Correct statement:** Either the badge should reference "all 11 tools" (matching the registry), or a 12th tool should be added to the registry specification.

**Impact on agent:** The badge condition can never be met as described, since the 12th tool does not exist in the spec.

---

## Error 6: Industry Hallucination Rate Baseline

**Location:** Part D, ~Page 40, Quality Benchmarks  
**Category:** Unsourced/Inflated Statistic  

**What the PDF says:** "Industry baseline hallucination rates for unverified financial AI agents are 45-60%."

**Why this is wrong:** This statistic is not supported by any cited source. Published research on LLM hallucination in financial contexts (Bloomberg GPT paper, FinanceBench benchmarks, academic studies on FinGPT) reports varying rates depending on task complexity, but no peer-reviewed source establishes "45-60%" as a general industry baseline for financial AI.

**Correct context:** Hallucination rates vary widely by model, task type, and verification method. Established financial AI benchmarks report different ranges. The 45-60% figure appears fabricated to set an artificially low bar.

**Impact on agent:** Sets a misleading baseline that makes even poorly performing agents appear acceptable by comparison.

---

## Error 7: OpenAI Embedding Model Dimensions

**Location:** Part E, ~Page 62, Tools Guide — Vector Database Setup  
**Category:** Wrong Technical Specification  

**What the PDF says:** The `text-embedding-3-large` model has 1024 dimensions.

**Why this is wrong:** OpenAI's `text-embedding-3-large` produces 3072-dimensional vectors by default. The `text-embedding-3-small` model produces 1536 dimensions. Neither model outputs 1024 dimensions by default. (The API does allow a `dimensions` parameter to truncate, but the default and documented maximum for `text-embedding-3-large` is 3072.)

**Correct specification:** `text-embedding-3-large` = 3072 dimensions (default). `text-embedding-3-small` = 1536 dimensions.

**Impact on agent:** A FAISS index initialized with 1024 dimensions would be incompatible with 3072-dimensional embeddings, causing crashes or producing garbage similarity scores.
