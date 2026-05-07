import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Import project modules
from tools import TOOL_REGISTRY
from agents.llm_client import LLMClient
from agents.react_loop import run_agent
from synthesis import synthesize
from reports import generate_report

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("run_challenges")

CHALLENGES = [
    "What was Apple's revenue in Q3 2024?",
    "Compare Apple's Q3 2024 reported revenue with analyst expectations",
    "Analyze discrepancies between Tesla's reported delivery numbers and third-party estimates for Q2 2024",
    "Track Microsoft's cloud revenue growth trajectory over the last 4 quarters and project next quarter",
    "Assess NVIDIA's market position by combining earnings data with market sentiment analysis",
    "Compare Amazon's AWS margins against Microsoft Azure and Google Cloud",
    "Evaluate the regulatory risk exposure of Meta Platforms considering recent antitrust developments",
    "Provide a comprehensive investment thesis for Alphabet Inc covering financials competitive position regulatory risks and growth catalysts"
]

TICKER_MAP = {
    "Apple": "AAPL",
    "Tesla": "TSLA",
    "Microsoft": "MSFT",
    "NVIDIA": "NVDA",
    "Amazon": "AMZN",
    "Meta": "META",
    "Alphabet": "GOOGL",
    "Google": "GOOGL"
}

def get_ticker(query: str) -> str:
    for name, ticker in TICKER_MAP.items():
        if name.lower() in query.lower():
            return ticker
    return "UNKNOWN"

async def run_challenge(query: str, index: int):
    ticker = get_ticker(query)
    start_time = datetime.now()
    start_ts = start_time.strftime("%Y-%m-%d %H:%M:%S")
    
    logger.info(f"=== Running Challenge {index} ===")
    logger.info(f"Query: {query}")
    
    llm_client = None
    agent_result = None
    report = None
    error = None
    
    try:
        llm_client = LLMClient()
        agent_result = await run_agent(
            query=query,
            tool_registry=TOOL_REGISTRY,
            llm_client=llm_client,
            max_iterations=8
        )
        
        if agent_result.get("status") != "error":
            logger.info(f"Synthesizing results for Challenge {index}...")
            synthesis_result = synthesize(memory=agent_result["memory"])
            
            logger.info(f"Generating final report for Challenge {index}...")
            report = generate_report(
                query=query,
                ticker=ticker,
                synthesis=synthesis_result,
                llm_client=llm_client
            )
        else:
            # Try to extract error
            for m in agent_result.get("memory", []):
                if "error" in m:
                    error = m["error"]
                    break
            if not error:
                error = "Unknown agent error"
                
    except Exception as e:
        error = str(e)
        logger.error(f"Challenge {index} failed: {e}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Construct Markdown output
    md_content = []
    md_content.append(f"Timestamp: {start_ts}")
    md_content.append(f"Query: {query}")
    md_content.append(f"Duration: {duration:.2f} seconds")
    md_content.append(f"Status: {agent_result.get('status') if agent_result else 'failed'}")
    md_content.append("")
    md_content.append("## Reasoning Steps")
    
    if agent_result and "memory" in agent_result:
        for step in agent_result["memory"]:
            it = step.get("iteration", "?")
            md_content.append(f"### Iteration {it}")
            
            decision = step.get("decision")
            if decision:
                md_content.append(f"**Thought:** {decision.get('thought', 'N/A')}")
                md_content.append(f"**Action:** {decision.get('action', 'N/A')}")
                if decision.get("tool_name"):
                    md_content.append(f"**Tool:** {decision.get('tool_name')}")
                    md_content.append(f"**Args:** `{json.dumps(decision.get('tool_args'), indent=None)}`")
            
            output = step.get("tool_output")
            md_content.append(f"**Observation:**")
            if output:
                md_content.append("```json")
                md_content.append(json.dumps(output, indent=2))
                md_content.append("```")
            else:
                md_content.append("N/A")
            
            if "error" in step:
                md_content.append(f"**Error:** {step['error']}")
            
            if step.get("fallback_metadata"):
                md_content.append(f"**Fallback Metadata:** `{json.dumps(step.get('fallback_metadata'), indent=None)}`")
                
            md_content.append("---")
    
    md_content.append("")
    md_content.append("## Final Answer/Report")
    if report and "markdown" in report:
        md_content.append(report["markdown"])
    elif error:
        md_content.append(f"### ERROR ENCOUNTERED\n{error}")
    else:
        md_content.append("No final report generated.")

    # Save to file
    filename = f"reports/challenge{index}.md"
    os.makedirs("reports", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
    
    logger.info(f"Saved Challenge {index} to {filename}")

async def main():
    # Ensure reports directory exists
    os.makedirs("reports", exist_ok=True)
    
    for i, query in enumerate(CHALLENGES, 1):
        try:
            await run_challenge(query, i)
        except Exception as e:
            logger.error(f"Fatal error in challenge {i}: {e}")
        
        # Sleep to avoid aggressive rate limiting
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
