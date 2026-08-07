"use client";

import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useOrganization } from "@/context/OrganizationContext";
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
  File,
} from "lucide-react";
import RagDocumentationPage from "@/pages/DocumentationPage";

export default function Sidebar() {
  const { organizations, selectedOrg, setSelectedOrg, addOrganization } =
    useOrganization();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showOrgDropdown, setShowOrgDropdown] = useState(false);
  const [expandedOrgId, setExpandedOrgId] = useState<string | null>(null);

  return (
    <aside className="w-64 h-screen flex flex-col bg-gradient-to-b from-white via-blue-50/30 to-amber-50/40 border-r border-blue-200/50 shadow-xl shadow-blue-950/5 relative">
      {/* Logo compacto */}
      <div className="px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 via-blue-500 to-amber-400 shadow-md shadow-blue-500/20">
            <Wheat className="text-white" size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-800">
              AgroPS
            </h1>
            <p className="text-[10px] uppercase tracking-widest text-blue-600/80">
              Agricultural Operations
            </p>
          </div>
        </div>
      </div>

      <div className="mx-4 h-px bg-gradient-to-r from-transparent via-blue-200 to-transparent" />

      {/* Selector de Organización Dinámico compacto */}
      <div className="px-4 mt-4 relative">
        <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-widest text-blue-800/80 flex justify-between items-center">
          <span>Organización</span>
          <button
            onClick={() => setIsModalOpen(true)}
            className="text-blue-600 hover:text-blue-700 p-0.5 rounded-full hover:bg-blue-100 transition-colors"
            title="Nueva Organización"
          >
            <Plus size={12} />
          </button>
        </p>

        <button
          onClick={() => setShowOrgDropdown(!showOrgDropdown)}
          className="group w-full rounded-xl border border-blue-200 bg-white px-3.5 py-2.5 flex justify-between items-center transition-all duration-300 hover:border-blue-400 hover:shadow-md focus:outline-none"
        >
          <div className="text-left min-w-0 flex-1 pr-2">
            <p className="text-sm font-semibold text-slate-800 truncate">
              {selectedOrg ? selectedOrg.name : "Select Workspace"}
            </p>
            <p className="text-[11px] text-slate-500 truncate">
              {selectedOrg?.description || "Ninguna seleccionada"}
            </p>
          </div>
          <ChevronDown
            size={16}
            className={`text-blue-500 transition-transform duration-200 ${showOrgDropdown ? "rotate-180" : ""}`}
          />
        </button>

        {showOrgDropdown && (
          <div className="absolute left-4 right-4 mt-1.5 bg-white border border-blue-200 rounded-xl shadow-xl z-50 overflow-hidden max-h-44 overflow-y-auto animate-fade-in">
            {organizations.length === 0 ? (
              <div className="p-3 text-xs text-slate-400 text-center">
                No hay organizaciones creadas.
              </div>
            ) : (
              organizations.map((org) => {
                const isExpanded = expandedOrgId === org.id;
                return (
                  <div
                    key={org.id}
                    className="border-b border-blue-50 last:border-b-0"
                  >
                    <button
                      onClick={() =>
                        setExpandedOrgId(isExpanded ? null : org.id)
                      }
                      className={`flex w-full items-center justify-between px-3 py-2.5 text-left text-xs transition-colors ${
                        selectedOrg?.id === org.id
                          ? "bg-blue-50 text-blue-900 font-medium"
                          : "text-slate-700 hover:bg-blue-50/50"
                      }`}
                    >
                      <span className="truncate">{org.name}</span>
                      <ChevronDown
                        size={14}
                        className={`shrink-0 text-blue-500 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                      />
                    </button>
                    {isExpanded && (
                      <div className="border-t border-blue-50 bg-blue-50/30 px-3 py-2">
                        <p className="text-[11px] text-slate-500">
                          {org.description || "Sin descripción disponible."}
                        </p>
                        <button
                          onClick={(event) => {
                            event.stopPropagation();
                            setSelectedOrg(org);
                            setShowOrgDropdown(false);
                            setExpandedOrgId(null);
                          }}
                          className="mt-1.5 rounded-lg bg-blue-600 px-2.5 py-1 text-[11px] font-semibold text-white transition-colors hover:bg-blue-700"
                        >
                          Seleccionar
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
            <div className="border-t border-blue-100 p-1 bg-blue-50/50">
              <button
                onClick={() => {
                  setIsModalOpen(true);
                  setShowOrgDropdown(false);
                }}
                className="w-full py-1 text-center text-[11px] text-blue-600 font-semibold hover:bg-white rounded-lg border border-dashed border-blue-300 transition-colors flex items-center justify-center gap-1"
              >
                <Plus size={12} /> Añadir nueva
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Tenant compacto */}
      <div className="px-4 mt-4">
        <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-widest text-blue-800/80">
          Inquilinos
        </p>
        <button className="group w-full rounded-xl border border-blue-200 bg-white px-3.5 py-2 flex justify-between items-center transition-all duration-300 hover:border-blue-400 hover:shadow-md">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100">
              <Tractor className="text-blue-600" size={16} />
            </div>
            <div className="text-left">
              <p className="text-xs font-semibold text-slate-800">Producción</p>
              <p className="text-[10px] text-slate-500">Inquilino activo</p>
            </div>
          </div>
          <ChevronDown size={16} className="text-blue-500" />
        </button>
      </div>

      <div className="mx-4 my-4 h-px bg-gradient-to-r from-transparent via-blue-200 to-transparent" />

      {/* Navegación más compacta */}
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        <MenuItem
          to="/dashboard/chat"
          icon={<MessageSquare size={17} />}
          text="Chat IA"
        />
        <MenuItem
          to="/dashboard/fincas"
          icon={<Tractor size={17} />}
          text="Fincas y Mapas"
        />
        <MenuItem
          to="/dashboard/analytics"
          icon={<TrendingUp size={17} />}
          text="Analítica de Demanda"
        />
        <MenuItem
          to="/dashboard/logistics"
          icon={<Ship size={17} />}
          text="Trazabilidad Marítima"
        />
        <MenuItem
          to="/dashboard/documentation"
          icon={<File size={17} />}
          text="Documentación"
        />
        <MenuItem
          to="/dashboard/organization"
          icon={<Building2 size={17} />}
          text="Organización"
        />
        <MenuItem
          to="/dashboard/tenants"
          icon={<Tractor size={17} />}
          text="Inquilinos"
        />
        <MenuItem
          to="/dashboard/settings"
          icon={<Settings size={17} />}
          text="Configuración"
        />
        <MenuItem
          to="/dashboard/knowledge-graph"
          icon={<Network size={17} />}
          text="Grafo de Conocimiento"
        />
        <MenuItem
          to="/dashboard/evaluacion"
          icon={<BrainCircuit size={17} />}
          text="Auditoría RAG"
        />
        <MenuItem
          to="/dashboard/chroma-debug"
          icon={<Database size={17} />}
          text="Base de Datos"
        />
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
}

interface MenuItemProps {
  to: string;
  icon: React.ReactNode;
  text: string;
}

function MenuItem({ to, icon, text }: MenuItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `
                group relative flex items-center gap-3 overflow-hidden rounded-xl px-4 py-2.5 text-xs font-medium transition-all duration-300
                ${
                  isActive
                    ? "bg-gradient-to-r from-blue-100 via-amber-100/60 to-blue-50 text-blue-900 shadow-sm ring-1 ring-blue-300 font-semibold"
                    : "text-slate-600 hover:bg-white hover:text-blue-600 hover:shadow-sm"
                }
            `}
    >
      <span className="text-blue-600">{icon}</span>
      <span className="truncate">{text}</span>
    </NavLink>
  );
}
