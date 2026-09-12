# V0.1 Question Content Review Manifest

- Status: `4/4/4 IMPLEMENTED / HUMAN_CONTENT_REVIEW_PASS`
- Scope: 12 immutable candidate Question Versions for `V0.1 Internal Validation`
- Distribution: 4 `ORDERING_SELECTION` / 4 `RESOURCE_ALLOCATION` / 4 `PLAN_DESIGN`
- Persona baseline: the existing 4 Persona Templates; exactly 3 distinct AI assignments and Private Stances per question
- Safety baseline: synthetic general-domain training only; no external personal/confidential data; hidden/reference/stance fields remain server-only

External human content review has passed. Reviewers assessed ambiguity, realism, genuine trade-offs, language quality, safety and whether each task supports a full group discussion. Automated checks remain separate supporting evidence for structure, identity, persistence and public/private boundaries only.

Finding-remediation note: each of the 11 added questions has three explicit question-specific Private Stances with differentiated initial positions, priority weights, concession conditions, red lines and preferred roles. The museum, rural-clinic and heatwave entries also include the missing public decision facts described below. P1-7D-F003 and P1-7D-F004 were externally re-reviewed and are `CLOSED`.

## Retained resource-allocation baseline

1. `INTERNAL_VALIDATION_RESOURCE_ALLOCATION` — **内部验证：社区活动资源安排** — `RESOURCE_ALLOCATION`
   - Objective: form an executable allocation within 100 units while explaining trade-offs.
   - Major trade-off: broad reach versus depth and long-term value.
   - Assignments: Logic Analyst / Creative Diverger / Gentle Coordinator; feasibility, alternative combinations and consensus lenses.
   - Safety note: internal synthetic community scenario; no personal data. The previously published bundle is retained unchanged.

## Ordering and selection

2. `V01_EMERGENCY_SUPPLY_PRIORITY` — **暴雨临时安置点物资优先序** — `ORDERING_SELECTION`
   - Objective: rank five supply groups and state adjustment triggers.
   - Major trade-off: immediate survival versus medical, order and special-population needs.
   - Stance conflict: medical/survival loading, vulnerable-population protection and trigger-based adaptable third-slot selection compete within the three-item first shipment.
   - Safety note: synthetic preparedness exercise; no operational emergency instruction or personal data.

3. `V01_MUSEUM_RECOVERY_ORDER` — **城市博物馆藏品抢救优先序** — `ORDERING_SELECTION`
   - Objective: rank five collection groups using value, irreversibility and feasibility.
   - Decision facts: public options state each group's material/quantity, deterioration window and movement constraint.
   - Major trade-off: cultural value, irreversible damage, public commitments and limited restoration capacity.
   - Stance conflict: the shortest deterioration window, large-scale irreversible damage and executable parallel handling/public commitment compete under the no-move constraint.
   - Safety note: synthetic cultural-property scenario; unstable objects remain a hard no-move boundary.

4. `V01_CAMPUS_SERVICE_RESTART` — **校园服务恢复优先序** — `ORDERING_SELECTION`
   - Objective: rank five campus services and communicate a common decision rule.
   - Major trade-off: reach, time sensitivity, learning continuity and technical dependency.
   - Stance conflict: technical dependency-first recovery, irreversible student deadlines and evidence-triggered reprioritization compete for sequence.
   - Safety note: synthetic service-recovery scenario; no student records or credentials.

5. `V01_CUSTOMER_ISSUE_TRIAGE` — **共享出行客诉处理优先序** — `ORDERING_SELECTION`
   - Objective: rank five issue classes by safety, scale, reversibility and promise windows.
   - Major trade-off: isolated high-risk events versus broad low-risk impact, compensation and root-cause repair.
   - Stance conflict: isolated safety-critical incidents, broad financial harm/root-cause repair and adaptive cross-team triage compete for the second workstream.
   - Safety note: human safety is an explicit first-batch constraint; no real customer data.

## Resource allocation

