import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Check, Loader2, Plus, RefreshCw, Search, Trash2 } from "lucide-react";
import { PageHeader, Panel, KpiCard } from "@/features/data/ui";
import { fmtNum } from "@/features/data/api";
import {
  deleteKode, getKodeReferensi, KodeItem, pesanGalat, postKode, putKode,
} from "@/features/data/manageApi";

const SEMUA = "semua";

export default function MasterKode() {
  const [data, setData] = useState<{
    total: number; items: KodeItem[]; belum_didefinisikan: number;
    fields: { name: string; label: string; jumlah_kode: number }[];
  } | null>(null);
  const [field, setField] = useState(SEMUA);
  const [hanyaKosong, setHanyaKosong] = useState(false);
  const [cari, setCari] = useState("");
  const [draft, setDraft] = useState<Record<string, { label: string; keterangan: string }>>({});
  const [simpanId, setSimpanId] = useState<string | null>(null);
  const [tambah, setTambah] = useState(false);
  const [baru, setBaru] = useState({ field: "", kode: "", label: "", keterangan: "" });
  const [loading, setLoading] = useState(true);

  const muat = useCallback(() => {
    setLoading(true);
    getKodeReferensi(field === SEMUA ? undefined : field, hanyaKosong || undefined)
      .then((r) => {
        setData(r);
        const d: Record<string, { label: string; keterangan: string }> = {};
        r.items.forEach((i) => { d[i.id] = { label: i.label || "", keterangan: i.keterangan || "" }; });
        setDraft(d);
      })
      .catch(() => toast.error("Gagal memuat master kode referensi"))
      .finally(() => setLoading(false));
  }, [field, hanyaKosong]);

  useEffect(() => { muat(); }, [muat]);

  const items = useMemo(() => {
    const list = data?.items || [];
    if (!cari) return list;
    const s = cari.toLowerCase();
    return list.filter((i) =>
      i.field_label.toLowerCase().includes(s) || String(i.kode).includes(s)
      || (i.label || "").toLowerCase().includes(s));
  }, [data, cari]);

  const simpan = async (item: KodeItem) => {
    setSimpanId(item.id);
    try {
      await putKode(item.id, draft[item.id]);
      toast.success(`Arti kode ${item.field_label} = ${item.kode} disimpan`);
      muat();
    } catch (e) {
      toast.error(pesanGalat(e).pesan);
    } finally {
      setSimpanId(null);
    }
  };

  const grup = useMemo(() => {
    const out: Record<string, KodeItem[]> = {};
    items.forEach((i) => { (out[i.field_label] = out[i.field_label] || []).push(i); });
    return out;
  }, [items]);

  return (
    <div data-testid="page-master-kode">
      <PageHeader title="Master Kode Referensi DTSEN"
        subtitle="Arti kode numerik pada data DTSEN tidak ditebak sistem — silakan diisi administrator"
        actions={
          <div className="flex gap-2">
            <button type="button" onClick={muat} data-testid="mk-muat-ulang"
              className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-700">
              <RefreshCw className="h-4 w-4" /> Muat Ulang
            </button>
            <button type="button" onClick={() => setTambah(true)} data-testid="mk-tambah"
              className="inline-flex h-9 items-center gap-2 rounded-md bg-slate-900 px-3 text-sm font-semibold text-white">
              <Plus className="h-4 w-4" /> Tambah Kode
            </button>
          </div>
        } />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard testid="mk-total" label="Total kode terdeteksi" value={fmtNum(data?.total)} />
        <KpiCard label="Belum didefinisikan" value={fmtNum(data?.belum_didefinisikan)} color="#b91c1c" />
        <KpiCard label="Sudah didefinisikan"
          value={fmtNum((data?.total || 0) - (data?.belum_didefinisikan || 0))} color="#16a34a" />
        <KpiCard label="Jenis field berkode" value={fmtNum(data?.fields?.length)} color="#4f46e5" />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <select value={field} onChange={(e) => setField(e.target.value)} data-testid="mk-field"
          className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto">
          <option value={SEMUA}>Semua Field</option>
          {(data?.fields || []).map((f) => (
            <option key={f.name} value={f.name}>{f.label}</option>
          ))}
        </select>
        <label className="flex min-h-9 items-center gap-2 text-xs font-semibold text-slate-600">
          <input type="checkbox" checked={hanyaKosong} data-testid="mk-hanya-kosong"
            onChange={(e) => setHanyaKosong(e.target.checked)} />
          Hanya yang belum didefinisikan
        </label>
        <div className="relative w-full min-w-0 sm:w-auto">
          <Search className="absolute left-2 top-3 h-4 w-4 text-slate-400 sm:top-2.5" aria-hidden="true" />
          <input value={cari} onChange={(e) => setCari(e.target.value)} data-testid="mk-cari" aria-label="Cari field, kode, atau arti"
            placeholder="Cari field / kode / arti"
            className="h-10 w-full rounded-md border border-slate-300 pl-8 pr-2 text-sm sm:h-9 sm:w-60" />
        </div>
        <span className="ml-auto text-xs text-slate-500">
          {loading ? "Memuat…" : `${fmtNum(items.length)} kode ditampilkan`}
        </span>
      </div>

      {Object.entries(grup).map(([label, list]) => (
        <Panel key={label} title={label} className="mt-3" testid={`mk-grup-${list[0].field}`}
          action={<span className="text-[11px] text-slate-500">{list.length} kode</span>}>
          <div className="table-scroll">
            <table className="w-full min-w-[740px] text-sm">
              <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="w-20 whitespace-nowrap px-3 py-2">Kode</th>
                  <th className="w-28 whitespace-nowrap px-3 py-2">Jumlah Data</th>
                  <th className="min-w-[200px] px-3 py-2">Arti / Label</th>
                  <th className="min-w-[200px] px-3 py-2">Keterangan</th>
                  <th className="w-28 whitespace-nowrap px-3 py-2">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {list.map((i) => (
                  <tr key={i.id} className="border-t border-slate-100">
                    <td className="whitespace-nowrap px-3 py-2 font-mono font-bold text-slate-800">{i.kode}</td>
                    <td className="whitespace-nowrap px-3 py-2 tabular-nums text-slate-600">{fmtNum(i.jumlah_data)}</td>
                    <td className="px-3 py-2">
                      <input value={draft[i.id]?.label ?? ""} data-testid={`mk-label-${i.id}`}
                        placeholder="mis. Keramik / Milik sendiri"
                        onChange={(e) => setDraft((d) => ({
                          ...d, [i.id]: { ...d[i.id], label: e.target.value },
                        }))}
                        className={`h-10 w-full min-w-[180px] rounded-md border px-2 text-sm sm:h-9 ${
                          i.label ? "border-slate-300" : "border-amber-400 bg-amber-50"}`} />
                    </td>
                    <td className="px-3 py-2">
                      <input value={draft[i.id]?.keterangan ?? ""} data-testid={`mk-ket-${i.id}`}
                        onChange={(e) => setDraft((d) => ({
                          ...d, [i.id]: { ...d[i.id], keterangan: e.target.value },
                        }))}
                        className="h-10 w-full min-w-[180px] rounded-md border border-slate-300 px-2 text-sm sm:h-9" />
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <div className="flex items-center gap-1">
                        <button type="button" onClick={() => simpan(i)} disabled={simpanId === i.id}
                          data-testid={`mk-simpan-${i.id}`} title="Simpan arti kode"
                          className="inline-flex h-10 items-center gap-1 whitespace-nowrap rounded-md bg-slate-900 px-3 text-xs font-semibold text-white disabled:opacity-50 sm:h-9">
                          {simpanId === i.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                          Simpan
                        </button>
                        {Number(i.jumlah_data) === 0 && (
                          <button type="button" title="Hapus kode (tidak dipakai data)"
                            aria-label={`Hapus kode ${i.kode}`}
                            data-testid={`mk-hapus-${i.id}`}
                            onClick={async () => {
                              try {
                                await deleteKode(i.id);
                                toast.success("Kode dihapus");
                                muat();
                              } catch (e) { toast.error(pesanGalat(e).pesan); }
                            }}
                            className="inline-flex h-10 w-10 items-center justify-center rounded text-slate-500 hover:bg-rose-100 hover:text-rose-700 sm:h-9 sm:w-9">
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
        </Panel>
      ))}

      {!loading && !items.length && (
        <Panel title="Tidak ada data" className="mt-3">
          <p className="text-sm text-slate-500">
            Belum ada kode yang cocok dengan filter. Kode akan otomatis terdeteksi setiap kali
            data DTSEN diimpor atau diinput manual.
          </p>
        </Panel>
      )}

      {tambah && (
        <div className="fixed inset-0 z-[950] flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-4 shadow-2xl" data-testid="mk-dialog-tambah">
            <h3 className="font-head text-base font-bold text-slate-900">Tambah Kode Referensi</h3>
            <div className="mt-3 space-y-3">
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase text-slate-600">Field</label>
                <select value={baru.field} onChange={(e) => setBaru({ ...baru, field: e.target.value })}
                  data-testid="mk-baru-field" className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm">
                  <option value="">— pilih field —</option>
                  {(data?.fields || []).map((f) => <option key={f.name} value={f.name}>{f.label}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase text-slate-600">Kode</label>
                <input value={baru.kode} onChange={(e) => setBaru({ ...baru, kode: e.target.value })}
                  data-testid="mk-baru-kode" className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase text-slate-600">Arti / Label</label>
                <input value={baru.label} onChange={(e) => setBaru({ ...baru, label: e.target.value })}
                  data-testid="mk-baru-label" className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm" />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setTambah(false)}
                className="h-9 rounded-md border border-slate-300 px-3 text-sm font-semibold">Batal</button>
              <button type="button" data-testid="mk-baru-simpan"
                onClick={async () => {
                  try {
                    await postKode(baru);
                    toast.success("Kode referensi ditambahkan");
                    setTambah(false);
                    setBaru({ field: "", kode: "", label: "", keterangan: "" });
                    muat();
                  } catch (e) { toast.error(pesanGalat(e).pesan); }
                }}
                className="h-9 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
