"use client";

import { LogOut, Menu, ChevronRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useShell } from "@/context/ShellContext";
import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { UserAvatar } from "@/components/UserAvatar";
import { ROUTE_LABELS, settingsTabLabel } from "@/lib/nav";

export default function Header() {
  const { user, logout } = useAuth();
  const { toggleSidebar } = useShell();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const crumbs = (() => {
    const items: Array<{ label: string; to?: string }> = [
      { label: "Panel", to: "/dashboard/datasets" },
    ];
    const current = ROUTE_LABELS[pathname] || "Sección";
    if (pathname === "/dashboard/settings") {
      items.push({ label: "Ajustes", to: "/dashboard/settings" });
      const tab = settingsTabLabel(searchParams.get("tab") || "profile");
      if (tab) items.push({ label: tab });
    } else if (pathname !== "/dashboard" && pathname !== "/dashboard/datasets") {
      items.push({ label: current });
    } else {
      items.push({ label: current });
    }
    return items;
  })();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-40 flex h-11 items-center justify-between gap-3 border-b border-[color:var(--agro-border)] bg-white/95 px-3 backdrop-blur-md sm:h-12 sm:px-5 lg:px-6">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <button
          type="button"
          onClick={toggleSidebar}
          className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 lg:hidden"
          aria-label="Abrir menú"
        >
          <Menu size={16} />
        </button>
        <nav aria-label="Ruta de navegación" className="flex min-w-0 items-center gap-1 text-xs">
          {crumbs.map((crumb, index) => {
            const last = index === crumbs.length - 1;
            return (
              <span key={`${crumb.label}-${index}`} className="flex min-w-0 items-center gap-1">
                {index > 0 && (
                  <ChevronRight size={12} className="shrink-0 text-slate-300" />
                )}
                {crumb.to && !last ? (
                  <Link
                    to={crumb.to}
                    className="truncate font-medium text-slate-500 hover:text-slate-800"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span
                    className={`truncate ${
                      last ? "font-semibold text-slate-800" : "font-medium text-slate-500"
                    }`}
                  >
                    {crumb.label}
                  </span>
                )}
              </span>
            );
          })}
        </nav>
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowUserMenu((v) => !v)}
            className={`flex h-8 w-8 items-center justify-center overflow-hidden rounded-full ${
              showUserMenu ? "ring-2 ring-blue-200" : "hover:opacity-90"
            }`}
            aria-label="Cuenta"
          >
            <UserAvatar src={user?.avatarUrl} name={user?.name} size={32} />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-xl">
              <div className="border-b border-slate-100 bg-slate-50/50 p-3 text-left">
                <p className="truncate text-sm font-bold text-slate-800">
                  {user?.name || "Usuario"}
                </p>
                {user?.jobTitle && (
                  <p className="truncate text-[11px] text-slate-500">{user.jobTitle}</p>
                )}
                <p className="mt-0.5 truncate text-xs text-slate-500">
                  {user?.email}
                </p>
              </div>
              <div className="p-1.5">
                <Link
                  to="/dashboard/settings?tab=profile"
                  onClick={() => setShowUserMenu(false)}
                  className="block rounded-xl px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                >
                  Ajustes
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="group flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm font-medium text-[color:var(--agro-danger)] hover:bg-red-50"
                >
                  <span>Cerrar sesión</span>
                  <LogOut size={16} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
