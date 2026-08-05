import api from "@/api";
import type { KnowledgeMap } from "@/types/knowledge";

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
class KnowledgeService {

    async getCurrent(): Promise<KnowledgeMap> {
        const response = await api.get<KnowledgeMap>(
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
