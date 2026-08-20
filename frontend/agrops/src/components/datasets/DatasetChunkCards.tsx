import { useTranslation } from "@/i18n/I18nProvider";

export type ChunkViewItem = {
  chunk_index?: number;
  title?: unknown;
  headline?: unknown;
  summary?: unknown;
};

function asText(value: unknown): string {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) {
    const parts = value
      .map((item) => asText(item))
      .filter((item) => item !== "—");
    return parts.join("\n") || "—";
  }
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

export function chunkTitleOf(
  item: Record<string, unknown>,
  fallback?: string,
): string {
  const metadata =
    item.metadata && typeof item.metadata === "object" && !Array.isArray(item.metadata)
      ? (item.metadata as Record<string, unknown>)
      : {};
  const extras =
    metadata.source_columns &&
    typeof metadata.source_columns === "object" &&
    !Array.isArray(metadata.source_columns)
      ? (metadata.source_columns as Record<string, unknown>)
      : {};
  const title =
    item.title ?? item.filename ?? metadata.filename ?? extras.filename ?? fallback;
  return asText(title);
}

export function DatasetChunkTable({
  items,
  emptyLabel,
}: {
  items: ChunkViewItem[];
  emptyLabel?: string;
}) {
  const { t } = useTranslation();
  const resolvedEmptyLabel = emptyLabel ?? t("datasets.chunksEmptyDefault");

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-400">
        {resolvedEmptyLabel}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2">{t("datasets.colIndex")}</th>
              <th className="px-3 py-2">{t("datasets.colTitle")}</th>
              <th className="px-3 py-2">{t("datasets.colHeadline")}</th>
              <th className="px-3 py-2">{t("datasets.colSummary")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700">
            {items.map((item, index) => (
              <tr key={item.chunk_index ?? index} className="align-top hover:bg-slate-50">
                <td className="whitespace-nowrap px-3 py-3 text-slate-400">
                  {item.chunk_index ?? index}
                </td>
                <td className="max-w-xs px-3 py-3 font-semibold text-slate-900">
                  {asText(item.title)}
                </td>
                <td className="max-w-md whitespace-pre-wrap px-3 py-3">
                  {asText(item.headline)}
                </td>
                <td className="max-w-lg whitespace-pre-wrap px-3 py-3 text-slate-600">
                  {asText(item.summary)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
