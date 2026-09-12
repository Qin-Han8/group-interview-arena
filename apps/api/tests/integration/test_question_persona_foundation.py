import asyncio
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import uuid4

import pytest
from sqlalchemy import URL, delete, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db import (
    PersonaPrivateStance,
    PersonaTemplate,
    QuestionPersonaAssignment,
    QuestionTemplate,
    QuestionVersion,
    SimulationSession,
    User,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.question_personas.domain import (
    PublishedQuestionBundle,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    V01_PERSONA_TEMPLATES,
    PublishedQuestionMutationError,
    SeedDataConflictError,
    persist_published_question_bundle,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


async def _with_database(
    temporary_database: TemporaryDatabaseContext,
) -> tuple[async_sessionmaker[AsyncSession], Any]:
    engine = create_database_engine(temporary_database.database_settings())
    return create_database_session_factory(engine), engine


async def _verify_repeatable_seed_and_private_relation(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    try:
        first = await seed_question_persona_foundation(session_factory)
        second = await seed_question_persona_foundation(session_factory)
        assert first.personas_inserted == 4
        assert first.question_versions_inserted == 12
        assert second.personas_inserted == 0
        assert second.question_versions_inserted == 0

        async with session_factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(PersonaTemplate))
                == 4
            )
            assert (
                await session.scalar(select(func.count()).select_from(QuestionTemplate))
                == 12
            )
            assert (
                await session.scalar(select(func.count()).select_from(QuestionVersion))
                == 12
            )
            assert (
                await session.scalar(
                    select(func.count()).select_from(QuestionPersonaAssignment)
                )
                == 36
            )
            assert (
                await session.scalar(
                    select(func.count()).select_from(PersonaPrivateStance)
                )
                == 36
            )
            assignment_ids = set(
                (await session.scalars(select(QuestionPersonaAssignment.id))).all()
            )
            stance_assignment_ids = set(
                (
                    await session.scalars(select(PersonaPrivateStance.assignment_id))
                ).all()
            )
            assert stance_assignment_ids == assignment_ids
    finally:
        await dispose_database_engine(engine)


async def _verify_published_bundle_is_insert_only(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    try:
        await seed_question_persona_foundation(session_factory)
        changed_content = INTERNAL_VALIDATION_BUNDLE.content.model_copy(
            update={"title": "被覆盖的标题"}
        )
        changed_bundle = INTERNAL_VALIDATION_BUNDLE.model_copy(
            update={"content": changed_content}
        )
        async with session_factory() as session:
            with pytest.raises(PublishedQuestionMutationError):
                async with session.begin():
                    await persist_published_question_bundle(session, changed_bundle)

        async with session_factory() as session:
            stored = await session.get(
                QuestionVersion, INTERNAL_VALIDATION_BUNDLE.version_id
            )
            assert stored is not None
            assert stored.title == INTERNAL_VALIDATION_BUNDLE.content.title

        next_assignments = tuple(
            assignment.model_copy(update={"id": uuid4()})
            for assignment in INTERNAL_VALIDATION_BUNDLE.assignments
        )
        next_bundle = INTERNAL_VALIDATION_BUNDLE.model_copy(
            update={
                "version_id": uuid4(),
                "version_number": 2,
                "assignments": next_assignments,
            }
        )
        async with session_factory() as session:
            async with session.begin():
                inserted = await persist_published_question_bundle(session, next_bundle)
            assert inserted is True

        async with session_factory() as session:
            versions = list(
                (
                    await session.scalars(
                        select(QuestionVersion)
                        .where(
                            QuestionVersion.question_template_id
                            == INTERNAL_VALIDATION_BUNDLE.template_id
                        )
                        .order_by(QuestionVersion.version_number)
                    )
                ).all()
            )
            assert [version.version_number for version in versions] == [1, 2]
            assert versions[0].title == INTERNAL_VALIDATION_BUNDLE.content.title
    finally:
        await dispose_database_engine(engine)


async def _verify_seed_drift_fails_without_partial_writes(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    try:
        drifted_persona = V01_PERSONA_TEMPLATES[2]
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    PersonaTemplate(
                        **{
                            **drifted_persona.model_dump(),
                            "display_name": "漂移名称",
                        }
                    )
                )

        with pytest.raises(SeedDataConflictError):
            await seed_question_persona_foundation(session_factory)

        async with session_factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(PersonaTemplate))
                == 1
            )
            assert (
                await session.scalar(select(func.count()).select_from(QuestionTemplate))
                == 0
            )
    finally:
        await dispose_database_engine(engine)


