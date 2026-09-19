import pytest
from pydantic import AnyHttpUrl, SecretStr, ValidationError
from pydantic_settings import SettingsError

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    LogLevel,
    SessionPhaseDurations,
    Settings,
    ZhipuProviderSettings,
)

DATABASE_PASSWORD = "database-settings-secret"
DATABASE_URL = (
    "postgresql+psycopg://group_interview_arena:"
    f"{DATABASE_PASSWORD}@127.0.0.1:5432/group_interview_arena"
)
ZHIPU_API_KEY = "zhipu-provider-settings-secret"
ZHIPU_MODEL = "glm-4.7-flashx"


def _clear_api_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GIA_API_ENVIRONMENT", raising=False)
    monkeypatch.delenv("GIA_API_LOG_LEVEL", raising=False)
    monkeypatch.delenv("GIA_API_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("GIA_API_SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("GIA_API_DATABASE_URL", raising=False)
    monkeypatch.delenv("GIA_API_OTEL_TRACING_ENABLED", raising=False)
    monkeypatch.delenv("GIA_API_OTEL_SERVICE_NAME", raising=False)
    monkeypatch.delenv("GIA_API_OTEL_OTLP_HTTP_ENDPOINT", raising=False)
    monkeypatch.delenv("GIA_API_ZHIPU_API_KEY", raising=False)
    monkeypatch.delenv("GIA_API_ZHIPU_MODEL", raising=False)


def test_development_settings_can_be_created(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)

    settings = Settings()

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.log_level is LogLevel.INFO
    assert settings.cors_origins == ()
    assert settings.session_cookie_secure is False
    assert settings.otel_tracing_enabled is False
    assert settings.otel_service_name == "group-interview-arena-api"
    assert settings.otel_otlp_http_endpoint is None
    assert settings.session_phase_durations.to_duration_plan().to_json() == {
        "PREPARATION": 240,
        "OPENING_STATEMENTS": 240,
        "EXPLORATION": 900,
        "CONFLICT_AND_EVALUATION": 300,
        "CONVERGENCE": 180,
        "FINAL_SUMMARY": 60,
    }


def test_enabled_tracing_requires_otlp_http_endpoint() -> None:
    with pytest.raises(ValidationError, match="Tracing requires an OTLP HTTP endpoint"):
        Settings(otel_tracing_enabled=True)


@pytest.mark.parametrize("value", [True, 1.0, "1", 0, -1])
def test_session_phase_duration_settings_require_strict_positive_integers(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        SessionPhaseDurations(preparation_seconds=value)  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("  internal-api  ", "internal-api"),
        ("a" * 128, "a" * 128),
    ],
)
def test_otel_service_name_is_trimmed_and_bounded(
    configured: str,
    expected: str,
) -> None:
    settings = Settings(otel_service_name=configured)

    assert settings.otel_service_name == expected


@pytest.mark.parametrize("configured", ["", "   ", "a" * 129])
def test_invalid_otel_service_name_is_rejected(configured: str) -> None:
    with pytest.raises(ValidationError):
        Settings(otel_service_name=configured)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:4318/v1/traces",
        "https://telemetry.example.test:8443/custom/traces",
    ],
)
def test_otel_endpoint_accepts_http_host_port_and_path(endpoint: str) -> None:
    settings = Settings(
        otel_tracing_enabled=True,
        otel_otlp_http_endpoint=AnyHttpUrl(endpoint),
    )

    assert str(settings.otel_otlp_http_endpoint) == endpoint


@pytest.mark.parametrize(
    "endpoint",
    [
        "ftp://telemetry.example.test/v1/traces",
        "https://user@telemetry.example.test/v1/traces",
        "https://user:password@telemetry.example.test/v1/traces",
        "https://telemetry.example.test/v1/traces?token=secret",
        "https://telemetry.example.test/v1/traces#fragment",
    ],
)
def test_otel_endpoint_rejects_unsafe_components(endpoint: str) -> None:
    with pytest.raises(ValidationError):
        Settings(otel_otlp_http_endpoint=AnyHttpUrl(endpoint))


def test_disabled_tracing_allows_preconfigured_safe_endpoint() -> None:
    settings = Settings(
        otel_tracing_enabled=False,
        otel_otlp_http_endpoint=AnyHttpUrl("http://localhost:4318/v1/traces"),
    )

    assert settings.otel_tracing_enabled is False


