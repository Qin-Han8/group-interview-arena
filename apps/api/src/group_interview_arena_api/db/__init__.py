"""Database infrastructure primitives and registered product metadata."""

from group_interview_arena_api.db.base import Base
from group_interview_arena_api.db.models import (
    AuthSession,
    DiscussionEvent,
    FloorDecision,
    FloorGrant,
    FloorIntervention,
    FloorRelease,
    PersonaPrivateStance,
    PersonaTemplate,
    QuestionPersonaAssignment,
    QuestionTemplate,
    QuestionVersion,
    SessionAction,
    SessionParticipant,
    SimulationSession,
    SpeakingOpportunity,
    User,
)

__all__ = [
    "AuthSession",
    "Base",
    "DiscussionEvent",
    "FloorDecision",
    "FloorGrant",
    "FloorIntervention",
    "FloorRelease",
    "PersonaPrivateStance",
    "PersonaTemplate",
    "QuestionPersonaAssignment",
    "QuestionTemplate",
    "QuestionVersion",
    "SessionAction",
    "SessionParticipant",
    "SimulationSession",
    "SpeakingOpportunity",
    "User",
]
