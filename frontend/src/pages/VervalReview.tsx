import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, MapPin, ShieldCheck, X } from "lucide-react";
import { api, errMsg, fmtWaktu, fotoUrl, GPS_LABEL, HUBUNGAN_LABEL, KESESUAIAN_LABEL, KESIMPULAN_LABEL, KONDISI_RIIL_LABEL } from "@/features/verval/api";
import { Card, DtsenNilai, Field, INPUT, StatusBadge, UjiBadge } from "@/features/verval/ui";
import { BTN_PRIMARY, BTN_SM, FR } from "@/features/a11y/ui";
import { FotoKoordinat } from "@/pages/VervalOperator";

/** Hasil Verval GeoTag — pemeriksaan oleh Verifikator (kecamatannya) / Admin Bappeda / Superadmin;
 *  Pimpinan hanya melihat (read-only). Semua ditegakkan di backend. */
export default function VervalReview() {
  const [params, setParams] = useSearchParams();
  const [status, setStatus] = useState("terkirim");
  const [list, setList] = useState<any>(null);
  const [cfg, setCfg] = useState<any>(null);
  const openId = params.get("id");

  const load = useCallback(() => {
    api.get("/verval/records", { params: { status: status || undefined, size: 100 } })
      .then((r) => setList(r.data)).catch((e) => { toast.error(errMsg(e)); setList({ items: [] }); });
  }, [status]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.get("/verval/konfigurasi").then((r) => setCfg(r.data)).catch(() => {}); }, []);

  return (
    <div className="space-y-4" data-testid="verval-review-page">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="font-head text-lg font-extrabold text-slate-900"><ShieldCheck className="mr-1 inline h-5 w-5 text-[#117A69]" />{cfg?.dapat_review ? "Pemeriksaan Hasil Verval GeoTag" : "Hasil Verval GeoTag"}</p>
            <p className="text-xs text-slate-600">
              {cfg?.dapat_review ? "Keputusan Anda tidak mengubah data sumber DTSEN. Koreksi data DTSEN tetap melalui alur pembaruan data yang berlaku." : "Anda melihat hasil Verval lapangan (foto, koordinat, kesimpulan) tanpa mengambil keputusan."}
              {cfg?.scope_kecamatan && <span className="ml-1 rounded-full bg-[#117A69]/10 px-2 py-0.5 text-[11px] font-bold text-[#0f5f52]" data-testid="review-scope">Kec. {cfg.scope_kecamatan}</span>}
            </p>
          </div>
          <select className={`${INPUT} max-w-[220px]`} value={status} onChange={(e) => setStatus(e.target.value)} data-testid="review-filter-status">
            <option value="">Semua (selain draft)</option>
            {["terkirim", "perlu_perbaikan", "disetujui", "ditolak"].map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        {!list ? <p className="mt-4 text-sm"><Loader2 className="inline h-4 w-4 animate-spin" /> Memuat…</p> : (
          <div className="table-scroll mt-3 overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-xs" data-testid="review-table">
              <thead className="bg-slate-50 text-[11px] uppercase text-slate-600"><tr><th className="p-2">Wilayah</th><th className="p-2">Petugas</th><th className="p-2">Foto</th><th className="p-2">GPS</th><th className="p-2">Dikirim</th><th className="p-2">Status</th><th className="p-2" /></tr></thead>
              <tbody>
                {list.items.map((r: any) => (
                  <tr key={r.id} className="border-t border-slate-100" data-testid="review-row">
                    <td className="p-2">{r.kelurahan}, {r.kecamatan} · RW {r.rw || "-"}/RT {r.rt || "-"} <UjiBadge show={r.data_uji} /></td>
                    <td className="p-2">{r.operator_nama || r.operator_email}</td>
                    <td className="p-2">{r.foto_count}</td>
                    <td className="p-2">{GPS_LABEL[r.status_gps] || "-"}</td>
                    <td className="p-2">{fmtWaktu(r.submitted_at)}</td>
                    <td className="p-2"><StatusBadge status={r.status} /></td>
                    <td className="p-2"><button type="button" className={BTN_SM} onClick={() => setParams({ id: r.id })} data-testid="review-open">{cfg?.dapat_review && r.status === "terkirim" ? "Periksa" : "Lihat"}</button></td>
                  </tr>
                ))}
                {!list.items.length && <tr><td colSpan={7} className="p-6 text-center text-slate-500">Tidak ada data.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {openId && <ReviewDetail id={openId} cfg={cfg} onClose={() => { setParams({}); load(); }} />}
    </div>
  );
}

function ReviewDetail({ id, cfg, onClose }: any) {
  const [r, setR] = useState<any>(null);
  const [keputusan, setKeputusan] = useState("disetujui");
  const [catatan, setCatatan] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { api.get(`/verval/records/${id}`).then((x) => setR(x.data)).catch((e) => setErr(errMsg(e))); }, [id]);

  const putus = async () => {
    setBusy(true);
    try { const x = await api.post(`/verval/records/${id}/review`, { keputusan, catatan }); setR(x.data); toast.success("Keputusan tersimpan"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[600] flex justify-end bg-slate-900/40" role="dialog" aria-modal="true" aria-label="Detail Verval">
      <div className="h-full w-full max-w-2xl overflow-y-auto bg-slate-50 p-4" data-testid="review-detail">
        <div className="mb-3 flex items-center justify-between"><h2 className="font-head text-base font-extrabold">Detail Verval</h2>
          <button type="button" onClick={onClose} className={`rounded-full p-2 hover:bg-slate-200 ${FR}`} aria-label="Tutup" data-testid="review-close"><X className="h-5 w-5" /></button></div>
        {err && <p className="rounded bg-rose-50 p-2 text-xs text-rose-800">{err}</p>}
        {!r ? !err && <Loader2 className="h-5 w-5 animate-spin" /> : (
          <div className="space-y-3">
            <Card>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-bold" data-testid="review-identitas">{r.sasaran?.kepala_keluarga || "(relasi DTSEN tidak ditemukan)"} <UjiBadge show={r.data_uji} /></p>
                  {r.sasaran && <p className="text-xs text-slate-600">No. KK {r.sasaran.no_kk} · {r.sasaran.alamat} · {r.kelurahan}, {r.kecamatan} · RW {r.rw || "-"}/RT {r.rt || "-"}</p>}
                  {r.catatan_relasi && <p className="text-xs text-amber-800">{r.catatan_relasi}</p>}
                  <p className="text-[11px] text-slate-500">Petugas: {r.operator_nama} ({r.operator_email}) · tanda terima {r.tanda_terima || "-"}</p>
                </div>
                <StatusBadge status={r.status} testid="review-status" />
              </div>
            </Card>
            <Card>
              <h3 className="text-xs font-bold uppercase text-slate-500">Lokasi GPS</h3>
              <p className="mt-1 text-xs" data-testid="review-gps"><MapPin className="mr-1 inline h-3.5 w-3.5" />{r.gps?.lat != null ? `${r.gps.lat.toFixed(6)}, ${r.gps.lng.toFixed(6)}${r.gps.akurasi_m != null ? ` · ±${r.gps.akurasi_m} m` : ""}` : "tidak ada koordinat"} · <b>{GPS_LABEL[r.gps?.status_gps] || "-"}</b> (batas {r.gps?.batas_akurasi_m ?? cfg?.gps_max_akurasi_m} m){r.gps?.sumber?.startsWith("foto") && <span className="ml-1 text-slate-500">· dari koordinat foto</span>}</p>
              {r.alasan_tanpa_gps && <p className="text-xs text-amber-800">Alasan tanpa GPS: {r.alasan_tanpa_gps}</p>}
              <p className="mt-1 text-[11px] text-slate-500">Posisi perangkat saat pemeriksaan; bukan bukti lokasi rumah terverifikasi.</p>
            </Card>
            <Card>
              <h3 className="text-xs font-bold uppercase text-slate-500">Foto ({r.foto?.length || 0})</h3>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid="review-foto">
                {(r.foto || []).map((f: any) => (
                  <a key={f.id} href={fotoUrl(f.id)} target="_blank" rel="noreferrer" className="overflow-hidden rounded-[10px] ring-1 ring-slate-200">
                    <img src={fotoUrl(f.id)} alt={`Foto ${f.jenis}`} className="h-28 w-full object-cover" />
                    <span className="block bg-white px-2 py-1 text-[10px]">{f.jenis.replace(/_/g, " ")} · {fmtWaktu(f.diterima_at)}<FotoKoordinat gps={f.gps_saat_foto} /></span>
                  </a>
                ))}
              </div>
            </Card>
            <Card>
              <h3 className="text-xs font-bold uppercase text-slate-500">II. Variabel Sosial Ekonomi (11)</h3>
              <p className="text-[11px] text-amber-800">{cfg?.indikator_sumber}</p>
              <div className="table-scroll mt-2 overflow-x-auto">
              <table className="w-full min-w-[420px] text-xs" data-testid="review-indikator"><tbody>
                {(cfg?.indikator || []).map((i: any) => {
                  const v = r.indikator?.[i.key] || {};
                  const beda = (v.kesesuaian === "beda" || v.kondisi_riil === "beda"
                                || v.kesesuaian === "rtlh" || v.kondisi_riil === "tidak_layak"
                                || v.kesesuaian === "babs" || v.kondisi_riil === "babs"
                                || v.kesesuaian === "non_aktif" || v.kondisi_riil === "non_aktif"
                                || v.kesesuaian === "graduasi" || v.kondisi_riil === "graduasi");
                  return (
                    <tr key={i.key} className="border-t border-slate-100 align-top">
                      <td className="py-1.5 pr-2 font-semibold">
                        {i.label}
                        <span className="ml-1 rounded bg-slate-100 px-1 py-0.5 text-[10px] font-normal text-slate-500">{i.opd}</span>
                      </td>
                      <td className="py-1.5 pr-2"><DtsenNilai vals={r.dtsen?.[i.key]} /></td>
                      <td className={`py-1.5 font-bold ${beda ? "text-rose-700" : "text-emerald-700"}`}>
                        {v.kesesuaian ? KESESUAIAN_LABEL[v.kesesuaian] || v.kesesuaian : "—"}
                        <span className="mx-1 text-slate-400">/</span>
                        {v.kondisi_riil ? KONDISI_RIIL_LABEL[v.kondisi_riil] || v.kondisi_riil : "—"}
                        {v.catatan ? <span className="block font-normal text-slate-600">{v.catatan}</span> : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody></table>
              </div>
            </Card>
            <Card>
              <h3 className="text-xs font-bold uppercase text-slate-500">III. Penapisan Individu Rentan ({(r.anggota_rentan || []).length})</h3>
              {(r.anggota_rentan || []).length === 0 ? (
                <p className="mt-2 text-xs text-slate-500">Tidak ada anggota rentan tercatat.</p>
              ) : (
                <ul className="mt-2 space-y-2 text-xs" data-testid="review-anggota-rentan">
                  {r.anggota_rentan.map((a: any) => (
                    <li key={a.id} className="rounded-[10px] bg-slate-50 p-2">
                      <p className="font-bold">{a.nama || "(tanpa nama)"} <span className="text-slate-500 font-normal">· {HUBUNGAN_LABEL[a.status_hubungan] || a.status_hubungan || "—"}</span></p>
                      {a.nik && <p className="text-[11px] text-slate-500">NIK: {a.nik}</p>}
                      {(a.kondisi_rentan || []).length > 0 && (
                        <p className="mt-0.5">Kondisi: <b>{a.kondisi_rentan.join(", ")}</b></p>
                      )}
                      {a.rekomendasi_opd && <p className="text-[11px] text-slate-600">Rekomendasi: {a.rekomendasi_opd}</p>}
                      {a.catatan && <p className="text-[11px] text-slate-600">{a.catatan}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card>
              <h3 className="text-xs font-bold uppercase text-slate-500">IV. Kesimpulan Verval</h3>
              <p className="mt-1 text-sm font-bold text-[#117A69]" data-testid="review-kesimpulan">
                {r.kesimpulan?.pilihan ? KESIMPULAN_LABEL[r.kesimpulan.pilihan] || r.kesimpulan.pilihan : "Belum ditetapkan"}
              </p>
              {r.kesimpulan?.catatan && <p className="mt-1 text-xs text-slate-600">{r.kesimpulan.catatan}</p>}
              {r.catatan_umum && <p className="mt-2 text-xs">Catatan umum: {r.catatan_umum}</p>}
            </Card>
            {r.status === "terkirim" && cfg?.dapat_review ? (
              <Card data-testid="review-form">
                <h3 className="text-sm font-bold">Keputusan pemeriksaan</h3>
                <div className="mt-2 grid grid-cols-3 gap-1">
                  {[["disetujui", "Setujui"], ["perlu_perbaikan", "Perlu perbaikan"], ["ditolak", "Tolak"]].map(([k, l]) => (
                    <button key={k} type="button" aria-pressed={keputusan === k} onClick={() => setKeputusan(k)} data-testid={`review-keputusan-${k}`}
                      className={`min-h-10 rounded-[10px] text-xs font-bold ${FR} ${keputusan === k ? "bg-[#232F3E] text-white" : "bg-white ring-1 ring-slate-200"}`}>{l}</button>
                  ))}
                </div>
                <div className="mt-2"><Field label={`Catatan${keputusan !== "disetujui" ? " (wajib)" : ""}`}><textarea className={INPUT} rows={3} value={catatan} onChange={(e) => setCatatan(e.target.value)} data-testid="review-catatan" /></Field></div>
                <button type="button" className={`${BTN_PRIMARY} mt-3 w-full`} onClick={putus} disabled={busy} data-testid="review-submit">{busy && <Loader2 className="h-4 w-4 animate-spin" />}Simpan keputusan</button>
              </Card>
            ) : r.review_catatan && <Card><p className="text-xs">Catatan pemeriksa ({r.reviewed_by}, {fmtWaktu(r.reviewed_at)}): {r.review_catatan}</p></Card>}
            <Card>
              <h3 className="text-xs font-bold uppercase text-slate-500">Riwayat</h3>
              <ol className="mt-1 space-y-1 text-xs" data-testid="review-riwayat">{(r.riwayat || []).map((h: any) => <li key={h.id}>{fmtWaktu(h.waktu)} · <b>{h.aksi}</b> {h.dari_status ? `${h.dari_status} → ` : ""}{h.ke_status} · {h.oleh}{h.catatan ? ` · ${h.catatan}` : ""}</li>)}</ol>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
