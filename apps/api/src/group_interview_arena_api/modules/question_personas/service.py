from dataclasses import dataclass
from typing import Never
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db import (
    PersonaPrivateStance,
    PersonaTemplate,
    QuestionPersonaAssignment,
    QuestionTemplate,
    QuestionVersion,
)
from group_interview_arena_api.modules.question_personas.domain import (
    ConstraintItem,
    QuestionOption,
    StakeholderItem,
)


class QuestionNotFoundError(Exception):
    pass


class QuestionPersistenceError(Exception):
    pass


@dataclass(frozen=True)
class PublicQuestionSummary:
    id: UUID
    question_template_id: UUID
    version_number: int
    title: str
    question_type: str
    background_domain: str
    difficulty: str
    estimated_minutes: int


@dataclass(frozen=True)
class PublicQuestionDetail(PublicQuestionSummary):
    scenario: str
    objective: str
    hard_constraints: tuple[ConstraintItem, ...]
    soft_constraints: tuple[ConstraintItem, ...]
    stakeholders: tuple[StakeholderItem, ...]
    options: tuple[QuestionOption, ...]


def _raise_persistence_error() -> Never:
    raise QuestionPersistenceError from None


async def _has_complete_active_assignments(
    session: AsyncSession,
    question_version_id: UUID,
    *,
    lock: bool,
) -> bool:
    statement = (
        select(QuestionPersonaAssignment)
        .where(QuestionPersonaAssignment.question_version_id == question_version_id)
        .order_by(QuestionPersonaAssignment.slot)
    )
    if lock:
        statement = statement.with_for_update()
    assignments = list((await session.scalars(statement)).all())
    if len(assignments) != 3 or [item.slot for item in assignments] != [1, 2, 3]:
        return False

    for assignment in assignments:
        persona = await session.get(
            PersonaTemplate,
            assignment.persona_template_id,
            with_for_update=lock,
        )
        stance = await session.get(
            PersonaPrivateStance,
            assignment.id,
            with_for_update=lock,
        )
        if persona is None or persona.retired_at is not None or stance is None:
            return False
    return True


async def require_selectable_question_version(
    session: AsyncSession,
    question_version_id: UUID,
) -> None:
    """Lock and validate the exact immutable version used by a new session."""
    try:
        pair = (
            await session.execute(
                select(QuestionVersion, QuestionTemplate)
                .join(
                    QuestionTemplate,
                    QuestionTemplate.id == QuestionVersion.question_template_id,
                )
                .where(QuestionVersion.id == question_version_id)
                .with_for_update()
            )
        ).one_or_none()
        if pair is None:
            raise QuestionNotFoundError
        version, template = pair
        if (
            version.published_at is None
            or version.retired_at is not None
            or template.retired_at is not None
            or not await _has_complete_active_assignments(
                session,
                question_version_id,
                lock=True,
            )
        ):
            raise QuestionNotFoundError
    except QuestionNotFoundError:
        raise
    except SQLAlchemyError:
        _raise_persistence_error()


def _summary(version: QuestionVersion) -> PublicQuestionSummary:
    return PublicQuestionSummary(
        id=version.id,
        question_template_id=version.question_template_id,
        version_number=version.version_number,
        title=version.title,
        question_type=version.question_type_code,
        background_domain=version.background_domain_code,
        difficulty=version.difficulty_code,
        estimated_minutes=version.estimated_minutes,
    )


def _detail(version: QuestionVersion) -> PublicQuestionDetail:
    try:
        hard_constraints = tuple(
            ConstraintItem.model_validate(item) for item in version.hard_constraints
        )
        soft_constraints = tuple(
            ConstraintItem.model_validate(item) for item in version.soft_constraints
        )
        stakeholders = tuple(
            StakeholderItem.model_validate(item) for item in version.stakeholders
        )
        options = tuple(QuestionOption.model_validate(item) for item in version.options)
    except ValidationError:
        _raise_persistence_error()
    summary = _summary(version)
    return PublicQuestionDetail(
        **summary.__dict__,
        scenario=version.scenario,
        objective=version.objective,
        hard_constraints=hard_constraints,
        soft_constraints=soft_constraints,
        stakeholders=stakeholders,
        options=options,
    )


async def list_selectable_questions(
    session: AsyncSession,
) -> list[PublicQuestionSummary]:
    try:
        versions = list(
            (
                await session.scalars(
                    select(QuestionVersion)
                    .join(
                        QuestionTemplate,
                        QuestionTemplate.id == QuestionVersion.question_template_id,
                    )
                    .where(
                        QuestionVersion.published_at.is_not(None),
                        QuestionVersion.retired_at.is_(None),
                        QuestionTemplate.retired_at.is_(None),
                    )
                    .order_by(QuestionVersion.title, QuestionVersion.id)
                )
            ).all()
        )
        return [
            _summary(version)
            for version in versions
            if await _has_complete_active_assignments(
                session,
                version.id,
                lock=False,
            )
        ]
    except SQLAlchemyError:
        _raise_persistence_error()


async def get_public_question(
    session: AsyncSession,
    question_version_id: UUID,
) -> PublicQuestionDetail:
    try:
        version = await session.scalar(
            select(QuestionVersion).where(
                QuestionVersion.id == question_version_id,
                QuestionVersion.published_at.is_not(None),
            )
        )
    except SQLAlchemyError:
        _raise_persistence_error()
    if version is None:
        raise QuestionNotFoundError
    return _detail(version)
