import { useTranslation } from "@/i18n/I18nProvider";
import type { IndexCounts, IndexState, DocumentItem, IndexTask } from "@/types";
import { RefreshCw } from "lucide-react";
import { NavLink } from "react-router-dom";

/* --- components/documents/IndexSummaryBar.tsx --- */

export type StatusFilter =
  | "all"
  | "indexed"
  | "pending"
  | "indexing"
  | "failed"
  | "none";

const STATS: Array<{ id: StatusFilter; countKey: keyof IndexCounts; labelKey: string }> = [
  { id: "all", countKey: "total", labelKey: "documents.statTotal" },
  { id: "indexed", countKey: "indexed", labelKey: "documents.statIndexed" },
  { id: "pending", countKey: "pending", labelKey: "documents.statPending" },
  { id: "indexing", countKey: "indexing", labelKey: "documents.statIndexing" },
  { id: "failed", countKey: "failed", labelKey: "documents.statFailed" },
  { id: "none", countKey: "none", labelKey: "documents.statNone" },
];

export function IndexSummaryBar({
  counts,
  filter,
  onFilter,
}: {
  counts: IndexCounts;
  filter: StatusFilter;
  onFilter: (next: StatusFilter) => void;
  onRefresh?: () => void;
  refreshing?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <ul className="flex flex-wrap gap-x-10 gap-y-3">
      {STATS.map((stat) => {
        const active = filter === stat.id;
        return (
          <li key={stat.id}>
            <button
              type="button"
              onClick={() => onFilter(active && stat.id !== "all" ? "all" : stat.id)}
              className={`text-left ${active ? "opacity-100" : "opacity-80 hover:opacity-100"}`}
            >
              <span className="block text-4xl font-bold tabular-nums leading-none text-slate-900">
                {counts[stat.countKey]}
              </span>
              <span
                className={`mt-0.5 block text-xs ${
                  active ? "font-semibold text-slate-700" : "text-slate-500"
                }`}
              >
                {t(stat.labelKey)}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/* --- components/documents/IndexStatesList.tsx --- */


export function tone(status?: string) {
  if (status === "indexed") return "bg-emerald-50 text-emerald-800";
  if (status === "failed") return "bg-red-50 text-red-700";
  if (status === "indexing") return "bg-amber-50 text-amber-800";
  return "bg-slate-100 text-slate-600";
}

export function label(status: string | undefined, t: (key: string) => string) {
  if (status === "indexed") return t("documents.statusIndexed");
  if (status === "indexing") return t("documents.indexing");
  if (status === "failed") return t("documents.failed");
  if (status === "pending") return t("documents.pending");
  return status || "—";
}

export function IndexStatesList({
  states,
  busyId,
  onRetry,
}: {
  states: IndexState[];
  busyId?: string | null;
  onRetry?: (state: IndexState) => void;
}) {
  const { t } = useTranslation();
  if (!states.length) return null;
  return (
    <ul className="mt-2 space-y-1.5">
      {states.map((state) => (
        <li
          key={state.id}
          className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 px-2 py-1.5"
        >
          <div className="min-w-0">
            <p className="truncate text-[11px] font-semibold text-slate-800">
              {state.display_name || state.slug || t("documents.model")}
            </p>
            {state.error ? (
              <p className="truncate text-[10px] text-red-600">{state.error}</p>
            ) : (state.attempts ?? 0) > 0 ? (
              <p className="text-[10px] text-slate-400">
                {t("documents.attempts")}: {state.attempts}
              </p>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${tone(state.status)}`}>
              {label(state.status, t)}
            </span>
            {onRetry && state.status !== "indexing" ? (
              <button
                type="button"
                disabled={busyId === state.id}
                onClick={() => onRetry(state)}
                className="rounded p-1 text-slate-400 hover:bg-slate-50 hover:text-[color:var(--agro-primary)] disabled:opacity-50"
                title={t("documents.retryIndex")}
              >
                <RefreshCw size={12} className={busyId === state.id ? "animate-spin" : ""} />
              </button>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}

/* --- components/documents/IndexTasksTable.tsx --- */

export function taskToDocument(task: IndexTask): DocumentItem {
  return {
    id: task.document_id,
    filename: task.filename,
    title: task.title || undefined,
    name: task.title || task.filename,
    size: 0,
    current_version: 1,
    created_at: task.updated_at || "",
    knowledge_base_id: task.knowledge_base_id,
    index_states: task.id
      ? [
          {
            id: task.id,
            document_id: task.document_id,
            status: task.status,
            attempts: task.attempts,
            error: task.error,
            slug: task.slug || undefined,
            display_name: task.display_name || undefined,
            runtime_model_id: task.runtime_model_id || undefined,
            updated_at: task.updated_at || undefined,
          },
        ]
      : [],
  };
}

function statusClass(status: string) {
  if (status === "indexed") return "font-medium text-emerald-700";
  if (status === "failed") return "font-medium text-red-600";
  if (status === "indexing") return "font-medium text-amber-700";
  if (status === "pending") return "font-medium text-slate-600";
  return "text-slate-500";
}

function statusLabel(
  status: string,
  t: (key: string) => string,
) {
  if (status === "indexed") return t("documents.statusIndexed");
  if (status === "indexing") return t("documents.indexing");
  if (status === "failed") return t("documents.failed");
  if (status === "pending") return t("documents.pending");
  if (status === "none") return t("documents.statNone");
  return status || "—";
}

export function IndexTasksTable({
  rows,
  busyId,
  onRetry,
  onOpen,
}: {
  rows: IndexTask[];
  busyId?: string | null;
  onRetry?: (task: IndexTask) => void;
  onOpen?: (document: DocumentItem) => void;
}) {
  const { t, language } = useTranslation();
  const locale = language === "en" ? "en-GB" : "es-ES";

  if (!rows.length) {
    return (
      <p className="px-4 py-10 text-center text-sm text-slate-500">
        {t("documents.emptyFilter")}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            <th className="px-4 py-3">{t("documents.colDocument")}</th>
            <th className="px-4 py-3">{t("documents.colModel")}</th>
            <th className="px-4 py-3">{t("documents.colStatus")}</th>
            <th className="px-4 py-3">{t("documents.colAttempts")}</th>
            <th className="px-4 py-3">{t("documents.colUpdated")}</th>
            <th className="px-4 py-3">{t("documents.colError")}</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const title = row.filename || row.title || "—";
            const status = row.status || "none";
            const updated = row.updated_at
              ? new Date(row.updated_at).toLocaleString(locale, {
                  dateStyle: "short",
                  timeStyle: "short",
                })
              : "—";
            const canRetry = Boolean(row.id) && status !== "indexing";
            return (
              <tr
                key={row.id || `${row.document_id}-none`}
                className="border-b border-slate-100 last:border-0"
              >
                <td className="max-w-[18rem] px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onOpen?.(taskToDocument(row))}
                    className="truncate font-medium text-slate-900 hover:text-[color:var(--agro-primary)]"
                    title={title}
                  >
                    {title}
                  </button>
                </td>
                <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">
                  {row.slug || row.runtime_model_id || row.display_name || "—"}
                </td>
                <td className={`px-4 py-3 ${statusClass(status)}`}>
                  {statusLabel(status, t)}
                </td>
                <td className="px-4 py-3 tabular-nums text-slate-600">
                  {row.attempts ?? "—"}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                  {updated}
                </td>
                <td className="max-w-[14rem] truncate px-4 py-3 text-xs text-red-600">
                  {row.error || "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  {canRetry && onRetry ? (
                    <button
                      type="button"
                      disabled={busyId === row.id}
                      title={t("documents.reindexHint")}
                      onClick={() => onRetry(row)}
                      className="text-sm font-medium text-[color:var(--agro-primary)] hover:underline disabled:opacity-50"
                    >
                      {t("documents.reindex")}
                    </button>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* --- components/documents/RagAdminHeader.tsx --- */


export function RagAdminHeader({
  tab,
  onRefresh,
  refreshing,
}: {
  tab: "indexacion" | "evaluacion";
  onRefresh?: () => void;
  refreshing?: boolean;
}) {
  const { t } = useTranslation();
  const tabs = [
    { id: "indexacion" as const, to: "/dashboard/documentos", label: t("documents.tabIndexing") },
    { id: "evaluacion" as const, to: "/dashboard/evaluacion", label: t("documents.tabEvaluation") },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            {t("documents.ragTitle")}
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            {t("documents.ragSubtitle")}
          </p>
        </div>
        {onRefresh ? (
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            {t("documents.refresh")}
          </button>
        ) : null}
      </div>
      <nav className="flex gap-6 border-b border-slate-200">
        {tabs.map((item) => (
          <NavLink
            key={item.id}
            to={item.to}
            className={() => {
              const active = tab === item.id;
              return [
                "-mb-px border-b-2 pb-2 text-sm font-semibold",
                active
                  ? "border-[color:var(--agro-primary)] text-[color:var(--agro-primary)]"
                  : "border-transparent text-slate-500 hover:text-slate-800",
              ].join(" ");
            }}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

