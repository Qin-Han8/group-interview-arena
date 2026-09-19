# 产品与技术决策记录

- Status: Active governance baseline
- Current phase: P1 — DONE / CLOSED; P2 — NOT_STARTED
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md)，高于领域文档和代码实现
- Last accepted decision established by task: P1-5E-1 automatic orchestration amendment to ADR-014 — approved

## 1. 文档规则

本文件采用轻量 ADR（Architecture/Decision Record）方式管理正式决策。

只有以下内容可以成为正式 decision：

1. `PROJECT_MASTER_PLAN V1.0` 已明确确认的产品决策；
2. 用户明确批准并要求记录的产品或技术决策。

状态定义：

- `Accepted`：已经确认，可直接约束后续工作；
- `Proposed`：建议方案，尚未批准；
- `TBD`：问题已知，但尚无决策；
- `Superseded`：已被后续正式决策替代，必须保留追溯关系；
- `Rejected`：经过评审后明确不采用。

禁止把总纲中的“推荐”“建议”“可选”或“等价方案”提升为 `Accepted`。实现代码也不能自动形成产品决策。

正式决策建议使用以下格式：

```markdown
### D-xxx / ADR-xxx — Title

- ID:
- Title:
- Date:
- Status: Proposed | Accepted | Rejected | Superseded
- Type: Product | Architecture | Data | Security | Operations
- Source:
- Context:
- Decision:
- Rationale:
- Consequences:
- Alternatives:
- Related documents:
```

产品决策沿用 `D-xxx`；新增技术决策使用 `ADR-xxx`。不得为了填号而创建没有真实决策的记录。

## 2. 已确认产品决策索引

以下条目是总纲 D-001～D-015 的摘要索引，不是对总纲的改写。完整语义以 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 第 0 节为准。

| ID | Status | 决策摘要 | 对研发的直接影响 | Source |
|---|---|---|---|---|
| D-001 | Accepted | 第一阶段做通用型群面训练 | 基础架构不得绑定单一行业或岗位 | PROJECT_MASTER_PLAN V1.0 |
| D-002 | Accepted | 首要用户是校招与初入职场求职者 | 首期内容和流程围绕校招无领导小组讨论 | PROJECT_MASTER_PLAN V1.0 |
| D-003 | Accepted | 核心是动态模拟，不是题库或答案生成 | 必须形成多角色真实互动闭环 | PROJECT_MASTER_PLAN V1.0 |
| D-004 | Accepted | 完整模拟以桌面 Web 为主 | 首期不开发原生 App；移动端承担轻量场景 | PROJECT_MASTER_PLAN V1.0 |
| D-005 | Accepted | 公开 MVP 必须支持语音 | V0.1 可文字验证，V0.5 不能仅有文字聊天 | PROJECT_MASTER_PLAN V1.0 |
| D-006 | Accepted | 首期不做摄像头、表情和微表情识别 | 不建立视频及相关伪科学评分链路 | PROJECT_MASTER_PLAN V1.0 |
| D-007 | Accepted | 首期每场使用 3 名 AI 候选人 | 控制角色数量、延迟、成本和认知负荷 | PROJECT_MASTER_PLAN V1.0 |
| D-008 | Accepted | 采用半实时、受控轮次制 | 发言权由讨论引擎调度，不追求同时抢话 | PROJECT_MASTER_PLAN V1.0 |
| D-009 | Accepted | 评分必须有证据 | 重要评价关联时间戳、原话、阶段和置信度 | PROJECT_MASTER_PLAN V1.0 |
| D-010 | Accepted | 评分只用于训练 | 不输出录取概率、岗位适配或招聘结论 | PROJECT_MASTER_PLAN V1.0 |
| D-011 | Accepted | 第一阶段不做正式面试实时提词 | 不开发隐蔽辅助或作弊功能 | PROJECT_MASTER_PLAN V1.0 |
| D-012 | Accepted | 先建立通用题型引擎 | 行业和岗位题包属于后续增值层 | PROJECT_MASTER_PLAN V1.0 |
| D-013 | Accepted | 角色行为差异优先于数字人表现 | 先验证立场、策略和行为，不优先做视觉拟真 | PROJECT_MASTER_PLAN V1.0 |
| D-014 | Accepted | 公共题目采用人工审核加 AI 变体 | 不允许模型无约束即时生成全部正式题目 | PROJECT_MASTER_PLAN V1.0 |
| D-015 | Accepted | 商业模式以场次包和冲刺包为主 | 不以长期月度订阅作为首要收入方式 | PROJECT_MASTER_PLAN V1.0 |

