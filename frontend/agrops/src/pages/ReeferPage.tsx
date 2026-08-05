"use client";

import { useState } from "react";
import { 
    Package, 
    Thermometer, 
    Ship, 
    AlertTriangle, 
    CheckCircle2, 
    Search, 
    Filter,
    Activity,
    Clock,
    ChevronRight
} from "lucide-react";

export default function ReeferPage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedStatus, setSelectedStatus] = useState("Todos");

    // Lista simulada de contenedores frigoríficos (Reefer) para la logística marítima canaria
    const reeferContainers = [
        {
            id: "REF-8492-CN",
            cultivo: "Plátano de Canarias (Exportación)",
            temperaturaActual: "13.2 °C",
            temperaturaObjetivo: "13.0 °C",
            humedad: "88%",
            estado: "Óptimo",
            buque: "Volcán de Teno",
            ruta: "Santa Cruz de Tenerife -> Cádiz",
            tiempoTransito: "42 horas restantes"
        },
        {
            id: "REF-3105-CN",
            cultivo: "Tomate de Canarias (Select)",
            temperaturaActual: "10.5 °C",
            temperaturaObjetivo: "10.0 °C",
            humedad: "90%",
            estado: "Óptimo",
            buque: "Al시오 de Las Palmas",
            ruta: "Las Palmas de Gran Canaria -> Huelva",
            tiempoTransito: "36 horas restantes"
        },
        {
            id: "REF-9921-CN",
            cultivo: "Aguacate Hass de Canarias",
            temperaturaActual: "6.8 °C",
            temperaturaObjetivo: "6.0 °C",
            humedad: "85%",
            estado: "Revisión Térmica",
            buque: "Ciudad de Valencia",
            ruta: "Santa Cruz de Tenerife -> Barcelona",
            tiempoTransito: "18 horas restantes"
        },
        {
            id: "REF-5540-CN",
            cultivo: "Papas Antiguas de Canarias",
            temperaturaActual: "12.0 °C",
            temperaturaObjetivo: "12.0 °C",
            humedad: "80%",
            estado: "Óptimo",
            buque: "Volcán de Tamasite",
            ruta: "Puerto del Rosario -> Sevilla",
            tiempoTransito: "50 horas restantes"
        }
    ];

    // Filtrar contenedores según búsqueda y estado
    const filteredContainers = reeferContainers.filter((container) => {
        const matchesSearch = container.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              container.cultivo.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              container.buque.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = selectedStatus === "Todos" || container.estado === selectedStatus;
        return matchesSearch && matchesStatus;
    });

    return (
        <div className="p-8 space-y-8 bg-slate-50/50 min-h-screen">
            
            {/* Cabecera del Panel Reefer */}
            <div className="bg-white p-6 rounded-2xl border border-blue-100 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="px-3 py-1 rounded-full bg-blue-100 text-[#0038A8] text-xs font-bold uppercase tracking-wider">
                            Logística Marítima & Cadena de Frío
                        </span>
                        <span className="text-xs text-slate-400 font-medium">Monitoreo en Vivo</span>
                    </div>
                    <h1 className="text-2xl font-black text-blue-950 mt-1">Contenedores Reefer</h1>
                    <p className="text-sm text-slate-600">Control de temperatura, humedad y trazabilidad de productos perecederos entre islas y península.</p>
                </div>

                <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-500 uppercase">Activos en Tránsito:</span>
                    <span className="bg-[#0038A8] text-white px-3 py-1.5 rounded-xl text-xs font-black shadow-md shadow-blue-500/20">
                        {reeferContainers.length} Contenedores
                    </span>
                </div>
            </div>

            {/* Filtros y Búsqueda */}
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="relative w-full sm:w-96">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input 
                        type="text"
                        placeholder="Buscar por ID, cultivo o buque..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-white border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0038A8] shadow-sm"
                    />
                </div>

                <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
                    {["Todos", "Óptimo", "Revisión Térmica"].map((status) => (
                        <button
                            key={status}
                            onClick={() => setSelectedStatus(status)}
                            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
                                selectedStatus === status
                                    ? "bg-[#0038A8] text-white shadow-md shadow-blue-500/20"
                                    : "bg-white text-slate-600 border border-slate-200 hover:bg-blue-50 hover:text-[#0038A8]"
                            }`}
                        >
                            {status}
                        </button>
                    ))}
                </div>
            </div>

            {/* Grid de Contenedores Reefer */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {filteredContainers.length === 0 ? (
                    <div className="col-span-full py-12 text-center bg-white rounded-2xl border border-slate-100 shadow-sm">
                        <p className="text-sm font-bold text-slate-400">No se encontraron contenedores con los filtros seleccionados.</p>
                    </div>
                ) : (
                    filteredContainers.map((container, idx) => (
                        <div 
                            key={idx} 
                            className="bg-white rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-all duration-300 p-6 flex flex-col justify-between space-y-4"
                        >
                            <div className="flex justify-between items-start">
                                <div className="flex items-center gap-3">
                                    <div className="h-12 w-12 rounded-xl bg-blue-50 text-[#0038A8] flex items-center justify-center font-bold border border-blue-100 shadow-sm">
                                        <Package size={22} />
                                    </div>
                                    <div>
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{container.id}</span>
                                        <h3 className="text-base font-black text-blue-950">{container.cultivo}</h3>
                                    </div>
                                </div>
                                <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1 ${
                                    container.estado === "Óptimo" 
                                        ? "bg-emerald-50 text-emerald-700 border border-emerald-100" 
                                        : "bg-amber-50 text-amber-700 border border-amber-100"
                                }`}>
                                    {container.estado === "Óptimo" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                                    {container.estado}
                                </span>
                            </div>

                            {/* Métricas de Temperatura y Humedad */}
                            <div className="grid grid-cols-3 gap-3 p-3.5 rounded-xl bg-slate-50 border border-slate-100">
                                <div className="space-y-0.5">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1">
                                        <Thermometer size={12} className="text-blue-600" /> Actual
                                    </span>
                                    <p className="text-sm font-black text-blue-950">{container.temperaturaActual}</p>
                                </div>
                                <div className="space-y-0.5">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase">Objetivo</span>
                                    <p className="text-sm font-black text-slate-700">{container.temperaturaObjetivo}</p>
                                </div>
                                <div className="space-y-0.5">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase">Humedad</span>
                                    <p className="text-sm font-black text-slate-700">{container.humedad}</p>
                                </div>
                            </div>

                            {/* Información de Ruta y Buque */}
                            <div className="space-y-2 text-xs text-slate-600 pt-2 border-t border-slate-100">
                                <div className="flex items-center gap-2">
                                    <Ship size={14} className="text-[#0038A8]" />
                                    <span className="font-bold text-blue-950">Buque:</span> {container.buque}
                                </div>
                                <div className="flex items-center gap-2">
                                    <Activity size={14} className="text-slate-400" />
                                    <span className="font-bold text-blue-950">Ruta:</span> {container.ruta}
                                </div>
                                <div className="flex items-center gap-2">
                                    <Clock size={14} className="text-amber-600" />
                                    <span className="font-bold text-blue-950">Tránsito:</span> {container.tiempoTransito}
                                </div>
                            </div>

                            <div className="pt-2 flex justify-end">
                                <button className="text-xs font-bold text-[#0038A8] hover:text-blue-900 flex items-center gap-1 transition-colors cursor-pointer">
                                    <span>Ver Gráfica Térmica</span>
                                    <ChevronRight size={14} />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>

        </div>
    );
}