"use client";

import { useEffect, useState } from "react";
import { Building2, FileText, HardDrive, Layers, CheckCircle2, Loader2 } from "lucide-react";
import TenantService from "@/services/tenant.service";
import DocumentService from "@/services/document.service";
import { useOrganization } from "@/context/OrganizationContext";
import { useTranslation } from "@/i18n/I18nProvider";

import type { Tenant } from "@/types/tenant";

interface DocumentItem {
    id: string;
    title?: string;
    filename?: string;
    size?: number;
}

export default function TenantPage() {
    const { t } = useTranslation();
    const { selectedOrg } = useOrganization();

    const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
    const [documents, setDocuments] = useState<DocumentItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [creating, setCreating] = useState(false);

    async function syncTenantForOrganization(org: { id: string; name: string }) {
        try {
            setLoading(true);
            setError(null);

            const tenants: any = await TenantService.list();
            const tenantList = Array.isArray(tenants) ? tenants : (tenants?.items || []);
            
            let tenantMatch = tenantList.find((t: any) => t.organization_id === org.id || t.id === org.id);

            if (!tenantMatch) {
                setCreating(true);
                const defaultTenantName = org.name.toLowerCase().includes("agrotech") ? "Producción" : `Workspace ${org.name}`;
                
                const newTenant = await TenantService.create({
                    name: defaultTenantName,
                    description: `Espacio de trabajo principal y aislamiento de datos para ${org.name}`,
                    // @ts-ignore: Forzamos si organization_id no está definido en el DTO estricto de creación
                    organization_id: org.id
                });
                tenantMatch = newTenant;
                setCreating(false);
            }

            setCurrentTenant(tenantMatch);
            if (tenantMatch?.id) {
                await loadDocuments(tenantMatch.id);
            }
        } catch (err) {
            console.error("Error sincronizando el tenant:", err);
            setError(t("tenant.syncFailed"));
        } finally {
            setLoading(false);
            setCreating(false);
        }
    }

    async function loadDocuments(tenantId: string) {
        try {
            const docs = await DocumentService.list(tenantId);
            setDocuments(Array.isArray(docs) ? docs : []);
        } catch (err) {
            console.error("Error al cargar documentos del tenant:", err);
            setDocuments([]);
        }
    }

    useEffect(() => {
        if (selectedOrg?.id) {
            syncTenantForOrganization(selectedOrg);
        }
    }, [selectedOrg?.id]);

    if (!selectedOrg) {
        return (
            <div className="flex h-full w-full flex-col items-center justify-center bg-gray-50 p-8">
                <Building2 className="text-slate-300 mb-2" size={36} />
                <h2 className="text-xl font-bold text-slate-900">{t("tenant.noOrgTitle")}</h2>
                <p className="text-gray-500 text-sm mt-1">{t("tenant.noOrgBody")}</p>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider text-emerald-600">{t("tenant.badge")}</span>
                        <span className="bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200">
                            {t("tenant.synced")}
                        </span>
                    </div>
                    <h1 className="text-2xl font-bold text-slate-900 mt-1">{selectedOrg.name}</h1>
                </div>

                {currentTenant && (
                    <div className="flex items-center gap-3 bg-emerald-50/60 border border-emerald-200/60 px-4 py-2 rounded-xl">
                        <CheckCircle2 size={18} className="text-emerald-600" />
                        <div className="text-left">
                            <p className="text-[10px] font-bold uppercase text-emerald-700 tracking-wider">{t("tenant.activeTenant")}</p>
                            <p className="text-xs font-semibold text-slate-800">{currentTenant.name}</p>
                        </div>
                    </div>
                )}
            </div>

            {loading && (
                <div className="bg-white rounded-2xl shadow-xs p-12 text-center flex flex-col items-center justify-center gap-3">
                    <Loader2 className="animate-spin text-emerald-600" size={28} />
                    <p className="text-sm font-medium text-slate-600">
                        {creating ? t("tenant.creating") : t("tenant.syncing")}
                    </p>
                </div>
            )}

            {error && (
                <div className="rounded-2xl bg-red-50 border border-red-200 p-6 text-red-700 text-sm flex items-start gap-3">
                    <Building2 className="text-red-500 shrink-0 mt-0.5" size={20} />
                    <div>
                        <p className="font-bold">{t("tenant.errorTitle")}</p>
                        <p className="mt-0.5">{error}</p>
                    </div>
                </div>
            )}

            {!loading && !error && currentTenant && (
                <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex items-center gap-4">
                            <div className="p-3.5 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-200">
                                <Building2 size={24} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-400 font-medium">{t("tenant.assignedSpace")}</p>
                                <p className="text-sm font-bold text-slate-800 mt-0.5">{currentTenant.name}</p>
                            </div>
                        </div>

                        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex items-center gap-4">
                            <div className="p-3.5 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-200">
                                <FileText size={24} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-400 font-medium">{t("tenant.indexedDocs")}</p>
                                <p className="text-sm font-bold text-slate-800 mt-0.5">{t("tenant.files", { count: documents.length })}</p>
                            </div>
                        </div>

                        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex items-center gap-4">
                            <div className="p-3.5 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-200">
                                <HardDrive size={24} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-400 font-medium">{t("tenant.isolationStatus")}</p>
                                <p className="text-sm font-bold text-emerald-600 mt-0.5">{t("tenant.protected")}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
                        <div className="flex justify-between items-center">
                            <div>
                                <h3 className="text-lg font-bold text-slate-900">{t("tenant.docsTitle")}</h3>
                                <p className="text-xs text-slate-400 mt-0.5">{t("tenant.docsSubtitle")}</p>
                            </div>
                        </div>
                        
                        {documents.length === 0 ? (
                            <div className="text-center py-12 border-2 border-dashed border-slate-100 rounded-xl space-y-2">
                                <Layers className="mx-auto text-slate-300" size={32} />
                                <p className="text-sm font-medium text-slate-600">{t("tenant.docsEmptyTitle")}</p>
                                <p className="text-xs text-slate-400">{t("tenant.docsEmptyHint")}</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {documents.map((doc) => (
                                    <div key={doc.id} className="flex items-center justify-between p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white transition-all">
                                        <div className="flex items-center gap-3 min-w-0">
                                            <div className="p-2.5 bg-emerald-100 text-emerald-700 rounded-lg shrink-0">
                                                <FileText size={18} />
                                            </div>
                                            <div className="min-w-0">
                                                <p className="text-sm font-bold text-slate-800 truncate" title={doc.title || doc.filename}>
                                                    {doc.title || doc.filename}
                                                </p>
                                                <p className="text-xs text-slate-400 mt-0.5">
                                                    {doc.size ? `${(doc.size / 1024).toFixed(1)} KB` : t("tenant.indexed")}
                                                </p>
                                            </div>
                                        </div>
                                        <span className="bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2.5 py-1 rounded-md border border-emerald-200 shrink-0">
                                            {t("tenant.isolated")}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
