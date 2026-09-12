"""Immutable candidate content catalog for the V0.1 internal-validation set."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from group_interview_arena_api.modules.question_personas.domain import (
    ConstraintItem,
    InternalTextItem,
    PersonaAssignmentDefinition,
    PhasePromptSet,
    PriorityDimension,
    PrivateStanceDefinition,
    PublishedQuestionBundle,
    QuestionOption,
    QuestionVersionContent,
    ReferenceDimension,
    StakeholderItem,
)

_CONTENT_TIME = datetime(2026, 9, 12, tzinfo=UTC)
_PERSONA_IDS = tuple(
    UUID(f"10000000-0000-4000-8000-{index:012d}") for index in range(1, 5)
)


@dataclass(frozen=True)
class _QuestionSpec:
    code: str
    title: str
    question_type: str
    scenario: str
    objective: str
    hard_constraint: str
    major_tradeoff: str
    options: tuple[tuple[str, str], ...]


_SPECS = (
    _QuestionSpec(
        "EMERGENCY_SUPPLY_PRIORITY",
        "暴雨临时安置点物资优先序",
        "ORDERING_SELECTION",
        "连续暴雨后，临时安置点将在六小时内接收不同年龄和健康状况的居民。首批运输能力有限，团队需确定五类物资的进场优先顺序。",
        "给出完整排序、排序准则及在信息变化时可调整的触发条件。",
        "首批车辆只能装载五类物资中的三类，且饮用水必须进入首批。",
        "即时生存保障与后续医疗、秩序和特殊人群需求之间需要取舍。",
        (
            ("A", "饮用水"),
            ("B", "常用药与急救包"),
            ("C", "折叠床和保温毯"),
            ("D", "照明与充电设备"),
            ("E", "婴幼儿与老人用品"),
        ),
    ),
    _QuestionSpec(
        "MUSEUM_RECOVERY_ORDER",
        "城市博物馆藏品抢救优先序",
        "ORDERING_SELECTION",
        "博物馆库房轻度进水，五组藏品的材质、数量、受损窗口和移动条件各不相同。修复团队在前四小时只能处理三组，需依据题面事实形成公开可解释的抢救顺序。",
        "形成五组藏品的完整处理顺序，并说明价值、不可逆损害和操作可行性的权衡。",
        "任何处理不得移动被鉴定为结构不稳定的大型石刻。",
        "文化价值、损害不可逆性、公众承诺与有限修复能力并不完全一致。",
        (
            ("A", "潮湿纸本文献"),
            ("B", "木质民俗器物"),
            ("C", "近代摄影底片"),
            ("D", "大型石刻"),
            ("E", "已预约展出的陶瓷组"),
        ),
    ),
    _QuestionSpec(
        "CAMPUS_SERVICE_RESTART",
        "校园服务恢复优先序",
        "ORDERING_SELECTION",
        "校园核心系统故障后，技术团队预计每两小时只能恢复一项服务。学生正处于选课与考试周交叠阶段，需要决定恢复顺序。",
        "给出五项服务的恢复排序、共同判断标准和面向受影响群体的解释。",
        "身份认证服务必须先于任何依赖统一登录的服务恢复。",
        "覆盖人数、时间敏感性、学习连续性和恢复依赖关系会导向不同顺序。",
        (
            ("A", "统一身份认证"),
            ("B", "在线考试平台"),
            ("C", "选课系统"),
            ("D", "图书馆远程资源"),
            ("E", "校园活动报名"),
        ),
    ),
    _QuestionSpec(
        "CUSTOMER_ISSUE_TRIAGE",
        "共享出行客诉处理优先序",
        "ORDERING_SELECTION",
        "共享出行平台在系统升级后同时收到五类集中投诉。客服、运营和技术资源只能并行处理两类问题，团队需确定整体响应顺序。",
        "形成完整处理优先序，并明确安全、影响范围、可逆性和承诺时效的判断标准。",
        "涉及人身安全的投诉必须立即进入首批处理。",
        "单个高风险事件与大规模低风险影响、短期补偿和根因修复之间存在张力。",
        (
            ("A", "车辆制动异常"),
            ("B", "重复扣费"),
            ("C", "定位漂移"),
            ("D", "月卡权益未到账"),
            ("E", "偏远区域无车可用"),
        ),
    ),
    _QuestionSpec(
        "RURAL_CLINIC_ALLOCATION",
        "乡镇巡诊资源配置",
        "RESOURCE_ALLOCATION",
        "一支巡诊团队可在一个月内投入120个服务单元：河谷镇有480名到期慢病复诊者且距基地30分钟；山岭镇有260名待筛查儿童，往返交通需4小时；湖滨镇覆盖12个偏远村、约900名居民，近期健康教育触达率仅35%。",
        "给出可核算的资源分配，并说明公平、健康风险和持续服务之间的取舍。",
        "三个乡镇都必须获得至少20个服务单元，且总量不得超过120。",
        "高风险人群深度服务、地域公平与预防性覆盖无法同时最大化。",
        (
            ("A", "慢病复诊"),
            ("B", "儿童筛查"),
            ("C", "健康教育"),
            ("D", "跨村交通保障"),
        ),
    ),
    _QuestionSpec(
        "YOUTH_PROGRAM_BUDGET",
        "青少年公益项目预算分配",
        "RESOURCE_ALLOCATION",
        "公益机构获得80万元年度预算，需要在学业支持、心理韧性、职业探索和家长协作四类项目间配置，同时保留基本项目评估能力。",
        "形成总额闭合的预算方案、阶段目标和预算调整条件。",
        "项目评估至少投入8万元，任何单一项目不得超过总预算的45%。",
        "可快速量化的覆盖面与较慢显现的深度影响之间存在冲突。",
        (
            ("A", "学业支持"),
            ("B", "心理韧性"),
            ("C", "职业探索"),
            ("D", "家长协作"),
            ("E", "项目评估"),
        ),
    ),
    _QuestionSpec(
        "HEATWAVE_RESPONSE_BUDGET",
        "城市高温应对资源分配",
        "RESOURCE_ALLOCATION",
        "城市将迎来持续一周的极端高温，可调配100个应急资源单元。不同措施具有明确单位成本与服务能力，团队需在避暑点、上门探访、户外劳动者补给和公共信息服务间形成可核算配置。",
        "提出覆盖一周的资源配置、重点人群理由和温度变化时的调整机制。",
        "至少开放两个避暑点，且上门探访不得少于20个资源单元。",
        "固定点位的规模效率与主动触达脆弱人群的精准性需要平衡。",
        (
            ("A", "社区避暑点"),
            ("B", "独居老人探访"),
            ("C", "户外劳动者补给"),
            ("D", "多语种风险提示"),
        ),
    ),
    _QuestionSpec(
        "PRODUCT_INCIDENT_RECOVERY",
        "软件发布事故恢复方案",
        "PLAN_DESIGN",
        "一款协作软件发布后出现部分数据同步延迟和错误通知。尚无数据丢失证据，但客户信任受损，团队需设计未来24小时的恢复计划。",
        "制定包含止损、验证、沟通、恢复和复盘门槛的分阶段方案。",
        "在完成数据一致性验证前不得宣布全面恢复，也不得删除用户数据。",
        "快速恢复服务、充分验证风险和及时透明沟通之间需要动态权衡。",
        (("A", "技术止损与验证"), ("B", "客户沟通与支持"), ("C", "分批恢复与监测")),
    ),
    _QuestionSpec(
        "NEIGHBORHOOD_FESTIVAL_PLAN",
        "社区周末文化节执行方案",
        "PLAN_DESIGN",
        "社区计划在六周后举办一场面向全年龄居民的文化节，场地紧凑、志愿者有限，附近居民对噪声和交通有顾虑。",
        "设计从筹备到撤场的执行方案，明确里程碑、责任、风险预案和居民沟通。",
        "活动必须在21时前结束，并保留消防通道和无障碍通行。",
        "活动丰富度、现场容量、志愿者负荷和周边居民体验之间存在张力。",
        (("A", "节目与摊位"), ("B", "安全与动线"), ("C", "志愿者与居民沟通")),
    ),
    _QuestionSpec(
        "DIGITAL_LITERACY_ROLLOUT",
        "中学数字素养课程落地方案",
        "PLAN_DESIGN",
        "学校准备在一个学期内为三个年级上线数字素养课程，但教师培训时间和设备数量有限，家长对屏幕时间与隐私保护也有不同意见。",
        "形成分阶段课程落地方案，包含试点、教师支持、设备共享、反馈和扩展条件。",
        "不得要求学生使用个人付费账号，涉及学生数据的工具须通过学校隐私审查。",
        "快速全覆盖、教师准备度、设备公平和真实学习效果无法同时最大化。",
        (("A", "小规模试点"), ("B", "教师共同备课"), ("C", "设备轮转与扩展")),
    ),
    _QuestionSpec(
        "VOLUNTEER_COORDINATION_PLAN",
        "灾后志愿服务协同方案",
        "PLAN_DESIGN",
        "轻度地震后，大量志愿者希望参与社区支持，但需求仍在核实，现场存在交通拥堵和重复配送风险。团队需设计未来48小时协同方案。",
        "制定需求确认、志愿者分流、物资交接、信息更新和退出机制。",
        "未经现场指挥确认的志愿者不得进入受限区域，个人信息不得公开传播。",
        "快速动员的热情、现场秩序、需求准确性和志愿者自主性需要平衡。",
        (("A", "需求与信息核验"), ("B", "志愿者登记分流"), ("C", "物资交接与现场协同")),
    ),
)


def _stance(
    initial_position: str,
    priorities: tuple[tuple[str, str], ...],
    concession_condition: str,
    red_line: str,
    preferred_group_role: str,
) -> PrivateStanceDefinition:
    return PrivateStanceDefinition(
        initial_position=initial_position,
        priority_dimensions=tuple(
            PriorityDimension(code=code, weight=Decimal(weight))
            for code, weight in priorities
        ),
        concession_conditions=(concession_condition,),
        red_lines=(red_line,),
        preferred_group_role=preferred_group_role,
    )


_OPTION_DESCRIPTIONS = {
    "MUSEUM_RECOVERY_ORDER": (
        "800页纸本文献已受潮；预计6小时后霉变风险显著上升，可由2人装箱转移。",
        "40件木质器物表面受潮；预计12小时后变形风险上升，可由2人转移。",
        "1200张醋酸纤维底片已沾水；4小时内可能粘连并加速化学降解，需冷藏转移。",
        "6件大型石刻所在区域有积水；结构评估为不稳定，只能原位遮护，24小时内风险较低。",
        "30件陶瓷状态稳定、包装干燥，但已承诺次日公开展出，可由1人转移。",
    ),
    "RURAL_CLINIC_ALLOCATION": (
        "用于河谷镇慢病复诊，每10个单元可完成约80人次。",
        "用于山岭镇儿童筛查，每10个单元可完成约65人次，交通另占服务时间。",
        "用于湖滨镇健康教育，每10个单元可覆盖约3个偏远村。",
        "每投入10个单元，可为山岭镇或湖滨镇增加一个往返运输班次。",
    ),
    "HEATWAVE_RESPONSE_BUDGET": (
        "每投入15个单元可开放1个避暑点，每个点每日最多服务120人。",
        "每投入1个单元可完成5户独居老人当日探访。",
        "每投入10个单元可维持4处户外补给站运行一周。",
        "每投入5个单元可覆盖一轮全市多语种风险提示。",
    ),
}


_PRIVATE_STANCES = {
    "EMERGENCY_SUPPLY_PRIORITY": (
        _stance(
            "首批先装饮用水、常用药与急救包，再以剩余运力覆盖保温需求。",
            (("FEASIBILITY", "0.95"), ("STAKEHOLDER_IMPACT", "0.70")),
            "若现场确认慢病用药库存可支撑12小时，可把常用药与急救包后移一位。",
            "饮用水不得离开首批，且不得用未核实的捐赠到货替代现有运力。",
            "首批装载约束核算",
        ),
        _stance(
            "首批先装饮用水、婴幼儿与老人用品、折叠床和保温毯，优先降低脆弱人群暴露。",
            (("STAKEHOLDER_IMPACT", "0.95"), ("ADAPTABILITY", "0.60")),
            "若登记显示脆弱人群不足预计人数的一半，可让常用药与急救包进入首批。",
            "不能把婴幼儿与老人用品完全推迟到第二批而不提供替代保障。",
            "脆弱人群风险校验",
        ),
        _stance(
            "首批锁定饮用水和常用药与急救包，第三类在照明与充电设备和保温物资间按到场信息决定。",
            (("ADAPTABILITY", "0.90"), ("FEASIBILITY", "0.75")),
            "若夜间照明已有可靠备份，则立即选择折叠床和保温毯。",
            "第三类物资必须绑定可观测触发条件，不能只以偏好决定。",
            "动态排序与触发条件主持",
        ),
    ),
    "MUSEUM_RECOVERY_ORDER": (
        _stance(
            "近代摄影底片的损害窗口最短，应排第一；潮湿纸本文献第二，木质民俗器物第三。",
            (("FEASIBILITY", "0.85"), ("ADAPTABILITY", "0.90")),
            "若冷藏转移设备两小时内无法到位，可先处理潮湿纸本文献并同步搭建底片临时冷却。",
            "不得移动结构不稳定的大型石刻，也不得忽略底片4小时粘连窗口。",
            "材料风险与时间窗分析",
        ),
        _stance(
            "潮湿纸本文献应先稳定，因为800页规模大且霉变后修复成本会快速扩散。",
            (("STAKEHOLDER_IMPACT", "0.80"), ("FEASIBILITY", "0.85")),
            "若底片已出现粘连征兆，则接受近代摄影底片先于纸本文献。",
            "不能因已预约展出的陶瓷组有公众承诺，就把状态稳定的陶瓷列入前三。",
            "馆藏价值与不可逆损害挑战",
        ),
        _stance(
            "前三应覆盖近代摄影底片、潮湿纸本文献和木质民俗器物，同时为大型石刻安排原位遮护。",
            (("ADAPTABILITY", "0.80"), ("STAKEHOLDER_IMPACT", "0.75")),
            "若两人转移能力成为瓶颈，可穿插由1人完成的陶瓷转移，但不占用前三抢救名额。",
            "完整排序必须解释大型石刻与已预约展出的陶瓷组为何后置。",
            "并行工序与公开说明协调",
        ),
    ),
    "CAMPUS_SERVICE_RESTART": (
        _stance(
            "统一身份认证必须第一，随后优先在线考试平台，再恢复选课系统。",
            (("FEASIBILITY", "0.95"), ("STAKEHOLDER_IMPACT", "0.75")),
            "若考试已统一延期且选课窗口两小时内关闭，可交换在线考试平台和选课系统。",
            "任何依赖统一登录的服务都不得越过统一身份认证先恢复。",
            "依赖关系与恢复路径校验",
        ),
        _stance(
            "统一身份认证之后应先恢复选课系统，避免学生错过不可逆的课程名额。",
            (("STAKEHOLDER_IMPACT", "0.95"), ("ADAPTABILITY", "0.55")),
            "若考试平台存在当日必须完成且无法延期的考试，则接受考试平台优先。",
            "不能只按受影响人数排序而忽略考试和选课的明确截止时间。",
            "学生时限影响代表",
        ),
        _stance(
            "以统一身份认证为共同前提，再用截止时间表决定在线考试平台与选课系统的先后。",
            (("ADAPTABILITY", "0.90"), ("FEASIBILITY", "0.70")),
            "收到教务处正式延期通知后，按新的截止时间重排后四项服务。",
            "图书馆远程资源和校园活动报名不得在核心教学服务仍中断时抢占前序。",
            "共同标准与变更信息主持",
        ),
    ),
    "CUSTOMER_ISSUE_TRIAGE": (
        _stance(
            "车辆制动异常必须首批，另一条并行线处理定位漂移以排查潜在行车风险。",
            (("STAKEHOLDER_IMPACT", "0.95"), ("FEASIBILITY", "0.80")),
            "若技术确认定位漂移只影响账单地图、不影响导航安全，可改为并行处理重复扣费。",
            "车辆制动异常不得因样本量小而后置。",
            "人身安全事件负责人",
        ),
        _stance(
            "车辆制动异常首批不变，第二条线应处理重复扣费，因为影响广且可快速止损退款。",
            (("FEASIBILITY", "0.85"), ("STAKEHOLDER_IMPACT", "0.85")),
            "若定位漂移与制动异常共享同一发布根因，则接受定位漂移合并进入首批。",
            "不能用批量补偿替代对重复扣费根因的修复。",
            "规模影响与客户补救分析",
        ),
        _stance(
            "先隔离车辆制动异常，再按安全关联、影响人数和承诺时效给定位漂移、重复扣费等问题排序。",
            (("ADAPTABILITY", "0.90"), ("FEASIBILITY", "0.75")),
            "每完成一次根因验证，就依据新影响范围更新剩余客诉顺序。",
            "月卡权益未到账和偏远区域无车可用必须获得明确响应时限，不能无限搁置。",
            "跨团队分流与更新节奏主持",
        ),
    ),
    "RURAL_CLINIC_ALLOCATION": (
        _stance(
            "应把最多单元投向河谷镇慢病复诊，同时为山岭镇儿童筛查和湖滨镇健康教育保留20单元底线。",
            (("FEASIBILITY", "0.90"), ("STAKEHOLDER_IMPACT", "0.80")),
            "若河谷镇当地医生可承接超过160人次复诊，可把释放单元转给山岭镇。",
            "三个乡镇都必须达到20单元，且120单元总量必须逐项闭合。",
            "资源总量与服务产能核算",
        ),
        _stance(
            "山岭镇儿童筛查和跨村交通保障应获得额外资源，以补偿4小时往返造成的可及性差距。",
            (("STAKEHOLDER_IMPACT", "0.95"), ("FEASIBILITY", "0.65")),
            "若新增运输班次不能提高实际到诊率，则把相应单元转为湖滨镇流动健康教育。",
            "不能以单位服务量较低为由，把山岭镇长期压在最低20单元。",
            "地域公平与可及性代表",
        ),
        _stance(
            "先锁定三镇各20单元，再用到诊率和覆盖率数据在慢病复诊、儿童筛查、健康教育间分配剩余60单元。",
            (("ADAPTABILITY", "0.95"), ("FEASIBILITY", "0.75")),
            "月中复核若某项完成率低于计划70%，可在不破坏乡镇底线的前提下重分配。",
            "任何调整都必须保留乡镇维度和服务项目维度的可核算记录。",
            "月中监测与重分配主持",
        ),
    ),
    "YOUTH_PROGRAM_BUDGET": (
        _stance(
            "学业支持应获最大份额，项目评估固定8万元，其余预算保障心理韧性和职业探索的基本覆盖。",
            (("FEASIBILITY", "0.95"), ("STAKEHOLDER_IMPACT", "0.70")),
            "若首季度学业参与率低于目标，可把未使用预算转向心理韧性。",
            "任何单一项目不得超过36万元，项目评估不得低于8万元。",
            "预算闭合与上限校验",
        ),
        _stance(
            "心理韧性应与学业支持获得同等优先级，避免只追求易量化的短期覆盖。",
            (("STAKEHOLDER_IMPACT", "0.95"), ("ADAPTABILITY", "0.60")),
            "若需求筛查显示心理支持等待名单明显低于预估，可增加职业探索投入。",
            "不能把家长协作压缩为零，也不能用活动人数替代深度影响证据。",
            "深度影响与家庭协作代表",
        ),
        _stance(
            "以项目评估为共同底座，分阶段拨付学业支持、心理韧性、职业探索和家长协作预算。",
            (("ADAPTABILITY", "0.95"), ("FEASIBILITY", "0.75")),
            "阶段指标连续两次达标后才释放下一批扩展预算。",
            "预算调整必须说明资金来源、去向和对应指标。",
            "阶段目标与预算复核主持",
        ),
    ),
    "HEATWAVE_RESPONSE_BUDGET": (
        _stance(
            "先用30个单元开放两个社区避暑点，再配置20个单元独居老人探访和户外劳动者补给。",
            (("FEASIBILITY", "0.95"), ("STAKEHOLDER_IMPACT", "0.80")),
            "若两个避暑点连续两日使用率低于50%，可把一个点后续15单元转为探访。",
            "不得低于两个避暑点和20个探访单元，也不得超过100单元。",
            "单位成本与最低约束核算",
        ),
        _stance(
            "在满足两个社区避暑点后，应把最多剩余单元投向独居老人探访，因为固定点位无法覆盖行动不便者。",
            (("STAKEHOLDER_IMPACT", "0.95"), ("ADAPTABILITY", "0.65")),
            "若探访确认高风险名单完成率达到95%，可将后续单元转给户外劳动者补给。",
            "不能用避暑点总容量替代对无法到场脆弱人群的主动触达。",
            "脆弱人群主动触达代表",
        ),
        _stance(
            "按30单元社区避暑点、25单元独居老人探访、30单元户外劳动者补给、15单元多语种风险提示形成初始闭合方案。",
            (("ADAPTABILITY", "0.95"), ("FEASIBILITY", "0.80")),
            "温度预报或实际使用量跨过预设阈值时，以5或10单元为步长调整。",
            "调整不得拆出无法形成完整点位、补给站或提示轮次的零散单元。",
            "一周监测与整包调整主持",
        ),
    ),
    "PRODUCT_INCIDENT_RECOVERY": (
        _stance(
            "先执行技术止损与验证，冻结风险发布并建立数据一致性样本，再讨论恢复。",
            (("FEASIBILITY", "0.95"), ("ADAPTABILITY", "0.80")),
            "若连续两轮一致性检查通过，可启动小比例分批恢复与监测。",
            "验证完成前不得宣布全面恢复，也不得删除用户数据。",
            "技术止损与恢复门槛负责人",
        ),
        _stance(
            "技术止损启动同时必须推进客户沟通与支持，明确已知影响、临时措施和下一次更新时间。",
            (("STAKEHOLDER_IMPACT", "0.95"), ("FEASIBILITY", "0.70")),
            "若影响范围经验证显著缩小，可从全量通知改为定向客户沟通。",
            "不能在证据不足时承诺无数据丢失或给出虚假恢复时间。",
            "客户信任与信息透明代表",
        ),
        _stance(
            "用技术止损与验证、客户沟通与支持、分批恢复与监测三条并行工作流覆盖24小时。",
            (("ADAPTABILITY", "0.95"), ("STAKEHOLDER_IMPACT", "0.75")),
            "任何阶段只要错误率回升，就退回上一恢复比例并更新客户说明。",
            "计划必须为每次扩容定义责任人、证据和回退条件。",
            "24小时节奏与跨线协调主持",
        ),
    ),
    "NEIGHBORHOOD_FESTIVAL_PLAN": (
        _stance(
            "先确定安全与动线，再据此削减节目与摊位数量，确保消防和无障碍边界。",
            (("FEASIBILITY", "0.95"), ("STAKEHOLDER_IMPACT", "0.70")),
            "若现场踏勘证明第二出口可用，可增加不阻塞主通道的摊位。",
            "消防通道和无障碍通行不得被任何节目与摊位占用。",
            "场地容量与安全动线负责人",
        ),
        _stance(
            "志愿者与居民沟通应提前成为主线，以21时结束和交通分流换取周边居民支持。",
            (("STAKEHOLDER_IMPACT", "0.95"), ("ADAPTABILITY", "0.65")),
            "若居民反馈集中在某一时段，可调整高音量节目而非整体缩减活动。",
            "不能把噪声、交通投诉留到活动当天才响应。",
            "社区关系与志愿者负荷代表",
        ),
        _stance(
            "以安全与动线为框架，把节目与摊位、志愿者与居民沟通拆成六周里程碑。",
            (("ADAPTABILITY", "0.90"), ("FEASIBILITY", "0.85")),
            "每周根据报名人数和志愿者到位率调整区域容量。",
            "每个里程碑必须有责任人和无法按期完成时的缩减方案。",
            "六周里程碑与风险预案主持",
        ),
    ),
    "DIGITAL_LITERACY_ROLLOUT": (
        _stance(
            "先做小规模试点，并把教师共同备课作为扩展前置条件。",
            (("FEASIBILITY", "0.95"), ("ADAPTABILITY", "0.80")),
            "试点教师准备度和学生任务完成率达标后，可扩到第二个年级。",
            "未经学校隐私审查的工具不得进入小规模试点。",
            "试点门槛与教师准备负责人",
        ),
        _stance(
            "设备轮转与扩展必须优先保障无个人设备学生，课程不能依赖个人付费账号。",
            (("STAKEHOLDER_IMPACT", "0.95"), ("FEASIBILITY", "0.75")),
            "若学校补充共享设备，可缩短轮转周期并扩大同步课堂。",
            "不能以家庭设备差异决定学生是否能完成必修任务。",
            "设备公平与学生权益代表",
        ),
        _stance(
            "把小规模试点、教师共同备课、设备轮转与扩展串成一个学期的阶段计划。",
            (("ADAPTABILITY", "0.95"), ("STAKEHOLDER_IMPACT", "0.70")),
            "家长反馈或隐私审查提出新风险时，暂停扩展并修订工具清单。",
            "扩展决策必须同时有学习效果、教师负荷和设备可用性证据。",
            "学期反馈与扩展条件主持",
        ),
    ),
    "VOLUNTEER_COORDINATION_PLAN": (
        _stance(
            "先完成需求与信息核验，再开放志愿者登记分流，避免重复配送。",
            (("FEASIBILITY", "0.95"), ("ADAPTABILITY", "0.80")),
            "若现场指挥发布已验证的紧急需求，可为具备对应技能者开快速通道。",
            "未经现场指挥确认的志愿者不得进入受限区域。",
            "需求核验与现场准入负责人",
        ),
        _stance(
            "志愿者登记分流应保留自主选择，同时按技能、时段和交通承载匹配任务。",
            (("STAKEHOLDER_IMPACT", "0.90"), ("FEASIBILITY", "0.75")),
            "当某类任务积压超过两小时，可向已登记志愿者发起自愿调剂。",
            "个人信息不得公开传播，也不能强制志愿者接受未说明风险的任务。",
            "志愿者体验与隐私代表",
        ),
        _stance(
            "以需求与信息核验为入口，用志愿者登记分流连接物资交接与现场协同，并每四小时更新一次。",
            (("ADAPTABILITY", "0.95"), ("FEASIBILITY", "0.80")),
            "需求清单变化时先更新交接点和分流公告，再派发新任务。",
            "任何物资交接都必须记录需求来源、接收点和确认状态。",
            "48小时信息节奏与交接主持",
        ),
    ),
}


def _build_bundle(index: int, spec: _QuestionSpec) -> PublishedQuestionBundle:
    persona_start = (index - 2) % len(_PERSONA_IDS)
    persona_ids = tuple(
        _PERSONA_IDS[(persona_start + offset) % len(_PERSONA_IDS)]
        for offset in range(3)
    )
    private_stances = _PRIVATE_STANCES[spec.code]
    assignments = tuple(
        PersonaAssignmentDefinition(
            id=UUID(f"22000000-0000-4000-8000-{4 + (index - 2) * 3 + slot - 1:012d}"),
            slot=slot,
            persona_template_id=persona_ids[slot - 1],
            private_stance=private_stances[slot - 1],
        )
        for slot in range(1, 4)
    )
    return PublishedQuestionBundle(
        template_id=UUID(f"20000000-0000-4000-8000-{index:012d}"),
        template_code=f"V01_{spec.code}",
        version_id=UUID(f"21000000-0000-4000-8000-{index:012d}"),
        version_number=1,
        content=QuestionVersionContent(
            title=spec.title,
            question_type_code=spec.question_type,
            background_domain_code="GENERAL",
            difficulty_code="STANDARD",
            scenario=spec.scenario,
            objective=spec.objective,
            estimated_minutes=30,
            hard_constraints=(
                ConstraintItem(key="BOUNDARY", text=spec.hard_constraint),
            ),
            soft_constraints=(
                ConstraintItem(
                    key="BALANCE", text="方案应清楚说明不同利益与时间尺度之间的取舍。"
                ),
                ConstraintItem(key="ADAPT", text="方案应给出新信息出现时的调整条件。"),
            ),
            stakeholders=(
                StakeholderItem(
                    key="DIRECT",
                    name="直接受影响者",
                    description="直接承受方案收益、成本或风险的人群。",
                ),
                StakeholderItem(
                    key="DELIVERY",
                    name="执行团队",
                    description="负责在有限资源和时间内落实共同决定。",
                ),
            ),
            options=tuple(
                QuestionOption(
                    key=key,
                    label=label,
                    description=description,
                )
                for (key, label), description in zip(
                    spec.options,
                    _OPTION_DESCRIPTIONS.get(
                        spec.code,
                        tuple(
                            f"需要与其他选项共同权衡的方案要素：{item_label}。"
                            for _, item_label in spec.options
                        ),
                    ),
                    strict=True,
                )
            ),
            reference_dimensions=(
                ReferenceDimension(
                    key="FEASIBILITY",
                    name="可行性",
                    description="是否满足资源、时间和硬约束。",
                ),
                ReferenceDimension(
                    key="STAKEHOLDER_IMPACT",
                    name="利益相关者影响",
                    description="是否识别不同群体的收益、成本和风险。",
                ),
                ReferenceDimension(
                    key="ADAPTABILITY",
                    name="适应性",
                    description="是否提供清晰的监测和调整条件。",
                ),
            ),
            hidden_conflicts=(
                InternalTextItem(key="MAJOR_TRADEOFF", text=spec.major_tradeoff),
            ),
            acceptable_outcome_patterns=(
                InternalTextItem(
                    key="TRACEABLE",
                    text="结论满足硬约束，且每个关键取舍均能追溯到明确标准。",
                ),
                InternalTextItem(
                    key="ADAPTIVE",
                    text="结论包含可执行步骤、责任或排序，并给出至少一个调整触发条件。",
                ),
            ),
            phase_prompts=PhasePromptSet.model_validate(
                {
                    "PREPARATION": "独立识别硬约束、主要利益相关者和需要权衡的维度。",
                    "OPENING_STATEMENTS": "提出初步方案和最重要的判断标准。",
                    "EXPLORATION": "补充备选方案、信息缺口和受影响群体。",
                    "CONFLICT_AND_EVALUATION": "用共同标准比较分歧方案，不回避主要取舍。",
                    "CONVERGENCE": "收敛到满足硬约束且可执行的共同方案。",
                    "FINAL_SUMMARY": "总结决定、理由、责任步骤和调整条件。",
                }
            ),
            safety_tags=("SYNTHETIC_TRAINING", "NO_EXTERNAL_PERSONAL_DATA"),
        ),
        assignments=assignments,
        created_at=_CONTENT_TIME,
        published_at=_CONTENT_TIME,
    )


ADDITIONAL_V01_QUESTION_BUNDLES = tuple(
    _build_bundle(index, spec) for index, spec in enumerate(_SPECS, start=2)
)
