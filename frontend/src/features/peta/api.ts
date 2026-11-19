import api from "@/lib/api";
import {
  MapConfig,
  RumahFeatureCollection,
  RumahFilters,
  RumahProps,
  RumahStats,
} from "./types";

export async function fetchMapConfig(): Promise<MapConfig> {
  const { data } = await api.get("/map/config");
  return data as MapConfig;
}

export async function fetchFilters(): Promise<RumahFilters> {
  const { data } = await api.get("/rumah/filters");
  return data as RumahFilters;
}

export interface RumahQuery {
  kelurahan?: string;
  rw?: string;
  status?: string;
  search?: string;
}

function cleanParams(q: RumahQuery): Record<string, string> {
  const out: Record<string, string> = {};
  Object.entries(q || {}).forEach(([k, v]) => {
    if (v && v !== "semua") out[k] = String(v);
  });
  return out;
}

export async function fetchGeoJSON(q: RumahQuery = {}): Promise<RumahFeatureCollection> {
  const { data } = await api.get("/rumah/geojson", { params: cleanParams(q) });
  return data as RumahFeatureCollection;
}

export async function fetchStats(q: RumahQuery = {}): Promise<RumahStats> {
  const { data } = await api.get("/rumah/stats", { params: cleanParams(q) });
  return data as RumahStats;
}

export async function fetchRumahList(
  q: RumahQuery = {},
): Promise<{ total: number; items: RumahProps[] }> {
  const { data } = await api.get("/rumah", { params: cleanParams(q) });
  return data as { total: number; items: RumahProps[] };
}

export async function createRumah(payload: Partial<RumahProps>): Promise<RumahProps> {
  const { data } = await api.post("/rumah", payload);
  return data as RumahProps;
}

export async function updateRumah(
  id: string,
  payload: Partial<RumahProps>,
): Promise<RumahProps> {
  const { data } = await api.put(`/rumah/${id}`, payload);
  return data as RumahProps;
}

export async function deleteRumah(id: string): Promise<void> {
  await api.delete(`/rumah/${id}`);
}
