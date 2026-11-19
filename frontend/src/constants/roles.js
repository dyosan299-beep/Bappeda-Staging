/**
 * Himpunan peran yang dipakai bersama oleh navigasi dan penjaga rute.
 * Disimpan terpisah agar sidebar dan App.js tidak lagi mendefinisikan ulang
 * daftar yang sama (risiko menu dan hak akses tidak sinkron).
 */

export const SUPER = ["superadmin", "admin"];
export const ADMINS = ["superadmin", "admin", "verifikator", "admin_bappeda"];
// Petugas & Operator RT/RW hanya: Dashboard Publik + Verval/GeoTag (bukan pengguna internal umum)
export const INTERNAL = ["superadmin", "admin", "verifikator", "admin_bappeda", "operator",
  "pimpinan", "admin_opd", "operator_kecamatan", "operator_kelurahan", "viewer"];
export const WRITERS = ["superadmin", "admin", "operator", "verifikator"];
export const VERVAL_OPERATOR = ["operator_rt_rw", "petugas"];
export const VERVAL_REVIEWER = [
  "operator_kelurahan", "operator", "operator_kecamatan",
  "verifikator", "admin_bappeda", "superadmin", "admin", "pimpinan",
];
export const VERVAL_PENUGASAN = ["superadmin", "admin", "admin_bappeda", "operator", "operator_kecamatan"];
export const USER_MANAGERS = ["superadmin", "admin", "operator", "operator_kecamatan"];
// Peran yang datanya dibatasi sesuai wilayah masing-masing
export const SCOPED = ["operator", "verifikator", "petugas", "operator_kecamatan", "operator_kelurahan", "operator_rt_rw"];
