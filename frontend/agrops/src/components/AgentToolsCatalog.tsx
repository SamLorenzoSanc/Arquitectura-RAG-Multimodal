"use client";

import { useMemo, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  ClipboardList,
  FlaskConical,
  HelpCircle,
  MessageSquareText,
  Scale,
  Search,
  Wrench,
} from "lucide-react";

import { useTranslation } from "@/i18n/I18nProvider";
import type { AgentTraceStep } from "@/types";

export type AgentToolId =
  | "search_knowledge_base"
  | "search_regulations"
  | "diagnose_crop"
  | "list_indexed_documents"
  | "query_operational_sql"
  | "recall_conversation";

type ToolDef = {
  id: AgentToolId;
  icon: typeof Search;
  titleKey: string;
  descKey: string;
  exampleKey: string;
};

const TOOLS: ToolDef[] = [
  {
    id: "search_knowledge_base",
    icon: Search,
    titleKey: "chat.toolSearchKbTitle",
    descKey: "chat.toolSearchKbDesc",
    exampleKey: "chat.toolSearchKbExample",
  },
  {
    id: "search_regulations",
    icon: Scale,
    titleKey: "chat.toolRegsTitle",
    descKey: "chat.toolRegsDesc",
    exampleKey: "chat.toolRegsExample",
  },
  {
    id: "diagnose_crop",
    icon: FlaskConical,
    titleKey: "chat.toolDiagnoseTitle",
    descKey: "chat.toolDiagnoseDesc",
    exampleKey: "chat.toolDiagnoseExample",
  },
  {
    id: "list_indexed_documents",
    icon: BookOpen,
    titleKey: "chat.toolListDocsTitle",
    descKey: "chat.toolListDocsDesc",
    exampleKey: "chat.toolListDocsExample",
  },
  {
    id: "query_operational_sql",
    icon: ClipboardList,
    titleKey: "chat.toolNotebookTitle",
    descKey: "chat.toolNotebookDesc",
    exampleKey: "chat.toolNotebookExample",
  },
  {
    id: "recall_conversation",
    icon: MessageSquareText,
    titleKey: "chat.toolMemoryTitle",
    descKey: "chat.toolMemoryDesc",
    exampleKey: "chat.toolMemoryExample",
  },
];

type Props = {
  agentTrace?: AgentTraceStep[] | null;
  onPickExample?: (question: string) => void;
  compact?: boolean;
};

export default function AgentToolsCatalog({
  agentTrace,
  onPickExample,
  compact = false,
}: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(!compact);

  const used = useMemo(() => {
    const ids = new Set<string>();
    for (const step of agentTrace ?? []) {
      if (step.tool) ids.add(step.tool);
    }
    return ids;
  }, [agentTrace]);

  return (
    <section className="rounded-xl border border-[color:var(--agro-border)] bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[color:var(--agro-pill)] text-[color:var(--agro-primary)]">
            <Wrench size={16} />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-bold text-slate-900">
              {t("chat.toolsCatalogTitle")}
            </p>
            <p className="truncate text-xs text-slate-500">
              {t("chat.toolsCatalogSubtitle")}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {used.size > 0 && (
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
              {t("chat.toolsUsedCount", { n: used.size })}
            </span>
          )}
          <span className="text-xs font-semibold text-slate-500">
            {open ? t("chat.hide") : t("chat.show")}
          </span>
        </div>
      </button>

      {open && (
        <div className="border-t border-[color:var(--agro-border)] px-4 py-3">
          <p className="mb-3 flex items-start gap-2 text-xs text-slate-600">
            <HelpCircle size={14} className="mt-0.5 shrink-0 text-slate-400" />
            {t("chat.toolsCatalogHint")}
          </p>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {TOOLS.map((tool) => {
              const Icon = tool.icon;
              const active = used.has(tool.id);
              return (
                <div
                  key={tool.id}
                  className={`rounded-lg border p-3 ${
                    active
                      ? "border-emerald-300 bg-emerald-50/70"
                      : "border-slate-200 bg-slate-50/80"
                  }`}
                >
                  <div className="mb-1.5 flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Icon
                        size={15}
                        className={
                          active
                            ? "text-emerald-700"
                            : "text-[color:var(--agro-primary)]"
                        }
                      />
                      <p className="text-xs font-bold text-slate-900">
                        {t(tool.titleKey)}
                      </p>
                    </div>
                    {active ? (
                      <CheckCircle2 size={14} className="text-emerald-600" />
                    ) : (
                      <span className="rounded bg-white px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-slate-400">
                        {t("chat.toolAvailable")}
                      </span>
                    )}
                  </div>
                  <p className="mb-2 text-[11px] leading-relaxed text-slate-600">
                    {t(tool.descKey)}
                  </p>
                  {onPickExample && (
                    <button
                      type="button"
                      onClick={() => onPickExample(t(tool.exampleKey))}
                      className="text-left text-[11px] font-semibold text-[color:var(--agro-primary)] hover:underline"
                    >
                      {t("chat.toolTryExample")}: “{t(tool.exampleKey)}”
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
