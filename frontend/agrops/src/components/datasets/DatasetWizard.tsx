import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  FileText,
  PlayCircle,
  ScrollText,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";

import DatasetService from "@/services/dataset.service";
import DocumentService from "@/services/document.service";
import {
  RAG_FIELDS,
  type CreateDatasetInput,
  type DatasetMapping,
  type DatasetPreview,
  type DatasetSource,
  type DemoCatalogItem,
  type RagDataset,
  type RagField,
} from "@/types/dataset";
import type { KnowledgeBaseSummary } from "@/services/knowledge.service";
import type { Department } from "@/services/department.service";

type Props = {
  open: boolean;
  source: DatasetSource;
  organizationId: string;
  knowledgeBases: KnowledgeBaseSummary[];
  departments: Department[];
  initialKnowledgeBaseId?: string;
  onClose: () => void;
  onCreated: (dataset: RagDataset) => void;
};

const SOURCE_META: Record<
  DatasetSource,
  { title: string; description: string; icon: typeof UploadCloud }
> = {
  file: {
    title: "Subir documento",
    description: "PDF, DOCX, PPT, vídeo, CSV, JSON o Excel para el RAG del departamento.",
    icon: FileText,
  },
  logs: {
    title: "Importar logs",
    description: "Traza de inferencias en JSONL, CSV, JSON o .log.",
    icon: ScrollText,
  },
  synthetic: {
    title: "Datos sintéticos",
    description: "Genera casos para la cola de validación humana.",
    icon: Sparkles,
  },
  demo: {
    title: "Datasets demo",
    description: "Carga un conjunto de ejemplo agrícola (POSEI, riego, sanidad).",
    icon: PlayCircle,
  },
};

const TABULAR_FILE = /\.(csv|json|jsonl|ndjson|xlsx|xls)$/i;
const FILE_ACCEPT =
  ".csv,.json,.jsonl,.ndjson,.xlsx,.xls,.pdf,.txt,.md,.docx,.doc,.pptx,.ppt,.mp4,.webm,.mov,.mkv,.avi";

const SUGGESTIONS: Record<string, RagField> = {
  topic: "prompt",
  description: "context",
  applications: "expected_response",
  headline: "prompt",
  fragment: "context",
  summary: "expected_response",
};

function messageFromError(error: unknown) {
  const candidate = error as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return (
    candidate.response?.data?.detail ||
    candidate.message ||
    "No se pudo completar la operación."
  );
}

function suggestedMapping(columns: string[]): DatasetMapping {
  const mapping: DatasetMapping = {};
  const normalized = new Map(columns.map((column) => [column.toLowerCase(), column]));
  for (const field of RAG_FIELDS) {
    const exact = normalized.get(field.toLowerCase());
    if (exact) mapping[field] = exact;
  }
  for (const [source, target] of Object.entries(SUGGESTIONS)) {
    const column = normalized.get(source);
    if (column && !mapping[target]) mapping[target] = column;
  }
  return mapping;
}

function sourceFor(mapping: DatasetMapping, column: string) {
  return RAG_FIELDS.find((field) => mapping[field] === column) ?? "";
}

