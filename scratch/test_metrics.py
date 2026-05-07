import json
import os
import sys

# Add current directory to path so we can import evaluation.metrics
sys.path.append(os.getcwd())

from evaluation.metrics import evaluate_run

def test_metrics():
    # Load sample data
    try:
        with open("agent_run_output.json", "r") as f:
            run_data = json.load(f)
        
        with open("report.json", "r") as f:
            report_dict = json.load(f)
            
        print("--- Running Evaluation ---")
        metrics = evaluate_run(run_data, report_dict)
        
        print(json.dumps(metrics, indent=2))
        
        # Verify specific metrics from ZeTheta rubric
        required_keys = [
            "FA-1_numerical_accuracy", "FA-2_citation_accuracy", "FA-3_temporal_accuracy", "FA-4_hallucination_rate",
            "SQ-1_source_diversity", "SQ-2_source_recency_score", "SQ-3_source_authority",
            "AB-1_conflict_detection", "AB-2_resolution_quality", "AB-3_bias_neutrality", "AB-4_memory_utilization", "AB-5_tool_efficiency",
            "PF-1_response_time_score", "PF-2_token_efficiency", "PF-3_error_recovery"
        ]
        
        missing = [k for k in required_keys if k not in metrics]
        if missing:
            print(f"FAILED: Missing metrics: {missing}")
        else:
            print("SUCCESS: All required rubric metrics are present.")
            
    except Exception as e:
        print(f"ERROR during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_metrics()
