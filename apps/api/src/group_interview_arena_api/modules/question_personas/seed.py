from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.db import (
    PersonaPrivateStance,
    PersonaTemplate,
    QuestionPersonaAssignment,
    QuestionTemplate,
    QuestionVersion,
)
from group_interview_arena_api.modules.question_personas.content import (
    ADDITIONAL_V01_QUESTION_BUNDLES,
)
from group_interview_arena_api.modules.question_personas.domain import (
    ConstraintItem,
    InternalTextItem,
    PersonaAssignmentDefinition,
    PersonaTemplateDefinition,
    PhasePromptSet,
    PriorityDimension,
    PrivateStanceDefinition,
    PublishedQuestionBundle,
    QuestionOption,
    QuestionVersionContent,
    ReferenceDimension,
    StakeholderItem,
)

_SEED_TIME = datetime(2026, 8, 17, tzinfo=UTC)


class SeedDataConflictError(RuntimeError):
    """Raised when a stable seed identity already has different content."""


class PublishedQuestionMutationError(RuntimeError):
    """Raised when an existing published bundle would be overwritten."""


@dataclass(frozen=True)
class SeedResult:
    personas_inserted: int
    question_versions_inserted: int


def _persona(
    *,
    id_value: str,
    code: str,
    display_name: str,
    speech_style_code: str,
    initiative: str,
    interrupt_tendency: str,
    average_turn_seconds: int,
    stance_stability: str,
    persuasion_threshold: str,
    novel_idea_rate: str,
    summary_tendency: str,
    time_awareness: str,
    detail_focus: str,
    cooperation: str,
    error_rate: str,
    off_topic_rate: str,
) -> PersonaTemplateDefinition:
    return PersonaTemplateDefinition(
        id=UUID(id_value),
        code=code,
        display_name=display_name,
        speech_style_code=speech_style_code,
        initiative=Decimal(initiative),
        interrupt_tendency=Decimal(interrupt_tendency),
        average_turn_seconds=average_turn_seconds,
        stance_stability=Decimal(stance_stability),
        persuasion_threshold=Decimal(persuasion_threshold),
        novel_idea_rate=Decimal(novel_idea_rate),
        summary_tendency=Decimal(summary_tendency),
        time_awareness=Decimal(time_awareness),
        detail_focus=Decimal(detail_focus),
        cooperation=Decimal(cooperation),
        support_user_bias=Decimal("0.000"),
        error_rate=Decimal(error_rate),
        off_topic_rate=Decimal(off_topic_rate),
        created_at=_SEED_TIME,
    )


V01_PERSONA_TEMPLATES = (
    _persona(
        id_value="10000000-0000-4000-8000-000000000001",
        code="LOGIC_ANALYST",
        display_name="逻辑分析者",
        speech_style_code="STRUCTURED",
        initiative="0.600",
        interrupt_tendency="0.200",
        average_turn_seconds=40,
        stance_stability="0.750",
        persuasion_threshold="0.700",
        novel_idea_rate="0.350",
        summary_tendency="0.600",
        time_awareness="0.650",
        detail_focus="0.800",
        cooperation="0.600",
        error_rate="0.100",
        off_topic_rate="0.050",
    ),
    _persona(
        id_value="10000000-0000-4000-8000-000000000002",
        code="CREATIVE_DIVERGER",
        display_name="创意发散者",
        speech_style_code="EXPLORATORY",
        initiative="0.700",
        interrupt_tendency="0.300",
        average_turn_seconds=45,
        stance_stability="0.500",
        persuasion_threshold="0.450",
        novel_idea_rate="0.900",
        summary_tendency="0.300",
        time_awareness="0.350",
        detail_focus="0.350",
        cooperation="0.650",
        error_rate="0.150",
        off_topic_rate="0.150",
    ),
    _persona(
        id_value="10000000-0000-4000-8000-000000000003",
        code="GENTLE_COORDINATOR",
        display_name="温和协调者",
        speech_style_code="SUPPORTIVE",
        initiative="0.500",
        interrupt_tendency="0.100",
        average_turn_seconds=35,
        stance_stability="0.450",
        persuasion_threshold="0.400",
        novel_idea_rate="0.450",
        summary_tendency="0.750",
        time_awareness="0.650",
        detail_focus="0.550",
        cooperation="0.900",
        error_rate="0.080",
        off_topic_rate="0.050",
    ),
    _persona(
        id_value="10000000-0000-4000-8000-000000000004",
        code="ASSERTIVE_FACILITATOR",
        display_name="强势控场者",
        speech_style_code="DIRECT",
        initiative="0.850",
        interrupt_tendency="0.650",
        average_turn_seconds=38,
        stance_stability="0.750",
        persuasion_threshold="0.700",
        novel_idea_rate="0.450",
        summary_tendency="0.550",
        time_awareness="0.600",
        detail_focus="0.400",
        cooperation="0.500",
        error_rate="0.150",
        off_topic_rate="0.080",
    ),
)


