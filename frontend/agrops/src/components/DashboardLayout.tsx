import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { OrganizationProvider } from "@/context/OrganizationContext";

// Definimos la interfaz para aceptar componentes hijos de forma opcional
export interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout() {
    return (
        <OrganizationProvider>
            <div className="h-screen bg-gray-100 flex">
                <Sidebar />
                <div className="flex-1 flex flex-col">
                    <Header />
                    <main className="flex-1 min-w-0 overflow-y-auto">
                        <Outlet />
                    </main>
                </div>
            </div>
        </OrganizationProvider>
    );
}