## 3. 已确认技术决策

以下技术决策由用户在 P0-2 明确批准，均处于总纲授权范围内。它们约束后续实现，但不改变 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 的产品方向。

### ADR-001 — 采用简单 Monorepo

- ID: `ADR-001`
- Title: 采用简单 Monorepo
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准的 P0-2 技术架构决策
- Context: 项目近期只有一个 Web 应用和一个 API 应用，需要共同演进文档、契约和实现。
- Decision: 使用简单 monorepo，规划 `apps/web` 与 `apps/api`；当前不采用 multi-repo、Nx 或 Turborepo。
- Rationale: 普通 workspace scripts 足以维护当前规模，能以最低工具成本提供原子变更和统一审查。
- Consequences: P0-3 只创建实际需要的应用目录；出现多个独立 JS package/application、CI 依赖明显复杂或普通 scripts 无法维护时重新评估。
- Alternatives: multi-repo；Nx；Turborepo。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`TASKS.md`](TASKS.md)

### ADR-002 — Next.js 前端基线

- ID: `ADR-002`
- Title: Next.js 前端基线
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准的 P0-2 技术架构决策；PROJECT_MASTER_PLAN V1.0 §21
- Context: V0.1 需要桌面 Web，后续公开产品需要稳定的路由和 Web 能力。
- Decision: 前端采用 Next.js App Router、React、TypeScript strict 和 Tailwind CSS。FastAPI 是业务权威；Next.js Server Actions/Route Handlers 只能处理 Web 专属能力，不得复制领域逻辑、会话状态机、评分、Agent 编排或持久化权威。
- Rationale: 与总纲推荐方向一致，并保留公开 Web 产品的演进空间。
- Consequences: UI primitives/component library 保持 Deferred；不在 P0-2 选择 shadcn、Radix、React Aria 或大型 UI suite。
- Alternatives: Vite SPA；当前冻结完整组件库。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`API.md`](API.md)

### ADR-003 — FastAPI 作为主要业务后端

- ID: `ADR-003`
- Title: FastAPI 作为主要业务后端
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准的 P0-2 技术架构决策；PROJECT_MASTER_PLAN V1.0 §21
- Context: AI、讨论编排、结构化输出和评分将主要使用 Python 生态。
- Decision: 后端采用 FastAPI、Pydantic v2，并在合适的 I/O 边界使用 Python async I/O。API schema、ORM model 和领域对象不得永久绑定；纯领域规则不因框架异步而被强制写成 async。
- Rationale: 提供明确的 Schema 校验、OpenAPI 和实时通信基础，同时让领域逻辑保持可测试。
- Consequences: Pydantic v1 不进入新项目；前后端契约按 ADR-007 治理。
- Alternatives: Node/Next.js 业务后端；Django；Pydantic v1。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`API.md`](API.md)

### ADR-004 — 运行时与包管理工具链

- ID: `ADR-004`
- Title: 运行时与包管理工具链
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准并经外部审核修订的 P0-2 技术架构决策
- Context: Windows 本地开发和未来 CI 需要可复现且单一的 JavaScript/Python 工具链。
- Decision: JavaScript 使用 Node.js 24 LTS 和 pnpm；Python 使用 CPython 3.14 和 uv。ADR 冻结 Node 24 LTS major policy，不锁 patch；P0-3 选择当时最新兼容的 24.x。`packageManager` 记录实际 pnpm 精确版本并提交唯一的 `pnpm-lock.yaml`；`.python-version` 使用 3.14，`pyproject.toml` 声明 Python 3.14 policy，并提交 `uv.lock`。
- Rationale: 新项目采用受支持的 LTS/runtime 和可复现锁文件，不以当前机器的 Node 26 Current 反向决定项目基线。
- Consequences: 只有项目必需依赖明确不兼容 Python 3.14 时，才能提出降至 3.13 的 Proposed ADR；不得自行降版或同时维护多套 lockfile。
- Alternatives: Node 26 Current；npm；Yarn；pip+venv；Poetry；CPython 3.13。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`TASKS.md`](TASKS.md)

