import { Database } from "lucide-react";

const bases = [

    {
        name: "Normativa PAC",
        docs: 45
    },

    {
        name: "Subvenciones Canarias",
        docs: 27
    },

    {
        name: "Cultivos Tropicales",
        docs: 56
    }

];

export default function KnowledgeBases() {

    return (

        <div className="bg-white rounded-xl shadow-sm border p-6">

            <h2 className="text-xl font-semibold mb-4">

                Bases de conocimiento

            </h2>

            <div className="space-y-3">

                {bases.map((kb) => (

                    <div
                        key={kb.name}
                        className="flex justify-between items-center p-4 rounded-lg hover:bg-gray-50"
                    >

                        <div className="flex gap-3 items-center">

                            <Database
                                className="text-green-600"
                            />

                            <span>

                                {kb.name}

                            </span>

                        </div>

                        <span className="text-sm text-gray-500">

                            {kb.docs} documentos

                        </span>

                    </div>

                ))}

            </div>

        </div>

    );

}