"use client";
import { createContext, useContext, useState, ReactNode } from "react";
import { createOrganization } from "@/services/organization.service";

// Interfaces ampliadas
export interface Department {
    id: string;
    name: string;
    description?: string;
}

export interface Member {
    id: string;
    name: string;
    email: string;
    role: string;
    departmentId?: string; // Vinculación clave
}

export interface Organization {
    id: string;
    name: string;
    description?: string;
    status: string;
    departments?: Department[];
    members?: Member[];
}

interface OrgContextType {
    organizations: Organization[];
    selectedOrg: Organization | null;
    selectedDept: Department | null;
    setSelectedOrg: (org: Organization | null) => void;
    setSelectedDept: (dept: Department | null) => void;
    addOrganization: (name: string, description: string) => Promise<void>;
    setOrganizations: (orgs: Organization[]) => void;
}

const OrganizationContext = createContext<OrgContextType | undefined>(undefined);

export function OrganizationProvider({ children }: { children: ReactNode }) {
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
    const [selectedDept, setSelectedDept] = useState<Department | null>(null);

    const addOrganization = async (name: string, description: string) => {
        const created = await createOrganization({ name, description });

        const newOrg: Organization = {
            id: created.organization_id ?? created.id,
            name,
            description,
            status: "ACTIVE",
            departments: [],
            members: []
        };

        setOrganizations((prev) => {
            if (prev.some((org) => org.id === newOrg.id)) {
                return prev;
            }
            return [...prev, newOrg];
        });
        setSelectedOrg(newOrg);
    };

    return (
        <OrganizationContext.Provider value={{ 
            organizations, selectedOrg, selectedDept, 
            setSelectedOrg, setSelectedDept, addOrganization, setOrganizations 
        }}>
            {children}
        </OrganizationContext.Provider>
    );
}

export function useOrganization() {
    const context = useContext(OrganizationContext);
    if (!context) throw new Error("useOrganization debe usarse dentro de un OrganizationProvider");
    return context;
}