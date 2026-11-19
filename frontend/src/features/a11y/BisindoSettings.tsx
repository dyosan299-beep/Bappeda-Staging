import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Hand, Loader2, Save, Trash2 } from "lucide-react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { PageHeader } from "@/features/data/ui";
import { resetBisindoCache } from "./data";

/** Halaman Admin: atur video Juru Bahasa Isyarat (BISINDO) per halaman publik (fitur I). */
export default function BisindoSettings() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [form, setForm] = useState<Record<string, { url: string; judul: string }>>({});
  const [busy, setBusy] = useState("");
  const muat = () => api.get("/inklusi/a11y/bisindo").then((r) => {
    setRows(r.data.halaman);
    setForm(Object.fromEntries(r.data.halaman.map((h: any) => [h.id, { url: h.url || "", judul: h.judul || "" }])));
  }).catch(() => { setRows([]); toast.error("Gagal memuat pengaturan BISINDO"); });
  useEffect(() => { muat(); }, []);

  const simpan = async (id: string, hapus = false) => {
    setBusy(id);
    try {
      await api.put("/inklusi/a11y/bisindo", { halaman: id, url: hapus ? "" : form[id]?.url || "", judul: form[id]?.judul || "" });
      toast.success(hapus ? "Video BISINDO dihapus" : "Video BISINDO disimpan — langsung tampil di halaman publik");
      resetBisindoCache();
      await muat();
    } catch (e: any) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Gagal menyimpan");
    } finally { setBusy(""); }
  };

  return (
    <div data-testid="page-bisindo-settings">
      <PageHeader title="Aksesibilitas — Video Bahasa Isyarat (BISINDO)"
        subtitle="Video juru bahasa isyarat tampil sebagai jendela melayang di halaman publik untuk teman Tuli. Kosongkan untuk menyembunyikan." />
      <div className="mb-4 rounded-lg border border-sky-200 bg-sky-50 p-3 text-xs text-sky-900">
        Format yang didukung: tautan <b>YouTube</b> (watch / youtu.be / shorts), <b>Vimeo</b>, atau berkas <b>.mp4 / .webm</b> (https).
        Disarankan video berisi juru bahasa isyarat yang menerjemahkan isi halaman, dengan subtitle bahasa Indonesia.
      </div>
      {!rows ? <p className="text-sm text-slate-500">Memuat…</p> : (
        <div className="grid gap-4 lg:grid-cols-2">
          {rows.map((h) => (
            <section key={h.id} className="rounded-xl border border-slate-200 bg-white p-4" data-testid={`bisindo-row-${h.id}`}>
              <div className="flex items-center justify-between gap-2">
                <h2 className="flex items-center gap-2 font-head text-base font-bold text-slate-900"><Hand className="h-4 w-4 text-[#7C3AED]" /> {h.label}</h2>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${h.embed ? "bg-emerald-100 text-emerald-900" : "bg-slate-100 text-slate-600"}`} data-testid={`bisindo-status-${h.id}`}>
                  {h.embed ? "Tampil" : "Belum ada video"}</span>
              </div>
              <label className="mt-3 block text-[11px] font-semibold uppercase text-slate-600" htmlFor={`bu-${h.id}`}>Tautan video</label>
              <input id={`bu-${h.id}`} value={form[h.id]?.url || ""} placeholder="https://www.youtube.com/watch?v=…" data-testid={`bisindo-url-${h.id}`}
                onChange={(e) => setForm({ ...form, [h.id]: { ...form[h.id], url: e.target.value } })}
                className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm" />
              <label className="mt-2 block text-[11px] font-semibold uppercase text-slate-600" htmlFor={`bj-${h.id}`}>Judul (opsional)</label>
              <input id={`bj-${h.id}`} value={form[h.id]?.judul || ""} placeholder="mis. Penjelasan Dashboard dalam BISINDO" data-testid={`bisindo-judul-${h.id}`}
                onChange={(e) => setForm({ ...form, [h.id]: { ...form[h.id], judul: e.target.value } })}
                className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm" />
              {h.embed && (
                <div className="mt-3 aspect-video overflow-hidden rounded-md bg-black">
                  {h.jenis === "video"
                    ? <video src={h.embed} controls className="h-full w-full" title={`Pratinjau BISINDO ${h.label}`} />
                    : <iframe src={h.embed} title={`Pratinjau BISINDO ${h.label}`} className="h-full w-full" allow="encrypted-media; picture-in-picture; fullscreen" />}
                </div>
              )}
              <div className="mt-3 flex gap-2">
                <button type="button" disabled={busy === h.id || !(form[h.id]?.url || "").trim()} onClick={() => simpan(h.id)} data-testid={`bisindo-save-${h.id}`}
                  className="inline-flex h-9 items-center gap-2 rounded-md bg-slate-900 px-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50">
                  {busy === h.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Simpan
                </button>
                {h.embed && (
                  <button type="button" disabled={busy === h.id} onClick={() => simpan(h.id, true)} data-testid={`bisindo-delete-${h.id}`}
                    className="inline-flex h-9 items-center gap-2 rounded-md border border-rose-300 px-3 text-sm font-semibold text-rose-700 hover:bg-rose-50">
                    <Trash2 className="h-4 w-4" /> Hapus
                  </button>
                )}
              </div>
              {h.diubah_at && <p className="mt-2 text-[11px] text-slate-500">Diubah {new Date(h.diubah_at).toLocaleString("id-ID")} oleh {h.oleh}</p>}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
