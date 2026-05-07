import logging
import re
import datetime
from typing import Dict, List, Any, Optional, Union

from synthesis.normalizer import normalize_value

logger = logging.getLogger(__name__)

# --- Constants ---
NOT_COMPUTED = "not_computed"

# --- Helper Functions ---

def extract_numbers_from_text(text: str) -> List[float]:
    """Extracts all numerical values from text using normalizer."""
    # Use a regex that finds potential currency/number patterns
    potential_matches = re.findall(r'[\$]?\s*-?[\d,]+\.?\d*\s*[BMTKbmtk]?\s*(?:billion|million|trillion|thousand)?', text)
    numbers = []
    for m in potential_matches:
        val = normalize_value(m)
        if val is not None:
            numbers.append(val)
    return numbers

def extract_dates_from_text(text: str) -> List[str]:
    """Extracts date-like patterns from text."""
    # Matches YYYY-MM-DD, Q1-Q4 YYYY, Month YYYY
    patterns = [
        r'\b\d{4}-\d{2}-\d{2}\b',
        r'\bQ[1-4]\s+\d{4}\b',
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b'
    ]
    dates = []
    for p in patterns:
        dates.extend(re.findall(p, text))
    return dates

def get_all_source_data(memory: List[Dict[str, Any]]) -> List[float]:
    """Flattens all numeric data from tool outputs for comparison."""
    all_values = []
    for item in memory:
        output = item.get("tool_output") or item.get("output")
        if not output or not isinstance(output, dict):
            continue
        data = output.get("data")
        if isinstance(data, dict):
            def collect_vals(d):
                if isinstance(d, dict):
                    for v in d.values(): collect_vals(v)
                elif isinstance(d, list):
                    for v in d: collect_vals(v)
                elif isinstance(d, (int, float)):
                    all_values.append(float(d))
                elif isinstance(d, str):
                    norm = normalize_value(d)
                    if norm is not None: all_values.append(norm)
            collect_vals(data)
        elif isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    for v in entry.values():
                        if isinstance(v, (int, float)): all_values.append(float(v))
                        elif isinstance(v, str):
                            norm = normalize_value(v)
                            if norm is not None: all_values.append(norm)
    return all_values

def get_all_source_dates(memory: List[Dict[str, Any]]) -> List[str]:
    """Collects all dates/periods from tool outputs."""
    dates = []
    for item in memory:
        output = item.get("tool_output") or item.get("output")
        if not output or not isinstance(output, dict):
            continue
        data = output.get("data")
        def collect_periods(d):
            if isinstance(d, dict):
                if "period" in d: dates.append(str(d["period"]))
                for v in d.values(): collect_periods(v)
            elif isinstance(d, list):
                for v in d: collect_periods(v)
        collect_periods(data)
    return dates

# --- Metric Computation Functions ---

def compute_fa1_numerical_accuracy(report_text: str, source_values: List[float]) -> Optional[float]:
    """FA-1 Numerical Accuracy: correct_numbers / total_numbers * 100"""
    numbers = extract_numbers_from_text(report_text)
    if not numbers: return None
    correct = 0
    for n in numbers:
        # Check within 1% tolerance
        if any(abs(n - sv) / max(1e-9, abs(sv)) <= 1e-2 for sv in source_values):
            correct += 1
    return (correct / len(numbers)) * 100.0

def compute_fa2_citation_accuracy(report_text: str, memory: List[Dict[str, Any]]) -> Optional[float]:
    """FA-2 Citation Accuracy: verified_citations / total_citations * 100"""
    citations = re.findall(r'\[Source:\s*([^\]]+)\]', report_text, re.I)
    if not citations: return None
    
    sources_in_memory = set()
    for m in memory:
        output = m.get("tool_output") or m.get("output")
        if output:
            src = output.get("source", "").lower().replace("_", " ")
            if src: sources_in_memory.add(src)
        if m.get("tool_name"):
            sources_in_memory.add(m.get("tool_name").lower().replace("_", " "))
    
    verified = 0
    for c in citations:
        c_norm = c.lower().strip()
        if c_norm in sources_in_memory or any(s in c_norm or c_norm in s for s in sources_in_memory):
            verified += 1
    return (verified / len(citations)) * 100.0

def compute_fa3_temporal_accuracy(report_text: str, source_dates: List[str]) -> Optional[float]:
    """FA-3 Temporal Accuracy: correct_dates / total_dates * 100"""
    dates = extract_dates_from_text(report_text)
    if not dates: return None
    
    norm_source_dates = [sd.lower().replace(" ", "") for sd in source_dates]
    correct = 0
    for d in dates:
        d_norm = d.lower().replace(" ", "")
        if any(d_norm in sd or sd in d_norm for sd in norm_source_dates):
            correct += 1
    return (correct / len(dates)) * 100.0

