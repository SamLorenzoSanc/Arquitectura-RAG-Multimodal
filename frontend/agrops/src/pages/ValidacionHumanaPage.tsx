"use client";

import { useMemo, useState } from "react";
import {
  BadgeCheck,
  Check,
  Loader2,
  Pencil,
  ShieldAlert,
  X,
} from "lucide-react";
import { useOrganization } from "@/context/OrganizationContext";
import {
  decideHumanReview,
  fetchHumanReviews,
  type HumanReview,
} from "@/services/validation.service";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { categoryLabel, reviewStatusLabel } from "@/components/evaluation/labels";

type SourceFilter = "document_question" | "synthetic_dataset" | "chat" | "all";

export default function ValidacionHumanaPage({
  embedded = false,
}: {
  embedded?: boolean;
}) {
  const { selectedOrg } = useOrganization();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<"pending" | "all">("pending");
  const [source, setSource] = useState<SourceFilter>("document_question");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [correction, setCorrection] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["human-reviews", selectedOrg?.id, filter, source],
    queryFn: () =>
      fetchHumanReviews({
        status: filter,
        source,
        organizationId: selectedOrg?.id,
      }),
  });

  const reviews = data?.data ?? [];
  const pending = useMemo(
    () => reviews.filter((r) => r.status === "pending").length,
    [reviews],
  );

  const decide = async (
    review: HumanReview,
    status: "approved" | "rejected" | "corrected",
  ) => {
    setBusyId(review.id);
    setError(null);
    try {
      await decideHumanReview(review.id, {
        status,
        reviewer_notes: notes[review.id],
        corrected_answer:
          status === "corrected" ? correction[review.id] : undefined,
      });
      setEditing(null);
      await qc.invalidateQueries({ queryKey: ["human-reviews"] });
    } catch {
      setError("No se pudo guardar la validación.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className={embedded ? "space-y-6" : "min-h-screen space-y-6 bg-slate-50/50 p-8"}>
      {!embedded && (
      <header className="rounded-2xl border border-blue-100 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold uppercase tracking-wider text-amber-800">
            HITL
          </span>
          <span className="text-xs font-medium text-slate-400">
            Human-in-the-loop
          </span>
        </div>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-black text-blue-950">
          <BadgeCheck size={22} />
          Validación humana
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Al subir un documento se extraen preguntas de muestra. Un experto las
          aprueba, rechaza o corrige; solo las aceptadas entran en el banco de
          evaluación del RAG.
        </p>
      </header>
      )}
      {embedded && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-bold text-slate-900">
            Validación humana (HITL)
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Preguntas de muestra extraídas al subir documentos. Aprueba,
            rechaza o corrige la respuesta de referencia antes de usarlas en
            las métricas.
          </p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setSource("document_question")}
          className={`rounded-xl px-3 py-1.5 text-xs font-bold ${
            source === "document_question"
              ? "bg-emerald-700 text-white"
              : "border border-slate-200 bg-white text-slate-600"
          }`}
        >
          Preguntas de documento
        </button>
        <button
          type="button"
          onClick={() => setSource("synthetic_dataset")}
          className={`rounded-xl px-3 py-1.5 text-xs font-bold ${
            source === "synthetic_dataset"
              ? "bg-violet-700 text-white"
              : "border border-slate-200 bg-white text-slate-600"
          }`}
        >
          Datos sintéticos
        </button>
        <button
          type="button"
          onClick={() => setSource("chat")}
          className={`rounded-xl px-3 py-1.5 text-xs font-bold ${
            source === "chat"
              ? "bg-blue-700 text-white"
              : "border border-slate-200 bg-white text-slate-600"
          }`}
        >
          Respuestas del chat
        </button>
        <button
          type="button"
          onClick={() => setFilter("pending")}
          className={`rounded-xl px-3 py-1.5 text-xs font-bold ${
            filter === "pending"
              ? "bg-[#0038A8] text-white"
              : "border border-slate-200 bg-white text-slate-600"
          }`}
        >
          Pendientes ({data?.pending ?? pending})
        </button>
        <button
          type="button"
          onClick={() => setFilter("all")}
          className={`rounded-xl px-3 py-1.5 text-xs font-bold ${
            filter === "all"
              ? "bg-[#0038A8] text-white"
              : "border border-slate-200 bg-white text-slate-600"
          }`}
        >
          Todas
        </button>
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-2 text-xs font-semibold text-red-700">
          {error}
        </p>
      )}

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 size={16} className="animate-spin" />
          Cargando cola de revisión…
        </div>
      ) : reviews.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          No hay preguntas de muestra pendientes. Sube un documento en
          Documentación para extraerlas y enviarlas aquí.
        </div>
      ) : (
        <ul className="space-y-4">
          {reviews.map((review) => (
            <li
              key={review.id}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase">
                <span
                  className={`rounded-full px-2 py-0.5 ${
                    review.source === "document_question"
                      ? "bg-emerald-100 text-emerald-800"
                      : review.source === "synthetic_dataset"
                        ? "bg-violet-100 text-violet-800"
                        : "bg-blue-100 text-blue-800"
                  }`}
                >
                  {review.source === "document_question"
                    ? "Muestra del documento"
                    : review.source === "synthetic_dataset"
                      ? "Dataset sintético"
                      : "Respuesta RAG"}
                </span>
                {review.category && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
                    {categoryLabel(review.category)}
                  </span>
                )}
                {review.filename && (
                  <span className="rounded-full bg-slate-50 px-2 py-0.5 font-medium normal-case text-slate-500">
                    {review.filename}
                  </span>
                )}
                <span
                  className={`rounded-full px-2 py-0.5 ${
                    review.status === "pending"
                      ? "bg-amber-100 text-amber-800"
                      : review.status === "approved"
                        ? "bg-emerald-100 text-emerald-800"
                        : review.status === "corrected"
                          ? "bg-indigo-100 text-indigo-800"
                          : "bg-red-100 text-red-700"
                  }`}
                >
                  {reviewStatusLabel(review.status)}
                </span>
              </div>
              <h2 className="mt-2 text-sm font-bold text-slate-900">
                {review.question}
              </h2>
              {review.answer && (
                <div className="mt-2 rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                    Respuesta de referencia
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                    {review.answer}
                  </p>
                </div>
              )}
              {(review.rationale || review.context_snippet) && (
                <p className="mt-2 text-[11px] text-slate-500">
                  Por qué se extrae: {review.rationale || review.context_snippet}
                </p>
              )}
              {review.status === "pending" && (
                <div className="mt-3 space-y-2">
                  <textarea
                    value={notes[review.id] ?? ""}
                    onChange={(e) =>
                      setNotes((prev) => ({ ...prev, [review.id]: e.target.value }))
                    }
                    placeholder="Notas del revisor (opcional)"
                    rows={2}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:bg-white"
                  />
                  {editing === review.id && (
                    <textarea
                      value={correction[review.id] ?? review.answer ?? ""}
                      onChange={(e) =>
                        setCorrection((prev) => ({
                          ...prev,
                          [review.id]: e.target.value,
                        }))
                      }
                      rows={4}
                      className="w-full rounded-xl border border-blue-200 bg-blue-50/40 px-3 py-2 text-sm outline-none focus:border-blue-400"
                    />
                  )}
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busyId === review.id}
                      onClick={() => void decide(review, "approved")}
                      className="inline-flex items-center gap-1 rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
                    >
                      <Check size={13} /> Aprobar y pasar al banco
                    </button>
                    <button
                      type="button"
                      disabled={busyId === review.id}
                      onClick={() => void decide(review, "rejected")}
                      className="inline-flex items-center gap-1 rounded-xl bg-red-600 px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
                    >
                      <X size={13} /> Rechazar
                    </button>
                    {editing === review.id ? (
                      <button
                        type="button"
                        disabled={busyId === review.id}
                        onClick={() => void decide(review, "corrected")}
                        className="inline-flex items-center gap-1 rounded-xl bg-indigo-600 px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
                      >
                        <Pencil size={13} /> Guardar corrección
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setEditing(review.id);
                          setCorrection((prev) => ({
                            ...prev,
                            [review.id]: review.answer ?? "",
                          }));
                        }}
                        className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-700"
                      >
                        <ShieldAlert size={13} /> Corregir referencia
                      </button>
                    )}
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
