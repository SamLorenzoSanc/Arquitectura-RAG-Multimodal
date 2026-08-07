"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import api from "@/api";

/* ============================================================
   TYPES
   ============================================================ */

type DocumentStatus =
  | "indexed"
  | "pending"
  | "indexing"
  | "failed"
  | "uploaded"
  | "processing";

interface RagDocument {
  id: string;

  name: string;

  filename?: string;

  status: DocumentStatus;

  model?: string;

  chunks?: number;

  attempts?: number;

  updated_at?: string;

  created_at?: string;

  error?: string | null;

  size?: number;

  content_type?: string;

  knowledge_base_id?: string;

  tenant_id?: string;
}

interface UploadResponse {
  id?: string;
  document_id?: string;
  message?: string;
}

/* ============================================================
   API
   ============================================================ */

const API = {
  // GET /api/v1/documents?knowledge_base_id=...
  documents: "http://localhost:8000/api/v1/documents",

  // POST /api/v1/documents
  upload: "http://localhost:8000/api/v1/documents",

  // POST /api/v1/documents/{id}/index
  index: (id: string) => `http://localhost:8000/api/v1/documents/${id}/index`,

  // POST /api/v1/documents/{id}/index
  reindex: (id: string) => `http://localhost:8000/api/v1/documents/${id}/index`,

  // DELETE /api/v1/documents/{id}
  delete: (id: string) => `http://localhost:8000/api/v1/documents/${id}`,

  // GET/POST /api/v1/rag/evaluation
  evaluation: "/rag/evaluation",

  // GET /api/v1/documents/{id}/progress
  progress: (id: string) =>
    `http://localhost:8000/api/v1/documents/${id}/progress`,
};

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

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function statusLabel(status: DocumentStatus) {
  switch (status) {
    case "indexed":
      return "Indexada";

    case "pending":
      return "Pendiente";

    case "indexing":
      return "Indexando";

    case "processing":
      return "Procesando";

    case "failed":
      return "Fallida";

    case "uploaded":
      return "Subida";

    default:
      return status;
  }
}

/* ============================================================
   STATUS
   ============================================================ */

