export const PROJECT_USE_CASES = [
  "Agentic Application",
  "Chatbot",
  "Q/A",
  "Consulta normativa",
  "Sanidad vegetal",
  "Otros",
] as const;

export type ProjectUseCase = (typeof PROJECT_USE_CASES)[number];
export type ChatScope = "project" | "organization";
