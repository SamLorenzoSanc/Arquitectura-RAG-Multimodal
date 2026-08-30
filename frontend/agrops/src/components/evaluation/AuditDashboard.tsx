import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import api from "@/api";
import AnnotatePanel from "@/components/evaluation/AnnotatePanel";
import { useTranslation } from "@/i18n/I18nProvider";
import { categoryLabel } from "@/components/evaluation/labels";
import FrozenRagConfigBar, {
  useSyncedTemperature,
} from "@/components/evaluation/FrozenRagConfigBar";
import { useOrganization } from "@/context";
import { useEvaluationTests, useKnowledgeBases } from "@/hooks";

type AuditTab = "retrieval" | "answer" | "validate";

type TestItem = {
  id: number;
  question: string;
  keywords: string[];
  reference_answer: string;
  category: string;
  source_file?: string;
  page?: string;
};

type ScoreBag = Record<string, number>;

type MetricKind = "mrr" | "ndcg" | "coverage" | "score" | "unit";

type KpiSpec = {
  key: string;
  label: string;
  kind: MetricKind;
};

function retrievalKpis(t: (key: string) => string): KpiSpec[] {
  return [
    { key: "mrr", label: t("evalExtended.kpiMrr"), kind: "mrr" },
    { key: "ndcg", label: t("evalExtended.kpiNdcg"), kind: "ndcg" },
    { key: "keyword_coverage", label: t("evalExtended.kpiKeywordCoverage"), kind: "coverage" },
    { key: "accuracy", label: t("evalExtended.kpiPrecisionK"), kind: "coverage" },
    { key: "completeness", label: t("evalExtended.kpiCompleteness"), kind: "score" },
    { key: "relevance", label: t("evalExtended.kpiRelevance"), kind: "score" },
  ];
}

function answerKpis(t: (key: string) => string): KpiSpec[] {
  return [
    { key: "accuracy", label: t("evalExtended.kpiAccuracy"), kind: "score" },
    { key: "completeness", label: t("evalExtended.kpiCompleteness"), kind: "score" },
    { key: "relevance", label: t("evalExtended.kpiRelevance"), kind: "score" },
  ];
}

function ragasKpis(t: (key: string) => string): KpiSpec[] {
  return [
    { key: "faithfulness", label: t("evalExtended.kpiRagasFaithfulness"), kind: "unit" },
    { key: "answer_relevancy", label: t("evalExtended.kpiRagasRelevancy"), kind: "unit" },
    { key: "context_precision", label: t("evalExtended.kpiRagasPrecision"), kind: "unit" },
    { key: "context_recall", label: t("evalExtended.kpiRagasRecall"), kind: "unit" },
  ];
}

const COMPARE_METRICS = ["accuracy", "completeness", "relevance"] as const;
const RAGAS_METRICS = [
  "faithfulness",
  "answer_relevancy",
  "context_precision",
  "context_recall",
] as const;

const TABS = [
  { id: "retrieval" as const, labelKey: "evalExtended.tabRetrieval" },
  { id: "answer" as const, labelKey: "evalExtended.tabAnswer" },
  { id: "validate" as const, labelKey: "evalExtended.tabValidate" },
];