### ADR-005 — PostgreSQL、SQLAlchemy 与 Alembic 数据基线

- ID: `ADR-005`
- Title: PostgreSQL、SQLAlchemy 与 Alembic 数据基线
- Date: 2026-08-11
- Status: Accepted
- Type: Data
- Source: 用户批准的 P0-2 技术架构决策；PROJECT_MASTER_PLAN V1.0 §21、§24
- Context: 会话、事件、版本和证据需要关系型事务、可追溯 migration 和明确模型边界。
- Decision: 从 P0-4 首次建立数据层时直接使用 PostgreSQL、SQLAlchemy 2.x 和 Alembic，并分离 ORM model、Pydantic API schema 与领域对象。架构只冻结 PostgreSQL；P0-4 实施基线为 PostgreSQL 18.x，镜像不得使用 `postgres:latest`。
- Rationale: 避免 SQLite 过渡路径造成类型、并发和 migration 差异。
- Consequences: P0-4 使用真实 PostgreSQL integration/migration tests；数据库 major 升级需要独立评估。
- Alternatives: SQLite 临时正式开发路径；MySQL；SQLModel 作为 API/ORM 永久统一模型。
- Related documents: [`DATABASE.md`](DATABASE.md)、[`ARCHITECTURE.md`](ARCHITECTURE.md)

### ADR-006 — REST 与 WebSocket 通信边界

- ID: `ADR-006`
- Title: REST 与 WebSocket 通信边界
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准的 P0-2 技术架构决策；PROJECT_MASTER_PLAN V1.0 §25
- Context: 资源访问与活动群面会话具有不同通信特征。
- Decision: REST 负责资源 CRUD、题目获取、会话创建和快照/加载、报告、设置及未来管理/订单能力；WebSocket 负责活动会话命令、状态变化、参与者事件、计时、发言权、打断、AI 流式文字及未来语音会话事件。SSE 不作为活动 session 主协议。
- Rationale: 活动讨论需要双向、有序且可恢复的通道。
- Consequences: P1 的第一个文字讨论 vertical slice 建立 WebSocket session channel；服务端状态权威，client command 有 action identity，事件有顺序，重连使用 snapshot + sequence。
- Alternatives: REST-only 完整讨论后再重写；SSE 作为主通道。
- Related documents: [`API.md`](API.md)、[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)

### ADR-007 — API 契约生成策略

- ID: `ADR-007`
- Title: API 契约生成策略
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准的 P0-2 技术架构决策
- Context: FastAPI 与 TypeScript 前端之间需要避免手写重复 DTO 和契约漂移。
- Decision: FastAPI OpenAPI 是 REST contract 的 Source of Truth，前端由其生成 TypeScript types/client。WebSocket 使用独立、版本化事件契约，至少表达 event type、schema version、session identity、ordering sequence、occurrence timestamp 和 client action identity；服务端错误与 REST error semantics 对齐。
- Rationale: 单一权威契约便于验证和演进。
- Consequences: OpenAPI generator package 与 WebSocket schema generator package 保持 Deferred；完整 P1 WebSocket event schema 不在 P0-2 冻结。
- Alternatives: 前后端手写两套同名 DTO；把 WebSocket 强行纳入 REST OpenAPI。
- Related documents: [`API.md`](API.md)、[`ARCHITECTURE.md`](ARCHITECTURE.md)

#### P0-3E 后续实施决议 — 2026-08-13

