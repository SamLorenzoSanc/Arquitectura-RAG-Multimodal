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
