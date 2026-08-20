import { useEffect, useMemo, useState, type ComponentType } from "react";
import { Navigate, useLocation } from "react-router-dom";

import DocumentsPage from "@/pages/DocumentsPage";
import EvaluationPage from "@/pages/EvalutionPage";
import HelpDocsPage from "@/pages/HelpDocsPage";
import KnowledgeGraphPage from "@/pages/KnowledgeGraphPage";
import OrganizationPage from "@/pages/OrganizationPage";
import RagPipelinePage from "@/pages/RagPipelinePage";
import SettingsPage from "@/pages/SettingsPage";
import SupportPage from "@/pages/SupportPage";
import ValidacionHumanaPage from "@/pages/ValidacionHumanaPage";
import DashboardOverview from "@/pages/Dashboard";

type DashRoute = {
  path: string;
  Component: ComponentType;
};

const DEFAULT_DASHBOARD = "/dashboard";

export const DASHBOARD_ROUTES: DashRoute[] = [
  { path: "/dashboard", Component: DashboardOverview },
  { path: "/dashboard/documentos", Component: DocumentsPage },
  { path: "/dashboard/embeddings", Component: KnowledgeGraphPage },
  { path: "/dashboard/flujo-rag", Component: RagPipelinePage },
  { path: "/dashboard/evaluacion", Component: EvaluationPage },
  { path: "/dashboard/validacion", Component: ValidacionHumanaPage },
  { path: "/dashboard/organization", Component: OrganizationPage },
  { path: "/dashboard/docs", Component: HelpDocsPage },
  { path: "/dashboard/settings", Component: SettingsPage },
  { path: "/dashboard/support", Component: SupportPage },
];

function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith("/")) {
    return pathname.slice(0, -1);
  }
  return pathname;
}

export default function DashboardKeepAlive() {
  const { pathname } = useLocation();
  const current = normalizePath(pathname);

  const known = useMemo(
    () => new Set(DASHBOARD_ROUTES.map((r) => r.path)),
    [],
  );

  const [visited, setVisited] = useState<string[]>(() =>
    known.has(current) ? [current] : [DEFAULT_DASHBOARD],
  );

  useEffect(() => {
    if (!known.has(current)) return;
    setVisited((prev) => (prev.includes(current) ? prev : [...prev, current]));
  }, [current, known]);

  if (current === "/dashboard/proyectos") {
    return <Navigate to="/dashboard/documentos" replace />;
  }

  if (current === "/dashboard/guardrails") {
    return <Navigate to="/dashboard/evaluacion" replace />;
  }

  if (current === "/dashboard/chat") {
    return <Navigate to={DEFAULT_DASHBOARD} replace />;
  }

  if (!known.has(current)) {
    return <Navigate to={DEFAULT_DASHBOARD} replace />;
  }

  return (
    <>
      {DASHBOARD_ROUTES.map(({ path, Component }) => {
        const active = path === current;
        // El canvas WebGL no sobrevive a display:none: montar solo en la ruta activa.
        if (path === "/dashboard/embeddings") {
          if (!active) return null;
          return (
            <div
              key={path}
              data-dashboard-page={path}
              className="flex h-full min-h-0 w-full flex-1 flex-col"
            >
              <Component />
            </div>
          );
        }
        if (!visited.includes(path)) return null;
        return (
          <div
            key={path}
            data-dashboard-page={path}
            aria-hidden={!active}
            className={
              active
                ? "flex min-h-full w-full flex-col"
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
