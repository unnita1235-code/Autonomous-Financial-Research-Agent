"""
tests/test_synthesis.py
───────────────────────
Unit tests for the synthesis engine.

Covers:
  • normalize_value: 10+ input formats
  • extract_metrics: SEC, transcript, news (happy + error paths)
  • detect_conflicts: no-conflict, within-threshold, above-threshold
  • resolve_metric: single source, multi-agree, conflict, error
  • synthesize: full integration with mock memory, empty memory edge case
"""

import pytest
from synthesis.normalizer import normalize_value
from synthesis.extractor import extract_metrics
from synthesis.conflict_detector import detect_conflicts, CONFLICT_THRESHOLD_PCT
from synthesis.resolver import (
    resolve_metric,
    CONFIDENCE_BASE_REAL_DATA,
    CONFIDENCE_MULTI_AGREE,
    CONFIDENCE_CONFLICT_RESOLVED,
    CONFIDENCE_ERROR,
)
from synthesis.engine import synthesize
from synthesis.narrative import generate_conflict_narrative


# ═══════════════════════════════════════════════════════════════════════════
# normalize_value — 10+ format tests
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeValue:
    """Tests for the normalize_value function across multiple input formats."""

    def test_already_int(self):
        assert normalize_value(85800000000) == 85800000000.0

    def test_already_float(self):
        assert normalize_value(85.8) == 85.8

    def test_dollar_billions_suffix_b(self):
        result = normalize_value("$85.8B")
        assert result == pytest.approx(85_800_000_000.0)

    def test_dollar_millions_suffix_m(self):
        result = normalize_value("$85,800M")
        assert result == pytest.approx(85_800_000_000.0)

    def test_word_billion(self):
        result = normalize_value("85.8 billion")
        assert result == pytest.approx(85_800_000_000.0)

    def test_dollar_eps_scale(self):
        """EPS-scale values like $2.18 — no suffix."""
        result = normalize_value("$2.18")
        assert result == pytest.approx(2.18)

    def test_approximately_prefix(self):
        result = normalize_value("approximately $84 billion")
        assert result == pytest.approx(84_000_000_000.0)

    def test_adjective_prefix(self):
        """Strip adjectives like 'strong' before the number."""
        result = normalize_value("strong $84B")
        assert result == pytest.approx(84_000_000_000.0)

    def test_full_comma_format(self):
        result = normalize_value("$85,800,000,000")
        assert result == pytest.approx(85_800_000_000.0)

    def test_trillion(self):
        result = normalize_value("$1.2T")
        assert result == pytest.approx(1_200_000_000_000.0)

    def test_none_input(self):
        assert normalize_value(None) is None

    def test_empty_string(self):
        assert normalize_value("") is None

    def test_garbage_input(self):
        """Non-numeric input should return None — never guess."""
        assert normalize_value("not a number at all") is None

    def test_negative_value(self):
        result = normalize_value("-$2.5B")
        assert result == pytest.approx(-2_500_000_000.0)

    def test_word_million(self):
        result = normalize_value("$340 million")
        assert result == pytest.approx(340_000_000.0)


# ═══════════════════════════════════════════════════════════════════════════
# extract_metrics — SEC source
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractSEC:
    """Tests for extracting metrics from SEC EDGAR tool output."""

    def test_happy_path(self):
        tool_output = {
            "source": "sec_edgar",
            "ticker": "AAPL",
            "data": {
                "revenue_quarterly": [
                    {"period": "2024-Q3", "value": 85800000000},
                    {"period": "2024-Q2", "value": 81800000000},
                ],
                "net_income_quarterly": [
                    {"period": "2024-Q3", "value": 20500000000},
                ],
                "eps_quarterly": [
                    {"period": "2024-Q3", "value": 1.46},
                ],
            },
            "error": None,
        }
        metrics = extract_metrics(tool_output)
        assert len(metrics) == 4  # 2 revenue + 1 net_income + 1 eps

        revenue_metrics = [m for m in metrics if m["metric_name"] == "revenue"]
        assert len(revenue_metrics) == 2
        assert revenue_metrics[0]["value"] == 85800000000.0
        assert revenue_metrics[0]["source"] == "sec_edgar"
        assert revenue_metrics[0]["period"] == "2024-Q3"

    def test_error_returns_empty(self):
        tool_output = {
            "source": "sec_edgar",
            "ticker": "AAPL",
            "data": {},
            "error": "Could not resolve CIK",
        }
        metrics = extract_metrics(tool_output)
        assert metrics == []


