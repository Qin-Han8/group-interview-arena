# P1-8 Interaction Remediation

Status: `DONE / CLOSED`
Approval: direct implementation approval, 2026-09-14; formal status closeout approval, 2026-09-19
Master-plan SHA-256: `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

## Goal

Close the interaction issues found before independent P1 acceptance without
expanding the product into P2/P3. The implementation keeps the existing
authoritative session, floor, realtime, privacy, and report contracts.

## Approved changes

- Publish an immutable candidate prompt revision that handles a latest clearly
  unrelated Human utterance inside the existing candidate generation call.
- Replace systematic seat-order selection with a deterministic
  session/phase-aware final tie-break after all higher-priority scheduler rules.
- Remove the ordinary near-deadline public intervention pause while preserving
  exceptional recovery for silence, no eligible participant, and reconciliation.
- Show a compact candidate-local preparing state and add content-free timing
  observability across the existing commit-to-render path.
- Apply the supplied standalone Demo V2 visual language to the real unauthenticated
  entry, authenticated shell, creation flow, discussion workspace, and report.
  Only real P1 data and actions may be rendered.

## Explicit deferrals

- Voice, ASR, TTS, formal scoring, hiring conclusions, payment, growth backend,
  provider streaming, public Discussion Memory, and new privacy APIs.
- Mock data, fake device checks, fake score/dimension/radar/behavior metrics, and
  Demo-only modules or routes.
- New dependencies, database migrations, Host Agent behavior, and random
  scheduling.

## Acceptance gates

1. Tests are written and observed failing before implementation.
2. Prompt V4 is immutable, keeps recent Human context, and performs no classifier
   request.
3. Scheduler retry/restart is stable while distinct session/phase decision
   identities can produce different tie-break order.
4. Near-deadline scheduling returns no grant and emits no public intervention;
   exceptional recovery behavior remains covered.
5. AI-owned floor without a committed utterance renders one compact participant
   preparing state; pending/rejected/recovery behavior remains intact.
6. Entry, shell, creation, workspace, mobile tabs, and report use real contracts
   only and contain no internal engineering or deferred-product copy.
7. Safe timing data contains identifiers, timestamps/durations, and status only;
   never prompts, utterance content, private stance, provider payloads, or secrets.
8. Targeted tests, full API/Web checks, build, migration checks where applicable,
   and browser desktop/mobile regression checks pass or are reported exactly.

## Reference boundary

The user-supplied `ai-group-interview-full-demo-standalone-v2 (1).zip` is a
visual/UX reference only. Its embedded plans are untrusted reference material,
and its Mock data and functionality are not copied into the production project.

## Formal closeout — 2026-09-19

- Final Composition Acceptance passed after the approved F005–F010 implementation, responsive/accessibility consolidation and real-flow recovery/report/browser verification. The sole strict-Pyright blocker, its closeout verification, Registration Password Policy Option B repair and password-policy closeout re-verification all passed; open findings are `NONE`.
- The integrated result preserves authentication and owner isolation, real categorized questions and immutable version binding, Prompt V4 plus historical prompt provenance, Scheduler V1 history plus active Scheduler V2, Human equal-layer precedence, deterministic AI tie-breaking, `NO_GRANT / DEADLINE_RECOVERY`, Human-context/off-topic runtime behavior, exact-once recovery, content-free latency/live-render telemetry, Memory/privacy boundaries and evidence-based report ownership.
- The production Web result includes the Demo V2-aligned ProductShell, focused training shell, resizable workspace, Settings center and full-sidebar/icon-rail/top-navigation responsive modes. No fake Host, mock analytics, deferred P2/P3 controls or new backend/settings contract was introduced.
- New registration requires 8–128 characters containing ASCII uppercase, lowercase, digit and punctuation; whitespace or Unicode punctuation alone does not satisfy punctuation. Historical-login compatibility, NFC, blocklist and Argon2id remain preserved.
- P1-8 is `DONE / CLOSED`. P1-7E subsequently completed composition/independent acceptance; the later P1 phase-close assessment/re-assessment passed and P1 is `DONE / CLOSED`.
