import React, { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import PublicLayout from "@/components/PublicLayout";

const UMUM = ["Data Source", "Input / Import Data", "Validasi Data", "Pembersihan & Standardisasi", "Masking Data Pribadi", "Database Terintegrasi",
  "Klasifikasi per Kategori", "Analisis Data", "Peta Sosial / Peta Kemiskinan", "Dashboard Statistik", "Identifikasi Permasalahan",
  "Rekomendasi / Inquiry Program", "Intervensi Program", "Monitoring & Evaluasi"];

const SLIDES = [
  { judul: "PETA INKLUSI", sub: "Flow sistem data sosial terintegrasi Kota Makassar", warna: "#232F3E",
    rantai: ["Data", "Informasi", "Analisis", "Program", "Intervensi", "Monitoring"],
    teks: "Empat data utama — Disabilitas, Stunting, Anak Tidak Sekolah (ATS), dan Kemiskinan — diolah dalam satu alur yang sama sehingga perencanaan program berbasis bukti dan saling terhubung." },
  { judul: "Flow Umum 4 Kategori", sub: "Dari sumber data hingga monitoring & evaluasi", warna: "#117A69", langkah: UMUM },
  { judul: "A. Disabilitas", sub: "Menuju program inklusi", warna: "#117A69",
    langkah: ["Data individu / keluarga", "Klasifikasi ragam disabilitas", "Lokasi (kecamatan → kelurahan)", "Kebutuhan / intervensi", "Analisis", "Program inklusi"] },
  { judul: "B. Stunting", sub: "Intervensi gizi spesifik & sensitif", warna: "#C8375B",
    langkah: ["Data anak (balita)", "Lokasi", "Indikator stunting (TB/U)", "Klasifikasi (pendek / sangat pendek)", "Analisis wilayah", "Identifikasi kebutuhan", "Program intervensi"] },
  { judul: "C. Anak Tidak Sekolah", sub: "Kembali ke sekolah", warna: "#B7791F",
    langkah: ["Data anak", "Status pendidikan", "Lokasi", "Usia / jenjang", "Analisis penyebab / status", "Identifikasi wilayah ATS", "Program intervensi pendidikan"] },
  { judul: "D. Kemiskinan", sub: "Pengentasan kemiskinan tepat sasaran", warna: "#3B4F6B",
    langkah: ["Data rumah tangga / individu (DTSEN)", "Indikator sosial ekonomi (desil, PBI, rumah)", "Lokasi", "Klasifikasi kondisi", "Analisis wilayah", "Identifikasi kebutuhan", "Program pengentasan kemiskinan"] },
  { judul: "Dari Data ke Aksi", sub: "Peran setiap pihak", warna: "#232F3E",
    rantai: ["4 Data Utama", "Peta Sosial + Kemiskinan", "Dashboard Publik", "Analisis", "Identifikasi Kebutuhan", "NGO Inquiry", "Program Intervensi", "Monitoring & Evaluasi"],
    teks: "Pemerintah daerah mengelola dan memvalidasi data; publik melihat statistik agregat; NGO mengajukan program berdasarkan wilayah prioritas; Admin memverifikasi, menyetujui, dan memantau pelaksanaan. Seluruh perubahan status tercatat di audit log." },
];

export function FlowSistemContent() {
  const [i, setI] = useState(0);
  const s: any = SLIDES[i];
  const go = (d: number) => setI((x) => Math.min(SLIDES.length - 1, Math.max(0, x + d)));
  return (
    <div className="mx-auto max-w-6xl px-4 py-8" onKeyDown={(e) => { if (e.key === "ArrowRight") go(1); if (e.key === "ArrowLeft") go(-1); }}>
        <div className="flex items-start justify-between gap-3">
          <p className="min-w-0 font-head text-[clamp(1.25rem,1rem+1.2vw,1.5rem)] font-extrabold leading-tight text-[#232F3E]">Flow Sistem PETA INKLUSI</p>
          <p className="shrink-0 whitespace-nowrap pt-1 text-sm text-slate-600" aria-live="polite">Slide {i + 1} / {SLIDES.length}</p>
        </div>
        <section className="mt-4 min-h-[min(460px,70dvh)] rounded-2xl p-5 text-white shadow-xl sm:p-8" style={{ background: `linear-gradient(135deg, ${s.warna}, #1A2330)` }}
          data-testid="flow-slide" aria-roledescription="slide" aria-label={s.judul} tabIndex={0}>
          <div className="flex items-center gap-3">
            <img src="/logo-icon.png" alt="" className="h-12 w-12 rounded-lg" />
            <div><h2 className="font-head text-3xl font-extrabold">{s.judul}</h2><p className="text-slate-200">{s.sub}</p></div>
          </div>
          {s.rantai && (
            <ol className="mt-8 flex flex-wrap items-center gap-2">
              {s.rantai.map((r: string, j: number) => (
                <li key={r} className="flex items-center gap-2">
                  <span className="rounded-lg bg-white/15 px-4 py-3 font-bold ring-1 ring-white/30">{r}</span>
                  {j < s.rantai.length - 1 && <ChevronRight className="h-5 w-5 text-[#6FE3CF]" aria-hidden="true" />}
                </li>
              ))}
            </ol>
          )}
          {s.langkah && (
            <ol className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {s.langkah.map((l: string, j: number) => (
                <li key={l} className="relative rounded-xl bg-white p-4 text-slate-900 shadow">
                  <span className="absolute -left-2 -top-2 flex h-7 w-7 items-center justify-center rounded-full text-xs font-extrabold text-white ring-2 ring-white" style={{ backgroundColor: s.warna }}>{j + 1}</span>
                  <p className="text-sm font-bold">{l}</p>
                </li>
              ))}
            </ol>
          )}
          {s.teks && <p className="mt-8 max-w-3xl text-lg leading-relaxed text-slate-100">{s.teks}</p>}
        </section>
        <div className="sticky bottom-0 z-10 -mx-4 mt-4 flex items-center justify-between gap-2 border-t border-slate-200 bg-slate-50/95 px-4 py-2 pr-16 backdrop-blur sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0 sm:py-0 sm:pr-0 sm:backdrop-blur-none" data-testid="flow-nav">
          <button type="button" onClick={() => go(-1)} disabled={i === 0} data-testid="flow-prev" aria-label="Slide sebelumnya" className="inline-flex min-h-11 shrink-0 items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-2 font-semibold disabled:opacity-40 sm:px-4"><ChevronLeft className="h-4 w-4" /> <span className="hidden sm:inline">Sebelumnya</span></button>
          <div className="flex min-w-0 flex-nowrap justify-center gap-1 sm:gap-1.5">{SLIDES.map((x, j) => <button key={x.judul} type="button" aria-label={`Ke slide ${j + 1}: ${x.judul}`} aria-current={j === i ? "step" : undefined} onClick={() => setI(j)} className="inline-flex h-6 w-6 items-center justify-center"><span className={`block h-2.5 rounded-full ${j === i ? "w-6 bg-[#117A69] sm:w-8" : "w-2.5 bg-slate-600"}`} /></button>)}</div>
          <button type="button" onClick={() => go(1)} disabled={i === SLIDES.length - 1} data-testid="flow-next" aria-label="Slide berikutnya" className="inline-flex min-h-11 shrink-0 items-center gap-1 rounded-md bg-[#117A69] px-3 py-2 font-semibold text-white disabled:opacity-40 sm:px-4"><span className="hidden sm:inline">Berikutnya</span> <ChevronRight className="h-4 w-4" /></button>
        </div>
        <p className="mt-2 text-center text-xs text-slate-500">Tip: gunakan tombol panah kiri/kanan pada keyboard atau mode layar penuh browser (F11) untuk presentasi.</p>
      </div>
  );
}

/** Versi publik (tanpa login) — dipakai rute /flow-sistem. */
export default function FlowSistem() {
  return (
    <PublicLayout>
      <FlowSistemContent />
    </PublicLayout>
  );
}
