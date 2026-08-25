import importlib
from typing import Any, cast
from uuid import uuid4

import pytest

from group_interview_arena_api.core.config import ZhipuProviderSettings
from group_interview_arena_api.modules.ai_runtime.continuous import (
    ContinuousAiDriveOutcome,
    ContinuousAiDriveResult,
)
from group_interview_arena_api.providers.zhipu import (
    ZHIPU_CONFIGURATION_VERSION,
    ZHIPU_PROVIDER_IDENTIFIER,
)


def test_imports_remain_lazy_without_zhipu_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GIA_API_ZHIPU_API_KEY", raising=False)
    monkeypatch.delenv("GIA_API_ZHIPU_MODEL", raising=False)

    app = importlib.import_module("group_interview_arena_api.app")
    continuous = importlib.import_module(
        "group_interview_arena_api.modules.ai_runtime.continuous"
    )
    composition = importlib.import_module(
        "group_interview_arena_api.modules.ai_runtime.composition"
    )

    assert app is not None
    assert continuous is not None
    assert composition is not None


def test_missing_configuration_fails_safely_before_composition_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from group_interview_arena_api.modules.ai_runtime import composition

    secret_sentinel = "composition-secret-must-not-leak"
    monkeypatch.setenv("GIA_API_ZHIPU_API_KEY", secret_sentinel)
    monkeypatch.delenv("GIA_API_ZHIPU_MODEL", raising=False)
    continuous_called = False

    async def forbidden_continuous(*_args: object, **_kwargs: object) -> object:
        nonlocal continuous_called
        continuous_called = True
        raise AssertionError("continuous drive must not run")

    monkeypatch.setattr(composition, "drive_continuous_ai", forbidden_continuous)

    with pytest.raises(composition.AiDriveCompositionError) as captured:
        import asyncio

        asyncio.run(
            composition.drive_configured_ai_session(
                cast(Any, object()),
                owner_id=uuid4(),
                session_id=uuid4(),
            )
        )

    assert str(captured.value) == "AI runtime provider configuration is unavailable."
    assert secret_sentinel not in str(captured.value)
    assert secret_sentinel not in repr(captured.value)
    assert not continuous_called


@pytest.mark.parametrize("model", ("glm-4.7-flashx", "glm-4.7"))
def test_configured_composition_uses_canonical_provenance_and_model_only_from_config(
    monkeypatch: pytest.MonkeyPatch,
    model: str,
) -> None:
    import asyncio

    from group_interview_arena_api.modules.ai_runtime import composition
    from group_interview_arena_api.modules.floor_control.scheduler import (
        V0_1_SCHEDULER_POLICY,
    )

    secret_sentinel = "test-only-composition-secret"
    monkeypatch.setenv("GIA_API_ZHIPU_API_KEY", secret_sentinel)
    monkeypatch.setenv("GIA_API_ZHIPU_MODEL", model)
    captured: dict[str, object] = {}
    expected_result = ContinuousAiDriveResult(
        outcome=ContinuousAiDriveOutcome.NO_CURRENT_WORK,
        automated_ai_turns_advanced=0,
    )

    def fake_provider(settings: object) -> object:
        captured["settings"] = settings
        return object()

    async def fake_continuous(
        session_factory: object,
        **kwargs: object,
    ) -> ContinuousAiDriveResult:
        captured["session_factory"] = session_factory
        captured.update(kwargs)
        return expected_result

    monkeypatch.setattr(composition, "ZhipuGenerationProvider", fake_provider)
    monkeypatch.setattr(composition, "drive_continuous_ai", fake_continuous)
    session_factory = object()
    owner_id = uuid4()
    session_id = uuid4()

    result = asyncio.run(
        composition.drive_configured_ai_session(
            cast(Any, session_factory),
            owner_id=owner_id,
            session_id=session_id,
        )
    )

    settings = cast(ZhipuProviderSettings, captured["settings"])
    assert settings.model == model
    assert captured["session_factory"] is session_factory
    assert captured["owner_id"] == owner_id
    assert captured["session_id"] == session_id
    assert captured["provider_identifier"] == ZHIPU_PROVIDER_IDENTIFIER
    assert captured["model_identifier"] == model
    assert captured["configuration_version"] == ZHIPU_CONFIGURATION_VERSION
    assert captured["scheduling_policy"] is V0_1_SCHEDULER_POLICY
    assert result is expected_result
    assert secret_sentinel not in result.model_dump_json()
