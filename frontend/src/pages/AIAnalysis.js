import { useEffect, useRef, useState } from "react";
import { marked } from "marked";
import { toast } from "sonner";
import api, { API } from "@/lib/api";
import { Speak } from "@/components/Speak";
import AIHistory from "@/components/AIHistory";
import { Sparkles, Loader2, AlertTriangle, RotateCw, FileDown } from "lucide-react";

const CATS = [
  { key: "kemiskinan", label: "Kemiskinan" },
  { key: "stunting", label: "Stunting" },
  { key: "anak_jalanan", label: "Anak Jalanan / PMKS" },
  { key: "ats", label: "Anak Tidak Sekolah" },
  { key: "disabilitas", label: "Disabilitas" },
];

export default function AIAnalysis() {
  const [kategori, setKategori] = useState("kemiskinan");
  const [wilayah, setWilayah] = useState("");
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [raw, setRaw] = useState("");
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [historyKey, setHistoryKey] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    api.get("/regions").then((r) => setRegions(r.data)).catch(() => {});
  }, []);

  const analyze = async () => {
    setLoading(true);
    setRaw("");
    setError("");
    setElapsed(0);
    timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    try {
      const res = await fetch(`${API}/ai/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ kategori, wilayah: wilayah || null }),
      });
      if (!res.ok || !res.body) throw new Error("gagal");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let acc = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop();
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          const payload = JSON.parse(line.slice(5).trim());
          if (payload.delta) {
            acc += payload.delta;
            setRaw(acc);
          } else if (payload.error) {
            throw new Error(payload.error);
          }
        }
      }
      if (!acc) throw new Error("kosong");
      toast.success("Analisa selesai dibuat");
      setHistoryKey((k) => k + 1);
    } catch (e) {
      setError("Gagal membuat analisa. Silakan coba lagi.");
    } finally {
      clearInterval(timerRef.current);
      setLoading(false);
    }
  };

  const html = raw ? marked.parse(raw) : "";
  const plain = raw.replace(/[#*`|>-]/g, " ");

  const downloadPdf = async () => {
    try {
      toast.loading("Menyiapkan laporan PDF…", { id: "ai-pdf" });
      const res = await fetch(`${API}/report/ai`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ kategori, wilayah: wilayah || null, hasil: raw }),
      });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Laporan_Analisa_${kategori}_${wilayah || "Kota_Makassar"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Laporan PDF berhasil diunduh", { id: "ai-pdf" });
    } catch {
      toast.error("Gagal mengunduh laporan", { id: "ai-pdf" });
    }
  };

  return (
    <div className="space-y-6" data-testid="ai-page">
      <div>
        <p className="font-head text-3xl font-extrabold md:text-4xl">Analisa Program AI</p>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Rekomendasi program pemerintah Kota Makassar yang tepat sasaran, dihasilkan AI
          berdasarkan data matriks tiap kategori. Setiap hasil analisa tersimpan otomatis pada Riwayat.
        </p>
      </div>

      <div className="rounded-lg border-2 border-border bg-card p-4 sm:p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label className="mb-1.5 block text-sm font-semibold">Kategori Data</label>
            <select
              data-testid="ai-kategori"
              value={kategori}
              onChange={(e) => setKategori(e.target.value)}
              className="w-full rounded-md border-2 border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
            >
              {CATS.map((c) => (
                <option key={c.key} value={c.key}>{c.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold">Wilayah (opsional)</label>
            <select
              data-testid="ai-wilayah"
              value={wilayah}
              onChange={(e) => setWilayah(e.target.value)}
              className="w-full rounded-md border-2 border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
            >
              <option value="">Seluruh Kota Makassar</option>
              {regions.map((r) => (
                <option key={r.id} value={r.nama}>Kecamatan {r.nama}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              data-testid="ai-analyze-btn"
              onClick={analyze}
              disabled={loading}
              className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-6 py-2.5 font-semibold text-primary-foreground transition-colors hover:bg-[#0E6456] focus:outline-none disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Sparkles className="h-5 w-5" />}
              {loading ? "Menganalisa…" : "Analisa dengan AI"}
            </button>
          </div>
        </div>
      </div>

      {error && !loading && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border-2 border-destructive bg-destructive/5 p-5" data-testid="ai-error">
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            <span className="font-semibold">{error}</span>
          </div>
          <button
            data-testid="ai-retry-btn"
            onClick={analyze}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-[#0E6456] focus:outline-none"
          >
            <RotateCw className="h-4 w-4" /> Coba Lagi
          </button>
        </div>
      )}

      {(loading || html) && (
        <div className="rounded-lg border-2 border-accent bg-card p-4 sm:p-6 md:p-8" data-testid="ai-result">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {loading ? `AI sedang menyusun rekomendasi… ${elapsed}s` : "Rekomendasi AI"}
            </div>
            {!loading && html && (
              <div className="flex flex-wrap items-center gap-2">
                <button
                  data-testid="ai-pdf-btn"
                  onClick={downloadPdf}
                  className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground transition-colors hover:bg-[hsl(222_47%_20%)] focus:outline-none"
                >
                  <FileDown className="h-4 w-4" /> Unduh PDF
                </button>
                <Speak text={plain} label="Bacakan Hasil" testid="ai-speak" />
              </div>
            )}
          </div>
          {html ? (
            <div className="prose-gov max-w-none" dangerouslySetInnerHTML={{ __html: html }} />
          ) : (
            <p className="text-sm text-muted-foreground">Memulai analisa…</p>
          )}
        </div>
      )}

      <AIHistory refreshKey={historyKey} />
    </div>
  );
}
