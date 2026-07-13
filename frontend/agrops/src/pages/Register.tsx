import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { Leaf, Mail, Lock, User } from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";

import api from "@/api";
import bgFarm from "@/assets/login-bg.png";

interface RegisterForm {
    name: string;
    email: string;
    password: string;
    confirmPassword: string;
}

export default function Register() {
    const navigate = useNavigate();

    const {
        register,
        handleSubmit,
        watch,
        formState: { errors, isSubmitting },
    } = useForm<RegisterForm>();

    const password = watch("password");

    const onSubmit = async (data: RegisterForm) => {
        try {
            const { confirmPassword, ...payload } = data;

            await api.post("/auth/register", payload);

            toast.success("Cuenta creada correctamente");

            navigate("/login");
        } catch (error) {
            if (axios.isAxiosError(error)) {
                toast.error(
                    error.response?.data?.detail ??
                        "No se pudo crear la cuenta"
                );
            } else {
                toast.error("Ha ocurrido un error inesperado");
            }
        }
    };

    return (
        <div className="min-h-screen flex">
            {/* Panel izquierdo */}
            <div
                className="hidden lg:flex w-1/2 text-white items-center justify-center p-16 bg-cover bg-center relative"
                style={{
                    backgroundImage: `linear-gradient(rgba(21,128,61,.82), rgba(21,128,61,.82)), url(${bgFarm})`,
                }}
            >
                <div className="max-w-md relative z-10">
                    <Leaf size={60} />

                    <h1 className="text-5xl font-bold mt-6">
                        AgroPS
                    </h1>

                    <p className="mt-6 text-lg leading-relaxed opacity-95">
                        Crea tu cuenta y comienza a utilizar la plataforma
                        inteligente para la gestión documental agrícola.
                    </p>

                    <ul className="mt-10 space-y-4 text-green-50 font-medium">
                        <li>Gestión documental</li>
                        <li>Inteligencia Artificial</li>
                        <li>Bases de conocimiento privadas</li>
                        <li>Consulta normativa agrícola</li>
                    </ul>
                </div>
            </div>

            {/* Panel derecho */}
            <div className="flex-1 flex items-center justify-center bg-gray-50 p-8">
                <div className="w-full max-w-md">
                    <div className="bg-white rounded-2xl shadow-xl p-10">
                        <h2 className="text-3xl font-bold text-center text-gray-800">
                            Crear cuenta
                        </h2>

                        <p className="text-center text-gray-500 mt-2 mb-8">
                            Regístrate para comenzar
                        </p>

                        <form
                            onSubmit={handleSubmit(onSubmit)}
                            className="space-y-6"
                        >
                            {/* Nombre */}
                            <div>
                                <label className="font-medium text-gray-700">
                                    Nombre completo
                                </label>

                                <div className="relative mt-2">
                                    <User
                                        size={18}
                                        className="absolute left-3 top-3 text-gray-400"
                                    />

                                    <input
                                        type="text"
                                        placeholder="Juan Pérez"
                                        className="w-full border rounded-lg pl-10 pr-4 py-3 focus:ring-2 focus:ring-green-600 outline-none"
                                        {...register("name", {
                                            required:
                                                "Introduce tu nombre",
                                        })}
                                    />
                                </div>

                                {errors.name && (
                                    <p className="text-red-500 text-sm mt-1">
                                        {errors.name.message}
                                    </p>
                                )}
                            </div>

                            {/* Email */}
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
                                            required:
                                                "Introduce tu correo",
                                            pattern: {
                                                value: /^\S+@\S+\.\S+$/,
                                                message:
                                                    "Correo electrónico inválido",
                                            },
                                        })}
                                    />
                                </div>

                                {errors.email && (
                                    <p className="text-red-500 text-sm mt-1">
                                        {errors.email.message}
                                    </p>
                                )}
                            </div>

                            {/* Password */}
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
                                            required:
                                                "Introduce una contraseña",
                                            minLength: {
                                                value: 8,
                                                message:
                                                    "Debe tener al menos 8 caracteres",
                                            },
                                        })}
                                    />
                                </div>

                                {errors.password && (
                                    <p className="text-red-500 text-sm mt-1">
                                        {errors.password.message}
                                    </p>
                                )}
                            </div>

                            {/* Confirmar password */}
                            <div>
                                <label className="font-medium text-gray-700">
                                    Confirmar contraseña
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
                                        {...register("confirmPassword", {
                                            required:
                                                "Confirma la contraseña",
                                            validate: (value) =>
                                                value === password ||
                                                "Las contraseñas no coinciden",
                                        })}
                                    />
                                </div>

                                {errors.confirmPassword && (
                                    <p className="text-red-500 text-sm mt-1">
                                        {errors.confirmPassword.message}
                                    </p>
                                )}
                            </div>

                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="w-full bg-green-700 hover:bg-green-800 text-white rounded-lg py-3 font-semibold transition disabled:opacity-50"
                            >
                                {isSubmitting
                                    ? "Creando cuenta..."
                                    : "Crear cuenta"}
                            </button>
                        </form>

                        <div className="mt-8 text-center text-gray-600">
                            ¿Ya tienes cuenta?

                            <Link
                                to="/login"
                                className="ml-2 text-green-700 font-semibold hover:underline"
                            >
                                Iniciar sesión
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}