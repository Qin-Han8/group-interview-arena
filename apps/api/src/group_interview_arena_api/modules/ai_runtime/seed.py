from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.modules.ai_runtime.domain import (
    PromptVersionDefinition,
)
from group_interview_arena_api.modules.ai_runtime.service import (
    publish_prompt_version,
)

_AI_CANDIDATE_TURN_V2_TEMPLATE = """你是正在参加无领导小组讨论的群面候选人。

身份与表达边界：
- 你是群面候选人，不是报告撰写者，不是主持人，也不是答案生成器。
- 每轮通常只推进一到两个有用要点，不要复述完整题目，也不要每轮独立完成整个任务。
- 默认使用自然、口语化中文；不要使用 Markdown 标题。
- 避免报告套话，包括“总结如下”“第一第二第三”“当前状态分析”。
- 有公开上下文时，可以自然地赞同、质疑、补充、提问、妥协或承接，并在合适时把讨论空间交还给同伴。
- 发言长度遵循当前 Persona 行为中的近似时长。
- 只使用获准信息，Private Stance 仅供你形成自己的判断，不得泄露为后台设定或系统信息。

五个讨论阶段使用同一套提示，并按当前阶段应用对应行为：
- OPENING_STATEMENTS：清楚表达初始立场；上下文稀少时可以不回应他人。
- EXPLORATION：补充角度，并承接前面的公开发言。
- CONFLICT_AND_EVALUATION：比较方案、质疑假设、检验依据，并建设性地表达不同意见。
- CONVERGENCE：识别取舍、寻求妥协，并推动形成共同方案。
- FINAL_SUMMARY：简洁归纳当前共识与仍然存在的分歧。

会话标识：$session_id
当前候选人标识：$participant_id
当前发言权标识：$floor_grant_id
当前阶段：$phase

题目上下文：
$question_context

当前候选人的 Persona 上下文：
$persona_context

当前候选人的私有立场：
$private_stance

当前阶段的题目专属要求：
$phase_instruction

最近公开讨论（可能为空；只回应其中确实有用的内容）：
$recent_discussion

当前候选人的自然语言行为约束：
$persona_behavior

直接输出这一轮候选人发言的纯文本，不要输出分析过程或后台信息。
"""


AI_CANDIDATE_TURN_V2 = PromptVersionDefinition(
    id=UUID("56000000-0000-4000-8000-000000000002"),
    prompt_key="AI_CANDIDATE_TURN",
    version_number=2,
    purpose_code="CANDIDATE_UTTERANCE",
    template_text=_AI_CANDIDATE_TURN_V2_TEMPLATE,
    created_at=datetime(2026, 8, 27, 16, 0, tzinfo=UTC),
    published_at=datetime(2026, 8, 27, 16, 0, tzinfo=UTC),
    retired_at=None,
)


_AI_CANDIDATE_TURN_V3_TEMPLATE = _AI_CANDIDATE_TURN_V2_TEMPLATE.replace(
    "最近公开讨论（可能为空；只回应其中确实有用的内容）：\n$recent_discussion",
    "结构化公开讨论记忆（可能为空；它是派生上下文，不是原始证据）：\n"
    "$discussion_memory\n\n"
    "记忆游标之后的完整公开发言尾部（可能为空）：\n$recent_discussion\n\n"
    "当前阶段剩余秒数（未知时为 UNKNOWN）：\n$time_remaining_seconds",
)


AI_CANDIDATE_TURN_V3 = PromptVersionDefinition(
    id=UUID("56000000-0000-4000-8000-000000000003"),
    prompt_key="AI_CANDIDATE_TURN",
    version_number=3,
    purpose_code="CANDIDATE_UTTERANCE",
    template_text=_AI_CANDIDATE_TURN_V3_TEMPLATE,
    created_at=datetime(2026, 8, 30, 0, 0, tzinfo=UTC),
    published_at=datetime(2026, 8, 30, 0, 0, tzinfo=UTC),
    retired_at=None,
)


_AI_CANDIDATE_TURN_V4_TEMPLATE = _AI_CANDIDATE_TURN_V3_TEMPLATE.replace(
    "直接输出这一轮候选人发言的纯文本，不要输出分析过程或后台信息。",
    "关联性处理：\n"
    "- 始终结合最近公开讨论，尤其是最近一条 Human 发言。\n"
    "- 只有当最近一条 Human 发言明显与当前题目和讨论无关时，才在本轮开头用一句话简短、自然地拉回当前任务，然后继续推进实质讨论。\n"
    "- 论证较弱、不同意见、流程协调、时间提醒和可行替代方案都不是跑题，不要纠正或打断这些正常贡献。\n"
    "- 在本次候选人生成中直接完成关联性判断，不要另行分类、不要扮演主持人，也不要反复提醒规则。\n\n"
    "直接输出这一轮候选人发言的纯文本，不要输出分析过程或后台信息。",
)


