export interface DocumentItem {
    id: string;
    filename: string;
    title?: string;
    description?: string;
    size: number;
    mime_type?: string;
    current_version: number;
    created_at: string;
}

export interface UploadDocumentRequest {
    file: File;
    knowledge_base_id: string;
    title?: string;
    description?: string;
}

export interface UploadDocumentResponse {
    id: string;
    message: string;
}