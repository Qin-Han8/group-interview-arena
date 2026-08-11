# AI 群面训练场

Group Interview Arena

## 项目定义

AI 群面训练场让用户无需临时召集真人，即可与具有不同性格、立场和行为模式的 AI 候选人完成受控的无领导小组讨论，并获得基于真实发言证据的结构化复盘和专项训练。

本仓库的最高层产品依据是 [`docs/PROJECT_MASTER_PLAN.md`](docs/PROJECT_MASTER_PLAN.md)。本 README 只提供入口和状态摘要，不替代总纲。

## 当前状态

- 当前开发阶段：`P0 — 项目基础`
- 已完成任务：`P0-1 — 仓库与文档治理`
- 下一候选任务：`P0-2 — 技术架构决策`
- P0-2 状态：`尚未开始 / awaiting explicit approval`
- 当前目标版本：`V0.1 — Internal Validation / 内部技术验证版`
- 当前实现状态：尚无业务代码或可运行应用

> 当前仍无可运行应用；P0-2 尚未获准开始。

## 核心原则摘要

- 动态群面模拟优先，不退化为题库或答案生成器。
- 讨论由状态机、阶段目标和发言权调度受控编排，不让多个 Agent 自由聊天。
- 首期每场使用 3 名 AI 候选人，并优先保证角色行为差异。
- 评分面向可观察行为，重要评价必须尽量关联时间戳和原话证据。
- 所有评分只用于训练，不给出录取概率或岗位适配结论。
- 产品是考前训练工具，不开发正式面试实时提词或其他作弊辅助。

## 仓库结构

```text
.
├── AGENTS.md                    # 开发代理长期执行规则
├── README.md                    # 仓库入口
├── .editorconfig                # 基础文本格式约定
├── .gitattributes               # 跨平台文本统一使用 LF
├── .env.example                 # 环境变量安全说明；当前无业务变量
├── .gitignore                   # 本地文件和敏感文件忽略规则
└── docs/
    ├── PROJECT_MASTER_PLAN.md   # 最高层产品设计基线
    ├── DECISIONS.md             # 产品与技术决策记录
    ├── ROADMAP.md               # 阶段、版本和里程碑
    ├── TASKS.md                 # 当前阶段任务清单
    ├── PRODUCT_REQUIREMENTS.md  # 产品需求骨架
    ├── QUESTION_SYSTEM.md       # 题型与题目系统骨架
    ├── AGENT_BEHAVIOR.md        # AI 角色与讨论编排骨架
    ├── SCORING_RUBRIC.md        # 评分与证据体系骨架
    ├── ARCHITECTURE.md          # 技术架构骨架
    ├── DATABASE.md              # 数据模型骨架
    ├── API.md                   # API 与事件设计骨架
    ├── PRIVACY_AND_SAFETY.md    # 隐私、安全与反作弊基线
    ├── RELEASE_CHECKLIST.md     # 分阶段发布检查骨架
    └── exec-plans/              # 复杂任务执行计划约定
```

业务代码目录将在对应任务获得批准并实际创建后再写入本节；不得把 planned 结构描述为已经实现。

## 文档阅读顺序

开始开发任务前，按以下顺序获取上下文：

1. [`docs/PROJECT_MASTER_PLAN.md`](docs/PROJECT_MASTER_PLAN.md)
2. [`AGENTS.md`](AGENTS.md)
3. [`docs/ROADMAP.md`](docs/ROADMAP.md)
4. [`docs/TASKS.md`](docs/TASKS.md)
5. [`docs/DECISIONS.md`](docs/DECISIONS.md)
6. 与当前任务直接相关的领域文档、代码和测试

如果下层文档或代码与上层依据冲突，先报告冲突并确认决策，不得静默改变产品方向。

## 如何运行

当前没有应用代码、依赖清单或启动命令。

> 当前仍无可运行应用；下一候选任务 P0-2 需要用户明确批准后才能开始。

后续只有在项目骨架任务完成后，才能在这里记录经过验证的安装和运行方式。

## 贡献规则

- 保持任务小而可审查，提交也应小而聚焦。
- 修改前先读取当前阶段、任务、决策和相关领域文档。
- 不越过当前阶段和目标版本边界，不“顺手”实现后续功能。
- 新的产品或技术决策必须先记录到 `docs/DECISIONS.md` 并取得所需批准。
- 任务状态变化同步更新 `docs/TASKS.md`；阶段变化同步更新 `docs/ROADMAP.md`。
- 代码、测试与文档必须保持一致。
- 默认先交付 diff；除非用户明确授权，不自动提交或推送。
