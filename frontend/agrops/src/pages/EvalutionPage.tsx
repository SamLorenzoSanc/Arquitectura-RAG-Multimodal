"use client";

import { useEffect, useMemo, useState } from "react";
import api from "@/api";
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

// ---------------------------------------------------------
// TIPOS DE DATOS
// ---------------------------------------------------------
type TestItem = {
  id: number;
  question: string;
  keywords: string[];
  reference_answer: string;
  category: string;
};

type RetrievalResult = {
  test_id?: number;
  id?: number;
  question: string;
  category: string;
  mrr?: number;
  ndcg?: number;
  keyword_coverage?: number;
  retrieval?: {
    mrr: number;
    ndcg: number;
    keywords_found: number;
    total_keywords: number;
    keyword_coverage: number;
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
  feedback?: string;
  evaluation?: {
    feedback: string;
    accuracy: number;
    precision?: number;
    completeness: number;
    relevance: number;
  };
};

// ---------------------------------------------------------
// HELPERS DEFENSIVOS DE EXTRACCIÓN
// ---------------------------------------------------------
function getRetrievalMetric(item: RetrievalResult | undefined | null, metric: string): number {
  if (!item) return 0;
  
  const target = item.retrieval || (item as unknown as Record<string, unknown>);
  if (target[metric] !== undefined && target[metric] !== null) {
    const val = Number(target[metric]);
    if (!isNaN(val)) return val;
  }
  return 0;
}

function getAnswerMetric(item: AnswerResult | undefined | null, metric: string): number {
  if (!item) return 0;

  const rawItem = item as unknown as Record<string, unknown>;
  const target = (rawItem.evaluation || rawItem.data || rawItem) as Record<string, unknown>;

  const metricAliases: Record<string, string[]> = {
    accuracy: ["accuracy", "punteria", "accuracy_score", "score"],
    precision: ["precision", "sin_paja", "precision_score"],
    completeness: ["completeness", "exhaustividad", "completeness_score"],
    relevance: ["relevance", "utilidad", "relevance_score"],
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

function getSafePercentage(value: number): number {
  if (!value || isNaN(value)) return 0;
  const scaled = value > 1 ? value : value * 100;
  return Math.round(Math.min(Math.max(scaled, 0), 100));
}

function formatAsPercent(value: number | undefined | null): string {
  if (value === undefined || value === null) return "N/A";
  return `${getSafePercentage(value)}%`;
}

export default function AuditPage() {
  const [tests, setTests] = useState<TestItem[]>([]);
  const [retrieval, setRetrieval] = useState<RetrievalResult[]>([]);
  const [answers, setAnswers] = useState<AnswerResult[]>([]);
  const [loadingTests, setLoadingTests] = useState(false);
  const [running, setRunning] = useState(false);
  const [runningStep, setRunningStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");

  useEffect(() => {
    void loadTests();
  }, []);

  const loadTests = async () => {
    setLoadingTests(true);
    setError(null);
    try {
      const { data } = await api.get<{ tests: TestItem[] }>("/chat/evaluation/tests");
      setTests(data.tests ?? []);
    } catch {
      setError("No se pudieron cargar los tests desde el backend.");
    } finally {
      setLoadingTests(false);
    }
  };

  const runRetrieval = async () => {
    if (!tests.length) return;
    setRunning(true);
    setRunningStep("Evaluando motor de búsqueda...");
    setError(null);

    try {
      const promises = tests.map((test) =>
        api.post<RetrievalResult>(`/chat/evaluation/retrieval/${test.id}`)
      );
      
      const settledResults = await Promise.allSettled(promises);
      
      const successfulResults = settledResults
        .filter((res): res is PromiseFulfilledResult<{ data: RetrievalResult }> => res.status === "fulfilled")
        .map((res) => res.value.data);

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
        api.post<AnswerResult>(`/chat/evaluation/answer/${test.id}`)
      );

      const settledResults = await Promise.allSettled(promises);

      const successfulResults = settledResults
        .filter((res): res is PromiseFulfilledResult<{ data: AnswerResult }> => res.status === "fulfilled")
        .map((res) => res.value.data);

      if (successfulResults.length < tests.length) {
        setError(`Se completaron ${successfulResults.length} de ${tests.length} evaluaciones de respuestas.`);
      }

      setAnswers(successfulResults);
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
      const retrievalPromises = tests.map((t) => api.post<RetrievalResult>(`/chat/evaluation/retrieval/${t.id}`));
      const answerPromises = tests.map((t) => api.post<AnswerResult>(`/chat/evaluation/answer/${t.id}`));

      const [retrievalSettled, answerSettled] = await Promise.all([
        Promise.allSettled(retrievalPromises),
        Promise.allSettled(answerPromises),
      ]);

      const successfulRetrieval = retrievalSettled
        .filter((res): res is PromiseFulfilledResult<{ data: RetrievalResult }> => res.status === "fulfilled")
        .map((res) => res.value.data);

      const successfulAnswers = answerSettled
        .filter((res): res is PromiseFulfilledResult<{ data: AnswerResult }> => res.status === "fulfilled")
        .map((res) => res.value.data);

      setRetrieval(successfulRetrieval);
      setAnswers(successfulAnswers);
    } catch {
      setError("Error ejecutando la auditoría completa.");
    } finally {
      setRunning(false);
      setRunningStep(null);
    }
  };

  // Promedios dinámicos
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

  // Datos para el gráfico por pregunta
  const chartData = useMemo(() => {
    return tests.map((test) => {
      const ret = retrieval.find((r) => (r.test_id ?? r.id) === test.id);
      const ans = answers.find((a) => (a.test_id ?? a.id) === test.id);

      const metrics: number[] = [];

      if (ret) {
        metrics.push(getSafePercentage(getRetrievalMetric(ret, "mrr")));
        metrics.push(getSafePercentage(getRetrievalMetric(ret, "ndcg")));
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

  if (loadingTests) {
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
        {/* Cabecera */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.25em] text-emerald-600">
              Panel de Calidad RAG
            </p>
            <h1 className="text-3xl font-extrabold text-slate-900">
              Evaluación del Asistente ({tests.length} pruebas)
            </h1>
            {runningStep && (
              <p className="mt-1 animate-pulse text-xs font-semibold text-emerald-700">
                ⏳ {runningStep}
              </p>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
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
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* METRICAS PRINCIPALES (TARJETAS KPI) */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <ClientMetricCard
            title="Rapidez de Hallazgo"
            technicalName="MRR"
            description="¿El documento correcto apareció de primero?"
            value={averages.mrr}
          />
          <ClientMetricCard
            title="Calidad de Búsqueda"
            technicalName="nDCG"
            description="¿Qué tan bien ordenados estaban los resultados?"
            value={averages.ndcg}
          />
          <ClientMetricCard
            title="Puntería de Respuesta"
            technicalName="Accuracy"
            description="¿Respondió correctamente según la información oficial?"
            value={averages.accuracy}
          />
          <ClientMetricCard
            title="Directo / Sin Paja"
            technicalName="Precision"
            description="¿Respondió sin inventar o meter texto innecesario?"
            value={averages.precision}
          />
          <ClientMetricCard
            title="Exhaustividad"
            technicalName="Completeness"
            description="¿Respondió la duda completa sin omitir datos?"
            value={averages.completeness}
          />
          <ClientMetricCard
            title="Útil y Enfocado"
            technicalName="Relevance"
            description="¿La respuesta realmente solucionó lo consultado?"
            value={averages.relevance}
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
                        {test.category}
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
                  const mrrVal = getSafePercentage(getRetrievalMetric(item, "mrr"));
                  const ndcgVal = getSafePercentage(getRetrievalMetric(item, "ndcg"));
                  const covVal = getSafePercentage(getRetrievalMetric(item, "keyword_coverage"));

                  return (
                    <div
                      key={testId}
                      className="rounded-xl border border-slate-100 bg-slate-50 p-4 transition-all hover:border-slate-200"
                    >
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800">
                          {item.category}
                        </span>
                        <span className="text-xs font-semibold text-slate-400">
                          Prueba #{testId}
                        </span>
                      </div>

                      <p className="mb-3 line-clamp-2 text-xs font-medium text-slate-700">
                        {item.question}
                      </p>

                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <MiniStat label="Posición" value={`${mrrVal}%`} percentage={mrrVal} />
                        <MiniStat label="Orden" value={`${ndcgVal}%`} percentage={ndcgVal} />
                        <MiniStat label="Cobertura" value={`${covVal}%`} percentage={covVal} />
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

                  return (
                    <div
                      key={testId}
                      className="rounded-xl border border-slate-100 bg-slate-50 p-4 transition-all hover:border-slate-200"
                    >
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-800">
                          {item.category}
                        </span>
                        <span className="text-xs font-semibold text-slate-400">
                          Prueba #{testId}
                        </span>
                      </div>

                      <p className="mb-2 line-clamp-2 text-xs font-medium text-slate-700">
                        {item.question}
                      </p>

                      <div className="grid grid-cols-4 gap-2 text-sm">
                        <MiniStat label="Puntería" value={`${accVal}%`} percentage={accVal} />
                        <MiniStat label="Sin Paja" value={`${precVal}%`} percentage={precVal} />
                        <MiniStat label="Completa" value={`${compVal}%`} percentage={compVal} />
                        <MiniStat label="Útil" value={`${relVal}%`} percentage={relVal} />
                      </div>

                      {item.generated_answer && (
                        <div className="mt-2.5 rounded-lg border border-blue-200/80 bg-blue-50/50 p-2.5 text-xs text-slate-700">
                          <strong className="text-blue-900">Respuesta Generada Bot: </strong>
                          {item.generated_answer}
                        </div>
                      )}

                      {feedback && (
                        <p className="mt-2 rounded-lg border border-slate-200/60 bg-white p-2 text-xs text-slate-600">
                          <strong className="text-slate-800">Evaluación: </strong>
                          {feedback}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}

function ClientMetricCard({
  title,
  technicalName,
  description,
  value,
}: {
  title: string;
  technicalName: string;
  description: string;
  value: number;
}) {
  const percentage = getSafePercentage(value);

  const getStatus = (val: number) => {
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
          <p className={`text-3xl font-black ${status.text}`}>{percentage}%</p>
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