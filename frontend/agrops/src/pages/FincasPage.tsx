"use client";

import React, { useEffect, useMemo, useState } from "react";
import L from "leaflet";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polygon,
  Polyline,
  CircleMarker,
  useMap,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  useCrops,
  useCreateCrops,
  useCreateTreatment,
  useDeleteCrop,
  useUpdateCrop,
  type CropFinca,
} from "@/hooks/useCachedApi";
import { useOrganization } from "@/context/OrganizationContext";
import {
  areaHaFromRing,
  boundsFromRing,
  centroidFromRing,
  distanceMeters,
  geoJsonFromRing,
  ringFromGeoJson,
  type LatLngTuple,
} from "@/lib/parcelGeometry";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

type Crop = CropFinca;

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

/** Clic cerca del 1.er vértice = cerrar polígono (~12 m). */
const CLOSE_SNAP_METERS = 12;

const isValidCoord = (lat: any, lon: any): boolean =>
  typeof lat === "number" &&
  typeof lon === "number" &&
  !isNaN(lat) &&
  !isNaN(lon) &&
  lat >= -90 &&
  lat <= 90 &&
  lon >= -180 &&
  lon <= 180;

function MapFitBounds({
  bounds,
  active,
}: {
  bounds: [[number, number], [number, number]] | null;
  active: boolean;
}) {
  const map = useMap();
  useEffect(() => {
    if (!active || !bounds) return;
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 17, animate: true });
  }, [bounds, active, map]);
  return null;
}

function MapDrawInteraction({
  enabled,
  draftRing,
  onAddVertex,
  onClosePolygon,
  setCursor,
}: {
  enabled: boolean;
  draftRing: LatLngTuple[];
  onAddVertex: (lat: number, lon: number) => void;
  onClosePolygon: () => void;
  setCursor: (p: LatLngTuple | null) => void;
}) {
  useMapEvents({
    click(e) {
      if (!enabled) return;
      const pt: LatLngTuple = [e.latlng.lat, e.latlng.lng];
      if (
        draftRing.length >= 3 &&
        distanceMeters(pt, draftRing[0]) <= CLOSE_SNAP_METERS
      ) {
        onClosePolygon();
        return;
      }
      onAddVertex(pt[0], pt[1]);
    },
    dblclick(e) {
      if (!enabled) return;
      L.DomEvent.stop(e as any);
      if (draftRing.length >= 3) onClosePolygon();
    },
    mousemove(e) {
      if (!enabled) return;
      setCursor([e.latlng.lat, e.latlng.lng]);
    },
    mouseout() {
      setCursor(null);
    },
  });
  return null;
}

