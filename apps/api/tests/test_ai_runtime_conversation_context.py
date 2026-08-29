from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from group_interview_arena_api.modules.ai_runtime.conversation_context import (
    PersonaBehaviorError,
    PublicDiscussionUtterance,
    SupportBiasBand,
    UnsignedBehaviorBand,
    public_participant_label,
    render_persona_behavior,
    render_recent_discussion,
    select_recent_public_discussion,
    support_bias_band,
    unsigned_behavior_band,
)
from group_interview_arena_api.modules.ai_runtime.prompting import (
    AuthorizedPersonaContext,
)
from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus
from group_interview_arena_api.modules.floor_control.domain import (
    ParticipantActorKind,
)


def _utterance(
    sequence: int,
    content: str,
    *,
    actor_kind: ParticipantActorKind = ParticipantActorKind.AI,
    seat_order: int = 2,
    phase: SessionStatus = SessionStatus.EXPLORATION,
) -> PublicDiscussionUtterance:
    return PublicDiscussionUtterance(
        sequence=sequence,
        participant_id=uuid4(),
        actor_kind=actor_kind,
        seat_order=seat_order,
        phase=phase,
        content=content,
    )


def _persona(
    *,
    speech_style_code: str = "STRUCTURED",
    support_user_bias: Decimal = Decimal("0"),
) -> AuthorizedPersonaContext:
    return AuthorizedPersonaContext(
        assignment_id=uuid4(),
        persona_template_id=uuid4(),
        code="TEST_PERSONA",
        display_name="Private Persona Name",
        speech_style_code=speech_style_code,
        initiative=Decimal("0.331"),
        interrupt_tendency=Decimal("0.334"),
        average_turn_seconds=42,
        stance_stability=Decimal("0.666"),
        persuasion_threshold=Decimal("0.667"),
        novel_idea_rate=Decimal("0.669"),
        summary_tendency=Decimal("0.333"),
        time_awareness=Decimal("0.334"),
        detail_focus=Decimal("0.667"),
        cooperation=Decimal("0.666"),
        support_user_bias=support_user_bias,
        error_rate=Decimal("0.331"),
        off_topic_rate=Decimal("0.669"),
    )


def test_recent_public_discussion_selects_at_most_six_in_chronological_order() -> None:
    assert select_recent_public_discussion(()) == ()

    newest_first = tuple(
        _utterance(sequence, str(sequence)) for sequence in range(7, 0, -1)
    )

    selected = select_recent_public_discussion(newest_first)

    assert tuple(item.sequence for item in selected) == (2, 3, 4, 5, 6, 7)


def test_recent_public_discussion_accepts_exact_codepoint_budget() -> None:
    exact = _utterance(1, "你" * 3999 + "🙂")

    assert len(exact.content) == 4000
    assert select_recent_public_discussion((exact,)) == (exact,)


def test_recent_public_discussion_rejects_oversized_newest_without_truncation() -> None:
    oversized = _utterance(1, "🙂" * 4001)

    assert select_recent_public_discussion((oversized,)) == ()


def test_recent_public_discussion_stops_at_first_older_non_fitting_item() -> None:
    newest_first = (
        _utterance(4, "新新"),
        _utterance(3, "近近"),
        _utterance(2, "不应跨过"),
        _utterance(1, "旧"),
    )

    selected = select_recent_public_discussion(
        newest_first,
        max_content_codepoints=5,
    )

    assert tuple(item.sequence for item in selected) == (3, 4)
    assert tuple(item.content for item in selected) == ("近近", "新新")


@pytest.mark.parametrize(
    "invalid",
    [
        replace(_utterance(1, "内容"), actor_kind=ParticipantActorKind.SYSTEM),
        replace(_utterance(1, "内容"), phase=SessionStatus.PREPARATION),
        replace(_utterance(1, "内容"), content=None),  # type: ignore[arg-type]
    ],
)
def test_recent_public_discussion_rejects_invalid_public_items(
    invalid: PublicDiscussionUtterance,
) -> None:
    with pytest.raises(ValueError):
        select_recent_public_discussion((invalid,))


@pytest.mark.parametrize(
    ("max_utterances", "max_content_codepoints"),
    [(0, 4000), (6, 0), (-1, 4000), (6, -1)],
)
def test_recent_public_discussion_rejects_non_positive_budgets(
    max_utterances: int,
    max_content_codepoints: int,
) -> None:
    with pytest.raises(ValueError):
        select_recent_public_discussion(
            (),
            max_utterances=max_utterances,
            max_content_codepoints=max_content_codepoints,
        )


def test_public_participant_labels_are_exact_and_source_owned() -> None:
    human = _utterance(
        1,
        "Human contribution",
        actor_kind=ParticipantActorKind.HUMAN,
        seat_order=1,
    )
    ai_participants = tuple(
        _utterance(seat, "AI contribution", seat_order=seat) for seat in range(1, 4)
    )

    assert public_participant_label(human) == "你"
    assert tuple(public_participant_label(item) for item in ai_participants) == (
        "AI 候选人 1",
        "AI 候选人 2",
        "AI 候选人 3",
    )


def test_recent_discussion_rendering_preserves_exact_content_and_hides_identifiers() -> (
    None
):
    human = _utterance(
        1,
        "第一行\n第二行",
        actor_kind=ParticipantActorKind.HUMAN,
        seat_order=1,
    )
    ai = _utterance(2, "补充内容", seat_order=3)
    private_persona_sentinel = "PERSONA_DISPLAY_NAME_MUST_NOT_RENDER"

    rendered = render_recent_discussion((human, ai))

    assert rendered == "你：第一行\n第二行\nAI 候选人 3：补充内容"
    assert str(human.participant_id) not in rendered
    assert str(ai.participant_id) not in rendered
    assert private_persona_sentinel not in rendered
    assert "EXPLORATION" not in rendered
    assert "sequence" not in rendered


