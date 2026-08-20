export const EVAL_CATEGORIES = [
  "direct_fact",
  "temporal",
  "relationship",
  "spanning",
  "regulatory_compliance",
  "regulatory_fact",
  "traceability",
] as const;

type TranslateFn = (key: string) => string;

const CATEGORY_KEYS = [
  "direct_fact",
  "temporal",
  "relationship",
  "spanning",
  "comparative",
  "numerical",
  "holistic",
  "regulatory_compliance",
  "regulatory_fact",
  "traceability",
  "out_of_knowledge",
  "general",
  "normativa",
  "parcelas",
  "logistica",
  "alucinaciones",
  "cadena_frio",
  "sat",
  "sigpac",
  "fitosanitario",
  "pac",
  "posei",
  "bcam",
  "geografia",
  "geography",
] as const;

const STATUS_KEYS = ["pending", "approved", "rejected", "corrected"] as const;

function humanize(value: string): string {
  const cleaned = value.replace(/[_-]+/g, " ").trim();
  if (!cleaned) return value;
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export function categoryLabel(
  t: TranslateFn,
  category?: string | null,
): string {
  if (!category) return t("evaluationLabels.general");
  const key = category.trim();
  const normalized = key === "geografía" ? "geografia" : key.toLowerCase();
  if (CATEGORY_KEYS.includes(normalized as (typeof CATEGORY_KEYS)[number])) {
    return t(`evaluationLabels.${normalized}`);
  }
  const translated = t(`evaluationLabels.${key}`);
  if (translated !== `evaluationLabels.${key}`) return translated;
  return humanize(key);
}

export function reviewStatusLabel(
  t: TranslateFn,
  status?: string | null,
): string {
  if (!status) return "";
  const normalized = status.toLowerCase();
  if (STATUS_KEYS.includes(normalized as (typeof STATUS_KEYS)[number])) {
    return t(`evaluationLabels.${normalized}`);
  }
  return humanize(status);
}
