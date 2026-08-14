export const queryKeys = {
  organizations: ["organizations"] as const,
  knowledgeBases: (orgId: string) => ["knowledge-bases", orgId] as const,
  documents: (kbId: string) => ["documents", kbId] as const,
  datasets: (orgId: string, departmentId?: string) =>
    ["datasets", orgId, departmentId ?? "all"] as const,
  tenants: ["tenants"] as const,
  conversations: ["conversations"] as const,
  chromaDocuments: ["chroma", "documents"] as const,
  evaluationTests: ["evaluation", "tests"] as const,
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
};
