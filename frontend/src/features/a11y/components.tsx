import React, { useId, useState } from "react";
import {
  Accessibility, Baby, BarChart3, ChevronDown, GraduationCap, Hand, Home, Info, MapPin, ShieldCheck, Square, Table2, Volume2,
} from "lucide-react";
import { useA11y } from "@/context/AccessibilityContext";
import type { ItemMudah } from "./narasi";
import { BTN_SM, FR } from "./ui";

/**
 * Tombol "Bacakan" untuk satu bagian/kartu (fitur B).
 * variant "icon" = tombol bulat ikon saja; "pill" = ikon + teks (untuk area hero/judul).
 */
export function SpeakMini({ text, label, testid, tone = "light", variant = "icon", pillLabel = "Dengarkan" }: {
  text: string; label: string; testid?: string; tone?: "light" | "dark"; variant?: "icon" | "pill"; pillLabel?: string;
}) {
  const { speak, stop, currentKey, status, reduceMotion } = useA11y();
  const key = `mini:${label}`;
  const aktif = currentKey === key && status !== "idle";
  const dark = tone === "dark";
  const warna = aktif
    ? "bg-[#117A69] text-white ring-[#117A69] shadow-[0_8px_20px_rgba(17,122,105,.28)]"
    : dark
      ? "bg-white/10 text-white ring-white/25 hover:bg-white/20"
      : "bg-white text-[#117A69] ring-slate-200 hover:bg-[#E6FAF6] hover:text-[#0B4F45] hover:ring-[#117A69]/30 active:bg-[#D2F4EC]";
  const bentuk = variant === "pill"
    ? "min-h-11 max-w-full gap-2 rounded-full py-1.5 pl-1.5 pr-3 text-sm font-semibold"
    : "h-10 w-10 shrink-0 rounded-full";
  return (
    <button type="button" data-testid={testid}
      onClick={() => (aktif ? stop() : speak(text, undefined, key))}
      aria-label={aktif ? `Hentikan pembacaan ${label}` : `Bacakan ${label}`} title={aktif ? "Hentikan" : `Bacakan ${label}`}
      aria-pressed={aktif}
      className={`relative inline-flex items-center justify-center text-left ring-1 transition-colors ${FR} ${bentuk} ${warna}`}>
      {aktif && !reduceMotion && <span className="absolute inset-0 animate-ping rounded-full ring-2 ring-[#6FE3CF]/60" aria-hidden="true" />}
      <span className={variant === "pill" ? `grid h-8 w-8 place-items-center rounded-full ${aktif ? "bg-white/15" : dark ? "bg-white/10" : "bg-[#E6FAF6]"}` : "contents"} aria-hidden="true">
        {aktif ? <Square className="h-3.5 w-3.5" /> : <Volume2 className="h-[18px] w-[18px]" />}
      </span>
      {variant === "pill" && <span className="min-w-0 break-words">{aktif ? "Hentikan" : pillLabel}</span>}
    </button>
  );
}

/**
 * Alternatif teks untuk grafik (fitur C): kalimat ringkasan + tabel data.
 * Tabel selalu terbaca pembaca layar (sr-only) dan dapat ditampilkan secara visual.
 */
