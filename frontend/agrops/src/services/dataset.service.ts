import api from "@/api";
import type {
  CreateDatasetInput,
  DatasetAddColumnInput,
  DatasetPreview,
  DatasetTrace,
  DemoCatalogItem,
  GuardrailRunResult,
  RagDataset,
  SyntheticConfig,
  UpdateDatasetInput,
} from "@/types/dataset";

type BackendDataset = Partial<RagDataset> & {
  id: string;
  name: string;
  source_type?: string;
  imported_rows?: number;
  data?: RagDataset[];
};

const SOURCE_ALIASES: Record<string, RagDataset["source"]> = {
  file: "file",
  upload: "file",
  document: "file",
  logs: "logs",
  log: "logs",
  synthetic: "synthetic",
  demo: "demo",
};

function normalizeDataset(
  item: BackendDataset,
  fallback?: Partial<RagDataset>,
): RagDataset {
  const rawSource = String(
    item.source ?? item.source_type ?? fallback?.source ?? "file",
  ).toLowerCase();
  const source = SOURCE_ALIASES[rawSource] ?? "file";
  return {
    ...fallback,
    ...item,
    id: item.id,
    name: item.name,
    source,
    status: item.status ?? fallback?.status ?? "ready",
    row_count: item.row_count ?? item.imported_rows ?? fallback?.row_count ?? 0,
    knowledge_base_id:
      item.knowledge_base_id ?? fallback?.knowledge_base_id ?? "",
    department_ids:
      item.department_ids ??
      item.departments?.map((department) => department.id) ??
      fallback?.department_ids ??
      [],
  };
}

function unwrapList(
  data:
    | RagDataset[]
    | { data?: BackendDataset[]; items?: BackendDataset[]; datasets?: BackendDataset[] },
) {
  if (Array.isArray(data)) return data;
  return (data.data ?? data.items ?? data.datasets ?? []).map((item) =>
    normalizeDataset(item),
  );
}

function organizationHeaders(organizationId: string) {
  return { "X-Organization-ID": organizationId };
}

function syntheticPayload(
  config: SyntheticConfig,
  base: {
    name: string;
    knowledge_base_id: string;
    department_ids: string[];
  },
) {
  return {
    name: base.name,
    knowledge_base_id: base.knowledge_base_id,
    department_ids: base.department_ids,
    limit: config.rows,
    questions: [config.topic].filter(Boolean),
    document_ids: [],
    enqueue_hitl: true,
    description: config.instructions,
  };
}

class DatasetService {
  async list(
    organizationId: string,
    departmentId?: string,
  ): Promise<RagDataset[]> {
    const { data } = await api.get<
      | RagDataset[]
      | { data?: BackendDataset[]; items?: BackendDataset[]; datasets?: BackendDataset[] }
    >("/datasets", {
      params: {
        organization_id: organizationId,
        department_id: departmentId || undefined,
      },
      headers: organizationHeaders(organizationId),
    });
    return unwrapList(data);
  }

  async previewFile(file: File, organizationId: string): Promise<DatasetPreview> {
    const body = new FormData();
    body.append("file", file);
    const { data } = await api.post<DatasetPreview>("/datasets/preview", body, {
      headers: organizationHeaders(organizationId),
    });
    return data;
  }

  async previewSynthetic(
    config: SyntheticConfig,
    base: { name: string; knowledge_base_id: string; department_ids: string[] },
    organizationId: string,
  ): Promise<DatasetPreview> {
    const { data } = await api.post<DatasetPreview>(
      "/datasets/synthetic/preview",
      syntheticPayload(config, base),
      { headers: organizationHeaders(organizationId) },
    );
    return data;
  }

  async demoCatalog(organizationId: string): Promise<DemoCatalogItem[]> {
    const { data } = await api.get<{ data?: DemoCatalogItem[] } | DemoCatalogItem[]>(
      "/datasets/demo-catalog",
      { headers: organizationHeaders(organizationId) },
    );
    return Array.isArray(data) ? data : (data.data ?? []);
  }

