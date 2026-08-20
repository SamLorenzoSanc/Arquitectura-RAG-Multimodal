import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/api";
import KnowledgeService from "@/services/knowledge.service";
import TenantService from "@/services/tenant.service";
import DocumentService from "@/services/document.service";
import { getOrganizationDepartments } from "@/services/organization.service";
import {
  createNotebookEntry,
  deleteNotebookEntry,
  fetchNotebookEntries,
  updateNotebookEntry,
  type FieldNotebookPayload,
} from "@/services/notebook.service";
import { queryKeys } from "@/lib/queryKeys";
import type { DocumentItem } from "@/types/document";
import { useOrganization } from "@/context/OrganizationContext";

export function useKnowledgeBases(
  orgId?: string | undefined,
  departmentId?: string,
) {
  return useQuery({
    queryKey: queryKeys.knowledgeBases(orgId || "default", departmentId),
    queryFn: () => KnowledgeService.list(orgId, departmentId),
  });
}

export function useDepartments(orgId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.orgDepartments(orgId || ""),
    queryFn: () => getOrganizationDepartments(orgId!),
    enabled: Boolean(orgId),
  });
}

export function useDocuments(kbId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.documents(kbId || ""),
    queryFn: () => DocumentService.list(kbId!),
    enabled: Boolean(kbId),
    placeholderData: (previous) => previous,
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
  const { selectedOrg } = useOrganization();
  const orgId = selectedOrg?.id;
  return useQuery({
    queryKey: [...queryKeys.evaluationTests, orgId ?? "none"],
    queryFn: async () => {
      const { data } = await api.get<{ tests: unknown[] }>(
        "/chat/evaluation/tests",
        { params: orgId ? { organization_id: orgId } : undefined },
      );
      return data.tests ?? [];
    },
    enabled: Boolean(orgId),
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

export function useFieldNotebook(
  orgId: string | undefined,
  dateFrom: string,
  dateTo: string,
) {
  return useQuery({
    queryKey: queryKeys.fieldNotebook(orgId || "none", dateFrom, dateTo),
    queryFn: () =>
      fetchNotebookEntries({
        organizationId: orgId,
        dateFrom,
        dateTo,
      }),
    enabled: Boolean(dateFrom && dateTo),
  });
}

export function useCreateNotebookEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: FieldNotebookPayload) => createNotebookEntry(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["field-notebook"] });
    },
  });
}

export function useUpdateNotebookEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Partial<FieldNotebookPayload>;
    }) => updateNotebookEntry(id, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["field-notebook"] });
    },
  });
}

export function useDeleteNotebookEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteNotebookEntry(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["field-notebook"] });
    },
  });
}
export function usePrefetchDashboard(orgId: string | undefined) {
  const qc = useQueryClient();
  return useCallback(async () => {
    const jobs: Promise<unknown>[] = [
      qc.prefetchQuery({
        queryKey: queryKeys.chromaDocuments,
        queryFn: async () => {
          const { data } = await api.get("/chat/list-all-documents");
          return data;
        },
      }),
      qc.prefetchQuery({
        queryKey: [...queryKeys.evaluationTests, orgId ?? "none"],
        queryFn: async () => {
          const { data } = await api.get<{ tests: unknown[] }>(
            "/chat/evaluation/tests",
            { params: orgId ? { organization_id: orgId } : undefined },
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
          queryFn: () => DocumentService.list(kbId),
        });
      }
    }
  }, [qc, orgId]);
}

export type { DocumentItem };
