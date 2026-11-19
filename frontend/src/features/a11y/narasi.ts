/**
 * Narasi aksesibilitas per halaman publik — disusun dari data agregat nyata (/public/summary).
 * Dipakai untuk: Bacakan Halaman, tombol 🔊 per bagian, ringkasan grafik, perintah suara, dan Bahasa Mudah.
 */
import type { HalamanKey } from "./data";

export type Bagian = { id: string; label: string; teks: string; target: string; kata: string[] };
export type ItemMudah = { ikon: "disabilitas" | "stunting" | "ats" | "kemiskinan" | "peta" | "info" | "privasi" | "tangan"; teks: string };
export type Narasi = { judul: string; pembuka: string; bagian: Bagian[]; mudah: ItemMudah[] };

const n = (v: any) => (v === null || v === undefined || v === "" ? "-" : Number(v).toLocaleString("id-ID"));
const top = (arr: any[], key: string, k = 3) => [...(arr || [])].sort((a, b) => (b[key] || 0) - (a[key] || 0)).slice(0, k);
const daftar = (xs: string[]) => (xs.length <= 1 ? xs.join("") : `${xs.slice(0, -1).join(", ")}, dan ${xs[xs.length - 1]}`);
const KAT_LABEL: Record<string, string> = { disabilitas: "penyandang disabilitas", stunting: "anak stunting", ats: "anak tidak sekolah", kemiskinan: "kepala keluarga miskin ekstrem" };

function rankKec(s: any, key: string, k = 3, satuan = "") {
  return daftar(top(s?.per_kecamatan, key, k).map((r: any) => `Kecamatan ${r.kecamatan} ${n(r[key])}${satuan ? ` ${satuan}` : ""}`));
}

function ringkasEmpat(s: any) {
  const k = s?.kategori || {};
  return `Penyandang disabilitas: ${n(k.disabilitas?.total)} orang. Stunting: ${n(k.stunting?.total)} anak` +
    (k.stunting?.terdata_by_name ? `, dan ${n(k.stunting.terdata_by_name)} balita terdata nama per nama di Kecamatan Makassar dan Tallo tahun 2026` : "") +
    `. Anak tidak sekolah: ${n(k.ats?.total)} anak. Kemiskinan ekstrem: ${n(k.kemiskinan?.total)} kepala keluarga` +
    (k.kemiskinan?.persen_kota ? `, dengan ${n(k.kemiskinan.persen_kota)} persen penduduk miskin pada tahun 2025` : "") + ".";
}

function kondisi(s: any) {
  const t = (key: string) => top(s?.per_kecamatan, key, 1)[0]?.kecamatan || "-";
  return `Kecamatan dengan kepala keluarga miskin ekstrem terbanyak adalah ${t("kemiskinan")}. Stunting terbanyak di Kecamatan ${t("stunting")}. ` +
    `Anak tidak sekolah terbanyak di Kecamatan ${t("ats")}. Penyandang disabilitas terbanyak di Kecamatan ${t("disabilitas")}.`;
}

