import { useEffect, useMemo, useState } from "react";
import { Copy, Search } from "lucide-react";

import { useTranslation } from "@/i18n/I18nProvider";
import {
  API_BASE,
  API_CONVENTIONS,
  API_ENDPOINTS,
  HEXAGON_LAYERS,
  fetchOpenApi,
  type ApiEndpoint,
  type HttpMethod,
} from "@/lib/apiDocs";

const GUIDE_SECTIONS = [
  { id: "inicio", titleKey: "help.sectionInicioTitle", bodyKey: "help.sectionInicioBody" },
  { id: "panel", titleKey: "help.sectionPanelTitle", bodyKey: "help.sectionPanelBody" },
  { id: "organizacion", titleKey: "help.sectionOrgTitle", bodyKey: "help.sectionOrgBody" },
  { id: "documentos", titleKey: "help.sectionDocsTitle", bodyKey: "help.sectionDocsBody" },
  { id: "asistente", titleKey: "help.sectionAssistantTitle", bodyKey: "help.sectionAssistantBody" },
  { id: "guardrails", titleKey: "help.sectionGuardrailsTitle", bodyKey: "help.sectionGuardrailsBody" },
  { id: "ajustes", titleKey: "help.sectionSettingsTitle", bodyKey: "help.sectionSettingsBody" },
  { id: "soporte", titleKey: "help.sectionSupportTitle", bodyKey: "help.sectionSupportBody" },
] as const;

const METHOD_CLASS: Record<HttpMethod, string> = {
  GET: "bg-sky-100 text-sky-800",
  POST: "bg-emerald-100 text-emerald-800",
  PUT: "bg-amber-100 text-amber-800",
  PATCH: "bg-yellow-100 text-yellow-900",
  DELETE: "bg-rose-100 text-rose-800",
};

function matchesQuery(endpoint: ApiEndpoint, query: string) {
  const haystack = [
    endpoint.method,
    endpoint.path,
    endpoint.tag,
    endpoint.summary,
    JSON.stringify(endpoint.body ?? ""),
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query);
}

function CodeBlock({ value }: { value: Record<string, unknown> | string }) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-100">
      {text}
    </pre>
  );
}

