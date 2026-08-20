import es, { type TranslationSchema } from "./locales/es";
import en from "./locales/en";

export type Language = "es" | "en";

const STORAGE_KEY = "agrops-lang";

const resources: Record<Language, TranslationSchema> = { es, en };

let currentLanguage: Language = readStoredLanguage();

function readStoredLanguage(): Language {
  if (typeof window === "undefined") return "es";
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "en" ? "en" : "es";
}

function lookup(dict: Record<string, unknown>, path: string): string | undefined {
  let node: unknown = dict;
  for (const part of path.split(".")) {
    if (typeof node !== "object" || node === null || !(part in node)) {
      return undefined;
    }
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string" ? node : undefined;
}

export function getLanguage(): Language {
  return currentLanguage;
}

export function changeLanguage(lang: Language): void {
  currentLanguage = lang;
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.lang = lang;
    window.dispatchEvent(new Event("languagechange"));
  }
}

export function t(key: string, params?: Record<string, string | number>): string {
  const raw =
    lookup(resources[currentLanguage] as unknown as Record<string, unknown>, key) ??
    lookup(resources.es as unknown as Record<string, unknown>, key) ??
    key;
  if (!params) return raw;
  return Object.entries(params).reduce(
    (acc, [name, value]) => acc.replaceAll(`{{${name}}}`, String(value)),
    raw,
  );
}

export { es, en };
