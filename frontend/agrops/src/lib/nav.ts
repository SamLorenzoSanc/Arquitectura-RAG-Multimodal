export type SettingsTab =
  | "profile"
  | "authenticate"
  | "api-keys"
  | "usage"
  | "billing"
  | "users";

export const SETTINGS_TAB_KEYS: Array<{ id: SettingsTab; labelKey: string }> = [
  { id: "profile", labelKey: "settings.profile" },
  { id: "authenticate", labelKey: "settings.authenticate" },
  { id: "api-keys", labelKey: "settings.apiKeys" },
  { id: "usage", labelKey: "settings.usage" },
  { id: "billing", labelKey: "settings.billing" },
  { id: "users", labelKey: "settings.users" },
];

export const ROUTE_LABEL_KEYS: Record<string, string> = {
  "/dashboard": "nav.dashboard",
  "/dashboard/documentos": "nav.documents",
  "/dashboard/embeddings": "nav.embeddings",
  "/dashboard/flujo-rag": "nav.ragFlow",
  "/dashboard/evaluacion": "nav.evaluation",
  "/dashboard/validacion": "nav.humanValidation",
  "/dashboard/organization": "nav.organization",
  "/dashboard/docs": "common.docs",
  "/dashboard/settings": "common.settings",
  "/dashboard/support": "common.support",
};

export function settingsTabLabel(
  tab: string | null | undefined,
  translate: (key: string) => string,
): string | null {
  const match = SETTINGS_TAB_KEYS.find((item) => item.id === tab);
  return match ? translate(match.labelKey) : null;
}

export function routeLabel(
  path: string,
  translate: (key: string) => string,
): string {
  const key = ROUTE_LABEL_KEYS[path];
  return key ? translate(key) : translate("common.section");
}
