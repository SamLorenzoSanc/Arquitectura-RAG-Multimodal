import { useMemo, useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Beaker, CheckCircle2, Clock3, DatabaseZap, FlaskConical, Play, Sparkles, BarChart3, Ruler, ChevronRight, Pencil, Plus, Search, X, XCircle } from "lucide-react";
import { useDepartments, useKnowledgeBases } from "@/hooks";
import FrozenRagConfigBar, { useSyncedTemperature } from "@/components/evaluation/FrozenRagConfigBar";
import { useTranslation } from "@/i18n/I18nProvider";
import { queryKeys } from "@/lib/app";
import { DatasetService, DocumentService, EvaluationService } from "@/services";
import type { RetrievalExperimentRun, RetrievalStrategy, DistanceMetricId, RagDataset, RagField, EvaluationCatalog, EvaluationConfig, EvaluationConfigInput, EvaluationMetric, EvaluationRun } from "@/types";

/* --- components/evaluation/RetrievalStrategyLab.tsx --- */


type RetrievalLabProps = {
  organizationId: string;
};

const STRATEGY_IDS: RetrievalStrategy[] = [
  "dense",
  "bm25",
  "hybrid_rrf",
  "hybrid_expansion_rrf",
];

function strategyDefs(t: (key: string) => string): Array<{
  id: RetrievalStrategy;
  name: string;
  description: string;
  cost: string;
}> {
  return [
    {
      id: "dense",
      name: t("evalExtended.strategyDenseName"),
      description: t("evalExtended.strategyDenseDesc"),
      cost: t("evalExtended.strategyCostOneSearch"),
    },
    {
      id: "bm25",
      name: t("evalExtended.strategyBm25Name"),
      description: t("evalExtended.strategyBm25Desc"),
      cost: t("evalExtended.strategyCostOneSearch"),
    },
    {
      id: "hybrid_rrf",
      name: t("evalExtended.strategyHybridRrfName"),
      description: t("evalExtended.strategyHybridRrfDesc"),
      cost: t("evalExtended.strategyCostTwoSearch"),
    },
    {
      id: "hybrid_rrf_rerank",
      name: t("evalExtended.strategyHybridRrfRerankName"),
      description: t("evalExtended.strategyHybridRrfRerankDesc"),
      cost: t("evalExtended.strategyCostAblation"),
    },
    {
      id: "hybrid_expansion_rrf",
      name: t("evalExtended.strategyExpansionName"),
      description: t("evalExtended.strategyExpansionDesc"),
      cost: t("evalExtended.strategyCostTwoFourSearch"),
    },
    {
      id: "hybrid_expansion_rrf_rerank",
      name: t("evalExtended.strategyFullPipelineName"),
      description: t("evalExtended.strategyFullPipelineDesc"),
      cost: t("evalExtended.strategyCostAblation"),
    },
  ];
}

const DEFAULT_STRATEGIES: RetrievalStrategy[] = STRATEGY_IDS;

function pct(value?: number | null) {
  return `${((value ?? 0) * 100).toFixed(1)}%`;
}

function seconds(value?: number | null) {
  return `${((value ?? 0) / 1000).toFixed(2)} s`;
}

function errorMessage(error: unknown, fallback: string) {
  const candidate = error as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return (
    candidate.response?.data?.detail ||
    candidate.message ||
    fallback
  );
}

function strategyId(run: RetrievalExperimentRun): string {
  return String(
    run.retrieval_strategy || run.parameters?.retrieval_strategy || "",
  );
}

function interpretRuns(
  t: (key: string, params?: Record<string, string | number>) => string,
  runs: RetrievalExperimentRun[],
): string[] {
  if (runs.length < 2) return [];
  const by = (id: string) =>
    runs.find((run) => strategyId(run) === id);
  const dense = by("dense");
  const bm25 = by("bm25");
  const hybrid = by("hybrid_rrf") || by("hybrid_expansion_rrf");
  const rerank =
    by("hybrid_rrf_rerank") || by("hybrid_expansion_rrf_rerank");
  const notes: string[] = [];
  const n = runs[0]?.evaluated_questions ?? runs[0]?.dataset_size;
  if (n && n <= 5) {
    notes.push(t("evalExtended.strategyInterpretSmallBank", { n }));
  }
  if (
    dense &&
    bm25 &&
    (bm25.recall_k ?? 0) < 0.001 &&
    (dense.recall_k ?? 0) > 0
  ) {
    notes.push(t("evalExtended.strategyInterpretBm25Zero"));
  }
  if (
    dense &&
    hybrid &&
    Math.abs((dense.mrr ?? 0) - (hybrid.mrr ?? 0)) < 0.001
  ) {
    notes.push(t("evalExtended.strategyInterpretHybridEquals"));
  }
  if (
    rerank &&
    dense &&
    (rerank.recall_1 ?? 0) + 0.001 < (dense.recall_1 ?? 0)
  ) {
    notes.push(t("evalExtended.strategyInterpretRerankRecall"));
  }
  if (runs.some((run) => (run.duration_ms ?? 0) >= 10_000)) {
    notes.push(t("evalExtended.strategyInterpretLatency"));
  }
  return notes;
}

