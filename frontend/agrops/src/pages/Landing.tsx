import {
  ArrowRight,
  Bot,
  ShieldCheck,
  Building2,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PublicHeader } from "@/components/PublicHeader";
import { useTranslation } from "@/i18n/I18nProvider";

export default function Landing() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-[color:var(--agro-canvas)] font-sans selection:bg-yellow-200 selection:text-blue-900">
      <PublicHeader />

      <section className="relative overflow-hidden bg-gradient-to-b from-blue-50/60 to-slate-50 pt-24 pb-16">
        <div className="mx-auto flex max-w-7xl flex-col items-center px-6 text-center">
          <span className="flex items-center gap-2 rounded-full border border-yellow-300 bg-yellow-100/50 px-4 py-1.5 text-sm font-semibold text-yellow-800 shadow-sm backdrop-blur-sm">
            <Sparkles size={16} className="text-yellow-600" />
            {t("landing.badge")}
          </span>

          <h1 className="mt-8 max-w-4xl text-5xl font-extrabold tracking-tight text-slate-900 sm:text-6xl lg:text-7xl">
            {t("landing.heroTitle")}{" "}
            <span className="bg-gradient-to-r from-blue-600 to-yellow-500 bg-clip-text text-transparent">
              {t("landing.heroHighlight")}
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
            {t("landing.heroDesc")}
          </p>

          <div className="mt-10 flex flex-col gap-4 sm:flex-row sm:gap-6">
            <Link
              to="/login"
              className="group flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-8 py-4 text-base font-semibold text-white shadow-lg shadow-blue-700/20 transition-all hover:-translate-y-0.5 hover:bg-blue-800 hover:shadow-blue-700/30 active:translate-y-0"
            >
              {t("landing.startNow")}
              <ChevronRight size={20} className="transition-transform group-hover:translate-x-1" />
            </Link>

            <Link
              to="/register"
              className="flex items-center justify-center gap-2 rounded-xl border-2 border-slate-200 bg-white px-8 py-4 text-base font-semibold text-slate-700 transition-all hover:border-slate-300 hover:bg-slate-50 active:bg-slate-100"
            >
              {t("landing.createAccount")}
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-20">
        <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl shadow-slate-200/50 group">
          <img
            src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?q=80&w=2072&auto=format&fit=crop"
            alt={t("landing.heroImageAlt")}
            className="w-full h-[400px] object-cover transition-transform duration-700 group-hover:scale-105 sm:h-[500px]"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900/40 via-transparent to-transparent"></div>
        </div>
      </section>

      <section className="relative mx-auto max-w-7xl px-6 pb-24">
        <div className="mb-16 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            {t("landing.servicesTitle")}
          </h2>
          <p className="mt-4 text-lg text-slate-600">{t("landing.servicesDesc")}</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <FeatureCard
            icon={<Bot size={28} />}
            title={t("landing.feature1Title")}
            text={t("landing.feature1Text")}
          />
          <FeatureCard
            icon={<ShieldCheck size={28} />}
            title={t("landing.feature2Title")}
            text={t("landing.feature2Text")}
          />
          <FeatureCard
            icon={<Building2 size={28} />}
            title={t("landing.feature3Title")}
            text={t("landing.feature3Text")}
          />
        </div>
      </section>

      <section className="bg-white py-24 sm:py-32 border-t border-slate-100">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-20">
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
              {t("landing.howTitle")}
            </h2>
            <p className="mt-4 text-lg leading-8 text-slate-600">{t("landing.howDesc")}</p>
          </div>

          <div className="grid gap-12 md:grid-cols-3 md:gap-8">
            <Step
              number="1"
              title={t("landing.step1Title")}
              text={t("landing.step1Text")}
              imgSrc="https://images.unsplash.com/photo-1605000797499-95a51c5269ae?q=80&w=800&auto=format&fit=crop"
              alt={t("landing.step1Alt")}
            />
            <Step
              number="2"
              title={t("landing.step2Title")}
              text={t("landing.step2Text")}
              imgSrc="https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?q=80&w=800&auto=format&fit=crop"
              alt={t("landing.step2Alt")}
            />
            <Step
              number="3"
              title={t("landing.step3Title")}
              text={t("landing.step3Text")}
              imgSrc="https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=800&auto=format&fit=crop"
              alt={t("landing.step3Alt")}
            />
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden bg-slate-900 py-24 sm:py-32">
        <div className="absolute -left-20 -top-20 h-[400px] w-[400px] rounded-full bg-blue-600/30 blur-[100px]" />
        <div className="absolute -right-20 -bottom-20 h-[400px] w-[400px] rounded-full bg-yellow-400/20 blur-[100px]" />

        <div className="relative mx-auto max-w-5xl px-6 text-center">
          <h2 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
            {t("landing.ctaTitle")}
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
            {t("landing.ctaDesc")}
          </p>

          <div className="mt-10 flex items-center justify-center gap-x-6">
            <Link
              to="/register"
              className="group flex items-center gap-2 rounded-xl bg-yellow-400 px-8 py-4 text-base font-semibold text-blue-900 transition-all hover:bg-yellow-500 hover:shadow-lg hover:shadow-yellow-500/20"
            >
              {t("landing.ctaButton")}
              <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  text,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
}) {
  return (
    <div className="group flex flex-col rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-blue-200 hover:shadow-xl hover:shadow-blue-900/5 hover:ring-1 hover:ring-blue-200">
      <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-xl bg-blue-50 text-blue-700 transition-colors group-hover:bg-blue-100 group-hover:text-blue-800">
        {icon}
      </div>
      <h3 className="mb-3 text-xl font-bold text-slate-900">{title}</h3>
      <p className="text-base leading-relaxed text-slate-600 flex-grow">{text}</p>
    </div>
  );
}

function Step({
  number,
  title,
  text,
  imgSrc,
  alt,
}: {
  number: string;
  title: string;
  text: string;
  imgSrc: string;
  alt: string;
}) {
  return (
    <div className="relative flex flex-col items-center text-center group">
      <div className="relative w-full mb-8 overflow-hidden rounded-2xl bg-slate-100 shadow-md">
        <img
          src={imgSrc}
          alt={alt}
          className="h-48 w-full object-cover transition-transform duration-500 group-hover:scale-110"
        />
        <div className="absolute inset-0 bg-slate-900/10 group-hover:bg-transparent transition-colors"></div>
        <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 flex h-12 w-12 items-center justify-center rounded-full bg-blue-700 text-xl font-bold text-white shadow-lg ring-4 ring-white">
          {number}
        </div>
      </div>
      <h3 className="mt-4 text-xl font-bold text-slate-900">{title}</h3>
      <p className="mt-3 text-base leading-relaxed text-slate-600 px-4">{text}</p>
    </div>
  );
}
