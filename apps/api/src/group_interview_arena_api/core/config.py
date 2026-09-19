from enum import StrEnum
from typing import Self
from urllib.parse import urlsplit

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from group_interview_arena_api.modules.discussion_sessions.domain import (
    PhaseDurationPlan,
    SessionStatus,
)


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


class ZhipuProviderSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GIA_API_ZHIPU_", extra="ignore")

    api_key: SecretStr
    model: str

    @field_validator("api_key")
    @classmethod
    def reject_blank_api_key(cls, api_key: SecretStr) -> SecretStr:
        if not api_key.get_secret_value().strip():
            raise ValueError("Zhipu API key must not be blank")
        return api_key

    @field_validator("model")
    @classmethod
    def normalize_model(cls, model: str) -> str:
        normalized = model.strip()
        if not normalized or len(normalized) > 128:
            raise ValueError("Zhipu model must contain 1 to 128 characters")
        return normalized


class SessionPhaseDurations(BaseModel):
    preparation_seconds: int = Field(default=240, gt=0, strict=True)
    opening_statements_seconds: int = Field(default=240, gt=0, strict=True)
    exploration_seconds: int = Field(default=900, gt=0, strict=True)
    conflict_and_evaluation_seconds: int = Field(default=300, gt=0, strict=True)
    convergence_seconds: int = Field(default=180, gt=0, strict=True)
    final_summary_seconds: int = Field(default=60, gt=0, strict=True)

    def to_duration_plan(self) -> PhaseDurationPlan:
        return PhaseDurationPlan.from_seconds(
            {
                SessionStatus.PREPARATION: self.preparation_seconds,
                SessionStatus.OPENING_STATEMENTS: self.opening_statements_seconds,
                SessionStatus.EXPLORATION: self.exploration_seconds,
                SessionStatus.CONFLICT_AND_EVALUATION: (
                    self.conflict_and_evaluation_seconds
                ),
                SessionStatus.CONVERGENCE: self.convergence_seconds,
                SessionStatus.FINAL_SUMMARY: self.final_summary_seconds,
            }
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GIA_API_", extra="ignore")

    environment: Environment = Environment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    cors_origins: tuple[str, ...] = ()
    session_cookie_secure: bool = False
    auth_trusted_caddy_mode: bool = False
    auth_rate_limit_hmac_key: SecretStr | None = None
    auth_register_global_limit: int = Field(default=200, gt=0, strict=True)
    auth_register_source_limit: int = Field(default=20, gt=0, strict=True)
    auth_register_invite_limit: int = Field(default=5, gt=0, strict=True)
    auth_login_global_limit: int = Field(default=1200, gt=0, strict=True)
    auth_login_source_limit: int = Field(default=60, gt=0, strict=True)
    auth_login_account_shard_limit: int = Field(default=10, gt=0, strict=True)
    otel_tracing_enabled: bool = False
    otel_service_name: str = "group-interview-arena-api"
    otel_otlp_http_endpoint: AnyHttpUrl | None = None
    session_phase_durations: SessionPhaseDurations = Field(
        default_factory=SessionPhaseDurations
    )

    @model_validator(mode="after")
    def require_secure_production_session_cookie(self) -> Self:
        if (
            self.environment is Environment.PRODUCTION
            and not self.session_cookie_secure
        ):
            raise ValueError("Production sessions require secure cookies")
        return self

    @model_validator(mode="after")
    def require_production_auth_boundary(self) -> Self:
        if self.environment is not Environment.PRODUCTION:
            return self
        if not self.auth_trusted_caddy_mode:
            raise ValueError(
                "Production auth requires trusted Caddy client source mode"
            )
        if self.auth_rate_limit_hmac_key is None:
            raise ValueError("Production auth requires a rate-limit HMAC key")
        return self

    @field_validator("auth_rate_limit_hmac_key")
    @classmethod
    def validate_auth_rate_limit_hmac_key(
        cls,
        key: SecretStr | None,
    ) -> SecretStr | None:
        if key is None:
            return None
        if len(key.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("Auth rate-limit HMAC key must contain at least 32 bytes")
        return key

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
