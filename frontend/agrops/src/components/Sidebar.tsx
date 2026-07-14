import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useOrganization } from "@/context/OrganizationContext"; // Ajusta la ruta a tu contexto
import {NewOrgModal} from "./NewOrgModal"; // El componente modal popup que has creado

import {
    Building2,
    MessageSquare,
    Settings,
    ChevronDown,
    Wheat,
    Tractor,
    LogOut,
    Plus,
} from "lucide-react";

export default function Sidebar() {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    
    // 1. Estados y variables de las organizaciones globales
    const { organizations, selectedOrg, setSelectedOrg, addOrganization } = useOrganization();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [showOrgDropdown, setShowOrgDropdown] = useState(false);
    const [expandedOrgId, setExpandedOrgId] = useState<string | null>(null);

    const handleLogout = () => {
        logout();
        navigate("/login", { replace: true });
    };

    const initials =
        user?.name
            ?.split(" ")
            .map((name) => name[0])
            .join("")
            .slice(0, 2)
            .toUpperCase() ?? "U";

    return (
        <aside className="w-72 h-screen flex flex-col bg-gradient-to-b from-white via-slate-50 to-slate-100/70 border-r border-slate-200 shadow-2xl shadow-slate-200/40 relative">
            
            {/* Logo */}
            <div className="px-7 py-8">
                <div className="flex items-center gap-4">
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-green-700 via-emerald-600 to-lime-500 shadow-lg shadow-green-500/30">
                        <Wheat className="text-white" size={30} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">AgroPS</h1>
                        <p className="text-xs uppercase tracking-widest text-slate-500">Agricultural Operations</p>
                    </div>
                </div>
            </div>

            <div className="mx-6 h-px bg-gradient-to-r from-transparent via-slate-300 to-transparent" />

            {/* Selector de Organización Dinámico */}
            <div className="px-6 mt-6 relative">
                <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500 flex justify-between items-center">
                    <span>Organización</span>
                    <button 
                        onClick={() => setIsModalOpen(true)}
                        className="text-emerald-600 hover:text-emerald-700 p-0.5 rounded-full hover:bg-emerald-50 transition-colors"
                        title="Nueva Organización"
                    >
                        <Plus size={14} />
                    </button>
                </p>

                {/* Botón Principal del Selector */}
                <button 
                    onClick={() => setShowOrgDropdown(!showOrgDropdown)}
                    className="group w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 flex justify-between items-center transition-all duration-300 hover:border-green-300 hover:shadow-lg focus:outline-none"
                >
                    <div className="text-left min-w-0 flex-1 pr-2">
                        <p className="font-semibold text-slate-800 truncate">
                            {selectedOrg ? selectedOrg.name : "Select Workspace"}
                        </p>
                        <p className="text-xs text-slate-500 truncate">
                            {selectedOrg?.description || "Ninguna seleccionada"}
                        </p>
                    </div>
                    <ChevronDown size={18} className={`text-slate-400 transition-transform duration-200 ${showOrgDropdown ? "rotate-180" : ""}`} />
                </button>

                {/* Menú desplegable flotante de selección */}
                {showOrgDropdown && (
                    <div className="absolute left-6 right-6 mt-2 bg-white border border-slate-200 rounded-2xl shadow-xl z-50 overflow-hidden max-h-48 overflow-y-auto animate-fade-in">
                        {organizations.length === 0 ? (
                            <div className="p-3 text-sm text-slate-400 text-center">No hay organizaciones creadas.</div>
                        ) : (
                            organizations.map((org) => {
                                const isExpanded = expandedOrgId === org.id;
                                return (
                                    <div key={org.id} className="border-b border-slate-100 last:border-b-0">
                                        <button
                                            onClick={() => setExpandedOrgId(isExpanded ? null : org.id)}
                                            className={`flex w-full items-center justify-between px-4 py-3 text-left text-sm transition-colors ${
                                                selectedOrg?.id === org.id
                                                    ? "bg-emerald-50 text-emerald-700 font-medium"
                                                    : "text-slate-700 hover:bg-slate-50"
                                            }`}
                                        >
                                            <span className="truncate">{org.name}</span>
                                            <ChevronDown
                                                size={16}
                                                className={`shrink-0 text-slate-400 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                                            />
                                        </button>
                                        {isExpanded && (
                                            <div className="border-t border-slate-100 bg-slate-50/70 px-4 py-3">
                                                <p className="text-xs text-slate-500">
                                                    {org.description || "Sin descripción disponible."}
                                                </p>
                                                <button
                                                    onClick={(event) => {
                                                        event.stopPropagation();
                                                        setSelectedOrg(org);
                                                        setShowOrgDropdown(false);
                                                        setExpandedOrgId(null);
                                                    }}
                                                    className="mt-2 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-emerald-700"
                                                >
                                                    Seleccionar
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                );
                            })
                        )}
                        <div className="border-t border-slate-100 p-1.5 bg-slate-50/50">
                            <button
                                onClick={() => {
                                    setIsModalOpen(true);
                                    setShowOrgDropdown(false);
                                }}
                                className="w-full py-1.5 text-center text-xs text-emerald-600 font-semibold hover:bg-white rounded-xl border border-dashed border-emerald-200 transition-colors flex items-center justify-center gap-1"
                            >
                                <Plus size={12} /> Añadir nueva
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Tenant */}
            <div className="px-6 mt-6">
                <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500">Tenant</p>
                <button className="group w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 flex justify-between items-center transition-all duration-300 hover:border-green-300 hover:shadow-lg">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-100">
                            <Tractor className="text-green-700" size={18} />
                        </div>
                        <div>
                            <p className="font-semibold text-slate-800">Producción</p>
                            <p className="text-xs text-slate-500">Tenant activo</p>
                        </div>
                    </div>
                    <ChevronDown size={18} className="text-slate-400" />
                </button>
            </div>

            <div className="mx-6 my-8 h-px bg-gradient-to-r from-transparent via-slate-300 to-transparent" />

            {/* Navegación */}
            <nav className="flex-1 px-4 space-y-2">
                <MenuItem to="/dashboard/chat" icon={<MessageSquare size={20} />} text="Chat IA" />
                <MenuItem to="/dashboard/organization" icon={<Building2 size={20} />} text="Organización" />
                <MenuItem to="/dashboard/tenants" icon={<Tractor size={20} />} text="Tenants" />
                <MenuItem to="/dashboard/settings" icon={<Settings size={20} />} text="Configuración" />
            </nav>

            {/* Usuario */}
            <div className="mt-auto border-t border-slate-200 bg-white/60 backdrop-blur-xl p-5">
                <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-lg shadow-slate-200/40">
                    <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-green-700 via-emerald-600 to-lime-500 text-lg font-bold text-white">
                            {initials}
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="truncate font-semibold text-slate-900">{user?.name}</p>
                            <p className="truncate text-sm text-slate-500">{user?.email}</p>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl border border-red-200 bg-red-50 py-3 font-medium text-red-600 transition-all duration-200 hover:-translate-y-0.5 hover:border-red-300 hover:bg-red-100 hover:shadow-md active:scale-95"
                    >
                        <LogOut size={18} />
                        Cerrar sesión
                    </button>
                </div>
            </div>

            {/* 2. Inyección del Pop-up Modal */}
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
                group relative flex items-center gap-4 overflow-hidden rounded-2xl px-5 py-3.5 text-sm font-medium transition-all duration-300
                ${isActive
                    ? "bg-gradient-to-r from-green-100 via-emerald-50 to-lime-50 text-green-700 shadow-md ring-1 ring-green-200"
                    : "text-slate-600 hover:bg-white hover:text-green-700 hover:shadow-md hover:-translate-y-0.5"
                }
            `}
        >
            {icon}
            <span>{text}</span>
        </NavLink>
    );
}