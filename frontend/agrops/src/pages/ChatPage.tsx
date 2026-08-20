"use client";

import { useState, useRef, useMemo, useEffect, type FormEvent } from "react";
import {
  Send,
  Database,
  Loader2,
  ChevronDown,
  Sparkles,
  Cpu,
} from "lucide-react";
import ChatService from "@/services/chat.service";
import { useRagRuntimeConfig } from "@/components/evaluation/FrozenRagConfigBar";
import { useOrganization } from "@/context/OrganizationContext";
import { useTranslation } from "@/i18n/I18nProvider";
import { CanaryFlag } from "@/components/BrandMark";
import type {
  ChatContext,
  RetrievalInfo,
  Message,
  ModeComparisonSide,
  AgentTraceStep,
} from "@/types/chat";

// Modelos de lenguaje gratuitos disponibles en Ollama
const OLLAMA_MODELS = [
  { id: "llama3.2:latest", name: "Llama 3.2 (General / Rápido)" },
  { id: "gpt-oss:latest", name: "GPT-OSS (Alta Precisión)" },
  { id: "deepseek-r1:1.5b", name: "DeepSeek R1 (Razonamiento lógico)" },
  { id: "llama3:latest", name: "Llama 3 (Equilibrado)" },
  { id: "phi3:latest", name: "Phi-3 (Eficiente)" },
  { id: "llama3.2-vision:latest", name: "Llama 3.2 Vision (Multimodal)" },
];

type RagMode = "hybrid" | "agentic" | "compare";

const MAX_VISIBLE_CONVERSATIONS = 5;

function takeRecentConversations(list: any[]) {
  return [...list]
    .sort(
      (a, b) =>
        new Date(b.updated_at ?? 0).getTime() -
        new Date(a.updated_at ?? 0).getTime(),
    )
    .slice(0, MAX_VISIBLE_CONVERSATIONS);
}

