"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import L from "leaflet";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  AlertTriangle,
  Apple,
  Info,
  Loader2,
  MapPin,
  Navigation,
  Play,
  RotateCcw,
  Truck,
} from "lucide-react";
import RecogidaService, {
  type GeoPoint,
  type GeoRutaResult,
} from "@/services/recogida.service";
import {
  useRecogidaMapa,
  useRefreshRecogidaMapa,
} from "@/hooks/useCachedApi";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

type EditMode = "cooperativa" | "parada";

function explainRoutingError(message: string): {
  title: string;
  tips: string[];
} {
  const lower = message.toLowerCase();
  if (lower.includes("desconectada") || lower.includes("no hay camino")) {
    return {
      title: "Red viaria desconectada entre paradas",
      tips: [
        "A* solo usa carreteras del grafo (líneas grises). No puede ir campo a través.",
        "Dos paradas pueden estar cerca en el mapa pero en tramos sin enlace en la red cargada.",
        "Si la fuente es «fallback», la red es simplificada: acerca las paradas a la misma vía continua.",
        "Sitúa cooperativa y recogidas sobre/cerca de la misma carretera gris y vuelve a calcular.",
        "También puedes quitar una parada conflictiva o pulsar Reiniciar para recargar la red.",
      ],
    };
  }
  if (lower.includes("fuera de la red") || lower.includes("está a")) {
    return {
      title: "Punto demasiado lejos de una carretera",
      tips: [
        "Cada clic se acopla al nodo de carretera más cercano (máx. ~800 m).",
        "Si marcas dentro de una finca lejos de la vía, el acoplado falla.",
        "Mueve el marcador más cerca de una línea gris del mapa.",
      ],
    };
  }
  return {
    title: "No se pudo calcular la ruta",
    tips: [
      "Revisa que haya cooperativa y al menos una parada.",
      "Las paradas deben estar cerca de carreteras visibles en el mapa.",
    ],
  };
}

