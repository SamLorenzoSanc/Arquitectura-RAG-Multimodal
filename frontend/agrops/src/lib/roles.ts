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
