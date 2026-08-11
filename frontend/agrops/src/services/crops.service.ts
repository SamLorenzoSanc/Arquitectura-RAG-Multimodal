import api from "@/api";
import type { DocumentItem } from "@/types/document";

export type CropTreatment = {
  id?: string;
  crop_id?: string;
  fecha: string;
  producto: string;
  materia_activa?: string;
  dosis?: string;
  plaga_objetivo?: string;
  carencia_dias?: number | null;
  observaciones?: string;
};

export type CropFinca = {
  id?: string;
  user_id?: string;
  organization_id?: string | null;
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
  ref_catastral?: string;
  superficie_ha?: number | null;
  variedad?: string;
  sistema_riego?: string;
  fuente_agua?: string;
  dotacion_m3_ha_anio?: number | null;
  comunidad_regantes?: string;
  certificaciones?: string;
  notas?: string;
  parcela_codigo?: string;
  /** GeoJSON Polygon */
  poligono?: {
    type: "Polygon";
    coordinates: number[][][];
  } | null;
  treatments?: CropTreatment[];
};

export async function fetchCrops(options?: {
  organizationId?: string;
  includeTreatments?: boolean;
}): Promise<CropFinca[]> {
  const { data } = await api.get<{ status?: string; data?: CropFinca[] } | CropFinca[]>(
    "/crops/",
    {
      params: {
        organization_id: options?.organizationId,
        include_treatments: options?.includeTreatments ? true : undefined,
      },
    },
  );
  if (Array.isArray(data)) return data;
  return (data as { data?: CropFinca[] })?.data ?? [];
}

export async function createCrops(
  payload: CropFinca | CropFinca[],
): Promise<unknown> {
  const { data } = await api.post("/crops/", payload);
  return data;
}

export async function updateCrop(
  id: string,
  payload: Partial<CropFinca>,
): Promise<unknown> {
  const { data } = await api.patch(`/crops/${id}`, payload);
  return data;
}

export async function deleteCrop(id: string): Promise<unknown> {
  const { data } = await api.delete(`/crops/${id}`);
  return data;
}

export async function createTreatment(
  cropId: string,
  payload: CropTreatment,
): Promise<unknown> {
  const { data } = await api.post(`/crops/${cropId}/treatments`, payload);
  return data;
}

export async function deleteTreatment(
  cropId: string,
  treatmentId: string,
): Promise<unknown> {
  const { data } = await api.delete(`/crops/${cropId}/treatments/${treatmentId}`);
  return data;
}

export async function fetchDocuments(kbId: string): Promise<DocumentItem[]> {
  const { data } = await api.get<DocumentItem[] | { documents?: DocumentItem[] }>(
    "/documents",
    { params: { knowledge_base_id: kbId } },
  );
  if (Array.isArray(data)) return data;
  return (data as { documents?: DocumentItem[] })?.documents ?? [];
}