export function ChartA11y({ judul, ringkasan, kolom, baris, testid, children }: {
  judul: string; ringkasan: string; kolom: string[]; baris: (string | number)[][]; testid: string; children: React.ReactNode;
}) {
  const [buka, setBuka] = useState(false);
  const id = useId();
  return (
    <div className="relative">
      <div role="img" aria-label={`Grafik: ${judul}`} aria-describedby={`${id}-r`}>
        {/* inert: grafik tetap diumumkan lewat role=img + aria-label di atas,
            sementara isi SVG (Recharts menambahkan elemen fokusable) tidak ikut
            tab order maupun accessibility tree (WCAG 4.1.2, 2.1.1). */}
        <div inert={true}>{children}</div>
      </div>
      <div className="mt-3 rounded-[14px] bg-slate-50 p-3 ring-1 ring-slate-200" data-testid={`${testid}-a11y-block`}>
        <div className="flex items-start gap-3">
          <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white text-[#117A69] ring-1 ring-slate-200" aria-hidden="true">
            <BarChart3 className="h-4 w-4" />
          </span>
          <p id={`${id}-r`} className="min-w-0 flex-1 text-sm leading-6 text-slate-700" data-testid={`${testid}-ringkasan`}>
            <span className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Ringkasan grafik:</span> {ringkasan}
          </p>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-200 pt-3">
          <button type="button" aria-expanded={buka} aria-controls={`${id}-t`} onClick={() => setBuka(!buka)} data-testid={`${testid}-toggle`}
            className={`${BTN_SM} ${buka ? "bg-[#E6FAF6] text-[#0B4F45] ring-[#117A69]/30" : ""}`}>
            <Table2 className="h-4 w-4 text-[#117A69]" aria-hidden="true" /> {buka ? "Sembunyikan tabel data" : "Tampilkan tabel data"}
            <ChevronDown className={`h-3.5 w-3.5 text-slate-500 ${buka ? "rotate-180" : ""}`} aria-hidden="true" />
          </button>
          <SpeakMini text={`${judul}. ${ringkasan}`} label={`ringkasan grafik ${judul}`} testid={`${testid}-speak`} />
          <span className="ml-auto hidden text-[11px] text-slate-500 sm:inline">{baris.length} baris data</span>
        </div>
      </div>
      <div id={`${id}-t`} className={buka ? "table-scroll mt-3 max-h-72 overflow-y-auto rounded-[14px] bg-white ring-1 ring-slate-200" : "sr-only left-0 top-0"}>
        <table className={buka ? "w-full min-w-[440px] text-sm" : "w-px table-fixed text-sm"} data-testid={`${testid}-table`}>
          <caption className="sr-only">Tabel data: {judul}</caption>
          <thead className="sticky top-0 bg-slate-50 shadow-[inset_0_-1px_0_rgb(226,232,240)]"><tr>{kolom.map((k) => <th key={k} scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">{k}</th>)}</tr></thead>
          <tbody>{baris.map((r, i) => (
            <tr key={i} className="border-t border-slate-100 odd:bg-white even:bg-slate-50/60 hover:bg-[#E6FAF6]/60">{r.map((c, j) => j === 0
              ? <th key={j} scope="row" className="px-3 py-2 text-left font-semibold text-slate-900">{c}</th>
              : <td key={j} className="px-3 py-2 tabular-nums text-slate-700">{typeof c === "number" ? c.toLocaleString("id-ID") : c}</td>)}</tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

const IKON = { disabilitas: Accessibility, stunting: Baby, ats: GraduationCap, kemiskinan: Home, peta: MapPin, info: Info, privasi: ShieldCheck, tangan: Hand };
const WARNA = { disabilitas: "#117A69", stunting: "#C8375B", ats: "#9A6416", kemiskinan: "#3B4F6B", peta: "#117A69", info: "#232F3E", privasi: "#0B4F45", tangan: "#7C3AED" };

/** Mode Bahasa Mudah (fitur H): kalimat pendek + ikon besar, masing-masing dapat dibacakan. */
export function EasyRead({ items, judul }: { items: ItemMudah[]; judul: string }) {
  return (
    <section id="a11y-bahasa-mudah" tabIndex={-1} aria-labelledby="judul-bahasa-mudah" data-testid="a11y-easy-read"
      className="mx-auto max-w-7xl px-4 pt-6 focus:outline-none">
      <div className="overflow-hidden rounded-[18px] bg-white shadow-[0_10px_30px_rgba(35,47,62,.10)] ring-2 ring-[#117A69]">
        <div className="flex flex-wrap items-center justify-between gap-3 bg-[#232F3E] px-5 py-4 text-white">
          <h2 id="judul-bahasa-mudah" className="flex items-center gap-3 font-head text-2xl font-extrabold">
            <span className="grid h-11 w-11 place-items-center rounded-[12px] bg-white/10 ring-1 ring-white/15" aria-hidden="true"><Hand className="h-6 w-6 text-[#6FE3CF]" /></span>
            Bahasa Mudah — {judul}
          </h2>
          <span className="inline-flex items-center rounded-full bg-[#6FE3CF] px-3 py-1 text-xs font-bold text-[#232F3E]">Mode aktif</span>
        </div>
        <ul className="grid gap-3 p-5 sm:grid-cols-2">
          {items.map((it, i) => {
            const Ic = IKON[it.ikon] || Info;
            return (
              <li key={i} className="flex items-center gap-4 rounded-[14px] bg-slate-50 p-4 ring-1 ring-slate-200 transition-colors hover:bg-white hover:ring-slate-300" data-testid="a11y-easy-item">
                <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-white shadow-sm" style={{ background: WARNA[it.ikon] }} aria-hidden="true">
                  <Ic className="h-8 w-8" />
                </span>
                <p className="flex-1 text-xl font-bold leading-snug text-slate-900">{it.teks}</p>
                <SpeakMini text={it.teks} label={it.teks} testid={`a11y-easy-speak-${i}`} />
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

/** Tabel data peta (fitur C untuk halaman peta) — alternatif peta untuk pembaca layar. */
export function MapDataTable({ s, jenis }: { s: any; jenis: "sosial" | "kemiskinan" }) {
  const rows = [...(s?.per_kecamatan || [])].sort((a, b) => a.kecamatan.localeCompare(b.kecamatan));
  const kolom = jenis === "sosial" ? ["Kecamatan", "Disabilitas (orang)", "Stunting (anak)", "Anak tidak sekolah (anak)"] : ["Kecamatan", "KK miskin ekstrem", "% penduduk miskin"];
  return (
    <section id="a11y-peta-tabel" tabIndex={-1} aria-labelledby="judul-peta-tabel" className="mx-auto max-w-7xl px-4 py-8 focus:outline-none" data-testid="a11y-map-table">
      <div className="rounded-[16px] bg-white p-5 shadow-[0_10px_24px_rgba(35,47,62,.06)] ring-1 ring-slate-200">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-[12px] bg-[#E6FAF6] text-[#117A69]" aria-hidden="true"><Table2 className="h-5 w-5" /></span>
            <div>
              <h2 id="judul-peta-tabel" className="font-head text-lg font-extrabold text-[#232F3E]">Tabel data peta per kecamatan</h2>
              <p className="text-xs text-slate-500">Alternatif teks dari peta — dapat dibaca pembaca layar</p>
            </div>
          </div>
          {s && <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">{rows.length} kecamatan</span>}
        </div>
        {!s ? <p className="mt-3 text-sm text-slate-500" aria-live="polite">Memuat data…</p> : (
          <div className="mt-4 overflow-x-auto rounded-[12px] ring-1 ring-slate-200">
            <table className="w-full text-sm">
              <caption className="sr-only">{jenis === "sosial" ? "Data disabilitas, stunting, dan anak tidak sekolah per kecamatan" : "Data kemiskinan per kecamatan"}</caption>
              <thead className="bg-slate-50"><tr>{kolom.map((k) => <th key={k} scope="col" className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">{k}</th>)}</tr></thead>
              <tbody>{rows.map((r: any, i: number) => (
                <tr key={`${r.kecamatan}-${i}`} className="border-t border-slate-100 odd:bg-white even:bg-slate-50/60 hover:bg-[#E6FAF6]/60" data-testid="a11y-map-row">
                  <th scope="row" className="px-3 py-2.5 text-left font-semibold text-slate-900">{r.kecamatan}</th>
                  {jenis === "sosial"
                    ? <><td className="px-3 py-2.5 tabular-nums">{Number(r.disabilitas || 0).toLocaleString("id-ID")}</td><td className="px-3 py-2.5 tabular-nums">{Number(r.stunting || 0).toLocaleString("id-ID")}</td><td className="px-3 py-2.5 tabular-nums">{Number(r.ats || 0).toLocaleString("id-ID")}</td></>
                    : <><td className="px-3 py-2.5 tabular-nums">{Number(r.kemiskinan || 0).toLocaleString("id-ID")}</td><td className="px-3 py-2.5 tabular-nums">{r.kemiskinan_persen != null ? `${Number(r.kemiskinan_persen).toLocaleString("id-ID")}%` : "-"}</td></>}
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
