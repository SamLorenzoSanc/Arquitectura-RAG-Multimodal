import api from "@/api";

import type {
    ChatRequest,
    ChatResponse,
    ConversationResponse
} from "@/types/chat";

class ChatService {

    async send(request: ChatRequest): Promise<ChatResponse> {

        console.log("=== CHAT REQUEST ===");
        console.log(request);

        try {

            const { data } = await api.post<ChatResponse>(
                "/chat/",
                request
            );

            console.log("=== CHAT RESPONSE ===");
            console.log(data);

            return data;

        } catch (error: any) {

            console.error(
                "CHAT ERROR",
                error.response?.data ?? error.message
            );

            throw new Error(
                error.response?.data?.detail ??
                "No se pudo enviar la pregunta"
            );

        }
    }

    async getConversation(
        conversationId: string,
    ): Promise<ConversationResponse> {

        try {

            const { data } = await api.get<ConversationResponse>(
                `/chat/${conversationId}`
            );

            return data;

        } catch (error: any) {

            console.error(
                "GET CONVERSATION ERROR",
                error.response?.data ?? error.message
            );

            throw new Error(
                "No se pudo cargar la conversación"
            );

        }
    }

    async deleteConversation(
        conversationId: string,
    ): Promise<void> {

        try {

            await api.delete(
                `/chat/${conversationId}`
            );

        } catch (error: any) {

            console.error(
                "DELETE CONVERSATION ERROR",
                error.response?.data ?? error.message
            );

            throw new Error(
                "No se pudo eliminar la conversación"
            );

        }
    }
}

export default new ChatService();