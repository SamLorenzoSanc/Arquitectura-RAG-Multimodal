import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";

import type { ReactNode } from "react";

interface Props {
    children: ReactNode;
}

export default function DashboardLayout({ children }: Props) {

    return (

        <div className="flex h-screen bg-slate-100">

            <Sidebar />

            <div className="flex flex-col flex-1 overflow-hidden">

                <Topbar />

                <main className="flex-1 overflow-y-auto p-8">

                    {children}

                </main>

            </div>

        </div>

    );

}