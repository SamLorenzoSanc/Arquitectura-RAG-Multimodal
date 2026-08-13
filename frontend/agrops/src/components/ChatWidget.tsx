"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  FileText,
  Loader2,
  MessageCircle,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import ChatService from "@/services/chat.service";
import { useOrganization } from "@/context/OrganizationContext";
import { useDocuments, useKnowledgeBases } from "@/hooks/useCachedApi";
import type { Message } from "@/types/chat";
import type { DocumentItem } from "@/types/document";

function docLabel(doc: DocumentItem) {
  return (doc.title || doc.filename || "documento")
    .replace(/\.pdf$/i, "")
    .replace(/[_-]+/g, " ")
    .trim();
}

const FARMER_STARTERS = [
  "Tengo goteros taponados: ¿cómo los limpio paso a paso y qué recambios llevo?",
  "¿Cómo podo el plátano y qué herramientas necesito?",
  "La cámara no mantiene el frío: ¿qué reviso y qué piezas pueden fallar?",
  "Hay manchas en hoja: ¿cómo identifico la plaga y qué tratamiento aplico?",
  "¿Cuál es el procedimiento de carga a reefer y qué controles de frío hago?",
];

function suggestionsFromDocuments(docs: DocumentItem[]): string[] {
  const fromTitles = docs.slice(0, 2).map(
    (doc) =>
      `Según ${docLabel(doc)}, ¿cuál es el procedimiento y qué herramientas o recambios indica?`,
  );
  return [...fromTitles, ...FARMER_STARTERS].slice(0, 5);
}

function relatedFromResponse(
  related?: string[] | null,
  retrievalDetails?: { related_questions?: unknown[] } | null,
): string[] {
  const fromApi = related?.filter(Boolean) ?? [];
  if (fromApi.length) return [...new Set(fromApi)].slice(0, 5);
  const extra = retrievalDetails?.related_questions ?? [];
  return [...new Set(extra.map(String))].slice(0, 5);
}

