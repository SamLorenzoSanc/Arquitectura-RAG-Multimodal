import { Bell, UserCircle2, Cloud, CloudRain, Sun, LogOut } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function Header() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [currentDate, setCurrentDate] = useState("");
    const [currentTime, setCurrentTime] = useState("");
    const [showUserMenu, setShowUserMenu] = useState(false);
    const [weather, setWeather] = useState({
        temp: 24,
        condition: "Parcialmente nublado",
        icon: "cloud",
        humidity: 65,
        windSpeed: 12,
    });

    useEffect(() => {
        // Actualizar fecha y hora
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

    const getWeatherIcon = () => {
        switch (weather.icon) {
            case "sun":
                return <Sun size={24} className="text-yellow-500" />;
            case "rain":
                return <CloudRain size={24} className="text-blue-500" />;
            default:
                return <Cloud size={24} className="text-gray-400" />;
        }
    };

    const handleLogout = () => {
        logout();
        navigate("/login", { replace: true });
    };

    return (
        <header className="h-20 bg-white border-b flex justify-between items-center px-8 shadow-sm">
            {/* Left side - Title and Date/Time */}
            <div className="flex-1">
                <h2 className="text-2xl font-bold text-gray-800">AgroPS</h2>
                <p className="text-xs text-gray-400 capitalize">
                    {currentDate} • {currentTime}
                </p>
            </div>

            {/* Center - Weather Widget */}
            <div className="flex-1 flex justify-center">
                <div className="bg-gradient-to-r from-blue-50 to-green-50 rounded-lg px-4 py-2 flex items-center gap-3 border border-gray-200">
                    {getWeatherIcon()}
                    <div className="text-sm">
                        <p className="font-semibold text-gray-700">{weather.temp}°C</p>
                        <p className="text-xs text-gray-500">{weather.condition}</p>
                        <div className="flex gap-3 text-xs text-gray-500 mt-1">
                            <span>💧 {weather.humidity}%</span>
                            <span>💨 {weather.windSpeed} km/h</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right side - Notifications and User Profile */}
            <div className="flex-1 flex items-center justify-end gap-6">
                {/* Notifications */}
                <div className="relative cursor-pointer group">
                    <Bell className="text-gray-500 hover:text-gray-700 transition" size={22} />
                    <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                    <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg p-4 hidden group-hover:block z-50 border border-gray-200">
                        <p className="text-sm font-semibold text-gray-700 mb-3">Notificaciones</p>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                            <div className="text-xs text-gray-600 p-2 hover:bg-gray-50 rounded cursor-pointer">
                                Sincronización completada
                            </div>
                            <div className="text-xs text-gray-600 p-2 hover:bg-gray-50 rounded cursor-pointer">
                                Tienes 3 tareas pendientes
                            </div>
                            <div className="text-xs text-gray-600 p-2 hover:bg-gray-50 rounded cursor-pointer">
                                 Reporte diario disponible
                            </div>
                        </div>
                    </div>
                </div>

                {/* User Profile Dropdown */}
                <div className="relative">
                    <div
                        onClick={() => setShowUserMenu(!showUserMenu)}
                        className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 px-3 py-2 rounded-lg transition"
                    >
                        <UserCircle2 size={42} className="text-green-700" />
                        <div className="text-right">
                            <p className="font-semibold text-sm text-gray-800">
                                {user?.name || "Usuario"}
                            </p>
                            <p className="text-xs text-gray-500">
                                {user?.email || "usuario@email.com"}
                            </p>
                        </div>
                    </div>

                    {/* User Menu Dropdown */}
                    {showUserMenu && (
                        <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                            <div className="p-4 border-b border-gray-100">
                                <p className="font-semibold text-gray-800">{user?.name || "Usuario"}</p>
                                <p className="text-xs text-gray-500">{user?.email || "usuario@email.com"}</p>
                            </div>
                            <div className="py-2">
                                <button className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition">
                                    Mi Perfil
                                </button>
                                <button className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition">
                                    Preferencias
                                </button>
                                <button className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition">
                                    Ayuda
                                </button>
                            </div>
                            <div className="border-t border-gray-100 p-2">
                                <button
                                    onClick={handleLogout}
                                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded transition"
                                >
                                    <LogOut size={16} />
                                    Cerrar Sesión
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}