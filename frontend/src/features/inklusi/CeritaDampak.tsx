import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Camera, CheckCircle2, ImagePlus, Loader2, MessageSquareQuote, Plus, ShieldCheck, Trash2, XCircle, Users, MapPin, CalendarCheck } from "lucide-react";
import api, { API, formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import * as DialogUI from "@/components/ui/dialog";

// Komponen shadcn ditulis dalam JSX (tanpa tipe) — di-cast agar lolos type-check TSX.
const { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } = DialogUI as any;
import { fmt } from "./theme";

export const fotoSrc = (url: string) => `${API.replace(/\/api$/, "")}${url}`;
const SENSITIVE = ["superadmin", "admin", "verifikator", "admin_bappeda"];
const area = "min-h-[110px] w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-[#117A69] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6FE3CF]";
const input = "h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm focus:border-[#117A69] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6FE3CF]";
const STATUS_CLS: Record<string, string> = {
  menunggu_review: "bg-amber-100 text-amber-900", dipublikasikan: "bg-emerald-100 text-emerald-900", ditolak: "bg-red-100 text-red-900",
};

/* ================================================================ PANEL DI DETAIL INQUIRY */
export function CeritaPanel({ inquiry }: { inquiry: any }) {
  const { user } = useAuth();
  const [c, setC] = useState<any>(null);
  const [f, setF] = useState<any>({ ringkasan_hasil: "", realisasi_penerima: "", testimoni: [] as any[], persetujuan: false });
  const [busy, setBusy] = useState(false);
  const [foto, setFoto] = useState<File | null>(null);
  const [ket, setKet] = useState("");
  const [note, setNote] = useState("");
  const iid = inquiry.id;
  const own = inquiry.user_email === user?.email;
  const canReview = SENSITIVE.includes(user?.role || "");
  const boleh = ["MONITORING", "COMPLETED"].includes(inquiry.status);

  const apply = (d: any) => {
    setC(d);
    if (d?.ada) setF({ ringkasan_hasil: d.ringkasan_hasil || "", realisasi_penerima: d.realisasi_penerima ?? "", testimoni: d.testimoni || [], persetujuan: !!d.persetujuan });
  };
  useEffect(() => {
    if (!boleh) return;
    api.get(`/inquiries/${iid}/cerita`).then((r) => apply(r.data)).catch(() => setC({ ada: false }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [iid, boleh]);
  if (!boleh) return null;
  if (!c) return <p className="text-sm text-slate-500" aria-live="polite">Memuat cerita dampak…</p>;

  const simpan = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      const r = await api.put(`/inquiries/${iid}/cerita`, { ...f, realisasi_penerima: Number(f.realisasi_penerima || 0), testimoni: f.testimoni.filter((t: any) => t.kutipan?.trim()) });
      apply(r.data); toast.success("Cerita dampak tersimpan dan dikirim untuk direview admin");
    } catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };
  const unggah = async () => {
    if (!foto) return; setBusy(true);
    try {
      const fd = new FormData(); fd.append("file", foto); fd.append("keterangan", ket);
      const r = await api.post(`/inquiries/${iid}/cerita/foto`, fd); apply(r.data); setFoto(null); setKet("");
      const el = document.getElementById("cerita-foto-input") as HTMLInputElement | null; if (el) el.value = "";
      toast.success("Foto diunggah (metadata lokasi dihapus otomatis)");
    } catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };
  const hapusFoto = async (fid: string) => {
    if (!window.confirm("Hapus foto ini?")) return;
    try { const r = await api.delete(`/inquiries/${iid}/cerita/foto/${fid}`); apply(r.data); toast.success("Foto dihapus"); }
    catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); }
  };
  const review = async (keputusan: string) => {
    setBusy(true);
    try { const r = await api.patch(`/inquiries/${iid}/cerita/review`, { keputusan, catatan: note }); apply(r.data); setNote(""); toast.success(keputusan === "publikasikan" ? "Cerita dipublikasikan ke galeri publik" : "Permintaan perbaikan dikirim ke NGO"); }
    catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };
  const setT = (i: number, k: string, v: string) => setF({ ...f, testimoni: f.testimoni.map((t: any, j: number) => (j === i ? { ...t, [k]: v } : t)) });

  return (
    <section className="space-y-4 rounded-xl border-2 border-[#6FE3CF] bg-white p-4" data-testid="cerita-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-head text-lg font-extrabold text-[#232F3E]"><Camera className="h-5 w-5 text-[#117A69]" /> Cerita Dampak Program</h2>
        {c.ada && <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${STATUS_CLS[c.status] || "bg-slate-100"}`} data-testid="cerita-status">{c.status_label}</span>}
      </div>
      <p className="text-xs text-slate-600">Ceritakan hasil program, lengkap dengan foto dan testimoni. Cerita tampil di <b>Galeri Program Selesai</b> (publik) setelah disetujui admin dan program berstatus Selesai.</p>
      {c.ada && c.status === "ditolak" && c.catatan_admin && (
        <p className="rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-900" data-testid="cerita-catatan-admin"><b>Catatan admin:</b> {c.catatan_admin}</p>
      )}

      {own ? (
        <form onSubmit={simpan} className="space-y-3" data-testid="cerita-form">
          <div>
            <label htmlFor="ringkasan_hasil" className="mb-1 block text-xs font-bold text-slate-700">Ringkasan hasil program *</label>
            <textarea id="ringkasan_hasil" required minLength={30} className={area} value={f.ringkasan_hasil} onChange={(e) => setF({ ...f, ringkasan_hasil: e.target.value })}
              placeholder="Contoh: Selama 6 bulan, 28 balita menerima PMT harian dan 11 di antaranya naik status gizi…" data-testid="cerita-ringkasan" />
          </div>
          <div className="max-w-xs">
            <label htmlFor="realisasi" className="mb-1 block text-xs font-bold text-slate-700">Realisasi penerima manfaat *</label>
            <input id="realisasi" type="number" min={0} required className={input} value={f.realisasi_penerima} onChange={(e) => setF({ ...f, realisasi_penerima: e.target.value })} data-testid="cerita-realisasi" />
            <p className="mt-0.5 text-[11px] text-slate-500">Rencana awal: {fmt(inquiry.jumlah_penerima)} orang</p>
          </div>
          <fieldset className="space-y-2">
            <legend className="text-xs font-bold text-slate-700">Testimoni (maks. 3)</legend>
            {f.testimoni.map((t: any, i: number) => (
              <div key={i} className="grid gap-2 rounded-lg bg-slate-50 p-2 md:grid-cols-[1fr_240px_auto]" data-testid={`cerita-testimoni-${i}`}>
                <textarea aria-label={`Kutipan testimoni ${i + 1}`} className={`${area} min-h-[60px]`} minLength={10} required value={t.kutipan} onChange={(e) => setT(i, "kutipan", e.target.value)} placeholder="Kutipan testimoni…" />
                <input aria-label={`Sumber testimoni ${i + 1}`} className={input} minLength={3} required value={t.sumber} onChange={(e) => setT(i, "sumber", e.target.value)} placeholder="Peran, mis. Ibu penerima, Kel. Buloa" />
                <button type="button" onClick={() => setF({ ...f, testimoni: f.testimoni.filter((_: any, j: number) => j !== i) })} aria-label="Hapus testimoni" className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-300 text-slate-600 hover:bg-red-50 hover:text-red-700"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
            {f.testimoni.length < 3 && (
              <button type="button" onClick={() => setF({ ...f, testimoni: [...f.testimoni, { kutipan: "", sumber: "" }] })} data-testid="cerita-add-testimoni"
                className="inline-flex items-center gap-1 rounded-md border border-dashed border-[#117A69] px-3 py-1.5 text-xs font-bold text-[#117A69] hover:bg-[#E6FAF6]"><Plus className="h-3.5 w-3.5" /> Tambah testimoni</button>
            )}
            <p className="text-[11px] text-slate-500">Gunakan peran/keterangan umum, bukan nama lengkap atau NIK penerima.</p>
          </fieldset>
          <label className="flex items-start gap-2 rounded-md bg-[#E6FAF6] p-3 text-xs text-[#0B4F45]">
            <input type="checkbox" className="mt-0.5" checked={f.persetujuan} onChange={(e) => setF({ ...f, persetujuan: e.target.checked })} data-testid="cerita-persetujuan" />
            <span><ShieldCheck className="mr-1 inline h-3.5 w-3.5" />Saya menyatakan foto & testimoni telah mendapat izin dari penerima manfaat (untuk anak: izin orang tua/wali), tidak memuat data pribadi (nama lengkap, NIK, alamat), dan boleh dipublikasikan di PETA INKLUSI.</span>
          </label>
          <button type="submit" disabled={busy || !f.persetujuan} data-testid="cerita-simpan"
            className="inline-flex items-center gap-2 rounded-md bg-[#117A69] px-5 py-2 text-sm font-bold text-white transition-colors hover:bg-[#0E6456] disabled:opacity-50">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} {c.ada ? "Simpan & kirim ulang untuk review" : "Simpan & kirim untuk review"}
          </button>
        </form>
      ) : c.ada ? (
        <div className="space-y-2 text-sm" data-testid="cerita-view">
          <p className="whitespace-pre-line">{c.ringkasan_hasil}</p>
          <p className="text-xs text-slate-600">Realisasi penerima: <b>{fmt(c.realisasi_penerima)}</b> (rencana {fmt(inquiry.jumlah_penerima)})</p>
          {(c.testimoni || []).map((t: any, i: number) => <blockquote key={i} className="border-l-4 border-[#6FE3CF] pl-3 italic text-slate-700">"{t.kutipan}" <span className="not-italic text-xs text-slate-500">— {t.sumber}</span></blockquote>)}
        </div>
      ) : <p className="text-sm text-slate-500" data-testid="cerita-kosong">NGO belum mengisi cerita dampak.</p>}

      {c.ada && (
        <div>
          <p className="mb-2 text-xs font-bold text-slate-700">Foto ({(c.foto || []).length}/5)</p>
          <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5" data-testid="cerita-foto-list">
            {(c.foto || []).map((p: any) => (
              <li key={p.id} className="group relative overflow-hidden rounded-lg ring-1 ring-slate-200">
                <img src={fotoSrc(p.url)} alt={p.keterangan || "Foto kegiatan program"} className="aspect-[4/3] w-full object-cover" loading="lazy" />
                {p.keterangan && <p className="truncate bg-white px-2 py-1 text-[11px] text-slate-600">{p.keterangan}</p>}
                {(own || canReview) && (
                  <button type="button" onClick={() => hapusFoto(p.id)} aria-label="Hapus foto" data-testid={`cerita-hapus-foto-${p.id}`}
                    className="absolute right-1 top-1 inline-flex h-7 w-7 items-center justify-center rounded-full bg-white/90 text-red-700 shadow hover:bg-white"><Trash2 className="h-3.5 w-3.5" /></button>
                )}
              </li>
            ))}
          </ul>
          {own && (c.foto || []).length < 5 && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <label htmlFor="cerita-foto-input" className="sr-only">Pilih foto</label>
              <input id="cerita-foto-input" type="file" accept=".jpg,.jpeg,.png,.webp" onChange={(e) => setFoto(e.target.files?.[0] || null)} data-testid="cerita-foto-input"
                className="text-sm file:mr-2 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-semibold hover:file:bg-slate-200" />
              <input aria-label="Keterangan foto" value={ket} onChange={(e) => setKet(e.target.value)} placeholder="Keterangan foto (opsional)" className="h-10 w-full min-w-0 rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-56" data-testid="cerita-foto-ket" />
              <button type="button" disabled={!foto || busy} onClick={unggah} data-testid="cerita-foto-upload"
                className="inline-flex h-9 items-center gap-1 rounded-md bg-[#232F3E] px-3 text-sm font-bold text-white hover:bg-[#1A2330] disabled:opacity-50"><ImagePlus className="h-4 w-4" /> Unggah</button>
              <p className="w-full text-[11px] text-slate-500">JPG/PNG/WEBP maks. 8 MB. Foto diperkecil otomatis dan metadata (termasuk lokasi GPS) dihapus.</p>
            </div>
          )}
        </div>
      )}

      {canReview && c.ada && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3" data-testid="cerita-review">
          <p className="text-xs font-bold text-slate-700">Review admin</p>
          <textarea aria-label="Catatan review" className={`${area} mt-1 min-h-[60px]`} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Catatan untuk NGO (wajib saat meminta perbaikan)" data-testid="cerita-review-note" />
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" disabled={busy} onClick={() => review("publikasikan")} data-testid="cerita-publikasikan" className="inline-flex items-center gap-1 rounded-md bg-[#117A69] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#0E6456] disabled:opacity-50"><CheckCircle2 className="h-3.5 w-3.5" /> Publikasikan</button>
            <button type="button" disabled={busy} onClick={() => review("tolak")} data-testid="cerita-tolak" className="inline-flex items-center gap-1 rounded-md bg-amber-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-800 disabled:opacity-50"><XCircle className="h-3.5 w-3.5" /> Minta perbaikan</button>
          </div>
          {inquiry.status !== "COMPLETED" && <p className="mt-1 text-[11px] text-slate-500">Catatan: cerita yang dipublikasikan baru tampil di galeri setelah status inquiry menjadi Selesai.</p>}
        </div>
      )}
    </section>
  );
}

/* ================================================================ DIALOG CERITA (GALERI PUBLIK) */
export function CeritaDialog({ program, open, onOpenChange }: { program: any; open: boolean; onOpenChange: (v: boolean) => void }) {
  const [idx, setIdx] = useState(0);
  const c = program?.cerita;
  useEffect(() => { setIdx(0); }, [program?.id]);
  if (!c) return null;
  const foto = c.foto || [];
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto" data-testid="cerita-dialog">
        <DialogHeader>
          <DialogTitle className="font-head text-xl font-extrabold text-[#232F3E]">{program.program}</DialogTitle>
          <DialogDescription className="flex flex-wrap items-center gap-3 text-xs">
            <span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{program.kelurahan ? `Kel. ${program.kelurahan}, ` : ""}Kec. {program.kecamatan}</span>
            <span className="inline-flex items-center gap-1"><Users className="h-3.5 w-3.5" />{fmt(c.realisasi_penerima)} penerima manfaat</span>
            <span className="inline-flex items-center gap-1"><CalendarCheck className="h-3.5 w-3.5" />{program.durasi_bulan} bulan</span>
            <span>NGO: {program.ngo}</span>
          </DialogDescription>
        </DialogHeader>
        {foto.length > 0 && (
          <div>
            <figure className="overflow-hidden rounded-xl bg-slate-100">
              <img src={fotoSrc(foto[idx].url)} alt={foto[idx].keterangan || `Foto kegiatan ${program.program}`} className="max-h-[380px] w-full object-cover" data-testid="cerita-dialog-foto" />
              {foto[idx].keterangan && <figcaption className="px-3 py-2 text-xs text-slate-600">{foto[idx].keterangan}</figcaption>}
            </figure>
            {foto.length > 1 && (
              <div className="mt-2 flex gap-2 overflow-x-auto" role="group" aria-label="Pilih foto">
                {foto.map((p: any, i: number) => (
                  <button key={p.id} type="button" onClick={() => setIdx(i)} aria-label={`Foto ${i + 1}`} aria-pressed={i === idx} data-testid={`cerita-thumb-${i}`}
                    className={`h-14 w-20 shrink-0 overflow-hidden rounded-md ring-2 transition-opacity ${i === idx ? "ring-[#117A69]" : "ring-transparent opacity-70 hover:opacity-100"}`}>
                    <img src={fotoSrc(p.url)} alt="" className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        <div>
          <h3 className="text-xs font-extrabold uppercase text-[#117A69]">Hasil program</h3>
          <p className="mt-1 whitespace-pre-line text-sm text-slate-800" data-testid="cerita-dialog-ringkasan">{c.ringkasan_hasil}</p>
        </div>
        {(c.testimoni || []).length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-extrabold uppercase text-[#117A69]">Testimoni</h3>
            {c.testimoni.map((t: any, i: number) => (
              <blockquote key={i} className="rounded-lg border-l-4 border-[#6FE3CF] bg-[#E6FAF6] p-3 text-sm text-[#0B4F45]" data-testid="cerita-dialog-testimoni">
                <MessageSquareQuote className="mb-1 h-4 w-4" aria-hidden="true" /> <span className="italic">"{t.kutipan}"</span>
                <footer className="mt-1 text-xs font-semibold not-italic">— {t.sumber}</footer>
              </blockquote>
            ))}
          </div>
        )}
        <p className="text-[11px] text-slate-500">Foto & testimoni dipublikasikan dengan persetujuan penerima manfaat dan telah direview admin Bappeda.</p>
      </DialogContent>
    </Dialog>
  );
}
