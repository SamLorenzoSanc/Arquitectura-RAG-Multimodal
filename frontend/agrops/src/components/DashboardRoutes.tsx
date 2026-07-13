import { Route } from "react-router-dom";

import DashboardLayout from "@/components/DashboardLayout";

import OrganizationPage from "@/pages/OrganizationPage";
import ChatPage from "@/pages/ChatPage";
import TenantPage from "@/pages/TenantPage";
import SettingsPage from "@/pages/SettingsPage";

export const DashboardRoutes = (
    <Route path="/dashboard" element={<DashboardLayout />}>
        <Route
            index
            element={<OrganizationPage />}
        />

        <Route
            path="organization"
            element={<OrganizationPage />}
        />

        <Route
            path="chat"
            element={<ChatPage />}
        />

        <Route
            path="tenants"
            element={<TenantPage />}
        />

        <Route
            path="settings"
            element={<SettingsPage />}
        />
    </Route>
);