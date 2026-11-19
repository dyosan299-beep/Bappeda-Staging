import api, { API, formatApiErrorDetail } from "@/lib/api";

export { api };

export const STATUS_LABEL: Record<string, string> = {
  belum_diverval: "Belum diverval",
  draft: "Draft",
  menunggu_kelurahan: "Menunggu periksa Kelurahan",
  menunggu_kecamatan: "Menunggu acc Kecamatan",
  terkirim: "Terkirim · menunggu pemeriksaan",
  perlu_perbaikan: "Perlu perbaikan",
  disetujui: "Disetujui Kecamatan",
  ditolak: "Ditolak",
};

export const STATUS_CLS: Record<string, string> = {
  belum_diverval: "bg-slate-100 text-slate-700 ring-slate-200",
  draft: "bg-amber-50 text-amber-900 ring-amber-200",
  menunggu_kelurahan: "bg-sky-50 text-sky-900 ring-sky-200",
  menunggu_kecamatan: "bg-indigo-50 text-indigo-900 ring-indigo-200",
  terkirim: "bg-sky-50 text-sky-900 ring-sky-200",
  perlu_perbaikan: "bg-orange-50 text-orange-900 ring-orange-300",
  disetujui: "bg-emerald-50 text-emerald-900 ring-emerald-200",
  ditolak: "bg-rose-50 text-rose-900 ring-rose-200",
};

export const STATUS_COLOR: Record<string, string> = {
  draft: "#D97706",
  menunggu_kelurahan: "#0284C7",
  menunggu_kecamatan: "#4F46E5",
  terkirim: "#0284C7",
  perlu_perbaikan: "#EA580C",
  disetujui: "#059669",
  ditolak: "#E11D48",
};

export const GPS_LABEL: Record<string, string> = {
  memenuhi: "Akurasi memenuhi target",
  pin_manual: "Pin manual (disesuaikan di peta)",
  akurasi_rendah: "Akurasi belum memenuhi target",
  izin_ditolak: "Izin lokasi ditolak",
  tidak_tersedia: "GPS tidak tersedia",
  belum_direkam: "Lokasi belum direkam",
};

export const HASIL_LABEL: Record<string, string> = {
  sesuai: "Sesuai",
  tidak_sesuai: "Tidak sesuai",
  tidak_dapat_diperiksa: "Tidak dapat diperiksa",
};

/** Label untuk opsi "Kesesuaian" (data DTSEN pre-printed) per variabel. */
export const KESESUAIAN_LABEL: Record<string, string> = {
  sesuai: "Sesuai",
  beda: "Beda",
  tetap: "Tetap",
  graduasi: "Graduasi",
  aktif: "Aktif",
  non_aktif: "Non-Aktif",
  rlh: "RLH (Rumah Layak Huni)",
  rtlh: "RTLH (Rumah Tidak Layak Huni)",
  layak: "Layak",
  tidak_layak: "Tidak Layak",
  babs: "BABS",
  odf: "ODF",
  butuh_pelatihan: "Butuh Pelatihan",
  cukup: "Cukup",
};

/** Label untuk opsi "Kondisi Riil Lapangan". */
export const KONDISI_RIIL_LABEL: Record<string, string> = {
  ...{} as any,
  sesuai: "Sesuai",
  beda: "Beda",
  tetap: "Tetap",
  graduasi: "Graduasi",
  aktif: "Aktif",
  non_aktif: "Non-Aktif",
  layak: "Layak",
  tidak_layak: "Tidak Layak",
  babs: "BABS",
  odf: "ODF",
  pelatihan: "Butuh Pelatihan",
  modal: "Butuh Modal",
  cukup: "Cukup",
};

/** Label singkat untuk status hubungan dalam Penapisan Individu. */
export const HUBUNGAN_LABEL: Record<string, string> = {
  kepala_keluarga: "Kepala Keluarga",
  istri: "Istri / Pasangan",
  anak_usia_sekolah: "Anak Usia Sekolah",
  balita_ibu_hamil: "Balita / Ibu Hamil",
  lansia_disabilitas: "Lansia / Disabilitas",
  lainnya: "Lainnya",
};

/** Label pilihan kesimpulan Verval. */
export const KESIMPULAN_LABEL: Record<string, string> = {
  ditemukan_sesuai: "Ditemukan & Sesuai",
  perubahan_karakteristik: "Ditemukan & Perubahan Karakteristik",
  pindah_domisili: "Pindah Domisili",
  meninggal_dunia: "Meninggal Dunia",
  tidak_ditemukan: "Tidak Ditemukan",
  graduasi_mandiri: "Graduasi Mandiri",
};

/** Opsi yang memicu catatan wajib pada field variabel (sesuai backend). */
export const INDIKATOR_PERLU_CATATAN = new Set<string>([
  "beda", "graduasi", "non_aktif", "rtlh", "tidak_layak", "babs",
  "butuh_pelatihan", "pelatihan", "modal",
]);

export const DASAR_LABEL: Record<string, string> = {
  wilayah_petugas: "Wilayah petugas (Kelurahan · RW/RT)",
  penugasan_rt_rw: "Penugasan RT/RW",
  kelurahan_tanpa_rtrw: "Kelurahan (RT/RW belum terisi)",
  warga_baru: "Warga baru (usulan RT/RW)",
  sasaran_admin: "KK sasaran (ditetapkan admin)",
  lintas_wilayah: "Penugasan lintas wilayah",
};

export function errMsg(e: any): string {
  const d = e?.response?.data?.detail;
  if (d && Array.isArray(d.masalah)) return `${d.msg}: ${d.masalah.join("; ")}`;
  if (!e?.response) return "Koneksi gagal. Periksa jaringan lalu coba lagi.";
  return formatApiErrorDetail(d);
}

export function newId(): string {
  const c: any = (window as any).crypto;
  if (c?.randomUUID) return c.randomUUID().replace(/-/g, "");
  return (Date.now().toString(16) + Math.random().toString(16).slice(2) + Math.random().toString(16).slice(2)).slice(0, 32);
}

/** client_uuid per sasaran disimpan lokal agar "Mulai Verval" yang diulang tidak membuat record ganda. */
export function clientUuidFor(ref: string): string {
  const key = `verval_cu_${ref}`;
  let v = localStorage.getItem(key);
  if (!v) { v = newId(); localStorage.setItem(key, v); }
  return v;
}

export const fotoUrl = (id: string) => `${API}/verval/foto/${id}`;

export const fmtWaktu = (s?: string) => {
  if (!s) return "-";
  try { return new Date(s).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }); } catch { return s; }
};
