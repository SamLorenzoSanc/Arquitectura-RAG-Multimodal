"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  BarChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import api from "@/api";
import { useOrganization } from "@/context/OrganizationContext";
import {
  useDocuments,
  useInvalidateDocuments,
  useKnowledgeBases,
} from "@/hooks/useCachedApi";

/* ============================================================
TYPES
============================================================ */

type DistanceMetric = "cosine" | "euclidean" | "manhattan";

interface RetrievedChunk {
  id: string;
  rank: number;
  title: string;
  description: string;
  content: string;

  score: number;
  distance: number | null;

  flag_different_info?: boolean;
  flag_out_of_knowledge?: boolean;
}

interface RetrievalInfo {
  original_query: string;
  rewritten_query: string;

  retrieved_chunks: number;
  rewritten_chunks: number;
  merged_chunks: number;

  dense_original_chunks: number;
  dense_rewritten_chunks: number;

  bm25_original_chunks: number;
  bm25_rewritten_chunks: number;

  candidate_chunks: number;
  final_chunks: number;

  retrieval_k: number;
  bm25_k: number;
  candidate_k: number;
  final_k: number;
  rrf_k: number;

  reranking: boolean;
  reranker: string;

  query_rewriting: boolean;
  parallel_retrieval: boolean;
}

interface RetrievalResponse {
  question: string;
  chunks: RetrievedChunk[];
  retrieval?: RetrievalInfo;
}

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

interface DocumentsResponse {
  documents?: RagDocument[];
}

/* ============================================================
DATASET EVALUATION
============================================================ */

interface DatasetEvaluationResult {
  model_date?: string;
  dataset_name: string;

  distance_metric?: DistanceMetric | string;

  recall_1: number;
  recall_k: number;
  precision_at_k?: number;
  ndcg?: number;
  mrr: number;

  false_positives: number;
  failures: number;

  duration_ms: number;

  created_at?: string;
  create_at?: string;
  cached?: boolean;
}

interface RetrievalAuditRow {
  id: number;
  question: string;
  qLabel: string;
  mrr: number;
  ndcg: number;
  coverage: number;
}

interface AnswerAuditRow {
  id: number;
  question: string;
  qLabel: string;
  accuracy: number;
  completeness: number;
  relevance: number;
}

interface KnowledgeBase {
  id: string;
  name?: string;
}

/* ============================================================
CONSTANTS
============================================================ */

/* ============================================================
EVALUATION AUDIT THRESHOLDS (match evaluator.py)
============================================================ */
const MRR_GREEN = 0.9;
const MRR_AMBER = 0.75;
const NDCG_GREEN = 0.9;
const NDCG_AMBER = 0.75;
const COVERAGE_GREEN = 90.0;
const COVERAGE_AMBER = 75.0;

const ANSWER_GREEN = 4.5;
const ANSWER_AMBER = 4.0;

/*
 * Métricas disponibles para la evaluación.
 *
 * IMPORTANTE:
 * Estos valores deben coincidir exactamente con los valores
 * aceptados por DatasetEvaluationRequest en FastAPI.
 */
const DISTANCE_METRICS: {
  value: DistanceMetric;
  label: string;
  description: string;
}[] = [
  {
    value: "cosine",
    label: "Coseno",
    description:
      "Mide la similitud angular entre los vectores. Adecuada para embeddings semánticos.",
  },
  {
    value: "euclidean",
    label: "Euclídea (L2)",
    description:
      "Mide la distancia geométrica entre los vectores en el espacio de embeddings.",
  },
  {
    value: "manhattan",
    label: "Manhattan (L1)",
    description:
      "Mide la suma de las diferencias absolutas entre las dimensiones.",
  },
];

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

function getMetricLabel(metric?: string) {
  switch (metric) {
    case "cosine":
      return "Coseno";

    case "euclidean":
      return "Euclídea (L2)";

    case "manhattan":
      return "Manhattan (L1)";

    default:
      return metric || "—";
  }
}

type HistogramBucket = {
  bucket: string;
  count: number;
};

function buildHistogram(
  values: number[],
  step: number,
  maxValue?: number,
  labelFormatter?: (start: number, end: number) => string,
): HistogramBucket[] {
  if (!values.length) {
    return [];
  }

  const effectiveMaxValue = maxValue ?? Math.max(...values, step * 10, 1);

  const formatter =
    labelFormatter ??
    ((start: number, end: number) => `${start.toFixed(1)}–${end.toFixed(1)}`);

  const buckets = Array.from(
    { length: Math.ceil(effectiveMaxValue / step) },
    (_, index) => ({
      start: index * step,
      end: (index + 1) * step,
      count: 0,
    }),
  );

  for (const value of values) {
    if (Number.isNaN(value) || value < 0) {
      continue;
    }

    const index =
      value >= effectiveMaxValue
        ? buckets.length - 1
        : Math.min(buckets.length - 1, Math.floor(value / step));

    buckets[index].count += 1;
  }

  return buckets.map((bucket) => ({
    bucket: formatter(bucket.start, bucket.end),
    count: bucket.count,
  }));
}

