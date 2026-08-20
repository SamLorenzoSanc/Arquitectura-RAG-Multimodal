import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  FileSpreadsheet,
  FileText,
  Layers3,
  MoreVertical,
  Pencil,
  PlayCircle,
  ScrollText,
  Search,
  Sparkles,
  Trash2,
  UploadCloud,
  Users,
  X,
} from "lucide-react";

import DatasetWizard from "@/components/datasets/DatasetWizard";
import DatasetWorkspace from "@/components/datasets/DatasetWorkspace";
import { useTranslation } from "@/i18n/I18nProvider";
import { useOrganization } from "@/context/OrganizationContext";
import { queryKeys } from "@/lib/queryKeys";
import DatasetService from "@/services/dataset.service";
import DepartmentService from "@/services/department.service";
import KnowledgeService from "@/services/knowledge.service";
import type { KnowledgeBaseSummary } from "@/services/knowledge.service";
import type { Department } from "@/services/department.service";
import type { DatasetSource, RagDataset } from "@/types/dataset";

const SOURCE_LABEL_KEYS: Record<DatasetSource, string> = {
  file: "datasets.sourceFile",
  logs: "datasets.sourceLogs",
  synthetic: "datasets.sourceSynthetic",
  demo: "datasets.sourceDemo",
};

const STATUS_STYLE = {
  ready: "bg-emerald-50 text-emerald-700",
  processing: "bg-amber-50 text-amber-700",
  pending_review: "bg-blue-50 text-blue-700",
  draft: "bg-slate-100 text-slate-600",
  failed: "bg-red-50 text-red-700",
};

