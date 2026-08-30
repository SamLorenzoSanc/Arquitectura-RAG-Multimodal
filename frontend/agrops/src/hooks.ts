import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/api";
import { DocumentService, KnowledgeService, getOrganizationDepartments } from "@/services";
import { queryKeys } from "@/lib/app";
import type { DocumentItem } from "@/types";
import { useOrganization } from "@/context";

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










export type { DocumentItem };
