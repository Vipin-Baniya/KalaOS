"""Async job endpoints for heavy AI/media processing workloads."""

from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

try:  # Runtime from backend/ working directory
    from usecases.jobs import get_job, list_jobs, submit_job
    from services import auth_service
except ImportError:  # Package-style runtime
    from backend.usecases.jobs import get_job, list_jobs, submit_job
    from backend.services import auth_service


router = APIRouter(prefix="/jobs", tags=["jobs"])

JobPriority = Literal["low", "normal", "high"]
JobGpuClass = Literal["small", "medium", "high"]


def _require_auth(token: str) -> None:
    """Validate the session token, matching the auth pattern used by the
    rest of the API (see auth_service.get_user / main.py's /auth/me)."""
    if not token or not auth_service.get_user(token):
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")


class JobSubmitRequest(BaseModel):
    token: str
    task_type: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: JobPriority = "normal"
    gpu_class: JobGpuClass = "small"


class JobSubmitResponse(BaseModel):
    id: str
    task_type: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    priority: str
    gpu_class: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/submit", response_model=JobSubmitResponse, summary="Submit an async AI/media job")
def submit_async_job(request: JobSubmitRequest):
    _require_auth(request.token)
    try:
        return submit_job(
            task_type=request.task_type,
            payload=request.payload,
            priority=request.priority,
            gpu_class=request.gpu_class,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/{job_id}", response_model=JobSubmitResponse, summary="Get async job status")
def get_async_job(job_id: str, token: str):
    _require_auth(token)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("", response_model=list[JobSubmitResponse], summary="List recent async jobs")
def list_async_jobs(token: str, limit: int = Query(default=50, ge=1, le=200)):
    _require_auth(token)
    return list_jobs(limit=limit)
