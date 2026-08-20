import type { KnowledgeBaseSummary } from "@/services/knowledge.service";

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
    departmentId?: string;
}

export interface Organization {
    id: string;
    name: string;
    description?: string;
    status?: string;
    is_global?: boolean;
    departments?: Department[];
    members?: Member[];
}

export interface OrgContextType {
    organizations: Organization[];
    selectedOrg: Organization | null;
    selectedDept: Department | null;
    knowledgeBases: KnowledgeBaseSummary[];
    generalKnowledgeBase: KnowledgeBaseSummary | null;
    setSelectedOrg: (org: Organization | null) => void;
    setSelectedDept: (dept: Department | null) => void;
    reloadKnowledgeBases: () => Promise<KnowledgeBaseSummary[]>;
    addOrganization: (name: string, description: string) => Promise<void>;
    setOrganizations: (orgs: Organization[]) => void;
}
