import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db import (
    AiUtterance,
    FloorGrant,
    LlmGenerationRequest,
    PromptVersion,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.ai_runtime.domain import (
    AiRuntimePersistenceError,
    FailGenerationCommand,
    GenerationContextError,
    GenerationFailureCode,
    GenerationRequestConflictError,
    GenerationRequestMetadata,
    GenerationRequestSnapshot,
    GenerationRequestStatus,
    GenerationStartClaim,
    GenerationStateError,
    PersistUtteranceCommand,
    PromptVersionDefinition,
    PromptVersionMutationError,
    RequestGenerationCommand,
    StartGenerationCommand,
)
from group_interview_arena_api.modules.discussion_sessions.domain import ACTIVE_PHASES
from group_interview_arena_api.modules.discussion_sessions.service import (
    reconcile_due_for_locked_aggregate,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _sha256_text(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def _request_digest(command: RequestGenerationCommand) -> bytes:
    payload = {
        "floor_grant_id": str(command.floor_grant_id),
        "model_identifier": command.model_identifier,
        "participant_id": str(command.participant_id),
        "prompt_version_id": str(command.prompt_version_id),
        "provider_identifier": command.provider_identifier,
        "request_metadata": command.request_metadata.model_dump(mode="json"),
        "requested_at": command.requested_at.isoformat(),
        "session_id": str(command.session_id),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).digest()


def _prompt_matches(
    stored: PromptVersion,
    definition: PromptVersionDefinition,
    digest: bytes,
) -> bool:
    return all(
        (
            stored.id == definition.id,
            stored.prompt_key == definition.prompt_key,
            stored.version_number == definition.version_number,
            stored.purpose_code == definition.purpose_code,
            stored.template_text == definition.template_text,
            stored.content_digest == digest,
            stored.created_at == definition.created_at,
            stored.published_at == definition.published_at,
            stored.retired_at == definition.retired_at,
        )
    )


async def publish_prompt_version(
    session: AsyncSession,
    definition: PromptVersionDefinition,
) -> bool:
    """Insert an immutable published prompt or verify an exact replay."""
    digest = _sha256_text(definition.template_text)
    try:
        async with session.begin():
            by_id = await session.get(PromptVersion, definition.id)
            by_version = await session.scalar(
                select(PromptVersion).where(
                    PromptVersion.prompt_key == definition.prompt_key,
                    PromptVersion.version_number == definition.version_number,
                )
            )
            existing = by_id or by_version
            if existing is not None:
                if _prompt_matches(existing, definition, digest):
                    return False
                raise PromptVersionMutationError(
                    "Published prompt identity cannot be overwritten."
                )
            session.add(
                PromptVersion(
                    id=definition.id,
                    prompt_key=definition.prompt_key,
                    version_number=definition.version_number,
                    purpose_code=definition.purpose_code,
                    template_text=definition.template_text,
                    content_digest=digest,
                    created_at=definition.created_at,
                    published_at=definition.published_at,
                    retired_at=definition.retired_at,
                )
            )
            await session.flush()
        return True
    except SQLAlchemyError as error:
        raise AiRuntimePersistenceError("Prompt version transaction failed.") from error


async def _lock_owned_session(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
) -> SimulationSession:
    aggregate = await session.scalar(
        select(SimulationSession)
        .where(
            SimulationSession.id == session_id,
            SimulationSession.owner_user_id == owner_id,
        )
        .with_for_update()
    )
    if aggregate is None:
        raise GenerationContextError("Generation context is unavailable.")
    return aggregate


async def _validate_live_generation_context(
    session: AsyncSession,
    *,
    aggregate: SimulationSession,
    participant_id: UUID,
    floor_grant_id: UUID,
) -> None:
    if (
        aggregate.status not in {item.value for item in ACTIVE_PHASES}
        or aggregate.current_floor_grant_id != floor_grant_id
    ):
        raise GenerationContextError("The floor grant is no longer active.")

    participant = await session.scalar(
        select(SessionParticipant).where(
            SessionParticipant.session_id == aggregate.id,
            SessionParticipant.id == participant_id,
        )
    )
    grant = await session.scalar(
        select(FloorGrant).where(
            FloorGrant.session_id == aggregate.id,
            FloorGrant.id == floor_grant_id,
        )
    )
    if (
        participant is None
        or participant.actor_kind != "AI"
        or participant.participation_role != "CANDIDATE"
        or participant.availability != "AVAILABLE"
        or participant.question_persona_assignment_id is None
        or grant is None
        or grant.participant_id != participant_id
        or grant.phase != aggregate.status
    ):
        raise GenerationContextError("Generation context is ineligible.")


async def _reconcile_due_before_generation_mutation(
    session: AsyncSession,
    aggregate: SimulationSession,
) -> bool:
    event_rows = await reconcile_due_for_locked_aggregate(
        session,
        aggregate,
        now=_utc_now(),
    )
    if not event_rows:
        return False
    session.add_all(event_rows)
    await session.flush()
    return True


def _to_snapshot(
    request: LlmGenerationRequest,
    *,
    utterance_id: UUID | None = None,
) -> GenerationRequestSnapshot:
    metadata = GenerationRequestMetadata.model_validate(request.request_metadata)
    return GenerationRequestSnapshot(
        request_id=request.id,
        session_id=request.session_id,
        participant_id=request.participant_id,
        floor_grant_id=request.floor_grant_id,
        prompt_version_id=request.prompt_version_id,
        provider_identifier=request.provider_identifier,
        model_identifier=request.model_identifier,
        request_metadata=metadata,
        status=GenerationRequestStatus(request.status),
        requested_at=request.requested_at,
        started_at=request.started_at,
        completed_at=request.completed_at,
        failed_at=request.failed_at,
        failure_code=(
            None
            if request.failure_code is None
            else GenerationFailureCode(request.failure_code)
        ),
        utterance_id=utterance_id,
    )


async def _locked_request(
    session: AsyncSession,
    *,
    session_id: UUID,
    request_id: UUID,
) -> LlmGenerationRequest:
    request = await session.scalar(
        select(LlmGenerationRequest)
        .where(
            LlmGenerationRequest.session_id == session_id,
            LlmGenerationRequest.id == request_id,
        )
        .with_for_update()
    )
    if request is None:
        raise GenerationContextError("Generation request is unavailable.")
    return request


async def create_generation_request(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: RequestGenerationCommand,
) -> GenerationRequestSnapshot:
    digest = _request_digest(command)
    pending_context_error: GenerationContextError | None = None
    snapshot: GenerationRequestSnapshot | None = None
    try:
        async with session.begin():
            aggregate = await _lock_owned_session(
                session, owner_id=owner_id, session_id=command.session_id
            )
            existing = await session.get(LlmGenerationRequest, command.request_id)
            if existing is not None:
                if existing.request_digest != digest:
                    raise GenerationRequestConflictError(
                        "Generation request identity conflicts with its original payload."
                    )
                utterance_id = None
                if existing.status == GenerationRequestStatus.COMPLETED.value:
                    utterance_id = await session.scalar(
                        select(AiUtterance.id).where(
                            AiUtterance.generation_request_id == existing.id
                        )
                    )
                return _to_snapshot(existing, utterance_id=utterance_id)

            if await _reconcile_due_before_generation_mutation(session, aggregate):
                pending_context_error = GenerationContextError(
                    "The floor grant is no longer active."
                )
            else:
                await _validate_live_generation_context(
                    session,
                    aggregate=aggregate,
                    participant_id=command.participant_id,
                    floor_grant_id=command.floor_grant_id,
                )
                prompt = await session.get(PromptVersion, command.prompt_version_id)
                if (
                    prompt is None
                    or prompt.published_at > command.requested_at
                    or (
                        prompt.retired_at is not None
                        and prompt.retired_at <= command.requested_at
                    )
                ):
                    raise GenerationContextError("Prompt version is unavailable.")

                request = LlmGenerationRequest(
                    id=command.request_id,
                    session_id=command.session_id,
                    participant_id=command.participant_id,
                    floor_grant_id=command.floor_grant_id,
                    prompt_version_id=command.prompt_version_id,
                    provider_identifier=command.provider_identifier,
                    model_identifier=command.model_identifier,
                    request_metadata=command.request_metadata.model_dump(mode="json"),
                    request_digest=digest,
                    status=GenerationRequestStatus.REQUESTED.value,
                    requested_at=command.requested_at,
                    started_at=None,
                    completed_at=None,
                    failed_at=None,
                    failure_code=None,
                )
                session.add(request)
                await session.flush()
                snapshot = _to_snapshot(request)
    except (SQLAlchemyError, ValueError) as error:
        raise AiRuntimePersistenceError(
            "Generation request transaction failed."
        ) from error
    if pending_context_error is not None:
        raise pending_context_error
    assert snapshot is not None
    return snapshot


async def claim_generation_request(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: StartGenerationCommand,
) -> GenerationStartClaim:
    pending_context_error: GenerationContextError | None = None
    claim: GenerationStartClaim | None = None
    try:
        async with session.begin():
            aggregate = await _lock_owned_session(
                session, owner_id=owner_id, session_id=command.session_id
            )
            request = await _locked_request(
                session,
                session_id=command.session_id,
                request_id=command.generation_request_id,
            )
            if request.status != GenerationRequestStatus.REQUESTED.value:
                return GenerationStartClaim(
                    snapshot=_to_snapshot(
                        request,
                        utterance_id=(
                            await session.scalar(
                                select(AiUtterance.id).where(
                                    AiUtterance.generation_request_id == request.id
                                )
                            )
                            if request.status == GenerationRequestStatus.COMPLETED.value
                            else None
                        ),
                    ),
                    claimed=False,
                )
            if command.started_at < request.requested_at:
                raise GenerationStateError("Generation cannot start before request.")
            if await _reconcile_due_before_generation_mutation(session, aggregate):
                pending_context_error = GenerationContextError(
                    "The floor grant is no longer active."
                )
            else:
                await _validate_live_generation_context(
                    session,
                    aggregate=aggregate,
                    participant_id=request.participant_id,
                    floor_grant_id=request.floor_grant_id,
                )
                request.status = GenerationRequestStatus.RUNNING.value
                request.started_at = command.started_at
                await session.flush()
                claim = GenerationStartClaim(
                    snapshot=_to_snapshot(request),
                    claimed=True,
                )
    except (SQLAlchemyError, ValueError) as error:
        raise AiRuntimePersistenceError(
            "Generation start transaction failed."
        ) from error
    if pending_context_error is not None:
        raise pending_context_error
    assert claim is not None
    return claim


async def start_generation_request(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: StartGenerationCommand,
) -> GenerationRequestSnapshot:
    claim = await claim_generation_request(
        session,
        owner_id=owner_id,
        command=command,
    )
    if (
        not claim.claimed
        and claim.snapshot.status is not GenerationRequestStatus.RUNNING
    ):
        raise GenerationStateError("Only a requested generation can start.")
    return claim.snapshot


async def complete_generation_request(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: PersistUtteranceCommand,
) -> GenerationRequestSnapshot:
    content_digest = _sha256_text(command.content)
    pending_context_error: GenerationContextError | None = None
    snapshot: GenerationRequestSnapshot | None = None
    try:
        async with session.begin():
            aggregate = await _lock_owned_session(
                session, owner_id=owner_id, session_id=command.session_id
            )
            request = await _locked_request(
                session,
                session_id=command.session_id,
                request_id=command.generation_request_id,
            )
            if request.status == GenerationRequestStatus.COMPLETED.value:
                utterance = await session.scalar(
                    select(AiUtterance).where(
                        AiUtterance.generation_request_id == request.id
                    )
                )
                if (
                    utterance is not None
                    and utterance.id == command.utterance_id
                    and utterance.content == command.content
                    and utterance.content_digest == content_digest
                    and utterance.persisted_at == command.persisted_at
                ):
                    return _to_snapshot(request, utterance_id=utterance.id)
                raise GenerationRequestConflictError(
                    "Completed generation identity conflicts with its utterance."
                )
            if request.status != GenerationRequestStatus.RUNNING.value:
                raise GenerationStateError("Only a running generation can complete.")
            if request.started_at is None or command.persisted_at < request.started_at:
                raise GenerationStateError("Utterance cannot precede generation start.")
            if await _reconcile_due_before_generation_mutation(session, aggregate):
                pending_context_error = GenerationContextError(
                    "The floor grant is no longer active."
                )
            else:
                await _validate_live_generation_context(
                    session,
                    aggregate=aggregate,
                    participant_id=request.participant_id,
                    floor_grant_id=request.floor_grant_id,
                )

                request.status = GenerationRequestStatus.COMPLETED.value
                request.completed_at = command.persisted_at
                utterance = AiUtterance(
                    id=command.utterance_id,
                    session_id=request.session_id,
                    participant_id=request.participant_id,
                    floor_grant_id=request.floor_grant_id,
                    generation_request_id=request.id,
                    generation_request_status=GenerationRequestStatus.COMPLETED.value,
                    content=command.content,
                    content_digest=content_digest,
                    persisted_at=command.persisted_at,
                )
                session.add(utterance)
                await session.flush()
                snapshot = _to_snapshot(request, utterance_id=utterance.id)
    except (SQLAlchemyError, ValueError) as error:
        raise AiRuntimePersistenceError(
            "Generation completion transaction failed."
        ) from error
    if pending_context_error is not None:
        raise pending_context_error
    assert snapshot is not None
    return snapshot


async def fail_generation_request(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: FailGenerationCommand,
) -> GenerationRequestSnapshot:
    try:
        async with session.begin():
            await _lock_owned_session(
                session, owner_id=owner_id, session_id=command.session_id
            )
            request = await _locked_request(
                session,
                session_id=command.session_id,
                request_id=command.generation_request_id,
            )
            if request.status == GenerationRequestStatus.FAILED.value:
                if (
                    request.failure_code == command.failure_code.value
                    and request.failed_at == command.failed_at
                ):
                    return _to_snapshot(request)
                raise GenerationRequestConflictError(
                    "Failed generation identity conflicts with its terminal record."
                )
            if request.status not in {
                GenerationRequestStatus.REQUESTED.value,
                GenerationRequestStatus.RUNNING.value,
            }:
                raise GenerationStateError(
                    "Only a requested or running generation can fail."
                )
            if command.failed_at < request.requested_at:
                raise GenerationStateError("Failure cannot precede request.")
            request.status = GenerationRequestStatus.FAILED.value
            request.completed_at = None
            request.failed_at = command.failed_at
            request.failure_code = command.failure_code.value
            await session.flush()
            return _to_snapshot(request)
    except SQLAlchemyError as error:
        raise AiRuntimePersistenceError(
            "Generation failure transaction failed."
        ) from error
