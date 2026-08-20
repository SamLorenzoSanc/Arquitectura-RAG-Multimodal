import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import api from "@/api";
import { queryKeys } from "@/lib/queryKeys";
import { useOrganization } from "@/context/OrganizationContext";
import { useEvaluationTests } from "@/hooks/useCachedApi";
import { useTranslation } from "@/i18n/I18nProvider";
import { categoryLabel } from "@/components/evaluation/labels";

type BankItem = {
  id: number;
  question: string;
  keywords: string[];
  reference_answer: string;
  category: string;
  source?: string;
  source_file?: string;
  page?: string;
  validated?: boolean;
  annotated?: boolean;
  split?: string;
};

function sourceBadgeLabel(
  t: (key: string) => string,
  test: BankItem,
): string {
  if (test.source === "hitl" || test.source === "document") {
    return test.validated === false
      ? t("evalExtended.docPending")
      : t("evalExtended.docValidated");
  }
  const map: Record<string, string> = {
    file: t("evalExtended.sourceFile"),
    annotated: t("evalExtended.sourceAnnotated"),
    merged: t("evalExtended.sourceMerged"),
    document: t("evalExtended.sourceHitl"),
    hitl: t("evalExtended.sourceHitl"),
  };
  return map[test.source || "file"] || test.source || "—";
}

export default function BankPanel() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { selectedOrg } = useOrganization();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const { data, isLoading, refetch } = useEvaluationTests();
  const tests = (data as BankItem[] | undefined) ?? [];

  const upload = async (file: File) => {
    if (!selectedOrg?.id) {
      setError(t("evalExtended.selectOrgFirst"));
      return;
    }
    setUploading(true);
    setError(null);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file, file.name);
      const response = await api.post("/chat/evaluation/upload-tests", form, {
        headers: { "Content-Type": "multipart/form-data" },
        params: {
          organization_id: selectedOrg.id,
          replace_dataset: true,
        },
      });
      await qc.invalidateQueries({ queryKey: queryKeys.evaluationTests });
      await refetch();
      const imported = Number(response.data.imported ?? 0);
      const updated = Number(response.data.updated ?? 0);
      setMessage(
        t("evalExtended.bankUpdatedDb", {
          uploaded: response.data.uploaded ?? 0,
          imported: imported + updated,
        }),
      );
    } catch (err: any) {
      setError(
        err.response?.data?.detail || err.message || t("evalExtended.uploadFailed"),
      );
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-bold text-slate-900">
          {t("evalExtended.bankTitle")}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          {t("evalExtended.bankIntroPanel")}
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
            {uploading ? t("evalExtended.uploading") : t("evalExtended.uploadJson")}
          </button>
          <button
            type="button"
            onClick={() => void refetch()}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
          >
            {t("evalExtended.refresh")}
          </button>
          <span className="text-xs text-slate-500">
            {t("evalExtended.bankCount", { count: tests.length })}
          </span>
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
          <p className="p-6 text-sm text-slate-500">
            {t("evalExtended.loadingBank")}
          </p>
        ) : tests.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-500">
            {t("evalExtended.emptyBankAnnotate")}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-white text-slate-500">
                <tr>
                  <th className="px-2 py-2">{t("evalExtended.colNumber")}</th>
                  <th className="px-2 py-2">{t("evalExtended.question")}</th>
                  <th className="px-2 py-2">{t("evalExtended.origin")}</th>
                  <th className="px-2 py-2">{t("evalExtended.colCategory")}</th>
                  <th className="px-2 py-2">{t("evalExtended.source")}</th>
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
                          {t("evalExtended.expectedPrefix")} {test.reference_answer}
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
                        {sourceBadgeLabel(t, test)}
                      </span>
                    </td>
                    <td className="px-2 py-2">{categoryLabel(t, test.category)}</td>
                    <td className="px-2 py-2 text-slate-500">
                      {[test.source_file?.replace(/^knowledge-base\//, ""), test.page]
                        .filter(Boolean)
                        .join(" · ") || "—"}
                    </td>
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
