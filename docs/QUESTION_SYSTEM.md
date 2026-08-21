# 题型与题目系统

- Status: P1-2 completed; design, persistence/domain/seed, safe caller, and independent acceptance complete
- Current phase: P1 — IN_PROGRESS
- Target version: V0.1 Internal Validation
- Current status: P1-2/P1-3/P1-4 DONE；P1-5A docs-only AI Runtime architecture freeze DONE；runtime implementation deferred
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件定义 P1-2 已确认的题目 identity、版本、结构化内容、发布/下线和历史追溯边界。具体 PostgreSQL columns、实施步骤和验收门见 [`exec-plans/P1-2_question-persona-foundation.md`](exec-plans/P1-2_question-persona-foundation.md)。本文件不代表完整 CMS、正式题库或 AI 出题已经实现。

## Confirmed by PROJECT_MASTER_PLAN

- 题型是内容架构第一层，行业背景只是题目属性。
- 先建立通用题型引擎，再扩展行业和岗位题包（D-012）。
- 公共题目采用人工审核加 AI 变体，不能由模型无约束即时生成（D-014）。
- 题目必须是结构化对象，而不是一段文本。
- 结构应能够承载题型、背景、难度、任务目标、硬/软约束、利益相关方、选项、参考维度、隐藏冲突、可接受结果模式、角色私有信息、阶段提示、评分覆盖和安全标签。
- 正式题目经历模板、AI 草案、自动逻辑检查、人工审核、小规模模拟、修正和发布流程。
- 已发布题目修改时产生新版本；历史会话必须保留原题版本关联。
- 自动检查至少覆盖目标清晰度、可讨论性、约束一致性、数据自洽、安全性、规定时间可完成性和角色分歧可能性。

## P1-2A frozen domain boundary

### Question Template

Question Template 只承载一道逻辑题目的稳定 UUID identity、稳定 internal code、创建时间和退休时间。它不承载 title、题型、难度、scenario、objective、options、constraints、人格分配或“当前内容”。

Template 是 versions 的容器，不是 session 的内容引用。首个版本发布后不得改名复用 template code；退休只阻止未来选择/版本生产，不修改或删除既有版本。

### Immutable Question Version

Question Version 由独立 UUID 和 template 内正整数 `version_number` 标识，并拥有完整内容、人格分配和私有立场快照。发布后：

- content、template link、version number、Persona Assignment 和 Private Stance 均不可覆盖修改；
- 任意内容修订必须插入同一 template 下的新 version；
- `retired_at` 只改变未来选题可用性，不改变历史内容；
- session 只绑定 immutable `question_version_id`，不绑定 template、`latest` alias 或 mutable current pointer；
- 新版本发布、旧版本下线或 template 退休均不重写历史 session。

Lifecycle 用 `published_at` / `retired_at` timestamps 表达，不使用 PostgreSQL native enum：draft、selectable published、retired historical。Draft 只有在未发布且未被引用时才可由未来获准的 CMS workflow 删除；published/referenced versions 采用 retirement/restrict 语义。

### Question type and difficulty evolution

Question type、difficulty、background domain 使用 bounded string code、语法校验和 application registry。数据库不使用 native enum，也不建立只允许当前值的封闭 check constraint。

V0.1 初始 question type codes：

- `ORDERING_SELECTION`；
- `RESOURCE_ALLOCATION`；
- `PLAN_DESIGN`。

初始 difficulty registry 至少包含 `STANDARD`；未来批准的 code 可以添加而不修改历史 rows 或执行 enum migration。代码新增仍需 domain/API/test 同步，不能接受任意用户字符串。

### Structured content — closed, not one arbitrary blob

P1-2B 不得用单一 `content` / `payload` JSONB 存整道题，也不得让 arbitrary dict 成为 domain/API 权威。Question Version 使用 scalar fields 加分别命名、独立 closed Schema 验证的结构字段：

- hard/soft constraints：ordered `ConstraintItem{key,text}`；
- stakeholders：ordered `StakeholderItem{key,name,description}`；
- options：ordered `QuestionOption{key,label,description}`；
- reference dimensions：ordered `ReferenceDimension{key,name,description}`；
- hidden conflicts / acceptable outcome patterns：ordered bounded internal text items；
- phase prompts：显式 frozen `PhasePromptSet`，只允许六个已支持 discussion phase fields；仅在 JSONB persistence adapter boundary 转换为 uppercase-key object；
- safety tags：unique bounded codes。

每个结构都有 count/length/key uniqueness/unknown-field validation；question-type-specific rules 在 domain publication boundary 验证。P1-2B 不创建 generic extension/metadata JSON escape hatch。

