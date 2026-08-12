export const queryKeys = {
  organizations: ["organizations"] as const,
  knowledgeBases: (orgId: string) => ["knowledge-bases", orgId] as const,
  documents: (kbId: string) => ["documents", kbId] as const,
  crops: ["crops"] as const,
  recogidaMapa: ["recogida", "mapa"] as const,
  tenants: ["tenants"] as const,
  conversations: ["conversations"] as const,
  logisticsShipments: ["logistics", "shipments"] as const,
  logisticsCatalog: ["logistics", "catalog"] as const,
  logisticsFleet: ["logistics", "fleet"] as const,
  chromaDocuments: ["chroma", "documents"] as const,
  evaluationTests: ["evaluation", "tests"] as const,
  knowledgeMap: (orgId: string, kbId?: string | null) =>
    ["knowledge-map", orgId, kbId ?? "all"] as const,
  orgMembers: (orgId: string) => ["organization", orgId, "members"] as const,
  orgDepartments: (orgId: string) =>
    ["organization", orgId, "departments"] as const,
  roles: ["roles"] as const,
  forecastAnalysis: (crop: string, island: string) =>
    ["forecast", "analysis", crop, island] as const,
};
