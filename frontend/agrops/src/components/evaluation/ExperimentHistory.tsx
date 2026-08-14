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

function metricLabel(metric: string): string {
  if (metric === "euclidean" || metric === "l2") return "Euclídea (L2)";
  if (metric === "manhattan" || metric === "l1") return "Manhattan (L1)";
  if (metric === "inner_product") return "Producto interno";
  return "Coseno";
}

function formatWhen(iso: string): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("es-ES", {
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
            Historial experimental
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Cada fila es una corrida persistida: modelo de embeddings × métrica
            de distancia frente a Recall, MRR, nDCG y precisión. Tras reindexar
            con varios modelos, la columna Embedding muestra cuál mejora al otro.
          </p>
        </div>
        <span className="text-xs font-semibold text-slate-400">
          {runs.length} corrida{runs.length === 1 ? "" : "s"}
        </span>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Cargando historial…</p>
      ) : runs.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-slate-400">
          Aún no hay corridas guardadas. Pulsa «Guardar corrida» o «Comparar 3
          distancias» para dejar constancia ante el tribunal.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-[11px] uppercase tracking-wide text-slate-500">
                <th className="px-2 py-2 font-semibold">Fecha</th>
                <th className="px-2 py-2 font-semibold">Embedding</th>
                <th className="px-2 py-2 font-semibold">Distancia</th>
                <th className="px-2 py-2 font-semibold">Recall@1</th>
                <th className="px-2 py-2 font-semibold">MRR</th>
                <th className="px-2 py-2 font-semibold">nDCG</th>
                <th className="px-2 py-2 font-semibold">Precisión</th>
                <th className="px-2 py-2 font-semibold">Cobertura</th>
                <th className="px-2 py-2 font-semibold">Fallos</th>
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
                      {formatWhen(run.created_at)}
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
                          mejor
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
