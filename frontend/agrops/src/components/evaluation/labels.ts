const CATEGORY_LABELS: Record<string, string> = {
  direct_fact: "Hecho directo",
  temporal: "Temporal",
  relationship: "Relación",
  spanning: "Transversal",
  regulatory_compliance: "Cumplimiento normativo",
  regulatory_fact: "Hecho normativo",
  traceability: "Trazabilidad",
  out_of_knowledge: "Fuera de conocimiento",
  general: "General",
  normativa: "Normativa",
  parcelas: "Parcelas",
  logistica: "Logística",
  alucinaciones: "Alucinaciones",
  cadena_frio: "Cadena de frío",
  sat: "SAT",
  sigpac: "SIGPAC",
  fitosanitario: "Fitosanitario",
  pac: "PAC",
  bcam: "BCAM",
  geografía: "Geografía",
  geografia: "Geografía",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  approved: "Aprobada",
  rejected: "Rechazada",
  corrected: "Corregida",
};

function humanize(value: string): string {
  const cleaned = value.replace(/[_-]+/g, " ").trim();
  if (!cleaned) return value;
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export function categoryLabel(category?: string | null): string {
  if (!category) return "General";
  const key = category.trim();
  return CATEGORY_LABELS[key] ?? CATEGORY_LABELS[key.toLowerCase()] ?? humanize(key);
}

export function reviewStatusLabel(status?: string | null): string {
  if (!status) return "";
  return STATUS_LABELS[status] ?? STATUS_LABELS[status.toLowerCase()] ?? humanize(status);
}
