import asyncio
import json
from collections.abc import Callable
from typing import cast
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from group_interview_arena_api.core.config import ZhipuProviderSettings
from group_interview_arena_api.modules.ai_runtime.domain import GenerationFailureCode
from group_interview_arena_api.modules.ai_runtime.generation import (
    RawGenerationFailure,
    RawGenerationResult,
    RawGenerationSuccess,
    RuntimeGenerationInput,
)
from group_interview_arena_api.providers.zhipu import ZhipuGenerationProvider

ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
API_KEY_SENTINEL = "ZHIPU_API_KEY_SENTINEL_P15D"
PROMPT_SENTINEL = "RENDERED_PROMPT_SENTINEL_P15D"
RAW_PROVIDER_SENTINEL = "RAW_PROVIDER_BODY_SENTINEL_P15D"
RAW_EXCEPTION_SENTINEL = "RAW_PROVIDER_EXCEPTION_SENTINEL_P15D"
MALFORMED_PAYLOADS: tuple[str, ...] = (
    '{"model": "glm-4.7-flashx"}',
    '{"model": "glm-4.7-flashx", "choices": []}',
    '{"model": "glm-4.7-flashx", "choices": [null]}',
    '{"model": "glm-4.7-flashx", "choices": [{}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"finish_reason": "stop"}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"finish_reason": "stop", "message": []}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"finish_reason": "stop", "message": {"role": "assistant"}}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": null}}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": 7}}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"finish_reason": null, "message": {"role": "assistant", "content": "Content"}}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"message": {"role": "assistant", "content": "Content"}}]}',
)
MODEL_OR_ROLE_MISMATCH_PAYLOADS: tuple[str, ...] = (
    '{"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Content"}}]}',
    '{"model": "another-model", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Content"}}]}',
    '{"model": 7, "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Content"}}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"finish_reason": "stop", "message": {"content": "Content"}}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"finish_reason": "stop", "message": {"role": "user", "content": "Content"}}]}',
    '{"model": "glm-4.7-flashx", "choices": [{"finish_reason": "stop", "message": {"role": 7, "content": "Content"}}]}',
)


def _input(
    *,
    provider_identifier: str = "zhipu",
    model_identifier: str = "glm-4.7-flashx",
    configuration_version: str = "ZHIPU_CHAT_DEV_V1",
) -> RuntimeGenerationInput:
    return RuntimeGenerationInput(
        generation_request_id=uuid4(),
        session_id=uuid4(),
        participant_id=uuid4(),
        floor_grant_id=uuid4(),
        phase="EXPLORATION",
        prompt_version_id=uuid4(),
        prompt_key="AI_CANDIDATE_TURN",
        prompt_version_number=1,
        rendered_prompt=PROMPT_SENTINEL,
        provider_identifier=provider_identifier,
        model_identifier=model_identifier,
        configuration_version=configuration_version,
    )


def _settings() -> ZhipuProviderSettings:
    return ZhipuProviderSettings(
        api_key=SecretStr(API_KEY_SENTINEL),
        model="glm-4.7-flashx",
    )


def _provider(
    handler: Callable[[httpx.Request], httpx.Response],
) -> ZhipuGenerationProvider:
    return ZhipuGenerationProvider(
        _settings(),
        transport=httpx.MockTransport(handler),
    )


def _run(
    provider: ZhipuGenerationProvider,
    generation_input: RuntimeGenerationInput | None = None,
) -> RawGenerationResult:
    return asyncio.run(
        provider(generation_input or _input()),
        loop_factory=asyncio.SelectorEventLoop,
    )


