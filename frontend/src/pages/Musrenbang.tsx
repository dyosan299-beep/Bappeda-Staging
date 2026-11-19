import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ChevronDown, ChevronRight, ClipboardList, HandCoins, Loader2, MapPin, Users,
} from "lucide-react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { PageTabs, TabPanel } from "@/components/PageTabs";
import { KpiCard, PageHeader, Panel } from "@/features/data/ui";

/**
 * Musrenbang Tematik RKPD 2027.
 *
 * Dua tab:
 *  - Usulan Tematik: permasalahan, kebutuhan, dan uraian usulan per kelompok
 *    kepentingan (Disabilitas, Lansia, Perempuan, Anak).
 *  - Program & Anggaran: program/kegiatan/sub kegiatan Renja SKPD yang diajukan
 *    untuk tiap usulan, beserta target dan anggarannya.
 *
 * Angka berasal dari berkas resmi yang diimpor admin; halaman ini tidak menghitung
 * atau menambah data sendiri.
 */

const TH = "whitespace-nowrap px-3 py-2 text-left text-[11px] font-bold uppercase tracking-wide text-slate-600";
const TD = "px-3 py-2 align-top text-slate-700";
const TD_NUM = `${TD} whitespace-nowrap text-right font-semibold tabular-nums`;
const INPUT =
  "mt-1 block min-h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm " +
  "font-semibold text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#117A69]";

const angka = (n: any) =>
  n === null || n === undefined || n === "" ? "-" : Number(n).toLocaleString("id-ID");
const rupiah = (n: any) =>
  n === null || n === undefined || n === "" ? "-" : `Rp ${Number(n).toLocaleString("id-ID")}`;
const rupiahRingkas = (n: any) => {
  if (n === null || n === undefined || n === "") return "-";
  const v = Number(n);
  if (Math.abs(v) >= 1e12) return `Rp ${(v / 1e12).toLocaleString("id-ID", { maximumFractionDigits: 2 })} T`;
  if (Math.abs(v) >= 1e9) return `Rp ${(v / 1e9).toLocaleString("id-ID", { maximumFractionDigits: 2 })} M`;
  if (Math.abs(v) >= 1e6) return `Rp ${(v / 1e6).toLocaleString("id-ID", { maximumFractionDigits: 1 })} jt`;
  return rupiah(v);
};
const teks = (v: any) => (v === null || v === undefined || v === "" ? "-" : String(v));
const ringkasTeks = (v: any, maks = 130) => {
  const s = String(v ?? "").replace(/\s+/g, " ").trim();
  if (!s) return "-";
  return s.length > maks ? `${s.slice(0, maks - 1)}…` : s;
};

const TEMA_WARNA: Record<string, string> = {
  DISABILITAS: "#117A69",
  LANSIA: "#8A5A00",
  PEREMPUAN: "#C8375B",
  ANAK: "#3B4F6B",
};

function TabelGulir({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div
      role="region"
      aria-label={label}
      tabIndex={0}
      className="max-w-full overflow-x-auto rounded-md ring-1 ring-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#117A69]"
    >
      {children}
    </div>
  );
}

function BadgeTema({ tema }: { tema: string }) {
  return (
    <span
      className="inline-block rounded-full px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide"
      style={{ backgroundColor: `${TEMA_WARNA[tema] || "#475569"}14`, color: TEMA_WARNA[tema] || "#475569" }}
    >
      {tema || "-"}
    </span>
  );
}

