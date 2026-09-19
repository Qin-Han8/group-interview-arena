# P1-8-F010 — Demo V2 信息架构与视觉对齐设计规格

- 日期：2026-09-15
- 状态：已批准并完成的设计基线；Task 1–9 已实现并通过用户视觉批准，Task 10、Final Composition Acceptance、后续有界修复与收口复验均已通过
- 阶段：P1-8 交互补救中的前端架构设计检查点
- 适用范围：`apps/web` 的公开入口、认证后应用框架、训练大厅、选题、专注训练工作台、训练报告和设置中心
- 交付性质：设计规格；本检查点不修改产品代码、接口、数据模型或运行时行为

## 1. 目标与成功定义

F010 不是一次局部 CSS 调整，而是把当前真实 P1 用户旅程重新组合为同一套产品框架：

```text
公开入口
  → 登录 / 注册
  → 认证后应用框架
  → 训练大厅
  → 按真实题型分类选题
  → 实时文字讨论工作台
  → 基于公开发言证据的训练报告
```

成功意味着这些页面在导航归属、网格比例、视觉层级、状态反馈和响应式行为上明显属于同一产品；已有认证、题目、会话、WebSocket、恢复与报告契约继续原样承担数据和行为权威。

## 2. 权威边界

### 2.1 Demo V2 可以决定的内容

用户提供的 Demo V2 仅作为以下内容的参考基线：

- 冷灰背景、蓝紫主色、白色 Surface、细边框和柔和阴影组成的视觉语言；
- 认证页的分栏构图；
- 认证后侧栏、顶部 Context Bar 与内容画布组成的应用框架；
- Dashboard / Setup / Report 的 12 列 Bento 组合；
- 讨论页左右支撑、中间主舞台的相对权重；
- 导航分组、信息优先级和窄屏区域切换方式；
- 克制的交互反馈、可见焦点和 reduced-motion 行为。

### 2.2 正式仓库可以决定的内容

以下内容只服从当前 P1 代码和已批准文档：

- 登录、注册、退出和当前用户状态；
- 题目列表、题目详情和实际题型代码；
- 会话创建、恢复、阶段推进、发言、楼层控制和 WebSocket 状态；
- 公开题面、公开讨论状态和公开发言；
- 报告生成、持久化、读取、状态和证据字段；
- 隐私、安全、所有权、错误披露和刷新恢复语义。

Demo 中的 Mock 分数、历史记录、成长、冲刺、场次余额、购买、设备检测、私人立场、Discussion Memory 和训练推荐不得成为正式 UI 的数据来源或行为依据。浏览器本地持久化只允许保存第 18–24 节批准的版本化讨论区宽度偏好；它不得保存或推断任何业务、会话、题目、发言、报告或私人笔记数据。

## 3. 当前真实来源与差异结论

### 3.1 2026-09-15 原始批准基线的前端组成

本表记录 Task 1 开始前的设计输入，用于保留批准历史；Task 1–5 的当前实现状态以第 18 节增补和实施计划为准。

| 当前来源                                           | 当前职责                                                 | F010 目标归属                                                              |
| -------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------- |
| `apps/web/src/app/auth-panel.tsx`                  | 登录状态、登录/注册、退出、当前侧栏与 SessionPanel 容器  | 保留认证所有权；拆出可复用的认证后 Shell 与分组导航；不接管完整会话状态    |
| `apps/web/src/features/sessions/session-panel.tsx` | 题目加载、选题、会话创建、恢复、实时连接和训练状态总编排 | 继续拥有完整权威会话状态；内部重组为大厅、选题和训练工作台三种产品 Surface |
| `discussion-workspace.tsx`                         | 三区域讨论构图与窄屏区域切换                             | 保留交互模型，调整桌面比例和视觉层级，让中间讨论区占主导                   |
| `task-brief-panel.tsx`                             | 公开题面、约束、选项与本地笔记                           | 成为讨论工作台左侧支撑区；补齐真实题型标签映射时只认正式代码               |
| `session-progress-panel.tsx`                       | 阶段和进程                                               | 成为讨论工作台右侧支撑区的一部分                                           |
| `discussion-stage.tsx`                             | 参与者、讨论流、输入和动作                               | 成为中间主舞台；减少工程事件日志观感                                       |
| `report-page-client.tsx` / `report-view.tsx`       | 独立报告路由、GET 读取、报告状态和内容                   | 放入与主流程一致的认证后 Shell；继续由报告 feature 读取与解释报告状态      |
| `report-contract.ts`                               | 报告响应的严格运行时解析                                 | 保持数据权威，不因视觉需要放宽或派生不存在的指标                           |
| `apps/web/src/lib/api/client.ts` 与生成 schema     | 当前公开 API 类型和调用                                  | 实施前字段核对的最终依据，不为填满布局扩展接口                             |
| `apps/web/src/app/globals.css`                     | 全局样式和当前视觉规则                                   | 承载统一 token、Surface、响应式和 reduced-motion 规则                      |

### 3.2 已确认的公开题目契约

`QuestionSummaryResponse` 当前公开字段为：

- `id`
- `question_template_id`
- `version_number`
- `title`
- `question_type`
- `background_domain`
- `difficulty`
- `estimated_minutes`

`QuestionDetailResponse` 在上述字段之外公开：

- `scenario`
- `objective`
- `hard_constraints`
- `soft_constraints`
- `stakeholders`
- `options`

选题列表卡只使用 Summary 字段。被选题目的右侧摘要在现有详情请求成功后才使用 Detail 字段。隐藏参考答案、评价器字段、AI 私人立场、Prompt 和服务商数据均不可进入前端。

