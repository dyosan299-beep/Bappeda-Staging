/* Pengelola overlay layer PETA DASAR di atas peta Leaflet.
   Dipakai oleh leafletEngine (halaman Peta Rumah) dan halaman Peta Sosial. */
import L from "leaflet";
import { BasemapFeatureCollection, BasemapLayerMeta } from "./basemapTypes";

const PANE = "sidataBasemapPane";

const LABELS: Record<string, string> = {
  nama: "Nama",
  jenis: "Jenis",
  fungsi: "Fungsi",
  kelas: "Kelas penutup lahan",
  klasifikasi: "Klasifikasi",
  status: "Status batas",
  remark: "Dasar hukum",
  elevasi: "Elevasi (m)",
  interval: "Interval kontur",
  panjang_m: "Panjang (m)",
  luas_m2: "Luas (m\u00b2)",
  kelurahan: "Kelurahan",
  kecamatan: "Kecamatan",
  kota: "Kota",
  provinsi: "Provinsi",
  tipe: "Tipe",
  tahun_sumber: "Tahun data",
  kode: "Kode",
  sumber: "Sumber",
  // GeoTag Verval DTSEN (lapisan dari modul Verval)
  status_verval: "Status Verval",
  rw_rt: "RW / RT",
  gps: "Koordinat",
  foto: "Jumlah foto",
  waktu: "Diperbarui",
};

const ORDER = [
  "nama", "klasifikasi", "jenis", "fungsi", "kelas", "elevasi", "interval",
  "status", "status_verval", "remark", "kelurahan", "kecamatan", "rw_rt", "kota", "provinsi",
  "gps", "foto", "waktu", "panjang_m", "luas_m2", "tahun_sumber", "kode", "sumber",
];

const STATUS_VERVAL_LABEL: Record<string, string> = {
  draft: "Draft", terkirim: "Terkirim · menunggu pemeriksaan", perlu_perbaikan: "Perlu perbaikan",
  disetujui: "Disetujui", ditolak: "Ditolak",
};

function esc(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtNum(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return esc(value);
  return n.toLocaleString("id-ID", { maximumFractionDigits: 1 });
}

export function popupHtml(meta: BasemapLayerMeta, props: Record<string, unknown>): string {
  const rows: string[] = [];
  ORDER.forEach((key) => {
    const val = props[key];
    if (val === undefined || val === null || val === "" || val === 0) return;
    let teks = key === "panjang_m" || key === "luas_m2" ? fmtNum(val) : esc(val);
    if (key === "status_verval") teks = esc(STATUS_VERVAL_LABEL[String(val)] || val);
    if (key === "waktu") {
      try { teks = esc(new Date(String(val)).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" })); } catch { /* biarkan */ }
    }
    rows.push(
      `<tr><td style="color:#64748b;padding:1px 6px 1px 0;vertical-align:top">${esc(
        LABELS[key] || key,
      )}</td><td style="font-weight:600;color:#0f172a">${teks}</td></tr>`,
    );
  });
  if (!rows.length) {
    rows.push(
      `<tr><td colspan="2" style="color:#64748b">Tidak ada atribut tambahan pada fitur ini.</td></tr>`,
    );
  }
  const tautan = props.record_id
    ? `<a href="/verval/review?id=${encodeURIComponent(String(props.record_id))}" style="display:inline-block;margin-top:6px;font-weight:700;color:#117A69">Buka detail Verval →</a>`
    : "";
  return (
    `<div style="min-width:190px;max-width:280px;font-size:11.5px">` +
    `<div style="font-weight:700;color:#0f172a;margin-bottom:4px">${esc(meta.label)}</div>` +
    `<table style="border-collapse:collapse">${rows.join("")}</table>` +
    tautan +
    `</div>`
  );
}

export interface OverlayController {
  setOverlay: (id: string, fc: BasemapFeatureCollection, meta: BasemapLayerMeta) => void;
  removeOverlay: (id: string) => void;
  clearAll: () => void;
}

export function createOverlayController(map: L.Map): OverlayController {
  if (!map.getPane(PANE)) {
    const pane = map.createPane(PANE);
    // di bawah overlayPane (400) agar polygon rumah/choropleth tetap di atas
    pane.style.zIndex = "380";
  }
  const layers: Record<string, L.GeoJSON> = {};

  const warnaFitur = (meta: BasemapLayerMeta, feature: any): string => {
    const field = meta.kategori_field;
    if (!field) return meta.warna;
    const kat = String(feature?.properties?.[field] ?? "");
    return (meta.kategori_warna || {})[kat] || meta.warna;
  };

  const styleFor = (meta: BasemapLayerMeta) => (feature: any): L.PathOptions => {
    const color = warnaFitur(meta, feature);
    if (meta.tipe === "polygon") {
      return {
        color,
        weight: meta.weight ?? 0.8,
        opacity: 0.9,
        fillColor: color,
        fillOpacity: meta.fill_opacity ?? 0.35,
        dashArray: meta.dash || undefined,
      };
    }
    return {
      color,
      weight: meta.weight ?? 1.4,
      opacity: 0.95,
      fill: false,
      dashArray: meta.dash || undefined,
    };
  };

  return {
    setOverlay(id, fc, meta) {
      if (layers[id]) {
        map.removeLayer(layers[id]);
        delete layers[id];
      }
      const layer = L.geoJSON(fc as any, {
        pane: PANE,
        style: styleFor(meta) as any,
        pointToLayer: (feature: any, latlng: L.LatLng) =>
          L.circleMarker(latlng, {
            pane: PANE,
            radius: 4,
            color: "#ffffff",
            weight: 1,
            fillColor: warnaFitur(meta, feature),
            fillOpacity: 0.95,
          }),
        onEachFeature: (feature: any, lyr: L.Layer) => {
          const props = (feature && feature.properties) || {};
          const nama = String(props.nama || props.kelas || props.klasifikasi || props.jenis || meta.label);
          lyr.bindTooltip(nama, { sticky: true, className: "text-[11px]" });
          lyr.bindPopup(popupHtml(meta, props), { maxWidth: 300, autoPan: true });
        },
      }).addTo(map);
      layers[id] = layer;
    },

    removeOverlay(id) {
      if (layers[id]) {
        map.removeLayer(layers[id]);
        delete layers[id];
      }
    },

    clearAll() {
      Object.keys(layers).forEach((id) => {
        map.removeLayer(layers[id]);
        delete layers[id];
      });
    },
  };
}
