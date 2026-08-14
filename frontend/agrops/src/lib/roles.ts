export interface RoleGuide {
  label: string;
  summary: string;
  can: string[];
  cannot: string[];
}

const SHARED_CONSULTATION = [
  "Consultar la organización y los departamentos",
  "Leer documentos, datasets y bases de conocimiento",
  "Usar el chat RAG",
  "Ver y lanzar evaluaciones RAG",
];

const ADMIN_ONLY = [
  "Crear o desactivar la organización y los inquilinos",
  "Añadir o quitar miembros y departamentos",
  "Crear o borrar bases de conocimiento",
  "Cambiar ajustes de la organización",
];

export const ROLE_GUIDES: Record<string, RoleGuide> = {
  ORG_ADMIN: {
    label: "Administrador de organización",
    summary:
      "Responsable de la cooperativa: configura el workspace y tiene acceso completo al RAG.",
    can: [
      ...ADMIN_ONLY,
      ...SHARED_CONSULTATION,
      "Ver métricas de uso",
    ],
    cannot: ["Acceso de depuración interna del sistema"],
  },
  SUPER_ADMIN: {
    label: "Superadministrador",
    summary: "Mismos poderes que el administrador, más depuración interna. Reservado al equipo técnico.",
    can: [
      ...ADMIN_ONLY,
      ...SHARED_CONSULTATION,
      "Ver métricas de uso",
      "Acceso de depuración interna",
    ],
    cannot: [],
  },
  FARM_MANAGER: {
    label: "Gestor de fincas / producción",
    summary:
      "Técnico de campo: consulta el conocimiento de producción, riego y cuaderno, sin administrar la org.",
    can: [...SHARED_CONSULTATION, "Ver métricas de uso"],
    cannot: ADMIN_ONLY,
  },
  QUALITY_CONTROLLER: {
    label: "Controlador de calidad",
    summary:
      "Calidad e IGP: consulta normativa, trazabilidad y evaluaciones, sin gestionar miembros.",
    can: [...SHARED_CONSULTATION, "Ver métricas de uso"],
    cannot: ADMIN_ONLY,
  },
  LOGISTICS_OPERATOR: {
    label: "Operador logístico",
    summary:
      "Empaquetado y comercialización operativa: consulta el RAG de tránsito y mercado, sin administrar.",
    can: [...SHARED_CONSULTATION, "Ver métricas de uso"],
    cannot: ADMIN_ONLY,
  },
  USER: {
    label: "Usuario estándar",
    summary:
      "Socio o personal de consulta: puede preguntar al asistente y ver datasets, sin métricas ni administración.",
    can: SHARED_CONSULTATION,
    cannot: [...ADMIN_ONLY, "Ver métricas de uso"],
  },
  MEMBER: {
    label: "Miembro",
    summary: "Equivalente al usuario estándar: consulta RAG y evaluaciones, sin administrar la cooperativa.",
    can: SHARED_CONSULTATION,
    cannot: [...ADMIN_ONLY, "Ver métricas de uso"],
  },
  VIEWER: {
    label: "Lector",
    summary: "Solo lectura: chat y documentos, sin gestionar evaluaciones ni métricas.",
    can: [
      "Consultar la organización y los departamentos",
      "Leer documentos y bases de conocimiento",
      "Usar el chat RAG",
      "Ver evaluaciones (sin gestionarlas)",
    ],
    cannot: [...ADMIN_ONLY, "Gestionar evaluaciones", "Ver métricas de uso"],
  },
};

export function roleGuide(roleName?: string | null): RoleGuide {
  const key = (roleName || "").trim().toUpperCase();
  if (ROLE_GUIDES[key]) return ROLE_GUIDES[key];
  const lower = (roleName || "").trim().toLowerCase();
  const alias: Record<string, string> = {
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
  const mapped = alias[lower];
  if (mapped && ROLE_GUIDES[mapped]) return ROLE_GUIDES[mapped];
  return {
    label: roleName || "Rol",
    summary: "Rol de la organización. Revisa con el administrador qué alcance tiene.",
    can: SHARED_CONSULTATION,
    cannot: ADMIN_ONLY,
  };
}
