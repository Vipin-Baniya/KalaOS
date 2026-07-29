"""Async job endpoints for heavy AI/media processing workloads."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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


@router.websocket("/ws/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job status updates.
    Requires valid session token passed as query parameter.

    Authentication flow:
    1. Client connects: ws://host/jobs/ws/{job_id}?token={token}
    2. Server validates token and verifies job ownership
    3. If valid: accept connection, send updates
    4. If invalid: reject with appropriate close code
    """
    # Extract token from query parameters
    token = websocket.query_params.get("token")

    # Step 1: Validate session token
    try:
        if not token or not auth_service.get_user(token):
            await websocket.close(code=4001, reason="Unauthorized")
            logger.warning(f"WebSocket connection rejected: invalid token for job {job_id}")
            return
    except Exception as exc:
        await websocket.close(code=4001, reason="Unauthorized")
        logger.warning(f"WebSocket token validation error for job {job_id}: {exc}")
        return

    # Step 2: Verify job exists
    try:
        job = get_job(job_id)
        if not job:
            await websocket.close(code=4004, reason="Not Found")
            logger.warning(f"WebSocket connection rejected: job {job_id} not found")
            return
    except Exception as exc:
        await websocket.close(code=4004, reason="Not Found")
        logger.warning(f"WebSocket job lookup error for {job_id}: {exc}")
        return

    # Step 3: Verify user owns the job (basic ownership check)
    # In a real implementation, you would check job ownership from the database
    # For now, we accept any authenticated user (can be enhanced with ownership verification)

    # Accept the connection
    await websocket.accept()
    logger.info(f"WebSocket connection established for job {job_id}")

    try:
        while True:
            # Check for client messages (e.g., refresh requests)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                try:
                    message = json.loads(data)
                    if message.get("action") == "refresh":
                        # Client requested a status refresh
                        pass
                except json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                # No message received within timeout, send a status update anyway
                pass

            # Get current job status
            try:
                job = get_job(job_id)
                if job:
                    # Send status update to client
                    await websocket.send_json({
                        "job_id": job["id"],
                        "status": job["status"],
                        "progress": job.get("progress", 0),
                        "message": job.get("message", ""),
                        "timestamp": int(time.time()),
                    })

                    # If job is complete, close connection
                    if job["status"] in ("completed", "failed"):
                        await websocket.close(code=1000, reason="Job complete")
                        logger.info(f"WebSocket connection closed: job {job_id} complete")
                        break
                else:
                    # Job no longer exists
                    await websocket.close(code=4004, reason="Job not found")
                    logger.info(f"WebSocket connection closed: job {job_id} deleted")
                    break

            except Exception as exc:
                logger.error(f"Error sending job status for {job_id}: {exc}")
                await websocket.close(code=1011, reason="Server error")
                break

            # Wait before next update
            await asyncio.sleep(2.0)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from job {job_id}")
    except Exception as exc:
        logger.error(f"WebSocket error for job {job_id}: {exc}")
        try:
            await websocket.close(code=1011, reason="Server error")
        except Exception:
            pass
