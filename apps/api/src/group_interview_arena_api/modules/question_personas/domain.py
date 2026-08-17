from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self, cast

from pydantic import (
    UUID4,
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

QUESTION_TYPE_CODES = frozenset(
    {"ORDERING_SELECTION", "RESOURCE_ALLOCATION", "PLAN_DESIGN"}
)
DIFFICULTY_CODES = frozenset({"STANDARD"})
BACKGROUND_DOMAIN_CODES = frozenset({"GENERAL"})
PHASE_CODES = frozenset(
    {
        "PREPARATION",
        "OPENING_STATEMENTS",
        "EXPLORATION",
        "CONFLICT_AND_EVALUATION",
        "CONVERGENCE",
        "FINAL_SUMMARY",
    }
)


def _reject_whitespace_only(value: str) -> str:
    if not value.strip():
        raise ValueError("text must contain a non-whitespace character")
    return value


Code = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")]
ShortText = Annotated[
    str,
    Field(min_length=1, max_length=200),
    AfterValidator(_reject_whitespace_only),
]
LongText = Annotated[
    str,
    Field(min_length=1, max_length=4000),
    AfterValidator(_reject_whitespace_only),
]
Probability = Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
SignedProbability = Annotated[
    Decimal,
    Field(ge=Decimal("-1"), le=Decimal("1")),
]


class ClosedDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _validate_utc_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value


def _validate_three_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("numeric value must be finite")
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int) or exponent < -3:
        raise ValueError("numeric value must have at most three decimal places")
    return value


def _ensure_unique(items: tuple[object, ...], attribute: str) -> tuple[object, ...]:
    values = [getattr(item, attribute) for item in items]
    if len(values) != len(set(values)):
        raise ValueError(f"{attribute} values must be unique")
    return items


class ConstraintItem(ClosedDomainModel):
    key: Code
    text: LongText


class StakeholderItem(ClosedDomainModel):
    key: Code
    name: ShortText
    description: LongText


class QuestionOption(ClosedDomainModel):
    key: Code
    label: ShortText
    description: LongText


class ReferenceDimension(ClosedDomainModel):
    key: Code
    name: ShortText
    description: LongText


class InternalTextItem(ClosedDomainModel):
    key: Code
    text: LongText


class PhasePromptSet(ClosedDomainModel):
    preparation: LongText | None = Field(default=None, alias="PREPARATION")
    opening_statements: LongText | None = Field(
        default=None,
        alias="OPENING_STATEMENTS",
    )
    exploration: LongText | None = Field(default=None, alias="EXPLORATION")
    conflict_and_evaluation: LongText | None = Field(
        default=None,
        alias="CONFLICT_AND_EVALUATION",
    )
    convergence: LongText | None = Field(default=None, alias="CONVERGENCE")
    final_summary: LongText | None = Field(default=None, alias="FINAL_SUMMARY")

    @model_validator(mode="after")
    def require_at_least_one_prompt(self) -> Self:
        if not any(
            value is not None
            for value in (
                self.preparation,
                self.opening_statements,
                self.exploration,
                self.conflict_and_evaluation,
                self.convergence,
                self.final_summary,
            )
        ):
            raise ValueError("at least one phase prompt is required")
        return self


class QuestionVersionContent(ClosedDomainModel):
    title: ShortText
    question_type_code: Code
    background_domain_code: Code
    difficulty_code: Code
    scenario: LongText
    objective: LongText
    estimated_minutes: Annotated[int, Field(ge=5, le=180)]
    hard_constraints: Annotated[
        tuple[ConstraintItem, ...], Field(min_length=1, max_length=20)
    ]
    soft_constraints: Annotated[tuple[ConstraintItem, ...], Field(max_length=20)] = ()
    stakeholders: Annotated[
        tuple[StakeholderItem, ...], Field(min_length=1, max_length=20)
    ]
    options: Annotated[tuple[QuestionOption, ...], Field(max_length=20)] = ()
    reference_dimensions: Annotated[
        tuple[ReferenceDimension, ...], Field(min_length=1, max_length=20)
    ]
    hidden_conflicts: Annotated[tuple[InternalTextItem, ...], Field(max_length=20)] = ()
    acceptable_outcome_patterns: Annotated[
        tuple[InternalTextItem, ...], Field(min_length=1, max_length=20)
    ]
    phase_prompts: PhasePromptSet
    safety_tags: Annotated[tuple[Code, ...], Field(max_length=20)] = ()

    @field_validator(
        "hard_constraints",
        "soft_constraints",
        "stakeholders",
        "options",
        "reference_dimensions",
        "hidden_conflicts",
        "acceptable_outcome_patterns",
        "safety_tags",
        mode="before",
    )
    @classmethod
    def normalize_json_arrays(cls, value: object) -> object:
        return tuple(cast(list[object], value)) if isinstance(value, list) else value

    @field_validator(
        "hard_constraints",
        "soft_constraints",
        "stakeholders",
        "options",
        "reference_dimensions",
        "hidden_conflicts",
        "acceptable_outcome_patterns",
    )
    @classmethod
    def validate_unique_keys(cls, value: tuple[object, ...]) -> tuple[object, ...]:
        return _ensure_unique(value, "key")

    @field_validator("safety_tags")
    @classmethod
    def validate_unique_safety_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("safety tags must be unique")
        return value

    @model_validator(mode="after")
    def validate_registered_codes_and_shape(self) -> Self:
        if self.question_type_code not in QUESTION_TYPE_CODES:
            raise ValueError("question type code is not registered")
        if self.background_domain_code not in BACKGROUND_DOMAIN_CODES:
            raise ValueError("background domain code is not registered")
        if self.difficulty_code not in DIFFICULTY_CODES:
            raise ValueError("difficulty code is not registered")
        if (
            self.question_type_code
            in {
                "ORDERING_SELECTION",
                "RESOURCE_ALLOCATION",
            }
            and len(self.options) < 2
        ):
            raise ValueError("question type requires at least two options")
        return self


