# 评分与证据体系骨架

- Status: Baseline + P1-7A basic evidence report design freeze
- Current phase: P1 — IN_PROGRESS
- Target version: V0.1 Internal Validation
- Detailed design: P1-7A V0.1 basic evidence report boundary frozen; formal scoring remains P3
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录正式评分的总纲基线，并承载 P1-7A 简版证据报告边界；它不构成冻结的正式评分公式。

## Confirmed by PROJECT_MASTER_PLAN

### 核心原则

- 评分对象是可观察行为，不是人格。
- 评分必须结合讨论阶段。
- 评分不能只依赖大模型整体印象。
- 客观统计、规则判断、语义评价和完整度修正需要分层。
- 每项重要评价必须尽量附带时间戳、原话、上下文、解释和置信度。
- 证据不足时明确标记，不强行生成精确分数。
- 不完整会话必须降低置信度。
- 评分只用于训练，不提供录用概率或岗位适配结论。

### 六个核心维度

1. 问题分析：目标、评价标准、硬约束、材料使用、事实与假设区分；
2. 观点贡献：新观点、理由证据、可执行方案、重复程度和结果影响；
3. 表达沟通：结构、简洁性、语速停顿、口头禅和上下文回应；
4. 团队协作：倾听承接、尊重差异、邀请参与、避免垄断和降低无效冲突；
5. 推动与组织：阶段总结、目标时间提醒、比较投票、共识和收敛；
6. 应变与抗压：回应质疑、被打断后恢复、新信息调整、时间压力和不合理行为处理。

### 分层建议

总纲给出的初始建议权重是：

| 层 | 初始建议权重 |
|---|---:|
| 客观行为统计 | 30% |
| 规则特征评价 | 25% |
| 语义证据评价 | 35% |
| 会话完整度和置信度修正 | 10% |

**这些是初始建议权重，后续必须通过人工标注和试运行校准，不是永久冻结规则。**

发言次数、时长、打断次数等客观指标不能机械等价为能力。

### 证据格式基线

证据至少需要表达：维度、正/负影响、起止时间、原话、当时上下文、解释和置信度。正式字段名称和 Schema 尚未冻结。

### 防虚假精确

- 不显示小数分；
- 证据不足时不强行评分；
- 明示 AI 评估误差；
- 允许用户标记不认可；
- 争议评价可进入人工校准样本；
- 样本和标准化不足时不输出全国排名式结论。

## P1-7A V0.1 basic evidence report freeze

- P1-7 report is a durable, versioned resource derived only after an authoritative `COMPLETED` text session. Raw public utterance/DiscussionEvent history remains evidence authority; P1-6 Memory is auxiliary context only.
- The basic report shows session overview, zero-to-three evidence-backed strongest behaviors, zero-to-three evidence-backed improvement opportunities, exactly one next-session priority and evidence cards with source participant/phase/utterance/event sequence/exact quote/interpretation/confidence.
- Semantic evaluation proposes behavior, interpretation, priority and confidence. Project-owned deterministic code validates eligibility, source watermark/order, session/participant/utterance/phase, exact quote provenance, Human-source identity, completeness, versions and idempotent re-entry. Invalid evidence is rejected rather than repaired.
- P1 `EvidenceItem` needs only `STRENGTH`/`IMPROVEMENT` kind and source provenance. Dimension, score, score effect, metric and rubric aggregation remain P3-additive concerns.
- P1-7 outputs no six-dimension/overall score, radar, percentile/ranking, hiring probability, job fit or personality type. The master-plan TBD on score versus level + evidence remains unresolved.
- Text V0.1 evidence uses event/utterance identity and sequence; it must not fabricate audio timestamps.

## 当前版本范围

- V0.1：只需要简版证据报告，用于验证证据链路，不要求完成正式六维聚合体系。
- V0.5：必须具备六维评分、时间戳证据和历史报告。
- P1-7A freezes the basic report/evidence boundary; P1-7B/P1-7C/P1-7D are `DONE / ACTUAL_SOURCE_REVIEW_PASS`; P1-7D REST/Web continues to expose no P3 score/rank.

## Implementation guidance

- 先定义可观察事件及其阶段语义，再讨论聚合分数。
- 评分规则、模型版本、题目版本和报告必须可追溯关联。
- 人工校准应包含至少两名有经验评审的独立评分和分歧记录。
- 不因口音、性别或声线产生不合理差异。
- 报告首页优先展示优势、问题和下一步训练，而不是制造排名焦虑。

## TBD

- TBD：报告展示数字分数还是等级加证据（总纲第 37 节）；
- TBD：人工群面教练校准支持来源（总纲第 37 节）；
- TBD：建议权重经过何种样本和指标校准；
- Frozen and implemented for P1-7 V0.1：report/evidence responsibilities, item caps, exactly one priority improvement and the closed P1-7D public read fields；formal scores remain P3；
- TBD：用户争议评价的复核和申诉流程；
- TBD：不同题型的权重调整方式。

除前两项注明来自总纲外，其余未解决项是派生 TBD，不是总纲原始 D-xxx；P1-7 已冻结的概念责任不是新的 Accepted scoring decision。

## Future work

- P1：P1-7A is frozen/reviewed；P1-7B/P1-7C/P1-7D are `DONE / ACTUAL_SOURCE_REVIEW_PASS`；P1-7D implements the report REST/Web surface without formal scores；P1-7E remains `NOT_STARTED`.
- P3：完成客观指标、证据提取、六维评分、报告和专项训练设计。
- P5：通过专家标注和公开测试校准可信度与用户认可率。

## 与其他文档关系

- 产品报告体验：[`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md)
- 阶段和角色行为：[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)
- 未来数据实体：[`DATABASE.md`](DATABASE.md)
- 隐私与公平边界：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
