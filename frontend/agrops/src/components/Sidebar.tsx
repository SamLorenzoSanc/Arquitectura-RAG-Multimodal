import { LayoutDashboard, FileText, MessagesSquare, Database, BarChart3, Settings, LogOut} from "lucide-react";
import SidebarItem from "./SidebarItem";
import { useAuth } from "@/context/AuthContext";

export default function Sidebar() {

    const { logout } = useAuth();

    return (

        <aside className="w-72 bg-white border-r border-slate-200 flex flex-col">

            <div className="p-6 border-b">

                <h1 className="text-3xl font-bold text-green-700">

                    AgrOPS

                </h1>

                <p className="text-sm text-slate-500">

                    Agricultural Assistant

                </p>

            </div>

            <nav className="flex-1 p-4 space-y-2">

                <SidebarItem
                    icon={LayoutDashboard}
                    label="Dashboard"
                    to="/dashboard"
                />

                <SidebarItem
                    icon={MessagesSquare}
                    label="Conversaciones"
                    to="/dashboard/chat"
                />

                <SidebarItem
                    icon={FileText}
                    label="Documentos"
                    to="/dashboard/documents"
                />

                <SidebarItem
                    icon={Database}
                    label="Bases de conocimiento"
                    to="/dashboard/kb"
                />

                <SidebarItem
                    icon={BarChart3}
                    label="Métricas"
                    to="/dashboard/metrics"
                />

                <SidebarItem
                    icon={Settings}
                    label="Configuración"
                    to="/dashboard/settings"
                />

            </nav>

            <div className="p-4 border-t">

                <button

                    onClick={logout}

                    className="flex items-center gap-2 text-red-500"

                >

                    <LogOut size={18}/>

                    Cerrar sesión

                </button>

            </div>

        </aside>

    );

}