export default function ChatPage() {
  const { t } = useTranslation();
  const { selectedOrg } = useOrganization();

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // ESTADO PARA EL MODELO SELECCIONADO
  const [selectedModel, setSelectedModel] = useState<string>("llama3.2:latest");

  const [thinkingStep, setThinkingStep] = useState<string>("");
  const [isThinkingOpen, setIsThinkingOpen] = useState(true);

  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [context, setContext] = useState<ChatContext[]>([]);
  const [retrieval, setRetrieval] = useState<RetrievalInfo | null>(null);
  const [retrievalDetails, setRetrievalDetails] = useState<any | null>(null);

  type StepState = "pending" | "running" | "completed" | "error";

  const [pipelineSteps, setPipelineSteps] = useState<
    { id: string; label: string; state: StepState; items?: any[] }[]
  >([]);

  const [conversations, setConversations] = useState<any[]>([]);
  const [useRag, setUseRag] = useState(true);
  const [ragMode, setRagMode] = useState<RagMode>("agentic");
  const workspaceName = selectedOrg?.name ?? "AgroPS";
  const [comparison, setComparison] = useState<{
    hybrid?: ModeComparisonSide;
    agentic?: ModeComparisonSide;
    note?: string;
  } | null>(null);
  const [agentTrace, setAgentTrace] = useState<AgentTraceStep[] | null>(null);
  const [architectureLabel, setArchitectureLabel] = useState<string | null>(
    null,
  );

  // Mostrar parámetros RAG
  interface RagParams {
    embedding_model: string;
    distance_metric: string;
    retrieval_k: number;
    bm25_k: number;
    rrf_k: number;
    candidate_k: number;
    final_k: number;
    temperature: number;
    use_reranking: boolean;
    reranker_model?: string;
    reranker_batch_size?: number;
  }

  const [ragParams, setRagParams] = useState<RagParams>({
    embedding_model: "nomic-embed-text",
    distance_metric: "cosine",
    retrieval_k: 12,
    bm25_k: 12,
    rrf_k: 60,
    candidate_k: 20,
    final_k: 8,
    temperature: 0,
    use_reranking: false,
    reranker_model: "BAAI/bge-reranker-v2-m3",
    reranker_batch_size: 16,
  });
  const runtimeConfig = useRagRuntimeConfig();
  useEffect(() => {
    const cfg = runtimeConfig.data;
    if (!cfg) return;
    setRagParams((current) => ({
      ...current,
      embedding_model: cfg.embedding_model,
      retrieval_k: cfg.retrieval_k,
      bm25_k: cfg.bm25_k,
      rrf_k: cfg.rrf_k,
      final_k: cfg.final_k,
      temperature: cfg.temperature,
      use_reranking: cfg.use_reranker,
    }));
  }, [runtimeConfig.data]);

  const [showRagParams, setShowRagParams] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const [relatedQuestions, setRelatedQuestions] = useState<string[]>([]);

  const generateQuestionFromSnippet = (text?: string | null) => {
    if (!text) return null;
    const cleaned = text.replace(/\s+/g, " ").trim();
    const first = cleaned.split(/[\.\?\!\n]/)[0] || cleaned;
    const words = first.split(/\s+/).slice(0, 10).join(" ");
    const noPdf = words.replace(/\.pdf/gi, "");
    const trimmed = noPdf.trim();
    if (!trimmed) return null;
    return t("chat.relatedQuestionTemplate", { topic: trimmed });
  };

  const getRelatedQuestions = (
    rd: any,
    fromApi?: string[] | null,
  ): string[] => {
    if (fromApi && fromApi.length > 0) {
      return [...new Set(fromApi.map(String))].slice(0, 6);
    }
    if (!rd) return [];
    if (Array.isArray(rd.related_questions) && rd.related_questions.length > 0) {
      const fromDetails: string[] = rd.related_questions.map((q: unknown) =>
        String(q),
      );
      return [...new Set(fromDetails)].slice(0, 6);
    }
    const items: any[] = rd.candidates ?? rd.dense_original ?? [];
    const qs: string[] = items
      .map((c) => {
        const txt =
          c.page_content ??
          c.metadata?.text ??
          c.metadata?.snippet ??
          c.metadata?.title ??
          "";
        return generateQuestionFromSnippet(txt);
      })
      .filter((q): q is string => typeof q === "string" && q.length > 0);
    return [...new Set(qs)].slice(0, 6);
  };

  const openConversation = async (id: string) => {
    try {
      const data = await ChatService.getConversation(id);
      setConversationId(data.conversation_id);
      setMessages(
        data.messages.map((msg: any) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.created_at || Date.now()),
        })),
      );
    } catch (error) {
      console.error("Error al abrir conversación:", error);
    }
  };

  const contextCharacters = useMemo(() => {
    return context.reduce(
      (total, chunk) => total + chunk.page_content.length,
      0,
    );
  }, [context]);

  const createNewChat = () => {
    setConversationId(null);
    setMessages([]);
    setContext([]);
    setRetrieval(null);
    setRetrievalDetails(null);
    setRelatedQuestions([]);
  };

  useEffect(() => {
    createNewChat();
    loadConversations();
  }, [selectedOrg?.id]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, thinkingStep]);

  const estimatedTokens = useMemo(() => {
    return Math.round(contextCharacters / 4);
  }, [contextCharacters]);

  const loadConversations = async () => {
    try {
      const data = await ChatService.listConversations();
      setConversations(takeRecentConversations(data ?? []));
    } catch (error) {
      console.error("Error al listar conversaciones:", error);
    }
  };

  const handleSendMessage = async (e: FormEvent) => {
    e.preventDefault();

    if (!inputValue.trim() || isLoading) return;

    const question = inputValue.trim();

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);

    setInputValue("");
    setIsLoading(true);
    setIsGenerating(false);

    setThinkingStep(
      !useRag
        ? t("chat.generatingNoRag", { model: selectedModel })
        : ragMode === "compare"
          ? t("chat.compareThinking", { model: selectedModel })
          : ragMode === "hybrid"
            ? t("chat.hybridThinking")
            : t("chat.agenticThinking"),
    );

    try {
      const history = updatedMessages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

      setPipelineSteps([
        { id: "rewrite", label: "Query Rewriting", state: "running" },
        { id: "embed", label: "Embedding + Dense Retrieval", state: "running" },
        { id: "bm25", label: "BM25 Retrieval", state: "running" },
        { id: "rrf", label: "RRF Fusion", state: "running" },
        { id: "rerank", label: "Cross-Encoder Rerank", state: "running" },
        { id: "final", label: "Final Top-K", state: "running" },
      ]);
      setIsGenerating(true);
      setRelatedQuestions([]);

      // Una sola llamada: evita /retrieve + /chat (ahorra latencia duplicada).
      ChatService.send({
        question,
        conversation_id: conversationId,
        history,
        organization_id: selectedOrg?.id,
        organization_name: selectedOrg?.name,
        use_rag: useRag,
        rag_mode: useRag ? ragMode : "hybrid",
        model: selectedModel,
        use_query_rewrite: false,
        use_reranking: ragParams.use_reranking,
        retrieval_k: ragParams.retrieval_k,
        final_k: ragParams.final_k,
        temperature: ragParams.temperature,
      })
        .then((response) => {
          if (response.conversation_id) {
            setConversationId(response.conversation_id);
            setConversations((prev) => {
              const exists = prev.some(
                (c) => c.id === response.conversation_id,
              );
              if (exists) {
                return takeRecentConversations(
                  prev.map((c) =>
                    c.id === response.conversation_id
                      ? { ...c, updated_at: new Date().toISOString() }
                      : c,
                  ),
                );
              }
              return takeRecentConversations([
                {
                  id: response.conversation_id,
                  title: question.substring(0, 40),
                  updated_at: new Date().toISOString(),
                },
                ...prev,
              ]);
            });
          }

          setContext(response.context ?? []);
          setRetrieval(response.retrieval ?? null);
          setRetrievalDetails(response.retrieval_details ?? null);
          setComparison(response.comparison ?? null);
          setAgentTrace(response.agent_trace ?? null);
          setArchitectureLabel(response.architecture ?? response.rag_mode ?? null);
          setRelatedQuestions(
            getRelatedQuestions(
              response.retrieval_details,
              response.related_questions,
            ),
          );

          if (response.retrieval_details) {
            const rd = response.retrieval_details;
            const updated = [
              {
                id: "rewrite",
                label: "Query Rewriting",
                state: "completed",
                items: [
                  {
                    original: rd.retrieval?.original_query ?? rd.original_query,
                    rewritten: rd.rewritten_query,
                  },
                ],
              },
              {
                id: "embed",
                label: "Embedding + Dense Retrieval",
                state: "completed",
                items:
                  rd.dense_original?.slice?.(0, rd.retrieval_k) ??
                  rd.dense_original ??
                  [],
              },
              {
                id: "bm25",
                label: "BM25 Retrieval",
                state: "completed",
                items:
                  rd.bm25_original?.slice?.(0, rd.bm25_k) ??
                  rd.bm25_original ??
                  [],
              },
              {
                id: "rrf",
                label: "RRF Fusion",
                state: "completed",
                items: rd.candidates ?? [],
              },
              {
                id: "rerank",
                label: "Cross-Encoder Rerank",
                state: "completed",
                items: rd.candidates?.slice?.(0, rd.candidate_k) ?? [],
              },
              {
                id: "final",
                label: "Final Top-K",
                state: "completed",
                items: response.context ?? [],
              },
            ];

            setPipelineSteps(updated as any);
          } else {
            setPipelineSteps((prev) =>
              prev.map((s) => ({ ...s, state: "completed" })),
            );
          }

          const assistantMessage: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content:
              response.comparison?.hybrid && response.comparison?.agentic
                ? [
                    t("chat.comparisonTitle"),
                    "",
                    `**${t("chat.hybridRag")}** (${response.comparison.hybrid.architecture ?? "Dense+BM25+RRF"} · ${response.comparison.hybrid.latency_ms ?? "—"} ms)`,
                    "",
                    response.comparison.hybrid.answer?.trim() || t("chat.noAnswer"),
                    "",
                    "---",
                    "",
                    `**${t("chat.agenticRag")}** (${response.comparison.agentic.architecture ?? "tools"} · ${response.comparison.agentic.latency_ms ?? "—"} ms)`,
                    "",
                    response.comparison.agentic.answer?.trim() || t("chat.noAnswer"),
                    "",
                    response.comparison.note
                      ? `_${response.comparison.note}_`
                      : "",
                  ]
                    .filter(Boolean)
                    .join("\n")
                : response.answer?.trim() ||
                  t("chat.emptyResponse"),
            timestamp: new Date(),
            sources: [],
            pendingReview: Boolean(response.review_id),
          };

          const rd = response.retrieval_details;
          const sourceChunks =
            (response.context ?? []).length > 0
              ? response.context
              : (rd?.chunks ?? rd?.candidates ?? rd?.dense_original ?? []);
          if (sourceChunks.length) {
            assistantMessage.sources = sourceChunks.slice(0, 8).map((c: any) => ({
              source:
                c.metadata?.source ??
                c.source ??
                c.metadata?.title ??
                c.metadata?.document_id,
              score:
                c.metadata?.score ??
                c.metadata?.rrf_score ??
                c.metadata?.distance ??
                c.metadata?.cross_encoder_score ??
                c.metadata?.bm25_score,
              chunk_id: c.metadata?.chunk_id,
              snippet: (c.page_content || "").substring(0, 220),
            }));
          }

          setMessages((prev) => [...prev, assistantMessage]);
        })
        .catch((error) => {
          console.error("Error enviando mensaje:", error);
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: t("chat.noResponse"),
              timestamp: new Date(),
            },
          ]);
        })
        .finally(() => {
          setIsGenerating(false);
          setIsLoading(false);
          setThinkingStep("");
        });
    } catch (error) {
      console.error("Error enviando mensaje:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: t("chat.noResponse"),
          timestamp: new Date(),
        },
      ]);
      setContext([]);
      setIsLoading(false);
      setIsGenerating(false);
      setThinkingStep("");
    }
  };

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-xl border border-[color:var(--agro-border)] bg-[color:var(--agro-canvas)]">
      <div className="shrink-0 border-b border-[color:var(--agro-border)] bg-white px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <CanaryFlag className="h-7 w-10 shrink-0" />
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[color:var(--agro-primary)]">
                  {t("chat.assistant")}
                </h4>
                <span className="rounded-full border border-[color:var(--agro-border)] bg-[color:var(--agro-pill)] px-2 py-0.5 text-[10px] font-bold text-[color:var(--agro-primary)]">
                  {useRag
                    ? ragMode === "hybrid"
                      ? t("chat.hybridRag")
                      : ragMode === "compare"
                        ? t("chat.modeCompare")
                        : t("chat.agenticRag")
                    : t("chat.modeNoRag")}
                </span>
                {architectureLabel && (
                  <span className="rounded-full border border-yellow-200 bg-[#FFD100]/20 px-2 py-0.5 text-[10px] font-bold text-[color:var(--agro-accent-ink)]">
                    {architectureLabel}
                  </span>
                )}
              </div>
              <h1 className="mt-1 text-2xl font-bold text-slate-900">
                {workspaceName}
              </h1>
            </div>
          </div>

          {/* SELECTOR DE MODELO LLM */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-600">
              {t("chat.allDocs", { org: workspaceName })}
            </div>
            {/* Selector de Modelos Ollama */}
            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 shrink-0 shadow-xs">
              <Cpu size={15} className="shrink-0 text-[color:var(--agro-accent-ink)]" />
              <label
                htmlFor="model-select"
                className="text-xs font-semibold text-slate-600 whitespace-nowrap"
              >
                {t("chat.model")}
              </label>
              <select
                id="model-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="bg-transparent text-xs font-bold text-slate-800 outline-none cursor-pointer pr-1"
              >
                {OLLAMA_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>
            {/* RAG parameters quick view */}
            <div className="hidden sm:flex flex-col gap-1 rounded-md border border-slate-100 bg-white px-3 py-2 text-xs text-slate-700">
              <div className="flex items-center gap-2">
                <span className="font-semibold">{t("chat.ragLabel")}</span>
                <button
                  onClick={() => setShowRagParams((v) => !v)}
                  className="ml-2 text-xs text-slate-500 hover:text-slate-700"
                >
                  {showRagParams ? t("chat.hide") : t("chat.show")}
                </button>
              </div>
              {showRagParams && (
                <div className="grid grid-cols-2 gap-2 text-[12px]">
                  <div className="text-slate-500">{t("chat.embedding")}</div>
                  <div className="text-slate-700 truncate">
                    {ragParams.embedding_model}
                  </div>

                  <div className="text-slate-500">{t("chat.distance")}</div>
                  <div className="text-slate-700">
                    {ragParams.distance_metric}
                  </div>

                  <div className="text-slate-500">{t("chat.retrievalK")}</div>
                  <div className="text-slate-700">{ragParams.retrieval_k}</div>

                  <div className="text-slate-500">{t("chat.bm25K")}</div>
                  <div className="text-slate-700">{ragParams.bm25_k}</div>

                  <div className="text-slate-500">{t("chat.rrfK")}</div>
                  <div className="text-slate-700">{ragParams.rrf_k}</div>

                  <div className="text-slate-500">{t("chat.candidateK")}</div>
                  <div className="text-slate-700">{ragParams.candidate_k}</div>

                  <div className="text-slate-500">{t("chat.finalK")}</div>
                  <div className="text-slate-700">{ragParams.final_k}</div>

                  <div className="text-slate-500">{t("chat.temperature")}</div>
                  <div className="text-slate-700">
                    {ragParams.temperature.toFixed(1)}
                  </div>

                  <div className="text-slate-500">{t("chat.reranker")}</div>
                  <div className="text-slate-700 truncate">
                    {ragParams.use_reranking
                      ? ragParams.reranker_model
                      : t("chat.off")}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden min-h-0">
        <aside className="w-[260px] shrink-0 border-r border-gray-200 bg-white p-4 flex flex-col min-h-0">
          <button
            onClick={createNewChat}
            className="mb-4 flex shrink-0 cursor-pointer items-center justify-center rounded-lg bg-[color:var(--agro-primary)] px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-[color:var(--agro-primary-hover)]"
          >
            {t("chat.newChat")}
          </button>

          <h3 className="mb-3 text-xs font-semibold uppercase text-gray-400 shrink-0">
            {t("chat.conversations")}
          </h3>

          <div className="min-h-0 flex-1 space-y-2 overflow-hidden pr-1">
            {conversations.length === 0 && (
              <p className="text-sm text-gray-400">{t("chat.noChats")}</p>
            )}
            {conversations.map((chat) => (
              <button
                key={chat.id}
                onClick={() => openConversation(chat.id)}
                className={`min-w-0 w-full cursor-pointer rounded-lg px-3 py-3 text-left transition-colors hover:bg-slate-100 ${conversationId === chat.id ? "bg-[color:var(--agro-pill)] font-semibold text-[color:var(--agro-primary)]" : ""}`}
              >
                <p className="truncate text-sm font-medium">{chat.title}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(chat.updated_at).toLocaleDateString()}
                </p>
              </button>
            ))}
          </div>
        </aside>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-gray-50">
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 sm:px-6 sm:py-6">
            {messages.length === 0 && !isLoading ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center max-w-md">
                  <h2 className="mb-3 text-2xl font-bold text-slate-900">
                    {t("chat.assistant")}
                  </h2>
                  <p className="text-sm text-gray-500 leading-relaxed">
                    {t("chat.emptyHintExtended")}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-6">
                {messages.map((message: Message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-2xl rounded-xl px-5 py-4 shadow-sm ${
                        message.role === "user"
                          ? "bg-[color:var(--agro-primary)] text-white"
                          : "border border-gray-200 bg-white text-gray-800"
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex-1">
                          <p className="whitespace-pre-wrap text-sm leading-relaxed break-words">
                            {message.content}
                          </p>
                          {message.role === "assistant" && message.pendingReview && (
                            <p className="mt-2 text-[11px] font-semibold text-[color:var(--agro-accent-ink)]">
                              {t("chat.hitlQueue")}
                            </p>
                          )}
                          <p
                            className={`mt-3 text-[11px] ${
                              message.role === "user"
                                ? "text-blue-100"
                                : "text-gray-400"
                            }`}
                          >
                            {message.timestamp.toLocaleTimeString()}
                          </p>
                        </div>

                        {/* Inline sources for assistant messages */}
                        {message.role === "assistant" &&
                          message.sources &&
                          message.sources.length > 0 && (
                            <div className="w-56 shrink-0">
                              <div className="rounded-md border bg-gray-50 p-2 text-xs">
                                <div className="font-semibold text-slate-700 mb-2">
                                  {t("chat.sources")}
                                </div>
                                <div className="space-y-2">
                                  {message.sources.map((s, i) => (
                                    <div key={i} className="truncate">
                                      <div className="font-medium text-slate-800 truncate">
                                        {s.source}
                                      </div>
                                      {s.snippet && (
                                        <div className="text-gray-500 text-[11px] line-clamp-3 whitespace-normal">
                                          {s.snippet}
                                        </div>
                                      )}
                                      <div className="text-gray-500 text-[11px] truncate">
                                        {s.score
                                          ? typeof s.score === "number"
                                            ? s.score.toFixed(4)
                                            : String(s.score)
                                          : ""}{" "}
                                        {s.chunk_id ? `· ${s.chunk_id}` : ""}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          )}
                      </div>
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="max-w-xl w-full rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden transition-all">
                      <button
                        onClick={() => setIsThinkingOpen(!isThinkingOpen)}
                        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100/70 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <Sparkles
                            size={14}
                            className="animate-spin text-[color:var(--agro-primary)]"
                          />
                          <span>{t("chat.generating", { model: selectedModel })}</span>
                        </div>
                        <ChevronDown
                          size={14}
                          className={`text-slate-400 transition-transform duration-200 ${
                            isThinkingOpen ? "rotate-180" : ""
                          }`}
                        />
                      </button>

                      {isThinkingOpen && (
                        <div className="px-4 py-3 bg-white border-t border-slate-100 flex items-center gap-3 text-xs text-slate-500 font-mono">
                          <Loader2
                            size={13}
                            className="shrink-0 animate-spin text-[color:var(--agro-primary)]"
                          />
                          <p className="animate-pulse truncate">
                            {thinkingStep || t("chat.processing")}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                {/* Related questions (from retrievalDetails) */}
                {comparison && (
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <div className="rounded-xl border border-[color:var(--agro-border)] bg-[color:var(--agro-pill)]/60 p-4">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <h3 className="text-sm font-bold text-[color:var(--agro-primary)]">
                          {t("chat.hybridRag")}
                        </h3>
                        <span className="text-[10px] font-semibold text-[color:var(--agro-primary)]">
                          {comparison.hybrid?.latency_ms ?? "—"} ms
                        </span>
                      </div>
                      <p className="mb-2 text-[11px] text-slate-600">
                        {comparison.hybrid?.architecture ??
                          "hybrid_dense_bm25_rrf"}
                      </p>
                      <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-800">
                        {comparison.hybrid?.answer}
                      </p>
                    </div>
                    <div className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-4">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <h3 className="text-sm font-bold text-indigo-900">
                          {t("chat.agenticRag")}
                        </h3>
                        <span className="text-[10px] font-semibold text-indigo-700">
                          {comparison.agentic?.latency_ms ?? "—"} ms
                        </span>
                      </div>
                      <p className="mb-2 text-[11px] text-indigo-800/80">
                        {comparison.agentic?.architecture ?? "agentic_langgraph_rag"}
                      </p>
                      <p className="mb-3 whitespace-pre-wrap text-xs leading-relaxed text-slate-800">
                        {comparison.agentic?.answer}
                      </p>
                      {(comparison.agentic?.agent_trace?.length ?? 0) > 0 && (
                        <div className="space-y-1.5 border-t border-indigo-100 pt-2">
                          <p className="text-[10px] font-bold uppercase tracking-wide text-indigo-700">
                            {t("chat.toolsExecuted")}
                          </p>
                          {comparison.agentic?.agent_trace?.map((step, idx) => (
                            <div
                              key={`${step.tool}-${idx}`}
                              className="rounded-lg bg-white/80 px-2 py-1.5 text-[11px]"
                            >
                              <span className="font-semibold text-indigo-900">
                                {step.tool}
                              </span>
                              <span className="text-slate-500">
                                {" "}
                                · {step.latency_ms} ms ·{" "}
                                {step.ok ? "ok" : "error"}
                              </span>
                              <p className="mt-0.5 line-clamp-2 text-slate-600">
                                {step.reason}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {!comparison && agentTrace && agentTrace.length > 0 && (
                  <div className="rounded-xl border border-indigo-200 bg-white p-4">
                    <h3 className="mb-2 text-sm font-bold text-indigo-900">
                      {t("chat.agentTrace")}
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {agentTrace.map((step, idx) => (
                        <span
                          key={`${step.tool}-${idx}`}
                          className="rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-800"
                        >
                          {step.tool} · {step.latency_ms} ms
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {relatedQuestions.length > 0 && (
                  <div className="mt-6 rounded-lg border bg-white p-4">
                    <h4 className="font-semibold mb-2">
                      {t("chat.relatedQuestions")}
                    </h4>
                    <div className="flex flex-col gap-2 text-sm">
                      {relatedQuestions.map((q: string, idx: number) => (
                          <button
                            key={idx}
                            className="text-left p-2 rounded hover:bg-gray-50"
                            onClick={() => setInputValue(q)}
                          >
                            {q}
                          </button>
                        ))}
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Right-side retrieval panel removed: sources now shown inline next to the assistant message and related questions appear under the chat. */}
      </div>

      <div className="shrink-0 border-t border-gray-200 bg-white px-4 py-3 sm:px-6 sm:py-4">
        <form
          onSubmit={handleSendMessage}
          className="flex items-center gap-4 max-w-5xl mx-auto"
        >
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setUseRag(!useRag)}
              title={
                useRag
                  ? t("chat.ragActive")
                  : t("chat.ragOff")
              }
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-semibold transition-colors cursor-pointer ${
                useRag
                  ? "border-[color:var(--agro-border)] bg-[color:var(--agro-pill)] text-[color:var(--agro-primary)]"
                  : "bg-gray-100 text-gray-500 border-gray-200"
              }`}
            >
              <Database size={15} />
              <span>{t("chat.ragState", { state: useRag ? "ON" : "OFF" })}</span>
            </button>
            {useRag && (
              <select
                value={ragMode}
                onChange={(e) => setRagMode(e.target.value as RagMode)}
                title={t("chat.howItWorks")}
                className="rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs font-semibold text-slate-700 outline-none"
              >
                <option value="agentic">{t("chat.modeAgentic")}</option>
                <option value="hybrid">{t("chat.modeHybrid")}</option>
                <option value="compare">{t("chat.modeCompare")}</option>
              </select>
            )}
          </div>

          <div className="relative flex-1">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={t("chat.placeholder")}
              disabled={isLoading}
              className="w-full rounded-xl border border-gray-200 bg-gray-50/50 px-4 py-3 pr-12 text-sm text-slate-800 shadow-xs outline-none transition-all placeholder-gray-400 focus:border-[color:var(--agro-primary)] focus:bg-white"
            />
          </div>

          <button
            type="submit"
            disabled={!inputValue.trim() || isLoading}
            className="flex shrink-0 cursor-pointer items-center justify-center rounded-xl bg-[color:var(--agro-primary)] px-5 py-3 text-white shadow-sm transition-colors hover:bg-[color:var(--agro-primary-hover)] disabled:opacity-40"
          >
            {isLoading ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Send size={18} />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
