export const QUESTION_TYPES = [
  "ORDERING_SELECTION",
  "RESOURCE_ALLOCATION",
  "PLAN_DESIGN",
] as const;

export type SupportedQuestionType = (typeof QUESTION_TYPES)[number];

const QUESTION_TYPE_LABELS: Record<SupportedQuestionType, string> = {
  ORDERING_SELECTION: "排序选择型",
  RESOURCE_ALLOCATION: "资源分配型",
  PLAN_DESIGN: "方案策划型",
};

const DIFFICULTY_LABELS: Record<string, string> = {
  BASIC: "基础",
  STANDARD: "标准",
  ADVANCED: "进阶",
};

const BACKGROUND_DOMAIN_LABELS: Record<string, string> = {
  GENERAL: "通用场景",
  CAMPUS: "校园场景",
  COMMUNITY: "社区场景",
  WORKPLACE: "职场场景",
  PUBLIC_SERVICE: "公共服务",
};

export function isSupportedQuestionType(
  value: string,
): value is SupportedQuestionType {
  return QUESTION_TYPES.some((type) => type === value);
}

export function questionTypeLabel(value: string) {
  return isSupportedQuestionType(value) ? QUESTION_TYPE_LABELS[value] : value;
}

export function questionDifficultyLabel(value: string) {
  return DIFFICULTY_LABELS[value] ?? value;
}

export function questionBackgroundLabel(value: string) {
  return BACKGROUND_DOMAIN_LABELS[value] ?? value;
}
