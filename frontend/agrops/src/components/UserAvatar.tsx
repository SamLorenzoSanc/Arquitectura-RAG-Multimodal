export function UserAvatar({
  src,
  name,
  size = 40,
}: {
  src?: string | null;
  name?: string | null;
  size?: number;
}) {
  const initials =
    name
      ?.split(" ")
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "US";

  if (src) {
    return (
      <img
        src={src}
        alt={name || "Avatar"}
        width={size}
        height={size}
        className="rounded-full object-cover"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <span
      className="inline-flex items-center justify-center rounded-full bg-[color:var(--agro-primary)] font-bold text-white"
      style={{ width: size, height: size, fontSize: Math.max(10, size * 0.32) }}
    >
      {initials}
    </span>
  );
}
