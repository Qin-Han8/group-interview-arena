# 技术架构骨架

- Status: Skeleton / Baseline
- Current phase: P0
- Target version: V0.1 Internal Validation
- Detailed design: Not started
- Architecture decisions: Not accepted in P0-1
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件未来记录系统上下文、模块边界、运行拓扑、依赖方向和正式 ADR。当前只整理总纲级架构分层和推荐方向，不代表技术选型或部署方案已冻结。

## Confirmed by PROJECT_MASTER_PLAN

### 总纲架构分层

```text
Web 客户端
  -> API 网关 / 认证
  -> 训练会话服务
      -> 讨论编排器
      -> AI 角色服务
      -> 语音服务
      -> 结构化记忆服务
  -> 评分与报告服务
  -> 题目内容服务
  -> 订单与权益服务
  -> 管理后台
  -> PostgreSQL / Redis / 对象存储
```

这是一份总纲层面的逻辑分层，不表示当前已有服务、部署单元或基础设施。

### 系统模块边界

- 用户与身份：注册登录、设置、隐私同意、删除账号和设备会话；
- 题目内容：查询、版本、难度标签、发布状态和 AI 变体；
- 训练会话：创建、状态、发言、时间、恢复和未来权益扣减；
- 讨论编排：阶段、发言人、角色决策、记忆、冲突和收敛；
- 语音：音频流、ASR、分句、TTS 和生命周期；
- 评分报告：特征、证据、聚合、报告和用户反馈；
- 商品权益：商品、订单、支付回调、场次、有效期、退款和补偿。

模块是领域责任边界，不要求早期拆成微服务。

## 当前版本范围

- 当前 P0-1：只建立文档和决策治理。
- P0-2：确认技术选择、仓库组织、模块边界和 ADR。
- V0.1：只支持内部文字版验证，不需要语音、支付、完整成长或行业题包。
- 不得因总纲展示完整长期架构就在 P0 一次性实现所有模块。

## Implementation guidance

总纲推荐但尚未正式决定的方向：

- 前端：Next.js/React、TypeScript、Tailwind CSS 或成熟组件库、Web Audio API、WebSocket/SSE、PWA；
- 后端：Python FastAPI、Pydantic、SQLAlchemy 或等价 ORM、PostgreSQL、Redis、异步任务队列；
- AI/语音：供应商抽象层、流式 ASR、流式或分段 TTS、自定义状态机；LangGraph 可选；
- 基础设施：Docker Compose、本地环境、对象存储、CDN、Sentry/OpenTelemetry 和产品分析工具。

所有上述内容当前状态均为 `Proposed / Recommended`。核心讨论调度逻辑即使采用工作流框架，也必须由项目代码掌控。

## TBD

以下均留给 P0-2 或后续 ADR，当前不是 Accepted：

- TBD：仓库结构和 monorepo 工具；
- TBD：Node.js 与 Python 包管理工具；
- TBD：WebSocket 或 SSE 的具体使用边界；
- TBD：正式认证方案；
- TBD：LLM/ASR/TTS Provider 接口及供应商；
- TBD：异步任务队列产品；
- TBD：部署、云平台、CDN 和对象存储；
- TBD：本地开发编排方式；
- TBD：日志、追踪和产品分析工具；
- TBD：模块是进程内模块还是独立服务的演进条件。

这些是派生 TBD，不是总纲原始 D-xxx。

## Future work

- P0-2：比较候选方案并形成必要的 Accepted ADR。
- P0-3：依据 ADR 建立最小前后端骨架。
- P0-4～P0-6：逐步补齐数据库、身份、CI、日志和可观测性。
- P1 以后：按当前版本需求演进业务模块，避免提前微服务化。

## 与其他文档关系

- 技术决策状态：[`DECISIONS.md`](DECISIONS.md)
- 数据边界：[`DATABASE.md`](DATABASE.md)
- API 与事件：[`API.md`](API.md)
- 安全约束：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
- 当前执行顺序：[`ROADMAP.md`](ROADMAP.md) 和 [`TASKS.md`](TASKS.md)
