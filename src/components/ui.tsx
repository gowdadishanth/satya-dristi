import type { ButtonHTMLAttributes, ReactNode } from "react";
import { IconCheck, IconTriangle, IconClose } from "./icons";

export function cn(...v: Array<string | false | null | undefined>) {
  return v.filter(Boolean).join(" ");
}

/* ---------------- Panel ---------------- */
export function Panel({
  children,
  className,
  raised,
  inset,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  raised?: boolean;
  inset?: boolean;
  as?: React.ElementType;
}) {
  return (
    <Tag className={cn("panel", raised && "panel-raised", inset && "panel-inset", className)}>
      {children}
    </Tag>
  );
}

/* ---------------- Button ---------------- */
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "accent" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
  icon?: ReactNode;
};
export function Button({
  variant = "outline",
  size = "md",
  icon,
  className,
  children,
  ...rest
}: BtnProps) {
  const base =
    "inline-flex items-center justify-center gap-2 font-medium rounded-md transition-colors focus-ring disabled:opacity-45 disabled:pointer-events-none select-none whitespace-nowrap";
  const sizes =
    size === "sm"
      ? "text-[12.5px] px-2.5 h-8"
      : size === "lg"
      ? "text-[14px] px-5 h-11"
      : "text-sm px-4 h-10";
  const variants: Record<string, string> = {
    primary: "bg-primary text-primary-foreground hover:opacity-90",
    accent: "bg-accent text-accent-foreground hover:opacity-90",
    outline: "border border-border bg-transparent hover:bg-muted text-foreground",
    ghost: "hover:bg-muted text-foreground",
  };
  return (
    <button className={cn(base, sizes, variants[variant], className)} {...rest}>
      {icon}
      {children}
    </button>
  );
}

/* ---------------- Badge ---------------- */
export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: "neutral" | "accent" | "ok" | "warn" | "err";
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: "bg-muted text-muted-foreground border-border",
    accent: "bg-accent/10 text-accent border-accent/30",
    ok: "text-[color:var(--ok)] border-[color:var(--ok)]/30 bg-[color:var(--ok)]/8",
    warn: "text-[color:var(--warn)] border-[color:var(--warn)]/30 bg-[color:var(--warn)]/8",
    err: "text-[color:var(--err)] border-[color:var(--err)]/30 bg-[color:var(--err)]/8",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] font-medium leading-none tracking-wide uppercase",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/* ---------------- Eyebrow / label ---------------- */
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("text-[10.5px] font-semibold uppercase tracking-[0.07em] text-muted-foreground", className)}>
      {children}
    </div>
  );
}

/* ---------------- Section title ---------------- */
export function StatDot({ tone }: { tone: "ok" | "warn" | "err" | "idle" }) {
  const c = {
    ok: "var(--ok)",
    warn: "var(--warn)",
    err: "var(--err)",
    idle: "var(--muted-foreground)",
  }[tone];
  return <span className="inline-block h-2 w-2 rounded-full" style={{ background: c }} />;
}

/* ---------------- Confidence component ---------------- */
export type Agreement = { label: string; state: "agree" | "partial" | "absent" };

export function Confidence({
  level,
  agreements,
  compact,
}: {
  level: "High" | "Moderate" | "Low";
  agreements: Agreement[];
  compact?: boolean;
}) {
  const color = { High: "var(--ok)", Moderate: "var(--warn)", Low: "var(--err)" }[level];

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <Eyebrow>Confidence</Eyebrow>
        <span className="inline-flex items-center gap-1.5 text-[15px] font-semibold" style={{ color }}>
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
          {level}
        </span>
      </div>
      {!compact && (
        <>
          <div className="mt-3">
            <Eyebrow>Model agreement</Eyebrow>
            <dl className="mt-1.5 divide-y divide-border rounded-md border border-border">
              {agreements.map((a) => (
                <div key={a.label} className="flex items-center justify-between px-2.5 py-1.5">
                  <dt className="text-[12px] text-muted-foreground">{a.label}</dt>
                  <dd>
                    {a.state === "agree" && <IconCheck className="h-4 w-4" style={{ color: "var(--ok)" }} />}
                    {a.state === "partial" && <IconTriangle className="h-4 w-4" style={{ color: "var(--warn)" }} />}
                    {a.state === "absent" && <IconClose className="h-4 w-4 text-muted-foreground" />}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
          <p className="mt-2.5 text-[12px] leading-relaxed text-muted-foreground">
            {level === "Moderate"
              ? "SAR shows partial agreement with the optical and fused predictions; treat the magnitude of change as indicative."
              : "Confidence reflects agreement between available specialist predictions."}
          </p>
        </>
      )}
    </div>
  );
}
