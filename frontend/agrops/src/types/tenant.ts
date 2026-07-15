export interface Tenant {
    id: string;
    organization_id: string;
    name: string;
    description: string | null;
    active: boolean;
}

export interface CreateTenantRequest {
    name: string;
    description?: string;
}

export interface UpdateTenantRequest {
    name?: string;
    description?: string;
    active?: boolean;
}

export interface TenantListResponse {
    items: Tenant[];
    total: number;
}