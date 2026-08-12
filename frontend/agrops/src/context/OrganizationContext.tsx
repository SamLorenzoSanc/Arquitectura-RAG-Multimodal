"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  createOrganization,
  getOrganizations,
} from "@/services/organization.service";
import type {
  Organization,
  Department,
  OrgContextType,
} from "@/types/organization";
import { queryClient } from "@/lib/queryClient";
import { queryKeys } from "@/lib/queryKeys";

const GLOBAL_ORG_NAME = "AgroTech";
const SELECTED_ORG_KEY = "agrops.selectedOrgId";

const OrganizationContext = createContext<OrgContextType | undefined>(
  undefined,
);

function isAgroTech(org: Organization): boolean {
  return (
    Boolean(org.is_global) ||
    org.name?.toLowerCase() === GLOBAL_ORG_NAME.toLowerCase()
  );
}

function sortOrgs(orgs: Organization[]): Organization[] {
  return [...orgs].sort((a, b) => {
    const ag = isAgroTech(a) ? 0 : 1;
    const bg = isAgroTech(b) ? 0 : 1;
    if (ag !== bg) return ag - bg;
    return (a.name || "").localeCompare(b.name || "", "es");
  });
}

function pickDefaultOrg(orgs: Organization[]): Organization | null {
  if (!orgs.length) return null;

  const storedId =
    typeof window !== "undefined"
      ? window.localStorage.getItem(SELECTED_ORG_KEY)
      : null;
  if (storedId) {
    const stored = orgs.find((o) => o.id === storedId);
    if (stored) return stored;
  }

  const agro = orgs.find(isAgroTech);
  return agro ?? orgs[0] ?? null;
}

function normalizeOrgs(data: unknown): Organization[] {
  if (!Array.isArray(data)) return [];
  const orgs = data
    .map((raw: any) => ({
      id: String(raw.id ?? raw.organization_id ?? ""),
      name: String(raw.name ?? ""),
      description: raw.description ?? undefined,
      status: raw.status ?? (raw.active ? "ACTIVE" : "INACTIVE"),
      is_global: Boolean(
        raw.is_global ||
          String(raw.name ?? "").toLowerCase() === GLOBAL_ORG_NAME.toLowerCase(),
      ),
      departments: raw.departments ?? [],
      members: raw.members ?? [],
    }))
    .filter((o) => o.id && o.name);
  return sortOrgs(orgs);
}

export function OrganizationProvider({ children }: { children: ReactNode }) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrgState] = useState<Organization | null>(
    null,
  );
  const [selectedDept, setSelectedDept] = useState<Department | null>(null);

  const setSelectedOrg = useCallback((org: Organization | null) => {
    setSelectedOrgState(org);
    if (typeof window === "undefined") return;
    if (org?.id) {
      window.localStorage.setItem(SELECTED_ORG_KEY, org.id);
    } else {
      window.localStorage.removeItem(SELECTED_ORG_KEY);
    }
  }, []);

  const loadOrganizations = useCallback(async () => {
    try {
      const data = await getOrganizations();
      const orgs = normalizeOrgs(data);
      setOrganizations(orgs);
      setSelectedOrgState((prev) => {
        if (prev && orgs.some((o) => o.id === prev.id)) return prev;
        const next = pickDefaultOrg(orgs);
        if (next?.id && typeof window !== "undefined") {
          window.localStorage.setItem(SELECTED_ORG_KEY, next.id);
        }
        return next;
      });
    } catch (error) {
      console.error("Error cargando organizaciones:", error);
    }
  }, []);

  useEffect(() => {
    void loadOrganizations();
  }, [loadOrganizations]);

  const addOrganization = async (name: string, description: string) => {
    const created = await createOrganization({ name, description });

    const newOrg: Organization = {
      id: created.organization_id ?? created.id,
      name,
      description,
      status: "ACTIVE",
      is_global: false,
      departments: [],
      members: [],
    };

    setOrganizations((prev) => {
      if (prev.some((org) => org.id === newOrg.id)) {
        return sortOrgs(prev);
      }
      return sortOrgs([...prev, newOrg]);
    });
    setSelectedOrg(newOrg);
    void queryClient.invalidateQueries({ queryKey: queryKeys.organizations });
  };

  return (
    <OrganizationContext.Provider
      value={{
        organizations,
        selectedOrg,
        selectedDept,
        setSelectedOrg,
        setSelectedDept,
        addOrganization,
        setOrganizations,
      }}
    >
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  const context = useContext(OrganizationContext);
  if (!context)
    throw new Error(
      "useOrganization debe usarse dentro de un OrganizationProvider",
    );
  return context;
}
