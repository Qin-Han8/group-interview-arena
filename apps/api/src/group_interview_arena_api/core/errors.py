import logging
from enum import StrEnum

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from group_interview_arena_api.core.request_id import (
    create_request_id,
    get_request_id,
)

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


def _current_or_new_request_id() -> str:
    return get_request_id() or create_request_id()


def error_response(*, status_code: int, code: ErrorCode, message: str) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=_current_or_new_request_id(),
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


async def http_exception_handler(
    _request: Request, exception: Exception
) -> JSONResponse:
    if not isinstance(exception, StarletteHTTPException):
        raise TypeError("Expected StarletteHTTPException")

    if exception.status_code == 404:
        return error_response(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Resource not found.",
        )

    if 400 <= exception.status_code < 500:
        return error_response(
            status_code=exception.status_code,
            code=ErrorCode.VALIDATION_ERROR,
            message="Request could not be processed.",
        )

    return error_response(
        status_code=exception.status_code,
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
    )


async def validation_exception_handler(
    _request: Request, exception: Exception
) -> JSONResponse:
    if not isinstance(exception, RequestValidationError):
        raise TypeError("Expected RequestValidationError")

    return error_response(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed.",
    )


async def unexpected_exception_handler(
    request: Request, exception: Exception
) -> JSONResponse:
    logger.error(
        "Unhandled request exception",
        exc_info=(type(exception), exception, exception.__traceback__),
        extra={
            "request_id": _current_or_new_request_id(),
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
        },
    )
    return error_response(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
    )
