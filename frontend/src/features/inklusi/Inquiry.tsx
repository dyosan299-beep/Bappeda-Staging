import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Send, Paperclip, Download, Clock, Plus } from "lucide-react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { fmt } from "./theme";
import { CeritaPanel } from "./CeritaDampak";

export const STATUS_LABEL: Record<string, string> = {
  SUBMITTED: "Diajukan", UNDER_REVIEW: "Ditinjau", VERIFICATION: "Verifikasi", APPROVED: "Disetujui",
  NEED_REVISION: "Perlu Revisi", REJECTED: "Ditolak", PROGRAM_IMPLEMENTATION: "Implementasi Program",
  MONITORING: "Monitoring", COMPLETED: "Selesai",
};
const STATUS_CLS: Record<string, string> = {
  SUBMITTED: "bg-slate-100 text-slate-800", UNDER_REVIEW: "bg-sky-100 text-sky-900", VERIFICATION: "bg-indigo-100 text-indigo-900",
  APPROVED: "bg-emerald-100 text-emerald-900", NEED_REVISION: "bg-amber-100 text-amber-900", REJECTED: "bg-red-100 text-red-900",
  PROGRAM_IMPLEMENTATION: "bg-teal-100 text-teal-900", MONITORING: "bg-cyan-100 text-cyan-900", COMPLETED: "bg-[#232F3E] text-white",
};
export const StatusBadge = ({ s }: { s: string }) => (
  <span className={`inline-block rounded-full px-2.5 py-0.5 text-[11px] font-bold ${STATUS_CLS[s] || "bg-slate-100"}`} data-testid="inquiry-status-badge">{STATUS_LABEL[s] || s}</span>
);
const KATEGORI = ["Disabilitas", "Stunting", "ATS", "Kemiskinan", "Lintas kategori"];
const input = "h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm focus:border-[#117A69]";
const area = "min-h-[90px] w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm";

function Field({ label, id, children, req = false, hint = "" }: any) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-bold text-slate-700">{label}{req && <span className="text-red-700" aria-hidden="true"> *</span>}</label>
      {children}
      {hint && <p className="mt-0.5 text-[11px] text-slate-500">{hint}</p>}
    </div>
  );
}

