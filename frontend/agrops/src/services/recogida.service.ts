import api from "@/api";

export interface GeoPoint {
  lat: number;
  lon: number;
}

export interface MapaLaPalma {
  bbox: { south: number; west: number; north: number; east: number };
  center: { lat: number; lon: number };
  cooperativa: { name: string; lat: number; lon: number };
  roads: number[][][];
  nodes: number;
  source: string;
  description: string;
}

export interface GeoRutaResult {
  found: boolean;
  start_snapped: number[];
  start_snap_m: number;
  order: number[][];
  order_snapped: number[][];
  full_path: number[][];
  segments: Array<{
    from: number[];
    to: number[];
    path: number[][];
    cost_m: number;
    nodes_expanded: number;
  }>;
  total_cost_m: number;
  total_cost_km: number;
  nodes_expanded: number;
  return_to_start: boolean;
  stops: number;
  graph_source: string;
  message: string;
}

const RecogidaService = {
  async getMapa(refresh = false): Promise<MapaLaPalma> {
    const { data } = await api.get<MapaLaPalma>("/recogida/mapa", {
      params: refresh ? { refresh: true } : undefined,
    });
    return data;
  },

  async calcularRutaGeo(payload: {
    start: GeoPoint;
    stops: GeoPoint[];
    return_to_start?: boolean;
    max_snap_m?: number;
  }): Promise<GeoRutaResult> {
    const { data } = await api.post<GeoRutaResult>("/recogida/mapa/ruta", payload);
    return data;
  },
};

export default RecogidaService;
