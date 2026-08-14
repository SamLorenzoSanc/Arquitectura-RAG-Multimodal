export interface DocumentItem {
    id: string;
    filename: string;
    name?: string;
    title?: string;
    description?: string;
    size: number;
    mime_type?: string;
    content_type?: string;
    current_version: number;
    created_at: string;
    updated_at?: string;
    status?: "active" | "inactive";
    processing_status?: string;
    embedding_model?: string;
    generation_model?: string;
    llm_model?: string;
    chunks?: number;
    attempts?: number;
    error?: string | null;
}