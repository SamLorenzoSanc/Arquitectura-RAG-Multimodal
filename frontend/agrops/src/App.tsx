import { Routes, Route, Navigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import OrganizationPage from "@/pages/OrganizationPage";
import ChatPage from "@/pages/ChatPage";
import TenantPage from "@/pages/TenantPage";
import SettingsPage from "@/pages/SettingsPage";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import { useAuth } from "@/context/AuthContext";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { isAuthenticated } = useAuth();

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return <>{children}</>;
}

export default function App() {
    return (
        <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route
                path="/dashboard"
                element={
                    <ProtectedRoute>
                        <DashboardLayout />
                    </ProtectedRoute>
                }
            >
                <Route index element={<Navigate to="/dashboard/organization" replace />} />
                <Route path="chat" element={<ChatPage />} />
                <Route path="organization" element={<OrganizationPage />} />
                <Route path="tenants" element={<TenantPage />} />
                <Route path="settings" element={<SettingsPage />} />
            </Route>

            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
    );
}