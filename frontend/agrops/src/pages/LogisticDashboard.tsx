"use client";

import { useState, useEffect } from "react";
import { 
    Ship, 
    ThermometerSnowflake, 
    MapPin, 
    PackageCheck, 
    AlertTriangle, 
    CheckCircle2,
    Compass,
    Warehouse,
    Layers,
    Loader2,
    PackagePlus,
    PlusCircle,
    Box,
    Anchor,
    Truck,
    ArrowRight,
    Building2,
    MessageSquare,
    UserCheck
} from "lucide-react";
import { 
    LineChart, 
    Line, 
    XAxis, 
    YAxis, 
    CartesianGrid, 
    Tooltip, 
    ReferenceLine, 
    ResponsiveContainer 
} from "recharts";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import api from "@/api";

function MapBoundsOptimizer({ coords }: { coords: [number, number][] }) {
    const map = useMap();
    if (coords && coords.length > 0) {
        const bounds = L.latLngBounds(coords);
        map.fitBounds(bounds, { padding: [50, 50], animate: true });
    }
    return null;
}

const farmerIcon = new L.DivIcon({
    html: `<div style="background-color: #059669; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 4px 6px rgba(0,0,0,0.2);"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg></div>`,
    className: "custom-icon-farmer",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
});

const coopIcon = new L.DivIcon({
    html: `<div style="background-color: #f59e0b; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 4px 6px rgba(0,0,0,0.2);"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 21h18M3 7v14M21 7v14M6 11h4M6 15h4M14 11h4M14 15h4M12 3L2 7h20L12 3z"></path></svg></div>`,
    className: "custom-icon-coop",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
});

const shipIcon = new L.DivIcon({
    html: `<div style="background-color: #3b82f6; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 4px 6px rgba(0,0,0,0.2);"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M2 21c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1 .6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/></svg></div>`,
    className: "custom-icon-ship",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
});

const destinationIcon = new L.DivIcon({
    html: `<div style="background-color: #8b5cf6; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 4px 6px rgba(0,0,0,0.2);"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line></svg></div>`,
    className: "custom-icon-destination",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
});

interface TempRecord { time: string; temp: number; }

interface ShipmentDetails {
    id: string;
    product: string;
    containerId: string;
    farmerName: string;
    originCoords: [number, number];       
    coopName: string;
    coopCoords: [number, number];
    vesselCoords: [number, number];       
    destinationName: string;
    destinationCoords: [number, number];  
    vessel: string;
    air_chamber?: string;
    truck_plate?: string;
    land_carrier?: string;
    departureDate: string;
    eta: string;
    currentStep: number; 
    temperatureThreshold: number; 
    temperatureHistory: TempRecord[];
    routeColor: string; 
    hasAlert?: boolean;
}

const TIMELINE_STEPS = [
    { label: "Agricultor & Finca", icon: UserCheck },
    { label: "Cooperativa Agrícola", icon: Building2 },
    { label: "Tránsito Marítimo", icon: Ship },
    { label: "Puerto Peninsular", icon: MapPin },
    { label: "Mercamadrid Destino", icon: CheckCircle2 }
];

const COLORS_PALETTE = ["#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6"];

interface LogisticsTrackerProps {
    selectedShipmentId?: string;
    onAskAI?: (query: string) => void;
}

