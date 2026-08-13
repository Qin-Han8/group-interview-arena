import pytest
from pydantic import SecretStr, ValidationError
from pydantic_settings import SettingsError

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    LogLevel,
    Settings,
)

DATABASE_PASSWORD = "database-settings-secret"
DATABASE_URL = (
    "postgresql+psycopg://group_interview_arena:"
    f"{DATABASE_PASSWORD}@127.0.0.1:5432/group_interview_arena"
)


def _clear_api_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GIA_API_ENVIRONMENT", raising=False)
    monkeypatch.delenv("GIA_API_LOG_LEVEL", raising=False)
    monkeypatch.delenv("GIA_API_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("GIA_API_DATABASE_URL", raising=False)


def test_development_settings_can_be_created(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)

    settings = Settings()

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.log_level is LogLevel.INFO
    assert settings.cors_origins == ()


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


def test_application_startup_does_not_require_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_environment(monkeypatch)

    settings = Settings()
    application = create_app(settings)

    assert application is not None
