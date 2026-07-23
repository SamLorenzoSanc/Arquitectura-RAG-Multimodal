import { useState, useEffect, useCallback } from "react";
import {
    TrendingUp,
    BarChart3,
    Sun,
    Droplets,
    Sliders,
    RefreshCw,
    Info,
    CheckCircle2,
    Zap,
    MapPin,
    Calendar,
    ArrowUpRight,
    Leaf,
    AlertCircle
} from "lucide-react";
import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend
} from "recharts";

interface ForecastMetric {
    MAPE: number;
    RMSE: number;
    execution_time_ms?: number;
}

interface ComparisonPoint {
    date: string;
    prophet_prediction: number;
    arimax_prediction: number;
}

interface WeatherRecord {
    ds: string;
    temperature_2m_max?: number;
    precipitation_sum?: number;
    [key: string]: any;
}

interface CommodityRecord {
    ds: string;
    close?: number;
    [key: string]: any;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";


const PRODUCTS = [
    { id: "platano_canarias", name: "Plátano de Canarias IGP", unit: "€/kg" },
    { id: "aguacate_hass", name: "Aguacate (La Palma/Tenerife)", unit: "€/kg" },
    { id: "papa_bonita", name: "Papa Bonita de Color", unit: "€/kg" },
    { id: "tomate_canario", name: "Tomate de Exportación", unit: "€/kg" }
];

const ISLANDS = [
    { id: "Tenerife_Norte", name: "Tenerife Norte (Valle de La Orotava)" },
    { id: "Gran_Canaria_Sur", name: "Gran Canaria Sur (San Bartolomé)" },
    { id: "La_Palma", name: "La Palma (Valle de Aridane)" }
];

export default function AnalyticsPage() {
    // Filtros
    const [selectedProduct, setSelectedProduct] = useState(PRODUCTS[0].id);
    const [selectedIsland, setSelectedIsland] = useState(ISLANDS[0].id);
    const [selectedModel, setSelectedModel] = useState<"prophet" | "arimax" | "compare">("compare");
    const [months, setMonths] = useState(6);
    const [priceAdjustment, setPriceAdjustment] = useState(0);

    // Estados de Datos Dinámicos
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [chartData, setChartData] = useState<ComparisonPoint[]>([]);
    const [prophetMetrics, setProphetMetrics] = useState<ForecastMetric | null>(null);
    const [arimaxMetrics, setArimaxMetrics] = useState<ForecastMetric | null>(null);
    const [bestModel, setBestModel] = useState<string>("");

    // Variables Exógenas
    const [weatherData, setWeatherData] = useState<WeatherRecord[]>([]);
    const [commodityData, setCommodityData] = useState<CommodityRecord[]>([]);

    const productInfo = PRODUCTS.find((p) => p.id === selectedProduct) || PRODUCTS[0];

    // 1. Cargar Pronóstico Principal desde FastAPI
    const fetchForecastData = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        const payload = {
            product_id: selectedProduct,
            island: selectedIsland,
            months: Number(months),
            price_adjustment: Number(priceAdjustment)
        };

        try {
            if (selectedModel === "compare") {
                const res = await fetch(`${API_BASE_URL}/forecast/compare`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) throw new Error("Error obteniendo la comparación de modelos");
                const data = await res.json();

                setChartData(data.forecast_comparison);
                setProphetMetrics(data.prophet_metrics);
                setArimaxMetrics(data.arimax_metrics);
                setBestModel(data.best_model);
            } else {
                // Prophet o ARIMAX individual
                const endpoint = selectedModel === "prophet" ? "/forecast/prophet" : "/forecast/arimax";
                const res = await fetch(`${API_BASE_URL}${endpoint}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) throw new Error(`Error en pronóstico con ${selectedModel.toUpperCase()}`);
                const data = await res.json();

                // Formateamos para Recharts
                const formattedData: ComparisonPoint[] = data.forecast.map((pt: any) => ({
                    date: pt.date,
                    prophet_prediction: selectedModel === "prophet" ? pt.predicted_value : 0,
                    arimax_prediction: selectedModel === "arimax" ? pt.predicted_value : 0
                }));

                setChartData(formattedData);
                if (selectedModel === "prophet") {
                    setProphetMetrics(data.metrics);
                    setArimaxMetrics(null);
                } else {
                    setArimaxMetrics(data.metrics);
                    setProphetMetrics(null);
                }
                setBestModel(selectedModel.toUpperCase());
            }
        } catch (err: any) {
            setError(err.message || "Error al conectar con la API de pronósticos");
        } finally {
            setIsLoading(false);
        }
    }, [selectedProduct, selectedIsland, selectedModel, months, priceAdjustment]);

    // 2. Cargar Datos Exógenos (Clima y Commodities)
    const fetchExogenousData = useCallback(async () => {
        try {
            const [resWeather, resCommodities] = await Promise.all([
                fetch(`${API_BASE_URL}/forecast/exogenous/weather?island=${selectedIsland}`),
                fetch(`${API_BASE_URL}/forecast/exogenous/commodities`)
            ]);

            if (resWeather.ok) {
                const wData = await resWeather.json();
                setWeatherData(wData.data || []);
            }
            if (resCommodities.ok) {
                const cData = await resCommodities.json();
                setCommodityData(cData.data || []);
            }
        } catch (e) {
            console.error("Error al cargar variables exógenas:", e);
        }
    }, [selectedIsland]);

    // Efecto de actualización automática
    useEffect(() => {
        fetchForecastData();
    }, [fetchForecastData]);

    useEffect(() => {
        fetchExogenousData();
    }, [fetchExogenousData]);

    // Cálculo de métricas promedio para KPIs
    const avgProphet = chartData.length > 0 
        ? (chartData.reduce((acc, curr) => acc + (curr.prophet_prediction || 0), 0) / chartData.length).toFixed(2)
        : "0.00";

    const latestWeather = weatherData.length > 0 ? weatherData[weatherData.length - 1] : null;
    const latestCommodity = commodityData.length > 0 ? commodityData[commodityData.length - 1] : null;

    return (
        <div className="p-8 space-y-8 bg-slate-50/50 min-h-screen">
            
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-3">
                        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                            <TrendingUp size={22} />
                        </span>
                        <div>
                            <h1 className="text-2xl font-bold text-slate-900">Analítica Predictiva de Demanda</h1>
                            <p className="text-sm text-slate-500">Predicción dinámicas (ARIMAX & Prophet)</p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                        <Leaf size={14} /> Posei / REA Canarias
                    </span>
                    <button
                        onClick={() => { fetchForecastData(); fetchExogenousData(); }}
                        disabled={isLoading}
                        className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm disabled:opacity-50"
                    >
                        <RefreshCw size={16} className={isLoading ? "animate-spin text-emerald-600" : ""} />
                        <span>Re-ejecutar API</span>
                    </button>
                </div>
            </div>

            {/* Error Banner */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center gap-3 text-red-700 text-sm">
                    <AlertCircle size={20} className="shrink-0" />
                    <p className="font-medium">{error}</p>
                </div>
            )}

            {/* Panel de Controles */}
            <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/40 space-y-6">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                    <div className="flex items-center gap-2 text-slate-800 font-semibold">
                        <Sliders size={18} className="text-emerald-600" />
                        <span>Parámetros del Pronóstico (FastAPI)</span>
                    </div>
                    <span className="text-xs text-slate-400">Endpoint: /forecast/{selectedModel}</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {/* Producto */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Producto Agrícola</label>
                        <select
                            value={selectedProduct}
                            onChange={(e) => setSelectedProduct(e.target.value)}
                            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm font-medium text-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none transition-all"
                        >
                            {PRODUCTS.map((p) => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Zona / Isla */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                            <MapPin size={12} /> Zona de Cultivo
                        </label>
                        <select
                            value={selectedIsland}
                            onChange={(e) => setSelectedIsland(e.target.value)}
                            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm font-medium text-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none transition-all"
                        >
                            {ISLANDS.map((i) => (
                                <option key={i.id} value={i.id}>{i.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Horizonte Temporal */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                            <Calendar size={12} /> Horizonte
                        </label>
                        <select
                            value={months}
                            onChange={(e) => setMonths(Number(e.target.value))}
                            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm font-medium text-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none transition-all"
                        >
                            <option value={3}>3 Meses</option>
                            <option value={6}>6 Meses</option>
                            <option value={12}>12 Meses</option>
                        </select>
                    </div>

                    {/* Algoritmo */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Modelo Predictivo</label>
                        <div className="flex bg-slate-100 p-1 rounded-2xl border border-slate-200">
                            <button
                                onClick={() => setSelectedModel("prophet")}
                                className={`flex-1 py-2 text-xs font-semibold rounded-xl transition-all ${selectedModel === "prophet" ? "bg-white text-emerald-700 shadow-sm" : "text-slate-600"}`}
                            >
                                Prophet
                            </button>
                            <button
                                onClick={() => setSelectedModel("arimax")}
                                className={`flex-1 py-2 text-xs font-semibold rounded-xl transition-all ${selectedModel === "arimax" ? "bg-white text-emerald-700 shadow-sm" : "text-slate-600"}`}
                            >
                                ARIMAX
                            </button>
                            <button
                                onClick={() => setSelectedModel("compare")}
                                className={`flex-1 py-2 text-xs font-semibold rounded-xl transition-all ${selectedModel === "compare" ? "bg-white text-emerald-700 shadow-sm" : "text-slate-600"}`}
                            >
                                Comparar
                            </button>
                        </div>
                    </div>
                </div>

                {/* Sensibilidad del Precio */}
                <div className="pt-2 border-t border-slate-100">
                    <div className="flex justify-between items-center mb-2">
                        <label className="text-xs font-semibold text-slate-600 flex items-center gap-1">
                            <span>Ajuste en Insumos/Combustible (Regresor Exógeno):</span>
                            <span className="font-bold text-emerald-700">{priceAdjustment > 0 ? `+${priceAdjustment}%` : `${priceAdjustment}%`}</span>
                        </label>
                    </div>
                    <input
                        type="range"
                        min="-15"
                        max="15"
                        value={priceAdjustment}
                        onChange={(e) => setPriceAdjustment(Number(e.target.value))}
                        className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                    />
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-lg shadow-slate-200/30 flex justify-between items-start">
                    <div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Precio Medio (API)</p>
                        <h3 className="text-3xl font-bold text-slate-900 mt-2">{avgProphet} {productInfo.unit}</h3>
                        <p className="text-xs font-medium text-emerald-600 flex items-center gap-1 mt-2">
                            <ArrowUpRight size={14} /> Modelo Activo: {bestModel || "Analizando"}
                        </p>
                    </div>
                    <div className="p-3 bg-emerald-50 rounded-2xl text-emerald-600">
                        <BarChart3 size={24} />
                    </div>
                </div>

                <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-lg shadow-slate-200/30 flex justify-between items-start">
                    <div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Mejor Algoritmo</p>
                        <h3 className="text-3xl font-bold text-slate-900 mt-2">{bestModel || "N/A"}</h3>
                        <p className="text-xs font-medium text-blue-600 flex items-center gap-1 mt-2">
                            <CheckCircle2 size={14} /> Menor MAPE Detectado
                        </p>
                    </div>
                    <div className="p-3 bg-blue-50 rounded-2xl text-blue-600">
                        <Zap size={24} />
                    </div>
                </div>

                {/* Tarjeta KPI 3: Actualizada para el Agricultor (MAPE) */}
                <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-lg shadow-slate-200/30 flex justify-between items-start">
                    <div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Margen de Error Esperado</p>
                        <h3 className="text-3xl font-bold text-slate-900 mt-2">
                            ± {prophetMetrics ? `${prophetMetrics.MAPE.toFixed(1)}%` : arimaxMetrics ? `${arimaxMetrics.MAPE.toFixed(1)}%` : "0.0%"}
                        </h3>
                        <p className="text-xs font-medium text-purple-600 flex items-center gap-1 mt-2">
                            <CheckCircle2 size={14} /> El precio real puede variar este %
                        </p>
                    </div>
                    <div className="p-3 bg-purple-50 rounded-2xl text-purple-600">
                        <AlertCircle size={24} />
                    </div>
                </div>

                <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-lg shadow-slate-200/30 flex justify-between items-start">
                    <div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Open-Meteo Temp.</p>
                        <h3 className="text-3xl font-bold text-slate-900 mt-2">
                            {latestWeather?.temperature_2m_max ? `${latestWeather.temperature_2m_max} °C` : "21.5 °C"}
                        </h3>
                        <p className="text-xs font-medium text-amber-600 flex items-center gap-1 mt-2">
                            <Sun size={14} /> API Meteorológica
                        </p>
                    </div>
                    <div className="p-3 bg-amber-50 rounded-2xl text-amber-600">
                        <Sun size={24} />
                    </div>
                </div>
            </div>

            {/* Gráfico Recharts dinámico */}
            <div className="bg-white p-7 rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/40 space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                    <div>
                        <h2 className="text-lg font-bold text-slate-900">Proyección Temporal ({productInfo.name})</h2>
                        <p className="text-xs text-slate-500">Datos recibidos dinámicamente desde el motor en Python/FastAPI</p>
                    </div>
                    <div className="flex items-center gap-4 text-xs font-medium">
                        {(selectedModel === "prophet" || selectedModel === "compare") && (
                            <span className="flex items-center gap-1.5 text-emerald-700">
                                <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" /> Prophet
                            </span>
                        )}
                        {(selectedModel === "arimax" || selectedModel === "compare") && (
                            <span className="flex items-center gap-1.5 text-blue-700">
                                <span className="w-3 h-3 rounded-full bg-blue-500 inline-block" /> ARIMAX
                            </span>
                        )}
                    </div>
                </div>

                <div className="h-80 w-full pt-4 relative">
                    {isLoading && (
                        <div className="absolute inset-0 bg-white/70 backdrop-blur-sm z-10 flex items-center justify-center">
                            <RefreshCw className="animate-spin text-emerald-600" size={32} />
                        </div>
                    )}
                    
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                            <defs>
                                <linearGradient id="prophetGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                                </linearGradient>
                                <linearGradient id="arimaxGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                            <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} />
                            <YAxis stroke="#64748b" fontSize={12} tickLine={false} domain={['auto', 'auto']} unit=" €" />
                            <Tooltip
                                contentStyle={{ backgroundColor: "#ffffff", borderRadius: "16px", border: "1px solid #e2e8f0", boxShadow: "0 10px 25px -5px rgba(0,0,0,0.1)" }}
                            />
                            <Legend />
                            {(selectedModel === "prophet" || selectedModel === "compare") && (
                                <Area type="monotone" name="Prophet" dataKey="prophet_prediction" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#prophetGrad)" />
                            )}
                            {(selectedModel === "arimax" || selectedModel === "compare") && (
                                <Area type="monotone" name="ARIMAX" dataKey="arimax_prediction" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#arimaxGrad)" />
                            )}
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Panel Inferior: Métricas Reales Backend y Exógenas */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Tabla de Auditoría: Actualizada para el Agricultor (MAPE/RMSE) */}
                <div className="lg:col-span-2 bg-white p-6 rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/40 space-y-4">
                    <h3 className="text-md font-bold text-slate-900 flex items-center gap-2">
                        <Info size={18} className="text-emerald-600" />
                        <span>Fiabilidad de las Predicciones (Histórico)</span>
                    </h3>
                    <p className="text-xs text-slate-500 mb-4">
                        Comparamos lo que predijo la inteligencia artificial en el pasado con el precio que realmente tuvo el producto.
                    </p>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-400">
                                    <th className="py-3 px-4">Algoritmo</th>
                                    <th className="py-3 px-4">Margen de Error (%)</th>
                                    <th className="py-3 px-4">Desviación del Precio</th>
                                    <th className="py-3 px-4">Recomendación</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 text-slate-700">
                                {prophetMetrics && (
                                    <tr className="hover:bg-slate-50/50 transition-colors">
                                        <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Prophet
                                        </td>
                                        <td className="py-3 px-4 text-emerald-600 font-bold">± {prophetMetrics.MAPE.toFixed(1)}%</td>
                                        <td className="py-3 px-4 text-slate-600">
                                            Falla por unos <span className="font-semibold text-slate-900">{prophetMetrics.RMSE.toFixed(2)} {productInfo.unit}</span>
                                        </td>
                                        <td className="py-3 px-4">
                                            {(bestModel.toUpperCase() === "PROPHET" || bestModel === "Prophet") && (
                                                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                                                    Más Exacto
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                )}
                                {arimaxMetrics && (
                                    <tr className="hover:bg-slate-50/50 transition-colors">
                                        <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                                            <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> ARIMAX
                                        </td>
                                        <td className="py-3 px-4 text-blue-600 font-bold">± {arimaxMetrics.MAPE.toFixed(1)}%</td>
                                        <td className="py-3 px-4 text-slate-600">
                                            Falla por unos <span className="font-semibold text-slate-900">{arimaxMetrics.RMSE.toFixed(2)} {productInfo.unit}</span>
                                        </td>
                                        <td className="py-3 px-4">
                                            {(bestModel.toUpperCase() === "ARIMAX" || bestModel === "ARIMAX") && (
                                                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                                                    Más Exacto
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Resumen de Insumos Exógenos (Se mantiene igual) */}
                <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/40 space-y-4">
                    <h3 className="text-md font-bold text-slate-900">Variables Exógenas (Auditoría)</h3>
                    <div className="space-y-3">
                        <div className="p-3 bg-slate-50 rounded-2xl flex justify-between items-center">
                            <div className="flex items-center gap-3">
                                <Sun size={20} className="text-amber-500" />
                                <div>
                                    <p className="text-xs font-bold text-slate-800">Open-Meteo Clima</p>
                                    <p className="text-xs text-slate-500">{selectedIsland}</p>
                                </div>
                            </div>
                            <span className="text-xs font-bold text-slate-700">
                                {latestWeather?.temperature_2m_max ? `${latestWeather.temperature_2m_max}°C` : "OK"}
                            </span>
                        </div>

                        <div className="p-3 bg-slate-50 rounded-2xl flex justify-between items-center">
                            <div className="flex items-center gap-3">
                                <Droplets size={20} className="text-blue-500" />
                                <div>
                                    <p className="text-xs font-bold text-slate-800">Precipitación</p>
                                    <p className="text-xs text-slate-500">Histórico/Proyección</p>
                                </div>
                            </div>
                            <span className="text-xs font-bold text-slate-700">
                                {latestWeather?.precipitation_sum ? `${latestWeather.precipitation_sum} mm` : "OK"}
                            </span>
                        </div>

                        <div className="p-3 bg-slate-50 rounded-2xl flex justify-between items-center">
                            <div className="flex items-center gap-3">
                                <TrendingUp size={20} className="text-emerald-500" />
                                <div>
                                    <p className="text-xs font-bold text-slate-800">Petróleo Crudo (CL=F)</p>
                                    <p className="text-xs text-slate-500">Commodity Global</p>
                                </div>
                            </div>
                            <span className="text-xs font-bold text-slate-700">
                                {latestCommodity?.close ? `$${latestCommodity.close}` : "$75.40"}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    );
}