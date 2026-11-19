import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { Accessibility, Info, Pencil, Trash2 } from "lucide-react";
import { KpiCard, Panel, PageHeader, CHART_COLORS } from "@/features/data/ui";
import { fmtNum, getDisabilitas } from "@/features/data/api";
import {
  createDisabilitas, deleteDisabilitas, getDisabilitasItems, updateDisabilitas,
} from "@/features/data/manageApi";
import DynamicForm from "@/features/data/DynamicForm";
import ExportButtons from "@/features/data/ExportButtons";
import { InputDataButton, KonfirmasiHapus } from "@/features/data/InputDataButton";
import { ChartA11y } from "@/features/a11y/components";
import { useAuth } from "@/context/AuthContext";
import { bolehHapus as cekHapus, bolehTulis as cekTulis } from "@/features/data/roles";

export default function DisabilitasDashboard() {
  const { user } = useAuth();
  const bolehTulis = cekTulis(user?.role);
  const bolehHapus = cekHapus(user?.role);
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [rekap, setRekap] = useState<any>(null);
  const [form, setForm] = useState<{ id: string | null; data: any } | null>(null);
  const [hapus, setHapus] = useState<any>(null);

  const muatRekap = useCallback(() => {
    getDisabilitasItems({ size: 200 }).then(setRekap).catch(() => {});
  }, []);

  const muat = useCallback(() => {
    setLoading(true);
    getDisabilitas()
      .then(setD)
      .catch(() => toast.error("Gagal memuat data disabilitas"))
      .finally(() => setLoading(false));
    muatRekap();
  }, [muatRekap]);

  useEffect(() => { muat(); }, [muat]);

  return (
    <div data-testid="page-disabilitas-dashboard">
      <PageHeader title="Dashboard Penyandang Disabilitas"
        subtitle="Rekap wilayah (Kec. Tallo & Kec. Makassar) + laporan ragam disabilitas Dinkes"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ExportButtons jalur="disabilitas" testid="dis-export" />
            {bolehTulis && (
              <InputDataButton jenis="disabilitas" testid="btn-input-disabilitas"
                onManual={() => setForm({ id: null, data: {} })} />
            )}
          </div>
        } />

      <div className="mb-3 flex items-start gap-2 rounded-lg border border-sky-200 bg-sky-50 p-3 text-[11.5px] text-sky-900">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{d?.catatan || "Memuat catatan sumber data…"} Data individu dilindungi dan hanya dapat diakses peran berwenang.</span>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard testid="kpi-dis-total" label="Total (rekap wilayah)" value={fmtNum(d?.total_wilayah)}
          icon={<Accessibility className="h-4 w-4 text-slate-400" />} />
        <KpiCard label="Total (laporan SKPD)" value={fmtNum(d?.total_laporan_opd)} color="#4f46e5" />
        <KpiCard label="Laki-laki" value={fmtNum(d?.gender?.laki_laki)} color="#0891b2" />
        <KpiCard label="Perempuan" value={fmtNum(d?.gender?.perempuan)} color="#db2777" />
        <KpiCard label="Usia < 18 tahun" value={fmtNum(d?.usia?.dibawah_18)} color="#f59e0b" />
        <KpiCard label="Usia 18-59 tahun" value={fmtNum(d?.usia?.usia_18_59)} color="#16a34a" />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-7"
        data-testid="kpi-ragam-disabilitas">
        <KpiCard label="Usia 60+ tahun" value={fmtNum(d?.usia?.usia_60_keatas)} color="#7c3aed" />
        {(d?.ragam || []).map((r: any, i: number) => (
          <KpiCard key={r.nama} label={r.nama} value={fmtNum(r.jumlah)}
            color={CHART_COLORS[i % CHART_COLORS.length]} />
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="Ragam Disabilitas" testid="chart-ragam">
          <ChartA11y
            judul="Ragam Disabilitas"
            ringkasan={`Sebaran ${fmtNum(d?.ragam?.length || 0)} ragam disabilitas pada data wilayah.`}
            kolom={["Ragam disabilitas", "Jumlah"]}
            baris={(d?.ragam || []).map((r: any) => [r.nama, r.jumlah])}
            testid="chart-ragam"
          >
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={d?.ragam || []} dataKey="jumlah" nameKey="nama" cx="50%" cy="45%"
                  innerRadius={45} outerRadius={90} isAnimationActive={false}>
                  {(d?.ragam || []).map((_: any, i: number) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: any) => fmtNum(v)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </ChartA11y>
        </Panel>
        <Panel title="Distribusi per Kelurahan (10 tertinggi)" testid="chart-dis-kelurahan">
          <ChartA11y
            judul="Distribusi per Kelurahan"
            ringkasan="Sepuluh kelurahan dengan jumlah penyandang disabilitas tertinggi."
            kolom={["Kelurahan", "Jumlah"]}
            baris={(d?.per_kelurahan || []).slice(0, 10).map((k: any) => [k.kelurahan, k.jumlah])}
            testid="chart-dis-kelurahan"
          >
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={(d?.per_kelurahan || []).slice(0, 10)} layout="vertical"
                margin={{ left: 8, right: 12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" fontSize={12} />
                <YAxis type="category" dataKey="kelurahan" fontSize={11} width={96} />
                <Tooltip formatter={(v: any) => fmtNum(v)} />
                <Bar dataKey="jumlah" fill="#4f46e5" radius={[0, 4, 4, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </ChartA11y>
        </Panel>
      </div>

      <Panel title="Rekap Data Disabilitas per Kelurahan" className="mt-4"
        testid="tabel-dis-kelurahan"
        action={<span className="text-[11px] text-slate-500">{fmtNum(rekap?.total)} baris data</span>}>
        <div className="table-scroll">
          <table className="w-full min-w-[780px] text-sm">
            <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Kecamatan</th>
                <th className="px-3 py-2">Kelurahan</th>
                <th className="px-3 py-2">Tahun</th>
                <th className="px-3 py-2">L</th>
                <th className="px-3 py-2">P</th>
                <th className="px-3 py-2">&lt;18</th>
                <th className="px-3 py-2">18-59</th>
                <th className="px-3 py-2">60+</th>
                <th className="px-3 py-2">Total</th>
                {bolehTulis && <th className="px-3 py-2">Aksi</th>}
              </tr>
            </thead>
            <tbody>
              {(rekap?.items || []).map((r: any) => (
                <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2">{r.kecamatan}</td>
                  <td className="px-3 py-2 font-semibold text-slate-800">{r.kelurahan || "-"}</td>
                  <td className="px-3 py-2">{r.tahun}</td>
                  <td className="px-3 py-2">{fmtNum(r.laki_laki)}</td>
                  <td className="px-3 py-2">{fmtNum(r.perempuan)}</td>
                  <td className="px-3 py-2">{fmtNum(r.usia_dibawah_18)}</td>
                  <td className="px-3 py-2">{fmtNum(r.usia_18_59)}</td>
                  <td className="px-3 py-2">{fmtNum(r.usia_60_keatas)}</td>
                  <td className="px-3 py-2 font-bold">{fmtNum(r.jumlah || r.total)}</td>
                  {bolehTulis && (
                    <td className="px-3 py-2">
                      <div className="flex gap-1">
                        <button type="button" title="Ubah data" aria-label={`Ubah data ${r.kelurahan || r.kecamatan}`} data-testid={`dis-edit-${r.id}`}
                          onClick={() => setForm({ id: r.id, data: r })}
                          className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-amber-100 hover:text-amber-700 sm:h-8 sm:w-8">
                          <Pencil className="h-4 w-4" />
                        </button>
                        {bolehHapus && (
                          <button type="button" title="Hapus data" aria-label={`Hapus data ${r.kelurahan || r.kecamatan}`} data-testid={`dis-hapus-${r.id}`}
                            onClick={() => setHapus(r)}
                            className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-rose-100 hover:text-rose-700 sm:h-8 sm:w-8">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {!(rekap?.items || []).length && (
                <tr><td colSpan={10} className="px-3 py-6 text-center text-slate-500">
                  Belum ada data rekap kelurahan
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Rekap Laporan per SKPD / Kecamatan" className="mt-4" testid="tabel-dis-opd">
        <div className="table-scroll">
          <table className="w-full min-w-[920px] text-sm">
            <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">SKPD / Kecamatan</th>
                <th className="px-3 py-2">L</th>
                <th className="px-3 py-2">P</th>
                <th className="px-3 py-2">Fisik</th>
                <th className="px-3 py-2">Ganda</th>
                <th className="px-3 py-2">Intelektual</th>
                <th className="px-3 py-2">Mental</th>
                <th className="px-3 py-2">Pendengaran</th>
                <th className="px-3 py-2">Penglihatan</th>
                <th className="px-3 py-2">&lt;18</th>
                <th className="px-3 py-2">18-59</th>
                <th className="px-3 py-2">Total</th>
              </tr>
            </thead>
            <tbody>
              {(d?.sumber_opd || []).map((o: any, i: number) => (
                <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2 font-semibold text-slate-800">{o.skpd}</td>
                  <td className="px-3 py-2">{fmtNum(o.laki_laki)}</td>
                  <td className="px-3 py-2">{fmtNum(o.perempuan)}</td>
                  <td className="px-3 py-2">{fmtNum(o.ragam?.Fisik)}</td>
                  <td className="px-3 py-2">{fmtNum(o.ragam?.Ganda)}</td>
                  <td className="px-3 py-2">{fmtNum(o.ragam?.Intelektual)}</td>
                  <td className="px-3 py-2">{fmtNum(o.ragam?.Mental)}</td>
                  <td className="px-3 py-2">{fmtNum(o.ragam?.["Sensorik Pendengaran"])}</td>
                  <td className="px-3 py-2">{fmtNum(o.ragam?.["Sensorik Penglihatan"])}</td>
                  <td className="px-3 py-2">{fmtNum(o.usia_dibawah_18)}</td>
                  <td className="px-3 py-2">{fmtNum(o.usia_18_59)}</td>
                  <td className="px-3 py-2 font-bold">{fmtNum(o.total)}</td>
                </tr>
              ))}
              {!loading && !(d?.sumber_opd || []).length && (
                <tr><td colSpan={12} className="px-3 py-6 text-center text-slate-500">Belum ada data</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      {form && (
        <DynamicForm
          jenis="disabilitas"
          recordId={form.id}
          initial={form.data}
          judul={form.id ? "Ubah Rekap Disabilitas" : "Input Rekap Disabilitas"}
          onClose={() => setForm(null)}
          onSimpan={async (data, mode) => (form.id
            ? updateDisabilitas(form.id, data)
            : createDisabilitas(data, mode))}
          onSelesai={muat}
        />
      )}

      {hapus && (
        <KonfirmasiHapus
          judul="Hapus rekap disabilitas"
          keterangan={`${hapus.kelurahan || hapus.kecamatan} · tahun ${hapus.tahun} · total ${hapus.jumlah}`}
          onBatal={() => setHapus(null)}
          onHapus={async (alasan) => {
            try {
              await deleteDisabilitas(hapus.id, alasan);
              toast.success("Data rekap disabilitas berhasil dihapus");
              setHapus(null);
              muat();
            } catch {
              toast.error("Gagal menghapus data (periksa hak akses Anda)");
            }
          }}
        />
      )}
    </div>
  );
}