async function mapPool<T>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<void>,
) {
  let next = 0;
  const workers = Array.from(
    { length: Math.min(limit, items.length) },
    async () => {
      while (next < items.length) {
        const index = next;
        next += 1;
        await fn(items[index], index);
      }
    },
  );
  await Promise.all(workers);
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function metricValue(
  payload: Record<string, unknown> | undefined,
  key: string,
  prefer: "retrieval" | "evaluation" | "vanilla" | "ragas" | "vanilla_ragas",
): number | null {
  if (!payload) return null;
  const retrieval = payload.retrieval as Record<string, unknown> | undefined;
  const evaluation = payload.evaluation as Record<string, unknown> | undefined;
  const vanilla = payload.vanilla_evaluation as Record<string, unknown> | undefined;
  const ragas = payload.ragas as Record<string, unknown> | undefined;
  const vanillaRagas = payload.vanilla_ragas as Record<string, unknown> | undefined;
  if (prefer === "vanilla") {
    return asNumber(vanilla?.[key]) ?? null;
  }
  if (prefer === "ragas") {
    return asNumber(ragas?.[key]) ?? null;
  }
  if (prefer === "vanilla_ragas") {
    return asNumber(vanillaRagas?.[key]) ?? null;
  }
  if (prefer === "evaluation") {
    return (
      asNumber(evaluation?.[key]) ??
      asNumber(retrieval?.[key]) ??
      asNumber(payload[key])
    );
  }
  return (
    asNumber(retrieval?.[key]) ??
    asNumber(evaluation?.[key]) ??
    asNumber(payload[key])
  );
}

function toneFor(value: number, kind: MetricKind): "green" | "amber" | "red" {
  if (kind === "coverage") {
    if (value >= 90) return "green";
    if (value >= 75) return "amber";
    return "red";
  }
  if (kind === "score") {
    if (value >= 4.5) return "green";
    if (value >= 4) return "amber";
    return "red";
  }
  if (kind === "unit") {
    if (value >= 0.8) return "green";
    if (value >= 0.6) return "amber";
    return "red";
  }
  if (value >= 0.9) return "green";
  if (value >= 0.75) return "amber";
  return "red";
}

function formatMetric(value: number, kind: MetricKind): string {
  if (kind === "coverage") return `${value.toFixed(1)}%`;
  if (kind === "score") return value.toFixed(2);
  if (kind === "unit") return value.toFixed(3);
  return value.toFixed(4);
}

function KpiCard({
  label,
  value,
  kind,
}: {
  label: string;
  value: number | null;
  kind: MetricKind;
}) {
  const tone = value == null ? "empty" : toneFor(value, kind);
  const tones = {
    green: "border-emerald-400 bg-emerald-50 text-emerald-800",
    amber: "border-amber-400 bg-amber-50 text-amber-800",
    red: "border-rose-400 bg-rose-50 text-rose-800",
    empty: "border-dashed border-slate-200 bg-slate-50 text-slate-400",
  };
  return (
    <div className={`rounded-xl border px-4 py-4 shadow-sm ${tones[tone]}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
        {label}
      </div>
      <div className="mt-1 text-3xl font-extrabold">
        {value == null ? "—" : formatMetric(value, kind)}
        {kind === "score" && value != null ? (
          <span className="ml-1 text-base font-semibold opacity-50">/ 5.0</span>
        ) : null}
        {kind === "unit" && value != null ? (
          <span className="ml-1 text-base font-semibold opacity-50">/ 1</span>
        ) : null}
      </div>
    </div>
  );
}

function CompareKpiCard({
  label,
  vanilla,
  rag,
  kind,
  vanillaLabel,
  ragLabel,
}: {
  label: string;
  vanilla: number | null;
  rag: number | null;
  kind: MetricKind;
  vanillaLabel: string;
  ragLabel: string;
}) {
  const delta =
    vanilla != null && rag != null ? rag - vanilla : null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-slate-50 px-2 py-2">
          <p className="text-[10px] font-semibold text-slate-500">{vanillaLabel}</p>
          <p className="text-xl font-extrabold text-slate-700">
            {vanilla == null ? "—" : formatMetric(vanilla, kind)}
          </p>
        </div>
        <div className="rounded-lg bg-emerald-50 px-2 py-2">
          <p className="text-[10px] font-semibold text-emerald-700">{ragLabel}</p>
          <p className="text-xl font-extrabold text-emerald-800">
            {rag == null ? "—" : formatMetric(rag, kind)}
          </p>
        </div>
      </div>
      {delta != null && (
        <p
          className={`mt-2 text-center text-[11px] font-semibold ${
            delta >= 0 ? "text-emerald-700" : "text-rose-600"
          }`}
        >
          Δ {delta >= 0 ? "+" : ""}
          {formatMetric(delta, kind)}
        </p>
      )}
    </div>
  );
}

export default function AuditDashboard() {
  const { t } = useTranslation();
  const retrievalKpiList = useMemo(() => retrievalKpis(t), [t]);
  const answerKpiList = useMemo(() => answerKpis(t), [t]);
  const ragasKpiList = useMemo(() => ragasKpis(t), [t]);
  const { selectedOrg } = useOrganization();
  const { data: testsData } = useEvaluationTests();
  const { data: kbList } = useKnowledgeBases(selectedOrg?.id);
  const tests = (testsData ?? []) as TestItem[];
  const knowledgeBases = kbList ?? [];

  const [tab, setTab] = useState<AuditTab>("retrieval");
  const [selectedKbId, setSelectedKbId] = useState("");
  const [running, setRunning] = useState<"retrieval" | "answer" | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const [doneCount, setDoneCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [retrieval, setRetrieval] = useState<Record<number, Record<string, unknown>>>({});
  const [answers, setAnswers] = useState<Record<number, Record<string, unknown>>>({});
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { temperature, setTemperature } = useSyncedTemperature();

  const evalParams = useMemo(() => {
    const params: Record<string, string> = {
      distance_metric: "cosine",
      temperature: String(temperature),
    };
    if (selectedOrg?.id) params.organization_id = selectedOrg.id;
    if (selectedKbId) params.knowledge_base_id = selectedKbId;
    params.top_k = "3";
    return params;
  }, [selectedOrg?.id, selectedKbId, temperature]);

  const prefer = tab === "answer" ? "evaluation" : "retrieval";
  const source = tab === "answer" ? answers : retrieval;

  const averages = (
    bag: Record<number, Record<string, unknown>>,
    keys: string[],
    sourcePrefer: "retrieval" | "evaluation" | "vanilla" | "ragas" | "vanilla_ragas",
  ) => {
    const totals: ScoreBag = {};
    const counts: ScoreBag = {};
    for (const test of tests) {
      const payload = bag[test.id];
      for (const key of keys) {
        const value = metricValue(payload, key, sourcePrefer);
        if (value == null) continue;
        totals[key] = (totals[key] || 0) + value;
        counts[key] = (counts[key] || 0) + 1;
      }
    }
    const result: Record<string, number | null> = {};
    for (const key of keys) {
      result[key] = counts[key] ? totals[key] / counts[key] : null;
    }
    return {
      result,
      count: tests.filter((test) => Boolean(bag[test.id])).length,
    };
  };

  const retrievalAvg = averages(
    retrieval,
    retrievalKpiList.map((item) => item.key),
    "retrieval",
  );
  const answerAvg = averages(
    answers,
    answerKpiList.map((item) => item.key),
    "evaluation",
  );
  const vanillaAvg = averages(
    answers,
    answerKpiList.map((item) => item.key),
    "vanilla",
  );
  const ragasAvg = averages(
    answers,
    ragasKpiList.map((item) => item.key),
    "ragas",
  );
  const vanillaRagasAvg = averages(
    answers,
    ragasKpiList.map((item) => item.key),
    "vanilla_ragas",
  );

  const categoryChart = (
    bag: Record<number, Record<string, unknown>>,
    metric: string,
    sourcePrefer: "retrieval" | "evaluation",
  ) => {
    const grouped = new Map<string, number[]>();
    for (const test of tests) {
      const value = metricValue(bag[test.id], metric, sourcePrefer);
      if (value == null) continue;
      const key = categoryLabel(t,test.category);
      grouped.set(key, [...(grouped.get(key) || []), value]);
    }
    return Array.from(grouped.entries()).map(([category, scores]) => ({
      category,
      valor: scores.reduce((sum, item) => sum + item, 0) / scores.length,
    }));
  };

  const comparisonChart = answerKpiList.map((kpi) => ({
    metric: kpi.label.split(" (")[0],
    sinRag: vanillaAvg.result[kpi.key],
    conRag: answerAvg.result[kpi.key],
  }));

  const ragasChart = ragasKpiList.map((kpi) => ({
    metric: kpi.label.split(" (")[0],
    sinRag: vanillaRagasAvg.result[kpi.key],
    conRag: ragasAvg.result[kpi.key],
  }));

  const hallucinationRate = (() => {
    let ragN = 0;
    let ragH = 0;
    let vanN = 0;
    let vanH = 0;
    for (const test of tests) {
      const payload = answers[test.id];
      if (!payload) continue;
      if (typeof payload.is_hallucination === "boolean") {
        ragN += 1;
        if (payload.is_hallucination) ragH += 1;
      }
      if (typeof payload.vanilla_is_hallucination === "boolean") {
        vanN += 1;
        if (payload.vanilla_is_hallucination) vanH += 1;
      }
    }
    return {
      withRag: ragN ? ragH / ragN : null,
      noRag: vanN ? vanH / vanN : null,
    };
  })();

  const ragasSource = Object.values(answers).find(
    (row) => typeof row.ragas_source === "string",
  )?.ragas_source as string | undefined;

  const runAudit = async (mode: "retrieval" | "answer") => {
    if (!tests.length || running) return;
    setRunning(mode);
    setError(null);
    setDoneCount(0);
    setProgress(t("evalExtended.analyzing", { current: 0, total: tests.length }));
    let failed = 0;
    try {
      await mapPool(tests, 1, async (test) => {
        try {
          if (mode === "answer") {
            const { data } = await api.post<Record<string, unknown>>(
              `/chat/evaluation/answer/${test.id}`,
              null,
              { params: evalParams, timeout: 300000 },
            );
            setAnswers((current) => ({ ...current, [test.id]: data }));
            if (data.retrieval) {
              setRetrieval((current) => ({
                ...current,
                [test.id]: { retrieval: data.retrieval as Record<string, unknown> },
              }));
            }
          } else {
            const { data } = await api.post<Record<string, unknown>>(
              `/chat/evaluation/retrieval/${test.id}`,
              null,
              { params: evalParams, timeout: 180000 },
            );
            setRetrieval((current) => ({ ...current, [test.id]: data }));
          }
        } catch {
          failed += 1;
        }
        setDoneCount((current) => {
          const next = current + 1;
          setProgress(
            t("evalExtended.analyzing", { current: next, total: tests.length }) +
              (failed ? t("evalExtended.errorsCount", { failed }) : ""),
          );
          return next;
        });
      });
      if (failed) {
        setError(
          t("evalExtended.partialEvalSuccess", {
            success: tests.length - failed,
            total: tests.length,
            failed,
          }),
        );
      }
    } catch {
      setError(
        mode === "answer"
          ? t("evalExtended.answerAuditFailed")
          : t("evalExtended.retrievalAuditFailed"),
      );
    } finally {
      setRunning(null);
      setProgress(null);
    }
  };

  const activeKpis = tab === "answer" ? answerKpiList : retrievalKpiList;
  const activeAvg = tab === "answer" ? answerAvg : retrievalAvg;
  const retrievalChart = categoryChart(retrieval, "mrr", "retrieval");
  const chartLabel =
    tab === "answer"
      ? t("evalExtended.chartCompareTitle")
      : t("evalExtended.avgMrr");
  const chartEmpty =
    tab === "answer"
      ? !comparisonChart.some((row) => row.sinRag != null || row.conRag != null)
      : retrievalChart.length === 0;  const evaluatedCount = activeAvg.count;
  const selectedTest = tests.find((item) => item.id === selectedId) ?? null;
  const selectedPayload = selectedTest ? source[selectedTest.id] : undefined;
  const generatedAnswer =
    typeof selectedPayload?.generated_answer === "string"
      ? selectedPayload.generated_answer
      : "";
  const vanillaAnswer =
    typeof selectedPayload?.vanilla_answer === "string"
      ? selectedPayload.vanilla_answer
      : "";
  const feedback =
    typeof (selectedPayload?.evaluation as Record<string, unknown> | undefined)
      ?.feedback === "string"
      ? String((selectedPayload?.evaluation as Record<string, unknown>).feedback)
      : "";
  const vanillaFeedback =
    typeof (
      selectedPayload?.vanilla_evaluation as Record<string, unknown> | undefined
    )?.feedback === "string"
      ? String(
          (selectedPayload?.vanilla_evaluation as Record<string, unknown>)
            .feedback,
        )
      : "";

  return (
    <section className="flex min-h-0 flex-1 flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("evalExtended.auditTitle")}
          </p>
          <p className="text-sm text-slate-700">
            {t("evalExtended.auditIntroFull", { count: tests.length })}
          </p>
        </div>
        <select
          value={selectedKbId}
          onChange={(event) => setSelectedKbId(event.target.value)}
          disabled={Boolean(running)}
          className="h-10 min-w-[220px] rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700"
        >
          <option value="">{t("evalExtended.allTenantBases")}</option>
          {knowledgeBases.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name}
            </option>
          ))}
        </select>
      </div>

      <FrozenRagConfigBar
        temperature={temperature}
        onTemperatureChange={setTemperature}
      />

      <div className="flex flex-wrap gap-2 border-b border-slate-200">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`rounded-t-xl px-4 py-2 text-sm font-semibold ${
              tab === item.id
                ? "bg-white text-[color:var(--agro-primary)] shadow-sm ring-1 ring-slate-200"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t(item.labelKey)}
          </button>
        ))}
      </div>

      {tab === "validate" ? (
        <AnnotatePanel />
      ) : tests.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center text-sm text-slate-500">
          {t("evalExtended.emptyBankAudit")}
        </div>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-[minmax(280px,1fr)_minmax(0,2fr)]">
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-900">
                {tab === "answer"
                  ? t("evalExtended.compareTitle")
                  : t("evalExtended.contextIndicators")}
              </h2>
              {tab === "answer" && (
                <p className="text-xs text-slate-500">
                  {t("evalExtended.compareIntro")}
                </p>
              )}
              <button
                type="button"
                disabled={Boolean(running) || tests.length === 0}
                onClick={() => void runAudit(tab === "answer" ? "answer" : "retrieval")}
                className="h-11 w-full rounded-lg bg-[color:var(--agro-primary)] text-sm font-semibold text-white shadow-sm disabled:opacity-50"
              >
                {running === (tab === "answer" ? "answer" : "retrieval")
                  ? t("evalExtended.executing")
                  : tab === "answer"
                    ? t("evalExtended.runCompareAudit", { n: tests.length })
                    : t("evalExtended.runRetrievalAudit")}
              </button>
              {progress && (
                <div>
                  <p className="text-xs font-medium text-slate-500">{progress}</p>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full bg-[color:var(--agro-primary)]"
                      style={{
                        width: `${tests.length ? (doneCount / tests.length) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
              )}
              {error && (
                <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                  {error}
                </p>
              )}
              {evaluatedCount === 0 && !running ? (
                <div className="rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-400">
                  {t("evalExtended.clickToRunPrefix")}{" "}
                  <b>
                    {tab === "answer"
                      ? t("evalExtended.clickToRunCompare")
                      : t("evalExtended.clickToRunRetrieval")}
                  </b>{" "}
                  {t("evalExtended.clickToRunSuffix")}
                </div>
              ) : tab === "answer" ? (
                <div className="space-y-3">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
                    {t("evalExtended.judgeSection")}
                  </p>
                  {answerKpiList.map((kpi) => (
                    <CompareKpiCard
                      key={kpi.key}
                      label={kpi.label}
                      vanilla={vanillaAvg.result[kpi.key]}
                      rag={answerAvg.result[kpi.key]}
                      kind={kpi.kind}
                      vanillaLabel={t("evalExtended.noRag")}
                      ragLabel={t("evalExtended.withRag")}
                    />
                  ))}
                  <p className="pt-2 text-[11px] font-bold uppercase tracking-wide text-slate-400">
                    {t("evalExtended.ragasSection")}
                    {ragasSource
                      ? ` · ${
                          ragasSource === "ragas"
                            ? t("evalExtended.ragasOfficial")
                            : t("evalExtended.ragasFallback")
                        }`
                      : ""}
                  </p>
                  {ragasKpiList.map((kpi) => (
                    <CompareKpiCard
                      key={kpi.key}
                      label={kpi.label}
                      vanilla={vanillaRagasAvg.result[kpi.key]}
                      rag={ragasAvg.result[kpi.key]}
                      kind={kpi.kind}
                      vanillaLabel={t("evalExtended.noRag")}
                      ragLabel={t("evalExtended.withRag")}
                    />
                  ))}
                  {(hallucinationRate.noRag != null ||
                    hallucinationRate.withRag != null) && (
                    <CompareKpiCard
                      label={t("evalExtended.kpiHallucinationRate")}
                      vanilla={hallucinationRate.noRag}
                      rag={hallucinationRate.withRag}
                      kind="unit"
                      vanillaLabel={t("evalExtended.noRag")}
                      ragLabel={t("evalExtended.withRag")}
                    />
                  )}
                  {evaluatedCount > 0 && (
                    <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-center text-xs font-semibold text-emerald-700">
                      {t("evalExtended.compareDoneCount", { count: evaluatedCount })}
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {activeKpis.map((kpi) => (
                    <KpiCard
                      key={kpi.key}
                      label={kpi.label}
                      value={activeAvg.result[kpi.key]}
                      kind={kpi.kind}
                    />
                  ))}
                  {evaluatedCount > 0 && (
                    <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-center text-xs font-semibold text-emerald-700">
                      {t("evalExtended.retrievalDoneCount", { count: evaluatedCount })}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-900">
                {tab === "answer"
                  ? t("evalExtended.chartCompareTitle")
                  : t("evalExtended.chartRetrievalTitle")}
              </h2>
              <p className="mt-1 text-xs text-slate-500">{chartLabel}</p>
              {chartEmpty ? (
                <div className="mt-8 rounded-xl border border-dashed border-slate-200 px-4 py-16 text-center text-sm text-slate-400">
                  {t("evalExtended.chartEmpty")}
                </div>
              ) : tab === "answer" ? (
                <div className="mt-4 space-y-6">
                  <div className="h-[280px]">
                    <p className="mb-1 text-xs font-semibold text-slate-600">
                      {t("evalExtended.judgeSection")} (1–5)
                    </p>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={comparisonChart}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="metric" tick={{ fontSize: 11 }} interval={0} />
                        <YAxis domain={[0, 5]} tick={{ fontSize: 11 }} />
                        <Tooltip
                          formatter={(value) =>
                            typeof value === "number"
                              ? value.toFixed(2)
                              : String(value ?? "")
                          }
                        />
                        <Legend />
                        <Bar
                          dataKey="sinRag"
                          name={t("evalExtended.noRag")}
                          fill="#94a3b8"
                          radius={[6, 6, 0, 0]}
                        />
                        <Bar
                          dataKey="conRag"
                          name={t("evalExtended.withRag")}
                          fill="#059669"
                          radius={[6, 6, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="h-[280px]">
                    <p className="mb-1 text-xs font-semibold text-slate-600">
                      {t("evalExtended.ragasSection")} (0–1)
                    </p>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={ragasChart}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="metric" tick={{ fontSize: 10 }} interval={0} />
                        <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                        <Tooltip
                          formatter={(value) =>
                            typeof value === "number"
                              ? value.toFixed(3)
                              : String(value ?? "")
                          }
                        />
                        <Legend />
                        <Bar
                          dataKey="sinRag"
                          name={t("evalExtended.noRag")}
                          fill="#94a3b8"
                          radius={[6, 6, 0, 0]}
                        />
                        <Bar
                          dataKey="conRag"
                          name={t("evalExtended.withRag")}
                          fill="#0f766e"
                          radius={[6, 6, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : (
                <div className="mt-4 h-[380px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={retrievalChart}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="category" tick={{ fontSize: 11 }} interval={0} />
                      <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                      <Tooltip
                        formatter={(value) =>
                          typeof value === "number"
                            ? value.toFixed(4)
                            : String(value ?? "")
                        }
                      />
                      <Bar
                        dataKey="valor"
                        name={chartLabel}
                        fill="#059669"
                        radius={[6, 6, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>

          {evaluatedCount > 0 && (
            <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-3 py-2 font-bold">{t("evalExtended.question")}</th>
                    <th className="px-3 py-2 font-bold">{t("evalExtended.colCategory")}</th>
                    {tab === "answer"
                      ? [
                          ...COMPARE_METRICS.flatMap((key) => [
                            <th key={`${key}-v`} className="px-3 py-2 font-bold">
                              {key.slice(0, 3).toUpperCase()} {t("evalExtended.noRagShort")}
                            </th>,
                            <th key={`${key}-r`} className="px-3 py-2 font-bold">
                              {key.slice(0, 3).toUpperCase()} {t("evalExtended.withRagShort")}
                            </th>,
                          ]),
                          ...RAGAS_METRICS.slice(0, 2).flatMap((key) => [
                            <th key={`${key}-v`} className="px-3 py-2 font-bold">
                              {key === "faithfulness" ? "Fai" : "Rel"}{" "}
                              {t("evalExtended.noRagShort")}
                            </th>,
                            <th key={`${key}-r`} className="px-3 py-2 font-bold">
                              {key === "faithfulness" ? "Fai" : "Rel"}{" "}
                              {t("evalExtended.withRagShort")}
                            </th>,
                          ]),
                        ]
                      : activeKpis.slice(0, 5).map((kpi) => (
                          <th key={kpi.key} className="px-3 py-2 font-bold">
                            {kpi.label.split(" (")[0]}
                          </th>
                        ))}
                  </tr>
                </thead>
                <tbody>
                  {tests
                    .filter((test) => Boolean(source[test.id]))
                    .map((test) => (
                      <tr
                        key={test.id}
                        className={`cursor-pointer border-t border-slate-100 ${
                          selectedId === test.id ? "bg-blue-50" : "hover:bg-slate-50"
                        }`}
                        onClick={() => setSelectedId(test.id)}
                      >
                        <td className="max-w-xs truncate px-3 py-2 font-medium text-slate-800">
                          {test.question}
                        </td>
                        <td className="px-3 py-2 text-slate-500">
                          {categoryLabel(t,test.category)}
                        </td>
                        {tab === "answer"
                          ? [
                              ...COMPARE_METRICS.flatMap((key) => {
                                const vanilla = metricValue(
                                  source[test.id],
                                  key,
                                  "vanilla",
                                );
                                const rag = metricValue(
                                  source[test.id],
                                  key,
                                  "evaluation",
                                );
                                return [
                                  <td
                                    key={`${test.id}-${key}-v`}
                                    className="px-3 py-2 tabular-nums text-slate-600"
                                  >
                                    {vanilla == null
                                      ? "—"
                                      : formatMetric(vanilla, "score")}
                                  </td>,
                                  <td
                                    key={`${test.id}-${key}-r`}
                                    className="px-3 py-2 tabular-nums font-semibold text-emerald-800"
                                  >
                                    {rag == null ? "—" : formatMetric(rag, "score")}
                                  </td>,
                                ];
                              }),
                              ...RAGAS_METRICS.slice(0, 2).flatMap((key) => {
                                const vanilla = metricValue(
                                  source[test.id],
                                  key,
                                  "vanilla_ragas",
                                );
                                const rag = metricValue(
                                  source[test.id],
                                  key,
                                  "ragas",
                                );
                                return [
                                  <td
                                    key={`${test.id}-${key}-v`}
                                    className="px-3 py-2 tabular-nums text-slate-600"
                                  >
                                    {vanilla == null
                                      ? "—"
                                      : formatMetric(vanilla, "unit")}
                                  </td>,
                                  <td
                                    key={`${test.id}-${key}-r`}
                                    className="px-3 py-2 tabular-nums font-semibold text-teal-800"
                                  >
                                    {rag == null ? "—" : formatMetric(rag, "unit")}
                                  </td>,
                                ];
                              }),
                            ]
                          : activeKpis.slice(0, 5).map((kpi) => {
                              const value = metricValue(
                                source[test.id],
                                kpi.key,
                                prefer,
                              );
                              return (
                                <td key={kpi.key} className="px-3 py-2 tabular-nums">
                                  {value == null
                                    ? "—"
                                    : formatMetric(value, kpi.kind)}
                                </td>
                              );
                            })}
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}

          {selectedTest && selectedPayload && (
            <aside className="rounded-2xl border border-amber-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">
                    {t("evalExtended.caseLabel", { id: selectedTest.id })}
                  </p>
                  <h3 className="text-sm font-semibold text-slate-900">
                    {selectedTest.question}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedId(null)}
                  className="text-slate-400 hover:text-slate-700"
                >
                  ✕
                </button>
              </div>
              <p className="mt-2 text-[11px] text-slate-500">
                {t("evalExtended.keywordsLabel", {
                  keywords: selectedTest.keywords.join(", ") || "—",
                })}
              </p>
              {tab === "answer" ? (
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">
                      {t("evalExtended.noRag")}
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                      {vanillaAnswer || "—"}
                    </p>
                    {vanillaFeedback && (
                      <p className="mt-2 text-xs text-slate-500">{vanillaFeedback}</p>
                    )}
                  </div>
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 px-3 py-2">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-700">
                      {t("evalExtended.withRag")}
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">
                      {generatedAnswer || "—"}
                    </p>
                    {feedback && (
                      <p className="mt-2 text-xs text-slate-600">{feedback}</p>
                    )}
                  </div>
                </div>
              ) : (
                <>
                  {generatedAnswer && (
                    <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">
                      {generatedAnswer}
                    </p>
                  )}
                  {feedback && (
                    <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                      {feedback}
                    </p>
                  )}
                </>
              )}
            </aside>
          )}
        </>
      )}
    </section>
  );
}
