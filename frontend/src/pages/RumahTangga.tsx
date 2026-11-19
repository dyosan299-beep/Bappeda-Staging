import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, Eye, Pencil, Search, ShieldAlert, Trash2 } from "lucide-react";
import { PageHeader, Panel, RISK_COLORS, RISK_LABELS } from "@/features/data/ui";
import {
  fmtNum, getHousehold, getHouseholds, getKelurahan, getWilayahSummary,
} from "@/features/data/api";
import {
  deleteHousehold, createHousehold, getHouseholdForm, getKodeMap, updateHousehold,
} from "@/features/data/manageApi";
import DynamicForm from "@/features/data/DynamicForm";
import ExportButtons from "@/features/data/ExportButtons";
import { InputDataButton, KonfirmasiHapus } from "@/features/data/InputDataButton";
import { useAuth } from "@/context/AuthContext";
import { bolehHapus as cekHapus, bolehTulis as cekTulis } from "@/features/data/roles";

const SEMUA = "semua";

export default function RumahTangga() {
  const { user } = useAuth();
  const bolehTulis = cekTulis(user?.role);
  const bolehHapus = cekHapus(user?.role);
  const [form, setForm] = useState<{ id: string | null; data: any } | null>(null);
  const [hapus, setHapus] = useState<any>(null);
  const [kodeMap, setKodeMap] = useState<Record<string, Record<string, string>>>({});
  const [wilayah, setWilayah] = useState<any>(null);
  const [kelList, setKelList] = useState<any[]>([]);
  const [kec, setKec] = useState(SEMUA);
  const [kel, setKel] = useState(SEMUA);
  const [desil, setDesil] = useState(SEMUA);
  const [risk, setRisk] = useState(SEMUA);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { getWilayahSummary().then(setWilayah).catch(() => {}); }, []);
  useEffect(() => { getKodeMap().then((r) => setKodeMap(r.labels || {})).catch(() => {}); }, []);
  useEffect(() => {
    getKelurahan(kec === SEMUA ? undefined : kec).then((r) => setKelList(r.items || []));
    setKel(SEMUA);
  }, [kec]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getHouseholds({
        kode_kecamatan: kec === SEMUA ? undefined : kec,
        kode_kelurahan: kel === SEMUA ? undefined : kel,
        desil: desil === SEMUA ? undefined : desil,
        risk_level: risk === SEMUA ? undefined : risk,
        search: search || undefined,
        page, size: 25,
      });
      setData(res);
    } catch {
      toast.error("Gagal memuat data rumah tangga");
    } finally {
      setLoading(false);
    }
  }, [kec, kel, desil, risk, search, page]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(1); }, [kec, kel, desil, risk, search]);

  /** Tampilkan kode kondisi rumah sebagai teks bila arti kode sudah didefinisikan admin. */
  const kodeTeks = (field: string, v: any) => {
    if (v === null || v === undefined || v === "") return "-";
    const label = kodeMap?.[field]?.[String(v)];
    return label ? `${v} — ${label}` : String(v);
  };

  return (
    <div data-testid="page-rumah-tangga">
      <PageHeader title="Data Rumah Tangga (DTSEN)"
        subtitle="Data pribadi ditampilkan dengan penyamaran (masking) sesuai hak akses pengguna"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ExportButtons jalur="dtsen" testid="rt-export" filter={{
              kode_kecamatan: kec === SEMUA ? undefined : kec,
              kode_kelurahan: kel === SEMUA ? undefined : kel,
              desil: desil === SEMUA ? undefined : desil,
              risk_level: risk === SEMUA ? undefined : risk,
              search: search || undefined,
            }} />
            {bolehTulis && (
              <InputDataButton jenis="dtsen" onManual={() => setForm({ id: null, data: {} })} />
            )}
          </div>
        } />

      <div className="mb-3 flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <select value={kec} onChange={(e) => setKec(e.target.value)} data-testid="rt-kecamatan"
          className="h-9 rounded-md border border-slate-300 px-2 text-sm">
          <option value={SEMUA}>Semua Kecamatan</option>
          {wilayah?.kecamatan?.map((k: any) => <option key={k.kode} value={k.kode}>{k.nama}</option>)}
        </select>
        <select value={kel} onChange={(e) => setKel(e.target.value)} data-testid="rt-kelurahan"
          className="h-9 rounded-md border border-slate-300 px-2 text-sm">
          <option value={SEMUA}>Semua Kelurahan</option>
          {kelList.map((k) => <option key={k.kode} value={k.kode}>{k.nama}</option>)}
        </select>
        <select value={desil} onChange={(e) => setDesil(e.target.value)}
          className="h-9 rounded-md border border-slate-300 px-2 text-sm">
          <option value={SEMUA}>Semua Desil</option>
          {[1, 2, 3, 4, 5].map((d) => <option key={d} value={d}>Desil {d}</option>)}
        </select>
        <select value={risk} onChange={(e) => setRisk(e.target.value)} data-testid="rt-risk"
          className="h-9 rounded-md border border-slate-300 px-2 text-sm">
          <option value={SEMUA}>Semua Prioritas</option>
          {Object.entries(RISK_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <div className="relative w-full min-w-0 sm:w-auto">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari nama KK / nomor KK" data-testid="rt-search"
            className="h-10 w-full sm:h-9 sm:w-60 rounded-md border border-slate-300 pl-8 pr-2 text-sm" />
        </div>
        <span className="ml-auto text-xs text-slate-500">
          {loading ? "Memuat…" : `${fmtNum(data?.total)} rumah tangga`}
          {data?.masked && " · data disamarkan"}
        </span>
      </div>

      <Panel title="Daftar Rumah Tangga" testid="tabel-rt">
        <div className="table-scroll">
          <table className="w-full min-w-[840px] text-sm">
            <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="whitespace-nowrap px-3 py-2">No. KK</th>
                <th className="px-3 py-2">Kepala Keluarga</th>
                <th className="whitespace-nowrap px-3 py-2">ART</th>
                <th className="px-3 py-2">Kelurahan</th>
                <th className="whitespace-nowrap px-3 py-2">Desil</th>
                <th className="whitespace-nowrap px-3 py-2">PBI</th>
                <th className="whitespace-nowrap px-3 py-2">Skor</th>
                <th className="whitespace-nowrap px-3 py-2">Prioritas</th>
                <th className="whitespace-nowrap px-3 py-2">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items || []).map((h: any) => (
                <tr key={h.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-[11px]">{h.no_kk}</td>
                  <td className="px-3 py-2 font-semibold text-slate-800">{h.kepala_keluarga}</td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{h.jumlah_anggota_keluarga}</td>
                  <td className="px-3 py-2">{h.kelurahan}<span className="ml-1 text-[11px] text-slate-500">({h.kecamatan})</span></td>
                  <td className="whitespace-nowrap px-3 py-2">{h.desil_nasional ?? "-"}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-[11px]">
                    {h.pbi_nas === 1 ? "Nasional" : ""}{h.pbi_nas === 1 && h.pbi_pemda === 1 ? " + " : ""}
                    {h.pbi_pemda === 1 ? "Pemda" : ""}{!h.pbi_nas && !h.pbi_pemda ? "-" : ""}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 font-bold tabular-nums">{h.risk_score}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-[11px] font-semibold">
                      <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: RISK_COLORS[h.risk_level] }} />
                      {RISK_LABELS[h.risk_level] || h.risk_level}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <div className="flex items-center gap-1">
                      <button type="button" onClick={async () => setDetail(await getHousehold(h.id))}
                        className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-slate-200 hover:text-slate-900 sm:h-8 sm:w-8"
                        data-testid={`rt-detail-${h.id}`} aria-label="Lihat detail" title="Detail">
                        <Eye className="h-4 w-4" />
                      </button>
                      {bolehTulis && (
                        <button type="button" data-testid={`rt-edit-${h.id}`} title="Ubah data"
                          onClick={async () => {
                            try {
                              const f = await getHouseholdForm(h.id);
                              setForm({ id: h.id, data: f.data });
                            } catch {
                              toast.error("Gagal memuat data untuk diubah");
                            }
                          }}
                          className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-amber-100 hover:text-amber-700 sm:h-8 sm:w-8"
                          aria-label="Ubah data">
                          <Pencil className="h-4 w-4" />
                        </button>
                      )}
                      {bolehHapus && (
                        <button type="button" data-testid={`rt-hapus-${h.id}`} title="Hapus data"
                          onClick={() => setHapus(h)}
                          className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-rose-100 hover:text-rose-700 sm:h-8 sm:w-8"
                          aria-label="Hapus data">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
          <span>Halaman {data?.page || 1} dari {fmtNum(data?.pages)}</span>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={(data?.page || 1) <= 1} onClick={() => setPage((p) => p - 1)}
              className="inline-flex min-h-10 items-center gap-1 rounded-md border border-slate-300 px-3 font-semibold disabled:opacity-40 sm:min-h-9">
              <ChevronLeft className="h-4 w-4" /> Sebelumnya
            </button>
            <button type="button" disabled={(data?.page || 1) >= (data?.pages || 1)}
              onClick={() => setPage((p) => p + 1)} data-testid="rt-next"
              className="inline-flex min-h-10 items-center gap-1 rounded-md border border-slate-300 px-3 font-semibold disabled:opacity-40 sm:min-h-9">
              Berikutnya <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </Panel>

      {detail && (
        <div className="fixed inset-0 z-[900] flex items-start justify-center overflow-y-auto bg-black/50 p-4">
          <div className="my-8 w-full max-w-2xl rounded-lg bg-white p-4 shadow-2xl" data-testid="rt-detail">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <h2 className="font-head text-lg font-bold">{detail.kepala_keluarga}</h2>
                <p className="text-xs text-slate-500">
                  KK {detail.no_kk} · {detail.kelurahan}, {detail.kecamatan}
                  {detail.data_masked && " · data disamarkan"}
                </p>
              </div>
              <button type="button" onClick={() => setDetail(null)}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold">Tutup</button>
            </div>
            <div className="mb-3 rounded-md border border-slate-200 bg-slate-50 p-3">
              <p className="flex items-center gap-2 text-sm font-bold" style={{ color: RISK_COLORS[detail.risk_level] }}>
                <ShieldAlert className="h-4 w-4" /> {detail.penjelasan_level} · skor {detail.risk_score}
              </p>
              <ul className="mt-2 list-inside list-disc text-xs text-slate-700">
                {(detail.risk_factors || []).map((f: string, i: number) => <li key={i}>{f}</li>)}
              </ul>
              {detail.perlu_validasi && (
                <p className="mt-2 rounded bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-800">
                  Sebagian kode kondisi belum dikenali — ditandai perlu validasi (data mentah dipertahankan)
                </p>
              )}
            </div>
            <div className="grid grid-cols-1 gap-x-4 gap-y-1 text-xs sm:grid-cols-2 md:grid-cols-3">
              {[
                ["Alamat", detail.alamat], ["Jumlah ART", detail.jumlah_anggota_keluarga],
                ["Desil Nasional", kodeTeks("desil_nasional", detail.desil_nasional)],
                ["PBI Nasional", kodeTeks("pbi_nas", detail.pbi_nas)],
                ["PBI Pemda", kodeTeks("pbi_pemda", detail.pbi_pemda)],
                ["Kepemilikan Rumah", kodeTeks("status_kepemilikan_rumah", detail.status_kepemilikan_rumah)],
                ["Lantai", kodeTeks("jenis_lantai_terluas", detail.jenis_lantai_terluas)],
                ["Luas Lantai", detail.luas_lantai],
                ["Dinding", kodeTeks("jenis_dinding_terluas", detail.jenis_dinding_terluas)],
                ["Atap", kodeTeks("jenis_atap_terluas", detail.jenis_atap_terluas)],
                ["Air Minum", kodeTeks("sumber_air_minum_utama", detail.sumber_air_minum_utama)],
                ["Penerangan", kodeTeks("sumber_penerangan_utama", detail.sumber_penerangan_utama)],
                ["Daya Terpasang", kodeTeks("daya_terpasang", detail.daya_terpasang)],
                ["Fasilitas BAB", kodeTeks("fasilitas_bab", detail.fasilitas_bab)],
                ["Kloset", kodeTeks("jenis_kloset", detail.jenis_kloset)],
                ["Pembuangan Tinja", kodeTeks("pembuangan_akhir_tinja", detail.pembuangan_akhir_tinja)],
                ["Aset Lahan Lain", kodeTeks("aset_tidak_bergerak_lahan_lainnya", detail.aset_tidak_bergerak_lahan_lainnya)],
                ["Aset Rumah Lain", kodeTeks("aset_tidak_bergerak_rumah_lainnya", detail.aset_tidak_bergerak_rumah_lainnya)],
                ["Sumber Berkas", detail.source_file],
              ].map(([k, v]) => (
                <div key={String(k)} className="flex justify-between gap-2 border-b border-dashed border-slate-200 py-1">
                  <span className="text-slate-500">{k}</span>
                  <span className="text-right font-semibold text-slate-800">{v === null || v === undefined || v === "" ? "-" : String(v)}</span>
                </div>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-slate-500">
              Arti kode mengikuti Master Kode Referensi (Administrasi → Master Kode). Kode tanpa
              keterangan ditampilkan apa adanya sesuai data DTSEN.
            </p>
          </div>
        </div>
      )}

      {form && (
        <DynamicForm
          jenis="dtsen"
          recordId={form.id}
          initial={form.data}
          judul={form.id ? "Ubah Data DTSEN Keluarga" : "Input Data DTSEN Keluarga"}
          onClose={() => setForm(null)}
          onSimpan={async (data, mode) => (form.id
            ? updateHousehold(form.id, data)
            : createHousehold(data, mode))}
          onSelesai={load}
        />
      )}

      {hapus && (
        <KonfirmasiHapus
          judul="Hapus data rumah tangga"
          keterangan={`${hapus.kepala_keluarga} · KK ${hapus.no_kk} · ${hapus.kelurahan}`}
          onBatal={() => setHapus(null)}
          onHapus={async (alasan) => {
            try {
              await deleteHousehold(hapus.id, alasan);
              toast.success("Data rumah tangga berhasil dihapus");
              setHapus(null);
              load();
            } catch {
              toast.error("Gagal menghapus data (periksa hak akses Anda)");
            }
          }}
        />
      )}
    </div>
  );
}
