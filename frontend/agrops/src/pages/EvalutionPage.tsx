"use client";

import { useSearchParams } from "react-router-dom";
import { useOrganization } from "@/context/OrganizationContext";
import { useTranslation } from "@/i18n/I18nProvider";
import AnnotatePanel from "@/components/evaluation/AnnotatePanel";
import AuditDashboard from "@/components/evaluation/AuditDashboard";
import BankPanel from "@/components/evaluation/BankPanel";
import ConfigurableEvaluationLab from "@/components/evaluation/ConfigurableEvaluationLab";
import EvaluationWorkbench, {
  type WorkbenchView,
} from "@/components/evaluation/EvaluationWorkbench";
import RetrievalStrategyLab from "@/components/evaluation/RetrievalStrategyLab";
import SimpleRetrievalEval from "@/components/evaluation/SimpleRetrievalEval";

type LabTab = "auditoria" | "anotar" | "banco" | "retrieval" | "metricas";
type PageView = "simple" | WorkbenchView | "lab";

const WORKBENCH_VIEWS = new Set<string>(["dataset", "analysis", "embedding"]);

export default function EvaluationPage() {
  const { t } = useTranslation();
  const { selectedOrg } = useOrganization();
  const [searchParams, setSearchParams] = useSearchParams();

  const LAB_TABS: { id: LabTab; label: string }[] = [
    { id: "auditoria", label: t("evaluation.auditTab") },
    { id: "anotar", label: t("evaluation.annotateTab") },
    { id: "banco", label: t("evaluation.bankTab") },
    { id: "retrieval", label: t("evaluation.retrievalLabTab") },
    { id: "metricas", label: t("evaluation.datasetTab") },
  ];

  const tabParam = searchParams.get("tab");
  const datasetId = searchParams.get("dataset");
  const view: PageView = WORKBENCH_VIEWS.has(tabParam || "")
    ? (tabParam as WorkbenchView)
    : tabParam === "lab" ||
        LAB_TABS.some((item) => item.id === tabParam) ||
        Boolean(datasetId)
      ? "lab"
      : "simple";
  const labTab: LabTab = LAB_TABS.some((item) => item.id === tabParam)
    ? (tabParam as LabTab)
    : datasetId
      ? "metricas"
      : "auditoria";

  const setView = (next: PageView) => {
    setSearchParams(
      next === "simple"
        ? {}
        : next === "lab"
          ? { tab: "auditoria" }
          : { tab: next },
      { replace: true },
    );
  };
  const setLabTab = (next: LabTab) => {
    setSearchParams({ tab: next }, { replace: true });
  };

  if (view === "simple") {
    return (
      <SimpleRetrievalEval onOpenLab={() => setView("lab")} />
    );
  }

  return (
    <div className="flex flex-col gap-4 pb-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">
            {t("evaluation.labTitle")}
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            {t("evaluation.labDescription")}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setView("simple")}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
        >
          {t("evaluation.backToSimpleEval")}
        </button>
      </div>

      {view !== "lab" ? (
        <EvaluationWorkbench
          view={view}
          onViewChange={(next) => setView(next)}
        />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-1">
            {LAB_TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setLabTab(item.id)}
                className={`rounded-t-xl px-4 py-2 text-sm font-semibold ${
                  labTab === item.id
                    ? "bg-white text-[color:var(--agro-primary)] shadow-sm ring-1 ring-slate-200"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          {labTab === "auditoria" && <AuditDashboard />}
          {labTab === "anotar" && <AnnotatePanel />}
          {labTab === "banco" && <BankPanel />}
          {labTab === "retrieval" && (
            <RetrievalStrategyLab
              key={selectedOrg?.id ?? "none"}
              organizationId={selectedOrg?.id ?? ""}
            />
          )}
          {labTab === "metricas" && (
            <ConfigurableEvaluationLab
              organizationId={selectedOrg?.id ?? ""}
              initialDatasetId={searchParams.get("dataset") ?? undefined}
            />
          )}
        </div>
      )}
    </div>
  );
}
