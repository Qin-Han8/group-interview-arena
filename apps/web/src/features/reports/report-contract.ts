const REPORT_STATUSES = [
  "REQUESTED",
  "RUNNING",
  "COMPLETED",
  "FAILED",
] as const;
const EVIDENCE_KINDS = ["STRENGTH", "IMPROVEMENT"] as const;
const PHASES = [
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
] as const;

export type ReportStatus = (typeof REPORT_STATUSES)[number];
export type EvidenceKind = (typeof EVIDENCE_KINDS)[number];
export type EvidencePhase = (typeof PHASES)[number];

export type PublicQuestion = {
  id: string;
  question_template_id: string;
  version_number: number;
  title: string;
  question_type: string;
  background_domain: string;
  difficulty: string;
  estimated_minutes: number;
  scenario: string;
  objective: string;
  hard_constraints: { key: string; text: string }[];
  soft_constraints: { key: string; text: string }[];
  stakeholders: { key: string; name: string; description: string }[];
  options: { key: string; label: string; description: string }[];
};

export type EvidenceCard = {
  kind: EvidenceKind;
  source_participant_id: string;
  source_utterance_id: string;
  source_event_sequence: number;
  phase: EvidencePhase;
  quote: string;
  interpretation: string;
  confidence: string | number;
};

export type ReportView = {
  report: {
    report_id: string;
    session_id: string;
    status: ReportStatus;
    report_schema_version: number;
    derivation_version: string;
    source_through_sequence: number;
    created_at: string;
    completed_at: string | null;
  };
  content: {
    overview: {
      session_status: "COMPLETED";
      question: PublicQuestion;
      participant_count: number;
      human_utterance_count: number;
      ai_utterance_count: number;
      total_utterance_count: number;
      covered_phases: EvidencePhase[];
      summary: string;
    };
    strengths: EvidenceCard[];
    improvements: EvidenceCard[];
    priority_improvement: string;
  } | null;
};

function object(
  value: unknown,
  keys: readonly string[],
): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    throw new Error("Invalid report response");
  const record = value as Record<string, unknown>;
  const actual = Object.keys(record).sort();
  const expected = [...keys].sort();
  if (
    actual.length !== expected.length ||
    actual.some((key, index) => key !== expected[index])
  )
    throw new Error("Unexpected report field");
  return record;
}

function text(value: unknown, preserve = false): string {
  if (typeof value !== "string" || !(preserve ? value.trim() : value.trim()))
    throw new Error("Invalid report text");
  return value;
}

function uuid(value: unknown): string {
  const result = text(value);
  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      result,
    )
  )
    throw new Error("Invalid report identity");
  return result;
}

function integer(value: unknown, minimum: number): number {
  if (!Number.isSafeInteger(value) || (value as number) < minimum)
    throw new Error("Invalid report number");
  return value as number;
}

function oneOf<T extends readonly string[]>(
  value: unknown,
  values: T,
): T[number] {
  if (typeof value !== "string" || !values.includes(value))
    throw new Error("Invalid report enum");
  return value as T[number];
}

function array<T>(value: unknown, parse: (item: unknown) => T): T[] {
  if (!Array.isArray(value)) throw new Error("Invalid report list");
  return value.map(parse);
}

function constraint(value: unknown) {
  const row = object(value, ["key", "text"]);
  return { key: text(row.key), text: text(row.text) };
}

function question(value: unknown): PublicQuestion {
  const row = object(value, [
    "id",
    "question_template_id",
    "version_number",
    "title",
    "question_type",
    "background_domain",
    "difficulty",
    "estimated_minutes",
    "scenario",
    "objective",
    "hard_constraints",
    "soft_constraints",
    "stakeholders",
    "options",
  ]);
  return {
    id: uuid(row.id),
    question_template_id: uuid(row.question_template_id),
    version_number: integer(row.version_number, 1),
    title: text(row.title),
    question_type: text(row.question_type),
    background_domain: text(row.background_domain),
    difficulty: text(row.difficulty),
    estimated_minutes: integer(row.estimated_minutes, 5),
    scenario: text(row.scenario),
    objective: text(row.objective),
    hard_constraints: array(row.hard_constraints, constraint),
    soft_constraints: array(row.soft_constraints, constraint),
    stakeholders: array(row.stakeholders, (item) => {
      const entry = object(item, ["key", "name", "description"]);
      return {
        key: text(entry.key),
        name: text(entry.name),
        description: text(entry.description),
      };
    }),
    options: array(row.options, (item) => {
      const entry = object(item, ["key", "label", "description"]);
      return {
        key: text(entry.key),
        label: text(entry.label),
        description: text(entry.description),
      };
    }),
  };
}

