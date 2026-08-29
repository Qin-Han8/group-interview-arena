from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from group_interview_arena_api.modules.ai_runtime.prompting import (
    AuthorizedPersonaContext,
)
from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus
from group_interview_arena_api.modules.floor_control.domain import (
    FLOOR_ENABLED_PHASES,
    ParticipantActorKind,
)


@dataclass(frozen=True)
class PublicDiscussionUtterance:
    sequence: int
    participant_id: UUID
    actor_kind: ParticipantActorKind
    seat_order: int
    phase: SessionStatus
    content: str


class PersonaBehaviorError(ValueError):
    """Persisted Persona data cannot be translated safely."""


class UnsignedBehaviorBand(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SupportBiasBand(StrEnum):
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"


_LOW_MAX = Decimal("0.333")
_HIGH_MIN = Decimal("0.667")

_SPEECH_STYLE_GUIDANCE = {
    "STRUCTURED": "说话有结构，但保持口语讨论，不写成报告。",
    "EXPLORATORY": "愿意补充新角度，每轮只推进少量有用内容。",
    "SUPPORTIVE": "会承接并整合他人观点，但不会无条件赞同。",
    "DIRECT": "直接且礼貌地表达判断，同时给同伴留出讨论空间。",
}

_INITIATIVE_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "较少主动发言，但被需要时会清楚回应。",
    UnsignedBehaviorBand.MEDIUM: "会在合适时机主动表达判断。",
    UnsignedBehaviorBand.HIGH: "会积极争取发言并推进讨论。",
}
_INTERRUPT_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "通常等待他人说完再回应。",
    UnsignedBehaviorBand.MEDIUM: "必要时会礼貌插入讨论。",
    UnsignedBehaviorBand.HIGH: "较容易主动插话，但必须保持礼貌并给他人空间。",
}
_COOPERATION_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "更重视独立判断，合作时仍保持尊重。",
    UnsignedBehaviorBand.MEDIUM: "在独立判断与团队协作之间保持平衡。",
    UnsignedBehaviorBand.HIGH: "积极承接他人并推动合作，但不盲从。",
}
_DETAIL_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "更关注整体方向，不纠缠次要细节。",
    UnsignedBehaviorBand.MEDIUM: "在整体方向和关键细节之间保持平衡。",
    UnsignedBehaviorBand.HIGH: "会主动检查关键细节和潜在风险。",
}
_SUMMARY_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "较少主动总结，但会配合已有收敛。",
    UnsignedBehaviorBand.MEDIUM: "在需要时会归纳讨论。",
    UnsignedBehaviorBand.HIGH: "会主动提炼共识、分歧和下一步。",
}
_STANCE_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "立场可随新信息灵活调整。",
    UnsignedBehaviorBand.MEDIUM: "会在保持判断的同时吸收新信息。",
    UnsignedBehaviorBand.HIGH: "会稳定维护核心立场，但仍回应有效证据。",
}
_PERSUASION_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "有合理依据时容易调整判断。",
    UnsignedBehaviorBand.MEDIUM: "需要清楚理由才会调整判断。",
    UnsignedBehaviorBand.HIGH: "需要充分证据才会改变判断。",
}
_NOVEL_IDEA_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "较少引入新方案，更多围绕已有内容推进。",
    UnsignedBehaviorBand.MEDIUM: "会适度补充新的角度或方案。",
    UnsignedBehaviorBand.HIGH: "会积极提出新角度，但每轮仍只推进少量内容。",
}
_TIME_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "较少主动提醒时间。",
    UnsignedBehaviorBand.MEDIUM: "会留意时间并在必要时提醒。",
    UnsignedBehaviorBand.HIGH: "会主动结合剩余时间推动节奏。",
}
_ERROR_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "尽量保持判断准确。",
    UnsignedBehaviorBand.MEDIUM: "允许出现有限且可纠正的判断偏差。",
    UnsignedBehaviorBand.HIGH: "可能出现少量可纠正的判断偏差，但不得故意荒谬。",
}
_OFF_TOPIC_GUIDANCE = {
    UnsignedBehaviorBand.LOW: "紧扣讨论目标。",
    UnsignedBehaviorBand.MEDIUM: "偶尔扩展话题，但会及时回到目标。",
    UnsignedBehaviorBand.HIGH: "可能短暂发散，但必须可被拉回且不持续跑题。",
}
_SUPPORT_GUIDANCE = {
    SupportBiasBand.NEGATIVE: "较少顺从“你”的观点，但保持建设性且不敌对",
    SupportBiasBand.NEUTRAL: "对“你”的观点保持平衡判断",
    SupportBiasBand.POSITIVE: (
        "较愿意支持“你”的合理观点，但必须独立判断，禁止讨好或无条件赞同"
    ),
}


def _runtime_value(value: object) -> object:
    return value


def unsigned_behavior_band(value: object) -> UnsignedBehaviorBand:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < Decimal(0)
        or value > Decimal(1)
    ):
        raise PersonaBehaviorError("Unsigned Persona probability is invalid.")
    if value <= _LOW_MAX:
        return UnsignedBehaviorBand.LOW
    if value < _HIGH_MIN:
        return UnsignedBehaviorBand.MEDIUM
    return UnsignedBehaviorBand.HIGH


def support_bias_band(value: object) -> SupportBiasBand:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < Decimal(-1)
        or value > Decimal(1)
    ):
        raise PersonaBehaviorError("Signed Persona support bias is invalid.")
    if value < -_LOW_MAX:
        return SupportBiasBand.NEGATIVE
    if value <= _LOW_MAX:
        return SupportBiasBand.NEUTRAL
    return SupportBiasBand.POSITIVE


