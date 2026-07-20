import { Routes, Route, Navigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import OrganizationPage from "@/pages/OrganizationPage";
import ChatPage from "@/pages/ChatPage";
import TenantPage from "@/pages/TenantPage";
import SettingsPage from "@/pages/SettingsPage";
import KnowledgeGraphPage from "./pages/KnowledgeGraphPage";
import EvaluationPage from "./pages/EvalutionPage";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Landing from "@/pages/Landing"; 
import ChromaDebugPage from "./pages/ChromaDebuPage";
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
            <Route path="/" element={<Landing />} />

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
                <Route path="knowledge-graph" element={<KnowledgeGraphPage />}/>
                <Route path="evaluacion" element={<EvaluationPage />} />
                <Route path="chroma-debug" element={<ChromaDebugPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}