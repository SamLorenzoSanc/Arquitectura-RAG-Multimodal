import api from "@/api";
import type {
  EvaluationBankItem,
  EvaluationCatalog,
  EvaluationConfig,
  EvaluationConfigInput,
  EvaluationRun,
  ProbeChunk,
  RagDatasetDetail,
  RetrievalExperimentRun,
  RetrievalStrategy,
  RetrievalStrategyComparison,
  RagRuntimeConfig,
} from "@/types/evaluation";

function headers(organizationId: string) {
  return { "X-Organization-ID": organizationId };
}

class EvaluationService {
  async catalog(
    organizationId: string,
    datasetId: string,
  ): Promise<EvaluationCatalog> {
    const { data } = await api.get<EvaluationCatalog>("/evaluation/catalog", {
      params: { dataset_id: datasetId },
      headers: headers(organizationId),
    });
    return data;
  }

  async dataset(
    organizationId: string,
    datasetId: string,
  ): Promise<RagDatasetDetail> {
    const { data } = await api.get<RagDatasetDetail>(`/datasets/${datasetId}`, {
      params: { limit: 100 },
      headers: headers(organizationId),
    });
    return data;
  }

  async configs(
    organizationId: string,
    datasetId: string,
  ): Promise<EvaluationConfig[]> {
    const { data } = await api.get<{ data: EvaluationConfig[] }>(
      "/evaluation/configs",
      {
        params: { dataset_id: datasetId },
        headers: headers(organizationId),
      },
    );
    return data.data;
  }

  async createConfig(
    organizationId: string,
    input: EvaluationConfigInput,
  ): Promise<EvaluationConfig> {
    const { data } = await api.post<EvaluationConfig>(
      "/evaluation/configs",
      input,
      { headers: headers(organizationId) },
    );
    return data;
  }

  async updateConfig(
    organizationId: string,
    configId: string,
    input: Partial<EvaluationConfigInput>,
  ): Promise<EvaluationConfig> {
    const { data } = await api.put<EvaluationConfig>(
      `/evaluation/configs/${configId}`,
      input,
      { headers: headers(organizationId) },
    );
    return data;
  }

  async run(
    organizationId: string,
    configId: string,
    force = false,
  ): Promise<EvaluationRun> {
    const { data } = await api.post<EvaluationRun>(
      `/evaluation/configs/${configId}/run`,
      { force },
      { headers: headers(organizationId) },
    );
    return data;
  }

  async compareRetrievalStrategies(
    organizationId: string,
    input: {
      strategies: RetrievalStrategy[];
      embedding_model: string;
      distance_metric: string;
      top_k: number;
      organization_id: string;
      department_id?: string | null;
      knowledge_base_id?: string | null;
      temperature?: number;
    },
  ): Promise<RetrievalStrategyComparison> {
    const { data } = await api.post<RetrievalStrategyComparison>(
      "/chat/evaluation/experiments/strategies",
      input,
      { headers: headers(organizationId), timeout: 900000 },
    );
    return data;
  }

  async retrievalExperimentHistory(
    organizationId: string,
  ): Promise<RetrievalExperimentRun[]> {
    const { data } = await api.get<RetrievalExperimentRun[]>(
      "/chat/evaluation/experiments",
      { headers: headers(organizationId) },
    );
    return data.filter((run) => run.experiment_type === "retrieval_strategy");
  }

  async retrievalHistory(
    organizationId: string,
  ): Promise<RetrievalExperimentRun[]> {
    const { data } = await api.get<RetrievalExperimentRun[]>(
      "/chat/evaluation/history",
      {
        params: { organization_id: organizationId },
        headers: headers(organizationId),
      },
    );
    return Array.isArray(data) ? data : [];
  }

  async runRetrievalEvaluation(
    organizationId: string,
    knowledgeBaseId?: string | null,
    temperature = 0,
  ): Promise<RetrievalExperimentRun> {
    const { data } = await api.post<RetrievalExperimentRun>(
      "/chat/evaluation/experiments",
      {
        embedding_model: "nomic-embed-text",
        distance_metric: "cosine",
        top_k: 3,
        knowledge_base_id: knowledgeBaseId || undefined,
        persist: true,
        temperature,
      },
      {
        params: { organization_id: organizationId },
        headers: headers(organizationId),
        timeout: 900000,
      },
    );
    return data;
  }

  async probeRetrieval(
    organizationId: string,
    question: string,
    knowledgeBaseId?: string | null,
  ): Promise<ProbeChunk[]> {
    const { data } = await api.post<{ chunks: ProbeChunk[] }>(
      "/chat/simulator/search",
      {
        question,
        knowledge_base_id: knowledgeBaseId || undefined,
        evaluation_mode: true,
        distance_metric: "cosine",
      },
      {
        params: { organization_id: organizationId },
        headers: headers(organizationId),
      },
    );
    return data.chunks ?? [];
  }

  async saveValidatedQuestion(
    organizationId: string,
    payload: {
      question: string;
      selected_chunk_ids: string[];
      flags: { different_info: boolean; out_of_knowledge: boolean };
    },
  ): Promise<void> {
    await api.post("/chat/simulator/save-dataset", payload, {
      params: { organization_id: organizationId },
      headers: headers(organizationId),
    });
  }

  async listQuestionBank(
    organizationId: string,
  ): Promise<EvaluationBankItem[]> {
    const { data } = await api.get<{ tests: EvaluationBankItem[] }>(
      "/chat/evaluation/tests",
      {
        params: { organization_id: organizationId },
        headers: headers(organizationId),
      },
    );
    return data.tests ?? [];
  }

  async embeddingModels(
    organizationId: string,
  ): Promise<{ indexed: string[]; default: string; note: string }> {
    const { data } = await api.get<{
      indexed: string[];
      default: string;
      note: string;
    }>("/chat/evaluation/embedding-models", {
      headers: headers(organizationId),
    });
    return data;
  }

  async runtimeConfig(): Promise<RagRuntimeConfig> {
    const { data } = await api.get<RagRuntimeConfig>(
      "/chat/evaluation/runtime-config",
    );
    return data;
  }
}

export default new EvaluationService();
