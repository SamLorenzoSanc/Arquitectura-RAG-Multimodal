import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { Lock, Mail } from "lucide-react";
import bgFarm from "@/assets/login-bg.png";
import { BrandMark } from "@/components/BrandMark";
import { useAuth } from "@/context/AuthContext";
import { useTranslation } from "@/i18n/I18nProvider";

interface LoginForm {
    email: string;
    password: string;
}

export default function Login() {
    const { t } = useTranslation();
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
            console.error("Login error", error);
        }
    };

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
                            {t("auth.loginHero")}
                        </h1>
                        <p className="mt-5 text-lg leading-relaxed text-blue-50">
                            {t("auth.loginHeroDesc")}
                        </p>
                        <ul className="mt-10 space-y-3 text-sm font-medium text-blue-50">
                            <li>{t("auth.loginBullet1")}</li>
                            <li>{t("auth.loginBullet2")}</li>
                            <li>{t("auth.loginBullet3")}</li>
                        </ul>
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
                                    {t("auth.loginTitle")}
                                </h2>
                                <p className="mb-8 mt-2 text-center text-slate-500">
                                    {t("auth.loginSubtitle")}
                                </p>
                                <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                                    <div>
                                        <label className="font-medium text-slate-700">{t("auth.email")}</label>
                                        <div className="relative mt-2">
                                            <Mail size={18} className="absolute left-3 top-3 text-slate-400" />
                                            <input
                                                type="email"
                                                placeholder={t("auth.emailPlaceholder")}
                                                className="w-full rounded-lg border border-slate-200 py-3 pl-10 pr-4 outline-none focus:border-[color:var(--agro-primary)] focus:ring-2 focus:ring-[color:var(--agro-pill)]"
                                                {...register("email", { required: t("auth.emailRequired") })}
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
                                                className="w-full rounded-lg border border-slate-200 py-3 pl-10 pr-4 outline-none focus:border-[color:var(--agro-primary)] focus:ring-2 focus:ring-[color:var(--agro-pill)]"
                                                {...register("password", { required: t("auth.passwordRequired") })}
                                            />
                                        </div>
                                        {errors.password && (
                                            <p className="mt-1 text-sm text-red-500">{errors.password.message}</p>
                                        )}
                                    </div>
                                    <button
                                        disabled={isSubmitting}
                                        className="w-full rounded-lg bg-[color:var(--agro-primary)] py-3 font-semibold text-white transition hover:bg-[color:var(--agro-primary-hover)] disabled:opacity-50"
                                    >
                                        {isSubmitting ? t("auth.signingIn") : t("auth.enter")}
                                    </button>
                                </form>
                                <div className="mt-8 text-center text-slate-600">
                                    {t("auth.noAccount")}
                                    <Link
                                        to="/register"
                                        className="ml-2 font-semibold text-[color:var(--agro-primary)] hover:underline"
                                    >
                                        {t("auth.createAccount")}
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
