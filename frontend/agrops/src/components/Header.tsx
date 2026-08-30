"use client";

import { Bell, ChevronRight, LogOut, Menu } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { UserAvatar } from "@/components/UserAvatar";
import { useAuth } from "@/context";
import { useShell } from "@/context";
import { useTranslation } from "@/i18n/I18nProvider";
import { routeLabel, settingsTabLabel } from "@/lib/app";

export default function Header() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { toggleSidebar } = useShell();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const crumbs = useMemo(() => {
    const items: Array<{ label: string; to?: string }> = [
      { label: t("nav.dashboard"), to: "/dashboard" },
    ];
    if (pathname === "/dashboard") {
      return items;
    }
    const current = routeLabel(pathname, t);
    if (pathname === "/dashboard/settings") {
      items.push({ label: t("common.settings"), to: "/dashboard/settings" });
      const tab = settingsTabLabel(searchParams.get("tab") || "profile", t);
      if (tab) items.push({ label: tab });
    } else if (
      pathname === "/dashboard/evaluacion" ||
      pathname === "/dashboard/validacion"
    ) {
      items.push({ label: t("nav.guardrails"), to: "/dashboard/evaluacion" });
      items.push({ label: current });
    } else {
      items.push({ label: current });
    }
    return items;
  }, [pathname, searchParams, t]);

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-40 flex h-12 items-center justify-between gap-3 border-b border-[color:var(--agro-border)] bg-white px-3 sm:px-5 lg:px-6">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <button
          type="button"
          onClick={toggleSidebar}
          className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 lg:hidden"
          aria-label={t("common.openMenu")}
        >
          <Menu size={16} />
        </button>
        <nav aria-label={t("common.breadcrumb")} className="flex min-w-0 items-center gap-1 text-xs">
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
        <button
          type="button"
          className="rounded-full p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-700"
          aria-label={t("common.notifications")}
        >
          <Bell size={16} />
        </button>
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowUserMenu((v) => !v)}
            className={`flex h-8 w-8 items-center justify-center overflow-hidden rounded-full ${
              showUserMenu ? "ring-2 ring-[color:var(--agro-accent)]" : "hover:opacity-90"
            }`}
            aria-label={t("common.account")}
          >
            <UserAvatar src={user?.avatarUrl} name={user?.name} size={32} />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-xl border border-[color:var(--agro-border)] bg-white shadow-xl">
              <div className="border-b border-slate-100 bg-slate-50/50 p-3 text-left">
                <p className="truncate text-sm font-bold text-slate-800">
                  {user?.name || t("common.user")}
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
                  className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                >
                  {t("common.settings")}
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="group flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-medium text-[color:var(--agro-danger)] hover:bg-red-50"
                >
                  <span>{t("common.logout")}</span>
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
