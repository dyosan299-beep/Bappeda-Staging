import {
  ADMINS, INTERNAL, USER_MANAGERS, VERVAL_OPERATOR, VERVAL_PENUGASAN, VERVAL_REVIEWER, WRITERS,
} from "./roles.js";

/**
 * Sumber tunggal susunan navigasi PETA INKLUSI.
 *
 * Urutan mengikuti "Rekomendasi Urutan Menu PETA INKLUSI Sesuai SOP" (24 Oktober 2026)
 * bagian 2: sembilan kelompok proses, dari Ringkasan sampai Bantuan dan Aksesibilitas.
 * Label, tujuan, dan pengelompokan mengikuti bagian 4 dokumen yang sama; rute lama
 * tetap hidup agar tautan/bookmark tidak rusak.
 *
 * `icon` berupa nama kunci; pemetaan ke komponen lucide ada di SidebarLayout supaya
 * berkas ini tetap data murni (mudah diuji dan dipakai untuk dokumentasi pemetaan).
 * Nomor 01–09 pada dokumen hanya penanda urutan, tidak ditampilkan di sidebar.
 */
export const MENU = [
  {
    id: "ringkasan",
    label: "Ringkasan",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: "dashboard", roles: INTERNAL, testid: "nav-dashboard" },
      { to: "/publik", label: "Dashboard Publik", icon: "globe", roles: [...INTERNAL, ...VERVAL_OPERATOR], testid: "nav-publik" },
      { to: "/ngo/statistik", label: "Statistik Agregat", icon: "chart", roles: ["ngo"], testid: "nav-ngo-statistik" },
    ],
  },
  {
    id: "petugas",
    label: "Petugas dan Wilayah Tugas",
    items: [
      { to: "/validasi-akun", label: "Validasi Akun Petugas", icon: "userCheck", roles: USER_MANAGERS, testid: "nav-validasi-akun" },
      { to: "/verval/penugasan", label: "Penugasan Operator", icon: "shield", roles: VERVAL_PENUGASAN, testid: "nav-verval-penugasan" },
    ],
  },
  {
    id: "pendataan",
    label: "Pendataan Warga",
    items: [
      { to: "/input-data", label: "Input Data", icon: "edit", roles: ["superadmin", "admin", "operator", "operator_kecamatan"], testid: "nav-data" },
      { to: "/rumah-tangga", label: "Data Rumah Tangga", icon: "edit", roles: INTERNAL, testid: "nav-rumah-tangga" },
      { to: "/peta-rumah", label: "Data Rumah/Bangunan", icon: "home", roles: INTERNAL, testid: "nav-peta-rumah" },
      { to: "/sosial", label: "Data Kemiskinan", icon: "users", roles: INTERNAL, testid: "nav-sosial" },
      { to: "/data-stunting", label: "Data Stunting", icon: "baby", roles: INTERNAL, testid: "nav-data-stunting" },
      { to: "/data-ats", label: "Data ATS", icon: "graduation", roles: INTERNAL, testid: "nav-data-ats" },
      { to: "/disabilitas", label: "Data Disabilitas", icon: "accessibility", roles: INTERNAL, testid: "nav-disabilitas" },
    ],
  },
  {
    id: "verifikasi",
    label: "Verifikasi dan Pemutakhiran Data",
    items: [
      { to: "/verval", label: "Verval & GeoTag", icon: "camera", roles: VERVAL_OPERATOR, testid: "nav-verval-operator", end: true },
      { to: "/verifikasi", label: "Verifikasi Data", icon: "check", roles: ["superadmin", "admin", "verifikator"], testid: "nav-verifikasi" },
      { to: "/verval/review", label: "Hasil Verifikasi Data", icon: "shield", roles: VERVAL_REVIEWER, testid: "nav-verval-review" },
    ],
  },
  {
    id: "peta",
    label: "Peta dan Kebutuhan Wilayah",
    items: [
      { to: "/peta-sosial", label: "Peta Sosial", icon: "map", roles: INTERNAL, testid: "nav-peta-sosial" },
      { to: "/ngo/peta-sosial", label: "Peta Sosial", icon: "map", roles: ["ngo"], testid: "nav-ngo-peta-sosial" },
      { to: "/peta-kemiskinan", label: "Peta Kemiskinan", icon: "home", roles: INTERNAL, testid: "nav-peta-kemiskinan" },
      { to: "/ngo/peta-kemiskinan", label: "Peta Kemiskinan", icon: "home", roles: ["ngo"], testid: "nav-ngo-peta-kemiskinan" },
      { to: "/peta-dasar", label: "Peta Dasar & Fasilitas", icon: "layers", roles: INTERNAL, testid: "nav-peta-dasar" },
      { to: "/prioritas", label: "Prioritas Intervensi", icon: "target", roles: INTERNAL, testid: "nav-prioritas" },
    ],
  },
  {
    id: "program",
    label: "Program dan Intervensi",
    items: [
      { to: "/ngo/inquiry", label: "Pengajuan Program NGO", icon: "send", roles: INTERNAL, testid: "nav-inquiry" },
      { to: "/musrenbang", label: "Musrenbang Tematik", icon: "target", roles: INTERNAL, testid: "nav-musrenbang" },
      { to: "/program", label: "Manajemen Program", icon: "target", roles: INTERNAL, testid: "nav-program" },
      { to: "/stunting", label: "Stunting: Program & Anggaran", icon: "handHeart", roles: INTERNAL, testid: "nav-stunting" },
      { to: "/rad", label: "RAD Disabilitas 2025–2030", icon: "check", roles: INTERNAL, testid: "nav-rad" },
      { to: "/bantuan", label: "Bantuan Sosial", icon: "handHeart", roles: INTERNAL, testid: "nav-bantuan" },
      { to: "/ngo/inquiry", label: "Status Pengajuan Saya", icon: "send", roles: ["ngo"], testid: "nav-ngo-inquiry", end: true },
      { to: "/ngo/inquiry/baru", label: "Ajukan Pengajuan", icon: "edit", roles: ["ngo"], testid: "nav-ngo-inquiry-baru" },
    ],
  },
  {
    id: "monitoring",
    label: "Monitoring, Evaluasi dan Laporan",
    items: [
      { to: "/matriks", label: "Matriks Evaluasi", icon: "clipboard", roles: INTERNAL, testid: "nav-matriks" },
      { to: "/laporan", label: "Laporan", icon: "clipboard", roles: INTERNAL, testid: "nav-laporan" },
      { to: "/laporan", label: "Laporan", icon: "clipboard", roles: ["ngo"], testid: "nav-ngo-laporan" },
      { to: "/ringkasan-mingguan", label: "Ringkasan Mingguan", icon: "calendar", roles: [...ADMINS, "pimpinan"], testid: "nav-ringkasan-mingguan" },
      { to: "/analisa-ai", label: "Analisis AI", icon: "sparkles", roles: INTERNAL, testid: "nav-ai" },
    ],
  },
  {
    id: "admin",
    label: "Administrasi Sistem",
    items: [
      { to: "/master-kode", label: "Master Kode Referensi", icon: "listTree", roles: ["superadmin", "admin"], testid: "nav-master-kode" },
      { to: "/gis-koordinat", label: "Titik Koordinat Kelurahan", icon: "mapPin", roles: ["superadmin", "admin", "verifikator", "operator", "pimpinan"], testid: "nav-gis-koordinat" },
      { to: "/impor-kualitas", label: "Impor & Kualitas Data", icon: "database", roles: INTERNAL, testid: "nav-impor-kualitas" },
      { to: "/kelola-petugas", label: "Manajemen Pengguna", icon: "users", roles: USER_MANAGERS, testid: "nav-users" },
      { to: "/role-permission", label: "Peran & Hak Akses", icon: "key", roles: ADMINS, testid: "nav-role-permission" },
      { to: "/audit-log", label: "Audit Log", icon: "scroll", roles: ADMINS, testid: "nav-audit-log" },
      { to: "/notifikasi-email", label: "Notifikasi Email", icon: "mail", roles: ADMINS, testid: "nav-notifikasi-email" },
    ],
  },
  {
    id: "bantuan",
    label: "Bantuan dan Aksesibilitas",
    items: [
      { to: "/ai-assistant", label: "Asisten AI", icon: "sparkles", roles: INTERNAL, testid: "nav-ai-assistant" },
      { to: "/panduan-alur", label: "Panduan Alur Sistem", icon: "listTree", roles: INTERNAL, testid: "nav-panduan-alur" },
      { to: "/aksesibilitas-bisindo", label: "Video BISINDO", icon: "hand", roles: ADMINS, testid: "nav-bisindo" },
    ],
  },
];

