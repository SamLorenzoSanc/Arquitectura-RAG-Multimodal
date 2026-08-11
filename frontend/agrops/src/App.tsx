import { Routes, Route, Navigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Landing from "@/pages/Landing";
import AboutProductPage from "@/pages/AboutProductPage";
import PrivacyPolicyPage from "@/pages/PrivacyPolicyPage";
import SustainabilityPage from "@/pages/SustainabilityPage";
import { useAuth } from "@/context/AuthContext";

/** Solo distingue usuario autenticado vs no autenticado. */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/about" element={<AboutProductPage />} />
      <Route path="/sustainability" element={<SustainabilityPage />} />
      <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* KeepAlive dentro de DashboardLayout cachea todas las páginas del panel */}
      <Route
        path="/dashboard/*"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
