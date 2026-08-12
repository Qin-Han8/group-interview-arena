# AI 群面训练场

Group Interview Arena

## 项目定义

AI 群面训练场让用户无需临时召集真人，即可与具有不同性格、立场和行为模式的 AI 候选人完成受控的无领导小组讨论，并获得基于真实发言证据的结构化复盘和专项训练。

本仓库的最高层产品依据是 [`docs/PROJECT_MASTER_PLAN.md`](docs/PROJECT_MASTER_PLAN.md)。本 README 只提供入口和状态摘要，不替代总纲。

## 当前状态

- 当前开发阶段：`P0 — 项目基础`
- 已完成任务：
  - `P0-1 — 仓库与文档治理`
  - `P0-2 — 技术架构决策`
- 当前任务：`P0-3 — 前后端项目骨架（IN_PROGRESS）`
- 已完成子步骤：`P0-3C — Root workspace + Web skeleton`
- 下一子步骤：`P0-3D — API skeleton（awaiting explicit approval）`
- 当前目标版本：`V0.1 — Internal Validation / 内部技术验证版`
- 当前实现状态：Web 技术骨架可运行；API、数据库和群面业务尚未实现

> P0-3C 的 Web 技术骨架已完成本地检查；P0-3 整体仍在进行中，不得在未获明确批准时进入 P0-3D。

## 核心原则摘要

- 动态群面模拟优先，不退化为题库或答案生成器。
- 讨论由状态机、阶段目标和发言权调度受控编排，不让多个 Agent 自由聊天。
- 首期每场使用 3 名 AI 候选人，并优先保证角色行为差异。
- 评分面向可观察行为，重要评价必须尽量关联时间戳和原话证据。
- 所有评分只用于训练，不给出录取概率或岗位适配结论。
- 产品是考前训练工具，不开发正式面试实时提词或其他作弊辅助。

## P0 已批准技术基线

- 简单 monorepo，`apps/web` 已建立，`apps/api` 仍待 P0-3D；当前不使用 Nx/Turborepo；
- Web：Next.js App Router、React、TypeScript strict、Tailwind CSS；
- API：FastAPI、Pydantic v2；业务权威不放入 Next.js；
- 工具链：Node.js 24 LTS + pnpm，CPython 3.14 + uv；
- 数据：P0-4 使用 PostgreSQL 18.x、SQLAlchemy 2.x、Alembic；
- 通信：REST + WebSocket；FastAPI OpenAPI 是 REST contract 权威；
- 本地开发：应用原生运行，P0-4 起基础服务使用 Docker Compose；
- Redis、独立 task queue、OpenTelemetry、具体 AI/语音供应商和 UI component library 仍为 Deferred/TBD；
- V0.1 使用自定义确定性讨论状态机，不使用 LangGraph。

完整决策、替代方案和重新评估条件见 [`docs/DECISIONS.md`](docs/DECISIONS.md)。

## 仓库结构

```text
.
├── AGENTS.md                    # 开发代理长期执行规则
├── README.md                    # 仓库入口
├── .editorconfig                # 基础文本格式约定
├── .gitattributes               # 跨平台文本统一使用 LF
├── .env.example                 # 环境变量安全说明；当前无业务变量
├── .gitignore                   # 本地文件和敏感文件忽略规则
├── package.json                 # 根 pnpm workspace 身份与 Web 委托命令
├── pnpm-workspace.yaml          # 当前仅包含 apps/web
├── pnpm-lock.yaml               # JavaScript workspace 唯一 lockfile
├── apps/
│   └── web/                     # Next.js App Router 技术骨架
│       ├── src/app/             # 最小首页、layout、全局样式和组件测试
│       ├── package.json         # Web 命令与依赖
│       ├── eslint.config.mjs    # ESLint 配置
│       ├── prettier.config.mjs  # Prettier 配置
│       ├── vitest.config.mts    # Vitest + jsdom 配置
│       └── tsconfig.json        # TypeScript strict 配置
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

`apps/api`、数据库、基础设施和业务模块尚不存在；它们只会在对应任务获得明确批准后创建。

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

要求 Node.js 24 LTS 与 pnpm 11。Windows PowerShell 使用 `.cmd` 入口：

```powershell
pnpm.cmd install
pnpm.cmd web:dev
```

Web 开发服务器默认运行于 `http://localhost:3000`。以下命令已经在 P0-3C 实际验证：

```powershell
pnpm.cmd web:lint
pnpm.cmd web:typecheck
pnpm.cmd web:test
pnpm.cmd web:format:check
pnpm.cmd web:build
```

FastAPI API、数据库和群面业务功能尚未建立，因此当前没有 API、migration 或跨应用启动命令。

## 贡献规则

- 保持任务小而可审查，提交也应小而聚焦。
- 修改前先读取当前阶段、任务、决策和相关领域文档。
- 不越过当前阶段和目标版本边界，不“顺手”实现后续功能。
- 新的产品或技术决策必须先记录到 `docs/DECISIONS.md` 并取得所需批准。
- 任务状态变化同步更新 `docs/TASKS.md`；阶段变化同步更新 `docs/ROADMAP.md`。
- 代码、测试与文档必须保持一致。
- 默认先交付 diff；除非用户明确授权，不自动提交或推送。
