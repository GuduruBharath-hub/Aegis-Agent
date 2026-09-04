from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.api.schemas import ErrorBody, ErrorEnvelope, ErrorKind


@dataclass(frozen=True, slots=True)
class ApiError(Exception):
    status_code: int
    kind: ErrorKind
    code: str
    message: str
    job_id: str | None = None
    retryable: bool = False


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        del request
        return _response(
            exc.status_code,
            ErrorBody(
                kind=exc.kind,
                code=exc.code,
                message=exc.message,
                job_id=exc.job_id,
                retryable=exc.retryable,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        first = exc.errors()[0] if exc.errors() else {}
        return _response(
            422,
            ErrorBody(
                kind="validation",
                code="request_validation_failed",
                message=str(first.get("msg", "request validation failed")),
            ),
        )


def _response(status_code: int, error: ErrorBody) -> JSONResponse:
    envelope = ErrorEnvelope(error=error)
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
    )
