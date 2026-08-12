import { useEffect, useMemo, useState, type ComponentType } from "react";
import { Navigate, useLocation } from "react-router-dom";

import ChatPage from "@/pages/ChatPage";
import RecogidaPage from "@/pages/RecogidaPage";
import DocumentPage from "@/pages/DocumentationPage";
import FincasPage from "@/pages/FincasPage";
import CultivosPage from "@/pages/CultivosPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import LogisticsDashboard from "@/pages/LogisticDashboard";
import FlotaPage from "@/pages/FlotaPage";
import ReeferPage from "@/pages/ReeferPage";
import TransitoPage from "@/pages/TransitoPage";
import OrganizationPage from "@/pages/OrganizationPage";
import TenantPage from "@/pages/TenantPage";
import SettingsPage from "@/pages/SettingsPage";
import KnowledgeGraphPage from "@/pages/KnowledgeGraphPage";
import EvaluationPage from "@/pages/EvalutionPage";
import ChromaDebugPage from "@/pages/ChromaDebuPage";
import FarmDashboard from "@/pages/FarmDashboard";

type DashRoute = {
  path: string;
  group: "work" | "ops" | "admin" | "labs";
  Component: ComponentType;
};

/** Todas las páginas del panel de control, agrupadas como en el Sidebar. */
export const DASHBOARD_ROUTES: DashRoute[] = [
  // Trabajo diario
  { path: "/dashboard/chat", group: "work", Component: ChatPage },
  { path: "/dashboard/recogida", group: "work", Component: RecogidaPage },
  { path: "/dashboard/documentation", group: "work", Component: DocumentPage },
  // Operaciones
  { path: "/dashboard/fincas", group: "ops", Component: FincasPage },
  { path: "/dashboard/cultivos", group: "ops", Component: CultivosPage },
  { path: "/dashboard/analytics", group: "ops", Component: AnalyticsPage },
  { path: "/dashboard/logistics", group: "ops", Component: LogisticsDashboard },
  { path: "/dashboard/flota", group: "ops", Component: FlotaPage },
  { path: "/dashboard/reefer", group: "ops", Component: ReeferPage },
  { path: "/dashboard/transito", group: "ops", Component: TransitoPage },
  { path: "/dashboard/farm-dashboard", group: "ops", Component: FarmDashboard },
  // Administración
  { path: "/dashboard/organization", group: "admin", Component: OrganizationPage },
  { path: "/dashboard/tenants", group: "admin", Component: TenantPage },
  { path: "/dashboard/settings", group: "admin", Component: SettingsPage },
  // Laboratorio
  {
    path: "/dashboard/knowledge-graph",
    group: "labs",
    Component: KnowledgeGraphPage,
  },
  { path: "/dashboard/evaluacion", group: "labs", Component: EvaluationPage },
  { path: "/dashboard/chroma-debug", group: "labs", Component: ChromaDebugPage },
];

function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith("/")) {
    return pathname.slice(0, -1);
  }
  return pathname;
}

/**
 * Mantiene montadas las páginas ya visitadas del dashboard.
 * Al cambiar de pestaña solo se ocultan; no se destruye el árbol React
 * ni se vuelven a lanzar los useEffect de carga iniciales.
 */
export default function DashboardKeepAlive() {
  const { pathname } = useLocation();
  const current = normalizePath(pathname);

  const known = useMemo(
    () => new Set(DASHBOARD_ROUTES.map((r) => r.path)),
    [],
  );

  const [visited, setVisited] = useState<string[]>(() =>
    known.has(current) ? [current] : ["/dashboard/chat"],
  );

  useEffect(() => {
    if (!known.has(current)) return;
    setVisited((prev) => (prev.includes(current) ? prev : [...prev, current]));
  }, [current, known]);

  if (current === "/dashboard") {
    return <Navigate to="/dashboard/chat" replace />;
  }

  if (!known.has(current)) {
    return <Navigate to="/dashboard/chat" replace />;
  }

  return (
    <>
      {DASHBOARD_ROUTES.map(({ path, Component }) => {
        if (!visited.includes(path)) return null;
        const active = path === current;
        return (
          <div
            key={path}
            data-dashboard-page={path}
            aria-hidden={!active}
            className={
              active
                ? "flex min-h-0 w-full flex-1 flex-col"
                : "hidden"
            }
          >
            <Component />
          </div>
        );
      })}
    </>
  );
}
