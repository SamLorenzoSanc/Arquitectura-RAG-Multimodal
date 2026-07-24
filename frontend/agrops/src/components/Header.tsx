"use client";

import { 
    Bell, 
    LogOut, 
    ChevronDown, 
    AlertTriangle,
    CheckCircle2
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import api from "@/api";

// Obtener los roles del usuario autenticado en todas sus organizaciones
export const getMyRoles = async () => {
    const { data } = await api.get("/users/me/roles");
    return data;
};

export default function Header() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [currentDate, setCurrentDate] = useState("");
    const [currentTime, setCurrentTime] = useState("");
    const [showUserMenu, setShowUserMenu] = useState(false);
    
    // Estado para almacenar el rol del usuario
    const [userRoleLabel, setUserRoleLabel] = useState("Miembro");

    // Estados para las alertas dinámicas en la campana
    const [alertCount, setAlertCount] = useState<number>(0);
    const [alertsList, setAlertsList] = useState<any[]>([]);
    const [showAlertsDropdown, setShowAlertsDropdown] = useState<boolean>(false);

    // Obtener las iniciales del usuario para el avatar
    const initials = user?.name
        ?.split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase() || "US";

    // Obtener el primer nombre para el saludo
    const firstName = user?.name?.split(" ")[0] || "Usuario";

    // Cargar el rol del usuario al montar el componente
    useEffect(() => {
        const fetchUserRole = async () => {
            try {
                const rolesData = await getMyRoles();
                if (rolesData) {
                    if (Array.isArray(rolesData) && rolesData.length > 0) {
                        setUserRoleLabel(rolesData[0].role_name || "Miembro");
                    } else if (typeof rolesData === "object" && rolesData.role_name) {
                        setUserRoleLabel(rolesData.role_name);
                    } else if (typeof rolesData === "string") {
                        setUserRoleLabel(rolesData);
                    }
                }
            } catch (error) {
                console.error("Error al obtener el rol del usuario:", error);
                setUserRoleLabel("Miembro");
            }
        };

        fetchUserRole();
    }, []);

    // Sincronizar alertas dinámicas desde el backend de logística para la campana
    useEffect(() => {
        const fetchAlertsSummary = async () => {
            try {
                const res = await api.get("/logistics/alerts/summary");
                if (res.data) {
                    setAlertCount(res.data.totalAlerts);
                    setAlertsList(res.data.alerts);
                }
            } catch (error) {
                console.error("Error al obtener el resumen de alertas:", error);
            }
        };

        fetchAlertsSummary();
        const interval = setInterval(fetchAlertsSummary, 30000); // Actualización cada 30 segundos
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const updateDateTime = () => {
            const now = new Date();
            const dateFormatter = new Intl.DateTimeFormat("es-ES", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
            });
            const timeFormatter = new Intl.DateTimeFormat("es-ES", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            });
            setCurrentDate(dateFormatter.format(now));
            setCurrentTime(timeFormatter.format(now));
        };

        updateDateTime();
        const interval = setInterval(updateDateTime, 1000);
        return () => clearInterval(interval);
    }, []);

    const handleLogout = () => {
        logout();
        navigate("/login", { replace: true });
    };

    return (
        <header className="h-24 bg-white/80 backdrop-blur-md border-b border-slate-200 flex justify-between items-center px-8 sticky top-0 z-40">
            {/* Izquierda - Saludo y Fecha/Hora */}
            <div className="flex-1 flex flex-col justify-center">
                <h2 className="text-2xl font-bold text-slate-800 tracking-tight">
                    Hola, <span className="bg-gradient-to-r from-emerald-600 to-green-500 bg-clip-text text-transparent">{firstName}</span>
                </h2>
                <div className="flex items-center gap-2 mt-1">
                    <p className="text-sm font-medium text-emerald-700 capitalize">
                        {currentDate}
                    </p>
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-300"></span>
                    <p className="text-sm font-semibold text-slate-500 font-mono tracking-tight">
                        {currentTime}
                    </p>
                </div>
            </div>

            {/* Derecha - Notificaciones y Perfil */}
            <div className="flex-1 flex items-center justify-end gap-5">
                
                {/* Notificaciones (Campana Dinámica de Cadena de Frío) */}
                <div className="relative">
                    <button 
                        onClick={() => setShowAlertsDropdown(!showAlertsDropdown)}
                        className="relative p-2.5 rounded-full text-slate-500 hover:bg-slate-100 hover:text-emerald-600 transition-colors focus:outline-none cursor-pointer"
                        title="Alertas de Cadena de Frío"
                    >
                        <Bell size={22} />
                        {alertCount > 0 && (
                            <span className="absolute top-1 right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-rose-600 text-[10px] font-black text-white border-2 border-white animate-bounce">
                                {alertCount}
                            </span>
                        )}
                    </button>
                    
                    {/* Dropdown de Alertas Dinámicas */}
                    {showAlertsDropdown && (
                        <div className="absolute right-0 mt-3 w-80 bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                            <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                                <p className="text-sm font-bold text-slate-800">Alertas de Cadena de Frío</p>
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                    alertCount > 0 ? 'bg-rose-100 text-rose-700 border-rose-200' : 'bg-emerald-100 text-emerald-700 border-emerald-200'
                                }`}>
                                    {alertCount > 0 ? `${alertCount} Críticas` : 'Todo Estable'}
                                </span>
                            </div>
                            
                            <div className="p-2 space-y-2 max-h-72 overflow-y-auto">
                                {alertsList.length === 0 ? (
                                    <div className="p-4 text-center space-y-1">
                                        <CheckCircle2 size={24} className="mx-auto text-emerald-500" />
                                        <p className="text-xs font-semibold text-slate-700">Sin alertas térmicas</p>
                                        <p className="text-[11px] text-slate-400">Todos los contenedores reefer operan dentro de los umbrales seguros.</p>
                                    </div>
                                ) : (
                                    alertsList.map((alert, idx) => (
                                        <div key={idx} className="p-3 rounded-xl bg-rose-50 border border-rose-200 flex gap-3 items-start text-left">
                                            <AlertTriangle size={16} className="text-rose-600 shrink-0 mt-0.5" />
                                            <div>
                                                <p className="text-xs font-bold text-rose-900">{alert.product}</p>
                                                <p className="text-[11px] text-rose-800 mt-0.5 leading-snug">{alert.message}</p>
                                                <span className="inline-block mt-1 font-mono text-[9px] bg-rose-200/60 text-rose-900 px-2 py-0.5 rounded font-bold">
                                                    Contenedor: {alert.containerId}
                                                </span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Separador vertical */}
                <div className="w-px h-8 bg-slate-200"></div>

                {/* Perfil de Usuario */}
                <div className="relative">
                    <button
                        onClick={() => setShowUserMenu(!showUserMenu)}
                        className={`flex items-center gap-3 p-1.5 pr-4 rounded-full border transition-all duration-200 cursor-pointer ${
                            showUserMenu 
                                ? 'bg-slate-50 border-emerald-300 shadow-sm' 
                                : 'bg-white border-slate-200 hover:border-emerald-300 hover:shadow-sm'
                        }`}
                    >
                        <div className="h-9 w-9 rounded-full bg-gradient-to-br from-emerald-600 to-green-500 flex items-center justify-center text-sm font-bold text-white shadow-inner">
                            {initials}
                        </div>
                        <div className="text-left hidden lg:block">
                            <p className="text-sm font-bold text-slate-700 leading-tight">
                                {user?.name || "Usuario"}
                            </p>
                            <p className="text-xs font-medium text-slate-500 leading-tight mt-0.5 capitalize">
                                {userRoleLabel}
                            </p>
                        </div>
                        <ChevronDown 
                            size={16} 
                            className={`text-slate-400 transition-transform duration-200 hidden lg:block ${showUserMenu ? 'rotate-180' : ''}`} 
                        />
                    </button>

                    {showUserMenu && (
                        <div className="absolute right-0 mt-3 w-56 bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                            <div className="p-4 border-b border-slate-100 bg-slate-50/50 text-left">
                                <p className="font-bold text-slate-800 truncate">{user?.name || "Usuario"}</p>
                                <p className="text-xs font-medium text-slate-500 truncate mt-0.5">{user?.email || "usuario@email.com"}</p>
                                <span className="inline-block mt-2 bg-slate-100 text-slate-600 text-[10px] font-bold px-2 py-0.5 rounded-full border border-slate-200 capitalize">
                                    {userRoleLabel}
                                </span>
                            </div>
                            <div className="p-2 space-y-0.5">
                                <button className="w-full text-left px-3 py-2.5 text-sm font-medium text-slate-600 hover:text-emerald-700 hover:bg-emerald-50 rounded-xl transition-colors cursor-pointer">
                                    Mi Perfil
                                </button>
                                <button className="w-full text-left px-3 py-2.5 text-sm font-medium text-slate-600 hover:text-emerald-700 hover:bg-emerald-50 rounded-xl transition-colors cursor-pointer">
                                    Preferencias
                                </button>
                                <button className="w-full text-left px-3 py-2.5 text-sm font-medium text-slate-600 hover:text-emerald-700 hover:bg-emerald-50 rounded-xl transition-colors cursor-pointer">
                                    Centro de Ayuda
                                </button>
                            </div>
                            <div className="p-2 border-t border-slate-100">
                                <button
                                    onClick={handleLogout}
                                    className="w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium text-rose-600 hover:bg-rose-50 rounded-xl transition-colors group cursor-pointer"
                                >
                                    <span>Cerrar Sesión</span>
                                    <LogOut size={16} className="group-hover:translate-x-1 transition-transform" />
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}