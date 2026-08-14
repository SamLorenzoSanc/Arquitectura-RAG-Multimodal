import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import api from "@/api";
import { queryKeys } from "@/lib/queryKeys";
import { useKnowledgeBases } from "@/hooks/useCachedApi";
import { useOrganization } from "@/context/OrganizationContext";

export type DistanceMetric = "cosine" | "euclidean" | "manhattan";

const DISTANCE_METRICS: {
  value: DistanceMetric;
  label: string;
  description: string;
}[] = [
  {
    value: "cosine",
    label: "Coseno",
    description:
      "Similitud angular entre embeddings. La más adecuada para texto semántico.",
  },
  {
    value: "euclidean",
    label: "Euclídea (L2)",
    description: "Distancia geométrica entre vectores en el espacio de embeddings.",
  },
  {
    value: "manhattan",
    label: "Manhattan (L1)",
    description: "Suma de diferencias absolutas entre dimensiones.",
  },
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

function metricLabel(metric: DistanceMetric) {
  return DISTANCE_METRICS.find((item) => item.value === metric)?.label ?? metric;
}

export default function AnnotatePanel() {
  const { selectedOrg } = useOrganization();
  const qc = useQueryClient();
  const { data: kbList } = useKnowledgeBases(selectedOrg?.id);
  const knowledgeBases = kbList ?? [];

  const [knowledgeBaseId, setKnowledgeBaseId] = useState("");
  const [distanceMetric, setDistanceMetric] = useState<DistanceMetric>("cosine");
  const [question, setQuestion] = useState("");
  const [chunks, setChunks] = useState<RetrievedChunk[]>([]);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

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
          "No se pudo ejecutar el retrieval.",
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
    const selected = chunks.find((chunk) => chunk.id === selectedChunkId);
    const outOfKnowledge = selected?.flag_out_of_knowledge || false;
    if (!question.trim() || (!selectedChunkId && !outOfKnowledge)) {
      setError("Selecciona el chunk correcto o marca fuera de conocimiento.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.post("/chat/simulator/save-dataset", {
        question: question.trim(),
        selected_chunk_id: selectedChunkId,
        selected_chunk_ids: selectedChunkId ? [selectedChunkId] : [],
        flags: {
          different_info: selected?.flag_different_info || false,
          out_of_knowledge: outOfKnowledge,
        },
      });
      setMessage("Pregunta anotada y añadida al banco unificado.");
      setQuestion("");
      setChunks([]);
      setSelectedChunkId(null);
      await qc.invalidateQueries({ queryKey: queryKeys.evaluationTests });
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "No se pudo guardar la anotación.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-bold text-slate-900">
          Simulador de retrieval
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Lanza una pregunta, elige la distancia y marca el chunk que contiene
          la información correcta. Esa anotación alimenta el banco y las
          métricas.
        </p>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="block text-xs font-semibold text-slate-700">
            Base de conocimiento
            <select
              value={knowledgeBaseId}
              onChange={(event) => setKnowledgeBaseId(event.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
            >
              <option value="">Todas las del tenant</option>
              {knowledgeBases.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-semibold text-slate-700">
            Métrica de distancia
            <select
              value={distanceMetric}
              onChange={(event) =>
                setDistanceMetric(event.target.value as DistanceMetric)
              }
              disabled={searching}
              className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
            >
              {DISTANCE_METRICS.map((metric) => (
                <option key={metric.value} value={metric.value}>
                  {metric.label}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-[11px] font-normal text-slate-400">
              {
                DISTANCE_METRICS.find((item) => item.value === distanceMetric)
                  ?.description
              }
            </span>
          </label>
        </div>

        <form onSubmit={search} className="mt-4 flex gap-3">
          <input
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ej: ¿Cuál es el protocolo fitosanitario del pimiento?"
            className="h-10 flex-1 rounded-md border border-slate-300 px-4 text-sm outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={searching || !question.trim()}
            className="rounded-md bg-slate-900 px-5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {searching ? "Buscando…" : "Probar retrieval"}
          </button>
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

      {chunks.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                Chunks recuperados
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Marca el fragmento que responde de verdad a la pregunta.
              </p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
              {chunks.length} resultados · {metricLabel(distanceMetric)}
            </span>
          </div>

          <div className="space-y-4">
            {chunks.map((chunk) => {
              const selected = selectedChunkId === chunk.id;
              return (
                <div
                  key={chunk.id}
                  className={`relative rounded-lg border p-4 ${
                    selected
                      ? "border-emerald-500 bg-emerald-50/50"
                      : "border-slate-200 bg-slate-50"
                  }`}
                >
                  <div className="absolute left-4 top-4">
                    <input
                      type="radio"
                      name="selected_chunk"
                      checked={selected}
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
                            {chunk.title || "Sin título"}
                          </h4>
                        </div>
                        <p className="mt-1 text-[10px] text-slate-400">
                          ID: {chunk.id}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="block text-[9px] uppercase text-slate-400">
                          Distancia
                        </span>
                        <span className="font-mono text-sm font-bold text-blue-600">
                          {chunk.distance != null
                            ? chunk.distance.toFixed(4)
                            : "—"}
                        </span>
                      </div>
                    </div>
                    {chunk.description && (
                      <p className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-600">
                        {chunk.description}
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
                        Información distinta
                      </label>
                      <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
                        <input
                          type="checkbox"
                          checked={chunk.flag_out_of_knowledge || false}
                          onChange={() =>
                            toggleFlag(chunk.id, "flag_out_of_knowledge")
                          }
                        />
                        Fuera de conocimiento
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
                ? "Chunk correcto seleccionado."
                : "Selecciona el chunk correcto antes de guardar."}
            </p>
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving || !selectedChunkId}
              className="rounded-md bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? "Guardando…" : "Guardar en el banco"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
