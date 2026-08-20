import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Camera, Copy, Search, Trash2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useOrganization } from "@/context/OrganizationContext";
import { useTranslation } from "@/i18n/I18nProvider";
import { SETTINGS_TAB_KEYS, type SettingsTab } from "@/lib/nav";
import AccountService, {
  type AccessTokenItem,
  type AccountUsage,
  type ManagedUser,
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

const CROP_OPTIONS = [
  { value: "Plátano", labelKey: "settingsExtended.cropBanana" },
  { value: "Aguacate", labelKey: "settingsExtended.cropAvocado" },
  { value: "Papa", labelKey: "settingsExtended.cropPotato" },
  { value: "Tomate", labelKey: "settingsExtended.cropTomato" },
  { value: "Uva", labelKey: "settingsExtended.cropGrape" },
  { value: "Otro", labelKey: "settingsExtended.cropOther" },
];

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
  return SETTINGS_TAB_KEYS.some((tab) => tab.id === value);
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
  const { t, changeLanguage, language } = useTranslation();
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
  const [createdPrefix, setCreatedPrefix] = useState<string | null>(null);
  const [tokenName, setTokenName] = useState("");
  const [usage, setUsage] = useState<AccountUsage | null>(null);
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [usersAdmin, setUsersAdmin] = useState(false);
  const [userQuery, setUserQuery] = useState("");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const setTab = (next: SettingsTab) => {
    setSearchParams({ tab: next });
    setMessage(null);
    setError(null);
    setCreatedToken(null);
    setCreatedPrefix(null);
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
        const lang = data.preferred_language === "en" ? "en" : "es";
        if (lang !== language) {
          changeLanguage(lang);
        }
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
    if (tab === "usage" || tab === "billing") {
      void AccountService.usage()
        .then(setUsage)
        .catch(() => setUsage(null));
    }
    if (tab === "users") {
      void AccountService.listUsers(selectedOrg?.id, userQuery)
        .then((page) => {
          setUsers(page.items);
          setUsersAdmin(page.is_admin);
          setSelectedUserId((current) => {
            if (current && page.items.some((item) => item.id === current)) {
              return current;
            }
            return page.items[0]?.id ?? user?.id ?? null;
          });
        })
        .catch(() => {
          setUsers([]);
          setUsersAdmin(false);
        });
    }
  }, [tab, selectedOrg?.id, userQuery, user?.id]);

  const title = useMemo(
    () =>
      SETTINGS_TAB_KEYS.find((item) => item.id === tab)
        ? t(SETTINGS_TAB_KEYS.find((item) => item.id === tab)!.labelKey)
        : t("common.settings"),
    [tab, t],
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
      setError(detail || t("auth.unexpectedError"));
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
        name: tokenName || (kind === "api_key" ? t("settingsExtended.defaultApiKeyName") : t("settingsExtended.defaultTokenName")),
        kind,
        expires_days: kind === "api_key" ? 365 : 30,
      });
      setCreatedToken(created.token);
      setCreatedPrefix(created.prefix || created.token_prefix || null);
      setTokenName("");
      setTokens(await AccountService.listTokens(kind));
      setMessage(created.note || t("settingsExtended.tokenGenerated"));
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail || t("settingsExtended.tokenGenerateFailed"));
    } finally {
      setSaving(false);
    }
  };

  const handleRevoke = async (id: string, kind: "access" | "api_key") => {
    try {
      await AccountService.revokeToken(id);
      setTokens(await AccountService.listTokens(kind));
      setMessage(t("settingsExtended.tokenRevoked"));
    } catch {
      setError(t("settingsExtended.tokenRevokeFailed"));
    }
  };

  const copyValue = async (value: string, label: string) => {
    await navigator.clipboard.writeText(value);
    setMessage(t("settingsExtended.copiedToClipboard", { label }));
  };

  return (
    <div className="flex flex-col gap-4 pb-8">
      <div className="flex flex-wrap gap-2">
        {SETTINGS_TAB_KEYS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition ${
              tab === item.id
                ? "bg-[color:var(--agro-primary)] text-white shadow-sm"
                : "bg-white text-slate-600 ring-1 ring-[color:var(--agro-border)] hover:text-[color:var(--agro-primary)]"
            }`}
          >
            {t(item.labelKey)}
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-[color:var(--agro-border)] bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-lg font-bold text-slate-900">{title}</h1>
          {(tab === "authenticate" || tab === "api-keys") && (
            <button
              type="button"
              disabled={saving}
              onClick={() =>
                void handleCreateToken(tab === "api-keys" ? "api_key" : "access")
              }
              className="rounded-lg bg-[color:var(--agro-primary)] px-3 py-2 text-xs font-bold text-white hover:bg-[color:var(--agro-primary-hover)] disabled:opacity-50"
            >
              {saving ? t("settingsExtended.generating") : t("settingsExtended.generateNewKey")}
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
                <Camera size={13} /> {t("settingsExtended.changePhoto")}
              </button>
              {avatarPreview && (
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => void handleDeleteAvatar()}
                  className="text-[11px] font-medium text-red-600"
                >
                  {t("settingsExtended.removePhoto")}
                </button>
              )}
              <p className="text-center text-[10px] text-slate-400">
                {t("settingsExtended.photoHint")}
              </p>
            </div>

            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-xs font-semibold text-slate-600">
                  {t("settingsExtended.displayName")}
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  {t("settingsExtended.jobTitle")}
                  <input
                    value={profile.job_title}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        job_title: event.target.value,
                      }))
                    }
                    placeholder={t("settingsExtended.jobPlaceholder")}
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600 sm:col-span-2">
                  {t("settingsExtended.email")}
                  <input
                    value={user?.email || ""}
                    disabled
                    className="mt-1 h-10 w-full rounded-md border border-slate-100 bg-slate-50 px-3 text-sm text-slate-500"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  {t("settingsExtended.phone")}
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
                  {t("settingsExtended.island")}
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
                    <option value="">{t("settingsExtended.unspecified")}</option>
                    {ISLANDS.map((island) => (
                      <option key={island} value={island}>
                        {island}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  {t("settingsExtended.municipality")}
                  <input
                    value={profile.municipality}
                    onChange={(event) =>
                      setProfile((current) => ({
                        ...current,
                        municipality: event.target.value,
                      }))
                    }
                    placeholder={t("settingsExtended.municipalityPlaceholder")}
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  {t("settingsExtended.mainCrop")}
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
                    <option value="">{t("settingsExtended.unspecified")}</option>
                    {CROP_OPTIONS.map((crop) => (
                      <option key={crop.value} value={crop.value}>
                        {t(crop.labelKey)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs font-semibold text-slate-600 sm:col-span-2">
                  {t("settingsExtended.aboutYou")}
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
                    placeholder={t("settingsExtended.bioPlaceholder")}
                    className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                  />
                  <span className="mt-1 block text-[10px] font-normal text-slate-400">
                    {profile.bio.length}/500
                  </span>
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  {t("common.language")}
                  <select
                    value={profile.preferred_language}
                    onChange={(event) => {
                      const lang = event.target.value as "es" | "en";
                      setProfile((current) => ({
                        ...current,
                        preferred_language: lang,
                      }));
                      changeLanguage(lang);
                    }}
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
                  >
                    <option value="es">{t("common.languageEs")}</option>
                    <option value="en">{t("common.languageEn")}</option>
                  </select>
                </label>
              </div>

              <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4">
                <p className="text-xs font-bold text-slate-700">{t("settingsExtended.notifications")}</p>
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
                  {t("settingsExtended.notifyEmail")}
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
                  {t("settingsExtended.notifyWhatsapp")}
                </label>
              </div>

              <p className="text-xs text-slate-400">
                {t("settingsExtended.emailHint")}
              </p>
              <button
                type="button"
                disabled={saving || name.trim().length < 2}
                onClick={() => void handleSaveProfile()}
                className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white disabled:opacity-50"
              >
                {saving ? t("common.saving") : t("settingsExtended.saveProfile")}
              </button>
            </div>
          </div>
        )}

        {(tab === "authenticate" || tab === "api-keys") && (
          <div className="space-y-4">
            <p className="max-w-2xl text-sm text-slate-600">
              {tab === "authenticate"
                ? t("settingsExtended.authHint")
                : t("settingsExtended.apiKeysHint")}
            </p>
            <input
              value={tokenName}
              onChange={(event) => setTokenName(event.target.value)}
              placeholder={
                tab === "api-keys" ? t("settingsExtended.keyName") : t("settingsExtended.tokenName")
              }
              className="h-9 max-w-sm rounded-md border border-slate-200 px-3 text-xs"
            />
            {createdToken && (
              <div className="overflow-hidden rounded-xl border border-[color:var(--agro-border)]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[color:var(--agro-pill)] text-slate-600">
                    <tr>
                      <th className="px-4 py-2 font-semibold">Access Key</th>
                      <th className="px-4 py-2 font-semibold">Secret Key</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-t border-slate-100">
                      <td className="px-4 py-3 font-mono text-slate-700">
                        <span className="mr-2">{createdPrefix || "agro_key"}</span>
                        <button
                          type="button"
                          onClick={() => void copyValue(createdPrefix || "", "Access Key")}
                          className="inline-flex text-slate-400 hover:text-[color:var(--agro-primary)]"
                        >
                          <Copy size={13} />
                        </button>
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-700">
                        <span className="mr-2 break-all">{createdToken}</span>
                        <button
                          type="button"
                          onClick={() => void copyValue(createdToken, "Secret Key")}
                          className="inline-flex text-slate-400 hover:text-[color:var(--agro-primary)]"
                        >
                          <Copy size={13} />
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <p className="border-t border-slate-100 bg-amber-50 px-4 py-2 text-[11px] text-amber-800">
                  {t("settingsExtended.copySecretNow")}
                </p>
              </div>
            )}
            {tokens.length === 0 && !createdToken ? (
              <p className="py-16 text-center text-sm text-slate-400">
                {t("support.noResults")}
              </p>
            ) : tokens.length > 0 ? (
              <div className="overflow-hidden rounded-xl border border-slate-100">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-400">
                    <tr>
                      <th className="px-4 py-2 font-medium">{t("common.name")}</th>
                      <th className="px-4 py-2 font-medium">Access Key</th>
                      <th className="px-4 py-2 font-medium">{t("settingsExtended.expires")}</th>
                      <th className="px-4 py-2 font-medium">{t("settingsExtended.status")}</th>
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
                          {item.revoked_at ? t("settingsExtended.revoked") : t("settingsExtended.active")}
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
                              <Trash2 size={12} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        )}

        {tab === "usage" && (
          <div className="grid max-w-3xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              [t("dashboardWidgets.documents"), usage?.documents ?? 0],
              [t("dashboardWidgets.conversations"), usage?.conversations ?? 0],
              [t("settingsExtended.apiCalls"), usage?.api_calls ?? 0],
              [t("settingsExtended.activeTokens"), usage?.active_tokens ?? 0],
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

        {tab === "billing" && (
          <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-xl border border-[color:var(--agro-border)] p-5">
              <p className="text-xs font-bold uppercase tracking-wide text-[color:var(--agro-primary)]">
                {t("settingsExtended.currentPlan")}
              </p>
              <h2 className="mt-1 text-xl font-bold text-slate-900">{t("settingsExtended.planName")}</h2>
              <p className="mt-2 text-sm text-slate-600">
                {t("settingsExtended.billingDesc")}
              </p>
              <p className="mt-4 text-3xl font-bold text-slate-900">0,00 €</p>
              <p className="text-xs text-slate-400">{t("settingsExtended.billingPeriod")}</p>
            </div>
            <div className="rounded-xl border border-[color:var(--agro-border)] p-5">
              <p className="text-sm font-semibold text-slate-800">{t("settingsExtended.estimatedUsage")}</p>
              <ul className="mt-3 space-y-2 text-sm text-slate-600">
                <li className="flex justify-between">
                  <span>{t("settingsExtended.indexedDocs")}</span>
                  <span className="font-semibold">{usage?.documents ?? 0}</span>
                </li>
                <li className="flex justify-between">
                  <span>{t("dashboardWidgets.conversations")}</span>
                  <span className="font-semibold">{usage?.conversations ?? 0}</span>
                </li>
                <li className="flex justify-between">
                  <span>{t("settingsExtended.apiCalls")}</span>
                  <span className="font-semibold">{usage?.api_calls ?? 0}</span>
                </li>
                <li className="flex justify-between border-t border-slate-100 pt-2">
                  <span>{t("settingsExtended.totalDue")}</span>
                  <span className="font-bold text-[color:var(--agro-primary)]">0,00 €</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {tab === "users" && (
          <div className="space-y-4">
            <div className="relative max-w-md">
              <Search
                size={15}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                value={userQuery}
                onChange={(event) => setUserQuery(event.target.value)}
                placeholder={t("settingsExtended.searchUser")}
                className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-[color:var(--agro-primary)]"
              />
            </div>
            {users.length === 0 ? (
              <p className="py-16 text-center text-sm text-slate-400">No Results Found</p>
            ) : (
              <div className="overflow-hidden rounded-xl border border-slate-100">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-400">
                    <tr>
                      <th className="px-4 py-2 font-medium">{t("common.name")}</th>
                      <th className="px-4 py-2 font-medium">{t("settingsExtended.email")}</th>
                      <th className="px-4 py-2 font-medium">{t("settingsExtended.role")}</th>
                      <th className="px-4 py-2 font-medium">{t("settingsExtended.status")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((item) => (
                      <tr key={item.id} className="border-t border-slate-100">
                        <td className="px-4 py-2 font-semibold text-slate-800">
                          {item.name}
                          {item.is_self ? (
                            <span className="ml-2 rounded-full bg-[color:var(--agro-pill)] px-2 py-0.5 text-[10px] text-[color:var(--agro-primary)]">
                              {t("settingsExtended.you")}
                            </span>
                          ) : null}
                        </td>
                        <td className="px-4 py-2 text-slate-500">{item.email}</td>
                        <td className="px-4 py-2 text-slate-500">
                          {item.role || (usersAdmin ? t("settingsExtended.member") : t("settingsExtended.account"))}
                        </td>
                        <td className="px-4 py-2">
                          {item.active === false ? t("settingsExtended.inactive") : t("settingsExtended.active")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
