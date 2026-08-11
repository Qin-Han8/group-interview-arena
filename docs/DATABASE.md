# 数据库设计骨架

- Status: Skeleton / Baseline
- Current phase: P0
- Target version: V0.1 Internal Validation
- Detailed design: Not started
- Schema and migrations: Not started
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件未来记录领域实体、关系、约束、索引、数据生命周期和迁移策略。当前只列出总纲中的未来领域实体，不构成完整表结构或 migration 设计。

## Confirmed by PROJECT_MASTER_PLAN

### Future domain entities from master plan

总纲提到的未来实体包括：

- 身份与同意：`users`、`user_profiles`、`consent_records`；
- 商品权益：`products`、`orders`、`entitlements`；
- 内容：`question_templates`、`question_versions`、`persona_templates`；
- 训练会话：`simulation_sessions`、`session_participants`、`session_phases`、`utterances`、`discussion_events`、`structured_memories`；
- 评分报告：`objective_metrics`、`evaluation_reports`、`evidence_items`；
- 训练成长：`skill_drills`、`drill_attempts`、`training_plans`；
- 反馈与治理：`user_feedback`、`model_invocations`、`moderation_events`、`audit_logs`。

这些名称表达总纲级领域概念，不表示表名、字段或拆分方式已冻结。

### 可追溯原则

- 会话需要关联题目版本、参与者、发言、事件和报告；
- 报告需要关联证据；
- 评分报告应与题目版本、模型版本和评分规则版本关联；
- 事件需要按 session sequence 编号；
- 服务端状态是断线恢复的权威来源。

### 数据生命周期原则

- 原始音频在报告生成后尽快删除，或仅在用户明确开启回放时限期保存；最终默认策略仍是 TBD；
- 转写文本可用于历史报告，但必须允许用户删除；
- 删除训练记录时，结构化指标同步删除或匿名化；
- 模型日志不得保留不必要的完整敏感输入；
- 匿名训练数据必须单独授权并去标识化。

## 当前版本范围

- 当前 P0-1：不创建数据库、模型、migration 或连接配置。
- P0-4：依据 P0-2 已批准的技术决策，建立 V0.1 所需的关系型数据库、数据访问层和 migration 基础，不一次性实现全部未来实体。
- V0.1 后续只应实现文字讨论闭环实际需要的最小数据范围。
- 支付、权益、语音、成长等 V0.5/V1.0 数据不能提前塞入 V0.1 业务模型。

## Implementation guidance

- `PROJECT_MASTER_PLAN.md` 当前推荐 PostgreSQL + SQLAlchemy 或等价方案，但在 P0-2 正式决策前不视为 `Accepted` 技术选型。
- 题目发布后不得直接覆盖；历史会话必须可追溯到原版本。
- 用户隔离、删除、审计和最小化保留应从最初的数据设计开始考虑。
- 正式字段、主键、外键、索引、枚举和删除策略必须在对应业务任务中验证。

## TBD

- TBD：数据库和 ORM 的最终技术选择；
- TBD：正式认证方案及用户主键边界；
- TBD：原始音频默认是否完全不保存（总纲第 37 节）；
- TBD：各类数据的精确保留期限；
- TBD：删除与匿名化的具体规则及审计边界；
- TBD：V0.1 最小实体集合；
- TBD：结构化记忆、证据和模型调用日志的正式 Schema；
- TBD：多租户或机构场景的未来隔离模型。

除特别注明的总纲问题外，其余是派生 TBD，不是新的 D-xxx。

## Future work

- P0-2：确认数据库和 ORM 技术方向。
- P0-4：依据 P0-2 批准的方案建立 V0.1 所需的关系型数据库、数据访问层、migration 工具和最小基础模型。
- P1：按文字讨论闭环增加最小题目、角色、会话、发言、记忆和报告数据。
- P2～P4：分别按获批任务扩展音频、评分训练和商业化数据。

## 与其他文档关系

- 数据安全和删除：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
- 题目领域：[`QUESTION_SYSTEM.md`](QUESTION_SYSTEM.md)
- 会话与角色：[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)
- 接口边界：[`API.md`](API.md)
- 技术选择：[`ARCHITECTURE.md`](ARCHITECTURE.md) 和 [`DECISIONS.md`](DECISIONS.md)
