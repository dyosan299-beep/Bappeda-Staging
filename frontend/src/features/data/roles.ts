/**
 * Matriks peran & wewenang SIDATA (7 peran).
 *
 * Peran lama tetap berlaku (kompatibilitas akun yang sudah ada):
 *   superadmin/admin      -> Super Admin
 *   verifikator           -> Admin Bappeda
 *   petugas               -> Operator Kecamatan
 *   operator              -> Operator Kelurahan
 *   pimpinan              -> Pimpinan
 * Peran baru: admin_opd (Admin OPD), viewer (Viewer).
 */
export const ROLE_LABELS: Record<string, string> = {
  superadmin: "Super Admin",
  admin: "Super Admin",
  admin_bappeda: "Admin Bappeda",
  verifikator: "Admin Bappeda",
  admin_opd: "Admin OPD",
  petugas: "Operator Kecamatan",
  operator_kecamatan: "Operator Kecamatan",
  operator: "Operator Kelurahan",
  operator_kelurahan: "Operator Kelurahan",
  pimpinan: "Pimpinan",
  viewer: "Viewer",
};

/** Boleh menambah / mengubah data (input manual & impor). */
export const PERAN_TULIS = [
  "superadmin", "admin", "admin_bappeda", "verifikator", "admin_opd",
  "petugas", "operator_kecamatan", "operator", "operator_kelurahan",
];

/** Boleh menghapus data. */
export const PERAN_HAPUS = ["superadmin", "admin", "admin_bappeda", "verifikator"];

/** Boleh melihat data pribadi tanpa penyamaran. */
export const PERAN_SENSITIF = ["superadmin", "admin", "admin_bappeda", "verifikator"];

/** Boleh mengelola master kode & pengguna. */
export const PERAN_ADMIN = ["superadmin", "admin"];

export const bolehTulis = (role?: string) => PERAN_TULIS.includes(role || "");
export const bolehHapus = (role?: string) => PERAN_HAPUS.includes(role || "");
export const bolehLihatSensitif = (role?: string) => PERAN_SENSITIF.includes(role || "");
export const labelPeran = (role?: string) => ROLE_LABELS[role || ""] || role || "-";
