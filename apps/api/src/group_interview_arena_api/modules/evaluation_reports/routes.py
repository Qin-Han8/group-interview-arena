from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import Settings
from group_interview_arena_api.core.errors import ApiError, ErrorCode, ErrorResponse
from group_interview_arena_api.db.dependencies import get_database_session_factory
from group_interview_arena_api.identity.csrf import (
    CSRF_OPENAPI_EXTRA,
    create_browser_csrf_guard,
)
from group_interview_arena_api.identity.dependencies import CurrentUserDependency
from group_interview_arena_api.modules.evaluation_reports.contracts import (
    CompletedReportContentResponse,
    EvidenceCardResponse,
    ReportMetadataResponse,
    ReportViewResponse,
    SessionOverviewResponse,
)
from group_interview_arena_api.modules.evaluation_reports.coordinator import (
    ReportGenerationCoordinator,
    ReportGenerationError,
    ReportGenerationPersistenceError,
)
from group_interview_arena_api.modules.evaluation_reports.domain import (
    EvaluationReportSnapshot,
    ReportQuestionSnapshot,
)
from group_interview_arena_api.modules.evaluation_reports.evaluation import (
    DeterministicReportEvaluator,
)
from group_interview_arena_api.modules.evaluation_reports.query import (
    CompletedReportContentView,
    ReportView,
    ReportViewNotFoundError,
    ReportViewPersistenceError,
    load_current_report_view,
)
from group_interview_arena_api.modules.evaluation_reports.service import (
    EvaluationReportPersistenceError,
    ReportSessionIneligibleError,
    ReportSessionNotFoundError,
)
from group_interview_arena_api.modules.question_personas.contracts import (
    PublicConstraint,
    PublicQuestionOption,
    PublicStakeholder,
    QuestionDetailResponse,
)

DatabaseSessionFactory = Annotated[
    async_sessionmaker[AsyncSession],
    Depends(get_database_session_factory),
]

V01_REPORT_SCHEMA_VERSION = 1
V01_REPORT_DERIVATION_VERSION = "basic-report/v1"
V01_REPORT_GENERATION_LEASE = timedelta(minutes=5)


def _internal_error() -> ApiError:
    return ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
    )


def _not_found() -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        code=ErrorCode.REPORT_NOT_FOUND,
        message="Report not found.",
    )


def _invalid_session_state() -> ApiError:
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        code=ErrorCode.INVALID_SESSION_STATE,
        message="Report generation requires a completed session.",
    )


def _metadata_response(report: EvaluationReportSnapshot) -> ReportMetadataResponse:
    return ReportMetadataResponse(
        report_id=report.report_id,
        session_id=report.session_id,
        status=report.status,
        report_schema_version=report.report_schema_version,
        derivation_version=report.derivation_version,
        source_through_sequence=report.source_through_sequence,
        created_at=report.created_at,
        completed_at=report.completed_at,
    )


def _question_response(question: ReportQuestionSnapshot) -> QuestionDetailResponse:
    return QuestionDetailResponse(
        id=question.id,
        question_template_id=question.question_template_id,
        version_number=question.version_number,
        title=question.title,
        question_type=question.question_type,
        background_domain=question.background_domain,
        difficulty=question.difficulty,
        estimated_minutes=question.estimated_minutes,
        scenario=question.scenario,
        objective=question.objective,
        hard_constraints=tuple(
            PublicConstraint(key=item.key, text=item.text)
            for item in question.hard_constraints
        ),
        soft_constraints=tuple(
            PublicConstraint(key=item.key, text=item.text)
            for item in question.soft_constraints
        ),
        stakeholders=tuple(
            PublicStakeholder(
                key=item.key,
                name=item.name,
                description=item.description,
            )
            for item in question.stakeholders
        ),
        options=tuple(
            PublicQuestionOption(
                key=item.key,
                label=item.label,
                description=item.description,
            )
            for item in question.options
        ),
    )


def _content_response(
    content: CompletedReportContentView,
) -> CompletedReportContentResponse:
    return CompletedReportContentResponse(
        overview=SessionOverviewResponse(
            session_status="COMPLETED",
            question=_question_response(content.overview.question),
            participant_count=content.overview.participant_count,
            human_utterance_count=content.overview.human_utterance_count,
            ai_utterance_count=content.overview.ai_utterance_count,
            total_utterance_count=content.overview.total_utterance_count,
            covered_phases=content.overview.covered_phases,
            summary=content.overview.summary,
        ),
        strengths=tuple(
            EvidenceCardResponse.model_validate(item.__dict__)
            for item in content.strengths
        ),
        improvements=tuple(
            EvidenceCardResponse.model_validate(item.__dict__)
            for item in content.improvements
        ),
        priority_improvement=content.priority_improvement,
    )


def _response(view: ReportView) -> ReportViewResponse:
    return ReportViewResponse(
        report=ReportMetadataResponse.model_validate(view.report.__dict__),
        content=(_content_response(view.content) if view.content is not None else None),
    )


def create_evaluation_report_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/sessions", tags=["reports"])
    require_browser_csrf = create_browser_csrf_guard(settings.cors_origins)

    @router.post(
        "/{session_id}/report",
        response_model=ReportMetadataResponse,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        dependencies=[Depends(require_browser_csrf)],
        openapi_extra=CSRF_OPENAPI_EXTRA,
    )
    async def generate_report(  # pyright: ignore[reportUnusedFunction]
        session_id: UUID4,
        user: CurrentUserDependency,
        session_factory: DatabaseSessionFactory,
    ) -> ReportMetadataResponse:
        coordinator = ReportGenerationCoordinator(session_factory)
        try:
            report = await coordinator.generate(
                owner_id=user.user_id,
                session_id=session_id,
                report_schema_version=V01_REPORT_SCHEMA_VERSION,
                derivation_version=V01_REPORT_DERIVATION_VERSION,
                evaluator=DeterministicReportEvaluator(),
                lease_duration=V01_REPORT_GENERATION_LEASE,
            )
        except ReportSessionNotFoundError:
            raise _not_found() from None
        except ReportSessionIneligibleError:
            raise _invalid_session_state() from None
        except (
            EvaluationReportPersistenceError,
            ReportGenerationPersistenceError,
            ReportGenerationError,
        ):
            raise _internal_error() from None
        return _metadata_response(report)

    @router.get(
        "/{session_id}/report",
        response_model=ReportViewResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def report(  # pyright: ignore[reportUnusedFunction]
        session_id: UUID4,
        user: CurrentUserDependency,
        session_factory: DatabaseSessionFactory,
    ) -> ReportViewResponse:
        try:
            async with session_factory() as session:
                view = await load_current_report_view(
                    session,
                    owner_id=user.user_id,
                    session_id=session_id,
                )
        except ReportViewNotFoundError:
            raise _not_found() from None
        except ReportViewPersistenceError:
            raise _internal_error() from None
        return _response(view)

    return router
