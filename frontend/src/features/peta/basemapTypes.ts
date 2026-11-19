// Tipe data layer PETA DASAR (hasil ekstraksi PETA_DASAR.gdb Edisi 2021 - BIG)

export type BasemapLayerTipe = "line" | "polygon" | "point";

export interface KategoriStat {
  kategori: string;
  jumlah: number;
  panjang_km: number;
  luas_ha: number;
}

export interface BasemapLayerMeta {
  id: string;
  label: string;
  grup: string;
  tipe: BasemapLayerTipe;
  file: string;
  jumlah: number;
  ukuran_bytes: number;
  bbox?: number[] | null;
  warna: string;
  fill_opacity?: number;
  weight?: number;
  dash?: string | null;
  min_zoom: number;
  bbox_required: boolean;
  kategori_field?: string | null;
  kategori_warna: Record<string, string>;
  keterangan?: string;
  sumber?: string;
  aktif_default?: boolean;
  panjang_km?: number;
  luas_ha?: number;
  per_kategori?: KategoriStat[];
}

export interface BasemapLayersResponse {
  generated_at: string | null;
  sumber: string;
  kota: string;
  grup: string[];
  total_layer: number;
  layers: BasemapLayerMeta[];
}

export interface BasemapFeature {
  type: "Feature";
  properties: Record<string, unknown>;
  geometry: { type: string; coordinates: unknown };
}

export interface BasemapFeatureCollection {
  type: "FeatureCollection";
  id: string;
  label: string;
  tipe: BasemapLayerTipe;
  warna: string;
  fill_opacity?: number;
  weight?: number;
  dash?: string | null;
  kategori_field?: string | null;
  kategori_warna: Record<string, string>;
  sumber?: string;
  count: number;
  total: number;
  truncated: boolean;
  bbox?: number[] | null;
  features: BasemapFeature[];
}

export interface PetaDasarRingkasan {
  sumber: string;
  generated_at: string | null;
  luas_kota_ha: number;
  jumlah_kelurahan: number;
  panjang_jalan_km: number;
  panjang_jalan_utama_km: number;
  panjang_jalan_lingkungan_km: number;
  panjang_sungai_kanal_km: number;
  panjang_garis_pantai_km: number;
  panjang_batas_administrasi_km: number;
  luas_perairan_ha: number;
  jumlah_jembatan: number;
  jumlah_toponimi: number;
  jumlah_kontur: number;
  jumlah_penutup_lahan: number;
  penutup_lahan_teratas: KategoriStat[];
  jalan_per_fungsi: KategoriStat[];
  toponimi_per_klasifikasi: KategoriStat[];
}

export interface FasilitasItem {
  fid: string;
  nama: string;
  jenis: string;
  klasifikasi: string;
  kelurahan: string;
  kecamatan: string;
  kode: string;
  lng: number;
  lat: number;
  sumber: string;
}

export interface FasilitasResponse {
  total: number;
  page: number;
  page_size: number;
  total_page: number;
  items: FasilitasItem[];
  filters: {
    klasifikasi: string[];
    jenis: string[];
    kecamatan: string[];
    kelurahan: string[];
  };
  sumber?: string;
}

export interface FasilitasRekapRow {
  wilayah: string;
  kecamatan: string;
  total: number;
  per_klasifikasi: Record<string, number>;
}

export interface FasilitasRekapResponse {
  level: "kelurahan" | "kecamatan";
  total: number;
  klasifikasi: { kategori: string; jumlah: number }[];
  rows: FasilitasRekapRow[];
  sumber?: string;
}