function HistogramCard({
  title,
  data,
  color,
}: {
  title: string;
  data: HistogramBucket[];
  color: string;
}) {
  if (!data.length) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-500">
        No hay datos suficientes para generar el histograma de {title}.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-4">
        <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
        <span className="text-[10px] text-slate-400">Buckets</span>
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 10, left: 0, bottom: 45 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="bucket"
              tick={{ fontSize: 10 }}
              interval={0}
              angle={-35}
              textAnchor="end"
              height={50}
            />
            <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
            <Tooltip formatter={(value) => [Number(value ?? 0), "Conteo"]} />
            <Bar dataKey="count" fill={color} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
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
DISTANCE METRIC SELECTOR
============================================================ */

function DistanceMetricSelector({
  value,
  onChange,
  disabled,
}: {
  value: DistanceMetric;
  onChange: (value: DistanceMetric) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <label className="mb-2 block text-xs font-semibold text-slate-700">
        Métrica de distancia
      </label>

      <select
        value={value}
        onChange={(event) => onChange(event.target.value as DistanceMetric)}
        disabled={disabled}
        className="
          h-10
          w-full
          rounded-md
          border
          border-slate-300
          bg-white
          px-3
          text-sm
          text-slate-700
          outline-none
          transition
          focus:border-blue-500
          disabled:cursor-not-allowed
          disabled:bg-slate-50
        "
      >
        {DISTANCE_METRICS.map((metric) => (
          <option key={metric.value} value={metric.value}>
            {metric.label}
          </option>
        ))}
      </select>

      <p className="mt-2 text-[11px] leading-4 text-slate-400">
        {DISTANCE_METRICS.find((metric) => metric.value === value)?.description}
      </p>
    </div>
  );
}

/* ============================================================
MAIN PAGE
============================================================ */

export default function RagDocumentationPage() {
  const { selectedOrg } = useOrganization();
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

  const [tab, setTab] = useState<"indexation" | "evaluation">("indexation");

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  /* ============================================================
  MANUAL RETRIEVAL
  ============================================================ */

  const [manualQuestion, setManualQuestion] = useState("");

  const [retrievedChunks, setRetrievedChunks] = useState<RetrievedChunk[]>([]);

  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);

  const [testingRetrieval, setTestingRetrieval] = useState(false);

  const [savingDataset, setSavingDataset] = useState(false);

  /* ============================================================
  DATASET EVALUATION
  ============================================================ */

  const [datasetEvalResult, setDatasetEvalResult] =
    useState<DatasetEvaluationResult | null>(null);

  // Tests dataset and upload
  const [tests, setTests] = useState<any[]>([]);
  const [loadingTests, setLoadingTests] = useState(false);
  const [uploadingTests, setUploadingTests] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Audit runs
  const [retrievalAudit, setRetrievalAudit] = useState<{
    mrr?: number;
    ndcg?: number;
    coverage?: number;
    progress?: number;
  } | null>(null);

  const [answerAudit, setAnswerAudit] = useState<{
    accuracy?: number;
    completeness?: number;
    relevance?: number;
    progress?: number;
  } | null>(null);

  const [retrievalAuditRows, setRetrievalAuditRows] = useState<
    RetrievalAuditRow[]
  >([]);
  const [answerAuditRows, setAnswerAuditRows] = useState<AnswerAuditRow[]>([]);

  const [retrievalHistogramData, setRetrievalHistogramData] = useState<{
    mrr: HistogramBucket[];
    ndcg: HistogramBucket[];
    coverage: HistogramBucket[];
  } | null>(null);

  const [answerHistogramData, setAnswerHistogramData] = useState<{
    accuracy: HistogramBucket[];
    completeness: HistogramBucket[];
    relevance: HistogramBucket[];
  } | null>(null);

  const [runningDatasetEval, setRunningDatasetEval] = useState(false);

  /*
   * MÉTRICA SELECCIONADA
   *
   * Esta variable controla la métrica utilizada por el backend.
   */
  const [distanceMetric, setDistanceMetric] =
    useState<DistanceMetric>("cosine");

  /* ============================================================
  TEST RETRIEVAL
  ============================================================ */

  const handleTestRetrieval = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!manualQuestion.trim()) {
      return;
    }

    setTestingRetrieval(true);
    setRetrievedChunks([]);
    setSelectedChunkId(null);
    setError(null);

    try {
      const response = await api.post<RetrievalResponse>(
        "/chat/simulator/search",
        {
          question: manualQuestion.trim(),

          /*
           * También enviamos la métrica al simulador.
           *
           * Si tu endpoint /search todavía no acepta este campo,
           * puedes eliminar esta propiedad del payload del search.
           */
          distance_metric: distanceMetric,
        },
      );

      console.log("RETRIEVAL RESPONSE:", response.data);

      const chunks = response.data?.chunks ?? [];

      setRetrievedChunks(chunks);
    } catch (err: any) {
      console.error("Error al simular retrieval:", err);

      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          "No se pudo ejecutar el retrieval.",
      );
    } finally {
      setTestingRetrieval(false);
    }
  };

  /* ============================================================
  TESTS DATASET HELPERS
  ============================================================ */
  const fetchTests = async () => {
    setLoadingTests(true);
    try {
      const res = await api.get("/chat/evaluation/tests");
      const data = res.data?.tests ?? [];
      setTests(data);
    } catch (err: any) {
      console.error("Error loading tests:", err);
      setTests([]);
    } finally {
      setLoadingTests(false);
    }
  };

  useEffect(() => {
    if (tab === "evaluation") {
      fetchTests();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const handleUploadTests = async (f?: File) => {
    const file = f ?? (fileInputRef.current?.files?.[0] as File | undefined);
    if (!file) return;

    setUploadingTests(true);
    try {
      const fd = new FormData();
      fd.append("file", file, file.name);

      const res = await api.post("/chat/evaluation/upload-tests", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      console.log("upload res", res.data);
      await fetchTests();
      setMessage(`Tests subidos: ${res.data.uploaded}`);
    } catch (err: any) {
      console.error("Error uploading tests:", err);
      setError(err.response?.data?.detail || err.message || "Error");
    } finally {
      setUploadingTests(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  /* ============================================================
  FULL AUDIT (all tests)
  ============================================================ */
  const runRetrievalAuditAll = async () => {
    if (!tests || tests.length === 0) return;
    setRetrievalAudit({ progress: 0 });
    setRetrievalAuditRows([]);

    let totalMrr = 0;
    let totalNdcg = 0;
    let totalCoverage = 0;

    const rows: RetrievalAuditRow[] = [];
    const mrrValues: number[] = [];
    const ndcgValues: number[] = [];
    const coverageValues: number[] = [];

    for (let i = 0; i < tests.length; i++) {
      const id = tests[i].id; // id is index in backend
      try {
        const res = await api.post(`/chat/evaluation/retrieval/${id}`);
        const r = res.data.retrieval;
        totalMrr += r.mrr ?? 0;
        totalNdcg += r.ndcg ?? 0;
        totalCoverage += r.keyword_coverage ?? 0;

        mrrValues.push(r.mrr ?? 0);
        ndcgValues.push(r.ndcg ?? 0);
        coverageValues.push(r.keyword_coverage ?? 0);

        rows.push({
          id,
          question: tests[i].question,
          qLabel: `${id + 1}. ${tests[i].question.slice(0, 40)}...`,
          mrr: Number((r.mrr ?? 0).toFixed(3)),
          ndcg: Number((r.ndcg ?? 0).toFixed(3)),
          coverage: Number((r.keyword_coverage ?? 0).toFixed(1)),
        });
      } catch (err) {
        console.error("Error evaluating retrieval test", id, err);
      }

      setRetrievalAudit({
        progress: Math.round(((i + 1) / tests.length) * 100),
      });
    }

    const count = tests.length;
    setRetrievalAuditRows(rows);
    setRetrievalHistogramData({
      mrr: buildHistogram(
        mrrValues,
        0.1,
        1,
        (start, end) => `${start.toFixed(1)}–${end.toFixed(1)}`,
      ),
      ndcg: buildHistogram(
        ndcgValues,
        0.1,
        1,
        (start, end) => `${start.toFixed(1)}–${end.toFixed(1)}`,
      ),
      coverage: buildHistogram(
        coverageValues,
        10,
        100,
        (start, end) => `${start.toFixed(0)}–${end.toFixed(0)}%`,
      ),
    });
    setRetrievalAudit({
      mrr: totalMrr / count,
      ndcg: totalNdcg / count,
      coverage: totalCoverage / count,
      progress: 100,
    });
  };

  const runAnswerAuditAll = async () => {
    if (!tests || tests.length === 0) return;
    setAnswerAudit({ progress: 0 });
    setAnswerAuditRows([]);

    let totalAcc = 0;
    let totalComp = 0;
    let totalRel = 0;

    const rows: AnswerAuditRow[] = [];
    const accuracyValues: number[] = [];
    const completenessValues: number[] = [];
    const relevanceValues: number[] = [];

    for (let i = 0; i < tests.length; i++) {
      const id = tests[i].id;
      try {
        const res = await api.post(`/chat/evaluation/answer/${id}`);
        const ev = res.data.evaluation;
        totalAcc += ev.accuracy ?? 0;
        totalComp += ev.completeness ?? 0;
        totalRel += ev.relevance ?? 0;

        accuracyValues.push(ev.accuracy ?? 0);
        completenessValues.push(ev.completeness ?? 0);
        relevanceValues.push(ev.relevance ?? 0);

        rows.push({
          id,
          question: tests[i].question,
          qLabel: `${id + 1}. ${tests[i].question.slice(0, 40)}...`,
          accuracy: Number((ev.accuracy ?? 0).toFixed(2)),
          completeness: Number((ev.completeness ?? 0).toFixed(2)),
          relevance: Number((ev.relevance ?? 0).toFixed(2)),
        });
      } catch (err) {
        console.error("Error evaluating answer test", id, err);
      }

      setAnswerAudit({ progress: Math.round(((i + 1) / tests.length) * 100) });
    }

    const count = tests.length;
    setAnswerAuditRows(rows);
    setAnswerHistogramData({
      accuracy: buildHistogram(
        accuracyValues,
        0.5,
        5,
        (start, end) => `${start.toFixed(1)}–${end.toFixed(1)}`,
      ),
      completeness: buildHistogram(
        completenessValues,
        0.5,
        5,
        (start, end) => `${start.toFixed(1)}–${end.toFixed(1)}`,
      ),
      relevance: buildHistogram(
        relevanceValues,
        0.5,
        5,
        (start, end) => `${start.toFixed(1)}–${end.toFixed(1)}`,
      ),
    });
    setAnswerAudit({
      accuracy: totalAcc / count,
      completeness: totalComp / count,
      relevance: totalRel / count,
      progress: 100,
    });
  };

  /* ============================================================
  FLAGS
  ============================================================ */

  const handleToggleFlag = (
    chunkId: string,
    flagType: "flag_different_info" | "flag_out_of_knowledge",
  ) => {
    setRetrievedChunks((prev) =>
      prev.map((chunk) =>
        chunk.id === chunkId
          ? {
              ...chunk,
              [flagType]: !chunk[flagType],
            }
          : chunk,
      ),
    );
  };

  /* ============================================================
  SAVE DATASET
  ============================================================ */

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

      setMessage("Pregunta y referencia guardadas correctamente.");

      setManualQuestion("");
      setRetrievedChunks([]);
      setSelectedChunkId(null);
    } catch (err: any) {
      console.error("Error al guardar el dataset:", err);

      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          "No se pudo guardar el registro de evaluación.",
      );
    } finally {
      setSavingDataset(false);
    }
  };

  /* ============================================================
  EXECUTE DATASET EVALUATION
  ============================================================ */

  const handleExecuteDatasetEvaluation = async () => {
    if (runningDatasetEval) {
      return;
    }

    setRunningDatasetEval(true);
    setError(null);
    setMessage(null);

    /*
     * PAYLOAD ACTUALIZADO
     *
     * distance_metric es ahora una propiedad explícita.
     */
    const payload = {
      model_name: "llama3.2",

      embedding_model: "qwen3-embedding:latest",

      distance_metric: distanceMetric,

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
      const response = await api.post<DatasetEvaluationResult>(
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

      setMessage(
        `Evaluación completada utilizando la distancia ${getMetricLabel(
          distanceMetric,
        )}.`,
      );
    } catch (err: any) {
      console.error("ERROR EVALUATION:", err.response?.data || err);

      const detail = err.response?.data?.detail;

      let errorMessage = "No se pudo ejecutar la evaluación.";

      if (Array.isArray(detail)) {
        errorMessage = detail
          .map((item) => item.msg || JSON.stringify(item))
          .join(", ");
      } else if (typeof detail === "string") {
        errorMessage = detail;
      }

      setError(errorMessage);
    } finally {
      setRunningDatasetEval(false);
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

  /* ============================================================
  AUTO REFRESH
  ============================================================ */

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
                Estado de indexación, retrieval y evaluación del RAG
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
            <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-1">
                <StatCard value={stats.total} label="Total" active />

                <StatCard value={stats.active} label="Activos" />

                <StatCard value={stats.inactive} label="Inactivos" />

                <StatCard value={stats.processing} label="Procesando" />

                <StatCard value={stats.failed} label="Fallidos" />
              </div>

              <p className="text-xs text-slate-400">
                Catálogo histórico en modo solo lectura
              </p>
            </div>

            <div className="mb-4">
              <div className="relative max-w-md">
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Buscar documento por título..."
                  className="h-9 w-full rounded-md border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none placeholder:text-slate-300 focus:border-slate-300"
                />
              </div>
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
                        className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/40"
                      >
                        <td className="px-4 py-3">
                          <div className="min-w-[230px]">
                            <p className="truncate text-xs font-semibold text-slate-700">
                              {document.name}
                            </p>

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
                          <div className="flex justify-end gap-2">
                            {(document.processing_status === "pending" ||
                              document.processing_status === "running") && (
                              <span className="text-xs text-slate-400">
                                Estado histórico: procesando
                              </span>
                            )}
                            <span className="text-xs text-slate-400">Solo lectura</span>
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
            {/* =================================================
                1. RETRIEVAL MANUAL
            ================================================= */}

            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-base font-bold text-slate-800">
                1. Simulador de Retrieval
              </h2>

              <p className="mb-5 mt-1 text-xs text-slate-500">
                Escribe una pregunta para comprobar cómo responde el sistema de
                recuperación.
              </p>

              <div className="mb-5 grid grid-cols-1 gap-5 md:grid-cols-[280px_1fr]">
                <DistanceMetricSelector
                  value={distanceMetric}
                  onChange={setDistanceMetric}
                  disabled={testingRetrieval}
                />

                <div className="rounded-lg border border-blue-100 bg-blue-50/50 p-4">
                  <p className="text-xs font-semibold text-blue-700">
                    Métrica seleccionada
                  </p>

                  <p className="mt-1 text-sm font-bold text-slate-800">
                    {getMetricLabel(distanceMetric)}
                  </p>

                  <p className="mt-1 text-[11px] leading-4 text-slate-500">
                    La métrica seleccionada se utilizará también en la
                    evaluación global del dataset.
                  </p>
                </div>
              </div>

              <form onSubmit={handleTestRetrieval} className="flex gap-3">
                <input
                  type="text"
                  value={manualQuestion}
                  onChange={(e) => setManualQuestion(e.target.value)}
                  placeholder="Ej: ¿Cuál es el procedimiento para la siembra de maíz?"
                  className="h-10 flex-1 rounded-md border border-slate-300 px-4 text-sm outline-none shadow-xs focus:border-blue-500"
                />

                <button
                  type="submit"
                  disabled={testingRetrieval || !manualQuestion.trim()}
                  className="rounded-md bg-slate-900 px-5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
                >
                  {testingRetrieval ? "Buscando..." : "Probar Retrieval"}
                </button>
              </form>
            </div>

            {/* =================================================
                2. RESULTADOS RETRIEVAL
            ================================================= */}

            {retrievedChunks.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-800">
                      Chunks recuperados
                    </h3>

                    <p className="mt-1 text-xs text-slate-500">
                      Selecciona el chunk que contiene la respuesta correcta.
                    </p>
                  </div>

                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                    {retrievedChunks.length} resultados
                  </span>
                </div>

                <div className="space-y-4">
                  {retrievedChunks.map((chunk) => {
                    const isSelected = selectedChunkId === chunk.id;

                    return (
                      <div
                        key={chunk.id}
                        className={`
                            relative rounded-lg border p-4 transition-all
                            ${
                              isSelected
                                ? "border-emerald-500 bg-emerald-50/50 shadow-sm"
                                : "border-slate-200 bg-slate-50 hover:border-slate-300"
                            }
                          `}
                      >
                        <div className="absolute left-4 top-4">
                          <input
                            type="radio"
                            name="selected_chunk"
                            checked={isSelected}
                            onChange={() => setSelectedChunkId(chunk.id)}
                            className="h-4 w-4 cursor-pointer accent-emerald-600"
                          />
                        </div>

                        <div className="ml-8">
                          <div className="flex items-start justify-between gap-6">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="rounded bg-slate-200 px-2 py-0.5 text-[10px] font-bold text-slate-600">
                                  #{chunk.rank}
                                </span>

                                <h4 className="truncate text-sm font-bold text-slate-800">
                                  {chunk.title || "Sin título"}
                                </h4>
                              </div>

                              <p className="mt-1 text-[10px] text-slate-400">
                                ID: {chunk.id}
                              </p>
                            </div>

                            <div className="flex shrink-0 gap-5">
                              <div className="text-right">
                                <span className="block text-[9px] uppercase tracking-wider text-slate-400">
                                  Distancia
                                </span>

                                <span className="font-mono text-sm font-bold text-blue-600">
                                  {chunk.distance !== null &&
                                  chunk.distance !== undefined
                                    ? chunk.distance.toFixed(4)
                                    : "—"}
                                </span>

                                <span className="mt-0.5 block text-[9px] text-slate-400">
                                  {getMetricLabel(distanceMetric)}
                                </span>
                              </div>

                              <div className="text-right">
                                <span className="block text-[9px] uppercase tracking-wider text-slate-400">
                                  Score
                                </span>

                                <span className="font-mono text-sm font-bold text-purple-600">
                                  {chunk.score !== undefined
                                    ? chunk.score.toExponential(2)
                                    : "—"}
                                </span>
                              </div>
                            </div>
                          </div>

                          {chunk.description && (
                            <div className="mt-3 rounded-md border border-slate-100 bg-white p-3">
                              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                Descripción
                              </p>

                              <p className="whitespace-pre-wrap text-xs leading-5 text-slate-600">
                                {chunk.description}
                              </p>
                            </div>
                          )}

                          {chunk.content && (
                            <details className="mt-2 rounded-md border border-slate-100 bg-white">
                              <summary className="cursor-pointer px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500 hover:text-slate-700">
                                Ver contenido completo
                              </summary>

                              <div className="border-t border-slate-100 px-3 py-3">
                                <p className="whitespace-pre-wrap text-xs leading-5 text-slate-600">
                                  {chunk.content}
                                </p>
                              </div>
                            </details>
                          )}

                          <div className="mt-4 flex flex-wrap gap-4 border-t border-slate-200/60 pt-3">
                            <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-700">
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

                              <span>Devolvió información distinta</span>
                            </label>

                            <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-700">
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

                              <span>Fuera de conocimiento</span>
                            </label>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
                  <p className="text-xs text-slate-400">
                    {selectedChunkId
                      ? "Chunk correcto seleccionado."
                      : "Selecciona el chunk correcto antes de guardar."}
                  </p>

                  <button
                    type="button"
                    onClick={handleSaveQuestionSet}
                    disabled={savingDataset || !selectedChunkId}
                    className="rounded-md bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {savingDataset
                      ? "Guardando..."
                      : "Guardar juego de preguntas"}
                  </button>
                </div>
              </div>
            )}

            {/* =================================================
                3. DATASET EVALUATION
            ================================================= */}

            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-6 flex items-start justify-between gap-6">
                <div>
                  <h2 className="text-base font-bold text-slate-800">
                    2. Evaluación del Dataset Consolidado
                  </h2>

                  <p className="mt-1 text-xs text-slate-500">
                    Ejecuta la evaluación completa utilizando la métrica de
                    distancia seleccionada.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={handleExecuteDatasetEvaluation}
                  disabled={runningDatasetEval}
                  className="shrink-0 rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                >
                  {runningDatasetEval ? "Ejecutando..." : "Ejecutar evaluación"}
                </button>
              </div>

              {/* =================================================
                  CONFIGURACIÓN DE EVALUACIÓN
              ================================================= */}

              <div className="mb-6 rounded-xl border border-slate-200 bg-slate-50/50 p-5">
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-slate-800">
                    Configuración de Retrieval
                  </h3>

                  <p className="mt-1 text-[11px] text-slate-400">
                    Selecciona la métrica utilizada para calcular la distancia
                    entre embeddings.
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                  {DISTANCE_METRICS.map((metric) => {
                    const selected = distanceMetric === metric.value;

                    return (
                      <button
                        key={metric.value}
                        type="button"
                        disabled={runningDatasetEval}
                        onClick={() => setDistanceMetric(metric.value)}
                        className={`
                            rounded-lg
                            border
                            p-4
                            text-left
                            transition
                            ${
                              selected
                                ? "border-blue-500 bg-blue-50 shadow-sm"
                                : "border-slate-200 bg-white hover:border-slate-300"
                            }
                            disabled:cursor-not-allowed
                            disabled:opacity-60
                          `}
                      >
                        <div className="flex items-center justify-between">
                          <span
                            className={`
                                text-sm font-semibold
                                ${selected ? "text-blue-700" : "text-slate-700"}
                              `}
                          >
                            {metric.label}
                          </span>

                          <span
                            className={`
                                flex h-4 w-4 items-center justify-center rounded-full border
                                ${
                                  selected
                                    ? "border-blue-600 bg-blue-600"
                                    : "border-slate-300 bg-white"
                                }
                              `}
                          >
                            {selected && (
                              <span className="h-1.5 w-1.5 rounded-full bg-white" />
                            )}
                          </span>
                        </div>

                        <p className="mt-2 text-[11px] leading-4 text-slate-500">
                          {metric.description}
                        </p>
                      </button>
                    );
                  })}
                </div>

                <div className="mt-4 flex items-center gap-2 rounded-md border border-blue-100 bg-blue-50 px-3 py-2">
                  <span className="text-[11px] font-medium text-blue-700">
                    Métrica actual:
                  </span>

                  <span className="text-[11px] font-bold text-blue-900">
                    {getMetricLabel(distanceMetric)}
                  </span>
                </div>
              </div>

              {/* =================================================
                  RESULTS
              ================================================= */}

              {datasetEvalResult ? (
                <>
                  <div className="mb-5 rounded-lg border border-emerald-100 bg-emerald-50/50 p-4">
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                      <div>
                        <span className="block text-[9px] uppercase tracking-wide text-slate-400">
                          Métrica
                        </span>

                        <span className="text-sm font-bold text-slate-800">
                          {getMetricLabel(
                            datasetEvalResult.distance_metric ?? distanceMetric,
                          )}
                        </span>
                      </div>

                      <div>
                        <span className="block text-[9px] uppercase tracking-wide text-slate-400">
                          Dataset
                        </span>

                        <span className="text-sm font-bold text-slate-800">
                          {datasetEvalResult.dataset_name}
                        </span>
                      </div>

                      <div>
                        <span className="block text-[9px] uppercase tracking-wide text-slate-400">
                          Modelo
                        </span>

                        <span className="text-sm font-bold text-slate-800">
                          {datasetEvalResult.model_date ?? "—"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
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
                      label="Fallos"
                      active
                    />

                    <StatCard
                      value={`${(datasetEvalResult.duration_ms / 1000).toFixed(
                        2,
                      )}s`}
                      label="Duración"
                    />

                    <StatCard
                      value={datasetEvalResult.dataset_name}
                      label="Dataset"
                    />

                    <StatCard
                      value={formatDate(
                        datasetEvalResult.created_at ??
                          datasetEvalResult.create_at,
                      )}
                      label="Fecha"
                    />
                  </div>
                </>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
                  <p className="text-sm text-slate-400">
                    Selecciona una métrica y ejecuta la evaluación para obtener
                    las métricas del RAG.
                  </p>
                </div>
              )}

              {/* =================================================
                  DATASET DE PRUEBAS + JSON UPLOAD
              ================================================= */}

              <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-sm font-bold text-slate-800">
                  Dataset de Pruebas
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  Listado de preguntas con las que se trabaja. Puedes subir un
                  JSON/JSONL para reemplazar el dataset de pruebas.
                </p>

                <div className="mt-4 flex items-center gap-3">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="application/json,text/json"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.[0])
                        handleUploadTests(e.target.files[0]);
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="rounded-md border px-3 py-2 text-sm"
                  >
                    Subir JSON de tests
                  </button>
                  <button
                    type="button"
                    onClick={fetchTests}
                    className="rounded-md border px-3 py-2 text-sm"
                  >
                    Refrescar listado
                  </button>
                  <button
                    type="button"
                    onClick={runRetrievalAuditAll}
                    className="ml-auto rounded-md bg-blue-600 px-3 py-2 text-sm text-white"
                  >
                    Ejecutar auditoría IR
                  </button>
                  <button
                    type="button"
                    onClick={runAnswerAuditAll}
                    className="rounded-md bg-purple-600 px-3 py-2 text-sm text-white"
                  >
                    Ejecutar auditoría respuestas
                  </button>
                </div>

                <div className="mt-4">
                  {loadingTests ? (
                    <div className="text-xs text-slate-400">
                      Cargando tests...
                    </div>
                  ) : tests.length === 0 ? (
                    <div className="text-xs text-slate-400">
                      No hay tests cargados.
                    </div>
                  ) : (
                    <div className="mt-3 max-h-64 overflow-auto border border-slate-100 p-2">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-left text-slate-500">
                            <th className="px-2 py-1">#</th>
                            <th className="px-2 py-1">Pregunta</th>
                            <th className="px-2 py-1">Keywords</th>
                            <th className="px-2 py-1">Categoría</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tests.map((t) => (
                            <tr key={t.id} className="border-t">
                              <td className="px-2 py-1 text-slate-600">
                                {t.id}
                              </td>
                              <td
                                className="px-2 py-1 truncate"
                                title={t.question}
                              >
                                {t.question}
                              </td>
                              <td className="px-2 py-1">
                                {(t.keywords || []).join(", ")}
                              </td>
                              <td className="px-2 py-1">{t.category}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div>
                    <h4 className="text-xs font-semibold text-slate-700">
                      Auditoría IR
                    </h4>
                    {retrievalAudit ? (
                      <div className="mt-2 space-y-2">
                        <div className="text-xs text-slate-500">
                          Progreso: {retrievalAudit.progress ?? 0}%
                        </div>
                        <div className="w-full rounded bg-slate-100 h-4 overflow-hidden">
                          <div
                            style={{
                              width: `${retrievalAudit.progress ?? 0}%`,
                            }}
                            className="h-4 bg-blue-600"
                          />
                        </div>
                        <div className="mt-2 text-xs">
                          <div>MRR: {(retrievalAudit.mrr ?? 0).toFixed(3)}</div>
                          <div>
                            nDCG: {(retrievalAudit.ndcg ?? 0).toFixed(3)}
                          </div>
                          <div>
                            Cobertura:{" "}
                            {(retrievalAudit.coverage ?? 0).toFixed(1)}%
                          </div>
                        </div>

                        <div className="mt-2 flex gap-2">
                          <div className="flex-1">
                            <div className="text-[10px] text-slate-500">
                              MRR
                            </div>
                            <div className="w-full bg-slate-100 h-3 rounded mt-1">
                              <div
                                style={{
                                  width: `${Math.min(100, (retrievalAudit.mrr ?? 0) * 100)}%`,
                                  background:
                                    (retrievalAudit.mrr ?? 0) >= MRR_GREEN
                                      ? "#10b981"
                                      : (retrievalAudit.mrr ?? 0) >= MRR_AMBER
                                        ? "#f59e0b"
                                        : "#ef4444",
                                }}
                                className="h-3 rounded"
                              />
                            </div>
                          </div>

                          <div className="flex-1">
                            <div className="text-[10px] text-slate-500">
                              nDCG
                            </div>
                            <div className="w-full bg-slate-100 h-3 rounded mt-1">
                              <div
                                style={{
                                  width: `${Math.min(100, (retrievalAudit.ndcg ?? 0) * 100)}%`,
                                  background:
                                    (retrievalAudit.ndcg ?? 0) >= NDCG_GREEN
                                      ? "#10b981"
                                      : (retrievalAudit.ndcg ?? 0) >= NDCG_AMBER
                                        ? "#f59e0b"
                                        : "#ef4444",
                                }}
                                className="h-3 rounded"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs text-slate-400">
                        No se ha ejecutado la auditoría IR.
                      </div>
                    )}
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-slate-700">
                      Auditoría Respuestas
                    </h4>
                    {answerAudit ? (
                      <div className="mt-2 space-y-2">
                        <div className="text-xs text-slate-500">
                          Progreso: {answerAudit.progress ?? 0}%
                        </div>
                        <div className="w-full rounded bg-slate-100 h-4 overflow-hidden">
                          <div
                            style={{ width: `${answerAudit.progress ?? 0}%` }}
                            className="h-4 bg-purple-600"
                          />
                        </div>
                        <div className="mt-2 text-xs">
                          <div>
                            Accuracy: {(answerAudit.accuracy ?? 0).toFixed(2)} /
                            5
                          </div>
                          <div>
                            Completeness:{" "}
                            {(answerAudit.completeness ?? 0).toFixed(2)} / 5
                          </div>
                          <div>
                            Relevance: {(answerAudit.relevance ?? 0).toFixed(2)}{" "}
                            / 5
                          </div>
                        </div>

                        <div className="mt-2 flex gap-2">
                          <div className="flex-1">
                            <div className="text-[10px] text-slate-500">
                              Accuracy
                            </div>
                            <div className="w-full bg-slate-100 h-3 rounded mt-1">
                              <div
                                style={{
                                  width: `${Math.min(100, ((answerAudit.accuracy ?? 0) / 5) * 100)}%`,
                                  background:
                                    (answerAudit.accuracy ?? 0) >= ANSWER_GREEN
                                      ? "#10b981"
                                      : (answerAudit.accuracy ?? 0) >= ANSWER_AMBER
                                        ? "#f59e0b"
                                        : "#ef4444",
                                }}
                                className="h-3 rounded"
                              />
                            </div>
                          </div>

                          <div className="flex-1">
                            <div className="text-[10px] text-slate-500">
                              Completeness
                            </div>
                            <div className="w-full bg-slate-100 h-3 rounded mt-1">
                              <div
                                style={{
                                  width: `${Math.min(100, ((answerAudit.completeness ?? 0) / 5) * 100)}%`,
                                  background:
                                    (answerAudit.completeness ?? 0) >= ANSWER_GREEN
                                      ? "#10b981"
                                      : (answerAudit.completeness ?? 0) >= ANSWER_AMBER
                                        ? "#f59e0b"
                                        : "#ef4444",
                                }}
                                className="h-3 rounded"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs text-slate-400">
                        No se ha ejecutado la auditoría de respuestas.
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="grid gap-4 xl:grid-cols-2">
                    <div className="space-y-4">
                      <div className="text-sm font-semibold text-slate-800">
                        Histogramas Retrieval
                      </div>
                      <div className="grid gap-4 md:grid-cols-3">
                        <HistogramCard
                          title="MRR"
                          data={retrievalHistogramData?.mrr ?? []}
                          color="#0ea5e9"
                        />
                        <HistogramCard
                          title="nDCG"
                          data={retrievalHistogramData?.ndcg ?? []}
                          color="#6366f1"
                        />
                        <HistogramCard
                          title="Cobertura"
                          data={retrievalHistogramData?.coverage ?? []}
                          color="#14b8a6"
                        />
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="text-sm font-semibold text-slate-800">
                        Histogramas Answer
                      </div>
                      <div className="grid gap-4 md:grid-cols-3">
                        <HistogramCard
                          title="Accuracy"
                          data={answerHistogramData?.accuracy ?? []}
                          color="#8b5cf6"
                        />
                        <HistogramCard
                          title="Completeness"
                          data={answerHistogramData?.completeness ?? []}
                          color="#ec4899"
                        />
                        <HistogramCard
                          title="Relevance"
                          data={answerHistogramData?.relevance ?? []}
                          color="#f59e0b"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

    </div>
  );
}