def compute_fa4_hallucination_rate(report_text: str, source_values: List[float], source_dates: List[str]) -> Optional[float]:
    """FA-4 Hallucination Rate: unsupported_claims / total_claims * 100"""
    sentences = [s.strip() for s in re.split(r'[.!?]', report_text) if len(s.strip()) > 20]
    if not sentences: return None
    unsupported = 0
    for s in sentences:
        nums = extract_numbers_from_text(s)
        dts = extract_dates_from_text(s)
        if nums or dts:
            num_match = any(any(abs(n - sv) / max(1e-9, abs(sv)) <= 1e-2 for sv in source_values) for n in nums) if nums else True
            date_match = any(any(d in sd or sd in d for sd in source_dates) for d in dts) if dts else True
            if not (num_match and date_match):
                unsupported += 1
    return (unsupported / len(sentences)) * 100.0

def compute_sq1_source_diversity(memory: List[Dict[str, Any]]) -> Optional[float]:
    """SQ-1 Source Diversity: unique_source_types_used / total_possible_source_types"""
    source_types = set()
    for m in memory:
        output = m.get("tool_output") or m.get("output")
        if output and output.get("source"):
            source_types.add(output.get("source"))
    if not source_types: return None
    total_possible = 4.0 # SEC, Transcript, News, Web/Data
    return len(source_types) / total_possible

def compute_sq2_source_recency(memory: List[Dict[str, Any]]) -> Optional[float]:
    """SQ-2 Source Recency: average_age_of_sources_in_days"""
    ages = []
    now = datetime.datetime.now(datetime.timezone.utc)
    for m in memory:
        output = m.get("tool_output") or m.get("output")
        if output and output.get("fetched_at"):
            try:
                fetched_at = datetime.datetime.fromisoformat(output["fetched_at"].replace("Z", "+00:00"))
                ages.append((now - fetched_at).days)
            except: continue
    if not ages: return None
    return sum(ages) / len(ages)

def compute_sq3_source_authority(memory: List[Dict[str, Any]]) -> Optional[float]:
    """SQ-3 Source Authority: weighted average using: SEC=1.0, Transcripts=0.85, Major News=0.7, Other=0.5"""
    tiers = {
        "sec_edgar": 1.0, "sec": 1.0,
        "transcript": 0.85,
        "news": 0.7,
        "google_search": 0.5, "web": 0.5
    }
    scores = []
    for m in memory:
        output = m.get("tool_output") or m.get("output")
        if output:
            src = output.get("source", "").lower()
            if src:
                scores.append(tiers.get(src, 0.5))
    if not scores: return None
    return sum(scores) / len(scores)

def compute_ab1_conflict_detection_rate(report_dict: Dict[str, Any], memory: List[Dict[str, Any]]) -> Optional[float]:
    """AB-1 Conflict Detection: conflicts_detected / actual_conflicts * 100"""
    # Heuristic for actual conflicts: any metric mentioned in multiple sources with different values
    metric_values = {}
    for m in memory:
        output = m.get("tool_output") or m.get("output")
        if output and output.get("data"):
            # Simplified: check for same keys in data across sources
            pass # Complex to implement accurately without strict schema
    
    # For now, we'll use a proxy: if there are multiple sources, assume there's at least one potential conflict
    # or use the number of conflicts found by synthesis engine if available
    detected = len(report_dict.get("sections", {}).get("data_conflicts", {}).get("conflict_items", []))
    actual = report_dict.get("metadata", {}).get("actual_conflicts_count")
    
    if actual is None:
        # Fallback: if we can't determine 'actual', we can't compute this accurately
        return None
        
    return (detected / max(1, actual)) * 100.0

def compute_ab2_resolution_quality(report_dict: Dict[str, Any]) -> Optional[float]:
    """AB-2 Resolution Quality: properly_resolved / total_detected * 100"""
    conflicts = report_dict.get("sections", {}).get("data_conflicts", {}).get("conflict_items", [])
    if not conflicts: return None
    resolved = 0
    narrative = report_dict.get("sections", {}).get("data_conflicts", {}).get("narrative", "") or ""
    if len(narrative) > 50:
        resolved = len(conflicts) 
    return (resolved / len(conflicts)) * 100.0

def compute_ab3_bias_neutrality(report_text: str) -> Optional[float]:
    """AB-3 Bias Neutrality: 1 - (abs(positive_claims - negative_claims) / total_claims)"""
    pos_words = len(re.findall(r'\b(growth|positive|optimistic|strong|increase|beat|exceed)\b', report_text, re.I))
    neg_words = len(re.findall(r'\b(decline|negative|weak|decrease|miss|below|risk|headwind)\b', report_text, re.I))
    total = pos_words + neg_words
    if total == 0: return None
    return 1.0 - (abs(pos_words - neg_words) / total)

def compute_ab4_memory_utilization(memory: List[Dict[str, Any]]) -> Optional[float]:
    """AB-4 Memory Utilization: memory_hits / total_api_calls"""
    total_calls = sum(1 for m in memory if m.get("action") == "tool" or (m.get("decision") and m["decision"].get("action") == "tool"))
    if total_calls == 0: return None
    hits = sum(1 for m in memory if "previous" in str(m.get("decision", {}).get("thought", "")).lower() or m.get("memory_hit", False))
    return hits / total_calls

