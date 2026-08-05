"use client";
import { createContext, useContext, useState} from "react";
import type { ReactNode } from "react";
import { createOrganization } from "@/services/organization.service";
import type { Organization, Department, OrgContextType } from "@/types/organization";


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