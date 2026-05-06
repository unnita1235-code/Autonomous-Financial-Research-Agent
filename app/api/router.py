"""
app/api/router.py
─────────────────
FastAPI routes for the integration layer.
"""

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Request as FastAPIRequest

from app.models import ResearchRequest, StatusResponse, ReportResponse, ApiResponse
from app.pipeline import JOB_STORE, run_research_pipeline
from app.limiter import limiter

router = APIRouter()


@router.post("/research", response_model=ApiResponse)
@limiter.limit("5/minute")
async def start_research(
    request: Request,
    payload: ResearchRequest,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Start a new research pipeline job.
    
    Validates the ticker, generates a unique job ID, and queues
    the job in the background.
    """
    job_id = str(uuid.uuid4())
    
    # We access the global state to pass to the background task
    app_state = request.app.state
    vector_store = getattr(app_state, "vector_store", None)
    db_engine = getattr(app_state, "db_engine", None)
    
    # Initial job status
    JOB_STORE[job_id] = {"status": "queued", "error": None, "report": None}
    
    # Add to background tasks
    background_tasks.add_task(
        run_research_pipeline,
        job_id=job_id,
        query=payload.query,
        ticker=payload.ticker,
        vector_store=vector_store,
        db_engine=db_engine,
    )
    
    return ApiResponse(
        success=True,
        data={"job_id": job_id, "message": "Research job queued successfully."},
        error=None,
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
@limiter.limit("5/minute")
async def get_status(request: Request, job_id: str) -> Any:
    """
    Retrieve the current status of a background research job.
    """
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
        
    return StatusResponse(
        success=True,
        data={
            "job_id": job_id,
            "status": job["status"]
        },
        error=job.get("error")
    )


@router.get("/report/{job_id}", response_model=ReportResponse)
@limiter.limit("5/minute")
async def get_report(request: Request, job_id: str) -> Any:
    """
    Retrieve the completed report for a background research job.
    Returns HTTP 202 if the job is still queued or running.
    """
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
        
    if job["status"] in ("queued", "running"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=202,
            content=ReportResponse(
                success=True,
                data=None,
                error=f"Job is currently {job['status']}."
            ).model_dump()
        )
        
    if job["status"] == "failed":
        return ReportResponse(
            success=False,
            data=None,
            error=job.get("error", "Job failed with an unknown error.")
        )
        
    return ReportResponse(
        success=True,
        data=job.get("report"),
        error=None
    )


@router.get("/health", response_model=ApiResponse)
@limiter.limit("5/minute")
async def health_check(request: Request) -> Any:
    """
    Health check endpoint to verify the API is running.
    """
    return ApiResponse(
        success=True,
        data={"status": "ok", "version": "1.0.0"},
        error=None,
    )
