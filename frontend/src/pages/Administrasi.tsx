import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Database, FileSpreadsheet, ShieldCheck, AlertTriangle } from "lucide-react";
import { KpiCard, Panel, PageHeader } from "@/features/data/ui";
import {
  fmtNum, getImportBatches, getImportSummary, getQualityIssues, getQualitySummary,
} from "@/features/data/api";

export default function Administrasi() {
  const [sum, setSum] = useState<any>(null);
  const [batches, setBatches] = useState<any>(null);
  const [qs, setQs] = useState<any>(null);
  const [issues, setIssues] = useState<any>(null);
  const [jenis, setJenis] = useState("semua");
  const [page, setPage] = useState(1);

  useEffect(() => {
    Promise.all([getImportSummary(), getImportBatches(), getQualitySummary()])
      .then(([s, b, q]) => { setSum(s); setBatches(b); setQs(q); })
      .catch(() => toast.error("Gagal memuat data administrasi"));
  }, []);

  useEffect(() => {
    getQualityIssues({ jenis: jenis === "semua" ? undefined : jenis, page, size: 25 })
      .then(setIssues)
      .catch(() => {});
  }, [jenis, page]);

  const c = sum?.counts || {};

  return (
    <div data-testid="page-administrasi">
      <PageHeader title="Administrasi Data: Impor & Kualitas Data"
        subtitle="Riwayat impor (audit), ringkasan basis data, dan temuan kualitas data" />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard testid="kpi-households" label="Rumah Tangga" value={fmtNum(c.households)}
          icon={<Database className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="Individu Terdata" value={fmtNum(c.household_members)} />
        <KpiCard label="Kelurahan (data)" value={fmtNum(c.villages)} hint={`${fmtNum(c.geo_kelurahan)} batas wilayah GIS`} />
        <KpiCard label="Kecamatan" value={fmtNum(c.districts)} />
        <KpiCard label="Sub Kegiatan Stunting" value={fmtNum(c.stunting_subactivities)} color="#0891b2" />
        <KpiCard label="Item RAD" value={fmtNum(c.rad_items)} color="#9333ea" />
        <KpiCard label="Rekap Disabilitas Wilayah" value={fmtNum(c.disability_region_stats)} />
        <KpiCard label="Laporan Disabilitas SKPD" value={fmtNum(c.disability_opd_stats)} />
        <KpiCard label="Baris Mentah (audit)" value={fmtNum(c.raw_imports)}
          icon={<FileSpreadsheet className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="Berkas Diproses" value={fmtNum(sum?.total_file)} />
        <KpiCard label="Master OPD" value={fmtNum(c.opd)} />
        <KpiCard testid="kpi-issues" label="Temuan Kualitas Data" value={fmtNum(qs?.total)} color="#dc2626"
          icon={<AlertTriangle className="h-4 w-4 text-slate-400" />} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="Ringkasan Impor per Jenis Data" testid="tabel-import-jenis">
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Ringkasan impor per jenis data">
          <table className="w-full min-w-[420px] text-sm">
            <thead className="bg-slate-50 text-left text-[11px] uppercase text-slate-500">
              <tr>
                <th className="px-2 py-2">Jenis</th><th className="px-2 py-2">Berkas</th>
                <th className="px-2 py-2">Baris</th><th className="px-2 py-2">Masuk</th>
                <th className="px-2 py-2">Duplikat</th><th className="px-2 py-2">Gagal</th>
              </tr>
            </thead>
            <tbody>
              {(sum?.per_jenis || []).map((j: any) => (
                <tr key={j.jenis} className="border-t border-slate-100">
                  <td className="px-2 py-2 font-semibold">{j.jenis}</td>
                  <td className="px-2 py-2">{fmtNum(j.file)}</td>
                  <td className="px-2 py-2">{fmtNum(j.total_rows)}</td>
                  <td className="px-2 py-2 text-emerald-700">{fmtNum(j.inserted)}</td>
                  <td className="px-2 py-2 text-amber-700">{fmtNum(j.duplicate)}</td>
                  <td className="px-2 py-2 text-red-700">{fmtNum(j.failed)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </Panel>

        <Panel title="Temuan Kualitas Data per Jenis" testid="quality-summary">
          <ul className="space-y-1 text-sm">
            {(qs?.per_jenis || []).map((q: any) => (
              <li key={q.jenis} className="flex items-center justify-between gap-3 rounded border border-slate-200 px-3 py-2">
                <span className="min-w-0 break-words font-semibold text-slate-700">{q.jenis.replace(/_/g, " ")}</span>
                <span className="font-bold">{fmtNum(q.jumlah)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 flex items-start gap-1.5 text-[11px] text-slate-500">
            <ShieldCheck className="mt-0.5 h-3.5 w-3.5" />
            Baris duplikat tidak dihapus dari berkas sumber — hanya tidak dimuat dua kali ke basis
            data, dan semuanya tercatat di sini untuk ditinjau.
          </p>
        </Panel>
      </div>

      <Panel title="Riwayat Impor (Audit)" className="mt-4" testid="tabel-batches">
        <div className="table-scroll max-h-80 overflow-y-auto" tabIndex={0} role="region" aria-label="Ringkasan basis data">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="sticky top-0 bg-slate-50 text-left text-[11px] uppercase text-slate-500">
              <tr>
                <th className="whitespace-nowrap px-2 py-2">Berkas</th><th className="whitespace-nowrap px-2 py-2">Sheet</th>
                <th className="whitespace-nowrap px-2 py-2">Jenis</th><th className="whitespace-nowrap px-2 py-2">Baris</th>
                <th className="whitespace-nowrap px-2 py-2">Masuk</th><th className="whitespace-nowrap px-2 py-2">Duplikat</th>
                <th className="whitespace-nowrap px-2 py-2">Gagal</th><th className="whitespace-nowrap px-2 py-2">Waktu</th>
              </tr>
            </thead>
            <tbody>
              {(batches?.items || []).map((b: any) => (
                <tr key={b.id} className="border-t border-slate-100">
                  <td className="px-2 py-2 text-[11.5px]">{b.filename}</td>
                  <td className="px-2 py-2 text-[11.5px]">{b.sheet}</td>
                  <td className="px-2 py-2 text-[11.5px]">{b.jenis}</td>
                  <td className="px-2 py-2">{fmtNum(b.total_rows)}</td>
                  <td className="px-2 py-2 text-emerald-700">{fmtNum(b.inserted)}</td>
                  <td className="px-2 py-2 text-amber-700">{fmtNum(b.duplicate)}</td>
                  <td className="px-2 py-2 text-red-700">{fmtNum(b.failed)}</td>
                  <td className="px-2 py-2 text-[11px] text-slate-500">
                    {String(b.uploaded_at || "").slice(0, 19).replace("T", " ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Daftar Temuan Kualitas Data" className="mt-4" testid="tabel-issues"
        action={
          <select value={jenis} onChange={(e) => { setJenis(e.target.value); setPage(1); }}
            aria-label="Filter jenis temuan kualitas data"
            data-testid="quality-filter" className="h-9 rounded-md border border-slate-300 px-2 text-xs">
            <option value="semua">Semua Jenis</option>
            {(qs?.per_jenis || []).map((q: any) => (
              <option key={q.jenis} value={q.jenis}>{q.jenis.replace(/_/g, " ")}</option>
            ))}
          </select>
        }>
        <div className="table-scroll">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-slate-50 text-left text-[11px] uppercase text-slate-500">
              <tr>
                <th className="whitespace-nowrap px-2 py-2">Jenis</th><th className="whitespace-nowrap px-2 py-2">Entitas</th>
                <th className="px-2 py-2">Keterangan</th><th className="whitespace-nowrap px-2 py-2">Referensi</th>
              </tr>
            </thead>
            <tbody>
              {(issues?.items || []).map((i: any) => (
                <tr key={i.id} className="border-t border-slate-100">
                  <td className="px-2 py-2 text-[11.5px] font-semibold">{i.jenis?.replace(/_/g, " ")}</td>
                  <td className="px-2 py-2 text-[11.5px]">{i.entitas}</td>
                  <td className="px-2 py-2 text-[11.5px] text-slate-600">{i.keterangan}</td>
                  <td className="px-2 py-2 font-mono text-[10.5px] text-slate-500">{i.ref || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
          <span>{fmtNum(issues?.total)} temuan · halaman {issues?.page} dari {fmtNum(issues?.pages)}</span>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={(issues?.page || 1) <= 1} onClick={() => setPage((p) => p - 1)}
              className="min-h-10 rounded-md border border-slate-300 px-3 font-semibold disabled:opacity-40 sm:min-h-9">Sebelumnya</button>
            <button type="button" disabled={(issues?.page || 1) >= (issues?.pages || 1)}
              onClick={() => setPage((p) => p + 1)}
              className="min-h-10 rounded-md border border-slate-300 px-3 font-semibold disabled:opacity-40 sm:min-h-9">Berikutnya</button>
          </div>
        </div>
      </Panel>
    </div>
  );
}
