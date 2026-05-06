# Trace Gallery - Agent Reasoning Paths

## Example 1: AAPL Dividend Growth
**Query:** "Analyze Apple's dividend growth over the last 3 years."

**Step 1:** `financial_data_api(ticker='AAPL', statement_type='cashflow', period='annual')`
**Observation:** Dividends paid: $15B (2023), $14.8B (2022), $14.5B (2021).
**Step 2:** `calculation_engine(calculation_type='cagr', inputs={'start_value': 14.5, 'end_value': 15.0, 'num_years': 3})`
**Observation:** CAGR = 1.13%.
**Step 3:** `news_sentiment(query='Apple dividend increase 2024')`
**Observation:** Positive sentiment regarding potential buyback increase.

**Synthesis:** Apple maintains steady but modest dividend growth, prioritizing capital return through buybacks.

## Example 2: TSLA Risk Assessment
**Query:** "What are the primary regulatory risks for Tesla in China?"

**Step 1:** `web_search(query='Tesla regulatory risks China 2024')`
**Observation:** Mentions of data security laws and EV subsidy changes.
**Step 2:** `sec_tool(ticker='TSLA', type='10-K')`
**Observation:** Identified "International Operations" section in Risk Factors.
**Step 3:** `fact_checker(claim='Tesla faces 20% tariff increase in China')`
**Observation:** Status: Inconclusive (contradicting reports found).

**Synthesis:** Regulatory landscape remains complex with data security being the primary headwind.
