"use client";

import { CheckCircle2, Circle, Loader2, Sparkles } from "lucide-react";

import LiveRagFlowDiagram, {
  type RagFlowMode,
} from "@/components/LiveRagFlowDiagram";
import { useTranslation } from "@/i18n/I18nProvider";
import type { LiveProcessStep, RagFlowNodeId, RagFlowNodeState } from "@/types";

type Props = {
  steps: LiveProcessStep[];
  draftAnswer?: string;
  open?: boolean;
  onToggle?: () => void;
  model?: string;
  flowMode?: RagFlowMode;
  flowNodes?: Partial<Record<RagFlowNodeId, RagFlowNodeState>>;
  flowCaption?: string;
};

function StepIcon({ status }: { status: LiveProcessStep["status"] }) {
  if (status === "running") {
    return (
      <Loader2
        size={13}
        className="shrink-0 animate-spin text-[color:var(--agro-primary)]"
      />
    );
  }
  if (status === "done") {
    return (
      <CheckCircle2 size={13} className="shrink-0 text-emerald-600" />
    );
  }
  if (status === "error") {
    return <Circle size={13} className="shrink-0 text-red-500" />;
  }
  return <Circle size={13} className="shrink-0 text-slate-300" />;
}

export default function LiveReasoningPanel({
  steps,
  draftAnswer,
  open = true,
  onToggle,
  model,
  flowMode = "agentic",
  flowNodes = {},
  flowCaption,
}: Props) {
  const { t } = useTranslation();

  return (
    <div className="max-w-3xl w-full rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100/70 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <Sparkles
            size={14}
            className="animate-spin text-[color:var(--agro-primary)]"
          />
          <span>
            {t("chat.liveProcess")}
            {model ? ` · ${model}` : ""}
          </span>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
          {open ? t("chat.hide") : t("chat.show")}
        </span>
      </button>

      {open && (
        <div className="border-t border-slate-100 px-4 py-3 space-y-3">
          <LiveRagFlowDiagram
            mode={flowMode}
            nodes={flowNodes}
            caption={flowCaption}
          />

          <ol className="space-y-2">
            {steps.map((step) => (
              <li
                key={step.id}
                className="flex items-start gap-2 text-xs text-slate-600"
              >
                <StepIcon status={step.status} />
                <div className="min-w-0 flex-1">
                  <p
                    className={
                      step.status === "running"
                        ? "font-semibold text-slate-800 animate-pulse"
                        : "font-medium text-slate-700"
                    }
                  >
                    {step.label}
                  </p>
                  {step.detail ? (
                    <p className="mt-0.5 line-clamp-3 font-mono text-[11px] text-slate-500 whitespace-pre-wrap">
                      {step.detail}
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>

          {draftAnswer ? (
            <div className="rounded-lg border border-[color:var(--agro-border)] bg-[color:var(--agro-pill)]/40 px-3 py-2">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-[color:var(--agro-primary)]">
                {t("chat.liveAnswer")}
              </p>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                {draftAnswer}
                <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-[color:var(--agro-primary)] align-middle" />
              </p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