function makeIcon(emoji: string, bg: string) {
  return L.divIcon({
    className: "geo-recogida-icon",
    html: `<div style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;border:2px solid white;box-shadow:0 3px 8px rgba(0,0,0,.35);background:${bg};font-size:16px">${emoji}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

const coopIcon = makeIcon("🚛", "#1d4ed8");
const stopIcon = makeIcon("🍌", "#d97706");

function ClickHandler({
  mode,
  onCoop,
  onStop,
}: {
  mode: EditMode;
  onCoop: (p: GeoPoint) => void;
  onStop: (p: GeoPoint) => void;
}) {
  useMapEvents({
    click(e) {
      const p = { lat: e.latlng.lat, lon: e.latlng.lng };
      if (mode === "cooperativa") onCoop(p);
      else onStop(p);
    },
  });
  return null;
}

export default function RecogidaPage() {
  const {
    data: mapaCached,
    isLoading: loadingMapa,
    error: mapaError,
  } = useRecogidaMapa();
  const refreshMapa = useRefreshRecogidaMapa();

  const mapa = mapaCached ?? null;
  const [cooperativa, setCooperativa] = useState<GeoPoint | null>(null);
  const [paradas, setParadas] = useState<GeoPoint[]>([]);
  const [mode, setMode] = useState<EditMode>("parada");
  const [returnToStart, setReturnToStart] = useState(true);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GeoRutaResult | null>(null);

  const loading = loadingMapa || refreshMapa.isPending;

  useEffect(() => {
    if (mapa && !cooperativa) {
      setCooperativa({
        lat: mapa.cooperativa.lat,
        lon: mapa.cooperativa.lon,
      });
    }
  }, [mapa, cooperativa]);

  useEffect(() => {
    if (mapaError) {
      setError(
        (mapaError as any)?.response?.data?.detail ||
          (mapaError as Error).message ||
          "No se pudo cargar el mapa de La Palma",
      );
    }
  }, [mapaError]);

  const loadMapa = useCallback(
    async (refresh = false) => {
      setError(null);
      setResult(null);
      setParadas([]);
      try {
        if (refresh) {
          const data = await refreshMapa.mutateAsync();
          setCooperativa({
            lat: data.cooperativa.lat,
            lon: data.cooperativa.lon,
          });
        }
      } catch (err: any) {
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            "No se pudo cargar el mapa de La Palma",
        );
      }
    },
    [refreshMapa],
  );

  const routeLatLngs = useMemo(() => {
    return (result?.full_path ?? []).map(
      (p) => [p[0], p[1]] as [number, number],
    );
  }, [result]);

  const roadLatLngs = useMemo(() => {
    return (mapa?.roads ?? []).map((line) =>
      line.map((p) => [p[0], p[1]] as [number, number]),
    );
  }, [mapa]);

  const onAddStop = (p: GeoPoint) => {
    setResult(null);
    setParadas((prev) => [...prev, p]);
  };

  const onSetCoop = (p: GeoPoint) => {
    setResult(null);
    setCooperativa(p);
  };

  const calcular = async () => {
    if (!cooperativa) {
      setError("Fija primero la cooperativa (camión)");
      return;
    }
    if (paradas.length === 0) {
      setError("Añade al menos un punto de recogida sobre/cerca de una carretera");
      return;
    }
    setComputing(true);
    setError(null);
    try {
      const data = await RecogidaService.calcularRutaGeo({
        start: cooperativa,
        stops: paradas,
        return_to_start: returnToStart,
        max_snap_m: 800,
      });
      setResult(data);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : err?.message || "Error al calcular la ruta A*",
      );
    } finally {
      setComputing(false);
    }
  };

  const center = mapa?.center ?? { lat: 28.66, lon: -17.86 };
  const errorHelp = error ? explainRoutingError(error) : null;

  return (
    <div className="space-y-5">
      <header className="rounded-2xl border border-amber-200/80 bg-white px-5 py-5 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-amber-700">
              La Palma · A* sobre carreteras
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              Planificador de recogida
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              {mapa?.description ||
                "El camión parte de la cooperativa y solo puede circular por carreteras. Fuera de la vía es obstáculo."}
            </p>
            <ol className="mt-3 list-decimal space-y-1 pl-5 text-xs text-slate-500">
              <li>
                Modo <strong>Cooperativa</strong>: clic en el mapa para situar el
                camión.
              </li>
              <li>
                Modo <strong>Recogida</strong>: clic para marcar fincas/paradas
                (cerca de carretera).
              </li>
              <li>
                Pulsa <strong>Calcular ruta A*</strong>: el camino sigue solo la
                red viaria.
              </li>
            </ol>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void loadMapa(false)}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <RotateCcw size={15} />
              Reiniciar
            </button>
            <button
              type="button"
              onClick={() => void calcular()}
              disabled={computing || loading || !cooperativa || paradas.length === 0}
              className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
            >
              {computing ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <Play size={15} />
              )}
              Calcular ruta A*
            </button>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Info size={16} className="text-slate-600" />
            Restricciones del problema (A* geográfico)
          </h2>
          <ul className="mt-2 grid gap-1.5 text-xs text-slate-600 sm:grid-cols-2">
            <li>
              <strong>Solo carreteras:</strong> el grafo son vías OSM/respaldo;
              salirse de la carretera es obstáculo (no hay aristas).
            </li>
            <li>
              <strong>Acoplado:</strong> cada punto se proyecta al nodo viario
              más cercano (máx. ~800 m).
            </li>
            <li>
              <strong>Conectividad:</strong> debe existir un camino continuo
              entre cooperativa y paradas; si no, error de red desconectada.
            </li>
            <li>
              <strong>Orden de visita:</strong> nearest-neighbor + A* por
              tramos (no garantiza el óptimo global TSP).
            </li>
          </ul>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3">
            <button
              type="button"
              onClick={() => setMode("cooperativa")}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold ${
                mode === "cooperativa"
                  ? "border-blue-300 bg-blue-50 text-blue-800"
                  : "border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              <Truck size={14} />
              Cooperativa / camión
            </button>
            <button
              type="button"
              onClick={() => setMode("parada")}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold ${
                mode === "parada"
                  ? "border-amber-300 bg-amber-50 text-amber-800"
                  : "border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              <Apple size={14} />
              Punto de recogida
            </button>
            <label className="ml-auto inline-flex items-center gap-2 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={returnToStart}
                onChange={(e) => setReturnToStart(e.target.checked)}
                className="rounded border-slate-300"
              />
              Volver a la cooperativa
            </label>
          </div>

          <div className="relative h-[520px] w-full bg-slate-100">
            {loading ? (
              <div className="flex h-full items-center justify-center text-slate-500">
                <Loader2 className="mr-2 animate-spin" size={18} />
                Cargando red viaria de La Palma…
              </div>
            ) : (
              <MapContainer
                center={[center.lat, center.lon]}
                zoom={11}
                minZoom={10}
                maxZoom={16}
                style={{ height: "100%", width: "100%" }}
                maxBounds={[
                  [mapa?.bbox.south ?? 28.4, mapa?.bbox.west ?? -18.05],
                  [mapa?.bbox.north ?? 28.9, mapa?.bbox.east ?? -17.65],
                ]}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <ClickHandler
                  mode={mode}
                  onCoop={onSetCoop}
                  onStop={onAddStop}
                />

                {roadLatLngs.slice(0, 600).map((line, i) => (
                  <Polyline
                    key={`road-${i}`}
                    positions={line}
                    pathOptions={{
                      color: "#94a3b8",
                      weight: 2,
                      opacity: 0.55,
                    }}
                  />
                ))}

                {routeLatLngs.length > 1 ? (
                  <Polyline
                    positions={routeLatLngs}
                    pathOptions={{
                      color: "#0284c7",
                      weight: 5,
                      opacity: 0.95,
                    }}
                  />
                ) : null}

                {cooperativa ? (
                  <Marker
                    position={[cooperativa.lat, cooperativa.lon]}
                    icon={coopIcon}
                  >
                    <Popup>
                      Cooperativa / camión
                      <br />
                      {cooperativa.lat.toFixed(5)}, {cooperativa.lon.toFixed(5)}
                    </Popup>
                  </Marker>
                ) : null}

                {paradas.map((p, i) => (
                  <Marker
                    key={`stop-${i}`}
                    position={[p.lat, p.lon]}
                    icon={stopIcon}
                    eventHandlers={{
                      click: () => {
                        setParadas((prev) =>
                          prev.filter((_, idx) => idx !== i),
                        );
                        setResult(null);
                      },
                    }}
                  >
                    <Popup>
                      Recogida #{i + 1}
                      <br />
                      Clic para eliminar
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            )}
          </div>

          {error && errorHelp ? (
            <div className="m-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              <p className="flex items-start gap-2 font-semibold">
                <AlertTriangle size={16} className="mt-0.5 shrink-0" />
                {errorHelp.title}
              </p>
              <p className="mt-2 text-xs leading-relaxed text-red-700/90">
                {error}
              </p>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-red-700">
                {errorHelp.tips.map((tip) => (
                  <li key={tip}>{tip}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Navigation size={16} className="text-amber-600" />
              Resultado A*
            </h2>
            {result?.found ? (
              <dl className="mt-3 space-y-2 text-sm text-slate-700">
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">Paradas</dt>
                  <dd className="font-semibold">{result.stops}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">Distancia</dt>
                  <dd className="font-semibold">{result.total_cost_km} km</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">Nodos expandidos</dt>
                  <dd className="font-semibold">{result.nodes_expanded}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">Red</dt>
                  <dd className="font-semibold uppercase">{result.graph_source}</dd>
                </div>
                <p className="pt-1 text-xs text-slate-500">{result.message}</p>
              </dl>
            ) : (
              <p className="mt-3 text-sm text-slate-500">
                Sitúa la cooperativa y las paradas, luego calcula la ruta por
                carretera.
              </p>
            )}
          </div>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-4 text-sm text-slate-700">
            <h3 className="font-bold text-slate-900">
              ¿Qué significa «red desconectada»?
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-600">
              El algoritmo A* busca un camino en un grafo. Si entre la
              cooperativa y una parada (o entre dos paradas) no hay secuencia
              de carreteras conectadas en la red cargada, no existe solución y
              aparece ese error. No es un bug de A*: es una restricción del
              modelo (solo vías, sin atajos fuera de carretera).
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
            <h3 className="font-bold text-slate-900">Leyenda</h3>
            <ul className="mt-2 space-y-1.5">
              <li className="flex items-center gap-2">
                <MapPin size={14} className="text-blue-700" /> Cooperativa /
                camión
              </li>
              <li>🍌 Punto de recogida</li>
              <li>
                <span className="inline-block h-2 w-6 rounded bg-slate-400 align-middle" />{" "}
                Carreteras (únicas transitables)
              </li>
              <li>
                <span className="inline-block h-2 w-6 rounded bg-sky-600 align-middle" />{" "}
                Ruta A*
              </li>
            </ul>
            {mapa ? (
              <p className="mt-2 text-[11px] text-slate-400">
                Grafo: {mapa.nodes} nodos · fuente {mapa.source}
                {mapa.source === "fallback"
                  ? " (simplificada; cobertura limitada)"
                  : ""}
              </p>
            ) : null}
          </div>

          {paradas.length > 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-bold text-slate-900">
                Paradas ({paradas.length})
              </h3>
              <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto text-xs text-slate-600">
                {paradas.map((p, i) => (
                  <li key={`${p.lat}-${p.lon}-${i}`}>
                    #{i + 1}: {p.lat.toFixed(4)}, {p.lon.toFixed(4)}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => {
                  setParadas([]);
                  setResult(null);
                }}
                className="mt-3 text-xs font-semibold text-amber-700 hover:underline"
              >
                Borrar todas las paradas
              </button>
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
