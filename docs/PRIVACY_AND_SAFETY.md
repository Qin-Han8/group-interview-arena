# 隐私、安全、合规与反作弊基线

- Status: Skeleton / Baseline
- Current phase: P0
- Target version: V0.1 Internal Validation
- Detailed design: Not started
- Security boundaries: Active from project start
- P0-5A identity security boundary: completed / approved
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录从项目开始就必须遵守的隐私、安全、内容安全和反作弊边界。当前尚不是完整威胁模型、隐私政策或合规评估，但其中已确认的边界不能等到公开发布前才处理。

## Confirmed by PROJECT_MASTER_PLAN

### 训练用途与非招聘结论

- 所有 AI 候选人都是虚拟角色并需要明确标识。
- 评分只用于训练参考，不代表任何招聘企业。
- 产品不保证面试结果，不输出录取概率或岗位适配结论。
- 产品不得在正式面试过程中使用，也不得支持冒充真人或欺骗他人。

### 反作弊边界

- 不开发正式面试实时提词；
- 不支持隐蔽悬浮窗或现场辅助；
- 用户交互中的“礼貌打断”等控制只分配发言权，不替用户生成内容；
- 产品流程必须围绕考前训练，而非真实面试执行。

### 数据最小化

- 首期不采集人脸视频，不做表情、微表情或眼神评分；
- 只收集训练所需的最少信息；
- 明确告知音频、转写和模型处理方式；
- 用户应能查阅、更正、删除数据并注销账号；
- 原始音频和转写采用最短必要保存策略；
- 模型日志不得保留不必要的完整敏感输入；
- 匿名训练数据必须单独授权并去标识化。

首期避免采集身份证、精确住址、正式面试录音、未经同意的第三方聊天/录音和招聘企业内部保密材料。上传自定义题目时必须提示不得上传公司保密资料。

### AI 身份与内容标识

- 界面明确标识 AI 候选人语音和内容；
- 分享或导出 AI 生成内容时，按适用规则处理显式和隐式标识；
- 不将 AI 候选人设计成故意冒充真实个人的形态。

### 安全工程

- 所有密钥只在服务端保存；
- 前端不得包含模型或其他服务端密钥；
- 音频上传未来使用短期签名；
- 用户之间数据严格隔离；
- 对象存储默认私有；
- 管理后台采用最小权限；
- 支付、权益和退款写入审计日志；
- 重要操作支持幂等及可恢复设计；
- 定期检查依赖和对象存储权限；
- 防范 Prompt 注入导致系统提示、角色私有信息或评分规则泄露。

### 内容安全

系统未来需要识别和处置仇恨歧视、侮辱、色情暴力、自残风险、违法指导、针对真实个人的诽谤、利用自定义题目骚扰及 AI 对用户的人格攻击。

合理反驳、压力和挑战观点不等于贬低个人，策略必须保留这一边界。

## 当前版本范围

- P0：建立安全边界、密钥规则、数据隔离原则和后续检查责任。
- V0.1：即使是内部文字版，也必须遵守 AI 标识、训练用途、数据最小化、密钥和隔离规则。
- V0.5：公开 MVP 必须提供删除数据和隐私设置，并对语音生命周期完成明确实现。
- P0-2 只记录了获批的信任边界、配置、错误和日志原则；P0-5B 已实现 identity persistence/security primitives，P0-5C 已实现 backend auth runtime，P0-5D 已实现 browser CORS/CSRF/Web closure；内容审核和其他后续安全能力仍未实现。

## P0-5 identity security boundary — P0-5D browser closure implemented

