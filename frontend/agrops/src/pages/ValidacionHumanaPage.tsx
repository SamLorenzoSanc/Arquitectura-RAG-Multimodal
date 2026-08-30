"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  BadgeCheck,
  Check,
  Loader2,
  Sparkles,
  X,
} from "lucide-react";
import { useOrganization } from "@/context";
import { useTranslation } from "@/i18n/I18nProvider";
import {
  decideHumanReview,
  extractMissingQuestions,
  fetchHumanReviews,
  type HumanReview,
} from "@/services";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { categoryLabel, reviewStatusLabel, EVAL_CATEGORIES } from "@/components/evaluation/labels";
import { queryKeys } from "@/lib/app";

type SourceFilter = "document_question" | "synthetic_dataset" | "chat" | "all";

export default function ValidacionHumanaPage({
  embedded = false,
}: {
  embedded?: boolean;
}) {
  const { t } = useTranslation();
  const { selectedOrg } = useOrganization();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<"pending" | "all">("pending");
  const [source, setSource] = useState<SourceFilter>("document_question");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [correction, setCorrection] = useState<Record<string, string>>({});
  const [keywordsDraft, setKeywordsDraft] = useState<Record<string, string>>({});
  const [categoryDraft, setCategoryDraft] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [generating, setGenerating] = useState(false);
  const autoForOrg = useRef<string | null>(null);

  const reviewsQuery = useQuery({
    queryKey: queryKeys.humanReviews(
      selectedOrg?.id || "none",
      filter,
      source,
    ),
    queryFn: () =>
      fetchHumanReviews({
        status: filter,
        source,
        organizationId: selectedOrg?.id,
      }),
    enabled: Boolean(selectedOrg?.id),
    refetchInterval: generating ? 4000 : false,
  });
  const data = reviewsQuery.data;
  const isLoading = reviewsQuery.isLoading;

  const reviews = data?.data ?? [];
  const pending = useMemo(
    () => reviews.filter((r) => r.status === "pending").length,
    [reviews],
  );

  const generateFromDocuments = async () => {
    if (!selectedOrg?.id || generating) return;
    setGenerating(true);
    setError(null);
    try {
      await extractMissingQuestions({ organizationId: selectedOrg.id });
      await qc.invalidateQueries({ queryKey: queryKeys.evaluationTests });
    } catch {
      setGenerating(false);
      setError(t("evaluation.generateFailed"));
    }
  };

  useEffect(() => {
    if (!selectedOrg?.id) return;
    if (source !== "document_question") return;
    if (reviewsQuery.isLoading || reviewsQuery.isError) return;
    if ((data?.pending ?? pending) > 0) {
      setGenerating(false);
      return;
    }
    if (autoForOrg.current === selectedOrg.id) return;
    autoForOrg.current = selectedOrg.id;
    void generateFromDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedOrg?.id, source, data?.pending, reviewsQuery.isLoading, reviewsQuery.isError]);

  useEffect(() => {
    if (!generating) return;
    const timer = window.setTimeout(() => setGenerating(false), 120_000);
    return () => window.clearTimeout(timer);
  }, [generating]);

  useEffect(() => {
    if (reviewsQuery.isError) {
      setError(t("evaluation.loadQueueFailed"));
    }
  }, [reviewsQuery.isError]);

  const decide = async (
    review: HumanReview,
    status: "approved" | "rejected" | "corrected",
  ) => {
    setBusyId(review.id);
    setError(null);
    const expected =
      correction[review.id] ?? review.answer ?? "";
    const keywords = (keywordsDraft[review.id] ?? (review.keywords || []).join(", "))
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const category = categoryDraft[review.id] || review.category || "direct_fact";
    if (status !== "rejected" && !expected.trim()) {
      setError(t("evaluation.approveHint"));
      setBusyId(null);
      return;
    }
    try {
      await decideHumanReview(review.id, {
        status,
        reviewer_notes: notes[review.id],
        corrected_answer:
          status === "rejected" ? undefined : expected,
        question: review.question,
        keywords,
        category,
      });
      await qc.invalidateQueries({ queryKey: ["human-reviews"] });
      await qc.invalidateQueries({ queryKey: queryKeys.evaluationTests });
    } catch {
      setError(t("evaluation.saveFailed"));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className={embedded ? "space-y-6" : "flex flex-col gap-4 pb-8"}>
      {!embedded && (
      <header className="rounded-2xl border border-blue-100 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold uppercase tracking-wider text-amber-800">
            {t("evaluation.hitl")}
          </span>
          <span className="text-xs font-medium text-slate-400">
            {t("evaluation.humanInTheLoop")}
          </span>
        </div>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-black text-blue-950">
          <BadgeCheck size={22} />
          {t("evaluation.humanValidation")}
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          {t("evaluation.pageDescription")}
        </p>
      </header>
      )}
      {embedded && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-bold text-slate-900">
            {t("evaluation.embeddedTitle")}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {t("evaluation.embeddedDescription")}
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
          {t("evaluation.sourceDocumentQuestion")}
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
          {t("evaluation.sourceSynthetic")}
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
          {t("evaluation.sourceChat")}
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
          {t("evaluation.pending", { n: data?.pending ?? pending })}
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
          {t("evaluation.all")}
        </button>
        {source === "document_question" && (
          <button
            type="button"
            disabled={generating}
            onClick={() => {
              autoForOrg.current = null;
              void generateFromDocuments();
            }}
            className="inline-flex items-center gap-1 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800 disabled:opacity-50"
          >
            {generating ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Sparkles size={13} />
            )}
            {generating ? t("evaluation.generatingQuestions") : t("evaluation.generateFromDocs")}
          </button>
        )}
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-2 text-xs font-semibold text-red-700">
          {error}
        </p>
      )}

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 size={16} className="animate-spin" />
          {t("evaluation.loadingQueue")}
        </div>
      ) : reviews.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          {generating ? (
            <p className="inline-flex items-center gap-2">
              <Loader2 size={16} className="animate-spin" />
              {t("evaluation.extractingQuestions")}
            </p>
          ) : (
            <>
              <p>{t("evaluation.emptyPending")}</p>
              <button
                type="button"
                onClick={() => {
                  autoForOrg.current = null;
                  void generateFromDocuments();
                }}
                className="mt-4 inline-flex items-center gap-1 rounded-xl bg-emerald-700 px-3 py-2 text-xs font-bold text-white"
              >
                <Sparkles size={13} /> {t("evaluation.generateFromDocs")}
              </button>
            </>
          )}
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
                    ? t("evaluation.sourceLabelDocument")
                    : review.source === "synthetic_dataset"
                      ? t("evaluation.sourceLabelSynthetic")
                      : t("evaluation.sourceLabelRag")}
                </span>
                {review.category && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
                    {categoryLabel(t,review.category)}
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
                  {reviewStatusLabel(t, review.status)}
                </span>
              </div>
              <h2 className="mt-2 text-sm font-bold text-slate-900">
                {review.question}
              </h2>
              {review.status !== "pending" && (review.keywords || []).length > 0 && (
                <p className="mt-1 text-[11px] text-slate-500">
                  {t("evaluation.keywords")} {(review.keywords || []).join(", ")}
                </p>
              )}
              {review.answer && review.status !== "pending" && (
                <div className="mt-2 rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                    {t("evaluation.referenceAnswer")}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                    {review.answer}
                  </p>
                </div>
              )}
              {(review.rationale || review.context_snippet) && (
                <p className="mt-2 text-[11px] text-slate-500">
                  {t("evaluation.whyExtracted")} {review.rationale || review.context_snippet}
                </p>
              )}
              {review.status === "pending" && (
                <div className="mt-3 space-y-2">
                  <label className="block text-[10px] font-bold uppercase tracking-wide text-slate-400">
                    {t("evaluation.expectedAnswer")}
                    <textarea
                      value={correction[review.id] ?? review.answer ?? ""}
                      onChange={(e) =>
                        setCorrection((prev) => ({
                          ...prev,
                          [review.id]: e.target.value,
                        }))
                      }
                      rows={3}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-normal normal-case text-slate-800 outline-none focus:border-blue-400 focus:bg-white"
                    />
                  </label>
                  <label className="block text-[10px] font-bold uppercase tracking-wide text-slate-400">
                    {t("evaluation.keywordsLabel")}
                    <input
                      value={
                        keywordsDraft[review.id] ??
                        (review.keywords || []).join(", ")
                      }
                      onChange={(e) =>
                        setKeywordsDraft((prev) => ({
                          ...prev,
                          [review.id]: e.target.value,
                        }))
                      }
                      placeholder={t("evaluation.keywordsPlaceholder")}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-normal normal-case text-slate-800 outline-none focus:border-blue-400 focus:bg-white"
                    />
                  </label>
                  <label className="block text-[10px] font-bold uppercase tracking-wide text-slate-400">
                    {t("evaluation.category")}
                    <select
                      value={
                        categoryDraft[review.id] ||
                        review.category ||
                        "direct_fact"
                      }
                      onChange={(e) =>
                        setCategoryDraft((prev) => ({
                          ...prev,
                          [review.id]: e.target.value,
                        }))
                      }
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-normal normal-case text-slate-800 outline-none focus:border-blue-400 focus:bg-white"
                    >
                      {EVAL_CATEGORIES.map((id) => (
                        <option key={id} value={id}>
                          {categoryLabel(t,id)}
                        </option>
                      ))}
                      {review.category &&
                        !EVAL_CATEGORIES.includes(
                          review.category as (typeof EVAL_CATEGORIES)[number],
                        ) && (
                          <option value={review.category}>
                            {categoryLabel(t,review.category)}
                          </option>
                        )}
                    </select>
                  </label>
                  <textarea
                    value={notes[review.id] ?? ""}
                    onChange={(e) =>
                      setNotes((prev) => ({ ...prev, [review.id]: e.target.value }))
                    }
                    placeholder={t("evaluation.reviewerNotes")}
                    rows={2}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:bg-white"
                  />
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busyId === review.id}
                      onClick={() => void decide(review, "approved")}
                      className="inline-flex items-center gap-1 rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
                    >
                      <Check size={13} /> {t("evaluation.approveToBank")}
                    </button>
                    <button
                      type="button"
                      disabled={busyId === review.id}
                      onClick={() => void decide(review, "rejected")}
                      className="inline-flex items-center gap-1 rounded-xl bg-red-600 px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
                    >
                      <X size={13} /> {t("evaluation.reject")}
                    </button>
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
