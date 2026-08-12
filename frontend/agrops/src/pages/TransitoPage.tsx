"use client";

import { useState } from "react";
import { 
    FileText, 
    Ship, 
    Clock, 
    CheckCircle2,
    Search, 
    MapPin, 
    ChevronRight,
    ArrowRight
} from "lucide-react";

export default function TransitoPage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedEstado, setSelectedEstado] = useState("Todos");

    // Lista simulada de tiempos de tránsito y documentación aduanera marítima
    const transitoData = [
        {
            id: "TR-2026-881",
            origen: "Puerto de La Luz (Gran Canaria)",
            destino: "Puerto de Huelva (Península)",
            buque: "Volcán de Tijarafe",
            mercancia: "Tomate de Exportación (IGP)",
            tiempoEstimado: "32 horas",
            estado: "En Curso",
            duaAduanas: "Completado y Sellado",
            fechaSalida: "27 Jul 2026 - 18:00"
        },
        {
            id: "TR-2026-882",
            origen: "Puerto de Santa Cruz de Tenerife",
            destino: "Puerto de Cádiz",
            buque: "Volcán de Teno",
            mercancia: "Plátano de Canarias (1ª Categoría)",
            tiempoEstimado: "40 horas",
            estado: "En Curso",
            duaAduanas: "Completado y Sellado",
            fechaSalida: "26 Jul 2026 - 22:30"
        },
        {
            id: "TR-2026-879",
            origen: "Puerto de Los Cristianos (Tenerife)",
            destino: "Puerto de San Sebastián (La Gomera)",
            buque: "Bencomo Express",
            mercancia: "Insumos Agrícolas y Riego",
            tiempoEstimado: "3 horas",
            estado: "Entregado",
            duaAduanas: "Verificado Interinsular",
            fechaSalida: "25 Jul 2026 - 09:00"
        },
        {
            id: "TR-2026-875",
            origen: "Puerto del Rosario (Fuerteventura)",
            destino: "Puerto de Las Palmas",
            buque: "Villa de Agaete",
            mercancia: "Aloe Vera Ecológico",
            tiempoEstimado: "5 horas",
            estado: "En Revisión Aduanera",
            duaAduanas: "Pendiente Inspección Fitosanitaria",
            fechaSalida: "28 Jul 2026 - 08:00"
        }
    ];

    // Filtrar los datos de tránsito
    const filteredTransitos = transitoData.filter((item) => {
        const matchesSearch = item.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              item.mercancia.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              item.buque.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesEstado = selectedEstado === "Todos" || item.estado === selectedEstado;
        return matchesSearch && matchesEstado;
    });

    return (
        <div className="p-8 space-y-8 bg-slate-50/50 min-h-screen">
            
            {/* Cabecera del Panel */}
            <div className="bg-white p-6 rounded-2xl border border-blue-100 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="px-3 py-1 rounded-full bg-blue-100 text-[#0038A8] text-xs font-bold uppercase tracking-wider">
                            Control Logístico & DUA
                        </span>
                        <span className="text-xs text-slate-400 font-medium">Actualizado en tiempo real</span>
                    </div>
                    <h1 className="text-2xl font-black text-blue-950 mt-1">Tiempos de Tránsito y Aduanas</h1>
                    <p className="text-sm text-slate-600">Seguimiento de tiempos de navegación marítima interinsular y con la península.</p>
                </div>

                <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-500 uppercase">Registros Activos:</span>
                    <span className="bg-[#0038A8] text-white px-3 py-1.5 rounded-xl text-xs font-black shadow-md shadow-blue-500/20">
                        {transitoData.length} Envíos
                    </span>
                </div>
            </div>

            {/* Búsqueda y Filtros */}
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="relative w-full sm:w-96">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input 
                        type="text"
                        placeholder="Buscar por ID, mercancía o buque..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-white border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0038A8] shadow-sm"
                    />
                </div>

                <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
                    {["Todos", "En Curso", "Entregado", "En Revisión Aduanera"].map((estado) => (
                        <button
                            key={estado}
                            onClick={() => setSelectedEstado(estado)}
                            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
                                selectedEstado === estado
                                    ? "bg-[#0038A8] text-white shadow-md shadow-blue-500/20"
                                    : "bg-white text-slate-600 border border-slate-200 hover:bg-blue-50 hover:text-[#0038A8]"
                            }`}
                        >
                            {estado}
                        </button>
                    ))}
                </div>
            </div>

            {/* Listado en Tarjetas de Tránsito */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {filteredTransitos.length === 0 ? (
                    <div className="col-span-full py-12 text-center bg-white rounded-2xl border border-slate-100 shadow-sm">
                        <p className="text-sm font-bold text-slate-400">No se encontraron registros con los filtros aplicados.</p>
                    </div>
                ) : (
                    filteredTransitos.map((item, idx) => (
                        <div 
                            key={idx} 
                            className="bg-white rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-all duration-300 p-6 flex flex-col justify-between space-y-4"
                        >
                            <div className="flex justify-between items-start">
                                <div className="flex items-center gap-3">
                                    <div className="h-12 w-12 rounded-xl bg-blue-50 text-[#0038A8] flex items-center justify-center font-bold border border-blue-100 shadow-sm">
                                        <FileText size={22} />
                                    </div>
                                    <div>
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{item.id}</span>
                                        <h3 className="text-base font-black text-blue-950">{item.mercancia}</h3>
                                    </div>
                                </div>
                                <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1 ${
                                    item.estado === "Entregado" 
                                        ? "bg-emerald-50 text-emerald-700 border border-emerald-100" 
                                        : item.estado === "En Curso"
                                        ? "bg-blue-50 text-[#0038A8] border border-blue-100"
                                        : "bg-amber-50 text-amber-700 border border-amber-100"
                                }`}>
                                    {item.estado === "Entregado" ? <CheckCircle2 size={14} /> : <Clock size={14} />}
                                    {item.estado}
                                </span>
                            </div>

                            {/* Origen y Destino */}
                            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-2">
                                <div className="flex items-start gap-2 text-xs text-slate-700">
                                    <MapPin size={14} className="text-[#0038A8] mt-0.5 shrink-0" />
                                    <div className="flex flex-col sm:flex-row sm:items-center gap-1">
                                        <span className="font-bold text-blue-950">Origen:</span>
                                        <span>{item.origen}</span>
                                    </div>
                                </div>
                                <div className="flex items-start gap-2 text-xs text-slate-700">
                                    <ArrowRight size={14} className="text-amber-600 mt-0.5 shrink-0" />
                                    <div className="flex flex-col sm:flex-row sm:items-center gap-1">
                                        <span className="font-bold text-blue-950">Destino:</span>
                                        <span>{item.destino}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Detalles de Buque, DUA y Tiempos */}
                            <div className="grid grid-cols-2 gap-3 text-xs text-slate-600 pt-2 border-t border-slate-100">
                                <div className="space-y-0.5">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1">
                                        <Ship size={12} className="text-[#0038A8]" /> Buque
                                    </span>
                                    <p className="font-bold text-blue-950">{item.buque}</p>
                                </div>
                                <div className="space-y-0.5">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1">
                                        <Clock size={12} className="text-amber-600" /> Tiempo estimado
                                    </span>
                                    <p className="font-bold text-blue-950">{item.tiempoEstimado}</p>
                                </div>
                            </div>

                            <div className="flex justify-between items-center pt-2 border-t border-slate-100 text-xs">
                                <span className="text-[11px] text-slate-500 font-medium">DUA: <strong className="text-slate-700">{item.duaAduanas}</strong></span>
                                <button className="text-xs font-bold text-[#0038A8] hover:text-blue-900 flex items-center gap-1 transition-colors cursor-pointer">
                                    <span>Ver Certificado</span>
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