function evidence(value: unknown): EvidenceCard {
  const row = object(value, [
    "kind",
    "source_participant_id",
    "source_utterance_id",
    "source_event_sequence",
    "phase",
    "quote",
    "interpretation",
    "confidence",
  ]);
  const confidence = row.confidence;
  if (!(
    (typeof confidence === "number" && confidence >= 0 && confidence <= 1) ||
    (typeof confidence === "string" &&
      confidence.trim() !== "" &&
      Number(confidence) >= 0 &&
      Number(confidence) <= 1)
  ))
    throw new Error("Invalid confidence");
  return {
    kind: oneOf(row.kind, EVIDENCE_KINDS),
    source_participant_id: uuid(row.source_participant_id),
    source_utterance_id: uuid(row.source_utterance_id),
    source_event_sequence: integer(row.source_event_sequence, 1),
    phase: oneOf(row.phase, PHASES),
    quote: text(row.quote, true),
    interpretation: text(row.interpretation),
    confidence,
  };
}

export function parseReportView(value: unknown): ReportView {
  const root = object(value, ["report", "content"]);
  const metadata = object(root.report, [
    "report_id",
    "session_id",
    "status",
    "report_schema_version",
    "derivation_version",
    "source_through_sequence",
    "created_at",
    "completed_at",
  ]);
  const status = oneOf(metadata.status, REPORT_STATUSES);
  const completedAt =
    metadata.completed_at === null ? null : text(metadata.completed_at);
  const report = {
    report_id: uuid(metadata.report_id),
    session_id: uuid(metadata.session_id),
    status,
    report_schema_version: integer(metadata.report_schema_version, 1),
    derivation_version: text(metadata.derivation_version),
    source_through_sequence: integer(metadata.source_through_sequence, 0),
    created_at: text(metadata.created_at),
    completed_at: completedAt,
  };
  if (status !== "COMPLETED") {
    if (root.content !== null || completedAt !== null)
      throw new Error("Non-completed report exposed content");
    return { report, content: null };
  }
  if (root.content === null || completedAt === null)
    throw new Error("Completed report is incomplete");
  const content = object(root.content, [
    "overview",
    "strengths",
    "improvements",
    "priority_improvement",
  ]);
  const overview = object(content.overview, [
    "session_status",
    "question",
    "participant_count",
    "human_utterance_count",
    "ai_utterance_count",
    "total_utterance_count",
    "covered_phases",
    "summary",
  ]);
  if (overview.session_status !== "COMPLETED")
    throw new Error("Invalid session status");
  const strengths = array(content.strengths, evidence);
  const improvements = array(content.improvements, evidence);
  if (
    strengths.length > 3 ||
    improvements.length > 3 ||
    strengths.some((item) => item.kind !== "STRENGTH") ||
    improvements.some((item) => item.kind !== "IMPROVEMENT")
  )
    throw new Error("Invalid evidence section");
  const human = integer(overview.human_utterance_count, 0);
  const ai = integer(overview.ai_utterance_count, 0);
  const total = integer(overview.total_utterance_count, 0);
  if (human + ai !== total) throw new Error("Invalid utterance counts");
  return {
    report,
    content: {
      overview: {
        session_status: "COMPLETED",
        question: question(overview.question),
        participant_count: integer(overview.participant_count, 1),
        human_utterance_count: human,
        ai_utterance_count: ai,
        total_utterance_count: total,
        covered_phases: array(overview.covered_phases, (item) =>
          oneOf(item, PHASES),
        ),
        summary: text(overview.summary),
      },
      strengths,
      improvements,
      priority_improvement: text(content.priority_improvement),
    },
  };
}
