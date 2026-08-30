/* --- lib/nav.ts --- */
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
  "/dashboard/lab-retrieval": "nav.ragProbe",
  "/dashboard/historial": "nav.userHistory",
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

/* --- lib/roles.ts --- */
export interface RoleGuide {
  label: string;
  summary: string;
  can: string[];
  cannot: string[];
}

type TranslateFn = (key: string) => string;

const ROLE_KEYS = [
  "ORG_ADMIN",
  "SUPER_ADMIN",
  "FARM_MANAGER",
  "QUALITY_CONTROLLER",
  "LOGISTICS_OPERATOR",
  "USER",
  "MEMBER",
  "VIEWER",
] as const;

type RoleKey = (typeof ROLE_KEYS)[number];

const ROLE_PERMISSIONS: Record<
  RoleKey,
  { can: string[]; cannot: string[] }
> = {
  ORG_ADMIN: {
    can: [
      "perm_adminOrg",
      "perm_manageMembers",
      "perm_manageDocs",
      "perm_orgSettings",
      "perm_viewOrg",
      "perm_readDocs",
      "perm_useChat",
      "perm_viewEval",
      "perm_viewMetrics",
    ],
    cannot: ["perm_debugDenied"],
  },
  SUPER_ADMIN: {
    can: [
      "perm_adminOrg",
      "perm_manageMembers",
      "perm_manageDocs",
      "perm_orgSettings",
      "perm_viewOrg",
      "perm_readDocs",
      "perm_useChat",
      "perm_viewEval",
      "perm_viewMetrics",
      "perm_debug",
    ],
    cannot: [],
  },
  FARM_MANAGER: {
    can: [
      "perm_viewOrg",
      "perm_readDocs",
      "perm_useChat",
      "perm_viewEval",
      "perm_viewMetrics",
    ],
    cannot: [
      "perm_adminOrg",
      "perm_manageMembers",
      "perm_manageDocs",
      "perm_orgSettings",
    ],
  },
  QUALITY_CONTROLLER: {
    can: [
      "perm_viewOrg",
      "perm_readDocs",
      "perm_useChat",
      "perm_viewEval",
      "perm_viewMetrics",
    ],
    cannot: [
      "perm_adminOrg",
      "perm_manageMembers",
      "perm_manageDocs",
      "perm_orgSettings",
    ],
  },
  LOGISTICS_OPERATOR: {
    can: [
      "perm_viewOrg",
      "perm_readDocs",
      "perm_useChat",
      "perm_viewEval",
      "perm_viewMetrics",
    ],
    cannot: [
      "perm_adminOrg",
      "perm_manageMembers",
      "perm_manageDocs",
      "perm_orgSettings",
    ],
  },
  USER: {
    can: ["perm_viewOrg", "perm_readDocs", "perm_useChat", "perm_viewEval"],
    cannot: [
      "perm_adminOrg",
      "perm_manageMembers",
      "perm_manageDocs",
      "perm_orgSettings",
      "perm_viewMetrics",
    ],
  },
  MEMBER: {
    can: ["perm_viewOrg", "perm_readDocs", "perm_useChat", "perm_viewEval"],
    cannot: [
      "perm_adminOrg",
      "perm_manageMembers",
      "perm_manageDocs",
      "perm_orgSettings",
      "perm_viewMetrics",
    ],
  },
  VIEWER: {
    can: [
      "perm_viewOrg",
      "perm_readDocsViewer",
      "perm_useChat",
      "perm_viewEvalReadOnly",
    ],
    cannot: [
      "perm_adminOrg",
      "perm_manageMembers",
      "perm_manageDocs",
      "perm_orgSettings",
      "perm_manageEvalDenied",
      "perm_viewMetrics",
    ],
  },
};

