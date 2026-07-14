import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { Leaf, Mail, Lock } from "lucide-react";
import bgFarm from "@/assets/login-bg.png"; 
import { useAuth } from "@/context/AuthContext";

interface LoginForm {
    email: string;
    password: string;
}

export default function Login() {
    const navigate = useNavigate();
    const { login } = useAuth();

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<LoginForm>();

    const onSubmit = async (data: LoginForm) => {
        try {
            await login(data.email, data.password);
            navigate("/dashboard", { replace: true });
        } catch (error) {
            console.error("Error al iniciar sesión", error);
        }
    };

    return (
        <div className="min-h-screen flex">
            
            {/* Panel izquierdo con la imagen de fondo y un overlay verde para legibilidad */}
            <div 
                className="hidden lg:flex w-1/2 text-white items-center justify-center p-16 bg-cover bg-center relative"
                style={{ 
                    backgroundImage: `linear-gradient(rgba(21, 128, 61, 0.82), rgba(21, 128, 61, 0.82)), url(${bgFarm})` 
                }}
            >
                {/* Contenido sobre el fondo */}
                <div className="max-w-md relative z-10">
                    <Leaf size={60} />

                    <h1 className="text-5xl font-bold mt-6">
                        AgroPS
                    </h1>

                    <p className="mt-6 text-lg leading-relaxed opacity-95">
                        Plataforma inteligente para la gestión documental,
                        consultas RAG y asistencia al agricultor.
                    </p>

                    <ul className="mt-10 space-y-4 text-green-50 font-medium">
                        <li className="flex items-center gap-2">Consulta normativa agrícola</li>
                        <li className="flex items-center gap-2">Gestión documental</li>
                        <li className="flex items-center gap-2">Inteligencia Artificial</li>
                        <li className="flex items-center gap-2">Bases de conocimiento privadas</li>
                    </ul>
                </div>
            </div>

            {/* Panel derecho (Formulario) */}
            <div className="flex-1 flex items-center justify-center bg-gray-50 p-8">
                <div className="w-full max-w-md">
                    <div className="bg-white rounded-2xl shadow-xl p-10">
                        <h2 className="text-3xl font-bold text-gray-800 text-center">
                            Iniciar sesión
                        </h2>

                        <p className="text-gray-500 text-center mt-2 mb-8">
                            Accede a tu asistente agrícola
                        </p>

                        <form
                            onSubmit={handleSubmit(onSubmit)}
                            className="space-y-6"
                        >
                            <div>
                                <label className="font-medium text-gray-700">
                                    Correo electrónico
                                </label>
                                <div className="relative mt-2">
                                    <Mail
                                        size={18}
                                        className="absolute left-3 top-3 text-gray-400"
                                    />
                                    <input
                                        type="email"
                                        placeholder="usuario@correo.com"
                                        className="w-full border rounded-lg pl-10 pr-4 py-3 focus:ring-2 focus:ring-green-600 outline-none"
                                        {...register("email", {
                                            required: "Introduce tu correo"
                                        })}
                                    />
                                </div>
                                {errors.email && (
                                    <p className="text-red-500 text-sm mt-1">
                                        {errors.email.message}
                                    </p>
                                )}
                            </div>

                            <div>
                                <label className="font-medium text-gray-700">
                                    Contraseña
                                </label>
                                <div className="relative mt-2">
                                    <Lock
                                        size={18}
                                        className="absolute left-3 top-3 text-gray-400"
                                    />
                                    <input
                                        type="password"
                                        placeholder="********"
                                        className="w-full border rounded-lg pl-10 pr-4 py-3 focus:ring-2 focus:ring-green-600 outline-none"
                                        {...register("password", {
                                            required: "Introduce tu contraseña"
                                        })}
                                    />
                                </div>
                                {errors.password && (
                                    <p className="text-red-500 text-sm mt-1">
                                        {errors.password.message}
                                    </p>
                                )}
                            </div>

                            <button
                                disabled={isSubmitting}
                                className="w-full bg-green-700 hover:bg-green-800 text-white rounded-lg py-3 font-semibold transition disabled:opacity-50"
                            >
                                {isSubmitting ? "Iniciando sesión..." : "Entrar"}
                            </button>
                        </form>

                        <div className="mt-8 text-center text-gray-600">
                            ¿No tienes cuenta?
                            <Link
                                to="/register"
                                className="ml-2 text-green-700 font-semibold hover:underline"
                            >
                                Crear cuenta
                            </Link>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    );
}