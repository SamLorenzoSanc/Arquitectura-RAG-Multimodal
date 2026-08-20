"use client";

import { useMemo, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  BookOpen,
  Boxes,
  Building2,
  ChevronDown,
  ChevronLeft,
  ClipboardCheck,
  FileText,
  GitFork,
  LayoutDashboard,
  LifeBuoy,
  Plus,
  Settings,
  ShieldAlert,
  X,
} from "lucide-react";

import { BrandMark, CanaryFlag } from "@/components/BrandMark";
import { NewOrgModal } from "@/components/NewOrgModal";
import { useOrganization } from "@/context/OrganizationContext";
import { useShell } from "@/context/ShellContext";
import { useTranslation } from "@/i18n/I18nProvider";

type NavItem = {
  to: string;
  labelKey: string;
  icon: typeof LayoutDashboard;
  end?: boolean;
};

function navClass(active: boolean, collapsed: boolean) {
  return [
    "group flex items-center gap-3 rounded-lg text-sm font-medium transition",
    collapsed ? "justify-center px-2 py-2.5" : "px-3 py-2.5",
    active
      ? "bg-[color:var(--agro-primary)] text-white shadow-sm"
      : "text-slate-600 hover:bg-[color:var(--agro-pill)] hover:text-[color:var(--agro-primary)]",
  ].join(" ");
}