def _stance(
    initial_position: str,
    dimension: str,
    weight: str,
    preferred_group_role: str,
) -> PrivateStanceDefinition:
    return PrivateStanceDefinition(
        initial_position=initial_position,
        priority_dimensions=(
            PriorityDimension(code=dimension, weight=Decimal(weight)),
        ),
        concession_conditions=("出现与硬约束一致、可复核的新证据。",),
        private_information=None,
        red_lines=("不得以未验证的假设突破题目硬约束。",),
        preferred_group_role=preferred_group_role,
    )


INTERNAL_VALIDATION_BUNDLE = PublishedQuestionBundle(
    template_id=UUID("20000000-0000-4000-8000-000000000001"),
    template_code="INTERNAL_VALIDATION_RESOURCE_ALLOCATION",
    version_id=UUID("21000000-0000-4000-8000-000000000001"),
    version_number=1,
    content=QuestionVersionContent(
        title="内部验证：社区活动资源安排",
        question_type_code="RESOURCE_ALLOCATION",
        background_domain_code="GENERAL",
        difficulty_code="STANDARD",
        scenario="内部工程验证题：团队需要在有限资源下安排三类社区活动。",
        objective="形成满足硬约束、说明取舍且可执行的资源安排。",
        estimated_minutes=25,
        hard_constraints=(
            ConstraintItem(key="BUDGET", text="总资源不得超过 100 个单位。"),
        ),
        soft_constraints=(
            ConstraintItem(key="BALANCE", text="兼顾覆盖面与长期价值。"),
        ),
        stakeholders=(
            StakeholderItem(
                key="RESIDENTS", name="社区居民", description="活动服务对象。"
            ),
        ),
        options=(
            QuestionOption(key="A", label="基础服务", description="保障最大覆盖面。"),
            QuestionOption(
                key="B", label="能力建设", description="提升长期自组织能力。"
            ),
            QuestionOption(key="C", label="主题活动", description="形成短期参与热度。"),
        ),
        reference_dimensions=(
            ReferenceDimension(
                key="FEASIBILITY", name="可行性", description="资源与时间内可落地。"
            ),
            ReferenceDimension(
                key="LONG_TERM_VALUE", name="长期价值", description="能否形成持续影响。"
            ),
        ),
        hidden_conflicts=(
            InternalTextItem(
                key="REACH_VS_DEPTH", text="覆盖面与单点投入深度存在冲突。"
            ),
        ),
        acceptable_outcome_patterns=(
            InternalTextItem(
                key="TRACEABLE", text="结果能追溯到约束、维度和明确取舍。"
            ),
        ),
        phase_prompts=PhasePromptSet.model_validate(
            {
                "PREPARATION": "识别硬约束和关键维度。",
                "CONVERGENCE": "收敛到一个可执行且理由清晰的方案。",
            }
        ),
        safety_tags=("INTERNAL_VALIDATION_ONLY",),
    ),
    assignments=(
        PersonaAssignmentDefinition(
            id=UUID("22000000-0000-4000-8000-000000000001"),
            slot=1,
            persona_template_id=V01_PERSONA_TEMPLATES[0].id,
            private_stance=_stance(
                "优先满足可行性与硬约束。", "FEASIBILITY", "0.900", "分析与校验"
            ),
        ),
        PersonaAssignmentDefinition(
            id=UUID("22000000-0000-4000-8000-000000000002"),
            slot=2,
            persona_template_id=V01_PERSONA_TEMPLATES[1].id,
            private_stance=_stance(
                "优先探索能兼顾多目标的新组合。", "LONG_TERM_VALUE", "0.800", "方案发散"
            ),
        ),
        PersonaAssignmentDefinition(
            id=UUID("22000000-0000-4000-8000-000000000003"),
            slot=3,
            persona_template_id=V01_PERSONA_TEMPLATES[2].id,
            private_stance=_stance(
                "优先促成各方可接受的平衡方案。", "FEASIBILITY", "0.700", "协调与总结"
            ),
        ),
    ),
    created_at=_SEED_TIME,
    published_at=_SEED_TIME,
)

