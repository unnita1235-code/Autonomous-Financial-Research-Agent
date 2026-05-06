"""
tests/test_reports.py
─────────────────────
Integration and unit tests for the report generator (Phase 5).

Covers:
  • verdict_logic: all threshold branches
  • section_generators: all 6 sections with mock synthesis data
  • generator: full pipeline integration (no LLM, deterministic fallbacks)
  • data_quality mapping
  • report structure validation
"""

import pytest
from reports.verdict_logic import (
    compute_verdict,
    _compute_data_quality,
    QUALITY_GATE,
    REVENUE_CONFIDENCE_MIN,
    SENTIMENT_POSITIVE,
    SENTIMENT_CAUTION,
)
from reports.section_generators import (
    generate_executive_summary,
    generate_financial_section,
    generate_management_insights,
    generate_risk_section,
    generate_conflicts_section,
    generate_verdict,
    _format_metric_value,
    _avg_confidence,
)
from reports.generator import generate_report


# ═══════════════════════════════════════════════════════════════════════════
# Mock synthesis data — reusable fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def full_synthesis():
    """A realistic synthesis dict with multiple metrics and a conflict."""
    return {
        "ticker": "AAPL",
        "metrics": {
            "revenue": {
                "value": 85800000000.0,
                "confidence": 0.90,
                "conflict": False,
                "winning_source": "sec_edgar",
                "period": "2024-Q3",
                "conflict_detail": None,
            },
            "net_income": {
                "value": 20500000000.0,
                "confidence": 0.70,
                "conflict": False,
                "winning_source": "sec_edgar",
                "period": "2024-Q3",
                "conflict_detail": None,
            },
            "eps": {
                "value": 1.46,
                "confidence": 0.90,
                "conflict": False,
                "winning_source": "sec_edgar",
                "period": "2024-Q3",
                "conflict_detail": None,
            },
            "sentiment_score": {
                "value": 0.62,
                "confidence": 0.70,
                "conflict": False,
                "winning_source": "news",
                "period": "latest",
                "conflict_detail": None,
            },
            "guidance": {
                "value": "We expect continued growth in services revenue.",
                "confidence": 0.70,
                "conflict": False,
                "winning_source": "transcript",
                "period": "latest",
                "conflict_detail": None,
            },
        },
        "conflicts_detected": [],
        "conflict_narrative": None,
        "synthesis_quality": 0.82,
    }


@pytest.fixture
def low_quality_synthesis():
    """A synthesis dict with quality below the 0.75 gate."""
    return {
        "ticker": "XYZ",
        "metrics": {
            "revenue": {
                "value": 1000000.0,
                "confidence": 0.30,
                "conflict": False,
                "winning_source": "news",
                "period": "unknown",
                "conflict_detail": None,
            },
        },
        "conflicts_detected": [],
        "conflict_narrative": None,
        "synthesis_quality": 0.50,
    }


@pytest.fixture
def conflict_synthesis():
    """A synthesis dict with an active revenue conflict and negative sentiment."""
    return {
        "ticker": "TSLA",
        "metrics": {
            "revenue": {
                "value": 85800000000.0,
                "confidence": 0.65,
                "conflict": True,
                "winning_source": "sec_edgar",
                "period": "2024-Q3",
                "conflict_detail": "SEC EDGAR: $85.8B vs TRANSCRIPT: $75.0B (12.6% diff)",
            },
            "sentiment_score": {
                "value": 0.35,
                "confidence": 0.70,
                "conflict": False,
                "winning_source": "news",
                "period": "latest",
                "conflict_detail": None,
            },
        },
        "conflicts_detected": [
            {
                "metric": "revenue",
                "period": "2024-Q3",
                "values": [
                    {"value": 85800000000.0, "source": "sec_edgar"},
                    {"value": 75000000000.0, "source": "transcript"},
                ],
                "max_diff_pct": 12.6,
                "flagged": True,
            }
        ],
        "conflict_narrative": "Revenue discrepancy likely due to GAAP vs non-GAAP reporting.",
        "synthesis_quality": 0.78,
    }


