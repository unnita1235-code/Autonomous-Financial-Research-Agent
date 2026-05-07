import json
import os
from evaluation.metrics import calculate_metrics
from evaluation.dashboard import generate_dashboard

def test_dashboard_generation():
    # Load sample data
    with open("agent_run_output.json", "r") as f:
        agent_data = json.load(f)
    with open("report.json", "r") as f:
        report_data = json.load(f)
    
    # Calculate metrics
    print("Calculating metrics...")
    metrics = calculate_metrics(
        report_dict=report_data,
        memory=agent_data["memory"],
        elapsed_sec=agent_data.get("elapsed_sec", 45.2)
    )
    
    # Generate dashboard
    output_path = "evaluation/test_dashboard.html"
    print(f"Generating dashboard at {output_path}...")
    generate_dashboard(metrics, output_path)
    
    if os.path.exists(output_path):
        print(f"SUCCESS: Dashboard generated at {os.path.abspath(output_path)}")
    else:
        print("FAILED: Dashboard not generated.")

if __name__ == "__main__":
    test_dashboard_generation()
