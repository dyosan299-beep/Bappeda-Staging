import api from "@/lib/api";

export interface WilayahSummary {
  kota: string;
  jumlah_kecamatan: number;
  jumlah_kelurahan: number;
  total_households: number;
  total_individu: number;
  kecamatan: { kode: string; nama: string; jumlah_kelurahan: number; total_households: number }[];
}

export interface SosialFilter {
  kode_kecamatan?: string;
  kode_kelurahan?: string;
  desil?: string | number;
  pbi_nas?: string | number;
  pbi_pemda?: string | number;
  risk_level?: string;
}

function params(f: Record<string, any> = {}) {
  const out: Record<string, any> = {};
  Object.entries(f).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== "semua") out[k] = v;
  });
  return out;
}

export const getWilayahSummary = async (): Promise<WilayahSummary> =>
  (await api.get("/wilayah/summary")).data;

export const getKelurahan = async (kode_kecamatan?: string) =>
  (await api.get("/wilayah/kelurahan", { params: params({ kode_kecamatan }) })).data as {
    items: { kode: string; nama: string; kecamatan: string; total_households: number }[];
  };

export const getSosialOverview = async (f: SosialFilter = {}) =>
  (await api.get("/sosial/overview", { params: params(f) })).data as any;

export const getRanking = async (level: string, metric: string, kode_kecamatan?: string, limit = 15) =>
  (await api.get("/sosial/ranking", { params: params({ level, metric, kode_kecamatan, limit }) })).data as any;

export const getHouseholds = async (f: Record<string, any>) =>
  (await api.get("/sosial/households", { params: params(f) })).data as any;

export const getHousehold = async (id: string) =>
  (await api.get(`/sosial/households/${id}`)).data as any;

export const getScoringConfig = async () => (await api.get("/sosial/scoring-config")).data as any;
export const putScoringConfig = async (payload: any) =>
  (await api.put("/sosial/scoring-config", payload)).data as any;

export const getGeoKelurahan = async (metric: string) =>
  (await api.get("/geo/kelurahan", { params: params({ metric }) })).data as any;

export const getPrioritas = async (limit = 10, kode_kecamatan?: string) =>
  (await api.get("/analisis/prioritas", { params: params({ limit, kode_kecamatan }) })).data as any;

export const getDisabilitas = async (kecamatan?: string) =>
  (await api.get("/disabilitas/overview", { params: params({ kecamatan }) })).data as any;

export const getStuntingOverview = async () => (await api.get("/stunting/overview")).data as any;
export const getStuntingItems = async (f: Record<string, any>) =>
  (await api.get("/stunting/items", { params: params(f) })).data as any;

export const getRadOverview = async () => (await api.get("/rad/overview")).data as any;
export const getRadItems = async (f: Record<string, any>) =>
  (await api.get("/rad/items", { params: params(f) })).data as any;
export const putRadMonitoring = async (id: string, payload: any) =>
  (await api.put(`/rad/monitoring/${id}`, payload)).data as any;

export const getImportSummary = async () => (await api.get("/admin/import-summary")).data as any;
export const getImportBatches = async () => (await api.get("/admin/import-batches")).data as any;
export const getQualitySummary = async () => (await api.get("/admin/data-quality/summary")).data as any;
export const getQualityIssues = async (f: Record<string, any>) =>
  (await api.get("/admin/data-quality", { params: params(f) })).data as any;

export const fmtNum = (n: any) => Number(n || 0).toLocaleString("id-ID");
export const fmtRp = (n: any) => {
  const v = Number(n || 0);
  if (v >= 1e12) return `Rp ${(v / 1e12).toFixed(2)} T`;
  if (v >= 1e9) return `Rp ${(v / 1e9).toFixed(2)} M`;
  if (v >= 1e6) return `Rp ${(v / 1e6).toFixed(1)} Jt`;
  return `Rp ${v.toLocaleString("id-ID")}`;
};
