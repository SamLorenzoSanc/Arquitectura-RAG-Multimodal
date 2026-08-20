import api from "@/api";

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

export default new AccountService();