V0.1 的真实题型和产品标签冻结为：

| 正式代码              | 产品标签   | 已发布数量 |
| --------------------- | ---------- | ---------: |
| `ORDERING_SELECTION`  | 排序选择型 |          4 |
| `RESOURCE_ALLOCATION` | 资源分配型 |          4 |
| `PLAN_DESIGN`         | 方案策划型 |          4 |

页面从 `listQuestions` 的真实响应分组并计算数量，同时在验收中确认当前发布集合为 3 类共 12 题。不得把 Demo 的 `RANKING`、`PLANNING` 或需求示例中的 `PRIORITIZATION`、`OPEN_DISCUSSION` 当作正式代码。

### 3.3 已确认的会话与报告契约

当前 `SessionSnapshot` 状态集合为：

`CREATED`、`PREPARATION`、`OPENING_STATEMENTS`、`EXPLORATION`、`CONFLICT_AND_EVALUATION`、`CONVERGENCE`、`FINAL_SUMMARY`、`COMPLETED`、`ABORTED_USER`。

报告继续使用现有 owner-only 契约：

- `POST /sessions/{session_id}/report`：对已完成场次执行幂等生成；
- `GET /sessions/{session_id}/report`：读取已持久化报告，刷新页面时不隐式生成；
- 稳定页面路由：`/sessions/{sessionId}/report`；
- 报告状态：`REQUESTED`、`RUNNING`、`COMPLETED`、`FAILED`。

完成态报告当前只允许展示：题目与练习概览、摘要、参与者数量、Human/AI/总发言数、覆盖阶段、最多 3 条优势证据、最多 3 条改进证据、单一优先改进项，以及现有公开来源元数据。

### 3.4 2026-09-15 原始基线与目标架构的差异

以下差异是 Task 1–5 的历史实施依据，不能解读为 2026-09-17 工作树仍未完成这些项目。

1. 当前认证后框架已有 240px 侧栏和 64px 顶栏雏形，但导航是扁平列表，报告入口永久禁用，页面标题固定为“训练大厅”。
2. 当前 `SessionNavigationState` 只有 `loading | lobby | active | terminal`，不能让 Shell 在不读取完整 Snapshot 的前提下区分已完成与用户中止，也没有场次标识。
3. 当前训练大厅仍以单个下拉框选题，未呈现 3 类 12 题的真实分类和卡片选择。
4. 当前完成训练后的报告动作只存在于 SessionPanel 终态区域，侧栏“训练报告”无法触发同一真实流程。
5. 当前报告路由是独立全屏页面，没有复用认证后产品 Shell；报告内容已有局部 Bento，但卡片次序与目标 8/4、6/6 层级不同。
6. Demo 报告的 78 总分、六维分数、行为统计和推荐训练不在 P1-7 契约内，正式设计必须留白或收紧构图，不能补造数据。
7. Demo 讨论区包含 Discussion Memory；当前批准的公开前端契约未暴露该内容，因此正式布局不为它创建数据接口或伪内容。

## 4. 整体页面与路由架构

### 4.1 路由保持

- `/`：未认证时显示公开认证入口；认证后显示产品 Shell，并在同一路由内承载训练大厅、选题和当前会话 Surface。
- `/?session_id={id}`：保留当前会话恢复语义；页面刷新继续从服务端恢复，不改为浏览器本地状态。
- `/sessions/{sessionId}/report`：唯一稳定报告详情路由；刷新后通过现有 GET 重新读取持久化报告。
- `/settings`：认证后的真实设置中心，使用正常 ProductShell；路由遵循当前 `apps/web/src/app/**/page.tsx` 的 Next App Router 约定。

F010 不增加专项训练、题型训练、成长中心、冲刺计划、场次包或历史报告路由。设置中心是 2026-09-17 已批准增补中唯一新增的产品路由。

### 4.2 认证后共享框架

正常认证后页面使用同一 presentational ProductShell；真实非终态训练会话使用第 18 节的专注训练模式，不显示这里的全局侧栏和顶部 Context Bar：

```text
┌──────── 232–240px Sidebar ────────┬──────────── Top Context Bar 64–72px ────────────┐
│ 品牌                               │ 当前页面标题                         用户 / 退出 │
│ Training                           ├──────────────────────────────────────────────────┤
│   完整模拟                         │                                                  │
│   专项训练（即将开放）             │          centered main content canvas            │
│   题型训练（即将开放）             │          max-width 1200–1280px                    │
│ Growth                             │          12-column where appropriate              │
│   成长中心（即将开放）             │                                                  │
│   冲刺计划（即将开放）             │                                                  │
│ Other                              │                                                  │
│   训练报告（真实状态）             │                                                  │
│   场次包（即将开放）               │                                                  │
│   设置（可用）                     │                                                  │
└────────────────────────────────────┴──────────────────────────────────────────────────┘
```

Shell 只负责品牌、分组导航、当前页面标题、用户/退出动作、全局导航请求和内容容器。认证、会话和报告 feature 分别保留自己的数据读取与错误处理所有权。

报告与设置路由复用相同的正常视觉 Shell。它们通过现有 `/auth/me` 获得用户展示与退出能力；报告通过现有 GET 判定内容状态，设置只读取浏览器 UI 偏好和当前认证用户，不建立新的全局用户存储、报告列表或后端设置契约。

### 4.3 导航状态

#### Training

- `完整模拟`：真实入口。无当前会话时聚焦“下一场完整模拟”；终态时请求 SessionPanel 返回大厅；活动会话时保持当前训练，不创建并行场次。
- `专项训练`、`题型训练`：禁用，显示“即将开放”，无 `href`、无点击成功反馈。

