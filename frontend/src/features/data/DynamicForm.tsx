import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Loader2, MapPin, Save, X } from "lucide-react";
import {
  FieldSection, getFieldMeta, getKabupaten, getKecamatanMaster, getKelurahanMaster,
  getProvinsi, pesanGalat, WilayahOpsi,
} from "@/features/data/manageApi";

/** Field wilayah DTSEN yang diisi otomatis lewat dropdown berantai. */
const WILAYAH_DTSEN = [
  "kode_provinsi", "provinsi", "kode_kabupaten_kota", "kabupaten_kota",
  "kode_kecamatan", "kecamatan", "kode_kelurahan_desa", "kelurahan_desa",
];

const PANJANG = [
  "alamat", "strategi_implementasi", "target_capaian", "indikator_capaian",
  "output_kegiatan", "indikator_capaian_terkait_disabilitas", "hambatan_tantangan",
  "keterangan", "program", "kegiatan", "sub_kegiatan",
];

type Props = {
  jenis: "dtsen" | "disabilitas" | "rad" | "gis_koordinat";
  recordId?: string | null;
  initial?: Record<string, any>;
  judul?: string;
  onClose: () => void;
  onSimpan: (data: Record<string, any>, mode: string) => Promise<any>;
  onSelesai?: () => void;
};

