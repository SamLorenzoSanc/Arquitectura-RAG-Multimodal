import { 
    Leaf, 
    TrendingDown, 
    Droplets, 
    Sparkles, 
    BarChart3, 
    Cpu, 
    Users, 
} from "lucide-react";
import { Link } from "react-router-dom";
import { PublicHeader } from "@/components/PublicHeader";
import { useTranslation } from "@/i18n/I18nProvider";

export default function PrivacyPolicyPage() {
    const { t } = useTranslation();

    return (
        <div className="min-h-screen bg-[color:var(--agro-canvas)] font-sans selection:bg-yellow-200 selection:text-blue-900">
            <PublicHeader active="privacy" />

            <section className="relative overflow-hidden pt-32 pb-24 text-white">
                <div className="absolute inset-0 z-0">
                    <img 
                        src="https://images.unsplash.com/photo-1500937386664-56d1dfef3854?q=80&w=2070&auto=format&fit=crop" 
                        alt={t("privacy.heroImageAlt")} 
                        className="w-full h-full object-cover object-center"
                    />
                    <div className="absolute inset-0 bg-blue-950/70 backdrop-blur-[2px]" />
                </div>

                <div className="relative z-10 mx-auto flex max-w-5xl flex-col items-center px-6 text-center">
                    <span className="flex items-center gap-2 rounded-full border border-amber-400/40 bg-blue-900/80 px-4 py-1.5 text-sm font-semibold text-amber-300 shadow-sm backdrop-blur-md">
                        <Leaf size={16} className="text-amber-400" />
                        {t("privacy.badge")}
                    </span>

                    <h1 className="mt-6 text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl text-white">
                        {t("privacy.heroTitle")}{" "}
                        <span className="text-amber-400 underline decoration-blue-500 decoration-4">
                            {t("privacy.heroHighlight")}
                        </span>
                    </h1>

                    <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-200">
                        {t("privacy.heroDesc")}
                    </p>
                </div>
            </section>

            <section className="mx-auto max-w-7xl px-6 py-16">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                    <div className="space-y-6">
                        <div className="inline-flex p-3 bg-amber-100 text-amber-800 rounded-2xl">
                            <Sparkles size={24} />
                        </div>
                        <h2 className="text-3xl font-bold tracking-tight text-slate-900">
                            {t("privacy.whyTitle")}
                        </h2>
                        <p className="text-slate-600 text-base leading-relaxed">
                            {t("privacy.whyIntro")}
                        </p>
                        <ul className="space-y-4 text-slate-700 font-medium">
                            {[
                                ["why1Title", "why1Text"],
                                ["why2Title", "why2Text"],
                                ["why3Title", "why3Text"],
                                ["why4Title", "why4Text"],
                            ].map(([titleKey, textKey]) => (
                                <li key={titleKey} className="flex items-start gap-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                                    <span className="text-amber-500 font-bold">•</span>
                                    <div>
                                        <strong className="text-slate-900">{t(`privacy.${titleKey}`)}</strong>{" "}
                                        {t(`privacy.${textKey}`)}
                                    </div>
                                </li>
                            ))}
                        </ul>
                        <p className="text-xs text-slate-400 font-mono">{t("privacy.sourceNote")}</p>
                    </div>

                    <div className="space-y-6">
                        <div className="p-8 rounded-3xl bg-blue-900 text-white shadow-xl space-y-6 relative overflow-hidden border-t-4 border-amber-400">
                            <div className="absolute right-0 top-0 translate-x-8 -translate-y-8 w-48 h-48 bg-blue-800 rounded-full blur-2xl opacity-50 pointer-events-none" />
                            <h3 className="text-xl font-bold">{t("privacy.howTitle")}</h3>
                            <p className="text-blue-100 text-sm leading-relaxed">
                                {t("privacy.howIntro")}
                            </p>
                            <div className="space-y-4">
                                {[
                                    ["how1Title", "how1Text"],
                                    ["how2Title", "how2Text"],
                                    ["how3Title", "how3Text"],
                                ].map(([titleKey, textKey]) => (
                                    <div key={titleKey} className="bg-blue-800/60 p-4 rounded-2xl border border-blue-700/50">
                                        <h4 className="font-bold text-sm text-white flex items-center justify-between">
                                            {t(`privacy.${titleKey}`)}
                                            <span className="w-2 h-2 rounded-full bg-amber-400" />
                                        </h4>
                                        <p className="text-xs text-blue-200 mt-1">{t(`privacy.${textKey}`)}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <section className="bg-blue-950 text-white py-20 my-8 overflow-hidden">
                <div className="mx-auto max-w-7xl px-6 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                    <div className="relative overflow-hidden rounded-3xl shadow-2xl border border-blue-800/50 group">
                        <img 
                            src="https://cdn.prod.website-files.com/64634f7e4648fab8dc7f7917/64d24247b8023ce59b5a1ef2_Rectangle%20693.jpg" 
                            alt={t("privacy.soilImageAlt")} 
                            className="w-full h-[400px] object-cover transition-transform duration-700 group-hover:scale-105"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-blue-950/80 via-transparent to-transparent" />
                    </div>

                    <div className="space-y-6">
                        <span className="text-xs font-bold uppercase tracking-wider text-amber-400 bg-blue-900/80 px-3 py-1.5 rounded-xl border border-blue-700">
                            {t("privacy.soilBadge")}
                        </span>
                        <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                            {t("privacy.soilTitle")}
                        </h2>
                        <p className="text-blue-100 text-base leading-relaxed">
                            {t("privacy.soilDesc")}
                        </p>
                        <div className="grid grid-cols-2 gap-4 pt-2">
                            <div className="p-4 rounded-2xl bg-blue-900/60 border border-blue-800">
                                <p className="text-2xl font-black text-amber-400 font-mono">100%</p>
                                <p className="text-xs text-blue-200 mt-1">{t("privacy.statOrigin")}</p>
                            </div>
                            <div className="p-4 rounded-2xl bg-blue-900/60 border border-blue-800">
                                <p className="text-2xl font-black text-amber-400 font-mono">24/7</p>
                                <p className="text-xs text-blue-200 mt-1">{t("privacy.statTraceability")}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <section className="bg-white py-20 border-y border-slate-100">
                <div className="mx-auto max-w-7xl px-6 space-y-16">
                    <div className="text-center space-y-4 max-w-3xl mx-auto">
                        <h2 className="text-3xl font-bold tracking-tight text-slate-900">
                            {t("privacy.exportTitle")}
                        </h2>
                        <p className="text-slate-600 text-base">
                            {t("privacy.exportIntro")}
                        </p>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                        <div className="relative overflow-hidden rounded-3xl shadow-xl border border-slate-200 bg-slate-100 group">
                            <img 
                                src="https://cdn.prod.website-files.com/64634f7e4648fab8dc7f7917/653fc6cc5b3f926a01e5d8f1_Frame%20221.webp" 
                                alt={t("privacy.exportImageAlt")} 
                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                            />
                        </div>

                        <div className="grid grid-cols-1 gap-6">
                            {[
                                ["export1Title", "export1Text"],
                                ["export2Title", "export2Text"],
                                ["export3Title", "export3Text"],
                            ].map(([titleKey, textKey], index) => (
                                <div key={titleKey} className="p-6 rounded-3xl bg-slate-50 border border-slate-200 space-y-3">
                                    <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
                                        {String(index + 1).padStart(2, "0")}
                                    </div>
                                    <h3 className="font-bold text-slate-900">{t(`privacy.${titleKey}`)}</h3>
                                    <p className="text-sm text-slate-600">{t(`privacy.${textKey}`)}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            <section className="mx-auto max-w-7xl px-6 py-20">
                <div className="text-center space-y-4 mb-16">
                    <span className="text-xs font-bold uppercase tracking-wider text-blue-700 bg-blue-50 px-3 py-1 rounded-full border border-blue-200">
                        {t("privacy.impactBadge")}
                    </span>
                    <h2 className="text-3xl font-bold tracking-tight text-slate-900">
                        {t("privacy.impactTitle")}
                    </h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm text-center space-y-4">
                        <div className="inline-flex p-3 bg-blue-50 text-blue-600 rounded-2xl">
                            <TrendingDown size={32} />
                        </div>
                        <p className="text-xs font-bold uppercase tracking-wider text-slate-400">{t("privacy.co2Label")}</p>
                        <p className="text-4xl font-black text-slate-900 font-mono">68.639,41</p>
                        <p className="text-xs font-semibold text-blue-800 bg-blue-50 py-1.5 px-3 rounded-xl border border-blue-200 inline-block">
                            {t("privacy.co2Equiv")}
                        </p>
                    </div>

                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm text-center space-y-4">
                        <div className="inline-flex p-3 bg-amber-50 text-amber-600 rounded-2xl">
                            <Droplets size={32} />
                        </div>
                        <p className="text-xs font-bold uppercase tracking-wider text-slate-400">{t("privacy.waterLabel")}</p>
                        <p className="text-4xl font-black text-slate-900 font-mono">3.408.104,95</p>
                        <p className="text-xs font-semibold text-amber-800 bg-amber-50 py-1.5 px-3 rounded-xl border border-amber-200 inline-block">
                            {t("privacy.waterEquiv")}
                        </p>
                    </div>
                </div>
            </section>

            <section className="bg-blue-950 text-white py-24">
                <div className="mx-auto max-w-6xl px-6 space-y-16">
                    <div className="text-center space-y-4">
                        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                            {t("privacy.helpTitle")}
                        </h2>
                        <p className="text-blue-200 max-w-2xl mx-auto text-base">
                            {t("privacy.helpIntro")}
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div className="bg-blue-900/80 p-8 rounded-3xl border border-blue-800 space-y-4">
                            <div className="p-3 bg-amber-400/20 text-amber-300 rounded-2xl w-fit">
                                <BarChart3 size={24} />
                            </div>
                            <h3 className="text-lg font-bold">{t("privacy.help1Title")}</h3>
                            <p className="text-sm text-blue-100 leading-relaxed">
                                {t("privacy.help1Text")}
                            </p>
                        </div>

                        <div className="bg-blue-900/80 p-8 rounded-3xl border border-blue-800 space-y-4">
                            <div className="p-3 bg-amber-400/20 text-amber-300 rounded-2xl w-fit">
                                <Cpu size={24} />
                            </div>
                            <h3 className="text-lg font-bold">{t("privacy.help2Title")}</h3>
                            <p className="text-sm text-blue-100 leading-relaxed">
                                {t("privacy.help2Text")}
                            </p>
                            <ul className="text-xs font-mono text-amber-300 space-y-1 pt-1">
                                {["help2Co2", "help2Water", "help2Acid", "help2Eutro"].map((key) => (
                                    <li key={key}>• {t(`privacy.${key}`)}</li>
                                ))}
                            </ul>
                        </div>

                        <div className="bg-blue-900/80 p-8 rounded-3xl border border-blue-800 space-y-4">
                            <div className="p-3 bg-amber-400/20 text-amber-300 rounded-2xl w-fit">
                                <Users size={24} />
                            </div>
                            <h3 className="text-lg font-bold">{t("privacy.help3Title")}</h3>
                            <p className="text-sm text-blue-100 leading-relaxed">
                                {t("privacy.help3Text")}
                            </p>
                        </div>
                    </div>

                    <div className="p-8 rounded-3xl bg-blue-900 border border-blue-700/60 flex flex-col md:flex-row items-center justify-between gap-6">
                        <div className="space-y-2">
                            <h3 className="text-xl font-bold text-white">{t("privacy.supportTitle")}</h3>
                            <p className="text-xs text-blue-200 max-w-xl leading-relaxed">
                                {t("privacy.supportText")}
                            </p>
                        </div>
                        <Link to="/register" className="bg-amber-400 hover:bg-amber-500 text-slate-950 font-bold px-6 py-3 rounded-xl text-xs transition shadow-lg shrink-0">
                            {t("privacy.joinTransition")}
                        </Link>
                    </div>

                    <blockquote className="border-l-4 border-amber-400 pl-6 py-2 space-y-3 italic text-blue-100">
                        <p className="text-base">
                            &ldquo;{t("privacy.testimonial")}&rdquo;
                        </p>
                        <footer className="text-xs font-semibold text-amber-300 not-italic">
                            {t("privacy.testimonialAuthor")}
                        </footer>
                    </blockquote>
                </div>
            </section>
        </div>
    );
}
