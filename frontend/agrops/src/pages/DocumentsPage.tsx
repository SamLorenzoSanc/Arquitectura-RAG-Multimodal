import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { UploadCloud } from "lucide-react";

import { useOrganization } from "@/context";
import { useTranslation } from "@/i18n/I18nProvider";
import DocumentChunksDrawer from "@/components/documents/DocumentChunksDrawer";
import { IndexSummaryBar, type StatusFilter } from "@/components/documents";
import { IndexTasksTable } from "@/components/documents";
import { RagAdminHeader } from "@/components/documents";
import { DocumentService } from "@/services";
import type { DocumentItem, IndexTask } from "@/types";
import { DOCUMENT_ACCEPT, MAX_DOCUMENT_BYTES } from "@/lib/app";

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function DocumentsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { selectedOrg, generalKnowledgeBase, knowledgeBases, reloadKnowledgeBases } =
    useOrganization();

  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [openDoc, setOpenDoc] = useState<DocumentItem | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [page, setPage] = useState(0);
  const [corpusModelId, setCorpusModelId] = useState("");
  const [applyingModel, setApplyingModel] = useState(false);
  const PAGE_SIZE = 50;

  const kbId = generalKnowledgeBase?.id;
  const kbIds = knowledgeBases.map((item) => item.id);

  const modelsQuery = useQuery({
    queryKey: ["embedding-models", kbId],
    queryFn: () => DocumentService.embeddingModels(kbId as string),
    enabled: Boolean(kbId),
  });

  const tasksQuery = useQuery({
    queryKey: ["index-tasks", kbIds.join("|"), statusFilter, query, page],
    queryFn: () =>
      DocumentService.indexTasks({
        knowledgeBaseIds: kbIds,
        status: statusFilter,
        q: query.trim() || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    enabled: Boolean(selectedOrg?.id && kbIds.length),
    refetchInterval: (current) => {
      const counts = current.state.data?.counts;
      if (!counts) return false;
      return counts.pending > 0 || counts.indexing > 0 ? 4000 : false;
    },
  });

  const catalogModels = modelsQuery.data?.models ?? [];
  const currentCorpus = modelsQuery.data?.corpus_model;
  const indexCounts = tasksQuery.data?.counts ?? {
    total: 0,
    indexed: 0,
    pending: 0,
    indexing: 0,
    failed: 0,
    none: 0,
  };
  const taskRows = tasksQuery.data?.items ?? [];
  const taskTotal = tasksQuery.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(taskTotal / PAGE_SIZE));

  useEffect(() => {
    const next =
      currentCorpus?.id ||
      catalogModels.find((model) => model.slug === "nomic-embed-text")?.id ||
      catalogModels[0]?.id ||
      "";
    if (next) setCorpusModelId((prev) => prev || next);
  }, [catalogModels, currentCorpus?.id]);

  useEffect(() => {
    setPage(0);
  }, [statusFilter, query]);

  async function refreshAll() {
    await Promise.all([
      tasksQuery.refetch(),
      modelsQuery.refetch(),
      queryClient.invalidateQueries({ queryKey: ["documents"] }),
    ]);
  }

  async function onUpload(file: File) {
    if (!kbId) {
      setError(t("documents.kbNotReady"));
      return;
    }
    if (file.size > MAX_DOCUMENT_BYTES) {
      setError(t("documents.fileTooLarge"));
      return;
    }
    setBusy(true);
    setError(null);
    setUploadMsg(t("documents.uploadingFile"));
    try {
      const result = await DocumentService.upload({
        knowledgeBaseId: kbId,
        file,
        onUploadProgress: (percent) => {
          setUploadMsg(t("documents.uploadingProgress", { percent }));
        },
      });
      if (result.processing_status === "failed" || result.status === "error") {
        setError(result.error || result.message || t("documents.ingestFailed"));
        setUploadMsg(null);
        return;
      }
      setUploadMsg(t("documents.fileSavedIndexing"));
      for (let i = 0; i < 600; i += 1) {
        const snap = await DocumentService.progress(kbId, result.id);
        if (snap.status === "completed") break;
        if (snap.status === "failed") {
          throw new Error(snap.error || snap.message || t("documents.ingestFailed"));
        }
        setUploadMsg(snap.message || t("documents.indexingEllipsis"));
        await sleep(450);
      }
      await reloadKnowledgeBases();
      await refreshAll();
      setUploadMsg(null);
    } catch (exc) {
      const status = (exc as { response?: { status?: number } }).response?.status;
      const detail = (exc as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(
        status === 413
          ? t("documents.uploadLimitExceeded")
          : detail || (exc instanceof Error ? exc.message : t("documents.indexFailed")),
      );
      setUploadMsg(null);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onRetryIndex(task: IndexTask) {
    if (!task.id) return;
    const targetKb = task.knowledge_base_id || kbId;
    if (!targetKb) return;
    setRetrying(task.id);
    try {
      await DocumentService.retryIndex({
        knowledgeBaseId: targetKb,
        stateId: task.id,
      });
      await queryClient.invalidateQueries({ queryKey: ["index-tasks"] });
    } finally {
      setRetrying(null);
    }
  }

  async function onApplyCorpusModel() {
    if (!kbId || !corpusModelId) return;
    setApplyingModel(true);
    setError(null);
    try {
      await DocumentService.applyEmbeddingModel({
        knowledgeBaseId: kbId,
        modelId: corpusModelId,
      });
      await refreshAll();
    } catch {
      setError(t("documents.corpusModelApplyFailed"));
    } finally {
      setApplyingModel(false);
    }
  }

  if (!selectedOrg) {
    return (
      <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-12 text-center text-sm text-slate-500">
        {t("documents.selectOrg")}
      </p>
    );
  }

  if (!kbId) {
    return (
      <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-12 text-center text-sm text-slate-500">
        {t("documents.preparingKb", { org: selectedOrg.name })}
      </p>
    );
  }

  return (
    <div className="flex w-full flex-col gap-6 pb-6">
      <RagAdminHeader
        tab="indexacion"
        onRefresh={() => void refreshAll()}
        refreshing={tasksQuery.isFetching}
      />

      <input
        ref={fileRef}
        type="file"
        className="hidden"
        accept={DOCUMENT_ACCEPT}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void onUpload(file);
        }}
      />

      <IndexSummaryBar
        counts={indexCounts}
        filter={statusFilter}
        onFilter={setStatusFilter}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("documents.searchByTitle")}
          className="h-10 min-w-[16rem] flex-1 rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-[color:var(--agro-primary)]"
        />
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => fileRef.current?.click()}
            className="inline-flex h-10 items-center gap-1.5 text-sm font-medium text-[color:var(--agro-primary)] hover:underline disabled:opacity-50"
          >
            <UploadCloud size={15} />
            {t("documents.uploadFile")}
          </button>
          {catalogModels.length > 0 ? (
            <>
              <select
                value={corpusModelId}
                onChange={(event) => setCorpusModelId(event.target.value)}
                className="h-10 min-w-[160px] rounded-md border border-slate-200 bg-white px-3 text-sm"
              >
                {catalogModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.slug || model.display_name}
                    {model.slug === "nomic-embed-text"
                      ? ` (${t("documents.corpusModelDefault")})`
                      : ""}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={
                  !corpusModelId ||
                  applyingModel ||
                  corpusModelId === currentCorpus?.id
                }
                onClick={() => void onApplyCorpusModel()}
                className="h-10 text-sm font-medium text-[color:var(--agro-primary)] hover:underline disabled:opacity-40"
              >
                {applyingModel
                  ? t("documents.corpusModelApplying")
                  : t("documents.corpusModelApply")}
              </button>
            </>
          ) : null}
        </div>
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}
      {uploadMsg && (
        <p className="text-sm text-slate-600">{uploadMsg}</p>
      )}

      <div className="bg-white">
        {tasksQuery.isLoading ? (
          <p className="px-4 py-10 text-center text-sm text-slate-500">
            {t("documents.loadingDocuments")}
          </p>
        ) : (
          <IndexTasksTable
            rows={taskRows}
            busyId={retrying}
            onRetry={(task) => void onRetryIndex(task)}
            onOpen={setOpenDoc}
          />
        )}
        {taskTotal > PAGE_SIZE ? (
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-xs text-slate-500">
            <span>
              {t("documents.pageOf", { page: page + 1, pages: pageCount })}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page === 0}
                onClick={() => setPage((current) => Math.max(0, current - 1))}
                className="rounded-lg border border-slate-200 px-2 py-1 font-semibold disabled:opacity-40"
              >
                {t("documents.prevPage")}
              </button>
              <button
                type="button"
                disabled={page + 1 >= pageCount}
                onClick={() => setPage((current) => current + 1)}
                className="rounded-lg border border-slate-200 px-2 py-1 font-semibold disabled:opacity-40"
              >
                {t("documents.nextPage")}
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {openDoc && (
        <DocumentChunksDrawer
          document={openDoc}
          onClose={() => setOpenDoc(null)}
        />
      )}
    </div>
  );
}