ADR-007 在 P0-2 建立时将具体 OpenAPI generator package 保持 Deferred；上述记录保留为当时的真实历史状态。P0-3E 已在不改变本 ADR 契约权威原则的前提下解决 REST OpenAPI tooling 选择：

- 当前 P0-3E / V0.1 实现基线使用 `openapi-typescript 7.13.0`，从 FastAPI `/openapi.json` 生成 TypeScript contract；
- 使用 `openapi-fetch 0.17.0` 消费生成的 `paths`，建立类型安全的 Fetch client；
- 生成物 `apps/web/src/lib/api/generated/schema.d.ts` 是由 generator 生成、纳入版本控制的派生 contract artifact，不是新的 Source of Truth，也不得作为手工维护的 REST DTO；
- contract drift check 用于验证生成物与 FastAPI OpenAPI 保持一致。

该后续决议只解决 REST OpenAPI tooling。WebSocket schema format、WebSocket schema generator 与 realtime protocol tooling 仍 Deferred 到 P1。上述工具及版本是当前 P0-3E / V0.1 实现基线，不是永久不可替换的架构锁定；未来替换必须继续保证 FastAPI OpenAPI 是 REST contract 的 Source of Truth，且 generated client/types 不形成独立权威。

### ADR-008 — Redis 延后运行

- ID: `ADR-008`
- Title: Redis 延后运行
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准并经外部审核修订的 P0-2 技术架构决策
- Context: Redis 可能用于未来跨进程广播、锁和限流，但 V0.1 初期没有该运行需求。
- Decision: 采用 Deferred runtime strategy。V0.1 初期不运行 Redis，不将 Redis 放入 P0-4 默认 Compose，领域业务不得直接依赖 Redis SDK。只在架构文档记录替换边界。
- Rationale: 避免没有实际需求的运行和维护成本。
- Consequences: 多 API workers、横向扩容、跨进程 WebSocket broadcast、distributed lock、centralized rate limiting 或 durable task queue 出现时重新评估。**不为了 deferred technology 创建无实际调用方的空 abstraction、adapter、factory 或目录。**
- Alternatives: 从 P0-4 起默认运行 Redis；完全忽略未来跨进程边界。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`TASKS.md`](TASKS.md)

### ADR-009 — 独立后台任务队列延后

- ID: `ADR-009`
- Title: 独立后台任务队列延后
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准并经外部审核修订的 P0-2 技术架构决策
- Context: 当前没有需要可靠异步执行的已实现任务或已验证负载。
- Decision: 当前不引入 Celery、RQ、Dramatiq、distributed worker 或其他独立 task queue；能够合理完成的任务同步执行。
- Rationale: 在需求出现前避免任务基础设施、重试和运维复杂度。
- Consequences: 出现 reliable retry、delayed jobs、scheduling、independent workers 或 cross-process execution 时重新评估。**不为了 deferred technology 创建无实际调用方的 JobRunner、Queue abstraction、worker 空目录或其他空 abstraction。**
- Alternatives: P0-3 即引入独立队列；先创建无实现的任务抽象。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`TASKS.md`](TASKS.md)

### ADR-010 — 本地应用原生运行、基础服务使用 Docker Compose

- ID: `ADR-010`
- Title: 本地应用原生运行、基础服务使用 Docker Compose
- Date: 2026-08-11
- Status: Accepted
- Type: Operations
- Source: 用户批准的 P0-2 技术架构决策
- Context: Windows 开发需要兼顾热更新体验与有状态服务一致性。
- Decision: Next.js 通过 Node/pnpm 原生运行，FastAPI 通过 uv/Python 原生运行；基础服务使用 Docker Compose。P0-3 不需要数据库容器；P0-4 才加入 PostgreSQL 18.x、SQLAlchemy、Alembic 和数据库 integration tests。Redis 不运行。
- Rationale: 避免全容器开发摩擦，同时标准化有状态基础服务。
- Consequences: Windows PowerShell 是正式支持环境，不要求 WSL；P0-3 只建立 Web/API skeleton、toolchain、health、连接、配置、日志和基础测试。
- Alternatives: 全栈容器化；全部服务原生安装；强制 WSL。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`TASKS.md`](TASKS.md)

