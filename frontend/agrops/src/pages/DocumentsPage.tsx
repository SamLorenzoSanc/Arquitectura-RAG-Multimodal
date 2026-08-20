import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Search, Trash2, UploadCloud } from "lucide-react";

import { useOrganization } from "@/context/OrganizationContext";
import { useTranslation } from "@/i18n/I18nProvider";
import DocumentChunksDrawer from "@/components/documents/DocumentChunksDrawer";
import DocumentService from "@/services/document.service";
import type { DocumentItem } from "@/types/document";
import { DOCUMENT_ACCEPT, MAX_DOCUMENT_BYTES } from "@/lib/uploads";

type LiveUpload = {
  localId: string;
  documentId?: string;
  filename: string;
  size: number;
  percent: number;
  message: string;
  status: "uploading" | "running" | "completed" | "failed";
  error?: string | null;
};

function formatBytes(size?: number) {
  if (!size || size <= 0) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function ProgressBar({
  percent,
  failed,
}: {
  percent: number;
  failed?: boolean;
}) {
  const width = Math.max(0, Math.min(100, percent));
  return (
    <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
      <div
        className={`h-full rounded-full transition-[width] duration-300 ${
          failed ? "bg-red-500" : "bg-[color:var(--agro-primary)]"
        }`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

export default function DocumentsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { selectedOrg, generalKnowledgeBase, knowledgeBases, reloadKnowledgeBases } =
    useOrganization();

  function formatStatus(status?: string) {
    if (!status) return t("documents.indexed");
    const labels: Record<string, string> = {
      running: t("documents.indexing"),
      queued: t("documents.queued"),
      uploading: t("documents.uploading"),
      completed: t("documents.indexed"),
      failed: t("documents.error"),
      uploaded: t("documents.uploaded"),
    };
    return labels[status] || status.replaceAll("_", " ");
  }
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [uploads, setUploads] = useState<LiveUpload[]>([]);
  const [openDoc, setOpenDoc] = useState<DocumentItem | null>(null);
  const watching = useRef(new Set<string>());

  const kbId = generalKnowledgeBase?.id;
  const docsQuery = useQuery({
    queryKey: [
      "documents",
      "org",
      selectedOrg?.id,
      knowledgeBases.map((item) => item.id).join("|"),
    ],
    queryFn: async () => {
      const batches = await Promise.all(
        knowledgeBases.map(async (kb) => {
          const items = await DocumentService.list(kb.id);
          return items.map((item) => ({
            ...item,
            knowledge_base_id: kb.id,
            knowledge_base_name: kb.name,
          }));
        }),
      );
      return batches.flat().sort((a, b) =>
        String(b.created_at || "").localeCompare(String(a.created_at || "")),
      );
    },
    enabled: Boolean(selectedOrg?.id && knowledgeBases.length),
  });

  const documents: DocumentItem[] = docsQuery.data ?? [];
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return documents;
    return documents.filter((doc) =>
      (doc.filename || doc.title || doc.name || "").toLowerCase().includes(q),
    );
  }, [documents, query]);

  function patchUpload(localId: string, patch: Partial<LiveUpload>) {
    setUploads((current) =>
      current.map((item) => (item.localId === localId ? { ...item, ...patch } : item)),
    );
  }

  async function watchIngest(localId: string, documentId: string, knowledgeBaseId: string) {
    watching.current.add(documentId);
    try {
      for (let i = 0; i < 600; i += 1) {
        const snap = await DocumentService.progress(knowledgeBaseId, documentId);
        const status =
          snap.status === "failed"
            ? "failed"
            : snap.status === "completed"
              ? "completed"
              : "running";
        patchUpload(localId, {
          documentId,
          percent: snap.percent ?? 0,
          message: snap.message || t("documents.indexingEllipsis"),
          status,
          error: snap.error,
        });
        if (status === "completed" || status === "failed") {
          if (status === "failed") {
            setError(snap.error || snap.message || t("documents.ingestFailed"));
          }
          await queryClient.invalidateQueries({ queryKey: ["documents"] });
          await reloadKnowledgeBases();
          await sleep(1200);
          setUploads((current) => current.filter((item) => item.localId !== localId));
          break;
        }
        await sleep(450);
      }
    } catch {
      patchUpload(localId, {
        status: "failed",
        percent: 100,
        message: t("documents.progressReadFailed"),
        error: t("documents.progressReadFailed"),
      });
    } finally {
      watching.current.delete(documentId);
    }
  }

    async function onUpload(file: File) {
    if (!kbId) {
      setError(t("documents.kbNotReady"));
      return;
    }
    if (file.size > MAX_DOCUMENT_BYTES) {
      setError(t("documents.fileTooLarge"));
      return;
    }
    const localId = `${Date.now()}-${file.name}`;
    setBusy(true);
    setError(null);
    setUploads((current) => [
      {
        localId,
        filename: file.name,
        size: file.size,
        percent: 1,
        message: t("documents.uploadingFile"),
        status: "uploading",
      },
      ...current,
    ]);
    try {
      const result = await DocumentService.upload({
        knowledgeBaseId: kbId,
        file,
        onUploadProgress: (percent) => {
          patchUpload(localId, {
            percent: Math.max(1, Math.round(percent * 0.14)),
            message: t("documents.uploadingProgress", { percent }),
            status: "uploading",
          });
        },
      });
      if (result.processing_status === "failed" || result.status === "error") {
        patchUpload(localId, {
          documentId: result.id,
          status: "failed",
          percent: 100,
          message: result.error || result.message || t("documents.ingestFailed"),
          error: result.error,
        });
        setError(result.error || result.message || t("documents.ingestFailed"));
        return;
      }
      patchUpload(localId, {
        documentId: result.id,
        status: "running",
        percent: result.progress?.percent ?? 15,
        message: result.progress?.message || t("documents.fileSavedIndexing"),
      });
      watching.current.add(result.id);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      await watchIngest(localId, result.id, kbId);
    } catch (exc) {
      const status = (exc as { response?: { status?: number } }).response?.status;
      const detail = (exc as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      const message =
        status === 413
          ? t("documents.uploadLimitExceeded")
          : detail || t("documents.indexFailed");
      patchUpload(localId, {
        status: "failed",
        percent: 100,
        message,
        error: message,
      });
      setError(message);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  useEffect(() => {
    if (!kbId) return;
    for (const doc of documents) {
      const running =
        doc.processing_status === "running" ||
        doc.processing_status === "queued" ||
        doc.progress?.status === "running";
      if (!running || watching.current.has(doc.id)) continue;
      const localId = `existing-${doc.id}`;
      setUploads((current) => {
        if (watching.current.has(doc.id)) return current;
        if (current.some((item) => item.documentId === doc.id)) return current;
        return [
          {
            localId,
            documentId: doc.id,
            filename: doc.filename || doc.title || doc.name || t("documents.defaultDocName"),
            size: doc.size || 0,
            percent: doc.progress?.percent ?? 20,
            message: doc.progress?.message || t("documents.indexingEllipsis"),
            status: "running",
          },
          ...current,
        ];
      });
      void watchIngest(localId, doc.id, doc.knowledge_base_id || kbId);
    }
  }, [documents, kbId]);

  async function onDelete(documentId: string, knowledgeBaseId?: string) {
    const targetKb = knowledgeBaseId || kbId;
    if (!targetKb) return;
    setBusy(true);
    setError(null);
    try {
      await DocumentService.delete({ knowledgeBaseId: targetKb, documentId });
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      await reloadKnowledgeBases();
    } catch {
      setError(t("documents.deleteFailed"));
    } finally {
      setBusy(false);
    }
  }

  const liveIds = new Set(uploads.map((item) => item.documentId).filter(Boolean));
  const listed = filtered.filter((doc) => !liveIds.has(doc.id));

  if (!selectedOrg) {
    return (
      <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-12 text-center text-sm text-slate-500">
        {t("documents.selectOrg")}
      </p>
    );
  }

  if (!kbId) {
    return (
      <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-12 text-center text-sm text-slate-500">
        {t("documents.preparingKb", { org: selectedOrg.name })}
      </p>
    );
  }

  const docCountLabel =
    documents.length === 1
      ? t("documents.docCountSingular", { count: documents.length })
      : t("documents.docCountPlural", { count: documents.length });

  return (
    <div className="flex w-full flex-col gap-5 pb-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <button
          type="button"
          disabled={busy || !kbId}
          onClick={() => fileRef.current?.click()}
          className="flex items-start gap-3 rounded-xl border border-[color:var(--agro-border)] bg-white p-4 text-left shadow-sm transition hover:border-[color:var(--agro-primary)] hover:shadow-md disabled:opacity-50"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[color:var(--agro-pill)] text-[color:var(--agro-primary)]">
            <UploadCloud size={18} />
          </span>
          <span>
            <span className="block text-sm font-semibold text-slate-900">
              {t("documents.uploadFile")}
            </span>
            <span className="mt-0.5 block text-xs text-slate-500">
              {t("documents.uploadHintExtended")}
            </span>
          </span>
        </button>
        <div className="flex items-start gap-3 rounded-xl border border-[color:var(--agro-border)] bg-white p-4 shadow-sm">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[color:var(--agro-accent)]/25 text-[color:var(--agro-accent-ink)]">
            <FileText size={18} />
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900">
              {t("documents.generalKb")}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              {selectedOrg.name}
              {` · ${docCountLabel}`}
            </p>
          </div>
        </div>
        <div className="hidden items-start gap-3 rounded-xl border border-dashed border-[color:var(--agro-border)] bg-white p-4 lg:flex">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-50 text-[color:var(--agro-primary)]">
            <Search size={16} />
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900">{t("documents.searchCorpus")}</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {t("documents.searchCorpusHint")}
            </p>
          </div>
        </div>
      </div>

      <input
        ref={fileRef}
        type="file"
        className="hidden"
        accept={DOCUMENT_ACCEPT}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void onUpload(file);
        }}
      />

      <div className="relative">
        <Search
          size={16}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
        />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("documents.searchPlaceholder")}
          className="h-11 w-full rounded-xl border border-[color:var(--agro-border)] bg-white pl-10 pr-4 text-sm outline-none focus:border-[color:var(--agro-primary)] focus:ring-2 focus:ring-[color:var(--agro-pill)]"
        />
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>
      )}

      {docsQuery.isLoading && uploads.length === 0 && (
        <p className="rounded-xl border border-[color:var(--agro-border)] bg-white px-4 py-8 text-center text-sm text-slate-500">
          {t("documents.loadingDocuments")}
        </p>
      )}

      {!docsQuery.isLoading && listed.length === 0 && uploads.length === 0 && (
        <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-12 text-center text-sm text-slate-500">
          {t("documents.noDocumentsExtended")}
        </p>
      )}

      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {uploads.map((item) => (
          <li
            key={item.localId}
            className="rounded-xl border border-[color:var(--agro-primary)]/40 bg-white p-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="truncate text-sm font-semibold text-slate-900">
                {item.filename}
              </h3>
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                  item.status === "failed"
                    ? "bg-red-50 text-red-700"
                    : item.status === "completed"
                      ? "bg-[color:var(--agro-pill)] text-[color:var(--agro-primary)]"
                      : "bg-amber-50 text-amber-800"
                }`}
              >
                {formatStatus(item.status)}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              {[formatBytes(item.size), `${item.percent}%`].filter(Boolean).join(" · ")}
            </p>
            <ProgressBar percent={item.percent} failed={item.status === "failed"} />
            <p className="mt-2 text-xs text-slate-600">{item.message}</p>
          </li>
        ))}
        {listed.map((doc) => (
          <li
            key={doc.id}
            className="rounded-xl border border-[color:var(--agro-border)] bg-white p-4 shadow-sm transition hover:border-[color:var(--agro-primary)] hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-3">
              <button
                type="button"
                onClick={() => setOpenDoc(doc)}
                className="min-w-0 flex-1 text-left"
              >
                <h3 className="truncate text-sm font-semibold text-slate-900">
                  {doc.filename || doc.title || doc.name}
                </h3>
                <p className="mt-1 text-[11px] text-[color:var(--agro-primary)]">
                  {t("documents.openChunks")}
                </p>
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void onDelete(doc.id, doc.knowledge_base_id)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                aria-label={t("documents.deleteAria", {
                  name: doc.filename || doc.title || doc.name || "",
                })}
              >
                <Trash2 size={15} />
              </button>
            </div>
            <dl className="mt-3 space-y-1.5 text-xs">
              <div className="flex items-center justify-between gap-2">
                <dt className="text-slate-500">{t("documents.type")}</dt>
                <dd className="rounded-full bg-[color:var(--agro-pill)] px-2 py-0.5 font-semibold text-[color:var(--agro-primary)]">
                  {formatStatus(doc.processing_status)}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-2">
                <dt className="text-slate-500">{t("documents.chunks")}</dt>
                <dd className="font-medium text-slate-800">{doc.chunks ?? "—"}</dd>
              </div>
              <div className="flex items-center justify-between gap-2">
                <dt className="text-slate-500">{t("documents.source")}</dt>
                <dd className="truncate font-medium text-slate-800">
                  {selectedOrg.name}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
      {openDoc && (
        <DocumentChunksDrawer
          document={openDoc}
          onClose={() => setOpenDoc(null)}
        />
      )}
    </div>
  );
}
