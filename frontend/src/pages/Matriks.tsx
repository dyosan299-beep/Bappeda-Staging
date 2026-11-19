import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import {
  Accessibility, BarChart3, ChevronDown, ChevronRight, ClipboardCheck, FileSpreadsheet,
  GraduationCap, Loader2, Upload,
} from "lucide-react";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { WRITERS } from "@/constants/roles";
import { PageTabs, TabPanel } from "@/components/PageTabs";
import { KpiCard, PageHeader, Panel } from "@/features/data/ui";
import { fmt } from "@/features/inklusi/theme";
import { downloadBlob } from "@/features/inklusi/download";

/**
 * Pusat matriks PETA INKLUSI.
 *
 * Kolom dua matriks mengikuti kertas kerja resmi agar angka yang tampil sama
 * persis dengan berkas sumber:
 *  - Evaluasi OPPKPKE Semester 1 (strategi, OPD, aktivitas real, anggaran,
 *    realisasi 2025, target 2026),
 *  - Kemiskinan, Stunting, ATS, dan Anak Jalanan per kecamatan,
 *  - Program, Kegiatan, dan Anggaran ATS 2025–2027.
 *
 * Matriks yang belum berisi data menampilkan keadaan kosong beserta jalur impor,
 * sehingga angka tidak pernah diisi tebakan.
 */

const TH = "whitespace-nowrap px-3 py-2 text-left text-[11px] font-bold uppercase tracking-wide text-slate-600";
const TD = "px-3 py-2 align-top text-slate-700";
const TD_NUM = `${TD} whitespace-nowrap text-right font-semibold tabular-nums`;
const KARTU = "rounded-lg border border-slate-200 bg-white p-4 shadow-sm";
const TOMBOL_UTAMA =
  "inline-flex min-h-11 items-center gap-2 rounded-md bg-[#232F3E] px-4 text-sm font-bold text-white " +
  "transition-colors hover:bg-[#1A2330] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#117A69] " +
  "focus-visible:ring-offset-2 disabled:opacity-50";
const TOMBOL_SEKUNDER =
  "inline-flex min-h-11 items-center gap-2 rounded-md border border-[#B7791F] bg-[#FEF6E4] px-4 text-sm font-bold " +
  "text-[#8A5A00] transition-colors hover:bg-[#FCE3AE] focus-visible:outline-none focus-visible:ring-2 " +
  "focus-visible:ring-[#F4B63A] focus-visible:ring-offset-2 disabled:opacity-50";
const INPUT =
  "mt-1 min-h-11 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-900 " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#117A69]";

const angka = (n: any) =>
  n === null || n === undefined || n === "" ? "-" : Number(n).toLocaleString("id-ID");
const persen = (n: any) =>
  n === null || n === undefined || n === ""
    ? "-"
    : `${Number(n).toLocaleString("id-ID", { maximumFractionDigits: 2 })}%`;
const rupiah = (n: any) =>
  n === null || n === undefined || n === "" ? "-" : `Rp ${Number(n).toLocaleString("id-ID")}`;
/** Rupiah ringkas untuk kartu KPI agar angka panjang tidak terpotong. */
const rupiahRingkas = (n: any) => {
  if (n === null || n === undefined || n === "") return "-";
  const v = Number(n);
  const opsi = { maximumFractionDigits: 2 };
  if (Math.abs(v) >= 1e12) return `Rp ${(v / 1e12).toLocaleString("id-ID", opsi)} T`;
  if (Math.abs(v) >= 1e9) return `Rp ${(v / 1e9).toLocaleString("id-ID", opsi)} M`;
  if (Math.abs(v) >= 1e6) return `Rp ${(v / 1e6).toLocaleString("id-ID", { maximumFractionDigits: 1 })} jt`;
  return rupiah(v);
};
const teks = (v: any) =>
  v === null || v === undefined || v === "" ? "-" : String(v);

/** Pembungkus tabel yang dapat digeser: fokusabel agar pengguna keyboard bisa menggeser. */
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

