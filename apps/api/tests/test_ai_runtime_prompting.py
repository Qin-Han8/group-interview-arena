from uuid import uuid4

import pytest

from group_interview_arena_api.modules.ai_runtime.prompting import (
    PROMPT_VARIABLES,
    PromptRenderError,
    render_prompt,
)


def test_prompt_renderer_is_closed_fail_closed_and_byte_stable() -> None:
    variables = {
        "session_id": str(uuid4()),
        "participant_id": str(uuid4()),
        "floor_grant_id": str(uuid4()),
        "phase": "EXPLORATION",
        "question_context": '{"objective":"Reach one decision."}',
        "persona_context": '{"code":"LOGIC_ANALYST"}',
        "private_stance": '{"initial_position":"Prefer option A."}',
        "phase_instruction": "Compare the hard constraints.",
    }
    template = (
        "Session ${session_id}\n"
        "Phase $phase\n"
        "Question $question_context\n"
        "Persona $persona_context\n"
        "Private $private_stance\n"
        "Instruction $phase_instruction\n"
        "Literal dollar: $$"
    )

    first = render_prompt(template, variables)
    second = render_prompt(template, dict(reversed(tuple(variables.items()))))

    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")
    assert first.endswith("Literal dollar: $")
    assert frozenset(variables) == PROMPT_VARIABLES


@pytest.mark.parametrize(
    ("template", "variables"),
    [
        ("$unknown_variable", {}),
        ("$session_id $phase", {"session_id": "known"}),
        ("${private_stance.__class__}", {}),
        ("dangling $", {}),
        ("constant", {"provider_secret": "must-not-enter"}),
    ],
)
def test_prompt_renderer_rejects_unknown_missing_invalid_or_extra_values(
    template: str,
    variables: dict[str, str],
) -> None:
    with pytest.raises(PromptRenderError):
        render_prompt(template, variables)
