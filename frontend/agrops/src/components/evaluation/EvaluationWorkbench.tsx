import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ChevronRight,
  Download,
  Filter,
  Lock,
  Plus,
  Search,
  Settings2,
  SlidersHorizontal,
  Table2,
  X,
} from "lucide-react";

import api from "@/api";
import { useTranslation } from "@/i18n/I18nProvider";
import { categoryLabel } from "@/components/evaluation/labels";
import FrozenRagConfigBar, {
  useSyncedTemperature,
} from "@/components/evaluation/FrozenRagConfigBar";
import ExperimentHistory from "@/components/evaluation/ExperimentHistory";
import { useEvaluationTests, useKnowledgeBases } from "@/hooks/useCachedApi";
import { useOrganization } from "@/context/OrganizationContext";

export type WorkbenchView = "dataset" | "analysis" | "embedding";

type Props = {
  view: WorkbenchView;
  onViewChange: (view: WorkbenchView) => void;
};

type TestItem = {
  id: number;
  question: string;
  keywords: string[];
  reference_answer: string;
  category: string;
  source_file?: string;
  page?: string;
};

type RetrievalPayload = {
  test_id?: number;
  id?: number;
  retrieval?: Record<string, number>;
} & Record<string, unknown>;

type AnswerPayload = {
  test_id?: number;
  id?: number;
  generated_answer?: string;
  evaluation?: Record<string, unknown>;
  retrieval?: Record<string, number>;
  retrieved_chunks?: Array<{ content?: string }>;
} & Record<string, unknown>;

type EvalCategory = "all" | "prompt" | "context" | "response" | "text";

type AgroMetric = {
  id: string;
  name: string;
  description: string;
  category: Exclude<EvalCategory, "all">;
  engine: string;
  source: "retrieval" | "answer";
  invert?: boolean;
  defaultThreshold: number;
};

type SchemaField = "question" | "keywords" | "reference_answer" | "generated_answer" | "category";

const METRIC_DEFAULTS: Record<
  string,
  { category: Exclude<EvalCategory, "all">; source: "retrieval" | "answer"; invert?: boolean; defaultThreshold: number }
> = {
  prompt_coverage: { category: "prompt", source: "answer", defaultThreshold: 0.6 },
  accuracy: { category: "response", source: "answer", defaultThreshold: 0.6 },
  completeness: { category: "response", source: "answer", defaultThreshold: 0.6 },
  relevance: { category: "response", source: "answer", defaultThreshold: 0.6 },
  hallucination: { category: "response", source: "answer", invert: true, defaultThreshold: 0.3 },
  faithfulness: { category: "response", source: "answer", defaultThreshold: 0.6 },
  mrr: { category: "context", source: "retrieval", defaultThreshold: 0.5 },
  ndcg: { category: "context", source: "retrieval", defaultThreshold: 0.6 },
  keyword_coverage: { category: "context", source: "retrieval", defaultThreshold: 0.7 },
  citation_accuracy: { category: "text", source: "answer", defaultThreshold: 0.8 },
};

function buildAgroMetrics(t: (key: string) => string): AgroMetric[] {
  return [
    {
      id: "prompt_coverage",
      name: t("evalExtended.metricPromptCoverage"),
      description: t("evalExtended.metricPromptCoverageDesc"),
      category: "prompt",
      engine: t("evalExtended.engineLlmJudge"),
      source: "answer",
      defaultThreshold: 0.6,
    },
    {
      id: "accuracy",
      name: t("evalExtended.metricAccuracy"),
      description: t("evalExtended.metricAccuracyDesc"),
      category: "response",
      engine: t("evalExtended.engineLlmJudge"),
      source: "answer",
      defaultThreshold: 0.6,
    },
    {
      id: "completeness",
      name: t("evalExtended.metricCompleteness"),
      description: t("evalExtended.metricCompletenessDesc"),
      category: "response",
      engine: t("evalExtended.engineLlmJudge"),
      source: "answer",
      defaultThreshold: 0.6,
    },
    {
      id: "relevance",
      name: t("evalExtended.metricRelevance"),
      description: t("evalExtended.metricRelevanceDesc"),
      category: "response",
      engine: t("evalExtended.engineLlmJudge"),
      source: "answer",
      defaultThreshold: 0.6,
    },
    {
      id: "hallucination",
      name: t("evalExtended.metricHallucination"),
      description: t("evalExtended.metricHallucinationDesc"),
      category: "response",
      engine: t("evalExtended.engineLlmJudge"),
      source: "answer",
      invert: true,
      defaultThreshold: 0.3,
    },
    {
      id: "faithfulness",
      name: t("evalExtended.metricFaithfulness"),
      description: t("evalExtended.metricFaithfulnessDesc"),
      category: "response",
      engine: t("evalExtended.engineLlmJudge"),
      source: "answer",
      defaultThreshold: 0.6,
    },
    {
      id: "mrr",
      name: t("evalExtended.metricMrrSources"),
      description: t("evalExtended.metricMrrSourcesDesc"),
      category: "context",
      engine: t("evalExtended.engineRetrieval"),
      source: "retrieval",
      defaultThreshold: 0.5,
    },
    {
      id: "ndcg",
      name: t("evalExtended.metricNdcgOrder"),
      description: t("evalExtended.metricNdcgOrderDesc"),
      category: "context",
      engine: t("evalExtended.engineRetrieval"),
      source: "retrieval",
      defaultThreshold: 0.6,
    },
    {
      id: "keyword_coverage",
      name: t("evalExtended.metricKeywordCoverage"),
      description: t("evalExtended.metricKeywordCoverageDesc"),
      category: "context",
      engine: t("evalExtended.engineRetrieval"),
      source: "retrieval",
      defaultThreshold: 0.7,
    },
    {
      id: "citation_accuracy",
      name: t("evalExtended.metricCitationAccuracy"),
      description: t("evalExtended.metricCitationAccuracyDesc"),
      category: "text",
      engine: t("evalExtended.engineDeterministic"),
      source: "answer",
      defaultThreshold: 0.8,
    },
  ];
}

