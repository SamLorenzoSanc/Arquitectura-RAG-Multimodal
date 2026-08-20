import api from "@/api";
import type {
    DocumentChunksResponse,
    DocumentItem,
    IngestProgress,
} from "@/types/document";

class DocumentService {
    async list(
        knowledgeBaseId: string
    ): Promise<DocumentItem[]> {

        const response = await api.get<DocumentItem[]>(
            "/documents",
            {
                params: {
                    knowledge_base_id: knowledgeBaseId,
                },
            }
        );

        return response.data;
    }

    async upload(params: {
        knowledgeBaseId: string;
        file: File;
        title?: string;
        description?: string;
        onUploadProgress?: (percent: number) => void;
    }): Promise<{
        id: string;
        filename: string;
        status: string;
        chunks?: number;
        embedding_model?: string | null;
        message?: string;
        processing_status?: string;
        error?: string | null;
        progress?: IngestProgress | null;
    }> {
        const form = new FormData();
        form.append("knowledge_base_id", params.knowledgeBaseId);
        form.append("file", params.file);
        if (params.title) form.append("title", params.title);
        if (params.description) form.append("description", params.description);
        const response = await api.post("/documents", form, {
            headers: { "Content-Type": "multipart/form-data" },
            timeout: 600_000,
            onUploadProgress: (event) => {
                if (!params.onUploadProgress) return;
                const total = event.total || params.file.size || 0;
                if (!total) return;
                params.onUploadProgress(
                    Math.min(100, Math.round((event.loaded / total) * 100)),
                );
            },
        });
        return response.data;
    }

    async chunks(
        documentId: string,
        knowledgeBaseId?: string,
    ): Promise<DocumentChunksResponse> {
        const response = await api.get<DocumentChunksResponse>(
            `/documents/${documentId}/chunks`,
            {
                params: knowledgeBaseId
                    ? { knowledge_base_id: knowledgeBaseId }
                    : undefined,
            },
        );
        return response.data;
    }

    async progress(
        knowledgeBaseId: string,
        documentId: string,
    ): Promise<IngestProgress> {
        const response = await api.get<IngestProgress>(
            `/documents/${documentId}/progress`,
            { params: { knowledge_base_id: knowledgeBaseId } },
        );
        return response.data;
    }

    async reprocess(
        knowledgeBaseId: string,
        documentId: string,
    ): Promise<{ status: string; id: string; message?: string }> {
        const response = await api.post(
            `/documents/${documentId}/reprocess`,
            null,
            { params: { knowledge_base_id: knowledgeBaseId } },
        );
        return response.data;
    }

    async delete(params: {
        knowledgeBaseId: string;
        documentId: string;
    }): Promise<{ status: string; id: string }> {
        const response = await api.delete(`/documents/${params.documentId}`, {
            params: { knowledge_base_id: params.knowledgeBaseId },
        });
        return response.data;
    }

    async embeddingModels(knowledgeBaseId: string): Promise<{
        indexed: string[];
        default: string;
        catalog: Array<{ id: string; label: string; why?: string }>;
        note?: string;
    }> {
        const response = await api.get("/documents/embedding-models", {
            params: { knowledge_base_id: knowledgeBaseId },
        });
        return response.data;
    }

    async reindexEmbeddings(params: {
        knowledgeBaseId: string;
        documentId?: string;
        embeddingModels: string[];
    }): Promise<{
        chunks: number;
        models: Record<
            string,
            {
                indexed: number;
                skipped: number;
                pending?: number;
                failed: number;
                error?: string | null;
            }
        >;
        note?: string;
    }> {
        const response = await api.post("/documents/reindex-embeddings", {
            knowledge_base_id: params.knowledgeBaseId,
            document_id: params.documentId || null,
            embedding_models: params.embeddingModels,
        });
        return response.data;
    }
}

export default new DocumentService();