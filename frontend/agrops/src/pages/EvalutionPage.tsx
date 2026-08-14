"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "@/api";
import { useOrganization } from "@/context/OrganizationContext";
import {
  useEvaluationTests,
  useKnowledgeBases,
} from "@/hooks/useCachedApi";
import AnnotatePanel from "@/components/evaluation/AnnotatePanel";
import BankPanel from "@/components/evaluation/BankPanel";
import ExperimentHistory from "@/components/evaluation/ExperimentHistory";
import ConfigurableEvaluationLab from "@/components/evaluation/ConfigurableEvaluationLab";
import { categoryLabel } from "@/components/evaluation/labels";
import ValidacionHumanaPage from "@/pages/ValidacionHumanaPage";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ReferenceLine, 
  ResponsiveContainer 
} from "recharts";

type EvalTab = "anotar" | "banco" | "metricas" | "validacion";

const EVAL_TABS: { id: EvalTab; label: string }[] = [
  { id: "anotar", label: "Anotar" },
  { id: "banco", label: "Banco" },
  { id: "metricas", label: "Métricas" },
  { id: "validacion", label: "Validación humana" },
];

type TestItem = {
  id: number;
  question: string;
  keywords: string[];
  reference_answer: string;
  category: string;
  source?: string;
};

type RetrievalResult = {
  test_id?: number;
  id?: number;
  question: string;
  category: string;
  mrr?: number;
  ndcg?: number;
  keyword_coverage?: number;
  accuracy?: number;
  retrieval?: {
    mrr: number;
    ndcg: number;
    keywords_found: number;
    total_keywords: number;
    keyword_coverage: number;
    accuracy: number;
  };
};

type AnswerResult = {
  test_id?: number;
  id?: number;
  question: string;
  category: string;
  generated_answer?: string;
  accuracy?: number;
  precision?: number;
  completeness?: number;
  relevance?: number;
  faithfulness?: number;
  groundedness?: number;
  citation_accuracy?: number;
  abstention?: number;
  feedback?: string;
  evaluation?: {
    feedback: string;
    accuracy: number;
    precision?: number;
    completeness: number;
    relevance: number;
    faithfulness?: number;
    groundedness?: number;
    citation_accuracy?: number;
    abstention?: number;
  };
};

function getRetrievalMetric(item: RetrievalResult | undefined | null, metric: string): number {
  if (!item) return 0;
  
  const target = (item.retrieval || item) as Record<string, any>;
  if (target[metric] !== undefined && target[metric] !== null) {
    const val = Number(target[metric]);
    if (!isNaN(val)) return val;
  }
  return 0;
}

function getAnswerMetric(item: AnswerResult | undefined | null, metric: string): number {
  if (!item) return 0;

  const rawItem = item as unknown as Record<string, any>;
  const target = (rawItem.evaluation || rawItem.data || rawItem) as Record<string, any>;

  const metricAliases: Record<string, string[]> = {
    accuracy: ["accuracy", "punteria", "accuracy_score", "score"],
    precision: ["precision", "sin_paja", "precision_score", "faithfulness"],
    completeness: ["completeness", "exhaustividad", "completeness_score"],
    relevance: ["relevance", "utilidad", "relevance_score"],
    faithfulness: ["faithfulness", "fidelidad"],
    groundedness: ["groundedness", "anclaje", "grounded"],
    citation_accuracy: ["citation_accuracy", "citas"],
    abstention: ["abstention", "abstencion"],
  };

  const aliases = metricAliases[metric] || [metric];

  for (const alias of aliases) {
    if (target[alias] !== undefined && target[alias] !== null) {
      const val = Number(target[alias]);
      if (!isNaN(val)) return val;
    }
    if (rawItem[alias] !== undefined && rawItem[alias] !== null) {
      const val = Number(rawItem[alias]);
      if (!isNaN(val)) return val;
    }
  }

  return 0;
}

function getFeedbackText(item: AnswerResult | undefined | null): string {
  if (!item) return "";
  return item.evaluation?.feedback || item.feedback || "";
}

/**
 * Convierte una métrica a porcentaje.
 * 0–1 (MRR, nDCG, citas) se multiplica por 100; 1–5 (juez Likert) se escala;
 * valores >5 se interpretan ya como porcentaje.
 */
function getSafePercentage(value: number): number {
  if (value === 0) return 0;
  if (!value || isNaN(value)) return 0;
  let scaled: number;
  if (value > 0 && value <= 1) {
    scaled = value * 100;
  } else if (value <= 5) {
    scaled = (value / 5) * 100;
  } else {
    scaled = value;
  }
  return Math.round(Math.min(Math.max(scaled, 0), 100));
}