@pytest.mark.parametrize(
    "invalid",
    [
        replace(_utterance(1, "内容"), actor_kind=ParticipantActorKind.SYSTEM),
        replace(_utterance(1, "内容"), seat_order=0),
        replace(_utterance(1, "内容"), seat_order=-1),
    ],
)
def test_public_participant_label_rejects_invalid_actor_or_seat(
    invalid: PublicDiscussionUtterance,
) -> None:
    with pytest.raises(ValueError):
        public_participant_label(invalid)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", UnsignedBehaviorBand.LOW),
        ("0.331", UnsignedBehaviorBand.LOW),
        ("0.333", UnsignedBehaviorBand.LOW),
        ("0.334", UnsignedBehaviorBand.MEDIUM),
        ("0.666", UnsignedBehaviorBand.MEDIUM),
        ("0.667", UnsignedBehaviorBand.HIGH),
        ("0.669", UnsignedBehaviorBand.HIGH),
        ("1", UnsignedBehaviorBand.HIGH),
    ],
)
def test_unsigned_behavior_bands_are_exhaustive(
    value: str,
    expected: UnsignedBehaviorBand,
) -> None:
    assert unsigned_behavior_band(Decimal(value)) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("-1", SupportBiasBand.NEGATIVE),
        ("-0.334", SupportBiasBand.NEGATIVE),
        ("-0.333", SupportBiasBand.NEUTRAL),
        ("0", SupportBiasBand.NEUTRAL),
        ("0.333", SupportBiasBand.NEUTRAL),
        ("0.334", SupportBiasBand.POSITIVE),
        ("1", SupportBiasBand.POSITIVE),
    ],
)
def test_support_bias_bands_keep_signed_semantics(
    value: str,
    expected: SupportBiasBand,
) -> None:
    assert support_bias_band(Decimal(value)) is expected


@pytest.mark.parametrize(
    "value",
    [Decimal("-0.001"), Decimal("1.001"), Decimal("NaN"), Decimal("Infinity")],
)
def test_unsigned_behavior_band_rejects_illegal_persisted_values(
    value: Decimal,
) -> None:
    with pytest.raises(PersonaBehaviorError):
        unsigned_behavior_band(value)


@pytest.mark.parametrize(
    "value",
    [Decimal("-1.001"), Decimal("1.001"), Decimal("NaN"), Decimal("-Infinity")],
)
def test_support_bias_band_rejects_illegal_persisted_values(
    value: Decimal,
) -> None:
    with pytest.raises(PersonaBehaviorError):
        support_bias_band(value)


@pytest.mark.parametrize(
    ("speech_style", "expected"),
    [
        ("STRUCTURED", "说话有结构，但保持口语讨论，不写成报告。"),
        ("EXPLORATORY", "愿意补充新角度，每轮只推进少量有用内容。"),
        ("SUPPORTIVE", "会承接并整合他人观点，但不会无条件赞同。"),
        ("DIRECT", "直接且礼貌地表达判断，同时给同伴留出讨论空间。"),
    ],
)
def test_persona_behavior_uses_exact_speech_style_wording(
    speech_style: str,
    expected: str,
) -> None:
    assert (
        render_persona_behavior(_persona(speech_style_code=speech_style)).splitlines()[
            0
        ]
        == expected
    )


def test_persona_behavior_has_stable_private_guidance_order_without_raw_values() -> (
    None
):
    rendered = render_persona_behavior(_persona())
    lines = rendered.splitlines()

    assert len(lines) == 14
    assert tuple(line.split("：", 1)[0] for line in lines[1:]) == (
        "发言时长",
        "主动性",
        "打断倾向",
        "合作倾向",
        "对你的支持倾向",
        "细节关注",
        "总结倾向",
        "立场稳定性",
        "被说服门槛",
        "新观点倾向",
        "时间意识",
        "判断偏差",
        "跑题倾向",
    )
    assert lines[1] == "发言时长：通常发言约 42 秒。"
    for raw_value in ("0.331", "0.333", "0.334", "0.666", "0.667", "0.669"):
        assert raw_value not in rendered
    for enum_name in (
        "LOW",
        "MEDIUM",
        "HIGH",
        "NEGATIVE",
        "NEUTRAL",
        "POSITIVE",
    ):
        assert enum_name not in rendered
    assert "Private Persona Name" not in rendered
    assert str(_persona().assignment_id) not in rendered


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            Decimal("-0.334"),
            "对你的支持倾向：较少顺从“你”的观点，但保持建设性且不敌对",
        ),
        (
            Decimal("-0.333"),
            "对你的支持倾向：对“你”的观点保持平衡判断",
        ),
        (
            Decimal("0.334"),
            "对你的支持倾向：较愿意支持“你”的合理观点，但必须独立判断，禁止讨好或无条件赞同",
        ),
    ],
)
def test_persona_behavior_keeps_signed_support_meaning(
    value: Decimal,
    expected: str,
) -> None:
    rendered = render_persona_behavior(_persona(support_user_bias=value))

    assert expected in rendered
    assert "自动敌对" not in rendered
    assert "无条件支持" not in rendered


def test_persona_behavior_fails_closed_for_unknown_style_or_illegal_field() -> None:
    with pytest.raises(PersonaBehaviorError):
        render_persona_behavior(_persona(speech_style_code="UNKNOWN"))

    invalid = _persona().model_copy(update={"initiative": Decimal("1.001")})
    with pytest.raises(PersonaBehaviorError):
        render_persona_behavior(invalid)
