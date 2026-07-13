export interface Organization {
    id: string;
    name: string;
    description: string;
    active: boolean;
    members: number;
    departments: number;
    tenants: number;
}

export interface OrganizationMember {
    id: string;
    name: string;
    email: string;
    role: string;
}