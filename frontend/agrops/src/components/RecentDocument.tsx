import { FileText } from "lucide-react";

const docs = [
    "PAC_2026.pdf",
    "Subvenciones_POSEI.pdf",
    "Normativa_Fitosanitaria.pdf"
];

export default function RecentDocuments() {

    return (

        <div className="bg-white rounded-xl shadow-sm border p-6">

            <h2 className="font-semibold text-xl mb-4">
                Últimos documentos
            </h2>

            <div className="space-y-3">

                {docs.map((doc) => (

                    <div
                        key={doc}
                        className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50"
                    >

                        <FileText className="text-green-600"/>

                        <span>{doc}</span>

                    </div>

                ))}

            </div>

        </div>

    );

}