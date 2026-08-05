"use client";

import { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { useOrganization } from "@/context/OrganizationContext"; 
import { NewOrgModal } from "./NewOrgModal";
import api from "@/api";

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
    MapPin,
    Package,
    FileText
} from "lucide-react";

// Función para obtener los roles del usuario autenticado
export const getMyRoles = async () => {
    const { data } = await api.get("/users/me/roles");
    return data;
};

export default function Sidebar() {
    const { organizations, selectedOrg, setSelectedOrg, addOrganization } = useOrganization();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [showOrgDropdown, setShowOrgDropdown] = useState(false);
    const [expandedOrgId, setExpandedOrgId] = useState<string | null>(null);

    // UUIDs y identificadores de roles especificados
    const FARM_MANAGER_UUID = "4ed47c72-d424-449f-af17-bad08e090f18";
    const LOGISTICS_OPERATOR_UUID = "e05a08fd-4119-4512-8c66-4dafc8ba963c";

    const [userRole, setUserRole] = useState<string>("FARM_MANAGER");
    const [loadingRole, setLoadingRole] = useState<boolean>(true);

    // Cargar el rol del usuario desde la API al montar el componente
    useEffect(() => {
        const fetchUserRole = async () => {
            try {
                const rolesData = await getMyRoles();
                if (rolesData) {
                    let roleIdentifier = "";
                    if (Array.isArray(rolesData) && rolesData.length > 0) {
                        roleIdentifier = rolesData[0].role_id || rolesData[0].role_name;
                    } else if (typeof rolesData === "object") {
                        roleIdentifier = rolesData.role_id || rolesData.role_name;
                    } else if (typeof rolesData === "string") {
                        roleIdentifier = rolesData;
                    }

                    // Mapear UUID o nombre al tipo correspondiente
                    if (roleIdentifier === FARM_MANAGER_UUID || roleIdentifier === "FARM_MANAGER") {
                        setUserRole("FARM_MANAGER");
                    } else if (roleIdentifier === LOGISTICS_OPERATOR_UUID || roleIdentifier === "LOGISTICS_OPERATOR") {
                        setUserRole("LOGISTICS_OPERATOR");
                    } else {
                        setUserRole("FARM_MANAGER");
                    }
                }
            } catch (error) {
                console.error("Error al obtener el rol para el sidebar:", error);
                setUserRole("FARM_MANAGER");
            } finally {
                setLoadingRole(false);
            }
        };

        fetchUserRole();
    }, []);

    // Definir los elementos del menú estrictamente filtrados según el rol activo (ocultando los ajenos)
    const getNavItems = () => {
        if (userRole === "FARM_MANAGER") {
            return [
                { to: "/dashboard/chat", icon: <MessageSquare size={17} />, text: "Chat IA Agrícola" },
                { to: "/dashboard/fincas", icon: <MapPin size={17} />, text: "Fincas y Producción" },
                { to: "/dashboard/cultivos", icon: <Wheat size={17} />, text: "Cultivos y Normativa IGP" },
                { to: "/dashboard/analytics", icon: <TrendingUp size={17} />, text: "Analítica de Demanda" },
                { to: "/dashboard/organization", icon: <Building2 size={17} />, text: "Organización" },
                { to: "/dashboard/knowledge-graph", icon: <Network size={17} />, text: "Grafo de Conocimiento" },
                { to: "/dashboard/evaluacion", icon: <BrainCircuit size={17} />, text: "Auditoría RAG" },
                { to: "/dashboard/settings", icon: <Settings size={17} />, text: "Configuración" },
            ];
        } else if (userRole === "LOGISTICS_OPERATOR") {
            return [
                { to: "/dashboard/chat", icon: <MessageSquare size={17} />, text: "Chat IA Logística" },
                { to: "/dashboard/flota", icon: <Ship size={17} />, text: "Flota Multiruta" },
                { to: "/dashboard/reefer", icon: <Package size={17} />, text: "Contenedores Reefer" },
                { to: "/dashboard/transito", icon: <FileText size={17} />, text: "Tiempos de Tránsito" },
                { to: "/dashboard/analytics", icon: <TrendingUp size={17} />, text: "Analítica Logística" },
                { to: "/dashboard/organization", icon: <Building2 size={17} />, text: "Organización" },
                { to: "/dashboard/evaluacion", icon: <BrainCircuit size={17} />, text: "Auditoría RAG" },
                { to: "/dashboard/settings", icon: <Settings size={17} />, text: "Configuración" },
            ];
        }
        return [{ to: "/dashboard/chat", icon: <MessageSquare size={17} />, text: "Chat IA" }];
    };

    const navItems = getNavItems();

    return (
        <aside className="w-64 h-screen flex flex-col bg-gradient-to-b from-blue-700 via-white to-amber-100/90 border-r border-blue-300 shadow-2xl shadow-blue-950/20 relative">
            
            {/* Logo y Branding con los colores oficiales de la Bandera de Canarias */}
            <div className="px-5 py-5 bg-blue-800 text-white border-b-4 border-amber-400 shadow-inner">
                <div className="flex items-center gap-3">
                    <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 via-blue-500 to-amber-400 shadow-lg shadow-blue-900/50 ring-2 ring-amber-300">
                        <div className="absolute inset-1 border border-white/30 rounded-xl pointer-events-none" />
                        <Wheat className="text-white drop-shadow-md" size={22} />
                    </div>
                    <div>
                        <div className="flex items-center gap-1.5">
                            <h1 className="text-lg font-extrabold tracking-tight text-white">AgroPS</h1>
                            <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-400 ring-1 ring-white shadow-sm" title="Bandera Canarias" />
                        </div>
                        <p className="text-[10px] uppercase tracking-widest text-amber-300 font-extrabold">
                            {userRole === "FARM_MANAGER" ? "Gestor de Fincas" : "Operador Logístico"}
                        </p>
                    </div>
                </div>
            </div>

            {/* Selector de Organización Dinámico */}
            <div className="px-4 mt-4 relative">
                <p className="mb-1.5 text-[11px] font-extrabold uppercase tracking-widest text-blue-900 flex justify-between items-center">
                    <span>Organización</span>
                    <button 
                        onClick={() => setIsModalOpen(true)}
                        className="text-blue-700 hover:text-blue-900 p-0.5 rounded-full hover:bg-amber-200 transition-colors"
                        title="Nueva Organización"
                    >
                        <Plus size={12} />
                    </button>
                </p>

                <button 
                    onClick={() => setShowOrgDropdown(!showOrgDropdown)}
                    className="group w-full rounded-xl border border-blue-300 bg-white px-3.5 py-2.5 flex justify-between items-center transition-all duration-300 hover:border-amber-500 hover:ring-2 hover:ring-amber-300 hover:shadow-md focus:outline-none"
                >
                    <div className="text-left min-w-0 flex-1 pr-2">
                        <p className="text-sm font-bold text-blue-950 truncate">
                            {selectedOrg ? selectedOrg.name : "Select Workspace"}
                        </p>
                        <p className="text-[11px] text-slate-500 truncate">
                            {selectedOrg?.description || "Ninguna seleccionada"}
                        </p>
                    </div>
                    <ChevronDown size={16} className={`text-blue-600 transition-transform duration-200 ${showOrgDropdown ? "rotate-180" : ""}`} />
                </button>

                {showOrgDropdown && (
                    <div className="absolute left-4 right-4 mt-1.5 bg-white border border-blue-300 rounded-xl shadow-2xl z-50 overflow-hidden max-h-44 overflow-y-auto animate-fade-in">
                        {organizations.length === 0 ? (
                            <div className="p-3 text-xs text-slate-400 text-center">No hay organizaciones creadas.</div>
                        ) : (
                            organizations.map((org) => {
                                const isExpanded = expandedOrgId === org.id;
                                return (
                                    <div key={org.id} className="border-b border-slate-100 last:border-b-0">
                                        <button
                                            onClick={() => setExpandedOrgId(isExpanded ? null : org.id)}
                                            className={`flex w-full items-center justify-between px-3 py-2.5 text-left text-xs transition-colors ${
                                                selectedOrg?.id === org.id
                                                    ? "bg-blue-100 text-blue-950 font-bold border-l-4 border-amber-500"
                                                    : "text-slate-700 hover:bg-blue-50"
                                            }`}
                                        >
                                            <span className="truncate">{org.name}</span>
                                            <ChevronDown
                                                size={14}
                                                className={`shrink-0 text-slate-400 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                                            />
                                        </button>
                                        {isExpanded && (
                                            <div className="border-t border-slate-100 bg-amber-50/50 px-3 py-2">
                                                <p className="text-[11px] text-slate-600">
                                                    {org.description || "Sin descripción disponible."}
                                                </p>
                                                <button
                                                    onClick={(event) => {
                                                        event.stopPropagation();
                                                        setSelectedOrg(org);
                                                        setShowOrgDropdown(false);
                                                        setExpandedOrgId(null);
                                                    }}
                                                    className="mt-1.5 rounded-lg bg-blue-700 px-2.5 py-1 text-[11px] font-bold text-white transition-colors hover:bg-blue-800 shadow-sm"
                                                >
                                                    Seleccionar
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                );
                            })
                        )}
                        <div className="border-t border-slate-100 p-1 bg-amber-50/30">
                            <button
                                onClick={() => {
                                    setIsModalOpen(true);
                                    setShowOrgDropdown(false);
                                }}
                                className="w-full py-1 text-center text-[11px] text-blue-800 font-bold hover:bg-white rounded-lg border border-dashed border-blue-400 transition-colors flex items-center justify-center gap-1"
                            >
                                <Plus size={12} /> Añadir nueva
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Tenant / Inquilino Activo */}
            <div className="px-4 mt-4">
                <p className="mb-1.5 text-[11px] font-extrabold uppercase tracking-widest text-blue-900">Inquilinos</p>
                <button className="group w-full rounded-xl border border-blue-300 bg-white px-3.5 py-2 flex justify-between items-center transition-all duration-300 hover:border-amber-500 hover:shadow-md">
                    <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-200 border border-amber-300">
                            <Tractor className="text-amber-800" size={16} />
                        </div>
                        <div className="text-left">
                            <p className="text-xs font-bold text-blue-950">
                                {userRole === "FARM_MANAGER" ? "Gestión Fincas" : "Logística Reefer"}
                            </p>
                            <p className="text-[10px] text-slate-500">Inquilino activo</p>
                        </div>
                    </div>
                    <ChevronDown size={16} className="text-slate-400" />
                </button>
            </div>

            <div className="mx-4 my-4 h-px bg-gradient-to-r from-transparent via-amber-400 to-transparent" />

            {/* Navegación Filtrada Dinámicamente */}
            <nav className="flex-1 px-3 space-y-1.5 overflow-y-auto">
                <p className="px-3 pb-1 text-[10px] font-bold uppercase tracking-wider text-blue-900/60">
                    Módulos Asignados
                </p>
                {loadingRole ? (
                    <div className="px-3 py-4 text-xs text-blue-900 text-center animate-pulse">
                        Cargando permisos...
                    </div>
                ) : (
                    navItems.map((item, idx) => (
                        <MenuItem key={idx} to={item.to} icon={item.icon} text={item.text} />
                    ))
                )}
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
                ${isActive
                    ? "bg-blue-700 text-white shadow-md shadow-blue-800/40 font-bold border-l-4 border-amber-400 ring-1 ring-blue-600"
                    : "text-blue-950 hover:bg-blue-100/70 hover:text-blue-900 hover:shadow-sm border border-transparent hover:border-blue-200"
                }
            `}
        >
            {icon}
            <span className="truncate">{text}</span>
        </NavLink>
    );
}