export interface ChatRequest {
    question: string;
    conversation_id?: string | null;
    history?: Array<{ role: string; content: string }>;
    knowledge_base_id?: string;
    department_id?: string;
    use_rag?: boolean;
    organization_id?: string;
    organization_name?: string;
    model?: string;
    rag_mode?: "hybrid" | "agentic" | "compare";
    use_query_rewrite?: boolean;
    use_reranking?: boolean;
    retrieval_k?: number;
    final_k?: number;
    temperature?: number;
}

export interface AgentTraceStep {
    tool: string;
    reason?: string;
    ok?: boolean;
    latency_ms?: number;
    summary?: string;
}

export interface ModeComparisonSide {
    mode: string;
    architecture?: string | null;
    answer: string;
    context?: ContextChunk[];
    retrieval?: RetrievalInfo | null;
    retrieval_details?: any;
    agent_trace?: AgentTraceStep[] | null;
    related_questions?: string[];
    latency_ms?: number | null;
}

export interface ChatResponse {
    conversation_id: string;
    answer: string;
    context: ContextChunk[];
    retrieval: RetrievalInfo;
    retrieval_details?: any;
    related_questions?: string[];
    rag_mode?: string | null;
    architecture?: string | null;
    agent_trace?: AgentTraceStep[] | null;
    comparison?: {
        hybrid?: ModeComparisonSide;
        agentic?: ModeComparisonSide;
        note?: string;
    } | null;
    review_id?: string | null;
}


export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    sources?: Array<{
        source?: string;
        score?: number;
        chunk_id?: string;
        snippet?: string;
    }>;
    pendingReview?: boolean;
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
    architecture?: string | null;
    agent_tools?: string[] | null;
    intent?: string | null;
    strategy?: string | null;
}



export interface ContextChunk {
    page_content:string;
    type:string;
    metadata:any;
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