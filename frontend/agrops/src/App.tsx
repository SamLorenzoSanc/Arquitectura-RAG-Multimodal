import { Routes, Route, Navigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import OrganizationPage from "@/pages/OrganizationPage";
import ChatPage from "@/pages/ChatPage";
import TenantPage from "@/pages/TenantPage";
import SettingsPage from "@/pages/SettingsPage";
import KnowledgeGraphPage from "./pages/KnowledgeGraphPage";
import EvaluationPage from "./pages/EvalutionPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Landing from "@/pages/Landing";
import AboutProductPage from "@/pages/AboutProductPage";
import PrivacyPolicyPage from "@/pages/PrivacyPolicyPage";
import SustainabilityPage from "@/pages/SustainabilityPage";
import ChromaDebugPage from "./pages/ChromaDebuPage";
import LogisticsDashboard from "@/pages/LogisticDashboard";

import FarmDashboard from "@/pages/FarmDashboard";
import FincasPage from "@/pages/FincasPage";
import CultivosPage from "@/pages/CultivosPage";
import DocumentPage from "@/pages/DocumentationPage";
import FlotaPage from "@/pages/FlotaPage";
import ReeferPage from "@/pages/ReeferPage";
import TransitoPage from "@/pages/TransitoPage";

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
      {/* Rutas Públicas */}
      <Route path="/" element={<Landing />} />
      <Route path="/about" element={<AboutProductPage />} />
      <Route path="/sustainability" element={<SustainabilityPage />} />{" "}
      <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
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
        <Route
          index
          element={<Navigate to="/dashboard/organization" replace />}
        />
        <Route path="chat" element={<ChatPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="organization" element={<OrganizationPage />} />
        <Route path="tenants" element={<TenantPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="knowledge-graph" element={<KnowledgeGraphPage />} />
        <Route path="evaluacion" element={<EvaluationPage />} />
        <Route path="chroma-debug" element={<ChromaDebugPage />} />
        <Route path="logistics" element={<LogisticsDashboard />} />
        <Route path="documentation" element={<DocumentPage />} />
        <Route path="farm-dashboard" element={<FarmDashboard />} />
        <Route path="fincas" element={<FincasPage />} />
        <Route path="cultivos" element={<CultivosPage />} />

        <Route path="flota" element={<FlotaPage />} />
        <Route path="reefer" element={<ReeferPage />} />
        <Route path="transito" element={<TransitoPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
