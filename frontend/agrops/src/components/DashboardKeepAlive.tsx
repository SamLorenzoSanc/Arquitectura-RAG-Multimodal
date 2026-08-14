import { useEffect, useMemo, useState, type ComponentType } from "react";
import { Navigate, useLocation } from "react-router-dom";

import ChatPage from "@/pages/ChatPage";
import CuadernoCampoPage from "@/pages/CuadernoCampoPage";
import DatasetsPage from "@/pages/DatasetsPage";
import OrganizationPage from "@/pages/OrganizationPage";
import TenantPage from "@/pages/TenantPage";
import SettingsPage from "@/pages/SettingsPage";
import KnowledgeGraphPage from "@/pages/KnowledgeGraphPage";
import EvaluationPage from "@/pages/EvalutionPage";
import HelpDocsPage from "@/pages/HelpDocsPage";
import SupportPage from "@/pages/SupportPage";

type DashRoute = {
  path: string;
  group: "work" | "admin" | "labs";
  Component: ComponentType;
};

const OPS_REDIRECTS = new Set([
  "/dashboard/cultivos",
  "/dashboard/almacenamiento",
  "/dashboard/analytics",
  "/dashboard/logistics",
  "/dashboard/flota",
  "/dashboard/reefer",
  "/dashboard/transito",
  "/dashboard/fincas",
  "/dashboard/farm-dashboard",
  "/dashboard/recogida",
]);

/** Páginas del panel centradas en documentación y evaluación RAG. */
export const DASHBOARD_ROUTES: DashRoute[] = [
  { path: "/dashboard/chat", group: "work", Component: ChatPage },
  { path: "/dashboard/cuaderno", group: "work", Component: CuadernoCampoPage },
  { path: "/dashboard/datasets", group: "work", Component: DatasetsPage },
  { path: "/dashboard/organization", group: "admin", Component: OrganizationPage },
  { path: "/dashboard/tenants", group: "admin", Component: TenantPage },
  { path: "/dashboard/settings", group: "admin", Component: SettingsPage },
  { path: "/dashboard/help", group: "admin", Component: HelpDocsPage },
  { path: "/dashboard/support", group: "admin", Component: SupportPage },
  {
    path: "/dashboard/knowledge-graph",
    group: "labs",
    Component: KnowledgeGraphPage,
  },
  { path: "/dashboard/evaluacion", group: "labs", Component: EvaluationPage },
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
    known.has(current) ? [current] : ["/dashboard/datasets"],
  );

  useEffect(() => {
    if (!known.has(current)) return;
    setVisited((prev) => (prev.includes(current) ? prev : [...prev, current]));
  }, [current, known]);

  if (current === "/dashboard/validacion") {
    return <Navigate to="/dashboard/evaluacion?tab=validacion" replace />;
  }

  if (current === "/dashboard/documentation" || OPS_REDIRECTS.has(current)) {
    return <Navigate to="/dashboard/datasets" replace />;
  }

  if (current === "/dashboard") {
    return <Navigate to="/dashboard/datasets" replace />;
  }

  if (!known.has(current)) {
    return <Navigate to="/dashboard/datasets" replace />;
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
                ? "flex h-full min-h-0 w-full flex-1 flex-col"
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
