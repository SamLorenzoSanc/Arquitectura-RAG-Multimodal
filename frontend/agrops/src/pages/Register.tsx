import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { Lock, Mail, User } from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";

import api from "@/api";
import bgFarm from "@/assets/login-bg.png";
import { BrandMark } from "@/components/BrandMark";
import { useTranslation } from "@/i18n/I18nProvider";

interface RegisterForm {
    name: string;
    email: string;
    password: string;
    confirmPassword: string;
}

export default function Register() {
    const { t } = useTranslation();
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
            void confirmPassword;
            await api.post("/auth/register", payload);
            toast.success(t("auth.accountCreated"));
            navigate("/login");
        } catch (error) {
            if (axios.isAxiosError(error)) {
                toast.error(
                    error.response?.data?.detail ?? t("auth.accountCreateFailed"),
                );
            } else {
                toast.error(t("auth.unexpectedError"));
            }
        }
    };

    const fieldClass =
        "w-full rounded-lg border border-slate-200 py-3 pl-10 pr-4 outline-none focus:border-[color:var(--agro-primary)] focus:ring-2 focus:ring-[color:var(--agro-pill)]";

    return (
        <div className="flex min-h-screen flex-col">
            <div className="agro-flag-bar" aria-hidden>
                <span />
                <span />
                <span />
            </div>
            <div className="flex min-h-0 flex-1">
                <div
                    className="relative hidden w-1/2 items-center justify-center bg-cover bg-center p-16 text-white lg:flex"
                    style={{
                        backgroundImage: `linear-gradient(rgba(0, 56, 168, 0.88), rgba(0, 45, 134, 0.92)), url(${bgFarm})`,
                    }}
                >
                    <div className="relative z-10 max-w-md">
                        <BrandMark
                            size="lg"
                            subtitle={t("common.canary")}
                            className="[&_p]:text-white [&_span]:text-[#FFD100]"
                        />
                        <h1 className="mt-8 text-4xl font-bold tracking-tight">
                            {t("auth.registerHero")}
                        </h1>
                        <p className="mt-5 text-lg leading-relaxed text-blue-50">
                            {t("auth.registerHeroDesc")}
                        </p>
                    </div>
                </div>

                <div className="flex flex-1 items-center justify-center bg-[color:var(--agro-canvas)] p-8">
                    <div className="w-full max-w-md">
                        <div className="mb-6 lg:hidden">
                            <BrandMark size="lg" />
                        </div>
                        <div className="overflow-hidden rounded-2xl border border-[color:var(--agro-border)] bg-white shadow-xl">
                            <div className="agro-flag-bar" aria-hidden>
                                <span />
                                <span />
                                <span />
                            </div>
                            <div className="p-10">
                                <h2 className="text-center text-3xl font-bold text-slate-900">
                                    {t("auth.registerTitle")}
                                </h2>
                                <p className="mb-8 mt-2 text-center text-slate-500">
                                    {t("auth.registerSubtitle")}
                                </p>
                                <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                                    <div>
                                        <label className="font-medium text-slate-700">{t("auth.fullName")}</label>
                                        <div className="relative mt-2">
                                            <User size={18} className="absolute left-3 top-3 text-slate-400" />
                                            <input
                                                type="text"
                                                placeholder={t("auth.namePlaceholder")}
                                                className={fieldClass}
                                                {...register("name", { required: t("auth.nameRequired") })}
                                            />
                                        </div>
                                        {errors.name && (
                                            <p className="mt-1 text-sm text-red-500">{errors.name.message}</p>
                                        )}
                                    </div>
                                    <div>
                                        <label className="font-medium text-slate-700">{t("auth.email")}</label>
                                        <div className="relative mt-2">
                                            <Mail size={18} className="absolute left-3 top-3 text-slate-400" />
                                            <input
                                                type="email"
                                                placeholder={t("auth.emailPlaceholder")}
                                                className={fieldClass}
                                                {...register("email", {
                                                    required: t("auth.emailRequired"),
                                                    pattern: {
                                                        value: /^\S+@\S+\.\S+$/,
                                                        message: t("auth.emailInvalid"),
                                                    },
                                                })}
                                            />
                                        </div>
                                        {errors.email && (
                                            <p className="mt-1 text-sm text-red-500">{errors.email.message}</p>
                                        )}
                                    </div>
                                    <div>
                                        <label className="font-medium text-slate-700">{t("auth.password")}</label>
                                        <div className="relative mt-2">
                                            <Lock size={18} className="absolute left-3 top-3 text-slate-400" />
                                            <input
                                                type="password"
                                                placeholder="********"
                                                className={fieldClass}
                                                {...register("password", {
                                                    required: t("auth.passwordRequired"),
                                                    minLength: {
                                                        value: 8,
                                                        message: t("auth.passwordMin"),
                                                    },
                                                })}
                                            />
                                        </div>
                                        {errors.password && (
                                            <p className="mt-1 text-sm text-red-500">{errors.password.message}</p>
                                        )}
                                    </div>
                                    <div>
                                        <label className="font-medium text-slate-700">{t("auth.confirmPassword")}</label>
                                        <div className="relative mt-2">
                                            <Lock size={18} className="absolute left-3 top-3 text-slate-400" />
                                            <input
                                                type="password"
                                                placeholder="********"
                                                className={fieldClass}
                                                {...register("confirmPassword", {
                                                    required: t("auth.confirmRequired"),
                                                    validate: (value) =>
                                                        value === password || t("auth.passwordMismatch"),
                                                })}
                                            />
                                        </div>
                                        {errors.confirmPassword && (
                                            <p className="mt-1 text-sm text-red-500">
                                                {errors.confirmPassword.message}
                                            </p>
                                        )}
                                    </div>
                                    <button
                                        type="submit"
                                        disabled={isSubmitting}
                                        className="w-full rounded-lg bg-[color:var(--agro-primary)] py-3 font-semibold text-white transition hover:bg-[color:var(--agro-primary-hover)] disabled:opacity-50"
                                    >
                                        {isSubmitting ? t("auth.creatingAccount") : t("auth.registerTitle")}
                                    </button>
                                </form>
                                <div className="mt-8 text-center text-slate-600">
                                    {t("auth.hasAccount")}
                                    <Link
                                        to="/login"
                                        className="ml-2 font-semibold text-[color:var(--agro-primary)] hover:underline"
                                    >
                                        {t("auth.loginTitle")}
                                    </Link>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
