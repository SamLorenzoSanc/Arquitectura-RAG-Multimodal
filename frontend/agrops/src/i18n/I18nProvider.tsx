import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { changeLanguage, getLanguage, t, type Language } from "./index";

type I18nContextValue = {
  language: Language;
  t: typeof t;
  changeLanguage: (lang: Language) => void;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(getLanguage());

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    const onLanguageChange = () => setLanguage(getLanguage());
    window.addEventListener("languagechange", onLanguageChange);
    return () => window.removeEventListener("languagechange", onLanguageChange);
  }, []);

  const setLang = useCallback((lang: Language) => {
    changeLanguage(lang);
    setLanguage(lang);
  }, []);

  const value = useMemo(
    () => ({ language, t, changeLanguage: setLang }),
    [language, setLang],
  );

  return (
    <I18nContext.Provider value={value}>
      <div key={language} className="contents">
        {children}
      </div>
    </I18nContext.Provider>
  );
}

export function useTranslation() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useTranslation must be used within I18nProvider");
  }
  return ctx;
}
