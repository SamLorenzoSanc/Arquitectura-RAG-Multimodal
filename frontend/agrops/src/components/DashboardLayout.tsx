import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { OrganizationProvider } from "@/context/OrganizationContext";

export default function DashboardLayout() {
    return (
        <OrganizationProvider>
            <div className="h-screen bg-gray-100 flex">
                <Sidebar />

                <div className="flex-1 flex flex-col">
                    <Header />

                    <main className="flex-1 overflow-auto p-8">
                        <Outlet />
                    </main>
                </div>
            </div>
        </OrganizationProvider>
    );
}