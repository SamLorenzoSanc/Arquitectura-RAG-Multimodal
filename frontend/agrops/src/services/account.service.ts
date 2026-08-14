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
}

export interface AccountUsage {
  documents: number;
  conversations: number;
  api_calls: number;
  active_tokens: number;
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

  async usage() {
    const { data } = await api.get<AccountUsage>("/account/usage");
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