# ═══════════════════════════════════════════════════════════════════════════
# extract_metrics — Transcript source
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractTranscript:
    """Tests for extracting metrics from transcript tool output."""

    def test_revenue_extraction(self):
        tool_output = {
            "source": "transcript",
            "ticker": "AAPL",
            "data": [
                {
                    "speaker": "CFO",
                    "text": "Revenue reached $84 billion this quarter.",
                    "sentiment_label": "positive",
                },
            ],
            "error": None,
        }
        metrics = extract_metrics(tool_output)
        revenue = [m for m in metrics if m["metric_name"] == "revenue"]
        assert len(revenue) == 1
        assert revenue[0]["value"] == pytest.approx(84_000_000_000.0)
        assert revenue[0]["source"] == "transcript"

    def test_no_numbers_returns_empty_numeric(self):
        tool_output = {
            "source": "transcript",
            "ticker": "AAPL",
            "data": [
                {
                    "speaker": "CEO",
                    "text": "We had a great quarter overall.",
                    "sentiment_label": "positive",
                },
            ],
            "error": None,
        }
        metrics = extract_metrics(tool_output)
        # No numeric metrics, possibly guidance if keyword matches
        numeric = [m for m in metrics if not m.get("is_qualitative")]
        assert len(numeric) == 0


# ═══════════════════════════════════════════════════════════════════════════
# extract_metrics — News source
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractNews:
    """Tests for extracting metrics from news tool output."""

    def test_sentiment_extraction(self):
        tool_output = {
            "source": "news",
            "ticker": "AAPL",
            "data": {
                "headlines": [],
                "sentiment_score": 0.62,
                "article_count": 50,
            },
            "error": None,
        }
        metrics = extract_metrics(tool_output)
        assert len(metrics) == 1
        assert metrics[0]["metric_name"] == "sentiment_score"
        assert metrics[0]["value"] == 0.62

    def test_error_returns_empty(self):
        tool_output = {
            "source": "news",
            "ticker": "AAPL",
            "data": {},
            "error": "API key not set",
        }
        metrics = extract_metrics(tool_output)
        assert metrics == []


# ═══════════════════════════════════════════════════════════════════════════
# detect_conflicts
# ═══════════════════════════════════════════════════════════════════════════

class TestDetectConflicts:
    """Tests for conflict detection logic."""

    def test_no_conflict_single_source(self):
        metrics = [
            {"metric_name": "revenue", "value": 85.8e9, "source": "sec_edgar", "period": "2024-Q3"},
        ]
        conflicts = detect_conflicts(metrics)
        assert conflicts == []

    def test_within_threshold_not_flagged(self):
        """Two values within 5% should create record but flagged=False."""
        metrics = [
            {"metric_name": "revenue", "value": 85.8e9, "source": "sec_edgar", "period": "2024-Q3"},
            {"metric_name": "revenue", "value": 84.0e9, "source": "transcript", "period": "2024-Q3"},
        ]
        conflicts = detect_conflicts(metrics)
        assert len(conflicts) == 1
        # 85.8 vs 84.0 → ~2.1% diff → within 5%
        assert conflicts[0]["flagged"] is False
        assert conflicts[0]["max_diff_pct"] < CONFLICT_THRESHOLD_PCT

    def test_above_threshold_flagged(self):
        """Two values differing by >5% should be flagged."""
        metrics = [
            {"metric_name": "revenue", "value": 85.8e9, "source": "sec_edgar", "period": "2024-Q3"},
            {"metric_name": "revenue", "value": 75.0e9, "source": "transcript", "period": "2024-Q3"},
        ]
        conflicts = detect_conflicts(metrics)
        assert len(conflicts) == 1
        assert conflicts[0]["flagged"] is True
        assert conflicts[0]["max_diff_pct"] > CONFLICT_THRESHOLD_PCT

    def test_qualitative_excluded(self):
        """Qualitative metrics should not trigger numeric conflict detection."""
        metrics = [
            {"metric_name": "guidance", "value": "strong outlook", "source": "transcript",
             "period": "2024-Q3", "is_qualitative": True},
            {"metric_name": "guidance", "value": "positive forecast", "source": "news",
             "period": "2024-Q3", "is_qualitative": True},
        ]
        conflicts = detect_conflicts(metrics)
        assert conflicts == []


# ═══════════════════════════════════════════════════════════════════════════
# resolve_metric
# ═══════════════════════════════════════════════════════════════════════════

