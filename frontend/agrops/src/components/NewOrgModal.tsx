import { useTranslation } from "@/i18n/I18nProvider";

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (name: string, description: string) => Promise<void> | void;
}

export function NewOrgModal({ isOpen, onClose, onSave }: ModalProps) {
    const { t } = useTranslation();

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);

        try {
            await onSave(formData.get("name") as string, formData.get("description") as string);
            onClose();
        } catch (error) {
            console.error("Error creating organization", error);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
            <div className="w-full max-w-md overflow-hidden rounded-xl border border-[color:var(--agro-border)] bg-white shadow-xl">
                <div className="agro-flag-bar" aria-hidden>
                    <span />
                    <span />
                    <span />
                </div>
                <div className="p-6">
                    <h3 className="mb-1 text-lg font-bold text-slate-900">{t("common.newOrganization")}</h3>
                    <p className="mb-4 text-sm text-slate-500">
                        {t("common.orgModalHint")}
                    </p>
                    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                        <div>
                            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">{t("common.name")}</label>
                            <input required name="name" type="text" className="w-full rounded-lg border border-slate-200 p-2.5 text-sm outline-none focus:border-[color:var(--agro-primary)] focus:ring-2 focus:ring-[color:var(--agro-pill)]" placeholder={t("common.orgNamePlaceholder")} />
                        </div>
                        <div>
                            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">{t("common.description")}</label>
                            <textarea name="description" rows={3} className="w-full rounded-lg border border-slate-200 p-2.5 text-sm outline-none focus:border-[color:var(--agro-primary)] focus:ring-2 focus:ring-[color:var(--agro-pill)]" placeholder={t("common.orgDescPlaceholder")} />
                        </div>
                        <div className="mt-2 flex justify-end gap-2">
                            <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">{t("common.cancel")}</button>
                            <button type="submit" className="rounded-lg bg-[color:var(--agro-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[color:var(--agro-primary-hover)]">{t("common.createOrganization")}</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
