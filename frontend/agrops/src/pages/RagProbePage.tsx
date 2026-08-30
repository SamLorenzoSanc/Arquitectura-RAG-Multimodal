"use client";

import { useMemo, useState, type FormEvent } from "react";
import {
  ArrowRight,
  Loader2,
  Radar,
  Search,
  Sparkles,
} from "lucide-react";

import FrozenRagConfigBar, {
  useRagRuntimeConfig,
} from "@/components/evaluation/FrozenRagConfigBar";
import { useTranslation } from "@/i18n/I18nProvider";
import { ChatService } from "@/services";

type ProbeChunk = {
  page_content?: string;
  metadata?: Record<string, unknown>;
};

type ProbeResult = {
  rewritten_query?: string | null;
  chunks?: ProbeChunk[];
  dense_original?: ProbeChunk[];
  dense_rewritten?: ProbeChunk[];
  bm25_original?: ProbeChunk[];
  bm25_rewritten?: ProbeChunk[];
  candidates?: ProbeChunk[];
  retrieval?: Record<string, unknown> | null;
};

function scoreOf(chunk: ProbeChunk): number | null {
  const m = chunk.metadata || {};
  const raw =
    m.score ??
    m.rrf_score ??
    m.cross_encoder_score ??
    m.bm25_score ??
    m.distance;
  if (typeof raw === "number") return raw;
  if (typeof raw === "string" && raw.trim() && !Number.isNaN(Number(raw))) {
    return Number(raw);
  }
  return null;
}

function sourceOf(chunk: ProbeChunk): string {
  const m = chunk.metadata || {};
  const src = m.source ?? m.title ?? m.document_id ?? m.chunk_id;
  return src != null ? String(src) : "—";
}

const EXAMPLES = [
  "¿Qué es el POSEI y a quién se aplica en Canarias?",
  "Dosis de un producto del vademécum para platanera",
  "Hojas amarillas en platanera, ¿qué reviso?",
];

