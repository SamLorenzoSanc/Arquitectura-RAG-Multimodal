import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FlaskConical,
  MoreVertical,
  Pencil,
  Trash2,
} from "lucide-react";

import {
  DatasetChunkTable,
  chunkTitleOf,
} from "@/components/datasets/DatasetChunkCards";
import { queryKeys } from "@/lib/queryKeys";
import DatasetService from "@/services/dataset.service";
import { useTranslation } from "@/i18n/I18nProvider";
import type { RagDataset } from "@/types/dataset";

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
    } catch {
      return {};
    }
  }
  return {};
}

function errorMessage(error: unknown, fallback: string) {
  const candidate = error as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return candidate.response?.data?.detail || candidate.message || fallback;
}

function chunkFromRow(
  row: Record<string, unknown>,
  index: number,
  fallbackTitle?: string,
) {
  const metadata = asRecord(row.metadata);
  return {
    chunk_index:
      typeof metadata.chunk_index === "number" ? metadata.chunk_index : index,
    title: chunkTitleOf(row, fallbackTitle),
    headline: row.prompt,
    summary: row.expected_response,
  };
}

type Props = {
  datasetId: string;
  organizationId: string;
  onBack: () => void;
  onEdit: (dataset: RagDataset) => void;
  onDelete: (dataset: RagDataset) => void;
};

export default function DatasetWorkspace({
  datasetId,
  organizationId,
  onBack,
  onEdit,
  onDelete,
}: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const detail = useQuery({
    queryKey: queryKeys.evaluationDataset(organizationId, datasetId),
    queryFn: () => DatasetService.get(datasetId, organizationId, 100),
    enabled: Boolean(organizationId && datasetId),
  });

  const dataset = detail.data?.dataset;
  const rows = detail.data?.rows ?? [];
  const chunks = rows.map((row, index) =>
    chunkFromRow(row, index, dataset?.source_name || dataset?.name),
  );

  if (detail.isLoading) {
    return (
      <div className="h-64 animate-pulse rounded-xl border border-slate-200 bg-white" />
    );
  }
  if (detail.isError || !dataset) {
    return (
      <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
        {errorMessage(detail.error, t("datasets.notFound"))}
        <button type="button" onClick={onBack} className="ml-3 font-semibold underline">
          {t("datasets.backToCatalog")}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button
            type="button"
            onClick={onBack}
            className="mb-2 inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-[#0038A8]"
          >
            <ArrowLeft size={14} />
            {t("datasets.title")}
          </button>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {dataset.name}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {t("datasets.chunkCount", {
              count: dataset.row_count ?? chunks.length,
            })}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() =>
              navigate(`/dashboard/evaluacion?dataset=${encodeURIComponent(dataset.id)}`)
            }
            className="inline-flex items-center gap-2 rounded-lg bg-[#0038A8] px-3 py-2 text-xs font-bold text-white"
          >
            <FlaskConical size={14} />
            {t("datasets.evaluate")}
          </button>
          <div className="relative">
            <button
              type="button"
              aria-label={t("datasets.actionsAria")}
              onClick={() => setMenuOpen((open) => !open)}
              className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50"
            >
              <MoreVertical size={16} />
            </button>
            {menuOpen && (
              <div className="absolute right-0 z-20 mt-1 w-48 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    onEdit(dataset);
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  <Pencil size={14} />
                  {t("datasets.updateFields")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    onDelete(dataset);
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-red-600 hover:bg-red-50"
                >
                  <Trash2 size={14} />
                  {t("datasets.deleteDataset")}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-800">{t("datasets.chunksTitle")}</h2>
          <span className="text-[11px] text-slate-400">{t("datasets.chunksHint")}</span>
        </div>
        <DatasetChunkTable
          items={chunks}
          emptyLabel={t("datasets.chunksEmpty")}
        />
      </section>
    </div>
  );
}
