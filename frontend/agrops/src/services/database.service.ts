import api from "@/api";
import type { DatabaseSchema } from "@/types/database";

export async function getDatabaseSchema(): Promise<DatabaseSchema> {
  const { data } = await api.get<DatabaseSchema>("/database/schema");
  return data;
}
