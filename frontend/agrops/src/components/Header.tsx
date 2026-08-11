"use client";

import {
  Bell,
  LogOut,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  Menu,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useShell } from "@/context/ShellContext";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/api";

export default function Header() {
  const { user, logout } = useAuth();
  const { toggleSidebar } = useShell();
  const navigate = useNavigate();
  const [currentDate, setCurrentDate] = useState("");
  const [currentTime, setCurrentTime] = useState("");
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [alertCount, setAlertCount] = useState(0);
  const [alertsList, setAlertsList] = useState<
    Array<{ product: string; message: string; containerId: string }>
  >([]);
  const [showAlertsDropdown, setShowAlertsDropdown] = useState(false);

  const initials =
    user?.name
      ?.split(" ")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "US";
  const firstName = user?.name?.split(" ")[0] || "Usuario";

  useEffect(() => {
    const fetchAlertsSummary = async () => {
      try {
        const res = await api.get("/logistics/alerts/summary");
        if (res.data) {
          setAlertCount(res.data.totalAlerts ?? 0);
          setAlertsList(res.data.alerts ?? []);
        }
      } catch {
        /* no bloquear shell */
      }
    };

    void fetchAlertsSummary();
    const interval = setInterval(fetchAlertsSummary, 120000); // 2 min: menos ruido que health/RAG

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const updateDateTime = () => {
      const now = new Date();
      setCurrentDate(
        new Intl.DateTimeFormat("es-ES", {
          timeZone: "Atlantic/Canary",
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
        }).format(now),
      );
      setCurrentTime(
        new Intl.DateTimeFormat("es-ES", {
          timeZone: "Atlantic/Canary",
          hour: "2-digit",
          minute: "2-digit",
        }).format(now),
      );
    };
    updateDateTime();
    const interval = setInterval(updateDateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between gap-3 border-b border-[color:var(--agro-border)] bg-white/90 px-3 backdrop-blur-md sm:h-20 sm:px-5 lg:px-6">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <button
          type="button"
          onClick={toggleSidebar}
          className="rounded-xl border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 lg:hidden"
          aria-label="Abrir menú"
        >
          <Menu size={20} />
        </button>
        <div className="min-w-0">
          <h2 className="truncate text-lg font-bold tracking-tight text-slate-800 sm:text-2xl">
            Hola,{" "}
            <span className="bg-gradient-to-r from-[color:var(--agro-primary)] to-blue-500 bg-clip-text text-transparent">
              {firstName}
            </span>
          </h2>
          <div className="mt-0.5 hidden items-center gap-2 sm:flex">
            <p className="truncate text-sm font-medium capitalize text-[color:var(--agro-primary)]">
              {currentDate}
            </p>
            <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
            <p className="font-mono text-sm font-semibold text-slate-500">
              {currentTime}
            </p>
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowAlertsDropdown((v) => !v)}
            className="relative rounded-full p-2.5 text-slate-500 transition hover:bg-blue-50 hover:text-[color:var(--agro-primary)]"
            title="Alertas de cadena de frío"
          >
            <Bell size={20} />
            {alertCount > 0 && (
              <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-[color:var(--agro-danger)] text-[9px] font-black text-white">
                {alertCount}
              </span>
            )}
          </button>

          {showAlertsDropdown && (
            <div className="absolute right-0 z-50 mt-3 w-[min(20rem,calc(100vw-1.5rem))] overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 p-4">
                <p className="text-sm font-bold text-slate-800">Alertas</p>
                <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-[color:var(--agro-primary)]">
                  {alertCount > 0 ? `${alertCount} críticas` : "Estable"}
                </span>
              </div>
              <div className="max-h-72 space-y-2 overflow-y-auto p-2">
                {alertsList.length === 0 ? (
                  <div className="space-y-1 p-4 text-center">
                    <CheckCircle2
                      size={24}
                      className="mx-auto text-[color:var(--agro-primary)]"
                    />
                    <p className="text-xs font-semibold text-slate-700">
                      Sin alertas térmicas
                    </p>
                  </div>
                ) : (
                  alertsList.map((alert, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50/60 p-3"
                    >
                      <AlertTriangle
                        size={16}
                        className="mt-0.5 shrink-0 text-[color:var(--agro-danger)]"
                      />
                      <div>
                        <p className="text-xs font-bold text-red-900">
                          {alert.product}
                        </p>
                        <p className="mt-0.5 text-[11px] leading-snug text-red-800">
                          {alert.message}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div className="relative">
          <button
            type="button"
            onClick={() => setShowUserMenu((v) => !v)}
            className={`flex items-center gap-2 rounded-full border p-1.5 pr-2 transition sm:pr-3 ${
              showUserMenu
                ? "border-[color:var(--agro-primary)] bg-blue-50/50"
                : "border-slate-200 bg-white hover:border-[color:var(--agro-primary)]"
            }`}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[color:var(--agro-primary)] text-sm font-bold text-white">
              {initials}
            </div>
            <div className="hidden text-left md:block">
              <p className="text-sm font-bold leading-tight text-slate-700">
                {user?.name || "Usuario"}
              </p>
              <p className="mt-0.5 text-xs font-medium leading-tight text-slate-500">
                Sesión activa
              </p>
            </div>
            <ChevronDown
              size={16}
              className={`hidden text-slate-400 transition md:block ${showUserMenu ? "rotate-180" : ""}`}
            />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 z-50 mt-3 w-56 overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-xl">
              <div className="border-b border-slate-100 bg-slate-50/50 p-4 text-left">
                <p className="truncate font-bold text-slate-800">
                  {user?.name || "Usuario"}
                </p>
                <p className="mt-0.5 truncate text-xs text-slate-500">
                  {user?.email}
                </p>
              </div>
              <div className="border-t border-slate-100 p-2">
                <button
                  type="button"
                  onClick={handleLogout}
                  className="group flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium text-[color:var(--agro-danger)] hover:bg-red-50"
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