### ADR-011 — 轻量领域导向混合模块架构

- ID: `ADR-011`
- Title: 轻量领域导向混合模块架构
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准的 P0-2 技术架构决策
- Context: 项目需要保护讨论编排等领域逻辑，但当前不适合完整 DDD 或微服务化。
- Decision: 后端规划 `api/`、`core/`、`db/`、`modules/`、`providers/`；`api` 是 transport adapter，`core` 是横切基础设施，`db` 是 persistence infrastructure，`modules` 按真实业务领域组织，`providers` 只容纳已经存在的外部 adapter。前端使用 feature-based 结构：`app`、`features`、共享 `components`、`lib/api`，并只在实时功能出现时建立 `lib/realtime`。
- Rationale: 以最少层次保持业务边界和可测试性。
- Consequences: 不采用 full DDD ceremony、repository/service/controller 空壳、global giant services.py，也不提前创建未来 module 或 feature 目录。
- Alternatives: 全局技术分层；完整 DDD；提前生成长期 roadmap 的所有目录。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)

### ADR-012 — 分阶段测试与质量工具策略

- ID: `ADR-012`
- Title: 分阶段测试与质量工具策略
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准的 P0-2 技术架构决策
- Context: 前后端、数据库、实时会话和模型行为需要不同层级的验证，但工具应按实际阶段安装。
- Decision: 后端采用 pytest、按需 pytest-asyncio、Ruff lint/format、Pyright；前端采用 Vitest、Testing Library、ESLint、`tsc`、Prettier；有真实跨应用用户流时采用 Playwright。P0-3 建立 backend unit/API tests、frontend unit/component smoke tests 及 lint/type/build；P0-4 使用真实 PostgreSQL integration/migration tests；P1 增加 WebSocket、deterministic simulation/orchestrator regression 和 fake provider tests。真实 LLM tests 不进入默认 CI。
- Rationale: 分层验证核心行为，同时避免在 P0-3 一次安装所有未来工具。
- Consequences: 不同时启用 mypy + Pyright，也不引入重复 formatter/linter；各阶段只安装当前验收需要的工具。
- Alternatives: 只做 E2E；只做单元测试；P0-3 安装全部未来测试栈。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)

### ADR-013 — 配置、错误与结构化日志基线

- ID: `ADR-013`
- Title: 配置、错误与结构化日志基线
- Date: 2026-08-11
- Status: Accepted
- Type: Security
- Source: 用户批准的 P0-2 技术架构决策
- Context: 应用从骨架开始就需要安全配置、可关联诊断和一致错误语义。
- Decision: 使用类型化、启动时校验的配置；服务端密钥不得进入前端或日志。应用从 P0-3 使用 structured logging 和 `request_id`，在相关功能出现后再增加 `session_id`、`connection_id`、provider invocation id、`job_id`。REST 使用标准 HTTP status、稳定 machine-readable code、安全 message、request correlation 和可选安全 details；WebSocket error event 与其语义一致。
- Rationale: 在不提前引入完整追踪平台的前提下建立安全、稳定的诊断契约。
- Consequences: 不生成虚假的未来 correlation 字段；stack trace、SQL、filesystem path、secret、prompt 和 provider credential 不得暴露。OpenTelemetry 延后到 P0-6，Sentry/SaaS exporter 保持 Deferred。
- Alternatives: 非结构化日志；P0-3 即引入完整 OTel/SaaS；使用框架默认错误格式作为长期契约。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`API.md`](API.md)、[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)

### ADR-014 — Provider-neutral AI 与自定义讨论编排

- ID: `ADR-014`
- Title: Provider-neutral AI 与自定义讨论编排
- Date: 2026-08-11
- Status: Accepted
- Type: Architecture
- Source: 用户批准并经外部审核修订的 P0-2 技术架构决策；PROJECT_MASTER_PLAN V1.0 §22
- Amendments:
  - 2026-08-24 用户批准 P1-5D config-driven model selection specialization；
  - 2026-08-24 用户批准 P1-5E application-level、state-driven automatic AI runtime orchestration boundary。
