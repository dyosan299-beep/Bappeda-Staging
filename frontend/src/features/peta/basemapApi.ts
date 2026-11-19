import api from "@/lib/api";
import {
  BasemapFeatureCollection,
  BasemapLayersResponse,
  FasilitasRekapResponse,
  FasilitasResponse,
  PetaDasarRingkasan,
} from "./basemapTypes";

export async function fetchBasemapLayers(): Promise<BasemapLayersResponse> {
  const { data } = await api.get("/peta-dasar/layers");
  return data as BasemapLayersResponse;
}

export interface LayerQuery {
  bbox?: string;
  kategori?: string;
  limit?: number;
}

export async function fetchBasemapLayer(
  id: string,
  q: LayerQuery = {},
): Promise<BasemapFeatureCollection> {
  const params: Record<string, string | number> = {};
  if (q.bbox) params.bbox = q.bbox;
  if (q.kategori) params.kategori = q.kategori;
  if (q.limit) params.limit = q.limit;
  const { data } = await api.get(`/peta-dasar/layer/${id}`, { params });
  return data as BasemapFeatureCollection;
}

export async function fetchPetaDasarRingkasan(): Promise<PetaDasarRingkasan> {
  const { data } = await api.get("/peta-dasar/ringkasan");
  return data as PetaDasarRingkasan;
}

export interface FasilitasQuery {
  search?: string;
  klasifikasi?: string;
  jenis?: string;
  kelurahan?: string;
  kecamatan?: string;
  page?: number;
  page_size?: number;
}

export async function fetchFasilitas(q: FasilitasQuery = {}): Promise<FasilitasResponse> {
  const params: Record<string, string | number> = {};
  Object.entries(q).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== "semua") {
      params[k] = v as string | number;
    }
  });
  const { data } = await api.get("/peta-dasar/fasilitas", { params });
  return data as FasilitasResponse;
}

export async function fetchFasilitasRekap(
  level: "kelurahan" | "kecamatan" = "kelurahan",
  kecamatan?: string,
): Promise<FasilitasRekapResponse> {
  const params: Record<string, string> = { level };
  if (kecamatan && kecamatan !== "semua") params.kecamatan = kecamatan;
  const { data } = await api.get("/peta-dasar/fasilitas/rekap", { params });
  return data as FasilitasRekapResponse;
}