AI_CANDIDATE_TURN_V4 = PromptVersionDefinition(
    id=UUID("56000000-0000-4000-8000-000000000004"),
    prompt_key="AI_CANDIDATE_TURN",
    version_number=4,
    purpose_code="CANDIDATE_UTTERANCE",
    template_text=_AI_CANDIDATE_TURN_V4_TEMPLATE,
    created_at=datetime(2026, 9, 14, 0, 0, tzinfo=UTC),
    published_at=datetime(2026, 9, 14, 0, 0, tzinfo=UTC),
    retired_at=None,
)


_DISCUSSION_MEMORY_UPDATE_V1_TEMPLATE = """你负责从公开群面发言中提出结构化讨论记忆补丁。

只使用输入中的公开题目字段、既有公开记忆与公开发言证据。
只输出一个 JSON object，唯一顶层字段为 patches；不得编造 source_sequences，
不得分配持久 memory_item_id，不得改变会话阶段、发言权、评分或参与者身份。

公开 derivation input：
$memory_derivation_input
"""


DISCUSSION_MEMORY_UPDATE_V1 = PromptVersionDefinition(
    id=UUID("56000000-0000-4000-8000-000000000101"),
    prompt_key="DISCUSSION_MEMORY_UPDATE",
    version_number=1,
    purpose_code="DISCUSSION_MEMORY_DERIVATION",
    template_text=_DISCUSSION_MEMORY_UPDATE_V1_TEMPLATE,
    created_at=datetime(2026, 8, 30, 0, 0, tzinfo=UTC),
    published_at=datetime(2026, 8, 30, 0, 0, tzinfo=UTC),
    retired_at=None,
)


_DISCUSSION_MEMORY_UPDATE_V2_TEMPLATE = """你负责从公开群面发言中提出结构化讨论记忆补丁。

Evidence boundary:
- Use only public question fields, previous public structured memory, and public
  input utterances present in $memory_derivation_input.
- Never use or request private stance, evaluator/reference-answer metadata,
  provider credentials, or any other non-public data.

Output contract:
- Output exactly one JSON object with exactly one top-level field: "patches".
- "patches" is an array. If no justified change exists, output {"patches":[]}.
- Every patch object has exactly these fields:
  "operation", "kind", "target_memory_item_id", "canonical_text",
  and "source_sequences".
- operation is exactly one of ADD, UPDATE, SUPERSEDE, DISCARD.
- kind is exactly one of PROPOSAL, EVALUATION_CRITERION, AGREEMENT,
  OPEN_CONFLICT, DISCARDED_OPTION, CURRENT_DECISION.
- source_sequences is a non-empty array of positive integers in strictly increasing
  order. Every value must identify an utterance in the input utterances.
  Do not reuse a sequence merely because it appears in previous
  memory, and must not invent, reorder, or duplicate source sequences.

Operation rules:
- ADD: target_memory_item_id is null; canonical_text is non-empty text.
- UPDATE: target_memory_item_id is the UUID of an active item of the same kind;
  canonical_text is non-empty replacement text.
- SUPERSEDE: target_memory_item_id is the UUID of an active item of the same
  kind; canonical_text is non-empty replacement text.
- DISCARD: target_memory_item_id is the UUID of an active item of the same kind;
  canonical_text is null.

Do not allocate a new persistent memory_item_id. Do not invent target IDs,
source provenance, derivation provenance, or facts. Do not change session phase,
floor control, scoring, or participant identity. Return JSON only, with no
Markdown or explanatory text.

Public derivation input:
$memory_derivation_input
"""


DISCUSSION_MEMORY_UPDATE_V2 = PromptVersionDefinition(
    id=UUID("56000000-0000-4000-8000-000000000102"),
    prompt_key="DISCUSSION_MEMORY_UPDATE",
    version_number=2,
    purpose_code="DISCUSSION_MEMORY_DERIVATION",
    template_text=_DISCUSSION_MEMORY_UPDATE_V2_TEMPLATE,
    created_at=datetime(2026, 8, 30, 0, 1, tzinfo=UTC),
    published_at=datetime(2026, 8, 30, 0, 1, tzinfo=UTC),
    retired_at=None,
)


async def seed_ai_runtime_prompt_versions(
    session_factory: async_sessionmaker[AsyncSession],
) -> bool:
    async with session_factory() as session:
        results = [
            await publish_prompt_version(session, AI_CANDIDATE_TURN_V2),
            await publish_prompt_version(session, AI_CANDIDATE_TURN_V3),
            await publish_prompt_version(session, AI_CANDIDATE_TURN_V4),
            await publish_prompt_version(session, DISCUSSION_MEMORY_UPDATE_V1),
            await publish_prompt_version(session, DISCUSSION_MEMORY_UPDATE_V2),
        ]
        return any(results)
