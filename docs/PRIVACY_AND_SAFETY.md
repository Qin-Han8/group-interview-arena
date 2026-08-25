# 隐私、安全、合规与反作弊基线

- Status: Active baseline through completed P1-5D first-provider integration + completed P1-5E automatic orchestration (P1-5E-1/P1-5E-2/P1-5E-3)
- Current phase: P1 — IN_PROGRESS
- Target version: V0.1 Internal Validation
- Detailed design: P1-5E-1 automatic orchestration privacy/safety boundary frozen；P1-5E-2 single-turn and P1-5E-3 continuous/configured composition remain provider-neutral；automated tests are network-free and the separately user-run sanitized composition smoke is `PASS`；full production/privacy design remains incomplete
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
- P0-2 只记录了获批的信任边界、配置、错误和日志原则；P0-5B 已实现 identity persistence/security primitives，P0-5C 已实现 backend auth runtime，P0-5D 已实现 browser CORS/CSRF/Web closure；P0-6C structured logging hardening、actual-source review 与 `JsonFormatter` safe fallback remediation/re-review 已完成并 `PASS`；内容审核和其他后续安全能力仍未实现。

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

## P0-6C application logging safety boundary — completed

- application logs 只从显式安全字段构造，不先收集 body/header/query/path/exception 再依赖通用 redaction；
- matched request 只记录 resolved route template；unmatched/404 只记录固定 `unmatched` classification，不记录 raw path 或任何 hash/truncation derivative；
- unexpected exception 只记录固定 `exception_category`，不记录 exception message、traceback、locals、SQL 或 filesystem path；
- negative tests 覆盖 password、request body、Cookie、raw session token、Authorization、CSRF header、query、dynamic path、exception 与 credential database URL sentinel，application logs 与 error response 均不得包含这些值；
- missing、`None`、non-string 或 empty event 使用固定低基数 `logging.record.invalid` fallback；formatter 不读取 message/args 或输出 exception diagnostic，logging misuse 不影响 request handling；
- P0-6C 未预建 tracing caller；P0-6D 已单独实现最小 OpenTelemetry tracing，OTel Logs、metrics、auto-instrumentation、vendor SDK 与 logging backend 仍未引入。

## P0-6D tracing safety boundary — completed

- tracing 默认关闭，不创建 provider/exporter，不联系 collector；启用配置是 server-only，OTLP endpoint 对 userinfo、query、fragment fail closed，P0-6 不支持 auth header/token/certificate/credential-provider；
- request carrier 只白名单复制 W3C `traceparent`，不接受 `tracestate` 或 baggage；不将 arbitrary headers、query、body、Cookie/session、Authorization/CSRF、identity、SQL、database URL、exception message/stack 或模型 payload 写入 span；
- resource 只由项目 typed config 直接构造 `service.name`，不运行 OTel ambient resource detection，也不吸收任意 `OTEL_RESOURCE_ATTRIBUTES`、`OTEL_SERVICE_NAME` 或 detector metadata；
- tracing enable 与 sampler authority 均由项目拥有：enabled 时若 ambient `OTEL_SDK_DISABLED` 会禁用 SDK 则在创建 provider/exporter 前 fail closed，sampler 显式固定为 parent-based always-on，不受 `OTEL_TRACES_SAMPLER`/`OTEL_TRACES_SAMPLER_ARG` 覆盖；
- enabled 时对 OTel 1.44.0 OTLP HTTP exporter 会读取的 headers、client key/certificate 与 trace credential-provider ambient variables 做 presence-only fail-closed validation，不读取或记录 credential value；disabled 时不建立 exporter，因此不因这些变量失败；
- matched span 仅使用 resolved route template；unmatched/404 使用固定 `<unmatched>`，不保留 raw/hashed/truncated path；5xx 只记录固定 `error.type`，不自动 record exception event；
- logs 的 `trace_id`/`span_id` 仅来自 active valid OTel span context，caller-supplied 同名字段不能伪造 correlation；
- exporter flush/shutdown failure 只产生固定 `telemetry.export.failed` 与安全 category，不记录 endpoint、credential、response body 或异常消息；失败不影响 request handling 或 database cleanup；
- sentinel negative tests 已覆盖 query/header/body/Cookie/Authorization/CSRF/dynamic path/exception/database URL，exported spans、application logs 与 error response 均不包含这些值。

## P1-2C question/private-data transport boundary — completed

- Ordinary authenticated `GET /questions`、detail、session snapshot、OpenAPI derivative、WebSocket 和 browser DOM 只使用 closed public DTO allowlist；不序列化 ORM/domain 私有对象。
- Private Stance、Persona Template behavior parameters、reference dimensions、hidden conflicts、acceptable outcome patterns、phase prompts 和 safety/internal calibration fields 不进入普通 transport、日志或错误。
- Session creation 只返回 safe `question_version_id`；assignment/private completeness 仅在 server-side transaction 内验证，没有为了未来 LLM caller 创建内部 endpoint。
- PostgreSQL/REST/OpenAPI/Web/Chromium negative sentinel tests 验证内部私有值不会出现在 JSON、generated contract、日志或 DOM；owner、CSRF/CORS/Origin 与 WebSocket safe-error 边界保持不变。