class PersonaTemplateDefinition(ClosedDomainModel):
    id: UUID4
    code: Code
    display_name: ShortText
    speech_style_code: Code
    initiative: Probability
    interrupt_tendency: Probability
    average_turn_seconds: Annotated[int, Field(ge=10, le=90)]
    stance_stability: Probability
    persuasion_threshold: Probability
    novel_idea_rate: Probability
    summary_tendency: Probability
    time_awareness: Probability
    detail_focus: Probability
    cooperation: Probability
    support_user_bias: SignedProbability
    error_rate: Probability
    off_topic_rate: Probability
    created_at: datetime
    retired_at: datetime | None = None

    @field_validator(
        "initiative",
        "interrupt_tendency",
        "stance_stability",
        "persuasion_threshold",
        "novel_idea_rate",
        "summary_tendency",
        "time_awareness",
        "detail_focus",
        "cooperation",
        "support_user_bias",
        "error_rate",
        "off_topic_rate",
    )
    @classmethod
    def validate_numeric_precision(cls, value: Decimal) -> Decimal:
        return _validate_three_decimal(value)

    @field_validator("created_at", "retired_at")
    @classmethod
    def validate_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _validate_utc_timestamp(value)

    @model_validator(mode="after")
    def validate_retirement_chronology(self) -> Self:
        if self.retired_at is not None and self.retired_at < self.created_at:
            raise ValueError("retirement cannot precede creation")
        return self


class PriorityDimension(ClosedDomainModel):
    code: Code
    weight: Probability

    @field_validator("weight")
    @classmethod
    def validate_weight_precision(cls, value: Decimal) -> Decimal:
        return _validate_three_decimal(value)


class PrivateStanceDefinition(ClosedDomainModel):
    initial_position: LongText
    priority_dimensions: Annotated[
        tuple[PriorityDimension, ...], Field(min_length=1, max_length=20)
    ]
    concession_conditions: Annotated[tuple[LongText, ...], Field(max_length=20)] = ()
    private_information: LongText | None = None
    red_lines: Annotated[tuple[LongText, ...], Field(max_length=20)] = ()
    preferred_group_role: ShortText | None = None

    @field_validator("priority_dimensions")
    @classmethod
    def validate_unique_dimensions(
        cls,
        value: tuple[PriorityDimension, ...],
    ) -> tuple[PriorityDimension, ...]:
        _ensure_unique(value, "code")
        return value


class PersonaAssignmentDefinition(ClosedDomainModel):
    id: UUID4
    slot: Annotated[int, Field(gt=0)]
    persona_template_id: UUID4
    private_stance: PrivateStanceDefinition


class PublishedQuestionBundle(ClosedDomainModel):
    template_id: UUID4
    template_code: Code
    version_id: UUID4
    version_number: Annotated[int, Field(gt=0)]
    content: QuestionVersionContent
    assignments: Annotated[
        tuple[PersonaAssignmentDefinition, ...], Field(min_length=3, max_length=3)
    ]
    created_at: datetime
    published_at: datetime

    @field_validator("created_at", "published_at")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _validate_utc_timestamp(value)

    @field_validator("assignments")
    @classmethod
    def validate_assignment_identity(
        cls,
        value: tuple[PersonaAssignmentDefinition, ...],
    ) -> tuple[PersonaAssignmentDefinition, ...]:
        if sorted(assignment.slot for assignment in value) != [1, 2, 3]:
            raise ValueError("published bundle requires slots 1, 2, and 3")
        _ensure_unique(value, "id")
        _ensure_unique(value, "persona_template_id")
        return value

    @model_validator(mode="after")
    def validate_publication_chronology(self) -> Self:
        if self.published_at < self.created_at:
            raise ValueError("publication cannot precede creation")
        return self
