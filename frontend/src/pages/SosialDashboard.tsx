import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { Users, Home, Droplets, ShieldAlert, MapPin, Building2 } from "lucide-react";
import { KpiCard, Panel, PageHeader, RISK_COLORS, RISK_LABELS, CHART_COLORS } from "@/features/data/ui";
import ExportButtons from "@/features/data/ExportButtons";
import {
  fmtNum, getKelurahan, getRanking, getSosialOverview, getWilayahSummary,
} from "@/features/data/api";

const SEMUA = "semua";

export default function SosialDashboard() {
  const [wilayah, setWilayah] = useState<any>(null);
  const [kelurahanList, setKelurahanList] = useState<any[]>([]);
  const [kec, setKec] = useState(SEMUA);
  const [kel, setKel] = useState(SEMUA);
  const [desil, setDesil] = useState(SEMUA);
  const [pbi, setPbi] = useState(SEMUA);
  const [ov, setOv] = useState<any>(null);
  const [ranking, setRanking] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getWilayahSummary().then(setWilayah).catch(() => toast.error("Gagal memuat data wilayah"));
  }, []);

  useEffect(() => {
    getKelurahan(kec === SEMUA ? undefined : kec).then((r) => setKelurahanList(r.items || []));
    setKel(SEMUA);
  }, [kec]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const filter: any = {
        kode_kecamatan: kec === SEMUA ? undefined : kec,
        kode_kelurahan: kel === SEMUA ? undefined : kel,
        desil: desil === SEMUA ? undefined : desil,
      };
      if (pbi === "nas") filter.pbi_nas = 1;
      if (pbi === "pemda") filter.pbi_pemda = 1;
      const [o, r] = await Promise.all([
        getSosialOverview(filter),
        getRanking(kel === SEMUA && kec === SEMUA ? "kecamatan" : "kelurahan",
          "skor_prioritas", kec === SEMUA ? undefined : kec, 12),
      ]);
      setOv(o);
      setRanking(r);
    } catch {
      toast.error("Gagal memuat data sosial");
    } finally {
      setLoading(false);
    }
  }, [kec, kel, desil, pbi]);

  useEffect(() => { load(); }, [load]);

  const desilData = useMemo(() => {
    const per = ov?.per_desil || {};
    return Object.keys(per)
      .filter((k) => k !== "-")
      .sort()
      .map((k) => ({ desil: `Desil ${k}`, jumlah: per[k] }));
  }, [ov]);

  const riskData = useMemo(
    () => (ov?.per_risk_urut || []).map((r: any) => ({
      name: RISK_LABELS[r.level] || r.level, value: r.jumlah, level: r.level,
    })),
    [ov],
  );

  return (
    <div data-testid="page-sosial-dashboard">
      <PageHeader
        title="Dashboard Data Sosial (DTSEN)"
        subtitle={`Sumber: data DTSEN per kelurahan · ${fmtNum(wilayah?.total_households)} rumah tangga terdata`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ExportButtons jalur="kelurahan" testid="sosial-export"
              filter={{ kode_kecamatan: kec === SEMUA ? undefined : kec }} />
            <Link to="/peta-sosial" className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              <MapPin className="h-4 w-4" /> Lihat Peta Sosial
            </Link>
          </div>
        }
      />

      {/* Filter terhubung */}
      <div className="mb-4 flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <select data-testid="filter-kecamatan" value={kec} onChange={(e) => setKec(e.target.value)}
          className="h-9 rounded-md border border-slate-300 px-2 text-sm">
          <option value={SEMUA}>Semua Kecamatan</option>
          {wilayah?.kecamatan?.map((k: any) => (
            <option key={k.kode} value={k.kode}>{k.nama}</option>
          ))}
        </select>
        <select data-testid="filter-kelurahan" value={kel} onChange={(e) => setKel(e.target.value)}
          className="h-9 rounded-md border border-slate-300 px-2 text-sm">
          <option value={SEMUA}>Semua Kelurahan</option>
          {kelurahanList.map((k) => (
            <option key={k.kode} value={k.kode}>{k.nama}</option>
          ))}
        </select>
        <select data-testid="filter-desil" value={desil} onChange={(e) => setDesil(e.target.value)}
          className="h-9 rounded-md border border-slate-300 px-2 text-sm">
          <option value={SEMUA}>Semua Desil</option>
          {[1, 2, 3, 4, 5].map((d) => <option key={d} value={d}>Desil {d}</option>)}
        </select>
        <select data-testid="filter-pbi" value={pbi} onChange={(e) => setPbi(e.target.value)}
          className="h-9 rounded-md border border-slate-300 px-2 text-sm">
          <option value={SEMUA}>Semua Status PBI</option>
          <option value="nas">PBI Nasional</option>
          <option value="pemda">PBI Pemda</option>
        </select>
        <span className="ml-auto text-xs text-slate-500">
          {loading ? "Memuat…" : `Sumber perhitungan: ${ov?.sumber === "agregat" ? "agregat wilayah" : "data detail"}`}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard testid="kpi-households" label="Rumah Tangga" value={fmtNum(ov?.total_households)}
          icon={<Home className="h-4 w-4 text-slate-400" />} />
        <KpiCard testid="kpi-individu" label="Individu (jiwa)" value={fmtNum(ov?.total_individu)}
          icon={<Users className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="Kecamatan" value={fmtNum(ov?.jumlah_kecamatan)}
          icon={<Building2 className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="Kelurahan" value={fmtNum(ov?.jumlah_kelurahan)}
          icon={<MapPin className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="PBI Nasional" value={fmtNum(ov?.pbi_nas)} color="#0891b2" />
        <KpiCard label="PBI Pemda" value={fmtNum(ov?.pbi_pemda)} color="#4f46e5" />
        <KpiCard label="Desil 1-2" value={fmtNum(ov?.desil_1_2)}
          hint={`${ov?.persen_desil_1_2 ?? 0}% dari total KK`} color="#b91c1c" />
        <KpiCard testid="kpi-rumah-rentan" label="Rumah Kondisi Rentan" value={fmtNum(ov?.rumah_rentan)}
          hint={`${ov?.persen_rumah_rentan ?? 0}% dari total KK`} color="#dc2626"
          icon={<ShieldAlert className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="Sanitasi Tidak Layak" value={fmtNum(ov?.sanitasi_tidak_layak)} color="#ea580c" />
        <KpiCard label="Air Minum Rentan" value={fmtNum(ov?.air_rentan)} color="#0891b2"
          icon={<Droplets className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="Hunian Rentan" value={fmtNum(ov?.hunian_rentan)} color="#f59e0b" />
        <KpiCard label="Skor Kerentanan Rata-rata" value={ov?.avg_risk ?? 0}
          hint="skala 0-100 (semakin tinggi semakin rentan)" color="#9333ea" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="Distribusi Rumah Tangga per Desil Nasional" testid="chart-desil">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={desilData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="desil" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip formatter={(v: any) => fmtNum(v)} />
              <Bar dataKey="jumlah" radius={[4, 4, 0, 0]}>
                {desilData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Kategori Prioritas Kerentanan Sosial" testid="chart-risk">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={riskData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={95}
                paddingAngle={2}>
                {riskData.map((r: any, i: number) => (
                  <Cell key={i} fill={RISK_COLORS[r.level] || CHART_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: any) => fmtNum(v)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      <Panel title={`Ranking Wilayah Prioritas (${ranking?.level || "-"})`} className="mt-4"
        testid="tabel-ranking"
        action={<Link to="/prioritas" className="text-xs font-semibold text-primary hover:underline">Lihat analisis prioritas →</Link>}>
        <div className="table-scroll">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Wilayah</th>
                <th className="px-3 py-2">Rumah Tangga</th>
                <th className="px-3 py-2">Jiwa</th>
                <th className="px-3 py-2">Desil 1-2</th>
                <th className="px-3 py-2">Rumah Rentan</th>
                <th className="px-3 py-2">Disabilitas</th>
                <th className="px-3 py-2">Skor Kerentanan</th>
                <th className="px-3 py-2">Skor Prioritas</th>
              </tr>
            </thead>
            <tbody>
              {(ranking?.items || []).map((r: any) => (
                <tr key={r.kode} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2 font-semibold text-slate-800">
                    {r.nama}
                    {ranking?.level === "kelurahan" && (
                      <span className="ml-1 text-[11px] font-normal text-slate-500">({r.kecamatan})</span>
                    )}
                  </td>
                  <td className="px-3 py-2">{fmtNum(r.total_households)}</td>
                  <td className="px-3 py-2">{fmtNum(r.total_individu)}</td>
                  <td className="px-3 py-2">{fmtNum(r.desil_1_2)}</td>
                  <td className="px-3 py-2">{fmtNum(r.rumah_rentan)}</td>
                  <td className="px-3 py-2">{fmtNum(r.disabilitas)}</td>
                  <td className="px-3 py-2">{r.avg_risk}</td>
                  <td className="px-3 py-2 font-bold text-red-700">{r.skor_prioritas ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
