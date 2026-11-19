import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";

/** Unduh berkas biner dari API (cookie auth) lalu simpan lewat tautan sementara. */
export async function downloadBlob(url: string, params: Record<string, any>, fallbackName: string) {
  try {
    const r = await api.get(url, { params, responseType: "blob" });
    const cd = String(r.headers?.["content-disposition"] || "");
    const m = cd.match(/filename="?([^";]+)"?/i);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(r.data);
    a.download = m ? m[1] : fallbackName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    return true;
  } catch (er: any) {
    let msg = "Gagal mengunduh berkas";
    try {
      const txt = await er.response?.data?.text?.();
      if (txt) msg = formatApiErrorDetail(JSON.parse(txt).detail) || msg;
    } catch { /* abaikan */ }
    toast.error(msg);
    return false;
  }
}

export const downloadLaporanKelurahan = (kecamatan: string, kelurahan: string) =>
  downloadBlob("/inklusi/laporan/kelurahan", { kecamatan, kelurahan }, `Laporan_Kel_${kelurahan}.pdf`);
