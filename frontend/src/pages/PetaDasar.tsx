import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import {
  Building2, Layers3, Loader2, MapPin, Milestone, Mountain, Route, Search, Waves,
} from "lucide-react";
import { KpiCard, Panel, PageHeader, CHART_COLORS } from "@/features/data/ui";
import { fmtNum } from "@/features/data/api";
import {
  fetchBasemapLayers, fetchFasilitas, fetchFasilitasRekap, fetchPetaDasarRingkasan,
} from "@/features/peta/basemapApi";
import {
  BasemapLayerMeta, FasilitasRekapResponse, FasilitasResponse, PetaDasarRingkasan,
} from "@/features/peta/basemapTypes";

const SEMUA = "semua";

export default function PetaDasar() {
  const [ringkasan, setRingkasan] = useState<PetaDasarRingkasan | null>(null);
  const [layers, setLayers] = useState<BasemapLayerMeta[]>([]);
  const [sumber, setSumber] = useState("");
  const [loading, setLoading] = useState(true);

  // pencarian fasilitas umum
  const [cari, setCari] = useState("");
  const [klasifikasi, setKlasifikasi] = useState(SEMUA);
  const [kecamatan, setKecamatan] = useState(SEMUA);
  const [page, setPage] = useState(1);
  const [fasilitas, setFasilitas] = useState<FasilitasResponse | null>(null);
  const [loadingFas, setLoadingFas] = useState(false);

  // rekap per wilayah
  const [rekapLevel, setRekapLevel] = useState<"kelurahan" | "kecamatan">("kecamatan");
  const [rekap, setRekap] = useState<FasilitasRekapResponse | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [r, l] = await Promise.all([fetchPetaDasarRingkasan(), fetchBasemapLayers()]);
        setRingkasan(r);
        setLayers(l.layers || []);
        setSumber(l.sumber || r.sumber || "");
      } catch {
        toast.error("Gagal memuat statistik peta dasar");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const loadFasilitas = useCallback(async () => {
    setLoadingFas(true);
    try {
      const res = await fetchFasilitas({
        search: cari || undefined,
        klasifikasi: klasifikasi === SEMUA ? undefined : klasifikasi,
        kecamatan: kecamatan === SEMUA ? undefined : kecamatan,
        page,
        page_size: 20,
      });
      setFasilitas(res);
    } catch {
      toast.error("Gagal memuat daftar fasilitas umum");
    } finally {
      setLoadingFas(false);
    }
  }, [cari, klasifikasi, kecamatan, page]);

  useEffect(() => {
    loadFasilitas();
  }, [loadFasilitas]);

  useEffect(() => {
    fetchFasilitasRekap(rekapLevel, kecamatan === SEMUA ? undefined : kecamatan)
      .then(setRekap)
      .catch(() => toast.error("Gagal memuat rekap fasilitas"));
  }, [rekapLevel, kecamatan]);

  const jalanData = useMemo(
    () => (ringkasan?.jalan_per_fungsi || [])
      .filter((j) => j.panjang_km > 0)
      .map((j) => ({ nama: j.kategori.replace("Jalan ", ""), km: Number(j.panjang_km.toFixed(1)) })),
    [ringkasan],
  );

  const penutupData = useMemo(
    () => (ringkasan?.penutup_lahan_teratas || [])
      .map((p) => ({ nama: p.kategori, ha: Number(p.luas_ha.toFixed(0)) })),
    [ringkasan],
  );

  const toponimiData = useMemo(
    () => (ringkasan?.toponimi_per_klasifikasi || [])
      .slice(0, 8)
      .map((t) => ({ nama: t.kategori, jumlah: t.jumlah })),
    [ringkasan],
  );

  const klasifikasiOptions = fasilitas?.filters?.klasifikasi || [];
  const kecamatanOptions = fasilitas?.filters?.kecamatan || [];

  return (
    <div data-testid="page-peta-dasar">
      <PageHeader
        title="Peta Dasar Kota Makassar"
        subtitle={sumber || "Data Penetapan Peta Dasar Edisi 2021 (BIG)"}
      />

      {loading && (
        <div className="mb-3 inline-flex items-center gap-2 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" /> Memuat statistik peta dasar…
        </div>
      )}

      {/* KPI */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label="Luas wilayah"
          value={`${fmtNum(Math.round(ringkasan?.luas_kota_ha || 0))} ha`}
          hint={`${fmtNum(ringkasan?.jumlah_kelurahan || 0)} kelurahan`}
          color="#0f172a"
          icon={<MapPin className="h-4 w-4" />}
          testid="kpi-luas-kota"
        />
        <KpiCard
          label="Panjang jalan"
          value={`${fmtNum(Math.round(ringkasan?.panjang_jalan_km || 0))} km`}
          hint={`Utama ${fmtNum(Math.round(ringkasan?.panjang_jalan_utama_km || 0))} km`}
          color="#dc2626"
          icon={<Route className="h-4 w-4" />}
          testid="kpi-jalan"
        />
        <KpiCard
          label="Sungai & kanal"
          value={`${fmtNum(Math.round(ringkasan?.panjang_sungai_kanal_km || 0))} km`}
          hint={`Perairan ${fmtNum(Math.round(ringkasan?.luas_perairan_ha || 0))} ha`}
          color="#2563eb"
          icon={<Waves className="h-4 w-4" />}
          testid="kpi-perairan"
        />
        <KpiCard
          label="Garis pantai"
          value={`${fmtNum(Math.round(ringkasan?.panjang_garis_pantai_km || 0))} km`}
          hint={`${fmtNum(ringkasan?.jumlah_jembatan || 0)} jembatan`}
          color="#0e7490"
          icon={<Milestone className="h-4 w-4" />}
          testid="kpi-pantai"
        />
        <KpiCard
          label="Fasilitas umum"
          value={fmtNum(ringkasan?.jumlah_toponimi || 0)}
          hint="titik toponimi tersurvei"
          color="#16a34a"
          icon={<Building2 className="h-4 w-4" />}
          testid="kpi-toponimi"
        />
        <KpiCard
          label="Poligon penutup lahan"
          value={fmtNum(ringkasan?.jumlah_penutup_lahan || 0)}
          hint={`${fmtNum(ringkasan?.jumlah_kontur || 0)} garis kontur`}
          color="#b45309"
          icon={<Mountain className="h-4 w-4" />}
          testid="kpi-penutup-lahan"
        />
      </div>

      {/* Grafik */}
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <Panel title="Panjang jalan per fungsi (km)" testid="panel-jalan">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={jalanData} margin={{ left: 6, right: 12, top: 8, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="nama" angle={-25} textAnchor="end" height={60}
                tick={{ fontSize: 10 }} interval={0} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: any) => `${fmtNum(v)} km`} />
              <Bar dataKey="km" radius={[4, 4, 0, 0]}>
                {jalanData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Penutup lahan terluas (ha)" testid="panel-penutup-lahan">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={penutupData} layout="vertical"
              margin={{ left: 40, right: 20, top: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="nama" width={120} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: any) => `${fmtNum(v)} ha`} />
              <Bar dataKey="ha" radius={[0, 4, 4, 0]}>
                {penutupData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[(i + 3) % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Fasilitas umum per klasifikasi" testid="panel-toponimi">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={toponimiData} dataKey="jumlah" nameKey="nama" cx="50%" cy="45%"
                outerRadius={90} label={(e: any) => e.jumlah}>
                {toponimiData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Tooltip formatter={(v: any) => fmtNum(v)} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Daftar layer peta dasar" testid="panel-layers">
          <div className="table-scroll max-h-[280px] overflow-y-auto">
            <table className="w-full min-w-[400px] text-[11.5px]">
              <thead className="sticky top-0 bg-slate-50 text-left text-[10px] uppercase text-slate-500">
                <tr>
                  <th className="p-1.5">Layer</th>
                  <th className="p-1.5">Grup</th>
                  <th className="p-1.5 text-right">Fitur</th>
                  <th className="p-1.5 text-right">Panjang/Luas</th>
                </tr>
              </thead>
              <tbody>
                {layers.map((l) => (
                  <tr key={l.id} className="border-b border-slate-100" data-testid={`row-layer-${l.id}`}>
                    <td className="p-1.5">
                      <span className="flex items-center gap-1.5">
                        <span className="inline-block h-2.5 w-2.5 rounded-sm"
                          style={{ backgroundColor: l.warna }} />
                        <span className="font-semibold text-slate-800">{l.label}</span>
                      </span>
                    </td>
                    <td className="p-1.5 text-slate-500">{l.grup}</td>
                    <td className="p-1.5 text-right font-semibold">{fmtNum(l.jumlah)}</td>
                    <td className="p-1.5 text-right text-slate-600">
                      {l.panjang_km ? `${fmtNum(Math.round(l.panjang_km))} km` : ""}
                      {l.luas_ha ? `${fmtNum(Math.round(l.luas_ha))} ha` : ""}
                      {!l.panjang_km && !l.luas_ha ? "-" : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 flex items-start gap-1 text-[10px] text-slate-500">
            <Layers3 className="mt-[1px] h-3 w-3 shrink-0" />
            Semua layer dapat ditampilkan pada halaman Peta Sosial dan Peta Kemiskinan melalui
            panel {"\u201c"}Layer Peta Dasar{"\u201d"}.
          </p>
        </Panel>
      </div>

      {/* Rekap fasilitas per wilayah */}
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <Panel
          title="Rekap fasilitas umum per wilayah"
          testid="panel-rekap-fasilitas"
          action={
            <select
              data-testid="rekap-level"
              value={rekapLevel}
              onChange={(e) => setRekapLevel(e.target.value as "kelurahan" | "kecamatan")}
              className="h-9 rounded-md border border-slate-300 px-2 text-xs"
            >
              <option value="kecamatan">Per Kecamatan</option>
              <option value="kelurahan">Per Kelurahan</option>
            </select>
          }
        >
          <div className="table-scroll max-h-[320px] overflow-y-auto">
            <table className="w-full min-w-[380px] text-[11.5px]">
              <thead className="sticky top-0 bg-slate-50 text-left text-[10px] uppercase text-slate-500">
                <tr>
                  <th className="p-1.5">Wilayah</th>
                  <th className="p-1.5 text-right">Total</th>
                  <th className="p-1.5">Terbanyak</th>
                </tr>
              </thead>
              <tbody>
                {(rekap?.rows || []).map((r) => {
                  const top = Object.entries(r.per_klasifikasi || {})
                    .sort((a, b) => b[1] - a[1])[0];
                  return (
                    <tr key={r.wilayah} className="border-b border-slate-100">
                      <td className="p-1.5 font-semibold text-slate-800">
                        {r.wilayah}
                        {rekapLevel === "kelurahan" && r.kecamatan ? (
                          <span className="ml-1 text-[10px] font-normal text-slate-500">
                            (Kec. {r.kecamatan})
                          </span>
                        ) : null}
                      </td>
                      <td className="p-1.5 text-right font-bold">{fmtNum(r.total)}</td>
                      <td className="p-1.5 text-slate-600">
                        {top ? `${top[0]} (${fmtNum(top[1])})` : "-"}
                      </td>
                    </tr>
                  );
                })}
                {!rekap?.rows?.length && (
                  <tr>
                    <td colSpan={3} className="p-3 text-center text-slate-500">
                      Belum ada data fasilitas umum.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Pencarian fasilitas umum / toponimi" testid="panel-cari-fasilitas">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[160px]">
              <Search className="absolute left-2 top-2.5 h-3.5 w-3.5 text-slate-400" />
              <input
                data-testid="input-cari-fasilitas"
                value={cari}
                onChange={(e) => {
                  setCari(e.target.value);
                  setPage(1);
                }}
                placeholder="Cari nama fasilitas (mis. puskesmas, SD)"
                className="h-9 w-full rounded-md border border-slate-300 pl-7 pr-2 text-xs"
              />
            </div>
            <select
              data-testid="filter-klasifikasi"
              value={klasifikasi}
              onChange={(e) => {
                setKlasifikasi(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-slate-300 px-2 text-xs"
            >
              <option value={SEMUA}>Semua klasifikasi</option>
              {klasifikasiOptions.map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
            <select
              data-testid="filter-kecamatan-fasilitas"
              value={kecamatan}
              onChange={(e) => {
                setKecamatan(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-slate-300 px-2 text-xs"
            >
              <option value={SEMUA}>Semua kecamatan</option>
              {kecamatanOptions.map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </div>

          <div className="table-scroll max-h-[280px] overflow-y-auto">
            <table className="w-full min-w-[500px] text-[11.5px]">
              <thead className="sticky top-0 bg-slate-50 text-left text-[10px] uppercase text-slate-500">
                <tr>
                  <th className="p-1.5">Nama</th>
                  <th className="p-1.5">Jenis</th>
                  <th className="p-1.5">Kelurahan</th>
                  <th className="whitespace-nowrap p-1.5">Koordinat</th>
                </tr>
              </thead>
              <tbody data-testid="tabel-fasilitas">
                {(fasilitas?.items || []).map((f) => (
                  <tr key={f.fid} className="border-b border-slate-100">
                    <td className="p-1.5 font-semibold text-slate-800">{f.nama || "-"}</td>
                    <td className="p-1.5 text-slate-600">{f.jenis}</td>
                    <td className="p-1.5 text-slate-600">
                      {f.kelurahan || "-"}
                      {f.kecamatan ? (
                        <span className="block text-[10px] text-slate-400">Kec. {f.kecamatan}</span>
                      ) : null}
                    </td>
                    <td className="whitespace-nowrap p-1.5 font-mono text-[10px] text-slate-500">
                      {Number(f.lat).toFixed(5)}, {Number(f.lng).toFixed(5)}
                    </td>
                  </tr>
                ))}
                {!loadingFas && !fasilitas?.items?.length && (
                  <tr>
                    <td colSpan={4} className="p-3 text-center text-slate-500">
                      Tidak ada fasilitas yang cocok dengan filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-600">
            <span data-testid="fasilitas-total">
              {loadingFas ? (
                <span className="inline-flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" /> memuat…
                </span>
              ) : (
                `${fmtNum(fasilitas?.total || 0)} fasilitas ditemukan`
              )}
            </span>
            <span className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                data-testid="btn-prev-fasilitas"
                disabled={(fasilitas?.page || 1) <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="min-h-9 rounded border border-slate-300 px-3 py-1 font-semibold disabled:opacity-40 sm:min-h-8"
              >
                Sebelumnya
              </button>
              <span>
                Hal. {fasilitas?.page || 1} / {fasilitas?.total_page || 1}
              </span>
              <button
                type="button"
                data-testid="btn-next-fasilitas"
                disabled={(fasilitas?.page || 1) >= (fasilitas?.total_page || 1)}
                onClick={() => setPage((p) => p + 1)}
                className="min-h-9 rounded border border-slate-300 px-3 py-1 font-semibold disabled:opacity-40 sm:min-h-8"
              >
                Berikutnya
              </button>
            </span>
          </div>
        </Panel>
      </div>
    </div>
  );
}
