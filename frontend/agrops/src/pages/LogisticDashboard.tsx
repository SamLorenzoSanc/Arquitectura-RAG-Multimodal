"use client";

import { useState, useEffect } from "react";
import {
  Ship,
  ThermometerSnowflake,
  AlertTriangle,
  Layers,
  Loader2,
  PackagePlus,
  PlusCircle,
  Truck,
  ArrowRight,
  MessageSquare,
  UserCheck,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
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

interface TempRecord {
  time: string;
  temp: number;
}

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

const COLORS_PALETTE = ["#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6"];

interface LogisticsTrackerProps {
  selectedShipmentId?: string;
}

export default function LogisticsTracker({
  selectedShipmentId: externalShipmentId,
}: LogisticsTrackerProps) {
  const [shipmentsData, setShipmentsData] = useState<
    Record<string, ShipmentDetails>
  >({});
  const [catalog, setCatalog] = useState<any[]>([]);
  const [fleetCatalog, setFleetCatalog] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const [internalShipmentId, setInternalShipmentId] = useState<string>("");
  const [activeOverlayIds, setActiveOverlayIds] = useState<string[]>([]);

  const [showForm, setShowForm] = useState<boolean>(false);
  const [formLoading, setFormLoading] = useState<boolean>(false);

  const [formData, setFormData] = useState({
    id: "LOTE-438",
    product: "Plátano de Canarias IGP",
    container_id: "MSCU 982105-4",
    origin_name: "Samuel - Finca San Miguel - Tazacorte (La Palma)",
    origin_lat: 28.6478,
    origin_lng: -17.9255,
    coop_name: "CoValle",
    coop_lat: 28.6628,
    coop_lng: -17.9105,
    destination_name: "Plataforma Logística - Cádiz",
    destination_lat: 36.5271,
    destination_lng: -6.2886,
    vessel_name: "Volcán de Teneguía",
    air_chamber: "Cámara Proa - Zona Fría A",
    truck_plate: "4829-LMX",
    land_carrier: "Transports Frío Peninsular S.A.",
    departure_date: "2026-07-25T07:49:15",
    eta: "2026-07-31T07:49:15",
    temperature_threshold: 14,
  });

  const fetchData = async () => {
    try {
      setLoading(true);

      const [shipmentsRes, catalogRes, fleetRes] = await Promise.all([
        api.get("/logistics/shipments"),
        api.get("/logistics/catalog/agricultural-options"),
        api.get("/logistics/fleet"),
      ]);

      const items = shipmentsRes.data;
      if (catalogRes.data) setCatalog(catalogRes.data);
      if (fleetRes.data) setFleetCatalog(fleetRes.data);

      if (Array.isArray(items) && items.length > 0) {
        const formattedMap: Record<string, ShipmentDetails> = {};
        items.forEach((item, index) => {
          formattedMap[item.id] = {
            ...item,
            farmerName:
              item.farmerName || item.originName || "Agricultor Local",
            coopName: item.coopName || "Cooperativa Agrícola Insular",
            coopCoords: item.coopCoords || [
              item.originCoords[0] + 0.02,
              item.originCoords[1] + 0.02,
            ],
            routeColor: COLORS_PALETTE[index % COLORS_PALETTE.length],
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
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleProductSelect = (productName: string) => {
    const selected = catalog.find((item) => item.product === productName);
    if (selected) {
      setFormData({
        ...formData,
        product: selected.product,
        container_id: selected.containerId,
        vessel_name: selected.vessel || formData.vessel_name,
        origin_name: selected.originName || "Agricultor Asociado",
        origin_lat: selected.originCoords[0],
        origin_lng: selected.originCoords[1],
        destination_name: selected.destinationName,
        destination_lat: selected.destinationCoords[0],
        destination_lng: selected.destinationCoords[1],
        temperature_threshold: selected.temperatureThreshold,
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
          <p className="text-sm font-medium text-slate-600">
            Sincronizando trazabilidad del agricultor...
          </p>
        </div>
      </div>
    );
  }

  const latestRecord = shipment?.temperatureHistory?.[
    shipment.temperatureHistory.length - 1
  ] || { temp: 0 };
  const hasTemperatureAlert =
    shipment?.hasAlert ||
    shipment?.temperatureHistory?.some(
      (d) => d.temp > shipment.temperatureThreshold,
    ) ||
    false;

  const toggleOverlayRoute = (id: string) => {
    if (activeOverlayIds.includes(id)) {
      if (activeOverlayIds.length > 1) {
        setActiveOverlayIds(activeOverlayIds.filter((item) => item !== id));
      }
    } else {
      setActiveOverlayIds([...activeOverlayIds, id]);
    }
  };

  const allActiveCoords: [number, number][] = activeOverlayIds.flatMap((id) => {
    const item = shipmentsData[id];
    if (!item) return [];
    return [
      item.originCoords,
      item.coopCoords || item.originCoords,
      item.vesselCoords,
      item.destinationCoords,
    ];
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 rounded-2xl bg-white p-5 border border-slate-200 shadow-sm">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <UserCheck size={20} className="text-emerald-600" />
            Centro de Control Logístico (Agricultor ➔ Cooperativa ➔ Mercamadrid)
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Trazabilidad de origen con certificación del agricultor y custodias
            en tiempo real
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {shipmentIds.length > 0 && (
            <div className="flex items-center gap-2">
              <label
                htmlFor="tracker-lote-select"
                className="text-sm font-semibold text-slate-700"
              >
                Lote Activo:
              </label>
              <select
                id="tracker-lote-select"
                value={currentId}
                onChange={(e) => setInternalShipmentId(e.target.value)}
                className="cursor-pointer rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-bold text-slate-900 shadow-sm focus:border-emerald-500 focus:bg-white focus:outline-none"
              >
                {Object.values(shipmentsData).map((item) => (
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
            <PlusCircle size={16} />{" "}
            {showForm ? "Cerrar Panel" : "Nuevo Lote con Agricultor"}
          </button>
        </div>
      </div>

      {showForm && (
        <form
          onSubmit={handleFormSubmit}
          className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xl space-y-6"
        >
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <h4 className="text-sm font-bold flex items-center gap-2 text-slate-900">
              <PackagePlus size={18} className="text-emerald-600" /> Registro
              del Envío (Todos los Campos de la Tabla)
            </h4>
            <span className="text-[11px] text-slate-500">
              Sincronizado con la API del backend
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
            <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  1. ID de Lote:
                </label>
                <input
                  type="text"
                  value={formData.id}
                  onChange={(e) =>
                    setFormData({ ...formData, id: e.target.value })
                  }
                  className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  2. Producto Agrícola:
                </label>
                <select
                  onChange={(e) => handleProductSelect(e.target.value)}
                  value={formData.product}
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

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  3. ID de Contenedor (Reefer):
                </label>
                <input
                  type="text"
                  value={formData.container_id}
                  onChange={(e) =>
                    setFormData({ ...formData, container_id: e.target.value })
                  }
                  className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  4. Origen / Finca (origin_name):
                </label>
                <input
                  type="text"
                  value={formData.origin_name}
                  onChange={(e) =>
                    setFormData({ ...formData, origin_name: e.target.value })
                  }
                  className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-bold text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    5. Latitud Origen:
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={formData.origin_lat}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        origin_lat: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    6. Longitud Origen:
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={formData.origin_lng}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        origin_lng: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  7. Destino (destination_name):
                </label>
                <input
                  type="text"
                  value={formData.destination_name}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      destination_name: e.target.value,
                    })
                  }
                  className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-bold text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    8. Latitud Destino:
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={formData.destination_lat}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        destination_lat: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    9. Longitud Destino:
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={formData.destination_lng}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        destination_lng: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  10. Buque Comercial (vessel_name):
                </label>
                <select
                  value={formData.vessel_name}
                  onChange={(e) =>
                    setFormData({ ...formData, vessel_name: e.target.value })
                  }
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
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  11. Cámara de Aire (air_chamber):
                </label>
                <input
                  type="text"
                  value={formData.air_chamber}
                  onChange={(e) =>
                    setFormData({ ...formData, air_chamber: e.target.value })
                  }
                  className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-bold text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    12. Matrícula Tráiler (truck_plate):
                  </label>
                  <input
                    type="text"
                    value={formData.truck_plate}
                    onChange={(e) =>
                      setFormData({ ...formData, truck_plate: e.target.value })
                    }
                    className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    13. Operador Terrestre (land_carrier):
                  </label>
                  <input
                    type="text"
                    value={formData.land_carrier}
                    onChange={(e) =>
                      setFormData({ ...formData, land_carrier: e.target.value })
                    }
                    className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-bold text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    14. Fecha de Salida (departure_date):
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.departure_date}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        departure_date: e.target.value,
                      })
                    }
                    className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    15. Estimación Llegada (eta):
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.eta}
                    onChange={(e) =>
                      setFormData({ ...formData, eta: e.target.value })
                    }
                    className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  16. Umbral de Temperatura (ºC):
                </label>
                <input
                  type="number"
                  step="any"
                  value={formData.temperature_threshold}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      temperature_threshold: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full p-3 border border-slate-200 rounded-2xl bg-slate-50 font-mono text-slate-900 focus:outline-none focus:border-emerald-500 text-xs shadow-inner"
                  required
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={formLoading}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-black py-3 rounded-2xl transition flex items-center justify-center gap-2 text-xs shadow-md shadow-emerald-600/20 cursor-pointer"
                >
                  {formLoading && (
                    <Loader2 className="animate-spin" size={16} />
                  )}
                  Registrar Lote en Base de Datos
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
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500 text-white shadow">
                      <Ship size={18} />
                    </div>
                  </div>

                  <div>
                    <h5 className="text-sm font-extrabold text-slate-900 tracking-wide">
                      {formData.product}
                    </h5>
                    <p className="text-[11px] text-emerald-700 font-mono mt-0.5">
                      Origen: {formData.origin_name}
                    </p>
                  </div>

                  <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm text-left space-y-1">
                    <p className="text-[11px] text-slate-700 flex items-center justify-between">
                      <span className="font-bold flex items-center gap-1">
                        <Ship size={12} className="text-blue-500" /> Buque:
                      </span>
                      <span className="font-semibold text-slate-900">
                        {formData.vessel_name}
                      </span>
                    </p>
                    <p className="text-[11px] text-slate-700 flex items-center justify-between">
                      <span className="font-bold flex items-center gap-1">
                        <Truck size={12} className="text-purple-500" />{" "}
                        Terrestre:
                      </span>
                      <span className="font-semibold text-slate-900">
                        {formData.truck_plate}
                      </span>
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center space-y-2 z-10 opacity-70">
                  <UserCheck
                    size={36}
                    className="mx-auto text-emerald-600 animate-bounce"
                  />
                  <p className="text-xs text-slate-500 font-medium">
                    Selecciona un producto para ver el esquema de envío
                  </p>
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
              <p className="text-sm font-bold">
                ¡ALERTA CRÍTICA EN LA CADENA DE FRÍO!
              </p>
              <p className="text-xs">
                El contenedor {shipment.containerId} ha superado los{" "}
                {shipment.temperatureThreshold}ºC.
              </p>
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
          <p className="text-sm mt-1">
            Registra tu primer lote completando el formulario de campos.
          </p>
        </div>
      ) : (
        shipment && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100 text-slate-900 font-bold text-sm">
                    <Layers size={18} className="text-emerald-600" />
                    Capas Activas en el Mapa
                  </div>
                  <div className="space-y-3">
                    {Object.values(shipmentsData).map((route) => {
                      const isChecked = activeOverlayIds.includes(route.id);
                      return (
                        <label
                          key={route.id}
                          className={`flex items-center justify-between p-3 rounded-xl border transition cursor-pointer ${
                            isChecked
                              ? "border-emerald-500 bg-emerald-50/40 shadow-sm"
                              : "border-slate-200 bg-slate-50 opacity-60"
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
                              <p className="text-xs font-bold text-slate-900">
                                {route.product}
                              </p>
                              <p className="text-[10px] text-slate-500">
                                Destino: {route.destinationName}
                              </p>
                            </div>
                          </div>
                          <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: route.routeColor }}
                          ></span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col">
                <div className="h-80 w-full rounded-2xl overflow-hidden relative z-0 border border-slate-200 shadow-inner">
                  <MapContainer
                    center={[34.0, -10.0]}
                    zoom={5}
                    scrollWheelZoom={true}
                    className="h-full w-full"
                  >
                    <MapBoundsOptimizer coords={allActiveCoords} />
                    <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" />
                    {activeOverlayIds.map((id) => {
                      const item = shipmentsData[id];
                      if (!item) return null;

                      const coopCoords = item.coopCoords || [
                        item.originCoords[0] + 0.02,
                        item.originCoords[1] + 0.02,
                      ];
                      const farmerToCoop: [number, number][] = [
                        item.originCoords,
                        coopCoords,
                      ];
                      const coopToVessel: [number, number][] = [
                        coopCoords,
                        item.vesselCoords,
                      ];
                      const landRoute: [number, number][] = [
                        item.vesselCoords,
                        item.destinationCoords,
                      ];

                      return (
                        <div key={item.id}>
                          <Polyline
                            positions={farmerToCoop}
                            pathOptions={{
                              color: "#059669",
                              weight: 4,
                              opacity: 0.9,
                            }}
                          />
                          <Polyline
                            positions={coopToVessel}
                            pathOptions={{
                              color: "#f59e0b",
                              weight: 4,
                              dashArray: "4, 4",
                              opacity: 0.9,
                            }}
                          />
                          <Polyline
                            positions={landRoute}
                            pathOptions={{
                              color: "#10b981",
                              weight: 4,
                              opacity: 0.9,
                            }}
                          />

                          <Marker
                            position={item.originCoords}
                            icon={farmerIcon}
                          >
                            <Popup className="font-sans text-xs rounded-xl">
                              <strong>Origen: {item.farmerName}</strong>
                            </Popup>
                          </Marker>
                          <Marker position={item.vesselCoords} icon={shipIcon}>
                            <Popup className="font-sans text-xs rounded-xl">
                              <strong>Buque: {item.vessel}</strong>
                            </Popup>
                          </Marker>
                          <Marker
                            position={item.destinationCoords}
                            icon={destinationIcon}
                          >
                            <Popup className="font-sans text-xs rounded-xl">
                              <strong>Destino: {item.destinationName}</strong>
                            </Popup>
                          </Marker>
                        </div>
                      );
                    })}
                  </MapContainer>
                </div>
              </div>
            </div>

            {/* GRÁFICO DE TEMPERATURA */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="lg:col-span-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900">
                      <ThermometerSnowflake
                        size={18}
                        className="text-blue-500"
                      />
                      Histórico de la Cadena de Frío — Lote: {shipment.id} (
                      {shipment.product})
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Contenedor:{" "}
                      <span className="font-mono font-semibold text-slate-700">
                        {shipment.containerId}
                      </span>{" "}
                      | Límite Crítico:{" "}
                      <span className="font-semibold text-rose-600">
                        {shipment.temperatureThreshold}ºC
                      </span>
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
                        Temperatura Actual
                      </p>
                      <p
                        className={`text-2xl font-black ${hasTemperatureAlert ? "text-rose-600" : "text-emerald-600"}`}
                      >
                        {latestRecord.temp.toFixed(1)}º
                        <span className="text-sm font-bold">C</span>
                      </p>
                    </div>
                  </div>
                </div>

                <div className="h-80 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={shipment.temperatureHistory}
                      margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="#f1f5f9"
                      />
                      <XAxis
                        dataKey="time"
                        tick={{ fontSize: 12, fill: "#64748b" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        domain={[
                          shipment.temperatureThreshold - 4,
                          shipment.temperatureThreshold + 4,
                        ]}
                        tick={{ fontSize: 12, fill: "#64748b" }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(value) => `${value}º`}
                      />
                      <Tooltip
                        content={
                          <CustomTooltip
                            threshold={shipment.temperatureThreshold}
                          />
                        }
                      />
                      <ReferenceLine
                        y={shipment.temperatureThreshold}
                        stroke="#ef4444"
                        strokeDasharray="4 4"
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="temp"
                        stroke={hasTemperatureAlert ? "#ef4444" : "#10b981"}
                        strokeWidth={3}
                        dot={{ r: 5, strokeWidth: 3, fill: "white" }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <p className="text-xs text-slate-500">
                    ¿Desea probar el envío de avisos de temperatura al WhatsApp?
                  </p>
                  <button
                    onClick={async () => {
                      try {
                        const res = await api.post(
                          `/logistics/shipments/${shipment.id}/force-alert`,
                        );
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
          </>
        )
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
        <p
          className={`mt-1 text-lg font-bold ${isAlert ? "text-rose-400" : "text-emerald-400"}`}
        >
          {temp.toFixed(1)} ºC
        </p>
      </div>
    );
  }
  return null;
}
