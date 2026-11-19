import api from "@/lib/api";

/* ------------------------------------------------------------------ tipe */
export interface FieldMeta {
  name: string;
  label: string;
  tipe: "text" | "int" | "num" | "kode";
  required: boolean;
  section: string;
  keterangan?: string;
  contoh?: any;
  opsi?: { kode: string; label: string; jumlah_data: number }[];
}

export interface FieldSection {
  section: string;
  fields: FieldMeta[];
}

export interface KodeItem {
  id: string;
  field: string;
  field_label: string;
  kode: string;
  label: string;
  keterangan: string;
  jumlah_data: number;
  sumber: string;
  updated_at?: string;
  updated_by?: string;
}

export interface WilayahOpsi {
  kode: string;
  nama: string;
  kecamatan?: string;
  kode_kecamatan?: string;
}

/* --------------------------------------------------------------- helper */
function bersih(f: Record<string, any> = {}) {
  const out: Record<string, any> = {};
  Object.entries(f).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== "semua") out[k] = v;
  });
  return out;
}

/** Ubah galat backend menjadi pesan yang mudah dipahami operator. */
export function pesanGalat(err: any): { pesan: string; rincian: { kolom: string; pesan: string }[]; duplikat?: any } {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return { pesan: detail, rincian: [] };
  if (detail && typeof detail === "object") {
    const rincian = Array.isArray(detail.errors) ? detail.errors : [];
    const dup = Array.isArray(detail.pilihan) ? detail : undefined;
    return { pesan: detail.message || "Data tidak dapat diproses", rincian, duplikat: dup };
  }
  if (Array.isArray(detail)) {
    return {
      pesan: "Data yang dikirim belum lengkap atau formatnya salah",
      rincian: detail.map((d: any) => ({ kolom: (d.loc || []).slice(-1)[0], pesan: d.msg })),
    };
  }
  return { pesan: err?.message || "Terjadi kesalahan tak terduga", rincian: [] };
}

/* ------------------------------------------------------- master kode kode */
export const getKodeReferensi = async (field?: string, hanya_kosong?: boolean) =>
  (await api.get("/master/kode", { params: bersih({ field, hanya_kosong }) })).data as {
    total: number; items: KodeItem[]; belum_didefinisikan: number;
    fields: { name: string; label: string; jumlah_kode: number }[];
  };

export const getKodeMap = async () =>
  (await api.get("/master/kode/map")).data as {
    labels: Record<string, Record<string, string>>;
    fields: Record<string, string>;
  };

export const putKode = async (id: string, payload: { label?: string; keterangan?: string }) =>
  (await api.put(`/master/kode/${encodeURIComponent(id)}`, payload)).data;

export const postKode = async (payload: { field: string; kode: string; label: string; keterangan?: string }) =>
  (await api.post("/master/kode", payload)).data;

export const deleteKode = async (id: string) =>
  (await api.delete(`/master/kode/${encodeURIComponent(id)}`)).data;

/* ------------------------------------------------------- master wilayah */
export const getProvinsi = async () =>
  (await api.get("/master/wilayah/provinsi")).data as { items: WilayahOpsi[] };
export const getKabupaten = async (kode_provinsi?: string) =>
  (await api.get("/master/wilayah/kabupaten", { params: bersih({ kode_provinsi }) })).data as { items: WilayahOpsi[] };
export const getKecamatanMaster = async (kode_kabupaten_kota?: string) =>
  (await api.get("/master/wilayah/kecamatan", { params: bersih({ kode_kabupaten_kota }) })).data as { items: WilayahOpsi[] };
export const getKelurahanMaster = async (kode_kecamatan?: string) =>
  (await api.get("/master/wilayah/kelurahan", { params: bersih({ kode_kecamatan }) })).data as { items: WilayahOpsi[] };

/* ------------------------------------------------------ metadata form */
export const getFieldMeta = async (jenis: string) =>
  (await api.get(`/master/fields/${jenis}`)).data as {
    jenis: string; label: string; kunci_duplikat: string; sections: FieldSection[];
  };

/* ------------------------------------------------------------ DTSEN CRUD */
export const createHousehold = async (data: Record<string, any>, mode_duplikat = "tolak", catatan = "") =>
  (await api.post("/sosial/households", { data, mode_duplikat, catatan })).data;

export const updateHousehold = async (id: string, data: Record<string, any>, catatan = "") =>
  (await api.put(`/sosial/households/${id}`, { data, catatan })).data;

export const deleteHousehold = async (id: string, alasan = "") =>
  (await api.delete(`/sosial/households/${id}`, { params: bersih({ alasan }) })).data;

export const getHouseholdForm = async (id: string) =>
  (await api.get(`/sosial/households/${id}/form`)).data as { id: string; data: Record<string, any> };

/* ------------------------------------------------------ DISABILITAS CRUD */
export const getDisabilitasItems = async (f: Record<string, any> = {}) =>
  (await api.get("/disabilitas/items", { params: bersih(f) })).data as any;

export const createDisabilitas = async (data: Record<string, any>, mode_duplikat = "tolak") =>
  (await api.post("/disabilitas/items", { data, mode_duplikat })).data;

export const updateDisabilitas = async (id: string, data: Record<string, any>) =>
  (await api.put(`/disabilitas/items/${id}`, { data })).data;

export const deleteDisabilitas = async (id: string, alasan = "") =>
  (await api.delete(`/disabilitas/items/${id}`, { params: bersih({ alasan }) })).data;

/* ------------------------------------------------------------- RAD CRUD */
export const createRad = async (data: Record<string, any>, mode_duplikat = "tolak") =>
  (await api.post("/rad/items", { data, mode_duplikat })).data;

export const updateRad = async (id: string, data: Record<string, any>) =>
  (await api.put(`/rad/items/${id}`, { data })).data;

export const deleteRad = async (id: string, alasan = "") =>
  (await api.delete(`/rad/items/${id}`, { params: bersih({ alasan }) })).data;

export const getRadForm = async (id: string) =>
  (await api.get(`/rad/items/${id}/form`)).data as { id: string; data: Record<string, any> };

/* --------------------------------------------------------- KOORDINAT GIS */
export const getGisLocations = async (kode_kecamatan?: string) =>
  (await api.get("/gis/locations", { params: bersih({ kode_kecamatan }) })).data as {
    total: number; items: any[]; tanpa_koordinat: string[]; catatan: string;
  };

export const putGisLocation = async (kelurahan: string, payload: { latitude: number; longitude: number; keterangan?: string }) =>
  (await api.put(`/gis/locations/${encodeURIComponent(kelurahan)}`, payload)).data;

export const resetGisLocation = async (kelurahan: string) =>
  (await api.delete(`/gis/locations/${encodeURIComponent(kelurahan)}`)).data;

export const refreshAgregat = async () => (await api.post("/sosial/refresh-agregat")).data;

/* -------------------------------------------------------------- EXPORT */
/** Unduh berkas export (Excel/CSV) mengikuti filter yang sedang aktif. */
export async function unduhExport(
  jalur: "dtsen" | "disabilitas" | "rad" | "kelurahan",
  format: "xlsx" | "csv",
  filter: Record<string, any> = {},
) {
  const res = await api.get(`/export/${jalur}`, {
    params: bersih({ ...filter, format }),
    responseType: "blob",
  });
  const nama = (res.headers?.["content-disposition"] || "").match(/filename="?([^";]+)"?/)?.[1]
    || `export_${jalur}.${format}`;
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = nama;
  a.click();
  window.URL.revokeObjectURL(url);
  return nama;
}

