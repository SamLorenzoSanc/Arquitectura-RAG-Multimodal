import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/context";
import { queryKeys } from "@/lib/app";
import { EvaluationService } from "@/services";
import { useTranslation } from "@/i18n/I18nProvider";
import { categoryLabel } from "@/components/evaluation/labels";
import FrozenRagConfigBar, {
  useSyncedTemperature,
} from "@/components/evaluation/FrozenRagConfigBar";
import type {
  EvaluationBankItem,
  ProbeChunk,
  RetrievalExperimentRun,
} from "@/types";

type ExpectedChoice = "chunk" | "other" | "out_of_kb";

function apiError(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

function pct(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return "—";
  }
  const raw = Number(value);
  const scaled = raw <= 1 ? raw * 100 : raw;
  return `${Math.round(scaled)}%`;
}

function formatWhen(iso: string, locale: string): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(locale, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function formatDuration(ms?: number): string {
  if (!ms || ms <= 0) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return rest ? `${minutes}m ${rest}s` : `${minutes}m`;
}

function datasetLabel(run: RetrievalExperimentRun): string {
  const params = run.parameters || {};
  if (typeof params.dataset_label === "string" && params.dataset_label) {
    return params.dataset_label;
  }
  return String(run.dataset_size ?? "—");
}

function falsePositivePct(run: RetrievalExperimentRun): string {
  const count = Number(run.false_positives ?? 0);
  const size = Number(run.dataset_size || 0);
  if (!size) return pct(0);
  return pct(count / size);
}

function formatDistance(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return Number(value).toFixed(3);
}

function expectedLabel(
  t: (key: string, params?: Record<string, string | number>) => string,
  item: EvaluationBankItem,
): string {
  if (item.out_of_knowledge) return t("evalExtended.outOfKnowledge");
  if (item.different_info) return t("evalExtended.otherAnswerShort");
  if (item.expected_chunk_ids?.length) {
    return t("evalExtended.chunksCount", {
      count: item.expected_chunk_ids.length,
    });
  }
  return t("evalExtended.unlabeled");
}

function sourceLabel(
  t: (key: string) => string,
  item: EvaluationBankItem,
): string {
  if (item.source === "annotated") return t("evalExtended.validated");
  if (item.source === "merged") return t("evalExtended.mergedValidation");
  if (item.source === "hitl" || item.source === "document") {
    return item.validated === false
      ? t("evalExtended.docPending")
      : t("evalExtended.docValidated");
  }
  if (item.source === "file") return t("evalExtended.imported");
  return item.source || "—";
}

export default function SimpleRetrievalEval({
  onOpenLab,
  hideTitle,
}: {
  onOpenLab?: () => void;
  hideTitle?: boolean;
}) {
  const { t, language } = useTranslation();
  const locale = language === "en" ? "en-US" : "es-ES";
  const { selectedOrg } = useOrganization();
  const orgId = selectedOrg?.id ?? "";
  const kbId = null;
  const qc = useQueryClient();

  const { temperature, setTemperature } = useSyncedTemperature();

  const historyQuery = useQuery({
    queryKey: queryKeys.evaluationHistory(orgId),
    queryFn: () => EvaluationService.retrievalHistory(orgId),
    enabled: Boolean(orgId),
  });

  const modelsQuery = useQuery({
    queryKey: queryKeys.evaluationEmbeddingModels(orgId),
    queryFn: () => EvaluationService.embeddingModels(orgId),
    enabled: Boolean(orgId),
    staleTime: 30_000,
  });

  const bankQuery = useQuery({
    queryKey: [...queryKeys.evaluationTests, orgId],
    queryFn: () => EvaluationService.listQuestionBank(orgId),
    enabled: Boolean(orgId),
  });

  const indexedModels = modelsQuery.data?.indexed ?? [];
  const [lastRunIds, setLastRunIds] = useState<number[]>([]);
  const [bestRunId, setBestRunId] = useState<number | null>(null);
  const [evalNote, setEvalNote] = useState<string | null>(null);

  const runEval = useMutation({
    mutationFn: () =>
      EvaluationService.runRetrievalEvaluation(orgId, kbId, temperature),
    onSuccess: async (result) => {
      const runs = result.runs ?? [];
      setLastRunIds(runs.map((run) => run.id));
      setBestRunId(result.best_mrr_id ?? null);
      const winner = runs.find((run) => run.id === result.best_mrr_id) ?? runs[0];
      setEvalNote(
        winner
          ? t("evalExtended.evalIndexedSummary", {
              count: runs.length,
              model: winner.embedding_model || winner.model_name || "—",
              mrr: Number(winner.mrr ?? 0).toFixed(3),
            })
          : result.note || null,
      );
      await qc.invalidateQueries({ queryKey: queryKeys.evaluationHistory(orgId) });
    },
  });

  const [question, setQuestion] = useState("");
  const [chunks, setChunks] = useState<ProbeChunk[]>([]);
  const [probed, setProbed] = useState(false);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);
  const [expected, setExpected] = useState<ExpectedChoice | null>(null);
  const [searching, setSearching] = useState(false);
  const [saving, setSaving] = useState(false);
  const [probeError, setProbeError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const canSave = useMemo(() => {
    if (!question.trim() || !probed) return false;
    if (expected === "chunk") return Boolean(selectedChunkId);
    return expected === "other" || expected === "out_of_kb";
  }, [expected, probed, question, selectedChunkId]);

  const probe = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!question.trim() || !orgId) return;
    setSearching(true);
    setProbeError(null);
    setSaveMessage(null);
    setChunks([]);
    setSelectedChunkId(null);
    setExpected(null);
    setProbed(false);
    try {
      const results = await EvaluationService.probeRetrieval(
        orgId,
        question.trim(),
        kbId,
      );
      setChunks(results);
      setProbed(true);
    } catch (error) {
      setProbeError(apiError(error, t("evalExtended.probeFailed")));
    } finally {
      setSearching(false);
    }
  };

  const selectChunk = (chunkId: string) => {
    setSelectedChunkId(chunkId);
    setExpected("chunk");
    setSaveMessage(null);
  };

  const save = async () => {
    if (!canSave || !orgId) return;
    setSaving(true);
    setProbeError(null);
    try {
      await EvaluationService.saveValidatedQuestion(orgId, {
        question: question.trim(),
        selected_chunk_ids:
          expected === "chunk" && selectedChunkId ? [selectedChunkId] : [],
        flags: {
          different_info: expected === "other",
          out_of_knowledge: expected === "out_of_kb",
        },
      });
      setSaveMessage(t("evalExtended.questionSaved"));
      setQuestion("");
      setChunks([]);
      setProbed(false);
      setSelectedChunkId(null);
      setExpected(null);
      await qc.invalidateQueries({
        queryKey: [...queryKeys.evaluationTests, orgId],
      });
      await qc.invalidateQueries({ queryKey: queryKeys.evaluationTests });
    } catch (error) {
      setProbeError(apiError(error, t("evalExtended.saveQuestionFailed")));
    } finally {
      setSaving(false);
    }
  };

  const runs = historyQuery.data ?? [];
  const tests = bankQuery.data ?? [];

  return (
    <div className="flex flex-col gap-6 pb-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            {hideTitle ? null : (
              <h1 className="text-2xl font-extrabold text-slate-900">
                {t("evalExtended.retrievalEvalTitle")}
              </h1>
            )}
            <p className={`max-w-3xl text-sm text-slate-500 ${hideTitle ? "" : "mt-1"}`}>
              {t("evalExtended.retrievalEvalIntroFull")}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => runEval.mutate()}
              disabled={!orgId || runEval.isPending}
              className="h-10 rounded-lg bg-[color:var(--agro-primary)] px-4 text-sm font-semibold text-white hover:bg-[color:var(--agro-primary-hover)] disabled:opacity-50"
            >
              {runEval.isPending
                ? indexedModels.length > 1
                  ? t("evalExtended.runEvaluatingIndexed", {
                      count: indexedModels.length,
                    })
                  : t("evalExtended.runEvaluating")
                : t("evalExtended.runEval")}
            </button>
            <button
              type="button"
              onClick={() => historyQuery.refetch()}
              className="text-sm font-semibold text-[color:var(--agro-primary)] hover:underline"
            >
              {t("evalExtended.refresh")}
            </button>
            {onOpenLab && (
              <button
                type="button"
                onClick={onOpenLab}
                className="text-xs font-semibold text-slate-400 hover:text-slate-600"
              >
                {t("evalExtended.advancedLab")}
              </button>
            )}
          </div>
        </div>

        <div className="mt-4">
          <FrozenRagConfigBar
            temperature={temperature}
            onTemperatureChange={setTemperature}
          />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
            {t("evalExtended.indexedModelsLabel")}
          </span>
          {indexedModels.length ? (
            indexedModels.map((model) => (
              <span
                key={model}
                className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800"
              >
                {model}
              </span>
            ))
          ) : (
            <span className="text-xs text-slate-500">
              {t("evalExtended.indexedModelsNone")}
            </span>
          )}
        </div>

        {evalNote && !runEval.isPending && (
          <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {evalNote}
          </p>
        )}

        {runEval.isError && (
          <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {apiError(runEval.error, t("evalExtended.evalFailed"))}
          </p>
        )}

        <div className="mt-5 overflow-x-auto">
          {historyQuery.isLoading ? (
            <p className="text-sm text-slate-500">
              {t("evalExtended.loadingHistory")}
            </p>
          ) : runs.length === 0 ? (
            <p className="text-sm text-slate-500">
              {t("evalExtended.noRunsStartHint")}
            </p>
          ) : (
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-[11px] font-bold uppercase tracking-wide text-slate-400">
                  <th className="py-2 pr-3">{t("evalExtended.colDate")}</th>
                  <th className="py-2 pr-3">{t("evalExtended.colModel")}</th>
                  <th className="py-2 pr-3">{t("evalExtended.colTemp")}</th>
                  <th className="py-2 pr-3">{t("evalExtended.colDataset")}</th>
                  <th className="py-2 pr-3">{t("evalExtended.colRecall1")}</th>
                  <th className="py-2 pr-3">{t("evalExtended.colRecallK")}</th>
                  <th className="py-2 pr-3">{t("evalExtended.colMrr")}</th>
                  <th className="py-2 pr-3">
                    {t("evalExtended.colFalsePositives")}
                  </th>
                  <th className="py-2 pr-3">{t("evalExtended.colFailures")}</th>
                  <th className="py-2">{t("evalExtended.colDuration")}</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => {
                  const isLatest = lastRunIds.includes(run.id);
                  const isBest = bestRunId === run.id;
                  return (
                  <tr
                    key={run.id}
                    className={`border-b border-slate-100 last:border-0 ${
                      isBest
                        ? "bg-emerald-50/80"
                        : isLatest
                          ? "bg-slate-50"
                          : ""
                    }`}
                  >
                    <td className="py-3 pr-3 text-slate-600">
                      {formatWhen(run.created_at, locale)}
                    </td>
                    <td className="py-3 pr-3 font-medium text-slate-800">
                      {run.embedding_model || run.model_name || "—"}
                      {isBest && lastRunIds.length > 1 ? (
                        <span className="ml-2 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-800">
                          MRR
                        </span>
                      ) : null}
                    </td>
                    <td className="py-3 pr-3 text-slate-600">
                      {typeof run.parameters?.temperature === "number"
                        ? Number(run.parameters.temperature).toFixed(1)
                        : "—"}
                    </td>
                    <td className="py-3 pr-3 text-slate-600">
                      {datasetLabel(run)}
                    </td>
                    <td className="py-3 pr-3 font-bold text-slate-900">
                      {pct(run.recall_1)}
                    </td>
                    <td className="py-3 pr-3 font-bold text-slate-900">
                      {pct(run.recall_k)}
                    </td>
                    <td className="py-3 pr-3 text-slate-800">
                      {Number(run.mrr ?? 0).toFixed(3)}
                    </td>
                    <td className="py-3 pr-3 text-slate-600">
                      {falsePositivePct(run)}
                    </td>
                    <td className="py-3 pr-3 text-slate-600">{run.failures}</td>
                    <td className="py-3 text-slate-600">
                      {formatDuration(run.duration_ms)}
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-extrabold text-slate-900">
          {t("evalExtended.probeTitle")}
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-slate-500">
          {t("evalExtended.probeIntroFull")}
        </p>

        <form onSubmit={probe} className="mt-4 flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t("evalExtended.probePlaceholder")}
            className="h-11 min-w-0 flex-1 rounded-lg border border-slate-300 px-4 text-sm outline-none focus:border-[color:var(--agro-primary)]"
          />
          <button
            type="submit"
            disabled={searching || !question.trim() || !orgId}
            className="h-11 shrink-0 rounded-lg bg-[color:var(--agro-primary)] px-5 text-sm font-semibold text-white hover:bg-[color:var(--agro-primary-hover)] disabled:opacity-50"
          >
            {searching ? t("evalExtended.probing") : t("evalExtended.probe")}
          </button>
        </form>

        {probeError && (
          <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {probeError}
          </p>
        )}
        {saveMessage && (
          <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {saveMessage}
          </p>
        )}

        {probed && chunks.length === 0 && (
          <p className="mt-4 text-sm text-slate-500">
            {t("evalExtended.noChunksRetrievedHint")}
          </p>
        )}

        {chunks.length > 0 && (
          <ul className="mt-5 space-y-3">
            {chunks.map((chunk) => {
              const checked =
                expected === "chunk" && selectedChunkId === chunk.id;
              return (
                <li key={`${chunk.rank}-${chunk.id}`}>
                  <label className="flex cursor-pointer gap-3 rounded-xl border border-slate-200 px-4 py-3 hover:border-slate-300">
                    <input
                      type="radio"
                      name="expected-chunk"
                      className="mt-1.5"
                      checked={checked}
                      onChange={() => selectChunk(chunk.id)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-start justify-between gap-3">
                        <span className="font-bold text-slate-900">
                          #{chunk.rank} {chunk.title}
                        </span>
                        <span className="shrink-0 text-xs font-semibold text-slate-500">
                          {t("evalExtended.distance")}{" "}
                          {formatDistance(chunk.distance)}
                        </span>
                      </span>
                      <span className="mt-1 block line-clamp-3 text-sm text-slate-500">
                        {chunk.description || chunk.content}
                      </span>
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        )}

        {probed && (
          <div className="mt-6 border-t border-slate-100 pt-5">
            <h3 className="text-xs font-bold uppercase tracking-wide text-slate-400">
              {t("evalExtended.expectedChunk")}
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              {t("evalExtended.expectedHintOr")}
            </p>
            <div className="mt-3 space-y-2">
              <label className="flex cursor-pointer items-center gap-3 text-sm text-slate-700">
                <input
                  type="radio"
                  name="expected-chunk"
                  checked={expected === "other"}
                  onChange={() => {
                    setExpected("other");
                    setSelectedChunkId(null);
                  }}
                />
                {t("evalExtended.otherAnswer")}
              </label>
              <label className="flex cursor-pointer items-center gap-3 text-sm text-slate-700">
                <input
                  type="radio"
                  name="expected-chunk"
                  checked={expected === "out_of_kb"}
                  onChange={() => {
                    setExpected("out_of_kb");
                    setSelectedChunkId(null);
                  }}
                />
                {t("evalExtended.outOfKb")}
              </label>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => void save()}
                disabled={!canSave || saving}
                className="h-10 rounded-lg bg-[color:var(--agro-primary)] px-4 text-sm font-semibold text-white hover:bg-[color:var(--agro-primary-hover)] disabled:opacity-50"
              >
                {saving
                  ? t("evalExtended.saving")
                  : t("evalExtended.saveQuestion")}
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-extrabold text-slate-900">
              {t("evalExtended.bankTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {t("evalExtended.bankIntroFull")}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-600">
              {tests.length === 1
                ? t("evalExtended.questionCountOne", { count: tests.length })
                : t("evalExtended.questionCount", { count: tests.length })}
            </span>
            <button
              type="button"
              onClick={() => bankQuery.refetch()}
              className="text-sm font-semibold text-[color:var(--agro-primary)] hover:underline"
            >
              {t("evalExtended.refresh")}
            </button>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          {bankQuery.isLoading ? (
            <p className="text-sm text-slate-500">
              {t("evalExtended.loadingBank")}
            </p>
          ) : tests.length === 0 ? (
            <p className="text-sm text-slate-500">
              {t("evalExtended.bankEmptyApiHint")}
            </p>
          ) : (
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-[11px] font-bold uppercase tracking-wide text-slate-400">
                  <th className="py-2 pr-3">{t("evalExtended.colNumber")}</th>
                  <th className="py-2 pr-3">{t("evalExtended.question")}</th>
                  <th className="py-2 pr-3">{t("evalExtended.colExpected")}</th>
                  <th className="py-2 pr-3">{t("evalExtended.colCategory")}</th>
                  <th className="py-2">{t("evalExtended.source")}</th>
                </tr>
              </thead>
              <tbody>
                {tests.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="py-3 pr-3 text-slate-400">{item.id}</td>
                    <td className="py-3 pr-3 font-medium text-slate-800">
                      {item.question}
                    </td>
                    <td className="py-3 pr-3 text-slate-600">
                      {expectedLabel(t, item)}
                    </td>
                    <td className="py-3 pr-3 text-slate-600">
                      {categoryLabel(t, item.category)}
                    </td>
                    <td className="py-3 text-slate-500">
                      <span className="block">{sourceLabel(t, item)}</span>
                      {(item.source_file || item.page) && (
                        <span className="mt-0.5 block text-[11px] text-slate-400">
                          {[item.source_file?.replace(/^knowledge-base\//, ""), item.page]
                            .filter(Boolean)
                            .join(" · ")}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