V01_QUESTION_BUNDLES = (
    INTERNAL_VALIDATION_BUNDLE,
    *ADDITIONAL_V01_QUESTION_BUNDLES,
)


_PERSONA_FIELDS = (
    "id",
    "code",
    "display_name",
    "speech_style_code",
    "initiative",
    "interrupt_tendency",
    "average_turn_seconds",
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
    "created_at",
)


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, tuple):
        return [_json_value(item) for item in cast(tuple[object, ...], value)]
    if isinstance(value, list):
        return [_json_value(item) for item in cast(list[object], value)]
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        return {str(key): _json_value(item) for key, item in mapping.items()}
    if isinstance(value, BaseModel):
        dumped = cast(dict[str, object], value.model_dump())
        return _json_value(dumped)
    return value


async def _seed_persona(
    session: AsyncSession,
    definition: PersonaTemplateDefinition,
) -> bool:
    by_code = await session.scalar(
        select(PersonaTemplate).where(PersonaTemplate.code == definition.code)
    )
    by_id = await session.get(PersonaTemplate, definition.id)
    existing = by_code or by_id
    if existing is None:
        session.add(PersonaTemplate(**definition.model_dump()))
        await session.flush()
        return True
    if any(
        getattr(existing, field) != getattr(definition, field)
        for field in _PERSONA_FIELDS
    ):
        raise SeedDataConflictError(f"persona seed drift: {definition.code}")
    return False


def _version_values(bundle: PublishedQuestionBundle) -> dict[str, object]:
    content = bundle.content
    return {
        "id": bundle.version_id,
        "question_template_id": bundle.template_id,
        "version_number": bundle.version_number,
        "title": content.title,
        "question_type_code": content.question_type_code,
        "background_domain_code": content.background_domain_code,
        "difficulty_code": content.difficulty_code,
        "scenario": content.scenario,
        "objective": content.objective,
        "estimated_minutes": content.estimated_minutes,
        "hard_constraints": _json_value(content.hard_constraints),
        "soft_constraints": _json_value(content.soft_constraints),
        "stakeholders": _json_value(content.stakeholders),
        "options": _json_value(content.options),
        "reference_dimensions": _json_value(content.reference_dimensions),
        "hidden_conflicts": _json_value(content.hidden_conflicts),
        "acceptable_outcome_patterns": _json_value(content.acceptable_outcome_patterns),
        "phase_prompts": _json_value(
            content.phase_prompts.model_dump(by_alias=True, exclude_none=True)
        ),
        "safety_tags": _json_value(content.safety_tags),
        "created_at": bundle.created_at,
        "published_at": bundle.published_at,
    }


def _version_matches(version: QuestionVersion, expected: dict[str, object]) -> bool:
    return all(getattr(version, name) == value for name, value in expected.items())


async def _existing_bundle_matches(
    session: AsyncSession,
    bundle: PublishedQuestionBundle,
    version: QuestionVersion,
) -> bool:
    if not _version_matches(version, _version_values(bundle)):
        return False
    assignments = list(
        (
            await session.scalars(
                select(QuestionPersonaAssignment)
                .where(QuestionPersonaAssignment.question_version_id == version.id)
                .order_by(QuestionPersonaAssignment.slot)
            )
        ).all()
    )
    if len(assignments) != len(bundle.assignments):
        return False
    for stored, expected in zip(assignments, bundle.assignments, strict=True):
        if (
            stored.id != expected.id
            or stored.slot != expected.slot
            or stored.persona_template_id != expected.persona_template_id
            or stored.created_at != bundle.created_at
        ):
            return False
        stance = await session.get(PersonaPrivateStance, stored.id)
        expected_stance = expected.private_stance
        if stance is None or any(
            (
                stance.initial_position != expected_stance.initial_position,
                stance.priority_dimensions
                != _json_value(expected_stance.priority_dimensions),
                stance.concession_conditions
                != list(expected_stance.concession_conditions),
                stance.private_information != expected_stance.private_information,
                stance.red_lines != list(expected_stance.red_lines),
                stance.preferred_group_role != expected_stance.preferred_group_role,
                stance.created_at != bundle.created_at,
            )
        ):
            return False
    return True


