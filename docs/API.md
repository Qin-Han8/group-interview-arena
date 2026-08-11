# API 与事件技术基线

- Status: P0 API Architecture Baseline
- Current phase: P0
- API architecture baseline established by: P0-2 — DONE
- Target version: V0.1 Internal Validation
- Implemented contracts: None
- Detailed P1 WebSocket schema: Not started
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录 P0-2 已批准的 REST、WebSocket、契约生成、恢复和错误语义基线。它不表示任何 API 已实现，也不冻结完整 P1 事件集合。

正式决策见 [`DECISIONS.md`](DECISIONS.md) `ADR-006`、`ADR-007`、`ADR-013`。

## Accepted protocol split

### REST

REST 用于：

- resource CRUD；
- question fetch；
- session create；
- session snapshot/load；
- reports；
- settings；
- future admin/orders。

总纲中的 endpoint 只是跨版本示例。P0-3 只建立获批的最小健康/基础 API；V0.1、V0.5 的业务接口必须在对应任务进入范围后才设计和实现。

### WebSocket

WebSocket 用于活动会话中的：

- client commands；
- state changes；
- participant events；
- timer；
- floor control；
- interruption；
- AI streamed text；
- future speech-related session events。

SSE 不作为活动 session 主协议。未来如果存在单向长任务进度等真实需求，可以单独评估，但不能因此建立第二套活动会话协议。

## WebSocket implementation timing

P1 的第一个文字讨论 vertical slice 建立 WebSocket session channel。不得先用 HTTP 完成整套文字讨论，再到 P2 重写 realtime。

P0-3 不实现 WebSocket 业务代码。P1 实施时遵守：

- server authoritative session state；
- client commands use action identity；
- session events are ordered；
- reconnect uses snapshot + sequence；
- state recovery is based on server truth。

## REST contract authority

- FastAPI OpenAPI 是 REST contract 的 Source of Truth；
- Frontend 从 OpenAPI 生成 TypeScript types/client；
- 不允许前后端手写两套同名 DTO；
- 具体 OpenAPI generator package 延后到 P0-3 选择；
- generator 选择不得改变 OpenAPI-as-source-of-truth 的 Accepted decision。

## Versioned WebSocket contract

WebSocket 使用独立版本化 event contract。原则至少包含：

- event type；
- schema version；
- session identity；
- ordering sequence；
- occurrence timestamp；
- client action identity，用于命令与结果关联。

时间戳使用 ISO 8601；UTC 输出使用 `Z`。事件顺序依赖 session 内 monotonic sequence，不依赖 UUID 顺序。

具体字段、JSON Schema、generator package、投递与重放细节在 P1 API design 中冻结。本文件不把总纲事件示例伪装成已经完成的正式 Schema。

## Snapshot and reconnect principle

- 服务端状态是权威来源；
- 客户端不能仅凭本地事件推断正式 session state；
- snapshot/load 使用 REST；
- WebSocket 承载 snapshot 之后的有序增量；
- client action identity 用于识别重试或重复命令；
- sequence 缺口、幂等窗口、保留期和重放范围由 P1 结合持久化设计确定。

## Unified error semantics

REST error model 至少表达：

- standard HTTP status；
- stable machine-readable error code；
- safe user-facing message；
- request correlation；
- optional safe details。

WebSocket 使用语义一致的 error event，并在实际 Schema 中增加必要的 session/action 上下文。

禁止在 API 或实时错误中暴露：

- stack trace；
- SQL；
- filesystem paths；
- secret；
- prompt；
- provider credentials。

具体 error field schema 按 P0-3/P1 实际接口逐步冻结，不以框架默认错误载荷作为未经决策的长期契约。

## Security and authority boundaries

- FastAPI 是领域、会话状态和持久化的业务权威；
- Next.js server-side 能力不得复制领域规则、状态机、评分、Agent 编排或持久化权威；
- 服务端密钥不得进入浏览器；
- 正式认证方案仍为 TBD；
- production 环境不得误启不安全的开发身份；
- structured output 和关键事件 payload 在对应实现阶段使用 Schema validation；
- prompt、角色私有信息和评分规则不得因 API 错误或日志泄露。

## Phase boundaries

### P0-3

- 最小健康/基础 API；
- Web → API connectivity；
- OpenAPI contract authority 落地；
- 基础 config、request correlation、structured logging 和 error semantics；
- 不实现 session WebSocket、Provider、数据库或业务端点。

### P1

- 细化文字会话 REST 端点；
- 冻结第一个版本化 WebSocket 事件契约；
- 实现 action identity、sequence、snapshot/reconnect；
- 添加 WebSocket tests 和 deterministic session regression。

### P2 and later

- P2 才细化音频、ASR、TTS、打断和恢复事件；
- P4 才细化订单、支付、权益和故障返还契约；
- 不得因长期端点出现在总纲示例中而提前实现。

## TBD

- TBD：具体 OpenAPI generator package；
- TBD：WebSocket schema generator package；
- TBD：P1 最小 REST endpoint 和 WebSocket event 集合；
- TBD：事件投递、重放、幂等窗口和兼容策略；
- TBD：正式认证与授权方案；
- TBD：音频上传和短期签名协议；
- TBD：支付 Provider 和 webhook 契约；
- TBD：公开 API 是否存在及其时间点。

## 与其他文档关系

- 正式决策：[`DECISIONS.md`](DECISIONS.md)
- 系统模块：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- 会话状态：[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)
- 数据模型：[`DATABASE.md`](DATABASE.md)
- 安全要求：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
