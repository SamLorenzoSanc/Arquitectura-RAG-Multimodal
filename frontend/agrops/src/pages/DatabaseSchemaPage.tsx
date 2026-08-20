import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ForceGraph2D from "react-force-graph-2d";
import { Database, KeyRound, RefreshCw, Search } from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { useTranslation } from "@/i18n/I18nProvider";
import { getDatabaseSchema } from "@/services/database.service";
import type { DatabaseTable } from "@/types/database";

function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  return `${(bytes / 1024 ** exponent).toFixed(exponent ? 1 : 0)} ${units[exponent]}`;
}

export default function DatabaseSchemaPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedTable, setSelectedTable] = useState<DatabaseTable | null>(null);
  const [search, setSearch] = useState("");
  const [size, setSize] = useState({ width: 0, height: 560 });

  const schemaQuery = useQuery({
    queryKey: ["database", "schema"],
    queryFn: getDatabaseSchema,
    enabled: Boolean(user?.isAdmin),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(([entry]) => {
      setSize({
        width: entry.contentRect.width,
        height: Math.max(entry.contentRect.height, 480),
      });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const visibleTables = useMemo(() => {
    const tables = schemaQuery.data?.tables ?? [];
    const normalizedSearch = search.trim().toLowerCase();
    if (!normalizedSearch) return tables;
    return tables.filter(
      (table) =>
        table.id.toLowerCase().includes(normalizedSearch) ||
        table.columns.some((column) =>
          column.name.toLowerCase().includes(normalizedSearch),
        ),
    );
  }, [schemaQuery.data, search]);

  const graphData = useMemo(() => {
    const visibleIds = new Set(visibleTables.map((table) => table.id));
    return {
      nodes: visibleTables.map((table) => ({
        id: table.id,
        name: table.name,
        schema: table.schema,
        table,
        val: Math.max(7, Math.min(18, 7 + table.columns.length / 2)),
        color: table === selectedTable ? "#f59e0b" : "#2563eb",
      })),
      links: (schemaQuery.data?.relations ?? [])
        .filter(
          (relation) =>
            visibleIds.has(relation.source_table) &&
            visibleIds.has(relation.target_table),
        )
        .map((relation) => ({
          source: relation.source_table,
          target: relation.target_table,
          label: `${relation.source_column} → ${relation.target_column}`,
        })),
    };
  }, [schemaQuery.data, selectedTable, visibleTables]);

  useEffect(() => {
    if (!graphData.nodes.length || !graphRef.current) return;
    requestAnimationFrame(() => graphRef.current?.zoomToFit(500, 70));
  }, [graphData]);

  if (!user?.isAdmin) {
    return (
      <div className="flex min-h-[420px] items-center justify-center p-8">
        <div className="max-w-md rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center">
          <KeyRound className="mx-auto mb-4 text-amber-600" size={34} />
          <h1 className="text-lg font-bold text-slate-900">
            {t("databaseSchema.restrictedTitle")}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t("databaseSchema.restrictedBody")}
          </p>
        </div>
      </div>
    );
  }

  if (schemaQuery.isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center text-sm text-slate-500">
        {t("databaseSchema.loading")}
      </div>
    );
  }

  if (schemaQuery.isError || !schemaQuery.data) {
    return (
      <div className="m-8 rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        {t("databaseSchema.errorFull")}
      </div>
    );
  }

  const totalBytes = schemaQuery.data.tables.reduce(
    (sum, table) => sum + table.total_bytes,
    0,
  );

  const statCards = [
    [t("databaseSchema.tables"), schemaQuery.data.tables.length],
    [t("databaseSchema.relations"), schemaQuery.data.relations.length],
    [
      t("databaseSchema.columns"),
      schemaQuery.data.tables.reduce((sum, table) => sum + table.columns.length, 0),
    ],
    [t("databaseSchema.size"), formatBytes(totalBytes)],
  ] as const;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-6 py-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Database className="text-blue-700" size={22} />
              <h1 className="text-xl font-bold text-slate-900">
                {t("databaseSchema.title")}
              </h1>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {schemaQuery.data.database} · PostgreSQL{" "}
              {schemaQuery.data.postgres_version}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void schemaQuery.refetch()}
            disabled={schemaQuery.isFetching}
            className="flex items-center gap-2 rounded-lg bg-blue-700 px-4 py-2 text-xs font-semibold text-white transition hover:bg-blue-800 disabled:opacity-60"
          >
            <RefreshCw
              size={14}
              className={schemaQuery.isFetching ? "animate-spin" : ""}
            />
            {t("databaseSchema.refresh")}
          </button>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          {statCards.map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-200 px-4 py-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {label}
              </p>
              <p className="mt-1 text-lg font-bold text-slate-800">{value}</p>
            </div>
          ))}
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 p-4 xl:flex-row">
        <section className="flex min-h-[560px] min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-slate-100 p-3">
            <Search size={15} className="text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("databaseSchema.searchPlaceholder")}
              className="w-full text-xs text-slate-700 outline-none placeholder:text-slate-400"
            />
            <span className="shrink-0 text-[11px] text-slate-400">
              {t("databaseSchema.visibleCount", { count: visibleTables.length })}
            </span>
          </div>
          <div ref={containerRef} className="min-h-[500px] flex-1 bg-slate-950">
            {size.width > 0 && (
              <ForceGraph2D
                ref={graphRef}
                width={size.width}
                height={size.height}
                graphData={graphData}
                backgroundColor="#020617"
                linkColor={() => "#64748b"}
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={1}
                linkLabel="label"
                nodeLabel={(node: any) =>
                  t("databaseSchema.nodeLabel", {
                    id: node.id,
                    count: node.table.columns.length,
                  })
                }
                nodeCanvasObject={(node: any, context, globalScale) => {
                  const radius = Math.max(5, node.val / 2);
                  context.beginPath();
                  context.arc(node.x, node.y, radius, 0, 2 * Math.PI);
                  context.fillStyle = node.color;
                  context.fill();
                  const fontSize = Math.max(3, 11 / globalScale);
                  context.font = `600 ${fontSize}px sans-serif`;
                  context.textAlign = "center";
                  context.textBaseline = "top";
                  context.fillStyle = "#e2e8f0";
                  context.fillText(node.name, node.x, node.y + radius + 2);
                }}
                onNodeClick={(node: any) => setSelectedTable(node.table)}
              />
            )}
          </div>
        </section>

        <aside className="w-full shrink-0 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:w-[390px]">
          {selectedTable ? (
            <>
              <div className="border-b border-slate-100 pb-4">
                <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600">
                  {selectedTable.schema}
                </p>
                <h2 className="mt-1 text-lg font-bold text-slate-900">
                  {selectedTable.name}
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  {t("databaseSchema.approxRows", {
                    count: selectedTable.estimated_rows,
                    size: formatBytes(selectedTable.total_bytes),
                  })}
                </p>
              </div>

              <h3 className="mb-2 mt-5 text-xs font-bold uppercase tracking-wider text-slate-500">
                {t("databaseSchema.detailColumns")}
              </h3>
              <div className="space-y-2">
                {selectedTable.columns.map((column) => (
                  <div
                    key={column.name}
                    className="rounded-lg border border-slate-100 bg-slate-50 p-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="truncate text-xs font-semibold text-slate-800">
                        {column.primary_key && "🔑 "}
                        {column.name}
                      </span>
                      <span className="shrink-0 font-mono text-[10px] text-blue-700">
                        {column.database_type}
                      </span>
                    </div>
                    <p className="mt-1 truncate text-[10px] text-slate-400">
                      {column.nullable
                        ? t("databaseSchema.nullable")
                        : t("databaseSchema.notNull")}
                      {column.default ? ` · ${column.default}` : ""}
                    </p>
                  </div>
                ))}
              </div>

              <h3 className="mb-2 mt-5 text-xs font-bold uppercase tracking-wider text-slate-500">
                {t("databaseSchema.indexes", { count: selectedTable.indexes.length })}
              </h3>
              <div className="space-y-2">
                {selectedTable.indexes.map((index) => (
                  <div key={index.name} className="rounded-lg bg-slate-950 p-3">
                    <p className="text-xs font-semibold text-emerald-300">
                      {index.name}
                    </p>
                    <p className="mt-1 break-all font-mono text-[9px] leading-4 text-slate-400">
                      {index.definition}
                    </p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex min-h-[300px] flex-col items-center justify-center text-center">
              <Database className="mb-3 text-slate-300" size={34} />
              <p className="text-sm font-semibold text-slate-600">
                {t("databaseSchema.selectTable")}
              </p>
              <p className="mt-1 max-w-[250px] text-xs text-slate-400">
                {t("databaseSchema.selectTableHint")}
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
