import pytest
from synthesis.normalizer import normalize_value
from synthesis.conflict_detector import detect_conflicts
from synthesis.engine import synthesize
from synthesis.narrative import generate_conflict_narrative

def test_normalize_billions():
    assert normalize_value("$85.8B") == 85_800_000_000.0

def test_normalize_millions():
    assert normalize_value("$1.2M") == 1_200_000.0

def test_normalize_numeric():
    assert normalize_value(1234.56) == 1234.56

def test_normalize_none():
    assert normalize_value(None) is None

def test_normalize_unparseable():
    assert normalize_value("not a number xyz") is None

def test_no_conflict_within_5pct():
    metrics = [
        {"metric_name": "revenue", "period": "2024-Q3", "value": 85_800_000_000.0, "source": "sec_edgar"},
        {"metric_name": "revenue", "period": "2024-Q3", "value": 85_500_000_000.0, "source": "transcript"},
    ]
    conflicts = detect_conflicts(metrics)
    assert len(conflicts) == 1
    assert not conflicts[0]["flagged"]

def test_conflict_flagged_above_5pct():
    metrics = [
        {"metric_name": "revenue", "period": "2024-Q3", "value": 85_800_000_000.0, "source": "sec_edgar"},
        {"metric_name": "revenue", "period": "2024-Q3", "value": 70_000_000_000.0, "source": "news"},
    ]
    conflicts = detect_conflicts(metrics)
    assert len(conflicts) == 1
    assert conflicts[0]["flagged"]

def test_synthesize_empty():
    result = synthesize([])
    assert result["synthesis_quality"] == 0.0
    assert result["metrics"] == {}

def test_narrative_no_conflicts():
    result = generate_conflict_narrative([])
    assert "No conflicts" in result

def test_narrative_with_conflicts():
    conflicts = [{"metric": "revenue", "period": "2024-Q3", "max_diff_pct": 12.5, "flagged": True}]
    result = generate_conflict_narrative(conflicts, llm_client=None)
    assert "revenue" in result.lower() or "conflict" in result.lower()
