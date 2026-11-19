/**
 * Token kelas Tailwind bersama untuk tombol & permukaan aksesibilitas / halaman publik.
 * Warna tetap memakai tema Bappeda: Teal #117A69, Dark Teal #0B4F45, Navy #232F3E, Mint #6FE3CF, Amber #F4B63A.
 */
export const FR = "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60";

const BASE = `inline-flex items-center justify-center gap-2 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${FR}`;

/** Tombol utama (teal solid). */
export const BTN_PRIMARY = `${BASE} min-h-11 rounded-[12px] bg-[#117A69] px-5 py-2.5 text-sm text-white shadow-[0_10px_24px_rgba(17,122,105,.22)] hover:bg-[#0B4F45] active:bg-[#0B4F45]`;
/** Tombol sekunder (permukaan putih + ring). */
export const BTN_SECONDARY = `${BASE} min-h-11 rounded-[12px] bg-white px-5 py-2.5 text-sm text-slate-900 ring-1 ring-slate-200 hover:bg-slate-50 hover:ring-slate-300 active:bg-slate-100`;
/** Tombol garis navy. */
export const BTN_OUTLINE_NAVY = `${BASE} min-h-10 rounded-[12px] bg-white px-4 py-2 text-xs text-[#232F3E] ring-1 ring-[#232F3E]/30 hover:bg-[#232F3E] hover:text-white active:bg-[#1A2330]`;
/** Tombol garis teal. */
export const BTN_OUTLINE_TEAL = `${BASE} min-h-10 rounded-[12px] bg-white px-4 py-2 text-xs text-[#117A69] ring-1 ring-[#117A69]/35 hover:bg-[#E6FAF6] active:bg-[#D2F4EC]`;
/** Tombol kecil (aksi di dalam kartu). */
export const BTN_SM = `${BASE} min-h-10 rounded-[10px] bg-white px-3 py-2 text-xs text-slate-800 ring-1 ring-slate-200 hover:bg-slate-50 hover:ring-slate-300 active:bg-slate-100`;
/** Tombol kecil utama. */
export const BTN_SM_PRIMARY = `${BASE} min-h-10 rounded-[10px] bg-[#117A69] px-3.5 py-2 text-xs text-white shadow-[0_8px_18px_rgba(17,122,105,.20)] hover:bg-[#0B4F45] active:bg-[#0B4F45]`;
/** Tombol ikon bulat. */
export const BTN_ICON = `${BASE} h-10 w-10 shrink-0 rounded-full bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50 hover:text-slate-900 active:bg-slate-100`;
/** Tombol ikon di atas permukaan gelap (navy). */
export const BTN_ICON_DARK = `${BASE} h-10 w-10 shrink-0 rounded-full bg-white/10 text-white ring-1 ring-white/15 hover:bg-white/20 active:bg-white/25`;

/** Kontrol segmented (pill). */
export const SEG = "grid rounded-full bg-slate-100 p-1 ring-1 ring-slate-200";
export const segItem = (on: boolean) =>
  `min-h-9 rounded-full px-3 py-2 text-xs font-semibold transition-colors ${FR} ${on ? "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200" : "text-slate-600 hover:text-slate-900"}`;

/** Elemen kbd. */
export const KBD = "inline-flex items-center rounded-md bg-white px-2 py-0.5 font-mono text-[11px] font-semibold text-slate-700 ring-1 ring-slate-200 shadow-[0_1px_0_rgba(15,23,42,.08)]";
