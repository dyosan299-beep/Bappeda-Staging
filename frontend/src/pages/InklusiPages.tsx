import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { fmt } from "@/features/inklusi/theme";
import { FileSpreadsheet, FileText, History, Upload } from "lucide-react";
import { AtsImportPanel, ImportDialog, SENSITIVE, StuntingImportPanel, WRITERS } from "@/features/inklusi/InklusiExtra";
import { InputDataButton } from "@/features/data/InputDataButton";
import { PageHeader } from "@/features/data/ui";
import { downloadBlob } from "@/features/inklusi/download";

const th = "p-2 text-left text-[11px] font-bold uppercase text-slate-600";

export function DataStunting() {
  const [d, setD] = useState<any>(null);
  const [st, setSt] = useState<any>(null);
  const [f, setF] = useState<any>({ q: "", kecamatan: "", status: "", jk: "", page: 1 });
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [reload, setReload] = useState(0);
  const filtered = !!(f.q || f.kecamatan || f.status || f.jk);
  const { user } = useAuth();
  const bolehImpor = SENSITIVE.includes(user?.role || "");
  const [impor, setImpor] = useState<"" | "impor" | "riwayat">("");
  const tutupImpor = React.useCallback(() => setImpor(""), []);
  useEffect(() => { api.get("/inklusi/stunting/stats").then((r) => setSt(r.data)).catch(() => setSt(null)); }, [reload]);
  useEffect(() => {
    const p: any = { size: 25 }; Object.entries(f).forEach(([k, v]) => { if (v) p[k] = v; });
    setLoading(true); setErr("");
    let active = true;
    api.get("/inklusi/stunting/children", { params: p }).then((r) => { if (active) setD(r.data); })
      .catch((e) => { if (!active) return; setD({ items: [], total: 0, pages: 1 }); setErr(e?.response?.data?.detail || "Gagal memuat data stunting dari server."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [f, reload]);
  return (
    <div className="space-y-4" data-testid="data-stunting">
      <PageHeader title="Data Stunting"
        subtitle="Balita stunting 2026 — Kec. Makassar & Kec. Tallo (sumber: DATA STUNTING KEC MAKASSAR DAN TALLO.pdf)"
        actions={bolehImpor ? (
          <div className="flex flex-wrap items-center gap-2">
            <InputDataButton testid="btn-input-stunting" pilihan={[
              { label: "Import PDF Stunting", ket: "Unggah PDF data balita, pratinjau, lalu simpan", icon: Upload, aksi: () => setImpor("impor"), testid: "menu-import-pdf-stunting" },
              { label: "Riwayat Impor", ket: "Lihat berkas yang pernah diimpor", icon: History, aksi: () => setImpor("riwayat"), testid: "menu-riwayat-stunting" },
            ]} />
          </div>
        ) : undefined} />
      {st && <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{[["Total balita", st.total], ...st.status_tbu.map((x: any) => [x.kategori, x.jumlah]), ...st.per_kecamatan.slice(0, 2).map((x: any) => [`Kec. ${x.kategori}`, x.jumlah])].slice(0, 4).map(([l, v]: any) => (
        <div key={l} className="rounded-xl bg-white p-3 ring-1 ring-slate-200" style={{ borderLeft: "5px solid #C8375B" }}><p className="text-[11px] font-bold uppercase text-slate-600">{l}</p><p className="font-head text-2xl font-extrabold tabular-nums">{fmt(v)}</p></div>))}</div>}
      {impor && (
        <ImportDialog judul="Import PDF Data Balita Stunting" testid="dialog-impor-stunting" onClose={tutupImpor}
          keterangan="Format kolom: No, Nama, JK, Tgl Lahir, Nama Orang Tua, Puskesmas, Kelurahan, Alamat, TB/U">
          <StuntingImportPanel fokusRiwayat={impor === "riwayat"}
            onImported={() => { setReload((x) => x + 1); setF({ q: "", kecamatan: "", status: "", jk: "", page: 1 }); setImpor(""); }} />
        </ImportDialog>
      )}
      {d?.masked && <p className="rounded-md bg-amber-50 p-2 text-xs text-amber-900" data-testid="stunting-masked-note">Nama, nama orang tua, alamat, dan tanggal lahir disamarkan sesuai peran Anda.</p>}
      <div className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-3">
        <input aria-label="Cari nama" placeholder="Cari nama…" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto sm:min-w-[180px]" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value, page: 1 })} data-testid="stunting-search" />
        <select aria-label="Kecamatan" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto" value={f.kecamatan} onChange={(e) => setF({ ...f, kecamatan: e.target.value, page: 1 })}><option value="">Semua kecamatan</option><option>Makassar</option><option>Tallo</option></select>
        <select aria-label="Status TB/U" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value, page: 1 })} data-testid="stunting-filter-status"><option value="">Semua status</option><option>Pendek</option><option>Sangat Pendek</option></select>
        <select aria-label="Jenis kelamin" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto" value={f.jk} onChange={(e) => setF({ ...f, jk: e.target.value, page: 1 })}><option value="">L/P</option><option value="L">Laki-laki</option><option value="P">Perempuan</option></select>
      </div>
      <div className="table-scroll rounded-xl border border-slate-200 bg-white"><table className="w-full min-w-[960px] text-sm"><thead className="bg-slate-50"><tr>{["Nama", "JK", "Tgl lahir", "Umur", "Orang tua", "Puskesmas", "Kelurahan", "Kecamatan", "Alamat", "TB/U"].map((h) => <th key={h} className={`${th} whitespace-nowrap`}>{h}</th>)}</tr></thead>
        <tbody>{loading && <tr><td colSpan={10} className="p-6 text-center text-slate-500" data-testid="stunting-loading">Memuat data…</td></tr>}
          {!loading && err && <tr><td colSpan={10} className="p-6 text-center text-red-700" data-testid="stunting-error">{String(err)}</td></tr>}
          {!loading && !err && (d?.items || []).length === 0 && <tr><td colSpan={10} className="p-6 text-center" data-testid="stunting-empty">
            {filtered ? <span className="text-slate-600">Tidak ada data balita yang sesuai filter.</span>
              : <span className="text-slate-700"><b>Data balita stunting belum diimpor.</b><br />{bolehImpor
                ? <span className="text-sm text-slate-600">Klik tombol <b>Input Data</b> di kanan atas → <b>Import PDF Stunting</b>.{" "}
                    <button type="button" onClick={() => setImpor("impor")} className="font-semibold text-[#117A69] underline" data-testid="stunting-empty-import">Impor sekarang</button></span>
                : <span className="text-sm text-slate-600">Hubungi Admin/Super Admin untuk mengimpor berkas PDF data stunting.</span>}</span>}</td></tr>}
          {!loading && (d?.items || []).map((r: any) => <tr key={r.id} className="border-t" data-testid="stunting-row"><td className="p-2 font-semibold">{r.nama}</td><td className="whitespace-nowrap p-2">{r.jk}</td><td className="whitespace-nowrap p-2">{r.tgl_lahir}</td><td className="whitespace-nowrap p-2">{r.kelompok_umur}</td><td className="p-2">{r.nama_ortu}</td><td className="p-2">{r.puskesmas}</td><td className="p-2">{r.kelurahan}</td><td className="whitespace-nowrap p-2">{r.kecamatan}</td><td className="p-2">{r.alamat}</td>
          <td className="whitespace-nowrap p-2"><span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-bold ${r.status_tbu === "Sangat Pendek" ? "bg-[#FCE8ED] text-[#8E2240]" : "bg-amber-100 text-amber-900"}`}>{r.status_tbu}</span></td></tr>)}</tbody></table></div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm"><span>{fmt(d?.total)} data</span><div className="flex flex-wrap items-center gap-2">
        <button type="button" disabled={f.page <= 1} onClick={() => setF({ ...f, page: f.page - 1 })} className="min-h-10 rounded border px-3 py-1 disabled:opacity-40">Sebelumnya</button><span>Hal. {f.page}/{d?.pages || 1}</span>
        <button type="button" disabled={f.page >= (d?.pages || 1)} onClick={() => setF({ ...f, page: f.page + 1 })} className="min-h-10 rounded border px-3 py-1 disabled:opacity-40" data-testid="stunting-next">Berikutnya</button></div></div>
    </div>
  );
}

export function DataATS() {
  const [d, setD] = useState<any>(null);
  const [kel, setKel] = useState<any>(null);
  const [tahun, setTahun] = useState<string>("");
  const [q, setQ] = useState("");
  const loadKel = (t = tahun) => api.get("/inklusi/ats/kelurahan", { params: t ? { tahun: t } : {} }).then((r) => setKel(r.data)).catch(() => setKel({ tersedia: false, items: [] }));
  useEffect(() => { api.get("/public/ats").then((r) => setD(r.data)).catch(() => {}); }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadKel(tahun); }, [tahun]);
  const rows = (kel?.items || []).filter((r: any) => !q || `${r.kelurahan} ${r.kecamatan}`.toLowerCase().includes(q.toLowerCase()));
  const { user } = useAuth();
  const bolehImpor = WRITERS.includes(user?.role || "");
  const [impor, setImpor] = useState(false);
  const tutupImpor = React.useCallback(() => setImpor(false), []);
  return (
    <div className="space-y-4" data-testid="data-ats">
      <PageHeader title="Data Anak Tidak Sekolah (ATS)"
        subtitle="Matriks ATS per kecamatan + data ATS tingkat kelurahan (impor Excel/CSV)"
        actions={bolehImpor ? (
          <div className="flex flex-wrap items-center gap-2">
            <InputDataButton testid="btn-input-ats" pilihan={[
              { label: "Import Excel / CSV", ket: "Unggah .xlsx / .xls / .csv jumlah anak per kelurahan", icon: FileSpreadsheet, aksi: () => setImpor(true), testid: "menu-import-ats" },
              { label: "Download Template Excel", ket: "Template kolom kelurahan, jenjang, L/P + petunjuk", icon: FileText,
                aksi: () => downloadBlob("/inklusi/ats/template", {}, "template_ats_kelurahan.xlsx"), testid: "menu-template-ats" },
            ]} />
          </div>
        ) : undefined} />
      {kel && !kel.tersedia && (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900" data-testid="ats-placeholder">
          Data ATS tingkat kelurahan <b>belum tersedia</b>.{" "}
          {bolehImpor
            ? <>Klik tombol <b>Input Data</b> di kanan atas → <b>Download Template Excel</b>, isi jumlah anak per kelurahan, lalu <b>Import Excel / CSV</b> — peta ATS tingkat kelurahan akan terisi otomatis.</>
            : <>Hubungi Admin/Operator untuk mengimpor data ATS per kelurahan.</>}
        </p>
      )}
      {impor && (
        <ImportDialog judul="Import Data ATS per Kelurahan" testid="dialog-impor-ats" onClose={tutupImpor}
          keterangan="Format: .xlsx / .xls / .csv sesuai template">
          <AtsImportPanel onImported={() => loadKel(tahun)} />
        </ImportDialog>
      )}
      {kel?.tersedia && (
        <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4" data-testid="ats-kelurahan-section">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div><h2 className="text-sm font-extrabold uppercase">ATS per kelurahan — tahun {kel.tahun}</h2>
              <p className="text-xs text-slate-600">{fmt(kel.items.length)} kelurahan · {fmt(kel.total)} anak · L {fmt(kel.laki_laki)} / P {fmt(kel.perempuan)}</p></div>
            <div className="flex w-full flex-wrap gap-2 sm:w-auto">
              <input aria-label="Cari kelurahan" placeholder="Cari kelurahan…" value={q} onChange={(e) => setQ(e.target.value)} className="h-10 min-w-0 flex-1 rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:flex-none" data-testid="ats-kel-search" />
              <select aria-label="Tahun" value={tahun || kel.tahun} onChange={(e) => setTahun(e.target.value)} className="h-9 rounded-md border border-slate-300 px-2 text-sm" data-testid="ats-tahun">
                {(kel.tahun_list || []).map((t: number) => <option key={t} value={t}>{t}</option>)}</select>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {[["Per jenjang", kel.per_jenjang], ["Per status pendidikan", kel.per_status]].map(([t, arr]: any) => (
              <div key={t} className="rounded-lg bg-slate-50 p-3"><p className="text-xs font-bold text-slate-600">{t}</p>
                <ul className="mt-1 space-y-0.5">{(arr || []).map((x: any) => <li key={x.kategori} className="flex justify-between text-xs"><span>{x.kategori}</span><b>{fmt(x.jumlah)}</b></li>)}</ul></div>
            ))}
          </div>
          <div className="max-h-[420px] overflow-auto rounded-md ring-1 ring-slate-200"><table className="w-full min-w-[540px] text-sm" data-testid="ats-kelurahan-table"><thead className="sticky top-0 bg-slate-50"><tr>{["Kelurahan", "Kecamatan", "Laki-laki", "Perempuan", "Jumlah"].map((h) => <th key={h} className={`${th} whitespace-nowrap`}>{h}</th>)}</tr></thead>
            <tbody>{rows.map((r: any) => <tr key={r.kelurahan + r.kecamatan} className="border-t" data-testid="ats-kel-row"><td className="p-2 font-semibold">{r.kelurahan}</td><td className="p-2">{r.kecamatan}</td><td className="p-2 tabular-nums">{fmt(r.laki_laki)}</td><td className="p-2 tabular-nums">{fmt(r.perempuan)}</td><td className="p-2 font-bold tabular-nums">{fmt(r.jumlah)}</td></tr>)}</tbody></table></div>
        </section>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="min-w-0 rounded-xl border border-slate-200 bg-white p-4"><h2 className="mb-2 text-sm font-extrabold uppercase">ATS per kecamatan (Matriks ATS)</h2>
          <div className="table-scroll"><table className="w-full text-sm"><tbody>{(d?.per_kecamatan || []).map((r: any) => <tr key={r.kecamatan} className="border-t"><td className="py-1.5 pr-2">{r.kecamatan}</td><td className="py-1.5 text-right font-bold tabular-nums">{fmt(r.jumlah)}</td></tr>)}</tbody></table></div></section>
        <section className="min-w-0 rounded-xl border border-slate-200 bg-white p-4"><h2 className="mb-2 text-sm font-extrabold uppercase">Ringkasan & tren</h2>
          <dl className="grid grid-cols-2 gap-2 text-sm">{Object.entries(d?.ringkasan || {}).map(([k, v]) => <div key={k}><dt className="text-xs uppercase text-slate-500">{k.replace(/_/g, " ")}</dt><dd className="font-bold tabular-nums">{fmt(v)}</dd></div>)}</dl>
          <div className="table-scroll mt-3"><table className="w-full min-w-[320px] text-sm"><thead><tr className="text-left text-xs text-slate-500"><th className="py-1 pr-2">Tahun</th><th className="py-1 pr-2">ATS SD</th><th className="py-1 pr-2">ATS SMP</th><th className="py-1">Kembali sekolah</th></tr></thead><tbody>{(d?.per_tahun || []).map((r: any) => <tr key={r.tahun} className="border-t"><td className="py-1.5 pr-2">{r.tahun}</td><td className="py-1.5 pr-2 tabular-nums">{fmt(r.ats_sd)}</td><td className="py-1.5 pr-2 tabular-nums">{fmt(r.ats_smp)}</td><td className="py-1.5 tabular-nums">{fmt(r.kembali_sekolah)}</td></tr>)}</tbody></table></div></section>
      </div>
    </div>
  );
}

export function ProgramManajemen() {
  const [m, setM] = useState<any>(null);
  const [inq, setInq] = useState<any>(null);
  const [kel, setKel] = useState("");
  useEffect(() => { api.get("/inklusi/musrenbang", { params: kel ? { kelompok: kel } : {} }).then((r) => setM(r.data)).catch(() => {}); }, [kel]);
  const [cer, setCer] = useState<any>(null);
  useEffect(() => { api.get("/inquiries", { params: { size: 100 } }).then((r) => setInq(r.data)).catch(() => {}); }, []);
  useEffect(() => { api.get("/inklusi/cerita").then((r) => setCer(r.data)).catch(() => setCer({ items: [], menunggu: 0 })); }, []);
  const aktif = (inq?.items || []).filter((i: any) => ["APPROVED", "PROGRAM_IMPLEMENTATION", "MONITORING", "COMPLETED"].includes(i.status));
  return (
    <div className="space-y-4" data-testid="program-manajemen">
      <p className="font-head text-2xl font-extrabold text-[#232F3E]">Manajemen Program</p>
      <section className="rounded-xl border border-slate-200 bg-white p-4"><h2 className="text-sm font-extrabold uppercase">Program intervensi dari NGO Inquiry (disetujui s.d. selesai)</h2>
        {aktif.length ? <ul className="mt-2 divide-y text-sm">{aktif.map((i: any) => <li key={i.id} className="flex flex-wrap justify-between gap-2 py-2"><Link to={`/ngo/inquiry/${i.id}`} className="font-semibold text-[#117A69] underline">{i.nomor} — {i.program_usulan}</Link><span>{i.nama_ngo} · {i.kategori} · {i.kecamatan} · {i.status}</span></li>)}</ul>
          : <p className="mt-2 text-sm text-slate-500">Belum ada program yang disetujui.</p>}</section>
      <section className="rounded-xl border border-slate-200 bg-white p-4" data-testid="cerita-list"><div className="flex items-center justify-between"><h2 className="text-sm font-extrabold uppercase">Cerita dampak program</h2>
        {cer?.menunggu > 0 && <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-900" data-testid="cerita-menunggu">{cer.menunggu} menunggu review</span>}</div>
        {cer?.items?.length ? <ul className="mt-2 divide-y text-sm">{cer.items.map((c: any) => <li key={c.inquiry_id} className="flex flex-wrap justify-between gap-2 py-2"><Link to={`/ngo/inquiry/${c.inquiry_id}`} className="font-semibold text-[#117A69] underline">{c.nomor} — {c.program}</Link><span className="text-xs text-slate-600">{c.nama_ngo} · {c.jumlah_foto} foto · <b>{c.status_label}</b></span></li>)}</ul>
          : <p className="mt-2 text-sm text-slate-500">Belum ada cerita dampak dari NGO.</p>}</section>
      <section className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-sm font-extrabold uppercase">Referensi usulan Musrenbang Tematik (26 Nov 2025)</h2>
        <select aria-label="Kelompok kepentingan" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto" value={kel} onChange={(e) => setKel(e.target.value)} data-testid="musrenbang-filter"><option value="">Semua kelompok</option>{(m?.kelompok || []).map((k: any) => <option key={k.kelompok} value={k.kelompok}>{k.kelompok} ({k.jumlah})</option>)}</select></div>
        <div className="table-scroll mt-2"><table className="w-full min-w-[780px] text-sm"><thead className="bg-slate-50"><tr>{["Kelompok", "Permasalahan", "Kebutuhan", "Usulan kegiatan", "Lokasi", "OPD"].map((h) => <th key={h} className={`${th} whitespace-nowrap`}>{h}</th>)}</tr></thead>
          <tbody>{(m?.items || []).map((r: any) => <tr key={r.id} className="border-t align-top" data-testid="musrenbang-row"><td className="p-2 font-semibold">{r.kelompok}</td><td className="p-2">{r.permasalahan}</td><td className="p-2">{r.kebutuhan}</td><td className="p-2">{r.usulan_kegiatan}</td><td className="p-2">{r.lokasi}</td><td className="p-2">{r.opd}</td></tr>)}</tbody></table></div></section>
    </div>
  );
}

const MATRIKS: [string, string[]][] = [
  ["Lihat dashboard & peta agregat", ["✓", "✓", "✓", "✓", "✓"]],
  ["Lihat data individu (tersamarkan)", ["–", "–", "✓", "✓", "✓"]],
  ["Lihat data individu asli (NIK, nama, alamat)", ["–", "–", "–", "✓*", "✓"]],
  ["Ajukan & pantau inquiry milik sendiri", ["–", "✓", "–", "–", "✓"]],
  ["Tinjau / verifikasi / setujui / tolak inquiry", ["–", "–", "✓", "✓", "✓"]],
  ["Input & impor data wilayah", ["–", "–", "✓", "✓", "✓"]],
  ["Hapus data / rollback impor", ["–", "–", "–", "✓", "✓"]],
  ["Lihat audit log", ["–", "–", "–", "✓", "✓"]],
  ["Kelola pengguna, peran & aktivasi NGO", ["–", "–", "–", "–", "✓"]],
];

export function RolePermission() {
  return (
    <div className="space-y-4" data-testid="role-permission">
      <p className="font-head text-2xl font-extrabold text-[#232F3E]">Role & Permission</p>
      <p className="text-sm text-slate-600">Otorisasi ditegakkan di server (API), bukan hanya di tampilan. Pemetaan akun lama: superadmin → Super Admin; verifikator & pimpinan → Admin (*pimpinan hanya-baca, data tersamarkan); petugas & operator → Operator.</p>
      <div className="table-scroll rounded-xl border border-slate-200 bg-white"><table className="w-full min-w-[560px] text-sm"><thead className="bg-[#232F3E] text-white"><tr><th className="p-3 text-left">Izin</th>{["Public", "NGO", "Operator", "Admin", "Super Admin"].map((r) => <th key={r} className="whitespace-nowrap p-3">{r}</th>)}</tr></thead>
        <tbody>{MATRIKS.map(([izin, v]) => <tr key={izin} className="border-t"><td className="p-3">{izin}</td>{v.map((x, i) => <td key={i} className={`p-3 text-center font-bold ${x.startsWith("✓") ? "text-[#117A69]" : "text-slate-400"}`}>{x}</td>)}</tr>)}</tbody></table></div>
      <p className="text-xs text-slate-500">Ubah peran pengguna melalui menu <Link to="/kelola-petugas" className="underline">User Management</Link>. Setiap perubahan peran/status tercatat di audit log.</p>
    </div>
  );
}

export function AuditLog() {
  const { user } = useAuth();
  const [d, setD] = useState<any>(null);
  const [f, setF] = useState<any>({ aksi: "", user: "", page: 1 });
  useEffect(() => {
    const p: any = {}; Object.entries(f).forEach(([k, v]) => { if (v) p[k] = v; });
    api.get("/inklusi/audit-logs", { params: p }).then((r) => setD(r.data)).catch(() => setD(false));
  }, [f]);
  if (d === false) return <p className="text-red-700">Audit log hanya untuk Admin/Super Admin ({user?.role}).</p>;
  return (
    <div className="space-y-4" data-testid="audit-log">
      <p className="font-head text-2xl font-extrabold text-[#232F3E]">Audit Log</p>
      <div className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-3">
        <select aria-label="Aktivitas" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto" value={f.aksi} onChange={(e) => setF({ ...f, aksi: e.target.value, page: 1 })} data-testid="audit-filter-aksi">
          <option value="">Semua aktivitas</option>{["login", "logout", "register_ngo", "create_inquiry", "update_inquiry", "update_status_inquiry", "approve_inquiry", "reject_inquiry", "lihat_data_sensitif", "ubah_status_user", "ubah_peran_user", "import_excel", "rollback_import"].map((a) => <option key={a}>{a}</option>)}</select>
        <input aria-label="Cari pengguna" placeholder="Cari email pengguna…" className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto sm:min-w-[220px]" value={f.user} onChange={(e) => setF({ ...f, user: e.target.value, page: 1 })} />
      </div>
      <div className="table-scroll rounded-xl border border-slate-200 bg-white"><table className="w-full min-w-[900px] text-xs"><thead className="bg-slate-50"><tr>{["Waktu", "Pengguna", "Peran", "Aktivitas", "Resource", "Ref", "Status", "IP / perangkat", "Detail"].map((h) => <th key={h} className={`${th} whitespace-nowrap`}>{h}</th>)}</tr></thead>
        <tbody>{(d?.items || []).map((a: any) => <tr key={a.id || a.created_at} className="border-t align-top" data-testid="audit-row"><td className="p-2 whitespace-nowrap">{new Date(a.created_at).toLocaleString("id-ID")}</td><td className="p-2">{a.user}</td><td className="p-2">{a.role}</td><td className="p-2 font-bold">{a.aksi || a.action}</td><td className="p-2">{a.entitas}</td><td className="p-2">{String(a.ref || "").slice(0, 12)}</td><td className="p-2">{a.status || "sukses"}</td><td className="p-2">{a.ip}<br /><span className="text-slate-400">{String(a.user_agent || "").slice(0, 40)}</span></td><td className="max-w-[260px] p-2 text-slate-600">{String(a.detail || "").slice(0, 160)}</td></tr>)}</tbody></table></div>
      <div className="flex flex-wrap items-center justify-end gap-2 text-sm"><button type="button" disabled={f.page <= 1} onClick={() => setF({ ...f, page: f.page - 1 })} className="min-h-10 rounded border px-3 py-1 disabled:opacity-40 sm:min-h-9">Sebelumnya</button><span>Hal. {f.page}/{d?.pages || 1}</span><button type="button" disabled={f.page >= (d?.pages || 1)} onClick={() => setF({ ...f, page: f.page + 1 })} className="min-h-10 rounded border px-3 py-1 disabled:opacity-40 sm:min-h-9">Berikutnya</button></div>
    </div>
  );
}
