from enum import StrEnum
from typing import Self
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GIA_API_", extra="ignore")

    database_url: SecretStr


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GIA_API_", extra="ignore")

    environment: Environment = Environment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    cors_origins: tuple[str, ...] = ()
    session_cookie_secure: bool = False
    otel_tracing_enabled: bool = False
    otel_service_name: str = "group-interview-arena-api"
    otel_otlp_http_endpoint: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def require_secure_production_session_cookie(self) -> Self:
        if (
            self.environment is Environment.PRODUCTION
            and not self.session_cookie_secure
        ):
            raise ValueError("Production sessions require secure cookies")
        return self

    @model_validator(mode="after")
    def require_tracing_endpoint_when_enabled(self) -> Self:
        if self.otel_tracing_enabled and self.otel_otlp_http_endpoint is None:
            raise ValueError("Tracing requires an OTLP HTTP endpoint")
        return self

    @field_validator("otel_service_name")
    @classmethod
    def validate_otel_service_name(cls, service_name: str) -> str:
        normalized = service_name.strip()
        if not normalized or len(normalized) > 128:
            raise ValueError("OTel service name must contain 1 to 128 characters")
        return normalized

    @field_validator("otel_otlp_http_endpoint")
    @classmethod
    def validate_otel_otlp_http_endpoint(
        cls,
        endpoint: AnyHttpUrl | None,
    ) -> AnyHttpUrl | None:
        if endpoint is None:
            return None
        if (
            endpoint.username is not None
            or endpoint.password is not None
            or endpoint.query is not None
            or endpoint.fragment is not None
        ):
            raise ValueError(
                "OTLP HTTP endpoint must not contain userinfo, query, or fragment"
            )
        return endpoint

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: tuple[str, ...]) -> tuple[str, ...]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "CORS origins must be explicit HTTP(S) origins without paths"
                )

        return origins
