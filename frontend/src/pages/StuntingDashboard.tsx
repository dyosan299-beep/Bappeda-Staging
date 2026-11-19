import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { Search, Building2, Wallet, Target } from "lucide-react";
import { KpiCard, Panel, PageHeader } from "@/features/data/ui";
import { fmtNum, fmtRp, getStuntingItems, getStuntingOverview } from "@/features/data/api";

export default function StuntingDashboard() {
  const [ov, setOv] = useState<any>(null);
  const [items, setItems] = useState<any>(null);
  const [opd, setOpd] = useState("semua");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    getStuntingOverview().then(setOv).catch(() => toast.error("Gagal memuat data stunting"));
  }, []);

  const load = useCallback(() => {
    getStuntingItems({ opd: opd === "semua" ? undefined : opd, search: search || undefined, page, size: 20 })
      .then(setItems)
      .catch(() => toast.error("Gagal memuat daftar kegiatan"));
  }, [opd, search, page]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(1); }, [opd, search]);

  const chart = (ov?.per_opd || []).slice(0, 10).map((o: any) => ({
    opd: o.opd?.length > 22 ? `${o.opd.slice(0, 22)}…` : o.opd,
    "2025": o.anggaran_2025, "2026": o.anggaran_2026,
  }));

  return (
    <div data-testid="page-stunting">
      <PageHeader title="Dashboard Program Stunting 2025-2027"
        subtitle="Sumber: Matriks Kegiatan Stunting Tahun 2025, 2026 & 2027" />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard testid="kpi-opd" label="OPD Terlibat" value={fmtNum(ov?.jumlah_opd)}
          icon={<Building2 className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="Program" value={fmtNum(ov?.jumlah_program)} />
        <KpiCard label="Kegiatan" value={fmtNum(ov?.jumlah_kegiatan)} />
        <KpiCard label="Sub Kegiatan" value={fmtNum(ov?.jumlah_sub_kegiatan)} />
        <KpiCard testid="kpi-anggaran-2025" label="Anggaran 2025" value={fmtRp(ov?.anggaran_2025)}
          color="#0891b2" icon={<Wallet className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="Anggaran 2026" value={fmtRp(ov?.anggaran_2026)} color="#4f46e5"
          hint={`Selisih ${fmtRp(ov?.selisih_anggaran)}`} />
        <KpiCard label="Target 2027 terisi" value={fmtNum(ov?.jumlah_target_2027)} color="#16a34a"
          icon={<Target className="h-4 w-4 text-slate-400" />} />
      </div>

      <Panel title="Perbandingan Anggaran per OPD (2025 vs 2026)" className="mt-4" testid="chart-stunting-opd">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chart} margin={{ bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="opd" fontSize={10} angle={-30} textAnchor="end" interval={0} height={70} />
            <YAxis fontSize={10} tickFormatter={(v) => fmtRp(v)} />
            <Tooltip formatter={(v: any) => fmtRp(v)} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="2025" fill="#0891b2" radius={[3, 3, 0, 0]} />
            <Bar dataKey="2026" fill="#4f46e5" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Panel>

      <Panel title="Daftar Sub Kegiatan" className="mt-4" testid="tabel-stunting"
        action={
          <div className="flex w-full flex-wrap gap-2 sm:w-auto">
            <select value={opd} onChange={(e) => setOpd(e.target.value)} data-testid="stunting-opd" aria-label="Filter OPD"
              className="h-10 w-full min-w-0 max-w-full rounded-md border border-slate-300 px-2 text-xs sm:h-9 sm:w-auto sm:max-w-xs">
              <option value="semua">Semua OPD</option>
              {(items?.opd_list || []).map((o: string) => <option key={o} value={o}>{o}</option>)}
            </select>
            <div className="relative w-full min-w-0 sm:w-auto">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" aria-hidden="true" />
              <input value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Cari program, kegiatan, atau indikator"
                placeholder="Cari program / kegiatan / indikator" data-testid="stunting-search"
                className="h-10 w-full rounded-md border border-slate-300 pl-8 pr-2 text-xs sm:h-9 sm:w-64" />
            </div>
          </div>
        }>
        <div className="table-scroll">
          <table className="w-full min-w-[840px] text-sm">
            <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">OPD</th>
                <th className="px-3 py-2">Program</th>
                <th className="px-3 py-2">Kegiatan</th>
                <th className="px-3 py-2">Sub Kegiatan</th>
                <th className="px-3 py-2">Indikator</th>
                <th className="px-3 py-2 text-right">2025</th>
                <th className="px-3 py-2 text-right">2026</th>
                <th className="px-3 py-2">Target 2027</th>
              </tr>
            </thead>
            <tbody>
              {(items?.items || []).map((s: any) => (
                <tr key={s.id} className="border-t border-slate-100 align-top hover:bg-slate-50">
                  <td className="px-3 py-2 font-semibold text-slate-800">{s.opd}</td>
                  <td className="px-3 py-2 text-[11.5px]">{s.program}</td>
                  <td className="px-3 py-2 text-[11.5px]">{s.kegiatan}</td>
                  <td className="px-3 py-2 text-[11.5px]">{s.nama}</td>
                  <td className="px-3 py-2 text-[11.5px] text-slate-600">{s.indikator || "-"}</td>
                  <td className="px-3 py-2 text-right">{fmtRp(s.anggaran_2025)}</td>
                  <td className="px-3 py-2 text-right">{fmtRp(s.anggaran_2026)}</td>
                  <td className="px-3 py-2 text-[11.5px]">{s.target_2027 ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
          <span>{fmtNum(items?.total)} sub kegiatan · halaman {items?.page} dari {items?.pages}</span>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={(items?.page || 1) <= 1} onClick={() => setPage((p) => p - 1)}
              className="min-h-10 rounded-md border border-slate-300 px-3 font-semibold disabled:opacity-40 sm:min-h-9">Sebelumnya</button>
            <button type="button" disabled={(items?.page || 1) >= (items?.pages || 1)}
              onClick={() => setPage((p) => p + 1)}
              className="min-h-10 rounded-md border border-slate-300 px-3 font-semibold disabled:opacity-40 sm:min-h-9">Berikutnya</button>
          </div>
        </div>
      </Panel>
    </div>
  );
}