function getUnitPercentage(value: number): number {
  if (!value || isNaN(value)) return 0;
  const scaled = value > 1 ? value : value * 100;
  return Math.round(Math.min(Math.max(scaled, 0), 100));
}

export default function AuditPage() {
  const { selectedOrg } = useOrganization();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tab: EvalTab = EVAL_TABS.some((item) => item.id === tabParam)
    ? (tabParam as EvalTab)
    : "metricas";
  const setTab = (next: EvalTab) => {
    setSearchParams(next === "metricas" ? {} : { tab: next }, { replace: true });
  };

  const [retrieval, setRetrieval] = useState<RetrievalResult[]>([]);
  const [answers, setAnswers] = useState<AnswerResult[]>([]);
  const [running, setRunning] = useState(false);
  const [runningStep, setRunningStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [selectedKbId, setSelectedKbId] = useState("");
  const [distanceMetric, setDistanceMetric] = useState<
    "cosine" | "euclidean" | "manhattan"
  >("cosine");
  const [embeddingModel, setEmbeddingModel] = useState("qwen3-embedding:latest");
  const [indexedModels, setIndexedModels] = useState<string[]>([
    "qwen3-embedding:latest",
  ]);
  const [experiments, setExperiments] = useState<
    Array<{
      id: number;
      created_at: string;
      embedding_model: string;
      distance_metric: string;
      dataset_size: number;
      recall_1: number;
      recall_k: number;
      mrr: number;
      ndcg?: number | null;
      precision_at_k?: number | null;
      keyword_coverage?: number | null;
      accuracy?: number | null;
      failures: number;
      duration_ms: number;
      experiment_type?: string;
    }>
  >([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [bestMrrId, setBestMrrId] = useState<number | null>(null);
  const [datasetEval, setDatasetEval] = useState<{
    recall_1: number;
    recall_k: number;
    mrr: number;
    ndcg?: number;
    false_positives: number;
    failures: number;
  } | null>(null);

  const {
    data: cachedTests,
    isLoading: loadingTests,
    isError: testsError,
    refetch: refetchTests,
  } = useEvaluationTests();
  const { data: kbList } = useKnowledgeBases(selectedOrg?.id);

  const tests = (cachedTests as TestItem[] | undefined) ?? [];
  const knowledgeBases = useMemo(
    () => (kbList ?? []).map((kb) => ({ id: kb.id, name: kb.name })),
    [kbList],
  );

  const evalParams = useMemo(() => {
    const params: Record<string, string> = {};
    if (selectedOrg?.id) params.organization_id = selectedOrg.id;
    if (selectedKbId) params.knowledge_base_id = selectedKbId;
    params.distance_metric = distanceMetric;
    params.embedding_model = embeddingModel;
    return params;
  }, [selectedOrg?.id, selectedKbId, distanceMetric, embeddingModel]);

  useEffect(() => {
    if (testsError) {
      setError("No se pudieron cargar los tests desde el backend.");
    }
  }, [testsError]);

  useEffect(() => {
    setSelectedKbId((prev) => prev || knowledgeBases[0]?.id || "");
  }, [knowledgeBases]);

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const [historyRes, modelsRes] = await Promise.all([
        api.get("/chat/evaluation/experiments"),
        api.get("/chat/evaluation/embedding-models"),
      ]);
      setExperiments(historyRes.data ?? []);
      const indexed = modelsRes.data?.indexed ?? [];
      if (indexed.length) {
        setIndexedModels(indexed);
        setEmbeddingModel((prev) =>
          indexed.includes(prev) ? prev : indexed[0],
        );
      }
    } catch {
      /* el historial puede no existir aún en Render */
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (tab === "metricas") {
      void loadHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const saveExperiment = async () => {
    setRunning(true);
    setRunningStep("Guardando corrida embedding × distancia…");
    setError(null);
    try {
      const response = await api.post("/chat/evaluation/experiments", {
        embedding_model: embeddingModel,
        distance_metric: distanceMetric,
        top_k: 10,
        knowledge_base_id: selectedKbId || null,
      });
      setBestMrrId(response.data?.id ?? null);
      await loadHistory();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "No se pudo guardar la corrida experimental.",
      );
    } finally {
      setRunning(false);
      setRunningStep(null);
    }
  };

  const compareDistances = async () => {
    setRunning(true);
    setRunningStep("Comparando coseno, L2 y L1 sobre el mismo embedding…");
    setError(null);
    try {
      const response = await api.post("/chat/evaluation/experiments/compare", {
        embedding_models: [embeddingModel],
        distance_metrics: ["cosine", "euclidean", "manhattan"],
        top_k: 10,
        knowledge_base_id: selectedKbId || null,
      });
      setBestMrrId(response.data?.best_mrr_id ?? null);
      await loadHistory();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "No se pudo comparar distancias.",
      );
    } finally {
      setRunning(false);
      setRunningStep(null);
    }
  };

  const compareEmbeddings = async () => {
    const models = indexedModels.length >= 2 ? indexedModels : [embeddingModel];
    if (models.length < 2) {
      setError(
        "Reindexa el corpus con al menos dos embeddings en Documentación para comparar cuál mejora al otro.",
      );
      return;
    }
    setRunning(true);
    setRunningStep("Comparando embeddings sobre la misma distancia…");
    setError(null);
    try {
      const response = await api.post("/chat/evaluation/experiments/compare", {
        embedding_models: models,
        distance_metrics: [distanceMetric],
        top_k: 10,
        knowledge_base_id: selectedKbId || null,
      });
      setBestMrrId(response.data?.best_mrr_id ?? null);
      await loadHistory();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "No se pudo comparar embeddings.",
      );
    } finally {
      setRunning(false);
      setRunningStep(null);
    }
  };

  const loadTests = async () => {
    setError(null);
    await refetchTests();
  };

  const runRetrieval = async () => {
    if (!tests.length) return;
    setRunning(true);
    setRunningStep("Evaluando motor de búsqueda...");
    setError(null);

    try {
      const promises = tests.map((test) =>
        api.post<RetrievalResult>(`/chat/evaluation/retrieval/${test.id}`, null, {
          params: evalParams,
        })
      );
      
      const settledResults = await Promise.allSettled(promises);
      
      const successfulResults = settledResults
        .filter((res: any) => res.status === "fulfilled")
        .map((res: any) => res.value.data);

      if (successfulResults.length < tests.length) {
        setError(`Se completaron ${successfulResults.length} de ${tests.length} evaluaciones de búsqueda.`);
      }

      setRetrieval(successfulResults);
    } catch {
      setError("Error crítico ejecutando evaluación de búsqueda.");
    } finally {
      setRunning(false);
      setRunningStep(null);
    }
  };

  const runAnswers = async () => {
    if (!tests.length) return;
    setRunning(true);
    setRunningStep("Evaluando calidad de respuestas con LLM...");
    setError(null);

    try {
      const promises = tests.map((test) =>
        api.post<AnswerResult>(`/chat/evaluation/answer/${test.id}`, null, {
          params: evalParams,
        })
      );

      const settledAnswers = await Promise.allSettled(promises);

      const successfulAnswers = settledAnswers
        .filter((res: any) => res.status === "fulfilled")
        .map((res: any) => res.value.data);

      if (successfulAnswers.length < tests.length) {
        setError(`Se completaron ${successfulAnswers.length} de ${tests.length} evaluaciones de las respuestas.`);
      }

      setAnswers(successfulAnswers);
    } catch {
      setError("Error crítico ejecutando evaluación de respuestas.");
    } finally {
      setRunning(false);
      setRunningStep(null);
    }
  };

  const runAll = async () => {
    if (!tests.length) return;
    setRunning(true);
    setRunningStep("Ejecutando auditoría completa en paralelo...");
    setError(null);

    try {
      const retrievalPromises = tests.map((t) =>
        api.post<RetrievalResult>(`/chat/evaluation/retrieval/${t.id}`, null, {
          params: evalParams,
        })
      );
      const answerPromises = tests.map((t) =>
        api.post<AnswerResult>(`/chat/evaluation/answer/${t.id}`, null, {
          params: evalParams,
        })
      );

      const [retrievalSettled, answerSettled] = await Promise.all([
        Promise.allSettled(retrievalPromises),
        Promise.allSettled(answerPromises),
      ]);

      const successfulRetrieval = retrievalSettled
        .filter((res: any) => res.status === "fulfilled")
        .map((res: any) => res.value.data);

      const successfulAnswers = answerSettled
        .filter((res: any) => res.status === "fulfilled")
        .map((res: any) => res.value.data);

      setRetrieval(successfulRetrieval);
      setAnswers(successfulAnswers);
    } catch {
      setError("Error ejecutando la auditoría completa.");
    } finally {
      setRunning(false);
      setRunningStep(null);
    }
  };

  const runDatasetEval = async () => {
    setRunning(true);
    setRunningStep("Evaluando dataset anotado (Recall/MRR sobre chunks)...");
    setError(null);
    try {
      const response = await api.post("/chat/simulator/evaluate-dataset", {
        model_name: "llama3.2:latest",
        embedding_model: embeddingModel,
        distance_metric: distanceMetric,
        top_k: 5,
        retrieval_k: 10,
        bm25_k: 10,
        rrf_k: 60,
        candidate_k: 15,
        split: "all",
        evaluation_mode: true,
        force: true,
      });
      setDatasetEval(response.data);
      await loadHistory();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "No hay preguntas anotadas en retrieval_dataset o falló la evaluación.",
      );
    } finally {
      setRunning(false);
      setRunningStep(null);
    }
  };

  const averages = useMemo(() => {
    const avg = (arr: number[]) =>
      arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    return {
      mrr: avg(retrieval.map((r) => getRetrievalMetric(r, "mrr"))),
      ndcg: avg(retrieval.map((r) => getRetrievalMetric(r, "ndcg"))),
      accuracy: avg(answers.map((a) => getAnswerMetric(a, "accuracy"))),
      precision: avg(answers.map((a) => getAnswerMetric(a, "precision"))),
      completeness: avg(answers.map((a) => getAnswerMetric(a, "completeness"))),
      relevance: avg(answers.map((a) => getAnswerMetric(a, "relevance"))),
      faithfulness: avg(answers.map((a) => getAnswerMetric(a, "faithfulness"))),
      groundedness: avg(answers.map((a) => getAnswerMetric(a, "groundedness"))),
      citation_accuracy: avg(answers.map((a) => getAnswerMetric(a, "citation_accuracy"))),
      abstention: avg(answers.map((a) => getAnswerMetric(a, "abstention"))),
    };
  }, [retrieval, answers]);

  // Filtros de búsqueda
  const filteredTests = useMemo(() => {
    const term = searchFilter.toLowerCase().trim();
    if (!term) return tests;
    return tests.filter(
      (t) =>
        t.question?.toLowerCase().includes(term) ||
        t.category?.toLowerCase().includes(term) ||
        categoryLabel(t.category).toLowerCase().includes(term) ||
        t.id.toString().includes(term)
    );
  }, [tests, searchFilter]);

  const filteredRetrieval = useMemo(() => {
    const term = searchFilter.toLowerCase().trim();
    if (!term) return retrieval;
    return retrieval.filter(
      (r) =>
        r.question?.toLowerCase().includes(term) ||
        r.category?.toLowerCase().includes(term) ||
        (r.test_id ?? r.id ?? "").toString().includes(term)
    );
  }, [retrieval, searchFilter]);

  const filteredAnswers = useMemo(() => {
    const term = searchFilter.toLowerCase().trim();
    if (!term) return answers;
    return answers.filter(
      (a) =>
        a.question?.toLowerCase().includes(term) ||
        a.category?.toLowerCase().includes(term) ||
        (a.test_id ?? a.id ?? "").toString().includes(term)
    );
  }, [answers, searchFilter]);

  const chartData = useMemo(() => {
    return tests.map((test) => {
      const ret = retrieval.find((r) => (r.test_id ?? r.id) === test.id);
      const ans = answers.find((a) => (a.test_id ?? a.id) === test.id);

      const metrics: number[] = [];

      if (ret) {
        metrics.push(getSafePercentage(getRetrievalMetric(ret, "mrr")));
        metrics.push(getSafePercentage(getRetrievalMetric(ret, "ndcg")));
        metrics.push(getSafePercentage(getRetrievalMetric(ret, "accuracy")));
      }

      if (ans) {
        metrics.push(getSafePercentage(getAnswerMetric(ans, "accuracy")));
        metrics.push(getSafePercentage(getAnswerMetric(ans, "precision")));
        metrics.push(getSafePercentage(getAnswerMetric(ans, "completeness")));
        metrics.push(getSafePercentage(getAnswerMetric(ans, "relevance")));
      }

      const average = metrics.length
        ? metrics.reduce((sum, val) => sum + val, 0) / metrics.length
        : 0;

      return {
        name: `P${test.id}`,
        promedio: Math.round(average),
        question: test.question,
        hasData: metrics.length > 0
      };
    });
  }, [tests, retrieval, answers]);

  if (loadingTests && tab === "metricas" && tests.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="animate-pulse font-semibold text-emerald-600">
          Cargando banco de pruebas...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.25em] text-emerald-600">
            Panel de Calidad RAG
          </p>
          <h1 className="text-3xl font-extrabold text-slate-900">
            Evaluación RAG
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Al subir un documento se extraen preguntas de muestra; la validación
            humana las aprueba o corrige; solo las aceptadas entran en el banco
            de métricas.
          </p>
        </div>

        <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-1">
          {EVAL_TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={`rounded-t-xl px-4 py-2 text-sm font-semibold ${
                tab === item.id
                  ? "bg-white text-emerald-700 shadow-sm ring-1 ring-slate-200"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {tab === "anotar" && <AnnotatePanel />}
        {tab === "banco" && <BankPanel />}
        {tab === "validacion" && <ValidacionHumanaPage embedded />}

        {tab === "metricas" && (
          <>
        <ConfigurableEvaluationLab
          organizationId={selectedOrg?.id ?? ""}
          initialDatasetId={searchParams.get("dataset") ?? undefined}
        />
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-xl font-extrabold text-slate-900">
              Métricas del banco ({tests.length} pruebas)
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Scope: {selectedOrg?.name ?? "sin organización"}
              {selectedKbId
                ? ` · KB ${knowledgeBases.find((k) => k.id === selectedKbId)?.name ?? selectedKbId}`
                : ""}
              {" · "}
              embedding {embeddingModel} · distancia {distanceMetric}
            </p>
            {runningStep && (
              <p className="mt-1 animate-pulse text-xs font-semibold text-emerald-700">
                {runningStep}
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              value={embeddingModel}
              onChange={(e) => setEmbeddingModel(e.target.value)}
              disabled={running}
              title="Modelo de embeddings indexado en el corpus"
            >
              {indexedModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
            <select
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              value={distanceMetric}
              onChange={(e) =>
                setDistanceMetric(
                  e.target.value as "cosine" | "euclidean" | "manhattan",
                )
              }
              disabled={running}
            >
              <option value="cosine">Coseno</option>
              <option value="euclidean">Euclídea (L2)</option>
              <option value="manhattan">Manhattan (L1)</option>
            </select>
            <select
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              value={selectedKbId}
              onChange={(e) => setSelectedKbId(e.target.value)}
              disabled={!selectedOrg || running}
            >
              <option value="">Todas las KBs del tenant</option>
              {knowledgeBases.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => void loadTests()}
              disabled={running}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-50"
            >
              Recargar pruebas
            </button>
            <button
              onClick={() => void runRetrieval()}
              disabled={!tests.length || running}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
            >
              Probar Búsqueda
            </button>
            <button
              onClick={() => void runAnswers()}
              disabled={!tests.length || running}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
            >
              Probar Respuestas
            </button>
            <button
              onClick={() => void runAll()}
              disabled={!tests.length || running}
              className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-50"
            >
              Ejecutar Auditoría Completa
            </button>
            <button
              onClick={() => void saveExperiment()}
              disabled={!tests.length || running}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 disabled:opacity-50"
            >
              Guardar corrida
            </button>
            <button
              onClick={() => void compareDistances()}
              disabled={!tests.length || running}
              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50"
            >
              Comparar 3 distancias
            </button>
            <button
              onClick={() => void compareEmbeddings()}
              disabled={!tests.length || running}
              className="rounded-xl bg-violet-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-800 disabled:opacity-50"
            >
              Comparar embeddings
            </button>
            <button
              onClick={() => void runDatasetEval()}
              disabled={running}
              className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-semibold text-indigo-700 disabled:opacity-50"
            >
              Evaluar anotaciones
            </button>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {tests.length === 0 && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            El banco está vacío. Sube un JSON en la pestaña Banco o anota
            chunks en Anotar. Las tarjetas permanecerán en «Pendiente» hasta
            pulsar «Ejecutar Auditoría Completa».
          </div>
        )}

        {datasetEval && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <MiniStat
              label="Recall@1"
              value={`${Math.round((datasetEval.recall_1 || 0) * 100)}%`}
              percentage={Math.round((datasetEval.recall_1 || 0) * 100)}
            />
            <MiniStat
              label="Recall@K"
              value={`${Math.round((datasetEval.recall_k || 0) * 100)}%`}
              percentage={Math.round((datasetEval.recall_k || 0) * 100)}
            />
            <MiniStat
              label="MRR anotado"
              value={`${Math.round((datasetEval.mrr || 0) * 100)}%`}
              percentage={Math.round((datasetEval.mrr || 0) * 100)}
            />
            <MiniStat
              label="nDCG anotado"
              value={`${Math.round((datasetEval.ndcg || 0) * 100)}%`}
              percentage={Math.round((datasetEval.ndcg || 0) * 100)}
            />
            <MiniStat
              label="Falsos positivos"
              value={String(datasetEval.false_positives)}
              percentage={datasetEval.false_positives ? 40 : 100}
            />
            <MiniStat
              label="Fallos"
              value={String(datasetEval.failures)}
              percentage={datasetEval.failures ? 40 : 100}
            />
          </div>
        )}

        <ExperimentHistory
          runs={experiments}
          bestMrrId={bestMrrId}
          loading={loadingHistory}
        />

        {/* METRICAS PRINCIPALES (TARJETAS KPI) */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <ClientMetricCard
            title="Rapidez de Hallazgo"
            technicalName="MRR"
            description="¿El documento correcto apareció de primero?"
            value={averages.mrr}
            asUnit
            pending={retrieval.length === 0}
          />
          <ClientMetricCard
            title="Calidad de Búsqueda"
            technicalName="nDCG"
            description="¿Qué tan bien ordenados estaban los resultados?"
            value={averages.ndcg}
            asUnit
            pending={retrieval.length === 0}
          />
          <ClientMetricCard
            title="Puntería de Respuesta"
            technicalName="Accuracy"
            description="¿Respondió correctamente según la información oficial?"
            value={averages.accuracy}
            pending={answers.length === 0}
          />
          <ClientMetricCard
            title="Directo / Sin Paja"
            technicalName="Precision"
            description="¿Respondió sin inventar o meter texto innecesario?"
            value={averages.precision}
            pending={answers.length === 0}
          />
          <ClientMetricCard
            title="Exhaustividad"
            technicalName="Completeness"
            description="¿Respondió la duda completa sin omitir datos?"
            value={averages.completeness}
            pending={answers.length === 0}
          />
          <ClientMetricCard
            title="Útil y Enfocado"
            technicalName="Relevance"
            description="¿La respuesta realmente solucionó lo consultado?"
            value={averages.relevance}
            pending={answers.length === 0}
          />
          <ClientMetricCard
            title="Fidelidad"
            technicalName="Faithfulness"
            description="¿La respuesta se ciñe al contexto recuperado (anti-alucinación)?"
            value={averages.faithfulness}
            pending={answers.length === 0}
          />
          <ClientMetricCard
            title="Anclaje"
            technicalName="Groundedness"
            description="¿Cada afirmación está respaldada por el contexto?"
            value={averages.groundedness}
            pending={answers.length === 0}
          />
          <ClientMetricCard
            title="Citas"
            technicalName="Citation"
            description="¿Las referencias citadas existen en las fuentes?"
            value={averages.citation_accuracy}
            asUnit
            pending={answers.length === 0}
          />
          <ClientMetricCard
            title="Abstención"
            technicalName="Abstention"
            description="¿Se abstuvo correctamente cuando no había conocimiento?"
            value={averages.abstention}
            asUnit
            pending={answers.length === 0}
          />
        </div>

        {/* Buscador */}
        <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
          <span className="pl-2 text-slate-400">🔍</span>
          <input
            type="text"
            placeholder="Buscar por pregunta, categoría o ID de prueba..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none"
          />
          {searchFilter && (
            <button
              onClick={() => setSearchFilter("")}
              className="pr-2 text-xs font-semibold text-slate-400 hover:text-slate-600"
            >
              Limpiar
            </button>
          )}
        </div>

        {/* Histograma de Rendimiento */}
        {chartData.length > 0 && chartData.some((d) => d.hasData) && (
          <div className="h-[400px] rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900">Rendimiento Promedio por Pregunta</h2>
              <span className="text-xs font-semibold text-slate-500">Umbral objetivo: 90%</span>
            </div>

            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 20, right: 10, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis
                    dataKey="name"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#64748b" }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#64748b" }}
                    tickFormatter={(value) => `${value}%`}
                  />
                  <Tooltip
                    cursor={{ fill: "#f8fafc" }}
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        const isPassing = data.promedio >= 90;

                        return (
                          <div className="max-w-[280px] rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
                            <p className="font-bold text-slate-900">{data.name}</p>
                            <p className="mb-3 mt-1 line-clamp-3 text-xs text-slate-600">
                              "{data.question}"
                            </p>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-slate-500">Promedio General:</span>
                              <span className={`text-sm font-black ${isPassing ? "text-emerald-600" : "text-rose-600"}`}>
                                {data.promedio}%
                              </span>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar
                    dataKey="promedio"
                    fill="#0f172a"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={40}
                  />
                  <ReferenceLine
                    y={90}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                    strokeWidth={2}
                    label={{
                      position: "insideTopRight",
                      value: "Umbral 90%",
                      fill: "#ef4444",
                      fontSize: 12,
                      fontWeight: "bold",
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* TRES PANELES EN GRID */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          
          {/* Panel 1: Banco de Preguntas */}
          <Panel title={`Banco de Preguntas (${filteredTests.length})`}>
            {filteredTests.length === 0 ? (
              <EmptyState text="No hay preguntas disponibles o ninguna coincide con el filtro." />
            ) : (
              <div className="max-h-[600px] space-y-3 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-200">
                {filteredTests.map((test) => (
                  <div
                    key={test.id}
                    className="rounded-xl border border-slate-100 bg-slate-50 p-4 transition-all hover:border-slate-200"
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="rounded-md bg-purple-100 px-2 py-0.5 text-xs font-bold text-purple-800">
                        {categoryLabel(test.category)}
                      </span>
                      <span className="text-xs font-semibold text-slate-400">
                        Prueba #{test.id}
                      </span>
                    </div>

                    <p className="mb-2 text-sm font-semibold text-slate-800">
                      {test.question}
                    </p>

                    {test.reference_answer && (
                      <div className="mt-2 rounded-lg border border-slate-200/60 bg-white p-2.5 text-xs text-slate-600">
                        <strong className="text-slate-800">Respuesta Oficial: </strong>
                        {test.reference_answer}
                      </div>
                    )}

                    {test.keywords && test.keywords.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {test.keywords.map((kw, idx) => (
                          <span
                            key={idx}
                            className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-700"
                          >
                            #{kw}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Panel>

          {/* Panel 2: Búsqueda */}
          <Panel title={`Efectividad de Búsqueda (${filteredRetrieval.length})`}>
            {retrieval.length === 0 ? (
              <EmptyState text="Aún no se han ejecutado las pruebas de búsqueda de información." />
            ) : filteredRetrieval.length === 0 ? (
              <EmptyState text="Sin coincidencias con el término buscado." />
            ) : (
              <div className="max-h-[600px] space-y-3 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-200">
                {filteredRetrieval.map((item, idx) => {
                  const testId = item.test_id ?? item.id ?? idx + 1;
                  const mrrVal = getUnitPercentage(getRetrievalMetric(item, "mrr"));
                  const ndcgVal = getUnitPercentage(getRetrievalMetric(item, "ndcg"));
                  const covVal = getSafePercentage(getRetrievalMetric(item, "keyword_coverage"));
                  const accVal = getSafePercentage(getRetrievalMetric(item, "accuracy"));
                  
                  return (
                    <div
                      key={testId}
                      className="rounded-xl border border-slate-100 bg-slate-50 p-4 transition-all hover:border-slate-200"
                    >
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800">
                          {categoryLabel(item.category)}
                        </span>
                        <span className="text-xs font-semibold text-slate-400">
                          Prueba #{testId}
                        </span>
                      </div>

                      <p className="mb-3 line-clamp-2 text-xs font-medium text-slate-700">
                        {item.question}
                      </p>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
                        <MiniStat label="Posición" value={`${mrrVal}%`} percentage={mrrVal} />
                        <MiniStat label="Orden" value={`${ndcgVal}%`} percentage={ndcgVal} />
                        <MiniStat label="Cobertura" value={`${covVal}%`} percentage={covVal} />
                        <MiniStat label="Exactitud" value={`${accVal}%`} percentage={accVal} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>

          {/* Panel 3: Respuestas */}
          <Panel title={`Calidad de Respuestas (${filteredAnswers.length})`}>
            {answers.length === 0 ? (
              <EmptyState text="Aún no se han ejecutado las pruebas de generación de respuestas." />
            ) : filteredAnswers.length === 0 ? (
              <EmptyState text="Sin coincidencias con el término buscado." />
            ) : (
              <div className="max-h-[600px] space-y-3 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-200">
                {filteredAnswers.map((item, idx) => {
                  const testId = item.test_id ?? item.id ?? idx + 1;
                  const feedback = getFeedbackText(item);

                  const accVal = getSafePercentage(getAnswerMetric(item, "accuracy"));
                  const precVal = getSafePercentage(getAnswerMetric(item, "precision"));
                  const compVal = getSafePercentage(getAnswerMetric(item, "completeness"));
                  const relVal = getSafePercentage(getAnswerMetric(item, "relevance"));
                  const faithVal = getSafePercentage(getAnswerMetric(item, "faithfulness"));
                  const groundVal = getSafePercentage(getAnswerMetric(item, "groundedness"));
                  const citeVal = getUnitPercentage(getAnswerMetric(item, "citation_accuracy"));
                  const abstVal = getUnitPercentage(getAnswerMetric(item, "abstention"));

                  return (
                    <div
                      key={testId}
                      className="rounded-xl border border-slate-100 bg-slate-50 p-4 transition-all hover:border-slate-200"
                    >
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-800">
                          {categoryLabel(item.category)}
                        </span>
                        <span className="text-xs font-semibold text-slate-400">
                          Prueba #{testId}
                        </span>
                      </div>

                      <p className="mb-2 line-clamp-2 text-xs font-medium text-slate-700">
                        {item.question}
                      </p>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
                        <MiniStat label="Puntería" value={`${accVal}%`} percentage={accVal} />
                        <MiniStat label="Sin Paja" value={`${precVal}%`} percentage={precVal} />
                        <MiniStat label="Completa" value={`${compVal}%`} percentage={compVal} />
                        <MiniStat label="Útil" value={`${relVal}%`} percentage={relVal} />
                        <MiniStat label="Fidelidad" value={`${faithVal}%`} percentage={faithVal} />
                        <MiniStat label="Anclaje" value={`${groundVal}%`} percentage={groundVal} />
                        <MiniStat label="Citas" value={`${citeVal}%`} percentage={citeVal} />
                        <MiniStat label="Abstención" value={`${abstVal}%`} percentage={abstVal} />
                      </div>

                      {item.generated_answer && (
                        <div className="mt-2.5 rounded-lg border border-blue-200/80 bg-blue-50/50 p-2.5 text-xs text-slate-700">
                          <strong className="text-blue-900">Respuesta Generada Bot: </strong>
                          {item.generated_answer}
                        </div>
                      )}

                      {feedback && (
                        <div className="mt-2 rounded-lg border border-slate-200/60 bg-white p-2 text-xs text-slate-600">
                          <strong className="text-slate-800">Evaluación: </strong>
                          {feedback}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>

        </div>
          </>
        )}
      </div>
    </div>
  );
}

function ClientMetricCard({
  title,
  technicalName,
  description,
  value,
  asUnit = false,
  pending = false,
}: {
  title: string;
  technicalName: string;
  description: string;
  value: number;
  asUnit?: boolean;
  pending?: boolean;
}) {
  const percentage = asUnit ? getUnitPercentage(value) : getSafePercentage(value);

  const getStatus = (val: number) => {
    if (pending)
      return {
        bg: "bg-slate-50",
        border: "border-slate-200",
        text: "text-slate-500",
        badge: "Pendiente",
      };
    if (val === 0)
      return {
        bg: "bg-rose-50",
        border: "border-rose-200",
        text: "text-rose-700",
        badge: "0% (Sin Datos)",
      };
    if (val < 60)
      return {
        bg: "bg-amber-50",
        border: "border-amber-200",
        text: "text-amber-700",
        badge: "Mejorable",
      };
    return {
      bg: "bg-emerald-50",
      border: "border-emerald-200",
      text: "text-emerald-700",
      badge: "Excelente",
    };
  };

  const status = getStatus(percentage);

  return (
    <div
      className={`flex flex-col justify-between rounded-2xl border ${status.border} ${status.bg} p-4 shadow-sm transition-all`}
    >
      <div>
        <div className="flex items-start justify-between gap-1">
          <p className="text-xs font-extrabold uppercase tracking-wide text-slate-800">
            {title}
          </p>
          <span className="text-[10px] font-semibold text-slate-400">
            ({technicalName})
          </span>
        </div>

        <p className="mt-1 text-[11px] leading-tight text-slate-600">
          {description}
        </p>
      </div>

      <div className="mt-4">
        <div className="flex items-baseline gap-2">
          <p className={`text-3xl font-black ${status.text}`}>
            {pending ? "—" : `${percentage}%`}
          </p>
        </div>
        <span
          className={`mt-1 inline-block rounded-full border bg-white/80 px-2 py-0.5 text-[10px] font-bold ${status.border} ${status.text}`}
        >
          {status.badge}
        </span>
      </div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-base font-bold text-slate-900">{title}</h2>
      {children}
    </div>
  );
}

function MiniStat({ label, value, percentage }: { label: string; value: string; percentage?: number }) {
  const getColor = (p?: number) => {
    if (p === undefined) return "text-slate-900";
    if (p >= 80) return "text-emerald-700";
    if (p >= 50) return "text-amber-700";
    return "text-rose-700";
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-2 py-1.5">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className={`text-xs font-bold ${getColor(percentage)}`}>{value}</p>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">
      {text}
    </div>
  );
}