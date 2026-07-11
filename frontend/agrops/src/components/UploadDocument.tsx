import { UploadCloud } from "lucide-react";

export default function UploadDocument() {

    return (

        <div className="bg-white rounded-xl shadow-sm border p-6">

            <h2 className="text-xl font-semibold mb-4">
                Subir documentación
            </h2>

            <div className="border-2 border-dashed border-green-300 rounded-xl p-12 text-center">

                <UploadCloud
                    className="mx-auto text-green-600"
                    size={52}
                />

                <p className="mt-4 text-gray-600">

                    Arrastra aquí un PDF o pulsa para seleccionarlo.

                </p>

                <button className="mt-6 px-6 py-3 rounded-lg bg-green-600 text-white hover:bg-green-700">

                    Seleccionar documento

                </button>

            </div>

        </div>

    );

}