import { useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import api from "@/api";
import { queryKeys } from "@/lib/queryKeys";
import { useKnowledgeBases } from "@/hooks/useCachedApi";
import { useOrganization } from "@/context/OrganizationContext";
import { useTranslation } from "@/i18n/I18nProvider";
import { categoryLabel } from "@/components/evaluation/labels";

export type DistanceMetric = "cosine" | "euclidean" | "manhattan";

const CATEGORY_OPTIONS = [
  "fitosanitario",
  "posei",
  "pac",
  "normativa",
  "parcelas",
  "cadena_frio",
  "sat",
  "sigpac",
  "bcam",
  "out_of_knowledge",
  "general",
];

type RetrievedChunk = {
  id: string;
  rank: number;
  title: string;
  description: string;
  content: string;
  score: number;
  distance: number | null;
  flag_different_info?: boolean;
  flag_out_of_knowledge?: boolean;
};

function parseKeywords(value: string): string[] {
  return value
    .split(/[,;\n]+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 1);
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function normalize(value: string) {
  return value.toLocaleLowerCase();
}

function HighlightedText({
  text,
  keywords,
}: {
  text: string;
  keywords: string[];
}) {
  const needles = keywords.map((item) => item.trim()).filter((item) => item.length > 1);
  if (!needles.length || !text) return <>{text}</>;
  const re = new RegExp(`(${needles.map(escapeRegExp).join("|")})`, "gi");
  const nodes: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  let index = 0;
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    nodes.push(
      <mark key={index} className="rounded bg-amber-200 px-0.5 text-amber-950">
        {match[0]}
      </mark>,
    );
    index += 1;
    last = match.index + match[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return <>{nodes}</>;
}

function liveIrMetrics(keywords: string[], chunks: RetrievedChunk[]) {
  const needles = keywords.filter(Boolean);
  if (!needles.length) return null;
  const texts = chunks.map(
    (chunk) => `${chunk.title || ""} ${chunk.description || ""} ${chunk.content || ""}`,
  );
  const ranks = needles.map((keyword) => {
    const needle = normalize(keyword);
    const rank = texts.findIndex((text) => normalize(text).includes(needle));
    return rank >= 0 ? rank + 1 : null;
  });
  const found = ranks.filter((rank): rank is number => rank != null);
  const mrr =
    needles.length === 0
      ? 0
      : found.reduce((sum, rank) => sum + 1 / rank, 0) / needles.length;
  const coverage = needles.length ? (found.length / needles.length) * 100 : 0;
  const ndcg =
    needles.length === 0
      ? 0
      : found.reduce((sum, rank) => sum + 1 / Math.log2(rank + 1), 0) /
        needles.reduce((sum, _, index) => sum + 1 / Math.log2(index + 2), 0);
  return {
    mrr,
    ndcg: Number.isFinite(ndcg) ? ndcg : 0,
    coverage,
    found: found.length,
    total: needles.length,
  };
}

export default function AnnotatePanel() {
  const { t } = useTranslation();
  const { selectedOrg } = useOrganization();
  const qc = useQueryClient();
  const { data: kbList } = useKnowledgeBases(selectedOrg?.id);
  const knowledgeBases = kbList ?? [];

  const distanceMetrics = useMemo(
    () =>
      [
        {
          value: "cosine" as const,
          label: t("evalExtended.metricCosine"),
          description: t("evalExtended.cosineDesc"),
        },
        {
          value: "euclidean" as const,
          label: t("evalExtended.metricEuclidean"),
          description: t("evalExtended.euclideanDesc"),
        },
        {
          value: "manhattan" as const,
          label: t("evalExtended.metricManhattan"),
          description: t("evalExtended.manhattanDesc"),
        },
      ] as const,
    [t],
  );

  const [knowledgeBaseId, setKnowledgeBaseId] = useState("");
  const [distanceMetric, setDistanceMetric] = useState<DistanceMetric>("cosine");
  const [question, setQuestion] = useState("");
  const [keywordsInput, setKeywordsInput] = useState("");
  const [referenceAnswer, setReferenceAnswer] = useState("");
  const [category, setCategory] = useState("general");
  const [chunks, setChunks] = useState<RetrievedChunk[]>([]);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const keywords = useMemo(() => parseKeywords(keywordsInput), [keywordsInput]);
  const preview = useMemo(() => liveIrMetrics(keywords, chunks), [keywords, chunks]);
  const selected = chunks.find((chunk) => chunk.id === selectedChunkId);
  const outOfKnowledge =
    selected?.flag_out_of_knowledge ||
    chunks.some((chunk) => chunk.flag_out_of_knowledge);

  const metricLabel = (metric: DistanceMetric) =>
    distanceMetrics.find((item) => item.value === metric)?.label ?? metric;

  const search = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!question.trim()) return;
    setSearching(true);
    setChunks([]);
    setSelectedChunkId(null);
    setError(null);
    setMessage(null);
    try {
      const response = await api.post<{ chunks: RetrievedChunk[] }>(
        "/chat/simulator/search",
        {
          question: question.trim(),
          knowledge_base_id: knowledgeBaseId || undefined,
          evaluation_mode: true,
          distance_metric: distanceMetric,
        },
      );
      setChunks(response.data?.chunks ?? []);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          t("evalExtended.retrieveFailed"),
      );
    } finally {
      setSearching(false);
    }
  };

  const toggleFlag = (
    chunkId: string,
    flag: "flag_different_info" | "flag_out_of_knowledge",
  ) => {
    setChunks((prev) =>
      prev.map((chunk) =>
        chunk.id === chunkId ? { ...chunk, [flag]: !chunk[flag] } : chunk,
      ),
    );
  };

  const save = async () => {
    if (!question.trim() || (!selectedChunkId && !outOfKnowledge)) {
      setError(t("evalExtended.selectChunkOrOok"));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.post("/chat/simulator/save-dataset", {
        question: question.trim(),
        selected_chunk_id: selectedChunkId,
        selected_chunk_ids: selectedChunkId ? [selectedChunkId] : [],
        keywords,
        reference_answer: referenceAnswer.trim() || null,
        category,
        flags: {
          different_info: selected?.flag_different_info || false,
          out_of_knowledge: Boolean(outOfKnowledge),
        },
      });
      setMessage(t("evalExtended.annotateSaved"));
      setQuestion("");
      setKeywordsInput("");
      setReferenceAnswer("");
      setChunks([]);
      setSelectedChunkId(null);
      await qc.invalidateQueries({ queryKey: queryKeys.evaluationTests });
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          t("evalExtended.annotateSaveFailed"),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-bold text-slate-900">
          {t("evalExtended.annotateTitle")}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          {t("evalExtended.annotateIntroFull")}
        </p>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="block text-xs font-semibold text-slate-700">
            {t("evalExtended.kbLabel")}
            <select
              value={knowledgeBaseId}
              onChange={(event) => setKnowledgeBaseId(event.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
            >
              <option value="">{t("evalExtended.allTenant")}</option>
              {knowledgeBases.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-semibold text-slate-700">
            {t("evalExtended.distanceMetric")}
            <select
              value={distanceMetric}
              onChange={(event) =>
                setDistanceMetric(event.target.value as DistanceMetric)
              }
              disabled={searching}
              className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
            >
              {distanceMetrics.map((metric) => (
                <option key={metric.value} value={metric.value}>
                  {metric.label}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-[11px] font-normal text-slate-400">
              {
                distanceMetrics.find((item) => item.value === distanceMetric)
                  ?.description
              }
            </span>
          </label>
        </div>

        <form onSubmit={search} className="mt-4 space-y-3">
          <input
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t("evalExtended.questionPlaceholder")}
            className="h-10 w-full rounded-md border border-slate-300 px-4 text-sm outline-none focus:border-blue-500"
          />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="block text-xs font-semibold text-slate-700">
              {t("evalExtended.expectedKeywords")}
              <input
                type="text"
                value={keywordsInput}
                onChange={(event) => setKeywordsInput(event.target.value)}
                placeholder={t("evalExtended.keywordsPlaceholder")}
                className="mt-1 h-10 w-full rounded-md border border-slate-300 px-3 text-sm font-normal"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-700">
              {t("evalExtended.colCategory")}
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm font-normal"
              >
                {CATEGORY_OPTIONS.map((item) => (
                  <option key={item} value={item}>
                    {categoryLabel(t, item)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block text-xs font-semibold text-slate-700">
            {t("evalExtended.referenceOptional")}
            <textarea
              value={referenceAnswer}
              onChange={(event) => setReferenceAnswer(event.target.value)}
              rows={3}
              placeholder={t("evalExtended.referencePlaceholder")}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-normal leading-5"
            />
          </label>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={searching || !question.trim()}
              className="h-10 rounded-md bg-slate-900 px-5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {searching
                ? t("evalExtended.searching")
                : t("evalExtended.retrieveChunks")}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {message}
        </div>
      )}

      {preview && chunks.length > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs">
            <div className="font-semibold uppercase text-slate-400">MRR</div>
            <div className="mt-1 text-lg font-bold text-slate-800">
              {preview.mrr.toFixed(3)}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs">
            <div className="font-semibold uppercase text-slate-400">nDCG</div>
            <div className="mt-1 text-lg font-bold text-slate-800">
              {preview.ndcg.toFixed(3)}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs">
            <div className="font-semibold uppercase text-slate-400">
              {t("evalExtended.coverage")}
            </div>
            <div className="mt-1 text-lg font-bold text-slate-800">
              {preview.coverage.toFixed(0)}%
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs">
            <div className="font-semibold uppercase text-slate-400">
              {t("evalExtended.hits")}
            </div>
            <div className="mt-1 text-lg font-bold text-slate-800">
              {preview.found}/{preview.total}
            </div>
          </div>
        </div>
      )}

      {chunks.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                {t("evalExtended.chunksTitle")}
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                {t("evalExtended.chunksIntroFull")}
              </p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
              {t("evalExtended.results", {
                count: chunks.length,
                metric: metricLabel(distanceMetric),
              })}
            </span>
          </div>

          <div className="space-y-4">
            {chunks.map((chunk) => {
              const selectedChunk = selectedChunkId === chunk.id;
              const body = chunk.description || chunk.content || "";
              return (
                <div
                  key={chunk.id}
                  className={`relative rounded-lg border p-4 ${
                    selectedChunk
                      ? "border-emerald-500 bg-emerald-50/50"
                      : "border-slate-200 bg-slate-50"
                  }`}
                >
                  <div className="absolute left-4 top-4">
                    <input
                      type="radio"
                      name="selected_chunk"
                      checked={selectedChunk}
                      onChange={() => setSelectedChunkId(chunk.id)}
                      className="h-4 w-4 accent-emerald-600"
                    />
                  </div>
                  <div className="ml-8">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-slate-200 px-2 py-0.5 text-[10px] font-bold text-slate-600">
                            #{chunk.rank}
                          </span>
                          <h4 className="text-sm font-bold text-slate-800">
                            {chunk.title || t("evalExtended.noTitle")}
                          </h4>
                        </div>
                        <p className="mt-1 text-[10px] text-slate-400">
                          ID: {chunk.id}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="block text-[9px] uppercase text-slate-400">
                          {t("evalExtended.distanceLabel")}
                        </span>
                        <span className="font-mono text-sm font-bold text-blue-600">
                          {chunk.distance != null
                            ? chunk.distance.toFixed(4)
                            : "—"}
                        </span>
                      </div>
                    </div>
                    {body && (
                      <p className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-600">
                        <HighlightedText text={body} keywords={keywords} />
                      </p>
                    )}
                    <div className="mt-3 flex flex-wrap gap-4 border-t border-slate-200/60 pt-3">
                      <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
                        <input
                          type="checkbox"
                          checked={chunk.flag_different_info || false}
                          onChange={() =>
                            toggleFlag(chunk.id, "flag_different_info")
                          }
                        />
                        {t("evalExtended.differentInfo")}
                      </label>
                      <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
                        <input
                          type="checkbox"
                          checked={chunk.flag_out_of_knowledge || false}
                          onChange={() =>
                            toggleFlag(chunk.id, "flag_out_of_knowledge")
                          }
                        />
                        {t("evalExtended.outOfKnowledgeBtn")}
                      </label>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
            <p className="text-xs text-slate-400">
              {selectedChunkId
                ? t("evalExtended.chunkSelected")
                : outOfKnowledge
                  ? t("evalExtended.markedOutOfKnowledge")
                  : t("evalExtended.selectChunkFirst")}
            </p>
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving || (!selectedChunkId && !outOfKnowledge)}
              className="rounded-md bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? t("evalExtended.saving") : t("evalExtended.validateSave")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