- Context: Production/default 供应商政策仍未决定；current development provider is Zhipu。核心讨论状态必须由项目代码掌控。
- Decision: 业务领域不得直接绑定厂商 SDK；概念边界包括 LLM Provider、ASR Provider、TTS Provider 和可选 Embedding Provider，SDK object 不得穿透 domain layer，structured output 必须 Schema validate。LLM provider、actual model identity and versioned non-secret invocation configuration are distinct provenance dimensions；model selection is server-side configuration rather than adapter-owned identity。P1-5D uses lazy environment configuration plus API restart；a later DB/admin-managed source may replace that configuration source without changing the provider-neutral runtime contract。V0.1 不使用 LangGraph，核心 discussion orchestrator 使用自定义、确定性、可测试状态机。P1-5E automatic orchestration is an application-level coordinator over existing P1-3 lifecycle、P1-4 Floor Control/Floor Scheduler and P1-5 AI Runtime authorities；it is state-driven from durable current session/grant/request/utterance/action truth rather than dependent on exactly-once event-listener delivery。One exact AI floor grant maps to deterministic generation、utterance、release and next-schedule identities；provider I/O remains outside transactions，committed release precedes committed scheduling，and the orchestrator never chooses the next participant or directly writes floor/lifecycle facts。
- Rationale: 降低厂商锁定并保持核心状态和行为可验证。
- Consequences: LLMProvider 在 P1 首次真实 LLM 调用时建立，ASRProvider/TTSProvider 在 P2 首次接入时建立，Embedding 仅在实际需要时建立。P1-5D 不实现 model table、admin API/UI、hot reload、registry、routing or fallback；changing its configured model requires configuration change and API restart but no Python/provider/schema change。P1-5E uses the existing schema and `SessionAction` replay/conflict plus aggregate-lock/current-grant/sequence guards；no orchestration table、Redis、queue、distributed lock or in-memory correctness authority is introduced。Confirmed `FAILED` releases the exact current AI grant through Floor Control as `INTERRUPTED` while preserving typed generation failure；uncertain or `RUNNING` truth stops automatic progression。Continuous drive is bounded to 8 AI turns per invocation and stops at human、no-grant、intervention、lifecycle、reconciliation or budget boundaries。**不为了 deferred technology 创建无实际调用方的空 interface、adapter、factory 或目录。** 局部离线报告或复杂 retry workflow 达到明显复杂度后，可单独重新评估 LangGraph。
- Alternatives: 领域代码直接依赖厂商 SDK；P0-3 创建所有 Provider 空接口；让 LangGraph 控制完整群面状态机。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)

### ADR-015 — Initial identity and browser session boundary

- ID: `ADR-015`
- Title: Initial identity and browser session boundary
- Date: 2026-08-14
- Status: Accepted
- Type: Security
- Source: 用户批准的 P0-5A 身份边界、安全边界与决策收尾
- Context: P0/V0.1 需要第一个可验证的稳定用户身份和第一方浏览器认证边界，同时当前没有 mobile client、third-party API 或 distributed service trust boundary 等必须采用 JWT 的需求。未来 phone、WeChat 等身份方式尚未进入当前实现范围，V0.1 也没有可验证的 self-service recovery identity。
- Decision:
  1. P0/V0.1 的首个认证机制采用 `username + password`；email、phone、SMS、WeChat、OAuth/social login、MFA 与 password recovery 不进入当前身份实现。
  2. UUIDv4 `user_id` 是稳定内部身份。`username` 是当前登录标识，未来 display name、phone、WeChat 等都不得成为核心用户主键。
  3. Password 使用 Argon2id。安全参数由 application 显式配置和拥有，并在目标环境 benchmark；不得仅依赖第三方库未来可能变化的默认值形成永久参数承诺。
  4. 第一方浏览器使用 PostgreSQL-backed opaque server-side session；当前架构不采用 JWT。
  5. Cryptographically random raw session token 只存在于浏览器 HttpOnly Cookie；数据库只持久化用于 lookup 的 cryptographic digest，不保存 raw token。
  6. `auth_sessions` 属于 FastAPI/PostgreSQL identity boundary，由服务端验证并解析为 authenticated current user。
  7. Browser security boundary 由 host-only Cookie、credentialed explicit CORS、exact Origin validation、required custom CSRF header 与 SameSite defense-in-depth 共同组成；不得把 SameSite 当作唯一 CSRF 防线。
  8. CORS 与 CSRF exact Origin validation 共用同一份 typed browser trusted-origin configuration Source of Truth；不得建立两套会漂移的 trusted-origin 配置。
  9. 未来 phone/WeChat 等身份方式通过后续获批的 identity mapping migration 指向既有 `user_id`；当前不提前创建没有 caller 的 identity-provider tables。
  10. V0.1 self-service account/password recovery 保持 Deferred。公开测试前必须重新建立 verified recovery identity 与 recovery flow，不得以 security questions、plaintext recovery secret、generic admin reset endpoint 或虚假 email recovery 替代。
