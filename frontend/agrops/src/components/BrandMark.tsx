import { useTranslation } from "@/i18n/I18nProvider";

type BrandSize = "sm" | "md" | "lg";

const FLAG_SIZE: Record<BrandSize, string> = {
  sm: "h-6 w-9",
  md: "h-8 w-12",
  lg: "h-10 w-14",
};

const TITLE_SIZE: Record<BrandSize, string> = {
  sm: "text-sm",
  md: "text-base",
  lg: "text-xl",
};

export function CanaryFlag({
  className = "h-7 w-10",
  ariaLabel,
}: {
  className?: string;
  ariaLabel?: string;
}) {
  const { t } = useTranslation();
  return (
    <svg
      viewBox="0 0 3 2"
      className={`overflow-hidden rounded-md border border-slate-200 shadow-sm ${className}`}
      aria-label={ariaLabel ?? t("brand.canaryFlag")}
      role="img"
    >
      <rect width="1" height="2" fill="#ffffff" />
      <rect x="1" width="1" height="2" fill="#0038A8" />
      <rect x="2" width="1" height="2" fill="#FFD100" />
    </svg>
  );
}

export function BrandMark({
  size = "md",
  subtitle,
  className = "",
}: {
  size?: BrandSize;
  subtitle?: string | null;
  className?: string;
}) {
  const { t } = useTranslation();
  const resolvedSubtitle = subtitle === undefined ? t("brand.subtitle") : subtitle;
  return (
    <div className={`flex min-w-0 items-center gap-2.5 ${className}`}>
      <CanaryFlag className={`${FLAG_SIZE[size]} shrink-0`} />
      <div className="min-w-0">
        <p
          className={`${TITLE_SIZE[size]} truncate font-bold tracking-tight text-slate-900`}
        >
          Agro<span className="text-[color:var(--agro-primary)]">PS</span>
        </p>
        {resolvedSubtitle ? (
          <p className="truncate text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--agro-accent-ink)]">
            {resolvedSubtitle}
          </p>
        ) : null}
      </div>
    </div>
  );
}
