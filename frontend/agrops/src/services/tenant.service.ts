import api from "@/api";

import type { Tenant, TenantListResponse, CreateTenantRequest, UpdateTenantRequest} from "@/types/tenant";

class TenantService {

    private headers() {

        const token = localStorage.getItem("token");

        return {

            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        };
    }

    async list(): Promise<Tenant[]> {
        const response = await fetch(
            `${api}/tenants`,
            {
                headers: this.headers(),
            }

        );

        if (!response.ok)
            throw new Error("Cannot load tenants");

        const data: TenantListResponse = await response.json();

        return data.items;
    }

    async get(
        id: string,
    ): Promise<Tenant> {

        const response = await fetch(

            `${api}/tenants/${id}`,

            {

                headers: this.headers(),
            }

        );

        if (!response.ok)
            throw new Error("Tenant not found");

        return await response.json();
    }

    async create(
        request: CreateTenantRequest,
    ): Promise<Tenant> {
        const response = await fetch(
            `${api}/tenants`,
            {
                method: "POST",
                headers: this.headers(),
                body: JSON.stringify(request),
            }

        );

        if (!response.ok)
            throw new Error("Cannot create tenant");

        return await response.json();
    }

    async update(
        id: string,
        request: UpdateTenantRequest,
    ): Promise<Tenant> {

        const response = await fetch(

            `${api}/tenants/${id}`,

            {

                method: "PUT",

                headers: this.headers(),

                body: JSON.stringify(request),
            }

        );

        if (!response.ok)
            throw new Error("Cannot update tenant");

        return await response.json();
    }

    async delete(
        id: string,
    ): Promise<void> {

        const response = await fetch(

            `${api}/tenants/${id}`,

            {

                method: "DELETE",

                headers: this.headers(),
            }

        );

        if (!response.ok)
            throw new Error("Cannot delete tenant");
    }

    async activate(
        id: string,
    ) {

        return this.update(id, {
            active: true,
        });
    }

    async deactivate(
        id: string,
    ) {
        return this.update(id, {
            active: false,
        });
    }

}

export default new TenantService();