- Rationale: 当前是 first-party Next.js Web → FastAPI → PostgreSQL 拓扑，数据库服务端 session 能直接提供可撤销、可过期、可审计且不向 JavaScript 暴露 token 的最小认证边界，同时为未来新增身份方式保留稳定 `user_id`。
- Consequences: P0-5 按五阶段实施；P0-5B 先建立 identity persistence、migration 与显式 Argon2id security primitives，P0-5C 建立 backend runtime/API，P0-5D 建立真实浏览器 Cookie/CORS/CSRF 闭环，P0-5E 独立验收。没有 verified recovery identity 时，V0.1 用户不能依赖 self-service recovery；公开暴露前还必须补充 durable authentication retry/rate limiting 与更强 compromised-password controls。
- Alternatives: email-first identity；JWT access/refresh token；将 raw session token 持久化；把 phone/WeChat 字段直接耦合到用户主键；仅依赖 SameSite；为每个安全机制维护独立 trusted-origin 配置。
- Re-evaluation: JWT 不是永久禁止。出现 mobile client、third-party API、distributed service trust boundary 或其他 server-side session 无法满足的真实需求时，通过新的 ADR 重新评估。
- Related documents: [`ARCHITECTURE.md`](ARCHITECTURE.md)、[`DATABASE.md`](DATABASE.md)、[`API.md`](API.md)、[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)、[`exec-plans/P0-5_identity-boundary.md`](exec-plans/P0-5_identity-boundary.md)

### ADR-016 — Hong Kong Closed Beta admission and durable auth throttling

- ID: `ADR-016`
- Title: Hong Kong Closed Beta admission and durable auth throttling
- Date: 2026-09-19
- Status: Accepted
- Type: Security
- Source: 用户明确批准的 HK-BETA-2A1 实施范围与参数
- Context: HK-BETA-1 已具备单机 Beta deployment package，但原始 `POST /auth/register` 允许任意互联网用户自助注册，且没有跨进程、跨重启的 authentication throttling；Beta 约束为个人维护、20～100 名邀请用户、无 Admin 后台。
- Decision:
  1. Closed Beta 使用一次性、非 username-bound 邀请码；默认 14 天过期，原始值至少 256-bit entropy，只向人工操作者 stdout 显示一次，数据库只保存 SHA-256 digest。
  2. 邀请消费与 user/session 创建在同一 PostgreSQL transaction 中，并对 invitation row 加锁；unknown、expired、revoked、used invite 与 duplicate username 对未认证调用者统一为 `ENROLLMENT_UNAVAILABLE`。
  3. Durable register/login throttling 使用 PostgreSQL，不引入 Redis。Register 固定为 global `200/hour`、client source `20/hour`、已存在 invite `5/hour`；随机/未知 invite 不创建 per-invite bucket。Login 固定为 global `1200/10 minutes`、client source `60/10 minutes`、account shard `10/15 minutes` 后 block 15 minutes。
  4. Username 先 canonicalize，再经 server-only HMAC 映射到精确 `16384` 个固定 account shards；client source 与其他 bucket key 同样只保存 HMAC digest，raw IP、username、invite secret 不进入 limiter table 或普通日志。
  5. Beta trusted-client-source 只接受 Caddy 覆盖写入的单值 `X-GIA-Client-IP`；API 在 trusted mode 对缺失、重复或非法 IPv4/IPv6 fail closed。Caddy/API 使用私有网络，Web 不加入 API 网络；API 另有仅供既有 LLM provider 出站的非发布 egress network。
  6. Login request password 最大 128 Unicode code points；既有 dummy Argon2、generic credential failure、opaque PostgreSQL session、Cookie/CORS/CSRF/WebSocket contract 保持不变。
  7. Verified recovery、stronger compromised-password controls、account deletion、quota/cost ceiling、PostgreSQL least-privilege role 与其他 go-live gates 不在本 ADR 中实现，仍按既有 Source of Truth 保持 blocker/deferred 状态。
