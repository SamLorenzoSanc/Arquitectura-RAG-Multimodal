import api from "@/api";

export const NOTEBOOK_CATEGORIES = [
  { id: "riego", label: "Riego" },
  { id: "plaga", label: "Plaga" },
  { id: "fertilizacion", label: "Fertilización" },
  { id: "cosecha", label: "Cosecha" },
  { id: "clima", label: "Clima" },
  { id: "maquinaria", label: "Maquinaria" },
  { id: "otro", label: "Otro" },
] as const;

export type NotebookCategory = (typeof NOTEBOOK_CATEGORIES)[number]["id"];

export type FieldNotebookEntry = {
  id: string;
  user_id?: string;
  organization_id?: string | null;
  crop_id?: string | null;
  entry_date: string;
  title: string;
  body?: string | null;
  category: NotebookCategory;
  reminder_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type FieldNotebookPayload = {
  title: string;
  body?: string;
  entry_date: string;
  category: NotebookCategory;
  crop_id?: string | null;
  organization_id?: string | null;
  reminder_at?: string | null;
};

export async function fetchNotebookEntries(params?: {
  dateFrom?: string;
  dateTo?: string;
  organizationId?: string;
  cropId?: string;
}): Promise<FieldNotebookEntry[]> {
  const { data } = await api.get<{ data?: FieldNotebookEntry[] }>(
    "/field-notebook/",
    {
      params: {
        date_from: params?.dateFrom,
        date_to: params?.dateTo,
        organization_id: params?.organizationId,
        crop_id: params?.cropId,
      },
    },
  );
  return data.data ?? [];
}

export async function createNotebookEntry(
  payload: FieldNotebookPayload,
): Promise<FieldNotebookEntry> {
  const { data } = await api.post<{ data: FieldNotebookEntry }>(
    "/field-notebook/",
    payload,
  );
  return data.data;
}

export async function updateNotebookEntry(
  id: string,
  payload: Partial<FieldNotebookPayload>,
): Promise<FieldNotebookEntry> {
  const { data } = await api.patch<{ data: FieldNotebookEntry }>(
    `/field-notebook/${id}`,
    payload,
  );
  return data.data;
}

export async function deleteNotebookEntry(id: string): Promise<void> {
  await api.delete(`/field-notebook/${id}`);
}
