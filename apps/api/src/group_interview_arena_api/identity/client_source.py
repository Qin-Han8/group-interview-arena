import ipaddress

from fastapi import Request

from group_interview_arena_api.core.config import Settings

CLIENT_SOURCE_HEADER = "X-GIA-Client-IP"


class InvalidClientSourceError(Exception):
    pass


def _canonical_ip(value: str) -> str:
    normalized = value.strip()
    if not normalized or "," in normalized:
        raise InvalidClientSourceError
    try:
        return ipaddress.ip_address(normalized).compressed
    except ValueError:
        raise InvalidClientSourceError from None


def resolve_client_source(request: Request, settings: Settings) -> str:
    if settings.auth_trusted_caddy_mode:
        values = request.headers.getlist(CLIENT_SOURCE_HEADER)
        if len(values) != 1:
            raise InvalidClientSourceError
        return _canonical_ip(values[0])

    client = request.client
    if client is None:
        raise InvalidClientSourceError
    return _canonical_ip(client.host)