- Rationale: 该方案用当前 PostgreSQL 与单机 Caddy topology 提供最小、可恢复、低运维成本的邀请制与认证滥用防护，并通过固定 shard/仅已知 invitation bucket 避免攻击者制造无界数据库基数。
- Consequences: 新增 `beta_invitations` 与 `auth_rate_limit_buckets` 的线性 Alembic migration；production startup 必须具有独立 HMAC key 与 trusted Caddy mode；API startup 不执行 migration 或 cleanup；没有 Admin UI、Redis、queue 或后台 cleanup job。`beta_invitations.consumed_by_user_id` 当前 `ON DELETE RESTRICT` 且消费字段成对约束依赖已消费用户存在，后续 account/data deletion 阶段必须显式处理该 schema dependency。只有数据库中实际存在的 invitation 才建立 `REGISTER_INVITE` bucket，因此 repeated attempts 仍有低风险的 invitation-existence timing/rate-limit side channel；至少 256-bit 高熵 raw invitation 使线上枚举不可行，但本 ADR 不宣称 invitation existence 对未授权调用者具有严格不可区分性，也不在本轮改变已批准的 per-existing-invite limiter。
- Alternatives: allowlist、预创建账号、Redis limiter、Admin dashboard、username-bound invitation；这些方案对当前 20～100 人个人维护 Beta 增加不必要的操作或基础设施复杂度。
- Related documents: [`API.md`](API.md)、[`DATABASE.md`](DATABASE.md)、[`ARCHITECTURE.md`](ARCHITECTURE.md)、[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)、[`exec-plans/HK-BETA-2A1_closed-beta-admission-auth-hardening.md`](exec-plans/HK-BETA-2A1_closed-beta-admission-auth-hardening.md)

## 4. 仍保持 TBD 的技术事项

以下都是派生 TBD，不是总纲原始 D-xxx：

- TBD：production/default LLM provider and model policy；
- TBD：ASR provider；
- TBD：TTS provider；
- TBD：支付供应商与正式价格；
- TBD：V0.5 public identity expansion、verified recovery identity 与 recovery flow；
- TBD：云平台、中国正式生产部署、CDN 和对象存储产品；
- TBD：analytics 产品与 Sentry/SaaS exporter；
- TBD：Redis implementation/product；
- TBD：task queue implementation；
- TBD：UI primitives/component library；
- TBD：WebSocket schema generator package 和 P1 完整事件 Schema；
- TBD：PWA production strategy；

## 5. 决策变更流程

1. 在任务或评审中明确提出问题；
2. 记录上下文、方案、影响和替代方案；
3. 保持为 `Proposed` 或 `TBD`；
4. 普通且不改变总纲的技术决策，经用户明确批准后可改为 `Accepted`；
5. 如果决策意图改变总纲，用户批准后先更新或升级 `PROJECT_MASTER_PLAN.md`，该记录在新总纲生效前不得作为冲突的 `Accepted` 决策实施；
6. 新总纲生效后再确认决策状态，并同步相关任务、路线图和领域文档；
7. 不允许当前总纲与下层 `Accepted` 决策长期保持相互冲突。