function buildSchemaColumns(t: (key: string) => string): { id: SchemaField; label: string }[] {
  return [
    { id: "question", label: t("evalExtended.workbenchSchemaColQuestion") },
    { id: "keywords", label: t("evalExtended.workbenchSchemaColKeywords") },
    { id: "reference_answer", label: t("evalExtended.workbenchSchemaColReference") },
    { id: "generated_answer", label: t("evalExtended.workbenchSchemaColGenerated") },
    { id: "category", label: t("evalExtended.workbenchSchemaColCategory") },
  ];
}

const DEFAULT_METRIC_IDS = [
  "accuracy",
  "completeness",
  "relevance",
  "faithfulness",
  "mrr",
  "ndcg",
  "keyword_coverage",
];

const DEFAULT_MAPPING: Record<string, SchemaField> = {
  prompt: "question",
  context: "keywords",
  response: "generated_answer",
  expected_response: "reference_answer",
};

function toUnit(value: number | null | undefined): number | null {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return null;
  }
  const raw = Number(value);
  if (raw < 0) return 0;
  if (raw <= 1) return raw;
  if (raw <= 5) return raw / 5;
  return Math.min(raw / 100, 1);
}

function metricFrom(target: Record<string, unknown> | undefined, keys: string[]): number | null {
  if (!target) return null;
  for (const key of keys) {
    const value = target[key];
    if (value !== undefined && value !== null && value !== "") {
      const numeric = Number(value);
      if (!Number.isNaN(numeric)) return numeric;
    }
  }
  return null;
}

function retrievalValue(row: RetrievalPayload | undefined, metric: string): number | null {
  if (!row) return null;
  const nested = (row.retrieval || row) as Record<string, unknown>;
  return metricFrom(nested, [metric]);
}

function answerValue(row: AnswerPayload | undefined, metric: string): number | null {
  if (!row) return null;
  const nested = (row.evaluation || row) as Record<string, unknown>;
  const aliases: Record<string, string[]> = {
    accuracy: ["accuracy", "punteria"],
    completeness: ["completeness", "exhaustividad"],
    prompt_coverage: ["completeness", "exhaustividad", "accuracy", "keyword_coverage"],
    relevance: ["relevance", "utilidad"],
    faithfulness: ["faithfulness", "fidelidad"],
    citation_accuracy: ["citation_accuracy", "citas"],
    mrr: ["mrr"],
    ndcg: ["ndcg"],
    keyword_coverage: ["keyword_coverage"],
  };
  const raw = metricFrom(nested, aliases[metric] || [metric]);
  if (metric !== "hallucination") return raw;
  const faithful = toUnit(metricFrom(nested, ["faithfulness", "fidelidad", "groundedness"]));
  if (faithful === null) return null;
  return 1 - faithful;
}

function formatScore(value: number | null): string {
  if (value === null) return "--";
  return value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "") || "0";
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
}

async function mapPool<T>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<void>,
) {
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const index = next;
      next += 1;
      await fn(items[index], index);
    }
  });
  await Promise.all(workers);
}

function ScorePill({
  value,
  invert,
  threshold,
}: {
  value: number | null;
  invert?: boolean;
  threshold: number;
}) {
  if (value === null) {
    return <span className="font-medium text-slate-300">--</span>;
  }
  const passed = invert ? value <= threshold : value >= threshold;
  return (
    <span
      className={`inline-flex min-w-[3.25rem] justify-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        passed
          ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
          : "bg-rose-50 text-rose-700 ring-1 ring-rose-200"
      }`}
    >
      {formatScore(value)}
    </span>
  );
}