#### Growth

- `成长中心`、`冲刺计划`：禁用，显示“即将开放”，无 `href`。

#### Other

- `训练报告`：按第 9 节状态矩阵工作。
- `场次包`：禁用，显示“即将开放”，无 `href`。
- `设置`：真实可用入口，进入 `/settings`；活动专注训练期间正常 ProductShell 被隐藏，因此不在 Session Bar 复制设置快捷入口。

“训练大厅”作为页面上下文标题，不再与“完整模拟”竞争两个同义主导航入口。

## 5. 会话状态所有权

### 5.1 狭窄的导航投影

完整 `SessionSnapshot` 继续留在 SessionPanel。Shell 只接收以下判别联合，名称延续当前 `SessionNavigationState` 约定：

```ts
type SessionNavigationState =
  | {
      sessionId: null;
      status: "loading" | "lobby";
      reportAvailable: false;
    }
  | {
      sessionId: string;
      status: SessionSnapshot["status"];
      reportAvailable: boolean;
    };
```

约束：

- `reportAvailable` 当且仅当 `status === "COMPLETED"` 时为 `true`；
- `ABORTED_USER` 是明确的终态但 `reportAvailable` 必须为 `false`；
- `sessionId` 只来自当前已恢复或已创建的权威 Snapshot；
- Shell 不读取 transcript、question detail、floor、grant、draft、recovery bundle、pending/rejected utterance、WebSocket 或内部运行状态；
- 投影只用于导航可用性、标签和导航请求，不成为会话真相的第二份副本。

### 5.2 全局动作回到 feature

Shell 点击“完整模拟”或“训练报告”时只发出单调递增的请求 token，SessionPanel 对请求进行权威复核：

- 返回大厅请求沿用当前 `returnToLobbyRequest` 模式；
- 报告请求使用同类的 `openCurrentReportRequest`；
- SessionPanel 收到报告请求后再次核对当前 Snapshot 的 `id` 与 `COMPLETED` 状态，再调用现有 `generateReport`，成功后进入稳定报告路由；
- 生成中防重复；失败时在当前 Surface 显示安全错误，Shell 不伪造成功或自行跳转；
- 活动场次或用户中止场次即使发生陈旧点击也不执行报告生成。

这样可以修复全局报告入口，同时不把报告 POST、路由时机或完整会话状态提升到 AuthPanel。

## 6. 公开入口与认证

### 6.1 桌面 1440px

- 主体采用约 7:5 分栏，整体内容限制在约 1180–1240px，垂直居中但允许短视口自然滚动。
- 左栏：品牌、单句价值主张，以及 2–3 条由当前能力支持的短说明，例如“与 3 位 AI 候选人完成文字群面”“体验真实阶段推进与协作收敛”“完成后查看基于公开发言证据的复盘”。
- 右栏：唯一任务卡，包含登录/注册模式切换、用户名、密码、验证/错误、提交/加载。
- API 健康状态只放在卡片底部或页面脚注的低层级诊断文案；不得出现 P1、内部验证底座、实现阶段或技术目标版本等工程叙事。

### 6.2 768px 与 390px

- 768px：收窄为均衡双栏或上下两段，认证卡不得低于可用输入宽度；较长价值说明自动换行。
- 390px：严格单列，品牌/价值说明压缩为短版，认证卡紧随其后；页面允许纵向滚动。
- 输入、模式切换和主按钮占可用宽度；错误信息不引发横向溢出；键盘焦点、错误关联和 loading 文案保持可见。

## 7. 训练大厅与选题

### 7.1 训练大厅 Bento

认证后的默认 Surface 是训练大厅，不再展示为原始会话表单。

桌面首屏采用 12 列：

- 主块 8 列：“下一场完整模拟”，说明用户将与 3 位 AI 候选人进行真实文字讨论，主 CTA 为“开始选题”；
- 辅助块 4 列：“一次训练如何进行”，仅解释阅读题目、参与讨论、完成后查看证据报告；
- 下方可使用 6/6 或 4/4/4 的轻量说明块，但每块都只能陈述当前真实能力。

未选择题目前不显示估算时长；选择后才从该题真实 `estimated_minutes` 展示。大厅不显示剩余场次、连续天数、进度、分数、最近训练或历史报告。

### 7.2 分类与卡片

点击“开始选题”进入同一主流程内的选题 Surface，并聚焦真实题型切换控件。

- 顶部是 3 个题型 tab / segmented control，标签使用第 3.2 节映射，数量由真实列表即时计算；
- 所有 12 道已发布题目必须可通过三组访问，不能只展示当前下拉框默认项；
- 桌面主体为 8 列题目区 + 4 列选择摘要；题目区通常为两列卡片；
- 题目卡只显示 Summary 字段中有产品价值的内容：标题、产品题型标签、难度、预计分钟数、背景领域和必要时的版本号；内部 UUID 不作为可见主信息；
- 整张卡片是可点击的 radio 选择目标，具备真实 `radio` 语义、可见标签、方向键或 Tab/Space 键操作和 `focus-visible`；
- 选中态同时使用边框、背景和勾选/“已选择”文字，不只靠颜色；
- 右侧摘要只在详情加载成功后显示 objective、hard constraints，以及创建会话所需的确认信息；不得从列表摘要猜测详情；
- 详情加载、失败和创建中各有局部状态，已选题不会因错误悄然改变；
- 主按钮为“创建并进入训练”，继续调用现有 create-session 流程。

## 8. 实时讨论工作台

### 8.1 桌面构图

