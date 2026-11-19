import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ShieldCheck, Map } from "lucide-react";
import PublicLayout from "@/components/PublicLayout";
import api from "@/lib/api";
import { KATEGORI_META, fmt, Kategori } from "@/features/inklusi/theme";
import { ProgramGallery } from "@/features/inklusi/InklusiExtra";
import { ChartA11y, SpeakMini } from "@/features/a11y/components";
import { buatNarasi } from "@/features/a11y/narasi";
import { BTN_PRIMARY } from "@/features/a11y/ui";

const KATS: Kategori[] = ["disabilitas", "stunting", "ats", "kemiskinan"];

function Card({ title, children, className = "", id, speak }: any) {
  return (
    <section id={id} tabIndex={id ? -1 : undefined} aria-labelledby={id ? `${id}-judul` : undefined}
      className={`min-w-0 rounded-[16px] border border-slate-200 bg-white p-4 shadow-[0_6px_18px_rgba(35,47,62,.05)] focus:outline-none focus-visible:ring-4 focus-visible:ring-[#F4B63A] sm:p-5 ${className}`}>
      <div className="mb-4 flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <h2 id={id ? `${id}-judul` : undefined} className="flex min-w-0 items-center gap-2 font-head text-sm font-extrabold uppercase tracking-wide text-[#232F3E]"><span className="h-4 w-1 shrink-0 rounded-full bg-[#117A69]" aria-hidden="true" /><span className="min-w-0 break-words">{title}</span></h2>
        {speak && <SpeakMini text={`${title}. ${speak}`} label={title} testid={id ? `speak-${id}` : undefined} />}
      </div>
      {children}
    </section>
  );
}

export function PublicDashboardContent({ headingTag: Heading = "h1" }: { headingTag?: "h1" | "p" } = {}) {
  const [s, setS] = useState<any>(null);
  const [st, setSt] = useState<any>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    api.get("/public/summary").then((r) => setS(r.data)).catch(() => setErr(true));
    api.get("/public/stunting/breakdown").then((r) => setSt(r.data)).catch(() => {});
  }, []);
  if (err) return <p className="p-8 text-center text-red-700">Gagal memuat data. Silakan muat ulang halaman.</p>;
  if (!s) return <p className="p-8 text-center text-slate-600" aria-live="polite">Memuat data agregat…</p>;
  const k = s.kategori;
  const nr = buatNarasi("publik", s, st);
  const teks = (id: string) => nr?.bagian.find((b) => b.id === id)?.teks || "";
  const perKec = s.per_kecamatan || [];
  return (
    <div className="space-y-5" data-testid="public-dashboard">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Heading className="font-head text-3xl font-extrabold text-[#232F3E]">Dashboard Informasi Umum</Heading>
          <p className="mt-1 text-sm text-slate-600">Kota Makassar · {s.wilayah.kecamatan} kecamatan · {s.wilayah.kelurahan} kelurahan</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-[#E6FAF6] px-4 py-1 text-xs font-semibold text-[#0B4F45] ring-1 ring-[#117A69]/15" data-testid="public-privacy-badge">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" /> Hanya data agregat — tanpa data pribadi</p>
          <SpeakMini variant="pill" pillLabel="Dengarkan pengantar" text={nr?.pembuka || ""} label="pengantar dashboard" testid="speak-publik-pembuka" />
        </div>
      </div>

      <section id="a11y-ringkasan" tabIndex={-1} aria-label="Ringkasan empat kategori" className="grid gap-4 focus:outline-none sm:grid-cols-2 lg:grid-cols-4">
        {KATS.map((c) => (
          <div key={c} className="rounded-[16px] bg-white p-5 shadow-[0_6px_18px_rgba(35,47,62,.05)] ring-1 ring-slate-200" style={{ borderLeft: `6px solid ${KATEGORI_META[c].warna}` }} data-testid={`public-card-${c}`}>
            <div className="flex items-start justify-between gap-2">
              <h2 className="text-xs font-extrabold uppercase tracking-wider" style={{ color: KATEGORI_META[c].warna }}>{KATEGORI_META[c].label}</h2>
              <SpeakMini text={`${KATEGORI_META[c].label}: ${fmt(k[c].total)} ${k[c].satuan}. Sumber: ${k[c].sumber}.`} label={`data ${KATEGORI_META[c].label}`} testid={`speak-card-${c}`} />
            </div>
            <p className="mt-1 font-head text-3xl font-extrabold text-slate-900">{fmt(k[c].total)}</p>
            <p className="text-xs text-slate-600">{k[c].satuan}{c === "kemiskinan" && k[c].persen_kota ? ` · ${k[c].persen_kota}% penduduk miskin (2025)` : ""}</p>
            <p className="mt-2 text-[10.5px] text-slate-500">Sumber: {k[c].sumber}</p>
            {c === "stunting" && <p className="text-[10.5px] text-slate-500">{fmt(k[c].terdata_by_name)} balita terdata by-name (Kec. Makassar & Tallo 2026)</p>}
            {c === "ats" && k[c].catatan && <p className="text-[10.5px] text-slate-500">{k[c].catatan} (rincian: {fmt(k[c].total_rincian_kecamatan)})</p>}
          </div>
        ))}
      </section>

      <section id="a11y-wilayah" tabIndex={-1} aria-label="Wilayah dan DTSEN" className="grid gap-4 focus:outline-none sm:grid-cols-3">
        {[["Kecamatan", s.wilayah.kecamatan], ["Kelurahan", s.wilayah.kelurahan], ["Rumah tangga DTSEN terdata", s.dtsen.rumah_tangga], ["Individu DTSEN terdata", s.dtsen.individu], ["Kelurahan dengan data DTSEN", s.dtsen.kelurahan_terdata]].slice(0, 3).map(([l, v]: any) => (
          <div key={l} className="rounded-[16px] bg-[#232F3E] p-5 text-white shadow-[0_10px_24px_rgba(35,47,62,.18)]"><p className="text-xs uppercase tracking-wider text-[#6FE3CF]">{l}</p><p className="font-head text-2xl font-extrabold">{fmt(v)}</p></div>
        ))}
      </section>

      <Card title="Statistik per kecamatan (4 kategori)" id="a11y-statistik" speak={teks("a11y-statistik")}>
        <ChartA11y judul="Statistik per kecamatan (4 kategori)" ringkasan={teks("a11y-statistik")} testid="chart-kecamatan"
          kolom={["Kecamatan", "Disabilitas", "Stunting", "ATS", "KK miskin ekstrem"]}
          baris={perKec.map((r: any) => [r.kecamatan, r.disabilitas, r.stunting, r.ats, r.kemiskinan])}>
          <div className="h-[370px]">
            <ResponsiveContainer>
              <BarChart data={s.per_kecamatan} margin={{ left: 0, right: 8, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="kecamatan" angle={-35} textAnchor="end" interval={0} height={72} fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip formatter={(v: any) => fmt(v)} />
                <Legend verticalAlign="top" />
                {KATS.map((c) => <Bar key={c} dataKey={c} name={KATEGORI_META[c].label} fill={KATEGORI_META[c].warna} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartA11y>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Perkembangan kemiskinan kota (%)" id="a11y-tren-kemiskinan" speak={teks("a11y-tren-kemiskinan")}>
          <ChartA11y judul="Perkembangan kemiskinan kota (%)" ringkasan={teks("a11y-tren-kemiskinan")} testid="chart-kemiskinan"
            kolom={["Tahun", "% penduduk miskin"]} baris={(s.tren.kemiskinan || []).map((r: any) => [String(r.tahun), `${Number(r.persen).toLocaleString("id-ID")}%`])}>
            <div className="h-[240px]"><ResponsiveContainer><LineChart data={s.tren.kemiskinan}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="tahun" /><YAxis domain={[3, 6]} /><Tooltip /><Line dataKey="persen" name="% penduduk miskin" stroke="#3B4F6B" strokeWidth={3} /></LineChart></ResponsiveContainer></div>
          </ChartA11y>
        </Card>
        <Card title="Perkembangan prevalensi stunting (%)" id="a11y-tren-stunting" speak={teks("a11y-tren-stunting")}>
          <ChartA11y judul="Perkembangan prevalensi stunting (%)" ringkasan={teks("a11y-tren-stunting")} testid="chart-stunting"
            kolom={["Tahun", "SSGI (%)", "e-PPGBM (%)"]} baris={(s.tren.stunting || []).map((r: any) => [String(r.tahun), r.ssgi_persen ?? "-", r.eppgbm_persen ?? "-"])}>
            <div className="h-[240px]"><ResponsiveContainer><LineChart data={s.tren.stunting}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="tahun" /><YAxis /><Tooltip /><Legend /><Line dataKey="ssgi_persen" name="SSGI" stroke="#C8375B" strokeWidth={3} /><Line dataKey="eppgbm_persen" name="e-PPGBM" stroke="#F4B63A" strokeWidth={3} /></LineChart></ResponsiveContainer></div>
          </ChartA11y>
        </Card>
        <Card title="Anak Tidak Sekolah per tahun" id="a11y-ats" speak={teks("a11y-ats")}>
          <ChartA11y judul="Anak Tidak Sekolah per tahun" ringkasan={teks("a11y-ats")} testid="chart-ats"
            kolom={["Tahun", "ATS SD", "ATS SMP"]} baris={(s.tren.ats || []).map((r: any) => [String(r.tahun), r.ats_sd, r.ats_smp])}>
            <div className="h-[240px]"><ResponsiveContainer><BarChart data={s.tren.ats}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="tahun" /><YAxis /><Tooltip formatter={(v: any) => fmt(v)} /><Legend /><Bar dataKey="ats_sd" name="ATS SD" fill="#F4B63A" /><Bar dataKey="ats_smp" name="ATS SMP" fill="#B7791F" /></BarChart></ResponsiveContainer></div>
          </ChartA11y>
        </Card>
        <Card title="Balita stunting 2026 (Kec. Makassar & Tallo)" id="a11y-balita" speak={teks("a11y-balita")}>
          {st ? (
            <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              {[["Status TB/U", st.status_tbu], ["Jenis kelamin", st.jenis_kelamin], ["Kelompok umur", st.kelompok_umur], ["Per kecamatan", st.per_kecamatan]].map(([t, arr]: any) => (
                <div key={t}><h3 className="text-xs font-bold text-slate-600">{t}</h3>
                  <ul className="mt-1 space-y-0.5">{arr.map((x: any) => <li key={x.kategori} className="flex justify-between gap-2 text-xs"><span>{x.kategori}</span><b className="shrink-0 tabular-nums">{fmt(x.jumlah)}</b></li>)}</ul>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-slate-500">Memuat…</p>}
        </Card>
      </div>

      <section id="a11y-galeri" tabIndex={-1} aria-label="Galeri program" className="focus:outline-none"><ProgramGallery /></section>

      <Card title="Peta agregat & ringkasan kondisi sosial" id="a11y-kondisi" speak={teks("a11y-kondisi")}>
        <p className="text-sm text-slate-700">
          Kecamatan dengan KK miskin ekstrem terbanyak: <b>{[...s.per_kecamatan].sort((a: any, b: any) => b.kemiskinan - a.kemiskinan)[0]?.kecamatan}</b>;
          stunting terbanyak: <b>{[...s.per_kecamatan].sort((a: any, b: any) => b.stunting - a.stunting)[0]?.kecamatan}</b>;
          ATS terbanyak: <b>{[...s.per_kecamatan].sort((a: any, b: any) => b.ats - a.ats)[0]?.kecamatan}</b>;
          disabilitas terbanyak: <b>{[...s.per_kecamatan].sort((a: any, b: any) => b.disabilitas - a.disabilitas)[0]?.kecamatan}</b>.
        </p>
        <Link to="/publik/peta-sosial" className={`mt-4 ${BTN_PRIMARY}`} data-testid="public-open-map"><Map className="h-4 w-4" aria-hidden="true" /> Buka peta agregat</Link>
        <p className="mt-3 text-xs text-slate-500">{s.catatan}</p>
      </Card>
    </div>
  );
}

export default function PublicDashboard() {
  return <PublicLayout><div className="mx-auto max-w-7xl px-4 py-8"><PublicDashboardContent /></div></PublicLayout>;
}
