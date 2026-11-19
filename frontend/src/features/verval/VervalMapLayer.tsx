import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { Camera, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { api, fotoUrl, GPS_LABEL, STATUS_COLOR, STATUS_LABEL, KESIMPULAN_LABEL, fmtWaktu } from "./api";
import { FR } from "@/features/a11y/ui";
import { isMapAlive } from "@/lib/leafletSafe";

export const VERVAL_PETA_EVENT = "verval:peta-berubah";

/** Panggil setelah foto/GPS/record Verval berubah agar seluruh peta memuat ulang lapisan GeoTag. */
export function umumkanPerubahanPeta() {
  try { window.dispatchEvent(new Event(VERVAL_PETA_EVENT)); } catch { /* abaikan */ }
}

const esc = (v: unknown) => String(v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** Isi popup GeoTag yang konsisten di semua peta (disesuaikan dengan data wilayah peta). */
export function vervalPopupHtml(t: any, opts: { linkDetail?: boolean; linkForm?: boolean } = {}): string {
  const color = STATUS_COLOR[t.status] || "#475569";
  const fotos: any[] = Array.isArray(t.foto) ? t.foto : [];
  const thumbs = fotos.slice(0, 3).map((f) => {
    const g = f.gps || {};
    const koor = g.lat != null ? `${Number(g.lat).toFixed(5)}, ${Number(g.lng).toFixed(5)}` : "tanpa koordinat";
    return `<a href="${fotoUrl(f.id)}" target="_blank" rel="noreferrer" title="${esc(f.jenis)} · ${esc(koor)}" style="display:block">
      <img src="${fotoUrl(f.id)}" alt="Foto ${esc(f.jenis)}" style="width:72px;height:54px;object-fit:cover;border-radius:6px;border:1px solid #e2e8f0"/>
      <span style="display:block;font-size:9px;color:#64748b;max-width:72px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(koor)}</span></a>`;
  }).join("");
  const rows = [
    ["Status", `<b style="color:${color}">${esc(STATUS_LABEL[t.status] || t.status)}</b>`],
    ...(t.kepala_keluarga ? [["Kepala Keluarga", esc(t.kepala_keluarga)]] : []),
    ...(t.nik ? [["NIK", esc(t.nik)]] : []),
    ["Kelurahan", esc(t.kelurahan || "-")],
    ["Kecamatan", esc(t.kecamatan || "-")],
    ["RW / RT", `RW ${esc(t.rw || "-")} / RT ${esc(t.rt || "-")}`],
    ["Koordinat", `${Number(t.lat).toFixed(6)}, ${Number(t.lng).toFixed(6)}${t.akurasi_m != null ? ` (±${esc(t.akurasi_m)} m)` : ""}`],
    ["Sumber titik", esc(t.sumber_koordinat === "pin_manual" ? `Pin manual${t.alasan_manual ? ` (${t.alasan_manual})` : ""}` : t.sumber_koordinat === "foto" ? "koordinat foto" : (t.sumber_koordinat || "").startsWith("foto_") ? "koordinat foto (otomatis)" : "GPS perangkat")],
    ["GPS", esc(GPS_LABEL[t.status_gps] || t.status_gps || "-")],
    ["Kesimpulan", esc(t.kesimpulan ? KESIMPULAN_LABEL[t.kesimpulan] || t.kesimpulan : "-")],
    ["Petugas", esc(t.operator_nama || "-")],
    ["Diperbarui", esc(fmtWaktu(t.updated_at))],
  ].map(([k, v]) => `<tr><td style="color:#64748b;padding:1px 6px 1px 0;vertical-align:top;white-space:nowrap">${k}</td><td style="font-weight:600;color:#0f172a">${v}</td></tr>`).join("");
  let links = "";
  if (opts.linkDetail) links += `<a href="/verval/review?id=${encodeURIComponent(t.id)}" style="display:inline-block;margin-top:6px;font-weight:700;color:#117A69">Buka detail Verval →</a>`;
  if (opts.linkForm && t.dtsen_ref) links += `<a href="/verval/sasaran/${encodeURIComponent(t.dtsen_ref)}" style="display:inline-block;margin-top:6px;font-weight:700;color:#117A69">Buka formulir Verval →</a>`;
  return `<div style="min-width:210px;max-width:300px;font-size:11.5px">
    <div style="font-weight:800;color:#0f172a;margin-bottom:4px">GeoTag Verval DTSEN${t.jenis_verval === "warga_baru" ? ' <span style="color:#117A69">· WARGA BARU</span>' : ""}${t.data_uji ? ' <span style="color:#b45309">· DATA UJI</span>' : ""}</div>
    <table style="border-collapse:collapse">${rows}</table>
    ${fotos.length ? `<div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap">${thumbs}</div>` : ""}
    <p style="margin:6px 0 0;color:#64748b">Foto: ${fotos.length} · Titik GeoTag Verval.</p>
    ${links}</div>`;
}

/** Ambil data lapisan GeoTag (satu sumber: GET /api/verval/peta). */
export function useVervalPeta() {
  const [data, setData] = useState<any>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    api.get("/verval/peta").then((r) => { if (alive) setData(r.data); }).catch(() => { if (alive) setData(false); });
    return () => { alive = false; };
  }, [tick]);
  useEffect(() => {
    const h = () => setTick((t) => t + 1);
    window.addEventListener(VERVAL_PETA_EVENT, h);
    window.addEventListener("focus", h);
    return () => { window.removeEventListener(VERVAL_PETA_EVENT, h); window.removeEventListener("focus", h); };
  }, []);
  return { data, reload: () => setTick((t) => t + 1) };
}

/** Lapisan GeoTag-Verval untuk peta Leaflet (Peta Sosial, Peta Kemiskinan, Titik Koordinat).
 *  Backend menentukan apa yang boleh dilihat:
 *  - Petugas RT/RW (wilayahnya), Kelurahan (kelurahannya), Kecamatan (kecamatannya), Admin Bappeda, Superadmin, Pimpinan: titik + foto + detail
 *  - Admin OPD / Viewer: rekap agregat per kelurahan */
export default function VervalMapLayer({ map, compact = false }: { map: L.Map | null; compact?: boolean }) {
  const { data, reload } = useVervalPeta();
  const [show, setShow] = useState(true);
  const [open, setOpen] = useState(false);
  const layerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!isMapAlive(map)) return;
    try { layerRef.current?.remove(); } catch { /* noop */ }
    layerRef.current = null;
    if (!data || data.mode !== "titik" || !show) return;
    const g = L.layerGroup();
    (data.titik || []).forEach((t: any) => {
      const color = STATUS_COLOR[t.status] || "#475569";
      const m = L.circleMarker([t.lat, t.lng], { radius: 8, color: "#fff", weight: 2, fillColor: color, fillOpacity: 0.95, pane: "markerPane" });
      m.bindTooltip(`GeoTag · ${t.kelurahan || "-"} · RW ${t.rw || "-"}/RT ${t.rt || "-"} · ${t.foto_count || 0} foto`, { direction: "top", className: "text-[11px]" });
      m.bindPopup(vervalPopupHtml(t, { linkDetail: !!data.peran_hasil, linkForm: !!data.peran_pelaksana }), { maxWidth: 320 });
      m.addTo(g);
    });
    g.addTo(map);
    layerRef.current = g;
    return () => { try { g.remove(); } catch { /* noop */ } };
  }, [map, data, show]);

  if (!data) return null;
  const titik = data.mode === "titik";
  return (
    <div className={`absolute bottom-3 left-3 z-[450] rounded-[14px] bg-white p-3 shadow-[0_18px_50px_rgba(35,47,62,.18)] ring-1 ring-slate-200 ${compact ? "w-[260px]" : "w-[300px]"} max-w-[calc(100%-5rem)] sm:max-w-[calc(100%-1.5rem)]`} data-testid="verval-map-layer">
      <div className="flex items-center justify-between gap-2">
        <label className="flex min-w-0 items-center gap-2 text-xs font-bold text-slate-800">
          {titik && <input type="checkbox" checked={show} onChange={(e) => setShow(e.target.checked)} data-testid="verval-layer-toggle" />}
          <Camera className="h-4 w-4 shrink-0 text-[#117A69]" /> <span className="truncate">GeoTag Verval DTSEN</span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px]" data-testid="verval-layer-count">{data.total}</span>
        </label>
        <div className="flex shrink-0 items-center">
          <button type="button" onClick={reload} aria-label="Muat ulang lapisan GeoTag" className={`rounded p-1 hover:bg-slate-100 ${FR}`} data-testid="verval-layer-reload"><RefreshCw className="h-3.5 w-3.5" /></button>
          <button type="button" onClick={() => setOpen(!open)} aria-label="Rincian lapisan GeoTag" className={`rounded p-1 hover:bg-slate-100 ${FR}`} data-testid="verval-layer-expand">
            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          </button>
        </div>
      </div>
      {open && (
        <div className="mt-2 space-y-2 text-[11px] text-slate-600">
          {data.scope_kelurahan && <p className="rounded bg-[#117A69]/10 px-2 py-1 font-semibold text-[#0f5f52]" data-testid="verval-layer-scope-kel">Wilayah: Kel. {data.scope_kelurahan}</p>}
          {data.scope_kecamatan && <p className="rounded bg-[#117A69]/10 px-2 py-1 font-semibold text-[#0f5f52]" data-testid="verval-layer-scope">Wilayah: Kec. {data.scope_kecamatan}</p>}
          {titik ? (
            <div className="flex flex-wrap gap-2">
              {Object.entries(STATUS_COLOR).map(([k, c]) => (
                <span key={k} className="inline-flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />{STATUS_LABEL[k]}</span>
              ))}
            </div>
          ) : (
            <div data-testid="verval-layer-agregat">
              <p className="mb-1">{data.catatan}</p>
              <ul className="max-h-40 space-y-0.5 overflow-auto">
                {(data.kelurahan || []).map((k: any) => (
                  <li key={k.kode_kelurahan || k.kelurahan} className="flex justify-between"><span>{k.kelurahan}</span><b>{k.total} ({k.per_status?.disetujui || 0} disetujui)</b></li>
                ))}
                {!data.kelurahan?.length && <li>Belum ada hasil Verval terkirim.</li>}
              </ul>
            </div>
          )}
          <p className="rounded bg-amber-50 p-2 text-amber-900" data-testid="verval-layer-bangunan-note">{data.integrasi_bangunan?.alasan}</p>
        </div>
      )}
    </div>
  );
}
