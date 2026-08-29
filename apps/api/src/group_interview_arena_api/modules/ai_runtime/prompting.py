import json
from collections.abc import Mapping
from decimal import Decimal
from string import Template

from pydantic import UUID4

from group_interview_arena_api.modules.ai_runtime.domain import (
    ClosedDomainModel,
    Code,
    PromptText,
)
from group_interview_arena_api.modules.question_personas.domain import (
    ConstraintItem,
    PrivateStanceDefinition,
    QuestionOption,
    StakeholderItem,
)

PROMPT_VARIABLES = frozenset(
    {
        "session_id",
        "participant_id",
        "floor_grant_id",
        "phase",
        "question_context",
        "persona_context",
        "private_stance",
        "phase_instruction",
        "recent_discussion",
        "persona_behavior",
    }
)


class PromptRenderError(RuntimeError):
    """A prompt template or its closed variable set is invalid."""


class PromptTemplateAsset(ClosedDomainModel):
    id: UUID4
    prompt_key: Code
    version_number: int
    template_text: PromptText


class AuthorizedQuestionContext(ClosedDomainModel):
    version_id: UUID4
    title: str
    question_type_code: Code
    background_domain_code: Code
    difficulty_code: Code
    scenario: str
    objective: str
    hard_constraints: tuple[ConstraintItem, ...]
    soft_constraints: tuple[ConstraintItem, ...]
    stakeholders: tuple[StakeholderItem, ...]
    options: tuple[QuestionOption, ...]


class AuthorizedPersonaContext(ClosedDomainModel):
    assignment_id: UUID4
    persona_template_id: UUID4
    code: Code
    display_name: str
    speech_style_code: Code
    initiative: Decimal
    interrupt_tendency: Decimal
    average_turn_seconds: int
    stance_stability: Decimal
    persuasion_threshold: Decimal
    novel_idea_rate: Decimal
    summary_tendency: Decimal
    time_awareness: Decimal
    detail_focus: Decimal
    cooperation: Decimal
    support_user_bias: Decimal
    error_rate: Decimal
    off_topic_rate: Decimal


class AuthorizedGenerationContext(ClosedDomainModel):
    session_id: UUID4
    participant_id: UUID4
    floor_grant_id: UUID4
    phase: Code
    question: AuthorizedQuestionContext
    persona: AuthorizedPersonaContext
    private_stance: PrivateStanceDefinition
    phase_instruction: str
    recent_discussion: str
    persona_behavior: str


def _stable_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def prompt_variables(context: AuthorizedGenerationContext) -> dict[str, str]:
    return {
        "session_id": str(context.session_id),
        "participant_id": str(context.participant_id),
        "floor_grant_id": str(context.floor_grant_id),
        "phase": context.phase,
        "question_context": _stable_json(context.question.model_dump(mode="json")),
        "persona_context": _stable_json(context.persona.model_dump(mode="json")),
        "private_stance": _stable_json(context.private_stance.model_dump(mode="json")),
        "phase_instruction": context.phase_instruction,
        "recent_discussion": context.recent_discussion,
        "persona_behavior": context.persona_behavior,
    }


def render_prompt(template_text: str, variables: Mapping[str, object]) -> str:
    template = Template(template_text)
    if not template.is_valid():
        raise PromptRenderError("Prompt template syntax is invalid.")
    normalized: dict[str, str] = {}
    for key, value in variables.items():
        if not isinstance(value, str):
            raise PromptRenderError("Prompt variables must be strings.")
        normalized[key] = value

    identifiers = frozenset(template.get_identifiers())
    supplied = frozenset(normalized)
    if (
        not identifiers <= PROMPT_VARIABLES
        or not supplied <= PROMPT_VARIABLES
        or not identifiers <= supplied
    ):
        raise PromptRenderError("Prompt variable contract is invalid.")
    try:
        return template.substitute(normalized)
    except (KeyError, ValueError) as error:
        raise PromptRenderError("Prompt rendering failed.") from error


def render_authorized_prompt(
    asset: PromptTemplateAsset,
    context: AuthorizedGenerationContext,
) -> str:
    return render_prompt(asset.template_text, prompt_variables(context))
