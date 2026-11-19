import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  AlertTriangle, CheckCircle2, ChevronRight, Download, FileSpreadsheet, History,
  Loader2, Play, RotateCcw, Table2, Upload, XCircle,
} from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, Panel } from "@/features/data/ui";
import { fmtNum } from "@/features/data/api";

const STEPS = ["Upload", "Mapping Kolom", "Validasi", "Preview", "Impor", "Selesai"];
const MODES = [
  { id: "update", label: "Perbarui data lama (upsert)" },
  { id: "update_changed", label: "Perbarui hanya field yang berubah" },
  { id: "skip", label: "Lewati data yang sudah ada" },
];

export default function ImportWizard() {
  const { user } = useAuth();
  const isSuper = ["superadmin", "admin"].includes(String(user?.role || ""));
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [session, setSession] = useState<any>(null);
  const [jenis, setJenis] = useState("dtsen");
  const [analisa, setAnalisa] = useState<any>(null);
  const [sheetsDipilih, setSheetsDipilih] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [validasi, setValidasi] = useState<any>(null);
  const [mode, setMode] = useState("update");
  const [job, setJob] = useState<any>(null);
  const [riwayat, setRiwayat] = useState<any[]>([]);

  const muatRiwayat = useCallback(() => {
    api.get("/import/history", { params: { limit: 20 } })
      .then((r) => setRiwayat(r.data.items || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    api.get("/import/datasets").then((r) => setDatasets(r.data.datasets || [])).catch(() => {});
    muatRiwayat();
  }, [muatRiwayat]);

  const fields = useMemo(
    () => (analisa?.fields || datasets.find((d) => d.jenis === jenis)?.fields || []),
    [analisa, datasets, jenis],
  );

  /* ---------------- STEP 1: upload ---------------- */
  const onUpload = async (f: File) => {
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const { data } = await api.post("/import/upload", fd,
        { headers: { "Content-Type": "multipart/form-data" } });
      setSession(data);
      setJenis(data.jenis_terdeteksi || "dtsen");
      setValidasi(null);
      setJob(null);
      await jalankanAnalisa(data.id, data.jenis_terdeteksi);
      setStep(1);
      toast.success(`Berkas terbaca: ${data.sheets?.length || 0} sheet, ${fmtNum(data.total_rows)} baris`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Berkas gagal diunggah/dibaca");
    } finally {
      setBusy(false);
    }
  };

  const jalankanAnalisa = async (sessionId: string, j?: string) => {
    const { data } = await api.post("/import/analyze", { session_id: sessionId, jenis: j || jenis });
    setAnalisa(data);
    setJenis(data.jenis);
    const siap = (data.sheets || []).filter((s: any) => s.rows > 0).map((s: any) => s.sheet);
    setSheetsDipilih(siap);
    setMapping((data.sheets || []).find((s: any) => s.rows > 0)?.mapping || {});
    return data;
  };

  const gantiJenis = async (j: string) => {
    if (!session) { setJenis(j); return; }
    setBusy(true);
    try {
      await jalankanAnalisa(session.id, j);
      setValidasi(null);
    } finally {
      setBusy(false);
    }
  };

  /* ---------------- STEP 3: validasi ---------------- */
  const jalankanValidasi = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/import/validate", {
        session_id: session.id, jenis, sheets: sheetsDipilih, mapping,
      });
      setValidasi(data);
      setStep(2);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Validasi gagal");
    } finally {
      setBusy(false);
    }
  };

  const unduhLaporanError = async (format: "xlsx" | "csv") => {
    try {
      const res = await api.get(`/import/errors/${session.id}`, {
        params: { format }, responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `laporan_error.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Laporan error gagal diunduh");
    }
  };

  const unduhTemplate = async () => {
    try {
      const res = await api.get("/import/template", { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "Template_Impor_SIDATA.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Template gagal diunduh");
    }
  };

  /* ---------------- STEP 5: impor ---------------- */
  const mulaiImpor = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/import/execute", {
        session_id: session.id, jenis, sheets: sheetsDipilih, mapping, mode,
      });
      setJob({ status: "menunggu", processed: 0, total: validasi?.total || 0 });
      setStep(4);
      pantauJob(data.job_id);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Impor tidak dapat dimulai");
    } finally {
      setBusy(false);
    }
  };

  const pantauJob = (jobId: string) => {
    const timer = setInterval(async () => {
      try {
        const { data } = await api.get(`/import/job/${jobId}`);
        setJob(data);
        if (data.status === "selesai" || data.status === "gagal") {
          clearInterval(timer);
          muatRiwayat();
          setStep(5);
          if (data.status === "selesai") toast.success(data.pesan || "Impor selesai");
          else toast.error(data.pesan || "Impor gagal");
        }
      } catch {
        clearInterval(timer);
      }
    }, 1500);
  };

  const batalkanBatch = async (batchId: string) => {
    if (!window.confirm("Batalkan batch impor ini? Seluruh data dari batch tersebut akan dihapus.")) return;
    try {
      const { data } = await api.delete(`/import/batch/${batchId}`);
      toast.success(`Batch dibatalkan, ${fmtNum(data.dihapus)} baris dihapus`);
      muatRiwayat();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Batch gagal dibatalkan");
    }
  };

  const ulangDariAwal = () => {
    setStep(0);
    setSession(null);
    setAnalisa(null);
    setValidasi(null);
    setJob(null);
    setMapping({});
    setSheetsDipilih([]);
  };

  const wajibBelum = useMemo(
    () => fields.filter((f: any) => f.required && !Object.values(mapping).includes(f.name))
      .map((f: any) => f.label),
    [fields, mapping],
  );

  const kolomExcel = useMemo(() => {
    const s = (analisa?.sheets || []).find((x: any) => sheetsDipilih.includes(x.sheet))
      || (analisa?.sheets || [])[0];
    return s?.columns || [];
  }, [analisa, sheetsDipilih]);

  return (
    <div data-testid="page-import-wizard">
      <PageHeader
        title="Impor Data (Excel / CSV)"
        subtitle="Upload → Mapping Kolom → Validasi → Preview → Impor → Selesai"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" data-testid="btn-template" onClick={unduhTemplate}
              className="inline-flex h-10 items-center gap-1.5 rounded-md border border-slate-300 px-3 text-xs font-semibold text-slate-700 hover:bg-slate-100 sm:h-9">
              <Download className="h-4 w-4 shrink-0" /> Download Template Excel
            </button>
            <button type="button" data-testid="btn-input-data" onClick={() => fileRef.current?.click()}
              className="inline-flex h-10 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-bold text-primary-foreground hover:opacity-90 sm:h-9">
              <Upload className="h-4 w-4 shrink-0" /> + INPUT DATA (Import Excel/CSV)
            </button>
          </div>
        }
      />

      {/* stepper */}
      <div className="mb-4 flex flex-wrap items-center gap-1.5" data-testid="wizard-stepper">
        {STEPS.map((s, i) => (
          <span key={s} className="flex items-center gap-1.5">
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold ${
              i === step ? "bg-primary text-primary-foreground"
                : i < step ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>
              {i < step ? <CheckCircle2 className="h-3.5 w-3.5" /> : <span>{i + 1}</span>} {s}
            </span>
            {i < STEPS.length - 1 && <ChevronRight className="h-3.5 w-3.5 text-slate-300" />}
          </span>
        ))}
      </div>

      <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" className="hidden"
        data-testid="input-file"
        onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])} />

      {/* STEP 1 */}
      {step === 0 && (
        <Panel title="Langkah 1 — Unggah berkas" testid="panel-upload">
          <div
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) onUpload(f); }}
            className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 py-10 text-center hover:border-primary"
          >
            {busy ? <Loader2 className="h-8 w-8 animate-spin text-primary" />
              : <FileSpreadsheet className="h-8 w-8 text-slate-400" />}
            <p className="text-sm font-semibold text-slate-700">
              Klik atau tarik berkas ke sini
            </p>
            <p className="text-[11px] text-slate-500">
              Format didukung: .xlsx, .xls, .csv — mendukung berkas dengan banyak sheet
            </p>
          </div>
          <p className="mt-3 text-[11px] text-slate-500">
            Sistem akan membaca jumlah sheet, jumlah baris, jumlah kolom, dan menampilkan preview
            sebelum data masuk database. Tidak ada data yang tersimpan sampai Anda menekan
            tombol Impor pada langkah 5.
          </p>
        </Panel>
      )}

      {/* STEP 2 mapping */}
      {step === 1 && analisa && (
        <div className="grid gap-3 lg:grid-cols-3">
          <Panel title="Berkas & Sheet" testid="panel-sheets" className="lg:col-span-1">
            <p className="text-[11.5px] font-semibold text-slate-800">{session?.filename}</p>
            <p className="text-[11px] text-slate-500">
              {(session?.sheets || []).length} sheet · {fmtNum(session?.total_rows)} baris ·{" "}
              {Math.round((session?.size || 0) / 1024)} KB
            </p>
            <label className="mt-3 block text-[10px] font-bold uppercase text-slate-500">
              Jenis dataset tujuan
            </label>
            <select data-testid="select-jenis" value={jenis} onChange={(e) => gantiJenis(e.target.value)}
              className="mt-1 h-9 w-full rounded-md border border-slate-300 px-2 text-xs">
              {datasets.map((d) => <option key={d.jenis} value={d.jenis}>{d.label}</option>)}
            </select>
            <p className="mt-1 text-[10px] text-slate-500">
              Kunci anti-duplikat: {analisa.kunci_duplikat}
            </p>

            <p className="mt-3 text-[10px] font-bold uppercase text-slate-500">Pilih sheet</p>
            <ul className="mt-1 space-y-1">
              {(analisa.sheets || []).map((s: any) => (
                <li key={s.sheet}>
                  <label className="flex items-start gap-2 rounded border border-slate-100 bg-slate-50/60 p-1.5">
                    <input type="checkbox" data-testid={`sheet-${s.sheet}`}
                      disabled={s.rows === 0}
                      checked={sheetsDipilih.includes(s.sheet)}
                      onChange={() => setSheetsDipilih((cur) => cur.includes(s.sheet)
                        ? cur.filter((x) => x !== s.sheet) : [...cur, s.sheet])}
                      className="mt-[3px] h-3.5 w-3.5" />
                    <span className="flex-1">
                      <span className="block text-[11.5px] font-semibold text-slate-800">{s.sheet}</span>
                      <span className="block text-[10px] text-slate-500">
                        {fmtNum(s.rows)} baris · {s.columns?.length || 0} kolom
                        {s.rows === 0 ? " · kosong" : ""}
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Langkah 2 — Mapping kolom Excel ke field database"
            testid="panel-mapping" className="lg:col-span-2">
            {wajibBelum.length > 0 && (
              <p className="mb-2 flex items-start gap-1.5 rounded bg-amber-50 p-2 text-[11px] text-amber-900">
                <AlertTriangle className="mt-[1px] h-3.5 w-3.5 shrink-0" />
                Field wajib belum dipetakan: <b>{wajibBelum.join(", ")}</b>
              </p>
            )}
            <div className="table-scroll max-h-[420px] overflow-x-auto overflow-y-auto">
              <table className="w-full min-w-[480px] text-[11.5px]">
                <thead className="sticky top-0 bg-slate-50 text-left text-[10px] uppercase text-slate-500">
                  <tr><th className="p-1.5">Kolom Excel</th><th className="p-1.5">Field Database</th></tr>
                </thead>
                <tbody>
                  {kolomExcel.map((col: string) => (
                    <tr key={col} className="border-b border-slate-100">
                      <td className="p-1.5 font-mono text-[11px] text-slate-700">{col}</td>
                      <td className="p-1.5">
                        <select
                          data-testid={`map-${col}`}
                          value={mapping[col] || ""}
                          onChange={(e) => setMapping((m) => ({ ...m, [col]: e.target.value }))}
                          className="h-8 w-full rounded-md border border-slate-300 px-1.5 text-[11px]">
                          <option value="">— tidak diimpor —</option>
                          {fields.map((f: any) => (
                            <option key={f.name} value={f.name}>
                              {f.label}{f.required ? " (wajib)" : ""}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex items-center justify-between">
              <button type="button" onClick={ulangDariAwal}
                className="text-[11px] font-semibold text-slate-500 underline">Ganti berkas</button>
              <button type="button" data-testid="btn-validasi" disabled={busy || !sheetsDipilih.length}
                onClick={jalankanValidasi}
                className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-bold text-primary-foreground disabled:opacity-50">
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ChevronRight className="h-4 w-4" />}
                Lanjut: Validasi
              </button>
            </div>
          </Panel>
        </div>
      )}

      {/* STEP 3 validasi */}
      {step === 2 && validasi && (
        <Panel title="Langkah 3 — Hasil validasi" testid="panel-validasi">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
            {[
              ["Total baris", validasi.total, "text-slate-900"],
              ["Valid", validasi.valid, "text-emerald-700"],
              ["Warning", validasi.warning, "text-amber-700"],
              ["Error", validasi.error, "text-rose-700"],
              ["Duplikat (berkas/DB)", `${validasi.duplikat_internal} / ${validasi.duplikat_db}`, "text-slate-700"],
            ].map(([l, v, c]) => (
              <div key={String(l)} className="rounded-lg border border-slate-200 bg-white p-2.5">
                <p className="text-[10px] font-bold uppercase text-slate-500">{l}</p>
                <p className={`font-head text-lg font-extrabold ${c}`} data-testid={`val-${l}`}>
                  {typeof v === "number" ? fmtNum(v) : v}
                </p>
              </div>
            ))}
          </div>

          {validasi.issues_total > 0 && (
            <>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-[11px] text-slate-600">
                  {fmtNum(validasi.issues_total)} catatan masalah ditemukan (ditampilkan maksimal 200).
                </p>
                <span className="flex gap-1.5">
                  <button type="button" data-testid="btn-error-xlsx" onClick={() => unduhLaporanError("xlsx")}
                    className="inline-flex h-8 items-center gap-1 rounded border border-slate-300 px-2 text-[11px] font-semibold hover:bg-slate-100">
                    <Download className="h-3.5 w-3.5" /> Error Report (Excel)
                  </button>
                  <button type="button" onClick={() => unduhLaporanError("csv")}
                    className="inline-flex h-8 items-center gap-1 rounded border border-slate-300 px-2 text-[11px] font-semibold hover:bg-slate-100">
                    <Download className="h-3.5 w-3.5" /> CSV
                  </button>
                </span>
              </div>
              <div className="table-scroll mt-2 max-h-[280px] overflow-x-auto overflow-y-auto" tabIndex={0} role="region" aria-label="Pratinjau data yang akan diimpor">
                <table className="w-full min-w-[520px] text-[11px]">
                  <thead className="sticky top-0 bg-slate-50 text-left text-[10px] uppercase text-slate-500">
                    <tr>
                      <th className="p-1.5">Sheet</th><th className="p-1.5">Baris</th>
                      <th className="p-1.5">Tingkat</th><th className="p-1.5">Kolom</th>
                      <th className="p-1.5">Pesan</th>
                    </tr>
                  </thead>
                  <tbody data-testid="tabel-isu">
                    {(validasi.issues || []).map((it: any, i: number) => (
                      <tr key={i} className="border-b border-slate-100">
                        <td className="p-1.5">{it.sheet}</td>
                        <td className="p-1.5">{it.baris}</td>
                        <td className={`p-1.5 font-bold ${it.tingkat === "error" ? "text-rose-700" : "text-amber-700"}`}>
                          {it.tingkat}
                        </td>
                        <td className="p-1.5 font-mono text-[10px]">{it.kolom}</td>
                        <td className="p-1.5 text-slate-700">{it.pesan}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          <div className="mt-3 flex items-center justify-between">
            <button type="button" onClick={() => setStep(1)}
              className="text-[11px] font-semibold text-slate-500 underline">Kembali ke mapping</button>
            <button type="button" data-testid="btn-ke-preview" onClick={() => setStep(3)}
              className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-bold text-primary-foreground">
              <ChevronRight className="h-4 w-4" /> Lanjut: Preview
            </button>
          </div>
        </Panel>
      )}

      {/* STEP 4 preview */}
      {step === 3 && validasi && (
        <Panel title="Langkah 4 — Preview data yang akan masuk database" testid="panel-preview">
          <div className="max-h-[380px] overflow-auto">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-slate-50 text-left text-[10px] uppercase text-slate-500">
                <tr>
                  <th className="p-1.5">Status</th>
                  {Object.keys((validasi.preview || [])[0] || {})
                    .filter((k) => !["status"].includes(k))
                    .slice(0, 10)
                    .map((k) => <th key={k} className="p-1.5">{k}</th>)}
                </tr>
              </thead>
              <tbody data-testid="tabel-preview">
                {(validasi.preview || []).map((r: any, i: number) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className={`p-1.5 font-bold ${r.status === "error" ? "text-rose-700"
                      : r.status === "warning" ? "text-amber-700" : "text-emerald-700"}`}>{r.status}</td>
                    {Object.keys((validasi.preview || [])[0] || {})
                      .filter((k) => !["status"].includes(k))
                      .slice(0, 10)
                      .map((k) => <td key={k} className="p-1.5 text-slate-700">{String(r[k] ?? "")}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-2">
              <label className="text-[11px] font-semibold text-slate-600">Bila data sudah ada:</label>
              <select data-testid="select-mode" value={mode} onChange={(e) => setMode(e.target.value)}
                className="h-9 rounded-md border border-slate-300 px-2 text-xs">
                {MODES.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
              </select>
            </span>
            <span className="flex gap-2">
              <button type="button" onClick={ulangDariAwal}
                className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-300 px-3 text-xs font-semibold">
                <XCircle className="h-4 w-4" /> Batalkan
              </button>
              <button type="button" data-testid="btn-import" disabled={busy} onClick={mulaiImpor}
                className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-bold text-primary-foreground disabled:opacity-50">
                <Play className="h-4 w-4" /> Impor {fmtNum(validasi.total)} baris
              </button>
            </span>
          </div>
        </Panel>
      )}

      {/* STEP 5 progres */}
      {step === 4 && (
        <Panel title="Langkah 5 — Proses impor" testid="panel-progres">
          <p className="text-sm font-semibold text-slate-800">
            Importing {fmtNum(job?.processed || 0)} / {fmtNum(job?.total || validasi?.total || 0)}
          </p>
          <div className="mt-2 h-3 w-full overflow-hidden rounded-full bg-slate-200">
            <div className="h-3 rounded-full bg-primary transition-all"
              style={{ width: `${job?.persen || 0}%` }} />
          </div>
          <p className="mt-2 text-[11px] text-slate-600">
            {job?.pesan || "Impor berjalan di latar belakang, halaman ini dapat ditinggalkan."}
          </p>
        </Panel>
      )}

      {/* STEP 6 selesai */}
      {step === 5 && job && (
        <Panel title="Langkah 6 — Selesai" testid="panel-selesai">
          <p className={`flex items-center gap-2 text-sm font-bold ${
            job.status === "selesai" ? "text-emerald-700" : "text-rose-700"}`}>
            {job.status === "selesai" ? <CheckCircle2 className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
            {job.status === "selesai" ? "Import berhasil" : "Import tidak selesai"}
          </p>
          <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
            {[["Data baru", job.inserted], ["Data diperbarui", job.updated],
              ["Duplikat dilewati", job.skipped], ["Error", job.failed]].map(([l, v]) => (
              <div key={String(l)} className="rounded-lg border border-slate-200 bg-white p-2.5">
                <p className="text-[10px] font-bold uppercase text-slate-500">{l}</p>
                <p className="font-head text-lg font-extrabold text-slate-900"
                  data-testid={`hasil-${l}`}>{fmtNum(v as number)}</p>
              </div>
            ))}
          </div>
          {job.pesan && <p className="mt-2 text-[11px] text-slate-600">{job.pesan}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" onClick={ulangDariAwal}
              className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-bold text-primary-foreground">
              <Upload className="h-4 w-4" /> Impor berkas lain
            </button>
            <a href="/rumah-tangga"
              className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-300 px-3 text-xs font-semibold text-slate-700">
              <Table2 className="h-4 w-4" /> Lihat tabel data
            </a>
            {(job.failed > 0 || validasi?.issues_total > 0) && (
              <button type="button" onClick={() => unduhLaporanError("xlsx")}
                className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-300 px-3 text-xs font-semibold text-slate-700">
                <Download className="h-4 w-4" /> Download Error Report
              </button>
            )}
          </div>
        </Panel>
      )}

      {/* Riwayat impor */}
      <div className="mt-4">
        <Panel title="Riwayat impor" testid="panel-riwayat"
          action={<button type="button" onClick={muatRiwayat}
            className="inline-flex h-8 items-center gap-1 rounded border border-slate-300 px-2 text-[11px] font-semibold">
            <History className="h-3.5 w-3.5" /> Muat ulang</button>}>
          <div className="table-scroll max-h-[280px] overflow-x-auto overflow-y-auto" tabIndex={0} role="region" aria-label="Riwayat impor">
            <table className="w-full min-w-[720px] text-[11px]">
              <thead className="sticky top-0 bg-slate-50 text-left text-[10px] uppercase text-slate-500">
                <tr>
                  <th className="p-1.5">Waktu</th><th className="p-1.5">Berkas / Sheet</th>
                  <th className="p-1.5">Jenis</th><th className="p-1.5 text-right">Baru</th>
                  <th className="p-1.5 text-right">Diperbarui</th><th className="p-1.5 text-right">Dilewati</th>
                  <th className="p-1.5 text-right">Gagal</th><th className="p-1.5">Status</th>
                  {isSuper && <th className="p-1.5">Aksi</th>}
                </tr>
              </thead>
              <tbody data-testid="tabel-riwayat">
                {riwayat.map((b) => (
                  <tr key={b.id} className="border-b border-slate-100">
                    <td className="p-1.5 text-slate-500">
                      {String(b.uploaded_at || "").slice(0, 16).replace("T", " ")}
                    </td>
                    <td className="p-1.5 font-semibold text-slate-800">
                      {b.filename}
                      <span className="block text-[10px] font-normal text-slate-500">{b.sheet}</span>
                    </td>
                    <td className="p-1.5">{b.jenis}</td>
                    <td className="p-1.5 text-right">{fmtNum(b.inserted)}</td>
                    <td className="p-1.5 text-right">{fmtNum(b.updated)}</td>
                    <td className="p-1.5 text-right">{fmtNum(b.duplicate)}</td>
                    <td className="p-1.5 text-right">{fmtNum(b.failed)}</td>
                    <td className="p-1.5">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                        b.status === "success" ? "bg-emerald-100 text-emerald-800"
                          : b.status === "dibatalkan" ? "bg-slate-200 text-slate-600"
                            : b.status === "failed" ? "bg-rose-100 text-rose-800"
                              : "bg-amber-100 text-amber-800"}`}>{b.status}</span>
                    </td>
                    {isSuper && (
                      <td className="p-1.5">
                        {b.status !== "dibatalkan" && b.sumber === "wizard" && (
                          <button type="button" data-testid={`btn-rollback-${b.id}`}
                            onClick={() => batalkanBatch(b.id)}
                            className="inline-flex items-center gap-1 rounded border border-rose-300 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700 hover:bg-rose-50">
                            <RotateCcw className="h-3 w-3" /> Batalkan
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
                {!riwayat.length && (
                  <tr><td colSpan={isSuper ? 9 : 8} className="p-3 text-center text-slate-500">
                    Belum ada riwayat impor.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </div>
  );
}
