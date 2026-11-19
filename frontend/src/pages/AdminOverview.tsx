import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { KATEGORI_META, fmt } from "@/features/inklusi/theme";
import { STATUS_LABEL } from "@/features/inklusi/Inquiry";

const Stat = ({ l, v, c = "#232F3E", to = "" }: any) => {
  const body = (
    <div className="flex h-full min-w-0 flex-col justify-between rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200" style={{ borderTop: `4px solid ${c}` }}>
      <p className="text-[11px] font-bold uppercase tracking-wide text-slate-600">{l}</p>
      <p className="mt-1 font-head text-2xl font-extrabold tabular-nums text-slate-900">{fmt(v)}</p>
    </div>
  );
  return to ? <Link to={to} className="block h-full">{body}</Link> : body;
};

export default function AdminOverview() {
  const { user } = useAuth();
  const [d, setD] = useState<any>(null);
  useEffect(() => { api.get("/inklusi/admin/overview").then((r) => setD(r.data)).catch(() => setD(false)); }, []);
  if (d === false) return <p className="text-red-700">Gagal memuat dashboard admin.</p>;
  if (!d) return <p className="text-slate-500">Memuat…</p>;
  return (
    <div className="space-y-5" data-testid="admin-overview">
      <div><p className="font-head text-[clamp(1.25rem,1rem+1vw,1.5rem)] font-extrabold leading-tight text-[#232F3E]">Dashboard Admin PETA INKLUSI</p><p className="text-sm text-slate-600">Selamat datang, {user?.name}.</p></div>
      <div className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-2 lg:grid-cols-4">
        <Stat l="Total Disabilitas" v={d.totals.disabilitas} c={KATEGORI_META.disabilitas.warna} to="/disabilitas" />
        <Stat l="Total Stunting" v={d.totals.stunting} c={KATEGORI_META.stunting.warna} to="/data-stunting" />
        <Stat l="Total ATS" v={d.totals.ats} c={KATEGORI_META.ats.warna} to="/data-ats" />
        <Stat l="KK Miskin Ekstrem" v={d.totals.kemiskinan} c={KATEGORI_META.kemiskinan.warna} to="/sosial" />
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        <Stat l="NGO terdaftar" v={d.ngo.total} to="/kelola-petugas" /><Stat l="NGO menunggu aktivasi" v={d.ngo.menunggu} c="#F4B63A" to="/kelola-petugas" />
        <Stat l="Total inquiry" v={d.inquiry.total} to="/ngo/inquiry" /><Stat l="Inquiry pending" v={d.inquiry.pending} c="#C8375B" to="/ngo/inquiry" />
        <Stat l="Inquiry diproses" v={d.inquiry.diproses} c="#117A69" to="/ngo/inquiry" /><Stat l="Inquiry selesai" v={d.inquiry.selesai} c="#232F3E" to="/ngo/inquiry" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <section className="min-w-0 rounded-xl border border-slate-200 bg-white p-4"><h2 className="mb-2 font-head text-sm font-extrabold uppercase text-[#232F3E]">Distribusi data per kecamatan</h2>
          <div className="h-[350px]"><ResponsiveContainer><BarChart data={d.per_kecamatan} margin={{ left: 0, right: 8, bottom: 64 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="kecamatan" angle={-35} textAnchor="end" interval={0} height={72} fontSize={10} /><YAxis fontSize={10} /><Tooltip /><Legend verticalAlign="top" />
            {(["disabilitas", "stunting", "ats", "kemiskinan"] as const).map((k) => <Bar key={k} dataKey={k} name={KATEGORI_META[k].label} fill={KATEGORI_META[k].warna} stackId="a" />)}</BarChart></ResponsiveContainer></div></section>
        <section className="min-w-0 rounded-xl border border-slate-200 bg-white p-4"><h2 className="mb-2 font-head text-sm font-extrabold uppercase text-[#232F3E]">Inquiry per status</h2>
          <ul className="space-y-1.5">{d.inquiry.per_status.map((s: any) => (<li key={s.status} className="flex items-center gap-2 text-sm"><span className="w-32 shrink-0 text-xs text-slate-700 sm:w-40 sm:text-sm">{STATUS_LABEL[s.status]}</span>
            <span className="flex min-w-0 flex-1 items-center gap-2"><span className="h-3 rounded bg-[#117A69]" style={{ width: `${Math.min(100, s.jumlah * 12)}%`, minWidth: s.jumlah ? 8 : 0 }} /><b className="shrink-0 tabular-nums">{s.jumlah}</b></span></li>))}</ul></section>
      </div>
      <section className="min-w-0 rounded-xl border border-slate-200 bg-white p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-head text-sm font-extrabold uppercase text-[#232F3E]">Aktivitas sistem terbaru</h2><Link to="/audit-log" className="text-xs font-bold text-[#117A69] underline">Lihat audit log</Link></div>
        <div className="table-scroll mt-2"><table className="w-full min-w-[560px] text-xs"><thead className="bg-slate-50 text-left text-slate-500"><tr><th className="px-2 py-1.5">Waktu</th><th className="px-2 py-1.5">Pengguna</th><th className="px-2 py-1.5">Aktivitas</th><th className="px-2 py-1.5">Resource</th><th className="px-2 py-1.5">Status</th></tr></thead>
          <tbody>{d.audit_terbaru.map((a: any, i: number) => <tr key={i} className="border-t"><td className="whitespace-nowrap px-2 py-1.5">{new Date(a.created_at).toLocaleString("id-ID")}</td><td className="px-2 py-1.5">{a.user}</td><td className="px-2 py-1.5 font-semibold">{a.aksi}</td><td className="px-2 py-1.5">{a.entitas}</td><td className="px-2 py-1.5">{a.status || "sukses"}</td></tr>)}</tbody></table></div></section>
    </div>
  );
}