export default function HelpDocsPage() {
  const { t } = useTranslation();
  const [pane, setPane] = useState<"guide" | "api">("guide");
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const [spec, setSpec] = useState<{
    title?: string;
    version?: string;
    paths: number;
  } | null>(null);

  useEffect(() => {
    void fetchOpenApi().then(setSpec);
  }, []);

  const tags = useMemo(
    () => [...new Set(API_ENDPOINTS.map((item) => item.tag))],
    [],
  );

  const guideSections = useMemo(
    () =>
      GUIDE_SECTIONS.map((section) => ({
        id: section.id,
        title: t(section.titleKey),
        body: t(section.bodyKey),
      })),
    [t],
  );

  const visibleGuide = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return guideSections;
    return guideSections.filter(
      (section) =>
        section.title.toLowerCase().includes(q) ||
        section.body.toLowerCase().includes(q),
    );
  }, [guideSections, query]);

  const visibleApi = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return API_ENDPOINTS;
    return API_ENDPOINTS.filter((item) => matchesQuery(item, q));
  }, [query]);

  const copyPath = async (path: string) => {
    await navigator.clipboard.writeText(`${API_BASE}${path}`);
    setCopied(path);
    window.setTimeout(() => setCopied(null), 1500);
  };

  return (
    <div className="flex flex-col gap-4 pb-8">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setPane("guide")}
          className={`rounded-lg px-3.5 py-2 text-xs font-semibold ${
            pane === "guide"
              ? "bg-[color:var(--agro-primary)] text-white"
              : "bg-white text-slate-600 ring-1 ring-[color:var(--agro-border)]"
          }`}
        >
          {t("help.tabGuide")}
        </button>
        <button
          type="button"
          onClick={() => setPane("api")}
          className={`rounded-lg px-3.5 py-2 text-xs font-semibold ${
            pane === "api"
              ? "bg-[color:var(--agro-primary)] text-white"
              : "bg-white text-slate-600 ring-1 ring-[color:var(--agro-border)]"
          }`}
        >
          {t("help.tabApi")}
        </button>
      </div>

      <div className="relative">
        <Search
          size={16}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
        />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={
            pane === "api"
              ? t("help.searchApi")
              : t("help.searchGuide")
          }
          className="h-11 w-full rounded-xl border border-[color:var(--agro-border)] bg-white pl-10 pr-4 text-sm outline-none focus:border-[color:var(--agro-primary)]"
        />
      </div>

      {pane === "guide" ? (
        <div className="rounded-xl border border-[color:var(--agro-border)] bg-white p-6 shadow-sm">
          <h1 className="text-lg font-bold text-slate-900">{t("help.title")}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {t("help.intro")}
          </p>
          <div className="mt-6 space-y-3">
            {visibleGuide.length === 0 ? (
              <p className="py-12 text-center text-sm text-slate-400">
                {t("support.noResults")}
              </p>
            ) : (
              visibleGuide.map((section) => (
                <article
                  key={section.id}
                  className="rounded-xl border border-slate-100 bg-slate-50/70 p-4"
                >
                  <h2 className="text-sm font-bold text-slate-800">{section.title}</h2>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    {section.body}
                  </p>
                </article>
              ))
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <section className="rounded-xl border border-[color:var(--agro-border)] bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="text-lg font-bold text-slate-900">{t("help.apiTitle")}</h1>
                <p className="mt-1 text-sm text-slate-500">
                  {t("help.apiIntro")}{" "}
                  <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                    {API_BASE}
                  </code>
                </p>
              </div>
              <a
                href="/docs"
                target="_blank"
                rel="noreferrer"
                className="rounded-lg bg-[color:var(--agro-pill)] px-3 py-2 text-xs font-semibold text-[color:var(--agro-primary)]"
              >
                {t("help.openSwagger")}
              </a>
            </div>
            {spec && (
              <p className="mt-2 text-[11px] text-slate-400">
                {t("help.openapiLive", {
                  title: spec.title ?? "",
                  version: spec.version ?? "",
                  paths: spec.paths,
                })}
              </p>
            )}
            <ul className="mt-4 list-disc space-y-1.5 pl-5 text-sm text-slate-600">
              {API_CONVENTIONS.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <pre className="mt-4 overflow-x-auto rounded-lg bg-slate-900 p-3 text-[11px] text-slate-100">
{`Authorization: Bearer <access_token>
Content-Type: application/json`}
            </pre>
          </section>

          <section className="rounded-xl border border-[color:var(--agro-border)] bg-white p-6 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900">
              {t("help.hexTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {t("help.hexIntro")}
            </p>
            <ol className="mt-4 grid gap-3 md:grid-cols-2">
              {HEXAGON_LAYERS.map((layer, index) => (
                <li
                  key={layer.name}
                  className="rounded-xl border border-slate-100 bg-slate-50/80 p-4"
                >
                  <p className="text-[11px] font-bold uppercase tracking-wide text-[color:var(--agro-primary)]">
                    {index + 1}. {layer.name}
                  </p>
                  <code className="mt-1 block text-[11px] text-slate-500">
                    {layer.path}
                  </code>
                  <p className="mt-2 text-sm text-slate-600">{layer.detail}</p>
                </li>
              ))}
            </ol>
          </section>

          {tags.map((tag) => {
            const items = visibleApi.filter((item) => item.tag === tag);
            if (items.length === 0) return null;
            return (
              <section
                key={tag}
                className="rounded-xl border border-[color:var(--agro-border)] bg-white p-5 shadow-sm"
              >
                <h2 className="mb-3 text-sm font-bold text-slate-900">{tag}</h2>
                <div className="space-y-3">
                  {items.map((item) => (
                    <article
                      key={`${item.method}-${item.path}`}
                      className="rounded-xl border border-slate-100 p-4"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${METHOD_CLASS[item.method]}`}
                        >
                          {item.method}
                        </span>
                        <code className="text-xs font-semibold text-slate-800">
                          {API_BASE}
                          {item.path}
                        </code>
                        <button
                          type="button"
                          onClick={() => void copyPath(item.path)}
                          className="rounded p-1 text-slate-400 hover:text-[color:var(--agro-primary)]"
                          aria-label={t("help.copyPathAria")}
                        >
                          <Copy size={13} />
                        </button>
                        {copied === item.path && (
                          <span className="text-[10px] font-semibold text-emerald-700">
                            {t("help.copied")}
                          </span>
                        )}
                        <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
                          {item.auth ? t("help.authBearer") : t("help.authPublic")}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-slate-600">{item.summary}</p>
                      {item.query && item.query.length > 0 && (
                        <p className="mt-2 text-[11px] text-slate-500">
                          {t("help.queryLabel")} {item.query.join(" · ")}
                        </p>
                      )}
                      {(item.body || item.response) && (
                        <div className="mt-3 grid gap-3 lg:grid-cols-2">
                          {item.body && (
                            <div>
                              <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">
                                {t("help.bodyLabel")}
                              </p>
                              <CodeBlock value={item.body} />
                            </div>
                          )}
                          {item.response && (
                            <div>
                              <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">
                                {t("help.responseLabel")}
                              </p>
                              <CodeBlock value={item.response} />
                            </div>
                          )}
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            );
          })}

          {visibleApi.length === 0 && (
            <p className="rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center text-sm text-slate-400">
              {t("support.noResults")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
