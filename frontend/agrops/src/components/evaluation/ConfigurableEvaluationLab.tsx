import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  ChevronRight,
  FlaskConical,
  Pencil,
  Play,
  Plus,
  Search,
  X,
  XCircle,
} from "lucide-react";

import { queryKeys } from "@/lib/queryKeys";
import DatasetService from "@/services/dataset.service";
import EvaluationService from "@/services/evaluation.service";
import type { RagDataset, RagField } from "@/types/dataset";
import type {
  EvaluationCatalog,
  EvaluationConfig,
  EvaluationConfigInput,
  EvaluationMetric,
  EvaluationRun,
} from "@/types/evaluation";

type Props = {
  organizationId: string;
  initialDatasetId?: string;
};

function message(error: unknown) {
  const candidate = error as {
    response?: { data?: { detail?: string | { message?: string } } };
    message?: string;
  };
  const detail = candidate.response?.data?.detail;
  return (
    (typeof detail === "string" ? detail : detail?.message) ||
    candidate.message ||
    "No se pudo completar la operación."
  );
}

export default function ConfigurableEvaluationLab({
  organizationId,
  initialDatasetId,
}: Props) {
  const queryClient = useQueryClient();
  const [datasetId, setDatasetId] = useState(initialDatasetId ?? "");
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [configDraft, setConfigDraft] = useState<{
    metrics: EvaluationMetric[];
    existing?: EvaluationConfig;
  } | null>(null);
  const [activeConfigId, setActiveConfigId] = useState("");
  const [latestRun, setLatestRun] = useState<EvaluationRun | null>(null);

  const datasets = useQuery({
    queryKey: queryKeys.datasets(organizationId),
    queryFn: () => DatasetService.list(organizationId),
    enabled: Boolean(organizationId),
  });
  const catalog = useQuery({
    queryKey: queryKeys.evaluationCatalog(organizationId, datasetId),
    queryFn: () => EvaluationService.catalog(organizationId, datasetId),
    enabled: Boolean(organizationId && datasetId),
  });
  const detail = useQuery({
    queryKey: queryKeys.evaluationDataset(organizationId, datasetId),
    queryFn: () => EvaluationService.dataset(organizationId, datasetId),
    enabled: Boolean(organizationId && datasetId),
  });
  const configs = useQuery({
    queryKey: queryKeys.evaluationConfigs(organizationId, datasetId),
    queryFn: () => EvaluationService.configs(organizationId, datasetId),
    enabled: Boolean(organizationId && datasetId),
  });

  useEffect(() => {
    if (!datasetId && datasets.data?.length) {
      setDatasetId(initialDatasetId || datasets.data[0].id);
    }
  }, [datasetId, datasets.data, initialDatasetId]);

  useEffect(() => {
    const items = configs.data ?? [];
    if (items.length && !items.some((item) => item.id === activeConfigId)) {
      setActiveConfigId(items[0].id);
    }
    if (!items.length) setActiveConfigId("");
  }, [activeConfigId, configs.data]);

  const activeConfig = configs.data?.find((item) => item.id === activeConfigId);
  const runMutation = useMutation({
    mutationFn: (configId: string) =>
      EvaluationService.run(organizationId, configId),
    onSuccess: setLatestRun,
  });

  const columns = catalog.data?.fields ?? [];
  const rows = detail.data?.rows ?? [];

  return (
    <section className="space-y-5 rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-700">
            <FlaskConical size={15} />
            Laboratorio configurable
          </p>
          <h2 className="mt-1 text-xl font-extrabold text-slate-900">
            Evaluaciones por dataset
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={datasetId}
            onChange={(event) => {
              setDatasetId(event.target.value);
              setLatestRun(null);
            }}
            className="h-10 min-w-64 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold"
          >
            <option value="">Selecciona un dataset</option>
            {(datasets.data ?? []).map((dataset: RagDataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name} · {dataset.row_count ?? 0} filas
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={!datasetId || !catalog.data}
            onClick={() => setCatalogOpen(true)}
            className="flex h-10 items-center gap-2 rounded-lg bg-blue-700 px-4 text-sm font-bold text-white disabled:opacity-40"
          >
            <Plus size={16} />
            Añadir evaluación
          </button>
        </div>
      </div>

      {catalog.isError && (
        <ErrorBox text={message(catalog.error)} />
      )}

      {datasetId && (
        <>
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs font-bold text-slate-700">
                Muestra del dataset · {rows.length} filas cargadas
              </p>
              <p className="text-[11px] text-slate-400">
                Campos detectados: {columns.join(", ") || "ninguno"}
              </p>
            </div>
            <div className="max-h-64 overflow-auto">
              <table className="min-w-full text-left text-xs">
                <thead className="sticky top-0 bg-white text-slate-500">
                  <tr>
                    {columns.slice(0, 7).map((column) => (
                      <th key={column} className="border-b px-3 py-2 font-bold">
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 20).map((row, index) => (
                    <tr key={String(row.id ?? index)} className="border-b last:border-0">
                      {columns.slice(0, 7).map((column) => (
                        <td
                          key={column}
                          className="max-w-64 truncate px-3 py-2 text-slate-600"
                          title={String(row[column] ?? "")}
                        >
                          {typeof row[column] === "object"
                            ? JSON.stringify(row[column])
                            : String(row[column] ?? "—")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 border-b border-slate-200">
            {(configs.data ?? []).map((config) => (
              <button
                key={config.id}
                type="button"
                onClick={() => {
                  setActiveConfigId(config.id);
                  setLatestRun(null);
                }}
                className={`border-b-2 px-3 py-2 text-xs font-bold ${
                  activeConfigId === config.id
                    ? "border-blue-600 text-blue-700"
                    : "border-transparent text-slate-500"
                }`}
              >
                {config.name}
              </button>
            ))}
          </div>

          {activeConfig ? (
            <div className="rounded-xl border border-slate-200 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-slate-900">{activeConfig.name}</h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Ollama · {activeConfig.model_name} ·{" "}
                    {activeConfig.metrics.length} métricas
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {activeConfig.metrics.map((metric) => (
                      <span
                        key={metric}
                        className="rounded-full bg-blue-50 px-2 py-1 text-[10px] font-bold text-blue-700"
                      >
                        {catalog.data?.metrics.find((item) => item.id === metric)
                          ?.name ?? metric}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      setConfigDraft({
                        existing: activeConfig,
                        metrics:
                          catalog.data?.metrics.filter((metric) =>
                            activeConfig.metrics.includes(metric.id),
                          ) ?? [],
                      })
                    }
                    className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600"
                  >
                    <Pencil size={14} />
                    Editar
                  </button>
                  <button
                    type="button"
                    disabled={runMutation.isPending}
                    onClick={() => runMutation.mutate(activeConfig.id)}
                    className="flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
                  >
                    <Play size={14} />
                    {runMutation.isPending ? "Ejecutando…" : "Ejecutar"}
                  </button>
                </div>
              </div>
              {runMutation.isError && (
                <div className="mt-3">
                  <ErrorBox text={message(runMutation.error)} />
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
              Añade una evaluación para configurar métricas y umbrales.
            </div>
          )}

          {latestRun && (
            <EvaluationRunResults run={latestRun} catalog={catalog.data} />
          )}
        </>
      )}

      {catalogOpen && catalog.data && (
        <EvaluationCatalogModal
          catalog={catalog.data}
          onClose={() => setCatalogOpen(false)}
          onNext={(metrics) => {
            setCatalogOpen(false);
            setConfigDraft({ metrics });
          }}
        />
      )}
      {configDraft && catalog.data && (
        <EvaluationConfigPanel
          datasetId={datasetId}
          catalog={catalog.data}
          metrics={configDraft.metrics}
          existing={configDraft.existing}
          organizationId={organizationId}
          onClose={() => setConfigDraft(null)}
          onSaved={(config) => {
            setConfigDraft(null);
            setActiveConfigId(config.id);
            void queryClient.invalidateQueries({
              queryKey: queryKeys.evaluationConfigs(organizationId, datasetId),
            });
          }}
        />
      )}
    </section>
  );
}

function EvaluationCatalogModal({
  catalog,
  onClose,
  onNext,
}: {
  catalog: EvaluationCatalog;
  onClose: () => void;
  onNext: (metrics: EvaluationMetric[]) => void;
}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<"all" | EvaluationMetric["category"]>(
    "all",
  );
  const [selected, setSelected] = useState<string[]>([]);
  const filtered = catalog.metrics.filter((metric) => {
    const matchesCategory = category === "all" || metric.category === category;
    const query = search.toLowerCase();
    return (
      matchesCategory &&
      `${metric.name} ${metric.description}`.toLowerCase().includes(query)
    );
  });
  return (
    <ModalShell onClose={onClose} width="max-w-4xl">
      <div className="border-b border-slate-200 px-6 py-5">
        <h2 className="text-lg font-extrabold text-slate-900">
          Añadir evaluaciones
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Selecciona métricas compatibles con las columnas del dataset.
        </p>
      </div>
      <div className="space-y-4 p-6">
        <label className="relative block">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar una evaluación"
            className="h-11 w-full rounded-lg border border-slate-200 pl-10 pr-3 text-sm outline-none focus:border-blue-500"
          />
        </label>
        <div className="grid grid-cols-5 overflow-hidden rounded-lg border border-slate-200">
          {(["all", "prompt", "context", "response", "text"] as const).map(
            (item) => (
              <button
                key={item}
                type="button"
                onClick={() => setCategory(item)}
                className={`px-3 py-2 text-xs font-bold capitalize ${
                  category === item
                    ? "bg-blue-600 text-white"
                    : "border-l border-slate-200 text-slate-500 first:border-0"
                }`}
              >
                {item === "all" ? "Todas" : item}
              </button>
            ),
          )}
        </div>
        <div className="grid max-h-[52vh] gap-3 overflow-auto pr-1 md:grid-cols-2">
          {filtered.map((metric) => {
            const checked = selected.includes(metric.id);
            return (
              <button
                key={metric.id}
                type="button"
                disabled={!metric.compatible}
                onClick={() =>
                  setSelected((current) =>
                    checked
                      ? current.filter((id) => id !== metric.id)
                      : [...current, metric.id],
                  )
                }
                className={`rounded-xl border p-4 text-left transition ${
                  checked
                    ? "border-blue-500 bg-blue-50"
                    : "border-slate-200 bg-white"
                } disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-55`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-[10px] font-bold uppercase text-slate-400">
                      {metric.category} · {metric.engine}
                    </p>
                    <h3 className="mt-1 text-sm font-bold text-slate-900">
                      {metric.name}
                    </h3>
                  </div>
                  {checked && <CheckCircle2 size={18} className="text-blue-600" />}
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-500">
                  {metric.description}
                </p>
                {!metric.compatible && (
                  <p className="mt-2 text-[10px] font-bold text-amber-700">
                    Faltan: {metric.missing_fields.join(", ")}
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </div>
      <div className="flex justify-end gap-2 border-t border-slate-200 px-6 py-4">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-bold text-slate-600"
        >
          Cancelar
        </button>
        <button
          type="button"
          disabled={!selected.length}
          onClick={() =>
            onNext(catalog.metrics.filter((metric) => selected.includes(metric.id)))
          }
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-40"
        >
          Configurar {selected.length || ""}
          <ChevronRight size={15} />
        </button>
      </div>
    </ModalShell>
  );
}

function EvaluationConfigPanel({
  datasetId,
  catalog,
  metrics,
  existing,
  organizationId,
  onClose,
  onSaved,
}: {
  datasetId: string;
  catalog: EvaluationCatalog;
  metrics: EvaluationMetric[];
  existing?: EvaluationConfig;
  organizationId: string;
  onClose: () => void;
  onSaved: (config: EvaluationConfig) => void;
}) {
  const requirements = useMemo(
    () => [...new Set(metrics.flatMap((metric) => metric.required_fields))],
    [metrics],
  );
  const defaultField = (requirement: string): RagField => {
    const alternatives: Record<string, RagField[]> = {
      response: ["response", "expected_response", "alternate_response"],
      expected_response: ["expected_response", "response", "alternate_response"],
      context: ["context", "expected_context"],
      expected_context: ["expected_context", "context"],
    };
    return (
      (alternatives[requirement] ?? [requirement as RagField]).find((field) =>
        catalog.fields.includes(field),
      ) ??
      catalog.fields[0] ??
      "prompt"
    );
  };
  const [name, setName] = useState(existing?.name ?? metrics[0]?.name ?? "Evaluación");
  const [model, setModel] = useState(
    existing?.model_name ?? catalog.models[0] ?? "llama3.2:latest",
  );
  const [mapping, setMapping] = useState<Record<string, RagField>>(() =>
    Object.fromEntries(
      requirements.map((field) => [
        field,
        existing?.mapping[field] ?? defaultField(field),
      ]),
    ),
  );
  const [thresholds, setThresholds] = useState<EvaluationConfig["thresholds"]>(
    () =>
      Object.fromEntries(
        metrics.map((metric) => [
          metric.id,
          existing?.thresholds[metric.id] ?? metric.default_threshold,
        ]),
      ),
  );
  const [split, setSplit] = useState(existing?.filters.split ?? "all");
  const [limit, setLimit] = useState(existing?.filters.limit ?? 100);
  const [categories, setCategories] = useState(
    existing?.filters.categories.join(", ") ?? "",
  );
  const mutation = useMutation({
    mutationFn: (input: EvaluationConfigInput) =>
      existing
        ? EvaluationService.updateConfig(
            organizationId,
            existing.id,
            input,
          )
        : EvaluationService.createConfig(organizationId, input),
    onSuccess: onSaved,
  });

  const save = () => {
    mutation.mutate({
      dataset_id: datasetId,
      name: name.trim(),
      provider: "ollama",
      model_name: model,
      metrics: metrics.map((metric) => metric.id),
      mapping,
      thresholds,
      filters: {
        split,
        categories: categories
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        statuses: ["ready", "approved"],
        limit,
      },
    });
  };

  return (
    <ModalShell onClose={onClose} width="max-w-3xl">
      <div className="border-b border-slate-200 px-6 py-5">
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="w-full text-lg font-extrabold text-slate-900 outline-none"
        />
        <p className="mt-1 text-xs text-slate-500">
          Configura proveedor, modelo, esquema, umbrales y filtros.
        </p>
      </div>
      <div className="max-h-[68vh] space-y-6 overflow-auto p-6">
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">Parámetros</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="text-xs font-bold text-slate-600">
              Proveedor
              <select
                disabled
                className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3"
              >
                <option>Ollama local</option>
              </select>
            </label>
            <label className="text-xs font-bold text-slate-600">
              Modelo
              <select
                value={model}
                onChange={(event) => setModel(event.target.value)}
                className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3"
              >
                {catalog.models.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-extrabold text-slate-900">Esquema</h3>
          <div className="mt-3 space-y-2">
            {requirements.map((requirement) => (
              <div
                key={requirement}
                className="grid grid-cols-[1fr_auto_1fr] items-center gap-3"
              >
                <span className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-bold text-slate-600">
                  {requirement}
                </span>
                <ChevronRight size={15} className="text-slate-400" />
                <select
                  value={mapping[requirement]}
                  onChange={(event) =>
                    setMapping((current) => ({
                      ...current,
                      [requirement]: event.target.value as RagField,
                    }))
                  }
                  className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs"
                >
                  {catalog.fields.map((field) => (
                    <option key={field}>{field}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-extrabold text-slate-900">Umbrales</h3>
          <div className="mt-3 space-y-2">
            {metrics.map((metric) => (
              <div
                key={metric.id}
                className="grid grid-cols-[1fr_90px_110px] items-center gap-2"
              >
                <span className="text-xs font-bold text-slate-600">
                  {metric.name}
                </span>
                <select
                  value={thresholds[metric.id]?.operator}
                  onChange={(event) =>
                    setThresholds((current) => ({
                      ...current,
                      [metric.id]: {
                        ...current[metric.id],
                        operator: event.target.value as "gte" | "lte",
                      },
                    }))
                  }
                  className="h-9 rounded-lg border border-slate-200 px-2 text-xs"
                >
                  <option value="gte">≥</option>
                  <option value="lte">≤</option>
                </select>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={thresholds[metric.id]?.value}
                  onChange={(event) =>
                    setThresholds((current) => ({
                      ...current,
                      [metric.id]: {
                        ...current[metric.id],
                        value: Number(event.target.value),
                      },
                    }))
                  }
                  className="h-9 rounded-lg border border-slate-200 px-3 text-xs"
                />
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-extrabold text-slate-900">Filtros</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <label className="text-xs font-bold text-slate-600">
              Split
              <select
                value={split}
                onChange={(event) =>
                  setSplit(event.target.value as "dev" | "holdout" | "all")
                }
                className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-2"
              >
                <option value="all">Todos</option>
                <option value="dev">Dev</option>
                <option value="holdout">Holdout</option>
              </select>
            </label>
            <label className="text-xs font-bold text-slate-600">
              Límite
              <input
                type="number"
                min={1}
                max={500}
                value={limit}
                onChange={(event) => setLimit(Number(event.target.value))}
                className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3"
              />
            </label>
            <label className="text-xs font-bold text-slate-600">
              Categorías
              <input
                value={categories}
                onChange={(event) => setCategories(event.target.value)}
                placeholder="temporal, direct_fact"
                className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3 font-normal"
              />
            </label>
          </div>
        </div>
        {mutation.isError && <ErrorBox text={message(mutation.error)} />}
      </div>
      <div className="flex justify-end gap-2 border-t border-slate-200 px-6 py-4">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-slate-200 px-5 py-2 text-xs font-bold text-slate-600"
        >
          Atrás
        </button>
        <button
          type="button"
          disabled={!name.trim() || mutation.isPending}
          onClick={save}
          className="rounded-lg bg-blue-600 px-6 py-2 text-xs font-bold text-white disabled:opacity-40"
        >
          {mutation.isPending ? "Guardando…" : "Guardar"}
        </button>
      </div>
    </ModalShell>
  );
}

function EvaluationRunResults({
  run,
  catalog,
}: {
  run: EvaluationRun;
  catalog?: EvaluationCatalog;
}) {
  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-bold text-slate-900">Resultado de la corrida</h3>
          <p className="text-xs text-slate-500">
            {run.row_count} filas · {run.cached ? "resultado reutilizado" : "nueva ejecución"}
          </p>
        </div>
        <div className="flex gap-2">
          <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">
            <CheckCircle2 size={13} /> {run.passed_count}
          </span>
          <span className="flex items-center gap-1 rounded-full bg-rose-100 px-3 py-1 text-xs font-bold text-rose-700">
            <XCircle size={13} /> {run.failed_count}
          </span>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Object.entries(run.aggregates ?? {}).map(([metric, value]) => (
          <div key={metric} className="rounded-lg border border-slate-200 bg-white p-3">
            <p className="truncate text-[10px] font-bold uppercase text-slate-400">
              {catalog?.metrics.find((item) => item.id === metric)?.name ?? metric}
            </p>
            <p className="mt-1 text-xl font-black text-slate-900">
              {(value * 100).toFixed(1)}%
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModalShell({
  children,
  onClose,
  width,
}: {
  children: React.ReactNode;
  onClose: () => void;
  width: string;
}) {
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/45 p-4">
      <div
        className={`relative max-h-[92vh] w-full overflow-hidden rounded-2xl bg-white shadow-2xl ${width}`}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"
        >
          <X size={18} />
        </button>
        {children}
      </div>
    </div>
  );
}

function ErrorBox({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs font-semibold text-rose-700">
      {text}
    </div>
  );
}
