import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/api";
import KnowledgeService from "@/services/knowledge.service";
import TenantService from "@/services/tenant.service";
import {
  createCrops,
  createTreatment,
  deleteCrop,
  deleteTreatment,
  fetchCrops,
  fetchDocuments,
  updateCrop,
  type CropFinca,
  type CropTreatment,
} from "@/services/crops.service";
import RecogidaService from "@/services/recogida.service";
import { queryKeys } from "@/lib/queryKeys";
import type { DocumentItem } from "@/types/document";

export function useKnowledgeBases(orgId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.knowledgeBases(orgId || ""),
    queryFn: () => KnowledgeService.list(orgId!),
    enabled: Boolean(orgId),
  });
}

export function useDocuments(kbId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.documents(kbId || ""),
    queryFn: () => fetchDocuments(kbId!),
    enabled: Boolean(kbId),
  });
}

export function useInvalidateDocuments() {
  const qc = useQueryClient();
  return useCallback(
    (kbId?: string) => {
      if (kbId) {
        return qc.invalidateQueries({ queryKey: queryKeys.documents(kbId) });
      }
      return qc.invalidateQueries({ queryKey: ["documents"] });
    },
    [qc],
  );
}

export function useCrops(includeTreatments = true) {
  return useQuery({
    queryKey: [...queryKeys.crops, includeTreatments ? "with-tx" : "basic"],
    queryFn: () => fetchCrops({ includeTreatments }),
  });
}

export function useCreateCrops() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CropFinca | CropFinca[]) => createCrops(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.crops });
    },
  });
}

export function useUpdateCrop() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<CropFinca> }) =>
      updateCrop(id, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.crops });
    },
  });
}

export function useDeleteCrop() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteCrop(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.crops });
    },
  });
}

export function useCreateTreatment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      cropId,
      payload,
    }: {
      cropId: string;
      payload: CropTreatment;
    }) => createTreatment(cropId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.crops });
    },
  });
}

export function useDeleteTreatment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      cropId,
      treatmentId,
    }: {
      cropId: string;
      treatmentId: string;
    }) => deleteTreatment(cropId, treatmentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.crops });
    },
  });
}

export function useRecogidaMapa() {
  return useQuery({
    queryKey: queryKeys.recogidaMapa,
    queryFn: () => RecogidaService.getMapa(false),
  });
}

export function useRefreshRecogidaMapa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => RecogidaService.getMapa(true),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.recogidaMapa, data);
    },
  });
}

export function useLogisticsBundle() {
  return useQuery({
    queryKey: ["logistics", "bundle"] as const,
    queryFn: async () => {
      const [shipmentsRes, catalogRes, fleetRes] = await Promise.all([
        api.get("/logistics/shipments"),
        api.get("/logistics/catalog/agricultural-options"),
        api.get("/logistics/fleet"),
      ]);
      return {
        shipments: shipmentsRes.data,
        catalog: catalogRes.data,
        fleet: fleetRes.data,
      };
    },
  });
}

export function useInvalidateLogistics() {
  const qc = useQueryClient();
  return useCallback(
    () => qc.invalidateQueries({ queryKey: ["logistics"] }),
    [qc],
  );
}

export function useChromaDocuments() {
  return useQuery({
    queryKey: queryKeys.chromaDocuments,
    queryFn: async () => {
      const { data } = await api.get<{
        total_en_documents: number;
        documentos: Array<{
          id: string;
          content: string;
          metadata: Record<string, unknown>;
        }>;
      }>("/chat/list-all-documents");
      return data;
    },
  });
}

export function useEvaluationTests() {
  return useQuery({
    queryKey: queryKeys.evaluationTests,
    queryFn: async () => {
      const { data } = await api.get<{ tests: unknown[] }>(
        "/chat/evaluation/tests",
      );
      return data.tests ?? [];
    },
  });
}

export function useTenants() {
  return useQuery({
    queryKey: queryKeys.tenants,
    queryFn: () => TenantService.list(),
  });
}

export function useKnowledgeMap(
  orgId: string | undefined,
  kbId?: string | null,
  opts?: { preview?: boolean; similarityThreshold?: number },
) {
  return useQuery({
    queryKey: [
      ...queryKeys.knowledgeMap(orgId || "", kbId),
      opts?.preview ?? false,
      opts?.similarityThreshold ?? 0.45,
    ],
    queryFn: () =>
      KnowledgeService.getMap(orgId!, {
        preview: opts?.preview,
        knowledgeBaseId: kbId || undefined,
        similarityThreshold: opts?.similarityThreshold,
      }),
    enabled: Boolean(orgId),
  });
}

/** Prefetch de lecturas del panel (trabajo diario, ops, admin, labs). */
export function usePrefetchDashboard(orgId: string | undefined) {
  const qc = useQueryClient();
  return useCallback(async () => {
    const jobs: Promise<unknown>[] = [
      qc.prefetchQuery({
        queryKey: [...queryKeys.crops, "with-tx"],
        queryFn: () => fetchCrops({ includeTreatments: true }),
      }),
      qc.prefetchQuery({
        queryKey: queryKeys.recogidaMapa,
        queryFn: () => RecogidaService.getMapa(false),
      }),
      qc.prefetchQuery({
        queryKey: ["logistics", "bundle"] as const,
        queryFn: async () => {
          const [shipmentsRes, catalogRes, fleetRes] = await Promise.all([
            api.get("/logistics/shipments"),
            api.get("/logistics/catalog/agricultural-options"),
            api.get("/logistics/fleet"),
          ]);
          return {
            shipments: shipmentsRes.data,
            catalog: catalogRes.data,
            fleet: fleetRes.data,
          };
        },
      }),
      qc.prefetchQuery({
        queryKey: queryKeys.chromaDocuments,
        queryFn: async () => {
          const { data } = await api.get("/chat/list-all-documents");
          return data;
        },
      }),
      qc.prefetchQuery({
        queryKey: queryKeys.evaluationTests,
        queryFn: async () => {
          const { data } = await api.get<{ tests: unknown[] }>(
            "/chat/evaluation/tests",
          );
          return data.tests ?? [];
        },
      }),
      qc.prefetchQuery({
        queryKey: queryKeys.tenants,
        queryFn: () => TenantService.list(),
      }),
    ];

    if (orgId) {
      jobs.push(
        qc.prefetchQuery({
          queryKey: queryKeys.knowledgeBases(orgId),
          queryFn: () => KnowledgeService.list(orgId),
        }),
        qc.prefetchQuery({
          queryKey: [
            ...queryKeys.knowledgeMap(orgId, null),
            false,
            0.45,
          ],
          queryFn: () =>
            KnowledgeService.getMap(orgId, {
              preview: false,
              similarityThreshold: 0.45,
            }),
        }),
      );
    }

    await Promise.allSettled(jobs);

    if (orgId) {
      const kbs = qc.getQueryData(queryKeys.knowledgeBases(orgId)) as
        | { id: string }[]
        | undefined;
      const kbId = kbs?.[0]?.id;
      if (kbId) {
        await qc.prefetchQuery({
          queryKey: queryKeys.documents(kbId),
          queryFn: () => fetchDocuments(kbId),
        });
      }
    }
  }, [qc, orgId]);
}

export type { DocumentItem, CropFinca, CropTreatment };
