"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import DocumentService from "@/services/document.service";
import { DOCUMENT_ACCEPT, MAX_DOCUMENT_BYTES } from "@/lib/uploads";
import { fetchDocumentQuestions, type DocumentQuestion } from "@/services/validation.service";
import { useTranslation } from "@/i18n/I18nProvider";
import { categoryLabel } from "@/components/evaluation/labels";
import { useOrganization } from "@/context/OrganizationContext";
import {
  useDocuments,
  useInvalidateDocuments,
  useKnowledgeBases,
} from "@/hooks/useCachedApi";

/* ============================================================
TYPES
============================================================ */

type DocumentStatus = "active" | "inactive";

type ProcessingStatus =
  | "uploaded"
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "unknown";

interface RagDocument {
  id: string;
  name: string;
  filename?: string;

  status: DocumentStatus;

  processing_status?: ProcessingStatus;

  active?: boolean;

  embedding_model?: string;
  generation_model?: string;
  llm_model?: string;

  job_id?: string;
  chunks?: number;
  attempts?: number;

  updated_at?: string;
  created_at?: string;

  error?: string | null;

  size?: number;
  content_type?: string;
  mime_type?: string;

  knowledge_base_id?: string;
  tenant_id?: string;
}

interface KnowledgeBase {
  id: string;
  name?: string;
}

/* ============================================================
HELPERS
============================================================ */

