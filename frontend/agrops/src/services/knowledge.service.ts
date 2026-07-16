import api from "@/api";
import type { KnowledgeBase } from "@/types/knowledge";

export const getOrganizations = async () => {
    const { data } = await api.get("/organization");
    return data;
};

export const getOrganization = async (id: string) => {
    const { data } = await api.get(`/organization/${id}`);
    return data;
};

export const getOrganizationMembers = async (id: string) => {
    const { data } = await api.get(`/organization/${id}/members`);
    return data;
};

export const createOrganization = async (body: any) => {
    const { data } = await api.post("/organization", body);
    return data;
};

export const updateOrganization = async (
    id: string,
    body: any,
) => {
    const { data } = await api.put(`/organization/${id}`, body);
    return data;
};

export const deleteOrganization = async (id: string) => {
    await api.delete(`/organization/${id}`);
};

export interface KnowledgeNode {
    id: string;
    x: number;
    y: number;
    label: string;
    source?: string;
    chunk?: string;
}

export interface KnowledgeMap {
    nodes: KnowledgeNode[];
}

class KnowledgeService {

    async getCurrent(): Promise<KnowledgeBase> {
        const response = await api.get<KnowledgeBase>(
            "/knowledge/current"
        );

        return response.data;
    }

    async getMap(
        organizationId:string,
    ):Promise<KnowledgeMap>{


        const {data}=await api.get<KnowledgeMap>(
            `/organization/${organizationId}/knowledge-map`
        );


        return data;

    }
}

export default new KnowledgeService();
