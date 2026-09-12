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


class ErrorCode(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_USERNAME = "INVALID_USERNAME"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    USERNAME_UNAVAILABLE = "USERNAME_UNAVAILABLE"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    CSRF_REJECTED = "CSRF_REJECTED"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    QUESTION_NOT_FOUND = "QUESTION_NOT_FOUND"
    INVALID_SESSION_STATE = "INVALID_SESSION_STATE"
    ACTION_ID_CONFLICT = "ACTION_ID_CONFLICT"


class ApiError(Exception):
    def __init__(self, *, status_code: int, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


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


async def api_error_handler(_request: Request, exception: Exception) -> JSONResponse:
    if not isinstance(exception, ApiError):
        raise TypeError("Expected ApiError")

    return error_response(
        status_code=exception.status_code,
        code=exception.code,
        message=exception.message,
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
    _request: Request, _exception: Exception
) -> JSONResponse:
    return error_response(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
    )
