import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  History,
  MessageSquare,
  Search,
  UserRound,
  Users,
} from "lucide-react";

import { useOrganization } from "@/context";
import { useTranslation } from "@/i18n/I18nProvider";
import { ChatService } from "@/services";
import type {
  ConversationHistoryDetail,
  ConversationHistoryItem,
} from "@/types";

function relativeTime(value?: string | null, locale = "es") {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const diff = Date.now() - date.getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return locale.startsWith("en") ? "just now" : "ahora";
  if (mins < 60) return `${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.round(hours / 24);
  return `${days} d`;
}

export default function UserHistoryPage() {
  const { t, language } = useTranslation();
  const { selectedOrg } = useOrganization();
  const orgId = selectedOrg?.id ?? "";

  const [mineOnly, setMineOnly] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const historyQuery = useQuery({
    queryKey: ["user-conversation-history", orgId, mineOnly],
    queryFn: () =>
      ChatService.userHistory({
        organizationId: orgId,
        mineOnly,
      }),
    enabled: Boolean(orgId),
  });

  const detailQuery = useQuery({
    queryKey: ["user-conversation-detail", orgId, selectedId],
    queryFn: () =>
      ChatService.conversationDetail(selectedId!, { organizationId: orgId }),
    enabled: Boolean(orgId && selectedId),
  });

  const conversations = historyQuery.data?.conversations ?? [];
  const users = historyQuery.data?.users ?? [];

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return conversations.filter((item) => {
      if (selectedUserId !== "all" && item.user_id !== selectedUserId) {
        return false;
      }
      if (!q) return true;
      return (
        item.title.toLowerCase().includes(q) ||
        item.user_name.toLowerCase().includes(q) ||
        item.user_email.toLowerCase().includes(q) ||
        (item.first_user_message || "").toLowerCase().includes(q)
      );
    });
  }, [conversations, query, selectedUserId]);

  const detail: ConversationHistoryDetail | undefined = detailQuery.data;

  if (!orgId) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
        {t("common.selectOrganization")}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 pb-8">
      <header className="rounded-2xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--agro-primary)]">
          {t("userHistory.eyebrow")}
        </p>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-extrabold text-slate-900">
          <History size={22} className="text-[color:var(--agro-primary)]" />
          {t("userHistory.title")}
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          {t("userHistory.intro")}
        </p>
        <div className="mt-4 flex flex-wrap gap-3 text-xs">
          <span className="rounded-lg bg-slate-100 px-3 py-1.5 font-semibold text-slate-700">
            <Users size={12} className="mr-1 inline" />
            {t("userHistory.usersCount", {
              count: users.length,
            })}
          </span>
          <span className="rounded-lg bg-slate-100 px-3 py-1.5 font-semibold text-slate-700">
            <MessageSquare size={12} className="mr-1 inline" />
            {t("userHistory.chatsCount", {
              count: historyQuery.data?.total_conversations ?? 0,
            })}
          </span>
        </div>
        {historyQuery.data?.note ? (
          <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
            {historyQuery.data.note}
          </p>
        ) : null}
      </header>

      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <label className="min-w-[200px] flex-1 text-xs font-semibold text-slate-600">
          {t("userHistory.search")}
          <div className="relative mt-1">
            <Search
              size={14}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("userHistory.searchPlaceholder")}
              className="h-9 w-full rounded-lg border border-slate-200 pl-8 pr-3 text-sm"
            />
          </div>
        </label>
        <label className="text-xs font-semibold text-slate-600">
          {t("userHistory.filterUser")}
          <select
            value={selectedUserId}
            onChange={(e) => setSelectedUserId(e.target.value)}
            className="mt-1 block h-9 min-w-[200px] rounded-lg border border-slate-200 px-2 text-sm"
          >
            <option value="all">{t("userHistory.allUsers")}</option>
            {users.map((user) => (
              <option key={user.user_id} value={user.user_id}>
                {user.user_name}
                {user.user_email ? ` (${user.user_email})` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3 text-xs font-semibold text-slate-700">
          <input
            type="checkbox"
            checked={mineOnly}
            onChange={(e) => {
              setMineOnly(e.target.checked);
              setSelectedUserId("all");
              setSelectedId(null);
            }}
          />
          {t("userHistory.mineOnly")}
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <section className="rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-4 py-3">
            <h2 className="text-sm font-bold text-slate-900">
              {t("userHistory.listTitle")}
            </h2>
          </div>
          {historyQuery.isLoading ? (
            <p className="p-4 text-sm text-slate-500">
              {t("userHistory.loading")}
            </p>
          ) : historyQuery.isError ? (
            <p className="p-4 text-sm text-red-600">
              {t("userHistory.loadFailed")}
            </p>
          ) : filtered.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-400">
              {t("userHistory.empty")}
            </p>
          ) : (
            <ul className="max-h-[70vh] divide-y divide-slate-100 overflow-y-auto">
              {filtered.map((item: ConversationHistoryItem) => {
                const active = item.id === selectedId;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(item.id)}
                      className={`w-full px-4 py-3 text-left transition ${
                        active
                          ? "bg-[color:var(--agro-pill)]"
                          : "hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-slate-900">
                            {item.title}
                          </p>
                          <p className="mt-0.5 flex items-center gap-1 truncate text-[11px] text-slate-500">
                            <UserRound size={11} />
                            {item.user_name}
                            {item.user_email ? ` · ${item.user_email}` : ""}
                          </p>
                          {item.first_user_message ? (
                            <p className="mt-1 line-clamp-2 text-xs text-slate-600">
                              {item.first_user_message}
                            </p>
                          ) : null}
                        </div>
                        <div className="shrink-0 text-right text-[11px] text-slate-400">
                          <div>{relativeTime(item.updated_at, language)}</div>
                          <div className="mt-1 font-medium text-slate-500">
                            {item.message_count === 1
                              ? t("userHistory.messageSingular", {
                                  count: item.message_count,
                                })
                              : t("userHistory.messagePlural", {
                                  count: item.message_count,
                                })}
                          </div>
                        </div>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-4 py-3">
            <h2 className="text-sm font-bold text-slate-900">
              {t("userHistory.detailTitle")}
            </h2>
            {detail ? (
              <p className="mt-1 text-[11px] text-slate-500">
                {detail.user_name}
                {detail.user_email ? ` · ${detail.user_email}` : ""}
              </p>
            ) : null}
          </div>
          {!selectedId ? (
            <p className="p-6 text-center text-sm text-slate-400">
              {t("userHistory.selectHint")}
            </p>
          ) : detailQuery.isLoading ? (
            <p className="p-4 text-sm text-slate-500">
              {t("userHistory.loadingDetail")}
            </p>
          ) : detailQuery.isError ? (
            <p className="p-4 text-sm text-red-600">
              {t("userHistory.detailFailed")}
            </p>
          ) : !detail || detail.messages.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-400">
              {t("userHistory.noMessages")}
            </p>
          ) : (
            <div className="max-h-[70vh] space-y-3 overflow-y-auto p-4">
              <h3 className="text-base font-bold text-slate-900">
                {detail.title}
              </h3>
              {detail.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`rounded-xl px-3 py-2 text-sm ${
                    msg.role === "user"
                      ? "ml-6 bg-[color:var(--agro-primary)] text-white"
                      : "mr-6 border border-slate-200 bg-slate-50 text-slate-800"
                  }`}
                >
                  <p className="mb-1 text-[10px] font-bold uppercase opacity-70">
                    {msg.role === "user"
                      ? t("userHistory.roleUser")
                      : t("userHistory.roleAssistant")}
                  </p>
                  <p className="whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
