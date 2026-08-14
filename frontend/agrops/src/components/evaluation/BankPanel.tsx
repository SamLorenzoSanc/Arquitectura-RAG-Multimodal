import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import api from "@/api";
import { queryKeys } from "@/lib/queryKeys";
import { useEvaluationTests } from "@/hooks/useCachedApi";
import { categoryLabel } from "@/components/evaluation/labels";

type BankItem = {
  id: number;
  question: string;
  keywords: string[];
  reference_answer: string;
  category: string;
  source?: string;
  annotated?: boolean;
  split?: string;
};

const SOURCE_LABEL: Record<string, string> = {
  file: "JSON local",
  annotated: "Anotada",
  merged: "JSON + anotación",
  document: "HITL (documento)",
  hitl: "HITL (documento)",
};

export default function BankPanel() {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const { data, isLoading, refetch } = useEvaluationTests();
  const tests = (data as BankItem[] | undefined) ?? [];

  const upload = async (file: File) => {
    setUploading(true);
    setError(null);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file, file.name);
      const response = await api.post("/chat/evaluation/upload-tests", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await qc.invalidateQueries({ queryKey: queryKeys.evaluationTests });
      await refetch();
      setMessage(
        `Banco actualizado: ${response.data.uploaded} preguntas en JSON` +
          (typeof response.data.imported === "number"
            ? ` · ${response.data.imported} nuevas en base de datos`
            : ""),
      );
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Error al subir el JSON.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-bold text-slate-900">Banco de preguntas</h2>
        <p className="mt-1 text-sm text-slate-500">
          Une el JSON/JSONL local con las anotaciones de chunks y las preguntas
          de documento aprobadas en Validación humana. Las métricas se calculan
          solo sobre este banco.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,text/json,.json,.jsonl"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {uploading ? "Subiendo…" : "Subir JSON / JSONL"}
          </button>
          <button
            type="button"
            onClick={() => void refetch()}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
          >
            Refrescar
          </button>
          <span className="text-xs text-slate-500">{tests.length} preguntas</span>
        </div>
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

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Cargando banco…</p>
        ) : tests.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-500">
            El banco está vacío. Sube un JSON o anota chunks en la pestaña
            Anotar.
          </p>
        ) : (
          <div className="max-h-[640px] overflow-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-white text-slate-500">
                <tr>
                  <th className="px-2 py-2">#</th>
                  <th className="px-2 py-2">Pregunta</th>
                  <th className="px-2 py-2">Origen</th>
                  <th className="px-2 py-2">Categoría</th>
                  <th className="px-2 py-2">Keywords</th>
                </tr>
              </thead>
              <tbody>
                {tests.map((test) => (
                  <tr key={test.id} className="border-t border-slate-100">
                    <td className="px-2 py-2 text-slate-500">{test.id}</td>
                    <td className="px-2 py-2">
                      <p className="font-semibold text-slate-800">{test.question}</p>
                      {test.reference_answer && (
                        <p className="mt-1 line-clamp-2 text-[11px] text-slate-500">
                          Esperada: {test.reference_answer}
                        </p>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          test.source === "annotated"
                            ? "bg-emerald-100 text-emerald-800"
                            : test.source === "merged"
                              ? "bg-indigo-100 text-indigo-800"
                              : test.source === "hitl" || test.source === "document"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {SOURCE_LABEL[test.source || "file"] || test.source}
                      </span>
                    </td>
                    <td className="px-2 py-2">{categoryLabel(test.category)}</td>
                    <td className="px-2 py-2 text-slate-500">
                      {(test.keywords || []).join(", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
