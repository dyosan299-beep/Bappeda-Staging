import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { Plus, Pencil, Trash2, Upload, Search, X, MapPin, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
  createRumah,
  deleteRumah,
  fetchFilters,
  fetchRumahList,
  fetchStats,
  updateRumah,
} from "@/features/peta/api";
import { STATUS_COLORS, STATUS_LABEL } from "@/features/peta/basemaps";
import { RumahFilters, RumahProps, RumahStats } from "@/features/peta/types";
import api from "@/lib/api";

const SEMUA = "semua";
const EDITOR_ROLES = ["superadmin", "admin", "petugas", "operator"];
const SUPER_ROLES = ["superadmin", "admin"];

const EMPTY: Partial<RumahProps> = {
  pemilik: "",
  nama: "",
  jumlah_orang: 1,
  no_kk: "",
  rt: "",
  rw: "",
  kelurahan: "",
  kecamatan: "Tallo",
  penghasilan: "P3",
  bantuan: "-",
  tahun_bangunan: "",
  dinding: "A",
  atap: "A",
  lantai: "A",
  sanitasi: "A",
  air: "A",
  status_lahan: "Milik",
  jalan: "Layak Huni",
  keterangan: "",
  luas: 80,
  kondisi: "Layak Huni",
  status: "hijau",
  foto_url: "",
  lat: -5.1477,
  lng: 119.4327,
};

function StatusBadge({ status }: { status?: string }) {
  const s = String(status || "kuning");
  return (
    <span
      className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold"
      style={{ backgroundColor: `${STATUS_COLORS[s]}22`, color: "#0f172a" }}
    >
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: STATUS_COLORS[s] }} />
      {STATUS_LABEL[s] || s}
    </span>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  options,
}: {
  label: string;
  value: any;
  onChange: (v: any) => void;
  type?: string;
  options?: string[];
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      {options ? (
        <select
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm focus:border-slate-500 focus:outline-none"
        >
          {options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      ) : (
        <input
          type={type}
          value={value ?? ""}
          onChange={(e) => onChange(type === "number" ? Number(e.target.value) : e.target.value)}
          className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm focus:border-slate-500 focus:outline-none"
        />
      )}
    </label>
  );
}

