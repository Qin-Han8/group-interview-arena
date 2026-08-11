# Exec Plans

本目录用于复杂、跨多个模块、预计持续多个 Codex 工作轮次的任务执行计划。简单、局部、单轮可完成的任务不需要创建计划文件，避免文档仪式替代实际工作。

## 何时创建

符合以下一项或多项时，可以建立 exec plan：

- 横跨多个模块或领域文档；
- 有多个相互依赖的实现阶段；
- 预计跨多个 Codex 工作轮次；
- 存在重要迁移、兼容、安全或回滚风险；
- 需要记录长时间执行进度和中间决策。

## 命名

```text
docs/exec-plans/<TASK_ID>_<NAME>.md
```

示例仅表示命名方式，不表示任务已经存在：

```text
docs/exec-plans/P0-4_database-foundation.md
```

## 必需内容

每份执行计划至少包含：

- `Goal`：计划要达成的可验证结果；
- `Context`：相关总纲、决策、任务和现有实现；
- `Scope`：本计划包含的工作；
- `Non-goals`：明确排除项；
- `Dependencies`：前置任务、决策和外部条件；
- `Implementation steps`：按依赖排序的实施步骤；
- `Validation`：测试、检查和验收证据；
- `Decisions`：已确认决策及计划中发现的待决策问题；
- `Risks`：技术、产品、数据和交付风险；
- `Progress`：已完成、进行中、阻塞和下一步。

## 规则

- 先读取 [`../PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)、[`../../AGENTS.md`](../../AGENTS.md)、[`../TASKS.md`](../TASKS.md) 和 [`../DECISIONS.md`](../DECISIONS.md)。
- 执行计划不能自行扩大 `TASKS.md` 中批准的范围。
- 新的正式决策必须进入 `DECISIONS.md`，不能只埋在计划正文中。
- 计划进度必须反映事实，不得把未验证步骤标成完成。
- 计划结束后保留作为审计记录；任务状态以 `TASKS.md` 为准。

P0-1 不额外建立单独 exec plan，因为本次执行说明已经给出完整范围、步骤和验收标准。
