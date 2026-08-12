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