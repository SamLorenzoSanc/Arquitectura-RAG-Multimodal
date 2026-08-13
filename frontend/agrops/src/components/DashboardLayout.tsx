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
          className={`min-w-0 flex-1 min-h-0 px-3 py-3 sm:px-5 sm:py-4 lg:px-6 ${
            isChat ? "flex flex-col overflow-hidden" : "overflow-y-auto"
          }`}
        >
          <div
            className={`mx-auto flex w-full max-w-[1400px] ${
              isChat
                ? "min-h-0 flex-1 flex-col overflow-hidden"
                : "min-h-0 flex-1 flex-col"
            }`}
          >
            <DashboardKeepAlive />
          </div>
        </main>
      </div>
      <ChatWidget />
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
