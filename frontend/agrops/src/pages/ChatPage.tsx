"use client";

import { useState, useRef, useMemo, useEffect, type FormEvent } from "react";
import { Send, Upload, X } from "lucide-react";
import ChatService from "@/services/chat.service";
import DocumentService from "@/services/document.service";
import type { DocumentItem } from "@/types/document";
import type {
    ChatContext,
    RetrievalInfo,
    Message
} from "@/types/chat";

export default function ChatPage() {
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
    const [attachments, setAttachments] = useState<File[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [knowledgeBaseId, setKnowledgeBaseId] = useState<string>("");
    const [documents, setDocuments] = useState<DocumentItem[]>([]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    
    const fileInputRef = useRef<HTMLInputElement>(null);
    const contextCharacters = useMemo(() => {
        return context.reduce(
            (total, chunk) => total + chunk.page_content.length,
            0
        );
    }, [context]);

    useEffect(() => {
        initialize();
    }, [knowledgeBaseId]);

    const estimatedTokens = useMemo(() => {
        return Math.round(contextCharacters / 4);
    }, [contextCharacters]);

    const initialize = async () => {

        try {

            const kb = await KnowledgeService.getCurrent();

            setKnowledgeBaseId(kb.id);

            const docs = await DocumentService.list(kb.id);

            setDocuments(docs);

        } catch (err) {

            console.error(err);

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

        try {
             if (uploadedFiles.length > 0) {
                console.log({
                    file: File.name,
                    knowledgeBaseId,
                });
                await Promise.all(

                    uploadedFiles.map(file =>
                        DocumentService.upload({
                            file,
                            knowledge_base_id: knowledgeBaseId!,
                            title: file.name,
                        })
                    )

                );

                setUploadedFiles([]);
            }
            // Historial para la API
            const history = updatedMessages.map((msg) => ({
                role: msg.role,
                content: msg.content,
            }));

            const response = await ChatService.send({
                question,
                conversation_id: conversationId,
                history,
            });

            console.log("===== RESPUESTA CHAT =====");
            console.log(response);

            // Guardar conversationId
            if (response.conversation_id) {
                setConversationId(response.conversation_id);
            }

            // Parsear contexto RAG
            setContext(response.context ?? []);
            setRetrieval(response.retrieval ?? null);
            
            console.log("===== CONTEXTO RAG =====");
            console.table(response.context);

            // Mensaje del asistente
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
            console.error(error);

            setMessages((prev) => [
                ...prev,
                {
                    id: crypto.randomUUID(),
                    role: "assistant",
                    content:
                        "No se pudo obtener respuesta del asistente.",
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

        } catch (err) {
            console.error(err);
        }

    };
    

    return (
        <div className="flex h-screen flex-col bg-gray-50">
            <div className="border-b border-gray-200 bg-white px-8 py-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-600">AgroPS CHAT</h4>
                        <h1 className="mt-2 text-2xl font-bold text-slate-900">Directores RRHH</h1>
                    </div>
                    <button
                        onClick={() => setShowUploadModal(true)}
                        className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
                    >
                        <Upload size={16} />
                        Upload
                    </button>
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex flex-1 overflow-hidden">

                {/* ================= CHAT ================= */}
                <div className="flex flex-1 flex-col">

                    <div className="flex-1 overflow-y-auto px-8 py-8">

                        {messages.length === 0 ? (
                            <div className="flex h-full items-center justify-center">
                                <div className="text-center">
                                    <h2 className="mb-4 text-2xl font-bold text-slate-900">
                                        Start a conversation
                                    </h2>
                        
                                    <p className="text-sm text-gray-500">
                                        Ask about the documents uploaded to this tenant
                                        context.
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-6">
                            
                                {messages.map((message: Message) => (
                                    <div
                                        key={message.id}
                                        className={`flex ${
                                            message.role === "user"
                                                ? "justify-end"
                                                : "justify-start"
                                        }`}
                                    >
                                        <div
                                            className={`max-w-2xl rounded-lg px-4 py-3 ${
                                                message.role === "user"
                                                    ? "bg-emerald-600 text-white"
                                                    : "border border-gray-200 bg-white text-gray-800"
                                            }`}
                                        >
                                            <p className="whitespace-pre-wrap text-sm">
                                                {message.content}
                                            </p>
                                        
                                            <p
                                                className={`mt-2 text-xs ${
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
                                        <div className="rounded-lg border bg-white px-4 py-3">
                                            <div className="flex gap-2">
                                                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                                                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-150" />
                                                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-300" />
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div ref={messagesEndRef} />
                            
                            </div>
                        )}

                    </div>
                    
                </div>
                    

                    
                <aside className="w-[420px] overflow-y-auto border-l border-gray-200 bg-white p-6">

            {/* ================= DOCUMENTOS ================= */}
            <div className="mb-6">
                <h3 className="mb-4 text-lg font-semibold text-slate-900">
                    Documentos
                </h3>

                {documents.length === 0 ? (
                    <p className="text-sm text-gray-400">
                        No hay documentos.
                    </p>
                ) : (
                    <div className="space-y-2">
                        {documents.map((doc) => (
                            <div
                                key={doc.id}
                                className="cursor-pointer rounded-lg border border-gray-200 p-3 transition hover:bg-gray-50"
                            >
                                <p className="font-medium text-sm">
                                    {doc.title || doc.filename}
                                </p>
                        
                                <p className="text-xs text-gray-500">
                                    {(doc.size / 1024).toFixed(1)} KB
                                </p>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            
            {/* ================= RETRIEVAL ================= */}
            {retrieval && (
                <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                
                    <h3 className="mb-3 font-semibold text-emerald-800">
                        Retrieval
                    </h3>
            
                    <div className="grid grid-cols-2 gap-3 text-sm">
            
                        <div>
                            <span className="font-medium">
                                Chunks
                            </span>
                            <p>{retrieval.final_chunks}</p>
                        </div>
            
                        <div>
                            <span className="font-medium">
                                Caracteres
                            </span>
                            <p>{contextCharacters.toLocaleString()}</p>
                        </div>
            
                        <div>
                            <span className="font-medium">
                                Tokens
                            </span>
                            <p>{estimatedTokens.toLocaleString()}</p>
                        </div>
            
                        <div>
                            <span className="font-medium">
                                Uso
                            </span>
                            <p>
                                {Math.round((estimatedTokens / 8192) * 100)}%
                            </p>
                        </div>
            
                    </div>
            
                </div>
            )}

            {/* ================= CHUNKS ================= */}
            <h3 className="mb-5 text-lg font-semibold text-slate-900">
                Chunks recuperados
            </h3>
        
            {context.length === 0 ? (
                <p className="text-sm text-gray-400">
                    Todavía no hay contexto.
                </p>
            ) : (
                <div className="space-y-4">
                
                    {context.map((chunk, index) => (
                        <div
                            key={index}
                            className="rounded-lg border border-gray-200 bg-gray-50 p-4"
                        >
                            <div className="mb-3">
                                <span className="rounded bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">
                                    {chunk.metadata.type}
                                </span>
                            </div>
                    
                            <p className="mb-3 whitespace-pre-wrap text-sm text-gray-700">
                                {chunk.page_content}
                            </p>
                    
                            <div className="border-t pt-2 text-xs">
                    
                                <p>
                                    <strong>Fuente:</strong> {chunk.metadata.source}
                                </p>
                    
                                {chunk.metadata.page && (
                                    <p>
                                        <strong>Página:</strong> {chunk.metadata.page}
                                    </p>
                                )}

                                {chunk.metadata.score && (
                                    <p>
                                        <strong>Score:</strong>{" "}
                                        {(chunk.metadata.score * 100).toFixed(1)}%
                                    </p>
                                )}

                            </div>
                        </div>
                    ))}

                </div>
            )}

            </aside>
                
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-200 bg-white px-8 py-6">

    {/* Archivos seleccionados */}

    {uploadedFiles.length > 0 && (

        <div className="mb-3 flex flex-wrap gap-2">

            {uploadedFiles.map((file, index) => (

                <div
                    key={index}
                    className="flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-2 text-sm"
                >
                    <span className="max-w-[180px] truncate">
                        📄 {file.name}
                    </span>

                    <button
                        type="button"
                        onClick={() =>
                            setUploadedFiles(files =>
                                files.filter((_, i) => i !== index)
                            )
                        }
                    >
                        <X size={14} />
                    </button>

                </div>

            ))}

        </div>

    )}
        <form
            onSubmit={handleSendMessage}
            className="flex items-center gap-3"
        >

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
                className="rounded-lg border border-gray-200 p-3 transition hover:bg-gray-100"
            >
                <Upload size={18} />
            </button>

            <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Haz una pregunta..."
                className="flex-1 rounded-lg border border-gray-200 px-4 py-3 text-sm outline-emerald-500"
            />

            <button
                type="submit"
                disabled={
                    isLoading ||
                    (
                        !inputValue.trim() &&
                        uploadedFiles.length === 0
                    )
                }
                className="flex items-center gap-2 rounded-lg bg-emerald-600 px-6 py-3 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
                <Send size={16}/>
                Enviar
            </button>
        </form>   
    </div>
    </div>
    );
}