function CultivosMap({
  crops,
  onSelect,
  selectedId,
  draftRing,
  drawing,
  polygonClosed,
  onAddVertex,
  onClosePolygon,
  fitBounds,
}: {
  crops: Crop[];
  onSelect: (c: Crop) => void;
  selectedId?: string | null;
  draftRing: LatLngTuple[];
  drawing: boolean;
  polygonClosed: boolean;
  onAddVertex: (lat: number, lon: number) => void;
  onClosePolygon: () => void;
  fitBounds: [[number, number], [number, number]] | null;
}) {
  const [isClient, setIsClient] = useState(false);
  const [cursor, setCursor] = useState<LatLngTuple | null>(null);
  useEffect(() => setIsClient(true), []);

  if (!isClient) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-slate-500 bg-slate-50">
        Cargando mapa...
      </div>
    );
  }

  const rubberBand =
    drawing && !polygonClosed && draftRing.length > 0 && cursor
      ? ([...draftRing, cursor] as LatLngTuple[])
      : null;

  return (
    <MapContainer
      center={[28.2916, -16.6291]}
      zoom={8}
      minZoom={7}
      maxZoom={18}
      doubleClickZoom={!drawing}
      style={{ height: "100%", width: "100%", cursor: drawing ? "crosshair" : undefined }}
    >
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <MapFitBounds bounds={fitBounds} active={!drawing} />
      <MapDrawInteraction
        enabled={drawing && !polygonClosed}
        draftRing={draftRing}
        onAddVertex={onAddVertex}
        onClosePolygon={onClosePolygon}
        setCursor={setCursor}
      />

      {crops.map((crop, idx) => {
        const ring = ringFromGeoJson(crop.poligono);
        const selected = crop.id === selectedId;
        const hasPoly = ring.length >= 3;
        return (
          <React.Fragment key={crop.id || `crop-${idx}`}>
            {hasPoly && (
              <Polygon
                positions={ring}
                pathOptions={{
                  color: selected ? "#b45309" : "#1d4ed8",
                  weight: selected ? 4 : 2,
                  fillColor: selected ? "#f59e0b" : "#3b82f6",
                  fillOpacity: selected ? 0.45 : 0.28,
                }}
                eventHandlers={{
                  click: (e) => {
                    if (drawing) return;
                    L.DomEvent.stopPropagation(e);
                    onSelect(crop);
                  },
                }}
              >
                <Popup>
                  <b>{crop.nombre}</b>
                  <br />
                  {crop.parcela_codigo ? `${crop.parcela_codigo} · ` : ""}
                  {crop.cultivo} ({crop.isla})
                  <br />
                  {crop.superficie_ha != null
                    ? `${crop.superficie_ha} ha`
                    : ""}
                </Popup>
              </Polygon>
            )}
            {/* Solo marcador si NO hay polígono (legado) */}
            {!hasPoly && isValidCoord(crop.lat, crop.lon) && (
              <Marker
                position={[crop.lat, crop.lon]}
                eventHandlers={{
                  click: () => {
                    if (!drawing) onSelect(crop);
                  },
                }}
              >
                <Popup>
                  <b>{crop.nombre}</b> (sin polígono)
                </Popup>
              </Marker>
            )}
          </React.Fragment>
        );
      })}

      {rubberBand && rubberBand.length >= 2 && (
        <Polyline
          positions={rubberBand}
          pathOptions={{ color: "#dc2626", weight: 2, dashArray: "6 4" }}
        />
      )}
      {draftRing.length >= 3 && (
        <Polygon
          positions={draftRing}
          pathOptions={{
            color: polygonClosed ? "#059669" : "#dc2626",
            weight: 2,
            fillColor: polygonClosed ? "#10b981" : "#ef4444",
            fillOpacity: 0.25,
          }}
        />
      )}
      {draftRing.map((pt, i) => (
        <CircleMarker
          key={`v-${i}`}
          center={pt}
          radius={i === 0 ? 7 : 5}
          pathOptions={{
            color: "#fff",
            fillColor: i === 0 ? "#059669" : "#dc2626",
            fillOpacity: 1,
            weight: 2,
          }}
        />
      ))}
    </MapContainer>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-white rounded-xl p-4 shadow border border-blue-100">
      <p className="text-blue-700/80 text-sm">{title}</p>
      <p className="text-xl font-bold text-slate-800 break-words">{value}</p>
    </div>
  );
}

