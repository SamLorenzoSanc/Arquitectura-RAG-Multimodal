"use client";

import { useMemo, useState } from "react";
import { NavLink } from "react-router-dom";
import { useOrganization } from "@/context/OrganizationContext";
import { useShell } from "@/context/ShellContext";
import { NewOrgModal } from "./NewOrgModal";
import {
  Building2,
  MessageSquare,
  Settings,
  ChevronDown,
  Wheat,
  Tractor,
  Plus,
  Network,
  BrainCircuit,
  Database,
  TrendingUp,
  Ship,
  FileText,
  Container,
  Route,
  Navigation,
  X,
} from "lucide-react";

type NavGroupId = "work" | "ops" | "admin" | "labs";

const NAV_GROUPS: Record<NavGroupId, string> = {
  work: "Trabajo diario",
  ops: "Operaciones",
  admin: "Administración",
  labs: "Laboratorio",
};

const NAV_ITEMS: Array<{
  to: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  group: NavGroupId;
}> = [
  { to: "/dashboard/chat", label: "Chat IA", icon: MessageSquare, group: "work" },
  {
    to: "/dashboard/recogida",
    label: "Planificador de rutas",
    icon: Navigation,
    group: "work",
  },
  {
    to: "/dashboard/documentation",
    label: "Documentación",
    icon: FileText,
    group: "work",
  },
  { to: "/dashboard/fincas", label: "Fincas y mapas", icon: Tractor, group: "ops" },
  { to: "/dashboard/cultivos", label: "Cultivos", icon: Wheat, group: "ops" },
  { to: "/dashboard/analytics", label: "Analítica", icon: TrendingUp, group: "ops" },
  { to: "/dashboard/logistics", label: "Trazabilidad", icon: Ship, group: "ops" },
  { to: "/dashboard/flota", label: "Flota", icon: Ship, group: "ops" },
  {
    to: "/dashboard/reefer",
    label: "Contenedores reefer",
    icon: Container,
    group: "ops",
  },
  { to: "/dashboard/transito", label: "Tránsito", icon: Route, group: "ops" },
  {
    to: "/dashboard/organization",
    label: "Organización",
    icon: Building2,
    group: "admin",
  },
  { to: "/dashboard/tenants", label: "Inquilinos", icon: Tractor, group: "admin" },
  { to: "/dashboard/settings", label: "Configuración", icon: Settings, group: "admin" },
  {
    to: "/dashboard/knowledge-graph",
    label: "Grafo de conocimiento",
    icon: Network,
    group: "labs",
  },
  {
    to: "/dashboard/evaluacion",
    label: "Auditoría RAG",
    icon: BrainCircuit,
    group: "labs",
  },
  {
    to: "/dashboard/chroma-debug",
    label: "Base de datos",
    icon: Database,
    group: "labs",
  },
];

