import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ChevronDown, Download, FileSpreadsheet, FileText, PencilLine, Plus, Trash2,
} from "lucide-react";
import api from "@/lib/api";

export type PilihanInput = {
  label: string;
  ket: string;
  icon: React.ComponentType<{ className?: string }>;
  aksi: () => void;
  testid: string;
};

/**
 * Tombol "+ INPUT DATA" dengan pilihan Input Manual / Import Excel / Import CSV.
 * Halaman lain (mis. Data Stunting, Data ATS) dapat memberi `pilihan` sendiri agar
 * posisi & tampilan tombol tetap seragam dengan halaman Disabilitas.
 */
export function InputDataButton({
  jenis, onManual, testid = "btn-input-data", pilihan: pilihanKhusus,
}: {
  jenis?: "dtsen" | "disabilitas" | "rad" | "gis_koordinat";
  onManual?: () => void;
  testid?: string;
  pilihan?: PilihanInput[];
}) {
  const [buka, setBuka] = useState(false);
  const nav = useNavigate();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const klik = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setBuka(false);
    };
    document.addEventListener("mousedown", klik);
    return () => document.removeEventListener("mousedown", klik);
  }, []);

  const unduhTemplate = async () => {
    try {
      const res = await api.get("/import/template", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "Template_Import_SIDATA.xlsx";
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success("Template Excel berhasil diunduh");
    } catch {
      toast.error("Gagal mengunduh template Excel");
    }
  };

  const pilihan: PilihanInput[] = pilihanKhusus || [
    {
      label: "Input Manual", ket: "Isi formulir data satu per satu",
      icon: PencilLine, aksi: () => onManual?.(), testid: "menu-input-manual",
    },
    {
      label: "Import Excel", ket: "Unggah .xlsx / .xls, banyak sheet didukung",
      icon: FileSpreadsheet, aksi: () => nav(`/impor?jenis=${jenis}`), testid: "menu-import-excel",
    },
    {
      label: "Import CSV", ket: "Unggah berkas .csv",
      icon: FileText, aksi: () => nav(`/impor?jenis=${jenis}&format=csv`), testid: "menu-import-csv",
    },
    {
      label: "Download Template Excel", ket: "Header sesuai basis data + contoh & petunjuk",
      icon: Download, aksi: unduhTemplate, testid: "menu-template",
    },
  ];

  return (
    <div className="relative" ref={ref}>
      <button type="button" data-testid={testid} onClick={() => setBuka((b) => !b)} aria-haspopup="menu" aria-expanded={buka}
        className="inline-flex h-9 items-center gap-2 rounded-md bg-slate-900 px-3 text-sm font-semibold text-white hover:bg-slate-800">
        <Plus className="h-4 w-4" /> Input Data <ChevronDown className="h-3.5 w-3.5" />
      </button>
      {buka && (
        <div className="absolute right-0 z-[800] mt-1 w-72 max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-md border border-slate-200 bg-white shadow-xl"
          data-testid="menu-input-data" role="menu">
          {pilihan.map((p) => (
            <button key={p.label} type="button" data-testid={p.testid} role="menuitem"
              onClick={() => { setBuka(false); p.aksi(); }}
              className="flex w-full items-start gap-2 border-b border-slate-100 px-3 py-2 text-left last:border-b-0 hover:bg-slate-50">
              <p.icon className="mt-0.5 h-4 w-4 text-slate-500" />
              <span>
                <span className="block text-sm font-semibold text-slate-800">{p.label}</span>
                <span className="block text-[11px] text-slate-500">{p.ket}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Dialog konfirmasi hapus dengan alasan (tercatat pada audit log). */
export function KonfirmasiHapus({
  judul, keterangan, onBatal, onHapus,
}: {
  judul: string;
  keterangan?: string;
  onBatal: () => void;
  onHapus: (alasan: string) => Promise<void>;
}) {
  const [alasan, setAlasan] = useState("");
  const [proses, setProses] = useState(false);
  return (
    <div className="fixed inset-0 z-[960] flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-4 shadow-2xl" data-testid="dialog-hapus">
        <h3 className="flex items-center gap-2 font-head text-base font-bold text-rose-700">
          <Trash2 className="h-4 w-4" /> {judul}
        </h3>
        {keterangan && <p className="mt-1 text-xs text-slate-600">{keterangan}</p>}
        <p className="mt-2 text-xs text-slate-600">
          Tindakan ini tidak dapat dibatalkan. Perubahan tercatat pada audit log.
        </p>
        <label className="mt-3 block text-[11px] font-semibold uppercase tracking-wide text-slate-600">
          Alasan penghapusan
        </label>
        <input value={alasan} onChange={(e) => setAlasan(e.target.value)} data-testid="hapus-alasan"
          placeholder="mis. data ganda / permintaan kelurahan"
          className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm" />
        <div className="mt-3 flex justify-end gap-2">
          <button type="button" onClick={onBatal}
            className="h-9 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-700">
            Batal
          </button>
          <button type="button" disabled={proses} data-testid="hapus-konfirmasi"
            onClick={async () => { setProses(true); try { await onHapus(alasan); } finally { setProses(false); } }}
            className="h-9 rounded-md bg-rose-600 px-4 text-sm font-semibold text-white disabled:opacity-50">
            Hapus Data
          </button>
        </div>
      </div>
    </div>
  );
}
