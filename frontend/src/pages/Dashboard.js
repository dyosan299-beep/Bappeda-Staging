import { useEffect, useState } from "react";
import api, { API } from "@/lib/api";
import { KpiCard } from "@/components/KpiCard";
import { Speak } from "@/components/Speak";
import { toast } from "sonner";
import {
  Users, Baby, Footprints, GraduationCap, Accessibility, RefreshCw, FileDown, FileSpreadsheet,
} from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, PieChart, Pie, Cell,
} from "recharts";

const fmt = (n) => (n ?? 0).toLocaleString("id-ID");
const PIE_COLORS = ["#DC2626", "#D97706", "#4338CA", "#C026D3", "#047857", "#0EA5E9"];

function Panel({ title, children, action }) {
  return (
    <div className="rounded-lg border-2 border-border bg-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-head text-lg font-bold">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

export default function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [regions, setRegions] = useState([]);
  const [poverty, setPoverty] = useState(null);
  const [stunting, setStunting] = useState([]);
  const [pmks, setPmks] = useState([]);
  const [disability, setDisability] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);

  const loadAll = async () => {
    const [ov, rg, pv, st, pk, ds] = await Promise.all([
      api.get("/stats/overview"),
      api.get("/regions"),
      api.get("/trends/poverty"),
      api.get("/trends/stunting"),
      api.get("/pmks"),
      api.get("/disability"),
    ]);
    setOverview(ov.data);
    setRegions(rg.data);
    setPoverty(pv.data);
    setStunting(st.data.tren);
    setPmks(pk.data.data);
    setDisability(ds.data);
    setUpdatedAt(new Date());
  };

  useEffect(() => {
    loadAll();
    const t = setInterval(loadAll, 30000); // pembaruan real-time tiap 30 detik
    return () => clearInterval(t);
  }, []);

  if (!overview) return <div className="p-10 text-center text-muted-foreground">Memuat data…</div>;

  const downloadReport = async () => {
    try {
      toast.loading("Menyiapkan laporan PDF…", { id: "dash-pdf" });
      const res = await fetch(`${API}/report/dashboard`, { credentials: "include" });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Ringkasan_Dashboard_Bappeda_Makassar.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Laporan PDF berhasil diunduh", { id: "dash-pdf" });
    } catch {
      toast.error("Gagal mengunduh laporan", { id: "dash-pdf" });
    }
  };

  const downloadExcel = async () => {
    try {
      toast.loading("Menyiapkan data Excel…", { id: "dash-xls" });
      const res = await fetch(`${API}/export/excel`, { credentials: "include" });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Data_Sosial_Kota_Makassar.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Data Excel berhasil diunduh", { id: "dash-xls" });
    } catch {
      toast.error("Gagal mengunduh data Excel", { id: "dash-xls" });
    }
  };

  // Poverty combined chart data
  const povChart = [
    ...poverty.tren.map((t) => ({ tahun: String(t.tahun), realisasi: t.persen })),
    ...poverty.target.filter((t) => t.tahun > 2025).map((t) => ({ tahun: String(t.tahun), target: t.target_persen })),
  ];
  // merge target baseline into 2025
  povChart.forEach((d) => {
    const tg = poverty.target.find((x) => String(x.tahun) === d.tahun);
    if (tg) d.target = tg.target_persen;
  });

  const ajTrend = (() => {
    const aj = pmks.find((p) => p.indikator === "Anak Jalanan");
    return aj ? [
      { tahun: "2022", jumlah: aj.y2022 },
      { tahun: "2023", jumlah: aj.y2023 },
      { tahun: "2024", jumlah: aj.y2024 },
      { tahun: "2025", jumlah: aj.y2025 },
    ] : [];
  })();

  const topPoverty = [...regions].sort((a, b) => b.kemiskinan_ekstrim_kk - a.kemiskinan_ekstrim_kk).slice(0, 8)
    .map((r) => ({ nama: r.nama, KK: r.kemiskinan_ekstrim_kk }));
  const topStunting = [...regions].sort((a, b) => b.stunting_anak - a.stunting_anak).slice(0, 8)
    .map((r) => ({ nama: r.nama, Anak: r.stunting_anak }));

  const summary = `Ringkasan data sosial Kota Makassar. Terdapat ${overview.jumlah_kecamatan} kecamatan dan ${overview.jumlah_kelurahan} kelurahan. Kemiskinan ekstrim mencapai ${fmt(overview.kemiskinan_ekstrim_kk)} kepala keluarga. Jumlah kasus stunting ${fmt(overview.stunting_anak)} anak. Anak tidak sekolah ${fmt(overview.ats)} anak. Anak jalanan ${fmt(overview.anak_jalanan)} jiwa. Penyandang disabilitas ${fmt(overview.disabilitas)} orang. Tingkat kemiskinan kota terkini ${overview.kemiskinan_persen_terkini} persen.`;

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-head text-3xl font-extrabold md:text-4xl">Dashboard Real-time</p>
          <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
            <RefreshCw className="h-3.5 w-3.5" />
            Diperbarui otomatis · {updatedAt?.toLocaleTimeString("id-ID")}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            data-testid="dashboard-pdf-btn"
            onClick={downloadReport}
            className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground transition-colors hover:bg-[hsl(222_47%_20%)] focus:outline-none"
          >
            <FileDown className="h-4 w-4" /> Unduh Laporan PDF
          </button>
          <button
            data-testid="dashboard-excel-btn"
            onClick={downloadExcel}
            className="inline-flex items-center gap-2 rounded-full bg-[hsl(160_84%_27%)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[hsl(160_84%_22%)] focus:outline-none"
          >
            <FileSpreadsheet className="h-4 w-4" /> Unduh Excel
          </button>
          <Speak text={summary} label="Bacakan Ringkasan" testid="dashboard-speak" />
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard testid="kpi-kemiskinan" label="Kemiskinan Ekstrim" value={fmt(overview.kemiskinan_ekstrim_kk)} sub="Kepala Keluarga" icon={Users} accent="primary" />
        <KpiCard testid="kpi-stunting" label="Stunting" value={fmt(overview.stunting_anak)} sub="Kasus anak (sebaran kecamatan)" icon={Baby} accent="amber" />
        <KpiCard testid="kpi-anak-jalanan" label="Anak Jalanan" value={fmt(overview.anak_jalanan)} sub="Jiwa (2025)" icon={Footprints} accent="indigo" />
        <KpiCard testid="kpi-ats" label="Anak Tidak Sekolah" value={fmt(overview.ats)} sub="Total ATS" icon={GraduationCap} accent="fuchsia" />
        <KpiCard testid="kpi-disabilitas" label="Disabilitas" value={fmt(overview.disabilitas)} sub="Orang (sebaran kecamatan)" icon={Accessibility} accent="emerald" />
        <KpiCard testid="kpi-kemiskinan-persen" label="Tingkat Kemiskinan Kota" value={`${overview.kemiskinan_persen_terkini}%`} sub={`${overview.penduduk_miskin_ribu} ribu jiwa · 2025`} icon={Users} accent="primary" />
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Tren Kemiskinan & Target RPJMD (%)">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={povChart} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="tahun" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="realisasi" name="Realisasi" stroke="#DC2626" strokeWidth={3} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="target" name="Target RPJMD" stroke="#4338CA" strokeWidth={3} strokeDasharray="6 4" dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Tren Stunting EPPGBM vs SSGI (%)">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={stunting.map((s) => ({ tahun: String(s.tahun), EPPGBM: s.eppgbm_persen, SSGI: s.ssgi_persen }))} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="tahun" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="EPPGBM" stroke="#D97706" strokeWidth={3} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="SSGI" stroke="#DC2626" strokeWidth={3} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Kemiskinan Ekstrim per Kecamatan (KK)">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={topPoverty} layout="vertical" margin={{ top: 0, right: 20, left: 30, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="nama" tick={{ fontSize: 12 }} width={90} />
              <Tooltip />
              <Bar dataKey="KK" fill="#DC2626" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Stunting per Kecamatan (anak)">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={topStunting} layout="vertical" margin={{ top: 0, right: 20, left: 30, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="nama" tick={{ fontSize: 12 }} width={90} />
              <Tooltip />
              <Bar dataKey="Anak" fill="#D97706" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      {/* Charts row 3 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Tren Anak Jalanan (jiwa)">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ajTrend} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="tahun" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="jumlah" name="Anak Jalanan" fill="#4338CA" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Ragam Disabilitas Kota (2025)">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={disability.ragam}
                dataKey="jumlah"
                nameKey="kategori"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ jumlah }) => fmt(jumlah)}
              >
                {disability.ragam.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      {/* PMKS table */}
      <Panel title="Tabel PMKS Kota Makassar (2022–2025)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="pmks-table">
            <thead>
              <tr className="border-b-2 border-border text-left">
                <th className="py-2 pr-4 font-bold">Indikator Sosial</th>
                <th className="py-2 pr-4 text-right font-bold">2022</th>
                <th className="py-2 pr-4 text-right font-bold">2023</th>
                <th className="py-2 pr-4 text-right font-bold">2024</th>
                <th className="py-2 text-right font-bold">2025</th>
              </tr>
            </thead>
            <tbody>
              {pmks.map((p) => (
                <tr key={p.indikator} className="border-b border-border">
                  <td className="py-2 pr-4 font-medium">{p.indikator}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{p.y2022 ?? "–"}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{p.y2023 ?? "–"}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{p.y2024 ?? "–"}</td>
                  <td className="py-2 text-right tabular-nums">{p.y2025 ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