function displayValue(value: unknown) {
  if (value == null) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function DatasetWizard({
  open,
  source,
  organizationId,
  knowledgeBases,
  departments,
  initialKnowledgeBaseId,
  onClose,
  onCreated,
}: Props) {
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [knowledgeBaseId, setKnowledgeBaseId] = useState("");
  const [departmentIds, setDepartmentIds] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [catalogId, setCatalogId] = useState("");
  const [demoItems, setDemoItems] = useState<DemoCatalogItem[]>([]);
  const [syntheticRows, setSyntheticRows] = useState(25);
  const [syntheticTopic, setSyntheticTopic] = useState("");
  const [syntheticInstructions, setSyntheticInstructions] = useState("");
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [mapping, setMapping] = useState<DatasetMapping>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  const meta = SOURCE_META[source];
  const Icon = meta.icon;

  const reset = () => {
    setStep(1);
    setName("");
    setKnowledgeBaseId(initialKnowledgeBaseId || knowledgeBases[0]?.id || "");
    setDepartmentIds([]);
    setFile(null);
    setCatalogId("");
    setSyntheticRows(25);
    setSyntheticTopic("");
    setSyntheticInstructions("");
    setPreview(null);
    setMapping({});
    setBusy(false);
    setError("");
  };

  useEffect(() => {
    if (open) reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, source, initialKnowledgeBaseId]);

  useEffect(() => {
    if (!open || source !== "demo" || !organizationId) return;
    void DatasetService.demoCatalog(organizationId)
      .then(setDemoItems)
      .catch(() => setDemoItems([]));
  }, [open, source, organizationId]);

  const mappedPreview = useMemo(() => preview?.rows.slice(0, 8) ?? [], [preview]);

  if (!open) return null;

  const loadPreview = async () => {
    if (!name.trim() || !knowledgeBaseId) {
      setError("Indica un nombre y una base de conocimiento.");
      return;
    }
    if (departmentIds.length === 0) {
      setError("Asigna el dataset al menos a un departamento.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      let data: DatasetPreview;
      if (source === "file" || source === "logs") {
        if (!file) throw new Error("Selecciona un archivo.");
        data = await DatasetService.previewFile(file, organizationId);
      } else if (source === "demo") {
        const item = demoItems.find((demo) => demo.id === catalogId);
        if (!item) throw new Error("Elige un dataset demo.");
        if (!name.trim()) setName(item.name);
        data = {
          columns: ["prompt", "expected_response"],
          rows: [
            {
              prompt: item.name,
              expected_response: item.description,
            },
          ],
          total_rows: item.row_count,
        };
        setPreview({ ...data, columns: data.columns, rows: data.rows ?? [] });
        setMapping({ prompt: "prompt", expected_response: "expected_response" });
        setStep(3);
        return;
      } else {
        data = await DatasetService.previewSynthetic(
          {
            rows: syntheticRows,
            topic: syntheticTopic,
            instructions: syntheticInstructions || undefined,
            destination: "human_validation",
          },
          {
            name: name.trim(),
            knowledge_base_id: knowledgeBaseId,
            department_ids: departmentIds,
          },
          organizationId,
        );
      }
      const columns =
        data.columns?.length > 0
          ? data.columns
          : Object.keys(data.rows?.[0] ?? {});
      const normalized = { ...data, columns, rows: data.rows ?? [] };
      setPreview(normalized);
      setMapping(
        data.suggested_mapping && Object.keys(data.suggested_mapping).length > 0
          ? data.suggested_mapping
          : suggestedMapping(columns),
      );
      setStep(2);
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setBusy(false);
    }
  };

  const assignColumn = (column: string, field: RagField | "") => {
    setMapping((current) => {
      const next = { ...current };
      for (const target of RAG_FIELDS) {
        if (next[target] === column) delete next[target];
      }
      if (field) next[field] = column;
      return next;
    });
  };

  const finish = async () => {
    const effectiveMapping =
      mapping.prompt || preview?.kind !== "chunks"
        ? mapping
        : {
            prompt: "headline",
            context: "fragment",
            expected_response: "summary",
          };
    if (!effectiveMapping.prompt) {
      setError("Asigna al menos una columna al campo prompt.");
      setStep(2);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const base = {
        name: name.trim(),
        organization_id: organizationId,
        knowledge_base_id: knowledgeBaseId,
        department_ids: departmentIds,
        mapping: effectiveMapping,
      };
      let input: CreateDatasetInput;
      if (source === "file" || source === "logs") {
        input = { ...base, source, file: file! };
      } else if (source === "demo") {
        input = { ...base, source, catalogId };
      } else {
        input = {
          ...base,
          source: "synthetic",
          synthetic: {
            rows: syntheticRows,
            topic: syntheticTopic,
            instructions: syntheticInstructions || undefined,
            destination: "human_validation",
          },
        };
      }
      const created = await DatasetService.create(input);
      if (source === "file" && file && !TABULAR_FILE.test(file.name)) {
        try {
          await DocumentService.upload({
            knowledgeBaseId: knowledgeBaseId,
            file,
            title: name.trim(),
          });
        } catch {
          /* el dataset ya está creado; la indexación RAG puede reintentarse */
        }
      }
      onCreated(created);
      onClose();
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dataset-wizard-title"
        className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-[#0038A8]">
              <Icon size={20} />
            </span>
            <div>
              <h2 id="dataset-wizard-title" className="font-bold text-slate-900">
                {meta.title}
              </h2>
              <p className="text-xs text-slate-500">{meta.description}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100"
            aria-label="Cerrar"
          >
            <X size={20} />
          </button>
        </header>

        <div className="border-b border-slate-100 px-6 py-4">
          <div className="mx-auto flex max-w-xl items-center">
            {(["Origen y acceso", preview?.kind === "chunks" ? "Fragmentos" : "Columnas", "Vista previa"] as const).map((label, index) => {
              const number = index + 1;
              return (
                <div key={label} className="flex flex-1 items-center last:flex-none">
                  <div className="flex items-center gap-2">
                    <span
                      className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                        step >= number
                          ? "bg-[#0038A8] text-white"
                          : "bg-slate-100 text-slate-400"
                      }`}
                    >
                      {step > number ? <Check size={14} /> : number}
                    </span>
                    <span className="hidden text-xs font-semibold text-slate-600 sm:inline">
                      {label}
                    </span>
                  </div>
                  {number < 3 && <span className="mx-3 h-px flex-1 bg-slate-200" />}
                </div>
              );
            })}
          </div>
        </div>

        <main className="min-h-0 flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-5 rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {step === 1 && (
            <div className="mx-auto max-w-3xl space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-semibold text-slate-700">
                  Nombre del dataset
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Ej. FAQ cultivos 2026"
                    className="mt-2 h-11 w-full rounded-lg border border-slate-200 px-3 font-normal outline-none focus:border-blue-400"
                  />
                </label>
                <label className="text-sm font-semibold text-slate-700">
                  Base de conocimiento
                  <select
                    value={knowledgeBaseId}
                    onChange={(event) => setKnowledgeBaseId(event.target.value)}
                    className="mt-2 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal outline-none focus:border-blue-400"
                  >
                    <option value="">Selecciona una KB</option>
                    {knowledgeBases.map((kb) => (
                      <option key={kb.id} value={kb.id}>
                        {kb.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <fieldset>
                <legend className="text-sm font-semibold text-slate-700">
                  Departamentos con acceso
                </legend>
                <p className="mt-1 text-xs text-slate-500">
                  Cada departamento ve solo sus datasets. Elige al menos uno.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {departments.map((department) => {
                    const selected = departmentIds.includes(department.id);
                    return (
                      <button
                        key={department.id}
                        type="button"
                        onClick={() =>
                          setDepartmentIds((current) =>
                            selected
                              ? current.filter((id) => id !== department.id)
                              : [...current, department.id],
                          )
                        }
                        className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                          selected
                            ? "border-blue-200 bg-blue-50 text-[#0038A8]"
                            : "border-slate-200 text-slate-600 hover:bg-slate-50"
                        }`}
                      >
                        {selected && "✓ "}
                        {department.name}
                      </button>
                    );
                  })}
                  {departments.length === 0 && (
                    <span className="text-xs text-slate-400">No hay departamentos.</span>
                  )}
                </div>
              </fieldset>

              {(source === "file" || source === "logs") && (
                <div>
                  <input
                    ref={fileInput}
                    type="file"
                    accept={
                      source === "logs"
                        ? ".csv,.json,.jsonl,.log,.ndjson"
                        : FILE_ACCEPT
                    }
                    className="hidden"
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  />
                  <button
                    type="button"
                    onClick={() => fileInput.current?.click()}
                    className="flex w-full flex-col items-center rounded-xl border-2 border-dashed border-slate-200 px-6 py-10 text-center hover:border-blue-300 hover:bg-blue-50/30"
                  >
                    <UploadCloud size={28} className="text-[#0038A8]" />
                    <span className="mt-3 text-sm font-bold text-slate-800">
                      {file?.name ?? "Selecciona o arrastra un archivo"}
                    </span>
                    <span className="mt-1 text-xs text-slate-500">
                      {source === "logs"
                        ? "CSV, JSON, JSONL o .log de inferencias"
                        : "CSV, JSON, Excel, PDF, DOCX, PowerPoint, vídeo, TXT o Markdown"}
                    </span>
                  </button>
                </div>
              )}

              {source === "demo" && (
                <div className="grid gap-3 sm:grid-cols-3">
                  {demoItems.map((item) => {
                    const selected = catalogId === item.id;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          setCatalogId(item.id);
                          if (!name.trim()) setName(item.name);
                        }}
                        className={`rounded-xl border p-4 text-left ${
                          selected
                            ? "border-blue-400 bg-blue-50"
                            : "border-slate-200 hover:border-blue-200"
                        }`}
                      >
                        <span className="block text-sm font-bold text-slate-900">
                          {item.name}
                        </span>
                        <span className="mt-1 block text-xs text-slate-500">
                          {item.description}
                        </span>
                        <span className="mt-2 block text-[11px] font-semibold text-slate-400">
                          {item.row_count} ejemplos
                        </span>
                      </button>
                    );
                  })}
                  {demoItems.length === 0 && (
                    <p className="text-xs text-slate-500 sm:col-span-3">
                      No hay datasets demo disponibles.
                    </p>
                  )}
                </div>
              )}

              {source === "synthetic" && (
                <div className="space-y-4 rounded-xl border border-purple-100 bg-purple-50/40 p-5">
                  <div className="grid gap-4 sm:grid-cols-[140px_1fr]">
                    <label className="text-xs font-bold text-slate-600">
                      Número de filas
                      <input
                        type="number"
                        min={1}
                        max={500}
                        value={syntheticRows}
                        onChange={(event) =>
                          setSyntheticRows(
                            Math.min(500, Math.max(1, Number(event.target.value))),
                          )
                        }
                        className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal"
                      />
                    </label>
                    <label className="text-xs font-bold text-slate-600">
                      Pregunta adicional (opcional)
                      <input
                        value={syntheticTopic}
                        onChange={(event) => setSyntheticTopic(event.target.value)}
                        placeholder="¿Qué requisitos debe cumplir el cultivo?"
                        className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal"
                      />
                    </label>
                  </div>
                  <label className="block text-xs font-bold text-slate-600">
                    Instrucciones opcionales
                    <textarea
                      value={syntheticInstructions}
                      onChange={(event) => setSyntheticInstructions(event.target.value)}
                      rows={4}
                      placeholder="Incluye preguntas difíciles y respuestas de referencia..."
                      className="mt-2 w-full rounded-lg border border-slate-200 bg-white p-3 font-normal"
                    />
                  </label>
                  <p className="text-xs text-purple-700">
                    Las filas se enviarán a Validación humana antes de incorporarse al banco.
                  </p>
                </div>
              )}
            </div>
          )}

          {step === 2 && preview && preview.kind === "chunks" && (
            <div className="space-y-5">
              <div>
                <h3 className="font-bold text-slate-900">Fragmentos detectados</h3>
                <p className="mt-1 text-xs text-slate-500">
                  {preview.chunks?.length ?? preview.rows.length} chunks extraídos del{" "}
                  {preview.format || "documento"}. Los parseadores no cambian; aquí se
                  previsualizan headline, resumen y fragmento.
                </p>
              </div>
              <div className="space-y-3">
                {(preview.chunks ?? preview.rows).slice(0, 12).map((chunk, index) => {
                  const item = chunk as {
                    chunk_index?: number;
                    headline?: unknown;
                    summary?: unknown;
                    fragment?: unknown;
                    characters?: number;
                  };
                  return (
                    <article
                      key={item.chunk_index ?? index}
                      className="rounded-xl border border-slate-200 bg-slate-50/60 p-4"
                    >
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-[#0038A8] px-2 py-0.5 text-[10px] font-bold text-white">
                          chunk {item.chunk_index ?? index}
                        </span>
                        <span className="text-[11px] font-semibold text-slate-500">
                          {item.characters ?? String(item.fragment ?? "").length} caracteres
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-slate-900">
                        {displayValue(item.headline)}
                      </h4>
                      <p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-slate-600">
                        {displayValue(item.fragment).slice(0, 700)}
                        {displayValue(item.fragment).length > 700 ? "…" : ""}
                      </p>
                    </article>
                  );
                })}
              </div>
              <p className="text-[11px] text-slate-400">
                Mapeo RAG automático: headline → prompt · fragmento → context · resumen →
                expected_response
              </p>
            </div>
          )}

          {step === 2 && preview && preview.kind !== "chunks" && (
            <div>
              <div className="mb-4">
                <h3 className="font-bold text-slate-900">Columnas detectadas</h3>
                <p className="mt-1 text-xs text-slate-500">
                  Se han extraído las {preview.columns.length} columnas del archivo. Relaciona
                  cada una con un campo RAG; las no asignadas se conservan en metadatos.
                </p>
              </div>
              <div className="overflow-hidden rounded-xl border border-slate-200">
                <table className="w-full">
                  <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-3">Columna de origen</th>
                      <th className="px-4 py-3">Tipo</th>
                      <th className="px-4 py-3">Ejemplo</th>
                      <th className="px-4 py-3">Campo RAG</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {preview.columns.map((column) => {
                      const suggestion = SUGGESTIONS[column.toLowerCase()];
                      const columnType =
                        preview.schema_mapping?.[column]?.columnType ?? "string";
                      return (
                        <tr key={column}>
                          <td className="px-4 py-3">
                            <span className="font-mono text-xs font-semibold text-slate-800">
                              {column}
                            </span>
                            {suggestion && (
                              <span className="ml-2 rounded bg-blue-50 px-2 py-0.5 text-[10px] text-blue-700">
                                sugerido → {suggestion}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] text-slate-600">
                              {columnType}
                            </span>
                          </td>
                          <td className="max-w-[360px] truncate px-4 py-3 text-xs text-slate-500">
                            {displayValue(preview.rows[0]?.[column])}
                          </td>
                          <td className="px-4 py-3">
                            <select
                              value={sourceFor(mapping, column)}
                              onChange={(event) =>
                                assignColumn(column, event.target.value as RagField | "")
                              }
                              className="h-9 min-w-48 rounded-lg border border-slate-200 bg-white px-3 text-xs"
                            >
                              <option value="">No importar</option>
                              {RAG_FIELDS.map((field) => (
                                <option
                                  key={field}
                                  value={field}
                                  disabled={
                                    Boolean(mapping[field]) && mapping[field] !== column
                                  }
                                >
                                  {field}
                                </option>
                              ))}
                            </select>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {step === 3 && preview && (
            <div>
              <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h3 className="font-bold text-slate-900">
                    {preview.kind === "chunks"
                      ? "Vista previa de fragmentos"
                      : "Vista previa de columnas"}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    {preview.total_rows ?? preview.rows.length}{" "}
                    {preview.kind === "chunks" ? "fragmentos" : "filas"} ·{" "}
                    {preview.columns.length} columnas
                    {preview.kind !== "chunks"
                      ? ` · ${Object.keys(mapping).length} campos RAG`
                      : ""}
                  </p>
                </div>
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  {source === "synthetic"
                    ? "Destino: Validación humana"
                    : "Listo para crear"}
                </span>
              </div>
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="min-w-full text-left">
                  <thead className="bg-slate-50 text-[10px] uppercase text-slate-500">
                    <tr>
                      {preview.columns.map((field) => (
                        <th key={field} className="whitespace-nowrap px-4 py-3">
                          {field}
                          {sourceFor(mapping, field) && (
                            <span className="ml-1 font-semibold text-[#0038A8]">
                              → {sourceFor(mapping, field)}
                            </span>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs text-slate-600">
                    {mappedPreview.map((row, index) => (
                      <tr key={index}>
                        {preview.columns.map((field) => (
                          <td
                            key={field}
                            className="max-w-xs truncate whitespace-nowrap px-4 py-3"
                          >
                            {displayValue(row[field])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>

        <footer className="flex items-center justify-between border-t border-slate-200 bg-slate-50/60 px-6 py-4">
          <button
            type="button"
            onClick={() => (step === 1 ? onClose() : setStep((value) => value - 1))}
            disabled={busy}
            className="flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-white disabled:opacity-50"
          >
            {step > 1 && <ArrowLeft size={16} />}
            {step === 1 ? "Cancelar" : "Atrás"}
          </button>
          {step === 1 ? (
            <button
              type="button"
              onClick={() => void loadPreview()}
              disabled={busy}
              className="flex items-center gap-2 rounded-lg bg-[#0038A8] px-5 py-2.5 text-sm font-bold text-white shadow-sm disabled:opacity-50"
            >
              {busy ? "Obteniendo esquema…" : "Continuar"}
              {!busy && <ArrowRight size={16} />}
            </button>
          ) : step === 2 ? (
            <button
              type="button"
              onClick={() => {
                if (preview?.kind !== "chunks" && !mapping.prompt) {
                  setError("Asigna al menos una columna al campo prompt.");
                  return;
                }
                setError("");
                setStep(3);
              }}
              className="flex items-center gap-2 rounded-lg bg-[#0038A8] px-5 py-2.5 text-sm font-bold text-white"
            >
              {preview?.kind === "chunks" ? "Revisar fragmentos" : "Revisar datos"}{" "}
              <ArrowRight size={16} />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void finish()}
              disabled={busy}
              className="flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
            >
              {busy ? "Creando dataset…" : "Finalizar y crear"}
              {!busy && <Check size={16} />}
            </button>
          )}
        </footer>
      </div>
    </div>
  );
}
