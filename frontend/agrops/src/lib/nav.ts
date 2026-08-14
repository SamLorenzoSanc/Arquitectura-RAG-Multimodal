export type SettingsTab =
  | "profile"
  | "authenticate"
  | "api-keys"
  | "usage"
  | "projects";

export const SETTINGS_TABS: Array<{ id: SettingsTab; label: string }> = [
  { id: "profile", label: "Perfil" },
  { id: "authenticate", label: "Autenticación" },
  { id: "api-keys", label: "API Keys" },
  { id: "usage", label: "Uso" },
  { id: "projects", label: "Proyectos" },
];

export const ROUTE_LABELS: Record<string, string> = {
  "/dashboard": "Panel",
  "/dashboard/chat": "Asistente",
  "/dashboard/cuaderno": "Cuaderno de campo",
  "/dashboard/documentation": "Datasets",
  "/dashboard/datasets": "Datasets",
  "/dashboard/organization": "Organización",
  "/dashboard/tenants": "Inquilinos",
  "/dashboard/settings": "Ajustes",
  "/dashboard/knowledge-graph": "Grafo de embeddings",
  "/dashboard/evaluacion": "Evaluación",
  "/dashboard/help": "Documentación",
  "/dashboard/support": "Soporte",
};

export function settingsTabLabel(tab?: string | null): string | null {
  const match = SETTINGS_TABS.find((item) => item.id === tab);
  return match?.label ?? null;
}