function formatDate(date?: string) {
  if (!date) {
    return "—";
  }

  try {
    return new Intl.DateTimeFormat("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(date));
  } catch {
    return date;
  }
}

function formatBytes(bytes?: number) {
  if (!bytes) {
    return "";
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

function processingLabel(status: ProcessingStatus | undefined, t: (key: string) => string) {
  switch (status) {
    case "uploaded":
      return t("ragDocs.procUploaded");
    case "pending":
      return t("ragDocs.procPending");
    case "running":
      return t("ragDocs.procRunning");
    case "completed":
      return t("ragDocs.procCompleted");
    case "failed":
      return t("ragDocs.procFailed");
    default:
      return "—";
  }
}

function statusLabel(status: DocumentStatus, t: (key: string) => string) {
  return status === "active" ? t("ragDocs.statusActive") : t("ragDocs.statusInactive");
}

function statusTone(status: DocumentStatus) {
  return status === "active"
    ? "bg-emerald-50 text-emerald-600"
    : "bg-slate-100 text-slate-500";
}

/* ============================================================
STATUS BADGE
============================================================ */

function StatusBadge({
  status,
  processingStatus,
  t,
}: {
  status: DocumentStatus;
  processingStatus?: ProcessingStatus;
  t: (key: string) => string;
}) {
  const isProcessing =
    processingStatus === "pending" || processingStatus === "running";

  return (
    <span
      className={`
        inline-flex
        items-center
        gap-1.5
        rounded-full
        px-2.5
        py-1
        text-xs
        font-medium
        ${statusTone(status)}
      `}
    >
      {isProcessing && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}

      {statusLabel(status, t)}
    </span>
  );
}

/* ============================================================
PROCESSING BADGE
============================================================ */

function ProcessingBadge({
  status,
  t,
}: {
  status?: ProcessingStatus;
  t: (key: string) => string;
}) {
  if (!status) {
    return null;
  }

  const classes: Record<ProcessingStatus, string> = {
    uploaded: "bg-slate-100 text-slate-500",
    pending: "bg-amber-50 text-amber-600",
    running: "bg-blue-50 text-blue-600",
    completed: "bg-emerald-50 text-emerald-600",
    failed: "bg-red-50 text-red-600",
    unknown: "bg-slate-100 text-slate-500",
  };

  return (
    <span
      className={`
        inline-flex
        items-center
        rounded-full
        px-2
        py-0.5
        text-[10px]
        font-medium
        ${classes[status]}
      `}
    >
      {processingLabel(status, t)}
    </span>
  );
}

/* ============================================================
STAT CARD
============================================================ */

function StatCard({
  value,
  label,
  active,
}: {
  value: number | string;
  label: string;
  active?: boolean;
}) {
  return (
    <div
      className={`
        flex
        min-w-[72px]
        flex-col
        justify-center
        rounded-md
        px-3
        py-2
        ${active ? "border border-slate-300 bg-white shadow-sm" : ""}
      `}
    >
      <span
        className={`
          text-lg
          font-semibold
          leading-none
          ${active ? "text-slate-800" : "text-slate-500"}
        `}
      >
        {value}
      </span>

      <span className="mt-1 text-[10px] text-slate-400">{label}</span>
    </div>
  );
}

/* ============================================================
MAIN PAGE
============================================================ */

export default function RagDocumentationPage() {
  const { t } = useTranslation();
  const { selectedOrg } = useOrganization();
  const queryClient = useQueryClient();
  const {
    data: kbsData,
    isLoading: loadingKbs,
    error: kbsError,
  } = useKnowledgeBases(selectedOrg?.id);
  const kbs = (kbsData as KnowledgeBase[]) ?? [];

  const [knowledgeBaseId, setKnowledgeBaseId] = useState("");
  const {
    data: documentsCached,
    isLoading: loadingDocs,
  } = useDocuments(knowledgeBaseId || undefined);
  const invalidateDocuments = useInvalidateDocuments();

  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const loading = (loadingKbs || loadingDocs) && documents.length === 0;

  const [search, setSearch] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const docFileRef = useRef<HTMLInputElement | null>(null);
  const [extractedQuestions, setExtractedQuestions] = useState<DocumentQuestion[]>([]);
  const [embeddingCatalog, setEmbeddingCatalog] = useState<
    Array<{ id: string; label: string; why?: string }>
  >([]);
  const [reindexingId, setReindexingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [rowEmbedding, setRowEmbedding] = useState<Record<string, string>>({});

  const handleUploadDocument = async (file?: File) => {
    const selected = file ?? docFileRef.current?.files?.[0];
    if (!selected || !knowledgeBaseId) {
      setError(t("ragDocs.selectKbFile"));
      return;
    }
    if (selected.size > MAX_DOCUMENT_BYTES) {
      setError(t("documents.fileTooLarge"));
      return;
    }
    setUploadingDoc(true);
    setError(null);
    try {
      const result = await DocumentService.upload({
        knowledgeBaseId,
        file: selected,
        title: selected.name,
      });
      setExtractedQuestions([]);
      if (result.processing_status === "failed" || result.status === "error") {
        setError(result.error || result.message || t("ragDocs.savedWithError"));
        setMessage(null);
      } else {
        setMessage(
          result.message ||
            (result.chunks
              ? t("ragDocs.ingested", { chunks: result.chunks })
              : t("ragDocs.ingestedPartial")),
        );
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          t("ragDocs.uploadFailed"),
      );
    } finally {
      await invalidateDocuments(knowledgeBaseId);
      await queryClient.invalidateQueries({ queryKey: ["human-reviews"] });
      setUploadingDoc(false);
      if (docFileRef.current) docFileRef.current.value = "";
    }
  };

  /* ============================================================
  LOAD DOCUMENTS (caché global; invalida solo tras mutaciones)
  ============================================================ */

  const loadDocuments = useCallback(
    async (
      kbId: string,
      _options?: {
        silent?: boolean;
      },
    ) => {
      if (!kbId) {
        setDocuments([]);
        return;
      }
      if (kbId !== knowledgeBaseId) {
        setKnowledgeBaseId(kbId);
      }
      await invalidateDocuments(kbId);
    },
    [invalidateDocuments, knowledgeBaseId],
  );

  useEffect(() => {
    if (documentsCached) {
      setDocuments(documentsCached as unknown as RagDocument[]);
    } else if (!knowledgeBaseId) {
      setDocuments([]);
    }
  }, [documentsCached, knowledgeBaseId]);

  useEffect(() => {
    if (!knowledgeBaseId) {
      setExtractedQuestions([]);
      return;
    }
    void fetchDocumentQuestions({ knowledgeBaseId })
      .then(setExtractedQuestions)
      .catch(() => setExtractedQuestions([]));
    void DocumentService.embeddingModels(knowledgeBaseId)
      .then((data) => {
        setEmbeddingCatalog(data.catalog ?? []);
      })
      .catch(() => undefined);
  }, [knowledgeBaseId]);

  useEffect(() => {
    if (!knowledgeBaseId && kbs.length > 0) {
      setKnowledgeBaseId(kbs[0].id);
    }
  }, [kbs, knowledgeBaseId]);

  useEffect(() => {
    if (kbsError) {
      setError("No se pudieron cargar las Knowledge Bases.");
    }
  }, [kbsError]);

  /* ============================================================
  ORGANIZATION CHANGE
  ============================================================ */

  useEffect(() => {
    if (!selectedOrg?.id) {
      setKnowledgeBaseId("");
      setDocuments([]);
    }
  }, [selectedOrg?.id]);

  useEffect(() => {
    const processing = documents.some(
      (document) =>
        document.processing_status === "pending" ||
        document.processing_status === "running",
    );
    if (!knowledgeBaseId || !processing) {
      return;
    }
    const timer = window.setInterval(() => {
      void invalidateDocuments(knowledgeBaseId);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [documents, knowledgeBaseId, invalidateDocuments]);

  /* ============================================================
  FILTER
  ============================================================ */

  const filteredDocuments = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return documents;
    }

    return documents.filter((document) => {
      const name = document.name?.toLowerCase() ?? "";

      const filename = document.filename?.toLowerCase() ?? "";

      return name.includes(query) || filename.includes(query);
    });
  }, [documents, search]);

  const groupedQuestions = useMemo(() => {
    const groups = new Map<string, DocumentQuestion[]>();
    for (const item of extractedQuestions) {
      const key = item.category || "general";
      const list = groups.get(key) ?? [];
      list.push(item);
      groups.set(key, list);
    }
    return Array.from(groups.entries());
  }, [extractedQuestions]);

  const handleReindex = async (documentId: string) => {
    if (!knowledgeBaseId) {
      setError(t("ragDocs.selectKb"));
      return;
    }
    const model =
      rowEmbedding[documentId] || embeddingCatalog[0]?.id;
    if (!model) {
      setError(t("ragDocs.selectEmbedding"));
      return;
    }
    setReindexingId(documentId);
    setError(null);
    try {
      const result = await DocumentService.reindexEmbeddings({
        knowledgeBaseId,
        documentId,
        embeddingModels: [model],
      });
      const stats = result.models?.[model];
      if (!result.chunks) {
        setError(
          stats?.error ||
            t("ragDocs.noChunks"),
        );
        setMessage(null);
      } else {
        setDocuments((prev) =>
          prev.map((document) =>
            document.id === documentId
              ? {
                  ...document,
                  embedding_model: model,
                  chunks: result.chunks,
                  processing_status:
                    stats?.failed && !stats?.indexed ? "failed" : "completed",
                  status: "active",
                  error: stats?.error || null,
                }
              : document,
          ),
        );
        setMessage(
          stats
            ? t("ragDocs.reindexed", {
                id: documentId.slice(0, 8),
                model,
                indexed: stats.indexed,
                skipped: stats.skipped,
                failed: stats.failed ? `, ${stats.failed}` : "",
              })
            : t("ragDocs.reindexedChunks", { count: result.chunks }),
        );
      }
      await invalidateDocuments(knowledgeBaseId);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          t("ragDocs.reindexFailed"),
      );
    } finally {
      setReindexingId(null);
    }
  };

  const handleDelete = async (document: RagDocument) => {
    if (!knowledgeBaseId) return;
    const confirmed = window.confirm(
      t("ragDocs.deleteConfirm", { name: document.name }),
    );
    if (!confirmed) return;
    setDeletingId(document.id);
    setError(null);
    try {
      await DocumentService.delete({
        knowledgeBaseId,
        documentId: document.id,
      });
      setMessage(t("ragDocs.deleted", { name: document.name }));
      await invalidateDocuments(knowledgeBaseId);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          t("ragDocs.deleteFailed"),
      );
    } finally {
      setDeletingId(null);
    }
  };

  /* ============================================================
  COUNTERS
  ============================================================ */

  const stats = useMemo(() => {
    return {
      total: documents.length,

      active: documents.filter((d) => d.status === "active").length,

      inactive: documents.filter((d) => d.status === "inactive").length,

      processing: documents.filter(
        (d) =>
          d.processing_status === "pending" ||
          d.processing_status === "running",
      ).length,

      failed: documents.filter((d) => d.processing_status === "failed").length,
    };
  }, [documents]);

  /* ============================================================
  RENDER
  ============================================================ */

  return (
    <div>
      {/* ==================================================
          HEADER
      ================================================== */}

      <div className="border-b border-slate-100">
        <div className="mx-auto max-w-[1500px] px-6 py-7">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-slate-800">
                {t("ragDocs.title")}
              </h1>

              <p className="mt-1 text-xs text-slate-400">
                {t("ragDocs.subtitle")}
              </p>
            </div>

            <button
              type="button"
              onClick={() => loadDocuments(knowledgeBaseId)}
              disabled={!knowledgeBaseId || loading}
              className="text-xs font-medium text-slate-600 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? t("ragDocs.updating") : t("ragDocs.refresh")}
            </button>
          </div>
        </div>
      </div>

      {/* ==================================================
          CONTENT
      ================================================== */}

      <main className="mx-auto max-w-[1500px] px-6 py-5">
        {error && (
          <div className="mb-4 rounded-md bg-red-50 px-4 py-3 text-xs text-red-600">
            {error}
          </div>
        )}

        {message && (
          <div className="mb-4 rounded-md bg-emerald-50 px-4 py-3 text-xs text-emerald-700">
            {message}{" "}
            {extractedQuestions.length > 0 && (
              <Link
                to="/dashboard/evaluacion"
                className="font-bold underline underline-offset-2"
              >
                {t("ragDocs.goToEval")}
              </Link>
            )}
          </div>
        )}

        {/* =================================================
            INDEXATION
        ================================================= */}

        <>
            <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-1">
                <StatCard value={stats.total} label={t("ragDocs.statTotal")} active />

                <StatCard value={stats.active} label={t("ragDocs.statActive")} />

                <StatCard value={stats.inactive} label={t("ragDocs.statInactive")} />

                <StatCard value={stats.processing} label={t("ragDocs.statProcessing")} />

                <StatCard value={stats.failed} label={t("ragDocs.statFailed")} />
              </div>

              <p className="text-xs text-slate-400">
                {t("evalExtended.ragDocsIndexHintFull")}
              </p>
            </div>

            <div className="mb-4 flex flex-wrap items-center gap-3">
              <select
                value={knowledgeBaseId}
                onChange={(event) => setKnowledgeBaseId(event.target.value)}
                className="h-9 max-w-[220px] rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700"
              >
                {kbs.length === 0 ? (
                  <option value="">{t("ragDocs.noKb")}</option>
                ) : (
                  kbs.map((kb) => (
                    <option key={kb.id} value={kb.id}>
                      {kb.name || kb.id}
                    </option>
                  ))
                )}
              </select>
              <div className="relative max-w-md flex-1">
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder={t("ragDocs.searchPlaceholder")}
                  className="h-9 w-full rounded-md border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none placeholder:text-slate-300 focus:border-slate-300"
                />
              </div>
              <input
                ref={docFileRef}
                type="file"
                className="hidden"
                accept={DOCUMENT_ACCEPT}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void handleUploadDocument(file);
                }}
              />
              <button
                type="button"
                disabled={uploadingDoc || !knowledgeBaseId}
                onClick={() => docFileRef.current?.click()}
                className="h-9 rounded-md bg-[#0038A8] px-3 text-xs font-bold text-white disabled:opacity-50"
              >
                {uploadingDoc ? t("ragDocs.uploading") : t("ragDocs.upload")}
              </button>
            </div>

            <div className="overflow-x-auto rounded-md border border-slate-100">
              <table className="w-full min-w-[1100px]">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      {t("ragDocs.colDocument")}
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      {t("ragDocs.colEmbedding")}
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      {t("ragDocs.colGeneration")}
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      {t("ragDocs.colStatus")}
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      {t("ragDocs.colChunks")}
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      {t("ragDocs.colAttempts")}
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      {t("ragDocs.colUpdated")}
                    </th>

                    <th className="px-4 py-3 text-right text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      {t("ragDocs.colAction")}
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {loading ? (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-4 py-14 text-center text-xs text-slate-400"
                      >
                        {t("ragDocs.loading")}
                      </td>
                    </tr>
                  ) : filteredDocuments.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-14 text-center">
                        <p className="text-sm font-medium text-slate-600">
                          {t("ragDocs.emptyTitle")}
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                          {t("ragDocs.emptyBody")}
                        </p>
                      </td>
                    </tr>
                  ) : (
                    filteredDocuments.map((document) => (
                      <tr
                        key={document.id}
                        className={`border-b border-slate-100 last:border-b-0 hover:bg-slate-50/40 ${
                          document.processing_status === "failed" || document.error
                            ? "bg-red-50/40"
                            : ""
                        }`}
                      >
                        <td className="px-4 py-3">
                          <div className="min-w-[230px]">
                            <p className="truncate text-xs font-semibold text-slate-700">
                              {document.name || document.filename || document.id}
                            </p>

                            <p className="mt-1 text-[10px] text-slate-400">
                              {document.content_type ??
                                document.mime_type ??
                                t("evalExtended.ragDocsDefaultDocType")}

                              {document.size
                                ? ` · ${formatBytes(document.size)}`
                                : ""}
                            </p>

                            {document.processing_status && (
                                <div className="mt-1.5">
                                  <ProcessingBadge
                                    status={document.processing_status}
                                    t={t}
                                  />
                                </div>
                              )}
                            {document.error && (
                              <p className="mt-1 max-w-[280px] text-[10px] leading-snug text-red-600">
                                {document.error}
                              </p>
                            )}
                          </div>
                        </td>

                        <td className="px-4 py-3">
                          <span className="block max-w-[180px] truncate text-xs text-slate-500">
                            {document.embedding_model ?? "—"}
                          </span>
                        </td>

                        <td className="px-4 py-3">
                          <span className="block max-w-[150px] truncate text-xs text-slate-500">
                            {document.generation_model ??
                              document.llm_model ??
                              "—"}
                          </span>
                        </td>

                        <td className="px-4 py-3">
                          <StatusBadge
                            status={document.status}
                            processingStatus={document.processing_status}
                            t={t}
                          />
                        </td>

                        <td className="px-4 py-3">
                          <span className="text-xs text-slate-500">
                            {document.chunks ?? 0}
                          </span>
                        </td>

                        <td className="px-4 py-3">
                          <span className="text-xs text-slate-500">
                            {document.attempts ?? 0}
                          </span>
                        </td>

                        <td className="px-4 py-3">
                          <span className="text-xs text-slate-500">
                            {formatDate(
                              document.updated_at ?? document.created_at,
                            )}
                          </span>
                        </td>

                        <td className="px-4 py-3 text-right">
                          <div className="flex min-w-[280px] items-center justify-end gap-2">
                            <select
                              value={
                                rowEmbedding[document.id] ||
                                document.embedding_model ||
                                embeddingCatalog[0]?.id ||
                                "nomic-embed-text"
                              }
                              onChange={(event) =>
                                setRowEmbedding((current) => ({
                                  ...current,
                                  [document.id]: event.target.value,
                                }))
                              }
                              className="h-8 max-w-[150px] rounded-md border border-slate-200 bg-white px-2 text-[10px] text-slate-700"
                            >
                              {(embeddingCatalog.length
                                ? embeddingCatalog
                                : [{ id: "nomic-embed-text", label: "Nomic" }]
                              ).map((item) => (
                                <option key={item.id} value={item.id}>
                                  {item.label}
                                </option>
                              ))}
                            </select>
                            <button
                              type="button"
                              disabled={
                                reindexingId === document.id ||
                                !knowledgeBaseId ||
                                document.processing_status === "pending" ||
                                document.processing_status === "running"
                              }
                              onClick={() => void handleReindex(document.id)}
                              className="h-8 rounded-md bg-slate-900 px-2 text-[10px] font-bold text-white disabled:opacity-50"
                            >
                              {reindexingId === document.id ? t("ragDocs.reindexing") : t("ragDocs.reindex")}
                            </button>
                            <button
                              type="button"
                              disabled={deletingId === document.id}
                              onClick={() => void handleDelete(document)}
                              className="h-8 rounded-md border border-red-200 px-2 text-[10px] font-bold text-red-600 hover:bg-red-50 disabled:opacity-50"
                            >
                              {deletingId === document.id ? t("ragDocs.deleting") : t("ragDocs.delete")}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {extractedQuestions.length > 0 && (
              <div className="mt-5 rounded-xl border border-emerald-100 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-bold text-slate-800">
                  {t("ragDocs.extractedTitle", { count: extractedQuestions.length })}
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  {t("ragDocs.extractedIntroRetrieval")}{" "}
                  <Link
                    to="/dashboard/evaluacion"
                    className="font-semibold text-emerald-700 underline underline-offset-2"
                  >
                    {t("ragDocs.openEval")}
                  </Link>
                </p>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  {groupedQuestions.map(([category, items]) => (
                    <div
                      key={category}
                      className="rounded-lg border border-slate-100 bg-slate-50/80 p-3"
                    >
                      <p className="mb-2 text-[11px] font-bold uppercase tracking-wide text-emerald-700">
                        {categoryLabel(t,category)} · {items.length}
                      </p>
                      <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-700">
                        {items.map((item) => (
                          <li key={item.id}>
                            <span className="font-semibold">{item.question}</span>
                            {item.rationale && (
                              <span className="mt-0.5 block text-xs text-slate-500">
                                {item.rationale}
                              </span>
                            )}
                            {item.keywords && item.keywords.length > 0 && (
                              <span className="mt-1 flex flex-wrap gap-1">
                                {item.keywords.map((kw) => (
                                  <span
                                    key={kw}
                                    className="rounded-full bg-white px-2 py-0.5 text-[10px] text-slate-600"
                                  >
                                    #{kw}
                                  </span>
                                ))}
                              </span>
                            )}
                          </li>
                        ))}
                      </ol>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
      </main>

    </div>
  );
}
