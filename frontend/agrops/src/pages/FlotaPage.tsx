"use content";

import { useState } from "react";
import { 
    Truck, 
    Ship, 
    Navigation, 
    MapPin, 
    CheckCircle2, 
    Search, 
    ChevronRight,
    Compass
} from "lucide-react";

export default function FlotaPage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedEstado, setSelectedEstado] = useState("Todos");

    // Lista simulada de la flota multiruta (marítima y terrestre) en Canarias
    const flotaVehiculos = [
        {
            id: "FLT-01-TF",
            nombre: "Buque Multiruta 'Volcán de Teno'",
            tipo: "Transporte Marítimo IGP",
            origen: "Santa Cruz de Tenerife",
            destino: "Cádiz (Península)",
            estado: "En Ruta",
            velocidad: "21.5 nudos",
            combustible: "78%",
            operador: "Logística Insular S.A."
        },
        {
            id: "FLT-02-GC",
            nombre: "Camión Frigorífico Reefer #12",
            tipo: "Transporte Terrestre",
            origen: "Finca Las Palmas (Norte)",
            destino: "Puerto de La Luz",
            estado: "En Ruta",
            velocidad: "65 km/h",
            combustible: "90%",
            operador: "AgroTránsito Canarias"
        },
        {
            id: "FLT-03-LP",
            nombre: "Furgón de Reparto Local #04",
            tipo: "Distribución Interinsular",
            origen: "Los Llanos de Aridane",
            destino: "Santa Cruz de La Palma",
            estado: "En Mantenimiento",
            velocidad: "0 km/h",
            combustible: "45%",
            operador: "Cooperativa Palmera"
        },
        {
            id: "FLT-04-LZ",
            nombre: "Buque Interinsular 'Mar de Las Palmas'",
            tipo: "Transporte Marítimo",
            origen: "Arrecife (Lanzarote)",
            destino: "Puerto del Rosario (Fuerteventura)",
            estado: "Completado",
            velocidad: "0 nudos",
            combustible: "60%",
            operador: "Naviera Archipiélago"
        }
    ];

    // Filtrar elementos de la flota
    const filteredFlota = flotaVehiculos.filter((item) => {
        const matchesSearch = item.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              item.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              item.origen.toLowerCase().includes(searchTerm.toLowerCase());
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
                            Logística & Transporte Multiruta
                        </span>
                        <span className="text-xs text-slate-400 font-medium">Control en Vivo</span>
                    </div>
                    <h1 className="text-2xl font-black text-blue-950 mt-1">Flota Multiruta</h1>
                    <p className="text-sm text-slate-600">Monitoreo de buques de carga, camiones reefer y distribución terrestre en las islas.</p>
                </div>

                <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-500 uppercase">Total Unidades:</span>
                    <span className="bg-[#0038A8] text-white px-3 py-1.5 rounded-xl text-xs font-black shadow-md shadow-blue-500/20">
                        {flotaVehiculos.length} Vehículos
                    </span>
                </div>
            </div>

            {/* Búsqueda y Filtros */}
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="relative w-full sm:w-96">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input 
                        type="text"
                        placeholder="Buscar por ID, nombre u origen..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-white border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0038A8] shadow-sm"
                    />
                </div>

                <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
                    {["Todos", "En Ruta", "En Mantenimiento", "Completado"].map((estado) => (
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

            {/* Grid de la Flota */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {filteredFlota.length === 0 ? (
                    <div className="col-span-full py-12 text-center bg-white rounded-2xl border border-slate-100 shadow-sm">
                        <p className="text-sm font-bold text-slate-400">No se encontraron unidades de transporte con los filtros seleccionados.</p>
                    </div>
                ) : (
                    filteredFlota.map((item, idx) => (
                        <div 
                            key={idx} 
                            className="bg-white rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-all duration-300 p-6 flex flex-col justify-between space-y-4"
                        >
                            <div className="flex justify-between items-start">
                                <div className="flex items-center gap-3">
                                    <div className="h-12 w-12 rounded-xl bg-blue-50 text-[#0038A8] flex items-center justify-center font-bold border border-blue-100 shadow-sm">
                                        {item.tipo.includes("Marítimo") ? <Ship size={22} /> : <Truck size={22} />}
                                    </div>
                                    <div>
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{item.id} - {item.tipo}</span>
                                        <h3 className="text-base font-black text-blue-950">{item.nombre}</h3>
                                    </div>
                                </div>
                                <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1 ${
                                    item.estado === "En Ruta" 
                                        ? "bg-blue-50 text-[#0038A8] border border-blue-100" 
                                        : item.estado === "Completado"
                                        ? "bg-emerald-50 text-emerald-700 border border-emerald-100"
                                        : "bg-amber-50 text-amber-700 border border-amber-100"
                                }`}>
                                    {item.estado === "En Ruta" ? <Navigation size={14} /> : <CheckCircle2 size={14} />}
                                    {item.estado}
                                </span>
                            </div>

                            {/* Ruta */}
                            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1.5 text-xs text-slate-700">
                                <div className="flex items-center gap-2">
                                    <MapPin size={14} className="text-[#0038A8]" />
                                    <span className="font-bold text-blue-950">Origen:</span> {item.origen}
                                </div>
                                <div className="flex items-center gap-2">
                                    <Compass size={14} className="text-amber-600" />
                                    <span className="font-bold text-blue-950">Destino:</span> {item.destino}
                                </div>
                            </div>

                            {/* Datos de Velocidad y Combustible */}
                            <div className="grid grid-cols-2 gap-3 text-xs text-slate-600 pt-2 border-t border-slate-100">
                                <div className="space-y-0.5">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase">Velocidad Actual</span>
                                    <p className="font-bold text-blue-950">{item.velocidad}</p>
                                </div>
                                <div className="space-y-0.5">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase">Nivel Combustible</span>
                                    <p className="font-bold text-blue-950">{item.combustible}</p>
                                </div>
                            </div>

                            <div className="flex justify-between items-center pt-2 border-t border-slate-100 text-xs">
                                <span className="text-[11px] text-slate-500 font-medium">Operador: <strong className="text-slate-700">{item.operador}</strong></span>
                                <button className="text-xs font-bold text-[#0038A8] hover:text-blue-900 flex items-center gap-1 transition-colors cursor-pointer">
                                    <span>Ver Telemetría</span>
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