async def _verify_retirement_preserves_session_history_and_fk_restrict(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    try:
        await seed_question_persona_foundation(session_factory)
        user_id = uuid4()
        session_id = uuid4()
        retired_at = datetime(2026, 8, 18, tzinfo=UTC)
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=user_id,
                        username=f"user_{user_id.hex[:12]}",
                        password_hash="hash",
                    )
                )
                await session.flush()
                session.add(
                    SimulationSession(
                        id=session_id,
                        owner_user_id=user_id,
                        question_version_id=INTERNAL_VALIDATION_BUNDLE.version_id,
                        status="CREATED",
                    )
                )
                await session.execute(
                    update(QuestionVersion)
                    .where(QuestionVersion.id == INTERNAL_VALIDATION_BUNDLE.version_id)
                    .values(retired_at=retired_at)
                )

        async with session_factory() as session:
            historical = await session.get(SimulationSession, session_id)
            assert historical is not None
            assert (
                historical.question_version_id == INTERNAL_VALIDATION_BUNDLE.version_id
            )
            version = await session.get(QuestionVersion, historical.question_version_id)
            assert version is not None
            assert version.retired_at == retired_at
            with pytest.raises(IntegrityError):
                await session.execute(
                    delete(QuestionVersion).where(
                        QuestionVersion.id == INTERNAL_VALIDATION_BUNDLE.version_id
                    )
                )
                await session.commit()
            await session.rollback()
    finally:
        await dispose_database_engine(engine)


def _next_version_bundle() -> PublishedQuestionBundle:
    return INTERNAL_VALIDATION_BUNDLE.model_copy(
        update={
            "version_id": uuid4(),
            "version_number": 2,
            "assignments": tuple(
                assignment.model_copy(update={"id": uuid4()})
                for assignment in INTERNAL_VALIDATION_BUNDLE.assignments
            ),
        }
    )


async def _verify_retired_template_blocks_only_new_versions(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    try:
        await seed_question_persona_foundation(session_factory)
        async with session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(QuestionTemplate)
                    .where(
                        QuestionTemplate.id == INTERNAL_VALIDATION_BUNDLE.template_id
                    )
                    .values(retired_at=datetime(2026, 8, 18, tzinfo=UTC))
                )
                await session.execute(
                    update(PersonaTemplate)
                    .where(
                        PersonaTemplate.id
                        == INTERNAL_VALIDATION_BUNDLE.assignments[0].persona_template_id
                    )
                    .values(retired_at=datetime(2026, 8, 18, tzinfo=UTC))
                )

        async with session_factory() as session:
            async with session.begin():
                assert (
                    await persist_published_question_bundle(
                        session, INTERNAL_VALIDATION_BUNDLE
                    )
                    is False
                )

        async with session_factory() as session:
            with pytest.raises(PublishedQuestionMutationError):
                async with session.begin():
                    await persist_published_question_bundle(
                        session, _next_version_bundle()
                    )

        async with session_factory() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(QuestionVersion)
                    .where(
                        QuestionVersion.question_template_id
                        == INTERNAL_VALIDATION_BUNDLE.template_id
                    )
                )
                == 1
            )
    finally:
        await dispose_database_engine(engine)


async def _verify_retired_persona_blocks_new_assignments(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    try:
        await seed_question_persona_foundation(session_factory)
        retired_persona_id = INTERNAL_VALIDATION_BUNDLE.assignments[
            0
        ].persona_template_id
        async with session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(PersonaTemplate)
                    .where(PersonaTemplate.id == retired_persona_id)
                    .values(retired_at=datetime(2026, 8, 18, tzinfo=UTC))
                )

        async with session_factory() as session:
            with pytest.raises(PublishedQuestionMutationError):
                async with session.begin():
                    await persist_published_question_bundle(
                        session, _next_version_bundle()
                    )

        async with session_factory() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(QuestionVersion)
                    .where(
                        QuestionVersion.question_template_id
                        == INTERNAL_VALIDATION_BUNDLE.template_id
                    )
                )
                == 1
            )
    finally:
        await dispose_database_engine(engine)


