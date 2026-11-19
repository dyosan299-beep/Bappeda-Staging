import React, { useState } from "react";
import { toast } from "sonner";
import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { unduhExport } from "@/features/data/manageApi";

/**
 * Tombol export Excel/CSV yang selalu mengirim filter dashboard yang sedang aktif
 * ke backend, sehingga isi berkas sama dengan yang dilihat pengguna.
 */
export default function ExportButtons({
  jalur, filter = {}, testid = "btn-export",
}: {
  jalur: "dtsen" | "disabilitas" | "rad" | "kelurahan";
  filter?: Record<string, any>;
  testid?: string;
}) {
  const [proses, setProses] = useState<string | null>(null);

  const unduh = async (format: "xlsx" | "csv") => {
    setProses(format);
    try {
      const nama = await unduhExport(jalur, format, filter);
      toast.success(`Berkas ${nama} berhasil diunduh (mengikuti filter aktif)`);
    } catch {
      toast.error("Gagal mengunduh berkas export");
    } finally {
      setProses(null);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid={testid}>
      <button type="button" onClick={() => unduh("xlsx")} disabled={!!proses}
        data-testid={`${testid}-xlsx`} title="Export Excel mengikuti filter aktif"
        className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
        {proses === "xlsx" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSpreadsheet className="h-4 w-4 text-emerald-600" />}
        Excel
      </button>
      <button type="button" onClick={() => unduh("csv")} disabled={!!proses}
        data-testid={`${testid}-csv`} title="Export CSV mengikuti filter aktif"
        className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
        {proses === "csv" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4 text-sky-600" />}
        CSV
      </button>
      <span className="hidden items-center text-[10px] text-slate-400 md:inline-flex">
        <Download className="mr-1 h-3 w-3" /> ikut filter
      </span>
    </div>
  );
}
