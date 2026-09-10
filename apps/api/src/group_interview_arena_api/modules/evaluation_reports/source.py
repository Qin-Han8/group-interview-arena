from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import (
    DiscussionEvent,
    EvaluationReport,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    SessionStatus,
    StoredEvent,
)
from group_interview_arena_api.modules.discussion_sessions.public_events import (
    PublicEventProjectionError,
    project_public_events,
)
from group_interview_arena_api.modules.evaluation_reports.domain import (
    EvidencePhase,
    ReportParticipantSource,
    ReportQuestionConstraint,
    ReportQuestionOption,
    ReportQuestionSnapshot,
    ReportQuestionStakeholder,
    ReportSourceSnapshot,
    ReportUtteranceSource,
)
from group_interview_arena_api.modules.floor_control.domain import (
    ParticipantActorKind,
)
from group_interview_arena_api.modules.question_personas.service import (
    QuestionNotFoundError,
    QuestionPersistenceError,
    get_public_question,
)

_UTTERANCE_EVENT_TYPE = "participant.utterance.created"


class ReportSourceCollectionError(RuntimeError):
    pass


class ReportSourceCollector:
    async def collect(
        self,
        session: AsyncSession,
        *,
        report_id: UUID,
        session_id: UUID,
    ) -> ReportSourceSnapshot:
        try:
            pair = (
                await session.execute(
                    select(EvaluationReport, SimulationSession)
                    .join(
                        SimulationSession,
                        SimulationSession.id == EvaluationReport.session_id,
                    )
                    .where(
                        EvaluationReport.id == report_id,
                        EvaluationReport.session_id == session_id,
                        SimulationSession.id == session_id,
                    )
                )
            ).one_or_none()
            if pair is None:
                raise ReportSourceCollectionError
            report, simulation = pair
            if (
                simulation.status != SessionStatus.COMPLETED.value
                or simulation.question_version_id is None
            ):
                raise ReportSourceCollectionError

            public_question = await get_public_question(
                session,
                simulation.question_version_id,
            )
            participant_rows = tuple(
                (
                    await session.scalars(
                        select(SessionParticipant)
                        .where(SessionParticipant.session_id == session_id)
                        .order_by(
                            SessionParticipant.seat_order.asc(),
                            SessionParticipant.id.asc(),
                        )
                    )
                ).all()
            )
            participants = tuple(
                ReportParticipantSource(
                    participant_id=row.id,
                    actor_kind=ParticipantActorKind(row.actor_kind),
                    seat_order=row.seat_order,
                )
                for row in participant_rows
            )
            roster = {item.participant_id: item.actor_kind for item in participants}

            event_rows = tuple(
                (
                    await session.scalars(
                        select(DiscussionEvent)
                        .where(
                            DiscussionEvent.session_id == session_id,
                            DiscussionEvent.event_type == _UTTERANCE_EVENT_TYPE,
                            DiscussionEvent.sequence <= report.source_through_sequence,
                        )
                        .order_by(DiscussionEvent.sequence.asc())
                    )
                ).all()
            )
            stored_events = tuple(
                StoredEvent(
                    event_version=row.event_version,
                    event_type=row.event_type,
                    session_id=row.session_id,
                    sequence=row.sequence,
                    occurred_at=row.occurred_at,
                    causation_action_id=row.causation_action_id,
                    payload=row.payload,
                )
                for row in event_rows
            )
            projected = await project_public_events(session, stored_events)
            utterances: list[ReportUtteranceSource] = []
            for event in projected:
                if (
                    event.type != _UTTERANCE_EVENT_TYPE
                    or event.schema_version != 1
                    or event.session_id != session_id
                ):
                    raise ReportSourceCollectionError
                participant_id = UUID(str(event.payload["participant_id"]))
                actor_kind = ParticipantActorKind(str(event.payload["actor_kind"]))
                if roster.get(participant_id) is not actor_kind:
                    raise ReportSourceCollectionError
                if actor_kind is ParticipantActorKind.HUMAN:
                    utterance_actor_kind = ParticipantActorKind.HUMAN
                elif actor_kind is ParticipantActorKind.AI:
                    utterance_actor_kind = ParticipantActorKind.AI
                else:
                    raise ReportSourceCollectionError
                content = event.payload["content"]
                if not isinstance(content, str):
                    raise ReportSourceCollectionError
                utterances.append(
                    ReportUtteranceSource(
                        utterance_id=UUID(str(event.payload["utterance_id"])),
                        source_event_sequence=event.sequence,
                        occurred_at=event.occurred_at,
                        participant_id=participant_id,
                        actor_kind=utterance_actor_kind,
                        floor_grant_id=UUID(str(event.payload["floor_grant_id"])),
                        phase=EvidencePhase(str(event.payload["phase"])),
                        content=content,
                    )
                )

            question = ReportQuestionSnapshot(
                id=public_question.id,
                question_template_id=public_question.question_template_id,
                version_number=public_question.version_number,
                title=public_question.title,
                question_type=public_question.question_type,
                background_domain=public_question.background_domain,
                difficulty=public_question.difficulty,
                estimated_minutes=public_question.estimated_minutes,
                scenario=public_question.scenario,
                objective=public_question.objective,
                hard_constraints=tuple(
                    ReportQuestionConstraint(key=item.key, text=item.text)
                    for item in public_question.hard_constraints
                ),
                soft_constraints=tuple(
                    ReportQuestionConstraint(key=item.key, text=item.text)
                    for item in public_question.soft_constraints
                ),
                stakeholders=tuple(
                    ReportQuestionStakeholder(
                        key=item.key,
                        name=item.name,
                        description=item.description,
                    )
                    for item in public_question.stakeholders
                ),
                options=tuple(
                    ReportQuestionOption(
                        key=item.key,
                        label=item.label,
                        description=item.description,
                    )
                    for item in public_question.options
                ),
            )
            return ReportSourceSnapshot(
                source_contract_version=1,
                report_id=report.id,
                session_id=report.session_id,
                report_schema_version=report.report_schema_version,
                derivation_version=report.derivation_version,
                source_through_sequence=report.source_through_sequence,
                question=question,
                participants=participants,
                utterances=tuple(utterances),
            )
        except ReportSourceCollectionError:
            raise
        except (
            KeyError,
            PublicEventProjectionError,
            QuestionNotFoundError,
            QuestionPersistenceError,
            SQLAlchemyError,
            TypeError,
            ValueError,
        ) as error:
            raise ReportSourceCollectionError from error