function StatusBadge({ status }: { status: DocumentStatus }) {
  const classes: Record<DocumentStatus, string> = {
    indexed: "bg-emerald-50 text-emerald-600",

    pending: "bg-amber-50 text-amber-600",

    indexing: "bg-blue-50 text-blue-600",

    processing: "bg-blue-50 text-blue-600",

    failed: "bg-red-50 text-red-600",

    uploaded: "bg-slate-100 text-slate-600",
  };

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
                ${classes[status]}
            `}
    >
      {(status === "indexing" || status === "processing") && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}

      {statusLabel(status)}
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
  value: number;
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
   UPLOAD MODAL
   ============================================================ */

function UploadModal({
  open,
  uploading,
  onClose,
  onUpload,
}: {
  open: boolean;

  uploading: boolean;

  onClose: () => void;

  onUpload: (files: File[]) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [dragActive, setDragActive] = useState(false);

  const [files, setFiles] = useState<File[]>([]);

  if (!open) {
    return null;
  }

  const addFiles = (incoming: FileList | File[]) => {
    const newFiles = Array.from(incoming);

    setFiles((current) => {
      const map = new Map(
        current.map((file) => [`${file.name}-${file.size}`, file]),
      );

      newFiles.forEach((file) => {
        map.set(`${file.name}-${file.size}`, file);
      });

      return Array.from(map.values());
    });
  };

  const removeFile = (index: number) => {
    setFiles((current) => current.filter((_, i) => i !== index));
  };

  const submit = () => {
    if (files.length === 0) {
      return;
    }

    onUpload(files);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-xl bg-white shadow-2xl">
        {/* HEADER */}

        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-slate-800">
              Subir documentación
            </h2>

            <p className="mt-1 text-xs text-slate-400">
              Los documentos se subirán pero no serán indexados automáticamente.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={uploading}
            className="rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            ×
          </button>
        </div>

        {/* BODY */}

        <div className="p-6">
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => {
              setDragActive(false);
            }}
            onDrop={(event) => {
              event.preventDefault();

              setDragActive(false);

              if (event.dataTransfer.files) {
                addFiles(event.dataTransfer.files);
              }
            }}
            onClick={() => inputRef.current?.click()}
            className={`
                            cursor-pointer
                            rounded-xl
                            border-2
                            border-dashed
                            p-10
                            text-center
                            transition
                            ${
                              dragActive
                                ? "border-blue-500 bg-blue-50"
                                : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                            }
                        `}
          >
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path d="M12 3v12" />
                <path d="m7 8 5-5 5 5" />
                <path d="M5 15v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" />
              </svg>
            </div>

            <p className="text-sm font-medium text-slate-700">
              Arrastra tus documentos aquí
            </p>

            <p className="mt-1 text-xs text-slate-400">
              o haz clic para seleccionarlos
            </p>

            <p className="mt-3 text-[11px] text-slate-400">
              PDF, DOC, DOCX, TXT, XLS, XLSX
            </p>

            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt,.xls,.xlsx"
              className="hidden"
              onChange={(event) => {
                if (event.target.files) {
                  addFiles(event.target.files);
                }
              }}
            />
          </div>

          {/* FILES */}

          {files.length > 0 && (
            <div className="mt-5 space-y-2">
              <div className="text-xs font-medium text-slate-500">
                Documentos seleccionados
              </div>

              {files.map((file, index) => (
                <div
                  key={`${file.name}-${file.size}`}
                  className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-slate-100">
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.7"
                      >
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <path d="M14 2v6h6" />
                      </svg>
                    </div>

                    <div className="min-w-0">
                      <p className="truncate text-xs font-medium text-slate-700">
                        {file.name}
                      </p>

                      <p className="text-[10px] text-slate-400">
                        {formatBytes(file.size)}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    disabled={uploading}
                    className="ml-3 text-xs text-slate-400 hover:text-red-500"
                  >
                    Eliminar
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* FOOTER */}

        <div className="flex justify-end gap-2 border-t px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            disabled={uploading}
            className="rounded-md border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            Cancelar
          </button>

          <button
            type="button"
            onClick={submit}
            disabled={files.length === 0 || uploading}
            className="rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading
              ? "Subiendo..."
              : `Subir ${files.length || ""} documentos`}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   MAIN PAGE
   ============================================================ */

export default function RagDocumentationPage() {
  const [documents, setDocuments] = useState<RagDocument[]>([]);

  const [loading, setLoading] = useState(true);

  const [uploadModal, setUploadModal] = useState(false);

  const [uploading, setUploading] = useState(false);

  const [search, setSearch] = useState("");

  const [tab, setTab] = useState<"indexation" | "evaluation">("indexation");

  const [error, setError] = useState<string | null>(null);

  const [message, setMessage] = useState<string | null>(null);

  /* ========================================================
       LOAD
       ======================================================== */

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(API.documents, {
        method: "GET",
        credentials: "include",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Error ${response.status}`);
      }

      const data = await response.json();

      /*
       * Admite:
       *
       * [...]
       *
       * o:
       *
       * {
       *   documents: [...]
       * }
       */

      const items = Array.isArray(data) ? data : (data.documents ?? []);

      setDocuments(items);
    } catch (err) {
      console.error(err);

      setError("No se pudieron cargar los documentos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  /* ========================================================
       UPLOAD
       ======================================================== */

  const uploadDocuments = async (files: File[]) => {
    try {
      setUploading(true);
      setError(null);
      setMessage(null);

      for (const file of files) {
        const formData = new FormData();

        formData.append("file", file);

        /*
         * Si tu backend utiliza tenant_id o
         * knowledge_base_id, puedes añadirlos:
         *
         * formData.append(
         *     "tenant_id",
         *     tenantId
         * );
         *
         * formData.append(
         *     "knowledge_base_id",
         *     knowledgeBaseId
         * );
         */

        const response = await fetch(API.upload, {
          method: "POST",
          body: formData,
          credentials: "include",
        });

        if (!response.ok) {
          const text = await response.text();

          throw new Error(text || `Error subiendo ${file.name}`);
        }
      }

      setMessage(
        files.length === 1
          ? "Documento subido correctamente."
          : `${files.length} documentos subidos correctamente.`,
      );

      setUploadModal(false);

      await loadDocuments();
    } catch (err) {
      console.error(err);

      setError(err instanceof Error ? err.message : "Error durante la subida.");
    } finally {
      setUploading(false);
    }
  };

  /* ========================================================
       INDEX
       ======================================================== */

  const indexDocument = async (documentId: string) => {
    try {
      setError(null);
      setMessage(null);

      setDocuments((current) =>
        current.map((document) =>
          document.id === documentId
            ? {
                ...document,
                status: "indexing",
              }
            : document,
        ),
      );

      const response = await fetch(API.index(documentId), {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("No se pudo iniciar la indexación.");
      }

      setMessage("Indexación iniciada.");

      /*
       * Importante:
       *
       * No esperamos aquí al pipeline completo.
       *
       * El backend debería crear un job.
       */

      await loadDocuments();
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error ? err.message : "Error iniciando la indexación.",
      );

      setDocuments((current) =>
        current.map((document) =>
          document.id === documentId
            ? {
                ...document,
                status: "failed",
              }
            : document,
        ),
      );
    }
  };

  /* ========================================================
       DELETE
       ======================================================== */

  const deleteDocument = async (documentId: string) => {
    const document = documents.find((item) => item.id === documentId);

    if (!document) {
      return;
    }

    const confirmed = window.confirm(`¿Eliminar "${document.name}"?`);

    if (!confirmed) {
      return;
    }

    try {
      setError(null);

      const response = await fetch(API.delete(documentId), {
        method: "DELETE",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("No se pudo eliminar.");
      }

      setDocuments((current) =>
        current.filter((item) => item.id !== documentId),
      );

      setMessage("Documento eliminado.");
    } catch (err) {
      console.error(err);

      setError("No se pudo eliminar el documento.");
    }
  };

  /* ========================================================
       FILTER
       ======================================================== */

  const filteredDocuments = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return documents;
    }

    return documents.filter((document) =>
      document.name.toLowerCase().includes(query),
    );
  }, [documents, search]);

  /* ========================================================
       COUNTERS
       ======================================================== */

  const stats = useMemo(() => {
    return {
      total: documents.length,

      indexed: documents.filter((d) => d.status === "indexed").length,

      pending: documents.filter(
        (d) => d.status === "pending" || d.status === "uploaded",
      ).length,

      indexing: documents.filter(
        (d) => d.status === "indexing" || d.status === "processing",
      ).length,

      failed: documents.filter((d) => d.status === "failed").length,
    };
  }, [documents]);

  /* ========================================================
       RENDER
       ======================================================== */

  return (
    <div className="min-h-screen bg-white">
      {/* ==================================================
                HEADER
            ================================================== */}

      <div className="border-b border-slate-100">
        <div className="mx-auto max-w-[1400px] px-6 py-7">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-slate-800">
                RAG
              </h1>

              <p className="mt-1 text-xs text-slate-400">
                Estado de indexación, pruebas de retrieval y evaluación de las
                recomendaciones del chatbot
              </p>
            </div>

            <button
              type="button"
              onClick={loadDocuments}
              className="text-xs font-medium text-slate-600 hover:text-slate-900"
            >
              Actualizar
            </button>
          </div>

          {/* TABS */}

          <div className="mt-6 flex gap-5">
            <button
              type="button"
              onClick={() => setTab("indexation")}
              className={`
                                border-b-2
                                px-2
                                pb-2
                                text-xs
                                font-medium
                                ${
                                  tab === "indexation"
                                    ? "border-slate-700 text-blue-600"
                                    : "border-transparent text-slate-500"
                                }
                            `}
            >
              Indexación
            </button>

            <button
              type="button"
              onClick={() => setTab("evaluation")}
              className={`
                                border-b-2
                                px-2
                                pb-2
                                text-xs
                                font-medium
                                ${
                                  tab === "evaluation"
                                    ? "border-slate-700 text-blue-600"
                                    : "border-transparent text-slate-500"
                                }
                            `}
            >
              Evaluación
            </button>
          </div>
        </div>
      </div>

      {/* ==================================================
                CONTENT
            ================================================== */}

      <main className="mx-auto max-w-[1400px] px-6 py-5">
        {error && (
          <div className="mb-4 rounded-md bg-red-50 px-4 py-3 text-xs text-red-600">
            {error}
          </div>
        )}

        {message && (
          <div className="mb-4 rounded-md bg-emerald-50 px-4 py-3 text-xs text-emerald-600">
            {message}
          </div>
        )}

        {/* =================================================
                    INDEXATION
                ================================================= */}

        {tab === "indexation" && (
          <>
            {/* TOP ACTIONS */}

            <div className="mb-5 flex items-center justify-between">
              <div className="flex items-center gap-1">
                <StatCard value={stats.total} label="Total" active />
                <StatCard value={stats.indexed} label="Indexadas" />
                <StatCard value={stats.pending} label="Pendientes" />
                <StatCard value={stats.indexing} label="Indexando" />
                <StatCard value={stats.failed} label="Fallidas" />
              </div>

              <button
                type="button"
                onClick={() => setUploadModal(true)}
                className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white shadow-sm hover:bg-slate-800"
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M12 3v12" />
                  <path d="m7 8 5-5 5 5" />
                  <path d="M5 15v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" />
                </svg>
                Subir documentos
              </button>
            </div>

            {/* SEARCH */}

            <div className="mb-4">
              <div className="relative max-w-md">
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-300"
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="11" cy="11" r="7" />

                  <path d="m20 20-4-4" />
                </svg>

                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Buscar documento por título..."
                  className="h-9 w-full rounded-md border border-slate-200 bg-white pl-9 pr-3 text-xs text-slate-700 outline-none placeholder:text-slate-300 focus:border-slate-300"
                />
              </div>
            </div>

            {/* TABLE */}

            <div className="overflow-hidden rounded-md border border-slate-100">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Documento
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Modelo
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
                      Última actualización
                    </th>

                    <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      Error
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
                          Sube un documento para comenzar.
                        </p>
                      </td>
                    </tr>
                  ) : (
                    filteredDocuments.map((document) => (
                      <tr
                        key={document.id}
                        className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/40"
                      >
                        {/* DOCUMENT */}

                        <td className="px-4 py-3">
                          <div className="min-w-[240px]">
                            <p className="truncate text-xs font-semibold text-slate-700">
                              {document.name}
                            </p>

                            <p className="mt-1 text-[10px] text-slate-400">
                              {document.content_type ?? "documento"}
                              {document.size
                                ? ` · ${formatBytes(document.size)}`
                                : ""}
                            </p>
                          </div>
                        </td>

                        {/* MODEL */}

                        <td className="px-4 py-3">
                          <span className="text-xs text-slate-500">
                            {document.model ?? "—"}
                          </span>
                        </td>

                        {/* STATUS */}

                        <td className="px-4 py-3">
                          <StatusBadge status={document.status} />
                        </td>

                        {/* CHUNKS */}

                        <td className="px-4 py-3">
                          <span className="text-xs text-slate-500">
                            {document.chunks ?? 0}
                          </span>
                        </td>

                        {/* ATTEMPTS */}

                        <td className="px-4 py-3">
                          <span className="text-xs text-slate-500">
                            {document.attempts ?? 0}
                          </span>
                        </td>

                        {/* DATE */}

                        <td className="px-4 py-3">
                          <span className="text-xs text-slate-500">
                            {formatDate(
                              document.updated_at ?? document.created_at,
                            )}
                          </span>
                        </td>

                        {/* ERROR */}

                        <td className="px-4 py-3">
                          <span
                            className={
                              document.error
                                ? "max-w-[180px] truncate text-xs text-red-500"
                                : "text-xs text-slate-300"
                            }
                          >
                            {document.error ?? "—"}
                          </span>
                        </td>

                        {/* ACTION */}

                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            {(document.status === "indexed" ||
                              document.status === "failed") && (
                              <button
                                type="button"
                                onClick={() => indexDocument(document.id)}
                                className="text-xs font-medium text-slate-500 hover:text-slate-900"
                              >
                                Reindexar
                              </button>
                            )}

                            {(document.status === "uploaded" ||
                              document.status === "pending") && (
                              <button
                                type="button"
                                onClick={() => indexDocument(document.id)}
                                className="text-xs font-medium text-blue-600 hover:text-blue-700"
                              >
                                Indexar
                              </button>
                            )}

                            {(document.status === "indexing" ||
                              document.status === "processing") && (
                              <span className="text-xs text-slate-400">
                                Procesando...
                              </span>
                            )}

                            <button
                              type="button"
                              onClick={() => deleteDocument(document.id)}
                              className="text-xs text-slate-400 hover:text-red-500"
                            >
                              Eliminar
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* =================================================
                    EVALUATION
                ================================================= */}

        {tab === "evaluation" && (
          <div className="rounded-md border border-slate-100">
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="text-sm font-semibold text-slate-700">
                Evaluación del RAG
              </h2>

              <p className="mt-1 text-xs text-slate-400">
                Evaluación independiente del retrieval y generación.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 p-5 md:grid-cols-4">
              <EvaluationCard label="MRR" value="—" />

              <EvaluationCard label="nDCG" value="—" />

              <EvaluationCard label="Factualidad" value="—" />

              <EvaluationCard label="Relevancia" value="—" />
            </div>
          </div>
        )}
      </main>

      {/* ==================================================
                UPLOAD MODAL
            ================================================== */}

      <UploadModal
        open={uploadModal}
        uploading={uploading}
        onClose={() => setUploadModal(false)}
        onUpload={uploadDocuments}
      />
    </div>
  );
}

/* ============================================================
   EVALUATION CARD
   ============================================================ */

function EvaluationCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-100 p-4">
      <p className="text-[10px] uppercase tracking-wide text-slate-400">
        {label}
      </p>

      <p className="mt-2 text-xl font-semibold text-slate-700">{value}</p>
    </div>
  );
}
