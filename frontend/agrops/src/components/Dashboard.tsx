import DashboardLayout from "@/components/DashboardLayout";

export default function Dashboard() {

    return (

        <DashboardLayout>

            <h1 className="text-4xl font-bold mb-8">
                Panel de control
            </h1>

            <div className="grid grid-cols-4 gap-6">

                <div className="rounded-xl bg-white p-6 shadow">
                    Documentos
                </div>

                <div className="rounded-xl bg-white p-6 shadow">
                    Conversaciones
                </div>

                <div className="rounded-xl bg-white p-6 shadow">
                    Bases
                </div>

                <div className="rounded-xl bg-white p-6 shadow">
                    Procesos
                </div>

            </div>

        </DashboardLayout>

    );

}