import api from "@/api";
import type { DocumentItem } from "@/types/document";

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

}

export default new DocumentService();