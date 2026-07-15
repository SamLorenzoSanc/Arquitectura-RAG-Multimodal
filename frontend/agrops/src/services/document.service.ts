import api from "@/api";
import type {
    DocumentItem,
    UploadDocumentRequest,
    UploadDocumentResponse,
} from "@/types/document";

class DocumentService {

    async upload(
        request: UploadDocumentRequest
    ): Promise<UploadDocumentResponse> {

        const formData = new FormData();

        formData.append("file", request.file);
        formData.append(
            "knowledge_base_id",
            request.knowledge_base_id
        );

        if (request.title)
            formData.append("title", request.title);

        if (request.description)
            formData.append("description", request.description);

        const response = await api.post(
            "/documents",
            formData
        );

        return response.data;
    }

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

}

export default new DocumentService();