- Initial credential 是 username/password；password 使用 application 显式拥有参数的 Argon2id，只持久化 password hash；
- small application-owned offline password blocklist 已在 P0-5B 实施，只做 full-password match，并覆盖 context-specific obvious passwords；不做 substring 禁止；
- P0-5 不接入 external breach API、massive leaked-password dataset、Redis 或 production distributed rate limiter；公开暴露前必须重新评估 stronger compromised-password controls 与 durable authentication retry/rate limiting；
- opaque raw session token 只存在于 host-only HttpOnly Cookie；数据库只保存 cryptographic digest；
- password、password hash、raw token、Cookie header、session digest 与 database credential URL 不得进入 response 或日志；
- browser Cookie authentication 需要 explicit credentialed CORS、exact Origin validation、required custom CSRF header 与 SameSite defense-in-depth；CORS/CSRF 共用同一 typed trusted-origin Source of Truth；
- 当前 username/password 没有 verified email、verified phone 或 WeChat identity，因此 V0.1 self-service password/account recovery Deferred；不得加入 security questions、plaintext recovery secret、generic admin reset endpoint 或虚假 email recovery；
- 公开测试前必须形成 verified recovery identity/flow，并重新审查账号删除、数据保留和用户所有业务数据的处置边界。

P0-5B 已实现显式参数的 Argon2id hash/verify/verify-and-update、username/password policy、`users`/`auth_sessions` persistence、SHA-256 session digest 与 7-day absolute-expiry primitives。P0-5C 已实现 backend register/login/logout/me、固定 dummy Argon2 unknown-user path、server-side session validation 与 host-only HttpOnly `gia_session` Cookie issue/clear；raw session token 不进入普通 result repr，production + insecure Cookie 配置会 fail closed，safe response tests 与 structured-log field audit 确认不回显 password、hash、raw token 或 digest。P0-5D 已实现 shared exact-origin credentialed CORS、unsafe auth POST 的 Origin/custom-header CSRF、`credentials: "include"` Web client 与真实 Chromium closure；浏览器验证确认 `document.cookie` 不暴露 `gia_session`，local/session storage 不保存认证 secret，logout 后服务端 session 与 Cookie 均失效。recovery 继续 Deferred。

## Implementation guidance

- 每个新数据字段都应说明目的、保留、删除、访问和日志处理。
- 安全检查必须与具体架构和供应商选择同步，而不是独立附加。
- 用户删除训练记录时，结构化指标应同步删除或匿名化。
- 不完整或故障会话的日志也必须遵守最小化原则。

## TBD

- TBD：原始音频是否默认完全不保存（总纲第 37 节）；
- TBD：音频、转写、日志、报告和匿名数据的精确保留期限；
- TBD：是否允许用户上传自定义题目（总纲第 37 节）；
- TBD：国内备案公开运营还是小范围邀请测试（总纲第 37 节）；
- TBD：V0.1 之后的 phone/WeChat/additional identity mapping 与 authorization；
- TBD：public testing 前的 verified recovery identity/flow；
- TBD：内容审核、投诉、申诉和人工处置流程；
- TBD：隐私同意文本、撤回机制和隐私影响评估流程；
- TBD：供应商数据处理、跨境及数据驻留要求；
- TBD：安全事件响应和审计保留策略。

除特别注明的总纲问题外，其余是派生 TBD，不是新的 D-xxx。

## Future work

- P0-2：在架构决策中记录基础信任边界；完整威胁建模随实际接口、数据和 Provider 逐步细化。
- P0-5C～P0-5E：backend/browser authentication、Cookie/CORS/CSRF 与最小日志边界已实现；P0-5E final outcome 为 `PASS after findings remediation and independent recheck`，P0-5 已转为 `DONE`。
- P0-6：awaiting explicit user approval / not started；获准进入后建立不泄露敏感信息的日志、安全检查和基础监控。
- P2：完成语音同意、上传、保存和删除设计。
- P4/P5：完成支付审计、公开隐私设置、投诉和发布合规检查。

## 与其他文档关系

- 产品非目标：[`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md)
- 技术信任边界：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- 数据生命周期：[`DATABASE.md`](DATABASE.md)
- API 认证与签名：[`API.md`](API.md)
- 发布安全验收：[`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)
