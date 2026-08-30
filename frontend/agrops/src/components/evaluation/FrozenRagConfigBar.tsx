import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useOrganization } from "@/context";
import { useTranslation } from "@/i18n/I18nProvider";
import { queryKeys } from "@/lib/app";
import { EvaluationService } from "@/services";
import type { RagRuntimeConfig } from "@/types";

export function useRagRuntimeConfig() {
  return useQuery({
    queryKey: ["evaluation", "runtime-config"],
    queryFn: () => EvaluationService.runtimeConfig(),
    staleTime: 60_000,
  });
}

type Props = {
  temperature?: number;
  onTemperatureChange?: (value: number) => void;
};

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] text-slate-600">
      <span className="font-semibold text-slate-500">{label}</span>
      <span className="font-bold text-slate-800">{value}</span>
    </span>
  );
}

export default function FrozenRagConfigBar({
  temperature,
  onTemperatureChange,
}: Props) {
  const { t } = useTranslation();
  const { selectedOrg } = useOrganization();
  const orgId = selectedOrg?.id ?? "";
  const { data, isLoading } = useRagRuntimeConfig();
  const modelsQuery = useQuery({
    queryKey: queryKeys.evaluationEmbeddingModels(orgId),
    queryFn: () => EvaluationService.embeddingModels(orgId),
    enabled: Boolean(orgId),
    staleTime: 30_000,
  });
  const config: RagRuntimeConfig | undefined = data;
  const shownTemp = temperature ?? config?.temperature ?? 0;
  const indexedModels = modelsQuery.data?.indexed ?? [];
  const embedModels = indexedModels.length
    ? indexedModels
    : config?.embedding_model
      ? [config.embedding_model]
      : [];

  return (
    <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-emerald-800">
            {t("evalExtended.frozenConfigTitle")}
          </p>
          <p className="mt-0.5 text-xs text-emerald-900/80">
            {config?.note || t("evalExtended.frozenConfigNote")}
          </p>
        </div>
        <label className="flex min-w-[220px] items-center gap-3 text-xs font-semibold text-slate-700">
          {t("evalExtended.temperature")}
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            disabled={!onTemperatureChange}
            value={shownTemp}
            onChange={(event) =>
              onTemperatureChange?.(Number(event.target.value))
            }
            className="h-1.5 flex-1 accent-emerald-700"
          />
          <span className="w-8 tabular-nums text-slate-900">
            {shownTemp.toFixed(1)}
          </span>
        </label>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {isLoading && (
          <span className="text-xs text-slate-500">{t("evalExtended.loadingConfig")}</span>
        )}
        {config && (
          <>
            <Chip label="LLM" value={config.generation_model} />
            {embedModels.map((model) => (
              <Chip key={model} label="embed" value={model} />
            ))}
            <Chip
              label="chunk"
              value={`${config.chunk_size_chars}/${config.chunk_overlap_chars}`}
            />
            <Chip label="k denso" value={String(config.retrieval_k)} />
            <Chip label="BM25" value={String(config.bm25_k)} />
            <Chip label="RRF" value={String(config.rrf_k)} />
            <Chip label="final k chat" value={String(config.final_k)} />
            <Chip
              label="eval k"
              value={String(config.eval_top_k ?? 3)}
            />
            <Chip
              label="reranker"
              value={config.use_reranker ? t("evalExtended.rerankerOn") : t("evalExtended.rerankerOff")}
            />
          </>
        )}
      </div>
    </div>
  );
}

export function useSyncedTemperature() {
  const { data } = useRagRuntimeConfig();
  const [temperature, setTemperature] = useState(0);
  useEffect(() => {
    if (typeof data?.temperature === "number") {
      setTemperature(data.temperature);
    }
  }, [data?.temperature]);
  return { temperature, setTemperature, config: data };
}
