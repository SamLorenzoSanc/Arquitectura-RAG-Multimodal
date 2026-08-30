import api from "@/api";
import type { ChatRequest, ChatResponse, ChatStreamEvent, ConversationHistoryDetail, ConversationResponse, UserConversationHistoryResponse, CreateDatasetInput, DatasetAddColumnInput, DatasetPreview, DatasetTrace, DemoCatalogItem, GuardrailRunResult, RagDataset, SyntheticConfig, UpdateDatasetInput, Department, DocumentChunksResponse, DocumentItem, IngestProgress, IndexState, IndexTasksResponse, EvaluationBankItem, EvaluationCatalog, EvaluationConfig, EvaluationConfigInput, EvaluationRun, ProbeChunk, RagDatasetDetail, RetrievalExperimentRun, RetrievalStrategy, RetrievalStrategyComparison, DistanceMetricsComparison, RagRuntimeConfig, KnowledgeBaseSummary, KnowledgeMap, Organization, Tenant, TenantListResponse, CreateTenantRequest, UpdateTenantRequest } from "@/types";

/* --- auth.service.ts --- */

export interface LoginRequest {
    email: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    expires_in: number;
}

export async function login(request: LoginRequest) {

    const response = await api.post<LoginResponse>(
        "/auth/login",
        request
    );

    return response.data;
}

export async function register(data: unknown) {

    const response = await api.post(
        "/auth/register",
        data
    );

    return response.data;
}

/* --- account.service.ts --- */

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  job_title?: string | null;
  phone?: string | null;
  island?: string | null;
  municipality?: string | null;
  bio?: string | null;
  crop_focus?: string | null;
  preferred_language?: string;
  notify_email?: boolean;
  notify_whatsapp?: boolean;
  has_avatar?: boolean;
}

export type TokenKind = "access" | "api_key";

export interface AccessTokenItem {
  id: string;
  name: string;
  kind: TokenKind;
  token_prefix: string;
  expires_at?: string | null;
  last_used_at?: string | null;
  revoked_at?: string | null;
  created_at?: string;
}

export interface CreatedToken extends AccessTokenItem {
  token: string;
  token_type: string;
  note?: string;
  prefix?: string;
}

export interface AccountUsage {
  documents: number;
  conversations: number;
  api_calls: number;
  active_tokens: number;
}

export interface AnalyticsTotals {
  documents: number;
  conversations: number;
  questions: number;
  projects: number;
  organizations: number;
  api_calls: number;
  active_tokens: number;
  support_tickets: number;
  documents_week: number;
  questions_week: number;
}

export interface AnalyticsActivityDay {
  day: string;
  documents: number;
  questions: number;
}

export interface AnalyticsDocument {
  id: string;
  filename: string;
  project_name?: string | null;
  uploaded_at?: string | null;
}

export interface AnalyticsConversation {
  id: string;
  title: string;
  message_count: number;
  updated_at?: string | null;
}

export interface AnalyticsProject {
  id: string;
  name: string;
  use_case?: string | null;
  document_count: number;
  created_at?: string | null;
}

export interface AnalyticsEvent {
  kind: "document" | "conversation" | "project" | string;
  title: string;
  created_at?: string | null;
  ref_id?: string | null;
}

export interface AccountAnalytics {
  user_id: string;
  user_name?: string | null;
  totals: AnalyticsTotals;
  activity: AnalyticsActivityDay[];
  recent_documents: AnalyticsDocument[];
  recent_conversations: AnalyticsConversation[];
  projects: AnalyticsProject[];
  timeline: AnalyticsEvent[];
}

export interface ManagedUser {
  id: string;
  name: string;
  email: string;
  role?: string | null;
  active?: boolean;
  is_self?: boolean;
}

export interface ManagedUsersPage {
  is_admin: boolean;
  total: number;
  items: ManagedUser[];
}

export interface AccountProject {
  id: string;
  name: string;
  description?: string | null;
  use_case?: string | null;
  document_count?: number;
  owned?: boolean;
  created_at?: string;
}

export interface SupportTicket {
  id: string;
  subject: string;
  message: string;
  status: string;
  created_at: string;
  author_name?: string;
  author_email?: string;
  organization_name?: string;
}

