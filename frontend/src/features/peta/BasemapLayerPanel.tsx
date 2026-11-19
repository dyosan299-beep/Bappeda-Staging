/* Panel pemilih layer PETA DASAR (Edisi 2021 - BIG) untuk halaman peta. */
import React, { useState } from "react";
import { ChevronDown, ChevronRight, Layers3, Loader2, Map as MapIcon, XCircle } from "lucide-react";
import { BasemapLayerMeta } from "./basemapTypes";
import { LayerStatus } from "./useBasemapLayers";

interface Props {
  grup: { grup: string; items: BasemapLayerMeta[] }[];
  aktif: string[];
  status: Record<string, LayerStatus>;
  jumlahTampil: Record<string, number>;
  sumber: string;
  onToggle: (id: string) => void;
  onReset: () => void;
  className?: string;
}

const fmt = (n: number) => Number(n || 0).toLocaleString("id-ID");

export default function BasemapLayerPanel({
  grup,
  aktif,
  status,
  jumlahTampil,
  sumber,
  onToggle,
  onReset,
  className = "",
}: Props) {
  const [terbuka, setTerbuka] = useState(false);
  const [grupTerbuka, setGrupTerbuka] = useState<string[]>(["Batas Administrasi", "Transportasi"]);
  const [legendaTerbuka, setLegendaTerbuka] = useState<string[]>([]);

  const toggleGrup = (g: string) =>
    setGrupTerbuka((cur) => (cur.includes(g) ? cur.filter((x) => x !== g) : [...cur, g]));
  const toggleLegenda = (id: string) =>
    setLegendaTerbuka((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));

  return (
    <div
      className={`w-72 max-w-full overflow-hidden rounded-lg border border-slate-200 bg-white/95 shadow-lg backdrop-blur ${className}`}
      data-testid="basemap-layer-panel"
    >
      <button
        type="button"
        data-testid="btn-toggle-peta-dasar"
        onClick={() => setTerbuka((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left"
      >
        <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-700">
          <Layers3 className="h-3.5 w-3.5" /> Layer Peta Dasar
        </span>
        <span className="flex items-center gap-1.5">
          {aktif.length > 0 && (
            <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold text-primary">
              {aktif.length} aktif
            </span>
          )}
          {terbuka ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
        </span>
      </button>

      {terbuka && (
        <div className="max-h-[60vh] overflow-y-auto border-t border-slate-200 px-3 pb-3">
          {grup.length === 0 && (
            <p className="py-2 text-[11px] text-slate-500">Daftar layer belum tersedia.</p>
          )}

          {grup.map((g) => (
            <div key={g.grup} className="mt-2">
              <button
                type="button"
                onClick={() => toggleGrup(g.grup)}
                className="flex w-full items-center gap-1 text-[10.5px] font-bold uppercase tracking-wide text-slate-500 hover:text-slate-700"
              >
                {grupTerbuka.includes(g.grup) ? (
                  <ChevronDown className="h-3 w-3" />
                ) : (
                  <ChevronRight className="h-3 w-3" />
                )}
                {g.grup}
              </button>

              {grupTerbuka.includes(g.grup) && (
                <ul className="mt-1 space-y-1">
                  {g.items.map((l) => {
                    const st = status[l.id] || "kosong";
                    const on = aktif.includes(l.id);
                    const kategori = Object.entries(l.kategori_warna || {});
                    return (
                      <li key={l.id} className="rounded border border-slate-100 bg-slate-50/60 p-1.5">
                        <label className="flex cursor-pointer items-start gap-2">
                          <input
                            type="checkbox"
                            data-testid={`layer-${l.id}`}
                            checked={on}
                            onChange={() => onToggle(l.id)}
                            className="mt-[3px] h-3.5 w-3.5 accent-slate-700"
                          />
                          <span className="flex-1">
                            <span className="flex items-center gap-1.5">
                              <span
                                className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                                style={{ backgroundColor: l.warna }}
                              />
                              <span className="text-[11.5px] font-semibold text-slate-800">{l.label}</span>
                              {st === "memuat" && <Loader2 className="h-3 w-3 animate-spin text-slate-500" />}
                            </span>
                            <span className="mt-0.5 block text-[10px] text-slate-500">
                              {fmt(l.jumlah)} fitur
                              {l.panjang_km ? ` · ${fmt(Math.round(l.panjang_km))} km` : ""}
                              {l.luas_ha ? ` · ${fmt(Math.round(l.luas_ha))} ha` : ""}
                            </span>
                            {on && st === "perlu_zoom" && (
                              <span className="mt-0.5 block rounded bg-amber-50 px-1 py-0.5 text-[10px] font-semibold text-amber-800">
                                Perbesar peta ke zoom {l.min_zoom}+ untuk menampilkan
                              </span>
                            )}
                            {on && st === "tampil" && jumlahTampil[l.id] !== undefined && (
                              <span className="mt-0.5 block text-[10px] text-emerald-700">
                                {fmt(jumlahTampil[l.id])} fitur tampil
                                {l.bbox_required ? " (area tampilan)" : ""}
                              </span>
                            )}
                            {on && st === "gagal" && (
                              <span className="mt-0.5 block text-[10px] font-semibold text-rose-700">
                                Gagal dimuat — coba lagi
                              </span>
                            )}
                            {kategori.length > 1 && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault();
                                  toggleLegenda(l.id);
                                }}
                                className="mt-0.5 text-[10px] font-semibold text-slate-500 underline hover:text-slate-700"
                              >
                                {legendaTerbuka.includes(l.id) ? "Sembunyikan legenda" : `Legenda (${kategori.length})`}
                              </button>
                            )}
                            {legendaTerbuka.includes(l.id) && (
                              <span className="mt-1 block space-y-0.5">
                                {kategori.map(([k, c]) => (
                                  <span key={k} className="flex items-center gap-1.5 text-[10px] text-slate-600">
                                    <span
                                      className="inline-block h-2 w-2 shrink-0 rounded-sm"
                                      style={{ backgroundColor: c }}
                                    />
                                    {k}
                                  </span>
                                ))}
                              </span>
                            )}
                          </span>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          ))}

          <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-2">
            <span className="flex items-start gap-1 text-[9.5px] leading-tight text-slate-500">
              <MapIcon className="mt-[1px] h-3 w-3 shrink-0" />
              {sumber || "Peta Dasar Kota Makassar Edisi 2021"}
            </span>
            <button
              type="button"
              data-testid="btn-reset-layer"
              onClick={onReset}
              className="inline-flex items-center gap-1 rounded border border-slate-300 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-100"
            >
              <XCircle className="h-3 w-3" /> Nonaktifkan
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
