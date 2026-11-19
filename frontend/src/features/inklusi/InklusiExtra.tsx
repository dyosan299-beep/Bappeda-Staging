import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  FileDown, Loader2, Upload, FileSpreadsheet, CheckCircle2, AlertTriangle, RotateCcw, Mail, Send,
  RefreshCw, MapPin, Users, CalendarCheck, Award, X,
} from "lucide-react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { KATEGORI_META, fmt } from "./theme";
import { downloadBlob, downloadLaporanKelurahan } from "./download";
import { CeritaDialog, fotoSrc } from "./CeritaDampak";

const sel = "h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm focus:border-[#117A69] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6FE3CF]";
const th = "p-2 text-left text-[11px] font-bold uppercase text-slate-600";
export const SENSITIVE = ["superadmin", "admin", "verifikator", "admin_bappeda"];
export const WRITERS = ["superadmin", "admin", "verifikator", "admin_bappeda", "petugas", "operator", "admin_opd",
  "operator_kecamatan", "operator_kelurahan"];

/* ================================================================ LAPORAN WILAYAH (PDF) */
export function LaporanWilayah() {
  const [wil, setWil] = useState<any[]>([]);
  const [kec, setKec] = useState("");
  const [kel, setKel] = useState("");
  const [busy, setBusy] = useState("");
  useEffect(() => { api.get("/public/wilayah").then((r) => setWil(r.data.kecamatan || [])).catch(() => setWil([])); }, []);
  const kelList: string[] = useMemo(() => wil.find((k) => k.nama === kec)?.kelurahan || [], [wil, kec]);
  const unduh = async (kc: string, kl: string) => {
    setBusy(kl);
    const ok = await downloadLaporanKelurahan(kc, kl);
    if (ok) toast.success(`Laporan Kel. ${kl} berhasil diunduh`);
    setBusy("");
  };
  return (
    <div className="space-y-5" data-testid="laporan-wilayah">
      <div>
        <p className="font-head text-2xl font-extrabold text-[#232F3E]">Laporan Wilayah (PDF)</p>
        <p className="text-sm text-slate-600">Ringkasan satu halaman per kelurahan berisi 4 kategori (Disabilitas, Stunting, ATS, Kemiskinan),
          program NGO, dan usulan Musrenbang terkait — siap dibawa ke rapat Musrenbang. Hanya memuat data agregat.</p>
      </div>
      <section className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
        <div>
          <label htmlFor="lap-kec" className="mb-1 block text-xs font-bold text-slate-700">Kecamatan</label>
          <select id="lap-kec" className={sel} value={kec} onChange={(e) => { setKec(e.target.value); setKel(""); }} data-testid="laporan-kecamatan">
            <option value="">Pilih kecamatan…</option>
            {wil.map((k) => <option key={k.nama} value={k.nama}>{k.nama}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="lap-kel" className="mb-1 block text-xs font-bold text-slate-700">Kelurahan</label>
          <select id="lap-kel" className={sel} value={kel} disabled={!kec} onChange={(e) => setKel(e.target.value)} data-testid="laporan-kelurahan">
            <option value="">{kec ? "Pilih kelurahan…" : "Pilih kecamatan dulu"}</option>
            {kelList.map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
        </div>
        <button type="button" disabled={!kel || !!busy} onClick={() => unduh(kec, kel)} data-testid="laporan-unduh-btn"
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-[#117A69] px-5 text-sm font-bold text-white transition-colors hover:bg-[#0E6456] focus-visible:ring-2 focus-visible:ring-[#6FE3CF] disabled:opacity-50">
          {busy && busy === kel ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />} Unduh PDF
        </button>
      </section>
      {kec && (
        <section className="rounded-xl border border-slate-200 bg-white p-4" data-testid="laporan-daftar-kelurahan">
          <h2 className="mb-3 text-sm font-extrabold uppercase text-[#232F3E]">Semua kelurahan di Kec. {kec} ({kelList.length})</h2>
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {kelList.map((k) => (
              <li key={k}>
                <button type="button" onClick={() => unduh(kec, k)} disabled={!!busy} data-testid={`laporan-quick-${k}`}
                  className="flex w-full items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 text-left text-sm transition-colors hover:border-[#117A69] hover:bg-[#E6FAF6] disabled:opacity-60">
                  <span className="flex items-center gap-1.5 font-semibold text-slate-800"><MapPin className="h-3.5 w-3.5 text-[#117A69]" /> {k}</span>
                  {busy === k ? <Loader2 className="h-4 w-4 animate-spin text-[#117A69]" /> : <FileDown className="h-4 w-4 text-[#117A69]" />}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="text-xs text-slate-500">Tip: laporan juga dapat diunduh langsung dari Peta Sosial / Peta Kemiskinan dengan memilih kelurahan pada peta.</p>
    </div>
  );
}

/* ================================================================ DIALOG IMPOR (dipakai tombol "Input Data") */
export function ImportDialog({ judul, keterangan, onClose, children, testid }: {
  judul: string; keterangan?: React.ReactNode; onClose: () => void; children: React.ReactNode; testid: string;
}) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", esc);
    const lama = document.body.style.overflow; document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", esc); document.body.style.overflow = lama; };
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-[950] flex items-start justify-center overflow-y-auto bg-black/50 p-3"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="my-6 w-full max-w-4xl rounded-lg bg-white shadow-2xl" role="dialog" aria-modal="true" aria-label={judul} data-testid={testid}>
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div>
            <h2 className="font-head text-base font-bold text-slate-900">{judul}</h2>
            {keterangan && <p className="text-[11px] text-slate-500">{keterangan}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="Tutup" data-testid={`${testid}-close`}
            className="rounded-md p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800"><X className="h-5 w-5" /></button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

/* ================================================================ IMPOR ATS KELURAHAN */
export function AtsImportPanel({ onImported }: { onImported: () => void }) {
  const { user } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [prev, setPrev] = useState<any>(null);
  const [mode, setMode] = useState("ganti_tahun");
  const [busy, setBusy] = useState(false);
  const [batches, setBatches] = useState<any[]>([]);
  const canWrite = WRITERS.includes(user?.role || "");
  const canRollback = SENSITIVE.includes(user?.role || "");
  const loadBatches = () => api.get("/inklusi/ats/batches").then((r) => setBatches(r.data.items || [])).catch(() => setBatches([]));
  useEffect(() => { loadBatches(); }, []);

  const preview = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const r = await api.post("/inklusi/ats/preview", fd);
      setPrev(r.data);
    } catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };
  const commit = async () => {
    setBusy(true);
    try {
      const r = await api.post("/inklusi/ats/commit", { preview_id: prev.preview_id, mode });
      toast.success(`${fmt(r.data.diimpor)} baris data ATS kelurahan berhasil diimpor`);
      setPrev(null); setFile(null); loadBatches(); onImported();
    } catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };
  const rollback = async (b: any) => {
    if (!window.confirm(`Batalkan impor "${b.nama_berkas}"? Seluruh ${b.jumlah_baris} baris dari batch ini akan dihapus.`)) return;
    try {
      const r = await api.delete(`/inklusi/ats/batches/${b.id}`);
      toast.success(`Impor dibatalkan (${fmt(r.data.dihapus)} baris dihapus)`);
      loadBatches(); onImported();
    } catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); }
  };

  if (!canWrite) return null;
  const s = prev?.ringkasan;
  return (
    <section className="space-y-4" data-testid="ats-import-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="text-sm text-slate-600">1) Unduh template  2) Isi jumlah anak per kelurahan  3) Unggah & periksa pratinjau  4) Simpan.</p>
        <button type="button" data-testid="ats-template-btn"
          onClick={() => downloadBlob("/inklusi/ats/template", {}, "template_ats_kelurahan.xlsx")}
          className="inline-flex items-center gap-2 rounded-md border border-[#B7791F] bg-[#FEF6E4] px-4 py-2 text-sm font-bold text-[#8A5A00] transition-colors hover:bg-[#FCE3AE] focus-visible:ring-2 focus-visible:ring-[#F4B63A]">
          <FileSpreadsheet className="h-4 w-4" /> Unduh Template Excel
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="ats-file" className="sr-only">Berkas data ATS</label>
        <input id="ats-file" type="file" accept=".xlsx,.xls,.csv" data-testid="ats-file-input"
          onChange={(e) => { setFile(e.target.files?.[0] || null); setPrev(null); }}
          className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-semibold hover:file:bg-slate-200" />
        <button type="button" disabled={!file || busy} onClick={preview} data-testid="ats-preview-btn"
          className="inline-flex items-center gap-2 rounded-md bg-[#232F3E] px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-[#1A2330] disabled:opacity-50">
          {busy && !prev ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />} Unggah & Pratinjau
        </button>
      </div>

      {prev && (
        <div className="space-y-3 rounded-lg bg-slate-50 p-3" data-testid="ats-preview-result">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            {[["Baris dibaca", s.baris_dibaca], ["Valid", s.valid], ["Error", s.error], ["Kelurahan", s.kelurahan], ["Total anak", s.total_anak]].map(([l, v]: any) => (
              <div key={l} className="rounded-md bg-white p-2 ring-1 ring-slate-200"><p className="text-[10px] font-bold uppercase text-slate-500">{l}</p>
                <p className={`font-head text-xl font-extrabold ${l === "Error" && v ? "text-[#B42318]" : "text-slate-900"}`} data-testid={`ats-preview-${l.replace(/\s/g, "-").toLowerCase()}`}>{fmt(v)}</p></div>
            ))}
          </div>
          <p className="text-xs text-slate-600">Tahun di berkas: <b>{(s.tahun || []).join(", ") || "-"}</b> · Baris kosong dilewati: {fmt(s.dilewati_kosong)}
            {prev.data_tahun_sama_saat_ini > 0 && <> · <span className="font-semibold text-amber-800">Sudah ada {fmt(prev.data_tahun_sama_saat_ini)} baris untuk tahun yang sama</span></>}</p>
          {prev.errors?.length > 0 && (
            <div className="max-h-40 overflow-y-auto rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-900" data-testid="ats-preview-errors">
              <p className="mb-1 flex items-center gap-1 font-bold"><AlertTriangle className="h-3.5 w-3.5" /> Baris bermasalah (tidak akan diimpor)</p>
              <ul className="space-y-0.5">{prev.errors.map((e: any, i: number) => <li key={i}>Baris {e.baris}: {e.pesan}</li>)}</ul>
            </div>
          )}
          {prev.per_kelurahan?.length > 0 && (
            <div className="overflow-x-auto rounded-md bg-white ring-1 ring-slate-200">
              <table className="w-full text-xs"><thead className="bg-slate-50"><tr><th className={th}>Wilayah (20 teratas)</th><th className={`${th} text-right`}>Jumlah anak</th></tr></thead>
                <tbody>{prev.per_kelurahan.map((r: any) => <tr key={r.wilayah} className="border-t"><td className="p-2">{r.wilayah}</td><td className="p-2 text-right font-bold">{fmt(r.jumlah)}</td></tr>)}</tbody></table>
            </div>
          )}
          <fieldset className="flex flex-wrap gap-4 text-sm">
            <legend className="sr-only">Mode impor</legend>
            <label className="flex items-center gap-2"><input type="radio" name="mode" checked={mode === "ganti_tahun"} onChange={() => setMode("ganti_tahun")} data-testid="ats-mode-ganti" /> Ganti data tahun yang sama</label>
            <label className="flex items-center gap-2"><input type="radio" name="mode" checked={mode === "tambah"} onChange={() => setMode("tambah")} data-testid="ats-mode-tambah" /> Tambahkan ke data yang ada</label>
          </fieldset>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={busy || !s.valid} onClick={commit} data-testid="ats-commit-btn"
              className="inline-flex items-center gap-2 rounded-md bg-[#117A69] px-5 py-2 text-sm font-bold text-white transition-colors hover:bg-[#0E6456] disabled:opacity-50">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Simpan {fmt(s.valid)} baris valid
            </button>
            <button type="button" onClick={() => setPrev(null)} className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold hover:bg-white" data-testid="ats-cancel-btn">Batal</button>
          </div>
        </div>
      )}

      <div>
        <h3 className="mb-2 text-xs font-extrabold uppercase text-slate-600">Riwayat impor ATS kelurahan</h3>
        {batches.length ? (
          <div className="overflow-x-auto rounded-md ring-1 ring-slate-200">
            <table className="w-full text-xs" data-testid="ats-batches-table"><thead className="bg-slate-50"><tr>{["Waktu", "Berkas", "Baris", "Tahun", "Mode", "Oleh", "Status", ""].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
              <tbody>{batches.map((b) => (
                <tr key={b.id} className="border-t" data-testid="ats-batch-row">
                  <td className="p-2 whitespace-nowrap">{new Date(b.diimpor_at || b.created_at).toLocaleString("id-ID")}</td><td className="p-2">{b.nama_berkas}</td>
                  <td className="p-2">{fmt(b.jumlah_baris)}</td><td className="p-2">{(b.ringkasan?.tahun || []).join(", ")}</td>
                  <td className="p-2">{b.mode === "tambah" ? "Tambah" : "Ganti tahun"}</td><td className="p-2">{b.oleh}</td>
                  <td className="p-2"><span className={`rounded-full px-2 py-0.5 font-bold ${b.status === "diimpor" ? "bg-emerald-100 text-emerald-900" : "bg-slate-200 text-slate-700"}`}>{b.status === "diimpor" ? "Aktif" : "Dibatalkan"}</span></td>
                  <td className="p-2 text-right">{canRollback && b.status === "diimpor" && (
                    <button type="button" onClick={() => rollback(b)} data-testid={`ats-rollback-${b.id}`} className="inline-flex items-center gap-1 rounded border border-red-300 px-2 py-1 font-semibold text-red-800 hover:bg-red-50">
                      <RotateCcw className="h-3 w-3" /> Batalkan</button>)}</td>
                </tr>))}</tbody></table>
          </div>
        ) : <p className="text-sm text-slate-500">Belum ada impor.</p>}
      </div>
    </section>
  );
}

/* ================================================================ IMPOR PDF BALITA STUNTING */
export function StuntingImportPanel({ onImported, fokusRiwayat = false }: { onImported: () => void; fokusRiwayat?: boolean }) {
  const { user } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [prev, setPrev] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [batches, setBatches] = useState<any[]>([]);
  const riwayatRef = React.useRef<HTMLDivElement>(null);
  const allowed = SENSITIVE.includes(user?.role || "");
  const loadBatches = () => api.get("/inklusi/stunting/import/batches").then((r) => setBatches(r.data.items || [])).catch(() => setBatches([]));
  useEffect(() => { if (allowed) loadBatches(); }, [allowed]);
  useEffect(() => { if (fokusRiwayat) setTimeout(() => riwayatRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 150); }, [fokusRiwayat]);

  const preview = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const r = await api.post("/inklusi/stunting/import/preview", fd, { timeout: 180000 });
      setPrev(r.data);
    } catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail) || "Gagal membaca PDF"); } finally { setBusy(false); }
  };
  const commit = async () => {
    if (prev.data_saat_ini > 0 && !window.confirm(`Data lama (${fmt(prev.data_saat_ini)} balita) akan DIGANTI dengan ${fmt(prev.ringkasan.valid)} balita dari berkas ini. Lanjutkan?`)) return;
    setBusy(true);
    try {
      const r = await api.post("/inklusi/stunting/import/commit", { preview_id: prev.preview_id }, { timeout: 180000 });
      toast.success(`${fmt(r.data.diimpor)} data balita stunting berhasil diimpor`);
      setPrev(null); setFile(null); loadBatches(); onImported();
    } catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };

  if (!allowed) return null;
  const s = prev?.ringkasan;
  return (
    <section className="space-y-4" data-testid="stunting-import-panel">
      <p className="text-sm text-slate-600">Unggah berkas PDF (mis. "DATA STUNTING KEC MAKASSAR DAN TALLO.pdf") → periksa pratinjau → simpan. Data baru <b>menggantikan</b> seluruh data balita sebelumnya; baris ganda otomatis dibuang.</p>
      <>
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="stunting-file" className="sr-only">Berkas PDF stunting</label>
          <input id="stunting-file" type="file" accept=".pdf,application/pdf" data-testid="stunting-file-input"
            onChange={(e) => { setFile(e.target.files?.[0] || null); setPrev(null); }}
            className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-semibold hover:file:bg-slate-200" />
          <button type="button" disabled={!file || busy} onClick={preview} data-testid="stunting-preview-btn"
            className="inline-flex items-center gap-2 rounded-md bg-[#232F3E] px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-[#1A2330] disabled:opacity-50">
            {busy && !prev ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />} {busy && !prev ? "Membaca PDF…" : "Unggah & Pratinjau"}
          </button>
        </div>

        {prev && (
          <div className="space-y-3 rounded-lg bg-slate-50 p-3" data-testid="stunting-preview-result">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
              {[["Baris dibaca", s.baris_dibaca], ["Duplikat dibuang", s.duplikat || 0], ["Balita unik", s.valid], ["Kelurahan", s.kelurahan], ["Kelurahan tak cocok", s.kelurahan_tidak_cocok], ["Data saat ini", prev.data_saat_ini]].map(([l, v]: any) => (
                <div key={l} className="rounded-md bg-white p-2 ring-1 ring-slate-200"><p className="text-[10px] font-bold uppercase text-slate-500">{l}</p>
                  <p className={`font-head text-xl font-extrabold ${l === "Kelurahan tak cocok" && v ? "text-[#B42318]" : "text-slate-900"}`} data-testid={`stunting-preview-${l.replace(/\s/g, "-").toLowerCase()}`}>{fmt(v)}</p></div>
              ))}
            </div>
            <p className="text-xs text-slate-600">Per kecamatan: {(prev.per_kecamatan || []).map((x: any) => `${x.kategori} ${fmt(x.jumlah)}`).join(" · ")} — Status TB/U: {(prev.status_tbu || []).map((x: any) => `${x.kategori} ${fmt(x.jumlah)}`).join(" · ")}</p>
            {prev.duplikat?.length > 0 && (
              <div className="max-h-40 overflow-y-auto rounded-md border border-sky-200 bg-sky-50 p-2 text-xs text-sky-950" data-testid="stunting-preview-duplicates">
                <p className="mb-1 flex items-center gap-1 font-bold"><AlertTriangle className="h-3.5 w-3.5" /> Baris ganda (nama anak + nama orang tua sama) — hanya satu yang disimpan (data paling lengkap)</p>
                <ul className="space-y-0.5">{prev.duplikat.map((e: any, i: number) => <li key={i} data-testid="stunting-duplicate-item">{e.nama} · {e.kelurahan}: disimpan No. {e.no_dipakai}, dibuang No. {e.no_dibuang} — {e.keterangan}</li>)}</ul>
              </div>
            )}
            {prev.daftar_tidak_cocok?.length > 0 && (
              <div className="max-h-32 overflow-y-auto rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900" data-testid="stunting-preview-unmatched">
                <p className="mb-1 flex items-center gap-1 font-bold"><AlertTriangle className="h-3.5 w-3.5" /> Nama kelurahan tidak cocok master (tetap diimpor, tidak tampil di peta kelurahan)</p>
                <ul>{prev.daftar_tidak_cocok.map((e: any) => <li key={e.kelurahan}>{e.kelurahan}: {fmt(e.jumlah)} baris</li>)}</ul>
              </div>
            )}
            <div className="overflow-x-auto rounded-md bg-white ring-1 ring-slate-200">
              <table className="w-full text-xs"><thead className="bg-slate-50"><tr>{["Nama (disamarkan)", "JK", "Umur", "Puskesmas", "Kelurahan", "Kecamatan", "TB/U"].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
                <tbody>{prev.contoh.map((r: any, i: number) => <tr key={i} className="border-t"><td className="p-2">{r.nama}</td><td className="p-2">{r.jk}</td><td className="p-2">{r.kelompok_umur}</td><td className="p-2">{r.puskesmas}</td><td className="p-2">{r.kelurahan}</td><td className="p-2">{r.kecamatan}</td><td className="p-2">{r.status_tbu}</td></tr>)}</tbody></table>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" disabled={busy || !s.valid} onClick={commit} data-testid="stunting-commit-btn"
                className="inline-flex items-center gap-2 rounded-md bg-[#117A69] px-5 py-2 text-sm font-bold text-white transition-colors hover:bg-[#0E6456] disabled:opacity-50">
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Simpan {fmt(s.valid)} balita unik
              </button>
              <button type="button" onClick={() => setPrev(null)} className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold hover:bg-white" data-testid="stunting-cancel-btn">Batal</button>
            </div>
          </div>
        )}

        <div ref={riwayatRef} data-testid="stunting-riwayat">
          <h3 className="mb-2 text-xs font-extrabold uppercase text-slate-600">Riwayat impor PDF stunting</h3>
          {batches.length ? (
            <div className="overflow-x-auto rounded-md ring-1 ring-slate-200">
              <table className="w-full text-xs" data-testid="stunting-batches-table"><thead className="bg-slate-50"><tr>{["Waktu", "Berkas", "Balita", "Oleh", "Status"].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
                <tbody>{batches.map((b) => (
                  <tr key={b.id} className="border-t" data-testid="stunting-batch-row">
                    <td className="p-2 whitespace-nowrap">{new Date(b.diimpor_at || b.created_at).toLocaleString("id-ID")}</td><td className="p-2">{b.nama_berkas}</td>
                    <td className="p-2">{fmt(b.jumlah_baris)}</td><td className="p-2">{b.oleh}</td>
                    <td className="p-2"><span className={`rounded-full px-2 py-0.5 font-bold ${b.status === "diimpor" ? "bg-emerald-100 text-emerald-900" : "bg-slate-200 text-slate-700"}`}>{b.status === "diimpor" ? "Aktif" : "Diganti"}</span></td>
                  </tr>))}</tbody></table>
            </div>
          ) : <p className="text-sm text-slate-500">Belum ada impor melalui website.</p>}
        </div>
      </>
    </section>
  );
}

/* ================================================================ NOTIFIKASI EMAIL (OUTBOX) */
const EMAIL_STATUS: Record<string, [string, string]> = {
  terkirim: ["Terkirim", "bg-emerald-100 text-emerald-900"],
  belum_terkirim: ["Belum terkirim", "bg-amber-100 text-amber-900"],
  gagal: ["Gagal", "bg-red-100 text-red-900"],
  antri: ["Antri", "bg-slate-100 text-slate-800"],
};

export function EmailOutbox() {
  const [d, setD] = useState<any>(null);
  const [f, setF] = useState({ status: "", page: 1 });
  const [busy, setBusy] = useState(false);
  const [to, setTo] = useState("");
  const [open, setOpen] = useState<string>("");
  const load = () => {
    const p: any = { page: f.page }; if (f.status) p.status = f.status;
    api.get("/inklusi/email-outbox", { params: p }).then((r) => setD(r.data)).catch(() => setD(false));
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [f]);
  if (d === false) return <p className="text-red-700">Gagal memuat notifikasi email (khusus Admin/Super Admin).</p>;
  if (!d) return <p className="text-slate-500" aria-live="polite">Memuat…</p>;
  const retry = async () => {
    setBusy(true);
    try { const r = await api.post("/inklusi/email-outbox/kirim-ulang"); toast.success(`${r.data.terkirim} email terkirim, ${r.data.gagal} gagal`); load(); }
    catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };
  const tes = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      const r = await api.post("/inklusi/email-outbox/tes", { to });
      if (r.data.status === "terkirim") toast.success("Email tes terkirim"); else toast.warning(`Email tes: ${EMAIL_STATUS[r.data.status]?.[0] || r.data.status}. ${r.data.error || ""}`);
      load();
    } catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };
  const smtp = d.smtp;
  return (
    <div className="space-y-5" data-testid="email-outbox">
      <div><p className="font-head text-2xl font-extrabold text-[#232F3E]">Notifikasi Email NGO</p>
        <p className="text-sm text-slate-600">Email otomatis dikirim ke NGO setiap kali status inquiry berubah, lengkap dengan catatan admin.</p></div>
      <section className={`rounded-xl border-2 p-4 ${smtp.configured ? "border-[#117A69] bg-[#E6FAF6]" : "border-[#F4B63A] bg-[#FEF6E4]"}`} data-testid="smtp-status">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="flex items-center gap-2 font-head text-base font-extrabold text-[#232F3E]"><Mail className="h-5 w-5" />
              {smtp.configured ? "SMTP aktif" : "SMTP belum dikonfigurasi"}</p>
            {smtp.configured ? <p className="text-sm text-slate-700">{smtp.host}:{smtp.port} ({smtp.security}) · pengirim: {smtp.from}</p>
              : <p className="mt-1 max-w-3xl text-sm text-[#8A5A00]">Email tetap dicatat dengan status <b>Belum terkirim</b>. Isi <code className="rounded bg-white px-1">SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM</code> pada berkas <code className="rounded bg-white px-1">backend/.env</code> lalu restart backend — email tertunda akan dikirim otomatis.</p>}
          </div>
          <button type="button" onClick={retry} disabled={busy || !smtp.configured} data-testid="email-retry-btn"
            className="inline-flex items-center gap-2 rounded-md bg-[#117A69] px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-[#0E6456] disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} /> Kirim ulang tertunda & gagal</button>
        </div>
        <form onSubmit={tes} className="mt-3 flex flex-wrap items-center gap-2">
          <label htmlFor="tes-email" className="text-xs font-bold text-slate-700">Kirim email tes ke</label>
          <input id="tes-email" type="email" required value={to} onChange={(e) => setTo(e.target.value)} placeholder="nama@domain.go.id" data-testid="email-test-input"
            className="h-10 w-full sm:h-9 sm:w-64 rounded-md border border-slate-300 bg-white px-2 text-sm" />
          <button type="submit" disabled={busy} data-testid="email-test-btn" className="inline-flex h-9 items-center gap-1 rounded-md border border-[#232F3E] bg-white px-3 text-sm font-bold text-[#232F3E] hover:bg-slate-50 disabled:opacity-50"><Send className="h-3.5 w-3.5" /> Kirim tes</button>
        </form>
      </section>
      <div className="grid gap-3 sm:grid-cols-4">
        {Object.entries(EMAIL_STATUS).map(([k, [l]]) => (
          <button key={k} type="button" onClick={() => setF({ status: f.status === k ? "" : k, page: 1 })} data-testid={`email-count-${k}`}
            className={`rounded-xl bg-white p-3 text-left ring-1 transition-colors ${f.status === k ? "ring-2 ring-[#117A69]" : "ring-slate-200 hover:ring-slate-300"}`}>
            <p className="text-[11px] font-bold uppercase text-slate-600">{l}</p><p className="font-head text-2xl font-extrabold">{fmt(d.ringkasan?.[k] || 0)}</p></button>
        ))}
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="w-full min-w-[760px] text-sm"><thead className="bg-slate-50"><tr>{["Waktu", "Penerima", "Subjek", "Jenis", "Status", "Percobaan", ""].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
          <tbody>
            {d.items.map((m: any) => (
              <React.Fragment key={m.id}>
                <tr className="border-t align-top" data-testid="email-row">
                  <td className="p-2 whitespace-nowrap text-xs">{new Date(m.created_at).toLocaleString("id-ID")}</td>
                  <td className="p-2 text-xs">{(m.to || []).join(", ")}</td><td className="p-2">{m.subject}</td><td className="p-2 text-xs">{m.jenis}</td>
                  <td className="p-2"><span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${EMAIL_STATUS[m.status]?.[1] || "bg-slate-100"}`}>{EMAIL_STATUS[m.status]?.[0] || m.status}</span>
                    {m.error && m.status !== "terkirim" && <p className="mt-0.5 max-w-[220px] text-[11px] text-slate-500">{m.error}</p>}</td>
                  <td className="p-2 text-xs">{m.attempts}</td>
                  <td className="p-2 text-right"><button type="button" onClick={() => setOpen(open === m.id ? "" : m.id)} className="text-xs font-bold text-[#117A69] underline" data-testid="email-toggle-body">{open === m.id ? "Tutup" : "Isi email"}</button></td>
                </tr>
                {open === m.id && <tr className="bg-slate-50"><td colSpan={7} className="p-3"><pre className="whitespace-pre-wrap font-sans text-xs text-slate-700" data-testid="email-body">{m.body_text}</pre></td></tr>}
              </React.Fragment>
            ))}
            {!d.items.length && <tr><td colSpan={7} className="p-6 text-center text-slate-500">Belum ada email. Email dibuat otomatis saat admin mengubah status inquiry.</td></tr>}
          </tbody></table>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2 text-sm">
        <button type="button" disabled={f.page <= 1} onClick={() => setF({ ...f, page: f.page - 1 })} className="min-h-10 rounded border px-3 py-1 disabled:opacity-40 sm:min-h-9">Sebelumnya</button>
        <span>Hal. {f.page}/{d.pages}</span>
        <button type="button" disabled={f.page >= d.pages} onClick={() => setF({ ...f, page: f.page + 1 })} className="min-h-10 rounded border px-3 py-1 disabled:opacity-40 sm:min-h-9">Berikutnya</button>
      </div>
    </div>
  );
}

/* ================================================================ GALERI PROGRAM SELESAI (publik) */
const KAT_WARNA: Record<string, string> = {
  Disabilitas: KATEGORI_META.disabilitas.warna, Stunting: KATEGORI_META.stunting.warna, ATS: KATEGORI_META.ats.warna,
  Kemiskinan: KATEGORI_META.kemiskinan.warna, "Lintas kategori": "#232F3E",
};

export function ProgramGallery({ limit = 9, compact = false }: { limit?: number; compact?: boolean }) {
  const [d, setD] = useState<any>(null);
  const [kat, setKat] = useState("");
  const [buka, setBuka] = useState<any>(null);
  useEffect(() => {
    api.get("/public/program-selesai", { params: kat ? { kategori: kat } : {} }).then((r) => setD(r.data)).catch(() => setD({ items: [], total: 0, total_penerima: 0 }));
  }, [kat]);
  const items = (d?.items || []).slice(0, limit);
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" data-testid="program-gallery" aria-labelledby="judul-galeri">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="judul-galeri" className="flex items-center gap-2 font-head text-base font-extrabold text-[#232F3E]"><Award className="h-4 w-4 text-[#117A69]" aria-hidden="true" /> Galeri program selesai</h2>
          <p className="mt-0.5 text-xs text-slate-600">Program intervensi NGO yang telah selesai dilaksanakan. Server menyamarkan nama NGO untuk menjaga privasi.</p>
        </div>
        {!compact && (
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter kategori program">
            {["", "Disabilitas", "Stunting", "ATS", "Kemiskinan", "Lintas kategori"].map((k) => (
              <button key={k || "semua"} type="button" onClick={() => setKat(k)} aria-pressed={kat === k} data-testid={`gallery-filter-${k || "semua"}`}
                className={`inline-flex min-h-9 items-center rounded-full px-3.5 py-1.5 text-xs font-bold transition-colors ${kat === k ? "bg-[#232F3E] text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>{k || "Semua"}</button>
            ))}
          </div>
        )}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {[["Program selesai", d?.total, Award], ["Total penerima manfaat", d?.total_penerima, Users], ["Kecamatan terjangkau", d?.kecamatan_terjangkau, MapPin]].map(([l, v, I]: any) => (
          <div key={l} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#E6FAF6] text-[#117A69]" aria-hidden="true">
              <I className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs font-semibold text-slate-600">{l}</p>
              <p className="font-head text-xl font-extrabold text-[#232F3E] tabular-nums" data-testid={`gallery-stat-${l.split(" ")[0].toLowerCase()}`}>{d ? fmt(v || 0) : "…"}</p>
            </div>
          </div>
        ))}
      </div>
      {!d && <div className="mt-4 grid gap-3 sm:grid-cols-3">{[0, 1, 2].map((i) => <div key={i} className="h-36 animate-pulse rounded-xl bg-slate-100" />)}</div>}
      {d && items.length === 0 && (
        <div className="mt-4 rounded-xl border border-dashed border-slate-300 p-6 text-center" data-testid="gallery-empty">
          <p className="text-sm font-semibold text-slate-700">Belum ada program yang selesai{kat ? ` untuk kategori ${kat}` : ""}.</p>
          <p className="mt-1 text-xs text-slate-500">NGO dapat mengajukan program intervensi berdasarkan wilayah prioritas pada peta.</p>
          <Link to="/login?mode=ngo" className="mt-3 inline-flex min-h-10 items-center justify-center rounded-md bg-[#117A69] px-4 py-2 text-xs font-bold text-white hover:bg-[#0E6456]">Daftar sebagai NGO</Link>
        </div>
      )}
      <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((p: any) => (
          <li key={p.id} className="flex flex-col overflow-hidden rounded-xl border border-slate-200 transition-shadow hover:shadow-md" data-testid="gallery-card">
            {p.cerita?.foto?.length > 0 && (
              <button type="button" onClick={() => setBuka(p)} className="relative block" aria-label={`Lihat cerita ${p.program}`} data-testid="gallery-cover">
                <img src={fotoSrc(p.cerita.foto[0].url)} alt={p.cerita.foto[0].keterangan || `Foto kegiatan ${p.program}`} className="aspect-[16/9] w-full object-cover" loading="lazy" />
                {p.cerita.foto.length > 1 && <span className="absolute bottom-2 right-2 rounded-full bg-black/60 px-2 py-0.5 text-[10px] font-bold text-white">{p.cerita.foto.length} foto</span>}
              </button>
            )}
            <div className="flex flex-1 flex-col p-4">
            <div className="flex items-center justify-between gap-2">
              <span className="rounded-full bg-[#232F3E] px-2.5 py-0.5 text-[10px] font-bold uppercase text-white">{p.kategori}</span>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800"><CheckCircle2 className="h-3 w-3" /> Selesai</span>
            </div>
            <h3 className="mt-2 font-head text-base font-extrabold leading-snug text-slate-900" data-testid="gallery-program-name">{p.program}</h3>
            <p className="mt-1 flex items-center gap-1 text-xs text-slate-600"><MapPin className="h-3.5 w-3.5" /> {p.kelurahan ? `Kel. ${p.kelurahan}, ` : ""}Kec. {p.kecamatan}</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div><dt className="text-slate-500">Penerima manfaat</dt><dd className="font-head text-lg font-extrabold text-[#117A69] tabular-nums" data-testid="gallery-penerima">{fmt(p.cerita?.realisasi_penerima ?? p.jumlah_penerima)}</dd></div>
              <div><dt className="text-slate-500">Durasi</dt><dd className="font-semibold text-slate-800">{p.durasi_bulan} bulan</dd></div>
            </dl>
            <p className="mt-2 text-xs text-slate-600">{p.target_penerima}</p>
            {p.cerita?.testimoni?.[0] && (
              <blockquote className="mt-2 line-clamp-3 border-l-4 border-[#6FE3CF] pl-2 text-xs italic text-slate-700" data-testid="gallery-quote">
                "{p.cerita.testimoni[0].kutipan}" <span className="not-italic text-slate-500">, {p.cerita.testimoni[0].sumber}</span></blockquote>
            )}
            {p.cerita && (
              <button type="button" onClick={() => setBuka(p)} data-testid="gallery-baca-cerita"
                className="mb-2 mt-3 self-start rounded-md border border-[#117A69] px-3 py-1.5 text-xs font-bold text-[#117A69] transition-colors hover:bg-[#E6FAF6]">Baca cerita dampak</button>
            )}
            <div className="mt-auto flex items-center justify-between gap-2 border-t border-slate-100 pt-2 text-[11px] text-slate-500">
              <span data-testid="gallery-ngo-masked">NGO: {p.ngo}</span>
              <span className="inline-flex items-center gap-1"><CalendarCheck className="h-3 w-3" /> {p.selesai ? new Date(p.selesai).toLocaleDateString("id-ID", { month: "short", year: "numeric" }) : "-"}</span>
            </div>
            </div>
          </li>
        ))}
      </ul>
      <CeritaDialog program={buka} open={!!buka} onOpenChange={(v) => { if (!v) setBuka(null); }} />
    </section>
  );
}