export default function FincasPage() {
  const { selectedOrg } = useOrganization();
  const { data: cropsData, isLoading: loading, isFetching } = useCrops(true);
  const createCropsMutation = useCreateCrops();
  const updateCropMutation = useUpdateCrop();
  const createTreatmentMutation = useCreateTreatment();
  const deleteCropMutation = useDeleteCrop();
  const crops = cropsData ?? [];

  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [selected, setSelected] = useState<Crop | null>(null);

  const [isCreating, setIsCreating] = useState(false);
  const [isEditingPolygon, setIsEditingPolygon] = useState(false);
  const [createModeTab, setCreateModeTab] = useState<"form" | "json">("form");
  const [jsonInput, setJsonInput] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [draftRing, setDraftRing] = useState<LatLngTuple[]>([]);
  const [polygonClosed, setPolygonClosed] = useState(false);
  const [treatmentForm, setTreatmentForm] = useState({
    fecha: new Date().toISOString().slice(0, 10),
    producto: "",
    materia_activa: "",
    dosis: "",
    plaga_objetivo: "",
    carencia_dias: 7,
    observaciones: "",
  });

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
    organization_id: undefined,
    ref_catastral: "",
    superficie_ha: 1,
    variedad: "",
    sistema_riego: "Goteo",
    fuente_agua: "",
    dotacion_m3_ha_anio: undefined,
    comunidad_regantes: "",
    certificaciones: "",
    notas: "",
    parcela_codigo: "P-01",
    poligono: null,
  });

  const drawing = isCreating || isEditingPolygon;

  const draftStats = useMemo(() => {
    const area = areaHaFromRing(draftRing);
    const center = centroidFromRing(draftRing);
    return { area, center, vertices: draftRing.length };
  }, [draftRing]);

  const fitBounds = useMemo(() => {
    if (drawing && draftRing.length >= 2) {
      return boundsFromRing(draftRing);
    }
    if (selected) {
      const ring = ringFromGeoJson(selected.poligono);
      if (ring.length >= 3) return boundsFromRing(ring);
    }
    return null;
  }, [drawing, draftRing, selected]);

  const selectParcel = (crop: Crop) => {
    if (drawing) return;
    setSelected(crop);
  };

  useEffect(() => {
    if (createModeTab === "form") {
      setJsonInput(JSON.stringify(formData, null, 2));
    }
  }, [formData, createModeTab]);

  useEffect(() => {
    if (!crops.length) {
      setSelected(null);
      return;
    }
    setSelected((prev) => {
      if (!prev) return crops[0];
      return crops.find((c) => c.id === prev.id) || crops[0];
    });
  }, [crops]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]:
        type === "number"
          ? value === ""
            ? undefined
            : parseFloat(value) || 0
          : value,
    }));
  };

  const applyRingToForm = (ring: LatLngTuple[]) => {
    const poly = geoJsonFromRing(ring);
    const center = centroidFromRing(ring);
    const area = areaHaFromRing(ring);
    setFormData((prev) => ({
      ...prev,
      poligono: poly,
      lat: center?.lat ?? prev.lat,
      lon: center?.lon ?? prev.lon,
      superficie_ha: area ?? prev.superficie_ha,
    }));
  };

  const handleAddVertex = (lat: number, lon: number) => {
    if (polygonClosed) return;
    setDraftRing((prev) => {
      const next: LatLngTuple[] = [...prev, [lat, lon]];
      if (isCreating) applyRingToForm(next);
      return next;
    });
  };

  const closePolygon = () => {
    if (draftRing.length < 3) return;
    setPolygonClosed(true);
    if (isCreating) applyRingToForm(draftRing);
  };

  const undoVertex = () => {
    setPolygonClosed(false);
    setDraftRing((prev) => {
      const next = prev.slice(0, -1);
      if (isCreating) applyRingToForm(next);
      return next;
    });
  };

  const clearPolygon = () => {
    setDraftRing([]);
    setPolygonClosed(false);
    if (isCreating) {
      setFormData((prev) => ({ ...prev, poligono: null }));
    }
  };

  const startEditPolygon = () => {
    if (!selected) return;
    setIsCreating(false);
    setIsEditingPolygon(true);
    const ring = ringFromGeoJson(selected.poligono);
    setDraftRing(ring);
    setPolygonClosed(ring.length >= 3);
    setFormError(null);
  };

  const saveEditedPolygon = async () => {
    if (!selected?.id) return;
    if (draftRing.length < 3) {
      setFormError("El polígono necesita al menos 3 vértices.");
      return;
    }
    const poly = geoJsonFromRing(draftRing);
    const center = centroidFromRing(draftRing);
    const area = areaHaFromRing(draftRing);
    setSubmitting(true);
    setFormError(null);
    try {
      await updateCropMutation.mutateAsync({
        id: selected.id,
        payload: {
          poligono: poly,
          lat: center?.lat,
          lon: center?.lon,
          superficie_ha: area ?? undefined,
        },
      });
      setIsEditingPolygon(false);
      setDraftRing([]);
      setPolygonClosed(false);
    } catch (err: any) {
      setFormError(
        err?.response?.data?.detail ||
          err.message ||
          "Error al guardar polígono",
      );
    } finally {
      setSubmitting(false);
    }
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
    } catch {
      // ignore
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
      } catch {
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
      } catch {
        setFormError("El formato JSON no es válido.");
        setSubmitting(false);
        return;
      }
    }

    const itemsToValidate = Array.isArray(payload) ? payload : [payload];
    for (const item of itemsToValidate) {
      const ring = item.poligono ? ringFromGeoJson(item.poligono) : draftRing;
      if (ring.length >= 3) {
        item.poligono = geoJsonFromRing(ring);
        const c = centroidFromRing(ring);
        if (c) {
          item.lat = c.lat;
          item.lon = c.lon;
        }
        const a = areaHaFromRing(ring);
        if (
          a != null &&
          (item.superficie_ha == null || item.superficie_ha === 0)
        ) {
          item.superficie_ha = a;
        }
      }
      if (!isValidCoord(item.lat, item.lon)) {
        setFormError(
          `Coordenadas no válidas para: ${item.nombre || "Sin nombre"}. Dibuja un polígono.`,
        );
        setSubmitting(false);
        return;
      }
      if (!item.poligono || ringFromGeoJson(item.poligono).length < 3) {
        setFormError(
          "Define el polígono de la parcela en el mapa (mínimo 3 vértices).",
        );
        setSubmitting(false);
        return;
      }
    }

    try {
      const payloadWithOrg = Array.isArray(payload)
        ? payload.map((p) => ({
            ...p,
            organization_id: p.organization_id || selectedOrg?.id,
          }))
        : {
            ...payload,
            organization_id: payload.organization_id || selectedOrg?.id,
          };
      await createCropsMutation.mutateAsync(payloadWithOrg);
      setIsCreating(false);
      setDraftRing([]);
      setPolygonClosed(false);
      setFormData((prev) => ({ ...prev, nombre: "", poligono: null }));
    } catch (err: any) {
      setFormError(
        err?.response?.data?.detail ||
          err.message ||
          "Error de conexión con el servidor",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const tiposDisponibles = Array.from(new Set(crops.map((c) => c.cultivo)));
  const filteredCrops =
    selectedFilter === "ALL"
      ? crops
      : crops.filter((c) => c.cultivo === selectedFilter);

  if (loading && crops.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 text-blue-900 font-medium">
        Cargando mapa{isFetching ? "…" : "..."}
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
          <div>
            <h1 className="text-lg font-bold text-slate-800">
              Fincas y parcelas (polígono)
            </h1>
            <p className="text-xs text-slate-500">
              Selecciona el polígono o elige la parcela en la lista
            </p>
          </div>
        </div>
        <button
          onClick={() => {
            setIsEditingPolygon(false);
            setIsCreating(!isCreating);
            setDraftRing([]);
            setPolygonClosed(false);
            setFormError(null);
          }}
          className={`font-medium text-sm px-4 py-2 rounded-xl shadow transition cursor-pointer ${
            isCreating
              ? "bg-slate-200 text-slate-700 hover:bg-slate-300"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {isCreating ? "✕ Cancelar" : "➕ Nueva parcela"}
        </button>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 p-4 overflow-hidden">
        <div className="lg:col-span-8 h-[350px] lg:h-full rounded-2xl overflow-hidden border bg-white shadow-md relative">
          {drawing && (
            <div className="absolute top-3 left-3 right-3 z-[1000] flex flex-wrap gap-2">
              <div className="bg-red-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-lg pointer-events-none">
                {polygonClosed
                  ? "Polígono cerrado — puedes guardar"
                  : "Clic = vértice · cerca del punto verde o doble clic = cerrar"}
              </div>
              <div className="bg-white/95 text-slate-800 text-xs font-semibold px-3 py-1.5 rounded-lg shadow border flex flex-wrap gap-2 items-center">
                <span>
                  {draftStats.vertices} vértices
                  {draftStats.area != null ? ` · ~${draftStats.area} ha` : ""}
                  {polygonClosed ? " · cerrado" : ""}
                </span>
                <button
                  type="button"
                  onClick={undoVertex}
                  className="px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200"
                >
                  Deshacer
                </button>
                <button
                  type="button"
                  onClick={clearPolygon}
                  className="px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200"
                >
                  Limpiar
                </button>
                {!polygonClosed && draftRing.length >= 3 && (
                  <button
                    type="button"
                    onClick={closePolygon}
                    className="px-2 py-0.5 rounded bg-emerald-700 text-white"
                  >
                    Cerrar polígono
                  </button>
                )}
                {polygonClosed && (
                  <button
                    type="button"
                    onClick={() => setPolygonClosed(false)}
                    className="px-2 py-0.5 rounded bg-amber-100 text-amber-900"
                  >
                    Seguir editando
                  </button>
                )}
                {isEditingPolygon && (
                  <>
                    <button
                      type="button"
                      onClick={() => {
                        setIsEditingPolygon(false);
                        setDraftRing([]);
                        setPolygonClosed(false);
                      }}
                      className="px-2 py-0.5 rounded bg-slate-100"
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      disabled={submitting || draftRing.length < 3}
                      onClick={() => void saveEditedPolygon()}
                      className="px-2 py-0.5 rounded bg-emerald-700 text-white disabled:opacity-50"
                    >
                      Guardar polígono
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
          <CultivosMap
            crops={filteredCrops}
            onSelect={selectParcel}
            selectedId={selected?.id}
            draftRing={draftRing}
            drawing={drawing}
            polygonClosed={polygonClosed}
            onAddVertex={handleAddVertex}
            onClosePolygon={closePolygon}
            fitBounds={fitBounds}
          />
        </div>

        <div className="lg:col-span-4 bg-white rounded-2xl p-6 shadow-md border space-y-6 flex flex-col overflow-y-auto">
          {isCreating ? (
            <form
              onSubmit={handleSubmit}
              className="space-y-4 flex-1 flex flex-col justify-between"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b pb-3">
                  <h2 className="text-lg font-bold text-slate-800">
                    Registrar parcela
                  </h2>
                  <div className="flex bg-slate-100 p-1 rounded-lg text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => setCreateModeTab("form")}
                      className={`px-2.5 py-1 rounded-md ${createModeTab === "form" ? "bg-white text-blue-600 shadow-sm" : "text-slate-600"}`}
                    >
                      Formulario
                    </button>
                    <button
                      type="button"
                      onClick={() => setCreateModeTab("json")}
                      className={`px-2.5 py-1 rounded-md ${createModeTab === "json" ? "bg-white text-blue-600 shadow-sm" : "text-slate-600"}`}
                    >
                      JSON
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
                    <div className="rounded-xl border border-red-100 bg-red-50/50 p-3 text-xs text-red-900">
                      Dibuja el polígono: <b>clic</b> añade vértices,{" "}
                      <b>punto verde / doble clic / botón</b> cierra el contorno.
                      El mapa se enfoca a la parcela, no al centroide.
                      {draftStats.vertices > 0 && (
                        <span className="block mt-1 font-semibold">
                          {draftStats.vertices} puntos
                          {draftStats.area != null
                            ? ` · ${draftStats.area} ha`
                            : ""}
                          {polygonClosed ? " · cerrado ✓" : ""}
                        </span>
                      )}
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Nombre *
                      </label>
                      <input
                        type="text"
                        name="nombre"
                        required
                        value={formData.nombre}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border rounded-lg text-sm"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Código parcela
                        </label>
                        <input
                          type="text"
                          name="parcela_codigo"
                          value={formData.parcela_codigo || ""}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Ref. catastral
                        </label>
                        <input
                          type="text"
                          name="ref_catastral"
                          value={formData.ref_catastral || ""}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border rounded-lg text-sm"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Cultivo *
                        </label>
                        <input
                          type="text"
                          name="cultivo"
                          required
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
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Variedad
                        </label>
                        <input
                          type="text"
                          name="variedad"
                          value={formData.variedad || ""}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Superficie (ha)
                        </label>
                        <input
                          type="number"
                          step="any"
                          name="superficie_ha"
                          value={formData.superficie_ha ?? ""}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border rounded-lg text-sm"
                        />
                      </div>
                    </div>
                    <div className="space-y-2 rounded-xl border border-emerald-100 bg-emerald-50/40 p-3">
                      <p className="text-[11px] font-bold uppercase text-emerald-800">
                        Agua / riego
                      </p>
                      <input
                        type="text"
                        name="sistema_riego"
                        placeholder="Sistema de riego"
                        value={formData.sistema_riego || ""}
                        onChange={handleInputChange}
                        className="w-full px-2 py-1.5 border rounded text-xs bg-white"
                      />
                      <input
                        type="text"
                        name="fuente_agua"
                        placeholder="Fuente de agua"
                        value={formData.fuente_agua || ""}
                        onChange={handleInputChange}
                        className="w-full px-2 py-1.5 border rounded text-xs bg-white"
                      />
                      <input
                        type="number"
                        step="any"
                        name="dotacion_m3_ha_anio"
                        placeholder="Dotación m³/ha·año"
                        value={formData.dotacion_m3_ha_anio ?? ""}
                        onChange={handleInputChange}
                        className="w-full px-2 py-1.5 border rounded text-xs bg-white"
                      />
                      <input
                        type="text"
                        name="certificaciones"
                        placeholder="Certificaciones"
                        value={formData.certificaciones || ""}
                        onChange={handleInputChange}
                        className="w-full px-2 py-1.5 border rounded text-xs bg-white"
                      />
                    </div>
                    <div>
                      <button
                        type="button"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="text-xs font-semibold text-blue-600"
                      >
                        {showAdvanced
                          ? "▾ Ocultar meteo"
                          : "▸ Datos climáticos (opcional)"}
                      </button>
                      {showAdvanced && (
                        <div className="grid grid-cols-2 gap-3 mt-3 p-3 bg-slate-50 rounded-xl border">
                          {(
                            [
                              ["temperatura", "Temp °C"],
                              ["humedad", "Humedad %"],
                              ["lluvia", "Lluvia mm"],
                              ["viento", "Viento km/h"],
                              ["ndvi", "NDVI"],
                            ] as const
                          ).map(([name, label]) => (
                            <div key={name}>
                              <label className="block text-[11px] text-slate-600 mb-1">
                                {label}
                              </label>
                              <input
                                type="number"
                                step="any"
                                name={name}
                                value={(formData as any)[name]}
                                onChange={handleInputChange}
                                className="w-full px-2 py-1 border rounded text-xs bg-white"
                              />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <input
                      type="file"
                      accept=".json"
                      onChange={handleFileUpload}
                      className="text-xs"
                    />
                    <textarea
                      rows={12}
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
                  onClick={() => {
                    setIsCreating(false);
                    setDraftRing([]);
                  }}
                  className="w-1/2 px-4 py-2 text-sm text-slate-600 bg-slate-100 rounded-lg font-medium"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-1/2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow font-medium"
                >
                  {submitting ? "Guardando..." : "Guardar parcela"}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-6 flex-1 flex flex-col">
              {formError && (
                <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg">
                  {formError}
                </div>
              )}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-blue-900">
                  Parcelas (clic para seleccionar y enfocar)
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                  <button
                    onClick={() => setSelectedFilter("ALL")}
                    className={`px-3 py-1.5 text-sm rounded-lg font-medium ${selectedFilter === "ALL" ? "bg-blue-600 text-white" : "bg-blue-50 text-blue-700"}`}
                  >
                    Todas
                  </button>
                  {tiposDisponibles.map((tipo) => (
                    <button
                      key={tipo}
                      onClick={() => setSelectedFilter(tipo)}
                      className={`px-3 py-1.5 text-sm rounded-lg font-medium ${selectedFilter === tipo ? "bg-blue-600 text-white" : "bg-blue-50 text-blue-700"}`}
                    >
                      {tipo}
                    </button>
                  ))}
                </div>
                <ul className="max-h-40 overflow-y-auto space-y-1 rounded-xl border border-slate-200 p-1">
                  {filteredCrops.map((c) => {
                    const hasPoly = ringFromGeoJson(c.poligono).length >= 3;
                    const active = c.id === selected?.id;
                    return (
                      <li key={c.id}>
                        <button
                          type="button"
                          onClick={() => selectParcel(c)}
                          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                            active
                              ? "bg-amber-100 text-amber-950 border border-amber-300"
                              : "hover:bg-slate-50 text-slate-800"
                          }`}
                        >
                          <span className="font-semibold block truncate">
                            {c.nombre}
                          </span>
                          <span className="text-[11px] text-slate-500">
                            {c.parcela_codigo ? `${c.parcela_codigo} · ` : ""}
                            {c.cultivo} · {c.isla}
                            {hasPoly
                              ? ` · ${c.superficie_ha ?? "?"} ha`
                              : " · sin polígono"}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                  {filteredCrops.length === 0 && (
                    <li className="px-3 py-4 text-xs text-slate-400 text-center">
                      No hay parcelas
                    </li>
                  )}
                </ul>
              </div>

              <hr className="border-blue-100" />

              <h2 className="text-xl font-bold text-slate-800">
                Detalle de la parcela
              </h2>
              {selected ? (
                <div className="space-y-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-lg font-semibold text-blue-700">
                        {selected.nombre}
                      </h3>
                      <p className="text-slate-600 text-sm">
                        {selected.parcela_codigo
                          ? `${selected.parcela_codigo} · `
                          : ""}
                        <b>{selected.cultivo}</b>
                        {selected.variedad ? ` (${selected.variedad})` : ""} ·{" "}
                        {selected.isla}
                      </p>
                    </div>
                    <div className="flex flex-col gap-1 items-end">
                      <button
                        type="button"
                        onClick={startEditPolygon}
                        className="text-xs font-semibold text-blue-700 hover:underline"
                      >
                        Editar polígono
                      </button>
                      {selected.id && (
                        <button
                          type="button"
                          onClick={() => {
                            if (
                              confirm(
                                "¿Eliminar esta parcela y sus tratamientos?",
                              )
                            ) {
                              void deleteCropMutation.mutateAsync(selected.id!);
                              setSelected(null);
                            }
                          }}
                          className="text-xs font-semibold text-red-600 hover:underline"
                        >
                          Eliminar
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Card
                      title="Ref. catastral"
                      value={selected.ref_catastral || "n/d"}
                    />
                    <Card
                      title="Superficie"
                      value={
                        selected.superficie_ha != null
                          ? `${selected.superficie_ha} ha`
                          : "n/d"
                      }
                    />
                    <Card
                      title="Polígono"
                      value={
                        ringFromGeoJson(selected.poligono).length
                          ? `${ringFromGeoJson(selected.poligono).length} vértices`
                          : "Sin geometría"
                      }
                    />
                    <Card
                      title="Riego"
                      value={selected.sistema_riego || "n/d"}
                    />
                  </div>

                  <div className="rounded-xl border border-slate-200 p-3 space-y-2">
                    <h4 className="text-sm font-bold text-slate-800">
                      Tratamientos fitosanitarios
                    </h4>
                    <ul className="space-y-1 max-h-28 overflow-y-auto text-xs text-slate-700">
                      {(selected.treatments || []).length === 0 && (
                        <li className="text-slate-400">Sin tratamientos</li>
                      )}
                      {(selected.treatments || []).map((t) => (
                        <li key={t.id || `${t.fecha}-${t.producto}`}>
                          <b>{t.fecha}</b>: {t.producto}
                          {t.carencia_dias != null
                            ? ` · carencia ${t.carencia_dias}d`
                            : ""}
                        </li>
                      ))}
                    </ul>
                    {selected.id && (
                      <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                        <input
                          type="date"
                          value={treatmentForm.fecha}
                          onChange={(e) =>
                            setTreatmentForm((p) => ({
                              ...p,
                              fecha: e.target.value,
                            }))
                          }
                          className="px-2 py-1 border rounded text-xs"
                        />
                        <input
                          placeholder="Producto"
                          value={treatmentForm.producto}
                          onChange={(e) =>
                            setTreatmentForm((p) => ({
                              ...p,
                              producto: e.target.value,
                            }))
                          }
                          className="px-2 py-1 border rounded text-xs"
                        />
                        <button
                          type="button"
                          className="col-span-2 rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-bold text-white"
                          onClick={async () => {
                            if (!selected.id || !treatmentForm.producto) return;
                            await createTreatmentMutation.mutateAsync({
                              cropId: selected.id,
                              payload: treatmentForm,
                            });
                            setTreatmentForm((p) => ({
                              ...p,
                              producto: "",
                              materia_activa: "",
                            }));
                          }}
                        >
                          Añadir tratamiento
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  Selecciona una parcela en el mapa.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
