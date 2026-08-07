"use client";

import React, { useEffect, useState } from "react";
import L from "leaflet";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

interface Crop {
  id?: string;
  user_id?: string;
  nombre: string;
  cultivo: string;
  isla: string;
  lat: number;
  lon: number;
  temperatura: number;
  humedad: number;
  lluvia: number;
  viento: number;
  ndvi: number;
  sentinel_tile?: string;
}

const ISLAS_CANARIAS = [
  "Tenerife",
  "Gran Canaria",
  "Lanzarote",
  "Fuerteventura",
  "La Palma",
  "La Gomera",
  "El Hierro",
  "La Graciosa",
];

const isValidCoord = (lat: any, lon: any): boolean =>
  typeof lat === "number" &&
  typeof lon === "number" &&
  !isNaN(lat) &&
  !isNaN(lon) &&
  lat >= -90 &&
  lat <= 90 &&
  lon >= -180 &&
  lon <= 180;

function getCustomIcon(cultivo: string) {
  let emoji = "🌱";
  let bgColor = "bg-blue-600";
  const lower = cultivo ? cultivo.toLowerCase() : "";

  if (lower.includes("plátano") || lower.includes("platano")) {
    emoji = "🍌";
    bgColor = "bg-amber-400";
  } else if (lower.includes("aguacate")) {
    emoji = "🥑";
    bgColor = "bg-blue-700";
  } else if (lower.includes("tomate")) {
    emoji = "🍅";
    bgColor = "bg-amber-500";
  } else if (lower.includes("viña") || lower.includes("vid")) {
    emoji = "🍇";
    bgColor = "bg-blue-800";
  }

  return L.divIcon({
    className: "custom-leaflet-icon",
    html: `<div style="display: flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 50%; border: 2px solid white; box-shadow: 0 4px 6px rgba(0,0,0,0.3);" class="${bgColor}"><span style="font-size: 16px;">${emoji}</span></div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -18],
  });
}

const draftIcon = L.divIcon({
  className: "custom-leaflet-icon-draft",
  html: `<div style="display: flex; align-items: center; justify-content: center; width: 38px; height: 38px; border-radius: 50%; border: 2px solid white; box-shadow: 0 4px 12px rgba(220,38,38,0.6);" class="bg-red-600 text-white font-bold animate-bounce">📍</div>`,
  iconSize: [38, 38],
  iconAnchor: [19, 19],
  popupAnchor: [0, -18],
});

function MapFlyTo({
  position,
}: {
  position: { lat: number; lon: number } | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (position && isValidCoord(position.lat, position.lon)) {
      map.flyTo([position.lat, position.lon], 12, { duration: 1.2 });
    }
  }, [position, map]);
  return null;
}

function MapClickListener({
  isPicking,
  onPick,
}: {
  isPicking: boolean;
  onPick: (lat: number, lon: number) => void;
}) {
  useMapEvents({
    click(e) {
      if (isPicking) {
        onPick(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
}

function CultivosMap({
  crops,
  onSelect,
  targetPos,
  isCreating,
  onLocationPick,
}: any) {
  const [isClient, setIsClient] = useState(false);
  useEffect(() => setIsClient(true), []);

  if (!isClient) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-slate-500 bg-slate-50">
        Cargando mapa...
      </div>
    );
  }

  const isValidTarget = targetPos && isValidCoord(targetPos.lat, targetPos.lon);

  return (
    <MapContainer
      center={[28.2916, -16.6291]}
      zoom={8}
      minZoom={7}
      maxZoom={13}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {isValidTarget && <MapFlyTo position={targetPos} />}
      <MapClickListener isPicking={isCreating} onPick={onLocationPick} />

      {isCreating && isValidTarget && (
        <Marker position={[targetPos.lat, targetPos.lon]} icon={draftIcon}>
          <Popup>
            <b>Ubicación Seleccionada</b>
            <br />
            Lat: {targetPos.lat.toFixed(4)}
            <br />
            Lon: {targetPos.lon.toFixed(4)}
          </Popup>
        </Marker>
      )}

      {crops
        .filter((c: Crop) => c && isValidCoord(c.lat, c.lon))
        .map((crop: Crop, idx: number) => (
          <Marker
            key={crop.id || `crop-${idx}`}
            position={[crop.lat, crop.lon]}
            icon={getCustomIcon(crop.cultivo)}
            eventHandlers={{ click: () => onSelect(crop) }}
          >
            <Popup>
              <b className="text-blue-900">{crop.nombre}</b>
              <br />
              {crop.cultivo} ({crop.isla})
            </Popup>
          </Marker>
        ))}
    </MapContainer>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-white rounded-xl p-4 shadow border border-blue-100">
      <p className="text-blue-700/80 text-sm">{title}</p>
      <p className="text-xl font-bold text-slate-800">{value}</p>
    </div>
  );
}

export default function FincasPage() {
  const [crops, setCrops] = useState<Crop[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [selected, setSelected] = useState<Crop | null>(null);
  const [loading, setLoading] = useState(true);

  const [isCreating, setIsCreating] = useState(false);
  const [createModeTab, setCreateModeTab] = useState<"form" | "json">("form");
  const [jsonInput, setJsonInput] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [formData, setFormData] = useState<Omit<Crop, "id">>({
    nombre: "",
    cultivo: "Plátano",
    isla: "Tenerife",
    lat: 28.3901,
    lon: -16.5222,
    temperatura: 22.0,
    humedad: 65.0,
    lluvia: 0.0,
    viento: 12.0,
    ndvi: 0.75,
    sentinel_tile: "T28RCS",
  });

  useEffect(() => {
    if (createModeTab === "form") {
      setJsonInput(JSON.stringify(formData, null, 2));
    }
  }, [formData, createModeTab]);

  async function fetchCultivos(isInitial: boolean) {
    try {
      const response = await fetch("http://localhost:8000/api/v1/crops/", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
          "Content-Type": "application/json",
        },
      });
      if (response.ok) {
        const result = await response.json();
        // Adaptado al nuevo formato del endpoint GET: { status: "success", data: [...] }
        const dataList: Crop[] = Array.isArray(result)
          ? result
          : result.data || [];
        setCrops(dataList);
        if (isInitial && dataList.length > 0) setSelected(dataList[0]);
      }
    } catch (error) {
      console.error("Error al obtener datos:", error);
    } finally {
      if (isInitial) setLoading(false);
    }
  }

  useEffect(() => {
    fetchCultivos(true);
  }, []);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "number" ? parseFloat(value) || 0 : value,
    }));
  };

  const handleLocationPicked = (lat: number, lon: number) => {
    setFormData((prev) => ({
      ...prev,
      lat: parseFloat(lat.toFixed(6)),
      lon: parseFloat(lon.toFixed(6)),
    }));
  };

  const handleJsonChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setJsonInput(val);
    try {
      const parsed = JSON.parse(val);
      if (
        typeof parsed === "object" &&
        parsed !== null &&
        !Array.isArray(parsed)
      ) {
        setFormData((prev) => ({ ...prev, ...parsed }));
        setFormError(null);
      }
    } catch (err) {
      // Ignorar errores parciales mientras escribe
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        const parsed = JSON.parse(content);
        setJsonInput(JSON.stringify(parsed, null, 2));
        setFormError(null);
      } catch (err) {
        setFormError("El archivo seleccionado no contiene un JSON válido.");
      }
    };
    reader.readAsText(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);

    let payload: any = formData;
    if (createModeTab === "json") {
      try {
        payload = JSON.parse(jsonInput);
      } catch (err) {
        setFormError("El formato JSON no es válido.");
        setSubmitting(false);
        return;
      }
    }

    // Validar coordenadas tanto si es un objeto único como un array de cultivos
    const itemsToValidate = Array.isArray(payload) ? payload : [payload];
    for (const item of itemsToValidate) {
      if (!isValidCoord(item.lat, item.lon)) {
        setFormError(
          `Coordenadas no válidas para la finca: ${item.nombre || "Sin nombre"}`,
        );
        setSubmitting(false);
        return;
      }
    }

    try {
      const response = await fetch("http://localhost:8000/api/v1/crops/", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Error al registrar");

      // Refrescamos los cultivos desde la base de datos para sincronizar con el backend y el user_id
      await fetchCultivos(false);
      setIsCreating(false);
      setFormData((prev) => ({ ...prev, nombre: "" }));
    } catch (err: any) {
      setFormError(err.message || "Error de conexión con el servidor");
    } finally {
      setSubmitting(false);
    }
  };

  const tiposDisponibles = Array.from(new Set(crops.map((c) => c.cultivo)));
  const filteredCrops =
    selectedFilter === "ALL"
      ? crops
      : crops.filter((c) => c.cultivo === selectedFilter);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 text-blue-900 font-medium">
        Cargando mapa...
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between shadow-sm shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold">
            🌴
          </div>
          <h1 className="text-lg font-bold text-slate-800">
            Gestión de Fincas en Canarias
          </h1>
        </div>
        <button
          onClick={() => setIsCreating(!isCreating)}
          className={`font-medium text-sm px-4 py-2 rounded-xl shadow transition cursor-pointer ${
            isCreating
              ? "bg-slate-200 text-slate-700 hover:bg-slate-300"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {isCreating ? "✕ Cancelar Creación" : "➕ Nueva Finca"}
        </button>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 p-4 overflow-hidden">
        {/* Mapa a la izquierda */}
        <div className="lg:col-span-8 h-[350px] lg:h-full rounded-2xl overflow-hidden border bg-white shadow-md relative">
          {isCreating && (
            <div className="absolute top-3 left-3 z-[1000] bg-red-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-2 pointer-events-none animate-pulse">
              <span>📍 Haz clic en el mapa para posicionar la finca</span>
            </div>
          )}
          <CultivosMap
            crops={filteredCrops}
            onSelect={setSelected}
            targetPos={{ lat: formData.lat, lon: formData.lon }}
            isCreating={isCreating}
            onLocationPick={handleLocationPicked}
          />
        </div>

        {/* Panel derecho */}
        <div className="lg:col-span-4 bg-white rounded-2xl p-6 shadow-md border space-y-6 flex flex-col overflow-y-auto">
          {isCreating ? (
            <form
              onSubmit={handleSubmit}
              className="space-y-4 flex-1 flex flex-col justify-between"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b pb-3">
                  <h2 className="text-lg font-bold text-slate-800">
                    Registrar Finca(s)
                  </h2>
                  <div className="flex bg-slate-100 p-1 rounded-lg text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => setCreateModeTab("form")}
                      className={`px-2.5 py-1 rounded-md transition ${createModeTab === "form" ? "bg-white text-blue-600 shadow-sm" : "text-slate-600"}`}
                    >
                      Formulario
                    </button>
                    <button
                      type="button"
                      onClick={() => setCreateModeTab("json")}
                      className={`px-2.5 py-1 rounded-md transition ${createModeTab === "json" ? "bg-white text-blue-600 shadow-sm" : "text-slate-600"}`}
                    >
                      JSON / Archivo
                    </button>
                  </div>
                </div>

                {formError && (
                  <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg">
                    {formError}
                  </div>
                )}

                {createModeTab === "form" ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Nombre de la Finca *
                      </label>
                      <input
                        type="text"
                        name="nombre"
                        required
                        placeholder="Ej: Finca Los Llanos"
                        value={formData.nombre}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border rounded-lg text-sm"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Tipo de Cultivo *
                        </label>
                        <input
                          type="text"
                          name="cultivo"
                          required
                          placeholder="Ej: Plátano"
                          value={formData.cultivo}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Isla *
                        </label>
                        <select
                          name="isla"
                          value={formData.isla}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border rounded-lg text-sm"
                        >
                          {ISLAS_CANARIAS.map((isla) => (
                            <option key={isla} value={isla}>
                              {isla}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 p-3 bg-blue-50/60 rounded-xl border border-blue-100">
                      <div>
                        <label className="block text-[11px] font-bold text-blue-900 mb-1">
                          Latitud (Clic en mapa)
                        </label>
                        <input
                          type="number"
                          step="any"
                          name="lat"
                          required
                          value={formData.lat}
                          onChange={handleInputChange}
                          className="w-full px-2 py-1.5 border rounded text-xs bg-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-bold text-blue-900 mb-1">
                          Longitud (Clic en mapa)
                        </label>
                        <input
                          type="number"
                          step="any"
                          name="lon"
                          required
                          value={formData.lon}
                          onChange={handleInputChange}
                          className="w-full px-2 py-1.5 border rounded text-xs bg-white font-mono"
                        />
                      </div>
                    </div>

                    <div>
                      <button
                        type="button"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer"
                      >
                        {showAdvanced
                          ? "▾ Ocultar datos climáticos avanzados"
                          : "▸ Añadir datos climáticos avanzados (opcional)"}
                      </button>
                      {showAdvanced && (
                        <div className="grid grid-cols-2 gap-3 mt-3 p-3 bg-slate-50 rounded-xl border">
                          <div>
                            <label className="block text-[11px] font-medium text-slate-600 mb-1">
                              Temperatura (°C)
                            </label>
                            <input
                              type="number"
                              step="any"
                              name="temperatura"
                              value={formData.temperatura}
                              onChange={handleInputChange}
                              className="w-full px-2 py-1 border rounded text-xs bg-white"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-medium text-slate-600 mb-1">
                              Humedad (%)
                            </label>
                            <input
                              type="number"
                              step="any"
                              name="humedad"
                              value={formData.humedad}
                              onChange={handleInputChange}
                              className="w-full px-2 py-1 border rounded text-xs bg-white"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-medium text-slate-600 mb-1">
                              Lluvia (mm)
                            </label>
                            <input
                              type="number"
                              step="any"
                              name="lluvia"
                              value={formData.lluvia}
                              onChange={handleInputChange}
                              className="w-full px-2 py-1 border rounded text-xs bg-white"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-medium text-slate-600 mb-1">
                              Viento (km/h)
                            </label>
                            <input
                              type="number"
                              step="any"
                              name="viento"
                              value={formData.viento}
                              onChange={handleInputChange}
                              className="w-full px-2 py-1 border rounded text-xs bg-white"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex flex-col gap-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        Subir archivo JSON (Carga masiva o individual):
                      </label>
                      <input
                        type="file"
                        accept=".json"
                        onChange={handleFileUpload}
                        className="text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                      />
                    </div>
                    <p className="text-[11px] text-slate-500">
                      O edita el código JSON directamente abajo:
                    </p>
                    <textarea
                      rows={10}
                      value={jsonInput}
                      onChange={handleJsonChange}
                      className="w-full p-3 font-mono text-xs border rounded-xl bg-slate-900 text-emerald-400"
                    />
                  </div>
                )}
              </div>

              <div className="flex gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="w-1/2 px-4 py-2 text-sm text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg cursor-pointer font-medium"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-1/2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow cursor-pointer font-medium"
                >
                  {submitting ? "Guardando..." : "Guardar Finca(s)"}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-6 flex-1 flex flex-col">
              <div className="space-y-2">
                <label className="text-sm font-semibold text-blue-900">
                  Filtrar por tipo de cultivo:
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setSelectedFilter("ALL")}
                    className={`px-3 py-1.5 text-sm rounded-lg transition font-medium cursor-pointer ${selectedFilter === "ALL" ? "bg-blue-600 text-white" : "bg-blue-50 text-blue-700"}`}
                  >
                    Todas
                  </button>
                  {tiposDisponibles.map((tipo) => (
                    <button
                      key={tipo}
                      onClick={() => setSelectedFilter(tipo)}
                      className={`px-3 py-1.5 text-sm rounded-lg transition font-medium cursor-pointer ${selectedFilter === tipo ? "bg-blue-600 text-white" : "bg-blue-50 text-blue-700"}`}
                    >
                      {tipo}
                    </button>
                  ))}
                </div>
              </div>

              <hr className="border-blue-100" />

              <h2 className="text-xl font-bold text-slate-800">
                Detalle de la Finca
              </h2>
              {selected ? (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-blue-700">
                      {selected.nombre}
                    </h3>
                    <p className="text-slate-600 text-sm">
                      Cultivo: <b>{selected.cultivo}</b> | Isla:{" "}
                      <b>{selected.isla}</b>
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Card
                      title="Temperatura"
                      value={`${selected.temperatura} °C`}
                    />
                    <Card title="Humedad" value={`${selected.humedad}%`} />
                    <Card title="Lluvia" value={`${selected.lluvia} mm`} />
                    <Card title="Viento" value={`${selected.viento} km/h`} />
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  Selecciona una finca en el mapa.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
