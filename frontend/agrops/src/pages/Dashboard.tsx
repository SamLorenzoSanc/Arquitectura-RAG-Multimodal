import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  FileText,
  LayoutDashboard,
  MessageSquare,
  Sparkles,
} from "lucide-react";

import { useAuth } from "@/context";
import { useOrganization } from "@/context";
import { useTranslation } from "@/i18n/I18nProvider";
import { queryKeys } from "@/lib/app";
import {
  AccountService,
  type AccountAnalytics,
  type AnalyticsEvent,
} from "@/services";

const emptyAnalytics: AccountAnalytics = {
  user_id: "",
  totals: {
    documents: 0,
    conversations: 0,
    questions: 0,
    projects: 0,
    organizations: 0,
    api_calls: 0,
    active_tokens: 0,
    support_tickets: 0,
    documents_week: 0,
    questions_week: 0,
  },
  activity: [],
  recent_documents: [],
  recent_conversations: [],
  projects: [],
  timeline: [],
};

export default function DashboardOverview() {
  const { t, language } = useTranslation();
  const { user } = useAuth();
  const { selectedOrg, organizations } = useOrganization();

  const relativeTime = (value?: string | null) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    const diff = Date.now() - date.getTime();
    const minutes = Math.max(1, Math.round(diff / 60_000));
    if (minutes < 60) return t("dashboard.minutesAgo", { n: minutes });
    const hours = Math.round(minutes / 60);
    if (hours < 24) return t("dashboard.hoursAgo", { n: hours });
    const days = Math.round(hours / 24);
    return days === 1
      ? t("dashboard.daysAgoSingular", { n: days })
      : t("dashboard.daysAgoPlural", { n: days });
  };

  const weekday = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const locale = language === "en" ? "en-US" : "es-ES";
    return date.toLocaleDateString(locale, { weekday: "short" }).replace(".", "");
  };

  const eventMeta = (event: AnalyticsEvent) => {
    if (event.kind === "document") {
      return { label: t("dashboard.documentEvent"), to: "/dashboard/documentos" };
    }
    if (event.kind === "project") {
      return { label: t("dashboard.documentEvent"), to: "/dashboard/documentos" };
    }
    return { label: t("dashboard.queryEvent"), to: "/dashboard" };
  };

  const analyticsQuery = useQuery({
    queryKey: queryKeys.analytics(user?.id || "me"),
    queryFn: () => AccountService.analytics(),
    enabled: Boolean(user?.id),
  });

  const data = analyticsQuery.data ?? emptyAnalytics;
  const totals = data.totals;
  const maxActivity = Math.max(
    1,
    ...data.activity.map((day) => day.questions + day.documents),
  );

  const kpis = [
    {
      label: t("dashboard.documents"),
      value: totals.documents,
      hint: t("dashboard.weekHint", { n: totals.documents_week }),
      icon: FileText,
      to: "/dashboard/documentos",
    },
    {
      label: t("dashboard.queries"),
      value: totals.questions,
      hint: t("dashboard.weekHint", { n: totals.questions_week }),
      icon: Sparkles,
      to: "/dashboard",
    },
    {
      label: t("dashboard.conversations"),
      value: totals.conversations,
      hint: t("dashboard.chatHistory"),
      icon: MessageSquare,
      to: "/dashboard",
    },
    {
      label: t("dashboard.organizations"),
      value: totals.organizations || organizations.length,
      hint: selectedOrg?.name || t("dashboard.noOrg"),
      icon: Building2,
      to: "/dashboard/organization",
    },
    {
      label: t("dashboard.apiCalls"),
      value: totals.api_calls,
      hint: t("dashboard.activeTokensHint", { n: totals.active_tokens }),
      icon: LayoutDashboard,
      to: "/dashboard/settings?tab=usage",
    },
  ];

  return (
    <div className="flex flex-col gap-5 pb-8">
      <section className="rounded-2xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--agro-primary)]">
          {t("dashboard.panel")}
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          {t("dashboard.hello")}
          {user?.name ? `, ${user.name.split(" ")[0]}` : ""}
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          {t("dashboard.summary")}
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-[color:var(--agro-pill)] px-3 py-1 font-semibold text-[color:var(--agro-primary)]">
            {t("dashboard.orgBadge", { name: selectedOrg?.name || "—" })}
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-600">
            {t("dashboard.generalKb")}
          </span>
          <Link
            to="/dashboard/embeddings"
            className="rounded-full bg-[color:var(--agro-pill)] px-3 py-1 font-semibold text-[color:var(--agro-primary)] hover:underline"
          >
            {t("dashboard.embeddings3d")}
          </Link>
          <Link
            to="/dashboard/flujo-rag"
            className="rounded-full bg-[color:var(--agro-pill)] px-3 py-1 font-semibold text-[color:var(--agro-primary)] hover:underline"
          >
            {t("dashboard.ragFlow")}
          </Link>
          <Link
            to="/dashboard/lab-retrieval"
            className="rounded-full bg-[color:var(--agro-pill)] px-3 py-1 font-semibold text-[color:var(--agro-primary)] hover:underline"
          >
            {t("nav.ragProbe")}
          </Link>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {kpis.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              to={item.to}
              className="rounded-xl border border-[color:var(--agro-border)] bg-white p-4 shadow-sm transition hover:border-[color:var(--agro-primary)] hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    {item.label}
                  </p>
                  <p className="mt-1 text-3xl font-bold text-slate-900">
                    {analyticsQuery.isLoading ? "…" : item.value}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{item.hint}</p>
                </div>
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[color:var(--agro-pill)] text-[color:var(--agro-primary)]">
                  <Icon size={18} />
                </span>
              </div>
            </Link>
          );
        })}
      </section>

      <section className="rounded-xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900">{t("dashboard.activity14d")}</h2>
            <p className="text-xs text-slate-500">{t("dashboard.activityDesc")}</p>
          </div>
          <div className="flex gap-3 text-[11px] font-semibold text-slate-500">
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-[color:var(--agro-primary)]" />
              {t("dashboard.legendQueries")}
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-[#FFD100]" />
              {t("dashboard.legendDocuments")}
            </span>
          </div>
        </div>
        {data.activity.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">
            {t("dashboard.noActivity")}
          </p>
        ) : (
          <div className="flex h-36 items-end gap-1.5">
            {data.activity.map((day) => {
              const questionsH = Math.round((day.questions / maxActivity) * 100);
              const docsH = Math.round((day.documents / maxActivity) * 100);
              return (
                <div
                  key={day.day}
                  className="flex min-w-0 flex-1 flex-col items-center gap-1"
                  title={t("dashboard.activityTooltip", {
                    day: day.day,
                    questions: day.questions,
                    documents: day.documents,
                  })}
                >
                  <div className="flex h-28 w-full items-end justify-center gap-0.5">
                    <span
                      className="w-1.5 rounded-t bg-[color:var(--agro-primary)]"
                      style={{ height: `${Math.max(day.questions ? 8 : 2, questionsH)}%` }}
                    />
                    <span
                      className="w-1.5 rounded-t bg-[#FFD100]"
                      style={{ height: `${Math.max(day.documents ? 8 : 2, docsH)}%` }}
                    />
                  </div>
                  <span className="truncate text-[10px] font-medium uppercase text-slate-400">
                    {weekday(day.day)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-12">
        <section className="rounded-xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm lg:col-span-7">
          <h2 className="text-sm font-bold text-slate-900">{t("dashboard.recentActions")}</h2>
          {data.timeline.length === 0 ? (
            <p className="py-10 text-center text-sm text-slate-400">
              {t("dashboard.timelineEmpty")}
            </p>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {data.timeline.map((event, index) => {
                const meta = eventMeta(event);
                return (
                  <li key={`${event.kind}-${event.ref_id}-${index}`}>
                    <Link
                      to={meta.to}
                      className="flex items-center justify-between gap-3 py-3 hover:bg-slate-50"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-semibold text-slate-800">
                          {event.title}
                        </span>
                        <span className="text-[11px] font-medium text-slate-400">
                          {meta.label}
                        </span>
                      </span>
                      <span className="shrink-0 text-xs text-slate-500">
                        {relativeTime(event.created_at)}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <div className="space-y-4 lg:col-span-5">
          <section className="rounded-xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900">{t("dashboard.recentDocuments")}</h2>
            {data.recent_documents.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">
                {t("dashboard.noDocumentsIndexed")}
              </p>
            ) : (
              <ul className="mt-3 space-y-2">
                {data.recent_documents.map((doc) => (
                  <li
                    key={doc.id}
                    className="flex items-center justify-between gap-2 px-1 py-1.5"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-slate-800">
                        {doc.filename}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        {doc.project_name || selectedOrg?.name || t("dashboard.general")}
                      </span>
                    </span>
                    <span className="shrink-0 text-[11px] text-slate-500">
                      {relativeTime(doc.uploaded_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-bold text-slate-900">{t("dashboard.recentQueries")}</h2>
              <Link
                to="/dashboard/historial"
                className="text-[11px] font-semibold text-[color:var(--agro-primary)] hover:underline"
              >
                {t("nav.userHistory")}
              </Link>
            </div>
            {data.recent_conversations.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">
                {t("dashboard.noAssistantYet")}
              </p>
            ) : (
              <ul className="mt-3 space-y-2">
                {data.recent_conversations.map((chat) => (
                  <li key={chat.id}>
                    <Link
                      to="/dashboard/historial"
                      className="flex items-center justify-between gap-2 rounded-lg px-1 py-1.5 hover:bg-slate-50"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-slate-800">
                          {chat.title}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          {chat.message_count === 1
                            ? t("dashboard.messageSingular", { count: chat.message_count })
                            : t("dashboard.messagePlural", { count: chat.message_count })}
                        </span>
                      </span>
                      <span className="shrink-0 text-[11px] text-slate-500">
                        {relativeTime(chat.updated_at)}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
