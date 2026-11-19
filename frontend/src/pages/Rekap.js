import { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { API } from "@/lib/api";
import AIHistory from "@/components/AIHistory";
import {
  ClipboardList, FileDown, FileSpreadsheet, Download,
  Users, Baby, Footprints, GraduationCap, Accessibility, Home,
} from "lucide-react";

const fmt = (n) => (n ?? 0).toLocaleString("id-ID");

const KPIS = [
  { key: "kemiskinan_ekstrim_kk", label: "Kemiskinan Ekstrim", unit: "KK", icon: Home, color: "#DC2626" },
  { key: "stunting_anak", label: "Stunting", unit: "anak", icon: Baby, color: "#D97706" },
  { key: "ats", label: "Anak Tidak Sekolah", unit: "anak", icon: GraduationCap, color: "#C026D3" },
  { key: "anak_jalanan", label: "Anak Jalanan", unit: "jiwa", icon: Footprints, color: "#4338CA" },
  { key: "disabilitas", label: "Disabilitas", unit: "orang", icon: Accessibility, color: "#047857" },
  { key: "jumlah_kelurahan", label: "Kelurahan", unit: "kelurahan", icon: Users, color: "#0F172A" },
];

async function downloadFile(url, filename, toastId, loadingMsg, okMsg) {
  try {
    toast.loading(loadingMsg, { id: toastId });
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) throw new Error();
    const blob = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objUrl);
    toast.success(okMsg, { id: toastId });
  } catch {
    toast.error("Gagal mengunduh berkas", { id: toastId });
  }
}

export default function Rekap() {
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    api.get("/stats/overview").then((r) => setOverview(r.data)).catch(() => {});
  }, []);

  const dlPdf = () =>
    downloadFile(`${API}/report/dashboard`, "Ringkasan_Dashboard_Bappeda_Makassar.pdf",
      "rk-pdf", "Menyiapkan laporan PDF…", "Laporan PDF berhasil diunduh");
  const dlExcel = () =>
    downloadFile(`${API}/export/excel`, "Data_Sosial_Kota_Makassar.xlsx",
      "rk-xls", "Menyiapkan data Excel…", "Data Excel berhasil diunduh");

  const dlAll = async () => {
    await dlPdf();
    await dlExcel();
  };

  return (
    <div className="space-y-6" data-testid="rekap-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="inline-flex items-center gap-2 font-head text-3xl font-extrabold md:text-4xl">
            <ClipboardList className="h-8 w-8 text-primary" /> Rekap &amp; Laporan
          </p>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Rekapitulasi data sosial terbaru dan seluruh hasil analisa AI Kota Makassar — siap
            diunduh sekali klik untuk pimpinan.
          </p>
        </div>
        <button
          data-testid="rekap-download-all"
          onClick={dlAll}
          className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-bold text-primary-foreground transition-colors hover:bg-[hsl(0_72%_43%)] focus:outline-none"
        >
          <Download className="h-4 w-4" /> Unduh Rekap Lengkap (PDF + Excel)
        </button>
      </div>

      {/* KPI ringkas */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 xl:grid-cols-6" data-testid="rekap-kpi">
        {KPIS.map((k) => (
          <div key={k.key} className="rounded-lg border-2 border-border bg-card p-4">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-md" style={{ backgroundColor: `${k.color}1a`, color: k.color }}>
                <k.icon className="h-4 w-4" />
              </span>
              <span className="text-xs font-semibold text-muted-foreground">{k.label}</span>
            </div>
            <p className="mt-2 font-head text-2xl font-extrabold tabular-nums">
              {overview ? fmt(overview[k.key]) : "…"}
            </p>
            <p className="text-xs text-muted-foreground">{k.unit}</p>
          </div>
        ))}
      </div>

      {/* Tombol unduh individual */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border-2 border-border bg-card p-5">
        <span className="text-sm font-semibold text-muted-foreground">Unduh terpisah:</span>
        <button
          data-testid="rekap-pdf-btn"
          onClick={dlPdf}
          className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground transition-colors hover:bg-[hsl(222_47%_20%)] focus:outline-none"
        >
          <FileDown className="h-4 w-4" /> Laporan Dashboard (PDF)
        </button>
        <button
          data-testid="rekap-excel-btn"
          onClick={dlExcel}
          className="inline-flex items-center gap-2 rounded-full bg-[hsl(160_84%_27%)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[hsl(160_84%_22%)] focus:outline-none"
        >
          <FileSpreadsheet className="h-4 w-4" /> Data Mentah (Excel)
        </button>
      </div>

      {/* Seluruh riwayat analisa AI */}
      <AIHistory refreshKey={0} />
    </div>
  );
}
