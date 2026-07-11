import { Link } from "react-router-dom";
import { Leaf } from "lucide-react";

export default function Navbar() {
    return (
        <header className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/80 backdrop-blur-md">

            <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6">

                <Link
                    to="/"
                    className="flex items-center gap-3"
                >
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-green-600">

                        <Leaf
                            size={22}
                            className="text-white"
                        />

                    </div>

                    <div>

                        <h1 className="text-xl font-bold text-slate-900">
                            AgrOPS
                        </h1>

                        <p className="text-xs text-slate-500">
                            AI Agriculture Assistant
                        </p>

                    </div>

                </Link>

                <nav className="hidden gap-10 font-medium text-slate-700 md:flex">

                    <a
                        href="#"
                        className="transition hover:text-green-600"
                    >
                        Inicio
                    </a>

                    <a
                        href="#features"
                        className="transition hover:text-green-600"
                    >
                        Características
                    </a>

                    <a
                        href="#how"
                        className="transition hover:text-green-600"
                    >
                        Cómo funciona
                    </a>

                </nav>

                <div className="flex items-center gap-4">

                    <Link
                        to="/login"
                        className="font-medium text-slate-700 transition hover:text-green-600"
                    >
                        Iniciar sesión
                    </Link>

                    <Link
                        to="/register"
                        className="rounded-xl bg-green-600 px-5 py-2.5 font-semibold text-white transition hover:bg-green-700"
                    >
                        Registrarse
                    </Link>

                </div>

            </div>

        </header>
    );
}