import logging
from typing import Any

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _make_json_safe(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _make_json_safe(val) for key, val in value.items()}
    return str(value)


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    payload = {
        "success": False,
        "detail": message,
        "error": {
            "code": code,
            "message": message,
            "details": _make_json_safe(details),
        },
        "request_id": _get_request_id(request),
    }

    return JSONResponse(
        status_code=status_code,
        content=payload,
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    detail = (
        exc.detail
        if isinstance(exc.detail, str)
        else "Request failed"
    )

    return _error_response(
        request=request,
        status_code=exc.status_code,
        code="HTTP_ERROR",
        message=detail,
        details=exc.detail,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Invalid request",
        details=exc.errors(),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled exception while processing request")
    return _error_response(
        request=request,
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
        details=[],
    )


async def rate_limit_exception_handler(
    request: Request,
    _: RateLimitExceeded,
) -> JSONResponse:
    return _error_response(
        request=request,
        status_code=429,
        code="RATE_LIMIT_EXCEEDED",
        message="Too many requests.",
        details=[],
    )