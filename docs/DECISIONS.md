# 产品与技术决策记录

- Status: Active governance baseline
- Current phase: P0
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md)，高于领域文档和代码实现
- Last established by task: P0-1

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

## 3. 技术建议登记（非 Accepted 决策）

总纲提出了 Next.js/React、TypeScript、FastAPI、Pydantic、PostgreSQL、Redis、WebSocket/SSE、Docker Compose、对象存储、可观测性工具及可选 LangGraph 等方向。这些当前统一为：

- Status: `Proposed / Recommended`
- Source: `PROJECT_MASTER_PLAN V1.0 §21`
- Decision stage: `P0-2 技术架构决策`

它们不得在 P0-1 中被表述为已经冻结的技术选型。

## 4. 待决策技术事项

以下都是派生 TBD，不是总纲原始 D-xxx：

- TBD：Node.js 包管理工具；
- TBD：Python 包与环境管理工具；
- TBD：仓库组织和 monorepo 工具；
- TBD：正式身份认证方案；
- TBD：ASR、TTS 和 LLM 供应商；
- TBD：支付供应商；
- TBD：云平台、部署和对象存储方案；
- TBD：异步队列具体产品；
- TBD：V0.1 四种基础角色的具体组合。

## 5. 决策变更流程

1. 在任务或评审中明确提出问题；
2. 记录上下文、方案、影响和替代方案；
3. 保持为 `Proposed` 或 `TBD`；
4. 普通且不改变总纲的技术决策，经用户明确批准后可改为 `Accepted`；
5. 如果决策意图改变总纲，用户批准后先更新或升级 `PROJECT_MASTER_PLAN.md`，该记录在新总纲生效前不得作为冲突的 `Accepted` 决策实施；
6. 新总纲生效后再确认决策状态，并同步相关任务、路线图和领域文档；
7. 不允许当前总纲与下层 `Accepted` 决策长期保持相互冲突。
