from collections.abc import Callable, Sequence
from typing import Annotated

from fastapi import Header, Request, status

from group_interview_arena_api.core.errors import ApiError, ErrorCode

CSRF_HEADER_NAME = "X-GIA-CSRF"
CSRF_HEADER_VALUE = "1"
CSRF_OPENAPI_EXTRA: dict[str, object] = {
    "parameters": [
        {
            "name": CSRF_HEADER_NAME,
            "in": "header",
            "required": True,
            "schema": {"type": "string", "const": CSRF_HEADER_VALUE},
            "description": "Required first-party browser request marker.",
        }
    ]
}

CsrfHeader = Annotated[
    str | None,
    Header(alias=CSRF_HEADER_NAME, include_in_schema=False),
]


def _csrf_rejected() -> ApiError:
    return ApiError(
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.CSRF_REJECTED,
        message="Browser request could not be authorized.",
    )


def has_exact_trusted_origin(
    origin_values: Sequence[str],
    trusted_origins: tuple[str, ...],
) -> bool:
    return (
        len(origin_values) == 1
        and origin_values[0] != "null"
        and origin_values[0] in frozenset(trusted_origins)
    )


def create_browser_csrf_guard(
    trusted_origins: tuple[str, ...],
) -> Callable[..., None]:
    def require_browser_csrf(
        request: Request,
        csrf_header: CsrfHeader = None,
    ) -> None:
        origins = request.headers.getlist("origin")
        csrf_headers = request.headers.getlist(CSRF_HEADER_NAME)
        if (
            not has_exact_trusted_origin(origins, trusted_origins)
            or len(csrf_headers) != 1
            or csrf_header != CSRF_HEADER_VALUE
        ):
            raise _csrf_rejected()

    return require_browser_csrf
