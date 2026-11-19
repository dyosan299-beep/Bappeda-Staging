// Tipe data modul PETA (GIS level bangunan) SIDATA

export type StatusRumah = "hijau" | "kuning" | "merah";

export interface RumahProps {
  id: string;
  kode?: string;
  nama?: string;
  pemilik?: string;
  jumlah_orang?: number;
  no_kk?: string;
  rt?: string;
  rw?: string;
  kelurahan?: string;
  kecamatan?: string;
  penghasilan?: string;
  bantuan?: string;
  tahun_bangunan?: string;
  dinding?: string;
  atap?: string;
  lantai?: string;
  sanitasi?: string;
  air?: string;
  status_lahan?: string;
  jalan?: string;
  keterangan?: string;
  luas?: number;
  kondisi?: string;
  status?: StatusRumah | string;
  foto_url?: string;
  lat?: number;
  lng?: number;
  [key: string]: unknown;
}

export interface RumahFeature {
  type: "Feature";
  id?: string;
  geometry: { type: string; coordinates: unknown };
  properties: RumahProps;
}

export interface RumahFeatureCollection {
  type: "FeatureCollection";
  features: RumahFeature[];
  bbox?: number[] | null;
  count?: number;
}

export interface LegendItem {
  status: string;
  label: string;
  color: string;
}

export interface MapConfig {
  center: { lat: number; lng: number };
  zoom: number;
  basemap: string;
  kota: string;
  google_maps_api_key: string;
  google_maps_enabled: boolean;
  legend: LegendItem[];
}

export interface RumahFilters {
  kelurahan: string[];
  rw_by_kelurahan: Record<string, string[]>;
  rw_all: string[];
  total: number;
}

export interface RumahStats {
  total: number;
  per_status: Record<string, number>;
  per_bantuan: Record<string, number>;
  per_kelurahan: Record<string, number>;
  total_jiwa: number;
  total_luas: number;
  legend: LegendItem[];
}

export type BasemapId =
  | "google_roadmap"
  | "google_satellite"
  | "google_hybrid"
  | "esri_imagery"
  | "esri_hybrid"
  | "osm";

export interface EngineOptions {
  center: { lat: number; lng: number };
  zoom: number;
  basemap: BasemapId;
  apiKey?: string;
}

export interface Pixel {
  x: number;
  y: number;
}

/** Antarmuka umum agar halaman peta tidak bergantung pada mesin peta tertentu. */
export interface MapEngine {
  readonly kind: "google" | "leaflet";
  setBasemap(basemap: BasemapId): void;
  setData(fc: RumahFeatureCollection): void;
  /** Layer PETA DASAR (jalan, perairan, penutup lahan, toponimi, dll). */
  setOverlay(id: string, fc: any, meta: any): void;
  removeOverlay(id: string): void;
  /** Batas tampilan aktif: [minLng, minLat, maxLng, maxLat]. */
  getBounds(): number[] | null;
  setSelected(id: string | null): void;
  fitBounds(bbox?: number[] | null): void;
  setView(center: { lat: number; lng: number }, zoom: number): void;
  zoomIn(): void;
  /** Hitung ulang ukuran kanvas setelah kontainer berubah (opsional). */
  resize?(): void;
  zoomOut(): void;
  getZoom(): number;
  project(lat: number, lng: number): Pixel | null;
  onSelect(cb: (props: RumahProps | null) => void): void;
  onViewChange(cb: () => void): void;
  destroy(): void;
}