async def _verify_retirement_chronology_constraints(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    try:
        await seed_question_persona_foundation(session_factory)
        invalid_updates = (
            update(QuestionTemplate)
            .where(QuestionTemplate.id == INTERNAL_VALIDATION_BUNDLE.template_id)
            .values(retired_at=datetime(2026, 8, 16, tzinfo=UTC)),
            update(PersonaTemplate)
            .where(PersonaTemplate.id == V01_PERSONA_TEMPLATES[0].id)
            .values(retired_at=datetime(2026, 8, 16, tzinfo=UTC)),
            update(QuestionVersion)
            .where(QuestionVersion.id == INTERNAL_VALIDATION_BUNDLE.version_id)
            .values(retired_at=datetime(2026, 8, 16, tzinfo=UTC)),
            update(QuestionVersion)
            .where(QuestionVersion.id == INTERNAL_VALIDATION_BUNDLE.version_id)
            .values(
                published_at=None,
                retired_at=datetime(2026, 8, 18, tzinfo=UTC),
            ),
        )
        for statement in invalid_updates:
            async with session_factory() as session:
                with pytest.raises(IntegrityError):
                    await session.execute(statement)
                    await session.commit()
                await session.rollback()
    finally:
        await dispose_database_engine(engine)


async def _verify_database_checks_reject_invalid_values(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    try:
        await seed_question_persona_foundation(session_factory)
        async with session_factory() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    update(PersonaTemplate)
                    .where(PersonaTemplate.code == "LOGIC_ANALYST")
                    .values(initiative=2)
                )
                await session.commit()
            await session.rollback()

        async with session_factory() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    update(QuestionVersion)
                    .where(QuestionVersion.id == INTERNAL_VALIDATION_BUNDLE.version_id)
                    .values(hard_constraints={"not": "an array"})
                )
                await session.commit()
            await session.rollback()
    finally:
        await dispose_database_engine(engine)


async def _verify_postgresql_numeric_scale_is_canonical_storage(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    try:
        await seed_question_persona_foundation(session_factory)
        async with session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(PersonaTemplate)
                    .where(PersonaTemplate.id == V01_PERSONA_TEMPLATES[0].id)
                    .values(initiative=Decimal("0.1234"))
                )

        async with session_factory() as session:
            initiative = await session.scalar(
                select(PersonaTemplate.initiative).where(
                    PersonaTemplate.id == V01_PERSONA_TEMPLATES[0].id
                )
            )
            assert initiative == Decimal("0.123")
    finally:
        await dispose_database_engine(engine)


