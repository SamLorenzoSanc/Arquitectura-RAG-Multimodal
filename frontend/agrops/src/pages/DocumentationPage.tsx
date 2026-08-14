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
import { fetchDocumentQuestions, type DocumentQuestion } from "@/services/validation.service";
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

function processingLabel(status?: ProcessingStatus) {
  switch (status) {
    case "uploaded":
      return "Subida";

    case "pending":
      return "Pendiente";

    case "running":
      return "Procesando";

    case "completed":
      return "Completada";

    case "failed":
      return "Fallida";

    default:
      return "—";
  }
}

function statusLabel(status: DocumentStatus) {
  return status === "active" ? "Activo" : "Inactivo";
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
}: {
  status: DocumentStatus;
  processingStatus?: ProcessingStatus;
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

      {statusLabel(status)}
    </span>
  );
}

/* ============================================================
PROCESSING BADGE
============================================================ */

function ProcessingBadge({ status }: { status?: ProcessingStatus }) {
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
      {processingLabel(status)}
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
      setError("Selecciona una base de conocimiento y un archivo.");
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
      const questions = (result.questions ?? []).map((item, index) => ({
        id: `${result.id}-${index}`,
        document_id: result.id,
        question: item.question,
        rationale: item.rationale,
        category: item.category,
        keywords: item.keywords,
        reference_answer: item.reference_answer,
        status: "pending",
      }));
      setExtractedQuestions(questions);
      if (result.processing_status === "failed" || result.status === "error") {
        setError(result.error || result.message || "El documento se guardó con error.");
        setMessage(null);
      } else {
        setMessage(
          questions.length
            ? `Documento subido. Se enviaron ${questions.length} preguntas de muestra a Validación humana.`
            : result.message || "Documento subido.",
        );
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "No se pudo subir el documento.",
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
      setError("Selecciona una base de conocimiento.");
      return;
    }
    const model =
      rowEmbedding[documentId] || embeddingCatalog[0]?.id;
    if (!model) {
      setError("Selecciona un modelo de embeddings.");
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
            "No se generaron fragmentos. El documento no tiene texto extraíble o el fichero no está en disco.",
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
            ? `${documentId.slice(0, 8)}… reindexado con ${model}: ${stats.indexed} nuevos, ${stats.skipped} ya indexados${stats.failed ? `, ${stats.failed} fallos` : ""}.`
            : `${result.chunks} chunks reindexados.`,
        );
      }
      await invalidateDocuments(knowledgeBaseId);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "No se pudo reindexar con ese embedding.",
      );
    } finally {
      setReindexingId(null);
    }
  };

  const handleDelete = async (document: RagDocument) => {
    if (!knowledgeBaseId) return;
    const confirmed = window.confirm(
      `¿Borrar «${document.name}» y sus embeddings? Esta acción no se puede deshacer.`,
    );
    if (!confirmed) return;
    setDeletingId(document.id);
    setError(null);
    try {
      await DocumentService.delete({
        knowledgeBaseId,
        documentId: document.id,
      });
      setMessage(`Documento «${document.name}» eliminado.`);
      await invalidateDocuments(knowledgeBaseId);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "No se pudo borrar el documento.",
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
                RAG
              </h1>

              <p className="mt-1 text-xs text-slate-400">
                Estado de indexación de documentos del RAG
              </p>
            </div>

            <button
              type="button"
              onClick={() => loadDocuments(knowledgeBaseId)}
              disabled={!knowledgeBaseId || loading}
              className="text-xs font-medium text-slate-600 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Actualizando..." : "Actualizar"}
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
                to="/dashboard/evaluacion?tab=validacion"
                className="font-bold underline underline-offset-2"
              >
                Ir a Validación humana
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
                <StatCard value={stats.total} label="Total" active />

                <StatCard value={stats.active} label="Activos" />

                <StatCard value={stats.inactive} label="Inactivos" />

                <StatCard value={stats.processing} label="Procesando" />

                <StatCard value={stats.failed} label="Fallidos" />
              </div>

              <p className="text-xs text-slate-400">
                Al subir un documento se extraen preguntas de muestra y se
                envían a Validación humana. Solo las aprobadas entran en el
                banco de métricas.
              </p>
            </div>

            <div className="mb-4 flex flex-wrap items-center gap-3">
              <select
                value={knowledgeBaseId}
                onChange={(event) => setKnowledgeBaseId(event.target.value)}
                className="h-9 max-w-[220px] rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700"
              >
                {kbs.length === 0 ? (
                  <option value="">Sin bases de conocimiento</option>
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
                  placeholder="Buscar documento por título..."
                  className="h-9 w-full rounded-md border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none placeholder:text-slate-300 focus:border-slate-300"
                />
              </div>
              <input
                ref={docFileRef}
                type="file"
                className="hidden"
                accept=".pdf,.txt,.md,.csv,.docx"
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
                {uploadingDoc ? "Subiendo…" : "Subir documento"}
              </button>
            </div>

            <div className="overflow-x-auto rounded-md border border-slate-100">
              <table className="w-full min-w-[1100px]">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Documento
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Embedding
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Generación
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Estado
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Chunks
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Intentos
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Actualización
                    </th>

                    <th className="px-4 py-3 text-right text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Acción
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
                        Cargando documentos...
                      </td>
                    </tr>
                  ) : filteredDocuments.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-14 text-center">
                        <p className="text-sm font-medium text-slate-600">
                          No hay documentos
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                          No hay metadatos documentales históricos en esta base.
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
                                "documento"}

                              {document.size
                                ? ` · ${formatBytes(document.size)}`
                                : ""}
                            </p>

                            {document.processing_status && (
                                <div className="mt-1.5">
                                  <ProcessingBadge
                                    status={document.processing_status}
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
                                "qwen3-embedding:latest"
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
                                : [{ id: "qwen3-embedding:latest", label: "Qwen3" }]
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
                              {reindexingId === document.id ? "Reindexando…" : "Reindexar"}
                            </button>
                            <button
                              type="button"
                              disabled={deletingId === document.id}
                              onClick={() => void handleDelete(document)}
                              className="h-8 rounded-md border border-red-200 px-2 text-[10px] font-bold text-red-600 hover:bg-red-50 disabled:opacity-50"
                            >
                              {deletingId === document.id ? "Borrando…" : "Borrar"}
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
                  Preguntas de muestra extraídas ({extractedQuestions.length})
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  Van a Evaluación RAG → Validación humana. Un experto las
                  aprueba, rechaza o corrige; solo entonces entran en el banco
                  de métricas.{" "}
                  <Link
                    to="/dashboard/evaluacion?tab=validacion"
                    className="font-semibold text-emerald-700 underline underline-offset-2"
                  >
                    Abrir cola HITL
                  </Link>
                </p>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  {groupedQuestions.map(([category, items]) => (
                    <div
                      key={category}
                      className="rounded-lg border border-slate-100 bg-slate-50/80 p-3"
                    >
                      <p className="mb-2 text-[11px] font-bold uppercase tracking-wide text-emerald-700">
                        {categoryLabel(category)} · {items.length}
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
