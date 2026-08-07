import { CheckCircle2, Loader2, AlertCircle, Circle } from "lucide-react";

type RagStep = {
  id: string;
  label: string;
  status: "pending" | "running" | "completed" | "error";
  detail?: string;
  duration?: number;
};

interface RagProgressProps {
  steps: RagStep[];
}

export function RagProgressBar({ steps }: RagProgressProps) {
  if (!steps || steps.length === 0) return null;

  // 1. Calcular porcentaje de progreso
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const hasError = steps.some((s) => s.status === "error");
  const progressPercentage = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="w-full space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
      {/* Cabecera con porcentaje */}
      <div className="flex items-center justify-between text-xs font-semibold">
        <span className="text-slate-700">
          {hasError ? (
            <span className="text-red-600 font-bold">Proceso interrumpido</span>
          ) : progressPercentage === 100 ? (
            <span className="text-emerald-600 font-bold">
              ¡Ingestión completada!
            </span>
          ) : (
            "Procesando documento..."
          )}
        </span>
        <span
          className={hasError ? "text-red-500" : "text-amber-600 font-bold"}
        >
          {progressPercentage}%
        </span>
      </div>

      {/* Barra de progreso visual */}
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full transition-all duration-500 ease-out ${
            hasError
              ? "bg-red-500"
              : progressPercentage === 100
                ? "bg-emerald-500"
                : "bg-amber-600"
          }`}
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      {/* Lista detallada de etapas del Pipeline */}
      <div className="mt-4 space-y-2.5">
        {steps.map((step) => (
          <div key={step.id} className="flex items-start gap-3 text-xs">
            <div className="mt-0.5 shrink-0">
              {step.status === "completed" && (
                <CheckCircle2 size={16} className="text-emerald-500" />
              )}
              {step.status === "running" && (
                <Loader2 size={16} className="animate-spin text-amber-600" />
              )}
              {step.status === "error" && (
                <AlertCircle size={16} className="text-red-500" />
              )}
              {step.status === "pending" && (
                <Circle size={16} className="text-slate-300" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <p
                className={`font-medium ${
                  step.status === "running"
                    ? "text-amber-700 font-semibold"
                    : step.status === "completed"
                      ? "text-slate-700"
                      : step.status === "error"
                        ? "text-red-600"
                        : "text-slate-400"
                }`}
              >
                {step.label}
              </p>
              {step.detail && (
                <p className="text-[11px] text-slate-500 truncate mt-0.5">
                  {step.detail}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
