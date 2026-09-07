"""Standard application errors and error-response envelope (FROZEN contract §4).

Error body shape: {"error": {"code": <str>, "message": <str>}}

U1 provides these error types and the exception-handler registration function.
The handlers are REGISTERED on the FastAPI app by the Integration Lead in main.py
(U1 does not create main.py).
"""
from typing import Any


class AppError(Exception):
    code: str = "INTERNAL"
    http_status: int = 500

    def __init__(self, message: str = "", *, code: str | None = None, http_status: int | None = None):
        self.message = message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        super().__init__(message)


class Unauthorized(AppError):
    code = "UNAUTHORIZED"
    http_status = 401


class Forbidden(AppError):
    code = "FORBIDDEN"
    http_status = 403


class NotFound(AppError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 422


class RateLimited(AppError):
    code = "RATE_LIMITED"
    http_status = 429


class Conflict(AppError):
    code = "CONFLICT"
    http_status = 409


def error_body(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


def register_error_handlers(app) -> None:
    """Register standard exception handlers on a FastAPI app.

    Provided by U1; called by the Integration Lead in main.py (and by tests).
    """
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(AppError)
    async def _handle_app_error(_request, exc: AppError):
        return JSONResponse(status_code=exc.http_status, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_request, _exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", "요청 형식이 올바르지 않습니다."),
        )