def test_test_settings_can_be_created(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ENVIRONMENT", "test")
    monkeypatch.setenv("GIA_API_LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.environment is Environment.TEST
    assert settings.log_level is LogLevel.DEBUG


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ENVIRONMENT", "staging")

    with pytest.raises(ValidationError):
        Settings()


def test_invalid_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_LOG_LEVEL", "VERBOSE")

    with pytest.raises(ValidationError):
        Settings()


def test_cors_origins_parse_from_json_array(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv(
        "GIA_API_CORS_ORIGINS",
        '["http://localhost:3000", "http://127.0.0.1:3000"]',
    )

    settings = Settings()

    assert settings.cors_origins == (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )


@pytest.mark.parametrize(
    "value",
    [
        "not-json",
        '{"origin":"http://localhost:3000"}',
        '["*"]',
        '["http://localhost:3000/path"]',
    ],
)
def test_invalid_cors_origins_are_rejected(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_CORS_ORIGINS", value)

    with pytest.raises((SettingsError, ValidationError)):
        Settings()


def test_database_settings_load_from_scoped_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_DATABASE_URL", DATABASE_URL)

    settings = DatabaseSettings()  # pyright: ignore[reportCallIssue]

    assert settings.database_url.get_secret_value() == DATABASE_URL


def test_database_settings_require_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)

    with pytest.raises(ValidationError):
        DatabaseSettings()  # pyright: ignore[reportCallIssue]


def test_database_settings_repr_redacts_password() -> None:
    settings = DatabaseSettings(database_url=SecretStr(DATABASE_URL))

    assert DATABASE_PASSWORD not in repr(settings)
    assert "**********" in repr(settings)


def test_zhipu_provider_settings_load_required_scoped_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ZHIPU_API_KEY", ZHIPU_API_KEY)
    monkeypatch.setenv("GIA_API_ZHIPU_MODEL", ZHIPU_MODEL)

    settings = ZhipuProviderSettings()  # pyright: ignore[reportCallIssue]

    assert settings.api_key.get_secret_value() == ZHIPU_API_KEY


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("glm-4.7-flashx", "glm-4.7-flashx"),
        ("  glm-4.7  ", "glm-4.7"),
    ],
)
def test_zhipu_provider_settings_load_configured_model(
    monkeypatch: pytest.MonkeyPatch,
    configured: str,
    expected: str,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ZHIPU_API_KEY", ZHIPU_API_KEY)
    monkeypatch.setenv("GIA_API_ZHIPU_MODEL", configured)

    settings = ZhipuProviderSettings()  # pyright: ignore[reportCallIssue]

    assert settings.model == expected


def test_zhipu_provider_settings_require_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ZHIPU_API_KEY", ZHIPU_API_KEY)

    with pytest.raises(ValidationError):
        ZhipuProviderSettings()  # pyright: ignore[reportCallIssue]


@pytest.mark.parametrize("model", ["", " ", "\t\r\n", "m" * 129])
def test_zhipu_provider_settings_reject_invalid_model(
    monkeypatch: pytest.MonkeyPatch,
    model: str,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ZHIPU_API_KEY", ZHIPU_API_KEY)
    monkeypatch.setenv("GIA_API_ZHIPU_MODEL", model)

    with pytest.raises(ValidationError):
        ZhipuProviderSettings()  # pyright: ignore[reportCallIssue]


def test_zhipu_provider_settings_require_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ZHIPU_MODEL", ZHIPU_MODEL)

    with pytest.raises(ValidationError):
        ZhipuProviderSettings()  # pyright: ignore[reportCallIssue]


@pytest.mark.parametrize("api_key", ["", " ", "\t\r\n"])
def test_zhipu_provider_settings_reject_whitespace_only_secret(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ZHIPU_API_KEY", api_key)
    monkeypatch.setenv("GIA_API_ZHIPU_MODEL", ZHIPU_MODEL)

    with pytest.raises(ValidationError):
        ZhipuProviderSettings()  # pyright: ignore[reportCallIssue]


def test_zhipu_provider_settings_repr_and_serialization_redact_api_key() -> None:
    settings = ZhipuProviderSettings(
        api_key=SecretStr(ZHIPU_API_KEY),
        model=ZHIPU_MODEL,
    )

    assert ZHIPU_API_KEY not in repr(settings)
    assert ZHIPU_API_KEY not in str(settings.model_dump())
    assert ZHIPU_API_KEY not in settings.model_dump_json()
    assert "**********" in repr(settings)


def test_global_settings_do_not_collect_zhipu_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ZHIPU_MODEL", ZHIPU_MODEL)

    settings = Settings()

    assert "model" not in settings.model_dump()


def test_application_construction_does_not_require_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)

    settings = Settings()
    application = create_app(settings)

    assert application is not None


def test_session_cookie_secure_loads_as_typed_boolean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_SESSION_COOKIE_SECURE", "true")

    assert Settings().session_cookie_secure is True


@pytest.mark.parametrize(
    ("environment", "session_cookie_secure"),
    [
        (Environment.DEVELOPMENT, False),
        (Environment.TEST, False),
        (Environment.DEVELOPMENT, True),
        (Environment.TEST, True),
        (Environment.PRODUCTION, True),
    ],
)
def test_session_cookie_security_accepts_safe_environment_combinations(
    environment: Environment,
    session_cookie_secure: bool,
) -> None:
    if environment is Environment.PRODUCTION:
        settings = Settings(
            environment=environment,
            session_cookie_secure=session_cookie_secure,
            auth_trusted_caddy_mode=True,
            auth_rate_limit_hmac_key=SecretStr("x" * 32),
        )
    else:
        settings = Settings(
            environment=environment,
            session_cookie_secure=session_cookie_secure,
        )

    assert settings.session_cookie_secure is session_cookie_secure


def test_production_settings_reject_insecure_session_cookie() -> None:
    with pytest.raises(
        ValidationError,
        match="Production sessions require secure cookies",
    ):
        Settings(
            environment=Environment.PRODUCTION,
            session_cookie_secure=False,
        )


def test_production_environment_rejects_insecure_session_cookie_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ENVIRONMENT", "production")
    monkeypatch.setenv("GIA_API_SESSION_COOKIE_SECURE", "false")

    with pytest.raises(ValidationError):
        Settings()


def test_production_environment_requires_explicit_secure_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)
    monkeypatch.setenv("GIA_API_ENVIRONMENT", "production")

    with pytest.raises(ValidationError):
        Settings()
