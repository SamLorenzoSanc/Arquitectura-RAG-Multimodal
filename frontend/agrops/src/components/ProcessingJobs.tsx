const jobs = [

    {
        file: "PAC_2026.pdf",
        status: "Procesando"
    },

    {
        file: "POSEI.pdf",
        status: "Finalizado"
    },

    {
        file: "Cultivos.pdf",
        status: "Pendiente"
    }

];

export default function ProcessingJobs() {

    return (

        <div className="bg-white rounded-xl shadow-sm border p-6">

            <h2 className="text-xl font-semibold mb-4">

                Procesamientos

            </h2>

            <table className="w-full">

                <thead>

                    <tr className="text-left text-gray-500">

                        <th>Documento</th>

                        <th>Estado</th>

                    </tr>

                </thead>

                <tbody>

                    {jobs.map((job) => (

                        <tr key={job.file}>

                            <td className="py-3">
                                {job.file}
                            </td>

                            <td>

                                <span className="px-3 py-1 rounded-full bg-green-100 text-green-700 text-sm">

                                    {job.status}

                                </span>

                            </td>

                        </tr>

                    ))}

                </tbody>

            </table>

        </div>

    );

}