真实非终态会话进入专注训练模式并使用整个 viewport；正常 ProductShell 的侧栏、顶部 Context Bar 和全局导航不显示。专注 Session Bar 保持紧凑，只呈现当前题目、阶段、倒计时、连接状态，以及现有能力已经支持的结束训练动作。

在可用内容宽度足够时使用可调整宽度的三区域工作台：

| 区域     |              目标宽度 | 内容与边界                                                                                  |
| -------- | --------------------: | ------------------------------------------------------------------------------------------- |
| 左支撑   | 默认 280px；220–420px | 公开题面、objective、公开约束/选项、本地私人笔记；笔记不发送到 API                          |
| 中主舞台 |  `minmax(520px, 1fr)` | 参与者条、当前发言者、真实 transcript、AI 局部准备状态、composer、pending/rejected/recovery |
| 右支撑   | 默认 280px；220–380px | 阶段进程、倒计时、当前 floor/讨论状态，以及契约已经公开的结构化状态                         |

中间区必须在面积、对比和交互密度上明显占主导。Transcript 使用会议记录式信息层级：发言者优先、时间弱化、消息边界克制；不渲染原始事件类型、内部序列调试信息或巨型运行状态横幅。

AI preparing 只附着在对应参与者 tile 上，使用紧凑文字/指示器。恢复、待发送和拒绝状态继续使用当前真实逻辑，并以局部、可理解的状态呈现。

当前没有公开 Discussion Memory 时，右栏不渲染该模块；不使用占位卡抢占空间，也不新增隐私敏感接口。未来只有在独立批准并具备公开契约后才可加入。

### 8.2 Tablet 与 Mobile

- 768×1024：继续使用已批准的“讨论 / 题目 / 进程”切换模型，中间讨论为默认区域；不并排挤压三栏。
- 390×844：专注训练满屏、单 Surface 满宽，紧凑顶部区域切换；composer 保持可达，软键盘出现时不遮住提交和错误；正常产品导航不得占据讨论空间。
- 区域切换保留各自滚动位置和草稿，不重建实时连接；移动端可以提示桌面体验更佳，但所有当前关键动作仍可操作。
- 当可用宽度无法同时满足左 220px、中 520px、右 220px、两个分隔条及必要间距时，直接回落到现有支撑面板切换模型；不得压缩桌面三栏。桌面宽度偏好在 tablet/mobile 下忽略但不清除。

## 9. 训练报告与全局入口

### 9.1 报告导航状态矩阵

| 当前状态                         | 训练报告入口                           | 点击结果                                              |
| -------------------------------- | -------------------------------------- | ----------------------------------------------------- |
| 初次发现中                       | 禁用，显示“正在确认训练状态”           | 无请求                                                |
| 大厅 / 无当前完成场次            | 禁用，显示“完成训练后可查看报告”       | 无请求                                                |
| `CREATED` 至 `FINAL_SUMMARY`     | 禁用，显示“完成当前训练后可查看”       | 无请求                                                |
| `ABORTED_USER`                   | 禁用，显示“本次训练未完成，无训练报告” | 无请求                                                |
| `COMPLETED`                      | 启用，显示“生成 / 查看本次训练报告”    | 由 SessionPanel 执行现有 POST，成功后进入稳定报告路由 |
| 报告路由 `REQUESTED` / `RUNNING` | 导航保持当前选中                       | 页面展示真实生成状态和刷新提示                        |
| 报告路由 `COMPLETED`             | 导航保持当前选中                       | 页面展示持久化内容，刷新使用 GET 重读                 |
| 报告路由 `FAILED`                | 导航保持当前选中                       | 安全错误、重新读取和返回训练大厅；不披露后端内部细节  |

当前没有用户级历史报告列表。侧栏入口只代表“当前已完成场次的报告”，不创建报告中心、历史列表、本地缓存或从浏览器状态推断历史。

### 9.2 完成报告的 Bento 构图

报告页在共享 Shell 的主画布中使用 12 列：

- 顶部概览 8 列：题目标题、objective、summary、参与者数、Human/AI/总发言数、覆盖阶段；
- 顶部优先改进 4 列：`priority_improvement`，作为唯一高强调行动提示；
- 下方优势 6 列：最多 3 条真实 strength evidence；
- 下方改进 6 列：最多 3 条真实 improvement evidence；
- 来源详情保持低优先级，可展开显示公开 phase、event sequence、participant/utterance id、confidence 和版本元数据。

证据卡展示原始公开 quote 与 interpretation，不把事件序号包装成音频时间跳转。数组为空时使用坦诚的空状态，允许卡片高度不对称，不用假指标填补空间。

`REQUESTED`、`RUNNING`、`FAILED`、401、404、配置失败和解析失败均在同一视觉框架内显示短小状态 Surface，并提供实际可执行的“返回训练大厅”或“重新读取”动作；页面不得渲染空白或返回 `null`。

## 10. 响应式组合

| Viewport | Shell                                                       | Dashboard / Setup / Report / Settings                            | Discussion                                            |
| -------- | ----------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------- |
| 1440×900 | 正常页面为 232–240px 左侧栏、64–72px 顶栏；活动训练隐藏二者 | 12 列；大厅 8/4；选题 8/4；报告 8/4 + 6/6；设置内容约 900–1000px | 专注满屏；默认 280 / `minmax(520, 1fr)` / 280，可拖动 |
| 768×1024 | 正常页面使用 compact nav；活动训练仅保留紧凑 Session Bar    | 1–2 列；选题与报告按优先级堆叠；设置使用紧凑 section switcher    | “讨论 / 题目 / 进程”切换，默认讨论，不应用桌面宽度    |
| 390×844  | 正常页面为单列紧凑导航；活动训练不显示全局导航              | 单列；卡片不横向溢出；设置 section switcher 和内容可达           | 专注满屏单 Surface 切换；composer 和错误始终可达      |