@pytest.fixture
def empty_synthesis():
    """An empty synthesis with no metrics."""
    return {
        "ticker": "UNKNOWN",
        "metrics": {},
        "conflicts_detected": [],
        "conflict_narrative": None,
        "synthesis_quality": 0.0,
    }


# ═══════════════════════════════════════════════════════════════════════════
# _compute_data_quality
# ═══════════════════════════════════════════════════════════════════════════

class TestDataQuality:
    """Tests for the confidence → data_quality mapping."""

    def test_high(self):
        assert _compute_data_quality(0.90) == "high"
        assert _compute_data_quality(0.80) == "high"

    def test_medium(self):
        assert _compute_data_quality(0.75) == "medium"
        assert _compute_data_quality(0.60) == "medium"

    def test_low(self):
        assert _compute_data_quality(0.59) == "low"
        assert _compute_data_quality(0.0) == "low"

    def test_boundary_080(self):
        """0.80 is the boundary between medium and high."""
        assert _compute_data_quality(0.80) == "high"
        assert _compute_data_quality(0.7999) == "medium"


# ═══════════════════════════════════════════════════════════════════════════
# _format_metric_value
# ═══════════════════════════════════════════════════════════════════════════

class TestFormatMetricValue:
    """Tests for metric value formatting."""

    def test_none(self):
        assert _format_metric_value(None) == "N/A"

    def test_billions(self):
        result = _format_metric_value(85800000000.0)
        assert "85.8" in result and "B" in result

    def test_millions(self):
        result = _format_metric_value(340000000.0)
        assert "340" in result and "M" in result

    def test_eps_scale(self):
        result = _format_metric_value(1.46)
        assert "1.46" in result

    def test_string_passthrough(self):
        assert _format_metric_value("strong outlook") == "strong outlook"


# ═══════════════════════════════════════════════════════════════════════════
# _avg_confidence
# ═══════════════════════════════════════════════════════════════════════════

class TestAvgConfidence:
    """Tests for average confidence computation."""

    def test_all_metrics(self, full_synthesis):
        result = _avg_confidence(full_synthesis["metrics"])
        assert 0.0 < result <= 1.0

    def test_selected_keys(self, full_synthesis):
        result = _avg_confidence(full_synthesis["metrics"], ["revenue", "eps"])
        assert result == 0.90  # Both are 0.90

    def test_missing_keys(self, full_synthesis):
        result = _avg_confidence(full_synthesis["metrics"], ["nonexistent"])
        assert result == 0.0

    def test_empty_metrics(self):
        assert _avg_confidence({}) == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# compute_verdict — all threshold branches
# ═══════════════════════════════════════════════════════════════════════════

class TestVerdict:
    """Tests for deterministic verdict logic."""

    def test_insufficient_data(self, low_quality_synthesis):
        """synthesis_quality < 0.75 → Insufficient Data."""
        verdict = compute_verdict(low_quality_synthesis)
        assert verdict["signal"] == "Insufficient Data"
        assert verdict["confidence_used"] < QUALITY_GATE

    def test_positive_signal(self, full_synthesis):
        """revenue_confidence > 0.80 AND sentiment > 0.60 → Positive."""
        verdict = compute_verdict(full_synthesis)
        assert verdict["signal"] == "Positive"
        assert verdict["data_quality"] in ("high", "medium", "low")

    def test_caution_signal(self, conflict_synthesis):
        """Revenue conflict AND sentiment < 0.40 → Caution."""
        verdict = compute_verdict(conflict_synthesis)
        assert verdict["signal"] == "Caution"

    def test_neutral_default(self):
        """No strong signals → Neutral."""
        synthesis = {
            "ticker": "MSFT",
            "metrics": {
                "revenue": {
                    "value": 50000000.0,
                    "confidence": 0.70,
                    "conflict": False,
                    "winning_source": "sec_edgar",
                    "period": "2024-Q3",
                    "conflict_detail": None,
                },
                "sentiment_score": {
                    "value": 0.55,
                    "confidence": 0.70,
                    "conflict": False,
                    "winning_source": "news",
                    "period": "latest",
                    "conflict_detail": None,
                },
            },
            "conflicts_detected": [],
            "conflict_narrative": None,
            "synthesis_quality": 0.78,
        }
        verdict = compute_verdict(synthesis)
        assert verdict["signal"] == "Neutral"

    def test_empty_metrics_below_gate(self, empty_synthesis):
        verdict = compute_verdict(empty_synthesis)
        assert verdict["signal"] == "Insufficient Data"

    def test_verdict_keys(self, full_synthesis):
        verdict = compute_verdict(full_synthesis)
        assert "signal" in verdict
        assert "reason" in verdict
        assert "data_quality" in verdict
        assert "confidence_used" in verdict


