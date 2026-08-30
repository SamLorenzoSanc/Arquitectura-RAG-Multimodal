import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { jwtDecode } from "jwt-decode";
import api from "@/api";
import {
  AccountService,
  KnowledgeService,
  createOrganization,
  getOrganizations,
  login as loginService,
} from "@/services";
import type { Department, KnowledgeBaseSummary, Organization, OrgContextType } from "@/types";
import { queryKeys } from "@/lib/app";
import { queryClient } from "@/lib/queryClient";

/* --- context/AuthContext.tsx --- */

interface JwtPayload {
  sub: string;
  email: string;
  exp: number;
}

export interface User {
  id: string;
  name: string;
  email: string;
  exp: number;
  isAdmin: boolean;
  jobTitle?: string | null;
  phone?: string | null;
  island?: string | null;
  hasAvatar?: boolean;
  avatarUrl?: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  updateUser: (patch: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

async function loadCurrentUser(token: string): Promise<User> {
  const decoded = jwtDecode<JwtPayload>(token);
  const { data } = await api.get("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });

  let avatarUrl: string | null = null;
  if (data.has_avatar) {
    try {
      avatarUrl = await AccountService.avatarObjectUrl();
    } catch {
      avatarUrl = null;
    }
  }

  return {
    id: decoded.sub,
    exp: decoded.exp,
    email: data.email,
    name: data.name,
    isAdmin: Boolean(data.is_admin),
    jobTitle: data.job_title,
    phone: data.phone,
    island: data.island,
    hasAvatar: Boolean(data.has_avatar),
    avatarUrl,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem("token"),
  );
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    async function initialize() {
      const savedToken = localStorage.getItem("token");
      if (!savedToken) {
        setToken(null);
        setUser(null);
        return;
      }

      try {
        const decoded = jwtDecode<JwtPayload>(savedToken);
        if (decoded.exp * 1000 < Date.now()) {
          localStorage.removeItem("token");
          setToken(null);
          setUser(null);
          return;
        }

        const currentUser = await loadCurrentUser(savedToken);
        setToken(savedToken);
        setUser(currentUser);
      } catch {
        localStorage.removeItem("token");
        setToken(null);
        setUser(null);
      }
    }

    void initialize();
  }, []);

  async function login(email: string, password: string) {
    const response = await loginService({ email, password });
    const jwt = response.access_token;
    localStorage.setItem("token", jwt);
    const currentUser = await loadCurrentUser(jwt);
    setToken(jwt);
    setUser(currentUser);
  }

  function logout() {
    localStorage.removeItem("token");
    sessionStorage.removeItem("token");
    setUser((current) => {
      if (current?.avatarUrl) URL.revokeObjectURL(current.avatarUrl);
      return null;
    });
    setToken(null);
  }

  function updateUser(patch: Partial<User>) {
    setUser((current) => {
      if (!current) return current;
      if (
        patch.avatarUrl &&
        current.avatarUrl &&
        patch.avatarUrl !== current.avatarUrl
      ) {
        URL.revokeObjectURL(current.avatarUrl);
      }
      return { ...current, ...patch };
    });
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        updateUser,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe utilizarse dentro de AuthProvider");
  }
  return context;
}

/* --- context/OrganizationContext.tsx --- */

const GLOBAL_ORG_NAME = "AgroTech";
const SELECTED_ORG_KEY = "agrops.selectedOrgId";
const GENERAL_KB_NAME = "Base de Conocimiento General";

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

function pickGeneralKnowledgeBase(
  items: KnowledgeBaseSummary[],
): KnowledgeBaseSummary | null {
  if (!items.length) return null;
  const general = items.find((item) =>
    (item.name || "").toLowerCase().includes("general"),
  );
  if (general) return general;
  return [...items].sort((a, b) =>
    String(a.created_at || "").localeCompare(String(b.created_at || "")),
  )[0];
}

export function OrganizationProvider({ children }: { children: ReactNode }) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrgState] = useState<Organization | null>(
    null,
  );
  const [selectedDept, setSelectedDept] = useState<Department | null>(null);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseSummary[]>(
    [],
  );
  const [generalKnowledgeBase, setGeneralKnowledgeBase] =
    useState<KnowledgeBaseSummary | null>(null);

  const setSelectedOrg = useCallback((org: Organization | null) => {
    setSelectedOrgState(org);
    setSelectedDept(null);
    setKnowledgeBases([]);
    setGeneralKnowledgeBase(null);
    if (typeof window === "undefined") return;
    if (org?.id) {
      window.localStorage.setItem(SELECTED_ORG_KEY, org.id);
    } else {
      window.localStorage.removeItem(SELECTED_ORG_KEY);
    }
  }, []);

  const applyKnowledgeBases = useCallback((items: KnowledgeBaseSummary[]) => {
    setKnowledgeBases(items);
    setGeneralKnowledgeBase(pickGeneralKnowledgeBase(items));
  }, []);

  const reloadKnowledgeBases = useCallback(async () => {
    if (!selectedOrg?.id) {
      setKnowledgeBases([]);
      setGeneralKnowledgeBase(null);
      return [];
    }
    let items = await KnowledgeService.list(selectedOrg.id);
    if (!items.length) {
      const created = await KnowledgeService.create({
        name: GENERAL_KB_NAME,
        description:
          "Repositorio compartido de la organización para todos los agricultores.",
        organizationId: selectedOrg.id,
      });
      items = [created];
    }
    applyKnowledgeBases(items);
    return items;
  }, [applyKnowledgeBases, selectedOrg?.id]);

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

  useEffect(() => {
    if (!selectedOrg?.id) {
      setKnowledgeBases([]);
      setGeneralKnowledgeBase(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        let items = await KnowledgeService.list(selectedOrg.id);
        if (!cancelled && !items.length) {
          const created = await KnowledgeService.create({
            name: GENERAL_KB_NAME,
            description:
              "Repositorio compartido de la organización para todos los agricultores.",
            organizationId: selectedOrg.id,
          });
          items = [created];
        }
        if (!cancelled) applyKnowledgeBases(items);
      } catch {
        if (!cancelled) {
          setKnowledgeBases([]);
          setGeneralKnowledgeBase(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applyKnowledgeBases, selectedOrg?.id]);

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
        knowledgeBases,
        generalKnowledgeBase,
        setSelectedOrg,
        setSelectedDept,
        reloadKnowledgeBases,
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

/* --- context/ShellContext.tsx --- */

interface ShellContextType {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  openSidebar: () => void;
  closeSidebar: () => void;
  toggleSidebar: () => void;
  toggleCollapsed: () => void;
}

const ShellContext = createContext<ShellContextType | null>(null);

export function ShellProvider({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const value = useMemo(
    () => ({
      sidebarOpen,
      sidebarCollapsed,
      openSidebar: () => setSidebarOpen(true),
      closeSidebar: () => setSidebarOpen(false),
      toggleSidebar: () => setSidebarOpen((v) => !v),
      toggleCollapsed: () => setSidebarCollapsed((v) => !v),
    }),
    [sidebarOpen, sidebarCollapsed],
  );

  return <ShellContext.Provider value={value}>{children}</ShellContext.Provider>;
}

export function useShell() {
  const ctx = useContext(ShellContext);
  if (!ctx) throw new Error("useShell debe usarse dentro de ShellProvider");
  return ctx;
}

