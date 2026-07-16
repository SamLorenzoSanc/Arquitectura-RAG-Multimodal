export interface KnowledgeNode {
    id: string;
    type:
        | "document"
        | "chunk"
        | "entity"
        | "concept";

    label: string;
    document?: string;
    content?: string;
    metadata?: Record<string, any>;
    words?: number;
    x: number;
    y: number;
    weight?: number;
    group?: string;
}


export interface KnowledgeEdge {
    source: string;
    target: string;
    label?: string;
    weight?: number;
}


export interface KnowledgeGraph {
    nodes: KnowledgeNode[];
    edges: KnowledgeEdge[];
    stats: {
        nodes: number;
        edges: number;
        documents: number;
        average_similarity: number;
    };

}



export interface KnowledgeMap {

    organization: {
        id: string;
        name: string;
        description?: string;
    };


    statistics: {
        nodes: number;
        edges: number;
        documents: number;
        chunks: number;
    };


    graph: KnowledgeGraph;

}