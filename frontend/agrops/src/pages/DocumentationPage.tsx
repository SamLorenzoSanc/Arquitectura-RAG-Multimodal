"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import api from "@/api";
import KnowledgeService from "@/services/knowledge.service";
import { useOrganization } from "@/context/OrganizationContext";

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

  /**
   * Estado visual que devuelve el backend:
   * active / inactive
   */
  status: DocumentStatus;

  /**
   * Estado técnico del pipeline RAG:
   * uploaded / pending / running / completed / failed
   */
  processing_status?: ProcessingStatus;

  active?: boolean;

  /**
   * Modelo utilizado para generar embeddings.
   */
  embedding_model?: string;

  /**
   * Modelo utilizado para generación/enriquecimiento
   * y resumen de vídeos.
   */
  generation_model?: string;

  /**
   * Alias compatible con respuestas anteriores.
   */
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

interface DocumentsResponse {
  documents?: RagDocument[];
}
interface RetrievedChunk {
  id: string;
  title: string;
  description: string;
  cosine_distance: number;

  // Flags de evaluación manual en la UI
  flag_different_info?: boolean;
  flag_out_of_knowledge?: boolean;
}

// Representa el resultado final de ejecutar la evaluación sobre el dataset guardado
interface DatasetEvaluationResult {
  model_date: string;
  dataset_name: string;
  recall_1: number;
  recall_k: number;
  mrr: number;
  false_positives: number;
  failures: number;
  duration_ms: number;
  create_at: Date;
}
interface UploadResponse {
  id?: string;
  document_id?: string;
  job_id?: string;
  status?: string;
  processing_status?: ProcessingStatus;
  active?: boolean;
  embedding_model?: string;
  generation_model?: string;
  message?: string;
}

interface KnowledgeBase {
  id: string;
  name?: string;
}

/* ============================================================
CONSTANTS
============================================================ */

const VIDEO_EXTENSIONS = [
  ".mp4",
  ".mov",
  ".avi",
  ".mkv",
  ".webm",
  ".mpeg",
  ".mpg",
  ".m4v",
];

const ACCEPTED_EXTENSIONS = [
  ".pdf",
  ".doc",
  ".docx",
  ".txt",
  ".xls",
  ".xlsx",
  ...VIDEO_EXTENSIONS,
];

const POLL_INTERVAL_MS = 2000;

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

