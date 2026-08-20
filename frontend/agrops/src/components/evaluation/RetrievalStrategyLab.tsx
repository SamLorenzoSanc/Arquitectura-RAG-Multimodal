import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Beaker,
  CheckCircle2,
  Clock3,
  DatabaseZap,
  FlaskConical,
  Play,
  Sparkles,
} from "lucide-react";

import { useDepartments, useKnowledgeBases } from "@/hooks/useCachedApi";
import DocumentService from "@/services/document.service";
import EvaluationService from "@/services/evaluation.service";
import FrozenRagConfigBar, {
  useSyncedTemperature,
} from "@/components/evaluation/FrozenRagConfigBar";
import { useTranslation } from "@/i18n/I18nProvider";
import type {
  RetrievalExperimentRun,
  RetrievalStrategy,
} from "@/types/evaluation";

type Props = {
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

export default function RetrievalStrategyLab({ organizationId }: Props) {
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