export default function Sidebar() {
  const { t } = useTranslation();
  const { sidebarOpen, sidebarCollapsed, closeSidebar, toggleCollapsed } =
    useShell();
  const {
    organizations,
    selectedOrg,
    setSelectedOrg,
    addOrganization,
  } = useOrganization();
  const navigate = useNavigate();
  const [orgMenuOpen, setOrgMenuOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  const navSections = useMemo(
    (): Array<{ id: string; labelKey: string; items: NavItem[] }> => [
      {
        id: "trabajo",
        labelKey: "nav.work",
        items: [
          { to: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard, end: true },
          { to: "/dashboard/documentos", labelKey: "nav.documents", icon: FileText },
          { to: "/dashboard/embeddings", labelKey: "nav.embeddings", icon: Boxes },
          { to: "/dashboard/flujo-rag", labelKey: "nav.ragFlow", icon: GitFork },
          { to: "/dashboard/organization", labelKey: "nav.organization", icon: Building2 },
        ],
      },
      {
        id: "guardrails",
        labelKey: "nav.guardrails",
        items: [
          { to: "/dashboard/evaluacion", labelKey: "nav.evaluation", icon: ClipboardCheck },
          { to: "/dashboard/validacion", labelKey: "nav.humanValidation", icon: ShieldAlert },
        ],
      },
    ],
    [],
  );

  const secondaryNav = useMemo(
    (): NavItem[] => [
      { to: "/dashboard/docs", labelKey: "common.docs", icon: BookOpen },
      { to: "/dashboard/settings", labelKey: "common.settings", icon: Settings },
      { to: "/dashboard/support", labelKey: "common.support", icon: LifeBuoy },
    ],
    [],
  );

  const collapsed = sidebarCollapsed;

  const panel = (
    <aside
      className={`flex h-full flex-col border-r border-[color:var(--agro-border)] bg-white ${
        collapsed ? "w-[72px]" : "w-72 max-w-[85vw] lg:w-60"
      }`}
    >
      <div className={`flex items-center ${collapsed ? "justify-center px-2 py-4" : "justify-between px-4 py-4"}`}>
        {collapsed ? (
          <CanaryFlag className="h-7 w-10" />
        ) : (
          <BrandMark size="md" />
        )}
        <button
          type="button"
          onClick={closeSidebar}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
          aria-label={t("common.closeMenu")}
        >
          <X size={18} />
        </button>
      </div>

      {!collapsed && (
        <div className="space-y-2 px-3 pb-3">
          <div className="relative">
            <button
              type="button"
              onClick={() => setOrgMenuOpen((v) => !v)}
              className="flex w-full items-center justify-between gap-2 rounded-lg border border-[color:var(--agro-border)] bg-[color:var(--agro-canvas)] px-3 py-2 text-left"
            >
              <span className="truncate text-xs font-semibold text-slate-700">
                {selectedOrg?.name || t("common.selectOrganization")}
              </span>
              <ChevronDown size={14} className="shrink-0 text-slate-400" />
            </button>
            {orgMenuOpen && (
              <div className="absolute inset-x-0 z-30 mt-1 max-h-64 overflow-y-auto rounded-lg border border-[color:var(--agro-border)] bg-white py-1 shadow-lg">
                {organizations.map((org) => (
                  <button
                    key={org.id}
                    type="button"
                    onClick={() => {
                      setSelectedOrg(org);
                      setOrgMenuOpen(false);
                    }}
                    className={`flex w-full px-3 py-2 text-left text-xs ${
                      selectedOrg?.id === org.id
                        ? "bg-[color:var(--agro-pill)] font-semibold text-[color:var(--agro-primary)]"
                        : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {org.name}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => {
                    setOrgMenuOpen(false);
                    setCreateOpen(true);
                  }}
                  className="flex w-full items-center gap-2 border-t border-[color:var(--agro-border)] px-3 py-2 text-left text-xs font-semibold text-[color:var(--agro-primary)] hover:bg-slate-50"
                >
                  <Plus size={12} /> {t("common.newOrganization")}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      <nav className="flex-1 space-y-3 overflow-y-auto px-2 py-2">
        {navSections.map((section) => (
          <div key={section.id} className="space-y-1">
            {collapsed ? (
              <div
                className="mx-auto my-2 h-px w-8 bg-slate-200"
                title={t(section.labelKey)}
              />
            ) : (
              <p className="px-3 pb-1 pt-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {t(section.labelKey)}
              </p>
            )}
            {section.items.map((item) => {
              const Icon = item.icon;
              const label = t(item.labelKey);
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  title={label}
                  onClick={closeSidebar}
                  className={({ isActive }) => navClass(isActive, collapsed)}
                >
                  <Icon size={17} className="shrink-0" />
                  {!collapsed && <span className="truncate">{label}</span>}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="space-y-1 border-t border-[color:var(--agro-border)] px-2 py-3">
        {secondaryNav.map((item) => {
          const Icon = item.icon;
          const label = t(item.labelKey);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              title={label}
              onClick={closeSidebar}
              className={({ isActive }) => navClass(isActive, collapsed)}
            >
              <Icon size={16} className="shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </NavLink>
          );
        })}
        <button
          type="button"
          onClick={toggleCollapsed}
          className="mt-1 hidden w-full items-center justify-center rounded-lg px-2 py-2 text-slate-400 hover:bg-slate-50 hover:text-slate-700 lg:flex"
          aria-label={collapsed ? t("common.expandMenu") : t("common.collapseMenu")}
        >
          <ChevronLeft
            size={16}
            className={collapsed ? "rotate-180" : ""}
          />
        </button>
      </div>
    </aside>
  );

  return (
    <>
      <div className="hidden h-full shrink-0 lg:block">{panel}</div>
      <div
        className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? "pointer-events-auto" : "pointer-events-none"}`}
      >
        <button
          type="button"
          aria-label={t("common.closeMenu")}
          onClick={closeSidebar}
          className={`absolute inset-0 bg-slate-950/40 transition ${
            sidebarOpen ? "opacity-100" : "opacity-0"
          }`}
        />
        <div
          className={`absolute inset-y-0 left-0 transition-transform duration-300 ease-out ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          {panel}
        </div>
      </div>
      <NewOrgModal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        onSave={async (name, description) => {
          await addOrganization(name, description);
          navigate("/dashboard/organization");
        }}
      />
    </>
  );
}
