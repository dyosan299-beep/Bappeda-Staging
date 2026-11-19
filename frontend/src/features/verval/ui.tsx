import React from "react";
import { STATUS_CLS, STATUS_LABEL } from "./api";

export function StatusBadge({ status, testid }: { status: string; testid?: string }) {
  return (
    <span data-testid={testid} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold ring-1 ${STATUS_CLS[status] || STATUS_CLS.belum_diverval}`}>
      {STATUS_LABEL[status] || status}
    </span>
  );
}

export function UjiBadge({ show }: { show?: boolean }) {
  if (!show) return null;
  return <span className="inline-flex items-center rounded-full bg-fuchsia-50 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-fuchsia-800 ring-1 ring-fuchsia-200" data-testid="badge-data-uji">Data UJI</span>;
}

export function Card({ children, className = "", ...rest }: any) {
  return <section className={`rounded-[16px] bg-white p-4 shadow-sm ring-1 ring-slate-200 ${className}`} {...rest}>{children}</section>;
}

export function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block text-xs font-semibold text-slate-700">
      {label}
      <div className="mt-1">{children}</div>
      {hint && <p className="mt-1 text-[11px] font-normal text-slate-500">{hint}</p>}
    </label>
  );
}

export const INPUT = "w-full rounded-[10px] border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-[#117A69] focus:outline-none focus:ring-2 focus:ring-[#6FE3CF]/50";

export function DtsenNilai({ vals }: { vals: any[] }) {
  if (!vals || !vals.length) return <span className="text-slate-400">tidak tercatat</span>;
  return (
    <span>
      {vals.map((v, i) => (
        <span key={i} className="mr-2 inline-block">
          <span className="text-slate-500">{v.field.replace(/_/g, " ")}:</span>{" "}
          <b className="text-slate-900">{String(v.nilai)}</b>{v.label ? ` (${v.label})` : ""}
        </span>
      ))}
    </span>
  );
}
