# Group Interview Arena — Agent Working Rules

本文件规定 Codex 及其他开发代理在本仓库中的长期工作方式。它不能覆盖 [`docs/PROJECT_MASTER_PLAN.md`](docs/PROJECT_MASTER_PLAN.md)；该总纲始终是当前最高层产品基线。任何下层决策在与当前总纲冲突时都不得先行生效。

## 1. Project Definition

AI 群面训练场是一个由通用题型引擎、参数化 AI 候选人、受控讨论编排器和证据化评分系统组成的群面能力训练平台。用户无需临时召集真人，即可完成动态无领导小组讨论，并从具体发言证据进入专项训练闭环。

当前开发阶段为 `P0`，当前目标版本为 `V0.1 Internal Validation`。阶段和版本是两套概念，不能混用。

## 2. Product Non-Goals

本项目不是：

- 群面答案生成器；
- 仅提供内容的普通群面题库；
- 多个 Agent 不受控制地自由聊天；
- 录取概率或岗位适配系统；
- 正式面试中的实时提词或隐蔽辅助工具；
- 当前阶段的通用一对一 AI 面试产品；
- 简历制作、职位投递或企业候选人筛选系统。

未经正式产品决策，不得将上述能力作为“顺手功能”加入项目。

## 3. Source of Truth

权威优先级从高到低为：

1. [`docs/PROJECT_MASTER_PLAN.md`](docs/PROJECT_MASTER_PLAN.md)
2. [`docs/DECISIONS.md`](docs/DECISIONS.md) 中状态为 `Accepted` 且已经用户批准的决策
3. [`docs/ROADMAP.md`](docs/ROADMAP.md) 中的当前阶段和版本范围
4. [`docs/TASKS.md`](docs/TASKS.md) 中获准执行的当前任务
5. 对应领域文档
6. 代码和测试所反映的当前实现

`Accepted Decision` 只有在与当前总纲一致，或属于总纲授权范围内的普通技术决策时，才能按上述优先级约束下层工作。它不得静默覆盖总纲中的核心产品决策，也不得造成两个长期并存且互相冲突的 Accepted Source of Truth。

代码不是天然的正确答案。如果代码与上层文档冲突，应停止扩大修改范围，明确报告冲突并回到上层依据判断。

如果新决策意图改变总纲，流程必须是：在 `DECISIONS.md` 记录 `Proposed Decision` → 用户明确批准 → 更新或升级 `PROJECT_MASTER_PLAN.md` 版本 → 新总纲生效 → 再将新产品方向视为最高层正式基线。在新总纲生效前，冲突方向不得实施或被视为已经替代原决策。实现代码不得反向修改产品方向。

## 4. Mandatory Context Before Work

每个任务开始前必须：

1. 检查当前目录、Git 分支和 working tree；
2. 完整读取 `docs/PROJECT_MASTER_PLAN.md`；
3. 读取 `docs/TASKS.md`，确认当前获批任务；
4. 读取 `docs/DECISIONS.md`，确认已有决策和待决策项；
5. 读取 `docs/ROADMAP.md`，区分当前阶段与目标版本；
6. 读取与任务相关的领域文档；
7. 查看现有代码、测试、配置和邻近实现；
8. 确认任务依赖、验收标准、非目标和安全边界。

若发现用户未知的未提交修改可能与任务冲突，立即停止，不覆盖、不清理、不 reset，并向用户报告。

## 5. Scope Control

- 只执行用户明确批准的任务。
- 不因为当前修改方便而顺便开发下一阶段。
- 不因框架默认功能、第三方示例或个人工程偏好扩大产品范围。
- 不因已有代码更容易修改而改变产品决策。
- 不把 `TBD`、`Proposed`、`Recommended` 当成 `Accepted`。
- 不把 P0～P6 的研发阶段与 V0.1/V0.5/V1.0 产品版本混为一谈。
- 发现更好的替代方案时可以提出，但未经决策不得静默采用并改变既定方向。

普通、低风险、可逆且不影响产品边界的工程细节可以在任务范围内自主处理，无需制造无意义的确认流程。

## 6. Decision Rules

遇到以下情况必须停止相关实现并报告：

- 与当前总纲（包括 D-001～D-015）冲突，或发现下层 `Accepted` 决策与总纲互相冲突；
- 引入新的产品方向、用户群、商业模式或版本范围；
- 需要替用户决定尚未解决的 `TBD`；
- 需要加入任务未要求的重型依赖；
- 需要修改 `docs/PROJECT_MASTER_PLAN.md`；
- 发现隐私、安全、合规、数据隔离或反作弊风险；
- 发现用户已有未提交修改可能被覆盖；
- 无法在当前任务验收标准内完成而必须实质扩展范围。

正式决策使用 `docs/DECISIONS.md` 的轻量 ADR 格式记录。只有总纲已确认的产品决策，或不改变总纲且处于授权范围内、经用户明确批准的普通技术 ADR，才可以标记为 `Accepted`。意图改变总纲的产品决策必须先完成总纲版本更新，不能长期以冲突的 `Accepted` 记录覆盖当前总纲。

## 7. Security Rules

- 不提交密钥、令牌、密码、私钥或真实生产配置。
- `.env` 和其他私有环境文件不得进入 Git；`.env.example` 只提供安全占位说明。
- 服务端密钥不得进入前端包、浏览器日志或公开构建产物。
- 不采集、保存或记录实现当前功能不需要的敏感数据。
- 用户数据必须严格隔离；对象存储和管理入口默认采用最小权限。
- 对 Prompt 注入、系统提示泄露和评分规则泄露进行威胁建模。
- 不开发正式面试实时提词、悬浮窗或其他作弊能力。
- 不让用户上传企业保密材料或未经同意的第三方录音。

## 8. Testing Rules

后续每个代码任务必须根据改动范围运行相关检查：

- formatting / lint；
- typecheck；
- unit tests；
- integration tests；
- build；
- migration checks；
- 必要的安全、回归和端到端验证。

具体工具和命令由后续正式技术决策及实际项目配置确定。当前不得虚构尚不存在的命令；无法执行的检查必须在交付报告中明确说明。

## 9. Documentation Rules

- 代码行为变化时同步更新对应领域文档。
- 新的产品或技术决策更新 `docs/DECISIONS.md`。
- 任务状态、范围或验收变化更新 `docs/TASKS.md`。
- 阶段或版本里程碑变化更新 `docs/ROADMAP.md`。
- 复杂跨模块任务按 `docs/exec-plans/README.md` 建立执行计划；简单任务不需要额外文档仪式。
- 领域文档必须区分 `Confirmed`、`Implementation guidance`、`TBD` 和 `Future work`。
- 不复制大段总纲形成第二份模糊权威；摘要必须保留原意并链接来源。

## 10. Task Completion Report

每次任务完成后至少汇报：

- 完成内容；
- 创建和修改的文件；
- 关键实现或治理变化；
- 实际运行的检查/测试命令；
- 检查/测试结果；
- 已知风险和限制；
- 仍存在的 TBD；
- 用户需要手动完成的操作；
- 最终 Git 分支、修改、暂存和提交状态。

不得把未运行的检查描述为已通过，也不得把部分完成描述为全部完成。

## 11. Git Rules

- 默认不自动 `git add`、`git commit` 或 `git push`。
- 不 reset、checkout、clean、stash 或删除用户未知的改动。
- 不删除、覆盖或重命名来源不明的文件。
- 完成任务后先提供 diff 和验证结果供用户审核。
- commit 与 push 是独立步骤，只有用户明确授权时才能执行。
- 不 force-push，不绕过分支保护或其他仓库保护措施。
