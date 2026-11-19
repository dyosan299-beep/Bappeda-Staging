import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Map, BarChart3, Send, ShieldCheck } from "lucide-react";
import PublicLayout from "@/components/PublicLayout";
import api from "@/lib/api";
import { KATEGORI_META, fmt } from "@/features/inklusi/theme";
import { ProgramGallery } from "@/features/inklusi/InklusiExtra";
import { SpeakMini } from "@/features/a11y/components";
import { buatNarasi } from "@/features/a11y/narasi";
import { FR } from "@/features/a11y/ui";

export default function Landing() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/public/summary").then((r) => setS(r.data)).catch(() => {}); }, []);
  const kat = s?.kategori || {};
  const nr = buatNarasi("beranda", s, null);
  const teks = (id) => nr?.bagian.find((b) => b.id === id)?.teks || "";
  return (
    <PublicLayout>
      <section id="a11y-pengantar" tabIndex={-1} className="bg-[#232F3E] text-white focus:outline-none" data-testid="landing-hero">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-14 md:grid-cols-[1.2fr_1fr]">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#6FE3CF]">Bappeda Kota Makassar</p>
            <h1 className="mt-3 font-head text-4xl font-extrabold leading-tight md:text-5xl">
              PETA INKLUSI<span className="mt-2 block text-xl font-bold leading-snug text-slate-300 md:text-2xl" data-testid="landing-hero-tagline">Penguatan Perencanaan Pembangunan Inklusi melalui Pemetaan Data Tematik dan Evaluasi Program pada Kelompok Rentan.</span>
            </h1>
            <p className="mt-4 max-w-xl text-slate-300">
              Satu platform untuk membaca kondisi <b className="text-[#6FE3CF]">Disabilitas</b>, <b className="text-[#F08BA4]">Stunting</b>,{" "}
              <b className="text-[#F4B63A]">Anak Tidak Sekolah</b>, dan <b className="text-white">Kemiskinan</b> hingga tingkat kelurahan —
              dari data, analisis, sampai usulan program intervensi.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Link to="/publik" data-testid="hero-dashboard-btn" className={`group inline-flex min-h-12 items-center gap-2 rounded-full bg-[#6FE3CF] px-6 py-3 font-bold text-[#232F3E] shadow-[0_12px_30px_rgba(111,227,207,.25)] transition-colors hover:bg-[#8FEBDB] active:bg-[#5FD6C1] ${FR}`}>
                Dashboard Informasi Umum <ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>
              <Link to="/publik/peta-sosial" data-testid="hero-peta-btn" className={`inline-flex min-h-12 items-center gap-2 rounded-full bg-white/5 px-6 py-3 font-bold text-white ring-1 ring-white/30 transition-colors hover:bg-white/10 active:bg-white/15 ${FR}`}>
                <Map className="h-4 w-4" aria-hidden="true" /> Jelajahi Peta Sosial</Link>
            </div>
            <div className="mt-4 flex items-center gap-3 border-t border-white/10 pt-4">
              <SpeakMini tone="dark" variant="pill" pillLabel="Dengarkan pengantar" text={teks("a11y-pengantar")} label="pengantar PETA INKLUSI" testid="speak-landing-pengantar" />
            </div>
          </div>
          <div className="flex justify-center">
            <img src="/logo-peta-inklusi.png" alt="Logo PETA INKLUSI: pin lokasi dengan figur manusia merangkul" className="w-full max-w-sm rounded-2xl" />
          </div>
        </div>
      </section>

      <section id="a11y-4data" tabIndex={-1} className="mx-auto max-w-7xl px-4 py-10 focus:outline-none" aria-labelledby="judul-4data">
        <div className="flex items-center gap-2">
          <h2 id="judul-4data" className="font-head text-2xl font-extrabold text-[#232F3E]">4 Data Utama</h2>
          <SpeakMini text={teks("a11y-4data")} label="empat data utama" testid="speak-landing-4data" />
        </div>
        <p className="text-sm text-slate-600">Angka agregat Kota Makassar — tanpa data pribadi.</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {["disabilitas", "stunting", "ats", "kemiskinan"].map((k) => (
            <div key={k} className="rounded-[16px] border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md" style={{ borderTop: `4px solid ${KATEGORI_META[k].warna}` }} data-testid={`landing-card-${k}`}>
              <p className="text-xs font-bold uppercase tracking-wider" style={{ color: KATEGORI_META[k].warna }}>{KATEGORI_META[k].label}</p>
              <p className="mt-2 font-head text-3xl font-extrabold text-slate-900">{fmt(kat[k]?.total)}</p>
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-slate-600">{kat[k]?.satuan || ""}</p>
                <SpeakMini text={`${KATEGORI_META[k].label}: ${fmt(kat[k]?.total)} ${kat[k]?.satuan || ""}`} label={`data ${KATEGORI_META[k].label}`} testid={`speak-landing-${k}`} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section id="a11y-galeri" tabIndex={-1} aria-label="Galeri program" className="mx-auto max-w-7xl px-4 pb-10 focus:outline-none">
        <ProgramGallery limit={3} compact />
      </section>

      <section id="a11y-fitur" tabIndex={-1} aria-label="Fitur layanan" className="bg-white focus:outline-none">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-10 md:grid-cols-4">
          {[
            { i: BarChart3, t: "Dashboard Publik", d: "Statistik agregat per kategori dan wilayah, dapat diakses tanpa login.", to: "/publik" },
            { i: Map, t: "Peta Sosial & Kemiskinan", d: "Choropleth kecamatan → kelurahan, pencarian wilayah, dan drill-down.", to: "/publik/peta-sosial" },
            { i: Send, t: "NGO Inquiry", d: "NGO mengajukan program intervensi langsung dari wilayah bermasalah di peta.", to: "/login?mode=ngo" },
            { i: ShieldCheck, t: "Privasi Terjaga", d: "Masking NIK, email, telepon; RBAC; audit log seluruh aktivitas penting.", to: "/tentang" },
          ].map((c) => (
            <Link key={c.t} to={c.to} className={`group flex flex-col rounded-[16px] border border-slate-200 p-5 transition-colors hover:border-[#117A69] hover:bg-[#F4FBF9] ${FR}`}>
              <c.i className="h-7 w-7 text-[#117A69]" aria-hidden="true" />
              <h3 className="mt-3 font-head text-lg font-bold text-slate-900">{c.t}</h3>
              <p className="mt-1 flex-1 text-sm text-slate-600">{c.d}</p>
              <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-[#117A69] group-hover:text-[#0B4F45]">Selengkapnya <ArrowRight className="h-4 w-4" aria-hidden="true" /></span>
            </Link>
          ))}
        </div>
      </section>
    </PublicLayout>
  );
}
