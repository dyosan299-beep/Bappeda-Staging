/**
 * Matriks peran & wewenang PETA INKLUSI / SIDATA (sinkron dengan backend verval & manajemen user).
 */
export const ROLE_LABELS: Record<string, string> = {
  superadmin: "Superadmin",
  admin: "Superadmin",
  admin_bappeda: "Admin Bappeda",
  verifikator: "Verifikator",
  admin_opd: "Admin OPD",
  operator: "Kecamatan",
  operator_kecamatan: "Kecamatan",
  operator_kelurahan: "Kelurahan",
  petugas: "Petugas RT/RW",
  operator_rt_rw: "Petugas RT/RW",
  pimpinan: "Pimpinan",
  viewer: "Viewer",
};

/** Boleh menambah / mengubah data (input manual & impor). */
export const PERAN_TULIS = [
  "superadmin", "admin", "admin_bappeda", "verifikator", "admin_opd",
  "operator_kecamatan", "operator", "operator_kelurahan",
];

/** Boleh menghapus data. */
export const PERAN_HAPUS = ["superadmin", "admin", "admin_bappeda", "verifikator"];

/** Boleh melihat data detail keluarga dalam cakupan wilayahnya. */
export const PERAN_SENSITIF = [
  "superadmin", "admin", "admin_bappeda", "verifikator",
  "operator", "operator_kecamatan", "operator_kelurahan", "petugas", "operator_rt_rw",
];

/** Boleh mengelola master kode & pengguna. */
export const PERAN_ADMIN = ["superadmin", "admin"];

export const bolehTulis = (role?: string) => PERAN_TULIS.includes(role || "");
export const bolehHapus = (role?: string) => PERAN_HAPUS.includes(role || "");
export const bolehLihatSensitif = (role?: string) => PERAN_SENSITIF.includes(role || "");
export const labelPeran = (role?: string) => ROLE_LABELS[role || ""] || role || "-";
