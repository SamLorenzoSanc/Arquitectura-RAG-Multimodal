import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Camera, Copy, Trash2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useOrganization } from "@/context/OrganizationContext";
import { useKnowledgeBases } from "@/hooks/useCachedApi";
import { SETTINGS_TABS, type SettingsTab } from "@/lib/nav";
import AccountService, {
  type AccessTokenItem,
  type AccountUsage,
  type UserProfile,
} from "@/services/account.service";
import { UserAvatar } from "@/components/UserAvatar";

const ISLANDS = [
  "El Hierro",
  "Fuerteventura",
  "Gran Canaria",
  "La Gomera",
  "Lanzarote",
  "La Palma",
  "Tenerife",
];

const CROPS = ["Plátano", "Aguacate", "Papa", "Tomate", "Uva", "Otro"];

const emptyProfile = {
  name: "",
  job_title: "",
  phone: "",
  island: "",
  municipality: "",
  bio: "",
  crop_focus: "",
  preferred_language: "es",
  notify_email: true,
  notify_whatsapp: false,
};

function isSettingsTab(value: string | null): value is SettingsTab {
  return SETTINGS_TABS.some((tab) => tab.id === value);
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export default function SettingsPage() {
  const { user, updateUser } = useAuth();
  const { selectedOrg } = useOrganization();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tab: SettingsTab = isSettingsTab(tabParam) ? tabParam : "profile";

  const [name, setName] = useState(user?.name || "");
  const [profile, setProfile] = useState(emptyProfile);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(user?.avatarUrl || null);
  const avatarInputRef = useRef<HTMLInputElement | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tokens, setTokens] = useState<AccessTokenItem[]>([]);
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [tokenName, setTokenName] = useState("");
  const [usage, setUsage] = useState<AccountUsage | null>(null);
  const { data: knowledgeBases } = useKnowledgeBases(selectedOrg?.id);

  const setTab = (next: SettingsTab) => {
    setSearchParams({ tab: next });
    setMessage(null);
    setError(null);
    setCreatedToken(null);
  };

  useEffect(() => {
    setName(user?.name || "");
  }, [user?.name]);

  useEffect(() => {
    if (tab !== "profile") return;
    void AccountService.getProfile()
      .then(async (data: UserProfile) => {
        setName(data.name || "");
        setProfile({
          name: data.name || "",
          job_title: data.job_title || "",
          phone: data.phone || "",
          island: data.island || "",
          municipality: data.municipality || "",
          bio: data.bio || "",
          crop_focus: data.crop_focus || "",
          preferred_language: data.preferred_language || "es",
          notify_email: data.notify_email !== false,
          notify_whatsapp: Boolean(data.notify_whatsapp),
        });
        if (data.has_avatar) {
          try {
            const url = await AccountService.avatarObjectUrl();
            setAvatarPreview(url);
          } catch {
            setAvatarPreview(user?.avatarUrl || null);
          }
        } else {
          setAvatarPreview(user?.avatarUrl || null);
        }
      })
      .catch(() => undefined);
  }, [tab, user?.avatarUrl]);

  useEffect(() => {
    if (tab === "authenticate" || tab === "api-keys") {
      const kind = tab === "api-keys" ? "api_key" : "access";
      void AccountService.listTokens(kind)
        .then(setTokens)
        .catch(() => setTokens([]));
    }
    if (tab === "usage") {
      void AccountService.usage()
        .then(setUsage)
        .catch(() => setUsage(null));
    }
  }, [tab, selectedOrg?.id]);

  const title = useMemo(
    () => SETTINGS_TABS.find((item) => item.id === tab)?.label || "Ajustes",
    [tab],
  );

  const handleSaveProfile = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await AccountService.updateProfile({
        name,
        job_title: profile.job_title,
        phone: profile.phone,
        island: profile.island,
        municipality: profile.municipality,
        bio: profile.bio,
        crop_focus: profile.crop_focus,
        preferred_language: profile.preferred_language,
        notify_email: profile.notify_email,
        notify_whatsapp: profile.notify_whatsapp,
      });
      let avatarUrl = user?.avatarUrl || null;
      if (updated.has_avatar) {
        try {
          avatarUrl = await AccountService.avatarObjectUrl();
        } catch {
          /* conservar la previa */
        }
      }
      updateUser({
        name: updated.name,
        jobTitle: updated.job_title,
        phone: updated.phone,
        island: updated.island,
        hasAvatar: Boolean(updated.has_avatar),
        avatarUrl,
      });
      setMessage("Perfil actualizado.");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail || "No se pudo guardar el perfil.");
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarFile = async (file?: File) => {
    if (!file) return;
    setSaving(true);
    setError(null);
    try {
      const local = URL.createObjectURL(file);
      setAvatarPreview(local);
      const updated = await AccountService.uploadAvatar(file);
      const url = await AccountService.avatarObjectUrl();
      setAvatarPreview(url);
      updateUser({
        name: updated.name,
        hasAvatar: true,
        avatarUrl: url,
        jobTitle: updated.job_title,
      });
      setMessage("Foto de perfil actualizada.");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail || "No se pudo subir la foto.");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAvatar = async () => {
    setSaving(true);
    try {
      await AccountService.deleteAvatar();
      setAvatarPreview(null);
      updateUser({ hasAvatar: false, avatarUrl: null });
      setMessage("Foto de perfil eliminada.");
    } catch {
      setError("No se pudo quitar la foto.");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateToken = async (kind: "access" | "api_key") => {
    setSaving(true);
    setError(null);
    setCreatedToken(null);
    try {
      const created = await AccountService.createToken({
        name: tokenName || (kind === "api_key" ? "Clave de API" : "Token de acceso"),
        kind,
        expires_days: kind === "api_key" ? 365 : 30,
      });
      setCreatedToken(created.token);
      setTokenName("");
      setTokens(await AccountService.listTokens(kind));
      setMessage(created.note || "Token generado. Cópialo ahora.");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail || "No se pudo generar el token.");
    } finally {
      setSaving(false);
    }
  };

  const handleRevoke = async (id: string, kind: "access" | "api_key") => {
    try {
      await AccountService.revokeToken(id);
      setTokens(await AccountService.listTokens(kind));
      setMessage("Token revocado.");
    } catch {
      setError("No se pudo revocar el token.");
    }
  };

  const copyToken = async () => {
    if (!createdToken) return;
    await navigator.clipboard.writeText(createdToken);
    setMessage("Token copiado al portapapeles.");
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 pt-4">
        <div className="flex flex-wrap gap-1">
          {SETTINGS_TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={`rounded-t-md px-3 py-2 text-xs font-semibold ${
                tab === item.id
                  ? "border-b-2 border-[color:var(--agro-primary)] text-[color:var(--agro-primary)]"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-6 py-6">
        <div className="mb-5 flex items-center justify-between gap-3">
          <h1 className="text-lg font-bold text-slate-900">{title}</h1>
          {(tab === "authenticate" || tab === "api-keys") && (
            <button
              type="button"
              disabled={saving}
              onClick={() =>
                void handleCreateToken(tab === "api-keys" ? "api_key" : "access")
              }
              className="rounded-lg bg-[color:var(--agro-primary)] px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
            >
              {saving ? "Generando…" : "Generar nueva clave"}
            </button>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-xs text-red-600">
            {error}
          </div>
        )}
        {message && (
          <div className="mb-4 rounded-md bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
            {message}
          </div>
        )}

        {tab === "profile" && (
          <div className="grid max-w-4xl gap-8 lg:grid-cols-[220px_1fr]">
            <div className="flex flex-col items-center gap-3 rounded-2xl border border-slate-100 bg-slate-50/70 p-5">
              <UserAvatar src={avatarPreview} name={name} size={96} />
              <input
                ref={avatarInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void handleAvatarFile(file);
                  event.target.value = "";
                }}
              />
              <button
                type="button"
                disabled={saving}
                onClick={() => avatarInputRef.current?.click()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[color:var(--agro-primary)] px-3 py-2 text-[11px] font-bold text-white disabled:opacity-50"
              >
                <Camera size={13} /> Cambiar foto
              </button>
              {avatarPreview && (
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => void handleDeleteAvatar()}
                  className="text-[11px] font-medium text-red-600"
                >
                  Quitar foto
                </button>
              )}
              <p className="text-center text-[10px] text-slate-400">
                JPG, PNG o WEBP. Máximo 2 MB.
              </p>
            </div>

            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-xs font-semibold text-slate-600">
                  Nombre visible
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  Cargo
                  <input
                    value={profile.job_title}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        job_title: event.target.value,
                      }))
                    }
                    placeholder="Agricultor, calidad, logística…"
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600 sm:col-span-2">
                  Correo
                  <input
                    value={user?.email || ""}
                    disabled
                    className="mt-1 h-10 w-full rounded-md border border-slate-100 bg-slate-50 px-3 text-sm text-slate-500"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  Teléfono
                  <input
                    value={profile.phone}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        phone: event.target.value,
                      }))
                    }
                    placeholder="+34 600 000 000"
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  Isla
                  <select
                    value={profile.island}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        island: event.target.value,
                      }))
                    }
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                  >
                    <option value="">Sin especificar</option>
                    {ISLANDS.map((island) => (
                      <option key={island} value={island}>
                        {island}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  Municipio
                  <input
                    value={profile.municipality}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        municipality: event.target.value,
                      }))
                    }
                    placeholder="Los Llanos, Guía de Isora…"
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  Cultivo principal
                  <select
                    value={profile.crop_focus}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        crop_focus: event.target.value,
                      }))
                    }
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                  >
                    <option value="">Sin especificar</option>
                    {CROPS.map((crop) => (
                      <option key={crop} value={crop}>
                        {crop}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs font-semibold text-slate-600 sm:col-span-2">
                  Sobre ti
                  <textarea
                    value={profile.bio}
                    maxLength={500}
                    rows={4}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        bio: event.target.value,
                      }))
                    }
                    placeholder="Cuéntanos tu explotación, cooperativa o rol en la cadena de frío."
                    className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                  />
                  <span className="mt-1 block text-[10px] font-normal text-slate-400">
                    {profile.bio.length}/500
                  </span>
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  Idioma
                  <select
                    value={profile.preferred_language}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        preferred_language: event.target.value,
                      }))
                    }
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                  >
                    <option value="es">Español</option>
                    <option value="en">English</option>
                  </select>
                </label>
              </div>

              <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4">
                <p className="text-xs font-bold text-slate-700">Avisos</p>
                <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={profile.notify_email}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        notify_email: event.target.checked,
                      }))
                    }
                  />
                  Recibir avisos por correo
                </label>
                <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={profile.notify_whatsapp}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        notify_whatsapp: event.target.checked,
                      }))
                    }
                  />
                  Recibir alertas de cadena de frío por WhatsApp
                </label>
              </div>

              <p className="text-xs text-slate-400">
                El correo identifica tu cuenta y no se puede cambiar desde aquí.
              </p>
              <button
                type="button"
                disabled={saving || name.trim().length < 2}
                onClick={() => void handleSaveProfile()}
                className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white disabled:opacity-50"
              >
                {saving ? "Guardando…" : "Guardar perfil"}
              </button>
            </div>
          </div>
        )}

        {(tab === "authenticate" || tab === "api-keys") && (
          <div className="space-y-4">
            <p className="max-w-2xl text-sm text-slate-600">
              {tab === "authenticate"
                ? "Genera un token Bearer para llamar al backend (Authorization: Bearer …) sin usar la sesión del navegador."
                : "Las API keys son tokens de larga duración para integraciones. Trátalas como una contraseña."}
            </p>
            <input
              value={tokenName}
              onChange={(event) => setTokenName(event.target.value)}
              placeholder={
                tab === "api-keys" ? "Nombre de la clave" : "Nombre del token"
              }
              className="h-9 max-w-sm rounded-md border border-slate-200 px-3 text-xs"
            />
            {createdToken && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                <p className="text-xs font-semibold text-amber-800">
                  Copia este valor ahora. No se mostrará otra vez.
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <code className="flex-1 truncate rounded-md bg-white px-3 py-2 text-[11px] text-slate-700">
                    {createdToken}
                  </code>
                  <button
                    type="button"
                    onClick={() => void copyToken()}
                    className="rounded-md border border-slate-200 bg-white p-2 text-slate-600"
                    title="Copiar"
                  >
                    <Copy size={14} />
                  </button>
                </div>
              </div>
            )}
            {tokens.length === 0 ? (
              <p className="py-10 text-center text-sm text-slate-400">
                Aún no hay claves.
              </p>
            ) : (
              <div className="overflow-hidden rounded-xl border border-slate-100">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-400">
                    <tr>
                      <th className="px-4 py-2 font-medium">Nombre</th>
                      <th className="px-4 py-2 font-medium">Prefijo</th>
                      <th className="px-4 py-2 font-medium">Caduca</th>
                      <th className="px-4 py-2 font-medium">Estado</th>
                      <th className="px-4 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {tokens.map((item) => (
                      <tr key={item.id} className="border-t border-slate-100">
                        <td className="px-4 py-2 font-semibold text-slate-700">
                          {item.name}
                        </td>
                        <td className="px-4 py-2 font-mono text-slate-500">
                          {item.token_prefix}
                        </td>
                        <td className="px-4 py-2 text-slate-500">
                          {formatDate(item.expires_at)}
                        </td>
                        <td className="px-4 py-2">
                          {item.revoked_at ? "Revocada" : "Activa"}
                        </td>
                        <td className="px-4 py-2 text-right">
                          {!item.revoked_at && (
                            <button
                              type="button"
                              onClick={() =>
                                void handleRevoke(
                                  item.id,
                                  tab === "api-keys" ? "api_key" : "access",
                                )
                              }
                              className="inline-flex items-center gap-1 text-red-600"
                            >
                              <Trash2 size={12} /> Revocar
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {tab === "usage" && (
          <div className="grid max-w-3xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Documentos", usage?.documents ?? 0],
              ["Conversaciones", usage?.conversations ?? 0],
              ["Llamadas API", usage?.api_calls ?? 0],
              ["Tokens activos", usage?.active_tokens ?? 0],
            ].map(([label, value]) => (
              <div
                key={String(label)}
                className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3"
              >
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  {label}
                </p>
                <p className="mt-1 text-2xl font-bold text-slate-800">{value}</p>
              </div>
            ))}
          </div>
        )}

        {tab === "projects" && (
          <div>
            <p className="mb-3 text-sm text-slate-600">
              Bases de conocimiento (proyectos) de tu organización.
            </p>
            {!knowledgeBases?.length ? (
              <p className="py-10 text-center text-sm text-slate-400">
                No hay proyectos todavía.
              </p>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2">
                {(
                  knowledgeBases as Array<{
                    id: string;
                    name?: string;
                    description?: string;
                  }>
                ).map((project) => (
                  <li
                    key={project.id}
                    className="rounded-xl border border-slate-100 bg-slate-50 p-4"
                  >
                    <p className="text-sm font-semibold text-slate-800">
                      {project.name || "Proyecto"}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {project.description || "Base de conocimiento RAG"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