function formatDate(value: string | undefined, locale: string, noDate: string) {
  if (!value) return noDate;
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function errorMessage(error: unknown, fallback: string) {
  const candidate = error as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return candidate.response?.data?.detail || candidate.message || fallback;
}

const ACTION_KEYS: Array<{
  source: DatasetSource;
  titleKey: string;
  descKey: string;
  icon: typeof UploadCloud;
  tone: string;
}> = [
  {
    source: "file",
    titleKey: "datasets.sourceFileTitle",
    descKey: "datasets.sourceFileDesc",
    icon: FileText,
    tone: "bg-blue-50 text-blue-700",
  },
  {
    source: "logs",
    titleKey: "datasets.sourceLogsTitle",
    descKey: "datasets.sourceLogsDescShort",
    icon: ScrollText,
    tone: "bg-slate-100 text-slate-700",
  },
  {
    source: "synthetic",
    titleKey: "datasets.sourceSyntheticTitle",
    descKey: "datasets.sourceSyntheticDescShort",
    icon: Sparkles,
    tone: "bg-purple-50 text-purple-700",
  },
  {
    source: "demo",
    titleKey: "datasets.sourceDemoTitle",
    descKey: "datasets.sourceDemoDesc",
    icon: PlayCircle,
    tone: "bg-amber-50 text-amber-700",
  },
];

export default function DatasetsPage() {
  const { t, language } = useTranslation();
  const dateLocale = language === "en" ? "en-US" : "es-ES";
  const { selectedOrg } = useOrganization();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [wizardSource, setWizardSource] = useState<DatasetSource | null>(null);
  const [workspaceEdit, setWorkspaceEdit] = useState<RagDataset | null>(null);
  const [workspaceDelete, setWorkspaceDelete] = useState<RagDataset | null>(null);
  const organizationId = selectedOrg?.id ?? "";
  const initialKnowledgeBaseId = searchParams.get("kb") ?? undefined;
  const departmentFromUrl = searchParams.get("department") ?? "";
  const openDatasetId = searchParams.get("dataset") ?? "";
  const [departmentId, setDepartmentId] = useState(departmentFromUrl);

  const departmentsQuery = useQuery({
    queryKey: queryKeys.orgDepartments(organizationId),
    queryFn: () => DepartmentService.list(organizationId),
    enabled: Boolean(organizationId),
  });
  const datasetsQuery = useQuery({
    queryKey: queryKeys.datasets(organizationId, departmentId || undefined),
    queryFn: () => DatasetService.list(organizationId, departmentId || undefined),
    enabled: Boolean(organizationId),
  });
  const knowledgeBasesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(organizationId),
    queryFn: () => KnowledgeService.list(organizationId),
    enabled: Boolean(organizationId),
  });

  useEffect(() => {
    const action = searchParams.get("action");
    if (
      action === "file" ||
      action === "logs" ||
      action === "synthetic" ||
      action === "demo"
    ) {
      setWizardSource(action);
    }
  }, [searchParams]);

  useEffect(() => {
    setDepartmentId(departmentFromUrl);
  }, [departmentFromUrl]);

  const closeWizard = () => {
    setWizardSource(null);
    const next = new URLSearchParams(searchParams);
    next.delete("action");
    setSearchParams(next, { replace: true });
  };

  const selectDepartment = (id: string) => {
    setDepartmentId(id);
    const next = new URLSearchParams(searchParams);
    if (id) next.set("department", id);
    else next.delete("department");
    setSearchParams(next, { replace: true });
  };

  const openDataset = (id: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("dataset", id);
    setSearchParams(next, { replace: true });
  };

  const closeDataset = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("dataset");
    setSearchParams(next, { replace: true });
  };

  const refreshDatasets = () => {
    void queryClient.invalidateQueries({
      queryKey: ["datasets", organizationId],
    });
  };

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    const items = datasetsQuery.data ?? [];
    if (!query) return items;
    return items.filter((dataset) =>
      [
        dataset.name,
        dataset.knowledge_base_name,
        t(SOURCE_LABEL_KEYS[dataset.source]),
        ...(dataset.departments?.map((department) => department.name) ?? []),
      ].some((value) => value?.toLowerCase().includes(query)),
    );
  }, [datasetsQuery.data, search, t]);

  const departments = departmentsQuery.data ?? [];

  return (
    <div className="min-h-full bg-[#f8fafc]">
      {!openDatasetId && (
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-[1500px] px-6 py-7">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-[#0038A8]">
                <Layers3 size={15} />
                {t("datasets.breadcrumb")}
              </div>
              <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
                {t("datasets.title")}
              </h1>
              <p className="mt-1 text-sm text-slate-500">{t("datasets.intro")}</p>
            </div>
          </div>
        </div>
      </header>
      )}

      <main className="mx-auto max-w-[1500px] space-y-8 px-6 py-7">
        {!organizationId && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            {t("datasets.noOrg")}
          </div>
        )}

        {openDatasetId ? (
          <DatasetWorkspace
            datasetId={openDatasetId}
            organizationId={organizationId}
            onBack={closeDataset}
            onEdit={setWorkspaceEdit}
            onDelete={setWorkspaceDelete}
          />
        ) : (
          <>
        <section>
          <h2 className="text-sm font-bold text-slate-800">{t("datasets.department")}</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => selectDepartment("")}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                !departmentId
                  ? "border-blue-200 bg-blue-50 text-[#0038A8]"
                  : "border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              {t("datasets.allDepts")}
            </button>
            {departments.map((department) => (
              <button
                key={department.id}
                type="button"
                onClick={() => selectDepartment(department.id)}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                  departmentId === department.id
                    ? "border-blue-200 bg-blue-50 text-[#0038A8]"
                    : "border-slate-200 text-slate-600 hover:bg-slate-50"
                }`}
              >
                {department.name}
              </button>
            ))}
            {departments.length === 0 && organizationId && (
              <span className="text-xs text-slate-400">{t("datasets.noDeptsHint")}</span>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-bold text-slate-800">{t("datasets.addData")}</h2>
          <div className="mt-3 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {ACTION_KEYS.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.source}
                  type="button"
                  disabled={!organizationId}
                  onClick={() => setWizardSource(action.source)}
                  className="group flex items-start gap-4 rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md disabled:opacity-50"
                >
                  <span
                    className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${action.tone}`}
                  >
                    <Icon size={22} />
                  </span>
                  <span>
                    <span className="block text-sm font-bold text-slate-900">
                      {t(action.titleKey)}
                    </span>
                    <span className="mt-1 block text-xs text-slate-500">
                      {t(action.descKey)}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-bold text-slate-800">{t("datasets.catalog")}</h2>
              <p className="mt-1 text-xs text-slate-500">
                {departmentId
                  ? t("datasets.countDept", { count: datasetsQuery.data?.length ?? 0 })
                  : t("datasets.countOrg", { count: datasetsQuery.data?.length ?? 0 })}
              </p>
            </div>
            <label className="relative block w-full sm:w-72">
              <Search
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("datasets.searchPlaceholder")}
                className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-xs outline-none focus:border-blue-400"
              />
            </label>
          </div>

          {datasetsQuery.isError && (
            <div className="mt-4 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
              {errorMessage(datasetsQuery.error, t("datasets.unexpectedError"))}
            </div>
          )}

          {datasetsQuery.isLoading ? (
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[0, 1, 2].map((item) => (
                <div
                  key={item}
                  className="h-48 animate-pulse rounded-xl border border-slate-200 bg-white"
                />
              ))}
            </div>
          ) : filtered.length > 0 ? (
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filtered.map((dataset) => (
                <DatasetCard
                  key={dataset.id}
                  dataset={dataset}
                  organizationId={organizationId}
                  knowledgeBases={knowledgeBasesQuery.data ?? []}
                  departments={departments}
                  onOpen={() => openDataset(dataset.id)}
                  onChanged={refreshDatasets}
                />
              ))}
            </div>
          ) : (
            <div className="mt-4 flex flex-col items-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
              <FileSpreadsheet size={30} className="text-slate-300" />
              <p className="mt-3 text-sm font-bold text-slate-700">
                {search ? t("datasets.noMatch") : t("datasets.none")}
              </p>
              <p className="mt-1 text-xs text-slate-500">{t("datasets.emptyHint")}</p>
            </div>
          )}
        </section>
          </>
        )}
      </main>

      <DatasetWizard
        open={wizardSource !== null}
        source={wizardSource ?? "file"}
        organizationId={organizationId}
        knowledgeBases={knowledgeBasesQuery.data ?? []}
        departments={departments}
        initialKnowledgeBaseId={initialKnowledgeBaseId}
        onClose={closeWizard}
        onCreated={() => {
          void queryClient.invalidateQueries({
            queryKey: ["datasets", organizationId],
          });
          void queryClient.invalidateQueries({ queryKey: ["human-reviews"] });
          void queryClient.invalidateQueries({
            queryKey: queryKeys.documents(initialKnowledgeBaseId || ""),
          });
        }}
      />
      {workspaceEdit && (
        <DatasetEditDialog
          dataset={workspaceEdit}
          organizationId={organizationId}
          knowledgeBases={knowledgeBasesQuery.data ?? []}
          departments={departments}
          onClose={() => setWorkspaceEdit(null)}
          onSaved={() => {
            setWorkspaceEdit(null);
            refreshDatasets();
            void queryClient.invalidateQueries({
              queryKey: queryKeys.evaluationDataset(organizationId, workspaceEdit.id),
            });
          }}
        />
      )}
      {workspaceDelete && (
        <WorkspaceDeleteDialog
          dataset={workspaceDelete}
          organizationId={organizationId}
          onClose={() => setWorkspaceDelete(null)}
          onDeleted={() => {
            setWorkspaceDelete(null);
            closeDataset();
            refreshDatasets();
          }}
        />
      )}
    </div>
  );
}