export default function DataRumah() {
  const { user } = useAuth() as { user: any };
  const canEdit = !!user && EDITOR_ROLES.includes(user.role);
  const canDelete = !!user && SUPER_ROLES.includes(user.role);

  const [filters, setFilters] = useState<RumahFilters | null>(null);
  const [stats, setStats] = useState<RumahStats | null>(null);
  const [kel, setKel] = useState(SEMUA);
  const [rw, setRw] = useState(SEMUA);
  const [status, setStatus] = useState(SEMUA);
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<RumahProps[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<Partial<RumahProps> | null>(null);
  const [saving, setSaving] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const query = { kelurahan: kel, rw, status, search };
      const [list, st] = await Promise.all([fetchRumahList(query), fetchStats({ kelurahan: kel, rw })]);
      setItems(list.items || []);
      setTotal(list.total || 0);
      setStats(st);
    } catch {
      toast.error("Gagal memuat data rumah");
    } finally {
      setLoading(false);
    }
  }, [kel, rw, status, search]);

  useEffect(() => {
    fetchFilters().then(setFilters).catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const rwOptions = useMemo(() => {
    if (!filters) return [];
    if (kel === SEMUA) return filters.rw_all || [];
    return filters.rw_by_kelurahan?.[kel] || [];
  }, [filters, kel]);

  const simpan = async () => {
    if (!form) return;
    if (!form.pemilik || !form.kelurahan) {
      toast.error("Nama pemilik dan kelurahan wajib diisi");
      return;
    }
    setSaving(true);
    try {
      if (form.id) {
        await updateRumah(String(form.id), form);
        toast.success("Data rumah diperbarui");
      } else {
        await createRumah(form);
        toast.success("Data rumah ditambahkan (polygon dibuat otomatis dari titik & luas)");
      }
      setForm(null);
      await load();
      const flt = await fetchFilters();
      setFilters(flt);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan data");
    } finally {
      setSaving(false);
    }
  };

  const hapus = async (row: RumahProps) => {
    if (!window.confirm(`Hapus data rumah ${row.pemilik}?`)) return;
    try {
      await deleteRumah(String(row.id));
      toast.success("Data rumah dihapus");
      await load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Gagal menghapus data");
    }
  };

  const importGeoJSON = async () => {
    try {
      const parsed = JSON.parse(importText);
      const { data } = await api.post("/rumah/import-geojson", {
        featureCollection: parsed,
        replace: false,
      });
      toast.success(`Berhasil impor ${data.imported} polygon (total ${data.total})`);
      setImportOpen(false);
      setImportText("");
      await load();
      setFilters(await fetchFilters());
    } catch (e: any) {
      toast.error(
        e?.response?.data?.detail || "GeoJSON tidak valid / gagal diimpor (hanya superadmin)",
      );
    }
  };

  return (
    <div className="space-y-4" data-testid="page-data-rumah">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-head text-xl font-extrabold text-slate-900">Data Rumah / Bangunan</p>
          <p className="text-xs text-slate-500">
            Sumber polygon peta GIS. Total terdata: <b>{stats?.total ?? 0}</b> bangunan
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/peta-kemiskinan"
            className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            <MapPin className="h-4 w-4" /> Lihat di Peta
          </Link>
          {canDelete && (
            <button
              type="button"
              data-testid="btn-import-geojson"
              onClick={() => setImportOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              <Upload className="h-4 w-4" /> Impor GeoJSON
            </button>
          )}
          {canEdit && (
            <button
              type="button"
              data-testid="btn-tambah-rumah"
              onClick={() => setForm({ ...EMPTY })}
              className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground hover:opacity-90"
            >
              <Plus className="h-4 w-4" /> Tambah Rumah
            </button>
          )}
        </div>
      </div>

      {/* Ringkasan status */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { k: "total", label: "Total Bangunan", value: stats?.total ?? 0, color: "#0f172a" },
          { k: "hijau", label: "Layak / Lengkap", value: stats?.per_status?.hijau ?? 0, color: STATUS_COLORS.hijau },
          { k: "kuning", label: "Perlu Verifikasi", value: stats?.per_status?.kuning ?? 0, color: STATUS_COLORS.kuning },
          { k: "merah", label: "Tidak Layak", value: stats?.per_status?.merah ?? 0, color: STATUS_COLORS.merah },
        ].map((c) => (
          <div key={c.k} className="rounded-lg border border-slate-200 bg-white p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{c.label}</p>
            <p className="mt-1 text-2xl font-extrabold" style={{ color: c.color }}>
              {c.value}
            </p>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <select
          data-testid="dr-filter-kelurahan"
          value={kel}
          onChange={(e) => { setKel(e.target.value); setRw(SEMUA); }}
          className="h-9 rounded-md border border-slate-300 px-2 text-sm"
        >
          <option value={SEMUA}>Semua Kelurahan</option>
          {filters?.kelurahan?.map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
        <select
          data-testid="dr-filter-rw"
          value={rw}
          onChange={(e) => setRw(e.target.value)}
          className="h-9 rounded-md border border-slate-300 px-2 text-sm"
        >
          <option value={SEMUA}>Semua RW</option>
          {rwOptions.map((r) => (
            <option key={r} value={r}>RW {r}</option>
          ))}
        </select>
        <select
          data-testid="dr-filter-status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="h-9 rounded-md border border-slate-300 px-2 text-sm"
        >
          <option value={SEMUA}>Semua Status</option>
          <option value="hijau">Hijau — lengkap</option>
          <option value="kuning">Kuning — perlu verifikasi</option>
          <option value="merah">Merah — tidak layak</option>
        </select>
        <div className="relative w-full min-w-0 sm:w-auto">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
          <input
            data-testid="dr-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari pemilik / kode / KK"
            className="h-10 w-full sm:h-9 sm:w-56 rounded-md border border-slate-300 pl-8 pr-2 text-sm"
          />
        </div>
        <span className="ml-auto text-xs text-slate-500">
          {loading ? "Memuat…" : `${items.length} dari ${total} data`}
        </span>
      </div>

      {/* Tabel */}
      <div className="table-scroll rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[780px] text-sm" data-testid="tabel-rumah">
          <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2">Kode</th>
              <th className="px-3 py-2">Pemilik</th>
              <th className="px-3 py-2">Jiwa</th>
              <th className="px-3 py-2">RT/RW</th>
              <th className="px-3 py-2">Kelurahan</th>
              <th className="px-3 py-2">Luas</th>
              <th className="px-3 py-2">Bantuan</th>
              <th className="px-3 py-2">Status</th>
              {(canEdit || canDelete) && <th className="px-3 py-2">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr key={String(r.id)} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-[11px] text-slate-500">{r.kode}</td>
                <td className="px-3 py-2 font-semibold text-slate-800">{r.pemilik}</td>
                <td className="px-3 py-2">{r.jumlah_orang}</td>
                <td className="px-3 py-2">{r.rt || "-"}/{r.rw || "-"}</td>
                <td className="px-3 py-2">{r.kelurahan}</td>
                <td className="px-3 py-2">{r.luas != null ? `${Number(r.luas).toFixed(2)} m²` : "-"}</td>
                <td className="px-3 py-2">{r.bantuan || "-"}</td>
                <td className="px-3 py-2"><StatusBadge status={String(r.status)} /></td>
                {(canEdit || canDelete) && (
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1">
                      {canEdit && (
                        <button
                          type="button"
                          onClick={() => setForm({ ...r })}
                          className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-slate-200 hover:text-slate-900 sm:h-8 sm:w-8"
                          aria-label={`Edit ${r.pemilik}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                      )}
                      {canDelete && (
                        <button
                          type="button"
                          onClick={() => hapus(r)}
                          className="inline-flex h-9 w-9 items-center justify-center rounded text-red-500 hover:bg-red-50 sm:h-8 sm:w-8"
                          aria-label={`Hapus ${r.pemilik}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={9} className="px-3 py-8 text-center text-sm text-slate-500">
                  Tidak ada data sesuai filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Form tambah / edit */}
      {form && (
        <div className="fixed inset-0 z-[900] flex items-start justify-center overflow-y-auto bg-black/50 p-4">
          <div className="my-8 w-full max-w-3xl rounded-lg bg-white shadow-2xl" data-testid="form-rumah">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <h2 className="font-head text-base font-bold">
                {form.id ? "Edit Data Rumah" : "Tambah Data Rumah"}
              </h2>
              <button type="button" onClick={() => setForm(null)} aria-label="Tutup form">
                <X className="h-5 w-5 text-slate-500" />
              </button>
            </div>
            <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 md:grid-cols-4">
              <Field label="Pemilik *" value={form.pemilik} onChange={(v) => setForm({ ...form, pemilik: v, nama: v })} />
              <Field label="Jumlah Orang" type="number" value={form.jumlah_orang} onChange={(v) => setForm({ ...form, jumlah_orang: v })} />
              <Field label="No. KK" value={form.no_kk} onChange={(v) => setForm({ ...form, no_kk: v })} />
              <Field label="Tahun Bangunan" value={form.tahun_bangunan} onChange={(v) => setForm({ ...form, tahun_bangunan: v })} />
              <Field label="RT" value={form.rt} onChange={(v) => setForm({ ...form, rt: v })} />
              <Field label="RW" value={form.rw} onChange={(v) => setForm({ ...form, rw: v })} />
              <Field label="Kelurahan *" value={form.kelurahan} onChange={(v) => setForm({ ...form, kelurahan: v })} />
              <Field label="Kecamatan" value={form.kecamatan} onChange={(v) => setForm({ ...form, kecamatan: v })} />
              <Field label="Penghasilan" value={form.penghasilan} onChange={(v) => setForm({ ...form, penghasilan: v })} options={["P1", "P2", "P3", "P4"]} />
              <Field label="Bantuan" value={form.bantuan} onChange={(v) => setForm({ ...form, bantuan: v })} options={["-", "PKH", "BPNT", "BLT", "BSPS"]} />
              <Field label="Dinding" value={form.dinding} onChange={(v) => setForm({ ...form, dinding: v })} options={["A", "B", "C"]} />
              <Field label="Atap" value={form.atap} onChange={(v) => setForm({ ...form, atap: v })} options={["A", "B", "C"]} />
              <Field label="Lantai" value={form.lantai} onChange={(v) => setForm({ ...form, lantai: v })} options={["A", "B", "C"]} />
              <Field label="Sanitasi" value={form.sanitasi} onChange={(v) => setForm({ ...form, sanitasi: v })} options={["A", "B", "C"]} />
              <Field label="Air" value={form.air} onChange={(v) => setForm({ ...form, air: v })} options={["A", "B", "C"]} />
              <Field label="Status Lahan" value={form.status_lahan} onChange={(v) => setForm({ ...form, status_lahan: v })} options={["Milik", "Sewa", "Menumpang", "Milik Keluarga"]} />
              <Field label="Jalan" value={form.jalan} onChange={(v) => setForm({ ...form, jalan: v })} options={["Layak Huni", "Tidak Layak Huni", "Perlu Perbaikan"]} />
              <Field label="Kondisi" value={form.kondisi} onChange={(v) => setForm({ ...form, kondisi: v })} options={["Layak Huni", "Perlu Perbaikan", "Tidak Layak Huni"]} />
              <Field label="Status Warna" value={form.status} onChange={(v) => setForm({ ...form, status: v })} options={["hijau", "kuning", "merah"]} />
              <Field label="Luas (m²)" type="number" value={form.luas} onChange={(v) => setForm({ ...form, luas: v })} />
              <Field label="Latitude" type="number" value={form.lat} onChange={(v) => setForm({ ...form, lat: v })} />
              <Field label="Longitude" type="number" value={form.lng} onChange={(v) => setForm({ ...form, lng: v })} />
              <div className="sm:col-span-2 md:col-span-2">
                <Field label="URL Foto Rumah" value={form.foto_url} onChange={(v) => setForm({ ...form, foto_url: v })} />
              </div>
              <div className="sm:col-span-2 md:col-span-4">
                <Field label="Keterangan" value={form.keterangan} onChange={(v) => setForm({ ...form, keterangan: v })} />
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 px-4 py-3">
              <p className="mr-auto text-[11px] text-slate-500">
                Polygon dibuat otomatis dari titik (lat/lng) &amp; luas bila belum ada geometry.
              </p>
              <button
                type="button"
                onClick={() => setForm(null)}
                className="h-9 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-700"
              >
                Batal
              </button>
              <button
                type="button"
                data-testid="btn-simpan-rumah"
                onClick={simpan}
                disabled={saving}
                className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />} Simpan
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Impor GeoJSON */}
      {importOpen && (
        <div className="fixed inset-0 z-[900] flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-2xl rounded-lg bg-white p-4 shadow-2xl">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-head text-base font-bold">Impor GeoJSON Polygon Rumah</h2>
              <button type="button" onClick={() => setImportOpen(false)} aria-label="Tutup">
                <X className="h-5 w-5 text-slate-500" />
              </button>
            </div>
            <input
              type="file"
              accept=".geojson,.json,application/geo+json,application/json"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (file) setImportText(await file.text());
              }}
              className="mb-2 block w-full text-sm"
            />
            <textarea
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              placeholder='{"type":"FeatureCollection","features":[...]}'
              className="h-48 w-full rounded-md border border-slate-300 p-2 font-mono text-[11px]"
            />
            <p className="mt-1 text-[11px] text-slate-500">
              Properti yang dikenali: pemilik, nama, jumlah_orang, no_kk, rt, rw, kelurahan,
              kecamatan, penghasilan, bantuan, tahun_bangunan, dinding, atap, lantai, sanitasi,
              air, status_lahan, jalan, keterangan, luas, kondisi, status, foto_url.
            </p>
            <div className="mt-3 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setImportOpen(false)}
                className="h-9 rounded-md border border-slate-300 px-3 text-sm font-semibold"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={importGeoJSON}
                className="h-9 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground"
              >
                Impor
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
