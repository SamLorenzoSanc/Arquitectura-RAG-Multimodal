import { Bell, Search, UserCircle} from "lucide-react";

import { useAuth } from "@/context/AuthContext";

export default function Topbar() {

    const { user } = useAuth();

    return (

        <header className="bg-white h-20 border-b flex items-center justify-between px-8">

            <div className="relative">

                <Search
                    size={18}
                    className="absolute left-3 top-3 text-slate-400"
                />

                <input

                    className="pl-10 pr-4 py-2 rounded-lg border w-96"

                    placeholder="Buscar documentos..."

                />

            </div>

            <div className="flex items-center gap-6">

                <Bell />

                <div className="flex items-center gap-3">

                    <UserCircle size={35}/>

                    <div>

                        <p className="font-semibold">

                            {user?.email}

                        </p>

                        <small className="text-slate-500">

                            Usuario autenticado

                        </small>

                    </div>

                </div>

            </div>

        </header>

    );

}