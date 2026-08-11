# API 与事件设计骨架

- Status: Skeleton / Baseline
- Current phase: P0
- Target version: V0.1 Internal Validation
- Detailed design: Not started
- Implemented contracts: None
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件未来定义 HTTP API、实时事件、认证、错误、幂等、版本和兼容规则。当前列出的端点和事件全部是 `Master-plan level contract examples`，不是已经实现或冻结的正式 API。

## Confirmed by PROJECT_MASTER_PLAN

### Master-plan level contract examples — REST

总纲给出的示例包括：

```text
POST /sessions
GET  /sessions/{id}
POST /sessions/{id}/device-check
POST /sessions/{id}/start
POST /sessions/{id}/actions/request-floor
POST /sessions/{id}/actions/interrupt
POST /sessions/{id}/actions/nominate
POST /sessions/{id}/finish
GET  /sessions/{id}/report
GET  /questions
POST /drills/{id}/attempts
GET  /users/me/progress
POST /orders
POST /payments/webhook
```

这些示例跨越 V0.1、V0.5 及后续范围，不能全部提前实现。

### Master-plan level contract examples — real-time events

客户端事件示例：

```text
audio.chunk
audio.end
floor.request
floor.interrupt
participant.nominate
vote.start
vote.submit
session.pause
```

服务端事件示例：

```text
session.state_changed
transcript.partial
transcript.final
participant.wants_to_speak
participant.speaking
participant.interrupted
tts.chunk
timer.updated
discussion.memory_updated
system.notice
session.completed
```

### 一致性原则

- 支付回调必须幂等；
- 权益扣减在正式开始讨论时发生；
- 系统故障失败的场次自动返还；
- 事件按 session sequence 编号；
- 断线恢复以服务端状态为准；
- 报告关联题目、模型和评分规则版本。

## 当前版本范围

- 当前 P0-1：不实现 API、WebSocket、SSE、认证或服务。
- P0-2：确认通信技术和契约治理方式。
- P0-3：只建立批准的最小基础 API。
- V0.1：后续只实现文字讨论闭环实际需要的最小契约。
- 语音、训练、订单、支付和权益接口不得因出现在总纲示例中而提前进入 P0/V0.1。

## Implementation guidance

- 正式契约需要定义身份与授权、请求响应 Schema、错误、幂等键、事件顺序、重试和兼容策略。
- 关键模型调用和事件载荷未来应采用结构化 Schema 验证。
- 实时通信使用 WebSocket 或 SSE 仍是建议项，尚未决定具体边界。
- 断线恢复、时间控制和会话状态以服务端为准。

## TBD

- TBD：WebSocket、SSE 及普通 HTTP 的具体边界；
- TBD：API 版本策略和错误格式；
- TBD：正式认证与授权方案；
- TBD：V0.1 最小端点和事件集合；
- TBD：事件投递、重放、幂等和顺序保证细节；
- TBD：音频上传和短期签名的正式协议；
- TBD：支付 Provider 和 webhook 契约；
- TBD：公开 API 是否存在及其时间点。

这些是派生 TBD，不是总纲原始 D-xxx。

## Future work

- P0-2：形成通信和契约治理 ADR。
- P0-3：定义并实现最小基础 API。
- P1：细化文字会话和讨论事件。
- P2：细化音频、转写、TTS、打断和恢复事件。
- P4：细化订单、支付、权益和故障返还契约。

## 与其他文档关系

- 系统模块：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- 会话状态：[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)
- 数据模型：[`DATABASE.md`](DATABASE.md)
- 安全要求：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
