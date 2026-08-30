from typing import cast

import httpx

from group_interview_arena_api.core.config import ZhipuProviderSettings
from group_interview_arena_api.modules.ai_runtime.domain import GenerationFailureCode
from group_interview_arena_api.modules.ai_runtime.generation import (
    ModelInvocationInput,
    ModelOutputExpectation,
    RawGenerationFailure,
    RawGenerationResult,
    RawGenerationSuccess,
    RuntimeGenerationInput,
)

_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_PROVIDER_IDENTIFIER = "zhipu"
ZHIPU_CONFIGURATION_VERSION = "ZHIPU_CHAT_DEV_V1"
_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)


def _failure(code: GenerationFailureCode) -> RawGenerationFailure:
    return RawGenerationFailure(failure_code=code)


def _normalize_success(
    response: httpx.Response,
    *,
    expected_model: str,
) -> RawGenerationResult:
    try:
        payload_object: object = response.json()
    except Exception:
        return _failure(GenerationFailureCode.INVALID_OUTPUT)
    if not isinstance(payload_object, dict):
        return _failure(GenerationFailureCode.INVALID_OUTPUT)
    payload = cast(dict[object, object], payload_object)
    response_model = payload.get("model")
    if not isinstance(response_model, str) or response_model != expected_model:
        return _failure(GenerationFailureCode.INVALID_OUTPUT)
    choices_object = payload.get("choices")
    if not isinstance(choices_object, list) or not choices_object:
        return _failure(GenerationFailureCode.INVALID_OUTPUT)
    choices = cast(list[object], choices_object)
    choice_object = choices[0]
    if not isinstance(choice_object, dict):
        return _failure(GenerationFailureCode.INVALID_OUTPUT)
    choice = cast(dict[object, object], choice_object)
    finish_reason = choice.get("finish_reason")
    if not isinstance(finish_reason, str):
        return _failure(GenerationFailureCode.INVALID_OUTPUT)
    if finish_reason != "stop":
        return _failure(GenerationFailureCode.PARTIAL_GENERATION)
    message_object = choice.get("message")
    if not isinstance(message_object, dict):
        return _failure(GenerationFailureCode.INVALID_OUTPUT)
    message = cast(dict[object, object], message_object)
    role = message.get("role")
    if not isinstance(role, str) or role != "assistant":
        return _failure(GenerationFailureCode.INVALID_OUTPUT)
    content = message.get("content")
    if not isinstance(content, str) or not content:
        return _failure(GenerationFailureCode.INVALID_OUTPUT)
    return RawGenerationSuccess(content=content)


class ZhipuGenerationProvider:
    """One-request, non-streaming adapter for the frozen P1-5D configuration."""

    __slots__ = ("_settings", "_transport")

    def __init__(
        self,
        settings: ZhipuProviderSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    async def __call__(
        self,
        generation_input: RuntimeGenerationInput,
    ) -> RawGenerationResult:
        return await self.invoke(generation_input.to_model_invocation())

    async def invoke(self, invocation: ModelInvocationInput) -> RawGenerationResult:
        if (
            invocation.provider_identifier != ZHIPU_PROVIDER_IDENTIFIER
            or invocation.model_identifier != self._settings.model
            or invocation.configuration_version != ZHIPU_CONFIGURATION_VERSION
        ):
            return _failure(GenerationFailureCode.INTERNAL_ERROR)

        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    _ENDPOINT,
                    headers={
                        "Authorization": (
                            "Bearer " + self._settings.api_key.get_secret_value()
                        )
                    },
                    json={
                        "model": self._settings.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": invocation.rendered_prompt,
                            }
                        ],
                        "thinking": {"type": "disabled"},
                        "stream": False,
                        "max_tokens": invocation.max_output_tokens,
                        "temperature": invocation.temperature,
                        **(
                            {"response_format": {"type": "json_object"}}
                            if invocation.output_expectation
                            is ModelOutputExpectation.JSON_OBJECT
                            else {}
                        ),
                    },
                )
        except httpx.TimeoutException:
            return _failure(GenerationFailureCode.TIMEOUT)
        except httpx.TransportError:
            return _failure(GenerationFailureCode.PROVIDER_UNAVAILABLE)
        except Exception:
            return _failure(GenerationFailureCode.INTERNAL_ERROR)

        if response.status_code == 408:
            return _failure(GenerationFailureCode.TIMEOUT)
        if response.status_code == 429:
            return _failure(GenerationFailureCode.RATE_LIMIT)
        if 500 <= response.status_code <= 599:
            return _failure(GenerationFailureCode.PROVIDER_UNAVAILABLE)
        if not 200 <= response.status_code <= 299:
            return _failure(GenerationFailureCode.INTERNAL_ERROR)
        return _normalize_success(response, expected_model=self._settings.model)
