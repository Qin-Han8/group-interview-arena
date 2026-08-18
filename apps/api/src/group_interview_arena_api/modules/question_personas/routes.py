from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.errors import ApiError, ErrorCode, ErrorResponse
from group_interview_arena_api.db.dependencies import get_database_session_factory
from group_interview_arena_api.identity.dependencies import CurrentUserDependency
from group_interview_arena_api.modules.question_personas.contracts import (
    PublicConstraint,
    PublicQuestionOption,
    PublicStakeholder,
    QuestionDetailResponse,
    QuestionSummaryResponse,
)
from group_interview_arena_api.modules.question_personas.service import (
    PublicQuestionDetail,
    PublicQuestionSummary,
    QuestionNotFoundError,
    QuestionPersistenceError,
    get_public_question,
    list_selectable_questions,
)

DatabaseSessionFactory = Annotated[
    async_sessionmaker[AsyncSession],
    Depends(get_database_session_factory),
]


def _summary_response(question: PublicQuestionSummary) -> QuestionSummaryResponse:
    return QuestionSummaryResponse(
        id=question.id,
        question_template_id=question.question_template_id,
        version_number=question.version_number,
        title=question.title,
        question_type=question.question_type,
        background_domain=question.background_domain,
        difficulty=question.difficulty,
        estimated_minutes=question.estimated_minutes,
    )


def _detail_response(question: PublicQuestionDetail) -> QuestionDetailResponse:
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


def _not_found() -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        code=ErrorCode.QUESTION_NOT_FOUND,
        message="Question not found.",
    )


def _internal_error() -> ApiError:
    return ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
    )


def create_question_router() -> APIRouter:
    router = APIRouter(prefix="/questions", tags=["questions"])

    @router.get(
        "",
        response_model=list[QuestionSummaryResponse],
        responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    )
    async def discover(  # pyright: ignore[reportUnusedFunction]
        _user: CurrentUserDependency,
        session_factory: DatabaseSessionFactory,
    ) -> list[QuestionSummaryResponse]:
        try:
            async with session_factory() as session:
                questions = await list_selectable_questions(session)
        except QuestionPersistenceError:
            raise _internal_error() from None
        return [_summary_response(question) for question in questions]

    @router.get(
        "/{question_version_id}",
        response_model=QuestionDetailResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def detail(  # pyright: ignore[reportUnusedFunction]
        question_version_id: UUID4,
        _user: CurrentUserDependency,
        session_factory: DatabaseSessionFactory,
    ) -> QuestionDetailResponse:
        try:
            async with session_factory() as session:
                question = await get_public_question(session, question_version_id)
        except QuestionNotFoundError:
            raise _not_found() from None
        except QuestionPersistenceError:
            raise _internal_error() from None
        return _detail_response(question)

    return router