# ═══════════════════════════════════════════════════════════════════════════
# Section generators — unit tests
# ═══════════════════════════════════════════════════════════════════════════

class TestExecSummary:
    """Tests for executive summary generation (without LLM)."""

    def test_fallback_generates_content(self, full_synthesis):
        result = generate_executive_summary(full_synthesis, llm_client=None)
        assert "content" in result
        assert "data_quality" in result
        assert len(result["content"]) > 0
        assert "AAPL" in result["content"] or "metrics" in result["content"]

    def test_empty_synthesis(self, empty_synthesis):
        result = generate_executive_summary(empty_synthesis, llm_client=None)
        assert result["data_quality"] == "low"


class TestFinancialSection:
    """Tests for the financial metrics table (deterministic)."""

    def test_rows_generated(self, full_synthesis):
        result = generate_financial_section(full_synthesis)
        assert "rows" in result
        assert len(result["rows"]) == 5  # 5 metrics
        assert result["data_quality"] in ("high", "medium", "low")

    def test_row_structure(self, full_synthesis):
        result = generate_financial_section(full_synthesis)
        for row in result["rows"]:
            assert "metric" in row
            assert "value" in row
            assert "source" in row
            assert "confidence" in row

    def test_empty_synthesis(self, empty_synthesis):
        result = generate_financial_section(empty_synthesis)
        assert result["rows"] == []


class TestManagementInsights:
    """Tests for management insights (without LLM)."""

    def test_fallback_with_transcript_data(self, full_synthesis):
        result = generate_management_insights(full_synthesis, llm_client=None)
        assert "content" in result
        assert "data_quality" in result

    def test_no_transcript_data(self, empty_synthesis):
        result = generate_management_insights(empty_synthesis, llm_client=None)
        assert "No transcript data" in result["content"]


class TestRiskSection:
    """Tests for risk assessment (without LLM)."""

    def test_fallback_generates_content(self, full_synthesis):
        result = generate_risk_section(full_synthesis, llm_client=None)
        assert "content" in result
        assert "data_quality" in result

    def test_with_conflicts(self, conflict_synthesis):
        result = generate_risk_section(conflict_synthesis, llm_client=None)
        assert "conflict" in result["content"].lower()


class TestConflictsSection:
    """Tests for data conflicts section (deterministic)."""

    def test_no_conflicts(self, full_synthesis):
        result = generate_conflicts_section(full_synthesis)
        assert result["conflict_items"] == []
        assert "No data conflicts" in result["content"]

    def test_with_conflicts(self, conflict_synthesis):
        result = generate_conflicts_section(conflict_synthesis)
        assert len(result["conflict_items"]) == 1
        assert result["conflict_items"][0]["metric"] == "Revenue"
        assert result["conflict_items"][0]["diff_pct"] == 12.6

    def test_narrative_included(self, conflict_synthesis):
        result = generate_conflicts_section(conflict_synthesis)
        assert result["narrative"] is not None


class TestVerdictSection:
    """Tests for the final verdict section (deterministic)."""

    def test_positive_verdict(self, full_synthesis):
        result = generate_verdict(full_synthesis)
        assert result["signal"] == "Positive"
        assert "confidence" in result
        assert "data_quality" in result

    def test_insufficient_data(self, low_quality_synthesis):
        result = generate_verdict(low_quality_synthesis)
        assert result["signal"] == "Insufficient Data"


