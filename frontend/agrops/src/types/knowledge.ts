export interface KnowledgeBase {
    id: string;
    tenant_id: string;
    name: string;
    description?: string;
}

export interface KnowledgeNode {
    id: string;
    x: number;
    y: number;
    label: string;
}

export interface KnowledgeMap {
    nodes: KnowledgeNode[];
}