宽屏不会让内容无限拉伸；窄屏不会靠缩小字体或把三个区域硬塞进一行解决布局。页面和局部滚动容器职责明确，任何 viewport 都不得出现整体横向滚动条。

## 11. 视觉系统

### 11.1 基础规则

- 页面背景：低饱和冷灰；仅公开入口或大厅的大面积空白可使用一次极淡蓝紫 mesh。
- Primary：克制靛蓝/蓝紫，用于主按钮、当前项、选择和焦点；不在大面积卡片中铺满。
- Surface：白色或接近白色；1px 冷灰边框；常态阴影弱，重点 Surface 使用柔和中等阴影。
- 圆角：控件 8px，标准卡 10px，重点复合容器 12px；pill 只用于状态和短标签。
- 字体：认证后标题紧凑，页面标题约 24–32px，卡片标题约 16–22px，正文约 14–16px；不使用认证后巨型营销标题。
- 间距：采用稳定的 4/8px 节奏，画布留白明显但不形成空洞卡片墙。
- 动效：状态反馈 120–220ms；不使用弹跳、外发光或复杂位移；`prefers-reduced-motion` 下移除非必要移动。

### 11.2 组件状态

- Button、Card、Input、Tabs、Nav Item、Badge、Skeleton、Empty/Error State 使用统一 hover、pressed、disabled 和 focus-visible 语言。
- disabled 入口同时有视觉弱化、原生禁用语义和说明文案，不只降低透明度。
- 成功、警告和错误使用低饱和语义色；错误不依赖颜色，必须有文字。
- 交互卡保持完整点击目标，但内部不能嵌套冲突按钮；最小触控目标约 44px。
- 图标使用现有图标方案或轻量内联 SVG，不使用 Emoji 代替产品图标。

## 12. 可访问性与状态真实性

- 登录字段保留正确 `autocomplete`、label、required 和错误关联。
- 题型切换使用 tabs 或等价的单选分组语义；题目卡使用 radio 语义和键盘操作。
- 侧栏当前项使用 `aria-current`；禁用未来模块不可聚焦为虚假链接。
- 状态变化使用适量 `aria-live`，不让倒计时或 transcript 高频打断读屏。
- 讨论区域切换可由键盘操作，焦点不会因切换或实时更新丢失。
- 桌面宽度分隔条使用垂直 separator 语义、当前值/最小值/最大值和可见焦点；方向键以 16px 调整，Shift+方向键以 40px 调整。
- Transcript 自动跟随继续服从用户滚动意图；恢复和重连不改变原有数据语义。
- 公开 UI 不显示私人立场、隐藏冲突、内部 Prompt、服务商响应、敏感日志或未经批准的 Memory。
- 所有空状态与错误状态描述真实后端状态，不制造成功、历史或可用额度。

## 13. 实施前必须再次核对的真实契约

后续获批实施开始时，以当时工作树为准重新核对以下现有来源；核对用于防止字段漂移，不构成扩展接口的许可：

1. `generated/schema.d.ts` 中的 `QuestionSummaryResponse`、`QuestionDetailResponse`、`SessionSnapshotResponse`、`SessionStatus` 和报告响应；
2. `client.ts` 中 `listQuestions`、`getQuestion`、`createSession`、`generateReport`、`getReport`、`getCurrentUser` 和 `logoutUser`；
3. `report-contract.ts` 的严格字段白名单、报告状态和证据数量限制；
4. SessionPanel 当前 URL 恢复、终态、报告生成和请求防重复逻辑；
5. DiscussionWorkspace 当前 responsive tabs、草稿、pending/rejected/recovery 和 WebSocket 生命周期；
6. V0.1 内容清单中 4/4/4 的真实题型分布与 12 个已发布 Question Version。
7. `SessionStatus` 的真实联合与 `isTerminalStatus` 判定，确认专注模式只覆盖已存在的非终态。
8. 当前 `min-[1200px]` 三区域断点、`讨论 / 题目 / 进程` 切换和 `prefers-reduced-motion` 全局规则。
9. 当前私人笔记仅为 SessionPanel 页面内 React 状态、带 `data-private-notes="memory-only"`，不会持久化或发送到 API。

任何视觉字段若不在当时公开契约中，直接省略；不修改 API、OpenAPI、数据库或后端仅为填充界面。

## 14. 后续可能受影响的现有文件与测试面

设计预期后续实施主要触及：

- `apps/web/src/app/auth-panel.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/src/features/sessions/session-panel.tsx`
- `apps/web/src/features/sessions/discussion-workspace.tsx`
- `apps/web/src/features/sessions/discussion-stage.tsx`
- `apps/web/src/features/sessions/task-brief-panel.tsx`
- `apps/web/src/features/sessions/session-progress-panel.tsx`
- `apps/web/src/features/reports/report-page-client.tsx`
- `apps/web/src/features/reports/report-view.tsx`
- `apps/web/src/app/settings/page.tsx`
- `apps/web/src/features/settings/settings-page-client.tsx`
- 共享的训练工作台布局偏好 helper（仅供 discussion workspace 与 settings 使用）
- 对应的 `*.test.tsx`、`apps/web/e2e/auth.spec.ts`、`apps/web/e2e/session.spec.ts` 和报告 E2E 覆盖

若共享 Shell 拆分为新 presentational component，其职责只能是布局、导航呈现和窄状态投影；不得成为新的会话、报告或认证数据仓库。实际文件组织在实施检查点中依据当时源码决定。