export default function LogisticsTracker({ selectedShipmentId: externalShipmentId, onAskAI }: LogisticsTrackerProps) {
    const [shipmentsData, setShipmentsData] = useState<Record<string, ShipmentDetails>>({});
    const [catalog, setCatalog] = useState<any[]>([]);
    const [fleetCatalog, setFleetCatalog] = useState<any[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const [internalShipmentId, setInternalShipmentId] = useState<string>("");
    const [activeOverlayIds, setActiveOverlayIds] = useState<string[]>([]);
    
    const [showForm, setShowForm] = useState<boolean>(false);
    const [formLoading, setFormLoading] = useState<boolean>(false);
    
    const [formData, setFormData] = useState({
        id: "LOTE-" + Math.floor(400 + Math.random() * 100),
        product: "",
        container_id: "",
        farmer_name: "Juan Antonio Pérez (Finca San Miguel)",
        origin_lat: 28.4682,
        origin_lng: -16.2546,
        coop_name: "Cooperativa Agrícola del Norte de Tenerife",
        coop_lat: 28.5000,
        coop_lng: -16.3500,
        destination_name: "Mercamadrid - Madrid",
        destination_lat: 40.3833,
        destination_lng: -3.6833,
        vessel_name: "",
        air_chamber: "Cámara Proa - Zona Fría A",
        truck_plate: "4829-LMX",
        land_carrier: "Transports Frío Peninsular S.A.",
        departure_date: new Date().toISOString().slice(0, 19),
        eta: new Date(Date.now() + 6 * 86400000).toISOString().slice(0, 19),
        temperature_threshold: 14.0
    });

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const [shipmentsRes, catalogRes, fleetRes] = await Promise.all([
                api.get("/logistics/shipments"),
                api.get("/logistics/catalog/agricultural-options"),
                api.get("/logistics/fleet")
            ]);

            const items = shipmentsRes.data;
            if (catalogRes.data) setCatalog(catalogRes.data);
            if (fleetRes.data) setFleetCatalog(fleetRes.data);

            if (Array.isArray(items) && items.length > 0) {
                const formattedMap: Record<string, ShipmentDetails> = {};
                items.forEach((item, index) => {
                    formattedMap[item.id] = {
                        ...item,
                        farmerName: item.farmerName || item.originName || "Agricultor Local",
                        coopName: item.coopName || "Cooperativa Agrícola Insular",
                        coopCoords: item.coopCoords || [item.originCoords[0] + 0.02, item.originCoords[1] + 0.02],
                        routeColor: COLORS_PALETTE[index % COLORS_PALETTE.length]
                    };
                });

                setShipmentsData(formattedMap);
                if (!internalShipmentId && items[0]) {
                    setInternalShipmentId(items[0].id);
                }
                setActiveOverlayIds(items.map((i: any) => i.id));
            } else {
                setShipmentsData({});
            }
        } catch (err) {
            console.error("Error al sincronizar datos con el backend:", err);
            setError("No se pudo conectar con el servidor para listar los productos y la flota.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleProductSelect = (productName: string) => {
        const selected = catalog.find(item => item.product === productName);
        if (selected) {
            setFormData({
                ...formData,
                product: selected.product,
                container_id: selected.containerId,
                vessel_name: selected.vessel || formData.vessel_name,
                farmer_name: selected.originName || "Agricultor Asociado",
                origin_lat: selected.originCoords[0],
                origin_lng: selected.originCoords[1],
                coop_name: selected.coopName || "Cooperativa Agrícola Regional",
                coop_lat: selected.originCoords[0] + 0.015,
                coop_lng: selected.originCoords[1] + 0.015,
                destination_name: selected.destinationName,
                destination_lat: selected.destinationCoords[0],
                destination_lng: selected.destinationCoords[1],
                temperature_threshold: selected.temperatureThreshold
            });
        }
    };

    const handleFormSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.product) {
            alert("Por favor, selecciona un producto agrícola.");
            return;
        }
        try {
            setFormLoading(true);
            await api.post("/logistics/shipments", formData);
            setShowForm(false);
            await fetchData(); 
        } catch (err) {
            console.error("Error al registrar el envío:", err);
            alert("Error al registrar el lote en la base de datos.");
        } finally {
            setFormLoading(false);
        }
    };

    const shipmentIds = Object.keys(shipmentsData);
    const currentId = externalShipmentId || internalShipmentId || shipmentIds[0];
    const shipment = shipmentsData[currentId];

    if (loading && shipmentIds.length === 0) {
        return (
            <div className="flex h-96 w-full items-center justify-center bg-white rounded-2xl border border-slate-200">
                <div className="flex flex-col items-center gap-3">
                    <Loader2 className="animate-spin text-emerald-600" size={32} />
                    <p className="text-sm font-medium text-slate-600">Sincronizando trazabilidad del agricultor...</p>
                </div>
            </div>
        );
    }

    const latestRecord = shipment?.temperatureHistory?.[shipment.temperatureHistory.length - 1] || { temp: 0 };
    const hasTemperatureAlert = shipment?.hasAlert || shipment?.temperatureHistory?.some(d => d.temp > shipment.temperatureThreshold) || false;

    const toggleOverlayRoute = (id: string) => {
        if (activeOverlayIds.includes(id)) {
            if (activeOverlayIds.length > 1) {
                setActiveOverlayIds(activeOverlayIds.filter(item => item !== id));
            }
        } else {
            setActiveOverlayIds([...activeOverlayIds, id]);
        }
    };

    const allActiveCoords: [number, number][] = activeOverlayIds.flatMap(id => {
        const item = shipmentsData[id];
        if (!item) return [];
        return [item.originCoords, item.coopCoords || item.originCoords, item.vesselCoords, item.destinationCoords];
    });

    return (
        <div className="space-y-6">
            
            {/* CABECERA Y ACCIÓN PRINCIPAL */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 rounded-2xl bg-white p-5 border border-slate-200 shadow-sm">
                <div>
                    <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                        <UserCheck size={20} className="text-emerald-600"/>
                        Centro de Control Logístico (Agricultor ➔ Cooperativa ➔ Mercamadrid)
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">Trazabilidad de origen con certificación del agricultor y custodias en tiempo real</p>
                </div>
                
                <div className="flex flex-wrap items-center gap-4">
                    {shipmentIds.length > 0 && (
                        <div className="flex items-center gap-2">
                            <label htmlFor="tracker-lote-select" className="text-sm font-semibold text-slate-700">
                                Lote Activo:
                            </label>
                            <select 
                                id="tracker-lote-select"
                                value={currentId}
                                onChange={(e) => setInternalShipmentId(e.target.value)}
                                className="cursor-pointer rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-bold text-slate-900 shadow-sm focus:border-emerald-500 focus:bg-white focus:outline-none"
                            >
                                {Object.values(shipmentsData).map(item => (
                                    <option key={item.id} value={item.id}>
                                        {item.id} — {item.product}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                    <button 
                        onClick={() => setShowForm(!showForm)}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-sm font-bold shadow-sm transition flex items-center gap-2 cursor-pointer"
                    >
                        <PlusCircle size={16} /> {showForm ? "Cerrar Panel" : "Nuevo Lote con Agricultor"}
                    </button>
                </div>
            </div>

            {/* FORMULARIO DINÁMICO */}
            {showForm && (
                <form onSubmit={handleFormSubmit} className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xl space-y-6">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                        <h4 className="text-sm font-bold flex items-center gap-2 text-slate-900">
                            <PackagePlus size={18} className="text-emerald-600" /> Registro del Agricultor, Cooperativa y Transporte
                        </h4>
                        <span className="text-[11px] text-slate-500">Sincronizado con la API del backend</span>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
                        <div className="space-y-4">
                            <div>
                                <label className="text-xs font-semibold text-slate-700 block mb-1">1. Producto Agrícola:</label>
                                <select 
                                    onChange={e => handleProductSelect(e.target.value)}
                                    className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-bold text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                                    required
                                >
                                    <option value="">-- Elige un producto del catálogo --</option>
                                    {catalog.map((cat, idx) => (
                                        <option key={idx} value={cat.product}>
                                            {cat.product} (Contenedor {cat.containerId})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs font-semibold text-slate-700 block mb-1">2. Agricultor / Finca:</label>
                                    <input 
                                        type="text"
                                        value={formData.farmer_name}
                                        onChange={e => setFormData({...formData, farmer_name: e.target.value})}
                                        className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-bold text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-slate-700 block mb-1">3. Cooperativa de Acopio:</label>
                                    <input 
                                        type="text"
                                        value={formData.coop_name}
                                        onChange={e => setFormData({...formData, coop_name: e.target.value})}
                                        className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-bold text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs font-semibold text-slate-700 block mb-1">4. Buque Comercial:</label>
                                    <select 
                                        value={formData.vessel_name}
                                        onChange={e => setFormData({...formData, vessel_name: e.target.value})}
                                        className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-bold text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                                        required
                                    >
                                        <option value="">-- Selecciona buque --</option>
                                        {fleetCatalog.map((vessel, idx) => (
                                            <option key={idx} value={vessel.vesselName}>
                                                🚢 {vessel.vesselName}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-slate-700 block mb-1">5. Código de Lote:</label>
                                    <input 
                                        type="text" 
                                        value={formData.id} 
                                        onChange={e => setFormData({...formData, id: e.target.value})}
                                        className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs font-semibold text-slate-700 block mb-1">6. Operador Terrestre:</label>
                                    <select 
                                        value={formData.land_carrier}
                                        onChange={e => setFormData({...formData, land_carrier: e.target.value})}
                                        className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-bold text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                                    >
                                        <option value="Transports Frío Peninsular S.A.">Transports Frío Peninsular</option>
                                        <option value="Logística Ibérica de Contenedores">Logística Ibérica</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-slate-700 block mb-1">7. Matrícula Tráiler:</label>
                                    <input 
                                        type="text" 
                                        value={formData.truck_plate} 
                                        onChange={e => setFormData({...formData, truck_plate: e.target.value})}
                                        className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="pt-2">
                                <button 
                                    type="submit" 
                                    disabled={formLoading}
                                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-black py-3 rounded-2xl transition flex items-center justify-center gap-2 text-xs shadow-md shadow-emerald-600/20 cursor-pointer"
                                >
                                    {formLoading && <Loader2 className="animate-spin" size={16} />}
                                    Confirmar y Desplegar con Agricultor
                                </button>
                            </div>
                        </div>

                        <div className="relative h-72 bg-slate-50 rounded-2xl border border-slate-200 p-6 flex flex-col items-center justify-center overflow-hidden shadow-inner group">
                            <div className="absolute inset-0 bg-radial from-emerald-500/5 via-transparent to-transparent pointer-events-none" />

                            {formData.product ? (
                                <div className="text-center space-y-4 animate-in fade-in zoom-in duration-300 z-10 w-full">
                                    <div className="flex items-center justify-center gap-2">
                                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600 text-white shadow">
                                            <UserCheck size={18} />
                                        </div>
                                        <ArrowRight size={14} className="text-slate-400" />
                                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500 text-white shadow">
                                            <Building2 size={18} />
                                        </div>
                                        <ArrowRight size={14} className="text-slate-400" />
                                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500 text-white shadow">
                                            <Ship size={18} />
                                        </div>
                                    </div>

                                    <div>
                                        <h5 className="text-sm font-extrabold text-slate-900 tracking-wide">{formData.product}</h5>
                                        <p className="text-[11px] text-emerald-700 font-mono mt-0.5">Agricultor: {formData.farmer_name}</p>
                                    </div>

                                    <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm text-left space-y-1">
                                        <p className="text-[11px] text-slate-700 flex items-center justify-between">
                                            <span className="font-bold flex items-center gap-1"><Building2 size={12} className="text-amber-500"/> Cooperativa:</span>
                                            <span className="font-semibold text-slate-900">{formData.coop_name}</span>
                                        </p>
                                        <p className="text-[11px] text-slate-700 flex items-center justify-between">
                                            <span className="font-bold flex items-center gap-1"><Truck size={12} className="text-purple-500"/> Terrestre:</span>
                                            <span className="font-semibold text-slate-900">{formData.truck_plate}</span>
                                        </p>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center space-y-2 z-10 opacity-70">
                                    <UserCheck size={36} className="mx-auto text-emerald-600 animate-bounce" />
                                    <p className="text-xs text-slate-500 font-medium">Selecciona un producto para ver el esquema del agricultor</p>
                                </div>
                            )}
                        </div>
                    </div>
                </form>
            )}

            {/* ALERTA CRÍTICA */}
            {hasTemperatureAlert && shipment && (
                <div className="rounded-2xl bg-rose-50 border border-rose-200 p-4 text-rose-800 flex items-center justify-between shadow-sm animate-pulse">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="text-rose-600 shrink-0" size={24} />
                        <div>
                            <p className="text-sm font-bold">¡ALERTA CRÍTICA EN LA CADENA DE FRÍO!</p>
                            <p className="text-xs">El contenedor {shipment.containerId} ha superado los {shipment.temperatureThreshold}ºC.</p>
                        </div>
                    </div>
                    <span className="bg-rose-600 text-white font-bold text-xs px-3 py-1.5 rounded-xl shrink-0">
                        Acción Requerida
                    </span>
                </div>
            )}

            {/* MAPA Y CAPAS */}
            {shipmentIds.length === 0 ? (
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-12 text-center text-slate-600">
                    <p className="font-bold text-base">No hay lotes logísticos activos</p>
                    <p className="text-sm mt-1">Registra tu primer lote seleccionando al agricultor de origen.</p>
                </div>
            ) : shipment && (
                <>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col justify-between">
                            <div>
                                <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100 text-slate-900 font-bold text-sm">
                                    <Layers size={18} className="text-emerald-600" />
                                    Capas Activas en el Mapa
                                </div>
                                <div className="space-y-3">
                                    {Object.values(shipmentsData).map(route => {
                                        const isChecked = activeOverlayIds.includes(route.id);
                                        return (
                                            <label 
                                                key={route.id}
                                                className={`flex items-center justify-between p-3 rounded-xl border transition cursor-pointer ${
                                                    isChecked ? 'border-emerald-500 bg-emerald-50/40 shadow-sm' : 'border-slate-200 bg-slate-50 opacity-60'
                                                }`}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <input 
                                                        type="checkbox"
                                                        checked={isChecked}
                                                        onChange={() => toggleOverlayRoute(route.id)}
                                                        className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
                                                    />
                                                    <div>
                                                        <p className="text-xs font-bold text-slate-900">{route.product}</p>
                                                        <p className="text-[10px] text-slate-500">Destino: {route.destinationName}</p>
                                                    </div>
                                                </div>
                                                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: route.routeColor }}></span>
                                            </label>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>

                        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col">
                            <div className="h-80 w-full rounded-2xl overflow-hidden relative z-0 border border-slate-200 shadow-inner">
                                <MapContainer center={[34.0, -10.0]} zoom={5} scrollWheelZoom={true} className="h-full w-full">
                                    <MapBoundsOptimizer coords={allActiveCoords} />
                                    <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" />
                                    {activeOverlayIds.map(id => {
                                        const item = shipmentsData[id];
                                        if (!item) return null;
                                        
                                        const coopCoords = item.coopCoords || [item.originCoords[0] + 0.02, item.originCoords[1] + 0.02];
                                        const farmerToCoop: [number, number][] = [item.originCoords, coopCoords];
                                        const coopToVessel: [number, number][] = [coopCoords, item.vesselCoords];
                                        const landRoute: [number, number][] = [item.vesselCoords, item.destinationCoords];

                                        return (
                                            <div key={item.id}>
                                                <Polyline positions={farmerToCoop} pathOptions={{ color: '#059669', weight: 4, opacity: 0.9 }} />
                                                <Polyline positions={coopToVessel} pathOptions={{ color: '#f59e0b', weight: 4, dashArray: '4, 4', opacity: 0.9 }} />
                                                <Polyline positions={landRoute} pathOptions={{ color: '#10b981', weight: 4, opacity: 0.9 }} />

                                                <Marker position={item.originCoords} icon={farmerIcon}>
                                                    <Popup className="font-sans text-xs rounded-xl"><strong>Agricultor: {item.farmerName}</strong><br/>Finca de Origen</Popup>
                                                </Marker>
                                                <Marker position={coopCoords} icon={coopIcon}>
                                                    <Popup className="font-sans text-xs rounded-xl"><strong>Cooperativa</strong><br/>{item.coopName}</Popup>
                                                </Marker>
                                                <Marker position={item.vesselCoords} icon={shipIcon}>
                                                    <Popup className="font-sans text-xs rounded-xl"><strong>Buque: {item.vessel}</strong></Popup>
                                                </Marker>
                                                <Marker position={item.destinationCoords} icon={destinationIcon}>
                                                    <Popup className="font-sans text-xs rounded-xl"><strong>Destino: {item.destinationName}</strong></Popup>
                                                </Marker>
                                            </div>
                                        );
                                    })}
                                </MapContainer>
                            </div>
                        </div>
                    </div>

                    {/* TRAZABILIDAD PASO A PASO CON AGRICULTOR */}
                    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-100 pb-4">
                            <div>
                                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
                                    <Compass size={18} className="text-emerald-600" /> Trazabilidad Completa: Agricultor ➔ Cooperativa ➔ Mercamadrid
                                </h3>
                                <p className="text-xs text-slate-500">Custodia certificada para el lote <span className="font-mono font-bold text-slate-800">{shipment.id}</span></p>
                            </div>
                            <span className="text-xs font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-xl font-bold">
                                Estado: {TIMELINE_STEPS[shipment.currentStep]?.label || "En Tránsito"}
                            </span>
                        </div>
                            
                        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                            <div className={`p-4 rounded-2xl border transition ${shipment.currentStep >= 0 ? 'bg-emerald-50/50 border-emerald-300 ring-2 ring-emerald-100' : 'bg-slate-50 border-slate-200 opacity-60'}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="p-2 rounded-xl bg-emerald-600 text-white shadow-sm"><UserCheck size={16} /></span>
                                    <span className="text-[10px] font-mono font-bold text-emerald-700">Paso 1</span>
                                </div>
                                <h4 className="text-xs font-bold text-slate-900">Agricultor & Finca</h4>
                                <p className="text-[11px] text-slate-600 mt-1 leading-snug">{shipment.farmerName}</p>
                            </div>
                            
                            <div className={`p-4 rounded-2xl border transition ${shipment.currentStep >= 1 ? 'bg-amber-50/50 border-amber-300' : 'bg-slate-50 border-slate-200 opacity-60'}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="p-2 rounded-xl bg-amber-600 text-white shadow-sm"><Building2 size={16} /></span>
                                    <span className="text-[10px] font-mono font-bold text-amber-700">Paso 2</span>
                                </div>
                                <h4 className="text-xs font-bold text-slate-900">Cooperativa</h4>
                                <p className="text-[11px] text-slate-600 mt-1 leading-snug">{shipment.coopName || "Acopio y Pre-frío"}</p>
                            </div>
                            
                            <div className={`p-4 rounded-2xl border transition ${shipment.currentStep >= 2 ? 'bg-blue-50/50 border-blue-300' : 'bg-slate-50 border-slate-200 opacity-60'}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="p-2 rounded-xl bg-blue-600 text-white shadow-sm"><Ship size={16} /></span>
                                    <span className="text-[10px] font-mono font-bold text-blue-700">Paso 3</span>
                                </div>
                                <h4 className="text-xs font-bold text-slate-900">Tránsito Marítimo</h4>
                                <p className="text-[11px] text-slate-600 mt-1 leading-snug"><strong className="text-slate-900">{shipment.vessel}</strong></p>
                            </div>
                            
                            <div className={`p-4 rounded-2xl border transition ${shipment.currentStep >= 3 ? 'bg-purple-50/50 border-purple-300' : 'bg-slate-50 border-slate-200 opacity-60'}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="p-2 rounded-xl bg-purple-600 text-white shadow-sm"><Truck size={16} /></span>
                                    <span className="text-[10px] font-mono font-bold text-purple-700">Paso 4</span>
                                </div>
                                <h4 className="text-xs font-bold text-slate-900">Tráiler Última Milla</h4>
                                <p className="text-[11px] text-slate-600 mt-1 leading-snug">{shipment.truck_plate || "4829-LMX"}</p>
                            </div>
                            
                            <div className={`p-4 rounded-2xl border transition ${shipment.currentStep >= 4 ? 'bg-violet-50/50 border-violet-300' : 'bg-slate-50 border-slate-200 opacity-60'}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="p-2 rounded-xl bg-violet-600 text-white shadow-sm"><CheckCircle2 size={16} /></span>
                                    <span className="text-[10px] font-mono font-bold text-violet-700">Paso 5</span>
                                </div>
                                <h4 className="text-xs font-bold text-slate-900">Mercamadrid</h4>
                                <p className="text-[11px] text-slate-600 mt-1 leading-snug">{shipment.destinationName}</p>
                            </div>
                        </div>
                    </div>

                    {/* GRÁFICO DE TEMPERATURA Y BOTÓN DE SIMULACIÓN DE WHATSAPP */}
                    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                        <div className="lg:col-span-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                            <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div>
                                    <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900">
                                        <ThermometerSnowflake size={18} className="text-blue-500" />
                                        Histórico de la Cadena de Frío — Lote: {shipment.id} ({shipment.product})
                                    </h3>
                                    <p className="text-xs text-slate-500 mt-0.5">
                                        Contenedor: <span className="font-mono font-semibold text-slate-700">{shipment.containerId}</span> | 
                                        Zona: <span className="font-semibold text-slate-700">{shipment.air_chamber || "Cámara Principal"}</span> | 
                                        Límite Crítico: <span className="font-semibold text-rose-600">{shipment.temperatureThreshold}ºC</span>
                                    </p>
                                </div>

                                <div className="flex items-center gap-3">
                                    <div className="text-right">
                                        <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Temperatura Actual</p>
                                        <p className={`text-2xl font-black ${hasTemperatureAlert ? 'text-rose-600' : 'text-emerald-600'}`}>
                                            {latestRecord.temp.toFixed(1)}º<span className="text-sm font-bold">C</span>
                                        </p>
                                    </div>
                                    <div className={`px-3 py-1 rounded-xl text-xs font-bold border ${
                                        hasTemperatureAlert ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    }`}>
                                        {hasTemperatureAlert ? "Fuera de Rango" : "Frío Estable"}
                                    </div>
                                </div>
                            </div>
                                
                            <div className="h-80 w-full pt-2">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={shipment.temperatureHistory} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                        <XAxis dataKey="time" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                                        <YAxis domain={[shipment.temperatureThreshold - 4, shipment.temperatureThreshold + 4]} tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} tickFormatter={(value) => `${value}º`} />
                                        <Tooltip content={<CustomTooltip threshold={shipment.temperatureThreshold} />} />
                                        <ReferenceLine y={shipment.temperatureThreshold} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={2} label={{ value: `MÁXIMO PERMITIDO (${shipment.temperatureThreshold}ºC)`, position: 'insideTopRight', fill: '#ef4444', fontSize: 10, fontWeight: 'bold' }} />
                                        <Line type="monotone" dataKey="temp" stroke={hasTemperatureAlert ? "#ef4444" : "#10b981"} strokeWidth={3} dot={{ r: 5, strokeWidth: 3, fill: 'white' }} activeDot={{ r: 7, stroke: hasTemperatureAlert ? "#ef4444" : "#10b981", strokeWidth: 2, fill: 'white' }} isAnimationActive={true} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            {/* Botón para Simular Alerta de WhatsApp */}
                            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                                <p className="text-xs text-slate-500">¿Desea probar el envío de avisos de temperatura al WhatsApp del agricultor?</p>
                                <button 
                                    onClick={async () => {
                                        try {
                                            const res = await api.post(`/logistics/shipments/${shipment.id}/force-alert`);
                                            alert(res.data.message);
                                        } catch (err) {
                                            console.error("Error al forzar la alerta:", err);
                                            alert("Error al simular la alerta de WhatsApp.");
                                        }
                                    }}
                                    className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-4 py-2 rounded-xl text-xs shadow-sm transition cursor-pointer flex items-center gap-1.5"
                                >
                                    <MessageSquare size={14} /> Simular Alerta de WhatsApp
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* GRÁFICOS ADICIONALES DE HUMEDAD Y VENTILACIÓN */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">                
                        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                            <div className="mb-4 flex items-center justify-between">
                                <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-900">
                                    <Layers size={16} className="text-blue-600" /> Humedad Relativa en Cámara (%)
                                </h3>
                                <span className="text-xs font-mono bg-blue-50 text-blue-700 px-2.5 py-1 rounded-lg font-bold">Óptimo: 85% - 90%</span>
                            </div>
                            <div className="h-60 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={shipment.temperatureHistory.map(d => ({ time: d.time, humidity: 85 + (Math.sin(d.temp) * 3) }))}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                        <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                                        <YAxis domain={[70, 100]} tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
                                        <Tooltip />
                                        <ReferenceLine y={90} stroke="#3b82f6" strokeDasharray="3 3" label={{ value: 'MAX', fill: '#3b82f6', fontSize: 10 }} />
                                        <Line type="monotone" dataKey="humidity" stroke="#3b82f6" strokeWidth={2.5} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                            <div className="mb-4 flex items-center justify-between">
                                <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-900">
                                    <Compass size={16} className="text-emerald-600" /> Tasa de Renovación de Aire (CMH)
                                </h3>
                                <span className="text-xs font-mono bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-lg font-bold">Flujo Constante</span>
                            </div>
                            <div className="h-60 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={shipment.temperatureHistory.map(d => ({ time: d.time, airFlow: 20 + (Math.cos(d.temp) * 2) }))}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                        <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                                        <YAxis domain={[10, 30]} tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v} m³/h`} />
                                        <Tooltip />
                                        <Line type="monotone" dataKey="airFlow" stroke="#10b981" strokeWidth={2.5} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

function CustomTooltip({ active, payload, label, threshold }: any) {
    if (active && payload && payload.length) {
        const temp = payload[0].value;
        const isAlert = temp > threshold;
        return (
            <div className="rounded-lg bg-slate-900 p-3 shadow-xl text-white border border-slate-700">
                <p className="text-xs font-medium text-slate-400">{label}</p>
                <p className={`mt-1 text-lg font-bold ${isAlert ? 'text-rose-400' : 'text-emerald-400'}`}>{temp.toFixed(1)} ºC</p>
            </div>
        );
    }
    return null;
}