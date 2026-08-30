import Sidebar from "./Sidebar";
import Header from "./Header";
import DashboardKeepAlive from "./DashboardKeepAlive";
import ChatWidget from "./ChatWidget";
import { OrganizationProvider } from "@/context";
import { ShellProvider } from "@/context";

function DashboardShell() {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[color:var(--agro-canvas)]">
      <div className="agro-flag-bar" aria-hidden>
        <span />
        <span />
        <span />
      </div>
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <Header />
          <main className="min-h-0 min-w-0 flex-1 overflow-y-auto px-3 py-3 sm:px-5 sm:py-4 lg:px-6">
            <div className="mx-auto flex min-h-0 w-full max-w-[1400px] flex-1 flex-col">
              <DashboardKeepAlive />
            </div>
          </main>
        </div>
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