async def _verify_exact_postgresql_catalog(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    session_factory, engine = await _with_database(temporary_database)
    del session_factory
    table_names = (
        "persona_private_stances",
        "persona_templates",
        "question_persona_assignments",
        "question_templates",
        "question_versions",
    )
    try:
        async with engine.connect() as connection:
            columns_result = await connection.execute(
                text(
                    "SELECT table_name, string_agg(column_name, ',' ORDER BY ordinal_position) "
                    "FROM information_schema.columns WHERE table_schema = 'public' "
                    "AND table_name = ANY(:tables) GROUP BY table_name"
                ),
                {"tables": list(table_names)},
            )
            columns = {str(row[0]): str(row[1]).split(",") for row in columns_result}
            numeric_result = await connection.execute(
                text(
                    "SELECT column_name, numeric_precision, numeric_scale "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'persona_templates' "
                    "AND data_type = 'numeric' ORDER BY ordinal_position"
                )
            )
            numeric_columns = [
                (str(row[0]), int(row[1]), int(row[2])) for row in numeric_result
            ]
            constraints_result = await connection.execute(
                text(
                    "SELECT conname FROM pg_catalog.pg_constraint "
                    "WHERE connamespace = 'public'::regnamespace "
                    "AND contype IN ('p', 'f', 'c', 'u') "
                    "AND conrelid::regclass::text = ANY(:tables) ORDER BY conname"
                ),
                {"tables": list(table_names)},
            )
            constraints = {str(name) for name in constraints_result.scalars()}
            indexes_result = await connection.execute(
                text(
                    "SELECT indexname FROM pg_catalog.pg_indexes "
                    "WHERE schemaname = 'public' AND tablename = ANY(:tables)"
                ),
                {"tables": list(table_names)},
            )
            indexes = {str(name) for name in indexes_result.scalars()}
            enum_count = await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_catalog.pg_type "
                    "WHERE typtype = 'e' AND typnamespace = 'public'::regnamespace"
                )
            )
    finally:
        await dispose_database_engine(engine)

    assert columns == {
        "question_templates": ["id", "code", "created_at", "retired_at"],
        "question_versions": [
            "id",
            "question_template_id",
            "version_number",
            "title",
            "question_type_code",
            "background_domain_code",
            "difficulty_code",
            "scenario",
            "objective",
            "estimated_minutes",
            "hard_constraints",
            "soft_constraints",
            "stakeholders",
            "options",
            "reference_dimensions",
            "hidden_conflicts",
            "acceptable_outcome_patterns",
            "phase_prompts",
            "safety_tags",
            "created_at",
            "published_at",
            "retired_at",
        ],
        "persona_templates": [
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
            "retired_at",
        ],
        "question_persona_assignments": [
            "id",
            "question_version_id",
            "slot",
            "persona_template_id",
            "created_at",
        ],
        "persona_private_stances": [
            "assignment_id",
            "initial_position",
            "priority_dimensions",
            "concession_conditions",
            "private_information",
            "red_lines",
            "preferred_group_role",
            "created_at",
        ],
    }
    assert numeric_columns == [
        ("initiative", 4, 3),
        ("interrupt_tendency", 4, 3),
        ("stance_stability", 4, 3),
        ("persuasion_threshold", 4, 3),
        ("novel_idea_rate", 4, 3),
        ("summary_tendency", 4, 3),
        ("time_awareness", 4, 3),
        ("detail_focus", 4, 3),
        ("cooperation", 4, 3),
        ("support_user_bias", 4, 3),
        ("error_rate", 4, 3),
        ("off_topic_rate", 4, 3),
    ]
    assert constraints == {
        "ck_persona_private_stances_concession_conditions_array",
        "ck_persona_private_stances_priority_dimensions_array",
        "ck_persona_private_stances_red_lines_array",
        "ck_persona_templates_average_turn_seconds_range",
        "ck_persona_templates_probability_ranges",
        "ck_persona_templates_retired_after_creation",
        "ck_persona_templates_support_user_bias_range",
        "ck_question_persona_assignments_slot_positive",
        "ck_question_versions_acceptable_outcome_patterns_array",
        "ck_question_versions_estimated_minutes_range",
        "ck_question_versions_hard_constraints_array",
        "ck_question_versions_hidden_conflicts_array",
        "ck_question_versions_options_array",
        "ck_question_versions_phase_prompts_object",
        "ck_question_versions_published_after_creation",
        "ck_question_versions_reference_dimensions_array",
        "ck_question_versions_retirement_lifecycle",
        "ck_question_versions_safety_tags_array",
        "ck_question_versions_soft_constraints_array",
        "ck_question_versions_stakeholders_array",
        "ck_question_versions_version_number_positive",
        "ck_question_templates_retired_after_creation",
        "fk_private_stances_assignment_id_assignments",
        "fk_qpa_persona_template_id_persona_templates",
        "fk_qpa_question_version_id_question_versions",
        "fk_question_versions_template_id_question_templates",
        "pk_persona_private_stances",
        "pk_persona_templates",
        "pk_question_persona_assignments",
        "pk_question_templates",
        "pk_question_versions",
        "uq_persona_templates_code",
        "uq_question_persona_assignments_version_persona",
        "uq_question_persona_assignments_version_slot",
        "uq_question_templates_code",
        "uq_question_versions_template_version",
    }
    assert indexes == {
        "pk_persona_private_stances",
        "pk_persona_templates",
        "pk_question_persona_assignments",
        "pk_question_templates",
        "pk_question_versions",
        "uq_persona_templates_code",
        "uq_question_persona_assignments_version_persona",
        "uq_question_persona_assignments_version_slot",
        "uq_question_templates_code",
        "uq_question_versions_template_version",
    }
    assert enum_count == 0


def test_seed_is_deterministic_repeatable_and_stances_are_one_to_one(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_repeatable_seed_and_private_relation(migrated_database))


def test_published_bundle_rejects_mutation_and_allows_new_version(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_published_bundle_is_insert_only(migrated_database))


def test_seed_drift_fails_atomically(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _verify_seed_drift_fails_without_partial_writes(migrated_database)
    )


def test_retirement_preserves_historical_session_reference(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _verify_retirement_preserves_session_history_and_fk_restrict(
            migrated_database
        )
    )


def test_database_checks_reject_numeric_range_and_wrong_json_shape(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_database_checks_reject_invalid_values(migrated_database))


def test_postgresql_numeric_scale_canonicalizes_direct_storage_input(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _verify_postgresql_numeric_scale_is_canonical_storage(migrated_database)
    )


def test_postgresql_catalog_matches_frozen_p1_2b_schema(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_exact_postgresql_catalog(migrated_database))


def test_retired_template_blocks_new_version_but_not_historical_exact_match(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _verify_retired_template_blocks_only_new_versions(migrated_database)
    )


def test_retired_persona_cannot_receive_a_new_assignment(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_retired_persona_blocks_new_assignments(migrated_database))


def test_database_enforces_retirement_timestamp_chronology(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_retirement_chronology_constraints(migrated_database))
