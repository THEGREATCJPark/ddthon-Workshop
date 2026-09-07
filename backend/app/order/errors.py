"""Framework-agnostic domain errors for U2, mapped to the contract error codes (§4).

Routers translate these into HTTP status + ErrorResponse `{error:{code,message}}`.
Kept import-light so services/repositories stay testable without FastAPI.
"""
from __future__ import annotations


class DomainError(Exception):
    """Base domain error carrying a contract error code and HTTP status."""

    code = "VALIDATION_ERROR"
    http_status = 422

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"
    http_status = 422


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    http_status = 404


class ConflictError(DomainError):
    code = "CONFLICT"
    http_status = 409
