import api from "@/api";
import type { KnowledgeMap } from "@/types/knowledge";

export type KnowledgeBaseSummary = {
  id: string;
  tenant_id: string;
  name: string;
  description?: string | null;
  use_case?: string | null;
  chroma_collection?: string | null;
  created_by?: string | null;
  created_by_name?: string | null;
  created_at?: string;
  document_count?: number;
  organization_id?: string;
  department_ids?: string[];
  knowledge_base_id?: string;
};

class KnowledgeService {
  async list(
    organizationId?: string,
    _departmentId?: string,
  ): Promise<KnowledgeBaseSummary[]> {
    const { data } = await api.get<KnowledgeBaseSummary[]>("/knowledge/", {
      params: organizationId ? { organization_id: organizationId } : undefined,
    });
    return Array.isArray(data) ? data : [];
  }

  async create(payload: {
    name: string;
    description?: string;
    use_case?: string;
    organizationId?: string;
  }): Promise<KnowledgeBaseSummary> {
    const { data } = await api.post<KnowledgeBaseSummary>(
      "/knowledge/",
      {
        name: payload.name,
        description: payload.description,
        use_case: payload.use_case,
      },
      {
        params: payload.organizationId
          ? { organization_id: payload.organizationId }
          : undefined,
      },
    );
    return data;
  }

  async get(
    knowledgeBaseId: string,
    organizationId?: string,
  ): Promise<KnowledgeBaseSummary> {
    const { data } = await api.get<KnowledgeBaseSummary>(
      `/knowledge/${knowledgeBaseId}`,
      {
        params: organizationId ? { organization_id: organizationId } : undefined,
      },
    );
    return data;
  }

  async update(
    knowledgeBaseId: string,
    payload: {
      name?: string;
      description?: string | null;
      use_case?: string;
      organizationId?: string;
    },
  ): Promise<KnowledgeBaseSummary> {
    const { data } = await api.patch<KnowledgeBaseSummary>(
      `/knowledge/${knowledgeBaseId}`,
      {
        name: payload.name,
        description: payload.description,
        use_case: payload.use_case,
      },
      {
        params: payload.organizationId
          ? { organization_id: payload.organizationId }
          : undefined,
      },
    );
    return data;
  }

  async delete(
    knowledgeBaseId: string,
    organizationId?: string,
  ): Promise<{ status: string; id: string }> {
    const { data } = await api.delete<{ status: string; id: string }>(
      `/knowledge/${knowledgeBaseId}`,
      {
        params: organizationId ? { organization_id: organizationId } : undefined,
      },
    );
    return data;
  }

  async getCurrent(organizationId?: string): Promise<KnowledgeBaseSummary> {
    const { data } = await api.get<KnowledgeBaseSummary>("/knowledge/current", {
      params: organizationId ? { organization_id: organizationId } : undefined,
    });
    return data;
  }

  async getMap(
    organizationId: string,
    options?: {
      preview?: boolean;
      knowledgeBaseId?: string;
      similarityThreshold?: number;
      maxNeighbors?: number;
    },
  ): Promise<KnowledgeMap> {
    const params: Record<string, string | number | boolean> = {};
    if (options?.preview) params.preview = true;
    if (options?.knowledgeBaseId) params.knowledge_base_id = options.knowledgeBaseId;
    if (options?.similarityThreshold != null) {
      params.similarity_threshold = options.similarityThreshold;
    }
    if (options?.maxNeighbors != null) {
      params.max_neighbors = options.maxNeighbors;
    }

    const { data } = await api.get<KnowledgeMap>(
      `/organization/${organizationId}/knowledge-map`,
      { params },
    );
    return data;
  }
}

export default new KnowledgeService();
