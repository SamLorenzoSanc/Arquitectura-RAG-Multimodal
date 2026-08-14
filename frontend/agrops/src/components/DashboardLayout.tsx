import { useLocation } from "react-router-dom";
import { useEffect } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import DashboardKeepAlive from "./DashboardKeepAlive";
import ChatWidget from "./ChatWidget";
import {
  OrganizationProvider,
  useOrganization,
} from "@/context/OrganizationContext";
import { ShellProvider } from "@/context/ShellContext";
import { usePrefetchDashboard } from "@/hooks/useCachedApi";

function DashboardShell() {
  const { pathname } = useLocation();
  const isChat = pathname.startsWith("/dashboard/chat");
  const isGraph = pathname.startsWith("/dashboard/knowledge-graph");
  const immersive = isChat || isGraph;
  const { selectedOrg } = useOrganization();
  const prefetch = usePrefetchDashboard(selectedOrg?.id);

  useEffect(() => {
    void prefetch();
  }, [prefetch, selectedOrg?.id]);

  return (
    <div className="flex h-screen overflow-hidden bg-[color:var(--agro-canvas)]">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header />
        <main
          className={`min-w-0 flex-1 min-h-0 ${
            immersive
              ? `flex flex-col overflow-hidden ${isGraph ? "p-0" : "px-3 py-3 sm:px-5 sm:py-4"}`
              : "overflow-y-auto px-3 py-3 sm:px-5 sm:py-4 lg:px-6"
          }`}
        >
          <div
            className={`flex w-full ${
              isGraph
                ? "h-full min-h-0 max-w-none flex-1 flex-col overflow-hidden"
                : immersive
                  ? "mx-auto min-h-0 max-w-[1400px] flex-1 flex-col overflow-hidden"
                  : "mx-auto min-h-0 max-w-[1400px] flex-1 flex-col"
            }`}
          >
            <DashboardKeepAlive />
          </div>
        </main>
      </div>
      {!isGraph && <ChatWidget />}
    </div>
  );
}

export default function DashboardLayout() {
  return (
    <OrganizationProvider>
      <ShellProvider>
        <DashboardShell />
      </ShellProvider>
    </OrganizationProvider>
  );
}
