"use client";

import { useState } from "react";
import { 
    Sprout, 
    MapPin, 
    CloudSun, 
    AlertTriangle, 
    Droplets, 
    ShieldCheck,
    ChevronRight,
} from "lucide-react";

export default function FarmDashboard() {
    // Estado simulado para el panel del agricultor / gestor de fincas
    const [selectedFinca, setSelectedFinca] = useState("Finca Las Palmas (Norte)");

    return (
        <div className="p-8 space-y-8 bg-slate-50/50 min-h-screen">
            
            {/* Cabecera del Panel */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-2xl border border-blue-100 shadow-sm">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-bold uppercase tracking-wider">
                            Gestión Agrícola & IGP
                        </span>
                        <span className="text-xs text-slate-400 font-medium">Actualizado hace 5 min</span>
                    </div>
                    <h1 className="text-2xl font-black text-blue-950 mt-1">Panel de Control de Fincas</h1>
                    <p className="text-sm text-slate-600">Monitoreo en tiempo real de cultivos, condiciones climáticas y normativas.</p>
                </div>

                {/* Selector de Finca */}
                <div className="flex items-center gap-3 w-full md:w-auto">
                    <span className="text-xs font-bold text-slate-500 uppercase">Finca Activa:</span>
                    <select 
                        value={selectedFinca}
                        onChange={(e) => setSelectedFinca(e.target.value)}
                        className="bg-blue-50 border border-blue-200 text-blue-950 text-xs font-bold rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-amber-400"
                    >
                        <option value="Finca Las Palmas (Norte)">Finca Las Palmas (Norte)</option>
                        <option value="Finca Tegueste (Sur)">Finca Tegueste (Sur)</option>
                        <option value="Finca Valle Gran Rey">Finca Valle Gran Rey</option>
                    </select>
                </div>
            </div>

            {/* Tarjetas de Métricas Principales */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                
                <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
                    <div className="h-12 w-12 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center font-bold">
                        <MapPin size={24} />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Hectáreas Totales</p>
                        <h3 className="text-xl font-black text-blue-950 mt-0.5">48.5 ha</h3>
                        <span className="text-[11px] text-emerald-600 font-bold">100% Bajo Norma IGP</span>
                    </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
                    <div className="h-12 w-12 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center font-bold">
                        <CloudSun size={24} />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Temperatura Media</p>
                        <h3 className="text-xl font-black text-blue-950 mt-0.5">23.4 °C</h3>
                        <span className="text-[11px] text-slate-500 font-medium">Humedad: 65%</span>
                    </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
                    <div className="h-12 w-12 rounded-xl bg-blue-50 text-[#0038A8] flex items-center justify-center font-bold">
                        <Droplets size={24} />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Eficiencia de Riego</p>
                        <h3 className="text-xl font-black text-blue-950 mt-0.5">91.2%</h3>
                        <span className="text-[11px] text-emerald-600 font-bold">Optimizado por IA</span>
                    </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
                    <div className="h-12 w-12 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
                        <ShieldCheck size={24} />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Auditoría RAG</p>
                        <h3 className="text-xl font-black text-blue-950 mt-0.5">Aprobado</h3>
                        <span className="text-[11px] text-emerald-600 font-bold">Sin alertas fitosanitarias</span>
                    </div>
                </div>

            </div>

            {/* Sección de Estado de Cultivos y Alertas */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Tabla o Lista de Parcelas */}
                <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
                    <div className="flex justify-between items-center mb-6">
                        <div>
                            <h2 className="text-lg font-black text-blue-950">Estado de Parcelas - {selectedFinca}</h2>
                            <p className="text-xs text-slate-500">Control de siembra, maduración y previsión de cosecha.</p>
                        </div>
                        <button className="text-xs font-bold text-blue-700 hover:text-blue-900 bg-blue-50 px-3 py-1.5 rounded-xl transition-colors">
                            Ver Todas
                        </button>
                    </div>

                    <div className="space-y-4">
                        {[
                            { parcela: "Parcela A-1 (Plátanos)", estado: "En Cosecha", progreso: 90, color: "bg-emerald-500" },
                            { parcela: "Parcela B-3 (Tomates IGP)", estado: "Crecimiento Vegetativo", progreso: 65, color: "bg-blue-600" },
                            { parcela: "Parcela C-2 (Aguacates)", estado: "Floración", progreso: 40, color: "bg-amber-500" },
                        ].map((item, idx) => (
                            <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                                <div className="flex items-center gap-3">
                                    <div className="h-10 w-10 rounded-lg bg-white shadow-sm flex items-center justify-center text-blue-700 font-bold border border-slate-100">
                                        <Sprout size={20} />
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-bold text-blue-950">{item.parcela}</h4>
                                        <span className="text-xs text-slate-500 font-medium">{item.estado}</span>
                                    </div>
                                </div>
                                <div className="w-full sm:w-48 space-y-1">
                                    <div className="flex justify-between text-xs font-semibold text-slate-600">
                                        <span>Progreso</span>
                                        <span>{item.progreso}%</span>
                                    </div>
                                    <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
                                        <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.progreso}%` }} />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Panel lateral: Alertas y Cuaderno de Campo RAG */}
                <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-4">
                            <AlertTriangle className="text-amber-500" size={20} />
                            <h3 className="text-base font-black text-blue-950">Alertas de Normativa IGP</h3>
                        </div>
                        
                        <div className="space-y-3">
                            <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200/60 text-xs text-amber-900">
                                <p className="font-bold mb-1">Revisión de Cuaderno de Campo</p>
                                <p className="text-[11px] opacity-90">Se requiere actualizar los registros de aplicación de abono orgánico antes del viernes.</p>
                            </div>
                            <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200/60 text-xs text-blue-900">
                                <p className="font-bold mb-1">Consulta RAG Disponible</p>
                                <p className="text-[11px] opacity-90">El asistente inteligente ha indexado las nuevas directrices fitosanitarias de la UE.</p>
                            </div>
                        </div>
                    </div>

                    <div className="mt-6 pt-4 border-t border-slate-100">
                        <button className="w-full py-3 bg-[#0038A8] text-white text-xs font-bold rounded-xl shadow-md shadow-blue-500/20 hover:bg-blue-800 transition-all flex items-center justify-center gap-2 cursor-pointer">
                            <span>Abrir Asistente RAG Agrícola</span>
                            <ChevronRight size={16} />
                        </button>
                    </div>
                </div>

            </div>

        </div>
    );
}