/** Pintasan tetap di kaki sidebar (WCAG 3.2.6): Mode Aksesibilitas selalu di posisi sama. */
export const UTILITY_ITEMS = [
  { to: "/aksesibilitas", label: "Mode Aksesibilitas", icon: "accessibility", testid: "nav-a11y" },
];

/** Staf yang boleh mengimpor data — dipakai hub Impor & Kualitas Data. */
export { WRITERS as PENULIS_IMPOR };

/** Judul untuk rute turunan yang tidak punya item menu sendiri. */
const JUDUL_TURUNAN = [
  ["/ngo/inquiry/baru", "Pengajuan Program NGO"],
  ["/ngo/inquiry", "Pengajuan Program NGO"],
  ["/verval/sasaran", "Formulir Verval DTSEN"],
  ["/verval/review", "Hasil Verifikasi Data"],
  ["/verval", "Verval & GeoTag"],
  ["/rekap", "Laporan"],
  ["/laporan-wilayah", "Laporan"],
  ["/administrasi", "Impor & Kualitas Data"],
  ["/impor", "Impor & Kualitas Data"],
  ["/dashboard-lama", "Dashboard"],
];

/** Apakah pengguna boleh melihat satu item menu. */
export function bolehLihat(item, user) {
  return !item.roles || (!!user && item.roles.includes(user.role));
}

/** Daftar datar item menu yang terlihat oleh pengguna (untuk pencarian & judul). */
export function menuDatar(user) {
  const out = [];
  MENU.forEach((grup) => {
    grup.items.forEach((item) => {
      if (bolehLihat(item, user)) out.push({ ...item, grup: grup.label });
    });
  });
  return out;
}

/** Judul halaman untuk header & `<title>` dokumen. */
export function judulHalaman(pathname, user) {
  const semua = [...menuDatar(user), ...UTILITY_ITEMS];
  const tepat = semua.find((n) => n.to === pathname);
  if (tepat) return tepat.label;
  const turunan = JUDUL_TURUNAN.find(([awal]) => pathname.startsWith(awal));
  return turunan ? turunan[1] : "PETA INKLUSI";
}

/** Nama kelompok menu dari halaman aktif (ditampilkan sebagai subjudul header). */
export function grupHalaman(pathname, user) {
  const tepat = menuDatar(user).find((n) => n.to === pathname);
  if (tepat) return tepat.grup;
  const turunan = JUDUL_TURUNAN.find(([awal]) => pathname.startsWith(awal));
  if (!turunan) return "";
  const induk = menuDatar(user).find((n) => n.label === turunan[1]);
  return induk ? induk.grup : "";
}
