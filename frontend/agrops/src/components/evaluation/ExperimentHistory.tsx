import { useTranslation } from "@/i18n/I18nProvider";

type ExperimentRun = {
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
  status?: string;
};

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

export default function ExperimentHistory({
  runs,
  bestMrrId,
  loading,
}: {
  runs: ExperimentRun[];
  bestMrrId?: number | null;
  loading?: boolean;
}) {
  const { t, language } = useTranslation();
  const locale = language === "en" ? "en-US" : "es-ES";

  const metricLabel = (metric: string): string => {
    if (metric === "euclidean" || metric === "l2") return t("evalExtended.metricEuclidean");
    if (metric === "manhattan" || metric === "l1") return t("evalExtended.metricManhattan");
    if (metric === "inner_product") return t("evalExtended.metricInnerProduct");
    return t("evalExtended.metricCosine");
  };

  const winner =
    bestMrrId ??
    (runs.length
      ? runs.reduce((best, run) => (run.mrr > best.mrr ? run : best)).id
      : null);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            {t("evalExtended.historyTitle")}
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            {t("evalExtended.historyIntro")}
          </p>
        </div>
        <span className="text-xs font-semibold text-slate-400">
          {t("evalExtended.runCount", { count: runs.length })}
        </span>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">{t("evalExtended.loadingHistory")}</p>
      ) : runs.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-slate-400">
          {t("evalExtended.noRunsYet")}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-[11px] uppercase tracking-wide text-slate-500">
                <th className="px-2 py-2 font-semibold">{t("evalExtended.colDate")}</th>
                <th className="px-2 py-2 font-semibold">{t("evalExtended.colEmbedding")}</th>
                <th className="px-2 py-2 font-semibold">{t("evalExtended.colDistance")}</th>
                <th className="px-2 py-2 font-semibold">{t("evalExtended.colRecall1")}</th>
                <th className="px-2 py-2 font-semibold">{t("evalExtended.colMrr")}</th>
                <th className="px-2 py-2 font-semibold">nDCG</th>
                <th className="px-2 py-2 font-semibold">{t("evalExtended.colPrecision")}</th>
                <th className="px-2 py-2 font-semibold">{t("evalExtended.coverage")}</th>
                <th className="px-2 py-2 font-semibold">{t("evalExtended.colFailures")}</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const isBest = winner === run.id;
                return (
                  <tr
                    key={`${run.id}-${run.created_at}`}
                    className={
                      isBest
                        ? "bg-emerald-50 font-semibold text-emerald-900"
                        : "text-slate-700"
                    }
                  >
                    <td className="whitespace-nowrap px-2 py-2">
                      {formatWhen(run.created_at, locale)}
                    </td>
                    <td className="px-2 py-2 font-mono text-xs">
                      {run.embedding_model}
                    </td>
                    <td className="px-2 py-2">
                      {metricLabel(run.distance_metric)}
                    </td>
                    <td className="px-2 py-2">{pct(run.recall_1)}</td>
                    <td className="px-2 py-2">
                      {pct(run.mrr)}
                      {isBest ? (
                        <span className="ml-1 text-[10px] uppercase text-emerald-700">
                          {t("evalExtended.best")}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-2 py-2">{pct(run.ndcg)}</td>
                    <td className="px-2 py-2">{pct(run.precision_at_k ?? run.accuracy)}</td>
                    <td className="px-2 py-2">{pct(run.keyword_coverage)}</td>
                    <td className="px-2 py-2">{run.failures}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
