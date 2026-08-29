from typing import Any

import pytest

import group_interview_arena_api.app as app_module


class _NoopDeadlineRecoveryRuntime:
    async def stop(self) -> None:
        pass


def disable_deadline_recovery_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    async def seed_no_prompt_versions(_session_factory: Any) -> bool:
        return False

    async def recover_no_due_sessions(_session_factory: Any) -> int:
        return 0

    def start_noop_deadline_recovery_runtime(
        _session_factory: Any,
    ) -> _NoopDeadlineRecoveryRuntime:
        return _NoopDeadlineRecoveryRuntime()

    monkeypatch.setattr(
        app_module,
        "seed_ai_runtime_prompt_versions",
        seed_no_prompt_versions,
    )
    monkeypatch.setattr(app_module, "recover_due_sessions", recover_no_due_sessions)
    monkeypatch.setattr(
        app_module,
        "start_deadline_recovery_runtime",
        start_noop_deadline_recovery_runtime,
    )