function resolveRoleKey(roleName?: string | null): RoleKey | null {
  const key = (roleName || "").trim().toUpperCase();
  if (ROLE_KEYS.includes(key as RoleKey)) return key as RoleKey;
  const lower = (roleName || "").trim().toLowerCase();
  const alias: Record<string, RoleKey> = {
    admin: "ORG_ADMIN",
    org_admin: "ORG_ADMIN",
    super_admin: "SUPER_ADMIN",
    farm_manager: "FARM_MANAGER",
    quality_controller: "QUALITY_CONTROLLER",
    logistics_operator: "LOGISTICS_OPERATOR",
    user: "USER",
    member: "MEMBER",
    viewer: "VIEWER",
  };
  return alias[lower] ?? null;
}

export function roleGuide(
  t: TranslateFn,
  roleName?: string | null,
): RoleGuide {
  const key = resolveRoleKey(roleName);
  if (key) {
    const perms = ROLE_PERMISSIONS[key];
    return {
      label: t(`roles.${key}_label`),
      summary: t(`roles.${key}_summary`),
      can: perms.can.map((perm) => t(`roles.${perm}`)),
      cannot: perms.cannot.map((perm) => t(`roles.${perm}`)),
    };
  }
  return {
    label: roleName || t("roles.defaultLabel"),
    summary: t("roles.defaultSummary"),
    can: [
      t("roles.perm_viewOrg"),
      t("roles.perm_readDocs"),
      t("roles.perm_useChat"),
      t("roles.perm_viewEval"),
    ],
    cannot: [
      t("roles.perm_adminOrg"),
      t("roles.perm_manageMembers"),
      t("roles.perm_manageDocs"),
      t("roles.perm_orgSettings"),
    ],
  };
}

/* --- lib/queryKeys.ts --- */
export const queryKeys = {
  organizations: ["organizations"] as const,
  knowledgeBases: (orgId: string, departmentId?: string) =>
    ["knowledge-bases", orgId, departmentId ?? "accessible"] as const,
  documents: (kbId: string) => ["documents", kbId] as const,
  datasets: (orgId: string, departmentId?: string) =>
    ["datasets", orgId, departmentId ?? "all"] as const,
  tenants: ["tenants"] as const,
  conversations: ["conversations"] as const,
  chromaDocuments: ["chroma", "documents"] as const,
  evaluationTests: ["evaluation", "tests"] as const,
  humanReviews: (orgId: string, status: string, source: string) =>
    ["human-reviews", orgId, status, source] as const,
  evaluationHistory: (orgId: string) =>
    ["evaluation", "history", orgId] as const,
  evaluationEmbeddingModels: (orgId: string) =>
    ["evaluation", "embedding-models", orgId] as const,
  evaluationCatalog: (orgId: string, datasetId: string) =>
    ["evaluation", "catalog", orgId, datasetId] as const,
  evaluationConfigs: (orgId: string, datasetId: string) =>
    ["evaluation", "configs", orgId, datasetId] as const,
  evaluationDataset: (orgId: string, datasetId: string) =>
    ["evaluation", "dataset", orgId, datasetId] as const,
  knowledgeMap: (orgId: string, kbId?: string | null) =>
    ["knowledge-map", orgId, kbId ?? "all"] as const,
  orgMembers: (orgId: string) => ["organization", orgId, "members"] as const,
  orgDepartments: (orgId: string) =>
    ["organization", orgId, "departments"] as const,
  roles: ["roles"] as const,
  fieldNotebook: (orgId: string, from: string, to: string) =>
    ["field-notebook", orgId, from, to] as const,
  analytics: (userId: string) => ["analytics", userId] as const,
};

/* --- lib/uploads.ts --- */
export const DOCUMENT_ACCEPT =
  ".pdf,.txt,.md,.docx,.csv,.mp4,.webm,.mov,.mkv,.avi,.mpeg,.mpg,.m4v,video/mp4,video/webm";

export const MAX_DOCUMENT_BYTES = 100 * 1024 * 1024;

/* --- lib/projects.ts --- */
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