export function trenKemiskinan(s: any) {
  const t = s?.tren?.kemiskinan || [];
  if (!t.length) return "Data tren kemiskinan belum tersedia.";
  const a = t[0], b = t[t.length - 1];
  return `Persentase penduduk miskin Kota Makassar: ${t.map((x: any) => `tahun ${x.tahun} ${n(x.persen)} persen`).join(", ")}. ` +
    `Dari ${a.tahun} ke ${b.tahun} ${b.persen < a.persen ? "turun" : b.persen > a.persen ? "naik" : "tetap"} ${n(Math.abs(Math.round((b.persen - a.persen) * 100) / 100))} poin persen.`;
}
export function trenStunting(s: any) {
  const t = s?.tren?.stunting || [];
  if (!t.length) return "Data tren stunting belum tersedia.";
  return `Prevalensi stunting per tahun: ${t.map((x: any) => `tahun ${x.tahun} SSGI ${n(x.ssgi_persen)} persen` + (x.eppgbm_persen != null ? `, e-PPGBM ${n(x.eppgbm_persen)} persen` : "")).join("; ")}.`;
}
export function trenAts(s: any) {
  const t = s?.tren?.ats || [];
  if (!t.length) return "Data anak tidak sekolah per tahun belum tersedia.";
  return `Anak tidak sekolah per tahun: ${t.map((x: any) => `tahun ${x.tahun} jenjang SD ${n(x.ats_sd)} anak dan SMP ${n(x.ats_smp)} anak`).join("; ")}.`;
}
export function statKecamatan(s: any) {
  return `Grafik batang membandingkan empat kategori di ${n(s?.per_kecamatan?.length)} kecamatan. ` +
    `Disabilitas terbanyak: ${rankKec(s, "disabilitas")}. Stunting terbanyak: ${rankKec(s, "stunting")}. ` +
    `Anak tidak sekolah terbanyak: ${rankKec(s, "ats")}. Kepala keluarga miskin ekstrem terbanyak: ${rankKec(s, "kemiskinan")}.`;
}
export function balitaStunting(st: any) {
  if (!st?.total) return "Data balita stunting nama per nama belum tersedia.";
  const f = (arr: any[]) => daftar((arr || []).map((x: any) => `${x.kategori} ${n(x.jumlah)}`));
  return `Balita stunting tahun 2026 di Kecamatan Makassar dan Tallo berjumlah ${n(st.total)} anak. Menurut status tinggi badan: ${f(st.status_tbu)}. ` +
    `Menurut jenis kelamin: ${f(st.jenis_kelamin)}. Menurut kecamatan: ${f(st.per_kecamatan)}. Menurut kelompok umur: ${f(st.kelompok_umur)}.`;
}

const b = (id: string, label: string, teks: string, kata: string[], target = id): Bagian => ({ id, label, teks, target, kata });