export interface OrgAdmin {
  id: string;
  name: string;
  organization_name?: string;
}

class AccountService {
  async getProfile(userId?: string, organizationId?: string) {
    const { data } = await api.get<UserProfile>("/account/profile", {
      params: {
        user_id: userId || undefined,
        organization_id: organizationId || undefined,
      },
    });
    return data;
  }

  async updateProfile(
    payload: Partial<UserProfile> & { name?: string },
    userId?: string,
    organizationId?: string,
  ) {
    const { data } = await api.patch<UserProfile>("/account/profile", payload, {
      params: {
        user_id: userId || undefined,
        organization_id: organizationId || undefined,
      },
    });
    return data;
  }

  async uploadAvatar(file: File, userId?: string, organizationId?: string) {
    const form = new FormData();
    form.append("file", file);
    const { data } = await api.post<UserProfile>("/account/profile/avatar", form, {
      params: {
        user_id: userId || undefined,
        organization_id: organizationId || undefined,
      },
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  }

  async deleteAvatar(userId?: string, organizationId?: string) {
    const { data } = await api.delete<UserProfile>("/account/profile/avatar", {
      params: {
        user_id: userId || undefined,
        organization_id: organizationId || undefined,
      },
    });
    return data;
  }

  async avatarObjectUrl(userId?: string) {
    const { data } = await api.get("/account/profile/avatar", {
      params: userId ? { user_id: userId } : undefined,
      responseType: "blob",
    });
    return URL.createObjectURL(data);
  }

  async listTokens(kind?: TokenKind) {
    const { data } = await api.get<AccessTokenItem[]>("/account/tokens", {
      params: kind ? { kind } : undefined,
    });
    return data;
  }

  async createToken(params: {
    name: string;
    kind: TokenKind;
    expires_days?: number;
  }) {
    const { data } = await api.post<CreatedToken>("/account/tokens", params);
    return data;
  }

  async revokeToken(tokenId: string) {
    const { data } = await api.delete(`/account/tokens/${tokenId}`);
    return data;
  }

  async usage(userId?: string, organizationId?: string) {
    const { data } = await api.get<AccountUsage>("/account/usage", {
      params: {
        user_id: userId || undefined,
        organization_id: organizationId || undefined,
      },
    });
    return data;
  }

  async analytics(userId?: string, organizationId?: string) {
    const { data } = await api.get<AccountAnalytics>("/account/analytics", {
      params: {
        user_id: userId || undefined,
        organization_id: organizationId || undefined,
      },
    });
    return data;
  }

  async listUsers(organizationId?: string, q = "") {
    const { data } = await api.get<ManagedUsersPage>("/account/users", {
      params: {
        organization_id: organizationId || undefined,
        q: q || undefined,
        limit: 50,
      },
    });
    return data;
  }

  async listProjects(organizationId: string, userId?: string) {
    const { data } = await api.get<{ user_id: string; items: AccountProject[] }>(
      "/account/projects",
      {
        params: {
          organization_id: organizationId,
          user_id: userId || undefined,
        },
      },
    );
    return data;
  }

  async admins(organizationId?: string) {
    const { data } = await api.get<OrgAdmin[]>("/account/admins", {
      params: organizationId ? { organization_id: organizationId } : undefined,
    });
    return data;
  }

  async supportTickets() {
    const { data } = await api.get<{
      is_admin: boolean;
      tickets: SupportTicket[];
    }>("/account/support");
    return data;
  }

  async createTicket(payload: {
    subject: string;
    message: string;
    organization_id?: string;
  }) {
    const { data } = await api.post("/account/support", payload);
    return data;
  }
}

const accountServiceInstance = new AccountService();
export { accountServiceInstance as AccountService };

/* --- chat.service.ts --- */


const API_BASE =
    import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

class ChatService {
    async send(request: ChatRequest): Promise<ChatResponse> {
        console.log("=== CHAT REQUEST ===");
        console.log(request);

        try {
            const { data } = await api.post<ChatResponse>("/chat/", request);
            console.log("=== CHAT RESPONSE ===");
            console.log(data);
            return data;
        } catch (error: any) {
            console.error("CHAT ERROR", error.response?.data ?? error.message);
            throw new Error(
                typeof error.response?.data?.detail === "string" &&
                    !/sqlalchemy|asyncpg|vector dimensions|\[SQL:/i.test(
                        error.response.data.detail,
                    )
                    ? error.response.data.detail
                    : "No se pudo consultar la documentación.",
            );
        }
    }

    /**
     * Chat con Server-Sent Events: proceso del agente + tokens en vivo.
     */
    async stream(
        request: ChatRequest,
        handlers: {
            onEvent: (event: ChatStreamEvent) => void;
            signal?: AbortSignal;
        },
    ): Promise<ChatResponse> {
        const token = localStorage.getItem("token");
        const response = await fetch(`${API_BASE}/chat/stream`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify(request),
            signal: handlers.signal,
        });

        if (!response.ok) {
            let detail = "No se pudo consultar la documentación.";
            try {
                const errBody = await response.json();
                if (typeof errBody?.detail === "string") {
                    detail = errBody.detail;
                }
            } catch {
                /* ignore */
            }
            if (response.status === 401) {
                localStorage.removeItem("token");
                window.location.href = "/login";
            }
            throw new Error(detail);
        }

        if (!response.body) {
            throw new Error("El servidor no devolvió un stream.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalPayload: ChatResponse | null = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const parts = buffer.split("\n\n");
            buffer = parts.pop() ?? "";

            for (const part of parts) {
                const lines = part
                    .split("\n")
                    .map((l) => l.trim())
                    .filter(Boolean);
                for (const line of lines) {
                    if (!line.startsWith("data:")) continue;
                    const raw = line.slice(5).trim();
                    if (!raw || raw === "[DONE]") continue;
                    try {
                        const event = JSON.parse(raw) as ChatStreamEvent;
                        handlers.onEvent(event);
                        if (event.type === "done" && event.payload) {
                            finalPayload = event.payload;
                        }
                        if (event.type === "error") {
                            throw new Error(
                                event.detail ||
                                    "No se pudo completar la consulta.",
                            );
                        }
                    } catch (err) {
                        if (err instanceof SyntaxError) continue;
                        throw err;
                    }
                }
            }
        }

        if (!finalPayload) {
            throw new Error("El stream terminó sin respuesta final.");
        }
        return finalPayload;
    }

    async getConversation(
        conversationId: string,
    ): Promise<ConversationResponse> {
        try {
            const { data } = await api.get<ConversationResponse>(
                `/chat/${conversationId}`,
            );
            return data;
        } catch (error: any) {
            console.error(
                "GET CONVERSATION ERROR",
                error.response?.data ?? error.message,
            );
            throw new Error("No se pudo cargar la conversación");
        }
    }

    async deleteConversation(conversationId: string): Promise<void> {
        try {
            await api.delete(`/chat/${conversationId}`);
        } catch (error: any) {
            console.error(
                "DELETE CONVERSATION ERROR",
                error.response?.data ?? error.message,
            );
            throw new Error("No se pudo eliminar la conversación");
        }
    }

    async listConversations() {
        const response = await api.get("/chat/conversations");
        return response.data;
    }

    async userHistory(params: {
        organizationId: string;
        mineOnly?: boolean;
        userId?: string | null;
        limit?: number;
    }) {
        const { data } = await api.get<UserConversationHistoryResponse>(
            "/chat/conversations/user-history",
            {
                params: {
                    organization_id: params.organizationId,
                    mine_only: params.mineOnly ?? false,
                    user_id: params.userId || undefined,
                    limit: params.limit ?? 200,
                },
                headers: { "X-Organization-ID": params.organizationId },
            },
        );
        return data;
    }

    async conversationDetail(
        conversationId: string,
        params: { organizationId: string },
    ) {
        const { data } = await api.get<ConversationHistoryDetail>(
            `/chat/conversations/${conversationId}/detail`,
            {
                params: { organization_id: params.organizationId },
                headers: { "X-Organization-ID": params.organizationId },
            },
        );
        return data;
    }

    async retrieve(question: string, knowledgeBaseId?: string) {
        try {
            const { data } = await api.post("/chat/retrieve", {
                question,
                knowledge_base_id: knowledgeBaseId || undefined,
            });
            return data;
        } catch (err: any) {
            console.error("RETRIEVE ERROR", err.response?.data ?? err.message);
            throw new Error("Error retrieving pipeline");
        }
    }
}

const chatServiceInstance = new ChatService();
export { chatServiceInstance as ChatService };

/* --- dataset.service.ts --- */

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

const datasetServiceInstance = new DatasetService();
export { datasetServiceInstance as DatasetService };

/* --- department.service.ts --- */

export interface DepartmentMember {
    id: string;
    name: string;
    email: string;
}

class DepartmentService {
    async list(
        organizationId: string
    ): Promise<Department[]> {

        const { data } = await api.get(
            `/department/organization/${organizationId}`
        );

        return data;
    }

    async getDepartments(
        departmentId: string
    ): Promise<Department> {

        const { data } = await api.get(
            `/department/${departmentId}`
        );

        return data;
    }

    async create(
        payload: {
            organization_id: string;
            name: string;
            description?: string;
        }
    ): Promise<Department> {

        const { data } = await api.post(
            "/department",
            payload
        );

        return data;
    }

    async update(
        departmentId: string,
        payload: {
            name: string;
            description?: string;
        }
    ) {

        const { data } = await api.put(
            `/department/${departmentId}`,
            payload
        );

        return data;
    }

    async delete(
        departmentId: string
    ) {

        await api.delete(
            `/department/${departmentId}`
        );

    }

    async getDepartmentMembers(
        departmentId: string
    ): Promise<DepartmentMember[]> {

        const { data } = await api.get(
            `/department/${departmentId}/members`
        );

        return data.items;
    }

    async addMember(
        departmentId: string,
        payload: {
            user_id: string;
        }
    ) {

        const { data } = await api.post(
            `/department/${departmentId}/members`,
            payload
        );

        return data;
    }

    async removeMember(
        departmentId: string,
        userId: string
    ) {

        await api.delete(
            `/department/${departmentId}/members/${userId}`
        );

    }

    async availableUsers(
        departmentId: string
    ) {

        const { data } = await api.get(
            `/department/${departmentId}/available-users`
        );

        return data.items;
    }

    async userDepartments(
        userId: string
    ): Promise<Department[]> {

        const { data } = await api.get(
            `/department/user/${userId}`
        );

        return data.items;
    }
}

const departmentServiceInstance = new DepartmentService();

export { departmentServiceInstance as DepartmentService };

export const getDepartments = departmentServiceInstance.getDepartments.bind(departmentServiceInstance);
export const getDepartmentMembers = departmentServiceInstance.getDepartmentMembers.bind(departmentServiceInstance);

/* --- document.service.ts --- */

class DocumentService {
    async list(
        knowledgeBaseId: string
    ): Promise<DocumentItem[]> {

        const response = await api.get<DocumentItem[]>(
            "/documents",
            {
                params: {
                    knowledge_base_id: knowledgeBaseId,
                },
            }
        );

        return response.data;
    }

    async upload(params: {
        knowledgeBaseId: string;
        file: File;
        title?: string;
        description?: string;
        onUploadProgress?: (percent: number) => void;
    }): Promise<{
        id: string;
        filename: string;
        status: string;
        chunks?: number;
        embedding_model?: string | null;
        message?: string;
        processing_status?: string;
        error?: string | null;
        progress?: IngestProgress | null;
    }> {
        const form = new FormData();
        form.append("knowledge_base_id", params.knowledgeBaseId);
        form.append("file", params.file);
        if (params.title) form.append("title", params.title);
        if (params.description) form.append("description", params.description);
        const response = await api.post("/documents", form, {
            headers: { "Content-Type": "multipart/form-data" },
            timeout: 600_000,
            onUploadProgress: (event) => {
                if (!params.onUploadProgress) return;
                const total = event.total || params.file.size || 0;
                if (!total) return;
                params.onUploadProgress(
                    Math.min(100, Math.round((event.loaded / total) * 100)),
                );
            },
        });
        return response.data;
    }

    async chunks(
        documentId: string,
        knowledgeBaseId?: string,
    ): Promise<DocumentChunksResponse> {
        const response = await api.get<DocumentChunksResponse>(
            `/documents/${documentId}/chunks`,
            {
                params: knowledgeBaseId
                    ? { knowledge_base_id: knowledgeBaseId }
                    : undefined,
            },
        );
        return response.data;
    }

    async progress(
        knowledgeBaseId: string,
        documentId: string,
    ): Promise<IngestProgress> {
        const response = await api.get<IngestProgress>(
            `/documents/${documentId}/progress`,
            { params: { knowledge_base_id: knowledgeBaseId } },
        );
        return response.data;
    }

    async reprocess(
        knowledgeBaseId: string,
        documentId: string,
    ): Promise<{ status: string; id: string; message?: string }> {
        const response = await api.post(
            `/documents/${documentId}/reprocess`,
            null,
            { params: { knowledge_base_id: knowledgeBaseId } },
        );
        return response.data;
    }

    async delete(params: {
        knowledgeBaseId: string;
        documentId: string;
    }): Promise<{ status: string; id: string }> {
        const response = await api.delete(`/documents/${params.documentId}`, {
            params: { knowledge_base_id: params.knowledgeBaseId },
        });
        return response.data;
    }

    async embeddingModels(knowledgeBaseId: string): Promise<{
        indexed: string[];
        default: string;
        catalog: Array<{ id: string; label: string; why?: string }>;
        corpus_model?: {
            id: string;
            slug: string;
            display_name: string;
            runtime_model_id: string;
            status: string;
            dimensions: number;
        } | null;
        models?: Array<{
            id: string;
            slug: string;
            display_name: string;
            runtime_model_id: string;
            status: string;
            dimensions: number;
        }>;
        note?: string;
    }> {
        const response = await api.get("/documents/embedding-models", {
            params: { knowledge_base_id: knowledgeBaseId },
        });
        return response.data;
    }

    async reindexEmbeddings(params: {
        knowledgeBaseId: string;
        documentId?: string;
        embeddingModels: string[];
    }): Promise<{
        chunks: number;
        models: Record<
            string,
            {
                indexed: number;
                skipped: number;
                pending?: number;
                failed: number;
                error?: string | null;
            }
        >;
        note?: string;
    }> {
        const response = await api.post("/documents/reindex-embeddings", {
            knowledge_base_id: params.knowledgeBaseId,
            document_id: params.documentId || null,
            embedding_models: params.embeddingModels,
        });
        return response.data;
    }

    async indexStates(params: {
        knowledgeBaseId: string;
        documentId: string;
    }): Promise<IndexState[]> {
        const response = await api.get<{ states: IndexState[] }>(
            `/documents/${params.documentId}/index-states`,
            { params: { knowledge_base_id: params.knowledgeBaseId } },
        );
        return response.data.states ?? [];
    }

    async retryIndex(params: {
        knowledgeBaseId: string;
        stateId: string;
    }): Promise<{ status: string; id?: string }> {
        const response = await api.post(
            `/documents/index-states/${params.stateId}/retry`,
            null,
            { params: { knowledge_base_id: params.knowledgeBaseId } },
        );
        return response.data;
    }

    async indexTasks(params: {
        knowledgeBaseIds: string[];
        status?: string;
        q?: string;
        limit?: number;
        offset?: number;
    }): Promise<IndexTasksResponse> {
        const search = new URLSearchParams();
        for (const id of params.knowledgeBaseIds) {
            search.append("knowledge_base_id", id);
        }
        if (params.status && params.status !== "all") {
            search.set("status", params.status);
        }
        if (params.q) search.set("q", params.q);
        search.set("limit", String(params.limit ?? 50));
        search.set("offset", String(params.offset ?? 0));
        const response = await api.get<IndexTasksResponse>(
            `/documents/index-tasks?${search.toString()}`,
        );
        return response.data;
    }

    async retryIndexBulk(params: {
        knowledgeBaseId: string;
        knowledgeBaseIds?: string[];
        ids?: string[];
        status?: string;
        q?: string;
    }): Promise<{ status: string; queued: number }> {
        const response = await api.post("/documents/index-states/retry-bulk", {
            knowledge_base_id: params.knowledgeBaseId,
            knowledge_base_ids: params.knowledgeBaseIds,
            ids: params.ids,
            status: params.status,
            q: params.q,
        });
        return response.data;
    }

    async setModelStatus(params: {
        knowledgeBaseId: string;
        modelId: string;
        status: "active" | "inactive";
    }): Promise<{ id: string; status: string; slug?: string }> {
        const response = await api.patch(
            `/documents/embedding-models/${params.modelId}`,
            { status: params.status },
            { params: { knowledge_base_id: params.knowledgeBaseId } },
        );
        return response.data;
    }

    async applyEmbeddingModel(params: {
        knowledgeBaseId: string;
        modelId: string;
    }): Promise<{
        id: string;
        status: string;
        slug?: string;
        display_name?: string;
        runtime_model_id?: string;
        queued?: number;
    }> {
        const response = await api.post(
            `/documents/embedding-models/${params.modelId}/apply-all`,
            null,
            { params: { knowledge_base_id: params.knowledgeBaseId } },
        );
        return response.data;
    }
}

const documentServiceInstance = new DocumentService();
export { documentServiceInstance as DocumentService };

/* --- evaluation.service.ts --- */

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

  async compareDistanceMetrics(
    organizationId: string,
    input: {
      embedding_models?: string[];
      distance_metrics: string[];
      top_k?: number;
      knowledge_base_id?: string | null;
    },
  ): Promise<DistanceMetricsComparison> {
    const { data } = await api.post<DistanceMetricsComparison>(
      "/chat/evaluation/experiments/compare",
      {
        embedding_models: input.embedding_models ?? ["nomic-embed-text"],
        distance_metrics: input.distance_metrics,
        top_k: input.top_k ?? 3,
        knowledge_base_id: input.knowledge_base_id || undefined,
      },
      { headers: headers(organizationId), timeout: 1800000 },
    );
    return data;
  }

  async distanceExperimentHistory(
    organizationId: string,
  ): Promise<RetrievalExperimentRun[]> {
    const { data } = await api.get<RetrievalExperimentRun[]>(
      "/chat/evaluation/experiments",
      { headers: headers(organizationId) },
    );
    return data.filter((run) => run.experiment_type === "distance_compare");
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
  ): Promise<DistanceMetricsComparison> {
    const { data } = await api.post<DistanceMetricsComparison>(
      "/chat/evaluation/experiments/indexed-models",
      {
        distance_metric: "cosine",
        top_k: 3,
        knowledge_base_id: knowledgeBaseId || undefined,
        persist: true,
        temperature,
      },
      {
        params: { organization_id: organizationId },
        headers: headers(organizationId),
        timeout: 1800000,
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

const evaluationServiceInstance = new EvaluationService();
export { evaluationServiceInstance as EvaluationService };

/* --- knowledge.service.ts --- */

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

const knowledgeServiceInstance = new KnowledgeService();
export { knowledgeServiceInstance as KnowledgeService };

/* --- organization.service.ts --- */

export const getOrganizations = async () => {
    const { data } = await api.get("/organization");

    return data;
};

export const getOrganization = async (id: string) => {
    const { data } = await api.get(`/organization/${id}`);

    return data;
};

export const getOrganizationMembers = async (id: string) => {
    const { data } = await api.get(`/organization/${id}/members`);

    return data;
};

export const getOrganizationDepartments = async (
    id: string,
): Promise<Department[]> => {
    const { data } = await api.get<Department[]>(
        `/organization/${id}/departments`,
    );
    return Array.isArray(data) ? data : [];
};

export const createOrganization = async (body: any) => {
    const { data } = await api.post("/organization", body);

    return data;
};

export const updateOrganization = async (
    id: string,
    body: any,
) => {
    const { data } = await api.put(`/organization/${id}`, body);

    return data;
};

export const deleteOrganization = async (id: string) => {
    await api.delete(`/organization/${id}`);
};

const OrganizationService = {


    async getAll(): Promise<Organization[]> {


        const response =
            await api.get(
                "/organization"
            );


        return response.data;


    },


};


export { OrganizationService };

/* --- tenant.service.ts --- */


class TenantService {

    private headers() {

        const token = localStorage.getItem("token");

        return {

            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        };
    }

    async list(): Promise<Tenant[]> {
        const response = await fetch(
            `${api.defaults.baseURL}/tenants`,
            {
                headers: this.headers(),
            }

        );

        if (!response.ok)
            throw new Error("Cannot load tenants");

        const data: TenantListResponse = await response.json();

        return data.items;
    }

    async get(
        id: string,
    ): Promise<Tenant> {

        const response = await fetch(

            `${api.defaults.baseURL}/tenants/${id}`,

            {

                headers: this.headers(),
            }

        );

        if (!response.ok)
            throw new Error("Tenant not found");

        return await response.json();
    }

    async create(
        request: CreateTenantRequest,
    ): Promise<Tenant> {
        const response = await fetch(
            `${api.defaults.baseURL}/tenants`,
            {
                method: "POST",
                headers: this.headers(),
                body: JSON.stringify(request),
            }

        );

        if (!response.ok)
            throw new Error("Cannot create tenant");

        return await response.json();
    }

    async update(
        id: string,
        request: UpdateTenantRequest,
    ): Promise<Tenant> {

        const response = await fetch(

            `${api.defaults.baseURL}/tenants/${id}`,

            {

                method: "PUT",

                headers: this.headers(),

                body: JSON.stringify(request),
            }

        );

        if (!response.ok)
            throw new Error("Cannot update tenant");

        return await response.json();
    }

    async delete(
        id: string,
    ): Promise<void> {

        const response = await fetch(

            `${api.defaults.baseURL}/tenants/${id}`,

            {

                method: "DELETE",

                headers: this.headers(),
            }

        );

        if (!response.ok)
            throw new Error("Cannot delete tenant");
    }

    async activate(
        id: string,
    ) {

        return this.update(id, {
            active: true,
        });
    }

    async deactivate(
        id: string,
    ) {
        return this.update(id, {
            active: false,
        });
    }

}

const tenantServiceInstance = new TenantService();
export { tenantServiceInstance as TenantService };

/* --- validation.service.ts --- */

export type HumanReviewStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "corrected";

export type HumanReview = {
  id: string;
  source: "chat" | "document_question" | string;
  question: string;
  answer?: string | null;
  context_snippet?: string | null;
  status: HumanReviewStatus;
  corrected_answer?: string | null;
  reviewer_notes?: string | null;
  created_at?: string | null;
  document_id?: string | null;
  category?: string | null;
  filename?: string | null;
  rationale?: string | null;
  keywords?: string[] | null;
};

export type DocumentQuestion = {
  id: string;
  document_id?: string | null;
  question: string;
  rationale?: string | null;
  category?: string | null;
  keywords?: string[] | null;
  reference_answer?: string | null;
  status: string;
};

export async function fetchHumanReviews(params?: {
  status?: string;
  source?: string;
  organizationId?: string;
}): Promise<{ count: number; pending: number; data: HumanReview[] }> {
  const { data } = await api.get("/human-validation/reviews", {
    params: {
      status: params?.status ?? "pending",
      source: params?.source ?? "document_question",
      organization_id: params?.organizationId,
    },
  });
  return data;
}

export async function decideHumanReview(
  id: string,
  payload: {
    status: "approved" | "rejected" | "corrected";
    reviewer_notes?: string;
    corrected_answer?: string;
    question?: string;
    keywords?: string[];
    category?: string;
  },
): Promise<void> {
  await api.post(`/human-validation/reviews/${id}`, payload);
}

export async function extractMissingQuestions(params?: {
  organizationId?: string;
}): Promise<{ status: string; organization_id?: string | null }> {
  const { data } = await api.post(
    "/human-validation/extract-missing",
    null,
    {
      params: { organization_id: params?.organizationId },
    },
  );
  return data;
}

export async function fetchDocumentQuestions(params?: {
  knowledgeBaseId?: string;
  documentId?: string;
}): Promise<DocumentQuestion[]> {
  const { data } = await api.get<{ data?: DocumentQuestion[] }>(
    "/human-validation/questions",
    {
      params: {
        knowledge_base_id: params?.knowledgeBaseId,
        document_id: params?.documentId,
      },
    },
  );
  return data.data ?? [];
}

