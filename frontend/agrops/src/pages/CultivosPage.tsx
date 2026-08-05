"use client";

import { useState, useEffect } from "react";
import { 
    Wheat, 
    Search, 
    ShieldCheck, 
    MapPin, 
    Sun, 
    Droplets,
    ChevronRight,
    Loader2
} from "lucide-react";

export default function CultivosPage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedCategoria, setSelectedCategoria] = useState("Todos");
    const [cultivosCanarias, setCultivosCanarias] = useState<any[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // Cargar datos oficiales al montar el componente
    useEffect(() => {
        const fetchCultivosOficiales = async () => {
            try {
                setLoading(true);
                
                // Datos preprocesados de cultivos tradicionales y protegidos de Canarias
                const dataOficial = [
                    {
                        id: 1,
                        nombre: "Plátano de Canarias",
                        categoria: "Fruta",
                        igp: "IGP Protegida",
                        islas: ["Tenerife", "La Palma", "Gran Canaria", "El Hierro", "La Gomera"],
                        descripcion: "Fruto caracterizado por sus pequeñas manchas oscuras en la piel ('pecas'), sabor dulce intenso y alto contenido en potasio.",
                        riego: "Riego por goteo optimizado",
                        temperatura: "20°C - 28°C",
                        imagen: "🍌"
                    },
                    {
                        id: 2,
                        nombre: "Tomate de Canarias (Exportación)",
                        categoria: "Hortaliza",
                        igp: "Certificación de Calidad",
                        islas: ["Gran Canaria", "Tenerife", "Fuerteventura"],
                        descripcion: "Cultivado bajo condiciones climáticas subtropicales únicas, reconocido internacionalmente por su firmeza y sabor equilibrado.",
                        riego: "Controlado por sensores de humedad",
                        temperatura: "18°C - 26°C",
                        imagen: "🍅"
                    },
                    {
                        id: 3,
                        nombre: "Papas Antiguas de Canarias",
                        categoria: "Tubérculo",
                        igp: "Denominación de Origen Protegida (DOP)",
                        islas: ["Tenerife", "Gran Canaria"],
                        descripcion: "Variedades históricas introducidas desde América (como la Bonita y la Negra Yema de Huevo), de textura firme y sabor almendrado.",
                        riego: "Riego moderado en secano controlado",
                        temperatura: "14°C - 22°C",
                        imagen: "🥔"
                    },
                    {
                        id: 4,
                        nombre: "Vinos de Canarias (Malvasía / Listán)",
                        categoria: "Viticultura",
                        igp: "DOP Islas Canarias",
                        islas: ["Lanzarote", "Tenerife", "La Palma", "El Hierro"],
                        descripcion: "Cepas prefiloxéricas cultivadas en suelos volcánicos únicos, destacando el famoso Malvasía Volcánica de Lanzarote.",
                        riego: "Secano extremo / retención de humedad volcánica",
                        temperatura: "16°C - 25°C",
                        imagen: "🍇"
                    }
                ];

                setCultivosCanarias(dataOficial);
            } catch (err) {
                console.error("Error al obtener los datos oficiales:", err);
                setError("No se pudieron cargar los datos de cultivos.");
            } finally {
                setLoading(false);
            }
        };

        fetchCultivosOficiales();
    }, []);

    // Filtrar cultivos según búsqueda y categoría
    const filteredCultivos = cultivosCanarias.filter((cultivo) => {
        const matchesSearch = cultivo.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              cultivo.descripcion.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesCategoria = selectedCategoria === "Todos" || cultivo.categoria === selectedCategoria;
        return matchesSearch && matchesCategoria;
    });

    return (
        <div className="p-8 space-y-8 bg-slate-50/50 min-h-screen">
            
            {/* Cabecera de la página */}
            <div className="bg-white p-6 rounded-2xl border border-blue-100 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="px-3 py-1 rounded-full bg-blue-100 text-[#0038A8] text-xs font-bold uppercase tracking-wider">
                            Normativa IGP & Cultivos
                        </span>
                        <span className="text-xs text-slate-400 font-medium">Catálogo Oficial</span>
                    </div>
                    <h1 className="text-2xl font-black text-blue-950 mt-1">Cultivos Tradicionales de Canarias</h1>
                    <p className="text-sm text-slate-600">Gestión, trazabilidad y cumplimiento de denominaciones de origen protegidas.</p>
                </div>

                <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-500 uppercase">Registros:</span>
                    <span className="bg-[#0038A8] text-white px-3 py-1.5 rounded-xl text-xs font-black shadow-md shadow-blue-500/20">
                        {cultivosCanarias.length} Variedades
                    </span>
                </div>
            </div>

            {/* Barra de Búsqueda y Filtros */}
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="relative w-full sm:w-96">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input 
                        type="text"
                        placeholder="Buscar por nombre o descripción..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-white border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0038A8] shadow-sm"
                    />
                </div>

                <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
                    {["Todos", "Fruta", "Hortaliza", "Tubérculo", "Viticultura"].map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setSelectedCategoria(cat)}
                            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
                                selectedCategoria === cat
                                    ? "bg-[#0038A8] text-white shadow-md shadow-blue-500/20"
                                    : "bg-white text-slate-600 border border-slate-200 hover:bg-blue-50 hover:text-[#0038A8]"
                            }`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            </div>

            {/* Contenido principal con estados de Carga / Error */}
            {loading ? (
                <div className="py-24 flex flex-col items-center justify-center bg-white rounded-2xl border border-slate-100 shadow-sm">
                    <Loader2 className="animate-spin text-[#0038A8] mb-3" size={32} />
                    <p className="text-xs font-bold text-slate-500">Cargando registros de cultivos...</p>
                </div>
            ) : error ? (
                <div className="py-12 text-center bg-red-50 rounded-2xl border border-red-100 text-red-700 text-xs font-bold">
                    {error}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredCultivos.length === 0 ? (
                        <div className="col-span-full py-12 text-center bg-white rounded-2xl border border-slate-100 shadow-sm">
                            <p className="text-sm font-bold text-slate-400">No se encontraron cultivos con los filtros seleccionados.</p>
                        </div>
                    ) : (
                        filteredCultivos.map((cultivo) => (
                            <div 
                                key={cultivo.id} 
                                className="bg-white rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-between overflow-hidden group"
                            >
                                <div className="p-6 space-y-4">
                                    <div className="flex justify-between items-start">
                                        <div className="h-12 w-12 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-2xl shadow-sm">
                                            {cultivo.imagen}
                                        </div>
                                        <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 text-[11px] font-bold border border-emerald-100 flex items-center gap-1">
                                            <ShieldCheck size={14} />
                                            {cultivo.igp}
                                        </span>
                                    </div>

                                    <div>
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{cultivo.categoria}</span>
                                        <h3 className="text-lg font-black text-blue-950 mt-0.5 group-hover:text-[#0038A8] transition-colors">{cultivo.nombre}</h3>
                                        <p className="text-xs text-slate-600 mt-2 leading-relaxed">{cultivo.descripcion}</p>
                                    </div>

                                    <div className="space-y-1.5 pt-2 border-t border-slate-100">
                                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                                            <MapPin size={12} className="text-[#0038A8]" />
                                            Islas Productoras:
                                        </p>
                                        <div className="flex flex-wrap gap-1">
                                            {cultivo.islas.map((isla: string, i: number) => (
                                                <span key={i} className="px-2 py-0.5 rounded-lg bg-slate-100 text-slate-700 text-[10px] font-semibold">
                                                    {isla}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 pt-2 text-xs text-slate-600">
                                        <div className="flex items-center gap-1.5 bg-blue-50/50 p-2 rounded-xl">
                                            <Droplets size={14} className="text-[#0038A8]" />
                                            <span className="text-[11px] font-medium truncate">{cultivo.riego}</span>
                                        </div>
                                        <div className="flex items-center gap-1.5 bg-amber-50/50 p-2 rounded-xl">
                                            <Sun size={14} className="text-amber-600" />
                                            <span className="text-[11px] font-medium truncate">{cultivo.temperatura}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex justify-between items-center">
                                    <span className="text-[11px] font-bold text-slate-500">Cuaderno RAG Activo</span>
                                    <button className="text-xs font-bold text-[#0038A8] hover:text-blue-900 flex items-center gap-1 transition-colors cursor-pointer">
                                        <span>Ver Directrices</span>
                                        <ChevronRight size={14} />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}

        </div>
    );
}