export function buatNarasi(halaman: HalamanKey | null, s: any, st: any): Narasi | null {
  if (!halaman) return null;
  const k = s?.kategori || {};
  const mudahAngka: ItemMudah[] = [
    { ikon: "disabilitas", teks: `Penyandang disabilitas: ${n(k.disabilitas?.total)} orang.` },
    { ikon: "stunting", teks: `Anak stunting (badan pendek): ${n(k.stunting?.total)} anak.` },
    { ikon: "ats", teks: `Anak tidak sekolah: ${n(k.ats?.total)} anak.` },
    { ikon: "kemiskinan", teks: `Keluarga sangat miskin: ${n(k.kemiskinan?.total)} keluarga.` },
  ];
  const privasi: ItemMudah = { ikon: "privasi", teks: "Nama dan alamat orang tidak ditampilkan. Data aman." };
  const tangan: ItemMudah = { ikon: "tangan", teks: "Butuh juru bahasa isyarat? Tekan tombol Asisten Aksesibilitas di kanan bawah." };

  if (halaman === "beranda") {
    return {
      judul: "Beranda PETA INKLUSI",
      pembuka: "Anda berada di halaman Beranda PETA INKLUSI, Bappeda Kota Makassar.",
      bagian: [
        b("a11y-pengantar", "Pengantar", "PETA INKLUSI menyajikan data agregat disabilitas, stunting, anak tidak sekolah, dan kemiskinan per kecamatan dan kelurahan untuk perencanaan dan pengajuan program intervensi di Kota Makassar.", ["pengantar", "tentang"]),
        b("a11y-4data", "Empat data utama", `Empat data utama Kota Makassar berupa angka agregat tanpa data pribadi. ${ringkasEmpat(s)}`, ["data utama", "angka", "ringkasan"]),
        b("a11y-galeri", "Galeri program", "Galeri program selesai menampilkan foto dan cerita dampak program bagi kelompok rentan. Tekan Tab untuk menelusuri setiap program.", ["galeri", "program"]),
        b("a11y-fitur", "Fitur layanan", "Fitur yang tersedia meliputi Dashboard publik berisi statistik agregat tanpa masuk akun, Peta sosial dan kemiskinan per kecamatan dan kelurahan, Usulan program NGO, serta Privasi data yang menyamarkan identitas warga.", ["fitur", "layanan", "menu"]),
      ],
      mudah: [
        { ikon: "info", teks: "Ini portal PETA INKLUSI milik Bappeda Kota Makassar." },
        { ikon: "info", teks: "Portal ini memuat data warga yang memerlukan bantuan di Makassar." },
        ...mudahAngka, privasi,
        { ikon: "peta", teks: "Mau lihat peta? Pilih menu Peta Sosial." }, tangan,
      ],
    };
  }
  if (halaman === "publik") {
    return {
      judul: "Dashboard Informasi Umum",
      pembuka: `Anda berada di Dashboard Informasi Umum. Kota Makassar memiliki ${n(s?.wilayah?.kecamatan)} kecamatan dan ${n(s?.wilayah?.kelurahan)} kelurahan. Halaman ini hanya menampilkan data agregat tanpa data pribadi.`,
      bagian: [
        b("a11y-ringkasan", "Ringkasan empat kategori", ringkasEmpat(s), ["ringkasan", "empat kategori", "angka"]),
        b("a11y-wilayah", "Wilayah dan DTSEN", `Kota Makassar terdiri dari ${n(s?.wilayah?.kecamatan)} kecamatan dan ${n(s?.wilayah?.kelurahan)} kelurahan. Rumah tangga DTSEN terdata: ${n(s?.dtsen?.rumah_tangga)}.`, ["wilayah", "dtsen", "kecamatan"]),
        b("a11y-statistik", "Statistik per kecamatan", statKecamatan(s), ["statistik", "per kecamatan", "grafik batang"]),
        b("a11y-tren-kemiskinan", "Tren kemiskinan", trenKemiskinan(s), ["kemiskinan", "miskin"]),
        b("a11y-tren-stunting", "Tren stunting", trenStunting(s), ["tren stunting", "prevalensi"]),
        b("a11y-ats", "Anak tidak sekolah per tahun", trenAts(s), ["anak tidak sekolah", "ats", "sekolah"]),
        b("a11y-balita", "Balita stunting 2026", balitaStunting(st), ["balita", "stunting"]),
        b("a11y-galeri", "Galeri program", "Galeri program intervensi menampilkan foto dan cerita dampak program. Tekan Tab untuk menelusuri setiap program.", ["galeri", "program"]),
        b("a11y-kondisi", "Ringkasan kondisi sosial", kondisi(s), ["kondisi", "terbanyak", "kesimpulan"]),
      ],
      mudah: [
        ...mudahAngka,
        { ikon: "peta", teks: `Kecamatan dengan keluarga sangat miskin paling banyak: ${top(s?.per_kecamatan, "kemiskinan", 1)[0]?.kecamatan || "-"}.` },
        { ikon: "stunting", teks: `Kecamatan dengan anak stunting paling banyak: ${top(s?.per_kecamatan, "stunting", 1)[0]?.kecamatan || "-"}.` },
        privasi, tangan,
      ],
    };
  }
  const petaTabel = (judul: string) => `${judul} juga tersedia sebagai tabel data di bawah peta, sehingga dapat dibaca dengan pembaca layar. Gunakan tautan Lewati peta untuk langsung menuju tabel.`;
  if (halaman === "peta_sosial") {
    return {
      judul: "Peta Sosial",
      pembuka: "Anda berada di halaman Peta Sosial. Peta berwarna menampilkan data disabilitas, stunting, dan anak tidak sekolah per kecamatan dan kelurahan. Warna lebih gelap berarti jumlah lebih banyak.",
      bagian: [
        b("a11y-peta-tentang", "Tentang peta", `Peta Sosial menampilkan data agregat disabilitas, stunting, dan anak tidak sekolah. ${petaTabel("Isi peta")}`, ["tentang peta", "peta"], "a11y-peta"),
        b("a11y-peta-disabilitas", "Peringkat disabilitas", `Kecamatan dengan penyandang disabilitas terbanyak: ${rankKec(s, "disabilitas", 5, "orang")}.`, ["disabilitas"], "a11y-peta-tabel"),
        b("a11y-peta-stunting", "Peringkat stunting", `Kecamatan dengan anak stunting terbanyak: ${rankKec(s, "stunting", 5, "anak")}.`, ["stunting"], "a11y-peta-tabel"),
        b("a11y-peta-ats", "Peringkat anak tidak sekolah", `Kecamatan dengan anak tidak sekolah terbanyak: ${rankKec(s, "ats", 5, "anak")}.`, ["anak tidak sekolah", "ats", "sekolah"], "a11y-peta-tabel"),
        b("a11y-peta-tabel", "Tabel data peta", `Tabel data peta berisi ${n(s?.per_kecamatan?.length)} kecamatan dengan kolom disabilitas, stunting, dan anak tidak sekolah.`, ["tabel"]),
      ],
      mudah: [
        { ikon: "peta", teks: "Ini peta Kota Makassar." },
        { ikon: "info", teks: "Warna makin gelap = jumlah orang makin banyak." },
        { ikon: "disabilitas", teks: `Disabilitas paling banyak: Kecamatan ${top(s?.per_kecamatan, "disabilitas", 1)[0]?.kecamatan || "-"}.` },
        { ikon: "stunting", teks: `Stunting paling banyak: Kecamatan ${top(s?.per_kecamatan, "stunting", 1)[0]?.kecamatan || "-"}.` },
        { ikon: "ats", teks: `Anak tidak sekolah paling banyak: Kecamatan ${top(s?.per_kecamatan, "ats", 1)[0]?.kecamatan || "-"}.` },
        { ikon: "info", teks: "Klik wilayah di peta untuk melihat angkanya. Tabel ada di bawah peta." }, tangan,
      ],
    };
  }
  return {
    judul: "Peta Kemiskinan",
    pembuka: "Anda berada di halaman Peta Kemiskinan. Peta berwarna menampilkan indikator kemiskinan per kecamatan dan kelurahan. Warna lebih gelap berarti angka lebih tinggi.",
    bagian: [
      b("a11y-peta-tentang", "Tentang peta", `Peta Kemiskinan menampilkan kepala keluarga desil 1 dan 2, penerima bantuan PBI, dan rumah rentan. ${petaTabel("Isi peta")}`, ["tentang peta", "peta"], "a11y-peta"),
      b("a11y-peta-kemiskinan", "Peringkat kemiskinan ekstrem", `Kecamatan dengan kepala keluarga miskin ekstrem terbanyak: ${rankKec(s, "kemiskinan", 5, "KK")}. Persentase penduduk miskin kota tahun 2025: ${n(k.kemiskinan?.persen_kota)} persen.`, ["kemiskinan", "miskin", "peringkat"], "a11y-peta-tabel"),
      b("a11y-peta-tabel", "Tabel data peta", `Tabel data peta berisi ${n(s?.per_kecamatan?.length)} kecamatan dengan jumlah kepala keluarga miskin ekstrem dan persentase kemiskinan.`, ["tabel"]),
    ],
    mudah: [
      { ikon: "peta", teks: "Ini peta kemiskinan Kota Makassar." },
      { ikon: "info", teks: "Warna makin gelap = keluarga miskin makin banyak." },
      { ikon: "kemiskinan", teks: `Keluarga sangat miskin di Makassar: ${n(k.kemiskinan?.total)} keluarga.` },
      { ikon: "kemiskinan", teks: `Paling banyak di Kecamatan ${top(s?.per_kecamatan, "kemiskinan", 1)[0]?.kecamatan || "-"}.` },
      { ikon: "info", teks: "Tabel angka ada di bawah peta." }, tangan,
    ],
  };
}

export function teksHalamanPenuh(nr: Narasi) {
  return [nr.pembuka, ...nr.bagian.map((x, i) => `Bagian ${i + 1}: ${x.label}. ${x.teks}`),
    "Selesai. Tekan Alt dan angka untuk melompat ke bagian tertentu, atau tekan tanda tanya untuk bantuan."].join(" ");
}

export { KAT_LABEL };