def compute_ab5_tool_efficiency(memory: List[Dict[str, Any]]) -> Optional[float]:
    """AB-5 Tool Efficiency: unique_tools_used / total_tool_calls"""
    tool_calls = [m for m in memory if m.get("action") == "tool" or (m.get("decision") and m["decision"].get("action") == "tool")]
    if not tool_calls: return None
    unique_tools = len(set(m.get("tool_name") or m.get("decision", {}).get("tool_name") for m in tool_calls))
    return unique_tools / len(tool_calls)

def compute_pf1_response_time(elapsed_sec: float) -> Optional[float]:
    """PF-1 Response Time: total_seconds"""
    if elapsed_sec <= 0: return None
    return elapsed_sec

def compute_pf2_token_efficiency(run_data: Dict[str, Any], report_text: str) -> Optional[float]:
    """PF-2 Token Efficiency: useful_output_tokens / total_tokens"""
    total_tokens = run_data.get("usage", {}).get("total_tokens")
    # In many cases, we might not have exact token counts per step, but total for the run
    if not total_tokens:
        # Heuristic if tokens missing
        return None
    
    # 'useful' tokens can be approximated by report length
    useful_tokens = len(report_text) / 4.0 # 1 token ~= 4 chars
    return useful_tokens / total_tokens

def compute_pf3_recovery_rate(memory: List[Dict[str, Any]]) -> Optional[float]:
    """PF-3: Error Recovery Rate = (recovered_errors / total_errors) * 100"""
    total_errors = 0
    recovered_errors = 0
    
    error_indices = []
    for i, m in enumerate(memory):
        has_error = "error" in m or (isinstance(m.get("tool_output"), dict) and "error" in m["tool_output"])
        if has_error:
            error_indices.append(i)
            total_errors += 1
            
    if total_errors == 0: return None
        
    for idx in error_indices:
        err_item = memory[idx]
        failed_tool = err_item.get("decision", {}).get("tool_name")
        
        for later_idx in range(idx + 1, len(memory)):
            later_item = memory[later_idx]
            if failed_tool and later_item.get("decision", {}).get("tool_name") == failed_tool:
                out = later_item.get("tool_output")
                if out and not (isinstance(out, dict) and "error" in out):
                    recovered_errors += 1
                    break
            if later_item.get("decision", {}).get("action") == "done":
                recovered_errors += 1
                break
                
    return (recovered_errors / total_errors) * 100.0

def calculate_metrics(report_dict: Dict[str, Any], run_data: Dict[str, Any]) -> Dict[str, Union[float, str]]:
    """
    Computes all ZeTheta rubric metrics (FA-1 through PF-3).
    """
    memory = run_data.get("memory", [])
    elapsed_sec = run_data.get("elapsed_sec", 0)
    report_text = report_dict.get("markdown", "")
    
    source_values = get_all_source_data(memory)
    source_dates = get_all_source_dates(memory)
    
    raw_metrics = {
        "FA-1_numerical_accuracy": compute_fa1_numerical_accuracy(report_text, source_values),
        "FA-2_citation_accuracy": compute_fa2_citation_accuracy(report_text, memory),
        "FA-3_temporal_accuracy": compute_fa3_temporal_accuracy(report_text, source_dates),
        "FA-4_hallucination_rate": compute_fa4_hallucination_rate(report_text, source_values, source_dates),
        "SQ-1_source_diversity": compute_sq1_source_diversity(memory),
        "SQ-2_source_recency_days": compute_sq2_source_recency(memory),
        "SQ-3_source_authority": compute_sq3_source_authority(memory),
        "AB-1_conflict_detection": compute_ab1_conflict_detection_rate(report_dict, memory),
        "AB-2_resolution_quality": compute_ab2_resolution_quality(report_dict),
        "AB-3_bias_neutrality": compute_ab3_bias_neutrality(report_text),
        "AB-4_memory_utilization": compute_ab4_memory_utilization(memory),
        "AB-5_tool_efficiency": compute_ab5_tool_efficiency(memory),
        "PF-1_response_time": compute_pf1_response_time(elapsed_sec),
        "PF-2_token_efficiency": compute_pf2_token_efficiency(run_data, report_text),
        "PF-3_error_recovery": compute_pf3_recovery_rate(memory)
    }
    
    final_metrics = {}
    for k, v in raw_metrics.items():
        if v is None:
            final_metrics[k] = NOT_COMPUTED
        else:
            final_metrics[k] = round(v, 4)
            
    return final_metrics

def evaluate_run(run_data: Dict[str, Any], report_dict: Dict[str, Any]) -> Dict[str, Union[float, str]]:
    """Master evaluation function."""
    return calculate_metrics(report_dict, run_data)