## 15. 视觉 QA 与验收

视觉验收不能由 DOM 测试替代。实施后必须在相同 viewport 分别截取正式前端与 Demo V2 参考，并逐页比较构图、留白、层级、比例和导航。

### 15.1 必验 viewport

- Desktop：1440×900
- Tablet：768×1024
- Mobile：390×844

### 15.2 必验 Surface

1. 登录与注册，包括错误和提交中；
2. 训练大厅；
3. 分类选题与已选摘要；
4. 活动讨论，包括 AI preparing、pending/rejected 或 recovery 的真实可触发状态；
5. 完成态报告，以及 `REQUESTED` / `RUNNING` / `FAILED` 中可由真实契约产生的状态。
6. 专注训练的默认宽度、自定义左右宽度、键盘调整、窄屏回落和刷新/新场次持久化；
7. 设置中心桌面、tablet 和 mobile，以及恢复默认布局后的真实状态。

### 15.3 比较记录

每个 Surface / viewport 记录：

- Shell 是否一致、主内容是否居中且不过宽；
- 主次区域面积是否符合本规格；
- 中间讨论是否明确占主导；
- 留白与信息密度是否接近 Demo V2 的克制感；
- 导航状态是否真实且未来项确实不可操作；
- 是否存在横向溢出、遮挡、不可见焦点或软键盘阻塞；
- 是否出现本规格禁止的 Mock 内容或工程状态文案；
- material mismatch 的截图、原因和修正结果。

目标不是逐像素复制，而是让正式页面可辨认地使用同一视觉系统和信息架构，同时完全保留 P1 的真实行为。

### 15.4 功能回归门

视觉实现仍需通过与改动风险相称的 formatting、lint、typecheck、unit、build 和 E2E。特别确认：

- 390 / 768 / 1440 登录注册工作且无横向溢出；
- 3 类 12 题全部可访问，数量真实，键盘选择可用；
- 讨论的恢复、重连、楼层、发言、pending/rejected 状态未改变；
- 完成场次可从全局入口执行真实 POST 并进入稳定报告路由；
- 报告刷新只执行 GET，内容只来自当前 P1-7 契约；
- reduced-motion、生效的禁用语义和 focus-visible 得到浏览器验证。
- 专注训练期间 ProductShell 确实隐藏，终态恢复正常产品框架，且 SessionPanel/实时连接不因视觉模式切换被重建；
- 布局偏好只写入获准 key，损坏/不支持版本/存储异常安全回退，tablet/mobile 不受桌面值影响；
- 设置恢复默认只影响下一次挂载的训练工作台，不宣称跨页面修改已挂载的隐藏工作台。

## 16. 明确非目标

F010 不包括：

- API、OpenAPI、数据库、迁移、后端行为或新依赖；
- 用户级历史报告列表或历史报告中心；
- 浏览器本地存储伪造的报告、进度或业务状态；除版本化左右栏宽度外不保存任何训练数据；
- 专项训练、题型训练、成长中心、冲刺计划或场次包的独立页面；
- 购买、余额、付费、设备检测或通知中心；
- 总分、六维分数、雷达、排名、录取概率、岗位匹配或成长趋势；
- 由 Demo Mock 驱动的行为统计、训练推荐、最近训练或成功态；
- 音频时间跳转、ASR、TTS 或语音入口；
- P2/P3 能力、正式评分、招聘决策或实时提词；
- 新的公开 Discussion Memory、私人立场、隐藏冲突或 Prompt 可见性；
- 改变现有会话、WebSocket、恢复、报告生成和 owner-only 权限语义。

## 17. 设计自审结论

| 审查项         | 结论                                                                                                             |
| -------------- | ---------------------------------------------------------------------------------------------------------------- |
| 内部一致性     | 路由、状态所有权、Shell 和页面构图使用同一边界；报告生成仍由 SessionPanel 发起，报告读取仍由 report feature 负责 |
| 需求覆盖       | 认证、Shell、大厅、分类选题、讨论、报告、全局报告入口、未来模块、响应式和视觉 QA 均已冻结                        |
| P2/P3 越界     | 未加入语音、正式评分、专项训练实现、成长或商业能力                                                               |
| Mock 泄漏      | Demo 的分数、历史、余额、进度、设备、推荐和购买均被明确排除                                                      |
| 隐私边界       | 未暴露私人立场、隐藏字段、Prompt、服务商数据或未公开 Memory；本地笔记保持不发送                                  |
| API 扩展       | 所有卡片和报告区块均可由现有公开契约组成；缺失字段一律省略                                                       |
| 报告所有权     | Shell 只发导航请求；SessionPanel 复核完成态并执行 POST；稳定报告路由通过 GET 读取和解释报告状态                  |
| 设置与偏好     | 仅新增真实 `/settings` 与浏览器本地布局偏好；无后端设置 API、账户同步、假开关或业务状态持久化                    |
| 待批准产品决策 | 本设计范围内没有未决产品选择；任何未来模块页面或接口扩展都需要独立明确批准                                       |

## 18. 2026-09-17 已批准增补：ProductShell 与专注训练生命周期

本节及第 19–24 节修订第 4、8、10、14–17 节中关于活动训练、设置和本地持久化的旧边界；未被明确修订的 Task 1–5 设计继续有效。

### 18.1 精确模式判定

模式只使用现有 `SessionSnapshot["status"]`，不发明后端状态：