export default function ChatWidget() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { selectedOrg } = useOrganization();
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [relatedQuestions, setRelatedQuestions] = useState<string[]>([]);
  const [knowledgeBaseId, setKnowledgeBaseId] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: kbs } = useKnowledgeBases(selectedOrg?.id);
  const { data: documents } = useDocuments(knowledgeBaseId || undefined);

  const hideOnFullChat = pathname.startsWith("/dashboard/chat");

  useEffect(() => {
    if (kbs?.length && !knowledgeBaseId) {
      setKnowledgeBaseId(kbs[0].id);
    }
  }, [kbs, knowledgeBaseId]);

  useEffect(() => {
    setMessages([]);
    setConversationId(null);
    setRelatedQuestions([]);
    setKnowledgeBaseId("");
  }, [selectedOrg?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, open]);

  const starterQuestions = useMemo(
    () => suggestionsFromDocuments(documents ?? []),
    [documents],
  );

  const visibleRelated =
    relatedQuestions.length > 0 ? relatedQuestions : starterQuestions;

  const ask = async (rawQuestion: string) => {
    const question = rawQuestion.trim();
    if (!question || isLoading || !selectedOrg?.id) return;

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

    try {
      const response = await ChatService.send({
        question,
        conversation_id: conversationId,
        history: nextMessages.map((msg) => ({
          role: msg.role,
          content: msg.content,
        })),
        knowledge_base_id: knowledgeBaseId || undefined,
        organization_id: selectedOrg.id,
        organization_name: selectedOrg.name,
        use_rag: true,
        rag_mode: "hybrid",
      });
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          timestamp: new Date(),
          sources: (response.context ?? []).slice(0, 3).map((chunk) => ({
            source: chunk.metadata?.source || chunk.metadata?.title,
            snippet: chunk.page_content?.slice(0, 160),
          })),
        },
      ]);
      setRelatedQuestions(
        relatedFromResponse(response.related_questions, response.retrieval_details),
      );
    } catch (error: unknown) {
      const detail =
        error instanceof Error ? error.message : "No se pudo consultar la documentación";
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
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    void ask(inputValue);
  };

  if (hideOnFullChat) return null;

  return (
    <div className="pointer-events-none fixed right-4 bottom-4 z-[1200] flex flex-col items-end gap-3 sm:right-6 sm:bottom-6">
      {open && (
        <section className="pointer-events-auto flex h-[min(640px,calc(100vh-7rem))] w-[min(420px,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-slate-900/20">
          <header className="flex items-start justify-between gap-3 border-b border-slate-100 bg-[color:var(--agro-primary)] px-4 py-3 text-white">
            <div className="min-w-0">
              <p className="flex items-center gap-1.5 text-sm font-bold">
                <Sparkles size={15} />
                Asistente del agricultor
              </p>
              <p className="mt-0.5 truncate text-[11px] text-white/80">
                {selectedOrg
                  ? `Problemas de campo · ${selectedOrg.name}`
                  : "Selecciona una organización"}
              </p>
              {(documents?.length ?? 0) > 0 && (
                <p className="mt-1 flex items-center gap-1 text-[10px] text-white/75">
                  <FileText size={11} />
                  {documents!.length} documento{documents!.length === 1 ? "" : "s"}
                </p>
              )}
            </div>
            <div className="flex shrink-0 gap-1">
              <button
                type="button"
                onClick={() => {
                  setMessages([]);
                  setConversationId(null);
                  setRelatedQuestions([]);
                }}
                className="rounded-lg px-2 py-1 text-[11px] font-semibold text-white/90 hover:bg-white/10"
              >
                Nuevo
              </button>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg p-1.5 hover:bg-white/10"
                aria-label="Cerrar asistente"
              >
                <X size={16} />
              </button>
            </div>
          </header>

          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-slate-50 px-3 py-3">
            {messages.length === 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <p className="text-xs font-semibold text-slate-800">
                  Describe el problema de tu finca
                </p>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                  Te devolveré el procedimiento paso a paso, datos técnicos y las
                  herramientas o recambios necesarios. Usa una sugerencia o escribe
                  lo que te está pasando.
                </p>
                {(documents?.length ?? 0) === 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setOpen(false);
                      navigate("/dashboard/documentation");
                    }}
                    className="mt-3 text-[11px] font-semibold text-blue-700 hover:underline"
                  >
                    Ir a Documentación para subir archivos
                  </button>
                )}
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
                    Fuentes:{" "}
                    {msg.sources
                      .map((s) => s.source)
                      .filter(Boolean)
                      .slice(0, 2)
                      .join(" · ") || "documentación subida"}
                  </p>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Loader2 size={14} className="animate-spin" />
                Preparando procedimiento y recambios…
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {visibleRelated.length > 0 && !isLoading && (
            <div className="border-t border-slate-100 bg-white px-3 py-2">
              <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">
                Preguntas de campo
              </p>
              <div className="flex flex-wrap gap-1.5">
                {visibleRelated.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => void ask(question)}
                    className="max-w-full rounded-full border border-blue-100 bg-blue-50 px-2.5 py-1 text-left text-[11px] font-medium text-blue-800 hover:bg-blue-100"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 border-t border-slate-100 bg-white p-3"
          >
            <input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={
                selectedOrg
                  ? "Describe el problema (riego, plaga, frío, maquinaria…)"
                  : "Selecciona una organización"
              }
              disabled={isLoading || !selectedOrg}
              className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-blue-400 focus:bg-white"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading || !selectedOrg}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[color:var(--agro-primary)] text-white disabled:opacity-40"
              aria-label="Enviar pregunta"
            >
              {isLoading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Send size={16} />
              )}
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="pointer-events-auto flex h-14 w-14 items-center justify-center rounded-full bg-[color:var(--agro-primary)] text-white shadow-lg shadow-blue-900/30 transition hover:scale-105"
        aria-label={open ? "Cerrar asistente" : "Abrir asistente del agricultor"}
      >
        {open ? <X size={22} /> : <MessageCircle size={24} />}
      </button>
    </div>
  );
}
