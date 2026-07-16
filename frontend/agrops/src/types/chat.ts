export interface ChatRequest {
    question:string;
    conversation_id:string|null;
    history:{
        role:string;
        content:string;
    }[];
    knowledge_base_id:string;
}

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
}

export interface ChatContext {
    type: string;
    page_content: string;
    metadata: {
        source?: string;
        type?: string;
        document_id?: string;
        chunk_id?: string;
        score?: number;
        page?: number;
        title?: string;
        author?: string;
        created_at?: string;
        [key: string]: any;
    };
}

export interface Conversation {
    id:string;
    title:string;
    created_at:string;
    updated_at:string;
}

export interface RetrievalInfo {
    original_query: string;
    rewritten_query: string;
    retrieved_chunks: number;
    rewritten_chunks: number;
    merged_chunks: number;
    final_chunks: number;
    retrieval_k: number;
    final_k: number;
    reranking: boolean;
}



export interface ContextChunk {
    page_content:string;
    type:string;
    metadata:any;
}



export interface ChatResponse {
    conversation_id:string;
    answer:string;
    context:ContextChunk[];
    retrieval: RetrievalInfo;

}


export interface ChatMessage {
    role:
        "user"
        |
        "assistant";
    content:string;

}

export interface ConversationMessage {
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
}

export interface ConversationResponse {
    conversation_id: string;
    title: string;
    messages: ConversationMessage[];
}