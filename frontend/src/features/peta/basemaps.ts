import { BasemapId } from "./types";

export const STATUS_COLORS: Record<string, string> = {
  hijau: "#00C853",
  kuning: "#FFC107",
  merah: "#FF5252",
};

export const STATUS_LABEL: Record<string, string> = {
  hijau: "Data lengkap / kondisi baik",
  kuning: "Perlu diverifikasi",
  merah: "Bermasalah / tidak layak huni",
};

export interface BasemapDef {
  id: BasemapId;
  label: string;
  group: "Google Maps" | "Alternatif (tanpa API key)";
  requiresGoogle: boolean;
}

export const BASEMAPS: BasemapDef[] = [
  { id: "google_hybrid", label: "Google Hybrid", group: "Google Maps", requiresGoogle: true },
  { id: "google_satellite", label: "Google Satellite", group: "Google Maps", requiresGoogle: true },
  { id: "google_roadmap", label: "Google Jalan (Roadmap)", group: "Google Maps", requiresGoogle: true },
  { id: "esri_hybrid", label: "ESRI Imagery + Label", group: "Alternatif (tanpa API key)", requiresGoogle: false },
  { id: "esri_imagery", label: "ESRI Satellite / Imagery", group: "Alternatif (tanpa API key)", requiresGoogle: false },
  { id: "osm", label: "OSM Jalan", group: "Alternatif (tanpa API key)", requiresGoogle: false },
];

/** Bila Google belum aktif (API key kosong), pakai padanan basemap gratis. */
export function fallbackBasemap(basemap: BasemapId): BasemapId {
  switch (basemap) {
    case "google_satellite":
      return "esri_imagery";
    case "google_hybrid":
      return "esri_hybrid";
    case "google_roadmap":
      return "osm";
    default:
      return basemap;
  }
}

export function isGoogleBasemap(basemap: BasemapId): boolean {
  return basemap.startsWith("google_");
}

const ESRI_IMAGERY =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const ESRI_LABELS =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}";
const ESRI_TRANSPORT =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}";
const OSM = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export interface TileSpec {
  urls: string[];
  attribution: string;
  maxNativeZoom: number;
}

export const TILE_SPECS: Record<string, TileSpec> = {
  esri_imagery: {
    urls: [ESRI_IMAGERY],
    attribution: "Citra: Esri, Maxar, Earthstar Geographics",
    maxNativeZoom: 19,
  },
  esri_hybrid: {
    urls: [ESRI_IMAGERY, ESRI_TRANSPORT, ESRI_LABELS],
    attribution: "Citra & label: Esri",
    maxNativeZoom: 19,
  },
  osm: {
    urls: [OSM],
    attribution: "&copy; OpenStreetMap",
    maxNativeZoom: 19,
  },
};
