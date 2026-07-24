"use client";

import { useState, useRef, useMemo, useEffect, FormEvent } from "react";
import { Send, Upload, X, Database, Layers, Loader2, FileText, ChevronDown, Sparkles, Building, Cpu } from "lucide-react";
import ChatService from "@/services/chat.service";
import DocumentService from "@/services/document.service";
import KnowledgeService from "../services/knowledge.service";
import { useOrganization } from "@/context/OrganizationContext";

import type { DocumentItem } from "@/types/document";
import type {
    ChatContext,
    RetrievalInfo,
    Message
} from "@/types/chat";

// Modelos de lenguaje gratuitos disponibles en Ollama
const OLLAMA_MODELS = [
    { id: "llama3.2:latest", name: "Llama 3.2 (General / Rápido)" },
    { id: "gpt-oss:latest", name: "GPT-OSS (Alta Precisión)" },
    { id: "deepseek-r1:1.5b", name: "DeepSeek R1 (Razonamiento lógico)" },
    { id: "llama3:latest", name: "Llama 3 (Equilibrado)" },
    { id: "phi3:latest", name: "Phi-3 (Eficiente)" },
    { id: "llama3.2-vision:latest", name: "Llama 3.2 Vision (Multimodal)" }
];

export default function ChatPage() {
    const { selectedOrg } = useOrganization();

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [conversationId, setConversationId] = useState<string | null>(null);
    const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
    const [selectedCategory, setSelectedCategory] = useState("Misc");
    const [isLoading, setIsLoading] = useState(false);
    
    // ESTADO PARA EL MODELO SELECCIONADO
    const [selectedModel, setSelectedModel] = useState<string>("llama3.2:latest");

    const [thinkingStep, setThinkingStep] = useState<string>("");
    const [isThinkingOpen, setIsThinkingOpen] = useState(true);

    const [isUploadingModal, setIsUploadingModal] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [context, setContext] = useState<ChatContext[]>([]);
    const [retrieval, setRetrieval] = useState<RetrievalInfo | null>(null);

    const [kbs, setKbs] = useState<any[]>([]); 
    const [knowledgeBaseId, setKnowledgeBaseId] = useState<string>(""); 

    const [documents, setDocuments] = useState<DocumentItem[]>([]);
    const [conversations, setConversations] = useState<any[]>([]);
    const [useRag, setUseRag] = useState(true);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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
                    timestamp: new Date(msg.created_at || Date.now())
                }))
            );
        } catch (error) {
            console.error("Error al abrir conversación:", error);
        }
    };

    const fileInputRef = useRef<HTMLInputElement>(null);
    
    const contextCharacters = useMemo(() => {
        return context.reduce(
            (total, chunk) => total + chunk.page_content.length,
            0
        );
    }, [context]);

    const createNewChat = () => {
        setConversationId(null);
        setMessages([]);
        setContext([]);
        setRetrieval(null);
    };

    useEffect(() => {
        if (selectedOrg?.id) {
            createNewChat();
            initialize(selectedOrg.id);
            loadConversations(selectedOrg.id);
        }
    }, [selectedOrg?.id]);

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading, thinkingStep]);

    const estimatedTokens = useMemo(() => {
        return Math.round(contextCharacters / 4);
    }, [contextCharacters]);

    const loadConversations = async (orgId: string) => {
        try {
            const data = await ChatService.listConversations(orgId);
            setConversations(data);
        } catch (error) {
            console.error("Error al listar conversaciones:", error);
        }
    };

    const initialize = async (orgId: string) => {
        try {
            let kbList = [];
            if (typeof KnowledgeService.list === 'function') {
                kbList = await KnowledgeService.list(orgId);
            } else if (typeof KnowledgeService.getCurrent === 'function') {
                const currentKb = await KnowledgeService.getCurrent(orgId);
                if (currentKb) kbList = [currentKb];
            }

            setKbs(kbList || []);

            if (kbList && kbList.length > 0) {
                const defaultKbId = kbList[0].id;
                setKnowledgeBaseId(defaultKbId);
                fetchDocumentsForKb(defaultKbId);
            } else {
                setKnowledgeBaseId("");
                setDocuments([]);
            }
        } catch (err) {
            console.error("Error al inicializar KBs:", err);
        }
    };

    const fetchDocumentsForKb = async (kbId: string) => {
        if (!kbId) {
            setDocuments([]);
            return;
        }
        try {
            const docs = await DocumentService.list(kbId);
            setDocuments(docs || []);
        } catch (err) {
            console.error("Error al obtener documentos:", err);
            setDocuments([]);
        }
    };

    const handleKbChange = (newKbId: string) => {
        setKnowledgeBaseId(newKbId);
        fetchDocumentsForKb(newKbId);
    };

    const handleUploadFilesModal = async () => {
        if (!knowledgeBaseId || uploadedFiles.length === 0) return;

        setIsUploadingModal(true);
        try {
            for (const file of uploadedFiles) {
                await DocumentService.upload({
                    file,
                    knowledge_base_id: knowledgeBaseId,
                    title: file.name,
                    description: selectedCategory,
                });
            }
            
            await new Promise((resolve) => setTimeout(resolve, 2500));

            setUploadedFiles([]);
            setShowUploadModal(false);
            fetchDocumentsForKb(knowledgeBaseId);
        } catch (err) {
            console.error("Error al subir archivos:", err);
        } finally {
            setIsUploadingModal(false);
        }
    };

    const handleSendMessage = async (e: FormEvent) => {
        e.preventDefault();

        if (!inputValue.trim() || isLoading || !selectedOrg?.id) return;

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

        setThinkingStep(`Cargando modelo ${selectedModel} y analizando consulta en "${selectedOrg.name}"...`);
        
        try {
            await new Promise((r) => setTimeout(r, 400));
            if (useRag) {
                setThinkingStep("Recuperando vectores optimizados con qwen3-embedding...");
                await new Promise((r) => setTimeout(r, 600));
                setThinkingStep(`Sintetizando contexto documental con el modelo ${selectedModel}...`);
                await new Promise((r) => setTimeout(r, 500));
            }

            const history = updatedMessages.map((msg) => ({
                role: msg.role,
                content: msg.content,
            }));

            // PETICIÓN CON EL MODELO DE LENGUAJE SELECCIONADO
            const response = await ChatService.send({
                question,
                conversation_id: conversationId,
                history,
                knowledge_base_id: useRag ? (knowledgeBaseId || undefined) : undefined,
                use_rag: useRag, 
                organization_id: selectedOrg.id,
                organization_name: selectedOrg.name,
                model: selectedModel // Envía el modelo de Ollama seleccionado
            });

            if (response.conversation_id) {
                setConversationId(response.conversation_id);
                setConversations(prev => {
                    const exists = prev.some(c => c.id === response.conversation_id);
                    if (exists) return prev;
                    return [
                        ...prev,
                        {
                            id: response.conversation_id,
                            title: question.substring(0, 40),
                            updated_at: new Date().toISOString()
                        }
                    ];
                });
            }

            setContext(response.context ?? []);
            setRetrieval(response.retrieval ?? null);
            
            const assistantMessage: Message = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: response.answer?.trim() || "El asistente no devolvió ninguna respuesta.",
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error("Error enviando mensaje:", error);
            setMessages((prev) => [
                ...prev,
                {
                    id: crypto.randomUUID(),
                    role: "assistant",
                    content: "No se pudo obtener respuesta del asistente.",
                    timestamp: new Date(),
                },
            ]);
            setContext([]);
        } finally {
            setIsLoading(false);
            setThinkingStep("");
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setUploadedFiles(Array.from(e.target.files));
        }
    };
   
    if (!selectedOrg) {
        return (
            <div className="flex h-full w-full flex-col items-center justify-center bg-gray-50">
                <div className="text-center">
                    <h2 className="text-2xl font-bold text-slate-900 mb-2">Ningún Workspace seleccionado</h2>
                    <p className="text-gray-500">Por favor, selecciona una organización en el menú lateral para acceder al chat.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-full w-full flex-col bg-gray-50 overflow-hidden">
            <div className="border-b border-gray-200 bg-white px-8 py-4 shrink-0">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-2">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-600">CHAT MULTI-INQUILINO</h4>
                            <span className="bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1">
                                <Building size={10} />
                                Aislamiento Activo
                            </span>
                        </div>
                        <h1 className="mt-1 text-2xl font-bold text-slate-900">{selectedOrg.name}</h1>
                    </div>

                    {/* SELECTORES DE MODELO LLM Y KNOWLEDGE BASE */}
                    <div className="flex flex-wrap items-center gap-3">
                        {/* Selector de Modelos Ollama */}
                        <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 shrink-0 shadow-xs">
                            <Cpu size={15} className="text-emerald-600 shrink-0" />
                            <label htmlFor="model-select" className="text-xs font-semibold text-slate-600 whitespace-nowrap">
                                Modelo:
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

                        {/* Selector de Base de Conocimiento */}
                        {useRag && (
                            <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-3 py-1.5 shrink-0 shadow-xs">
                                <Layers size={15} className="text-emerald-600 shrink-0" />
                                <label htmlFor="kb-select" className="text-xs font-semibold text-gray-600 whitespace-nowrap">
                                    Base de Conocimiento:
                                </label>
                                <select
                                    id="kb-select"
                                    value={knowledgeBaseId}
                                    onChange={(e) => handleKbChange(e.target.value)}
                                    className="bg-transparent text-xs font-bold text-slate-800 outline-none cursor-pointer pr-1"
                                >
                                    <option value="">Todas las KBs</option>
                                    {kbs.map((kb) => (
                                        <option key={kb.id} value={kb.id}>
                                            {kb.name || kb.title || `KB-${kb.id.substring(0, 6)}`}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}
                    </div>
                </div>
            </div>
            
            <div className="flex flex-1 overflow-hidden min-h-0">
                <aside className="w-[260px] shrink-0 border-r border-gray-200 bg-white p-4 flex flex-col min-h-0">
                    <button
                        onClick={createNewChat}
                        className="mb-4 flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-3 text-sm font-medium text-white hover:bg-emerald-700 shrink-0 transition-colors"
                    >
                        + Nuevo chat
                    </button>

                    <h3 className="mb-3 text-xs font-semibold uppercase text-gray-400 shrink-0">
                        Conversaciones ({selectedOrg.name})
                    </h3>

                    <div className="space-y-2 overflow-y-auto flex-1 min-h-0 pr-2">
                        {conversations.length === 0 && (
                            <p className="text-sm text-gray-400">No hay chats todavía</p>
                        )}
                        {conversations.map(chat => (       
                            <button
                                key={chat.id}
                                onClick={() => openConversation(chat.id)}
                                className={`w-full rounded-lg px-3 py-3 text-left hover:bg-gray-100 min-w-0 transition-colors ${conversationId === chat.id ? 'bg-emerald-50 text-emerald-700 font-semibold' : ''}`}
                            >
                                <p className="truncate text-sm font-medium">
                                    {chat.title}
                                </p>
                                <p className="text-xs text-gray-400 mt-1">
                                    {new Date(chat.updated_at).toLocaleDateString()}
                                </p>
                            </button>
                        ))}
                    </div>
                </aside>

                <div className="flex flex-1 flex-col min-w-0 bg-gray-50">
                    <div className="flex-1 overflow-y-auto px-8 py-8 min-h-0">
                        {messages.length === 0 && !isLoading ? (
                            <div className="flex h-full items-center justify-center">
                                <div className="text-center max-w-md">
                                    <h2 className="mb-3 text-2xl font-bold text-slate-900">
                                        Asistente de {selectedOrg.name}
                                    </h2>
                                    <p className="text-sm text-gray-500 leading-relaxed">
                                        Este chat está limitado exclusivamente a la información y documentos de esta organización utilizando el modelo <span className="font-semibold text-emerald-600">{selectedModel}</span>.
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
                                                    ? "bg-emerald-600 text-white"
                                                    : "border border-gray-200 bg-white text-gray-800"
                                            }`}
                                        >
                                            <p className="whitespace-pre-wrap text-sm leading-relaxed break-words">
                                                {message.content}
                                            </p>
                                            <p
                                                className={`mt-3 text-[11px] ${
                                                    message.role === "user"
                                                        ? "text-emerald-100"
                                                        : "text-gray-400"
                                                }`}
                                            >
                                                {message.timestamp.toLocaleTimeString()}
                                            </p>
                                        </div>
                                    </div>
                                ))}

                                {isLoading && (
                                    <div className="flex justify-start">
                                        <div className="max-w-xl w-full rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden transition-all">
                                            <button
                                                onClick={() => setIsThinkingOpen(!isThinkingOpen)}
                                                className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100/70 text-slate-700 text-xs font-semibold transition-colors"
                                            >
                                                <div className="flex items-center gap-2">
                                                    <Sparkles size={14} className="text-emerald-600 animate-spin" />
                                                    <span>Generando con {selectedModel}...</span>
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
                                                    <Loader2 size={13} className="animate-spin text-emerald-600 shrink-0" />
                                                    <p className="animate-pulse truncate">{thinkingStep || "Procesando información..."}</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>
                        )}
                    </div>
                </div>

                <aside className="w-[380px] lg:w-[420px] shrink-0 overflow-y-auto border-l border-gray-200 bg-white p-6">
                    <div className="mb-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-slate-900">
                                Documentos de la Organización
                            </h3>
                            {knowledgeBaseId && (
                                <button
                                    onClick={() => setShowUploadModal(true)}
                                    className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 transition-colors"
                                >
                                    + Añadir documento
                                </button>
                            )}
                        </div>

                        {!knowledgeBaseId ? (
                            <p className="text-sm text-gray-400 bg-gray-50 p-3 rounded-lg border border-dashed border-gray-200">
                                Selecciona una KB específica para gestionar tus documentos.
                            </p>
                        ) : documents.length === 0 ? (
                            <p className="text-sm text-gray-400">No hay documentos en esta Base de Conocimiento.</p>
                        ) : (
                            <div className="space-y-2">
                                {documents.map((doc) => (
                                    <div key={doc.id} className="rounded-lg border border-gray-200 p-3 transition hover:bg-gray-50 flex items-center gap-3">
                                        <FileText size={18} className="text-emerald-600 shrink-0" />
                                        <div className="flex-1 min-w-0">
                                            <p className="font-medium text-sm truncate" title={doc.title || doc.filename}>
                                                {doc.title || doc.filename}
                                            </p>
                                            <p className="text-xs text-gray-500 mt-0.5 shrink-0">
                                                {doc.size ? `${(doc.size / 1024).toFixed(1)} KB` : 'Documento activo'}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    
                    {retrieval && (
                        <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50/50 p-4">
                            <h3 className="mb-3 font-semibold text-emerald-800">Retrieval (Tenant Context)</h3>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-xs font-medium text-emerald-600">Chunks</span>
                                    <p className="font-semibold text-slate-700">{retrieval.final_chunks}</p>
                                </div>
                                <div>
                                    <span className="text-xs font-medium text-emerald-600">Caracteres</span>
                                    <p className="font-semibold text-slate-700">{contextCharacters.toLocaleString()}</p>
                                </div>
                                <div>
                                    <span className="text-xs font-medium text-emerald-600">Tokens</span>
                                    <p className="font-semibold text-slate-700">{estimatedTokens.toLocaleString()}</p>
                                </div>
                                <div>
                                    <span className="text-xs font-medium text-emerald-600">Uso</span>
                                    <p className="font-semibold text-slate-700">{Math.round((estimatedTokens / 8192) * 100)}%</p>
                                </div>
                            </div>
                        </div>
                    )}

                    <h3 className="mb-4 text-lg font-semibold text-slate-900">
                        Chunks recuperados
                    </h3>
                    {context.length === 0 ? (
                        <p className="text-sm text-gray-400">Todavía no hay contexto.</p>
                    ) : (
                        <div className="space-y-4">
                            {context.map((chunk, index) => (
                                <div key={index} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                                    <div className="mb-3">
                                        <span className="rounded bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">
                                            {chunk.metadata?.type || "Fragmento"}
                                        </span>
                                    </div>
                                    <p className="mb-3 whitespace-pre-wrap text-sm text-gray-700 break-words leading-relaxed">
                                        {chunk.page_content}
                                    </p>
                                    <div className="border-t border-gray-200 pt-3 text-xs text-gray-500 space-y-1.5">
                                        {chunk.metadata?.source && (
                                            <p className="truncate"><strong className="text-gray-700">Fuente:</strong> {chunk.metadata.source}</p>
                                        )}
                                        {chunk.metadata?.page && <p><strong className="text-gray-700">Página:</strong> {chunk.metadata.page}</p>}
                                        {chunk.metadata?.score && <p><strong className="text-gray-700">Score:</strong> {(chunk.metadata.score * 100).toFixed(1)}%</p>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </aside>
            </div>

            {showUploadModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs">
                    <div className="w-[420px] rounded-xl bg-white shadow-xl overflow-hidden">
                        <div className="flex justify-between border-b px-6 py-4 items-center bg-gray-50/50">
                            <div>
                                <h2 className="font-bold text-slate-800">Subir documentos</h2>
                                <p className="text-xs text-gray-500">Añadir archivos a {selectedOrg.name}</p>
                            </div>
                            <button 
                                onClick={() => !isUploadingModal && setShowUploadModal(false)}
                                disabled={isUploadingModal}
                                className="text-gray-400 hover:text-gray-600"
                            >
                                <X size={18}/>
                            </button>
                        </div>
                        <div className="space-y-5 p-6">
                            <div>
                                <label className="text-xs font-semibold text-slate-700">Seleccionar Archivos</label>
                                <div
                                    onClick={() => !isUploadingModal && fileInputRef.current?.click()}
                                    className={`mt-2 rounded-lg border border-dashed p-8 text-center transition-colors ${
                                        isUploadingModal ? 'opacity-50 cursor-not-allowed bg-gray-50' : 'cursor-pointer hover:bg-gray-50'
                                    }`}
                                >
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        multiple
                                        className="hidden"
                                        accept=".pdf,.doc,.docx,.txt,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg"
                                        onChange={handleFileSelect}
                                        disabled={isUploadingModal}
                                    />
                                    <Upload className="mx-auto mb-2 text-emerald-600 animate-pulse"/>
                                    <p className="text-sm font-medium text-slate-700">Haz clic para buscar archivos</p>
                                    <p className="text-xs text-gray-400 mt-1">PDF, TXT, DOCX, imágenes, etc.</p>
                                </div>

                                {uploadedFiles.length > 0 && (
                                    <div className="mt-3 space-y-2 max-h-36 overflow-y-auto">
                                        {uploadedFiles.map((file, index) => (
                                            <div key={index} className="flex items-center justify-between rounded-lg bg-emerald-50/50 px-3 py-2 text-sm border border-emerald-100">
                                                <span className="truncate pr-4 text-emerald-900 font-medium">{file.name}</span>
                                                {!isUploadingModal && (
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            setUploadedFiles(files => files.filter((_, i) => i !== index));
                                                        }}
                                                        className="text-gray-400 hover:text-red-500 shrink-0"
                                                    >
                                                        <X size={14}/>
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <div>
                                <label className="text-xs font-semibold text-slate-700">Categoría</label>
                                <select
                                    value={selectedCategory}
                                    onChange={(e) => setSelectedCategory(e.target.value)}
                                    disabled={isUploadingModal}
                                    className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm outline-emerald-500 bg-white"
                                >
                                    <option>Misc</option>
                                    <option>Normativa agrícola</option>
                                    <option>Manual técnico</option>
                                </select>
                            </div>

                            {isUploadingModal && (
                                <div className="flex items-center gap-3 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-medium animate-pulse">
                                    <Loader2 size={16} className="animate-spin text-emerald-600 shrink-0" />
                                    <span>Subiendo e indexando vectores con qwen3-embedding... Por favor espera.</span>
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end gap-3 border-t px-6 py-4 bg-gray-50 rounded-b-xl">
                            <button
                                onClick={() => setShowUploadModal(false)}
                                disabled={isUploadingModal}
                                className="rounded-lg border bg-white px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleUploadFilesModal}
                                disabled={uploadedFiles.length === 0 || isUploadingModal}
                                className="flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium text-white disabled:opacity-50 hover:bg-emerald-700 transition-colors shadow-sm"
                            >
                                {isUploadingModal ? (
                                    <>
                                        <Loader2 size={16} className="animate-spin" />
                                        Procesando...
                                    </>
                                ) : (
                                    "Subir e Indexar"
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div className="border-t border-gray-200 bg-white px-8 py-5 shrink-0">
                <div className="max-w-5xl mx-auto mb-3 flex items-center justify-between">
                    <label className="flex items-center cursor-pointer group">
                        <div className="relative flex items-center">
                            <input 
                                type="checkbox" 
                                className="sr-only" 
                                checked={useRag} 
                                onChange={() => setUseRag(!useRag)} 
                            />
                            <div className={`block w-10 h-5 rounded-full transition-colors ${useRag ? 'bg-emerald-500' : 'bg-gray-300'}`}></div>
                            <div className={`absolute left-0.5 top-0.5 bg-white w-4 h-4 rounded-full transition-transform ${useRag ? 'transform translate-x-5' : ''}`}></div>
                        </div>
                        <div className="ml-3 text-xs font-semibold uppercase tracking-wider text-gray-600 flex items-center gap-1.5 group-hover:text-emerald-600 transition-colors">
                            <Database size={14} className={useRag ? "text-emerald-500" : "text-gray-400"} />
                            {useRag ? `RAG Restringido (${selectedOrg.name}) — Modelo: ${selectedModel}` : "Chat General Desactivado"}
                        </div>
                    </label>
                </div>
                
                <form onSubmit={handleSendMessage} className="flex items-center gap-3 max-w-5xl mx-auto">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={`Consulta exclusiva sobre ${selectedOrg.name} usando ${selectedModel}...`}
                        className="flex-1 rounded-lg border border-gray-200 px-4 py-3.5 text-sm outline-emerald-500 shadow-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !inputValue.trim()}
                        className="flex items-center gap-2 rounded-lg bg-emerald-600 px-6 py-3.5 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                    >
                        <Send size={18}/>
                        Enviar
                    </button>
                </form>  
            </div>
        </div>
    );
}