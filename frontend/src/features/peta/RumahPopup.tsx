import React from "react";
import { X } from "lucide-react";
import { STATUS_COLORS, STATUS_LABEL } from "./basemaps";
import { Pixel, RumahProps } from "./types";

const FALLBACK_FOTO =
  "https://images.pexels.com/photos/8840839/pexels-photo-8840839.jpeg";

const POPUP_WIDTH = 320;

interface Props {
  data: RumahProps;
  pixel: Pixel | null;
  containerSize: { width: number; height: number };
  onClose: () => void;
}

function Row({ label, value }: { label: string; value?: React.ReactNode }) {
  const shown =
    value === undefined || value === null || value === "" ? "-" : value;
  return (
    <div className="flex items-start justify-between gap-2 border-b border-dashed border-slate-200 py-[3px] last:border-0">
      <span className="shrink-0 text-slate-500">{label}</span>
      <span className="text-right font-semibold text-slate-800">{shown}</span>
    </div>
  );
}

export function RumahPopup({ data, pixel, containerSize, onClose }: Props) {
  const status = String(data.status || "kuning");
  const color = STATUS_COLORS[status] || STATUS_COLORS.kuning;
  const cardRef = React.useRef<HTMLDivElement | null>(null);
  const [cardHeight, setCardHeight] = React.useState(360);

  React.useLayoutEffect(() => {
    if (cardRef.current) setCardHeight(cardRef.current.offsetHeight || 360);
  }, [data.id, containerSize.height]);

  // Posisi popup: diusahakan di atas titik, lalu dijepit agar selalu utuh
  // di dalam kanvas peta (tidak menembus header maupun tepi bawah).
  const popupWidth = containerSize.width > 0
    ? Math.min(POPUP_WIDTH, Math.max(260, containerSize.width - 24))
    : POPUP_WIDTH;
  const px = pixel?.x ?? containerSize.width / 2;
  const py = pixel?.y ?? containerSize.height / 2;
  const maxLeft = Math.max(containerSize.width - popupWidth - 12, 12);
  const left = Math.min(Math.max(px - popupWidth / 2, 12), maxLeft);
  const maxTop = Math.max(containerSize.height - cardHeight - 12, 12);
  const preferredTop = py - cardHeight - 16;
  const top = Math.min(Math.max(preferredTop < 12 ? py + 16 : preferredTop, 12), maxTop);

  return (
    <div
      ref={cardRef}
      data-testid="rumah-popup"
      className="pointer-events-auto absolute z-[500]"
      style={{ left, top, width: popupWidth }}
    >
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-2xl">
        <div className="relative">
          <img
            src={(data.foto_url as string) || FALLBACK_FOTO}
            alt={`Foto rumah ${data.pemilik || ""}`}
            className="h-32 w-full object-cover"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src = FALLBACK_FOTO;
            }}
          />
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup popup"
            className="absolute right-2 top-2 inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-slate-700 shadow hover:bg-white"
          >
            <X className="h-4 w-4" />
          </button>
          <div className="absolute bottom-2 left-2 flex items-center gap-2 rounded-md bg-white/92 px-2 py-1 shadow">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-700">
              {STATUS_LABEL[status] || status}
            </span>
          </div>
        </div>

        <div className="max-h-[46vh] overflow-y-auto px-3 py-2 text-[11.5px] leading-snug">
          <p className="mb-1 text-sm font-bold uppercase text-slate-900" data-testid="popup-nama">
            {data.pemilik || data.nama || "-"}
          </p>
          <p className="mb-2 text-[11px] text-slate-500">
            {data.kode ? `${data.kode} · ` : ""}
            {data.kondisi || "-"}
          </p>
          <Row label="Nama" value={data.nama} />
          <Row label="Pemilik" value={data.pemilik} />
          <Row label="Jumlah Orang" value={data.jumlah_orang} />
          <Row label="KK" value={data.no_kk} />
          <Row label="RT" value={data.rt} />
          <Row label="RW" value={data.rw} />
          <Row label="Penghasilan" value={data.penghasilan} />
          <Row label="Bantuan" value={data.bantuan} />
          <Row label="Tahun Bangunan" value={data.tahun_bangunan} />
          <Row label="Dinding" value={data.dinding} />
          <Row label="Atap" value={data.atap} />
          <Row label="Lantai" value={data.lantai} />
          <Row label="Sanitasi" value={data.sanitasi} />
          <Row label="Air" value={data.air} />
          <Row label="Status Lahan" value={data.status_lahan} />
          <Row label="Kelurahan" value={data.kelurahan} />
          <Row label="Kecamatan" value={data.kecamatan} />
          <Row label="Jalan" value={data.jalan} />
          <Row label="Keterangan" value={data.keterangan} />
          <Row
            label="Luas"
            value={data.luas != null ? `${Number(data.luas).toFixed(2)} m²` : "-"}
          />
        </div>

        <div className="border-t border-slate-200 p-2">
          <button
            type="button"
            data-testid="popup-tutup"
            onClick={onClose}
            className="w-full rounded-md bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-200"
          >
            Tutup
          </button>
        </div>
      </div>
    </div>
  );
}

export default RumahPopup;
