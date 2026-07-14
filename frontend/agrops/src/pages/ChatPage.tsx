"use client";

import { useState, useRef, useEffect, type FormEvent } from "react";
import { Send, Upload, X } from "lucide-react";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
    const [selectedCategory, setSelectedCategory] = useState("Misc");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSendMessage = async (e: FormEvent) => {
        e.preventDefault();
        if (!inputValue.trim()) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: inputValue,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInputValue("");
        setIsLoading(true);

        // Simulate API call to backend
        setTimeout(() => {
            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: "Esta es una respuesta de demostración. Integra aquí tu backend RAG.",
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, assistantMessage]);
            setIsLoading(false);
        }, 1000);
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setUploadedFiles(Array.from(e.target.files));
        }
    };

    const handleUploadFiles = async () => {
        if (uploadedFiles.length === 0) return;

        // TODO: Integrar con backend para subir archivos
        console.log("Uploading files:", uploadedFiles, "Category:", selectedCategory);
        
        setUploadedFiles([]);
        setShowUploadModal(false);
    };

    return (
        <div className="flex h-screen flex-col bg-gray-50">
            {/* Header */}
            <div className="border-b border-gray-200 bg-white px-8 py-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-600">POLICYOPS CHAT</h4>
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
            <div className="flex-1 overflow-y-auto px-8 py-8">
                {messages.length === 0 ? (
                    <div className="flex h-full items-center justify-center">
                        <div className="text-center">
                            <h2 className="mb-4 text-2xl font-bold text-slate-900">Start a conversation</h2>
                            <p className="text-sm text-gray-500">Ask about the documents uploaded to this tenant context.</p>
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col gap-6">
                        {messages.map((message) => (
                            <div
                                key={message.id}
                                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                            >
                                <div
                                    className={`max-w-md rounded-lg px-4 py-3 ${
                                        message.role === "user"
                                            ? "bg-emerald-600 text-white"
                                            : "border border-gray-200 bg-white text-gray-800"
                                    }`}
                                >
                                    <p className="text-sm">{message.content}</p>
                                    <p className={`mt-1 text-xs ${message.role === "user" ? "text-emerald-100" : "text-gray-400"}`}>
                                        {message.timestamp.toLocaleTimeString()}
                                    </p>
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
                                    <div className="flex gap-2">
                                        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                                        <div className="animation-delay-200 h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                                        <div className="animation-delay-400 h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-200 bg-white px-8 py-6">
                <form onSubmit={handleSendMessage} className="flex gap-3">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder="Ask a question..."
                        className="flex-1 rounded-lg border border-gray-200 px-4 py-3 text-sm outline-emerald-500 placeholder:text-gray-400"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !inputValue.trim()}
                        className="flex items-center gap-2 rounded-lg bg-emerald-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
                    >
                        <Send size={16} />
                        Send
                    </button>
                </form>
            </div>

            {/* Upload Modal */}
            {showUploadModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div className="w-full max-w-md rounded-xl border border-gray-100 bg-white p-6 shadow-xl">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-slate-900">Upload documents</h3>
                            <button
                                onClick={() => setShowUploadModal(false)}
                                className="text-gray-400 hover:text-gray-600"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <p className="mb-6 text-sm text-gray-600">
                            Add files to this tenant so PolicyOps can index them for future answers.
                        </p>

                        <div className="mb-6">
                            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-500">
                                Files
                            </label>
                            <label className="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed border-gray-300 p-6 transition-colors hover:border-emerald-500 hover:bg-emerald-50">
                                <Upload size={20} className="text-gray-400" />
                                <div>
                                    <p className="text-sm font-medium text-gray-700">Click to upload</p>
                                    <p className="text-xs text-gray-500">or drag and drop</p>
                                </div>
                                <input
                                    type="file"
                                    multiple
                                    onChange={handleFileUpload}
                                    className="hidden"
                                    accept=".pdf,.doc,.docx,.txt,.xlsx,.pptx"
                                />
                            </label>

                            {uploadedFiles.length > 0 && (
                                <div className="mt-4 space-y-2">
                                    {uploadedFiles.map((file, idx) => (
                                        <div
                                            key={idx}
                                            className="flex items-center justify-between rounded-lg bg-gray-50 p-3"
                                        >
                                            <span className="text-sm text-gray-700">{file.name}</span>
                                            <button
                                                onClick={() =>
                                                    setUploadedFiles(uploadedFiles.filter((_, i) => i !== idx))
                                                }
                                                className="text-gray-400 hover:text-gray-600"
                                            >
                                                <X size={16} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="mb-6">
                            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-500">
                                Category
                            </label>
                            <select
                                value={selectedCategory}
                                onChange={(e) => setSelectedCategory(e.target.value)}
                                className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm outline-emerald-500"
                            >
                                <option>Misc</option>
                                <option>Policies</option>
                                <option>Procedures</option>
                                <option>Guidelines</option>
                                <option>Other</option>
                            </select>
                        </div>

                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => setShowUploadModal(false)}
                                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleUploadFiles}
                                disabled={uploadedFiles.length === 0}
                                className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                            >
                                <Upload size={16} />
                                Upload files
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}