export default function Musrenbang() {
  const [data, setData] = useState<any>(null);
  const [memuat, setMemuat] = useState(true);
  const [galat, setGalat] = useState("");
  const [tab, setTab] = useState("usulan");
  const [tema, setTema] = useState("");
  const [opd, setOpd] = useState("");
  const [q, setQ] = useState("");
  const [buka, setBuka] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    let aktif = true;
    api.get("/musrenbang")
      .then((r) => { if (aktif) setData(r.data); })
      .catch((er: any) => { if (aktif) setGalat(formatApiErrorDetail(er?.response?.data?.detail)); })
      .finally(() => { if (aktif) setMemuat(false); });
    return () => { aktif = false; };
  }, []);

  const ringkas = data?.ringkasan || {};
  const usulanSemua: any[] = Array.isArray(data?.usulan) ? data.usulan : [];
  const intervensiSemua: any[] = Array.isArray(data?.intervensi) ? data.intervensi : [];

  const temaOpsi = useMemo(() => {
    const daftar = (ringkas.per_tema || []).map((t: any) => t.tema).filter(Boolean);
    return daftar.length ? daftar : Array.from(new Set(usulanSemua.map((u) => u.tema)));
  }, [ringkas.per_tema, usulanSemua]);

  const opdOpsi = useMemo(
    () => Array.from(new Set(intervensiSemua.map((i) => i.opd).filter(Boolean))).sort(),
    [intervensiSemua],
  );

  const cari = q.trim().toLowerCase();
  const usulan = useMemo(() => usulanSemua.filter((u) => {
    if (tema && u.tema !== tema) return false;
    if (!cari) return true;
    return [u.permasalahan, u.kebutuhan, u.usulan, u.lokasi, u.opd, u.catatan]
      .some((v) => String(v ?? "").toLowerCase().includes(cari));
  }), [usulanSemua, tema, cari]);

  const intervensi = useMemo(() => intervensiSemua.filter((i) => {
    if (tema && i.tema !== tema) return false;
    if (opd && i.opd !== opd) return false;
    if (!cari) return true;
    return [i.program, i.kegiatan, i.sub_kegiatan, i.target, i.keterangan, i.opd]
      .some((v) => String(v ?? "").toLowerCase().includes(cari));
  }), [intervensiSemua, tema, opd, cari]);

  const alih = (id: string) => setBuka((lama) => {
    const baru = new Set(lama);
    if (baru.has(id)) baru.delete(id);
    else baru.add(id);
    return baru;
  });

  const tabs = useMemo(() => [
    { id: "usulan", label: `Usulan Tematik (${usulanSemua.length})`, icon: ClipboardList },
    { id: "intervensi", label: `Program & Anggaran (${intervensiSemua.length})`, icon: HandCoins },
  ], [usulanSemua.length, intervensiSemua.length]);

  return (
    <div data-testid="musrenbang-page">
      <PageHeader
        title="Musrenbang Tematik"
        subtitle={`Usulan Musrenbang Tematik RKPD ${data?.tahun || 2027} per kelompok kepentingan beserta program dan anggaran yang diajukan OPD.`}
      />

      {galat && (
        <div role="alert" className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {galat}
        </div>
      )}

      {memuat ? (
        <p className="flex items-center gap-2 text-sm text-slate-500" aria-live="polite">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Memuat data Musrenbang…
        </p>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Usulan" value={angka(ringkas.jumlah_usulan)} hint="Usulan warga & OPD" color="#117A69" testid="kpi-musrenbang-usulan" />
            <KpiCard label="Kelompok" value={angka(ringkas.jumlah_tema)} hint="Disabilitas, Lansia, Perempuan, Anak" color="#3B4F6B" testid="kpi-musrenbang-tema" />
            <KpiCard label="Intervensi" value={angka(ringkas.jumlah_intervensi)} hint={`${angka(ringkas.jumlah_opd)} OPD mengisi program`} color="#8A5A00" testid="kpi-musrenbang-intervensi" />
            <KpiCard label="Anggaran Usulan" value={rupiahRingkas(ringkas.total_anggaran)} hint={rupiah(ringkas.total_anggaran)} color="#C8375B" testid="kpi-musrenbang-anggaran" />
          </div>

          <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-3">
            <label className="w-full text-[11px] font-bold uppercase tracking-wide text-slate-600 sm:w-auto sm:min-w-[185px]">
              Kelompok
              <select value={tema} onChange={(e) => setTema(e.target.value)} className={`${INPUT} pr-8`}>
                <option value="">Semua kelompok</option>
                {temaOpsi.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            {tab === "intervensi" && (
              <label className="w-full text-[11px] font-bold uppercase tracking-wide text-slate-600 sm:w-auto sm:min-w-[200px]">
                OPD
                <select value={opd} onChange={(e) => setOpd(e.target.value)} className={`${INPUT} pr-8`}>
                  <option value="">Semua OPD</option>
                  {opdOpsi.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </label>
            )}
            <label className="w-full min-w-0 flex-1 text-[11px] font-bold uppercase tracking-wide text-slate-600 sm:min-w-[240px]">
              Cari
              <input
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Cari permasalahan, usulan, atau program…"
                className={INPUT}
              />
            </label>
            <p className="w-full text-[11px] font-semibold text-slate-500 sm:w-auto sm:pb-3" aria-live="polite">
              {tab === "usulan" ? `${usulan.length} usulan` : `${intervensi.length} intervensi`} ditampilkan
            </p>
          </div>

          <PageTabs tabs={tabs} value={tab} onChange={setTab} label="Bagian Musrenbang" />

          <TabPanel id={tab}>
            {tab === "usulan" ? (
              <Panel
                title={`Usulan Tematik RKPD ${data?.tahun || 2027}`}
                action={<span className="text-[11px] font-semibold text-slate-500">
                  {usulan.length} dari {usulanSemua.length} usulan
                </span>}
                testid="musrenbang-usulan-panel"
              >
                <TabelGulir label="Daftar usulan Musrenbang Tematik">
                  <table className="w-full min-w-[980px] border-collapse text-sm">
                    <caption className="sr-only">
                      Usulan Musrenbang Tematik per kelompok kepentingan beserta permasalahan,
                      lokasi, dan OPD penanggung jawab.
                    </caption>
                    <thead className="bg-slate-50">
                      <tr>
                        <th scope="col" className={TH}><span className="sr-only">Rincian</span></th>
                        <th scope="col" className={TH}>No</th>
                        <th scope="col" className={TH}>Kelompok</th>
                        <th scope="col" className={TH}>Permasalahan Utama</th>
                        <th scope="col" className={TH}>Lokasi</th>
                        <th scope="col" className={TH}>OPD Penanggung Jawab</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usulan.length === 0 ? (
                        <tr><td className={TD} colSpan={6}>Tidak ada usulan yang cocok dengan filter.</td></tr>
                      ) : usulan.map((u) => {
                        const id = `usulan-detail-${u.id}`;
                        const terbuka = buka.has(u.id);
                        return (
                          <React.Fragment key={u.id}>
                            <tr className="border-t border-slate-200">
                              <td className={TD}>
                                <button
                                  type="button"
                                  onClick={() => alih(u.id)}
                                  aria-expanded={terbuka}
                                  aria-controls={id}
                                  aria-label={`Rincian usulan nomor ${u.no}`}
                                  className="inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#117A69] sm:h-9 sm:w-9"
                                >
                                  {terbuka
                                    ? <ChevronDown className="h-4 w-4" aria-hidden="true" />
                                    : <ChevronRight className="h-4 w-4" aria-hidden="true" />}
                                </button>
                              </td>
                              <td className={`${TD} font-semibold text-slate-900`}>{u.no}</td>
                              <td className={TD}><BadgeTema tema={u.tema} /></td>
                              <td className={TD}>{ringkasTeks(u.permasalahan)}</td>
                              <td className={TD}>{ringkasTeks(u.lokasi, 70)}</td>
                              <td className={TD}>{ringkasTeks(u.opd, 90)}</td>
                            </tr>
                            {terbuka && (
                              <tr id={id} className="border-t border-slate-200 bg-slate-50">
                                <td colSpan={6} className="px-3 py-3">
                                  <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
                                    <div>
                                      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Permasalahan Utama</dt>
                                      <dd className="whitespace-pre-line text-sm text-slate-800">{teks(u.permasalahan)}</dd>
                                    </div>
                                    <div>
                                      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Kebutuhan</dt>
                                      <dd className="whitespace-pre-line text-sm text-slate-800">{teks(u.kebutuhan)}</dd>
                                    </div>
                                    <div className="sm:col-span-2">
                                      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Usulan Kegiatan</dt>
                                      <dd className="whitespace-pre-line text-sm text-slate-800">{teks(u.usulan)}</dd>
                                    </div>
                                    <div>
                                      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Lokasi</dt>
                                      <dd className="text-sm text-slate-800">{teks(u.lokasi)}</dd>
                                    </div>
                                    <div>
                                      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">OPD Penanggung Jawab</dt>
                                      <dd className="text-sm text-slate-800">{teks(u.opd)}</dd>
                                    </div>
                                    <div className="sm:col-span-2">
                                      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Catatan OPD</dt>
                                      <dd className="whitespace-pre-line text-sm text-slate-800">{teks(u.catatan)}</dd>
                                    </div>
                                  </dl>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </TabelGulir>
                <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-relaxed text-slate-500">
                  <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  Usulan berasal dari Musrenbang Tematik per kelompok kepentingan. Nama pengusul
                  tidak ditampilkan; hanya usulan dan lokasinya.
                </p>
              </Panel>
            ) : (
              <Panel
                title="Program, Kegiatan, dan Anggaran Usulan"
                action={<span className="text-[11px] font-semibold text-slate-500">
                  {intervensi.length} dari {intervensiSemua.length} intervensi
                </span>}
                testid="musrenbang-intervensi-panel"
              >
                <TabelGulir label="Program dan anggaran usulan Musrenbang Tematik">
                  <table className="w-full min-w-[1120px] border-collapse text-sm">
                    <caption className="sr-only">
                      Program, kegiatan, sub kegiatan, target, dan anggaran yang diajukan OPD untuk
                      usulan Musrenbang Tematik.
                    </caption>
                    <thead className="bg-slate-50">
                      <tr>
                        <th scope="col" className={TH}>No</th>
                        <th scope="col" className={TH}>Kelompok</th>
                        <th scope="col" className={TH}>OPD</th>
                        <th scope="col" className={TH}>Program</th>
                        <th scope="col" className={TH}>Kegiatan</th>
                        <th scope="col" className={TH}>Sub Kegiatan</th>
                        <th scope="col" className={TH}>Target</th>
                        <th scope="col" className={`${TH} text-right`}>Anggaran</th>
                      </tr>
                    </thead>
                    <tbody>
                      {intervensi.length === 0 ? (
                        <tr><td className={TD} colSpan={8}>Belum ada program yang cocok dengan filter.</td></tr>
                      ) : intervensi.map((i) => (
                        <tr key={i.id} className="border-t border-slate-200">
                          <td className={`${TD} font-semibold text-slate-900`}>{i.no}</td>
                          <td className={TD}><BadgeTema tema={i.tema} /></td>
                          <td className={`${TD} font-semibold text-slate-900`}>{teks(i.opd)}</td>
                          <td className={TD}>{ringkasTeks(i.program, 80)}</td>
                          <td className={TD}>{ringkasTeks(i.kegiatan, 80)}</td>
                          <td className={TD}>{ringkasTeks(i.sub_kegiatan, 90)}</td>
                          <td className={TD}>{teks(i.target)}</td>
                          <td className={TD_NUM}>{rupiah(i.anggaran)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TabelGulir>
                <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-relaxed text-slate-500">
                  <Users className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  Anggaran di sini adalah <strong>usulan</strong> Renja SKPD, bukan realisasi.
                  Hanya OPD yang mengisi kolom program pada berkas Musrenbang yang tampil di tab ini.
                </p>
              </Panel>
            )}
          </TabPanel>
        </div>
      )}
    </div>
  );
}
