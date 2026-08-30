import asyncio
from datetime import UTC, datetime
from string import Template
from uuid import UUID

import pytest

from group_interview_arena_api.modules.ai_runtime import seed as seed_module
from group_interview_arena_api.modules.ai_runtime.prompting import PROMPT_VARIABLES
from group_interview_arena_api.modules.ai_runtime.seed import (
    AI_CANDIDATE_TURN_V2,
    AI_CANDIDATE_TURN_V3,
    DISCUSSION_MEMORY_UPDATE_V1,
    DISCUSSION_MEMORY_UPDATE_V2,
    seed_ai_runtime_prompt_versions,
)


def test_candidate_v3_is_additive_and_memory_backed_without_mutating_v2() -> None:
    assert AI_CANDIDATE_TURN_V2.version_number == 2
    assert AI_CANDIDATE_TURN_V3.version_number == 3
    assert AI_CANDIDATE_TURN_V3.id == UUID("56000000-0000-4000-8000-000000000003")
    assert "$discussion_memory" in AI_CANDIDATE_TURN_V3.template_text
    assert "$recent_discussion" in AI_CANDIDATE_TURN_V3.template_text
    assert "$time_remaining_seconds" in AI_CANDIDATE_TURN_V3.template_text


def test_discussion_memory_prompt_has_separate_immutable_public_only_identity() -> None:
    definition = DISCUSSION_MEMORY_UPDATE_V1
    assert definition.id == UUID("56000000-0000-4000-8000-000000000101")
    assert definition.prompt_key == "DISCUSSION_MEMORY_UPDATE"
    assert definition.version_number == 1
    assert definition.purpose_code == "DISCUSSION_MEMORY_DERIVATION"
    assert "$memory_derivation_input" in definition.template_text
    assert "Private Stance" not in definition.template_text


def test_discussion_memory_v2_freezes_one_self_describing_closed_patch_contract() -> (
    None
):
    definition = DISCUSSION_MEMORY_UPDATE_V2
    template = definition.template_text
    assert definition.id == UUID("56000000-0000-4000-8000-000000000102")
    assert definition.prompt_key == "DISCUSSION_MEMORY_UPDATE"
    assert definition.version_number == 2
    assert definition.purpose_code == "DISCUSSION_MEMORY_DERIVATION"
    assert definition.created_at > DISCUSSION_MEMORY_UPDATE_V1.created_at
    assert "$memory_derivation_input" in template
    for required in (
        '{"patches":[]}',
        "operation",
        "kind",
        "target_memory_item_id",
        "canonical_text",
        "source_sequences",
        "ADD",
        "UPDATE",
        "SUPERSEDE",
        "DISCARD",
        "PROPOSAL",
        "EVALUATION_CRITERION",
        "AGREEMENT",
        "OPEN_CONFLICT",
        "DISCARDED_OPTION",
        "CURRENT_DECISION",
        "positive",
        "strictly increasing",
        "input utterances",
        "must not invent",
        "public",
    ):
        assert required in template
    assert "Private Stance" not in template


def test_ai_candidate_turn_v2_has_exact_immutable_identity_and_vocabulary() -> None:
    definition = AI_CANDIDATE_TURN_V2

    assert definition.id == UUID("56000000-0000-4000-8000-000000000002")
    assert definition.prompt_key == "AI_CANDIDATE_TURN"
    assert definition.version_number == 2
    assert definition.purpose_code == "CANDIDATE_UTTERANCE"
    assert definition.created_at == datetime(2026, 8, 27, 16, 0, tzinfo=UTC)
    assert definition.published_at == datetime(2026, 8, 27, 16, 0, tzinfo=UTC)
    assert definition.retired_at is None
    assert frozenset(Template(definition.template_text).get_identifiers()) == (
        PROMPT_VARIABLES
    )
    assert len(PROMPT_VARIABLES) == 10


def test_ai_candidate_turn_v2_freezes_conversational_candidate_behavior() -> None:
    template = AI_CANDIDATE_TURN_V2.template_text

    for required in (
        "群面候选人",
        "不是报告撰写者",
        "不是主持人",
        "不是答案生成器",
        "一到两个有用要点",
        "口语化中文",
        "不要使用 Markdown 标题",
        "总结如下",
        "第一第二第三",
        "当前状态分析",
        "不要复述完整题目",
        "不要每轮独立完成整个任务",
        "赞同、质疑、补充、提问、妥协或承接",
        "把讨论空间交还给同伴",
        "recent_discussion",
        "persona_behavior",
        "phase_instruction",
        "Private Stance",
    ):
        assert required in template


def test_ai_candidate_turn_v2_contains_one_closed_five_phase_mapping() -> None:
    template = AI_CANDIDATE_TURN_V2.template_text

    expected_phase_guidance = {
        "OPENING_STATEMENTS": "清楚表达初始立场；上下文稀少时可以不回应他人",
        "EXPLORATION": "补充角度，并承接前面的公开发言",
        "CONFLICT_AND_EVALUATION": "比较方案、质疑假设、检验依据，并建设性地表达不同意见",
        "CONVERGENCE": "识别取舍、寻求妥协，并推动形成共同方案",
        "FINAL_SUMMARY": "简洁归纳当前共识与仍然存在的分歧",
    }
    for phase, guidance in expected_phase_guidance.items():
        assert template.count(phase) == 1
        assert guidance in template


@pytest.mark.parametrize("inserted", [True, False])
def test_ai_runtime_prompt_seed_returns_exact_publication_result(
    monkeypatch: pytest.MonkeyPatch,
    inserted: bool,
) -> None:
    session = object()
    published: list[tuple[object, object]] = []

    class _SessionContext:
        async def __aenter__(self) -> object:
            return session

        async def __aexit__(self, *_args: object) -> None:
            return None

    def session_factory() -> _SessionContext:
        return _SessionContext()

    async def publish(candidate_session: object, definition: object) -> bool:
        published.append((candidate_session, definition))
        return inserted

    monkeypatch.setattr(seed_module, "publish_prompt_version", publish)

    result = asyncio.run(
        seed_ai_runtime_prompt_versions(session_factory)  # type: ignore[arg-type]
    )

    assert result is inserted
    assert published == [
        (session, AI_CANDIDATE_TURN_V2),
        (session, AI_CANDIDATE_TURN_V3),
        (session, DISCUSSION_MEMORY_UPDATE_V1),
        (session, DISCUSSION_MEMORY_UPDATE_V2),
    ]
