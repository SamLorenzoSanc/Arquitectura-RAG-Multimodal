interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (name: string, description: string) => Promise<void> | void;
}

export function NewOrgModal({ isOpen, onClose, onSave }: ModalProps) {
    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);

        try {
            await onSave(formData.get("name") as string, formData.get("description") as string);
            onClose();
        } catch (error) {
            console.error("Error al crear la organización", error);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
            <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl border border-gray-100">
                <h3 className="text-xl font-bold text-slate-900 mb-4">New Organization</h3>
                <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                    <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Name</label>
                        <input required name="name" type="text" className="w-full border border-gray-200 rounded-lg p-2.5 outline-emerald-500 text-sm" placeholder="e.g. My Enterprise" />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Description</label>
                        <textarea name="description" rows={3} className="w-full border border-gray-200 rounded-lg p-2.5 outline-emerald-500 text-sm" placeholder="Brief details about the company..." />
                    </div>
                    <div className="flex justify-end gap-2 mt-2">
                        <button type="button" onClick={onClose} className="px-4 py-2 border border-gray-200 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50">Cancel</button>
                        <button type="submit" className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">Save organization</button>
                    </div>
                </form>
            </div>
        </div>
    );
}