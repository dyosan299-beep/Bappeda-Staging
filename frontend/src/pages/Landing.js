import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight, Map, BarChart3, Send, ShieldCheck, Search, MapPin,
  Accessibility, Baby, GraduationCap, Home,
} from "lucide-react";
import PublicLayout from "@/components/PublicLayout";
import api from "@/lib/api";
import { KATEGORI_META, fmt } from "@/features/inklusi/theme";
import { ProgramGallery } from "@/features/inklusi/InklusiExtra";
import { SpeakMini } from "@/features/a11y/components";
import { buatNarasi } from "@/features/a11y/narasi";
import { FR } from "@/features/a11y/ui";

const KAT_ICON = {
  disabilitas: Accessibility,
  stunting: Baby,
  ats: GraduationCap,
  kemiskinan: Home,
};

const LAYANAN = [
  {
    Icon: BarChart3,
    t: "Dashboard publik",
    d: "Lihat statistik agregat per kategori dan wilayah tanpa perlu masuk akun.",
    to: "/publik",
  },
  {
    Icon: Map,
    t: "Peta sosial dan kemiskinan",
    d: "Telusuri peta kecamatan sampai kelurahan dengan pencarian wilayah dan rincian angka.",
    to: "/publik/peta-sosial",
  },
  {
    Icon: Send,
    t: "Usulan program NGO",
    d: "NGO mengajukan program intervensi langsung dari wilayah prioritas pada peta.",
    to: "/login?mode=ngo",
  },
  {
    Icon: ShieldCheck,
    t: "Privasi data terjaga",
    d: "Server menyamarkan NIK, email, dan telepon, membatasi akses per peran, serta mencatat log audit.",
    to: "/tentang",
  },
];

