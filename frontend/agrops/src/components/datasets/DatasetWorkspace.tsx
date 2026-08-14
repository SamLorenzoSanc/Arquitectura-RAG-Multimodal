import { useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  Columns3,
  FlaskConical,
  MoreVertical,
  Pencil,
  Plus,
  Shield,
  Trash2,
  UploadCloud,
} from "lucide-react";

import { queryKeys } from "@/lib/queryKeys";
import DatasetService from "@/services/dataset.service";
import {
  DEFAULT_LLM_COLUMN_TEMPLATE,
  RAG_FIELDS,
  type RagDataset,
} from "@/types/dataset";

const DISPLAY_FIELDS = [
  "prompt",
  "context",
  "response",
  "expected_response",
  "expected_context",
  "traceId",
  "timestamp",
] as const;

type TabId = "datos" | "traces" | "guardrails";

function displayValue(value: unknown) {
  if (value == null || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

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

function llmColumnsOf(row: Record<string, unknown>) {
  return asRecord(asRecord(row.metadata).llm_columns);
}

function guardrailsOf(row: Record<string, unknown>) {
  return asRecord(asRecord(row.metadata).guardrails);
}

function errorMessage(error: unknown) {
  const candidate = error as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return candidate.response?.data?.detail || candidate.message || "Error inesperado.";
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
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [tab, setTab] = useState<TabId>("datos");
  const [menuOpen, setMenuOpen] = useState(false);
  const [columnOpen, setColumnOpen] = useState(false);
  const [columnName, setColumnName] = useState("veredicto");
  const [columnTemplate, setColumnTemplate] = useState(DEFAULT_LLM_COLUMN_TEMPLATE);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const detail = useQuery({
    queryKey: queryKeys.evaluationDataset(organizationId, datasetId),
    queryFn: () => DatasetService.get(datasetId, organizationId, 100),
    enabled: Boolean(organizationId && datasetId),
  });

  const traces = useQuery({
    queryKey: ["datasets", organizationId, datasetId, "traces"],
    queryFn: () => DatasetService.traces(datasetId, organizationId, 100),
    enabled: Boolean(organizationId && datasetId) && tab === "traces",
  });

  const dataset = detail.data?.dataset;
  const rows = detail.data?.rows ?? [];
  const mapping = (dataset?.mapping ?? {}) as Record<string, string>;
  const llmColumnNames = useMemo(() => {
    const names = new Set<string>();
    for (const row of rows) {
      Object.keys(llmColumnsOf(row)).forEach((name) => names.add(name));
    }
    return [...names];
  }, [rows]);
  const columns = useMemo(() => {
    const present = DISPLAY_FIELDS.filter((field) =>
      rows.some((row) => row[field] != null && row[field] !== ""),
    );
    return present.length > 0 ? present : ["prompt", "context", "expected_response"];
  }, [rows]);
  const guardrailSummary = useMemo(() => {
    let scanned = 0;
    let passed = 0;
    const flags: Record<string, number> = {};
    for (const row of rows) {
      const verdict = guardrailsOf(row);
      if (!Object.keys(verdict).length) continue;
      scanned += 1;
      if (verdict.passed) passed += 1;
      for (const flag of (verdict.flags as string[]) || []) {
        flags[flag] = (flags[flag] ?? 0) + 1;
      }
    }
    return { scanned, passed, flagged: scanned - passed, flags };
  }, [rows]);

  const refresh = async () => {
    await queryClient.invalidateQueries({
      queryKey: queryKeys.evaluationDataset(organizationId, datasetId),
    });
    await queryClient.invalidateQueries({
      queryKey: ["datasets", organizationId, datasetId, "traces"],
    });
    await queryClient.invalidateQueries({ queryKey: ["datasets", organizationId] });
  };

  const run = async (action: string, work: () => Promise<string>) => {
    setBusy(action);
    setError("");
    setNotice("");
    try {
      setNotice(await work());
      await refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy("");
    }
  };

  const addRows = (file: File) =>
    run("rows", async () => {
      const result = await DatasetService.addRows(datasetId, organizationId, file);
      return (
        `Añadidas ${result.imported_rows} filas` +
        (result.rejected_rows ? ` · ${result.rejected_rows} omitidas` : "")
      );
    });

  const addColumn = () =>
    run("column", async () => {
      const result = await DatasetService.addColumn(datasetId, organizationId, {
        column_name: columnName,
        prompt_template: columnTemplate,
      });
      setColumnOpen(false);
      return `Columna «${result.column_name}» en ${result.filled_rows} filas`;
    });

  const importTraces = () =>
    run("traces", async () => {
      const result = await DatasetService.importTraces(datasetId, organizationId);
      setTab("traces");
      return `Importadas ${result.imported_rows} traces de chat`;
    });

  const runGuardrails = () =>
    run("guardrails", async () => {
      const result = await DatasetService.runGuardrails(datasetId, organizationId);
      setTab("guardrails");
      return `Guardrails: ${result.passed} OK · ${result.flagged} con avisos`;
    });

  if (detail.isLoading) {
    return (
      <div className="h-64 animate-pulse rounded-xl border border-slate-200 bg-white" />
    );
  }
  if (detail.isError || !dataset) {
    return (
      <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
        {errorMessage(detail.error) || "Dataset no encontrado."}
        <button type="button" onClick={onBack} className="ml-3 font-semibold underline">
          Volver al catálogo
        </button>
      </div>
    );
  }

  const tabs: Array<{ id: TabId; label: string; icon: typeof Columns3 }> = [
    { id: "datos", label: "Datos", icon: Columns3 },
    { id: "traces", label: "Traces", icon: Activity },
    { id: "guardrails", label: "Guardrails", icon: Shield },
  ];

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
            Datasets
          </button>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {dataset.name}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {dataset.row_count ?? rows.length} filas · esquema RAG ·{" "}
            {dataset.status || "ready"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileInput}
            type="file"
            accept=".csv,.json,.jsonl,.ndjson,.xlsx,.xls"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) void addRows(file);
            }}
          />
          <button
            type="button"
            disabled={Boolean(busy)}
            onClick={() => fileInput.current?.click()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <UploadCloud size={14} />
            {busy === "rows" ? "Añadiendo…" : "Añadir filas"}
          </button>
          <button
            type="button"
            disabled={Boolean(busy)}
            onClick={() => setColumnOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <Columns3 size={14} />
            Columna LLM
          </button>
          <button
            type="button"
            disabled={Boolean(busy)}
            onClick={() => void importTraces()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <Activity size={14} />
            {busy === "traces" ? "Importando…" : "Importar traces"}
          </button>
          <button
            type="button"
            disabled={Boolean(busy)}
            onClick={() => void runGuardrails()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <Shield size={14} />
            {busy === "guardrails" ? "Analizando…" : "Ejecutar guardrails"}
          </button>
          <button
            type="button"
            onClick={() =>
              navigate(`/dashboard/evaluacion?dataset=${encodeURIComponent(dataset.id)}`)
            }
            className="inline-flex items-center gap-2 rounded-lg bg-[#0038A8] px-3 py-2 text-xs font-bold text-white"
          >
            <FlaskConical size={14} />
            Evaluar
          </button>
          <div className="relative">
            <button
              type="button"
              aria-label="Acciones del dataset"
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
                  Actualizar campos
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
                  Eliminar dataset
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-lg border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {notice}
        </div>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-800">Schema mapping</h2>
          <span className="text-[11px] text-slate-400">
            {Object.keys(mapping).length || RAG_FIELDS.length} campos
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(mapping).length > 0
            ? Object.entries(mapping)
            : RAG_FIELDS.map((field) => [field, field])
          ).map(([target, source]) => (
            <span
              key={`${target}-${source}`}
              className="rounded-full border border-blue-100 bg-blue-50 px-2.5 py-1 font-mono text-[11px] text-[#0038A8]"
            >
              {source} → {target}
            </span>
          ))}
          {llmColumnNames.map((name) => (
            <span
              key={name}
              className="rounded-full border border-violet-100 bg-violet-50 px-2.5 py-1 font-mono text-[11px] text-violet-700"
            >
              llm.{name}
            </span>
          ))}
        </div>
      </section>

      <div className="flex gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`inline-flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-bold ${
              tab === item.id
                ? "bg-white text-[#0038A8] shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <item.icon size={14} />
            {item.label}
          </button>
        ))}
      </div>

      {tab === "datos" && (
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <h2 className="text-sm font-bold text-slate-800">Datos</h2>
            <span className="text-[11px] text-slate-400">
              Vista tabular al estilo Catalyst
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">#</th>
                  {columns.map((field) => (
                    <th key={field} className="whitespace-nowrap px-3 py-2">
                      {field}
                    </th>
                  ))}
                  {llmColumnNames.map((name) => (
                    <th key={name} className="whitespace-nowrap px-3 py-2 text-violet-600">
                      {name}
                    </th>
                  ))}
                  {guardrailSummary.scanned > 0 && (
                    <th className="whitespace-nowrap px-3 py-2">guardrails</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {rows.length === 0 ? (
                  <tr>
                    <td
                      colSpan={columns.length + 1}
                      className="px-4 py-10 text-center text-slate-400"
                    >
                      No hay filas. Usa «Añadir filas» o «Importar traces».
                    </td>
                  </tr>
                ) : (
                  rows.map((row, index) => {
                    const verdict = guardrailsOf(row);
                    const flags = (verdict.flags as string[]) || [];
                    return (
                      <tr key={String(row.id ?? index)} className="hover:bg-slate-50">
                        <td className="px-3 py-2 text-slate-400">{index + 1}</td>
                        {columns.map((field) => (
                          <td key={field} className="max-w-xs truncate px-3 py-2">
                            {displayValue(row[field])}
                          </td>
                        ))}
                        {llmColumnNames.map((name) => (
                          <td key={name} className="max-w-xs truncate px-3 py-2 text-violet-700">
                            {displayValue(llmColumnsOf(row)[name])}
                          </td>
                        ))}
                        {guardrailSummary.scanned > 0 && (
                          <td className="px-3 py-2">
                            {!Object.keys(verdict).length ? (
                              "—"
                            ) : verdict.passed ? (
                              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                                OK
                              </span>
                            ) : (
                              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                                {flags.join(", ") || "aviso"}
                              </span>
                            )}
                          </td>
                        )}
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === "traces" && (
        <section className="space-y-3">
          {traces.isLoading ? (
            <div className="h-40 animate-pulse rounded-xl border border-slate-200 bg-white" />
          ) : (traces.data?.data ?? []).length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-400">
              No hay traces. Importa conversaciones del chat o añade filas con traceId.
            </div>
          ) : (
            (traces.data?.data ?? []).map((trace) => (
              <article
                key={trace.traceId || trace.row_id}
                className="rounded-xl border border-slate-200 bg-white p-4"
              >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <p className="font-mono text-xs font-bold text-[#0038A8]">
                    {trace.traceId || "sin-trace"}
                  </p>
                  <span className="text-[11px] text-slate-400">
                    {trace.timestamp ? String(trace.timestamp) : "sin timestamp"}
                  </span>
                </div>
                <ol className="space-y-2">
                  {trace.spans.map((span) => (
                    <li key={span.name} className="rounded-lg bg-slate-50 px-3 py-2">
                      <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                        {span.name}
                      </p>
                      <p className="mt-1 line-clamp-4 text-xs text-slate-700">
                        {span.content || "—"}
                      </p>
                    </li>
                  ))}
                </ol>
              </article>
            ))
          )}
        </section>
      )}

      {tab === "guardrails" && (
        <section className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
                Analizadas
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-900">
                {guardrailSummary.scanned}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
                Superadas
              </p>
              <p className="mt-1 text-2xl font-bold text-emerald-700">
                {guardrailSummary.passed}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
                Con avisos
              </p>
              <p className="mt-1 text-2xl font-bold text-amber-700">
                {guardrailSummary.flagged}
              </p>
            </div>
          </div>
          {Object.keys(guardrailSummary.flags).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(guardrailSummary.flags).map(([flag, count]) => (
                <span
                  key={flag}
                  className="rounded-full border border-amber-100 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-800"
                >
                  {flag}: {count}
                </span>
              ))}
            </div>
          )}
          <p className="text-xs text-slate-500">
            Comprueba alucinación numérica, contexto vacío y PII (email, NIF, teléfono).
          </p>
        </section>
      )}

      <p className="flex items-center gap-1 text-[11px] text-slate-400">
        <Plus size={12} />
        Columnas LLM, traces de chat y guardrails se guardan en el metadata de cada fila.
      </p>

      {columnOpen && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-llm-column"
            className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl"
          >
            <h3 id="add-llm-column" className="font-bold text-slate-900">
              Añadir columna LLM
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              Usa <code>{"{{prompt}}"}</code>, <code>{"{{context}}"}</code> y{" "}
              <code>{"{{response}}"}</code> en la plantilla.
            </p>
            <label className="mt-4 block text-xs font-bold text-slate-600">
              Nombre
              <input
                value={columnName}
                onChange={(event) => setColumnName(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </label>
            <label className="mt-3 block text-xs font-bold text-slate-600">
              Plantilla
              <textarea
                value={columnTemplate}
                onChange={(event) => setColumnTemplate(event.target.value)}
                rows={6}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs"
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                disabled={Boolean(busy)}
                onClick={() => setColumnOpen(false)}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={Boolean(busy) || !columnName.trim()}
                onClick={() => void addColumn()}
                className="rounded-lg bg-[#0038A8] px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
              >
                {busy === "column" ? "Generando…" : "Generar columna"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
