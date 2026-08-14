import api from "@/api";

export interface SatSociety {
  denominacion: string;
  nif?: string | null;
  objeto_social_principal_nombre?: string | null;
  situacion?: string | null;
  direccion_municipio_nombre?: string | null;
  direccion_provincia_nombre?: string | null;
  numero_socios?: number | null;
}

export interface IstacSeries {
  series_id: string;
  title: string;
  updated_at?: string | null;
  source_file: string;
  observation_count?: number;
}

export interface IstacObservation {
  row_label?: string | null;
  column_label?: string | null;
  value: number;
  unit?: string | null;
}

export async function listSatSocieties(params?: {
  municipio?: string;
  situacion?: string;
  cnae_contains?: string;
  limit?: number;
}): Promise<SatSociety[]> {
  const { data } = await api.get("/opendata/sat", { params });
  return data.data ?? [];
}

export async function listIstacSeries(): Promise<IstacSeries[]> {
  const { data } = await api.get("/opendata/istac/series");
  return data.data ?? [];
}

export async function listIstacObservations(
  seriesId: string,
  limit = 100,
): Promise<IstacObservation[]> {
  const { data } = await api.get(
    `/opendata/istac/series/${encodeURIComponent(seriesId)}/observations`,
    { params: { limit } },
  );
  return data.data ?? [];
}

export async function importOpenData(): Promise<unknown> {
  const { data } = await api.post("/opendata/import");
  return data;
}