export function RetrievalStrategyLab({ organizationId }: RetrievalLabProps) {
  const { t } = useTranslation();
  const strategies = useMemo(() => strategyDefs(t), [t]);
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<RetrievalStrategy[]>(
    DEFAULT_STRATEGIES,
  );
  const [embeddingModel, setEmbeddingModel] = useState("nomic-embed-text");
  const [distanceMetric, setDistanceMetric] = useState("cosine");
  const [departmentId, setDepartmentId] = useState("");
  const [knowledgeBaseId, setKnowledgeBaseId] = useState("");
  const [topK, setTopK] = useState(3);
  const [latestRuns, setLatestRuns] = useState<RetrievalExperimentRun[]>([]);
  const [bestMrrId, setBestMrrId] = useState<number | null>(null);
  const [reindexMessage, setReindexMessage] = useState("");
  const { temperature, setTemperature } = useSyncedTemperature();

  const departments = useDepartments(organizationId);
  const knowledgeBases = useKnowledgeBases(
    organizationId,
    departmentId || undefined,
  );
  const models = useQuery({
    queryKey: ["evaluation", "embedding-models", organizationId],
    queryFn: () => EvaluationService.embeddingModels(organizationId),
    enabled: Boolean(organizationId),
  });
  const documentModels = useQuery({
    queryKey: ["documents", "embedding-models", knowledgeBaseId],
    queryFn: () => DocumentService.embeddingModels(knowledgeBaseId),
    enabled: Boolean(knowledgeBaseId),
  });
  const history = useQuery({
    queryKey: ["evaluation", "retrieval-strategy-history", organizationId],
    queryFn: () => EvaluationService.retrievalExperimentHistory(organizationId),
    enabled: Boolean(organizationId),
  });

  const availableModels = useMemo(
    () => [
      ...new Set([
        ...(documentModels.data?.catalog ?? []).map((item) => item.id),
        ...(models.data?.indexed ?? []),
        embeddingModel,
      ]),
    ],
    [documentModels.data, embeddingModel, models.data],
  );
  const effectiveEmbeddingModel = availableModels.includes(embeddingModel)
    ? embeddingModel
    : models.data?.default || availableModels[0];

  const mutation = useMutation({
    mutationFn: () =>
      EvaluationService.compareRetrievalStrategies(organizationId, {
        strategies: selected,
        embedding_model: effectiveEmbeddingModel,
        distance_metric: distanceMetric,
        top_k: topK,
        organization_id: organizationId,
        department_id: departmentId || null,
        knowledge_base_id: knowledgeBaseId || null,
        temperature,
      }),
    onSuccess: (result) => {
      setLatestRuns(result.runs);
      setBestMrrId(result.best_mrr_id);
      void queryClient.invalidateQueries({
        queryKey: ["evaluation", "retrieval-strategy-history", organizationId],
      });
    },
  });
  const reindexMutation = useMutation({
    mutationFn: () =>
      DocumentService.reindexEmbeddings({
        knowledgeBaseId,
        embeddingModels: [effectiveEmbeddingModel],
      }),
    onSuccess: (result) => {
      const stats = result.models?.[effectiveEmbeddingModel];
      if (stats?.error && !stats.indexed && !stats.skipped) {
        setReindexMessage(stats.error);
        return;
      }
      setReindexMessage(
        t("evalExtended.reindexResult", {
          chunks: result.chunks,
          indexed: stats?.indexed ?? 0,
          skipped: stats?.skipped ?? 0,
          failedPart: stats?.failed
            ? t("evalExtended.reindexFailedPart", { failed: stats.failed })
            : "",
        }),
      );
      void queryClient.invalidateQueries({
        queryKey: ["evaluation", "embedding-models", organizationId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["documents", "embedding-models", knowledgeBaseId],
      });
    },
    onError: (error) => setReindexMessage(errorMessage(error, t("evalExtended.operationFailed"))),
  });

  const displayedRuns = useMemo(
    () => (latestRuns.length ? latestRuns : history.data ?? []),
    [history.data, latestRuns],
  );
  const winner = useMemo(() => {
    if (bestMrrId !== null) return bestMrrId;
    return displayedRuns.length
      ? displayedRuns.reduce((best, run) => (run.mrr > best.mrr ? run : best)).id
      : null;
  }, [bestMrrId, displayedRuns]);
  const reading = useMemo(() => interpretRuns(t, latestRuns), [t, latestRuns]);

  const toggle = (strategy: RetrievalStrategy) => {
    setSelected((current) =>
      current.includes(strategy)
        ? current.filter((item) => item !== strategy)
        : [...current, strategy],
    );
  };

  return (
    <section className="space-y-5">
      <header className="rounded-2xl border border-indigo-100 bg-white p-6 shadow-sm">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-indigo-700">
          <FlaskConical size={16} />
          {t("evalExtended.strategyEyebrow")}
        </p>
        <h2 className="mt-2 text-2xl font-black text-slate-900">
          {t("evalExtended.strategyTitle")}
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600">
          {t("evalExtended.strategyIntroFull")}
        </p>
      </header>

      <FrozenRagConfigBar
        temperature={temperature}
        onTemperatureChange={setTemperature}
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {strategies.map((strategy) => {
          const active = selected.includes(strategy.id);
          return (
            <button
              key={strategy.id}
              type="button"
              onClick={() => toggle(strategy.id)}
              className={`rounded-2xl border p-4 text-left transition ${
                active
                  ? "border-indigo-400 bg-indigo-50 ring-1 ring-indigo-200"
                  : "border-slate-200 bg-white hover:border-indigo-200"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-extrabold text-slate-900">
                    {strategy.name}
                  </h3>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">
                    {strategy.description}
                  </p>
                </div>
                {active && (
                  <CheckCircle2
                    size={19}
                    className="shrink-0 text-indigo-600"
                  />
                )}
              </div>
              <span className="mt-3 inline-flex rounded-full bg-white px-2 py-1 text-[10px] font-bold text-slate-500">
                {strategy.cost}
              </span>
            </button>
          );
        })}
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 opacity-75">
          <div className="flex items-center gap-2">
            <Sparkles size={17} className="text-amber-600" />
            <h3 className="font-extrabold text-slate-700">{t("evalExtended.strategyHydeName")}</h3>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-slate-500">
            {t("evalExtended.strategyHydeDesc")}
          </p>
          <span className="mt-3 inline-flex rounded-full bg-amber-100 px-2 py-1 text-[10px] font-bold text-amber-700">
            {t("evalExtended.comingSoon")}
          </span>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-7">
          <label className="text-xs font-bold text-slate-600">
            {t("evalExtended.strategyLabelEmbedding")}
            <select
              value={effectiveEmbeddingModel}
              onChange={(event) => setEmbeddingModel(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal"
            >
              {availableModels.map((model) => (
                <option key={model}>{model}</option>
              ))}
            </select>
          </label>
          <label className="text-xs font-bold text-slate-600">
            {t("evalExtended.strategyLabelDistance")}
            <select
              value={distanceMetric}
              onChange={(event) => setDistanceMetric(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal"
            >
              <option value="cosine">{t("evalExtended.metricCosine")}</option>
              <option value="euclidean">{t("evalExtended.metricEuclidean")}</option>
              <option value="manhattan">{t("evalExtended.metricManhattan")}</option>
            </select>
          </label>
          <label className="text-xs font-bold text-slate-600">
            {t("evalExtended.strategyLabelDepartment")}
            <select
              value={departmentId}
              onChange={(event) => {
                setDepartmentId(event.target.value);
                setKnowledgeBaseId("");
              }}
              className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal"
            >
              <option value="">{t("evalExtended.strategyScopeAccessible")}</option>
              {(departments.data ?? []).map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-bold text-slate-600">
            {t("evalExtended.strategyLabelKb")}
            <select
              value={knowledgeBaseId}
              onChange={(event) => setKnowledgeBaseId(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal"
            >
              <option value="">{t("evalExtended.strategyAllScopedBases")}</option>
              {(knowledgeBases.data ?? []).map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-bold text-slate-600">
            Top-k
            <input
              type="number"
              min={1}
              max={50}
              value={topK}
              onChange={(event) => setTopK(Number(event.target.value))}
              className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 font-normal"
            />
          </label>
          <button
            type="button"
            disabled={!knowledgeBaseId || reindexMutation.isPending}
            onClick={() => {
              setReindexMessage("");
              reindexMutation.mutate();
            }}
            title={
              knowledgeBaseId
                ? t("evalExtended.strategyReindexTitle")
                : t("evalExtended.selectKb")
            }
            className="mt-auto flex h-10 items-center justify-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 text-xs font-bold text-indigo-700 disabled:opacity-40"
          >
            <DatabaseZap size={16} />
            {reindexMutation.isPending
              ? t("evalExtended.reindexing")
              : t("evalExtended.reindexKb")}
          </button>
          <button
            type="button"
            disabled={!selected.length || mutation.isPending}
            onClick={() => mutation.mutate()}
            className="mt-auto flex h-10 items-center justify-center gap-2 rounded-lg bg-indigo-700 px-4 text-sm font-bold text-white disabled:opacity-40"
          >
            <Play size={16} />
            {mutation.isPending
              ? t("evalExtended.executing")
              : t("evalExtended.compare", { n: selected.length })}
          </button>
        </div>
        {reindexMessage && (
          <p
            className={`mt-3 rounded-lg border px-4 py-3 text-xs font-semibold ${
              reindexMessage.includes("No se pudo") ||
              reindexMessage.includes("fallos")
                ? "border-amber-200 bg-amber-50 text-amber-800"
                : "border-emerald-200 bg-emerald-50 text-emerald-700"
            }`}
          >
            {reindexMessage}
          </p>
        )}
        {mutation.isError && (
          <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs font-semibold text-rose-700">
            {errorMessage(mutation.error, t("evalExtended.operationFailed"))}
          </p>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h3 className="flex items-center gap-2 font-extrabold text-slate-900">
              <Beaker size={17} className="text-indigo-600" />
              {t("evalExtended.resultsTitle")}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              {t("evalExtended.strategyResultsHint")}
            </p>
          </div>
          <span className="text-xs font-bold text-slate-400">
            {t("evalExtended.strategyRunsCount", { count: displayedRuns.length })}
          </span>
        </div>
        {history.isLoading && !latestRuns.length ? (
          <p className="py-8 text-center text-sm text-slate-500">
            {t("evalExtended.loadingHistory")}
          </p>
        ) : !displayedRuns.length ? (
          <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
            {t("evalExtended.strategySelectAndRun")}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-[10px] uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">{t("evalExtended.colStrategy")}</th>
                  <th className="px-3 py-2">{t("evalExtended.colRecall1")}</th>
                  <th className="px-3 py-2">{t("evalExtended.colRecallK")}</th>
                  <th className="px-3 py-2">{t("evalExtended.colMrr")}</th>
                  <th className="px-3 py-2">nDCG</th>
                  <th className="px-3 py-2">{t("evalExtended.colPrecisionAtK")}</th>
                  <th className="px-3 py-2">{t("evalExtended.colTotalLatency")}</th>
                  <th className="px-3 py-2">{t("evalExtended.colFailures")}</th>
                </tr>
              </thead>
              <tbody>
                {displayedRuns.map((run) => {
                  const strategy =
                    strategies.find(
                      (item) =>
                        item.id ===
                        (run.retrieval_strategy ||
                          run.parameters?.retrieval_strategy),
                    )?.name ||
                    run.retrieval_strategy ||
                    String(run.parameters?.retrieval_strategy ?? "—");
                  const best = winner === run.id;
                  return (
                    <tr
                      key={`${run.id}-${run.created_at}`}
                      className={`border-b border-slate-100 last:border-0 ${
                        best ? "bg-emerald-50" : ""
                      }`}
                    >
                      <td className="px-3 py-3 font-bold text-slate-800">
                        {strategy}
                        {best && (
                          <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-[9px] uppercase text-emerald-700">
                            {t("evalExtended.bestMrr")}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-3">{pct(run.recall_1)}</td>
                      <td className="px-3 py-3">{pct(run.recall_k)}</td>
                      <td className="px-3 py-3 font-bold">{pct(run.mrr)}</td>
                      <td className="px-3 py-3">{pct(run.ndcg)}</td>
                      <td className="px-3 py-3">
                        {pct(run.precision_at_k)}
                      </td>
                      <td className="px-3 py-3">
                        <span className="inline-flex items-center gap-1">
                          <Clock3 size={13} className="text-slate-400" />
                          {seconds(run.duration_ms)}
                        </span>
                      </td>
                      <td className="px-3 py-3">{run.failures}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {reading.length > 0 && (
          <ul className="mt-4 space-y-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-900">
            {reading.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

/* --- components/evaluation/DistanceMetricsLab.tsx --- */


type DistanceLabProps = {
  organizationId: string;
};

const DISTANCE_IDS: DistanceMetricId[] = ["cosine", "euclidean", "manhattan"];

function pctDistance(value?: number | null) {
  return `${((value ?? 0) * 100).toFixed(1)}%`;
}

function metricLabel(
  t: (key: string) => string,
  metric: string,
): string {
  if (metric === "euclidean" || metric === "l2") {
    return t("evalExtended.metricEuclidean");
  }
  if (metric === "manhattan" || metric === "l1") {
    return t("evalExtended.metricManhattan");
  }
  if (metric === "inner_product" || metric === "ip") {
    return t("evalExtended.metricInnerProduct");
  }
  return t("evalExtended.metricCosine");
}

function interpretDistances(
  t: (key: string, params?: Record<string, string | number>) => string,
  runs: RetrievalExperimentRun[],
): string[] {
  if (runs.length < 2) return [];
  const sorted = [...runs].sort((a, b) => (b.mrr ?? 0) - (a.mrr ?? 0));
  const best = sorted[0];
  const worst = sorted[sorted.length - 1];
  const delta = (best.mrr ?? 0) - (worst.mrr ?? 0);
  const notes: string[] = [
    t("evalExtended.distanceInterpretBest", {
      best: metricLabel(t, best.distance_metric),
      mrr: pct(best.mrr),
      ndcg: pct(best.ndcg),
    }),
  ];
  if (delta > 0.01) {
    notes.push(
      t("evalExtended.distanceInterpretDelta", {
        best: metricLabel(t, best.distance_metric),
        worst: metricLabel(t, worst.distance_metric),
        delta: pct(delta),
      }),
    );
  } else {
    notes.push(t("evalExtended.distanceInterpretSimilar"));
  }
  const cosine = runs.find((r) => r.distance_metric === "cosine");
  if (cosine && best.distance_metric === "cosine") {
    notes.push(t("evalExtended.distanceInterpretCosineWins"));
  } else if (cosine && best.distance_metric !== "cosine") {
    notes.push(
      t("evalExtended.distanceInterpretOtherWins", {
        best: metricLabel(t, best.distance_metric),
      }),
    );
  }
  notes.push(t("evalExtended.distanceInterpretHnsw"));
  return notes;
}

function MetricBar({
  label,
  value,
  max,
  highlight,
}: {
  label: string;
  value: number;
  max: number;
  highlight?: boolean;
}) {
  const width = max > 0 ? Math.max(4, (value / max) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className={highlight ? "font-bold text-[color:var(--agro-primary)]" : "font-semibold text-slate-600"}>
          {label}
        </span>
        <span className="font-mono text-slate-700">{pct(value)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${
            highlight ? "bg-[color:var(--agro-primary)]" : "bg-slate-400"
          }`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

export function DistanceMetricsLab({ organizationId }: DistanceLabProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { temperature } = useSyncedTemperature();
  const { data: knowledgeBases = [] } = useKnowledgeBases(organizationId || undefined);

  const [selected, setSelected] = useState<DistanceMetricId[]>([...DISTANCE_IDS]);
  const [topK, setTopK] = useState(3);
  const [kbId, setKbId] = useState<string>("");
  const [lastRuns, setLastRuns] = useState<RetrievalExperimentRun[]>([]);
  const [bestId, setBestId] = useState<number | null>(null);
  const [note, setNote] = useState("");

  const modelsQuery = useQuery({
    queryKey: queryKeys.evaluationEmbeddingModels(organizationId),
    queryFn: () => EvaluationService.embeddingModels(organizationId),
    enabled: Boolean(organizationId),
    staleTime: 30_000,
  });

  const historyQuery = useQuery({
    queryKey: ["distance-experiments", organizationId],
    queryFn: () => EvaluationService.distanceExperimentHistory(organizationId),
    enabled: Boolean(organizationId),
  });

  const indexedModels = modelsQuery.data?.indexed ?? [];

  const compareMutation = useMutation({
    mutationFn: () =>
      EvaluationService.compareDistanceMetrics(organizationId, {
        embedding_models: indexedModels.length
          ? indexedModels
          : [modelsQuery.data?.default || "nomic-embed-text"],
        distance_metrics: selected,
        top_k: topK,
        knowledge_base_id: kbId || null,
      }),
    onSuccess: (data) => {
      setLastRuns(data.runs ?? []);
      setBestId(data.best_mrr_id);
      setNote(data.note || "");
      void queryClient.invalidateQueries({
        queryKey: ["distance-experiments", organizationId],
      });
    },
  });

  const displayRuns = lastRuns.length > 0 ? lastRuns : (historyQuery.data ?? []).slice(0, 6);
  const insights = useMemo(
    () => interpretDistances(t, lastRuns.length > 0 ? lastRuns : []),
    [lastRuns, t],
  );
  const maxMrr = Math.max(0.01, ...displayRuns.map((r) => r.mrr ?? 0));
  const maxNdcg = Math.max(0.01, ...displayRuns.map((r) => r.ndcg ?? 0));

  const defs = useMemo(
    () => [
      {
        id: "cosine" as const,
        name: t("evalExtended.metricCosine"),
        description: t("evalExtended.cosineDesc"),
      },
      {
        id: "euclidean" as const,
        name: t("evalExtended.metricEuclidean"),
        description: t("evalExtended.euclideanDesc"),
      },
      {
        id: "manhattan" as const,
        name: t("evalExtended.metricManhattan"),
        description: t("evalExtended.manhattanDesc"),
      },
    ],
    [t],
  );

  const toggle = (id: DistanceMetricId) => {
    setSelected((prev) => {
      if (prev.includes(id)) {
        return prev.length === 1 ? prev : prev.filter((x) => x !== id);
      }
      return [...prev, id];
    });
  };

  if (!organizationId) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
        {t("common.selectOrganization")}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--agro-primary)]">
          {t("evalExtended.distanceEyebrow")}
        </p>
        <h2 className="mt-1 flex items-center gap-2 text-lg font-bold text-slate-900">
          <Ruler size={18} className="text-[color:var(--agro-primary)]" />
          {t("evalExtended.distanceTitle")}
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          {t("evalExtended.distanceIntro")}
        </p>
        <div className="mt-4">
          <FrozenRagConfigBar />
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        {defs.map((item) => {
          const on = selected.includes(item.id);
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => toggle(item.id)}
              className={`rounded-xl border p-4 text-left transition ${
                on
                  ? "border-[color:var(--agro-primary)] bg-[color:var(--agro-pill)]"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <p className="text-sm font-bold text-slate-900">{item.name}</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-600">
                {item.description}
              </p>
            </button>
          );
        })}
      </section>

      <section className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <label className="text-xs font-semibold text-slate-600">
          Top-k
          <input
            type="number"
            min={1}
            max={20}
            value={topK}
            onChange={(e) => setTopK(Math.max(1, Number(e.target.value) || 3))}
            className="mt-1 block h-9 w-20 rounded-lg border border-slate-200 px-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-600">
          {t("evalExtended.strategyLabelKb")}
          <select
            value={kbId}
            onChange={(e) => setKbId(e.target.value)}
            className="mt-1 block h-9 min-w-[200px] rounded-lg border border-slate-200 px-2 text-sm"
          >
            <option value="">{t("evalExtended.strategyAllScopedBases")}</option>
            {knowledgeBases.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={
            compareMutation.isPending ||
            selected.length < 2 ||
            modelsQuery.isLoading
          }
          onClick={() => compareMutation.mutate()}
          className="inline-flex h-9 items-center gap-2 rounded-lg bg-[color:var(--agro-primary)] px-4 text-sm font-semibold text-white disabled:opacity-50"
        >
          <Play size={14} />
          {compareMutation.isPending
            ? t("evalExtended.comparingDistances")
            : t("evalExtended.compareDistances")}
        </button>
        <p className="text-[11px] text-slate-400">
          {t("evalExtended.distanceTempHint", { temp: temperature })}
        </p>
      </section>

      {compareMutation.isError && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {errorMessage(compareMutation.error, t("evalExtended.distanceCompareFailed"))}
        </p>
      )}

      {insights.length > 0 && (
        <section className="rounded-xl border border-amber-200 bg-amber-50/70 p-4">
          <h3 className="text-sm font-bold text-amber-900">
            {t("evalExtended.distanceInsights")}
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-950">
            {insights.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          {note ? (
            <p className="mt-2 text-[11px] text-amber-800/80">{note}</p>
          ) : null}
        </section>
      )}

      {displayRuns.length > 0 && (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900">
              <BarChart3 size={16} />
              {t("evalExtended.distanceChartMrr")}
            </h3>
            <div className="space-y-3">
              {displayRuns.map((run) => (
                <MetricBar
                  key={`mrr-${run.id}-${run.distance_metric}`}
                  label={metricLabel(t, run.distance_metric)}
                  value={run.mrr ?? 0}
                  max={maxMrr}
                  highlight={bestId != null && run.id === bestId}
                />
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900">
              <BarChart3 size={16} />
              {t("evalExtended.distanceChartNdcg")}
            </h3>
            <div className="space-y-3">
              {displayRuns.map((run) => (
                <MetricBar
                  key={`ndcg-${run.id}-${run.distance_metric}`}
                  label={metricLabel(t, run.distance_metric)}
                  value={run.ndcg ?? 0}
                  max={maxNdcg}
                  highlight={bestId != null && run.id === bestId}
                />
              ))}
            </div>
          </div>
        </section>
      )}

      {displayRuns.length > 0 && (
        <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">{t("evalExtended.distanceMetric")}</th>
                <th className="px-3 py-2">MRR</th>
                <th className="px-3 py-2">nDCG</th>
                <th className="px-3 py-2">Recall@1</th>
                <th className="px-3 py-2">Recall@K</th>
                <th className="px-3 py-2">Precision@K</th>
                <th className="px-3 py-2">{t("evalExtended.coverage")}</th>
                <th className="px-3 py-2">{t("evalExtended.colTotalLatency")}</th>
              </tr>
            </thead>
            <tbody>
              {displayRuns.map((run) => {
                const win = bestId != null && run.id === bestId;
                return (
                  <tr
                    key={`${run.id}-${run.distance_metric}`}
                    className={win ? "bg-[color:var(--agro-pill)]/60" : "border-t border-slate-100"}
                  >
                    <td className="px-3 py-2 font-semibold text-slate-800">
                      {metricLabel(t, run.distance_metric)}
                      {win ? (
                        <span className="ml-2 rounded-full bg-[color:var(--agro-primary)] px-2 py-0.5 text-[10px] font-bold text-white">
                          {t("evalExtended.bestMrr")}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 font-mono">{pct(run.mrr)}</td>
                    <td className="px-3 py-2 font-mono">{pct(run.ndcg)}</td>
                    <td className="px-3 py-2 font-mono">{pct(run.recall_1)}</td>
                    <td className="px-3 py-2 font-mono">{pct(run.recall_k)}</td>
                    <td className="px-3 py-2 font-mono">{pct(run.precision_at_k)}</td>
                    <td className="px-3 py-2 font-mono">
                      {pct(run.keyword_coverage ?? (
                        typeof run.parameters?.keyword_coverage === "number"
                          ? run.parameters.keyword_coverage
                          : undefined
                      ))}
                    </td>
                    <td className="px-3 py-2 font-mono">{seconds(run.duration_ms)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

/* --- components/evaluation/ConfigurableEvaluationLab.tsx --- */


type ConfigurableLabProps = {
  organizationId: string;
  initialDatasetId?: string;
};

function message(error: unknown, fallback: string) {
  const candidate = error as {
    response?: { data?: { detail?: string | { message?: string } } };
    message?: string;
  };
  const detail = candidate.response?.data?.detail;
  return (
    (typeof detail === "string" ? detail : detail?.message) ||
    candidate.message ||
    fallback
  );
}

export function ConfigurableEvaluationLab({
  organizationId,
  initialDatasetId,
}: ConfigurableLabProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [datasetId, setDatasetId] = useState(initialDatasetId ?? "");
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [configDraft, setConfigDraft] = useState<{
    metrics: EvaluationMetric[];
    existing?: EvaluationConfig;
  } | null>(null);
  const [activeConfigId, setActiveConfigId] = useState("");
  const [latestRun, setLatestRun] = useState<EvaluationRun | null>(null);

  const datasets = useQuery({
    queryKey: queryKeys.datasets(organizationId),
    queryFn: () => DatasetService.list(organizationId),
    enabled: Boolean(organizationId),
  });
  const catalog = useQuery({
    queryKey: queryKeys.evaluationCatalog(organizationId, datasetId),
    queryFn: () => EvaluationService.catalog(organizationId, datasetId),
    enabled: Boolean(organizationId && datasetId),
  });
  const detail = useQuery({
    queryKey: queryKeys.evaluationDataset(organizationId, datasetId),
    queryFn: () => EvaluationService.dataset(organizationId, datasetId),
    enabled: Boolean(organizationId && datasetId),
  });
  const configs = useQuery({
    queryKey: queryKeys.evaluationConfigs(organizationId, datasetId),
    queryFn: () => EvaluationService.configs(organizationId, datasetId),
    enabled: Boolean(organizationId && datasetId),
  });

  useEffect(() => {
    if (!datasetId && datasets.data?.length) {
      setDatasetId(initialDatasetId || datasets.data[0].id);
    }
  }, [datasetId, datasets.data, initialDatasetId]);

  useEffect(() => {
    const items = configs.data ?? [];
    if (items.length && !items.some((item) => item.id === activeConfigId)) {
      setActiveConfigId(items[0].id);
    }
    if (!items.length) setActiveConfigId("");
  }, [activeConfigId, configs.data]);

  const activeConfig = configs.data?.find((item) => item.id === activeConfigId);
  const runMutation = useMutation({
    mutationFn: (configId: string) =>
      EvaluationService.run(organizationId, configId),
    onSuccess: setLatestRun,
  });

  const columns = catalog.data?.fields ?? [];
  const rows = detail.data?.rows ?? [];

  return (
    <section className="space-y-5 rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-700">
            <FlaskConical size={15} />
            {t("evalExtended.configLabEyebrow")}
          </p>
          <h2 className="mt-1 text-xl font-extrabold text-slate-900">
            {t("evalExtended.configLabTitle")}
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={datasetId}
            onChange={(event) => {
              setDatasetId(event.target.value);
              setLatestRun(null);
            }}
            className="h-10 min-w-64 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold"
          >
            <option value="">{t("evalExtended.selectDataset")}</option>
            {(datasets.data ?? []).map((dataset: RagDataset) => (
              <option key={dataset.id} value={dataset.id}>
                {t("evalExtended.configDatasetRowsOption", {
                  name: dataset.name,
                  count: dataset.row_count ?? 0,
                })}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={!datasetId || !catalog.data}
            onClick={() => setCatalogOpen(true)}
            className="flex h-10 items-center gap-2 rounded-lg bg-blue-700 px-4 text-sm font-bold text-white disabled:opacity-40"
          >
            <Plus size={16} />
            {t("evalExtended.addEvaluation")}
          </button>
        </div>
      </div>

      <FrozenRagConfigBar />

      {catalog.isError && (
        <ErrorBox text={message(catalog.error, t("evalExtended.operationFailed"))} />
      )}

      {datasetId && (
        <>
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs font-bold text-slate-700">
                {t("evalExtended.configDatasetRows", { count: rows.length })}
              </p>
              <p className="text-[11px] text-slate-400">
                {t("evalExtended.configFieldsDetected", {
                  fields: columns.join(", ") || t("evalExtended.configNoFields"),
                })}
              </p>
            </div>
            <div className="max-h-64 overflow-auto">
              <table className="min-w-full text-left text-xs">
                <thead className="sticky top-0 bg-white text-slate-500">
                  <tr>
                    {columns.slice(0, 7).map((column) => (
                      <th key={column} className="border-b px-3 py-2 font-bold">
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 20).map((row, index) => (
                    <tr key={String(row.id ?? index)} className="border-b last:border-0">
                      {columns.slice(0, 7).map((column) => (
                        <td
                          key={column}
                          className="max-w-64 truncate px-3 py-2 text-slate-600"
                          title={String(row[column] ?? "")}
                        >
                          {typeof row[column] === "object"
                            ? JSON.stringify(row[column])
                            : String(row[column] ?? "—")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 border-b border-slate-200">
            {(configs.data ?? []).map((config) => (
              <button
                key={config.id}
                type="button"
                onClick={() => {
                  setActiveConfigId(config.id);
                  setLatestRun(null);
                }}
                className={`border-b-2 px-3 py-2 text-xs font-bold ${
                  activeConfigId === config.id
                    ? "border-blue-600 text-blue-700"
                    : "border-transparent text-slate-500"
                }`}
              >
                {config.name}
              </button>
            ))}
          </div>

          {activeConfig ? (
            <div className="rounded-xl border border-slate-200 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-slate-900">{activeConfig.name}</h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Ollama · {activeConfig.model_name} ·{" "}
                    {t("evalExtended.configMetricsCount", {
                      count: activeConfig.metrics.length,
                    })}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {activeConfig.metrics.map((metric) => (
                      <span
                        key={metric}
                        className="rounded-full bg-blue-50 px-2 py-1 text-[10px] font-bold text-blue-700"
                      >
                        {catalog.data?.metrics.find((item) => item.id === metric)
                          ?.name ?? metric}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      setConfigDraft({
                        existing: activeConfig,
                        metrics:
                          catalog.data?.metrics.filter((metric) =>
                            activeConfig.metrics.includes(metric.id),
                          ) ?? [],
                      })
                    }
                    className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600"
                  >
                    <Pencil size={14} />
                    {t("evalExtended.configEdit")}
                  </button>
                  <button
                    type="button"
                    disabled={runMutation.isPending}
                    onClick={() => runMutation.mutate(activeConfig.id)}
                    className="flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
                  >
                    <Play size={14} />
                    {runMutation.isPending
                      ? t("evalExtended.configExecuting")
                      : t("evalExtended.configRun")}
                  </button>
                </div>
              </div>
              {runMutation.isError && (
                <div className="mt-3">
                  <ErrorBox text={message(runMutation.error, t("evalExtended.operationFailed"))} />
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
              {t("evalExtended.configAddHint")}
            </div>
          )}

          {latestRun && (
            <EvaluationRunResults run={latestRun} catalog={catalog.data} t={t} />
          )}
        </>
      )}

      {catalogOpen && catalog.data && (
        <EvaluationCatalogModal
          catalog={catalog.data}
          onClose={() => setCatalogOpen(false)}
          onNext={(metrics) => {
            setCatalogOpen(false);
            setConfigDraft({ metrics });
          }}
        />
      )}
      {configDraft && catalog.data && (
        <EvaluationConfigPanel
          datasetId={datasetId}
          catalog={catalog.data}
          metrics={configDraft.metrics}
          existing={configDraft.existing}
          organizationId={organizationId}
          onClose={() => setConfigDraft(null)}
          onSaved={(config) => {
            setConfigDraft(null);
            setActiveConfigId(config.id);
            void queryClient.invalidateQueries({
              queryKey: queryKeys.evaluationConfigs(organizationId, datasetId),
            });
          }}
        />
      )}
    </section>
  );
}

function EvaluationCatalogModal({
  catalog,
  onClose,
  onNext,
}: {
  catalog: EvaluationCatalog;
  onClose: () => void;
  onNext: (metrics: EvaluationMetric[]) => void;
}) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<"all" | EvaluationMetric["category"]>(
    "all",
  );
  const [selected, setSelected] = useState<string[]>([]);
  const filtered = catalog.metrics.filter((metric) => {
    const matchesCategory = category === "all" || metric.category === category;
    const query = search.toLowerCase();
    return (
      matchesCategory &&
      `${metric.name} ${metric.description}`.toLowerCase().includes(query)
    );
  });
  return (
    <ModalShell onClose={onClose} width="max-w-4xl">
      <div className="border-b border-slate-200 px-6 py-5">
        <h2 className="text-lg font-extrabold text-slate-900">
          {t("evalExtended.configAddEvaluations")}
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          {t("evalExtended.configAddEvaluationsHint")}
        </p>
      </div>
      <div className="space-y-4 p-6">
        <label className="relative block">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("evalExtended.searchEval")}
            className="h-11 w-full rounded-lg border border-slate-200 pl-10 pr-3 text-sm outline-none focus:border-blue-500"
          />
        </label>
        <div className="grid grid-cols-5 overflow-hidden rounded-lg border border-slate-200">
          {(["all", "prompt", "context", "response", "text"] as const).map(
            (item) => (
              <button
                key={item}
                type="button"
                onClick={() => setCategory(item)}
                className={`px-3 py-2 text-xs font-bold capitalize ${
                  category === item
                    ? "bg-blue-600 text-white"
                    : "border-l border-slate-200 text-slate-500 first:border-0"
                }`}
              >
                {item === "all" ? t("evalExtended.configAllCategories") : item}
              </button>
            ),
          )}
        </div>
        <div className="grid max-h-[52vh] gap-3 overflow-auto pr-1 md:grid-cols-2">
          {filtered.map((metric) => {
            const checked = selected.includes(metric.id);
            return (
              <button
                key={metric.id}
                type="button"
                disabled={!metric.compatible}
                onClick={() =>
                  setSelected((current) =>
                    checked
                      ? current.filter((id) => id !== metric.id)
                      : [...current, metric.id],
                  )
                }
                className={`rounded-xl border p-4 text-left transition ${
                  checked
                    ? "border-blue-500 bg-blue-50"
                    : "border-slate-200 bg-white hover:bg-slate-50"
                } disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-55`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-[10px] font-bold uppercase text-slate-400">
                      {metric.category} · {metric.engine}
                    </p>
                    <h3 className="mt-1 text-sm font-bold text-slate-900">
                      {metric.name}
                    </h3>
                  </div>
                  {checked && <CheckCircle2 size={18} className="text-blue-600" />}
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-500">
                  {metric.description}
                </p>
                <span className="mt-3 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
                  {metric.engine}
                </span>
                {!metric.compatible && (
                  <p className="mt-2 text-[10px] font-bold text-amber-700">
                    {t("evalExtended.configMissingFields", {
                      fields: metric.missing_fields.join(", "),
                    })}
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </div>
      <div className="flex justify-end gap-2 border-t border-slate-200 px-6 py-4">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-bold text-slate-600"
        >
          {t("common.cancel")}
        </button>
        <button
          type="button"
          disabled={!selected.length}
          onClick={() =>
            onNext(catalog.metrics.filter((metric) => selected.includes(metric.id)))
          }
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-40"
        >
          {t("evalExtended.configure", { n: selected.length || "" })}
          <ChevronRight size={15} />
        </button>
      </div>
    </ModalShell>
  );
}

function EvaluationConfigPanel({
  datasetId,
  catalog,
  metrics,
  existing,
  organizationId,
  onClose,
  onSaved,
}: {
  datasetId: string;
  catalog: EvaluationCatalog;
  metrics: EvaluationMetric[];
  existing?: EvaluationConfig;
  organizationId: string;
  onClose: () => void;
  onSaved: (config: EvaluationConfig) => void;
}) {
  const { t } = useTranslation();
  const requirements = useMemo(
    () => [...new Set(metrics.flatMap((metric) => metric.required_fields))],
    [metrics],
  );
  const defaultField = (requirement: string): RagField => {
    const alternatives: Record<string, RagField[]> = {
      response: ["response", "expected_response", "alternate_response"],
      expected_response: ["expected_response", "response", "alternate_response"],
      context: ["context", "expected_context"],
      expected_context: ["expected_context", "context"],
    };
    return (
      (alternatives[requirement] ?? [requirement as RagField]).find((field) =>
        catalog.fields.includes(field),
      ) ??
      catalog.fields[0] ??
      "prompt"
    );
  };
  const [name, setName] = useState(
    existing?.name ?? metrics[0]?.name ?? t("evalExtended.defaultEvalName"),
  );
  const [model, setModel] = useState(
    existing?.model_name ?? catalog.models[0] ?? "llama3.2:latest",
  );
  const [mapping, setMapping] = useState<Record<string, RagField>>(() =>
    Object.fromEntries(
      requirements.map((field) => [
        field,
        existing?.mapping[field] ?? defaultField(field),
      ]),
    ),
  );
  const [thresholds, setThresholds] = useState<EvaluationConfig["thresholds"]>(
    () =>
      Object.fromEntries(
        metrics.map((metric) => [
          metric.id,
          existing?.thresholds[metric.id] ?? metric.default_threshold,
        ]),
      ),
  );
  const [split, setSplit] = useState(existing?.filters.split ?? "all");
  const [limit, setLimit] = useState(existing?.filters.limit ?? 100);
  const [categories, setCategories] = useState(
    existing?.filters.categories.join(", ") ?? "",
  );
  const mutation = useMutation({
    mutationFn: (input: EvaluationConfigInput) =>
      existing
        ? EvaluationService.updateConfig(
            organizationId,
            existing.id,
            input,
          )
        : EvaluationService.createConfig(organizationId, input),
    onSuccess: onSaved,
  });

  const save = () => {
    mutation.mutate({
      dataset_id: datasetId,
      name: name.trim(),
      provider: "ollama",
      model_name: model,
      metrics: metrics.map((metric) => metric.id),
      mapping,
      thresholds,
      filters: {
        split,
        categories: categories
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        statuses: ["ready", "approved"],
        limit,
      },
    });
  };

  return (
    <ModalShell onClose={onClose} width="max-w-3xl">
      <div className="border-b border-slate-200 px-6 py-5">
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="w-full text-lg font-extrabold text-slate-900 outline-none"
        />
        <p className="mt-1 text-xs text-slate-500">
          {t("evalExtended.configConfigureHint")}
        </p>
      </div>
      <div className="max-h-[68vh] space-y-6 overflow-auto p-6">
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">
            {t("evalExtended.configParameters")}
          </h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="text-xs font-bold text-slate-600">
              {t("evalExtended.configProvider")}
              <select
                disabled
                className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3"
              >
                <option>{t("evalExtended.configProviderOllama")}</option>
              </select>
            </label>
            <label className="text-xs font-bold text-slate-600">
              {t("evalExtended.configModel")}
              <select
                value={model}
                onChange={(event) => setModel(event.target.value)}
                className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3"
              >
                {catalog.models.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-extrabold text-slate-900">
            {t("evalExtended.configSchema")}
          </h3>
          <div className="mt-3 space-y-2">
            {requirements.map((requirement) => (
              <div
                key={requirement}
                className="grid grid-cols-[1fr_auto_1fr] items-center gap-3"
              >
                <span className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-bold text-slate-600">
                  {requirement}
                </span>
                <ChevronRight size={15} className="text-slate-400" />
                <select
                  value={mapping[requirement]}
                  onChange={(event) =>
                    setMapping((current) => ({
                      ...current,
                      [requirement]: event.target.value as RagField,
                    }))
                  }
                  className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs"
                >
                  {catalog.fields.map((field) => (
                    <option key={field}>{field}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-extrabold text-slate-900">
            {t("evalExtended.configThresholds")}
          </h3>
          <div className="mt-3 space-y-2">
            {metrics.map((metric) => (
              <div
                key={metric.id}
                className="grid grid-cols-[1fr_90px_110px] items-center gap-2"
              >
                <span className="text-xs font-bold text-slate-600">
                  {metric.name}
                </span>
                <select
                  value={thresholds[metric.id]?.operator}
                  onChange={(event) =>
                    setThresholds((current) => ({
                      ...current,
                      [metric.id]: {
                        ...current[metric.id],
                        operator: event.target.value as "gte" | "lte",
                      },
                    }))
                  }
                  className="h-9 rounded-lg border border-slate-200 px-2 text-xs"
                >
                  <option value="gte">≥</option>
                  <option value="lte">≤</option>
                </select>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={thresholds[metric.id]?.value}
                  onChange={(event) =>
                    setThresholds((current) => ({
                      ...current,
                      [metric.id]: {
                        ...current[metric.id],
                        value: Number(event.target.value),
                      },
                    }))
                  }
                  className="h-9 rounded-lg border border-slate-200 px-3 text-xs"
                />
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-extrabold text-slate-900">
            {t("evalExtended.configFilters")}
          </h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <label className="text-xs font-bold text-slate-600">
              {t("evalExtended.configSplit")}
              <select
                value={split}
                onChange={(event) =>
                  setSplit(event.target.value as "dev" | "holdout" | "all")
                }
                className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-2"
              >
                <option value="all">{t("evalExtended.configSplitAll")}</option>
                <option value="dev">Dev</option>
                <option value="holdout">Holdout</option>
              </select>
            </label>
            <label className="text-xs font-bold text-slate-600">
              {t("evalExtended.configLimit")}
              <input
                type="number"
                min={1}
                max={500}
                value={limit}
                onChange={(event) => setLimit(Number(event.target.value))}
                className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3"
              />
            </label>
            <label className="text-xs font-bold text-slate-600">
              {t("evalExtended.configCategories")}
              <input
                value={categories}
                onChange={(event) => setCategories(event.target.value)}
                placeholder="temporal, direct_fact"
                className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3 font-normal"
              />
            </label>
          </div>
        </div>
        {mutation.isError && (
          <ErrorBox text={message(mutation.error, t("evalExtended.operationFailed"))} />
        )}
      </div>
      <div className="flex justify-end gap-2 border-t border-slate-200 px-6 py-4">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-slate-200 px-5 py-2 text-xs font-bold text-slate-600"
        >
          {t("evalExtended.back")}
        </button>
        <button
          type="button"
          disabled={!name.trim() || mutation.isPending}
          onClick={save}
          className="rounded-lg bg-blue-600 px-6 py-2 text-xs font-bold text-white disabled:opacity-40"
        >
          {mutation.isPending ? t("evalExtended.configSaving") : t("common.save")}
        </button>
      </div>
    </ModalShell>
  );
}

function EvaluationRunResults({
  run,
  catalog,
  t,
}: {
  run: EvaluationRun;
  catalog?: EvaluationCatalog;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-bold text-slate-900">{t("evalExtended.configRunResult")}</h3>
          <p className="text-xs text-slate-500">
            {t("evalExtended.configRunRows", {
              count: run.row_count,
              mode: run.cached
                ? t("evalExtended.runReused")
                : t("evalExtended.runNew"),
            })}
          </p>
        </div>
        <div className="flex gap-2">
          <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">
            <CheckCircle2 size={13} /> {run.passed_count}
          </span>
          <span className="flex items-center gap-1 rounded-full bg-rose-100 px-3 py-1 text-xs font-bold text-rose-700">
            <XCircle size={13} /> {run.failed_count}
          </span>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Object.entries(run.aggregates ?? {}).map(([metric, value]) => (
          <div key={metric} className="rounded-lg border border-slate-200 bg-white p-3">
            <p className="truncate text-[10px] font-bold uppercase text-slate-400">
              {catalog?.metrics.find((item) => item.id === metric)?.name ?? metric}
            </p>
            <p className="mt-1 text-xl font-black text-slate-900">
              {(value * 100).toFixed(1)}%
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModalShell({
  children,
  onClose,
  width,
}: {
  children: React.ReactNode;
  onClose: () => void;
  width: string;
}) {
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/45 p-4">
      <div
        className={`relative max-h-[92vh] w-full overflow-hidden rounded-2xl bg-white shadow-2xl ${width}`}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"
        >
          <X size={18} />
        </button>
        {children}
      </div>
    </div>
  );
}

function ErrorBox({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs font-semibold text-rose-700">
      {text}
    </div>
  );
}

