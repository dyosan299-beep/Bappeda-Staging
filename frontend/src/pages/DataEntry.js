import { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Save, FileEdit, Lock, MapPin, Building } from "lucide-react";

const FIELDS = [
  { key: "kemiskinan_ekstrim_kk", label: "Kemiskinan Ekstrim (KK)" },
  { key: "stunting_anak", label: "Stunting (anak)" },
  { key: "anak_jalanan", label: "Anak Jalanan (jiwa)" },
  { key: "ats", label: "Anak Tidak Sekolah" },
  { key: "disabilitas", label: "Disabilitas (orang)" },
  { key: "kemiskinan_persen", label: "Tingkat Kemiskinan (%)" },
];

const fmt = (n) => (n ?? 0).toLocaleString("id-ID");

export default function DataEntry() {
  const { user } = useAuth();
  const isSuper = ["superadmin", "admin"].includes(user?.role);
  const [regions, setRegions] = useState([]);
  const [activeRegion, setActiveRegion] = useState(null);
  const [kelurahan, setKelurahan] = useState([]);
  const [selectedKel, setSelectedKel] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  const canEditRegion = (r) =>
    isSuper || (user?.wilayah && r.nama.toLowerCase() === user.wilayah.toLowerCase());

  const loadRegions = async () => {
    const { data } = await api.get("/regions");
    setRegions(data);
    return data;
  };

  const openRegion = async (r) => {
    setActiveRegion(r);
    setSelectedKel(null);
    const { data } = await api.get(`/regions/${r.id}/kelurahan`);
    setKelurahan(data);
  };

  useEffect(() => {
    loadRegions().then((data) => {
      let def = data[0];
      if (!isSuper && user?.wilayah) {
        def = data.find((r) => r.nama.toLowerCase() === user.wilayah.toLowerCase()) || data[0];
      }
      if (def) openRegion(def);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectKel = (k) => {
    setSelectedKel(k);
    const f = {};
    FIELDS.forEach((fl) => (f[fl.key] = k[fl.key]));
    setForm(f);
  };

  const editable = activeRegion ? canEditRegion(activeRegion) : false;

  const save = async () => {
    if (!selectedKel) return;
    setSaving(true);
    try {
      const payload = {};
      FIELDS.forEach((fl) => {
        const v = form[fl.key];
        payload[fl.key] = fl.key === "kemiskinan_persen" ? parseFloat(v) : parseInt(v, 10);
      });
      const { data } = await api.put(`/kelurahan/${selectedKel.id}`, payload);
      if (data.status === "pending") {
        toast.success(data.message || "Perubahan dikirim untuk verifikasi.", { duration: 5000 });
      } else {
        const kel = data.kelurahan || data;
        setKelurahan((prev) => prev.map((k) => (k.id === kel.id ? kel : k)));
        setSelectedKel(kel);
        toast.success(`Data Kelurahan ${kel.nama} berhasil diperbarui`);
        loadRegions().then((rs) => {
          const fresh = rs.find((r) => r.id === activeRegion.id);
          if (fresh) setActiveRegion(fresh);
        });
      }
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Gagal menyimpan data");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="dataentry-page">
      <div>
        <p className="font-head text-3xl font-extrabold md:text-4xl">Input Data Kelurahan</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {isSuper
            ? "Sebagai superadmin, perubahan Anda langsung diterapkan. Total kecamatan otomatis dihitung dari data kelurahan."
            : `Anda dapat mengusulkan perubahan data kelurahan di Kecamatan ${user?.wilayah || "-"}. Perubahan akan tampil setelah disetujui verifikator.`}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Kecamatan list */}
        <div className="rounded-lg border-2 border-border bg-card p-4">
          <h3 className="mb-3 flex items-center gap-2 px-2 font-head text-base font-bold">
            <MapPin className="h-4 w-4" /> Kecamatan
          </h3>
          <ul className="max-h-52 space-y-1 overflow-y-auto lg:max-h-[560px]" data-testid="region-list">
            {regions.map((r) => (
              <li key={r.id}>
                <button
                  data-testid={`region-select-${r.nama}`}
                  onClick={() => openRegion(r)}
                  className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm font-medium transition-colors focus:outline-none ${
                    activeRegion?.id === r.id ? "bg-primary text-primary-foreground" : "hover:bg-secondary"
                  }`}
                >
                  {r.nama}
                  {!canEditRegion(r) && <Lock className="h-3.5 w-3.5 opacity-60" />}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Kelurahan list */}
        <div className="rounded-lg border-2 border-border bg-card p-4">
          <h3 className="mb-1 flex items-center gap-2 px-2 font-head text-base font-bold">
            <Building className="h-4 w-4" /> Kelurahan
          </h3>
          {activeRegion && (
            <p className="mb-3 px-2 text-xs text-muted-foreground">
              Kec. {activeRegion.nama} · {kelurahan.length} kelurahan
            </p>
          )}
          <ul className="max-h-52 space-y-1 overflow-y-auto lg:max-h-[540px]" data-testid="kelurahan-list">
            {kelurahan.map((k) => (
              <li key={k.id}>
                <button
                  data-testid={`kelurahan-select-${k.nama}`}
                  onClick={() => selectKel(k)}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors focus:outline-none ${
                    selectedKel?.id === k.id ? "bg-accent text-accent-foreground" : "hover:bg-secondary"
                  }`}
                >
                  {k.nama}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Form */}
        <div className="min-w-0 lg:col-span-2">
          {activeRegion && (
            <div className="mb-4 rounded-lg border-2 border-dashed border-border bg-secondary/50 p-4" data-testid="kecamatan-aggregate">
              <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
                Total Kecamatan {activeRegion.nama} (otomatis dari kelurahan)
              </p>
              <div className="grid grid-cols-1 gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2 2xl:grid-cols-3">
                {FIELDS.slice(0, 5).map((fl) => (
                  <div key={fl.key} className="flex items-center justify-between gap-2">
                    <span className="truncate text-muted-foreground">{fl.label.split(" (")[0]}</span>
                    <span className="shrink-0 font-bold tabular-nums">{fmt(activeRegion[fl.key])}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedKel ? (
            <div className="rounded-lg border-2 border-border bg-card p-4 sm:p-6" data-testid="dataentry-form">
              <div className="mb-5 flex flex-wrap items-center gap-2">
                <FileEdit className="h-5 w-5 shrink-0 text-primary" />
                <h3 className="font-head text-lg font-extrabold sm:text-xl">Kelurahan {selectedKel.nama}</h3>
                <span className="ml-auto text-sm text-muted-foreground">Kec. {selectedKel.kecamatan}</span>
              </div>

              {!editable && (
                <div className="mb-4 flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                  <Lock className="h-4 w-4 shrink-0" /> Anda tidak memiliki izin mengubah wilayah ini.
                </div>
              )}

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {FIELDS.map((fl) => (
                  <div key={fl.key}>
                    <label className="mb-1.5 block text-sm font-semibold">{fl.label}</label>
                    <input
                      data-testid={`field-${fl.key}`}
                      type="number"
                      step={fl.key === "kemiskinan_persen" ? "0.1" : "1"}
                      disabled={!editable}
                      value={form[fl.key] ?? ""}
                      onChange={(e) => setForm({ ...form, [fl.key]: e.target.value })}
                      className="w-full rounded-md border-2 border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none disabled:opacity-60"
                    />
                  </div>
                ))}
              </div>

              <button
                data-testid="save-btn"
                onClick={save}
                disabled={!editable || saving}
                className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-6 py-2.5 font-semibold text-primary-foreground transition-colors hover:bg-[#0E6456] focus:outline-none disabled:opacity-60"
              >
                <Save className="h-5 w-5" /> {saving ? "Menyimpan…" : (isSuper ? "Simpan Perubahan" : "Kirim untuk Verifikasi")}
              </button>
            </div>
          ) : (
            <div className="rounded-lg border-2 border-dashed border-border p-10 text-center text-sm text-muted-foreground">
              Pilih kelurahan di daftar untuk mengubah datanya.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
