"""
app/models.py
─────────────
Pydantic models for API request and response validation.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=500, description="The research question")
    ticker: str = Field(..., description="Stock ticker symbol (1-5 letters)")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.upper().strip()
        if not v.isalpha() or not (1 <= len(v) <= 5):
            raise ValueError("ticker must be 1-5 alphabetic characters")
        return v

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        try:
            from security.prompt_injection_shield import shield
            if not shield.is_safe(v):
                raise ValueError("Query contains potentially unsafe content")
        except ImportError:
            pass
        return v


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
