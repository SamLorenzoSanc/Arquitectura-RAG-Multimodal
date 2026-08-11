"use client";

import { useMemo, useState } from "react";
import {
  Sprout,
  MapPin,
  CloudSun,
  AlertTriangle,
  Droplets,
  ShieldCheck,
  ChevronRight,
} from "lucide-react";
import { useCrops } from "@/hooks/useCachedApi";

export default function FarmDashboard() {
  const { data: crops, isLoading } = useCrops(true);
  const parcels = crops ?? [];
  const [selectedId, setSelectedId] = useState<string>("");

  const active = useMemo(() => {
    if (!parcels.length) return null;
    const id = selectedId || parcels[0]?.id;
    return parcels.find((p) => p.id === id) || parcels[0];
  }, [parcels, selectedId]);

  const totalHa = useMemo(
    () =>
      parcels.reduce((acc, p) => acc + (Number(p.superficie_ha) || 0), 0),
    [parcels],
  );

  const recentTreatments = active?.treatments?.slice(0, 4) ?? [];

  if (isLoading && parcels.length === 0) {
    return (
      <div className="p-8 text-sm text-slate-500">Cargando parcelas...</div>
    );
  }

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-screen">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-2xl border border-blue-100 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-bold uppercase tracking-wider">
              Perfil operativo
            </span>
            <span className="text-xs text-slate-400 font-medium">
              Datos estructurados para el LLM
            </span>
          </div>
          <h1 className="text-2xl font-black text-blue-950 mt-1">
            Panel de Control de Fincas
          </h1>
          <p className="text-sm text-slate-600">
            Parcelas, riego, agua y fitosanitarios registrados por el agricultor.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <span className="text-xs font-bold text-slate-500 uppercase">
            Finca activa:
          </span>
          <select
            value={active?.id || ""}
            onChange={(e) => setSelectedId(e.target.value)}
            className="bg-blue-50 border border-blue-200 text-blue-950 text-xs font-bold rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-amber-400"
          >
            {parcels.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center font-bold">
            <MapPin size={24} />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Hectáreas totales
            </p>
            <h3 className="text-xl font-black text-blue-950 mt-0.5">
              {totalHa.toFixed(1)} ha
            </h3>
            <span className="text-[11px] text-emerald-600 font-bold">
              {parcels.length} parcela(s)
            </span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center font-bold">
            <CloudSun size={24} />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Temperatura
            </p>
            <h3 className="text-xl font-black text-blue-950 mt-0.5">
              {active?.temperatura ?? "—"} °C
            </h3>
            <span className="text-[11px] text-slate-500 font-medium">
              Humedad: {active?.humedad ?? "—"}%
            </span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-blue-50 text-[#0038A8] flex items-center justify-center font-bold">
            <Droplets size={24} />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Dotación hídrica
            </p>
            <h3 className="text-xl font-black text-blue-950 mt-0.5">
              {active?.dotacion_m3_ha_anio ?? "—"}
            </h3>
            <span className="text-[11px] text-emerald-600 font-bold">
              {active?.sistema_riego || "Sin riego registrado"}
            </span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
            <ShieldCheck size={24} />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Certificaciones
            </p>
            <h3 className="text-sm font-black text-blue-950 mt-0.5 line-clamp-2">
              {active?.certificaciones || "Sin certificar"}
            </h3>
            <span className="text-[11px] text-emerald-600 font-bold">
              {recentTreatments.length} tratamiento(s) recientes
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Sprout className="text-emerald-700" size={18} />
            <h2 className="font-bold text-slate-900">Parcela activa</h2>
          </div>
          {active ? (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-400 text-xs uppercase font-semibold">
                  Ref. catastral
                </dt>
                <dd className="font-semibold text-slate-800">
                  {active.ref_catastral || "n/d"}
                </dd>
              </div>
              <div>
                <dt className="text-slate-400 text-xs uppercase font-semibold">
                  Cultivo / variedad
                </dt>
                <dd className="font-semibold text-slate-800">
                  {active.cultivo}
                  {active.variedad ? ` · ${active.variedad}` : ""}
                </dd>
              </div>
              <div>
                <dt className="text-slate-400 text-xs uppercase font-semibold">
                  Isla
                </dt>
                <dd className="font-semibold text-slate-800">{active.isla}</dd>
              </div>
              <div>
                <dt className="text-slate-400 text-xs uppercase font-semibold">
                  Fuente de agua
                </dt>
                <dd className="font-semibold text-slate-800">
                  {active.fuente_agua || "n/d"}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-slate-400 text-xs uppercase font-semibold">
                  Notas
                </dt>
                <dd className="text-slate-700">{active.notas || "—"}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-slate-500">
              No hay parcelas. Regístralas en Fincas y mapas.
            </p>
          )}
        </div>

        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="text-amber-600" size={18} />
            <h2 className="font-bold text-slate-900">Fitosanitarios</h2>
          </div>
          {recentTreatments.length === 0 ? (
            <p className="text-sm text-slate-500">Sin tratamientos recientes.</p>
          ) : (
            <ul className="space-y-2">
              {recentTreatments.map((t) => (
                <li
                  key={t.id || `${t.fecha}-${t.producto}`}
                  className="flex items-start justify-between gap-2 rounded-xl border border-slate-100 p-3 text-sm"
                >
                  <div>
                    <p className="font-semibold text-slate-800">{t.producto}</p>
                    <p className="text-xs text-slate-500">
                      {t.fecha} · {t.plaga_objetivo || "sin plaga"} · carencia{" "}
                      {t.carencia_dias ?? "n/d"}d
                    </p>
                  </div>
                  <ChevronRight size={16} className="text-slate-300 mt-1" />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
