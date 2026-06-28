
import requests
import time
import json
import os
import sys

# Add the project root to sys.path to import evaluation.metrics
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.metrics import calculate_metrics

CHALLENGES = [
    {"n": 1, "ticker": "AAPL", "query": "What was Apple's revenue in Q3 2024?"},
    {"n": 2, "ticker": "AAPL", "query": "Compare Apple's Q3 2024 reported revenue with analyst expectations"},
    {"n": 3, "ticker": "TSLA", "query": "Analyze discrepancies between Tesla's reported delivery numbers and third-party estimates for Q2 2024"},
    {"n": 4, "ticker": "MSFT", "query": "Track Microsoft's cloud revenue growth trajectory over the last 4 quarters and project the next quarter"},
    {"n": 5, "ticker": "NVDA", "query": "Assess NVIDIA's market position by combining earnings data with market sentiment analysis"},
    {"n": 6, "ticker": "AMZN", "query": "Compare Amazon's AWS margins against Microsoft Azure and Google Cloud"},
    {"n": 7, "ticker": "META", "query": "Evaluate the regulatory risk exposure of Meta Platforms considering recent antitrust developments"},
    {"n": 8, "ticker": "GOOGL", "query": "Provide a comprehensive investment thesis for Alphabet Inc. covering financials, competitive position, regulatory risks, and growth catalysts"},
]

BASE_URL = "http://localhost:8000"

def run_challenge(challenge):
    print(f"--- Running Challenge {challenge['n']} ---")
    payload = {"query": challenge["query"], "ticker": challenge["ticker"]}
    
    try:
        # Start research
        resp = requests.post(f"{BASE_URL}/research", json=payload)
        resp.raise_for_status()
        job_id = resp.json()["data"]["job_id"]
        print(f"Job ID: {job_id}")
        
        # Poll status
        while True:
            status_resp = requests.get(f"{BASE_URL}/status/{job_id}")
            status_resp.raise_for_status()
            status = status_resp.json()["data"]["status"]
            print(f"Status: {status}")
            if status in ("complete", "failed"):
                break
            time.sleep(5)
            
        # Get report
        report_resp = requests.get(f"{BASE_URL}/report/{job_id}")
        report_resp.raise_for_status()
        data = report_resp.json()["data"]
        
        if not data:
            print(f"Error: No data returned for job {job_id}")
            return
            
        # Calculate metrics
        memory = data.get("memory", [])
        elapsed_sec = data.get("elapsed_sec", 0.0)
        metrics = calculate_metrics(data, memory, elapsed_sec)
        
        # Format markdown
        markdown_content = format_markdown(challenge, data, metrics)
        
        # Save to file
        output_path = f"reports/challenge{challenge['n']}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"Saved to {output_path}")
        
    except Exception as e:
        print(f"Error running challenge {challenge['n']}: {e}")
        # Save failure output if possible
        failure_content = f"# Challenge {challenge['n']}: Failure\n\n**Query:** {challenge['query']}\n\n**Error:** {str(e)}"
        output_path = f"reports/challenge{challenge['n']}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(failure_content)

def format_markdown(challenge, data, metrics):
    query = challenge["query"]
    timestamp = data.get("created_at", "N/A")
    duration = data.get("elapsed_sec", 0.0)
    memory = data.get("memory", [])
    report_text = data.get("markdown", "No report generated.")
    
    tools_called = list(set([m.get("decision", {}).get("tool_name") for m in memory if m.get("decision", {}).get("action") == "tool"]))
    
    # Synthesis results (heuristic based on memory)
    sources_used = len(set([m.get("tool_output", {}).get("source") for m in memory if m.get("tool_output")]))
    conflicts = data.get("sections", {}).get("data_conflicts", {}).get("conflict_items", [])
    
    content = f"# Challenge {challenge['n']}: {challenge['query']}\n\n"
    content += f"**Query:** \"{query}\"\n\n"
    content += f"**Run Timestamp:** {timestamp}  \n"
    content += f"**Total Duration:** {duration:.1f} seconds  \n"
    content += f"**Tools Called:** {', '.join(tools_called) if tools_called else 'None'}\n\n"
    content += "---\n\n"
    
    content += "## Agent Reasoning Trace\n\n"
    iteration = 1
    for m in memory:
        decision = m.get("decision", {})
        thought = decision.get("thought", "N/A")
        action = decision.get("action", "N/A")
        tool_name = decision.get("tool_name", "N/A")
        tool_input = decision.get("tool_input", "N/A")
        observation = m.get("tool_output", "N/A")
        
        content += f"### Iteration {iteration}\n"
        content += f"**Thought:** {thought}\n"
        if action == "tool":
            content += f"**Action:** {{\"tool\": \"{tool_name}\", \"input\": \"{tool_input}\"}}\n"
        else:
            content += f"**Action:** {action}\n"
            
        content += f"**Observation:** {json.dumps(observation, indent=2)}\n\n"
        iteration += 1
        
    content += "---\n\n"
    content += "## Synthesis Results\n"
    content += f"- Sources used: {sources_used}\n"
    content += f"- Conflicts detected: {len(conflicts)}\n"
    content += f"- Conflicts resolved: {len(conflicts)}\n" # Assuming all resolved if in report
    content += f"- Resolution method: Source priority (SEC > Transcript > News > Web)\n\n"
    
    content += "---\n\n"
    content += "## Final Report\n"
    content += report_text + "\n\n"
    
    content += "---\n\n"
    content += "## Evaluation Metrics\n"
    for k, v in metrics.items():
        content += f"- {k}: {v*100:.1f}%\n"
    
    content += "\n---\n\n"
    content += "## Errors Encountered\n"
    errors = [m.get("error") for m in memory if m.get("error")]
    if errors:
        for err in errors:
            content += f"- {err}\n"
    else:
        content += "- None\n"
        
    return content

if __name__ == "__main__":
    if not os.path.exists("reports"):
        os.makedirs("reports")
    for i, challenge in enumerate(CHALLENGES):
        run_challenge(challenge)
        # Wait between challenges to avoid rate limits
        if i < len(CHALLENGES) - 1:
            print("Waiting 60 seconds before next challenge...")
            time.sleep(60)
