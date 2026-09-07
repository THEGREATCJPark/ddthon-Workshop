"""Translate U2 DomainError -> contract ErrorResponse `{error:{code,message}}` (§4).

Self-contained (no main.py change): routers wrap handler bodies and return this
JSONResponse on DomainError, preserving the exact top-level `error` envelope.
"""
from __future__ import annotations

from fastapi.responses import JSONResponse

from .errors import DomainError


def error_response(exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