export default function Landing() {
  const [s, setS] = useState(null);
  const [cari, setCari] = useState("");
  const navigate = useNavigate();

  useEffect(() => { api.get("/public/summary").then((r) => setS(r.data)).catch(() => {}); }, []);
  const kat = s?.kategori || {};
  const nr = buatNarasi("beranda", s, null);
  const teks = (id) => nr?.bagian.find((b) => b.id === id)?.teks || "";

  const hasilCari = useMemo(() => {
    const q = cari.trim().toLowerCase();
    if (!q) return [];
    return (s?.per_kecamatan || [])
      .filter((r) => String(r.kecamatan || "").toLowerCase().includes(q))
      .slice(0, 5);
  }, [cari, s]);

  const onCariSubmit = (e) => {
    e.preventDefault();
    navigate("/publik/peta-sosial");
  };

  return (
    <PublicLayout>
      {/* Hero terpusat dan tenang dalam palet asli PETA INKLUSI */}
      <section
        id="a11y-pengantar"
        tabIndex={-1}
        className="relative overflow-hidden bg-[#232F3E] text-white focus:outline-none"
        data-testid="landing-hero"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            background: "radial-gradient(60% 70% at 50% 0%, rgba(111,227,207,0.10), transparent 70%)",
          }}
        />
        <div className="relative mx-auto max-w-4xl px-4 py-14 text-center sm:px-6 sm:py-20">
          <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-xs font-semibold tracking-wide text-[#6FE3CF] ring-1 ring-white/15">
            Bappeda Kota Makassar · {fmt(s?.wilayah?.kecamatan ?? 15)} Kecamatan · {fmt(s?.wilayah?.kelurahan ?? 153)} Kelurahan
          </p>
          <h1 className="mt-5 font-head text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">
            PETA INKLUSI
          </h1>
          <p
            className="mx-auto mt-3 max-w-2xl text-lg font-semibold leading-snug text-slate-200 sm:text-2xl"
            data-testid="landing-hero-tagline"
          >
            Pemetaan data tematik dan evaluasi program kelompok rentan Kota Makassar.
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-slate-300 sm:text-base">
            Data disabilitas, stunting, anak tidak sekolah, dan kemiskinan tersaji per kecamatan dan kelurahan untuk perencanaan dan pengajuan program intervensi.
          </p>

          <form onSubmit={onCariSubmit} className="relative mx-auto mt-7 max-w-xl text-left" role="search" aria-label="Cari kecamatan di Kota Makassar">
            <div className="flex items-center rounded-xl bg-white p-1.5 shadow-[0_14px_34px_rgba(15,23,42,0.28)]">
              <Search className="ml-3 h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
              <input
                type="search"
                value={cari}
                onChange={(e) => setCari(e.target.value)}
                aria-label="Cari kecamatan di Kota Makassar"
                placeholder="Cari kecamatan (mis. Tallo)"
                data-testid="hero-wilayah-search"
                className="h-10 min-w-0 flex-1 bg-transparent px-3 text-sm text-slate-900 placeholder:text-slate-500 focus:outline-none"
              />
              <button
                type="submit"
                className={`inline-flex h-10 shrink-0 items-center justify-center rounded-lg bg-[#117A69] px-5 text-sm font-bold text-white transition-colors hover:bg-[#0E6456] ${FR}`}
              >
                Cari
              </button>
            </div>
            {hasilCari.length > 0 && (
              <ul
                className="absolute left-0 right-0 top-full z-20 mt-2 divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white text-slate-900 shadow-xl"
                data-testid="hero-search-results"
              >
                {hasilCari.map((r) => (
                  <li key={r.kecamatan}>
                    <Link
                      to="/publik/peta-sosial"
                      className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm transition-colors hover:bg-[#E6FAF6]"
                    >
                      <span className="inline-flex items-center gap-1.5 font-bold text-[#232F3E]">
                        <MapPin className="h-3.5 w-3.5 text-[#117A69]" aria-hidden="true" />
                        Kecamatan {r.kecamatan}
                      </span>
                      <span className="text-xs text-slate-600 tabular-nums">
                        Disabilitas {fmt(r.disabilitas)}, Stunting {fmt(r.stunting)}, ATS {fmt(r.ats)}, Kemiskinan {fmt(r.kemiskinan)}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </form>

          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/publik"
              data-testid="hero-dashboard-btn"
              className={`inline-flex min-h-11 items-center gap-2 rounded-full bg-[#6FE3CF] px-6 py-2.5 text-sm font-bold text-[#232F3E] transition-colors hover:bg-[#8FEBDB] active:bg-[#5FD6C1] ${FR}`}
            >
              Dashboard Informasi Umum <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link
              to="/publik/peta-sosial"
              data-testid="hero-peta-btn"
              className={`inline-flex min-h-11 items-center gap-2 rounded-full bg-white/10 px-6 py-2.5 text-sm font-bold text-white ring-1 ring-white/25 transition-colors hover:bg-white/15 active:bg-white/20 ${FR}`}
            >
              <Map className="h-4 w-4" aria-hidden="true" /> Jelajahi Peta Sosial
            </Link>
            <SpeakMini
              tone="dark"
              variant="pill"
              pillLabel="Dengarkan pengantar"
              text={teks("a11y-pengantar")}
              label="pengantar PETA INKLUSI"
              testid="speak-landing-pengantar"
            />
          </div>
        </div>
      </section>

      {/* Empat data utama */}
      <section id="a11y-4data" tabIndex={-1} className="mx-auto max-w-7xl px-4 py-12 focus:outline-none sm:px-6 sm:py-14" aria-labelledby="judul-4data">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-[#117A69]">Data agregat publik</p>
            <div className="mt-1 flex items-center gap-2.5">
              <h2 id="judul-4data" className="font-head text-2xl font-extrabold text-[#232F3E] sm:text-3xl">Empat data utama</h2>
              <SpeakMini text={teks("a11y-4data")} label="empat data utama" testid="speak-landing-4data" />
            </div>
            <p className="mt-1 text-sm text-slate-600">Angka agregat Kota Makassar tanpa data pribadi.</p>
          </div>
          <Link
            to="/publik"
            className={`inline-flex min-h-10 items-center gap-1.5 rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-[#232F3E] transition-colors hover:border-[#117A69] hover:text-[#117A69] sm:text-sm ${FR}`}
          >
            Lihat rincian lengkap <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {["disabilitas", "stunting", "ats", "kemiskinan"].map((k) => {
            const Icon = KAT_ICON[k];
            return (
              <div
                key={k}
                className="flex flex-col rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_5px_15px_rgba(15,23,42,0.04)] transition-shadow hover:shadow-md sm:p-6"
                data-testid={`landing-card-${k}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#E6FAF6] text-[#117A69]" aria-hidden="true">
                    <Icon className="h-5 w-5" />
                  </span>
                  <SpeakMini
                    text={`${KATEGORI_META[k].label}: ${fmt(kat[k]?.total)} ${kat[k]?.satuan || ""}`}
                    label={`data ${KATEGORI_META[k].label}`}
                    testid={`speak-landing-${k}`}
                  />
                </div>
                <p className="mt-4 text-xs font-bold uppercase tracking-wider text-slate-500">{KATEGORI_META[k].label}</p>
                <p className="mt-1 font-head text-3xl font-extrabold text-[#232F3E] tabular-nums">{fmt(kat[k]?.total)}</p>
                <p className="mt-1 text-xs font-medium text-slate-600">{kat[k]?.satuan || ""}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Layanan portal */}
      <section id="a11y-fitur" tabIndex={-1} aria-labelledby="judul-layanan" className="border-y border-slate-200/80 bg-white py-12 focus:outline-none sm:py-14">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="text-center">
            <p className="text-xs font-bold uppercase tracking-widest text-[#117A69]">Layanan publik</p>
            <h2 id="judul-layanan" className="mt-1 font-head text-2xl font-extrabold text-[#232F3E] sm:text-3xl">
              Layanan portal PETA INKLUSI
            </h2>
            <p className="mx-auto mt-1.5 max-w-2xl text-sm text-slate-600">
              Akses data agregat wilayah, peta tematik, usulan program intervensi, dan kebijakan privasi data.
            </p>
          </div>
          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {LAYANAN.map((c) => (
              <Link
                key={c.t}
                to={c.to}
                className={`group flex flex-col items-center rounded-2xl border border-slate-200/80 bg-white p-6 text-center shadow-[0_5px_15px_rgba(15,23,42,0.04)] transition-all hover:-translate-y-0.5 hover:border-[#117A69]/40 hover:shadow-md ${FR}`}
              >
                <span className="grid h-14 w-14 place-items-center rounded-full bg-[#E6FAF6] text-[#117A69] transition-colors group-hover:bg-[#117A69] group-hover:text-white" aria-hidden="true">
                  <c.Icon className="h-6 w-6" />
                </span>
                <h3 className="mt-4 font-head text-base font-bold text-[#232F3E]">{c.t}</h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{c.d}</p>
                <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-[#117A69] group-hover:text-[#0B4F45]">
                  Selengkapnya <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Galeri program selesai */}
      <section id="a11y-galeri" tabIndex={-1} aria-label="Galeri program" className="mx-auto max-w-7xl px-4 py-12 focus:outline-none sm:px-6 sm:py-14">
        <ProgramGallery limit={3} compact />
      </section>
    </PublicLayout>
  );
}