  async create(input: CreateDatasetInput): Promise<RagDataset> {
    if (input.source === "file" || input.source === "logs") {
      const body = new FormData();
      body.append("file", input.file);
      body.append("name", input.name);
      body.append("knowledge_base_id", input.knowledge_base_id);
      body.append("department_ids", JSON.stringify(input.department_ids));
      body.append("mapping", JSON.stringify(input.mapping));
      body.append("source_type", input.source === "logs" ? "logs" : "document");
      const { data } = await api.post<BackendDataset>("/datasets/import", body, {
        headers: organizationHeaders(input.organization_id),
      });
      return normalizeDataset(data, {
        source: input.source,
        knowledge_base_id: input.knowledge_base_id,
        department_ids: input.department_ids,
      });
    }

    if (input.source === "demo") {
      const { data } = await api.post<BackendDataset>(
        "/datasets/demo",
        {
          catalog_id: input.catalogId,
          name: input.name,
          knowledge_base_id: input.knowledge_base_id,
          department_ids: input.department_ids,
        },
        { headers: organizationHeaders(input.organization_id) },
      );
      return normalizeDataset(data, {
        source: "demo",
        knowledge_base_id: input.knowledge_base_id,
        department_ids: input.department_ids,
      });
    }

    if (input.source === "synthetic") {
      const { data } = await api.post<BackendDataset>(
        "/datasets/synthetic",
        syntheticPayload(input.synthetic, input),
        { headers: organizationHeaders(input.organization_id) },
      );
      return normalizeDataset(data, {
        source: "synthetic",
        knowledge_base_id: input.knowledge_base_id,
        department_ids: input.department_ids,
      });
    }

    throw new Error("Origen de dataset no soportado");
  }

  async get(
    datasetId: string,
    organizationId: string,
    limit = 100,
  ): Promise<{
    dataset: RagDataset;
    rows: Array<Record<string, unknown>>;
    offset: number;
    limit: number;
  }> {
    const { data } = await api.get<{
      dataset: BackendDataset;
      rows: Array<Record<string, unknown>>;
      offset: number;
      limit: number;
    }>(`/datasets/${datasetId}`, {
      params: { limit },
      headers: organizationHeaders(organizationId),
    });
    return {
      ...data,
      dataset: normalizeDataset(data.dataset),
    };
  }

  async addRows(
    datasetId: string,
    organizationId: string,
    file: File,
  ): Promise<{ imported_rows: number; rejected_rows: number; row_count: number }> {
    const body = new FormData();
    body.append("file", file);
    const { data } = await api.post<{
      imported_rows: number;
      rejected_rows: number;
      row_count: number;
    }>(`/datasets/${datasetId}/rows`, body, {
      headers: organizationHeaders(organizationId),
    });
    return data;
  }

  async update(
    datasetId: string,
    organizationId: string,
    input: UpdateDatasetInput,
  ): Promise<RagDataset> {
    const { data } = await api.patch<BackendDataset>(
      `/datasets/${datasetId}`,
      input,
      { headers: organizationHeaders(organizationId) },
    );
    return normalizeDataset(data);
  }

  async remove(datasetId: string, organizationId: string): Promise<void> {
    await api.delete(`/datasets/${datasetId}`, {
      headers: organizationHeaders(organizationId),
    });
  }

  async traces(
    datasetId: string,
    organizationId: string,
    limit = 100,
  ): Promise<{ count: number; data: DatasetTrace[] }> {
    const { data } = await api.get<{ count: number; data: DatasetTrace[] }>(
      `/datasets/${datasetId}/traces`,
      {
        params: { limit },
        headers: organizationHeaders(organizationId),
      },
    );
    return data;
  }

  async importTraces(
    datasetId: string,
    organizationId: string,
    limit = 50,
  ): Promise<{ imported_rows: number; rejected_rows: number; row_count: number }> {
    const { data } = await api.post<{
      imported_rows: number;
      rejected_rows: number;
      row_count: number;
    }>(
      `/datasets/${datasetId}/traces/import`,
      { limit },
      { headers: organizationHeaders(organizationId) },
    );
    return data;
  }

  async addColumn(
    datasetId: string,
    organizationId: string,
    input: DatasetAddColumnInput,
  ): Promise<{ column_name: string; filled_rows: number; errors: number }> {
    const { data } = await api.post<{
      column_name: string;
      filled_rows: number;
      errors: number;
    }>(`/datasets/${datasetId}/columns`, input, {
      headers: organizationHeaders(organizationId),
    });
    return data;
  }

  async runGuardrails(
    datasetId: string,
    organizationId: string,
    limit = 100,
  ): Promise<GuardrailRunResult> {
    const { data } = await api.post<GuardrailRunResult>(
      `/datasets/${datasetId}/guardrails`,
      { limit },
      { headers: organizationHeaders(organizationId) },
    );
    return data;
  }
}

export default new DatasetService();