function isVideoFile(file: File) {
  const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;

  return file.type.startsWith("video/") || VIDEO_EXTENSIONS.includes(extension);
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
  if (!status || status === "completed") {
    return null;
  }

  const classes: Record<
    Exclude<ProcessingStatus, "completed" | "unknown">,
    string
  > = {
    uploaded: "bg-slate-100 text-slate-500",
    pending: "bg-amber-50 text-amber-600",
    running: "bg-blue-50 text-blue-600",
    failed: "bg-red-50 text-red-600",
  };

  const className =
    status === "unknown" ? "bg-slate-100 text-slate-500" : classes[status];

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
        ${className}
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

  useEffect(() => {
    if (!open) {
      setFiles([]);
      setDragActive(false);
    }
  }, [open]);

  if (!open) {
    return null;
  }

  const addFiles = (incoming: FileList | File[]) => {
    const newFiles = Array.from(incoming);

    setFiles((current) => {
      const map = new Map(
        current.map((file) => [
          `${file.name}-${file.size}-${file.lastModified}`,
          file,
        ]),
      );

      newFiles.forEach((file) => {
        map.set(`${file.name}-${file.size}-${file.lastModified}`, file);
      });

      return Array.from(map.values());
    });
  };

  const removeFile = (index: number) => {
    setFiles((current) => current.filter((_, i) => i !== index));
  };

  const submit = () => {
    if (files.length === 0 || uploading) {
      return;
    }

    onUpload(files);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 p-4">
      <div className="w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-xl">
        {/* HEADER */}

        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-slate-800">
              Subir documentación
            </h2>

            <p className="mt-1 text-xs text-slate-400">
              La indexación comienza automáticamente después de la subida.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={uploading}
            className="rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
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
              Arrastra tus documentos o vídeos aquí
            </p>

            <p className="mt-1 text-xs text-slate-400">
              o haz clic para seleccionarlos
            </p>

            <p className="mt-3 text-[11px] text-slate-400">
              PDF, DOC, DOCX, TXT, XLS, XLSX, MP4, MOV, AVI, MKV, WEBM
            </p>

            <input
              ref={inputRef}
              type="file"
              multiple
              accept={ACCEPTED_EXTENSIONS.join(",")}
              className="hidden"
              onChange={(event) => {
                if (event.target.files) {
                  addFiles(event.target.files);
                }

                // Permite volver a seleccionar el mismo archivo.
                event.currentTarget.value = "";
              }}
            />
          </div>

          {/* FILES */}

          {files.length > 0 && (
            <div className="mt-5 space-y-2">
              <div className="text-xs font-medium text-slate-500">
                Archivos seleccionados
              </div>

              {files.map((file, index) => {
                const video = isVideoFile(file);

                return (
                  <div
                    key={`${file.name}-${file.size}-${file.lastModified}`}
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div
                        className={`
                          flex h-8 w-8 shrink-0 items-center justify-center rounded-md
                          ${
                            video
                              ? "bg-blue-50 text-blue-600"
                              : "bg-slate-100 text-slate-500"
                          }
                        `}
                      >
                        {video ? (
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.7"
                          >
                            <rect x="3" y="5" width="18" height="14" rx="2" />
                            <path d="m10 9 5 3-5 3z" />
                          </svg>
                        ) : (
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
                        )}
                      </div>

                      <div className="min-w-0">
                        <p className="truncate text-xs font-medium text-slate-700">
                          {file.name}
                        </p>

                        <p className="text-[10px] text-slate-400">
                          {video ? "Vídeo" : "Documento"}
                          {file.size ? ` · ${formatBytes(file.size)}` : ""}
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        removeFile(index);
                      }}
                      disabled={uploading}
                      className="ml-3 text-xs text-slate-400 hover:text-red-500 disabled:opacity-50"
                    >
                      Eliminar
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* FOOTER */}

        <div className="flex justify-end gap-2 border-t px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            disabled={uploading}
            className="rounded-md border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
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
              : `Subir ${files.length || ""} archivo${
                  files.length === 1 ? "" : "s"
                }`}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
EVALUATION CARD
============================================================ */

function EvaluationCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-100 p-4">
      <span className="text-xs text-slate-400">{label}</span>

      <p className="mt-2 text-xl font-semibold text-slate-700">{value}</p>
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

  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);

  const [tab, setTab] = useState<"indexation" | "evaluation">("indexation");

  const [knowledgeBaseId, setKnowledgeBaseId] = useState("");

  const [error, setError] = useState<string | null>(null);

  const [message, setMessage] = useState<string | null>(null);

  const { selectedOrg } = useOrganization();
  const [manualQuestion, setManualQuestion] = useState("");
  const [retrievedChunks, setRetrievedChunks] = useState<RetrievedChunk[]>([]);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);
  const [testingRetrieval, setTestingRetrieval] = useState(false);
  const [savingDataset, setSavingDataset] = useState(false);

  // Estados para la evaluación masiva del dataset
  const [datasetEvalResult, setDatasetEvalResult] =
    useState<DatasetEvaluationResult | null>(null);
  const [runningDatasetEval, setRunningDatasetEval] = useState(false);

  // 1. Probar la búsqueda y obtener chunks con distancia coseno
  const handleTestRetrieval = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualQuestion.trim()) return;

    setTestingRetrieval(true);
    setRetrievedChunks([]);
    setSelectedChunkId(null);

    try {
      // Endpoint que debe devolver los chunks con su distancia coseno
      const response = await api.post<RetrievedChunk[]>(
        "/chat/simulator/search",
        {
          question: manualQuestion,
        },
      );
      setRetrievedChunks(response.data || []);
    } catch (err) {
      console.error("Error al simular retrieval:", err);
    } finally {
      setTestingRetrieval(false);
    }
  };

  // 2. Manejar el cambio de los flags de cada chunk
  const handleToggleFlag = (
    chunkId: string,
    flagType: "flag_different_info" | "flag_out_of_knowledge",
  ) => {
    setRetrievedChunks((prev) =>
      prev.map((chunk) =>
        chunk.id === chunkId
          ? { ...chunk, [flagType]: !chunk[flagType] }
          : chunk,
      ),
    );
  };

  // 3. Guardar el juego de preguntas en la BD
  const handleSaveQuestionSet = async () => {
    if (!manualQuestion || !selectedChunkId) {
      alert("Por favor, selecciona el chunk correcto antes de guardar.");
      return;
    }
    setSavingDataset(true);
    try {
      const selectedChunk = retrievedChunks.find(
        (c) => c.id === selectedChunkId,
      );

      await api.post("/chat/simulator/save-dataset", {
        question: manualQuestion,
        selected_chunk_id: selectedChunkId,
        flags: {
          different_info: selectedChunk?.flag_different_info || false,
          out_of_knowledge: selectedChunk?.flag_out_of_knowledge || false,
        },
      });

      setMessage("Dataset y métricas de evaluación guardadas con éxito.");
      setManualQuestion("");
      setRetrievedChunks([]);
      setSelectedChunkId(null);
    } catch (err) {
      console.error("Error al guardar el dataset:", err);
      setError("No se pudo guardar el registro de evaluación.");
    } finally {
      setSavingDataset(false);
    }
  };

  // 4. Ejecutar evaluación sobre todo el dataset guardado
  const handleExecuteDatasetEvaluation = async () => {
    if (runningDatasetEval) return;

    setRunningDatasetEval(true);
    setError(null);

    const payload = {
      model_name: "llama3.2",
      embedding_model: "qwen3-embedding:latest",
      top_k: 5,
      retrieval_k: 10,
      bm25_k: 10,
      rrf_k: 60,
      candidate_k: 15,
      reranker_model: "BAAI/bge-reranker-v2-m3",
      reranker_batch_size: 16,
    };

    console.log("PAYLOAD EVALUATION:", payload);

    try {
      const response = await api.post(
        "/chat/simulator/evaluate-dataset",
        payload,
        {
          headers: {
            "Content-Type": "application/json",
          },
        },
      );

      console.log("EVALUATION RESPONSE:", response.data);

      setDatasetEvalResult(response.data);
    } catch (err: any) {
      console.error("ERROR EVALUATION:", err.response?.data || err);

      setError(
        err.response?.data?.detail || "No se pudo ejecutar la evaluación.",
      );
    } finally {
      setRunningDatasetEval(false);
    }
  };
  /* ========================================================
  LOAD DOCUMENTS
  ======================================================== */

  const loadDocuments = useCallback(
    async (
      kbId: string,
      options?: {
        silent?: boolean;
      },
    ) => {
      if (!kbId) {
        setDocuments([]);
        setLoading(false);
        return;
      }

      try {
        if (!options?.silent) {
          setLoading(true);
        }

        const response = await api.get<RagDocument[] | DocumentsResponse>(
          "/documents",
          {
            params: {
              knowledge_base_id: kbId,
            },
          },
        );

        const data = response.data;

        const items: RagDocument[] = Array.isArray(data)
          ? data
          : (data?.documents ?? []);

        setDocuments(items);

        // Si una actualización correcta llega después de un error,
        // quitamos el mensaje antiguo.
        if (!options?.silent) {
          setError(null);
        }
      } catch (err: any) {
        console.error("Error cargando documentos:", err);

        console.error("Status:", err.response?.status);

        console.error("Data:", err.response?.data);

        setDocuments([]);

        setError(
          err.response?.data?.detail ||
            err.response?.data?.message ||
            err.message ||
            "No se pudieron cargar los documentos.",
        );
      } finally {
        if (!options?.silent) {
          setLoading(false);
        }
      }
    },
    [],
  );

  /* ========================================================
  INITIALIZE
  ======================================================== */

  const initialize = useCallback(
    async (orgId: string) => {
      try {
        let kbList: KnowledgeBase[] = [];

        if (
          "list" in KnowledgeService &&
          typeof (KnowledgeService as any).list === "function"
        ) {
          kbList = await (KnowledgeService as any).list(orgId);
        } else if (
          "getCurrent" in KnowledgeService &&
          typeof (KnowledgeService as any).getCurrent === "function"
        ) {
          const currentKb = await (KnowledgeService as any).getCurrent();

          if (currentKb) {
            kbList = [currentKb];
          }
        }

        setKbs(kbList || []);

        if (kbList && kbList.length > 0) {
          const defaultKbId = kbList[0].id;

          setKnowledgeBaseId(defaultKbId);

          await loadDocuments(defaultKbId);
        } else {
          setKnowledgeBaseId("");
          setDocuments([]);
          setLoading(false);
        }
      } catch (err: any) {
        console.error("Error al inicializar KBs:", err);

        setKbs([]);
        setKnowledgeBaseId("");
        setDocuments([]);
        setLoading(false);

        setError(
          err.response?.data?.detail ||
            err.response?.data?.message ||
            "No se pudieron cargar las Knowledge Bases.",
        );
      }
    },
    [loadDocuments],
  );

  /* ========================================================
  ORGANIZATION CHANGE
  ======================================================== */

  useEffect(() => {
    if (selectedOrg?.id) {
      initialize(selectedOrg.id);
    } else {
      setKbs([]);
      setKnowledgeBaseId("");
      setDocuments([]);
      setLoading(false);
    }
  }, [selectedOrg?.id, initialize]);

  /* ========================================================
  AUTO REFRESH WHILE PROCESSING
  ======================================================== */

  useEffect(() => {
    if (!knowledgeBaseId) {
      return;
    }

    const processing = documents.some(
      (document) =>
        document.processing_status === "pending" ||
        document.processing_status === "running",
    );

    if (!processing) {
      return;
    }

    const interval = window.setInterval(() => {
      loadDocuments(knowledgeBaseId, {
        silent: true,
      });
    }, POLL_INTERVAL_MS);

    return () => {
      window.clearInterval(interval);
    };
  }, [documents, knowledgeBaseId, loadDocuments]);

  /* ========================================================
  UPLOAD DOCUMENTS
  ======================================================== */

  const uploadDocuments = async (files: File[]) => {
    if (!knowledgeBaseId) {
      setError("No hay ninguna Knowledge Base seleccionada.");
      return;
    }

    try {
      setUploading(true);
      setError(null);
      setMessage(null);

      let uploaded = 0;
      let videos = 0;

      for (const file of files) {
        const formData = new FormData();

        formData.append("file", file);
        formData.append("knowledge_base_id", knowledgeBaseId);
        formData.append("title", file.name);

        const response = await api.post<UploadResponse>("/documents", formData);

        if (response.data?.id || response.data?.document_id) {
          uploaded += 1;
        }

        if (isVideoFile(file)) {
          videos += 1;
        }

        console.log(`Archivo ${file.name} subido:`, response.data);
      }

      setMessage(
        videos > 0
          ? uploaded === 1
            ? "Vídeo subido. Se ha iniciado automáticamente la extracción de voz, resumen e indexación."
            : `${uploaded} archivos subidos. Los vídeos se procesarán automáticamente antes de la indexación.`
          : uploaded === 1
            ? "Documento subido y procesamiento iniciado."
            : `${uploaded} documentos subidos y procesamiento iniciado.`,
      );

      setUploadModal(false);

      // El backend crea el job PENDING antes de devolver la respuesta.
      // Esperamos un pequeño instante para que el primer estado aparezca
      // en la tabla.
      await loadDocuments(knowledgeBaseId);
    } catch (err: any) {
      console.error("Error subiendo documentos:", err);

      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          "Error durante la subida.",
      );
    } finally {
      setUploading(false);
    }
  };

  /* ========================================================
  REINDEX DOCUMENT
  ======================================================== */

  const indexDocument = async (documentId: string) => {
    try {
      setError(null);
      setMessage(null);

      // El backend devuelve PENDING inmediatamente y
      // procesa posteriormente en BackgroundTasks.
      setDocuments((current) =>
        current.map((document) =>
          document.id === documentId
            ? {
                ...document,
                status: "inactive",
                processing_status: "pending",
                active: false,
              }
            : document,
        ),
      );

      const response = await api.post(`/documents/${documentId}/index`);

      console.log("Indexación iniciada:", response.data);

      setMessage(
        "Procesamiento iniciado. La tabla se actualizará automáticamente.",
      );

      await loadDocuments(knowledgeBaseId, {
        silent: true,
      });
    } catch (err: any) {
      console.error("Error iniciando la indexación:", err);

      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          "Error iniciando la indexación.",
      );

      setDocuments((current) =>
        current.map((document) =>
          document.id === documentId
            ? {
                ...document,
                status: "inactive",
                processing_status: "failed",
                active: false,
              }
            : document,
        ),
      );
    }
  };

  /* ========================================================
  DELETE DOCUMENT
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
      setMessage(null);

      await api.delete(`/documents/${documentId}`);

      setDocuments((current) =>
        current.filter((item) => item.id !== documentId),
      );

      setMessage("Documento eliminado.");
    } catch (err: any) {
      console.error("Error eliminando documento:", err);

      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          "No se pudo eliminar el documento.",
      );
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

    return documents.filter((document) => {
      const name = document.name?.toLowerCase() ?? "";

      const filename = document.filename?.toLowerCase() ?? "";

      return name.includes(query) || filename.includes(query);
    });
  }, [documents, search]);

  /* ========================================================
  COUNTERS
  ======================================================== */

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

  /* ========================================================
  RENDER
  ======================================================== */

  return (
    <div className="min-h-full">
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
                Estado de indexación, modelos utilizados, retrieval y evaluación
                del RAG
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

      <main className="mx-auto max-w-[1500px] px-6 py-5">
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

            <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-1">
                <StatCard value={stats.total} label="Total" active />

                <StatCard value={stats.active} label="Activos" />

                <StatCard value={stats.inactive} label="Inactivos" />

                <StatCard value={stats.processing} label="Procesando" />

                <StatCard value={stats.failed} label="Fallidos" />
              </div>

              <button
                type="button"
                onClick={() => setUploadModal(true)}
                disabled={!knowledgeBaseId}
                className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
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
                  <path d="m7 8-5 5 5 5" />
                  <path d="M17 8V6a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-2" />
                </svg>
                Subir documentos / vídeos
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

            <div className="overflow-x-auto rounded-md border border-slate-100">
              <table className="w-full min-w-[1250px]">
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
                        colSpan={9}
                        className="px-4 py-14 text-center text-xs text-slate-400"
                      >
                        Cargando documentos...
                      </td>
                    </tr>
                  ) : filteredDocuments.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-14 text-center">
                        <p className="text-sm font-medium text-slate-600">
                          No hay documentos
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                          Sube un documento o vídeo para comenzar.
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
                          <div className="min-w-[230px]">
                            <div className="flex items-center gap-2">
                              {document.content_type?.startsWith("video/") ||
                              VIDEO_EXTENSIONS.some((extension) =>
                                document.name.toLowerCase().endsWith(extension),
                              ) ? (
                                <span
                                  title="Vídeo"
                                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-600"
                                >
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="1.8"
                                  >
                                    <rect
                                      x="3"
                                      y="5"
                                      width="18"
                                      height="14"
                                      rx="2"
                                    />
                                    <path d="m10 9 5 3-5 3z" />
                                  </svg>
                                </span>
                              ) : null}

                              <p className="truncate text-xs font-semibold text-slate-700">
                                {document.name}
                              </p>
                            </div>

                            <p className="mt-1 text-[10px] text-slate-400">
                              {document.content_type ??
                                document.mime_type ??
                                "documento"}

                              {document.size
                                ? ` · ${formatBytes(document.size)}`
                                : ""}
                            </p>

                            {document.processing_status &&
                              document.processing_status !== "completed" && (
                                <div className="mt-1.5">
                                  <ProcessingBadge
                                    status={document.processing_status}
                                  />
                                </div>
                              )}
                          </div>
                        </td>

                        {/* EMBEDDING MODEL */}

                        <td className="px-4 py-3">
                          <span
                            className="block max-w-[180px] truncate text-xs text-slate-500"
                            title={document.embedding_model ?? ""}
                          >
                            {document.embedding_model ?? "—"}
                          </span>
                        </td>

                        {/* GENERATION MODEL */}

                        <td className="px-4 py-3">
                          <span
                            className="block max-w-[150px] truncate text-xs text-slate-500"
                            title={
                              document.generation_model ??
                              document.llm_model ??
                              ""
                            }
                          >
                            {document.generation_model ??
                              document.llm_model ??
                              "—"}
                          </span>
                        </td>

                        {/* STATUS */}

                        <td className="px-4 py-3">
                          <StatusBadge
                            status={document.status}
                            processingStatus={document.processing_status}
                          />
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
                            title={document.error ?? undefined}
                            className={
                              document.error
                                ? "block max-w-[180px] truncate text-xs text-red-500"
                                : "text-xs text-slate-300"
                            }
                          >
                            {document.error ?? "—"}
                          </span>
                        </td>

                        {/* ACTION */}

                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            {document.processing_status === "completed" && (
                              <button
                                type="button"
                                onClick={() => indexDocument(document.id)}
                                className="text-xs font-medium text-slate-500 hover:text-slate-900"
                              >
                                Reindexar
                              </button>
                            )}

                            {document.processing_status === "failed" && (
                              <button
                                type="button"
                                onClick={() => indexDocument(document.id)}
                                className="text-xs font-medium text-blue-600 hover:text-blue-700"
                              >
                                Reintentar
                              </button>
                            )}

                            {document.processing_status === "pending" ||
                            document.processing_status === "running" ? (
                              <span className="text-xs text-slate-400">
                                Procesando...
                              </span>
                            ) : null}

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
          <div className="space-y-8">
            {/* SECCIÓN 1: BUSCADOR MANUAL */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-base font-bold text-slate-800">
                1. Simulador de Retrieval
              </h2>
              <p className="mt-1 text-xs text-slate-500 mb-4">
                Escribe una pregunta para probar el retrieval. Los resultados
                incluirán la distancia coseno. Selecciona el chunk correcto para
                agregarlo al dataset de pruebas.
              </p>

              <form onSubmit={handleTestRetrieval} className="flex gap-3">
                <input
                  type="text"
                  value={manualQuestion}
                  onChange={(e) => setManualQuestion(e.target.value)}
                  placeholder="Ej: ¿Cuál es el procedimiento para la siembra de maíz?"
                  className="flex-1 h-10 rounded-md border border-slate-300 px-4 text-sm outline-none focus:border-blue-500 shadow-xs"
                />
                <button
                  type="submit"
                  disabled={testingRetrieval || !manualQuestion.trim()}
                  className="rounded-md bg-slate-900 px-5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 transition"
                >
                  {testingRetrieval ? "Buscando..." : "Probar Retrieval"}
                </button>
              </form>
            </div>

            {/* SECCIÓN 2: RESULTADOS DE LA BÚSQUEDA */}
            {retrievedChunks.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
                <h3 className="text-sm font-bold text-slate-800">
                  Chunks Recuperados Semánticamente
                </h3>

                <div className="space-y-4">
                  {retrievedChunks.map((chunk) => (
                    <div
                      key={chunk.id}
                      className={`relative rounded-lg border p-4 transition-all ${selectedChunkId === chunk.id ? "border-emerald-500 bg-emerald-50" : "border-slate-200 bg-slate-50 hover:border-slate-300"}`}
                    >
                      {/* Checkbox para seleccionar el correcto */}
                      <div className="absolute top-4 left-4">
                        <input
                          type="radio"
                          name="selected_chunk"
                          checked={selectedChunkId === chunk.id}
                          onChange={() => setSelectedChunkId(chunk.id)}
                          className="h-4 w-4 cursor-pointer accent-emerald-600"
                        />
                      </div>

                      <div className="ml-8">
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="text-sm font-bold text-slate-800">
                              {chunk.title || "Sin título"}
                            </h4>
                          </div>
                          {/* Distancia coseno a la derecha */}
                          <div className="flex flex-col items-end">
                            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                              Distancia Coseno
                            </span>
                            <span className="text-sm font-mono font-bold text-blue-600">
                              {chunk.cosine_distance.toFixed(4)}
                            </span>
                          </div>
                        </div>

                        <p className="mt-2 text-xs text-slate-600 bg-white p-3 rounded border border-slate-100">
                          {chunk.description}
                        </p>

                        {/* Funciones / Flags de Evaluación Manual */}
                        <div className="mt-4 flex flex-wrap gap-4 pt-3 border-t border-slate-200/60">
                          <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={chunk.flag_different_info || false}
                              onChange={() =>
                                handleToggleFlag(
                                  chunk.id,
                                  "flag_different_info",
                                )
                              }
                              className="rounded text-amber-500 focus:ring-amber-500"
                            />
                            Devolvió información distinta
                          </label>
                          <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={chunk.flag_out_of_knowledge || false}
                              onChange={() =>
                                handleToggleFlag(
                                  chunk.id,
                                  "flag_out_of_knowledge",
                                )
                              }
                              className="rounded text-rose-500 focus:ring-rose-500"
                            />
                            Fuera de conocimiento (No debería devolver nada)
                          </label>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Botón para guardar en la BD */}
                <div className="flex justify-end pt-4 border-t border-slate-100">
                  <button
                    onClick={handleSaveQuestionSet}
                    disabled={savingDataset || !selectedChunkId}
                    className="rounded-md bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition cursor-pointer"
                  >
                    {savingDataset
                      ? "Guardando..."
                      : "Guardar juego de preguntas"}
                  </button>
                </div>
              </div>
            )}

            {/* SECCIÓN 3: EVALUAR DATASET GUARDADO */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h2 className="text-base font-bold text-slate-800">
                    2. Evaluación del Dataset Consolidado
                  </h2>
                  <p className="text-xs text-slate-500 mt-1">
                    Calcula las métricas de todo el dataset de preguntas y
                    chunks correctos almacenados en la base de datos.
                  </p>
                </div>
                <button
                  onClick={handleExecuteDatasetEvaluation}
                  disabled={runningDatasetEval}
                  className="rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {runningDatasetEval
                    ? "Ejecutando..."
                    : "Ejecutar / Actualizar Evaluación"}
                </button>
              </div>

              {datasetEvalResult ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard
                    value={datasetEvalResult.recall_1.toFixed(2)}
                    label="Recall @ 1"
                    active
                  />
                  <StatCard
                    value={datasetEvalResult.recall_k.toFixed(2)}
                    label="Recall @ K"
                    active
                  />
                  <StatCard
                    value={datasetEvalResult.mrr.toFixed(3)}
                    label="MRR Global"
                    active
                  />
                  <StatCard
                    value={datasetEvalResult.false_positives}
                    label="Falsos Positivos"
                    active
                  />
                  <StatCard
                    value={datasetEvalResult.failures}
                    label="Fallos (Misses)"
                    active
                  />
                  <StatCard
                    value={`${(datasetEvalResult.duration_ms / 1000).toFixed(2)}s`}
                    label="Duración Total"
                  />
                  <StatCard
                    value={datasetEvalResult.dataset_name}
                    label="Dataset"
                  />
                  <StatCard
                    value={formatDate(datasetEvalResult.created_at)}
                    label="Fecha del Modelo"
                  />
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
                  <p className="text-sm text-slate-400">
                    Haz clic en ejecutar para ver las métricas del modelo.
                  </p>
                </div>
              )}
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
