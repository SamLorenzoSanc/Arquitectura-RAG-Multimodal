export interface IngestProgress {
    document_id?: string;
    stage?: string;
    percent?: number;
    status?: string;
    message?: string;
    chunks?: number;
    embedded?: number;
    total?: number;
    error?: string | null;
}

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
    progress?: IngestProgress | null;
    knowledge_base_id?: string;
    knowledge_base_name?: string;
}

export interface DocumentChunk {
    id: string;
    position: number;
    headline: string;
    summary: string;
    content: string;
    char_count: number;
    overlap_prev: number;
    embedding_models: string[];
}

export interface DocumentChunksResponse {
    id: string;
    filename: string;
    title: string;
    mime_type?: string;
    size?: number;
    knowledge_base_id: string;
    chunk_count: number;
    chunks: DocumentChunk[];
}