def render_persona_behavior(persona: AuthorizedPersonaContext) -> str:
    speech_guidance = _SPEECH_STYLE_GUIDANCE.get(persona.speech_style_code)
    if speech_guidance is None:
        raise PersonaBehaviorError("Persona speech style is invalid.")
    average_turn_seconds = _runtime_value(persona.average_turn_seconds)
    if (
        not isinstance(average_turn_seconds, int)
        or isinstance(average_turn_seconds, bool)
        or not 10 <= average_turn_seconds <= 90
    ):
        raise PersonaBehaviorError("Persona speaking duration is invalid.")

    lines = [
        speech_guidance,
        f"发言时长：通常发言约 {average_turn_seconds} 秒。",
        f"主动性：{_INITIATIVE_GUIDANCE[unsigned_behavior_band(persona.initiative)]}",
        (
            "打断倾向："
            f"{_INTERRUPT_GUIDANCE[unsigned_behavior_band(persona.interrupt_tendency)]}"
        ),
        f"合作倾向：{_COOPERATION_GUIDANCE[unsigned_behavior_band(persona.cooperation)]}",
        f"对你的支持倾向：{_SUPPORT_GUIDANCE[support_bias_band(persona.support_user_bias)]}",
        f"细节关注：{_DETAIL_GUIDANCE[unsigned_behavior_band(persona.detail_focus)]}",
        f"总结倾向：{_SUMMARY_GUIDANCE[unsigned_behavior_band(persona.summary_tendency)]}",
        f"立场稳定性：{_STANCE_GUIDANCE[unsigned_behavior_band(persona.stance_stability)]}",
        (
            "被说服门槛："
            f"{_PERSUASION_GUIDANCE[unsigned_behavior_band(persona.persuasion_threshold)]}"
        ),
        f"新观点倾向：{_NOVEL_IDEA_GUIDANCE[unsigned_behavior_band(persona.novel_idea_rate)]}",
        f"时间意识：{_TIME_GUIDANCE[unsigned_behavior_band(persona.time_awareness)]}",
        f"判断偏差：{_ERROR_GUIDANCE[unsigned_behavior_band(persona.error_rate)]}",
        f"跑题倾向：{_OFF_TOPIC_GUIDANCE[unsigned_behavior_band(persona.off_topic_rate)]}",
    ]
    return "\n".join(lines)


def _validate_public_discussion_items(
    items: Sequence[object],
) -> tuple[PublicDiscussionUtterance, ...]:
    previous_sequence: int | None = None
    validated: list[PublicDiscussionUtterance] = []
    for candidate in items:
        if not isinstance(candidate, PublicDiscussionUtterance):
            raise ValueError("Recent discussion item is invalid.")
        item = candidate
        sequence = _runtime_value(item.sequence)
        participant_id = _runtime_value(item.participant_id)
        content = _runtime_value(item.content)
        if (
            not isinstance(sequence, int)
            or isinstance(sequence, bool)
            or sequence <= 0
            or not isinstance(participant_id, UUID)
            or participant_id.version != 4
            or item.actor_kind
            not in {ParticipantActorKind.HUMAN, ParticipantActorKind.AI}
            or item.phase not in FLOOR_ENABLED_PHASES
            or not isinstance(content, str)
        ):
            raise ValueError("Recent discussion item is invalid.")
        if previous_sequence is not None and sequence >= previous_sequence:
            raise ValueError("Recent discussion must be ordered newest-first.")
        validated.append(item)
        previous_sequence = sequence
    return tuple(validated)


def select_recent_public_discussion(
    items: Sequence[object],
    *,
    max_utterances: object = 6,
    max_content_codepoints: object = 4000,
) -> tuple[PublicDiscussionUtterance, ...]:
    if (
        not isinstance(max_utterances, int)
        or isinstance(max_utterances, bool)
        or max_utterances <= 0
        or not isinstance(max_content_codepoints, int)
        or isinstance(max_content_codepoints, bool)
        or max_content_codepoints <= 0
    ):
        raise ValueError("Recent discussion budgets must be positive integers.")
    validated_items = _validate_public_discussion_items(items)

    newest_first: list[PublicDiscussionUtterance] = []
    content_codepoints = 0
    for item in validated_items:
        if len(newest_first) == max_utterances:
            break
        next_codepoints = content_codepoints + len(item.content)
        if next_codepoints > max_content_codepoints:
            break
        newest_first.append(item)
        content_codepoints = next_codepoints

    return tuple(reversed(newest_first))


def public_participant_label(item: object) -> str:
    seat_order = (
        _runtime_value(item.seat_order)
        if isinstance(item, PublicDiscussionUtterance)
        else None
    )
    if (
        not isinstance(item, PublicDiscussionUtterance)
        or item.actor_kind not in {ParticipantActorKind.HUMAN, ParticipantActorKind.AI}
        or not isinstance(seat_order, int)
        or isinstance(seat_order, bool)
        or seat_order <= 0
    ):
        raise ValueError("Public participant label is invalid.")
    if item.actor_kind is ParticipantActorKind.HUMAN:
        return "你"
    return f"AI 候选人 {seat_order}"


def render_recent_discussion(items: Sequence[object]) -> str:
    previous_sequence: int | None = None
    rendered: list[str] = []
    for candidate in items:
        if not isinstance(candidate, PublicDiscussionUtterance):
            raise ValueError("Recent discussion rendering input is invalid.")
        item = candidate
        content = _runtime_value(item.content)
        if (
            not isinstance(content, str)
            or item.phase not in FLOOR_ENABLED_PHASES
            or previous_sequence is not None
            and item.sequence <= previous_sequence
        ):
            raise ValueError("Recent discussion rendering input is invalid.")
        rendered.append(f"{public_participant_label(item)}：{content}")
        previous_sequence = item.sequence
    return "\n".join(rendered)