export default function Sidebar() {
  const { organizations, selectedOrg, setSelectedOrg, addOrganization } =
    useOrganization();
  const { sidebarOpen, closeSidebar } = useShell();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showOrgDropdown, setShowOrgDropdown] = useState(false);

  const grouped = useMemo(() => {
    const order: NavGroupId[] = ["work", "ops", "admin", "labs"];
    return order
      .map((group) => ({
        group,
        label: NAV_GROUPS[group],
        items: NAV_ITEMS.filter((item) => item.group === group),
      }))
      .filter((g) => g.items.length > 0);
  }, []);

  const panel = (
    <aside className="flex h-full w-72 max-w-[85vw] flex-col border-r border-[color:var(--agro-border)] bg-[color:var(--agro-surface)] shadow-xl shadow-slate-900/5 lg:w-64">
      <div className="flex items-center justify-between px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[color:var(--agro-primary)] shadow-md shadow-blue-900/20">
            <Wheat className="text-white" size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-900">
              AgroPS
            </h1>
            <p className="text-[10px] uppercase tracking-[0.18em] text-[color:var(--agro-accent)]">
              Agricultural Ops
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={closeSidebar}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
          aria-label="Cerrar menú"
        >
          <X size={18} />
        </button>
      </div>

      <div className="mx-4 h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent" />

      <div className="relative mt-4 px-4">
        <p className="mb-1.5 flex items-center justify-between text-[11px] font-semibold uppercase tracking-widest text-slate-500">
          <span>Organización</span>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="rounded-full p-0.5 text-[color:var(--agro-primary)] hover:bg-blue-50"
            title="Nueva organización"
          >
            <Plus size={12} />
          </button>
        </p>

        <button
          type="button"
          onClick={() => setShowOrgDropdown((v) => !v)}
          className="flex w-full items-center justify-between rounded-xl border border-[color:var(--agro-border)] bg-white px-3.5 py-2.5 transition hover:border-blue-300"
        >
          <div className="min-w-0 flex-1 pr-2 text-left">
            <p className="truncate text-sm font-semibold text-slate-800">
              {selectedOrg ? selectedOrg.name : "Seleccionar espacio"}
            </p>
            <p className="truncate text-[11px] text-slate-500">
              {selectedOrg?.description || "Ninguna seleccionada"}
            </p>
          </div>
          <ChevronDown
            size={16}
            className={`text-slate-400 transition ${showOrgDropdown ? "rotate-180" : ""}`}
          />
        </button>

        {showOrgDropdown && (
          <div className="absolute left-4 right-4 z-50 mt-1.5 max-h-52 overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-xl">
            {organizations.length === 0 ? (
              <div className="p-3 text-center text-xs text-slate-400">
                No hay organizaciones.
              </div>
            ) : (
              organizations.map((org) => (
                <button
                  key={org.id}
                  type="button"
                  onClick={() => {
                    setSelectedOrg(org);
                    setShowOrgDropdown(false);
                    closeSidebar();
                  }}
                  className={`flex w-full items-center gap-2 px-3 py-2.5 text-left text-xs transition ${
                    selectedOrg?.id === org.id
                      ? "bg-blue-50 font-semibold text-blue-900"
                      : "text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <Building2 size={14} className="shrink-0 text-blue-600" />
                  <span className="min-w-0 flex-1 truncate">{org.name}</span>
                  {(org.is_global ||
                    org.name?.toLowerCase() === "agrotech") && (
                    <span className="shrink-0 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-800">
                      Global
                    </span>
                  )}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <div className="mx-4 my-4 h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent" />

      <nav className="flex-1 space-y-4 overflow-y-auto px-3 pb-6">
        {grouped.map(({ group, label, items }) => (
          <div key={group}>
            <p className="mb-1.5 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
              {label}
            </p>
            <div className="space-y-0.5">
              {items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={closeSidebar}
                    className={({ isActive }) =>
                      `group flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-medium transition ${
                        isActive
                          ? "bg-[color:var(--agro-primary)] text-white shadow-md shadow-blue-900/15"
                          : "text-slate-600 hover:bg-white hover:text-[color:var(--agro-primary)] hover:shadow-sm"
                      }`
                    }
                  >
                    <Icon size={17} className="shrink-0 opacity-90" />
                    <span className="truncate">{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <NewOrgModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={async (name, description) => {
          await addOrganization(name, description);
          setIsModalOpen(false);
        }}
      />
    </aside>
  );

  return (
    <>
      <div className="hidden h-screen shrink-0 lg:block">{panel}</div>
      <div
        className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? "pointer-events-auto" : "pointer-events-none"}`}
      >
        <button
          type="button"
          aria-label="Cerrar menú"
          onClick={closeSidebar}
          className={`absolute inset-0 bg-slate-950/40 transition ${
            sidebarOpen ? "opacity-100" : "opacity-0"
          }`}
        />
        <div
          className={`absolute inset-y-0 left-0 transition-transform duration-300 ease-out ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          {panel}
        </div>
      </div>
    </>
  );
}