@pytest.mark.parametrize("configured_model", ["glm-4.7-flashx", "glm-4.7"])
def test_configured_model_switches_without_provider_code_change(
    configured_model: str,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        payload = json.loads(request.content)
        assert isinstance(payload, dict)
        assert payload["model"] == configured_model
        return httpx.Response(
            200,
            json={
                "model": configured_model,
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "Configured model response.",
                        },
                    }
                ],
            },
        )

    provider = ZhipuGenerationProvider(
        ZhipuProviderSettings(
            api_key=SecretStr(API_KEY_SENTINEL),
            model=configured_model,
        ),
        transport=httpx.MockTransport(handler),
    )
    result = _run(
        provider,
        _input(
            model_identifier=configured_model,
            configuration_version="ZHIPU_CHAT_DEV_V1",
        ),
    )

    assert result == RawGenerationSuccess(content="Configured model response.")
    assert requests == 1


def test_exact_request_and_success_normalization_are_frozen() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        assert isinstance(payload, dict)
        assert request.method == "POST"
        assert str(request.url) == ENDPOINT
        assert request.headers["Authorization"] == f"Bearer {API_KEY_SENTINEL}"
        assert payload == {
            "model": "glm-4.7-flashx",
            "messages": [{"role": "user", "content": PROMPT_SENTINEL}],
            "thinking": {"type": "disabled"},
            "stream": False,
            "max_tokens": 512,
            "temperature": 0.7,
        }
        timeout = cast(dict[str, float], request.extensions["timeout"])
        assert timeout == {
            "connect": 5.0,
            "read": 60.0,
            "write": 10.0,
            "pool": 5.0,
        }
        return httpx.Response(
            200,
            json={
                "id": RAW_PROVIDER_SENTINEL,
                "request_id": RAW_PROVIDER_SENTINEL,
                "model": "glm-4.7-flashx",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "Compare the hard constraints first.",
                            "reasoning_content": RAW_PROVIDER_SENTINEL,
                        },
                    }
                ],
            },
        )

    result = _run(_provider(handler))

    assert result == RawGenerationSuccess(content="Compare the hard constraints first.")
    assert len(requests) == 1
    assert RAW_PROVIDER_SENTINEL not in repr(result)


@pytest.mark.parametrize("finish_reason", ["length", "content_filter", "tool_calls"])
def test_any_non_stop_finish_reason_is_partial(finish_reason: str) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "glm-4.7-flashx",
                "choices": [
                    {
                        "finish_reason": finish_reason,
                        "message": {
                            "role": "assistant",
                            "content": "Partial provider content.",
                        },
                    }
                ],
            },
        )

    assert _run(_provider(handler)) == RawGenerationFailure(
        failure_code=GenerationFailureCode.PARTIAL_GENERATION
    )


@pytest.mark.parametrize(
    "payload",
    MALFORMED_PAYLOADS,
)
def test_malformed_success_shape_is_invalid_output(payload: str) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=payload,
            headers={"content-type": "application/json"},
        )

    assert _run(_provider(handler)) == RawGenerationFailure(
        failure_code=GenerationFailureCode.INVALID_OUTPUT
    )


@pytest.mark.parametrize("payload", MODEL_OR_ROLE_MISMATCH_PAYLOADS)
def test_model_or_role_mismatch_is_invalid_output(payload: str) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=payload,
            headers={"content-type": "application/json"},
        )

    assert _run(_provider(handler)) == RawGenerationFailure(
        failure_code=GenerationFailureCode.INVALID_OUTPUT
    )


@pytest.mark.parametrize("content", ["", [], 1, None])
def test_empty_or_non_string_content_is_invalid_output(content: object) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "glm-4.7-flashx",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": content},
                    }
                ],
            },
        )

    assert _run(_provider(handler)) == RawGenerationFailure(
        failure_code=GenerationFailureCode.INVALID_OUTPUT
    )


def test_malformed_json_is_invalid_output() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"not-json",
            headers={"content-type": "application/json"},
        )

    assert _run(_provider(handler)) == RawGenerationFailure(
        failure_code=GenerationFailureCode.INVALID_OUTPUT
    )


