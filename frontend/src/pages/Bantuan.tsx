import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { HandHeart } from "lucide-react";
import { fetchFilters, fetchRumahList, fetchStats } from "@/features/peta/api";
import { STATUS_COLORS } from "@/features/peta/basemaps";
import { RumahFilters, RumahProps, RumahStats } from "@/features/peta/types";

const SEMUA = "semua";

export default function Bantuan() {
  const [stats, setStats] = useState<RumahStats | null>(null);
  const [filters, setFilters] = useState<RumahFilters | null>(null);
  const [items, setItems] = useState<RumahProps[]>([]);
  const [kel, setKel] = useState(SEMUA);
  const [jenis, setJenis] = useState(SEMUA);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [st, list] = await Promise.all([
        fetchStats({ kelurahan: kel }),
        fetchRumahList({ kelurahan: kel }),
      ]);
      setStats(st);
      setItems(list.items || []);
    } catch {
      toast.error("Gagal memuat data bantuan");
    } finally {
      setLoading(false);
    }
  }, [kel]);

  useEffect(() => {
    fetchFilters().then(setFilters).catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const penerima = useMemo(
    () =>
      items.filter(
        (r) =>
          r.bantuan && r.bantuan !== "-" && (jenis === SEMUA || r.bantuan === jenis),
      ),
    [items, jenis],
  );

  const jenisList = useMemo(
    () => Object.keys(stats?.per_bantuan || {}).filter((k) => k !== "-").sort(),
    [stats],
  );

  const totalPenerima = useMemo(
    () =>
      Object.entries(stats?.per_bantuan || {})
        .filter(([k]) => k !== "-")
        .reduce((a, [, v]) => a + v, 0),
    [stats],
  );

  return (
    <div className="space-y-4" data-testid="page-bantuan">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 font-head text-xl font-extrabold text-slate-900">
            <HandHeart className="h-5 w-5 text-primary" /> Bantuan Sosial
          </p>
          <p className="text-xs text-slate-500">
            Rekap penerima bantuan berdasarkan data rumah hasil survei lapangan
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <select
            data-testid="bantuan-filter-kelurahan"
            aria-label="Filter kelurahan"
            value={kel}
            onChange={(e) => setKel(e.target.value)}
            className="h-10 min-w-0 max-w-full flex-1 rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:flex-none"
          >
            <option value={SEMUA}>Semua Kelurahan</option>
            {filters?.kelurahan?.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
          <select
            data-testid="bantuan-filter-jenis"
            aria-label="Filter jenis bantuan"
            value={jenis}
            onChange={(e) => setJenis(e.target.value)}
            className="h-10 min-w-0 max-w-full flex-1 rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:flex-none"
          >
            <option value={SEMUA}>Semua Jenis</option>
            {jenisList.map((j) => (
              <option key={j} value={j}>{j}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-5">
        <div className="col-span-2 rounded-lg border border-slate-200 bg-white p-3 md:col-span-1">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            Total Penerima
          </p>
          <p className="mt-1 text-2xl font-extrabold tabular-nums text-slate-900">{totalPenerima}</p>
          <p className="text-[11px] text-slate-500">dari {stats?.total ?? 0} rumah terdata</p>
        </div>
        {jenisList.map((j) => (
          <div key={j} className="rounded-lg border border-slate-200 bg-white p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{j}</p>
            <p className="mt-1 text-2xl font-extrabold tabular-nums text-primary">
              {stats?.per_bantuan?.[j] ?? 0}
            </p>
            <p className="text-[11px] text-slate-500">keluarga penerima</p>
          </div>
        ))}
      </div>

      <div className="table-scroll rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[740px] text-sm" data-testid="tabel-bantuan">
          <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="whitespace-nowrap px-3 py-2">Kode</th>
              <th className="px-3 py-2">Penerima</th>
              <th className="whitespace-nowrap px-3 py-2">Jiwa</th>
              <th className="whitespace-nowrap px-3 py-2">RT/RW</th>
              <th className="px-3 py-2">Kelurahan</th>
              <th className="whitespace-nowrap px-3 py-2">Penghasilan</th>
              <th className="whitespace-nowrap px-3 py-2">Bantuan</th>
              <th className="whitespace-nowrap px-3 py-2">Kondisi</th>
            </tr>
          </thead>
          <tbody>
            {penerima.map((r) => (
              <tr key={String(r.id)} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-[11px] text-slate-500">{r.kode}</td>
                <td className="px-3 py-2 font-semibold text-slate-800">{r.pemilik}</td>
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">{r.jumlah_orang}</td>
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">{r.rt || "-"}/{r.rw || "-"}</td>
                <td className="px-3 py-2">{r.kelurahan}</td>
                <td className="whitespace-nowrap px-3 py-2">{r.penghasilan || "-"}</td>
                <td className="whitespace-nowrap px-3 py-2">
                  <span className="inline-block whitespace-nowrap rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                    {r.bantuan}
                  </span>
                </td>
                <td className="whitespace-nowrap px-3 py-2">
                  <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-[11px] font-semibold text-slate-700">
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: STATUS_COLORS[String(r.status)] }}
                    />
                    {r.kondisi || "-"}
                  </span>
                </td>
              </tr>
            ))}
            {!loading && penerima.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-sm text-slate-500">
                  Tidak ada penerima bantuan pada filter ini.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
