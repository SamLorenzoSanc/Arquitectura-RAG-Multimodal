import { Outlet } from "react-router-dom";
import type { ReactNode } from "react"; // Usamos 'import type' por la regla estricta de tu tsconfig
import Sidebar from "./Sidebar";
import Header from "./Header";
import { OrganizationProvider } from "@/context/OrganizationContext";

// Definimos la interfaz para aceptar componentes hijos de forma opcional
interface DashboardLayoutProps {
    children?: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
    return (
        <OrganizationProvider>
            <div className="h-screen bg-gray-100 flex">
                <Sidebar />

                <div className="flex-1 flex flex-col">
                    <Header />

                    <main className="flex-1 overflow-auto p-8">
                        {/* Si se le pasan hijos, los renderiza. Si no, usa el Outlet de las rutas */}
                        {children || <Outlet />}
                    </main>
                </div>
            </div>
        </OrganizationProvider>
    );
}