async def persist_published_question_bundle(
    session: AsyncSession,
    bundle: PublishedQuestionBundle,
) -> bool:
    """Insert a published bundle or verify an exact existing copy; never update."""
    template_by_code = await session.scalar(
        select(QuestionTemplate).where(QuestionTemplate.code == bundle.template_code)
    )
    template_by_id = await session.get(QuestionTemplate, bundle.template_id)
    template = template_by_code or template_by_id
    if template is None:
        template = QuestionTemplate(
            id=bundle.template_id,
            code=bundle.template_code,
            created_at=bundle.created_at,
        )
        session.add(template)
        await session.flush()
    elif template.id != bundle.template_id or template.code != bundle.template_code:
        raise PublishedQuestionMutationError(
            f"question template identity conflict: {bundle.template_code}"
        )

    version_by_id = await session.get(QuestionVersion, bundle.version_id)
    version_by_number = await session.scalar(
        select(QuestionVersion).where(
            QuestionVersion.question_template_id == bundle.template_id,
            QuestionVersion.version_number == bundle.version_number,
        )
    )
    existing = version_by_id or version_by_number
    if existing is not None:
        if await _existing_bundle_matches(session, bundle, existing):
            return False
        raise PublishedQuestionMutationError(
            f"published question version conflict: {bundle.template_code}@{bundle.version_number}"
        )

    if template.retired_at is not None:
        raise PublishedQuestionMutationError(
            f"question template is retired: {bundle.template_code}"
        )

    persona_ids = tuple(
        assignment.persona_template_id for assignment in bundle.assignments
    )
    personas = {
        persona.id: persona
        for persona in (
            await session.scalars(
                select(PersonaTemplate).where(PersonaTemplate.id.in_(persona_ids))
            )
        ).all()
    }
    for persona_id in persona_ids:
        persona = personas.get(persona_id)
        if persona is None or persona.retired_at is not None:
            raise PublishedQuestionMutationError(
                f"persona template is unavailable: {persona_id}"
            )

    session.add(QuestionVersion(**_version_values(bundle)))
    await session.flush()
    for assignment in bundle.assignments:
        session.add(
            QuestionPersonaAssignment(
                id=assignment.id,
                question_version_id=bundle.version_id,
                slot=assignment.slot,
                persona_template_id=assignment.persona_template_id,
                created_at=bundle.created_at,
            )
        )
        await session.flush()
        stance = assignment.private_stance
        session.add(
            PersonaPrivateStance(
                assignment_id=assignment.id,
                initial_position=stance.initial_position,
                priority_dimensions=_json_value(stance.priority_dimensions),
                concession_conditions=list(stance.concession_conditions),
                private_information=stance.private_information,
                red_lines=list(stance.red_lines),
                preferred_group_role=stance.preferred_group_role,
                created_at=bundle.created_at,
            )
        )
    await session.flush()
    return True


async def seed_question_persona_foundation(
    session_factory: async_sessionmaker[AsyncSession],
) -> SeedResult:
    """Seed the deterministic P1-2B foundation in one owned transaction."""
    personas_inserted = 0
    question_versions_inserted = 0
    async with session_factory() as session:
        async with session.begin():
            for persona in V01_PERSONA_TEMPLATES:
                personas_inserted += int(await _seed_persona(session, persona))
            for bundle in V01_QUESTION_BUNDLES:
                question_versions_inserted += int(
                    await persist_published_question_bundle(session, bundle)
                )
    return SeedResult(
        personas_inserted=personas_inserted,
        question_versions_inserted=question_versions_inserted,
    )
