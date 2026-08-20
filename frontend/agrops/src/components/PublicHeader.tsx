import { Link } from "react-router-dom";

import { BrandMark } from "@/components/BrandMark";
import { useTranslation } from "@/i18n/I18nProvider";
import type { Language } from "@/i18n";

export function PublicHeader({ active }: { active?: "about" | "sustainability" | "privacy" }) {
  const { t, language, changeLanguage } = useTranslation();

  const link = (path: string, key: string, labelKey: string) => (
    <Link
      to={path}
      className={`text-sm font-semibold transition ${
        active === key
          ? "text-[color:var(--agro-primary)]"
          : "text-slate-700 hover:text-[color:var(--agro-primary)]"
      }`}
    >
      {t(labelKey)}
    </Link>
  );

  const langBtn = (lang: Language, label: string) => (
    <button
      type="button"
      onClick={() => changeLanguage(lang)}
      className={`rounded-md px-2 py-1 text-xs font-bold transition ${
        language === lang
          ? "bg-[color:var(--agro-primary)] text-white"
          : "text-slate-500 hover:bg-slate-100"
      }`}
      aria-pressed={language === lang}
    >
      {label}
    </button>
  );

  return (
    <>
      <div className="agro-flag-bar" aria-hidden>
        <span />
        <span />
        <span />
      </div>
      <header className="sticky top-0 z-50 flex h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-6 shadow-xs backdrop-blur-md sm:px-8">
        <Link to="/">
          <BrandMark size="lg" subtitle={t("common.canary")} />
        </Link>
        <nav className="hidden items-center gap-8 lg:flex">
          {link("/about", "about", "public.about")}
          {link("/sustainability", "sustainability", "public.sustainability")}
          {link("/privacy-policy", "privacy", "public.privacy")}
        </nav>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-0.5 rounded-lg border border-slate-200 p-0.5">
            {langBtn("es", "ES")}
            {langBtn("en", "EN")}
          </div>
          <Link
            to="/login"
            className="px-3 py-2 text-sm font-bold text-slate-700 hover:text-[color:var(--agro-primary)]"
          >
            {t("public.login")}
          </Link>
          <Link
            to="/register"
            className="rounded-xl bg-[color:var(--agro-primary)] px-5 py-2.5 text-sm font-bold text-white hover:bg-[color:var(--agro-primary-hover)]"
          >
            {t("public.getStarted")}
          </Link>
        </div>
      </header>
    </>
  );
}
