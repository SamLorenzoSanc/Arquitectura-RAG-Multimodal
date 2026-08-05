"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Limpieza para evitar errores con los iconos predeterminados de Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

interface Crop {
  id: string;
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

// -----------------------------
// Generador de Iconos Dinámicos por Cultivo
// -----------------------------
function getCustomIcon(cultivo: string) {
  let emoji = "🌱";
  let bgColor = "bg-green-600";

  // Personaliza los emojis y colores según los cultivos de tu base de datos
  const lowerCultivo = cultivo.toLowerCase();
  if (lowerCultivo.includes("plátano") || lowerCultivo.includes("platano")) {
    emoji = "🍌";
    bgColor = "bg-yellow-500";
  } else if (lowerCultivo.includes("aguacate")) {
    emoji = "🥑";
    bgColor = "bg-emerald-600";
  } else if (lowerCultivo.includes("tomate")) {
    emoji = "🍅";
    bgColor = "bg-red-500";
  } else if (lowerCultivo.includes("viña") || lowerCultivo.includes("vid")) {
    emoji = "🍇";
    bgColor = "bg-purple-600";
  }

  return L.divIcon({
    className: "custom-leaflet-icon",
    html: `
      <div style="display: flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 50%; border: 2px solid white; box-shadow: 0 4px 6px rgba(0,0,0,0.3);" class="${bgColor}">
        <span style="font-size: 16px;">${emoji}</span>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -18],
  });
}

// -----------------------------
// Componente de Mapa Leaflet
// -----------------------------
function CultivosMap({
  crops,
  selected,
  onSelect,
}: {
  crops: Crop[];
  selected: Crop | null;
  onSelect: (c: Crop) => void;
}) {
  return (
    <MapContainer
      center={[28.2916, -16.6291]} 
      zoom={8}                     
      minZoom={7}                  
      maxZoom={13}                
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

      {crops.map((crop) => (
        <Marker
          key={crop.id}
          position={[crop.lat, crop.lon]}
          icon={getCustomIcon(crop.cultivo)} // <-- Asignamos el icono dinámico aquí
          eventHandlers={{
            click: () => onSelect(crop),
          }}
        >
          <Popup>
            <b>{crop.nombre}</b>
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
    <div className="bg-white rounded-xl p-4 shadow border">
      <p className="text-gray-500 text-sm">{title}</p>
      <p className="text-xl font-bold">{value}</p>
    </div>
  );
}

// -----------------------------
// Página Principal con Carga Automática
// -----------------------------
export default function Page() {
  const [crops, setCrops] = useState<Crop[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [selected, setSelected] = useState<Crop | null>(null);
  const [loading, setLoading] = useState(true);

  async function fetchCultivos(isInitial: boolean) {
    try {
      const response = await fetch("http://localhost:8000/map/cultivos", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
        },
      });

      if (response.ok) {
        const data: Crop[] = await response.json();
        setCrops(data);

        if (isInitial && data.length > 0) {
          setSelected(data[0]);
        } else if (selected) {
          const updatedSelected = data.find((c) => c.id === selected.id);
          if (updatedSelected) setSelected(updatedSelected);
        }
      }
    } catch (error) {
      console.error("Error al actualizar los cultivos automáticamente:", error);
    } finally {
      if (isInitial) setLoading(false);
    }
  }

  useEffect(() => {
    fetchCultivos(true);

    const intervalTimer = setInterval(() => {
      fetchCultivos(false);
    }, 300000);

    return () => clearInterval(intervalTimer);
  }, []);

  const tiposDisponibles = Array.from(new Set(crops.map((c) => c.cultivo)));

  const filteredCrops =
    selectedFilter === "ALL"
      ? crops
      : crops.filter((c) => c.cultivo === selectedFilter);

  if (loading)
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50 text-lg font-medium">
        Cargando mapa automatizado de Canarias...
      </div>
    );

  return (
    <div className="h-screen grid grid-cols-1 lg:grid-cols-12 gap-4 p-4 bg-gray-100">
      {/* MAPA AUTOMÁTICO (Izquierda - 8 columnas) */}
      <div className="lg:col-span-8 h-[400px] lg:h-full rounded-2xl overflow-hidden border bg-white shadow">
        <CultivosMap
          crops={filteredCrops}
          selected={selected}
          onSelect={setSelected}
        />
      </div>

      {/* PANEL DE FILTROS Y DATOS EN TIEMPO REAL (Derecha - 4 columnas) */}
      <div className="lg:col-span-4 bg-white rounded-2xl p-6 shadow space-y-6 flex flex-col overflow-y-auto">
        <h1 className="text-2xl font-bold">Monitoreo de Cultivos</h1>

        <div className="space-y-2">
          <label className="text-sm font-semibold text-gray-600">
            Filtrar por tipo de cultivo:
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedFilter("ALL")}
              className={`px-3 py-1.5 text-sm rounded-lg transition ${
                selectedFilter === "ALL"
                  ? "bg-green-600 text-white font-semibold"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
            >
              Todos
            </button>
            {tiposDisponibles.map((tipo) => (
              <button
                key={tipo}
                onClick={() => setSelectedFilter(tipo)}
                className={`px-3 py-1.5 text-sm rounded-lg transition ${
                  selectedFilter === tipo
                    ? "bg-green-600 text-white font-semibold"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
              >
                {tipo}
              </button>
            ))}
          </div>
        </div>

        <hr />

        <h2 className="text-xl font-bold">Información parcela</h2>
        {selected ? (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-green-700">
                {selected.nombre}
              </h3>
              <p className="text-gray-600 text-sm">
                Cultivo: <b>{selected.cultivo}</b> | Isla: <b>{selected.isla}</b>
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Card title="Temperatura" value={`${selected.temperatura} °C`} />
              <Card title="Humedad" value={`${selected.humedad}%`} />
              <Card title="Lluvia" value={`${selected.lluvia} mm`} />
              <Card title="Viento" value={`${selected.viento} km/h`} />
            </div>

            <div>
              <div className="flex justify-between text-sm font-medium">
                <span>Índice NDVI (Sentinel)</span>
                <span>{selected.ndvi}</span>
              </div>
              <div className="w-full h-3 bg-gray-200 rounded mt-1 overflow-hidden">
                <div
                  className="h-3 bg-green-600 transition-all duration-500"
                  style={{ width: `${selected.ndvi * 100}%` }}
                />
              </div>
            </div>

            <div className="text-xs text-gray-400 pt-2">
              * Sincronización automática activa cada 5 minutos con FastAPI.
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            Selecciona un marcador en el mapa para ver sus métricas automatizadas.
          </p>
        )}
      </div>
    </div>
  );
}