export default function EvaluationWorkbench({ view, onViewChange }: Props) {
  const { t } = useTranslation();
  const agroMetrics = useMemo(() => buildAgroMetrics(t), [t]);
  const schemaColumns = useMemo(() => buildSchemaColumns(t), [t]);
  const { selectedOrg } = useOrganization();
  const { data: cachedTests, isLoading } = useEvaluationTests();
  const { data: kbList } = useKnowledgeBases(selectedOrg?.id);
  const tests = (cachedTests as TestItem[] | undefined) ?? [];

  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [filterOpen, setFilterOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [schemaOpen, setSchemaOpen] = useState(false);
  const [schemaStep, setSchemaStep] = useState(false);
  const [locked, setLocked] = useState(false);
  const [detailId, setDetailId] = useState<number | null>(null);

  const [selectedIds, setSelectedIds] = useState<string[]>(DEFAULT_METRIC_IDS);
  const [mapping, setMapping] = useState(DEFAULT_MAPPING);
  const [thresholds, setThresholds] = useState<Record<string, { operator: "gte" | "lte"; value: number }>>(
    () =>
      Object.fromEntries(
        Object.entries(METRIC_DEFAULTS).map(([id, metric]) => [
          id,
          {
            operator: metric.invert ? "lte" : "gte",
            value: metric.defaultThreshold,
          },
        ]),
      ),
  );

  const [retrieval, setRetrieval] = useState<Record<number, RetrievalPayload>>({});
  const [answers, setAnswers] = useState<Record<number, AnswerPayload>>({});
  const [timestamps, setTimestamps] = useState<Record<number, string>>({});
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
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
  const bestMrrId = useMemo(() => {
    if (!experiments.length) return null;
    return experiments.reduce((best, run) => (run.mrr > best.mrr ? run : best)).id;
  }, [experiments]);

  const knowledgeBases = useMemo(
    () => (kbList ?? []).map((kb) => ({ id: kb.id, name: kb.name })),
    [kbList],
  );
  const [selectedKbId, setSelectedKbId] = useState("");
  const { temperature, setTemperature } = useSyncedTemperature();

  useEffect(() => {
    setSelectedKbId((prev) => prev || knowledgeBases[0]?.id || "");
  }, [knowledgeBases]);

  useEffect(() => {
    if (view !== "embedding") return;
    void api
      .get("/chat/evaluation/experiments")
      .then((response) => setExperiments(response.data ?? []))
      .catch(() => undefined);
  }, [view]);

  const selectedMetrics = agroMetrics.filter((metric) => selectedIds.includes(metric.id));
  const categories = useMemo(
    () => Array.from(new Set(tests.map((test) => test.category).filter(Boolean))),
    [tests],
  );

  const rows = useMemo(() => {
    const term = search.toLowerCase().trim();
    return tests.filter((test) => {
      if (categoryFilter !== "all" && test.category !== categoryFilter) return false;
      if (!term) return true;
      const answer = String(answers[test.id]?.generated_answer || "");
      return (
        test.question.toLowerCase().includes(term) ||
        answer.toLowerCase().includes(term) ||
        categoryLabel(t,test.category).toLowerCase().includes(term)
      );
    });
  }, [tests, search, categoryFilter, answers]);

  const datasetLabel = selectedKbId
    ? knowledgeBases.find((kb) => kb.id === selectedKbId)?.name || "banco_agricola"
    : "banco_agricola";

  const evalParams = useMemo(() => {
    const params: Record<string, string> = {};
    if (selectedOrg?.id) params.organization_id = selectedOrg.id;
    if (selectedKbId) params.knowledge_base_id = selectedKbId;
    params.distance_metric = "cosine";
    params.embedding_model = "nomic-embed-text";
    params.temperature = String(temperature);
    params.top_k = "3";
    return params;
  }, [selectedOrg?.id, selectedKbId, temperature]);

  const runEvaluate = async () => {
    if (!tests.length || locked) return;
    const needRetrieval = selectedMetrics.some((metric) => metric.source === "retrieval");
    const needAnswer = selectedMetrics.some((metric) => metric.source === "answer");
    setRunning(true);
    setError(null);
    let done = 0;
    setProgress(t("evalExtended.workbenchEvaluating", { done: 0, total: tests.length }));
    let failed = 0;
    try {
      await mapPool(tests, 1, async (test) => {
        try {
          if (needAnswer) {
            const { data } = await api.post<AnswerPayload>(
              `/chat/evaluation/answer/${test.id}`,
              null,
              { params: evalParams, timeout: 300000 },
            );
            setAnswers((current) => ({ ...current, [test.id]: data }));
            if (data.retrieval) {
              setRetrieval((current) => ({ ...current, [test.id]: data }));
            }
          } else if (needRetrieval) {
            const { data } = await api.post<RetrievalPayload>(
              `/chat/evaluation/retrieval/${test.id}`,
              null,
              { params: evalParams, timeout: 180000 },
            );
            setRetrieval((current) => ({ ...current, [test.id]: data }));
          }
          setTimestamps((current) => ({ ...current, [test.id]: new Date().toISOString() }));
        } catch {
          failed += 1;
        }
        done += 1;
        setProgress(
          failed
            ? failed === 1
              ? t("evalExtended.workbenchEvaluatingError", {
                  done,
                  total: tests.length,
                  failed,
                })
              : t("evalExtended.workbenchEvaluatingErrors", {
                  done,
                  total: tests.length,
                  failed,
                })
            : t("evalExtended.workbenchEvaluating", { done, total: tests.length }),
        );
      });
      if (failed) {
        setError(
          t("evalExtended.workbenchPartialEval", {
            success: tests.length - failed,
            total: tests.length,
            failed,
          }),
        );
      }
    } catch {
      setError(t("evalExtended.evalFailedWorkbench"));
    } finally {
      setRunning(false);
      setProgress(null);
    }
  };

  const cellValue = (testId: number, metric: AgroMetric): number | null => {
    if (metric.source === "retrieval") {
      return toUnit(retrievalValue(retrieval[testId], metric.id));
    }
    return toUnit(answerValue(answers[testId], metric.id));
  };

  const exportCsv = () => {
    const headers = [
      "traceId",
      "timestamp",
      "prompt",
      "response",
      "category",
      ...selectedMetrics.map((metric) => metric.id),
    ];
    const lines = [headers.join(",")];
    for (const test of rows) {
      const answer = String(answers[test.id]?.generated_answer || "").replace(/"/g, '""');
      const values = [
        `eval-${test.id}`,
        timestamps[test.id] || "",
        `"${test.question.replace(/"/g, '""')}"`,
        `"${answer}"`,
        test.category,
        ...selectedMetrics.map((metric) => formatScore(cellValue(test.id, metric))),
      ];
      lines.push(values.join(","));
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "evaluacion-agrops.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const analysisData = useMemo(() => {
    const grouped = new Map<string, { category: string; count: number; scores: Record<string, number[]> }>();
    for (const test of tests) {
      const key = categoryLabel(t,test.category);
      if (!grouped.has(key)) {
        grouped.set(key, { category: key, count: 0, scores: {} });
      }
      const bucket = grouped.get(key)!;
      bucket.count += 1;
      for (const metric of selectedMetrics) {
        const value = cellValue(test.id, metric);
        if (value === null) continue;
        bucket.scores[metric.id] = bucket.scores[metric.id] || [];
        bucket.scores[metric.id].push(value);
      }
    }
    return Array.from(grouped.values()).map((bucket) => {
      const row: Record<string, string | number> = {
        category: bucket.category,
        preguntas: bucket.count,
      };
      for (const metric of selectedMetrics) {
        const values = bucket.scores[metric.id] || [];
        row[metric.id] = values.length
          ? values.reduce((sum, value) => sum + value, 0) / values.length
          : 0;
      }
      return row;
    });
  }, [tests, retrieval, answers, selectedMetrics]);

  const passRate = useMemo(() => {
    let total = 0;
    let passed = 0;
    for (const test of tests) {
      for (const metric of selectedMetrics) {
        const value = cellValue(test.id, metric);
        if (value === null) continue;
        total += 1;
        const threshold = thresholds[metric.id]?.value ?? metric.defaultThreshold;
        const ok = metric.invert ? value <= threshold : value >= threshold;
        if (ok) passed += 1;
      }
    }
    return { total, passed };
  }, [tests, retrieval, answers, selectedMetrics, thresholds]);

  const detail = tests.find((test) => test.id === detailId) ?? null;

  return (
    <section className="flex min-h-[calc(100vh-11rem)] flex-1 flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-4 pt-3">
        <FrozenRagConfigBar
          temperature={temperature}
          onTemperatureChange={setTemperature}
        />
      </div>
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3">
        <select
          value={selectedKbId}
          onChange={(event) => setSelectedKbId(event.target.value)}
          disabled={locked || running}
          className="h-9 max-w-[220px] rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700"
        >
          <option value="">banco_agricola.jsonl</option>
          {knowledgeBases.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="h-9 rounded-md border border-dashed border-slate-300 px-3 text-xs font-semibold text-slate-500"
          title={t("evalExtended.workbenchCompareTitle")}
        >
          {t("evalExtended.workbenchCompare")}
        </button>
        <label className="relative min-w-[220px] flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("evalExtended.searchQuestion")}
            className="h-9 w-full rounded-md border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm outline-none focus:border-[color:var(--agro-primary)] focus:bg-white"
          />
        </label>
        <button
          type="button"
          onClick={() => setSchemaOpen(true)}
          className="h-9 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-600"
        >
          {t("evalExtended.viewSchema")}
        </button>
        <button
          type="button"
          onClick={() => setLocked((value) => !value)}
          className={`flex h-9 items-center gap-1.5 rounded-md border px-3 text-xs font-semibold ${
            locked
              ? "border-amber-200 bg-amber-50 text-amber-700"
              : "border-slate-200 text-slate-600"
          }`}
        >
          <Lock size={13} />
          {locked ? t("evalExtended.locked") : t("evalExtended.lockDataset")}
        </button>
        <button
          type="button"
          onClick={() => setFilterOpen((value) => !value)}
          className="flex h-9 items-center gap-1.5 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-600"
        >
          <Filter size={13} />
          {t("evalExtended.filter")}
        </button>
      </div>

      {filterOpen && (
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2">
          <Filter size={14} className="text-slate-400" />
          <select
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            className="h-8 rounded-md border border-slate-200 bg-white px-2 text-xs"
          >
            <option value="all">{t("evalExtended.allCategories")}</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {categoryLabel(t,category)}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-2">
        <div className="flex overflow-hidden rounded-md border border-slate-200">
          {(
            [
              ["dataset", t("evalExtended.tabDataset")],
              ["analysis", t("evalExtended.tabAnalysis")],
              ["embedding", t("evalExtended.tabEmbedding")],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => onViewChange(id)}
              className={`px-4 py-1.5 text-xs font-bold ${
                view === id
                  ? "bg-[color:var(--agro-primary)] text-white"
                  : "bg-white text-slate-500 hover:bg-slate-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {progress && (
            <span className="text-xs font-semibold text-[color:var(--agro-primary)]">
              {progress}
            </span>
          )}
          {passRate.total > 0 && (
            <span className="text-xs text-slate-500">
              {t("evalExtended.passRate", {
                passed: passRate.passed,
                total: passRate.total,
              })}
            </span>
          )}
          <button
            type="button"
            onClick={() => {
              setSchemaStep(false);
              setAddOpen(true);
            }}
            className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-500 hover:bg-slate-50"
            title={t("evalExtended.workbenchAddEvaluations")}
          >
            <Plus size={15} />
          </button>
          <button
            type="button"
            onClick={exportCsv}
            className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-500 hover:bg-slate-50"
            title={t("evalExtended.workbenchExportCsv")}
          >
            <Download size={15} />
          </button>
          <button
            type="button"
            onClick={() => setSchemaOpen(true)}
            className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-500 hover:bg-slate-50"
            title={t("evalExtended.workbenchConfigureSchema")}
          >
            <Settings2 size={15} />
          </button>
          <button
            type="button"
            onClick={() => void runEvaluate()}
            disabled={running || locked || !tests.length}
            title={t("evalExtended.workbenchEvaluateHint")}
            className="flex h-8 items-center gap-1.5 rounded-md bg-[color:var(--agro-primary)] px-3 text-xs font-bold text-white disabled:opacity-40"
          >
            <SlidersHorizontal size={14} />
            {t("evalExtended.evaluate")}
          </button>
        </div>
      </div>

      {error && (
        <p className="border-b border-rose-100 bg-rose-50 px-4 py-2 text-xs font-semibold text-rose-700">
          {error}
        </p>
      )}

      {view === "dataset" && (
        <div className="min-h-0 flex-1 overflow-auto">
          {isLoading ? (
            <p className="p-8 text-sm text-slate-500">{t("evalExtended.loadingBankWorkbench")}</p>
          ) : (
            <table className="min-w-full text-left text-sm">
              <thead className="sticky top-0 z-10 bg-slate-50 text-[11px] font-bold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="whitespace-nowrap px-4 py-2">traceId</th>
                  <th className="whitespace-nowrap px-4 py-2">timestamp</th>
                  <th className="min-w-[280px] px-4 py-2">prompt</th>
                  <th className="whitespace-nowrap px-4 py-2">{t("evalExtended.workbenchCategoryCol")}</th>
                  {selectedMetrics.map((metric) => (
                    <th key={metric.id} className="whitespace-nowrap px-3 py-2">
                      {metric.name}
                    </th>
                  ))}
                  <th className="min-w-[240px] px-4 py-2">response</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((test) => {
                  const answer = String(answers[test.id]?.generated_answer || "");
                  return (
                    <tr
                      key={test.id}
                      onClick={() => setDetailId(test.id)}
                      className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                    >
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-slate-500">
                        eval-{String(test.id).padStart(4, "0")}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-[11px] text-slate-500">
                        {formatTimestamp(timestamps[test.id] || null)}
                      </td>
                      <td className="max-w-[320px] px-4 py-3 text-slate-800">
                        <span className="line-clamp-2">{test.question}</span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                          {categoryLabel(t,test.category)}
                        </span>
                      </td>
                      {selectedMetrics.map((metric) => (
                        <td key={metric.id} className="px-3 py-3">
                          <ScorePill
                            value={cellValue(test.id, metric)}
                            invert={metric.invert}
                            threshold={thresholds[metric.id]?.value ?? metric.defaultThreshold}
                          />
                        </td>
                      ))}
                      <td className="max-w-[280px] px-4 py-3 text-slate-600">
                        <span className="line-clamp-2">{answer || "—"}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
          {!isLoading && rows.length === 0 && (
            <p className="p-8 text-sm text-slate-500">{t("evalExtended.emptyBankWorkbench")}</p>
          )}
        </div>
      )}

      {view === "analysis" && (
        <div className="grid gap-4 p-4 lg:grid-cols-[1.4fr_1fr]">
          <div className="rounded-lg border border-slate-200 p-4">
            <h3 className="text-sm font-bold text-slate-800">
              {t("evalExtended.workbenchMetricsByCategory")}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              {t("evalExtended.workbenchMetricsByCategoryHint", { dataset: datasetLabel })}
            </p>
            <div className="mt-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analysisData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="category" tick={{ fontSize: 11 }} interval={0} angle={-18} textAnchor="end" height={70} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  {selectedMetrics.slice(0, 4).map((metric, index) => (
                    <Bar
                      key={metric.id}
                      dataKey={metric.id}
                      name={metric.name}
                      fill={["#0038a8", "#22c55e", "#f59e0b", "#d91424"][index]}
                      radius={[4, 4, 0, 0]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <h3 className="text-sm font-bold text-slate-800">{t("evalExtended.workbenchBankSummary")}</h3>
            <dl className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">{t("evalExtended.workbenchQuestions")}</dt>
                <dd className="font-semibold">{tests.length}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">{t("evalExtended.workbenchEvaluated")}</dt>
                <dd className="font-semibold">{Object.keys(timestamps).length}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">{t("evalExtended.workbenchCriteriaPassed")}</dt>
                <dd className="font-semibold">
                  {passRate.passed}/{passRate.total || "—"}
                </dd>
              </div>
              {selectedMetrics.map((metric) => {
                const values = tests
                  .map((test) => cellValue(test.id, metric))
                  .filter((value): value is number => value !== null);
                const avg = values.length
                  ? values.reduce((sum, value) => sum + value, 0) / values.length
                  : null;
                return (
                  <div key={metric.id} className="flex items-center justify-between gap-3">
                    <dt className="text-slate-500">{metric.name}</dt>
                    <dd>
                      <ScorePill
                        value={avg}
                        invert={metric.invert}
                        threshold={thresholds[metric.id]?.value ?? metric.defaultThreshold}
                      />
                    </dd>
                  </div>
                );
              })}
            </dl>
          </div>
        </div>
      )}

      {view === "embedding" && (
        <div className="space-y-4 p-4">
          <p className="text-sm text-slate-600">{t("evalExtended.workbenchEmbeddingHint")}</p>
          <ExperimentHistory
            runs={experiments}
            loading={false}
            bestMrrId={bestMrrId}
          />
        </div>
      )}

      {addOpen && (
        <AddEvalsModal
          selectedIds={selectedIds}
          onClose={() => {
            setAddOpen(false);
            setSchemaStep(false);
          }}
          onNext={(ids) => {
            setSelectedIds(ids);
            setSchemaStep(true);
          }}
          onBack={() => setSchemaStep(false)}
          schemaStep={schemaStep}
          mapping={mapping}
          onMapping={setMapping}
          thresholds={thresholds}
          onThresholds={setThresholds}
          onSave={() => {
            setAddOpen(false);
            setSchemaStep(false);
          }}
        />
      )}

      {schemaOpen && (
        <SchemaDrawer
          mapping={mapping}
          schemaColumns={schemaColumns}
          onClose={() => setSchemaOpen(false)}
        />
      )}

      {detail && (
        <RowDrawer
          test={detail}
          answer={answers[detail.id]}
          retrieval={retrieval[detail.id]}
          metrics={selectedMetrics}
          values={Object.fromEntries(
            selectedMetrics.map((metric) => [metric.id, cellValue(detail.id, metric)]),
          )}
          thresholds={thresholds}
          onClose={() => setDetailId(null)}
          t={t}
        />
      )}
    </section>
  );
}

function AddEvalsModal({
  selectedIds,
  onClose,
  onNext,
  onBack,
  schemaStep,
  mapping,
  onMapping,
  thresholds,
  onThresholds,
  onSave,
}: {
  selectedIds: string[];
  onClose: () => void;
  onNext: (ids: string[]) => void;
  onBack: () => void;
  schemaStep: boolean;
  mapping: Record<string, SchemaField>;
  onMapping: (value: Record<string, SchemaField>) => void;
  thresholds: Record<string, { operator: "gte" | "lte"; value: number }>;
  onThresholds: (
    value: Record<string, { operator: "gte" | "lte"; value: number }>,
  ) => void;
  onSave: () => void;
}) {
  const { t } = useTranslation();
  const agroMetrics = useMemo(() => buildAgroMetrics(t), [t]);
  const schemaColumns = useMemo(() => buildSchemaColumns(t), [t]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<EvalCategory>("all");
  const [draft, setDraft] = useState<string[]>(selectedIds);
  const filtered = agroMetrics.filter((metric) => {
    const matches = category === "all" || metric.category === category;
    const query = search.toLowerCase();
    return (
      matches &&
      `${metric.name} ${metric.description}`.toLowerCase().includes(query)
    );
  });

  if (schemaStep) {
    const selected = agroMetrics.filter((metric) => draft.includes(metric.id));
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
        <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl bg-white shadow-xl">
          <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                {t("evalExtended.workbenchConfigureEval")}
              </p>
              <h2 className="text-lg font-extrabold text-slate-900">
                {t("evalExtended.workbenchSchemaThreshold")}
              </h2>
            </div>
            <button type="button" onClick={onClose} className="text-slate-400">
              <X size={18} />
            </button>
          </header>
          <div className="space-y-5 overflow-auto p-5">
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                {t("evalExtended.workbenchSchemaRequired")}
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                {t("evalExtended.workbenchSchemaMapHint")}
              </p>
              <div className="mt-3 space-y-2">
                {(["prompt", "context", "response", "expected_response"] as const).map((field) => (
                  <div
                    key={field}
                    className="grid grid-cols-[1fr_auto_1fr] items-center gap-3"
                  >
                    <span className="rounded-md bg-slate-100 px-3 py-2 text-xs font-bold uppercase text-slate-600">
                      {field === "prompt"
                        ? t("evalExtended.workbenchFieldQuestion")
                        : field === "context"
                          ? t("evalExtended.workbenchFieldContext")
                          : field === "response"
                            ? t("evalExtended.workbenchFieldAnswer")
                            : t("evalExtended.workbenchFieldReference")}
                    </span>
                    <ChevronRight size={14} className="text-slate-400" />
                    <select
                      value={mapping[field]}
                      onChange={(event) =>
                        onMapping({ ...mapping, [field]: event.target.value as SchemaField })
                      }
                      className="h-9 rounded-md border border-slate-200 bg-white px-2 text-xs"
                    >
                      {schemaColumns.map((column) => (
                        <option key={column.id} value={column.id}>
                          {column.label}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                {t("evalExtended.workbenchPassCriteria")}
              </h3>
              <div className="mt-3 space-y-2">
                {selected.map((metric) => (
                  <div
                    key={metric.id}
                    className="grid grid-cols-[1fr_auto_90px] items-center gap-2"
                  >
                    <span className="text-xs font-semibold text-slate-600">{metric.name}</span>
                    <div className="flex overflow-hidden rounded-md border border-slate-200">
                      {(["lte", "gte"] as const).map((operator) => (
                        <button
                          key={operator}
                          type="button"
                          onClick={() =>
                            onThresholds({
                              ...thresholds,
                              [metric.id]: {
                                ...(thresholds[metric.id] || { value: metric.defaultThreshold }),
                                operator,
                              },
                            })
                          }
                          className={`px-2 py-1 text-[11px] font-bold ${
                            (thresholds[metric.id]?.operator || (metric.invert ? "lte" : "gte")) ===
                            operator
                              ? "bg-[color:var(--agro-primary)] text-white"
                              : "bg-white text-slate-500"
                          }`}
                        >
                          {operator === "lte" ? "≤" : "≥"}
                        </button>
                      ))}
                    </div>
                    <input
                      type="number"
                      min={0}
                      max={1}
                      step={0.05}
                      value={thresholds[metric.id]?.value ?? metric.defaultThreshold}
                      onChange={(event) =>
                        onThresholds({
                          ...thresholds,
                          [metric.id]: {
                            operator:
                              thresholds[metric.id]?.operator ||
                              (metric.invert ? "lte" : "gte"),
                            value: Number(event.target.value),
                          },
                        })
                      }
                      className="h-8 rounded-md border border-slate-200 px-2 text-xs"
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
          <footer className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
            <button
              type="button"
              onClick={onBack}
              className="rounded-md border border-slate-200 px-4 py-2 text-xs font-bold text-slate-600"
            >
              {t("evalExtended.back")}
            </button>
            <button
              type="button"
              onClick={onSave}
              className="rounded-md bg-[color:var(--agro-primary)] px-4 py-2 text-xs font-bold text-white"
            >
              {t("common.save")}
            </button>
          </footer>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-white shadow-xl">
        <header className="flex items-start justify-between border-b border-slate-200 px-6 py-5">
          <div>
            <h2 className="text-lg font-extrabold text-slate-900">
              {t("evalExtended.workbenchAddEvaluations")}
            </h2>
            <p className="mt-1 max-w-2xl text-xs text-slate-500">
              {t("evalExtended.workbenchAddEvaluationsHint")}
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400">
            <X size={18} />
          </button>
        </header>
        <div className="space-y-4 p-6">
          <label className="relative block">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("evalExtended.searchEval")}
              className="h-11 w-full rounded-lg border border-slate-200 pl-10 pr-3 text-sm outline-none focus:border-[color:var(--agro-primary)]"
            />
          </label>
          <div className="grid grid-cols-5 overflow-hidden rounded-lg border border-slate-200">
            {(["all", "prompt", "context", "response", "text"] as const).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setCategory(item)}
                className={`px-3 py-2 text-xs font-bold ${
                  category === item
                    ? "bg-[color:var(--agro-primary)] text-white"
                    : "border-l border-slate-200 text-slate-500 first:border-0"
                }`}
              >
                {item === "all" ? t("evalExtended.configAllCategories") : item}
              </button>
            ))}
          </div>
          <div className="grid max-h-[48vh] gap-3 overflow-auto pr-1 md:grid-cols-2">
            {filtered.map((metric) => {
              const checked = draft.includes(metric.id);
              return (
                <button
                  key={metric.id}
                  type="button"
                  onClick={() =>
                    setDraft((current) =>
                      checked
                        ? current.filter((id) => id !== metric.id)
                        : [...current, metric.id],
                    )
                  }
                  className={`rounded-xl border p-4 text-left transition ${
                    checked
                      ? "border-[color:var(--agro-primary)] bg-[color:var(--agro-pill)]"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <p className="text-[10px] font-bold uppercase text-slate-400">
                    {metric.category === "context"
                      ? t("evalExtended.workbenchCategoryContext")
                      : metric.category === "response"
                        ? t("evalExtended.workbenchCategoryResponse")
                        : metric.category === "prompt"
                          ? t("evalExtended.workbenchCategoryPrompt")
                          : t("evalExtended.workbenchCategoryText")}
                  </p>
                  <h3 className="mt-1 text-sm font-bold text-slate-900">{metric.name}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-slate-500">
                    {metric.description}
                  </p>
                  <span className="mt-3 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
                    {metric.engine}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
        <footer className="flex justify-end gap-2 border-t border-slate-200 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-bold text-slate-600"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            disabled={!draft.length}
            onClick={() => onNext(draft)}
            className="flex items-center gap-2 rounded-lg bg-[color:var(--agro-primary)] px-4 py-2 text-xs font-bold text-white disabled:opacity-40"
          >
            {t("evalExtended.configure", { n: draft.length || "" })}
            <ChevronRight size={15} />
          </button>
        </footer>
      </div>
    </div>
  );
}

function SchemaDrawer({
  mapping,
  schemaColumns,
  onClose,
}: {
  mapping: Record<string, SchemaField>;
  schemaColumns: { id: SchemaField; label: string }[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-lg rounded-xl bg-white p-5 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-extrabold text-slate-900">
            <Table2 size={16} /> {t("evalExtended.workbenchSchemaTitle")}
          </h2>
          <button type="button" onClick={onClose} className="text-slate-400">
            <X size={18} />
          </button>
        </div>
        <ul className="mt-4 space-y-2 text-sm">
          {Object.entries(mapping).map(([field, column]) => (
            <li
              key={field}
              className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2"
            >
              <span className="font-semibold text-slate-600">{field}</span>
              <span className="text-slate-800">
                {schemaColumns.find((item) => item.id === column)?.label}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function RowDrawer({
  test,
  answer,
  retrieval,
  metrics,
  values,
  thresholds,
  onClose,
  t,
}: {
  test: TestItem;
  answer?: AnswerPayload;
  retrieval?: RetrievalPayload;
  metrics: AgroMetric[];
  values: Record<string, number | null>;
  thresholds: Record<string, { operator: "gte" | "lte"; value: number }>;
  onClose: () => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  const feedback = String(
    (answer?.evaluation as Record<string, unknown> | undefined)?.feedback ||
      answer?.feedback ||
      "",
  );
  const chunks = answer?.retrieved_chunks ?? [];
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30" onClick={onClose}>
      <aside
        className="h-full w-full max-w-xl overflow-auto bg-white p-5 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] text-slate-400">eval-{String(test.id).padStart(4, "0")}</p>
            <h2 className="mt-1 text-base font-extrabold text-slate-900">{test.question}</h2>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400">
            <X size={18} />
          </button>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-slate-700">
          {String(answer?.generated_answer || t("evalExtended.noAnswerYet"))}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {metrics.map((metric) => (
            <div key={metric.id} className="rounded-lg border border-slate-200 px-3 py-2">
              <p className="text-[10px] font-bold uppercase text-slate-400">{metric.name}</p>
              <div className="mt-1">
                <ScorePill
                  value={values[metric.id]}
                  invert={metric.invert}
                  threshold={thresholds[metric.id]?.value ?? metric.defaultThreshold}
                />
              </div>
            </div>
          ))}
        </div>
        {feedback && (
          <p className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">{feedback}</p>
        )}
        <h3 className="mt-5 text-xs font-bold uppercase text-slate-400">
          {t("evalExtended.referenceAnswer")}
        </h3>
        <p className="mt-1 text-sm text-slate-600">{test.reference_answer}</p>
        {chunks.length > 0 && (
          <>
            <h3 className="mt-5 text-xs font-bold uppercase text-slate-400">
              {t("evalExtended.retrievedContext")}
            </h3>
            <ul className="mt-2 space-y-2">
              {chunks.slice(0, 4).map((chunk, index) => (
                <li key={index} className="rounded-lg border border-slate-100 p-2 text-xs text-slate-600">
                  {String(chunk.content || "").slice(0, 280)}
                </li>
              ))}
            </ul>
          </>
        )}
        {retrieval?.retrieval && (
          <p className="mt-4 text-[11px] text-slate-400">
            MRR {formatScore(toUnit(Number((retrieval.retrieval as Record<string, number>).mrr)))} ·
            nDCG {formatScore(toUnit(Number((retrieval.retrieval as Record<string, number>).ndcg)))}
          </p>
        )}
      </aside>
    </div>
  );
}
