import api from "@/api";
import type { Organization } from "@/types/organization";

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

const OrganizationService = {


    async getAll(): Promise<Organization[]> {


        const response =
            await api.get(
                "/organization"
            );


        return response.data;


    },


};


export default OrganizationService;