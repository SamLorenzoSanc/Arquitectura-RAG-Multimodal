"use client";

import { useState, useRef, useMemo, useEffect, FormEvent } from "react";
import { Send, Upload, X, Database, Layers } from "lucide-react";
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

export default function ChatPage() {
    const { selectedOrg } = useOrganization();

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [conversationId, setConversationId] = useState<string | null>(null);
    const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
    const [selectedCategory, setSelectedCategory] = useState("Misc");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [context, setContext] = useState<ChatContext[]>([]);
    const [retrieval, setRetrieval] = useState<RetrievalInfo | null>(null);

    // ESTADOS DE KNOWLEDGE BASE
    const [kbs, setKbs] = useState<any[]>([]); // Lista de todas las KBs
    const [knowledgeBaseId, setKnowledgeBaseId] = useState<string>(""); // KB seleccionada ("" = Todas)

    const [documents, setDocuments] = useState<DocumentItem[]>([]);
    const [conversations, setConversations] = useState<any[]>([]);
    const [activeConversation, setActiveConversation] = useState<string | null>(null);
    
    // Controla si se usa RAG o no
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
        setActiveConversation(null);
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
    }, [messages]);

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

    // Inicialización: obtiene la lista de KBs de la organización
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

            // Si hay KBs disponibles, seleccionamos la primera por defecto
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

    // Función auxiliar para cargar documentos según la KB seleccionada
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

    // Cambio manual de Knowledge Base desde el Selector
    const handleKbChange = (newKbId: string) => {
        setKnowledgeBaseId(newKbId);
        fetchDocumentsForKb(newKbId);
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

        try {
            // Si hay archivos adjuntos en la caja de texto y RAG activado, subirlos primero
            if (uploadedFiles.length > 0 && useRag && knowledgeBaseId) {
                await Promise.all(
                    uploadedFiles.map(file =>
                        DocumentService.upload({
                            file,
                            knowledge_base_id: knowledgeBaseId,
                            title: file.name,
                        })
                    )
                );
                setUploadedFiles([]);
                fetchDocumentsForKb(knowledgeBaseId);
            }
            
            const history = updatedMessages.map((msg) => ({
                role: msg.role,
                content: msg.content,
            }));

            // Enviamos 'knowledge_base_id' solo si RAG está activo y hay una KB seleccionada. Si es "", enviará undefined para buscar globalmente.
            const response = await ChatService.send({
                question,
                conversation_id: conversationId,
                history,
                knowledge_base_id: useRag ? (knowledgeBaseId || undefined) : undefined,
                use_rag: useRag, 
                organization_id: selectedOrg?.id
            });

            if (response.conversation_id) {
                setConversationId(response.conversation_id);
                setConversations(prev => {
                    const exists = prev.some(
                        c => c.id === response.conversation_id
                    );
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
                content:
                    response.answer?.trim() ||
                    "El asistente no devolvió ninguna respuesta.",
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
        }
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setUploadedFiles(Array.from(e.target.files));
        }
    };

    const handleUploadFiles = async () => {
        if (!knowledgeBaseId) return;

        try {
            await Promise.all(
                uploadedFiles.map(file =>
                    DocumentService.upload({
                        file,
                        knowledge_base_id: knowledgeBaseId,
                        title: file.name,
                        description: "",
                    })
                )
            );
            setUploadedFiles([]);
            setShowUploadModal(false);
            fetchDocumentsForKb(knowledgeBaseId);
        } catch (err) {
            console.error("Error al subir archivos:", err);
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
            
            {/* Header del Chat con Selector de KB Integrado */}
            <div className="border-b border-gray-200 bg-white px-8 py-5 shrink-0">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-600">CHAT</h4>
                        <h1 className="mt-1 text-2xl font-bold text-slate-900">{selectedOrg.name}</h1>
                    </div>

                    {/* SELECTOR DE KNOWLEDGE BASE */}
                    {useRag && (
                        <div className="flex items-center gap-2.5 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 shrink-0">
                            <Layers size={16} className="text-emerald-600 shrink-0" />
                            <label htmlFor="kb-select" className="text-xs font-semibold text-gray-600 whitespace-nowrap">
                                Base de Conocimiento:
                            </label>
                            <select
                                id="kb-select"
                                value={knowledgeBaseId}
                                onChange={(e) => handleKbChange(e.target.value)}
                                className="bg-transparent text-sm font-medium text-slate-800 outline-none cursor-pointer pr-2"
                            >
                                <option value="">Todas las Bases de Conocimiento</option>
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
            
            {/* Área Media (Sidebars + Mensajes) */}
            <div className="flex flex-1 overflow-hidden min-h-0">

                {/* Sidebar Izquierdo: Conversaciones */}
                <aside className="w-[260px] shrink-0 border-r border-gray-200 bg-white p-4 flex flex-col min-h-0">
                    <button
                        onClick={createNewChat}
                        className="mb-4 flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-3 text-sm font-medium text-white hover:bg-emerald-700 shrink-0 transition-colors"
                    >
                        + Nuevo chat
                    </button>

                    <h3 className="mb-3 text-xs font-semibold uppercase text-gray-400 shrink-0">
                        Conversaciones
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

                {/* Chat Principal */}
                <div className="flex flex-1 flex-col min-w-0 bg-gray-50">
                    <div className="flex-1 overflow-y-auto px-8 py-8 min-h-0">
                        {messages.length === 0 ? (
                            <div className="flex h-full items-center justify-center">
                                <div className="text-center max-w-md">
                                    <h2 className="mb-3 text-2xl font-bold text-slate-900">
                                        Empieza una conversación
                                    </h2>
                                    <p className="text-sm text-gray-500 leading-relaxed">
                                        Pregunta cualquier duda. Usa el conmutador inferior para activar/desactivar RAG o selecciona una Base de Conocimiento específica arriba.
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
                                        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
                                            <div className="flex items-center gap-2">
                                                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-300" />
                                                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-300 delay-150" />
                                                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-300 delay-300" />
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>
                        )}
                    </div>
                </div>

                {/* Sidebar Derecho: Documentos y Métricas Retrieval */}
                <aside className="w-[380px] lg:w-[420px] shrink-0 overflow-y-auto border-l border-gray-200 bg-white p-6">
                    
                    {/* DOCUMENTOS */}
                    <div className="mb-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-slate-900">
                                Documentos
                            </h3>
                            {knowledgeBaseId && (
                                <button
                                    onClick={() => setShowUploadModal(true)}
                                    className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
                                >
                                    + Añadir
                                </button>
                            )}
                        </div>

                        {!knowledgeBaseId ? (
                            <p className="text-sm text-gray-400 bg-gray-50 p-3 rounded-lg border border-dashed border-gray-200">
                                Buscando en todas las Bases de Conocimiento. Selecciona una KB específica para ver sus documentos.
                            </p>
                        ) : documents.length === 0 ? (
                            <p className="text-sm text-gray-400">No hay documentos en esta Base de Conocimiento.</p>
                        ) : (
                            <div className="space-y-2">
                                {documents.map((doc) => (
                                    <div key={doc.id} className="rounded-lg border border-gray-200 p-3 transition hover:bg-gray-50 flex flex-col min-w-0">
                                        <p className="font-medium text-sm truncate" title={doc.title || doc.filename}>
                                            {doc.title || doc.filename}
                                        </p>
                                        <p className="text-xs text-gray-500 mt-1 shrink-0">
                                            {doc.size ? `${(doc.size / 1024).toFixed(1)} KB` : 'Documento activo'}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    
                    {/* RETRIEVAL */}
                    {retrieval && (
                        <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50/50 p-4">
                            <h3 className="mb-3 font-semibold text-emerald-800">Retrieval</h3>
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

                    {/* CHUNKS */}
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

            {/* Modal de subida */}
            {showUploadModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="w-[420px] rounded-xl bg-white shadow-xl">
                        <div className="flex justify-between border-b px-6 py-4">
                            <div>
                                <h2 className="font-semibold">Subir documentos</h2>
                                <p className="text-xs text-gray-500">Añadir archivos a {selectedOrg.name}</p>
                            </div>
                            <button onClick={() => setShowUploadModal(false)}>
                                <X size={18}/>
                            </button>
                        </div>
                        <div className="space-y-5 p-6">
                            <div>
                                <label className="text-xs font-medium">Archivos</label>
                                <div
                                    onClick={() => fileInputRef.current?.click()}
                                    className="mt-2 cursor-pointer rounded-lg border border-dashed p-8 text-center hover:bg-gray-50 transition-colors"
                                >
                                    <Upload className="mx-auto mb-2 text-gray-400"/>
                                    <p className="text-sm text-gray-600">Selecciona archivos</p>
                                </div>
                                {uploadedFiles.length > 0 && (
                                    <div className="mt-3 space-y-2">
                                        {uploadedFiles.map((file, index) => (
                                            <div key={index} className="flex items-center justify-between rounded bg-gray-50 px-3 py-2 text-sm border border-gray-100">
                                                <span className="truncate pr-4">{file.name}</span>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setUploadedFiles(files => files.filter((_, i) => i !== index));
                                                    }}
                                                    className="text-gray-400 hover:text-red-500 shrink-0"
                                                >
                                                    <X size={14}/>
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <div>
                                <label className="text-xs font-medium">Categoría</label>
                                <select
                                    value={selectedCategory}
                                    onChange={(e) => setSelectedCategory(e.target.value)}
                                    className="mt-2 w-full rounded-lg border px-3 py-2.5 text-sm outline-emerald-500 bg-white"
                                >
                                    <option>Misc</option>
                                    <option>Normativa agrícola</option>
                                    <option>Manual técnico</option>
                                </select>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 border-t px-6 py-4 bg-gray-50 rounded-b-xl">
                            <button
                                onClick={() => setShowUploadModal(false)}
                                className="rounded-lg border bg-white px-4 py-2 text-sm font-medium hover:bg-gray-50"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleUploadFiles}
                                disabled={uploadedFiles.length === 0}
                                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 hover:bg-emerald-700 transition-colors"
                            >
                                Subir archivos
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Área de Input del Chat (Barra inferior) */}
            <div className="border-t border-gray-200 bg-white px-8 py-5 shrink-0">
                
                {/* Conmutador Toggle RAG */}
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
                            {useRag ? "RAG Activado (Chat con Documentos)" : "RAG Desactivado (Chat General)"}
                        </div>
                    </label>
                </div>

                {/* Vista previa de archivos adjuntos */}
                {uploadedFiles.length > 0 && (
                    <div className="mb-3 flex flex-wrap gap-2 max-w-5xl mx-auto">
                        {uploadedFiles.map((file, index) => (
                            <div key={index} className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm">
                                <span className="max-w-[180px] truncate text-emerald-800">
                                    📄 {file.name}
                                </span>
                                <button
                                    type="button"
                                    className="text-emerald-600 hover:text-emerald-800"
                                    onClick={() => setUploadedFiles(files => files.filter((_, i) => i !== index))}
                                >
                                    <X size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
                
                {/* Formulario de envío */}
                <form onSubmit={handleSendMessage} className="flex items-center gap-3 max-w-5xl mx-auto">
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        className="hidden"
                        accept=".pdf,.doc,.docx,.txt,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg"
                        onChange={handleFileUpload}
                    />
                    
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={!useRag}
                        className="rounded-lg border border-gray-200 p-3.5 text-gray-500 transition hover:bg-gray-50 hover:text-emerald-600 disabled:opacity-30 disabled:hover:bg-transparent disabled:cursor-not-allowed"
                        title={useRag ? "Adjuntar archivo" : "Activa RAG para adjuntar archivos"}
                    >
                        <Upload size={20} />
                    </button>

                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={`Pregunta al asistente ${useRag ? `sobre los documentos en ${selectedOrg.name}...` : "de forma general..."}`}
                        className="flex-1 rounded-lg border border-gray-200 px-4 py-3.5 text-sm outline-emerald-500 shadow-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || (!inputValue.trim() && uploadedFiles.length === 0)}
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