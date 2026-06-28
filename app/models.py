"""
app/models.py
─────────────
Pydantic models for API request and response validation.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """
    Request model for starting a new research job.
    """
    query: str = Field(..., description="The user's research question")
    ticker: str = Field(
        ...,
        pattern=r"^[A-Z]{1,5}$",
        description="The target stock ticker (1-5 uppercase letters)",
    )


class ApiResponse(BaseModel):
    """
    Standard response envelope for all API endpoints.
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StatusData(BaseModel):
    status: str
    job_id: str


class StatusResponse(ApiResponse):
    """
    Response model for checking job status.
    """
    data: Optional[StatusData] = None


class ReportResponse(ApiResponse):
    """
    Response model for fetching a completed report.
    """
    data: Optional[Dict[str, Any]] = None