export default function DynamicForm({
  jenis, recordId, initial, judul, onClose, onSimpan, onSelesai,
}: Props) {
  const [meta, setMeta] = useState<{ label: string; kunci_duplikat: string; sections: FieldSection[] } | null>(null);
  const [nilai, setNilai] = useState<Record<string, any>>(initial || {});
  const [galat, setGalat] = useState<{ pesan: string; rincian: { kolom: string; pesan: string }[] } | null>(null);
  const [duplikat, setDuplikat] = useState<any>(null);
  const [simpan, setSimpan] = useState(false);
  const [aktif, setAktif] = useState(0);

  // dropdown berantai wilayah
  const [provList, setProvList] = useState<WilayahOpsi[]>([]);
  const [kabList, setKabList] = useState<WilayahOpsi[]>([]);
  const [kecList, setKecList] = useState<WilayahOpsi[]>([]);
  const [kelList, setKelList] = useState<WilayahOpsi[]>([]);
  const pakaiWilayah = jenis === "dtsen";

  useEffect(() => {
    getFieldMeta(jenis).then(setMeta).catch(() => toast.error("Gagal memuat struktur form"));
  }, [jenis]);

  useEffect(() => {
    if (!pakaiWilayah) return;
    getProvinsi().then((r) => {
      setProvList(r.items);
      setNilai((v) => (v.kode_provinsi || !r.items[0] ? v : {
        ...v, kode_provinsi: r.items[0].kode, provinsi: r.items[0].nama,
      }));
    }).catch(() => {});
  }, [pakaiWilayah]);

  const kodeProv = nilai.kode_provinsi;
  const kodeKab = nilai.kode_kabupaten_kota;
  const kodeKec = nilai.kode_kecamatan;

  useEffect(() => {
    if (!pakaiWilayah || !kodeProv) return;
    getKabupaten(String(kodeProv)).then((r) => {
      setKabList(r.items);
      setNilai((v) => (v.kode_kabupaten_kota || !r.items[0] ? v : {
        ...v, kode_kabupaten_kota: r.items[0].kode, kabupaten_kota: r.items[0].nama,
      }));
    }).catch(() => {});
  }, [pakaiWilayah, kodeProv]);

  useEffect(() => {
    if (!pakaiWilayah || !kodeKab) return;
    getKecamatanMaster(String(kodeKab)).then((r) => setKecList(r.items)).catch(() => {});
  }, [pakaiWilayah, kodeKab]);

  useEffect(() => {
    if (!pakaiWilayah || !kodeKec) { setKelList([]); return; }
    getKelurahanMaster(String(kodeKec)).then((r) => setKelList(r.items)).catch(() => {});
  }, [pakaiWilayah, kodeKec]);

  const set = useCallback((name: string, val: any) => {
    setNilai((v) => ({ ...v, [name]: val }));
  }, []);

  const sections = useMemo(() => meta?.sections || [], [meta]);

  const kirim = async (mode = "tolak") => {
    setSimpan(true);
    setGalat(null);
    try {
      const res = await onSimpan(nilai, mode);
      if (res?.status === "skipped") toast.info("Data sudah ada — penyimpanan dilewati");
      else toast.success(recordId ? "Perubahan data berhasil disimpan" : "Data baru berhasil disimpan");
      if ((res?.warnings || []).length) {
        toast.warning(`${res.warnings.length} catatan peringatan: ${res.warnings[0]?.pesan || ""}`);
      }
      setDuplikat(null);
      onSelesai?.();
      onClose();
    } catch (e: any) {
      const g = pesanGalat(e);
      if (g.duplikat) setDuplikat(g.duplikat);
      else {
        setGalat(g);
        toast.error(g.pesan);
      }
    } finally {
      setSimpan(false);
    }
  };

  const galatKolom = (name: string) =>
    galat?.rincian?.find((r) => r.kolom === name)?.pesan;

  const renderField = (f: any) => {
    if (pakaiWilayah && WILAYAH_DTSEN.includes(f.name)) return null;
    const err = galatKolom(f.name);
    const nilaiField = nilai[f.name] ?? "";
    const kelas = `h-10 w-full rounded-md border px-2 text-sm sm:h-9 ${err ? "border-rose-400 bg-rose-50" : "border-slate-300"}`;
    return (
      <div key={f.name} className={PANJANG.includes(f.name) ? "md:col-span-2" : ""}>
        <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-600">
          {f.label}{f.required && <span className="text-rose-600"> *</span>}
        </label>
        {f.tipe === "kode" && (f.opsi || []).length > 0 ? (
          <select className={kelas} value={String(nilaiField)} data-testid={`form-${f.name}`}
            onChange={(e) => set(f.name, e.target.value)}>
            <option value="">— belum diisi —</option>
            {f.opsi.map((o: any) => (
              <option key={o.kode} value={o.kode}>{o.kode} — {o.label}</option>
            ))}
          </select>
        ) : PANJANG.includes(f.name) ? (
          <textarea rows={2} className={`w-full rounded-md border px-2 py-1.5 text-sm ${err ? "border-rose-400 bg-rose-50" : "border-slate-300"}`}
            value={String(nilaiField)} data-testid={`form-${f.name}`}
            placeholder={f.contoh ? `Contoh: ${f.contoh}` : ""}
            onChange={(e) => set(f.name, e.target.value)} />
        ) : (
          <input type={f.tipe === "int" || f.tipe === "num" ? "number" : "text"}
            step={f.tipe === "num" ? "any" : undefined}
            className={kelas} value={String(nilaiField)} data-testid={`form-${f.name}`}
            placeholder={f.contoh !== "" && f.contoh !== undefined ? `Contoh: ${f.contoh}` : ""}
            onChange={(e) => set(f.name, e.target.value)} />
        )}
        {(f.keterangan || err) && (
          <p className={`mt-0.5 text-[11px] ${err ? "font-semibold text-rose-600" : "text-slate-500"}`}>
            {err || f.keterangan}
          </p>
        )}
      </div>
    );
  };

  const wilayahBlok = (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      <div>
        <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-600">Provinsi</label>
        <select className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9" data-testid="form-provinsi"
          value={String(nilai.kode_provinsi || "")}
          onChange={(e) => {
            const o = provList.find((p) => p.kode === e.target.value);
            setNilai((v) => ({ ...v, kode_provinsi: o?.kode || "", provinsi: o?.nama || "" }));
          }}>
          <option value="">— pilih provinsi —</option>
          {provList.map((p) => <option key={p.kode} value={p.kode}>{p.nama}</option>)}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-600">Kabupaten / Kota</label>
        <select className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9" data-testid="form-kabupaten"
          value={String(nilai.kode_kabupaten_kota || "")}
          onChange={(e) => {
            const o = kabList.find((p) => p.kode === e.target.value);
            setNilai((v) => ({ ...v, kode_kabupaten_kota: o?.kode || "", kabupaten_kota: o?.nama || "" }));
          }}>
          <option value="">— pilih kabupaten/kota —</option>
          {kabList.map((p) => <option key={p.kode} value={p.kode}>{p.nama}</option>)}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-600">Kecamatan</label>
        <select className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9" data-testid="form-kecamatan"
          value={String(nilai.kode_kecamatan || "")}
          onChange={(e) => {
            const o = kecList.find((p) => p.kode === e.target.value);
            setNilai((v) => ({
              ...v, kode_kecamatan: o?.kode || "", kecamatan: o?.nama || "",
              kode_kelurahan_desa: "", kelurahan_desa: "",
            }));
          }}>
          <option value="">— pilih kecamatan —</option>
          {kecList.map((p) => <option key={p.kode} value={p.kode}>{p.nama}</option>)}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-600">
          Kelurahan / Desa <span className="text-rose-600">*</span>
        </label>
        <select className={`h-10 w-full rounded-md border px-2 text-sm sm:h-9 ${galatKolom("kelurahan_desa") ? "border-rose-400 bg-rose-50" : "border-slate-300"}`}
          data-testid="form-kelurahan" value={String(nilai.kode_kelurahan_desa || "")}
          onChange={(e) => {
            const o = kelList.find((p) => p.kode === e.target.value);
            setNilai((v) => ({ ...v, kode_kelurahan_desa: o?.kode || "", kelurahan_desa: o?.nama || "" }));
          }}>
          <option value="">{kodeKec ? "— pilih kelurahan —" : "pilih kecamatan lebih dulu"}</option>
          {kelList.map((p) => <option key={p.kode} value={p.kode}>{p.nama}</option>)}
        </select>
        <p className="mt-0.5 text-[11px] text-slate-500">
          Daftar kelurahan mengikuti kecamatan yang dipilih.
        </p>
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-[950] flex items-start justify-center overflow-y-auto bg-black/50 p-3">
      <div className="my-6 w-full max-w-3xl rounded-lg bg-white shadow-2xl" data-testid="dynamic-form">
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div>
            <h2 className="font-head text-base font-bold text-slate-900">
              {judul || (recordId ? "Ubah Data" : "Input Data Manual")} — {meta?.label || "…"}
            </h2>
            <p className="text-[11px] text-slate-500">
              Kunci duplikat: {meta?.kunci_duplikat || "-"} · tanda * wajib diisi
            </p>
          </div>
          <button type="button" onClick={onClose} data-testid="form-tutup"
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-slate-300 text-slate-500 hover:bg-slate-100">
            <X className="h-4 w-4" />
          </button>
        </div>

        {!meta ? (
          <div className="flex items-center gap-2 p-8 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Memuat struktur form…
          </div>
        ) : (
          <>
            <div className="flex flex-wrap gap-1 border-b border-slate-200 bg-slate-50 px-3 py-2">
              {sections.map((s, i) => (
                <button key={s.section} type="button" onClick={() => setAktif(i)}
                  data-testid={`form-tab-${i}`}
                  className={`inline-flex min-h-9 items-center rounded-md px-2.5 py-1 text-[11px] font-semibold ${
                    aktif === i ? "bg-slate-900 text-white" : "bg-white text-slate-600 border border-slate-300"
                  }`}>
                  {i + 1}. {s.section}
                </button>
              ))}
            </div>

            <div className="max-h-[55vh] overflow-y-auto px-4 py-4">
              {galat && (
                <div className="mb-3 rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-800">
                  <p className="flex items-center gap-2 font-bold">
                    <AlertTriangle className="h-4 w-4" /> {galat.pesan}
                  </p>
                  <ul className="mt-1 list-inside list-disc">
                    {galat.rincian.map((r, i) => <li key={i}>{r.kolom}: {r.pesan}</li>)}
                  </ul>
                </div>
              )}
              {sections.map((s, i) => (
                <div key={s.section} className={i === aktif ? "" : "hidden"}>
                  <h3 className="mb-2 font-head text-xs font-bold uppercase tracking-wide text-slate-500">
                    {s.section}
                  </h3>
                  {pakaiWilayah && s.section === "Identitas Wilayah" && (
                    <div className="mb-3">{wilayahBlok}</div>
                  )}
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    {s.fields.map(renderField)}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 px-4 py-3">
              <p className="text-[11px] text-slate-500">
                <MapPin className="mr-1 inline h-3 w-3" />
                Data tersimpan permanen pada basis data dan langsung tampil di dashboard, tabel, dan peta.
              </p>
              <div className="flex gap-2">
                <button type="button" onClick={onClose}
                  className="h-10 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-700 sm:h-9">
                  Batal
                </button>
                <button type="button" disabled={simpan} onClick={() => kirim("tolak")}
                  data-testid="form-simpan"
                  className="inline-flex h-10 items-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50 sm:h-9">
                  {simpan ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  Simpan Data
                </button>
              </div>
            </div>
          </>
        )}

        {duplikat && (
          <div className="fixed inset-0 z-[960] flex items-center justify-center bg-black/50 p-4">
            <div className="w-full max-w-md rounded-lg bg-white p-4 shadow-2xl" data-testid="dialog-duplikat">
              <h3 className="font-head text-base font-bold text-amber-700">Data sudah tersedia</h3>
              <p className="mt-1 text-xs text-slate-600">
                {duplikat.kunci ? `Identifier: ${duplikat.kunci}` : duplikat.message}
              </p>
              <p className="mt-2 text-xs text-slate-600">Pilih tindakan yang diinginkan:</p>
              <div className="mt-3 space-y-2">
                {[
                  ["skip", "Lewati (Skip)", "Biarkan data lama, tidak ada perubahan"],
                  ["update", "Perbarui data lama", "Seluruh isian form menimpa data lama"],
                  ["update_perubahan", "Perbarui hanya field yang berubah", "Field kosong pada form tidak menimpa data lama"],
                ].filter(([m]) => (duplikat.pilihan || []).includes(m)).map(([mode, label, ket]) => (
                  <button key={mode as string} type="button" disabled={simpan}
                    data-testid={`dup-${mode}`}
                    onClick={() => { setDuplikat(null); kirim(mode as string); }}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-left text-sm hover:bg-slate-50">
                    <span className="font-semibold text-slate-800">{label}</span>
                    <span className="block text-[11px] text-slate-500">{ket}</span>
                  </button>
                ))}
                <button type="button" onClick={() => setDuplikat(null)}
                  className="w-full rounded-md px-3 py-2 text-center text-xs font-semibold text-slate-500">
                  Batalkan
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