export default function RagProbePage() {
  const { t } = useTranslation();
  const { data: config } = useRagRuntimeConfig();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProbeResult | null>(null);
  const [lastQuestion, setLastQuestion] = useState("");

  const stages = useMemo(() => {
    if (!result) return [];
    return [
      {
        id: "dense",
        label: t("ragProbe.stageDense"),
        count:
          (result.dense_original?.length ?? 0) +
          (result.dense_rewritten?.length ?? 0),
      },
      {
        id: "bm25",
        label: t("ragProbe.stageBm25"),
        count:
          (result.bm25_original?.length ?? 0) +
          (result.bm25_rewritten?.length ?? 0),
      },
      {
        id: "rrf",
        label: t("ragProbe.stageRrf"),
        count: result.candidates?.length ?? 0,
      },
      {
        id: "final",
        label: t("ragProbe.stageFinal"),
        count: result.chunks?.length ?? 0,
      },
    ];
  }, [result, t]);

  const runProbe = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    setLastQuestion(trimmed);
    try {
      const data = (await ChatService.retrieve(trimmed)) as ProbeResult;
      setResult(data);
    } catch (err) {
      console.error(err);
      setResult(null);
      setError(t("ragProbe.error"));
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void runProbe(question);
  };

  return (
    <div className="flex flex-col gap-5 pb-8">
      <section className="rounded-2xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[color:var(--agro-pill)] text-[color:var(--agro-primary)]">
            <Radar size={20} />
          </span>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--agro-primary)]">
              {t("ragProbe.badge")}
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              {t("ragProbe.title")}
            </h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-500">
              {t("ragProbe.intro")}
            </p>
          </div>
        </div>
      </section>

      <FrozenRagConfigBar />

      <section className="rounded-xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
        <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="min-w-0 flex-1 text-xs font-semibold text-slate-600">
            {t("ragProbe.questionLabel")}
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={t("ragProbe.placeholder")}
              disabled={loading}
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-800 outline-none focus:border-[color:var(--agro-primary)] focus:bg-white"
            />
          </label>
          <button
            type="submit"
            disabled={!question.trim() || loading}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[color:var(--agro-primary)] px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[color:var(--agro-primary-hover)] disabled:opacity-40"
          >
            {loading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Search size={16} />
            )}
            {t("ragProbe.run")}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => {
                setQuestion(ex);
                void runProbe(ex);
              }}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] font-medium text-slate-600 transition hover:border-[color:var(--agro-primary)] hover:text-[color:var(--agro-primary)]"
            >
              {ex}
            </button>
          ))}
        </div>

        {error ? (
          <p className="mt-3 text-sm font-medium text-red-600">{error}</p>
        ) : null}
      </section>

      {result ? (
        <>
          <section className="rounded-xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900">
              {t("ragProbe.pipelineTitle")}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {t("ragProbe.queryLine", { q: lastQuestion })}
            </p>
            {result.rewritten_query &&
            result.rewritten_query !== lastQuestion ? (
              <p className="mt-2 flex items-start gap-2 text-xs text-slate-700">
                <Sparkles
                  size={14}
                  className="mt-0.5 shrink-0 text-[color:var(--agro-primary)]"
                />
                <span>
                  <span className="font-semibold">
                    {t("ragProbe.rewritten")}
                  </span>{" "}
                  {result.rewritten_query}
                </span>
              </p>
            ) : (
              <p className="mt-2 text-xs text-slate-500">
                {t("ragProbe.noRewrite")}
              </p>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-2">
              {stages.map((stage, idx) => (
                <div key={stage.id} className="flex items-center gap-2">
                  <div
                    className={`rounded-lg border px-3 py-2 text-center ${
                      stage.count > 0
                        ? "border-[color:var(--agro-border)] bg-[color:var(--agro-pill)]/50"
                        : "border-slate-100 bg-slate-50"
                    }`}
                  >
                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">
                      {stage.label}
                    </p>
                    <p className="text-lg font-bold text-slate-900">
                      {stage.count}
                    </p>
                  </div>
                  {idx < stages.length - 1 ? (
                    <ArrowRight size={14} className="text-slate-300" />
                  ) : null}
                </div>
              ))}
            </div>

            <dl className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg bg-slate-50 px-3 py-2">
                <dt className="font-semibold text-slate-400">
                  {t("ragProbe.embedModel")}
                </dt>
                <dd className="font-bold text-slate-800">
                  {config?.embedding_model ?? "—"}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 px-3 py-2">
                <dt className="font-semibold text-slate-400">
                  {t("ragProbe.retrievalK")}
                </dt>
                <dd className="font-bold text-slate-800">
                  {config?.retrieval_k ?? "—"}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 px-3 py-2">
                <dt className="font-semibold text-slate-400">
                  {t("ragProbe.finalK")}
                </dt>
                <dd className="font-bold text-slate-800">
                  {config?.final_k ?? "—"}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 px-3 py-2">
                <dt className="font-semibold text-slate-400">
                  {t("ragProbe.rerank")}
                </dt>
                <dd className="font-bold text-slate-800">
                  {config?.use_reranker
                    ? t("ragProbe.on")
                    : t("ragProbe.off")}
                </dd>
              </div>
            </dl>
          </section>

          <section className="rounded-xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm">
            <h2 className="mb-3 text-sm font-bold text-slate-900">
              {t("ragProbe.chunksTitle", {
                n: result.chunks?.length ?? 0,
              })}
            </h2>
            {(result.chunks?.length ?? 0) === 0 ? (
              <p className="text-sm text-slate-500">{t("ragProbe.emptyChunks")}</p>
            ) : (
              <ol className="space-y-3">
                {(result.chunks ?? []).map((chunk, idx) => {
                  const score = scoreOf(chunk);
                  return (
                    <li
                      key={`${sourceOf(chunk)}-${idx}`}
                      className="rounded-lg border border-slate-100 bg-slate-50/80 p-3"
                    >
                      <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
                        <span className="text-xs font-bold text-[color:var(--agro-primary)]">
                          #{idx + 1} · {sourceOf(chunk)}
                        </span>
                        {score != null ? (
                          <span className="rounded-full bg-white px-2 py-0.5 font-mono text-[11px] font-semibold text-slate-600">
                            {t("ragProbe.score")}: {score.toFixed(4)}
                          </span>
                        ) : null}
                      </div>
                      <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-700">
                        {(chunk.page_content || "").slice(0, 520)}
                        {(chunk.page_content || "").length > 520 ? "…" : ""}
                      </p>
                    </li>
                  );
                })}
              </ol>
            )}
          </section>
        </>
      ) : (
        <section className="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-8 text-center">
          <p className="text-sm text-slate-500">{t("ragProbe.emptyState")}</p>
        </section>
      )}
    </div>
  );
}
