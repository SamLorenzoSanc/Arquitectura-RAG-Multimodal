"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Loader2, MessageCircle, Send, Sparkles, X } from "lucide-react";

import { CanaryFlag } from "@/components/BrandMark";
import { useOrganization } from "@/context/OrganizationContext";
import { useTranslation } from "@/i18n/I18nProvider";
import ChatService from "@/services/chat.service";
import { useSyncedTemperature } from "@/components/evaluation/FrozenRagConfigBar";
import type { AgentTraceStep, Message } from "@/types/chat";

function relatedFromResponse(
  related?: string[] | null,
  retrievalDetails?: { related_questions?: unknown[] } | null,
): string[] {
  const fromApi = related?.filter(Boolean) ?? [];
  if (fromApi.length) return [...new Set(fromApi)].slice(0, 4);
  const extra = retrievalDetails?.related_questions ?? [];
  return [...new Set(extra.map(String))].slice(0, 4);
}

export default function ChatWidget() {
  const { t } = useTranslation();
  const { selectedOrg } = useOrganization();
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [thinking, setThinking] = useState("");
  const [relatedQuestions, setRelatedQuestions] = useState<string[]>([]);
  const [trace, setTrace] = useState<AgentTraceStep[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { temperature } = useSyncedTemperature();

  const starters = useMemo(
    () => [
      t("widget.starter1"),
      t("widget.starter2"),
      t("widget.starter3"),
      t("widget.starter4"),
    ],
    [t],
  );

  useEffect(() => {
    setMessages([]);
    setConversationId(null);
    setRelatedQuestions([]);
    setTrace([]);
  }, [selectedOrg?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, open, thinking]);

  const visibleRelated =
    relatedQuestions.length > 0 ? relatedQuestions : starters;

  const resetChat = () => {
    setMessages([]);
    setConversationId(null);
    setRelatedQuestions([]);
    setTrace([]);
    setThinking("");
  };

  const ask = async (rawQuestion: string) => {
    const question = rawQuestion.trim();
    if (
      !question ||
      isLoading ||
      !selectedOrg?.id
    ) {
      return;
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInputValue("");
    setIsLoading(true);
    setRelatedQuestions([]);
    setTrace([]);
    setThinking(t("widget.searching"));

    try {
      const response = await ChatService.send({
        question,
        conversation_id: conversationId,
        history: nextMessages.map((msg) => ({
          role: msg.role,
          content: msg.content,
        })),
        organization_id: selectedOrg.id,
        organization_name: selectedOrg.name,
        use_rag: true,
        rag_mode: "agentic",
        use_query_rewrite: false,
        use_reranking: false,
        retrieval_k: 12,
        final_k: 8,
        temperature,
      });
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
      const sources = (response.context ?? []).slice(0, 6).map((chunk) => ({
        source: chunk.metadata?.source || chunk.metadata?.title,
        snippet: chunk.page_content?.slice(0, 220),
      }));
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            response.answer?.trim() || t("widget.insufficientInfo"),
          timestamp: new Date(),
          sources,
          pendingReview: Boolean(response.review_id),
        },
      ]);
      setTrace(response.agent_trace ?? []);
      setRelatedQuestions(
        relatedFromResponse(response.related_questions, response.retrieval_details),
      );
    } catch (error: unknown) {
      const detail =
        error instanceof Error
          ? error.message
          : t("widget.queryFailed");
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: detail,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
      setThinking("");
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    void ask(inputValue);
  };

  return (
    <div className="pointer-events-none fixed right-4 bottom-4 z-[1200] flex flex-col items-end gap-3 sm:right-6 sm:bottom-6">
      {open && (
        <section className="pointer-events-auto flex h-[min(640px,calc(100vh-7rem))] w-[min(420px,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-[color:var(--agro-border)] bg-white shadow-2xl shadow-slate-900/20">
          <div className="agro-flag-bar" aria-hidden>
            <span />
            <span />
            <span />
          </div>
          <header className="flex items-start justify-between gap-3 bg-[color:var(--agro-primary)] px-4 py-3 text-white">
            <div className="flex min-w-0 items-start gap-2.5">
              <CanaryFlag className="mt-0.5 h-6 w-9 shrink-0 border-white/30" />
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 text-sm font-bold">
                  <Sparkles size={15} />
                  {t("widget.title")}
                </p>
                <p className="mt-0.5 truncate text-[11px] text-white/80">
                  {selectedOrg
                    ? t("chat.allDocs", { org: selectedOrg.name })
                    : t("common.selectOrganization")}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 gap-1">
              <button
                type="button"
                onClick={resetChat}
                className="rounded-lg px-2 py-1 text-[11px] font-semibold text-white/90 hover:bg-white/10"
              >
                {t("widget.new")}
              </button>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg p-1.5 hover:bg-white/10"
                aria-label={t("widget.closeAssistant")}
              >
                <X size={16} />
              </button>
            </div>
          </header>

          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-[color:var(--agro-canvas)] px-3 py-3">
            {messages.length === 0 && (
              <div className="rounded-xl border border-[color:var(--agro-border)] bg-white p-3">
                <p className="text-xs font-semibold text-slate-800">
                  {t("widget.askAboutDocs")}
                </p>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                  {t("widget.askHint")}
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "ml-auto bg-[color:var(--agro-primary)] text-white"
                    : "bg-white text-slate-800 shadow-sm ring-1 ring-slate-100"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                  <p className="mt-2 border-t border-slate-100 pt-1.5 text-[10px] text-slate-500">
                    {t("widget.sources")}{" "}
                    {msg.sources
                      .map((s) => s.source)
                      .filter(Boolean)
                      .slice(0, 4)
                      .join(" · ") || t("widget.indexedDocs")}
                  </p>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Loader2 size={14} className="animate-spin text-[color:var(--agro-primary)]" />
                {thinking || t("widget.inferring")}
              </div>
            )}

            {!isLoading && trace.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {trace.map((step, idx) => (
                  <span
                    key={`${step.tool}-${idx}`}
                    className="rounded-full bg-[color:var(--agro-pill)] px-2 py-0.5 text-[10px] font-semibold text-[color:var(--agro-primary)]"
                  >
                    {step.tool}
                  </span>
                ))}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {visibleRelated.length > 0 && !isLoading && (
            <div className="border-t border-slate-100 bg-white px-3 py-2">
              <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">
                {t("widget.suggestions")}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {visibleRelated.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => void ask(question)}
                    className="max-w-full rounded-full border border-blue-100 bg-[color:var(--agro-pill)] px-2.5 py-1 text-left text-[11px] font-medium text-[color:var(--agro-primary)] hover:bg-blue-100"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-2 border-t border-slate-100 bg-white p-3"
          >
            <div className="flex items-center gap-2">
            <input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={
                !selectedOrg
                  ? t("common.selectOrganization")
                  : t("widget.placeholder")
              }
              disabled={isLoading || !selectedOrg}
              className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-[color:var(--agro-primary)] focus:bg-white"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading || !selectedOrg}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[color:var(--agro-primary)] text-white disabled:opacity-40"
              aria-label={t("widget.sendQuestion")}
            >
              {isLoading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Send size={16} />
              )}
            </button>
            </div>
          </form>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="pointer-events-auto flex items-center gap-2 rounded-full bg-[color:var(--agro-primary)] py-3 pl-3 pr-4 text-white shadow-lg shadow-blue-900/30 transition hover:scale-105 hover:bg-[color:var(--agro-primary-hover)]"
        aria-label={open ? t("widget.closeAssistant") : t("widget.openAssistant")}
      >
        {open ? (
          <X size={22} />
        ) : (
          <>
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/15">
              <MessageCircle size={18} />
            </span>
            <span className="pr-1 text-sm font-semibold">{t("widget.assistant")}</span>
          </>
        )}
      </button>
    </div>
  );
}