/* ------------------------------------------------------------ FORM */
export function InquiryForm() {
  const { user } = useAuth();
  const [sp] = useSearchParams();
  const { id } = useParams();
  const navigate = useNavigate();
  const [wil, setWil] = useState<any[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState<any>({
    nama_ngo: (user as any)?.organisasi || "", nama_pic: user?.name || "", email: user?.email || "", telepon: "", organisasi: (user as any)?.organisasi || "",
    alamat_organisasi: "", kategori: sp.get("kategori") || "Disabilitas", kecamatan: sp.get("kecamatan") || "", kelurahan: sp.get("kelurahan") || "",
    permasalahan: "", deskripsi_kebutuhan: "", program_usulan: "", target_penerima: "", jumlah_penerima: "", durasi_bulan: "", estimasi_anggaran: "", catatan: "",
  });
  const statistik = useMemo(() => (sp.get("nilai") ? { indikator: sp.get("indikator"), nilai: Number(sp.get("nilai")), sumber: "PETA INKLUSI" } : {}), [sp]);
  useEffect(() => { api.get("/public/wilayah").then((r) => setWil(r.data.kecamatan)).catch(() => {}); }, []);
  useEffect(() => {
    if (!id) return;
    api.get(`/inquiries/${id}`).then((r) => setF({ ...r.data, estimasi_anggaran: r.data.estimasi_anggaran ?? "" })).catch(() => toast.error("Inquiry tidak ditemukan"));
  }, [id]);
  useEffect(() => {
    if (sp.get("nilai") && !f.permasalahan) {
      setF((x: any) => ({ ...x, permasalahan: `Berdasarkan PETA INKLUSI, ${sp.get("indikator")} di ${sp.get("kelurahan") ? "Kel. " + sp.get("kelurahan") + ", " : ""}Kec. ${sp.get("kecamatan")} tercatat ${fmt(sp.get("nilai"))}. ` }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });
  const kelList = wil.find((k) => k.nama === f.kecamatan)?.kelurahan || [];

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { ...f, jumlah_penerima: Number(f.jumlah_penerima), durasi_bulan: Number(f.durasi_bulan),
        estimasi_anggaran: f.estimasi_anggaran === "" ? null : Number(f.estimasi_anggaran), statistik_wilayah: id ? f.statistik_wilayah || {} : statistik };
      ["id", "nomor", "status", "riwayat", "lampiran", "user_email", "user_name", "created_at", "updated_at", "transisi_berikut", "data_masked"].forEach((k) => delete payload[k]);
      const r = id ? await api.put(`/inquiries/${id}`, payload) : await api.post("/inquiries", payload);
      if (file) {
        const fd = new FormData(); fd.append("file", file);
        await api.post(`/inquiries/${r.data.id}/lampiran`, fd).catch((er) => toast.error(formatApiErrorDetail(er.response?.data?.detail)));
      }
      toast.success(id ? "Revisi inquiry terkirim" : `Inquiry ${r.data.nomor} berhasil diajukan`);
      navigate(`/ngo/inquiry/${r.data.id}`);
    } catch (er: any) {
      toast.error(formatApiErrorDetail(er.response?.data?.detail));
    } finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit} className="space-y-5" data-testid="inquiry-form">
      <div>
        <p className="font-head text-2xl font-extrabold text-[#232F3E]">{id ? "Revisi Inquiry" : "Ajukan Inquiry / Program Intervensi"}</p>
        <p className="text-sm text-slate-600">Isian bertanda * wajib diisi.</p>
      </div>
      {!!Object.keys(statistik).length && !id && (
        <div className="rounded-lg border border-[#6FE3CF] bg-[#E6FAF6] p-3 text-sm text-[#0B4F45]" data-testid="inquiry-prefill-info">
          Diisi otomatis dari peta: <b>{f.kategori}</b> · Kec. <b>{f.kecamatan}</b>{f.kelurahan && <> · Kel. <b>{f.kelurahan}</b></>} · {statistik.indikator}: <b>{fmt(statistik.nilai)}</b>
        </div>
      )}
      <fieldset className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 md:grid-cols-2">
        <legend className="px-1 font-head text-sm font-extrabold text-[#117A69]">Identitas NGO</legend>
        <Field label="Nama NGO" id="nama_ngo" req><input id="nama_ngo" required className={input} value={f.nama_ngo} onChange={set("nama_ngo")} data-testid="inq-nama-ngo" /></Field>
        <Field label="Nama PIC" id="nama_pic" req><input id="nama_pic" required className={input} value={f.nama_pic} onChange={set("nama_pic")} data-testid="inq-nama-pic" /></Field>
        <Field label="Email" id="email" req><input id="email" type="email" required className={input} value={f.email} onChange={set("email")} data-testid="inq-email" /></Field>
        <Field label="Nomor telepon" id="telepon" req><input id="telepon" required inputMode="tel" pattern="\+?[0-9 ()-]{6,20}" className={input} value={f.telepon} onChange={set("telepon")} data-testid="inq-telepon" /></Field>
        <Field label="Organisasi" id="organisasi"><input id="organisasi" className={input} value={f.organisasi} onChange={set("organisasi")} /></Field>
        <Field label="Alamat / keterangan organisasi" id="alamat_organisasi"><input id="alamat_organisasi" className={input} value={f.alamat_organisasi} onChange={set("alamat_organisasi")} /></Field>
      </fieldset>
      <fieldset className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 md:grid-cols-2">
        <legend className="px-1 font-head text-sm font-extrabold text-[#117A69]">Informasi Program</legend>
        <Field label="Kategori program" id="kategori" req><select id="kategori" className={input} value={f.kategori} onChange={set("kategori")} data-testid="inq-kategori">{KATEGORI.map((k) => <option key={k}>{k}</option>)}</select></Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Kecamatan" id="kecamatan" req><select id="kecamatan" required className={input} value={f.kecamatan} onChange={(e) => setF({ ...f, kecamatan: e.target.value, kelurahan: "" })} data-testid="inq-kecamatan"><option value="">Pilih…</option>{wil.map((k) => <option key={k.nama}>{k.nama}</option>)}</select></Field>
          <Field label="Kelurahan" id="kelurahan"><select id="kelurahan" className={input} value={f.kelurahan} onChange={set("kelurahan")} data-testid="inq-kelurahan"><option value="">Semua / lintas kelurahan</option>{kelList.map((k: string) => <option key={k}>{k}</option>)}</select></Field>
        </div>
        <div className="md:col-span-2"><Field label="Permasalahan yang ditemukan" id="permasalahan" req><textarea id="permasalahan" required minLength={10} className={area} value={f.permasalahan} onChange={set("permasalahan")} data-testid="inq-permasalahan" /></Field></div>
        <div className="md:col-span-2"><Field label="Deskripsi kebutuhan / intervensi" id="deskripsi_kebutuhan" req><textarea id="deskripsi_kebutuhan" required minLength={10} className={area} value={f.deskripsi_kebutuhan} onChange={set("deskripsi_kebutuhan")} data-testid="inq-kebutuhan" /></Field></div>
        <Field label="Program yang diusulkan" id="program_usulan" req><input id="program_usulan" required minLength={3} className={input} value={f.program_usulan} onChange={set("program_usulan")} data-testid="inq-program" /></Field>
        <Field label="Target penerima manfaat" id="target_penerima" req><input id="target_penerima" required minLength={3} className={input} value={f.target_penerima} onChange={set("target_penerima")} data-testid="inq-target" /></Field>
        <Field label="Perkiraan jumlah penerima" id="jumlah_penerima" req><input id="jumlah_penerima" type="number" min={1} required className={input} value={f.jumlah_penerima} onChange={set("jumlah_penerima")} data-testid="inq-jumlah" /></Field>
        <Field label="Durasi program (bulan)" id="durasi_bulan" req><input id="durasi_bulan" type="number" min={1} max={120} required className={input} value={f.durasi_bulan} onChange={set("durasi_bulan")} data-testid="inq-durasi" /></Field>
        <Field label="Estimasi kebutuhan anggaran (Rp)" id="estimasi_anggaran" hint="Opsional"><input id="estimasi_anggaran" type="number" min={0} className={input} value={f.estimasi_anggaran} onChange={set("estimasi_anggaran")} data-testid="inq-anggaran" /></Field>
        <Field label="Lampiran dokumen proposal" id="lampiran" hint="PDF/DOC/DOCX/XLS/PPT/JPG/PNG, maks. 10 MB"><input id="lampiran" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png" className="block w-full max-w-full text-sm file:mr-2 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-xs file:font-semibold hover:file:bg-slate-200" onChange={(e) => setFile(e.target.files?.[0] || null)} data-testid="inq-lampiran" /></Field>
        <div className="md:col-span-2"><Field label="Catatan tambahan" id="catatan"><textarea id="catatan" className={area} value={f.catatan} onChange={set("catatan")} /></Field></div>
      </fieldset>
      <button type="submit" disabled={busy} data-testid="inq-submit" className="inline-flex items-center gap-2 rounded-md bg-[#117A69] px-6 py-3 font-bold text-white hover:bg-[#0E6456] disabled:opacity-50">
        <Send className="h-4 w-4" /> {busy ? "Mengirim…" : id ? "Kirim Revisi" : "Kirim Inquiry"}
      </button>
    </form>
  );
}

/* ------------------------------------------------------------ LIST */
export function InquiryList() {
  const { user } = useAuth();
  const [d, setD] = useState<any>(null);
  const [filt, setFilt] = useState<any>({ status: "", kategori: "", q: "" });
  const isNgo = user?.role === "ngo";
  useEffect(() => {
    const p: any = {}; Object.entries(filt).forEach(([k, v]) => { if (v) p[k] = v; });
    api.get("/inquiries", { params: p }).then((r) => setD(r.data)).catch(() => setD({ items: [], total: 0 }));
  }, [filt]);
  return (
    <div className="space-y-4" data-testid="inquiry-list">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="font-head text-2xl font-extrabold text-[#232F3E]">{isNgo ? "Status Inquiry Saya" : "NGO Inquiry"}</p>
          <p className="text-sm text-slate-600">{isNgo ? "Pantau inquiry yang Anda ajukan." : "Tinjau, verifikasi, dan proses usulan program dari NGO."}</p></div>
        {(isNgo || ["superadmin", "admin"].includes(user?.role || "")) && <Link to="/ngo/inquiry/baru" data-testid="inquiry-new-btn" className="inline-flex items-center gap-2 rounded-md bg-[#117A69] px-4 py-2 text-sm font-bold text-white"><Plus className="h-4 w-4" /> Ajukan Inquiry</Link>}
      </div>
      <div className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-3">
        <select aria-label="Filter status" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto" value={filt.status} onChange={(e) => setFilt({ ...filt, status: e.target.value })} data-testid="inquiry-filter-status">
          <option value="">Semua status</option>{Object.keys(STATUS_LABEL).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}</select>
        <select aria-label="Filter kategori" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto" value={filt.kategori} onChange={(e) => setFilt({ ...filt, kategori: e.target.value })} data-testid="inquiry-filter-kategori">
          <option value="">Semua kategori</option>{KATEGORI.map((k) => <option key={k}>{k}</option>)}</select>
        {!isNgo && <input aria-label="Cari nama NGO" placeholder="Cari nama NGO…" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-56" value={filt.q} onChange={(e) => setFilt({ ...filt, q: e.target.value })} data-testid="inquiry-search" />}
      </div>
      <div className="table-scroll overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-600"><tr><th className="p-3">Nomor</th><th className="p-3">NGO</th><th className="p-3">Kategori</th><th className="p-3">Wilayah</th><th className="p-3">Program</th><th className="p-3">Status</th><th className="p-3">Diperbarui</th></tr></thead>
          <tbody>
            {(d?.items || []).map((i: any) => (
              <tr key={i.id} className="border-t hover:bg-slate-50" data-testid={`inquiry-row-${i.nomor}`}>
                <td className="p-3 font-semibold"><Link className="text-[#117A69] underline" to={`/ngo/inquiry/${i.id}`}>{i.nomor}</Link></td>
                <td className="p-3">{i.nama_ngo}</td><td className="p-3">{i.kategori}</td><td className="p-3">{i.kelurahan ? `${i.kelurahan}, ` : ""}{i.kecamatan}</td>
                <td className="p-3">{i.program_usulan}</td><td className="p-3"><StatusBadge s={i.status} /></td><td className="p-3 text-xs text-slate-500">{new Date(i.updated_at).toLocaleString("id-ID")}</td>
              </tr>
            ))}
            {d && !d.items.length && <tr><td colSpan={7} className="p-6 text-center text-slate-500">Belum ada inquiry.</td></tr>}
            {!d && <tr><td colSpan={7} className="p-6 text-center text-slate-500">Memuat…</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ DETAIL */
export function InquiryDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [d, setD] = useState<any>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => api.get(`/inquiries/${id}`).then((r) => setD(r.data)).catch(() => setD(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [id]);
  if (d === false) return <p className="p-6 text-red-700">Inquiry tidak ditemukan atau Anda tidak berwenang.</p>;
  if (!d) return <p className="p-6 text-slate-500">Memuat…</p>;
  const ubah = async (status: string) => {
    setBusy(true);
    try {
      const r = await api.patch(`/inquiries/${id}/status`, { status, catatan: note }); setD(r.data); setNote("");
      const em = r.data.notifikasi_email;
      toast.success(`Status diubah ke ${STATUS_LABEL[status]}`, {
        description: em === "terkirim" ? "Email notifikasi terkirim ke NGO." : em === "belum_terkirim" ? "Email notifikasi dicatat (SMTP belum dikonfigurasi)." : em === "gagal" ? "Email notifikasi gagal dikirim — cek menu Notifikasi Email." : undefined,
      });
    }
    catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };
  const unduh = async (m: any) => {
    const r = await api.get(`/inquiries/${id}/lampiran/${m.id}`, { responseType: "blob" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(r.data); a.download = m.nama; a.click();
  };
  const own = d.user_email === user?.email;
  const rows = [["Nama NGO", d.nama_ngo], ["PIC", d.nama_pic], ["Email", d.email], ["Telepon", d.telepon], ["Organisasi", d.organisasi], ["Alamat organisasi", d.alamat_organisasi],
    ["Kategori", d.kategori], ["Wilayah", `${d.kelurahan ? "Kel. " + d.kelurahan + ", " : ""}Kec. ${d.kecamatan}`], ["Program usulan", d.program_usulan], ["Target penerima", d.target_penerima],
    ["Jumlah penerima", fmt(d.jumlah_penerima)], ["Durasi", `${d.durasi_bulan} bulan`], ["Estimasi anggaran", d.estimasi_anggaran ? `Rp ${fmt(d.estimasi_anggaran)}` : "-"]];
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_340px]" data-testid="inquiry-detail">
      <div className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-center gap-3"><p className="font-head text-2xl font-extrabold text-[#232F3E]">{d.nomor}</p><StatusBadge s={d.status} />
          {d.data_masked && <span className="text-xs text-slate-500">(kontak tersamarkan sesuai peran)</span>}</div>
        {own && ["SUBMITTED", "NEED_REVISION"].includes(d.status) && <Link to={`/ngo/inquiry/${d.id}/revisi`} data-testid="inquiry-revise-btn" className="inline-block rounded-md border border-[#117A69] px-3 py-1.5 text-sm font-bold text-[#117A69]">Revisi inquiry</Link>}
        <dl className="grid gap-x-6 gap-y-2 rounded-xl border border-slate-200 bg-white p-4 text-sm sm:grid-cols-2">
          {rows.map(([k, v]) => <div key={k} className="min-w-0"><dt className="text-xs font-bold text-slate-500">{k}</dt><dd className="break-words text-slate-900">{v || "-"}</dd></div>)}
        </dl>
        {[["Permasalahan", d.permasalahan], ["Deskripsi kebutuhan / intervensi", d.deskripsi_kebutuhan], ["Catatan", d.catatan]].map(([k, v]) => v ? (
          <section key={k} className="rounded-xl border border-slate-200 bg-white p-4"><h2 className="text-xs font-bold uppercase text-slate-500">{k}</h2><p className="mt-1 whitespace-pre-line text-sm">{v}</p></section>) : null)}
        {d.statistik_wilayah && Object.keys(d.statistik_wilayah).length > 0 && (
          <section className="rounded-xl border border-[#6FE3CF] bg-[#E6FAF6] p-4 text-sm"><h2 className="text-xs font-bold uppercase text-[#0B4F45]">Statistik wilayah terkait (dari peta)</h2>
            <p className="mt-1">{Object.entries(d.statistik_wilayah).map(([k, v]) => `${k}: ${v}`).join(" · ")}</p></section>)}
        <section className="rounded-xl border border-slate-200 bg-white p-4"><h2 className="flex items-center gap-1 text-xs font-bold uppercase text-slate-500"><Paperclip className="h-3.5 w-3.5" /> Lampiran</h2>
          {(d.lampiran || []).length ? d.lampiran.map((m: any) => <button key={m.id} type="button" onClick={() => unduh(m)} className="mt-1 flex items-center gap-1 break-all text-left text-sm text-[#117A69] underline" data-testid="inquiry-attachment"><Download className="h-3.5 w-3.5 shrink-0" /> {m.nama} ({Math.round(m.ukuran / 1024)} KB)</button>) : <p className="text-sm text-slate-500">Tidak ada lampiran.</p>}
        </section>
        <CeritaPanel key={`${d.id}-${d.status}`} inquiry={d} />
      </div>
      <aside className="min-w-0 space-y-4">
        {(d.transisi_berikut || []).length > 0 && (
          <section className="rounded-xl border-2 border-[#117A69] bg-white p-4" data-testid="inquiry-actions"><h2 className="font-head text-sm font-extrabold text-[#232F3E]">Proses Inquiry</h2>
            <label htmlFor="catatan-proses" className="mt-2 block text-xs font-bold text-slate-600">Catatan (wajib untuk revisi/penolakan)</label>
            <textarea id="catatan-proses" className={area} value={note} onChange={(e) => setNote(e.target.value)} data-testid="inquiry-note" />
            <div className="mt-2 flex flex-wrap gap-2">{d.transisi_berikut.map((s: string) => (
              <button key={s} type="button" disabled={busy} onClick={() => ubah(s)} data-testid={`inquiry-action-${s}`}
                className={`rounded-md px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50 ${s === "REJECTED" ? "bg-red-700" : s === "NEED_REVISION" ? "bg-amber-700" : "bg-[#117A69]"}`}>{STATUS_LABEL[s]}</button>))}</div>
          </section>)}
        <section className="rounded-xl border border-slate-200 bg-white p-4"><h2 className="flex items-center gap-1 font-head text-sm font-extrabold text-[#232F3E]"><Clock className="h-4 w-4" /> Histori Status</h2>
          <ol className="mt-3 space-y-3 border-l-2 border-[#6FE3CF] pl-4" data-testid="inquiry-history">{(d.riwayat || []).slice().reverse().map((h: any, i: number) => (
            <li key={i}><StatusBadge s={h.status} /><p className="mt-0.5 text-xs text-slate-600">{new Date(h.waktu).toLocaleString("id-ID")} · {h.peran} ({h.oleh})</p>
              {h.email && user?.role !== "ngo" && <p className="text-[11px] text-slate-500" data-testid="inquiry-history-email">Email NGO: {h.email === "terkirim" ? "terkirim" : h.email === "belum_terkirim" ? "belum terkirim (SMTP belum aktif)" : h.email}</p>}{h.catatan && <p className="text-sm">{h.catatan}</p>}</li>))}</ol>
        </section>
      </aside>
    </div>
  );
}
