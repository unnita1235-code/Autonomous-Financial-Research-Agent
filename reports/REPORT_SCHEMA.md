# Report Output Schema

Complete documentation of the report generator output dict,
verdict thresholds, and edge cases.

---

## Report Dict Schema

The `generate_report()` function returns a dict with this exact structure:

```json
{
    "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "ticker": "AAPL",
    "query": "Analyze Apple Q3 2024 performance",
    "created_at": "2026-05-06T01:00:00+00:00",
    "sections": {
        "executive_summary": {
            "content": "...",
            "data_quality": "high"
        },
        "financial_metrics": {
            "content": "5 metrics extracted and reconciled.",
            "rows": [
                {
                    "metric": "Revenue",
                    "value": "$85.8B",
                    "source": "Sec Edgar",
                    "confidence": "90%"
                }
            ],
            "data_quality": "high"
        },
        "management_insights": {
            "content": "...",
            "data_quality": "medium"
        },
        "risk_assessment": {
            "content": "...",
            "data_quality": "medium"
        },
        "data_conflicts": {
            "content": "1 conflict(s) detected.",
            "items": [
                {
                    "metric": "Revenue",
                    "period": "2024-Q3",
                    "detail": "Sec Edgar: $85.8B vs Transcript: $84.0B → Resolved: Sec Edgar prioritised",
                    "diff_pct": 2.1
                }
            ],
            "narrative": "...",
            "data_quality": "medium"
        },
        "final_verdict": {
            "content": "Revenue confidence (90%) exceeds 80% threshold...",
            "signal": "Positive",
            "reason": "Revenue confidence (90%) exceeds 80% threshold...",
            "data_quality": "high",
            "confidence": "82%"
        }
    },
    "markdown": "# Financial Research Report: AAPL\n...",
    "synthesis_quality": 0.82,
    "status": "complete"
}
```

---

## Field Reference

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `report_id` | `str` | UUID4 string — prevents enumeration attacks |
| `ticker` | `str` | Stock ticker symbol (e.g. "AAPL") |
| `query` | `str` | Original user research query |
| `created_at` | `str` | ISO 8601 UTC timestamp |
| `sections` | `dict` | Section name → section data dict |
| `markdown` | `str` | Full rendered Markdown report (Jinja2) |
| `synthesis_quality` | `float` | 0.0–1.0, mean confidence of all resolved metrics |
| `status` | `str` | Always "complete" (future: "partial", "error") |

### Section Fields

Every section contains at minimum:
- `content` (str): Human-readable section text
- `data_quality` (str): "high" | "medium" | "low"

#### `financial_metrics` (additional)
- `rows` (list): Table row dicts with `metric`, `value`, `source`, `confidence`

#### `data_conflicts` (additional)
- `items` (list): Conflict dicts with `metric`, `period`, `detail`, `diff_pct`
- `narrative` (str | None): LLM-generated explanation or deterministic fallback

#### `final_verdict` (additional)
- `signal` (str): "Positive" | "Neutral" | "Caution" | "Insufficient Data"
- `reason` (str): Detailed explanation
- `confidence` (str): Synthesis quality as percentage string

---

## Data Quality Mapping

| Avg Confidence | Label | Meaning |
|----------------|-------|---------|
| ≥ 0.80 | **high** | Multi-source corroboration or high-priority single source |
| ≥ 0.60 | **medium** | Single source or partial corroboration |
| < 0.60 | **low** | Significant gaps, conflicts, or errors |

---

## Verdict Thresholds

All thresholds are deterministic — no LLM involved.

| Threshold | Value | Rationale |
|-----------|-------|-----------|
| `QUALITY_GATE` | 0.75 | Below this, synthesis has significant data gaps. Any signal would be unreliable. Academic research on analyst confidence shows <75% agreement correlates with random outcomes. |
| `REVENUE_CONFIDENCE_MIN` | 0.80 | Revenue is the top-line metric. 0.80 ensures at least partial multi-source corroboration. |
| `SENTIMENT_POSITIVE` | 0.60 | Net-positive market reception. Below 0.50 is neutral. |
| `SENTIMENT_CAUTION` | 0.40 | Actively negative market reception. Combined with revenue conflict = "Caution". |

### Verdict Decision Tree

```
synthesis_quality < 0.75?
  → "Insufficient Data"

revenue_confidence > 0.80 AND sentiment > 0.60?
  → "Positive"

revenue_conflict AND sentiment < 0.40?
  → "Caution"

else
  → "Neutral"
```

---

## "Insufficient Data" — When and Why

**When:** The `synthesis_quality` score is below 0.75 (75%).

**What it means:** The synthesis engine could not gather enough reliable
data to produce an actionable signal. Common causes:

1. **Tool failures:** One or more data sources (SEC EDGAR, transcript, news)
   returned errors or were unavailable.
2. **Missing metrics:** Key metrics like revenue or EPS were not found in
   any source.
3. **High conflict rate:** Multiple metrics had >5% variance between sources,
   reducing confidence scores to conflict-resolved levels (0.65).
4. **Single-source data:** All metrics came from a single source with no
   corroboration (0.70 confidence max per metric).

**User guidance:** When a report shows "Insufficient Data", the user should:
- Retry with a different ticker or time period
- Check that API keys (NEWS_API_KEY, etc.) are configured
- Verify that the ticker has SEC filings and earnings transcripts available
- Consider the report's individual section data quality ratings for partial insights

---

## Database Tables

### `reports`

| Column | Type | Description |
|--------|------|-------------|
| `report_id` | UUID (PK) | UUID4 from report generator |
| `ticker` | VARCHAR | Stock ticker |
| `query` | TEXT | Original query |
| `markdown` | TEXT | Full rendered Markdown |
| `synthesis_quality` | FLOAT | 0.0–1.0 |
| `status` | VARCHAR | "complete" |
| `created_at` | TIMESTAMP | UTC timestamp |

### `findings`

| Column | Type | Description |
|--------|------|-------------|
| `finding_id` | UUID (PK) | UUID4 per finding |
| `report_id` | UUID (FK) | References reports.report_id |
| `metric_name` | VARCHAR | Canonical metric key |
| `metric_value` | VARCHAR | Formatted value string |
| `confidence` | FLOAT | 0.0–1.0 |
| `source` | VARCHAR | Winning source name |
| `period` | VARCHAR | Fiscal period or "latest" |
| `conflict_flagged` | BOOLEAN | Whether conflict was detected |
| `conflict_detail` | TEXT | Human-readable conflict detail |
