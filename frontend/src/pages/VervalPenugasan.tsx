import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Loader2, RefreshCw, UserCheck } from "lucide-react";
import { api, errMsg, fmtWaktu } from "@/features/verval/api";
import { Card, Field, INPUT, UjiBadge } from "@/features/verval/ui";
import { BTN_PRIMARY, BTN_SM, BTN_SM_PRIMARY } from "@/features/a11y/ui";

/** Penugasan wilayah RT/RW & penetapan KK sasaran — Kecamatan / Admin Bappeda / Superadmin. */
export default function VervalPenugasan() {
  const [cfg, setCfg] = useState<any>(null);
  const [ops, setOps] = useState<any[]>([]);
  const [wil, setWil] = useState<any[]>([]);
  const [wilLoaded, setWilLoaded] = useState(false);
  const [data, setData] = useState<any>({ penugasan: [], sasaran: [] });
  const [f, setF] = useState<any>({ user_id: "", kode_kelurahan: "", rw: "", rt: [], lintas_wilayah: false, dasar_penugasan: "", berlaku_mulai: "", berlaku_sampai: "" });
  const [rtManual, setRtManual] = useState("");
  const [cari, setCari] = useState({ kode_kelurahan: "", search: "" });
  const [hh, setHh] = useState<any>(null);
  const [sas, setSas] = useState<any>({ user_id: "", dasar_penugasan: "", berlaku_sampai: "" });

  const load = useCallback(() => {
    api.get("/verval/penugasan").then((r) => setData(r.data)).catch((e) => toast.error(errMsg(e)));
  }, []);
  useEffect(() => {
    api.get("/verval/konfigurasi").then((r) => setCfg(r.data)).catch(() => {});
    api.get("/verval/operator").then((r) => setOps(r.data.items)).catch(() => {});
    api.get("/verval/wilayah-dtsen").then((r) => setWil(r.data.items)).catch(() => {}).finally(() => setWilLoaded(true));
    load();
  }, [load]);

  const kel = useMemo(() => wil.find((w) => w.kode_kelurahan === f.kode_kelurahan), [wil, f.kode_kelurahan]);
  const rwItem = kel?.rw?.find((x: any) => x.rw === f.rw);

  const simpan = async (e: any) => {
    e.preventDefault();
    try {
      await api.post("/verval/penugasan", { ...f, berlaku_mulai: f.berlaku_mulai || null, berlaku_sampai: f.berlaku_sampai || null });
      toast.success("Penugasan disimpan"); setRtManual(""); load();
    } catch (er) { toast.error(errMsg(er)); }
  };
  const cabut = async (jenis: "penugasan" | "sasaran-kk", id: string) => {
    const alasan = window.prompt("Alasan pencabutan (wajib):");
    if (!alasan) return;
    try { await api.post(`/verval/${jenis}/${id}/cabut`, { alasan }); toast.success("Dicabut"); load(); } catch (er) { toast.error(errMsg(er)); }
  };
  const cariKK = async () => {
    try {
      const r = await api.get("/sosial/households", { params: { kode_kelurahan: cari.kode_kelurahan || undefined, search: cari.search || undefined, size: 25 } });
      setHh(r.data);
    } catch (er) { toast.error(errMsg(er)); }
  };
  const tetapkan = async (household_id: string) => {
    if (!sas.user_id) { toast.error("Pilih operator terlebih dahulu"); return; }
    try {
      const r = await api.post("/verval/sasaran-kk", { ...sas, household_id, berlaku_sampai: sas.berlaku_sampai || null });
      toast.success(r.data.lintas_wilayah ? "KK sasaran lintas wilayah ditetapkan" : "KK sasaran ditetapkan"); load();
    } catch (er) { toast.error(errMsg(er)); }
  };
  const opName = (id: string) => ops.find((o) => o.id === id)?.email || id;

  return (
    <div className="space-y-4" data-testid="verval-penugasan-page">
      <Card>
        <p className="font-head text-lg font-extrabold">
          <UserCheck className="mr-1 inline h-5 w-5 text-[#117A69]" />
          Penugasan Operator RT/RW — GeoTag Verval
          {cfg?.scope_kecamatan && (
            <span className="ml-2 rounded-full bg-[#117A69]/10 px-2.5 py-0.5 text-xs font-bold text-[#0f5f52]" data-testid="penugasan-scope">
              Kec. {cfg.scope_kecamatan}
            </span>
          )}
        </p>
        <p className="text-xs text-slate-600">Penugasan memberi hak Verval &amp; GeoTag kepada petugas wilayah. Selama kolom RT/RW DTSEN masih kosong, petugas tetap dapat mencari sasaran sesuai kelurahan penugasannya.</p>
        {cfg && (
          <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3" data-testid="verval-status-konfigurasi">
            <p className={`rounded p-2 ${cfg.modul_siap ? "bg-emerald-50" : "bg-rose-50"}`}>Referensi DTSEN stabil: <b>{cfg.modul_siap ? "aktif" : "VERVAL_REF_SECRET belum diatur"}</b></p>
            <p className={`rounded p-2 ${cfg.penyimpanan?.dapat_ditulis ? "bg-emerald-50" : "bg-rose-50"}`}>Penyimpanan foto: <b>{cfg.penyimpanan?.pesan}</b></p>
            <p className="flex items-center justify-between rounded bg-slate-50 p-2">KK tanpa ref: <b>{cfg.households_tanpa_ref}</b>
              <button type="button" className={BTN_SM} onClick={() => api.post("/verval/sinkron-referensi").then((r) => toast.success(`${r.data.diisi} referensi diisi`)).catch((e) => toast.error(errMsg(e)))} data-testid="verval-sinkron-ref"><RefreshCw className="h-3.5 w-3.5" /></button></p>
          </div>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="text-sm font-bold">1. Penugasan wilayah RT/RW</h2>
          <p className="text-[11px] text-slate-500">Daftar RW/RT otomatis diambil dari kolom RT/RW DTSEN; jika masih kosong di DTSEN, nomor RW/RT dapat diketik manual.</p>
          <form className="mt-3 grid gap-2 sm:grid-cols-2" onSubmit={simpan}>
            <Field label="Operator RT/RW"><select required className={INPUT} value={f.user_id} onChange={(e) => setF({ ...f, user_id: e.target.value })} data-testid="pen-operator">
              <option value="">Pilih…</option>{ops.map((o) => <option key={o.id} value={o.id}>{o.name} ({o.email})</option>)}</select></Field>
            <Field label="Kelurahan (DTSEN)"><select required className={INPUT} value={f.kode_kelurahan} onChange={(e) => { setF({ ...f, kode_kelurahan: e.target.value, rw: "", rt: [] }); setRtManual(""); }} data-testid="pen-kelurahan">
              <option value="">{!wilLoaded ? "Memuat…" : "Pilih…"}</option>{wil.map((w) => <option key={w.kode_kelurahan} value={w.kode_kelurahan}>{w.kelurahan} — {w.kecamatan} ({w.kk_dengan_rt_rw}/{w.total_kk} KK ber-RT/RW)</option>)}</select></Field>
            <Field label="RW">
              {kel && (!kel.rw || kel.rw.length === 0) ? (
                <input required className={INPUT} placeholder="cth. 01" value={f.rw} onChange={(e) => setF({ ...f, rw: e.target.value })} data-testid="pen-rw" />
              ) : (
                <select required className={INPUT} value={f.rw} onChange={(e) => setF({ ...f, rw: e.target.value, rt: [] })} data-testid="pen-rw">
                  <option value="">Pilih…</option>{(kel?.rw || []).map((x: any) => <option key={x.rw} value={x.rw}>RW {x.rw}</option>)}
                </select>
              )}
            </Field>
            <Field label="RT (kosong = seluruh RT)">
              {kel && (!kel.rw || kel.rw.length === 0) ? (
                <div data-testid="pen-rt">
                  <input className={INPUT} placeholder="cth. 01, 02 (kosong = seluruh RT)" value={rtManual}
                    onChange={(e) => { const v = e.target.value; setRtManual(v); setF({ ...f, rt: v.split(/[,\s]+/).map((x: string) => x.trim()).filter(Boolean) }); }} />
                </div>
              ) : (
                <div className="flex flex-wrap gap-2 pt-1" data-testid="pen-rt">
                  {(rwItem?.rt || []).map((rt: string) => (
                    <label key={rt} className="flex items-center gap-1 text-xs"><input type="checkbox" checked={f.rt.includes(rt)} onChange={(e) => setF({ ...f, rt: e.target.checked ? [...f.rt, rt] : f.rt.filter((x: string) => x !== rt) })} />RT {rt}</label>
                  ))}{!rwItem && <span className="text-[11px] text-slate-400">pilih RW</span>}
                </div>
              )}
            </Field>
            <Field label="Berlaku mulai"><input type="date" className={INPUT} value={f.berlaku_mulai} onChange={(e) => setF({ ...f, berlaku_mulai: e.target.value })} /></Field>
            <Field label="Berlaku sampai"><input type="date" className={INPUT} value={f.berlaku_sampai} onChange={(e) => setF({ ...f, berlaku_sampai: e.target.value })} data-testid="pen-sampai" /></Field>
            <label className="flex items-center gap-2 text-xs sm:col-span-2"><input type="checkbox" checked={f.lintas_wilayah} onChange={(e) => setF({ ...f, lintas_wilayah: e.target.checked })} data-testid="pen-lintas" />Penugasan lintas wilayah (wajib dasar penugasan & tanggal berakhir)</label>
            <div className="sm:col-span-2"><Field label="Dasar penugasan (mis. nomor SK)"><input className={INPUT} value={f.dasar_penugasan} onChange={(e) => setF({ ...f, dasar_penugasan: e.target.value })} data-testid="pen-dasar" /></Field></div>
            <button className={`${BTN_PRIMARY} sm:col-span-2`} data-testid="pen-simpan">Simpan penugasan</button>
          </form>
        </Card>

        <Card>
          <h2 className="text-sm font-bold">2. Tetapkan KK sasaran</h2>
          <p className="text-[11px] text-slate-500">Untuk KK tanpa RT/RW pada data DTSEN, atau penugasan khusus. KK di luar kelurahan penugasan operator tercatat sebagai lintas wilayah.</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Field label="Operator"><select className={INPUT} value={sas.user_id} onChange={(e) => setSas({ ...sas, user_id: e.target.value })} data-testid="sas-operator">
              <option value="">Pilih…</option>{ops.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select></Field>
            <Field label="Dasar penugasan"><input className={INPUT} placeholder="Wajib bila lintas wilayah" value={sas.dasar_penugasan} onChange={(e) => setSas({ ...sas, dasar_penugasan: e.target.value })} data-testid="sas-dasar" /></Field>
            <Field label="Kelurahan"><select className={INPUT} value={cari.kode_kelurahan} onChange={(e) => setCari({ ...cari, kode_kelurahan: e.target.value })} data-testid="sas-kelurahan">
              <option value="">{!wilLoaded ? "Memuat…" : "Semua"}</option>{wil.map((w) => <option key={w.kode_kelurahan} value={w.kode_kelurahan}>{w.kelurahan}</option>)}</select></Field>
            <Field label="Cari nama / No. KK"><div className="flex gap-1"><input className={INPUT} value={cari.search} onChange={(e) => setCari({ ...cari, search: e.target.value })} data-testid="sas-search" />
              <button type="button" className={BTN_SM_PRIMARY} onClick={cariKK} data-testid="sas-cari">Cari</button></div></Field>
          </div>
          {hh && (
            <ul className="mt-3 max-h-64 divide-y divide-slate-100 overflow-auto text-xs" data-testid="sas-hasil">
              {hh.items.map((h: any) => (
                <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span className="min-w-0 flex-1 break-words">{h.kepala_keluarga} · {h.no_kk} · {h.kelurahan} · RW {h.rw || "-"}/RT {h.rt || "-"} <UjiBadge show={h.data_uji} /></span>
                  <button type="button" className={`${BTN_SM} shrink-0`} onClick={() => tetapkan(h.id)} data-testid="sas-tetapkan">Tetapkan</button>
                </li>
              ))}
              {!hh.items.length && <li className="py-3 text-slate-500">Tidak ditemukan.</li>}
            </ul>
          )}
        </Card>
      </div>

      <Card>
        <h2 className="text-sm font-bold">Daftar penugasan & KK sasaran</h2>
        {!data ? <Loader2 className="h-4 w-4 animate-spin" /> : (
          <div className="table-scroll mt-2 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-xs" data-testid="pen-table">
              <thead className="bg-slate-50 text-[11px] uppercase text-slate-600"><tr><th className="p-2">Jenis</th><th className="p-2">Operator</th><th className="p-2">Cakupan</th><th className="p-2">Dasar / berlaku</th><th className="p-2">Status</th><th className="p-2" /></tr></thead>
              <tbody>
                {data.penugasan.map((p: any) => (
                  <tr key={p.id} className="border-t border-slate-100"><td className="p-2">RT/RW{p.lintas_wilayah ? " · lintas" : ""}</td><td className="p-2">{p.operator_email}</td>
                    <td className="p-2">{p.kelurahan} · RW {p.rw} · RT {p.rt?.length ? p.rt.join(", ") : "semua"}</td><td className="p-2">{p.dasar_penugasan || "-"} · {p.berlaku_sampai || "tanpa batas"}</td>
                    <td className="p-2">{p.status}</td><td className="p-2">{p.status === "aktif" && <button type="button" className={BTN_SM} onClick={() => cabut("penugasan", p.id)} data-testid="pen-cabut">Cabut</button>}</td></tr>
                ))}
                {data.sasaran.map((s: any) => (
                  <tr key={s.id} className="border-t border-slate-100"><td className="p-2">KK sasaran{s.lintas_wilayah ? " · lintas" : ""}</td><td className="p-2">{s.operator_email || opName(s.user_id)}</td>
                    <td className="p-2">{s.kelurahan} · KK {s.no_kk_tersamar}</td><td className="p-2">{s.dasar_penugasan || "-"} · {fmtWaktu(s.created_at)}</td>
                    <td className="p-2">{s.status}</td><td className="p-2">{s.status === "aktif" && <button type="button" className={BTN_SM} onClick={() => cabut("sasaran-kk", s.id)} data-testid="sas-cabut">Cabut</button>}</td></tr>
                ))}
                {!data.penugasan.length && !data.sasaran.length && <tr><td colSpan={6} className="p-4 text-center text-slate-500">Belum ada penugasan.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