function DatasetCard({
  dataset,
  organizationId,
  knowledgeBases,
  departments,
  onOpen,
  onChanged,
}: {
  dataset: RagDataset;
  organizationId: string;
  knowledgeBases: KnowledgeBaseSummary[];
  departments: Department[];
  onOpen: () => void;
  onChanged: () => void;
}) {
  const { t, language } = useTranslation();
  const dateLocale = language === "en" ? "en-US" : "es-ES";
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);
  const status = dataset.status || "draft";
  const departmentNames = dataset.departments?.map((item) => item.name) ?? [];
  const Icon =
    dataset.source === "synthetic"
      ? Sparkles
      : dataset.source === "logs"
        ? ScrollText
        : dataset.source === "demo"
          ? PlayCircle
          : FileText;

  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menuOpen]);

  const removeDataset = async () => {
    setBusy(true);
    setError("");
    try {
      await DatasetService.remove(dataset.id, organizationId);
      setConfirmDelete(false);
      onChanged();
    } catch (err) {
      setError(errorMessage(err, t("datasets.unexpectedError")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="relative rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
          <Icon size={19} />
        </span>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase ${
              STATUS_STYLE[status] ?? STATUS_STYLE.draft
            }`}
          >
            {status}
          </span>
          <div ref={menuRef} className="relative">
            <button
              type="button"
              aria-label={t("datasets.actionsAria")}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            >
              <MoreVertical size={16} />
            </button>
            {menuOpen && (
              <div
                role="menu"
                className="absolute right-0 z-20 mt-1 w-48 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg"
              >
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    setEditing(true);
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  <Pencil size={14} />
                  {t("datasets.updateFields")}
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    setConfirmDelete(true);
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-red-600 hover:bg-red-50"
                >
                  <Trash2 size={14} />
                  {t("datasets.deleteDataset")}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      <h3 className="mt-4 truncate text-base font-bold text-slate-900">
        <button
          type="button"
          onClick={onOpen}
          className="text-left hover:text-[#0038A8]"
        >
          {dataset.name}
        </button>
      </h3>
      {dataset.description && (
        <p className="mt-1 line-clamp-2 text-xs text-slate-500">
          {dataset.description}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {departmentNames.length > 0 ? (
          departmentNames.map((name) => (
            <span
              key={name}
              className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-[#0038A8]"
            >
              {name}
            </span>
          ))
        ) : (
          <span className="text-xs text-slate-400">{t("datasets.noDepartment")}</span>
        )}
      </div>
      <div className="mt-3 space-y-2 text-xs text-slate-500">
        <p className="flex items-center gap-2">
          <Layers3 size={14} className="text-blue-600" />
          <span className="font-semibold text-slate-700">
            {dataset.knowledge_base_name || dataset.knowledge_base_id || t("datasets.noKb")}
          </span>
        </p>
        <p className="flex items-start gap-2">
          <Users size={14} className="mt-0.5 text-slate-400" />
          <span>
            {departmentNames.length > 0
              ? departmentNames.join(", ")
              : t("datasets.wholeOrg")}
          </span>
        </p>
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-[11px] text-slate-400">
        <span>{t(SOURCE_LABEL_KEYS[dataset.source]) ?? dataset.source}</span>
        <span>
          {t("datasets.rows", {
            count: Number(dataset.row_count ?? 0),
            date: formatDate(
              dataset.updated_at ?? dataset.created_at,
              dateLocale,
              t("datasets.noDate"),
            ),
          })}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={onOpen}
          className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
        >
          <Layers3 size={14} />
          {t("datasets.open")}
        </button>
        <button
          type="button"
          onClick={() =>
            navigate(`/dashboard/evaluacion?dataset=${encodeURIComponent(dataset.id)}`)
          }
          className="flex items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-bold text-blue-700 hover:bg-blue-100"
        >
          {t("datasets.evaluate")}
        </button>
      </div>

      {editing && (
        <DatasetEditDialog
          dataset={dataset}
          organizationId={organizationId}
          knowledgeBases={knowledgeBases}
          departments={departments}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            onChanged();
          }}
        />
      )}

      {confirmDelete && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={`delete-dataset-${dataset.id}`}
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"
          >
            <h3
              id={`delete-dataset-${dataset.id}`}
              className="font-bold text-slate-900"
            >
              {t("datasets.deleteTitle")}
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              {t("datasets.deleteBody", { name: dataset.name })}
            </p>
            {error && (
              <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
                {error}
              </p>
            )}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => setConfirmDelete(false)}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
              >
                {t("common.cancel")}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void removeDataset()}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
              >
                {busy ? t("datasets.deleting") : t("datasets.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}

function DatasetEditDialog({
  dataset,
  organizationId,
  knowledgeBases,
  departments,
  onClose,
  onSaved,
}: {
  dataset: RagDataset;
  organizationId: string;
  knowledgeBases: KnowledgeBaseSummary[];
  departments: Department[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(dataset.name);
  const [description, setDescription] = useState(dataset.description ?? "");
  const [knowledgeBaseId, setKnowledgeBaseId] = useState(
    dataset.knowledge_base_id || "",
  );
  const [departmentIds, setDepartmentIds] = useState<string[]>(
    dataset.department_ids?.length
      ? dataset.department_ids
      : (dataset.departments?.map((item) => item.id) ?? []),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const save = async () => {
    if (!name.trim()) {
      setError(t("datasets.nameRequired"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      await DatasetService.update(dataset.id, organizationId, {
        name: name.trim(),
        description: description.trim() || null,
        knowledge_base_id: knowledgeBaseId || null,
        department_ids: departmentIds,
      });
      onSaved();
    } catch (err) {
      setError(errorMessage(err, t("datasets.unexpectedError")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={`edit-dataset-${dataset.id}`}
        className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h3
            id={`edit-dataset-${dataset.id}`}
            className="font-bold text-slate-900"
          >
            {t("datasets.editTitle")}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"
            aria-label={t("datasets.closeAria")}
          >
            <X size={18} />
          </button>
        </header>
        <div className="space-y-4 p-5">
          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
              {error}
            </p>
          )}
          <label className="block text-sm font-semibold text-slate-700">
            {t("datasets.name")}
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-2 h-11 w-full rounded-lg border border-slate-200 px-3 font-normal outline-none focus:border-blue-400"
            />
          </label>
          <label className="block text-sm font-semibold text-slate-700">
            {t("datasets.description")}
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal outline-none focus:border-blue-400"
            />
          </label>
          <label className="block text-sm font-semibold text-slate-700">
            {t("datasets.kb")}
            <select
              value={knowledgeBaseId}
              onChange={(event) => setKnowledgeBaseId(event.target.value)}
              className="mt-2 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal outline-none focus:border-blue-400"
            >
              <option value="">{t("datasets.noKb")}</option>
              {knowledgeBases.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          </label>
          <fieldset>
            <legend className="text-sm font-semibold text-slate-700">
              {t("datasets.departments")}
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {departments.map((department) => {
                const selected = departmentIds.includes(department.id);
                return (
                  <button
                    key={department.id}
                    type="button"
                    onClick={() =>
                      setDepartmentIds((current) =>
                        selected
                          ? current.filter((id) => id !== department.id)
                          : [...current, department.id],
                      )
                    }
                    className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                      selected
                        ? "border-blue-200 bg-blue-50 text-[#0038A8]"
                        : "border-slate-200 text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {department.name}
                  </button>
                );
              })}
              {departments.length === 0 && (
                <span className="text-xs text-slate-400">{t("datasets.noDepartments")}</span>
              )}
            </div>
          </fieldset>
        </div>
        <footer className="flex justify-end gap-2 border-t border-slate-200 bg-slate-50/60 px-5 py-4">
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-white"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void save()}
            className="rounded-lg bg-[#0038A8] px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
          >
            {busy ? t("common.saving") : t("datasets.saveChanges")}
          </button>
        </footer>
      </div>
    </div>
  );
}

function WorkspaceDeleteDialog({
  dataset,
  organizationId,
  onClose,
  onDeleted,
}: {
  dataset: RagDataset;
  organizationId: string;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const remove = async () => {
    setBusy(true);
    setError("");
    try {
      await DatasetService.remove(dataset.id, organizationId);
      onDeleted();
    } catch (err) {
      setError(errorMessage(err, t("datasets.unexpectedError")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm">
      <div role="dialog" aria-modal="true" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h3 className="font-bold text-slate-900">{t("datasets.deleteTitle")}</h3>
        <p className="mt-2 text-sm text-slate-600">
          {t("datasets.deleteBody", { name: dataset.name })}
        </p>
        {error && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>
        )}
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void remove()}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
          >
            {busy ? t("datasets.deleting") : t("datasets.delete")}
          </button>
        </div>
      </div>
    </div>
  );
}
