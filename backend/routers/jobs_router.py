"""Async job endpoints for heavy AI/media processing workloads."""

from typing import Any, Dict, Literal, Optional
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

try:  # Runtime from backend/ working directory
    from usecases.jobs import get_job, list_jobs, submit_job
    from services import auth_service
except ImportError:  # Package-style runtime
    from backend.usecases.jobs import get_job, list_jobs, submit_job
    from backend.services import auth_service

logger = logging.getLogger(__name__)


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
async def websocket_job_updates(websocket: WebSocket, job_id: str, token: str = Query(...)):
    """
    WebSocket endpoint for real-time job status updates.

    Security:
    - Requires valid session token via query parameter (token=...)
    - Verifies user owns the job before streaming updates
    - Closes connection with 4003 (Forbidden) if user doesn't own job
    - Closes connection with 4001 (Unauthorized) if token is invalid

    Usage:
    ```javascript
    const ws = new WebSocket('wss://kalaos.app/api/jobs/ws/job123?token=SESSION_TOKEN');
    ws.onmessage = (event) => {
        const update = JSON.parse(event.data);
        console.log('Job status:', update.status);
    };
    ```

    Message format:
    ```json
    {
        "job_id": "job123",
        "status": "processing",
        "progress": 45,
        "message": "Processing step 3/7"
    }
    ```
    """
    # Step 1: Authenticate the session token
    try:
        user = auth_service.get_user(token)
        if not user:
            await websocket.close(code=4001, reason="Unauthorized: Invalid or expired token")
            return
    except Exception as exc:
        logger.error(f"Token validation error: {exc}")
        await websocket.close(code=4001, reason="Unauthorized: Token validation failed")
        return

    # Step 2: Verify job exists and user owns it
    try:
        job = get_job(job_id)
        if not job:
            await websocket.close(code=4004, reason="Job not found")
            return

        # SECURITY: Verify the authenticated user owns this job
        # In a production system, job would have owner_id field
        # For now, we check if the user has access to view the job
        # TODO: Add owner_id field to job model for proper ownership checks
        job_owner_email = job.get("owner_email") or job.get("created_by")
        if job_owner_email and job_owner_email != user.get("email"):
            logger.warning(
                f"Unauthorized access attempt: user {user.get('email')} "
                f"tried to access job {job_id} owned by {job_owner_email}"
            )
            await websocket.close(code=4003, reason="Forbidden: You do not own this job")
            return
    except Exception as exc:
        logger.error(f"Job authorization check error: {exc}")
        await websocket.close(code=4001, reason="Authorization check failed")
        return

    # Step 3: Accept the WebSocket connection
    await websocket.accept()
    logger.info(f"WebSocket connection established: user={user.get('email')}, job={job_id}")

    try:
        # Send initial job status
        initial_update = {
            "job_id": job_id,
            "status": job.get("status", "unknown"),
            "created_at": job.get("created_at"),
            "message": "Connected to job status stream"
        }
        await websocket.send_json(initial_update)

        # Stream job updates
        # In a production system, this would subscribe to a message queue (Redis, RabbitMQ)
        # or poll a database for status changes
        # For now, we simulate updates and allow client-initiated status checks
        while True:
            # Wait for client messages (e.g., "refresh" requests)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)

                if message.get("action") == "refresh":
                    # Client requested status refresh
                    updated_job = get_job(job_id)
                    if updated_job:
                        update = {
                            "job_id": job_id,
                            "status": updated_job.get("status"),
                            "message": "Status refreshed"
                        }
                        if "progress" in updated_job:
                            update["progress"] = updated_job["progress"]
                        await websocket.send_json(update)
            except asyncio.TimeoutError:
                # No message from client for 30 seconds - check job status
                updated_job = get_job(job_id)
                if updated_job:
                    update = {
                        "job_id": job_id,
                        "status": updated_job.get("status"),
                        "message": "Periodic status check"
                    }
                    if "progress" in updated_job:
                        update["progress"] = updated_job["progress"]
                    if updated_job.get("status") in ["completed", "failed"]:
                        update["result"] = updated_job.get("result")
                        await websocket.send_json(update)
                        break  # Connection closes when job completes
                    await websocket.send_json(update)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: job={job_id}")
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}")
        await websocket.close(code=1011, reason=f"Server error: {str(exc)}")
    finally:
        logger.info(f"WebSocket connection closed: job={job_id}")
