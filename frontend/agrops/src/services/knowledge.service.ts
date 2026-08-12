import api from "@/api";
import type { KnowledgeMap } from "@/types/knowledge";

export type KnowledgeBaseSummary = {
  id: string;
  tenant_id: string;
  name: string;
  description?: string | null;
  chroma_collection?: string | null;
  created_by?: string | null;
  created_at?: string;
  organization_id?: string;
};

class KnowledgeService {
  async list(organizationId: string): Promise<KnowledgeBaseSummary[]> {
    const { data } = await api.get<KnowledgeBaseSummary[]>(
      `/organization/${organizationId}/knowledge-bases`,
    );
    return Array.isArray(data) ? data : [];
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