# ═══════════════════════════════════════════════════════════════════════════
# Full pipeline integration — generate_report()
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateReport:
    """Integration tests: feed mock synthesis → validate complete report."""

    def test_all_six_sections(self, full_synthesis):
        """The report must contain exactly 6 mandatory sections."""
        report = generate_report(
            query="Analyze Apple Q3 2024 performance",
            ticker="AAPL",
            synthesis=full_synthesis,
            llm_client=None,
        )

        required_sections = [
            "executive_summary",
            "financial_metrics",
            "management_insights",
            "risk_assessment",
            "data_conflicts",
            "final_verdict",
        ]
        for section in required_sections:
            assert section in report["sections"], f"Missing section: {section}"
            assert "content" in report["sections"][section]
            assert "data_quality" in report["sections"][section]

    def test_report_top_level_keys(self, full_synthesis):
        report = generate_report(
            query="Analyze Apple Q3 2024",
            ticker="AAPL",
            synthesis=full_synthesis,
            llm_client=None,
        )
        assert "report_id" in report
        assert "ticker" in report
        assert "query" in report
        assert "created_at" in report
        assert "sections" in report
        assert "markdown" in report
        assert "synthesis_quality" in report
        assert "status" in report

    def test_report_id_is_uuid4(self, full_synthesis):
        """Report ID must be a valid UUID4 string."""
        import uuid
        report = generate_report(
            query="Test", ticker="AAPL",
            synthesis=full_synthesis, llm_client=None,
        )
        # Should not raise
        parsed = uuid.UUID(report["report_id"], version=4)
        assert str(parsed) == report["report_id"]

    def test_markdown_rendered(self, full_synthesis):
        """Markdown should contain the ticker and section headers."""
        report = generate_report(
            query="Analyze Apple Q3 2024",
            ticker="AAPL",
            synthesis=full_synthesis,
            llm_client=None,
        )
        md = report["markdown"]
        assert "AAPL" in md
        assert "Executive Summary" in md
        assert "Financial Metrics" in md
        assert "Management Insights" in md
        assert "Risk Assessment" in md
        assert "Data Conflicts" in md
        assert "Final Verdict" in md

    def test_financial_table_in_markdown(self, full_synthesis):
        """The financial metrics should render as a Markdown table."""
        report = generate_report(
            query="Test", ticker="AAPL",
            synthesis=full_synthesis, llm_client=None,
        )
        md = report["markdown"]
        assert "| Metric |" in md
        assert "Revenue" in md

    def test_synthesis_quality_passthrough(self, full_synthesis):
        report = generate_report(
            query="Test", ticker="AAPL",
            synthesis=full_synthesis, llm_client=None,
        )
        assert report["synthesis_quality"] == 0.82

    def test_status_is_complete(self, full_synthesis):
        report = generate_report(
            query="Test", ticker="AAPL",
            synthesis=full_synthesis, llm_client=None,
        )
        assert report["status"] == "complete"

    def test_empty_synthesis_produces_report(self, empty_synthesis):
        """Even with no data, the report should generate without crashing."""
        report = generate_report(
            query="Test", ticker="UNKNOWN",
            synthesis=empty_synthesis, llm_client=None,
        )
        assert report["status"] == "complete"
        assert "Insufficient Data" in report["sections"]["final_verdict"]["signal"]

    def test_conflict_synthesis_report(self, conflict_synthesis):
        """Report with conflicts should show them in the conflicts section."""
        report = generate_report(
            query="Analyze Tesla", ticker="TSLA",
            synthesis=conflict_synthesis, llm_client=None,
        )
        conflicts = report["sections"]["data_conflicts"]
        assert len(conflicts["conflict_items"]) == 1
        assert conflicts["conflict_items"][0]["metric"] == "Revenue"

    def test_unique_report_ids(self, full_synthesis):
        """Two reports should have different UUIDs."""
        r1 = generate_report("Test", "AAPL", full_synthesis, None)
        r2 = generate_report("Test", "AAPL", full_synthesis, None)
        assert r1["report_id"] != r2["report_id"]
