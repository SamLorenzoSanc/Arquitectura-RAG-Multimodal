import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Layers, RefreshCw, X } from "lucide-react";

import { useTranslation } from "@/i18n/I18nProvider";
import DocumentService from "@/services/document.service";
import type { DocumentChunk, DocumentItem } from "@/types/document";

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const TONES = [
  "bg-blue-50 ring-blue-200",
  "bg-amber-50 ring-amber-200",
  "bg-emerald-50 ring-emerald-200",
  "bg-violet-50 ring-violet-200",
  "bg-sky-50 ring-sky-200",
];

function formatBytes(size?: number) {
  if (!size || size <= 0) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentChunksDrawer({
  document,
  onClose,
}: {
  document: DocumentItem;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"cards" | "flow">("cards");
  const [openId, setOpenId] = useState<string | null>(null);
  const [reprocessing, setReprocessing] = useState(false);
  const [progressMsg, setProgressMsg] = useState<string | null>(null);
  const [reprocessError, setReprocessError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["documents", document.id, "chunks"],
    queryFn: () => DocumentService.chunks(document.id, document.knowledge_base_id),
  });

  async function onReprocess() {
    const kb = document.knowledge_base_id;
    if (!kb || reprocessing) return;
    setReprocessing(true);
    setReprocessError(null);
    setProgressMsg(t("documentsDrawer.ocrExtracting"));
    try {
      await DocumentService.reprocess(kb, document.id);
      for (let i = 0; i < 800; i += 1) {
        const snap = await DocumentService.progress(kb, document.id);
        setProgressMsg(snap.message || t("documentsDrawer.reprocessing"));
        if (snap.status === "completed") break;
        if (snap.status === "failed") {
          throw new Error(snap.error || snap.message || t("documentsDrawer.reprocessFailed"));
        }
        await sleep(500);
      }
      await query.refetch();
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    } catch (exc) {
      const detail = (exc as { response?: { data?: { detail?: string } } }).response
        ?.data?.detail;
      setReprocessError(detail || (exc as Error).message || t("documentsDrawer.reprocessError"));
    } finally {
      setReprocessing(false);
    }
  }
  const chunks = query.data?.chunks ?? [];
  const averageOverlap = useMemo(() => {
    const values = chunks.map((item) => item.overlap_prev).filter((value) => value > 0);
    if (!values.length) return 0;
    return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
  }, [chunks]);

  const chunkCount = query.data?.chunk_count ?? document.chunks ?? 0;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30" onClick={onClose}>
      <aside
        className="flex h-full w-full max-w-3xl flex-col bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-[color:var(--agro-primary)]">
              <Layers size={13} />
              {t("documentsDrawer.title")}
            </p>
            <h2 className="mt-1 truncate text-lg font-extrabold text-slate-900">
              {query.data?.title || document.filename || document.title}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {document.knowledge_base_name ? `${document.knowledge_base_name} · ` : ""}
              {chunkCount} {t("documentsDrawer.chunks")}
              {averageOverlap
                ? ` · ${t("documentsDrawer.avgOverlap", { n: averageOverlap })}`
                : ""}
              {formatBytes(document.size) ? ` · ${formatBytes(document.size)}` : ""}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {document.knowledge_base_id ? (
              <button
                type="button"
                disabled={reprocessing}
                onClick={() => void onReprocess()}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--agro-border)] px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                <RefreshCw size={13} className={reprocessing ? "animate-spin" : ""} />
                {reprocessing ? t("documentsDrawer.reprocessing") : t("documentsDrawer.reprocessOcr")}
              </button>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-50"
              aria-label={t("documentsDrawer.closeAria")}
            >
              <X size={18} />
            </button>
          </div>
        </header>

        <div className="flex gap-2 border-b border-slate-100 px-5 py-2">
          <button
            type="button"
            onClick={() => setTab("cards")}
            className={`rounded-md px-3 py-1.5 text-xs font-bold ${
              tab === "cards"
                ? "bg-[color:var(--agro-primary)] text-white"
                : "text-slate-500 hover:bg-slate-50"
            }`}
          >
            {t("documentsDrawer.tabChunks")}
          </button>
          <button
            type="button"
            onClick={() => setTab("flow")}
            className={`rounded-md px-3 py-1.5 text-xs font-bold ${
              tab === "flow"
                ? "bg-[color:var(--agro-primary)] text-white"
                : "text-slate-500 hover:bg-slate-50"
            }`}
          >
            {t("documentsDrawer.tabFlow")}
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
          {(progressMsg || reprocessError) && (
            <p
              className={`mb-3 rounded-lg px-3 py-2 text-xs ${
                reprocessError
                  ? "bg-rose-50 text-rose-700"
                  : "bg-amber-50 text-amber-900"
              }`}
            >
              {reprocessError || progressMsg}
            </p>
          )}
          {query.isLoading && (
            <p className="text-sm text-slate-500">{t("documentsDrawer.loadingChunks")}</p>
          )}
          {query.isError && (
            <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {t("documentsDrawer.loadError")}
            </p>
          )}
          {!query.isLoading && chunks.length === 0 && (
            <p className="rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-400">
              {t("documentsDrawer.noChunks")}
            </p>
          )}

          {tab === "cards" &&
            chunks.map((chunk, index) => (
              <ChunkCard
                key={chunk.id}
                chunk={chunk}
                index={index}
                open={openId === chunk.id || chunks.length <= 3}
                onToggle={() =>
                  setOpenId((current) => (current === chunk.id ? null : chunk.id))
                }
              />
            ))}

          {tab === "flow" && chunks.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-slate-500">
                {t("documentsDrawer.flowHint")}
              </p>
              {chunks.map((chunk, index) => {
                const overlap = chunk.overlap_prev || 0;
                const repeated = overlap > 0 ? chunk.content.slice(0, overlap) : "";
                const unique = chunk.content.slice(overlap);
                return (
                  <article
                    key={chunk.id}
                    className={`rounded-xl p-3 text-sm leading-relaxed ring-1 ${TONES[index % TONES.length]}`}
                  >
                    <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-slate-500">
                      {t("documentsDrawer.chunkN", { n: index + 1 })}
                      {overlap ? ` · ${t("documentsDrawer.overlapChars", { n: overlap })}` : ""}
                    </p>
                    {repeated ? (
                      <span className="rounded bg-amber-200/70 text-amber-950">
                        {repeated}
                      </span>
                    ) : null}
                    <span className="whitespace-pre-wrap text-slate-800">{unique}</span>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

function ChunkCard({
  chunk,
  index,
  open,
  onToggle,
}: {
  chunk: DocumentChunk;
  index: number;
  open: boolean;
  onToggle: () => void;
}) {
  const { t } = useTranslation();

  return (
    <article className={`mb-3 rounded-xl ring-1 ${TONES[index % TONES.length]}`}>
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left"
      >
        <div>
          <p className="text-sm font-bold text-slate-900">
            {t("documentsDrawer.chunkN", { n: index + 1 })}
            {chunk.headline ? ` · ${chunk.headline}` : ""}
          </p>
          <p className="mt-0.5 text-[11px] text-slate-500">
            {chunk.char_count} {t("documentsDrawer.chars")}
            {chunk.overlap_prev
              ? ` · ${t("documentsDrawer.overlapPrev", { n: chunk.overlap_prev })}`
              : ""}
            {chunk.embedding_models.length
              ? ` · ${chunk.embedding_models.join(", ")}`
              : ""}
          </p>
        </div>
        <span className="text-[11px] font-semibold text-slate-400">
          {open ? t("documentsDrawer.hide") : t("documentsDrawer.showText")}
        </span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-white/60 px-4 py-3">
          {chunk.summary ? (
            <p className="text-xs italic text-slate-500">{chunk.summary}</p>
          ) : null}
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
            {chunk.content || t("documentsDrawer.noText")}
          </p>
        </div>
      )}
    </article>
  );
}
