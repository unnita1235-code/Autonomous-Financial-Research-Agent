"""
app/pipeline.py
───────────────
Orchestrates the background research pipeline phases.
Tracks job status in-memory.
"""

import logging
from typing import Any, Dict

from agents import run_agent, LLMClient
from synthesis import synthesize
from reports import generate_report, save_report, save_findings
from tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)

# In-memory store for tracking jobs.
# NOTE: In production, this should be replaced by Redis.
JOB_STORE: Dict[str, Dict[str, Any]] = {}


async def run_research_pipeline(
    job_id: str,
    query: str,
    ticker: str,
    vector_store: Any,
    db_engine: Any,
) -> None:
    """
    Execute the entire research pipeline sequentially.
    Updates JOB_STORE at each step and catches all exceptions.
    """
    try:
        JOB_STORE[job_id] = {"status": "running", "error": None, "report": None}
        logger.info(f"Job {job_id} started for ticker {ticker}: {query}")

        # Initialize LLM Client
        llm_client = LLMClient()

        # Phase 2 & 3: Run ReAct Agent + Semantic Memory
        logger.info(f"Job {job_id}: Running agent loop...")
        agent_result = await run_agent(
            query=query,
            tool_registry=TOOL_REGISTRY,
            llm_client=llm_client,
            vector_store=vector_store,
        )

        # Ensure agent completed without error
        if agent_result.get("status") == "error":
            # Find the first error in memory
            err_msg = "Agent loop encountered an error."
            for m in agent_result.get("memory", []):
                if "error" in m:
                    err_msg = m["error"]
                    break
            raise RuntimeError(err_msg)

        # Phase 4: Synthesize Data
        logger.info(f"Job {job_id}: Synthesizing data...")
        synthesis_result = synthesize(memory=agent_result["memory"])

        # Phase 5: Generate Report
        logger.info(f"Job {job_id}: Generating report...")
        report = generate_report(
            query=query,
            ticker=ticker,
            synthesis=synthesis_result,
            llm_client=llm_client,
        )

        # Persistence: Save Report to PostgreSQL
        logger.info(f"Job {job_id}: Saving report to database...")
        db_report_id = save_report(report=report)
        if db_report_id:
            save_findings(report_id=db_report_id, metrics=synthesis_result.get("metrics", {}))

        # Mark Complete
        JOB_STORE[job_id]["status"] = "complete"
        JOB_STORE[job_id]["report"] = report
        logger.info(f"Job {job_id} successfully completed.")

    except Exception as exc:
        logger.error(f"Job {job_id} failed: {exc}", exc_info=True)
        JOB_STORE[job_id] = {
            "status": "failed",
            "error": str(exc),
            "report": None,
        }
