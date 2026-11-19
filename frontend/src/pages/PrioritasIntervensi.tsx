import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Target, Building2 } from "lucide-react";
import { PageHeader, Panel } from "@/features/data/ui";
import { fmtNum, fmtRp, getPrioritas, getWilayahSummary } from "@/features/data/api";

export default function PrioritasIntervensi() {
  const [data, setData] = useState<any>(null);
  const [wilayah, setWilayah] = useState<any>(null);
  const [kec, setKec] = useState("semua");
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(true);

  useEffect(() => { getWilayahSummary().then(setWilayah).catch(() => {}); }, []);

  useEffect(() => {
    setLoading(true);
    getPrioritas(limit, kec === "semua" ? undefined : kec)
      .then(setData)
      .catch(() => toast.error("Gagal memuat analisis prioritas"))
      .finally(() => setLoading(false));
  }, [kec, limit]);

  return (
    <div data-testid="page-prioritas">
      <PageHeader
        title="Wilayah Prioritas Intervensi"
        subtitle="Integrasi data sosial (DTSEN) + disabilitas + program stunting + RAD disabilitas"
        actions={
          <div className="flex w-full flex-wrap gap-2 sm:w-auto">
            <select value={kec} onChange={(e) => setKec(e.target.value)} data-testid="prioritas-kecamatan" aria-label="Filter kecamatan"
              className="h-10 min-w-0 flex-1 rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:flex-none">
              <option value="semua">Semua Kecamatan</option>
              {wilayah?.kecamatan?.map((k: any) => <option key={k.kode} value={k.kode}>{k.nama}</option>)}
            </select>
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))} aria-label="Jumlah wilayah ditampilkan"
              className="h-10 min-w-0 flex-1 rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:flex-none">
              {[5, 10, 20, 29].map((n) => <option key={n} value={n}>{n} wilayah teratas</option>)}
            </select>
          </div>
        }
      />
      {loading && <p className="text-sm text-slate-500">Memuat analisis…</p>}
      <div className="space-y-4">
        {(data?.items || []).map((it: any, idx: number) => (
          <Panel key={it.kode_kelurahan} testid={`prioritas-${idx}`}
            title={`${idx + 1}. ${it.kelurahan} — Kec. ${it.kecamatan}`}
            action={
              <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-700">
                Skor prioritas {it.skor_prioritas}
              </span>
            }>
            <div className="grid gap-4 lg:grid-cols-3">
              <div>
                <p className="mb-1 flex items-center gap-1.5 text-xs font-bold uppercase text-slate-600">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-600" /> Permasalahan utama
                </p>
                <ul className="list-inside list-disc text-xs text-slate-700">
                  {(it.masalah_utama || []).map((m: string, i: number) => <li key={i}>{m}</li>)}
                </ul>
                <div className="mt-2 grid grid-cols-2 gap-1 text-[11px]">
                  <span className="text-slate-500">Rumah tangga</span><b>{fmtNum(it.total_households)}</b>
                  <span className="text-slate-500">Jiwa</span><b>{fmtNum(it.total_individu)}</b>
                  <span className="text-slate-500">KK prioritas tinggi</span><b>{fmtNum(it.populasi_terdampak)}</b>
                  <span className="text-slate-500">Disabilitas</span><b>{fmtNum(it.disabilitas)}</b>
                  <span className="text-slate-500">Skor kerentanan</span><b>{it.avg_risk}</b>
                </div>
              </div>
              <div>
                <p className="mb-1 flex items-center gap-1.5 text-xs font-bold uppercase text-slate-600">
                  <Target className="h-3.5 w-3.5 text-emerald-600" /> Rekomendasi tindak lanjut
                </p>
                <ul className="list-inside list-disc text-xs text-slate-700">
                  {(it.rekomendasi || []).map((m: string, i: number) => <li key={i}>{m}</li>)}
                </ul>
              </div>
              <div>
                <p className="mb-1 flex items-center gap-1.5 text-xs font-bold uppercase text-slate-600">
                  <Building2 className="h-3.5 w-3.5 text-indigo-600" /> Program OPD relevan
                </p>
                <p className="text-[11px] font-semibold text-slate-500">Stunting</p>
                <ul className="mb-2 space-y-1">
                  {(it.program_relevan?.stunting || []).map((p: any, i: number) => (
                    <li key={i} className="rounded border border-slate-200 p-1.5 text-[11px]">
                      <b>{p.opd}</b> · {p.sub_kegiatan}
                      <span className="block text-slate-500">2025 {fmtRp(p.anggaran_2025)} · 2026 {fmtRp(p.anggaran_2026)}</span>
                    </li>
                  ))}
                  {!(it.program_relevan?.stunting || []).length && (
                    <li className="text-[11px] text-slate-400">Tidak ada program cocok</li>
                  )}
                </ul>
                <p className="text-[11px] font-semibold text-slate-500">RAD Disabilitas</p>
                <ul className="space-y-1">
                  {(it.program_relevan?.rad_disabilitas || []).map((p: any, i: number) => (
                    <li key={i} className="rounded border border-slate-200 p-1.5 text-[11px]">
                      {p.program || "-"}<span className="block text-slate-500">{p.kegiatan}</span>
                    </li>
                  ))}
                  {!(it.program_relevan?.rad_disabilitas || []).length && (
                    <li className="text-[11px] text-slate-400">Tidak ada program cocok</li>
                  )}
                </ul>
              </div>
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
