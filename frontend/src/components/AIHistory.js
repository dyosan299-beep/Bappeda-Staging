import { useCallback, useEffect, useState } from "react";
import { marked } from "marked";
import { toast } from "sonner";
import api, { API } from "@/lib/api";
import { Speak } from "@/components/Speak";
import { useAuth } from "@/context/AuthContext";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { History, Trash2, GitCompare, FileDown, Loader2, Clock } from "lucide-react";

const fmtDate = (iso) => {
  try {
    return new Date(iso).toLocaleString("id-ID", {
      day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso || "";
  }
};

export default function AIHistory({ refreshKey }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState(null); // full analysis object
  const [selected, setSelected] = useState([]); // ids for compare (max 2)
  const [compare, setCompare] = useState(null); // { a, b }
  const [busy, setBusy] = useState(false);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/ai/history");
      setItems(r.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory, refreshKey]);

  const openDetail = async (id) => {
    setBusy(true);
    try {
      const r = await api.get(`/ai/history/${id}`);
      setDetail(r.data);
    } catch {
      toast.error("Gagal memuat riwayat");
    } finally {
      setBusy(false);
    }
  };

  const toggleSelect = (id) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const doCompare = async () => {
    if (selected.length !== 2) return;
    setBusy(true);
    try {
      const [a, b] = await Promise.all(
        selected.map((id) => api.get(`/ai/history/${id}`).then((r) => r.data))
      );
      setCompare({ a, b });
    } catch {
      toast.error("Gagal memuat perbandingan");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("Hapus riwayat analisa ini?")) return;
    try {
      await api.delete(`/ai/history/${id}`);
      setSelected((prev) => prev.filter((x) => x !== id));
      setItems((prev) => prev.filter((x) => x.id !== id));
      toast.success("Riwayat dihapus");
    } catch {
      toast.error("Gagal menghapus (perlu login)");
    }
  };

  const downloadPdf = async (a) => {
    try {
      toast.loading("Menyiapkan laporan PDF…", { id: "hist-pdf" });
      const res = await fetch(`${API}/report/ai`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ kategori: a.kategori, wilayah: a.wilayah, hasil: a.hasil }),
      });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Laporan_Analisa_${a.kategori}_${(a.wilayah || "Kota_Makassar").replace(/\s+/g, "_")}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.success("Laporan PDF berhasil diunduh", { id: "hist-pdf" });
    } catch {
      toast.error("Gagal mengunduh laporan", { id: "hist-pdf" });
    }
  };

  return (
    <div className="rounded-lg border-2 border-border bg-card p-6" data-testid="ai-history">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="inline-flex items-center gap-2 font-head text-xl font-extrabold">
          <History className="h-5 w-5 text-primary" /> Riwayat Analisa AI
        </h2>
        <button
          data-testid="ai-compare-btn"
          onClick={doCompare}
          disabled={selected.length !== 2 || busy}
          className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground transition-colors hover:bg-[hsl(222_47%_20%)] focus:outline-none disabled:opacity-40"
        >
          <GitCompare className="h-4 w-4" /> Bandingkan ({selected.length}/2)
        </button>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Memuat riwayat…
        </div>
      ) : items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          Belum ada riwayat. Jalankan analisa AI, hasilnya otomatis tersimpan di sini.
        </p>
      ) : (
        <ul className="space-y-2" data-testid="ai-history-list">
          {items.map((it) => {
            const isSel = selected.includes(it.id);
            return (
              <li
                key={it.id}
                data-testid="ai-history-item"
                onClick={() => openDetail(it.id)}
                className={`flex cursor-pointer items-start gap-3 rounded-md border-2 p-3 transition-colors hover:border-primary ${
                  isSel ? "border-accent bg-accent/5" : "border-border"
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSel}
                  onChange={() => {}}
                  onClick={(e) => { e.stopPropagation(); toggleSelect(it.id); }}
                  aria-label="Pilih untuk dibandingkan"
                  className="mt-1 h-4 w-4 shrink-0 accent-[hsl(var(--primary))]"
                  data-testid="ai-history-checkbox"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-bold text-primary">
                      {it.kategori_label}
                    </span>
                    <span className="text-sm font-semibold">{it.wilayah}</span>
                    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" /> {fmtDate(it.created_at)}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{it.ringkasan}…</p>
                </div>
                {user && (
                  <button
                    onClick={(e) => remove(it.id, e)}
                    aria-label="Hapus riwayat"
                    data-testid="ai-history-delete"
                    className="shrink-0 rounded-md p-2 text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary focus:outline-none"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {/* Detail dialog */}
      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-bold text-primary">
                {detail?.kategori_label}
              </span>
              {detail?.wilayah}
              <span className="text-xs font-normal text-muted-foreground">
                · {fmtDate(detail?.created_at)}
              </span>
            </DialogTitle>
          </DialogHeader>
          {detail && (
            <>
              <div className="mb-3 flex items-center gap-2">
                <button
                  onClick={() => downloadPdf(detail)}
                  className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground hover:bg-[hsl(222_47%_20%)] focus:outline-none"
                >
                  <FileDown className="h-4 w-4" /> Unduh PDF
                </button>
                <Speak text={(detail.hasil || "").replace(/[#*`|>-]/g, " ")} label="Bacakan" testid="hist-speak" />
              </div>
              <div
                className="prose-gov max-w-none"
                dangerouslySetInnerHTML={{ __html: marked.parse(detail.hasil || "") }}
              />
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Compare dialog */}
      <Dialog open={!!compare} onOpenChange={(o) => !o && setCompare(null)}>
        <DialogContent className="max-h-[85vh] max-w-6xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="inline-flex items-center gap-2">
              <GitCompare className="h-5 w-5 text-primary" /> Perbandingan Analisa
            </DialogTitle>
          </DialogHeader>
          {compare && (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {[compare.a, compare.b].map((a, i) => (
                <div key={i} className="rounded-lg border-2 border-border p-4">
                  <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-border pb-2">
                    <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-bold text-primary">
                      {a.kategori_label}
                    </span>
                    <span className="text-sm font-semibold">{a.wilayah}</span>
                    <span className="text-xs text-muted-foreground">{fmtDate(a.created_at)}</span>
                  </div>
                  <div
                    className="prose-gov max-w-none text-sm"
                    dangerouslySetInnerHTML={{ __html: marked.parse(a.hasil || "") }}
                  />
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
