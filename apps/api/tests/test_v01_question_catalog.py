from collections import Counter

from group_interview_arena_api.modules.question_personas.domain import (
    PublishedQuestionBundle,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    V01_PERSONA_TEMPLATES,
    V01_QUESTION_BUNDLES,
)


def _bundle(template_code: str) -> PublishedQuestionBundle:
    return next(
        item for item in V01_QUESTION_BUNDLES if item.template_code == template_code
    )


def test_v01_catalog_is_exact_closed_four_four_four_set() -> None:
    assert len(V01_QUESTION_BUNDLES) == 12
    assert V01_QUESTION_BUNDLES[0] is INTERNAL_VALIDATION_BUNDLE
    assert all(
        isinstance(item, PublishedQuestionBundle) for item in V01_QUESTION_BUNDLES
    )
    assert Counter(
        item.content.question_type_code for item in V01_QUESTION_BUNDLES
    ) == {
        "ORDERING_SELECTION": 4,
        "RESOURCE_ALLOCATION": 4,
        "PLAN_DESIGN": 4,
    }


def test_v01_catalog_has_stable_unique_identity_and_three_private_ai_stances() -> None:
    assert len(V01_PERSONA_TEMPLATES) == 4
    assert len({item.template_id for item in V01_QUESTION_BUNDLES}) == 12
    assert len({item.template_code for item in V01_QUESTION_BUNDLES}) == 12
    assert len({item.version_id for item in V01_QUESTION_BUNDLES}) == 12
    assignment_ids = [
        assignment.id
        for bundle in V01_QUESTION_BUNDLES
        for assignment in bundle.assignments
    ]
    assert len(assignment_ids) == len(set(assignment_ids)) == 36
    for bundle in V01_QUESTION_BUNDLES:
        assert [item.slot for item in bundle.assignments] == [1, 2, 3]
        assert len({item.persona_template_id for item in bundle.assignments}) == 3
        assert all(item.private_stance.initial_position for item in bundle.assignments)
        assert bundle.content.hidden_conflicts
        assert bundle.content.reference_dimensions
        assert bundle.content.acceptable_outcome_patterns


def test_reviewed_questions_expose_decision_grade_public_facts() -> None:
    museum = _bundle("V01_MUSEUM_RECOVERY_ORDER")
    assert [item.description for item in museum.content.options] == [
        "800页纸本文献已受潮；预计6小时后霉变风险显著上升，可由2人装箱转移。",
        "40件木质器物表面受潮；预计12小时后变形风险上升，可由2人转移。",
        "1200张醋酸纤维底片已沾水；4小时内可能粘连并加速化学降解，需冷藏转移。",
        "6件大型石刻所在区域有积水；结构评估为不稳定，只能原位遮护，24小时内风险较低。",
        "30件陶瓷状态稳定、包装干燥，但已承诺次日公开展出，可由1人转移。",
    ]

    rural = _bundle("V01_RURAL_CLINIC_ALLOCATION")
    for fact in (
        "河谷镇有480名到期慢病复诊者",
        "山岭镇有260名待筛查儿童",
        "湖滨镇覆盖12个偏远村",
    ):
        assert fact in rural.content.scenario

    heatwave = _bundle("V01_HEATWAVE_RESPONSE_BUDGET")
    assert [item.description for item in heatwave.content.options] == [
        "每投入15个单元可开放1个避暑点，每个点每日最多服务120人。",
        "每投入1个单元可完成5户独居老人当日探访。",
        "每投入10个单元可维持4处户外补给站运行一周。",
        "每投入5个单元可覆盖一轮全市多语种风险提示。",
    ]


def test_each_added_question_has_three_question_specific_private_stances() -> None:
    all_initial_positions: list[str] = []
    for bundle in V01_QUESTION_BUNDLES[1:]:
        stances = [item.private_stance for item in bundle.assignments]
        option_labels = tuple(item.label for item in bundle.content.options)
        assert len({item.initial_position for item in stances}) == 3
        assert all(
            any(label in stance.initial_position for label in option_labels)
            for stance in stances
        )
        assert len({item.priority_dimensions for item in stances}) == 3
        assert len({item.concession_conditions for item in stances}) == 3
        assert len({item.red_lines for item in stances}) == 3
        assert len({item.preferred_group_role for item in stances}) == 3
        all_initial_positions.extend(item.initial_position for item in stances)

    assert len(all_initial_positions) == len(set(all_initial_positions)) == 33