| 真实状态                        | 视觉模式          | 说明                                                             |
| ------------------------------- | ----------------- | ---------------------------------------------------------------- |
| 无 Snapshot、`loading`、`lobby` | 正常 ProductShell | 登录后的大厅与选题继续使用全局导航                               |
| `CREATED`                       | Focused Training  | 已进入真实会话，即使尚未开始阶段，也隐藏正常 ProductShell chrome |
| `PREPARATION`                   | Focused Training  | 专注训练                                                         |
| `OPENING_STATEMENTS`            | Focused Training  | 专注训练                                                         |
| `EXPLORATION`                   | Focused Training  | 专注训练                                                         |
| `CONFLICT_AND_EVALUATION`       | Focused Training  | 专注训练                                                         |
| `CONVERGENCE`                   | Focused Training  | 专注训练                                                         |
| `FINAL_SUMMARY`                 | Focused Training  | 专注训练                                                         |
| `COMPLETED`                     | 正常 ProductShell | 离开专注模式，保留真实报告生成/查看流程                          |
| `ABORTED_USER`                  | 正常 ProductShell | 离开专注模式并按现有返回训练流程处理，不提供报告                 |
| 报告路由、设置路由              | 正常 ProductShell | 永不使用专注训练 chrome                                          |

`SessionPanel` 继续拥有完整 Snapshot、URL 恢复、REST hydration、WebSocket、scheduler、transcript、floor、draft 与 report intent 复核。上层只消费现有窄 `SessionNavigationState` 的 `status` 来选择视觉框架；不得提升完整 Snapshot。框架切换必须保持 SessionPanel 内容宿主稳定，不能因隐藏/恢复 chrome 重建会话 feature、重复连接 WebSocket 或丢失草稿。

结合当前源码模式，`FocusedTrainingShell` 是一个视觉职责而不是第二个会话容器：现有 `AuthenticatedAppShell` 增加 `product | focused-training` presentation mode 并保持同一个内容宿主；现有 `DiscussionWorkspace` 与 `SessionHeader` 提供专注 Session Bar 和三区域内容。这样既让正常 ProductShell chrome 真正不渲染，也避免创建会重挂 SessionPanel 的平行 Shell/路由。

### 18.2 Focused Training 构图

Focused Training 使用整个可用 viewport：

```text
┌────────────────────────────────────────────────────────────┐
│ Session Bar：题目 / 阶段 / 倒计时 / 连接 / 结束训练       │
├───────────────┬───────────────────────────┬────────────────┤
│ 题目与思考    │ 实时讨论                  │ 训练进程       │
│               │                           │                │
└───────────────┴───────────────────────────┴────────────────┘
```

Session Bar 不显示全局训练大厅标题、成长、报告、场次包、设置或未来模块，也不增加 Host 控制。可见信息只来自当前公开会话/题目状态；AI preparing 仍保持 participant-local，不升级为全宽横幅。

## 19. 可调整桌面工作台

### 19.1 宽度模型与回落

- 默认：左 280px、中心自适应且占主导、右 280px。
- 左栏硬边界：220–420px。
- 右栏硬边界：220–380px。
- 中心实用最小宽度：520px。
- 两个垂直分隔条分别只调整对应支撑栏，中心消费剩余宽度。
- 实际可用宽度还需扣除两个 handle、grid gap 和容器 padding；拖动上限必须动态保护中心 520px。
- 当当前 viewport 无法同时容纳左/中/右最小值及结构开销时，复用现有 `min-[1200px]` 以下的 tablet/mobile 支撑面板切换；不建立第二套相互冲突的断点系统，也不把三栏硬挤在一行。

### 19.2 Pointer 与键盘

- handle 使用 Pointer Events 和 pointer capture，拖动时即时更新布局；pointer up 后自动持久化，无 Save 按钮。
- 默认 divider 轻量，hover、focus-visible 和 dragging 状态增强；交互期间使用 resize cursor。
- handle 使用适用的 `role="separator"`、`aria-orientation="vertical"`、`aria-valuemin`、`aria-valuemax`、`aria-valuenow` 和可理解的名称。
- `ArrowLeft` / `ArrowRight` 每次调整 16px；加 `Shift` 时调整 40px。左右 handle 的方向值都以屏幕横轴和自身控制的栏宽为准，并经过硬边界与中心最小宽度约束。
- tablet/mobile 不渲染可交互分隔条，不把桌面存储值转化为窄屏内联宽度。

## 20. 浏览器本地布局偏好

### 20.1 唯一允许的存储

冻结 key：`gia.training.workspace.layout`。

版本 1 的完整 JSON 形状为：

```ts
type TrainingWorkspaceLayoutPreferenceV1 = {
  version: 1;
  leftWidth: number;
  rightWidth: number;
};
```

不得向该对象或同类 key 写入用户 ID、会话 ID、题目、transcript、参与者、报告、私人笔记、阶段或任何业务状态。

### 20.2 读取、写入和失败语义

桌面工作台挂载时：

1. 在浏览器 effect/事件中安全读取，SSR/module evaluation 不访问 `window`；
2. 捕获 `getItem`、JSON parse 和 storage security/quota 错误；
3. 只接受普通对象、`version === 1`、有限数值，并要求左右宽度各自在批准硬边界内；
4. 任一字段损坏、缺失、版本不支持或数值越界时，整条记录无效并回退 280/280；
5. 合法记录只在桌面三区域模式应用；当前 viewport 的中心保护仍优先；
6. pointer 调整完成和每次键盘调整后自动写入完整 v1 对象；写入失败只失去持久化，不阻断训练。