class TestResolveMetric:
    """Tests for metric resolution logic."""

    def test_single_source(self):
        entries = [
            {"metric_name": "revenue", "value": 85.8e9, "source": "sec_edgar", "period": "2024-Q3"},
        ]
        result = resolve_metric("revenue", entries)
        assert result["value"] == 85.8e9
        assert result["confidence"] == CONFIDENCE_BASE_REAL_DATA
        assert result["conflict_flagged"] is False

    def test_multi_agree(self):
        """Two sources within 5% → average, high confidence."""
        entries = [
            {"metric_name": "revenue", "value": 85.8e9, "source": "sec_edgar", "period": "2024-Q3"},
            {"metric_name": "revenue", "value": 84.0e9, "source": "transcript", "period": "2024-Q3"},
        ]
        # No conflict (within threshold)
        conflict = {"metric": "revenue", "period": "2024-Q3", "flagged": False, "max_diff_pct": 2.1}
        result = resolve_metric("revenue", entries, conflict)
        assert result["confidence"] == CONFIDENCE_MULTI_AGREE
        assert result["conflict_flagged"] is False
        # Average of 85.8e9 and 84.0e9
        expected_avg = (85.8e9 + 84.0e9) / 2
        assert result["value"] == pytest.approx(expected_avg)

    def test_conflict_resolved_by_priority(self):
        """Conflict → pick SEC (highest priority), lower confidence."""
        entries = [
            {"metric_name": "revenue", "value": 85.8e9, "source": "sec_edgar", "period": "2024-Q3"},
            {"metric_name": "revenue", "value": 75.0e9, "source": "transcript", "period": "2024-Q3"},
        ]
        conflict = {
            "metric": "revenue", "period": "2024-Q3",
            "flagged": True, "max_diff_pct": 12.6,
            "values": [
                {"value": 85.8e9, "source": "sec_edgar"},
                {"value": 75.0e9, "source": "transcript"},
            ],
        }
        result = resolve_metric("revenue", entries, conflict)
        assert result["value"] == 85.8e9  # SEC wins
        assert result["winning_source"] == "sec_edgar"
        assert result["confidence"] == CONFIDENCE_CONFLICT_RESOLVED
        assert result["conflict_flagged"] is True
        assert result["conflict_detail"] is not None

    def test_empty_entries(self):
        result = resolve_metric("revenue", [])
        assert result["value"] is None
        assert result["confidence"] == CONFIDENCE_ERROR


# ═══════════════════════════════════════════════════════════════════════════
# synthesize — integration tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSynthesize:
    """Integration tests for the full synthesis pipeline."""

    def test_empty_memory(self):
        result = synthesize([])
        assert result["ticker"] == "UNKNOWN"
        assert result["metrics"] == {}
        assert result["conflicts_detected"] == []
        assert result["synthesis_quality"] == 0.0

    def test_full_pipeline(self):
        """End-to-end test with SEC + transcript + news mock memory."""
        memory = [
            {
                "iteration": 1,
                "decision": {"thought": "...", "action": "tool", "tool_name": "sec",
                             "tool_args": {"ticker": "AAPL"}, "confidence": 0.9},
                "tool_output": {
                    "source": "sec_edgar",
                    "ticker": "AAPL",
                    "data": {
                        "revenue_quarterly": [{"period": "2024-Q3", "value": 85800000000}],
                        "net_income_quarterly": [{"period": "2024-Q3", "value": 20500000000}],
                        "eps_quarterly": [{"period": "2024-Q3", "value": 1.46}],
                    },
                    "error": None,
                },
            },
            {
                "iteration": 2,
                "decision": {"thought": "...", "action": "tool", "tool_name": "transcript",
                             "tool_args": {"ticker": "AAPL"}, "confidence": 0.8},
                "tool_output": {
                    "source": "transcript",
                    "ticker": "AAPL",
                    "data": [
                        {"speaker": "CFO", "text": "Revenue reached $84 billion this quarter.",
                         "sentiment_label": "positive"},
                    ],
                    "error": None,
                },
            },
            {
                "iteration": 3,
                "decision": {"thought": "...", "action": "tool", "tool_name": "news",
                             "tool_args": {"ticker": "AAPL"}, "confidence": 0.7},
                "tool_output": {
                    "source": "news",
                    "ticker": "AAPL",
                    "data": {"headlines": [], "sentiment_score": 0.62, "article_count": 50},
                    "error": None,
                },
            },
        ]

        result = synthesize(memory)

        # Basic structure
        assert result["ticker"] == "AAPL"
        assert "revenue" in result["metrics"]
        assert "sentiment_score" in result["metrics"]
        assert isinstance(result["synthesis_quality"], float)
        assert 0.0 <= result["synthesis_quality"] <= 1.0

        # Revenue should exist with a resolved value
        rev = result["metrics"]["revenue"]
        assert rev["value"] is not None
        assert rev["confidence"] > 0
        assert isinstance(rev["conflict"], bool)

    def test_error_source_handling(self):
        """A tool that returned an error should not crash the pipeline."""
        memory = [
            {
                "iteration": 1,
                "decision": {"thought": "...", "action": "tool", "tool_name": "sec",
                             "tool_args": {"ticker": "AAPL"}, "confidence": 0.9},
                "tool_output": {
                    "source": "sec_edgar",
                    "ticker": "AAPL",
                    "data": {},
                    "error": "CIK not found",
                },
            },
        ]
        result = synthesize(memory)
        assert result["ticker"] == "AAPL"
        assert result["metrics"] == {}
        assert result["synthesis_quality"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# narrative — fallback test
# ═══════════════════════════════════════════════════════════════════════════

class TestNarrative:
    """Tests for conflict narrative generation."""

    def test_no_conflicts_returns_message(self):
        result = generate_conflict_narrative([])
        assert "No conflicts" in result

    def test_fallback_without_llm(self):
        conflicts = [
            {"metric": "revenue", "period": "2024-Q3", "max_diff_pct": 12.6,
             "values": [], "flagged": True},
        ]
        result = generate_conflict_narrative(conflicts, llm_client=None)
        assert "revenue" in result
        assert "GAAP" in result or "conflict" in result.lower()