Reference dimensions、hidden conflicts、acceptable outcome patterns、phase prompts 和 safety tags 属于 internal calibration/orchestration data，不进入普通 browser question response。总纲中的 `agent_private_information` 在 P1-2 被正规化为 version-specific Persona Assignment / Private Stance，见 [`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)。Scoring overrides 保持 Deferred。

## P1-5A Prompt Version relationship

Question Version and Prompt Version are separate immutable assets:

- Question Version owns the exact question content、assignment/private-stance snapshot and question-level internal `phase_prompts` material；
- Prompt Version owns the future generation template/instruction asset used by AI Runtime；
- `phase_prompts` are inputs/material for future prompt assembly, not the complete rendered prompt and not a substitute for Prompt Version identity；
- publishing a new Question Version does not silently rewrite a Prompt Version, and prompt iteration does not mutate historical Question Versions；
- each future Generation Request must record both exact Question Version and exact Prompt Version, plus actual provider/model/effective non-secret configuration, so a historical utterance can be explained without following `latest` pointers；
- Persona Template must not absorb prompt content/provider secrets, and ordinary public question projection remains unchanged。

P1-5A adds no prompt schema、question column、migration、API or runtime。Exact Prompt Version storage/rendering is Deferred to a separately approved implementation subphase；see [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。

## Public and private projections

P1-2C 普通 authenticated browser caller 只可读取：

- immutable version/template identities and version number；
- title、question type、background domain、difficulty、estimated minutes；
- scenario、objective、hard/soft constraints、stakeholders、options。

普通 REST/OpenAPI/Browser/WebSocket/session snapshot/log/trace/error 不得包含：

- persona assignments、persona parameters 或 Private Stance；
- reference dimensions、hidden conflicts、acceptable outcome patterns；
- phase prompts、internal safety/calibration details；
- future prompt、provider 或 scoring rules。

Retired published public content 仍可按 immutable version ID 为历史 session 加载；它只是不再出现在可选题列表。Draft/missing version 不对普通 caller 暴露。

## V0.1 scope

- 3 种题型：排序选择、资源分配、方案策划；
- 每类建议 4 道，共 12 道人工审核题；12 道正式内容生产本轮 Deferred；
- P1-2B 可以建立一个明确标记的 `INTERNAL_VALIDATION` 人工 fixture，供 P1-2C 真实 vertical slice 使用；它不计入 12 道正式题；
- 管理端只需要的“最小题目配置”不等于本轮建设完整 CMS/RBAC/审批流；
- 质量优先于数量。

V0.5 扩展到排序选择、资源分配、方案策划和两难决策，共 20～30 道精品题。V1.0 的更多题型与数量以后续批准范围为准。

## Publication and history invariants

- 发布事务必须一次验证完整 content、registered codes、三个 V0.1 assignments、distinct personas 和每席完整 Private Stance；
- published payload 不提供普通 update path；修订以新 version 完成；
- session foreign key 对 question version 使用 restrict/no-action historical semantics；
- P1-1 legacy session rows可 nullable，P1-2C 后的新 session 必须绑定 selectable version；
- retirement 不 cascade 到 session/report；用户未来删除训练记录也不得删除共享题目源记录；
- 下线、回滚和 CMS 权限流细节继续 Deferred，但任何未来实现必须复用上述不变量。

## Current implementation status

- P1-2B 已新增五张 question/persona tables、nullable session version FK、revision `f1a12b15c002`、strict closed domain validation 和 insert-or-exact-match publication writer。
- deterministic seed 精确包含四种 V0.1 Persona Template 与一个明确标记的 internal-validation bundle；它不属于 12 道正式内容。
- P1-2C 已新增面向普通用户的 safe question projection，用于题目发现、读取及 version-bound session creation；普通 REST/OpenAPI/Browser/WS surface 仍不暴露 persona assignment、persona behavior parameters、Private Stance、internal calibration 或其他 server-only 内部数据。
- P1-2C 已增加 safe question read、version-bound session creation 和最小 Web caller；公开 DTO 使用显式 allowlist，历史 session 按 snapshot 中 exact version ID 解析 retired published content。

## TBD

- TBD：是否允许用户上传自定义题目（总纲第 37 节）；
- TBD：V0.1 的 12 道正式题目及审核责任人；
- TBD：完整题目审核、发布、回滚、RBAC 和操作审计流程；
- TBD：行业题包进入哪个具体版本；
- TBD：未来 item-level relational query/edit caller 是否要求进一步 normalize 结构字段；
- TBD：scoring overrides 的正式 Schema 和进入阶段。

除特别注明的总纲问题外，其余是派生 TBD，不是新的 D-xxx。

## Deferred / Future work

- P1-2B：completed；persistence/domain/seed foundation 已建立；
- P1-2C：completed；safe API/session/Web vertical slice 已建立并通过真实 Chromium/PostgreSQL 验证；
- P1-2D：completed；independent verdict `PASS`；
- P1-3A～D：completed；state/timing design、backend foundation、realtime/Web flow 和 independent acceptance 均未改变 question/persona schema；P1-3 verdict `PASS`，P1-3 `DONE`；
- P3：细化题型对评分权重和证据要求的影响；
- P5：通过公开测试补充精品题并验证质量指标；
- V1.0：按已批准范围扩展更多题型和 AI 变体能力。

## 与其他文档关系

- 产品范围：[`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md)
- 角色私有信息和阶段行为：[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)
- 正式数据边界：[`DATABASE.md`](DATABASE.md)
- safe browser API：[`API.md`](API.md)
- 评分覆盖：[`SCORING_RUBRIC.md`](SCORING_RUBRIC.md)
- 执行和验收：[`exec-plans/P1-2_question-persona-foundation.md`](exec-plans/P1-2_question-persona-foundation.md)
