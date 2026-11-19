import React from "react";

export function KpiCard({
  label,
  value,
  hint,
  color = "#0f172a",
  icon,
  onClick,
  testid,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  color?: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  testid?: string;
}) {
  return (
    <div
      data-testid={testid}
      onClick={onClick}
      className={`min-w-0 rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition-shadow ${
        onClick ? "cursor-pointer hover:shadow-md" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
        {icon}
      </div>
      <p className="mt-1 break-words font-head text-xl font-extrabold leading-tight tabular-nums sm:text-2xl" style={{ color }}>
        {value}
      </p>
      {hint && <p className="mt-0.5 break-words text-[11px] text-slate-500">{hint}</p>}
    </div>
  );
}

export function Panel({
  title,
  action,
  children,
  className = "",
  testid,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  testid?: string;
}) {
  return (
    <section
      data-testid={testid}
      className={`min-w-0 rounded-lg border border-slate-200 bg-white p-3 shadow-sm sm:p-4 ${className}`}
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="min-w-0 font-head text-sm font-bold uppercase tracking-wide text-slate-700">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0 max-w-full">
        <p className="font-head text-[clamp(1.125rem,1rem+0.6vw,1.375rem)] font-extrabold leading-tight text-slate-900">{title}</p>
        {subtitle && <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export const RISK_COLORS: Record<string, string> = {
  sangat_tinggi: "#b91c1c",
  tinggi: "#f97316",
  sedang: "#f59e0b",
  rendah: "#16a34a",
};

export const RISK_LABELS: Record<string, string> = {
  sangat_tinggi: "Prioritas Sangat Tinggi",
  tinggi: "Prioritas Tinggi",
  sedang: "Prioritas Sedang",
  rendah: "Prioritas Rendah",
};

export const CHART_COLORS = [
  "#dc2626", "#ea580c", "#f59e0b", "#16a34a", "#0891b2",
  "#4f46e5", "#9333ea", "#db2777", "#0f172a", "#65a30d",
];