@pytest.mark.parametrize(
    ("status_code", "failure_code"),
    [
        (408, GenerationFailureCode.TIMEOUT),
        (429, GenerationFailureCode.RATE_LIMIT),
        (500, GenerationFailureCode.PROVIDER_UNAVAILABLE),
        (502, GenerationFailureCode.PROVIDER_UNAVAILABLE),
        (503, GenerationFailureCode.PROVIDER_UNAVAILABLE),
        (400, GenerationFailureCode.INTERNAL_ERROR),
        (401, GenerationFailureCode.INTERNAL_ERROR),
        (403, GenerationFailureCode.INTERNAL_ERROR),
    ],
)
def test_http_statuses_map_to_safe_typed_failures(
    status_code: int,
    failure_code: GenerationFailureCode,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={"error": {"message": RAW_PROVIDER_SENTINEL}},
        )

    result = _run(_provider(handler))

    assert result == RawGenerationFailure(failure_code=failure_code)
    assert RAW_PROVIDER_SENTINEL not in repr(result)


@pytest.mark.parametrize(
    ("failure_kind", "failure_code"),
    [
        ("timeout", GenerationFailureCode.TIMEOUT),
        ("network", GenerationFailureCode.PROVIDER_UNAVAILABLE),
    ],
)
def test_transport_failures_map_without_raw_exception_leakage(
    failure_kind: str,
    failure_code: GenerationFailureCode,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if failure_kind == "timeout":
            raise httpx.ReadTimeout(RAW_EXCEPTION_SENTINEL, request=request)
        raise httpx.ConnectError(RAW_EXCEPTION_SENTINEL, request=request)

    result = _run(_provider(handler))

    assert result == RawGenerationFailure(failure_code=failure_code)
    assert RAW_EXCEPTION_SENTINEL not in repr(result)


@pytest.mark.parametrize(
    ("provider_identifier", "model_identifier", "configuration_version"),
    [
        ("other", "glm-4.7-flashx", "ZHIPU_CHAT_DEV_V1"),
        ("zhipu", "other-model", "ZHIPU_CHAT_DEV_V1"),
        ("zhipu", "glm-4.7-flashx", "OTHER_CONFIGURATION"),
    ],
)
def test_provenance_mismatch_fails_before_http(
    provider_identifier: str,
    model_identifier: str,
    configuration_version: str,
) -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        raise AssertionError("provenance mismatch must not perform HTTP")

    result = _run(
        _provider(handler),
        _input(
            provider_identifier=provider_identifier,
            model_identifier=model_identifier,
            configuration_version=configuration_version,
        ),
    )

    assert result == RawGenerationFailure(
        failure_code=GenerationFailureCode.INTERNAL_ERROR
    )
    assert requests == 0


@pytest.mark.parametrize("failure_kind", ["429", "503", "timeout"])
def test_failure_never_retries(failure_kind: str) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if failure_kind == "timeout":
            raise httpx.ReadTimeout("safe timeout", request=request)
        return httpx.Response(int(failure_kind))

    _run(_provider(handler))

    assert requests == 1


def test_redirect_response_is_not_followed() -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(307, headers={"location": f"{ENDPOINT}/redirected"})

    result = _run(_provider(handler))

    assert result == RawGenerationFailure(
        failure_code=GenerationFailureCode.INTERNAL_ERROR
    )
    assert requests == 1


def test_provider_settings_results_and_logs_do_not_leak_sensitive_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = _settings()

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": RAW_PROVIDER_SENTINEL}},
        )

    provider = ZhipuGenerationProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )
    result = _run(provider)

    surfaces = (repr(settings), repr(provider), repr(result), caplog.text)
    for surface in surfaces:
        assert API_KEY_SENTINEL not in surface
        assert PROMPT_SENTINEL not in surface
        assert RAW_PROVIDER_SENTINEL not in surface


def test_unexpected_adapter_exception_is_contained_without_raw_details() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise RuntimeError(RAW_EXCEPTION_SENTINEL)

    result = _run(_provider(handler))

    assert result == RawGenerationFailure(
        failure_code=GenerationFailureCode.INTERNAL_ERROR
    )
    assert RAW_EXCEPTION_SENTINEL not in repr(result)
