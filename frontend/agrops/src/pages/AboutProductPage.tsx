import { MessageSquare, Bot, ArrowRight, Building2, ThermometerSnowflake } from "lucide-react";
import { Link } from "react-router-dom";
import { PublicHeader } from "@/components/PublicHeader";
import { useTranslation } from "@/i18n/I18nProvider";

export default function AboutProductPage() {
    const { t } = useTranslation();

    return (
        <div className="min-h-screen bg-[color:var(--agro-canvas)] font-sans selection:bg-yellow-200 selection:text-blue-900">
            <PublicHeader active="about" />

            <main className="mx-auto max-w-5xl px-6 py-16 space-y-16">
                <div className="text-center space-y-4">
                    <span className="inline-block bg-yellow-100 text-yellow-800 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                        {t("about.badge")}
                    </span>
                    <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
                        {t("about.title")}
                    </h1>
                    <p className="max-w-2xl mx-auto text-base text-slate-600">
                        {t("about.intro")}
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <div className="p-3 bg-blue-50 text-blue-600 rounded-2xl w-fit">
                            <ThermometerSnowflake size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">{t("about.feature1Title")}</h3>
                        <p className="text-sm text-slate-600 leading-relaxed">
                            {t("about.feature1Text")}
                        </p>
                    </div>

                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <div className="p-3 bg-yellow-50 text-yellow-600 rounded-2xl w-fit">
                            <MessageSquare size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">{t("about.feature2Title")}</h3>
                        <p className="text-sm text-slate-600 leading-relaxed">
                            {t("about.feature2Text")}
                        </p>
                    </div>

                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <div className="p-3 bg-blue-50 text-blue-700 rounded-2xl w-fit">
                            <Building2 size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">{t("about.feature3Title")}</h3>
                        <p className="text-sm text-slate-600 leading-relaxed">
                            {t("about.feature3Text")}
                        </p>
                    </div>

                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <div className="p-3 bg-yellow-50 text-yellow-600 rounded-2xl w-fit">
                            <Bot size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">{t("about.feature4Title")}</h3>
                        <p className="text-sm text-slate-600 leading-relaxed">
                            {t("about.feature4Text")}
                        </p>
                    </div>
                </div>

                <div className="p-10 rounded-3xl bg-slate-900 text-white text-center space-y-6">
                    <h2 className="text-2xl font-bold tracking-tight">{t("about.ctaTitle")}</h2>
                    <p className="text-sm text-slate-300 max-w-xl mx-auto">
                        {t("about.ctaDesc")}
                    </p>
                    <Link to="/register" className="inline-flex items-center gap-2 bg-yellow-400 hover:bg-yellow-500 text-blue-900 font-bold px-6 py-3 rounded-xl text-xs transition shadow-lg">
                        {t("about.ctaButton")} <ArrowRight size={16} />
                    </Link>
                </div>
            </main>
        </div>
    );
}