恢复默认布局只删除该 key，并立即把设置页状态显示为“默认布局”。它保证下一次挂载的训练工作台使用 280 / flexible / 280；由于设置页与活动训练互斥且不要求跨页同步，不宣称修改已经挂载的隐藏工作台，也不增加 storage event、跨 tab 或全局同步。

## 21. 真实设置中心

### 21.1 路由与所有权

- 路由冻结为 `/settings`，实现位置遵循当前 App Router：`apps/web/src/app/settings/page.tsx`，route-level client 位于 `apps/web/src/features/settings/`。
- 页面使用正常 authenticated ProductShell，导航当前项为“设置”；认证 bootstrap、用户名和退出复用现有 `getCurrentUser` / `logoutUser` 流程。
- Settings 不读取 SessionSnapshot、不增加后端设置 API、数据库表、全局状态框架或第三方 resizable dependency。
- 活动训练不显示正常全局导航，也不在 Session Bar 增加设置捷径。

### 21.2 信息架构

桌面内容最大宽度约 900–1000px，左侧/上方类别导航包含：

1. `训练界面`
2. `账户与会话`
3. `隐私与数据`
4. `更多设置`

tablet/mobile 使用与现有视觉系统一致的紧凑 section switcher/tabs；不为这一页构建通用设置框架。

`训练界面`：

- 显示“默认布局”或“自定义浏览器布局”的真实状态；可选的比例预览只能是非交互且由真实宽度计算。
- 解释左右栏宽只保存在本浏览器、不跨设备同步。
- 唯一真实动作是“恢复默认布局”；默认时保持诚实禁用或说明状态，不伪造成功。
- reduced motion 只说明界面服从操作系统/浏览器 `prefers-reduced-motion`；不创建应用开关。

`账户与会话`：

- 显示现有认证用户返回的 username。
- 提供现有真实 logout 动作。
- 不显示 email、电话、头像、订阅、密码修改或账户删除。

`隐私与数据`：

- 说明公开会话/讨论数据用于当前恢复与报告生成，不扩大既有隐私承诺。
- 说明工作台左右栏宽是唯一浏览器本地偏好。
- 说明当前私人笔记只存在于已挂载页面的内存状态，不发送到 API、不写入 localStorage，刷新后消失。
- 不提供下载全部数据、删除账户、清空云端历史或假隐私开关。

`更多设置`：

- 仅以克制文本说明声音与设备、训练偏好、通知等属于后续版本。
- 不渲染看似可操作的 switch、保存按钮或 mock success。

## 22. 更新后的 ProductShell 可用性

| 分组     | 入口     | 状态                              |
| -------- | -------- | --------------------------------- |
| Training | 完整模拟 | 可用                              |
| Training | 专项训练 | 即将开放                          |
| Training | 题型训练 | 即将开放                          |
| Growth   | 成长中心 | 即将开放                          |
| Growth   | 冲刺计划 | 即将开放                          |
| Other    | 训练报告 | 按第 9.1 节真实会话状态有条件可用 |
| Other    | 场次包   | 即将开放                          |
| Other    | 设置     | 可用，进入 `/settings`            |

正常 ProductShell 承担上述全局导航；Focused Training 只承担正在进行的会话上下文，两者不得同时在视觉上出现。

## 23. 增补的非目标与隐私边界

本增补不批准：

- 后端 settings API、数据库设置表或账户/设备云同步；
- SessionSnapshot、scheduler、recovery、WebSocket 或报告契约变更；
- Redux/全局业务状态或第三方 resizable-panel 依赖；
- 把会话、题目、transcript、报告、参与者或私人笔记写入浏览器存储；
- 跨 tab、跨路由或已挂载工作台的即时布局同步；
- 布局预设、命名方案、紧凑/专业模式或 Save 按钮；
- 设置中的假账户、假隐私、声音、设备、通知或 P2/P3 控件；
- Focused Training 中的全局产品导航、Host 控制、成长、报告或设置快捷入口。

## 24. 分阶段视觉批准与设计自审

新增 Surface 不得等到最终矩阵才首次查看：

- Task 6 后必须提交 desktop focused training、AI-preparing focused training、mobile focused training，并硬停止等待用户批准。
- Task 7 后必须提交默认宽度、左扩展、右扩展、min/max clamp、键盘调整和 reload/新场次持久化证据，并硬停止等待用户批准。
- Task 8 后必须提交 settings desktop、tablet、mobile，并硬停止等待用户批准。
- Task 9 才统一收敛响应式、accessibility 和 scroll；Task 10 是全部旧/新 Surface 的最终矩阵与真实流程回归，不是首次视觉检查。

本增补自审结论：

- ProductShell 与 Focused Training 的状态集合互斥且穷尽当前真实状态；
- 完整 Snapshot 没有被提升，SessionPanel 权威不变；
- localStorage 只有版本化左右栏宽度，不含会话或私人数据；
- reset 对下一次工作台挂载生效，不虚构已挂载工作台同步；
- 宽度不可满足时明确回退现有支撑面板切换；
- 设置只暴露真实 username/logout、布局 reset 与信息性内容；
- 无后端设置 API、无 P2/P3 泄漏、无未决设计占位。

本规格仍是 F010 的设计边界。Task 1–9 已获得用户视觉批准；Task 10 已于 2026-09-18 完成最终矩阵与真实流程实现验证；随后 Final Composition Acceptance、唯一 Pyright blocker 修复/复验和注册密码策略 Option B 修复/收口复验均通过。2026-09-19 用户授权正式状态收口，F010 随 P1-8 转为 `DONE / CLOSED`。P1-7E 后续完成 composition/independent acceptance，P1 phase-close assessment/re-assessment 也已通过；P1 为 `DONE / CLOSED`。
