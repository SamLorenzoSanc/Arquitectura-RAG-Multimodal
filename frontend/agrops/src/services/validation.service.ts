import api from "@/api";

export type HumanReviewStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "corrected";

export type HumanReview = {
  id: string;
  source: "chat" | "document_question" | string;
  question: string;
  answer?: string | null;
  context_snippet?: string | null;
  status: HumanReviewStatus;
  corrected_answer?: string | null;
  reviewer_notes?: string | null;
  created_at?: string | null;
  document_id?: string | null;
  category?: string | null;
  filename?: string | null;
  rationale?: string | null;
};

export type DocumentQuestion = {
  id: string;
  document_id?: string | null;
  question: string;
  rationale?: string | null;
  category?: string | null;
  keywords?: string[] | null;
  reference_answer?: string | null;
  status: string;
};

export async function fetchHumanReviews(params?: {
  status?: string;
  source?: string;
  organizationId?: string;
}): Promise<{ count: number; pending: number; data: HumanReview[] }> {
  const { data } = await api.get("/human-validation/reviews", {
    params: {
      status: params?.status ?? "pending",
      source: params?.source ?? "document_question",
      organization_id: params?.organizationId,
    },
  });
  return data;
}

export async function decideHumanReview(
  id: string,
  payload: {
    status: "approved" | "rejected" | "corrected";
    reviewer_notes?: string;
    corrected_answer?: string;
  },
): Promise<void> {
  await api.post(`/human-validation/reviews/${id}`, payload);
}

export async function fetchDocumentQuestions(params?: {
  knowledgeBaseId?: string;
  documentId?: string;
}): Promise<DocumentQuestion[]> {
  const { data } = await api.get<{ data?: DocumentQuestion[] }>(
    "/human-validation/questions",
    {
      params: {
        knowledge_base_id: params?.knowledgeBaseId,
        document_id: params?.documentId,
      },
    },
  );
  return data.data ?? [];
}