/** Pemilih tahun anggaran dengan tombol terapkan (tidak memicu permintaan tiap ketikan). */
function TahunPicker({ tahun, onTerapkan, label }: {
  tahun: number; onTerapkan: (t: number) => void; label: string;
}) {
  const id = useId();
  const [draft, setDraft] = useState(String(tahun));
  useEffect(() => setDraft(String(tahun)), [tahun]);

  const kirim = (e: React.FormEvent) => {
    e.preventDefault();
    const n = Number(draft);
    if (!Number.isInteger(n) || n < 2000 || n > 2100) {
      toast.error("Tahun harus berupa angka antara 2000 dan 2100");
      return;
    }
    onTerapkan(n);
  };

  return (
    <form onSubmit={kirim} className="flex flex-wrap items-end gap-2">
      <div>
        <label htmlFor={id} className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          {label}
        </label>
        <input
          id={id}
          type="number"
          inputMode="numeric"
          min={2000}
          max={2100}
          step={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className={`${INPUT} w-28`}
        />
      </div>
      <button type="submit" className={TOMBOL_UTAMA}>Tampilkan</button>
    </form>
  );
}

function SemesterPicker({ semester, onChange }: { semester: number; onChange: (s: number) => void }) {
  const id = useId();
  return (
    <div className="min-w-[9.5rem]">
      <label htmlFor={id} className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Semester
      </label>
      <select
        id={id}
        value={semester}
        onChange={(e) => onChange(Number(e.target.value))}
        className={`${INPUT} w-full pr-8 sm:w-auto sm:min-w-[9.5rem]`}
      >
        <option value={1}>Semester 1</option>
        <option value={2}>Semester 2</option>
      </select>
    </div>
  );
}

/** Panel impor bersama untuk matriks OPPKPKE dan Program ATS. */
function PanelImpor({ jenis, label, semester, tahun, onSelesai }: {
  jenis: string; label: string; semester?: number; tahun: number; onSelesai: () => void;
}) {
  const { user } = useAuth();
  const idBerkas = useId();
  const berkasRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<any[]>([]);
  const bolehTulis = WRITERS.includes(user?.role || "");

  if (!bolehTulis) return null;

  const unggah = async () => {
    if (!file) return;
    setBusy(true);
    setErrors([]);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const params: Record<string, any> = { tahun };
      if (jenis === "oppkpke") params.semester = semester || 1;
      const r = await api.post(`/matriks/${jenis}/import`, fd, { params, timeout: 180000 });
      const d = r.data || {};
      toast.success(
        `${angka(d.diimpor)} baris ${label} disimpan` +
        (jenis === "oppkpke" ? ` untuk Semester ${params.semester} ${tahun}` : ""),
      );
      setFile(null);
      if (berkasRef.current) berkasRef.current.value = "";
      onSelesai();
    } catch (er: any) {
      const detail = er?.response?.data?.detail;
      if (detail && typeof detail === "object" && !Array.isArray(detail)) {
        toast.error(detail.pesan || "Impor ditolak");
        setErrors(Array.isArray(detail.errors) ? detail.errors : []);
      } else {
        toast.error(formatApiErrorDetail(detail));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title={`Impor Matriks ${label}`} testid={`matriks-impor-${jenis}`}>
      <p className="text-sm leading-relaxed text-slate-600">
        1) Unduh template &nbsp;2) Isi sesuai kolom resmi &nbsp;3) Unggah berkas.
        {jenis === "oppkpke"
          ? " Baris untuk semester dan tahun yang dipilih akan diganti seluruhnya."
          : " Seluruh isi matriks program ATS akan diganti dengan isi berkas."}
        {" "}Impor disimpan hanya bila seluruh baris valid.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => downloadBlob(`/matriks/${jenis}/template`, {}, `template_matriks_${jenis}.xlsx`)}
          className={TOMBOL_SEKUNDER}
          data-testid={`matriks-template-${jenis}`}
        >
          <FileSpreadsheet className="h-4 w-4" aria-hidden="true" /> Unduh Template Excel
        </button>
        <div className="flex min-w-0 flex-wrap items-end gap-2">
          <div className="min-w-0">
            <label htmlFor={idBerkas} className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Berkas .xlsx atau .csv
            </label>
            <input
              id={idBerkas}
              ref={berkasRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={(e) => { setFile(e.target.files?.[0] || null); setErrors([]); }}
              className="mt-1 min-h-11 max-w-full text-sm file:mr-3 file:min-h-11 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:text-sm file:font-semibold hover:file:bg-slate-200"
              data-testid={`matriks-file-${jenis}`}
            />
          </div>
          <button
            type="button"
            disabled={!file || busy}
            onClick={unggah}
            className={TOMBOL_UTAMA}
            data-testid={`matriks-unggah-${jenis}`}
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              : <Upload className="h-4 w-4" aria-hidden="true" />}
            {busy ? "Mengimpor…" : "Unggah & Simpan"}
          </button>
        </div>
      </div>

      {errors.length > 0 && (
        <div role="alert" className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-900">
          <p className="mb-1 font-bold">Baris bermasalah (belum ada data yang disimpan)</p>
          <ul className="max-h-48 space-y-0.5 overflow-y-auto">
            {errors.map((e, i) => (
              <li key={i}>Baris {e.baris}: {e.pesan}</li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}

/** Baris detail yang dapat dibuka per baris tabel. */
function BarisDetail({ id, terbuka, label, isi, colSpan }: {
  id: string; terbuka: boolean; label: string; isi: Array<[string, React.ReactNode]>; colSpan: number;
}) {
  if (!terbuka) return null;
  return (
    <tr id={id} className="border-t border-slate-200 bg-slate-50">
      <td colSpan={colSpan} className="px-3 py-3">
        <p className="mb-2 text-[11px] font-bold uppercase tracking-wide text-slate-500">{label}</p>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2 xl:grid-cols-3">
          {isi.map(([k, v]) => (
            <div key={k} className="min-w-0">
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{k}</dt>
              <dd className="break-words text-sm text-slate-800">{v}</dd>
            </div>
          ))}
        </dl>
      </td>
    </tr>
  );
}

const KOLOM_OPDKPKE: Array<[string, string, boolean]> = [
  ["opd", "OPD", false],
  ["program", "Program", false],
  ["sub_kegiatan", "Sub Kegiatan", false],
  ["anggaran", "Anggaran (Rp)", true],
  ["realisasi_sem1_2025", "Realisasi Sem 1 2025", true],
  ["total_realisasi_2025", "Total Realisasi 2025", true],
  ["target_2026", "Target 2026", false],
];

const DETAIL_OPDKPKE: Array<[string, string]> = [
  ["strategi", "Strategi OPPKPKE"],
  ["aktivitas_langsung", "Aktivitas Real — Langsung"],
  ["aktivitas_tidak_langsung", "Aktivitas Real — Tidak Langsung"],
  ["aktivitas_penunjang", "Aktivitas Real — Penunjang"],
  ["sumber_pembiayaan", "Sumber Pembiayaan"],
  ["sifat_bantuan", "Sifat Bantuan"],
  ["lokasi", "Lokasi"],
  ["jumlah_sasaran", "Jumlah Sasaran Penerima Manfaat"],
  ["besaran_manfaat", "Besaran Manfaat"],
  ["jenis_bantuan", "Jenis Bantuan"],
  ["durasi", "Durasi Pemberian Bantuan"],
];

const DETAIL_ATS: Array<[string, string]> = [
  ["sasaran", "Sasaran/Permasalahan ATS"],
  ["target_2025", "Target 2025"],
  ["anggaran_2025", "Anggaran 2025 (Rp)"],
  ["realisasi_2025", "Realisasi 2025 (Rp)"],
  ["persen_2025", "Capaian 2025"],
  ["target_2026", "Target 2026"],
  ["anggaran_2026", "Anggaran 2026 (Rp)"],
  ["realisasi_2026", "Realisasi 2026 Semester 1 (Rp)"],
  ["persen_2026", "Capaian 2026 Semester 1"],
  ["anggaran_2027", "Anggaran 2027 (Rp)"],
];

const DETAIL_DISABILITAS: Array<[string, string]> = [
  ["strategi", "Strategi Implementasi"],
  ["target_capaian", "Target Capaian"],
  ["target_2025", "Target 2025"],
  ["target_2026", "Target 2026"],
  ["capaian_2025", "Capaian Target 2025"],
  ["capaian_2026", "Capaian Target 2026"],
  ["indikator", "Indikator Capaian"],
  ["output", "Output Kegiatan"],
  ["indikator_disabilitas", "Indikator Terkait Penyandang Disabilitas"],
  ["hambatan", "Hambatan/Tantangan"],
  ["satuan", "Satuan"],
  ["lokasi", "Lokasi"],
  ["spesifik", "Spesifik/Tidak Spesifik"],
  ["keterangan", "Keterangan"],
];

/** Matriks monitoring dan evaluasi kegiatan disabilitas lintas OPD. */
function MatriksDisabilitas() {
  const [data, setData] = useState<any>(null);
  const [memuat, setMemuat] = useState(true);
  const [galat, setGalat] = useState("");
  const [buka, setBuka] = useState<Set<string>>(() => new Set());

  const muat = useCallback(() => {
    setMemuat(true);
    setGalat("");
    return api.get("/matriks/disabilitas")
      .then((r) => setData(r.data))
      .catch((er: any) => setGalat(formatApiErrorDetail(er?.response?.data?.detail)))
      .finally(() => setMemuat(false));
  }, []);

  useEffect(() => { muat(); }, [muat]);

  const alih = (id: string) => setBuka((lama) => {
    const baru = new Set(lama);
    if (baru.has(id)) baru.delete(id);
    else baru.add(id);
    return baru;
  });

  const ringkas = data?.ringkasan || {};
  const items: any[] = Array.isArray(data?.items) ? data.items : [];

  return (
    <div className="space-y-4" data-testid="matriks-disabilitas">
      <div className="min-w-0">
        <p className="font-head text-sm font-bold text-slate-800">
          Matriks Disabilitas — Monitoring dan Evaluasi Kegiatan
        </p>
        <p className="mt-0.5 text-xs text-slate-500">
          Kegiatan lintas OPD yang berpihak pada penyandang disabilitas, lengkap dengan target,
          capaian, anggaran, dan realisasi 2025–2026.
        </p>
      </div>

      {galat && (
        <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {galat}
        </div>
      )}

      {memuat ? (
        <p className="text-sm text-slate-500" aria-live="polite">Memuat matriks…</p>
      ) : items.length === 0 ? (
        <div className={`${KARTU} border-dashed`} data-testid="matriks-kosong-disabilitas">
          <p className="flex items-center gap-2 font-head text-sm font-bold text-slate-800">
            <Accessibility className="h-4 w-4 text-[#117A69]" aria-hidden="true" />
            Data matriks disabilitas belum tersedia
          </p>
          <p className="mt-1 text-sm leading-relaxed text-slate-600">
            Angka diisi dari berkas monev resmi oleh Admin Bappeda. Unduh template di bawah, isi
            sesuai kolom, lalu unggah kembali.
          </p>
          <div className="mt-3">
            <PanelImpor jenis="disabilitas" label="Matriks Disabilitas" tahun={2026} onSelesai={muat} />
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Kegiatan"
              value={angka(ringkas.jumlah_kegiatan)}
              hint={`${angka(ringkas.jumlah_opd)} OPD · ${angka(ringkas.jumlah_program)} program`}
              color="#117A69"
              testid="kpi-disabilitas-kegiatan"
            />
            <KpiCard
              label="Anggaran 2025"
              value={rupiahRingkas(ringkas.anggaran_2025)}
              hint={rupiah(ringkas.anggaran_2025)}
              color="#3B4F6B"
              testid="kpi-disabilitas-anggaran-2025"
            />
            <KpiCard
              label="Realisasi 2025"
              value={rupiahRingkas(ringkas.realisasi_2025)}
              hint={`Serapan ${persen(ringkas.serapan_2025)}`}
              color="#8A5A00"
              testid="kpi-disabilitas-realisasi-2025"
            />
            <KpiCard
              label="Anggaran 2026"
              value={rupiahRingkas(ringkas.anggaran_2026)}
              hint={`Realisasi ${rupiahRingkas(ringkas.realisasi_2026)}`}
              color="#C8375B"
              testid="kpi-disabilitas-anggaran-2026"
            />
          </div>

          <Panel
            title="Matriks Disabilitas — Kegiatan per OPD"
            action={<span className="text-[11px] font-semibold text-slate-500">
              {items.length} baris · {angka(ringkas.jumlah_opd)} OPD
            </span>}
            testid="matriks-disabilitas-panel"
          >
            <TabelGulir label="Matriks monitoring dan evaluasi kegiatan disabilitas per OPD">
              <table className="w-full min-w-[1080px] border-collapse text-sm">
                <caption className="sr-only">
                  Kegiatan disabilitas per perangkat daerah beserta target, capaian, anggaran, dan
                  realisasi tahun 2025 dan 2026.
                </caption>
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className={TH}><span className="sr-only">Rincian</span></th>
                    <th scope="col" className={TH}>OPD</th>
                    <th scope="col" className={TH}>Program</th>
                    <th scope="col" className={TH}>Sub Kegiatan</th>
                    <th scope="col" className={`${TH} text-right`}>Anggaran 2025</th>
                    <th scope="col" className={`${TH} text-right`}>Realisasi 2025</th>
                    <th scope="col" className={`${TH} text-right`}>Serapan</th>
                    <th scope="col" className={`${TH} text-right`}>Anggaran 2026</th>
                    <th scope="col" className={`${TH} text-right`}>Realisasi 2026</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((row) => {
                    const id = `disabilitas-detail-${row.id}`;
                    const terbuka = buka.has(row.id);
                    return (
                      <React.Fragment key={row.id}>
                        <tr className="border-t border-slate-200">
                          <td className={TD}>
                            <button
                              type="button"
                              onClick={() => alih(row.id)}
                              aria-expanded={terbuka}
                              aria-controls={id}
                              aria-label={`Rincian ${row.sub_kegiatan || row.program || "kegiatan"}`}
                              className="inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#117A69] sm:h-9 sm:w-9"
                            >
                              {terbuka
                                ? <ChevronDown className="h-4 w-4" aria-hidden="true" />
                                : <ChevronRight className="h-4 w-4" aria-hidden="true" />}
                            </button>
                          </td>
                          <td className={`${TD} font-semibold text-slate-900`}>{teks(row.opd)}</td>
                          <td className={TD}>{teks(row.program)}</td>
                          <td className={TD}>{teks(row.sub_kegiatan)}</td>
                          <td className={TD_NUM}>{rupiah(row.anggaran_2025)}</td>
                          <td className={TD_NUM}>{rupiah(row.realisasi_2025)}</td>
                          <td className={TD_NUM}>{persen(row.serapan_2025)}</td>
                          <td className={TD_NUM}>{rupiah(row.anggaran_2026)}</td>
                          <td className={TD_NUM}>{rupiah(row.realisasi_2026)}</td>
                        </tr>
                        <BarisDetail
                          id={id}
                          terbuka={terbuka}
                          label="Rincian kegiatan disabilitas"
                          colSpan={9}
                          isi={DETAIL_DISABILITAS.map(
                            ([k, label]) => [label, teks(row[k])] as [string, React.ReactNode],
                          )}
                        />
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </TabelGulir>
            <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
              Sumber: matriks monev kegiatan disabilitas per OPD (23 lembar). Baris dengan nilai
              keuangan identik digabung agar anggaran tidak terhitung ganda. Angka 2026 adalah
              target dan realisasi berjalan.
            </p>
            <div className="mt-3">
              <PanelImpor jenis="disabilitas" label="Matriks Disabilitas" tahun={2026} onSelesai={muat} />
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}

function MatriksOppkpke() {
  const [semester, setSemester] = useState(1);
  const [tahun, setTahun] = useState(() => new Date().getFullYear());
  const [data, setData] = useState<any>(null);
  const [memuat, setMemuat] = useState(true);
  const [galat, setGalat] = useState("");
  const [buka, setBuka] = useState<Record<string, boolean>>({});
  const { user } = useAuth();
  const bolehTulis = WRITERS.includes(user?.role || "");

  const muat = useCallback(async () => {
    setMemuat(true);
    setGalat("");
    try {
      const r = await api.get("/matriks/oppkpke", { params: { semester, tahun } });
      setData(r.data);
    } catch (er: any) {
      setData(null);
      setGalat(formatApiErrorDetail(er?.response?.data?.detail));
    } finally {
      setMemuat(false);
    }
  }, [semester, tahun]);

  useEffect(() => { muat(); }, [muat]);

  const ringkas = data?.ringkasan || {};
  const items: any[] = Array.isArray(data?.items) ? data.items : [];
  const periodeTeks = `Semester ${semester} · Tahun ${tahun}`;
  const judulTabel = `Matriks Evaluasi OPPKPKE ${periodeTeks}`;

  return (
    <div className="space-y-4" data-testid="matriks-oppkpke">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="font-head text-sm font-bold text-slate-800">Evaluasi OPPKPKE — {periodeTeks}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            Kertas kerja resmi OPPKPKE: strategi, aktivitas real, alokasi anggaran, realisasi 2025,
            dan target 2026. Angka berasal dari berkas resmi yang diimpor.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <SemesterPicker semester={semester} onChange={setSemester} />
          <TahunPicker tahun={tahun} onTerapkan={setTahun} label="Tahun anggaran" />
        </div>
      </div>

      {galat && (
        <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {galat}
        </div>
      )}

      {memuat ? (
        <p className="text-sm text-slate-500" aria-live="polite">Memuat matriks…</p>
      ) : items.length === 0 ? (
        <div className={`${KARTU} border-dashed`} data-testid="matriks-kosong-oppkpke">
          <p className="flex items-center gap-2 font-head text-sm font-bold text-slate-800">
            <ClipboardCheck className="h-4 w-4 text-[#117A69]" aria-hidden="true" />
            Data Evaluasi OPPKPKE {periodeTeks} belum tersedia
          </p>
          <p className="mt-1 text-sm leading-relaxed text-slate-600">
            {bolehTulis
              ? "Sistem tidak mengisi angka secara otomatis. Siapkan kertas kerja resmi, unduh template di bawah, isi sesuai kolom, lalu unggah kembali."
              : "Data diisi dari berkas resmi oleh Admin Bappeda atau Operator; hubungi mereka bila matriks ini diperlukan."}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Kegiatan"
              value={angka(ringkas.jumlah_kegiatan)}
              hint={`${angka(ringkas.jumlah_opd)} OPD · ${angka(ringkas.jumlah_program)} program`}
              testid="kpi-kegiatan-oppkpke"
            />
            <KpiCard
              label="Total Anggaran"
              value={rupiahRingkas(ringkas.total_anggaran)}
              hint={rupiah(ringkas.total_anggaran)}
              testid="kpi-anggaran-oppkpke"
            />
            <KpiCard
              label="Realisasi Sem 1 2025"
              value={rupiahRingkas(ringkas.total_realisasi_sem1_2025)}
              hint={rupiah(ringkas.total_realisasi_sem1_2025)}
              testid="kpi-realisasi-sem1-oppkpke"
            />
            <KpiCard
              label="Total Realisasi 2025"
              value={rupiahRingkas(ringkas.total_realisasi_2025)}
              hint={rupiah(ringkas.total_realisasi_2025)}
              color="#117A69"
              testid="kpi-realisasi-2025-oppkpke"
            />
          </div>

          <Panel
            title="Tabel Evaluasi OPPKPKE"
            action={<span className="text-[11px] font-semibold text-slate-500">{periodeTeks}</span>}
            testid="matriks-tabel-panel-oppkpke"
          >
            <TabelGulir label={judulTabel}>
              <table className="w-full min-w-[1080px] border-collapse text-sm">
                <caption className="sr-only">{judulTabel}</caption>
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className={`${TH} text-right`}>No</th>
                    {KOLOM_OPDKPKE.map(([key, label, num]) => (
                      <th key={key} scope="col" className={`${TH} ${num ? "text-right" : ""}`}>{label}</th>
                    ))}
                    <th scope="col" className={TH}>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((row, i) => {
                    const kunci = row.id || String(i);
                    const terbuka = !!buka[kunci];
                    const detailId = `detail-oppkpke-${kunci}`;
                    return (
                      <React.Fragment key={kunci}>
                        <tr className="border-t border-slate-200 align-top">
                          <td className={`${TD} text-right text-slate-500`}>{teks(row.no ?? i + 1)}</td>
                          {KOLOM_OPDKPKE.map(([key, , num]) => (
                            <td key={key} className={num ? TD_NUM : TD}>
                              {num ? rupiah(row[key]) : teks(row[key])}
                            </td>
                          ))}
                          <td className={TD}>
                            <button
                              type="button"
                              onClick={() => setBuka((s) => ({ ...s, [kunci]: !s[kunci] }))}
                              aria-expanded={terbuka}
                              aria-controls={detailId}
                              aria-label={`${terbuka ? "Tutup" : "Buka"} detail baris ${i + 1}`}
                              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-md border border-slate-300 text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#117A69]"
                            >
                              {terbuka ? <ChevronDown className="h-4 w-4" aria-hidden="true" />
                                : <ChevronRight className="h-4 w-4" aria-hidden="true" />}
                            </button>
                          </td>
                        </tr>
                        <BarisDetail
                          id={detailId}
                          terbuka={terbuka}
                          label={`Detail kegiatan ${teks(row.no ?? i + 1)}`}
                          colSpan={KOLOM_OPDKPKE.length + 2}
                          isi={DETAIL_OPDKPKE.map(([key, label]): [string, React.ReactNode] =>
                            [label, teks(row[key])])}
                        />
                      </React.Fragment>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-slate-300 bg-slate-100 font-bold text-slate-900">
                    <td className={TD} colSpan={4}>Total</td>
                    <td className={TD_NUM}>{angka(ringkas.total_anggaran)}</td>
                    <td className={TD_NUM}>{angka(ringkas.total_realisasi_sem1_2025)}</td>
                    <td className={TD_NUM}>{angka(ringkas.total_realisasi_2025)}</td>
                    <td className={TD}>-</td>
                    <td className={TD}>-</td>
                  </tr>
                </tfoot>
              </table>
            </TabelGulir>
            <p className="mt-2 text-[11px] text-slate-500">
              Tekan tombol <b>Detail</b> pada baris untuk melihat strategi, aktivitas real, sumber
              pembiayaan, sifat bantuan, lokasi, sasaran, besaran manfaat, jenis bantuan, dan durasi.
              {ringkas.diperbarui ? ` Terakhir diperbarui ${new Date(ringkas.diperbarui).toLocaleString("id-ID")}.` : ""}
            </p>
          </Panel>
        </>
      )}

      <PanelImpor
        jenis="oppkpke"
        label="Evaluasi OPPKPKE"
        semester={semester}
        tahun={tahun}
        onSelesai={muat}
      />
    </div>
  );
}

function MatriksAts() {
  const [tahun, setTahun] = useState(2026);
  const [data, setData] = useState<any>(null);
  const [memuat, setMemuat] = useState(true);
  const [galat, setGalat] = useState("");
  const [buka, setBuka] = useState<Record<string, boolean>>({});
  const { user } = useAuth();
  const bolehTulis = WRITERS.includes(user?.role || "");

  const muat = useCallback(async () => {
    setMemuat(true);
    setGalat("");
    try {
      const r = await api.get("/matriks/ats-program", { params: { tahun } });
      setData(r.data);
    } catch (er: any) {
      setData(null);
      setGalat(formatApiErrorDetail(er?.response?.data?.detail));
    } finally {
      setMemuat(false);
    }
  }, [tahun]);

  useEffect(() => { muat(); }, [muat]);

  const ringkas = data?.ringkasan || {};
  const perTahun = ringkas.per_tahun || {};
  const items: any[] = Array.isArray(data?.items) ? data.items : [];
  const periodeTeks = `Tahun ${tahun}`;
  const judulTabel = `Matriks Program Kegiatan ATS ${periodeTeks}`;

  const kolom = useMemo<Array<[string, string, boolean]>>(() => {
    const dasar: Array<[string, string, boolean]> = [
      ["opd", "OPD", false],
      ["program", "Program", false],
      ["kegiatan", "Kegiatan", false],
      ["sub_kegiatan", "Sub Kegiatan", false],
    ];
    if (tahun === 2027) {
      return [...dasar, ["anggaran_2027", "Anggaran 2027 (Rp)", true]];
    }
    return [
      ...dasar,
      [`target_${tahun}`, "Target", false],
      [`anggaran_${tahun}`, "Anggaran (Rp)", true],
      [`realisasi_${tahun}`, "Realisasi (Rp)", true],
      [`persen_${tahun}`, "Capaian", true],
    ];
  }, [tahun]);

  return (
    <div className="space-y-4" data-testid="matriks-ats-program">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="font-head text-sm font-bold text-slate-800">Program Kegiatan ATS — {periodeTeks}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            Matriks program, kegiatan, dan anggaran penanganan Anak Tidak Sekolah. Angka berasal dari
            berkas resmi yang diimpor.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label htmlFor="tahun-ats" className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Tahun anggaran
            </label>
            <select
              id="tahun-ats"
              value={tahun}
              onChange={(e) => setTahun(Number(e.target.value))}
              className={`${INPUT} w-32`}
            >
              {(data?.tahun_tersedia || [2025, 2026, 2027]).map((t: number) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {galat && (
        <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {galat}
        </div>
      )}

      {memuat ? (
        <p className="text-sm text-slate-500" aria-live="polite">Memuat matriks…</p>
      ) : items.length === 0 ? (
        <div className={`${KARTU} border-dashed`} data-testid="matriks-kosong-ats-program">
          <p className="flex items-center gap-2 font-head text-sm font-bold text-slate-800">
            <ClipboardCheck className="h-4 w-4 text-[#117A69]" aria-hidden="true" />
            Data Program Kegiatan ATS {periodeTeks} belum tersedia
          </p>
          <p className="mt-1 text-sm leading-relaxed text-slate-600">
            {bolehTulis
              ? "Sistem tidak mengisi angka secara otomatis. Unduh template di bawah, isi sesuai kolom resmi, lalu unggah kembali."
              : "Data diisi dari berkas resmi oleh Admin Bappeda atau Operator; hubungi mereka bila matriks ini diperlukan."}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Program/Kegiatan"
              value={angka(ringkas.jumlah_program)}
              hint={`${angka(ringkas.jumlah_opd)} OPD`}
              testid="kpi-program-ats"
            />
            <KpiCard
              label={`Anggaran ${tahun}`}
              value={rupiahRingkas(ringkas.anggaran)}
              hint={rupiah(ringkas.anggaran)}
              testid="kpi-anggaran-ats"
            />
            <KpiCard
              label={`Realisasi ${tahun}`}
              value={tahun === 2027 ? "-" : rupiahRingkas(ringkas.realisasi)}
              hint={tahun === 2027 ? "Belum tersedia" : rupiah(ringkas.realisasi)}
              testid="kpi-realisasi-ats"
            />
            <KpiCard
              label={`Serapan ${tahun}`}
              value={tahun === 2027 ? "-" : persen(ringkas.serapan_persen)}
              hint={tahun === 2027 ? "Belum tersedia" : "Realisasi ÷ anggaran"}
              color="#117A69"
              testid="kpi-serapan-ats"
            />
          </div>

          <Panel
            title="Tabel Program Kegiatan ATS"
            action={<span className="text-[11px] font-semibold text-slate-500">{periodeTeks}</span>}
            testid="matriks-tabel-panel-ats-program"
          >
            <TabelGulir label={judulTabel}>
              <table className="w-full min-w-[1100px] border-collapse text-sm">
                <caption className="sr-only">{judulTabel}</caption>
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className={`${TH} text-right`}>No</th>
                    {kolom.map(([key, label, num]) => (
                      <th key={key} scope="col" className={`${TH} ${num ? "text-right" : ""}`}>{label}</th>
                    ))}
                    <th scope="col" className={TH}>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((row, i) => {
                    const kunci = row.id || String(i);
                    const terbuka = !!buka[kunci];
                    const detailId = `detail-ats-${kunci}`;
                    return (
                      <React.Fragment key={kunci}>
                        <tr className="border-t border-slate-200 align-top">
                          <td className={`${TD} text-right text-slate-500`}>{teks(row.no ?? i + 1)}</td>
                          {kolom.map(([key, , num]) => (
                            <td key={key} className={num ? TD_NUM : TD}>
                              {num
                                ? (key.startsWith("persen_") ? persen(row[key]) : rupiah(row[key]))
                                : teks(row[key])}
                            </td>
                          ))}
                          <td className={TD}>
                            <button
                              type="button"
                              onClick={() => setBuka((s) => ({ ...s, [kunci]: !s[kunci] }))}
                              aria-expanded={terbuka}
                              aria-controls={detailId}
                              aria-label={`${terbuka ? "Tutup" : "Buka"} detail baris ${i + 1}`}
                              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-md border border-slate-300 text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#117A69]"
                            >
                              {terbuka ? <ChevronDown className="h-4 w-4" aria-hidden="true" />
                                : <ChevronRight className="h-4 w-4" aria-hidden="true" />}
                            </button>
                          </td>
                        </tr>
                        <BarisDetail
                          id={detailId}
                          terbuka={terbuka}
                          label={`Detail program ${teks(row.no ?? i + 1)}`}
                          colSpan={kolom.length + 2}
                          isi={DETAIL_ATS.map(([key, label]): [string, React.ReactNode] => {
                            const nilai = row[key];
                            const angkaField = key.startsWith("anggaran_") || key.startsWith("realisasi_");
                            const persenField = key.startsWith("persen_");
                            return [label, angkaField ? rupiah(nilai) : persenField ? persen(nilai) : teks(nilai)];
                          })}
                        />
                      </React.Fragment>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-slate-300 bg-slate-100 font-bold text-slate-900">
                    <td className={TD} colSpan={5}>Total</td>
                    <td className={TD_NUM}>-</td>
                    <td className={TD_NUM}>{angka(ringkas.anggaran)}</td>
                    {tahun !== 2027 && (
                      <>
                        <td className={TD_NUM}>{angka(ringkas.realisasi)}</td>
                        <td className={TD_NUM}>{persen(ringkas.serapan_persen)}</td>
                      </>
                    )}
                    <td className={TD}>-</td>
                  </tr>
                </tfoot>
              </table>
            </TabelGulir>
            <p className="mt-2 text-[11px] text-slate-500">
              Serapan = realisasi ÷ anggaran. Pilih tahun lain untuk melihat target, realisasi, dan
              capaian tahun tersebut; rincian semua tahun tersedia pada tombol <b>Detail</b>.
              {Object.keys(perTahun).length > 0 && (
                <> Ringkasan: {Object.entries(perTahun).map(([th, v]: any) =>
                  `${th}: ${rupiah(v.anggaran)}`).join(" · ")}.</>
              )}
            </p>
          </Panel>
        </>
      )}

      <PanelImpor
        jenis="ats-program"
        label="Program Kegiatan ATS"
        tahun={2026}
        onSelesai={muat}
      />
    </div>
  );
}

/** Matriks kemiskinan, stunting, ATS, dan anak jalanan per kecamatan (data basis data). */
function MatriksKategori() {
  const [data, setData] = useState<any>(null);
  const [memuat, setMemuat] = useState(true);
  const [galat, setGalat] = useState("");

  useEffect(() => {
    let aktif = true;
    api.get("/matriks/kategori")
      .then((r) => { if (aktif) setData(r.data); })
      .catch((er: any) => { if (aktif) setGalat(formatApiErrorDetail(er?.response?.data?.detail)); })
      .finally(() => { if (aktif) setMemuat(false); });
    return () => { aktif = false; };
  }, []);

  if (memuat) return <p className="text-sm text-slate-500" aria-live="polite">Memuat matriks…</p>;
  if (galat) {
    return <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{galat}</div>;
  }

  const items: any[] = Array.isArray(data?.items) ? data.items : [];
  const total = data?.total || {};
  const jumlahKecamatan = data?.jumlah_kecamatan ?? items.length;

  return (
    <div className="space-y-4" data-testid="matriks-kategori">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Kemiskinan Ekstrem" value={angka(total.kemiskinan_ekstrim_kk)} hint="Kepala keluarga (KK)" color="#3B4F6B" testid="kpi-kemiskinan" />
        <KpiCard label="Anak Stunting" value={angka(total.stunting_anak)} hint="Anak" color="#C8375B" testid="kpi-stunting" />
        <KpiCard label="Anak Tidak Sekolah" value={angka(total.ats)} hint="Anak (ATS)" color="#8A5A00" testid="kpi-ats" />
        <KpiCard label="Anak Jalanan" value={angka(total.anak_jalanan)} hint="Anak" color="#117A69" testid="kpi-anak-jalanan" />
      </div>

      <Panel
        title="Matriks Kemiskinan, Stunting, ATS, dan Anak Jalanan"
        action={<span className="text-[11px] font-semibold text-slate-500">{jumlahKecamatan} kecamatan</span>}
        testid="matriks-kategori-panel"
      >
        <TabelGulir label="Matriks kemiskinan, stunting, ATS, dan anak jalanan per kecamatan">
          <table className="w-full min-w-[780px] border-collapse text-sm">
            <caption className="sr-only">
              Jumlah kemiskinan ekstrem, stunting, anak tidak sekolah, dan anak jalanan per kecamatan
              di Kota Makassar.
            </caption>
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className={TH}>Kecamatan</th>
                <th scope="col" className={`${TH} text-right`}>Kelurahan</th>
                <th scope="col" className={`${TH} text-right`}>Kemiskinan Ekstrem (KK)</th>
                <th scope="col" className={`${TH} text-right`}>% Miskin</th>
                <th scope="col" className={`${TH} text-right`}>Stunting (anak)</th>
                <th scope="col" className={`${TH} text-right`}>ATS (anak)</th>
                <th scope="col" className={`${TH} text-right`}>Anak Jalanan</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.kecamatan} className="border-t border-slate-200">
                  <td className={`${TD} font-semibold text-slate-900`}>{row.kecamatan}</td>
                  <td className={TD_NUM}>{angka(row.jumlah_kelurahan)}</td>
                  <td className={TD_NUM}>{angka(row.kemiskinan_ekstrim_kk)}</td>
                  <td className={TD_NUM}>{persen(row.kemiskinan_persen)}</td>
                  <td className={TD_NUM}>{angka(row.stunting_anak)}</td>
                  <td className={TD_NUM}>{angka(row.ats)}</td>
                  <td className={TD_NUM}>{angka(row.anak_jalanan)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-300 bg-slate-100 font-bold text-slate-900">
                <td className={TD}>TOTAL</td>
                <td className={TD_NUM}>{angka(total.jumlah_kelurahan)}</td>
                <td className={TD_NUM}>{angka(total.kemiskinan_ekstrim_kk)}</td>
                <td className={TD_NUM}>-</td>
                <td className={TD_NUM}>{angka(total.stunting_anak)}</td>
                <td className={TD_NUM}>{angka(total.ats)}</td>
                <td className={TD_NUM}>{angka(total.anak_jalanan)}</td>
              </tr>
            </tfoot>
          </table>
        </TabelGulir>
        <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
          Sumber: {data?.sumber || "Matriks Bappeda Kota Makassar"}. Persentase kemiskinan adalah
          proporsi penduduk miskin per kecamatan sehingga tidak dijumlahkan pada baris total.
          Angka kemiskinan ekstrem dalam satuan kepala keluarga (KK). Data stunting 2026 dan
          disabilitas rinci tersedia untuk Kec. Tallo dan Kec. Makassar; kecamatan lain mengikuti
          rekap terakhir.
        </p>
      </Panel>
    </div>
  );
}

export default function Matriks() {
  const tabs = useMemo(() => [
    { id: "oppkpke", label: "Evaluasi OPPKPKE Semester 1", icon: ClipboardCheck },
    { id: "kategori", label: "Kemiskinan, Stunting, ATS, Anak Jalanan", icon: BarChart3 },
    { id: "ats", label: "Program Kegiatan ATS", icon: GraduationCap },
    { id: "disabilitas", label: "Matriks Disabilitas", icon: Accessibility },
  ], []);
  // Tautan langsung ke tab: /matriks?tab=kategori (dipakai juga oleh uji axe).
  const [pilih, setPilih] = useState(() => {
    try {
      const q = new URLSearchParams(window.location.search).get("tab") || "";
      return tabs.some((t) => t.id === q) ? q : "";
    } catch {
      return "";
    }
  });
  const aktif = tabs.some((t) => t.id === pilih) ? pilih : tabs[0].id;

  return (
    <div data-testid="matriks-page">
      <PageHeader
        title="Matriks Evaluasi"
        subtitle="Evaluasi OPPKPKE, matriks kemiskinan–stunting–ATS–anak jalanan, program kegiatan ATS, dan monev kegiatan disabilitas dalam satu halaman."
      />
      <PageTabs tabs={tabs} value={aktif} onChange={setPilih} label="Jenis matriks" />
      <TabPanel id={aktif}>
        {aktif === "oppkpke" && <MatriksOppkpke />}
        {aktif === "kategori" && <MatriksKategori />}
        {aktif === "ats" && <MatriksAts />}
        {aktif === "disabilitas" && <MatriksDisabilitas />}
      </TabPanel>
    </div>
  );
}
