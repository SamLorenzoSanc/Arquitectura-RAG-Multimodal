import api from "@/api";
import type {
  EvaluationCatalog,
  EvaluationConfig,
  EvaluationConfigInput,
  EvaluationRun,
  RagDatasetDetail,
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
}

export default new EvaluationService();