6. `V01_RURAL_CLINIC_ALLOCATION` — **乡镇巡诊资源配置** — `RESOURCE_ALLOCATION`
   - Objective: allocate 120 service units across three towns and service types.
   - Decision facts: public scenario states separate chronic-care, child-screening, transport and remote-village demand.
   - Major trade-off: high-risk depth, geographic fairness and preventive reach.
   - Stance conflict: service throughput, geographic accessibility/equity and monitored adaptive reallocation compete within the 120-unit closure.
   - Safety note: synthetic planning only; not medical diagnosis or individual treatment advice.

7. `V01_YOUTH_PROGRAM_BUDGET` — **青少年公益项目预算分配** — `RESOURCE_ALLOCATION`
   - Objective: close an 800,000-yuan budget with goals and reallocation conditions.
   - Major trade-off: quickly measurable reach versus slower deep impact.
   - Stance conflict: measurable academic reach, deeper psychosocial/family impact and stage-gated evidence-based funding compete within budget caps.
   - Safety note: synthetic program design; no minor identities or sensitive records.

8. `V01_HEATWAVE_RESPONSE_BUDGET` — **城市高温应对资源分配** — `RESOURCE_ALLOCATION`
   - Objective: allocate 100 emergency units over one week with adjustment rules.
   - Decision facts: public options state the unit cost and service capacity of every measure.
   - Major trade-off: fixed-site scale efficiency versus proactive reach to vulnerable groups.
   - Stance conflict: fixed-site capacity, proactive outreach to immobile vulnerable residents and threshold-driven packaged reallocation compete within 100 units.
   - Safety note: synthetic preparedness discussion; no claim to replace official emergency guidance.

## Plan design

9. `V01_PRODUCT_INCIDENT_RECOVERY` — **软件发布事故恢复方案** — `PLAN_DESIGN`
   - Objective: create a 24-hour containment, validation, communication, recovery and review plan.
   - Major trade-off: service speed, sufficient risk validation and timely transparency.
   - Stance conflict: technical containment evidence, timely customer transparency and parallel staged recovery/rollback compete across the 24-hour plan.
   - Safety note: no real customer/system data; deletion before verification is prohibited.

10. `V01_NEIGHBORHOOD_FESTIVAL_PLAN` — **社区周末文化节执行方案** — `PLAN_DESIGN`
   - Objective: design milestones, ownership, contingency and resident communication for a six-week delivery.
   - Major trade-off: program richness, capacity, volunteer load and neighborhood impact.
   - Stance conflict: safety-and-capacity limits, resident/volunteer impact and milestone-driven program flexibility compete across six weeks.
   - Safety note: fire access, accessibility and end-time are explicit hard constraints.

11. `V01_DIGITAL_LITERACY_ROLLOUT` — **中学数字素养课程落地方案** — `PLAN_DESIGN`
   - Objective: phase a semester rollout with pilot, teacher support, device sharing and expansion gates.
   - Major trade-off: rapid coverage, teacher readiness, device equity and learning quality.
   - Stance conflict: pilot evidence and teacher readiness, device equity and privacy-triggered staged expansion compete over semester rollout.
   - Safety note: no paid personal accounts; student-data tools require school privacy review.

12. `V01_VOLUNTEER_COORDINATION_PLAN` — **灾后志愿服务协同方案** — `PLAN_DESIGN`
   - Objective: design 48-hour demand verification, volunteer routing, handoff, updates and exit mechanisms.
   - Major trade-off: rapid mobilization, site order, demand accuracy and volunteer autonomy.
   - Stance conflict: verified demand and controlled access, volunteer autonomy/privacy and rapid traceable handoff updates compete during the first 48 hours.
   - Safety note: restricted-area and personal-information boundaries are explicit; scenario is synthetic.

## Human review outcome

- Verdict: `PASS`
- Material content findings: `NONE OPEN`
- P1-7D-F003: `CLOSED`
- P1-7D-F004: `CLOSED`
- Closure authority: external P1-7D actual-source/content review