## P1-5D completed first-provider secret/data boundary

- Zhipu API key only exists in lazy server-only `GIA_API_ZHIPU_API_KEY` `SecretStr` settings and the outbound Authorization header。Required `GIA_API_ZHIPU_MODEL` is non-secret but remains lazy server-only configuration；neither value is collected by global settings or exposed through `NEXT_PUBLIC_*`。Both have no default；missing or whitespace-only values fail closed only when provider settings are explicitly loaded，while ordinary API startup remains independent。
- Provider input contains only the existing rendered authorized prompt and non-secret provenance。Project-owned `provider_identifier`、configured `model_identifier` and model-independent `configuration_version` remain durable allowlisted internal provenance and are not projected to current user-facing UI/API/report surfaces。Provider request/response IDs、provider response headers、raw provider metadata、raw request/response bodies、reasoning content、credentials and raw exception messages are not copied into durable metadata/results、ordinary logs、traces or public exceptions。
- Adapter failures discard provider error bodies and normalize only allowlisted `TIMEOUT`、`RATE_LIMIT`、`PROVIDER_UNAVAILABLE`、`PARTIAL_GENERATION`、`INVALID_OUTPUT` or `INTERNAL_ERROR` codes。There is no adapter logging and application retry is `0`。
- Sentinel tests cover settings/provider/result repr and serialization、captured application logs、typed failures and PostgreSQL request/utterance metadata。All automated provider tests use injected HTTPX MockTransport；Codex made zero real GLM calls。
- Implementation/config-driven patch actual-source reviews and the final user-run sanitized real-provider acceptance smoke are `PASS`。Only allowlisted acceptance facts are recorded：`zhipu`、`glm-4.7-flashx`、`ZHIPU_CHAT_DEV_V1`、`RawGenerationSuccess` and satisfaction of the intended Chinese group-interview smoke expectation；credential、raw provider response、sensitive headers、verbatim generated content and diagnostic payloads are not recorded。Production supplier processing、data residency、retention、cross-border terms and production/default provider/model policy remain TBD。

## P1-5E-1 automatic orchestration privacy/safety freeze — no telemetry implementation

- Automatic coordination consumes only owner-scoped session/current-grant、participant eligibility、exact Prompt Version、Generation Request/AiUtterance and allowlisted floor/scheduler facts。It does not expand provider prompt content、Private Stance visibility or user-facing provider/model exposure。
- The orchestrator must never persist/log/expose the Zhipu key、Authorization header、rendered private prompt、raw provider request/response、raw exception text、reasoning content、another participant's Private Stance or hidden persona calibration。Deterministic IDs are opaque project identities，not containers for sensitive input。
- Durable provenance remains allowlisted：session/grant/request/utterance identities、exact Prompt Version identity、provider/model/configuration identifiers and typed safe generation failure code。`FloorRelease.reason = INTERRUPTED` for terminal AI failure does not replace or weaken the request's typed failure truth。
- `RUNNING`、request conflict、internal uncertainty and stale/unproved state stop automatic progression。After release/scheduler persistence uncertainty，only an exact proved durable result may be recovered；another proved authority change returns `STATE_CHANGED`，and otherwise the drive returns `RECONCILIATION_REQUIRED`。Safety favors uncertain durable truth over retry/progress；no second provider call、synthetic result、stale release or unproved next scheduling is allowed。
- HUMAN ownership is a hard safety boundary：no automatic generation、fabrication、release or scheduling over the human。P1-5F must preserve that boundary when transport is later introduced。
- Future internal diagnostics may allowlist `session_id`、`floor_grant_id`、`generation_request_id`、orchestration outcome code、provider/model provenance and aggregate latency/counters only。P1-5E-1 adds no log field、trace span、metric、table、dependency or telemetry exporter。
- P1-5E-2/P1-5E-3 automatic tests remain network-free and include privacy sentinels。The configured composition reads secrets only through lazy `SecretStr` settings at explicit invocation；missing configuration raises one generic safe error before provider/drive work，and no secret enters result serialization。Codex made zero real-provider calls。The separately user-run sanitized composition smoke is `PASS`；no credential、Authorization header、raw provider response、rendered prompt、Private Stance or verbatim model output was recorded，and its temporary test file was removed from project source。

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
- P0：`DONE`；P1 is `IN_PROGRESS`，P1-1～P1-4 and P1-5A/B/C/D/P1-5E/P1-5E-1/P1-5E-2/P1-5E-3 are completed；Codex made no real-model call and recorded no provider secret/raw response；P1-5F transport is `NOT_STARTED` and requires separate explicit approval。
- P2：完成语音同意、上传、保存和删除设计。
- P4/P5：完成支付审计、公开隐私设置、投诉和发布合规检查。

## 与其他文档关系

- 产品非目标：[`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md)
- 技术信任边界：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- 数据生命周期：[`DATABASE.md`](DATABASE.md)
- API 认证与签名：[`API.md`](API.md)
- 发布安全验收：[`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)
