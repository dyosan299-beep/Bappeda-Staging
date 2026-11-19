import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { Search, Pencil, X, FileEdit, Trash2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { KpiCard, Panel, PageHeader } from "@/features/data/ui";
import { fmtNum, getRadItems, getRadOverview, putRadMonitoring } from "@/features/data/api";
import { createRad, deleteRad, getRadForm, updateRad } from "@/features/data/manageApi";
import DynamicForm from "@/features/data/DynamicForm";
import ExportButtons from "@/features/data/ExportButtons";
import { InputDataButton, KonfirmasiHapus } from "@/features/data/InputDataButton";
import { bolehHapus as cekHapus, bolehTulis as cekTulis } from "@/features/data/roles";

const STATUS = ["Belum Dimulai", "Dalam Perencanaan", "Sedang Berjalan", "Selesai", "Tertunda"];

export default function RadDisabilitas() {
  const { user } = useAuth() as { user: any };
  const canEdit = cekTulis(user?.role);
  const canDelete = cekHapus(user?.role);
  const [form, setForm] = useState<{ id: string | null; data: any } | null>(null);
  const [hapus, setHapus] = useState<any>(null);
  const [ov, setOv] = useState<any>(null);
  const [items, setItems] = useState<any>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("semua");
  const [page, setPage] = useState(1);
  const [edit, setEdit] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  const loadOv = useCallback(() => {
    getRadOverview().then(setOv).catch(() => toast.error("Gagal memuat ringkasan RAD"));
  }, []);
  const load = useCallback(() => {
    getRadItems({ search: search || undefined, status: status === "semua" ? undefined : status, page, size: 15 })
      .then(setItems)
      .catch(() => toast.error("Gagal memuat item RAD"));
  }, [search, status, page]);

  useEffect(() => { loadOv(); }, [loadOv]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(1); }, [search, status]);

  const simpan = async () => {
    if (!edit) return;
    setSaving(true);
    try {
      await putRadMonitoring(edit.id, {
        status: edit.monitoring.status,
        progress: Number(edit.monitoring.progress) || 0,
        catatan: edit.monitoring.catatan || "",
        dokumen: edit.monitoring.dokumen || "",
        penanggung_jawab: edit.monitoring.penanggung_jawab || "",
      });
      toast.success("Monitoring diperbarui");
      setEdit(null);
      load();
      loadOv();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan monitoring");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div data-testid="page-rad">
      <PageHeader title="RAD Penyandang Disabilitas 2025-2030"
        subtitle="Sumber: Matriks RAD PD OPD · monitoring status & progres per kegiatan"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ExportButtons jalur="rad" testid="rad-export" filter={{ search: search || undefined }} />
            {canEdit && (
              <InputDataButton jenis="rad" testid="btn-input-rad"
                onManual={() => setForm({ id: null, data: {} })} />
            )}
          </div>
        } />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard testid="kpi-rad-strategi" label="Sasaran Strategis" value={fmtNum(ov?.jumlah_strategi)} />
        <KpiCard label="Kebijakan" value={fmtNum(ov?.jumlah_kebijakan)} />
        <KpiCard label="Program" value={fmtNum(ov?.jumlah_program)} color="#4f46e5" />
        <KpiCard label="Kegiatan" value={fmtNum(ov?.jumlah_kegiatan)} color="#0891b2" />
        <KpiCard label="Item Matriks" value={fmtNum(ov?.jumlah_item)} />
        <KpiCard label="Rata-rata Progres" value={`${ov?.rata_progress ?? 0}%`} color="#16a34a" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="Total Target Kegiatan per Tahun" testid="chart-rad-target">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={ov?.target_per_tahun || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="tahun" fontSize={11} />
              <YAxis fontSize={10} />
              <Tooltip formatter={(v: any) => fmtNum(v)} />
              <Bar dataKey="target" fill="#9333ea" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Status Implementasi" testid="rad-status">
          <ul className="space-y-2 text-sm">
            {(ov?.status || []).map((s: any) => (
              <li key={s.status} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2">
                <span className="font-semibold text-slate-700">{s.status}</span>
                <span className="font-bold">{fmtNum(s.jumlah)}</span>
              </li>
            ))}
          </ul>
          {!!(ov?.hambatan_utama || []).length && (
            <div className="mt-3">
              <p className="text-[11px] font-bold uppercase text-slate-500">Hambatan utama tercatat</p>
              <ul className="mt-1 list-inside list-disc text-[11px] text-slate-600">
                {(ov?.hambatan_utama || []).slice(0, 4).map((h: string, i: number) => (
                  <li key={i}>{String(h).slice(0, 160)}</li>
                ))}
              </ul>
            </div>
          )}
        </Panel>
      </div>

      <Panel title="Matriks Kegiatan & Monitoring" className="mt-4" testid="tabel-rad"
        action={
          <div className="flex w-full flex-wrap gap-2 sm:w-auto">
            <select value={status} onChange={(e) => setStatus(e.target.value)} data-testid="rad-filter-status"
              aria-label="Filter status RAD"
              className="h-10 w-full rounded-md border border-slate-300 px-2 text-xs sm:h-9 sm:w-auto">
              <option value="semua">Semua Status</option>
              {STATUS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <div className="relative w-full min-w-0 sm:w-auto">
              <Search className="absolute left-2 top-3 h-4 w-4 text-slate-400 sm:top-2.5" aria-hidden="true" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                aria-label="Cari program, kegiatan, atau indikator"
                placeholder="Cari program / kegiatan / indikator" data-testid="rad-search"
                className="h-10 w-full rounded-md border border-slate-300 pl-8 pr-2 text-xs sm:h-9 sm:w-64" />
            </div>
          </div>
        }>
        <div className="table-scroll">
          <table className="w-full min-w-[960px] text-sm">
            <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="min-w-[220px] px-3 py-2">Program / Kegiatan</th>
                <th className="min-w-[180px] px-3 py-2">Indikator</th>
                <th className="whitespace-nowrap px-3 py-2">Satuan</th>
                <th className="whitespace-nowrap px-3 py-2">2025</th>
                <th className="whitespace-nowrap px-3 py-2">2026</th>
                <th className="whitespace-nowrap px-3 py-2">2027</th>
                <th className="whitespace-nowrap px-3 py-2">2030</th>
                <th className="whitespace-nowrap px-3 py-2">Status</th>
                <th className="whitespace-nowrap px-3 py-2">Progres</th>
                {canEdit && <th className="whitespace-nowrap px-3 py-2">Aksi</th>}
              </tr>
            </thead>
            <tbody>
              {(items?.items || []).map((r: any) => (
                <tr key={r.id} className="border-t border-slate-100 align-top hover:bg-slate-50">
                  <td className="px-3 py-2 text-[11.5px]">
                    <b className="block text-slate-800">{r.program || "-"}</b>
                    <span className="text-slate-600">{r.kegiatan}</span>
                    {r.sub_kegiatan && <span className="block text-slate-500">{r.sub_kegiatan}</span>}
                  </td>
                  <td className="px-3 py-2 text-[11.5px] text-slate-600">{r.indikator_capaian || "-"}</td>
                  <td className="px-3 py-2 text-[11.5px]">{r.satuan || "-"}</td>
                  {["2025", "2026", "2027", "2030"].map((t) => (
                    <td key={t} className="whitespace-nowrap px-3 py-2 tabular-nums">{r.targets?.[t] != null ? fmtNum(r.targets[t]) : "-"}</td>
                  ))}
                  <td className="whitespace-nowrap px-3 py-2 text-[11.5px] font-semibold">{r.monitoring?.status}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <div className="h-2 w-20 rounded bg-slate-200">
                      <div className="h-2 rounded bg-emerald-500"
                        style={{ width: `${Math.min(100, r.monitoring?.progress || 0)}%` }} />
                    </div>
                    <span className="text-[10px] text-slate-500">{r.monitoring?.progress || 0}%</span>
                  </td>
                  {canEdit && (
                    <td className="whitespace-nowrap px-3 py-2">
                      <div className="flex gap-1">
                        <button type="button" onClick={() => setEdit(JSON.parse(JSON.stringify(r)))}
                          data-testid={`rad-edit-${r.id}`} title="Ubah monitoring"
                          className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-slate-200 hover:text-slate-900 sm:h-8 sm:w-8"
                          aria-label="Ubah monitoring">
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button type="button" data-testid={`rad-ubah-matriks-${r.id}`}
                          title="Ubah isi matriks (program, target, anggaran)"
                          onClick={async () => {
                            try {
                              const f = await getRadForm(r.id);
                              setForm({ id: r.id, data: f.data });
                            } catch {
                              toast.error("Gagal memuat matriks untuk diubah");
                            }
                          }}
                          className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-amber-100 hover:text-amber-700 sm:h-8 sm:w-8"
                          aria-label="Ubah matriks">
                          <FileEdit className="h-4 w-4" />
                        </button>
                        {canDelete && (
                          <button type="button" data-testid={`rad-hapus-${r.id}`} title="Hapus item RAD"
                            onClick={() => setHapus(r)}
                            className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-rose-100 hover:text-rose-700 sm:h-8 sm:w-8"
                            aria-label="Hapus item RAD">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
          <span>{fmtNum(items?.total)} item · halaman {items?.page} dari {items?.pages}</span>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={(items?.page || 1) <= 1} onClick={() => setPage((p) => p - 1)}
              className="min-h-10 rounded-md border border-slate-300 px-3 font-semibold disabled:opacity-40 sm:min-h-9">Sebelumnya</button>
            <button type="button" disabled={(items?.page || 1) >= (items?.pages || 1)}
              onClick={() => setPage((p) => p + 1)}
              className="min-h-10 rounded-md border border-slate-300 px-3 font-semibold disabled:opacity-40 sm:min-h-9">Berikutnya</button>
          </div>
        </div>
      </Panel>

      {edit && (
        <div className="fixed inset-0 z-[900] flex items-start justify-center overflow-y-auto bg-black/50 p-4">
          <div className="my-10 w-full max-w-lg rounded-lg bg-white p-4 shadow-2xl" data-testid="rad-form">
            <div className="mb-3 flex items-start justify-between">
              <h2 className="font-head text-base font-bold">Monitoring Kegiatan RAD</h2>
              <button type="button" onClick={() => setEdit(null)} aria-label="Tutup"><X className="h-5 w-5 text-slate-500" /></button>
            </div>
            <p className="mb-3 text-xs text-slate-600">{edit.program} — {edit.kegiatan}</p>
            <div className="space-y-3">
              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase text-slate-500">Status</span>
                <select value={edit.monitoring.status} data-testid="rad-form-status"
                  onChange={(e) => setEdit({ ...edit, monitoring: { ...edit.monitoring, status: e.target.value } })}
                  className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm">
                  {STATUS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase text-slate-500">Progres (%)</span>
                <input type="number" min={0} max={100} value={edit.monitoring.progress}
                  data-testid="rad-form-progress"
                  onChange={(e) => setEdit({ ...edit, monitoring: { ...edit.monitoring, progress: e.target.value } })}
                  className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm" />
              </label>
              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase text-slate-500">Penanggung Jawab / OPD</span>
                <input value={edit.monitoring.penanggung_jawab}
                  onChange={(e) => setEdit({ ...edit, monitoring: { ...edit.monitoring, penanggung_jawab: e.target.value } })}
                  className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm" />
              </label>
              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase text-slate-500">Catatan</span>
                <textarea value={edit.monitoring.catatan}
                  onChange={(e) => setEdit({ ...edit, monitoring: { ...edit.monitoring, catatan: e.target.value } })}
                  className="h-20 w-full rounded-md border border-slate-300 p-2 text-sm" />
              </label>
              <label className="block">
                <span className="mb-1 block text-[11px] font-semibold uppercase text-slate-500">Tautan Bukti Dokumen</span>
                <input value={edit.monitoring.dokumen}
                  onChange={(e) => setEdit({ ...edit, monitoring: { ...edit.monitoring, dokumen: e.target.value } })}
                  className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm" />
              </label>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setEdit(null)}
                className="h-9 rounded-md border border-slate-300 px-3 text-sm font-semibold">Batal</button>
              <button type="button" onClick={simpan} disabled={saving} data-testid="rad-form-simpan"
                className="h-9 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60">
                Simpan
              </button>
            </div>
          </div>
        </div>
      )}

      {form && (
        <DynamicForm
          jenis="rad"
          recordId={form.id}
          initial={form.data}
          judul={form.id ? "Ubah Matriks RAD" : "Input Matriks RAD"}
          onClose={() => setForm(null)}
          onSimpan={async (data, mode) => (form.id ? updateRad(form.id, data) : createRad(data, mode))}
          onSelesai={() => { load(); loadOv(); }}
        />
      )}

      {hapus && (
        <KonfirmasiHapus
          judul="Hapus item matriks RAD"
          keterangan={`${hapus.program || "-"} · ${hapus.kegiatan || ""}`}
          onBatal={() => setHapus(null)}
          onHapus={async (alasan) => {
            try {
              await deleteRad(hapus.id, alasan);
              toast.success("Item RAD berhasil dihapus");
              setHapus(null);
              load();
              loadOv();
            } catch {
              toast.error("Gagal menghapus item RAD (periksa hak akses Anda)");
            }
          }}
        />
      )}
    </div>
  );
}
