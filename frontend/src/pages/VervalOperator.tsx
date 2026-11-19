import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import L from "leaflet";
import { toast } from "sonner";
import { Camera, CheckCircle2, ChevronLeft, ClipboardCheck, Crosshair, Loader2, Lock, MapPin, Plus, RefreshCw, Search, Send, SwitchCamera, Trash2, TriangleAlert, Upload, UserPlus, X } from "lucide-react";
import { api, clientUuidFor, DASAR_LABEL, errMsg, fmtWaktu, fotoUrl, GPS_LABEL, HUBUNGAN_LABEL, INDIKATOR_PERLU_CATATAN, KESESUAIAN_LABEL, KESIMPULAN_LABEL, KONDISI_RIIL_LABEL, newId } from "@/features/verval/api";
import { Card, DtsenNilai, Field, INPUT, StatusBadge, UjiBadge } from "@/features/verval/ui";
import { umumkanPerubahanPeta } from "@/features/verval/VervalMapLayer";
import { useAuth } from "@/context/AuthContext";
import { ensureLeafletSafe, safeRemoveMap } from "@/lib/leafletSafe";
import { BTN_PRIMARY, BTN_SECONDARY, BTN_SM, BTN_SM_PRIMARY, FR } from "@/features/a11y/ui";

/* =================================================================== Beranda operator */
export function VervalBeranda() {
  const navigate = useNavigate();
  const [info, setInfo] = useState<any>(null);
  const [list, setList] = useState<any>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [err, setErr] = useState("");
  const [showBaru, setShowBaru] = useState(false);
  const [busyBaru, setBusyBaru] = useState(false);
  const [baru, setBaru] = useState({
    no_kk: "", nik: "", kepala_keluarga: "", alamat: "",
    rw: "", rt: "", jumlah_anggota_keluarga: "1", kode_kelurahan: "",
  });

  const load = useCallback(() => {
    setErr("");
    api.get("/verval/sasaran", { params: { search: q || undefined, status: status || undefined, size: 100 } })
      .then((r) => setList(r.data)).catch((e) => { setErr(errMsg(e)); setList({ items: [] }); });
  }, [q, status]);
  useEffect(() => {
    api.get("/verval/saya").then((r) => {
      setInfo(r.data);
      const p0 = r.data?.penugasan?.[0];
      if (p0) {
        setBaru((prev) => ({
          ...prev,
          kode_kelurahan: prev.kode_kelurahan || p0.kode_kelurahan || "",
          rw: prev.rw || p0.rw || "",
          rt: prev.rt || (Array.isArray(p0.rt) && p0.rt.length === 1 ? p0.rt[0] : ""),
        }));
      }
    }).catch((e) => setErr(errMsg(e)));
  }, []);
  useEffect(() => { load(); }, [load]);

  const daftarWargaBaru = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusyBaru(true);
    try {
      const selPen = (info?.penugasan || []).find((p: any) => p.kode_kelurahan === baru.kode_kelurahan) || info?.penugasan?.[0];
      const payload = {
        client_uuid: newId(),
        no_kk: baru.no_kk.replace(/\D/g, "").slice(0, 16),
        nik: baru.nik.replace(/\D/g, "").slice(0, 16),
        kepala_keluarga: baru.kepala_keluarga.trim(),
        alamat: baru.alamat.trim(),
        rw: baru.rw.replace(/\D/g, ""),
        rt: baru.rt.replace(/\D/g, ""),
        jumlah_anggota_keluarga: Number(baru.jumlah_anggota_keluarga || 1),
        kode_kelurahan: baru.kode_kelurahan || selPen?.kode_kelurahan || "",
        kelurahan: selPen?.kelurahan || "",
        kecamatan: selPen?.kecamatan || "",
      };
      const r = await api.post("/verval/warga-baru", payload);
      toast.success("Pendaftaran warga baru dibuat; lanjutkan pengisian Verval & foto geotag");
      setShowBaru(false);
      navigate(`/verval/sasaran/${r.data.dtsen_ref}`);
    } catch (er) {
      toast.error(errMsg(er));
    } finally {
      setBusyBaru(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4" data-testid="verval-beranda">
      <section className="rounded-[16px] p-4 text-white shadow-sm" style={{ backgroundColor: "#232F3E" }} data-testid="verval-ringkasan">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-[#6FE3CF]">GeoTag · Verval DTSEN</p>
            <p className="font-head text-xl font-extrabold">Daftar Sasaran Pemeriksaan</p>
            <p className="mt-1 text-xs text-slate-300">Menampilkan warga wilayah Anda (termasuk tingkat kelurahan selama RT/RW awal masih kosong) serta usulan warga baru.</p>
          </div>
          <button type="button" onClick={() => setShowBaru((v) => !v)} data-testid="verval-btn-warga-baru"
            className={`inline-flex min-h-10 items-center gap-1.5 rounded-full bg-[#6FE3CF] px-3.5 py-2 text-xs font-bold text-[#232F3E] transition-colors hover:bg-[#8FEBDB] ${FR}`}>
            <Plus className="h-4 w-4" /> Daftarkan Warga Baru
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2" data-testid="verval-penugasan-saya">
          {(info?.penugasan || []).map((p: any) => (
            <span key={p.id} className="rounded-full bg-white/10 px-3 py-1 text-xs ring-1 ring-white/20">
              {p.kelurahan} · RW {p.rw} · RT {p.rt?.length ? p.rt.join(", ") : "semua"}{p.lintas_wilayah ? " · lintas wilayah" : ""}
            </span>
          ))}
          {info && !info.penugasan?.length && <span className="text-xs text-amber-200">Belum ada wilayah RT/RW aktif. Hubungi operator kecamatan Anda.</span>}
          {info?.jumlah_sasaran_khusus > 0 && <span className="rounded-full bg-white/10 px-3 py-1 text-xs ring-1 ring-white/20">+{info.jumlah_sasaran_khusus} KK sasaran khusus</span>}
        </div>
        {info && (
          <div className="mt-3 grid grid-cols-3 gap-2 text-center sm:grid-cols-6">
            {[
              ["Sasaran", info.jumlah_sasaran],
              ["Draft", info.per_status?.draft || 0],
              ["Menunggu Kel.", (info.per_status?.menunggu_kelurahan || 0) + (info.per_status?.terkirim || 0)],
              ["Menunggu Kec.", info.per_status?.menunggu_kecamatan || 0],
              ["Perbaikan", info.per_status?.perlu_perbaikan || 0],
              ["Disetujui", info.per_status?.disetujui || 0],
            ].map(([l, v]) => (
              <div key={l as string} className="rounded-[10px] bg-white/10 p-2"><p className="text-lg font-extrabold">{v as any}</p><p className="text-[10px] text-slate-300">{l}</p></div>
            ))}
          </div>
        )}
      </section>

      {showBaru && (
        <Card className="border-2 border-[#117A69]/40" data-testid="verval-warga-baru-form">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Pendaftaran Warga Baru (Belum Terdaftar di DTSEN)</h2>
              <p className="text-[11px] text-slate-600">Setelah didaftarkan, lengkapi formulir 11 indikator, foto kamera langsung + geotag, lalu kirim ke Kelurahan &amp; Kecamatan.</p>
            </div>
            <button type="button" onClick={() => setShowBaru(false)} className={`rounded-full p-1.5 hover:bg-slate-100 ${FR}`} aria-label="Tutup form warga baru"><X className="h-4 w-4" /></button>
          </div>
          <form className="grid gap-3 sm:grid-cols-2" onSubmit={daftarWargaBaru}>
            <Field label="Nomor KK (16 digit)">
              <input required className={INPUT} inputMode="numeric" maxLength={16} placeholder="7371..."
                value={baru.no_kk} onChange={(e) => setBaru({ ...baru, no_kk: e.target.value.replace(/\D/g, "").slice(0, 16) })}
                data-testid="wb-no-kk" />
            </Field>
            <Field label="NIK Kepala Keluarga (16 digit)">
              <input required className={INPUT} inputMode="numeric" maxLength={16} placeholder="7371..."
                value={baru.nik} onChange={(e) => setBaru({ ...baru, nik: e.target.value.replace(/\D/g, "").slice(0, 16) })}
                data-testid="wb-nik" />
            </Field>
            <Field label="Nama Kepala Keluarga">
              <input required className={INPUT} value={baru.kepala_keluarga}
                onChange={(e) => setBaru({ ...baru, kepala_keluarga: e.target.value })}
                data-testid="wb-nama" />
            </Field>
            <Field label="Jumlah Anggota Keluarga">
              <input type="number" min={1} max={50} className={INPUT} value={baru.jumlah_anggota_keluarga}
                onChange={(e) => setBaru({ ...baru, jumlah_anggota_keluarga: e.target.value })}
                data-testid="wb-anggota" />
            </Field>
            <div className="sm:col-span-2">
              <Field label="Alamat Lengkap">
                <input required className={INPUT} value={baru.alamat}
                  onChange={(e) => setBaru({ ...baru, alamat: e.target.value })}
                  data-testid="wb-alamat" />
              </Field>
            </div>
            {(info?.penugasan || []).length > 1 && (
              <div className="sm:col-span-2">
                <Field label="Kelurahan Penugasan">
                  <select className={INPUT} value={baru.kode_kelurahan} onChange={(e) => setBaru({ ...baru, kode_kelurahan: e.target.value })} data-testid="wb-kelurahan">
                    {(info?.penugasan || []).map((p: any) => (
                      <option key={p.id} value={p.kode_kelurahan}>{p.kelurahan} (Kec. {p.kecamatan})</option>
                    ))}
                  </select>
                </Field>
              </div>
            )}
            <Field label="RW">
              <input required className={INPUT} inputMode="numeric" placeholder="mis. 01" value={baru.rw}
                onChange={(e) => setBaru({ ...baru, rw: e.target.value.replace(/\D/g, "").slice(0, 4) })}
                data-testid="wb-rw" />
            </Field>
            <Field label="RT">
              <input required className={INPUT} inputMode="numeric" placeholder="mis. 02" value={baru.rt}
                onChange={(e) => setBaru({ ...baru, rt: e.target.value.replace(/\D/g, "").slice(0, 4) })}
                data-testid="wb-rt" />
            </Field>
            <div className="flex justify-end gap-2 sm:col-span-2">
              <button type="button" className={BTN_SECONDARY} onClick={() => setShowBaru(false)}>Batal</button>
              <button type="submit" disabled={busyBaru} className={BTN_PRIMARY} data-testid="wb-submit">
                {busyBaru ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Daftarkan &amp; Lanjut Verval
              </button>
            </div>
          </form>
        </Card>
      )}

      <Card>
        <form className="flex flex-wrap gap-2 sm:flex-nowrap" onSubmit={(e) => { e.preventDefault(); load(); }}>
          <input className={`${INPUT} min-w-[160px] flex-1`} placeholder="Cari nama KK, NIK, No. KK, atau alamat" value={q} onChange={(e) => setQ(e.target.value)} data-testid="verval-search" />
          <select className={`${INPUT} w-auto max-w-[190px] flex-1 sm:flex-none`} value={status} onChange={(e) => setStatus(e.target.value)} data-testid="verval-filter-status">
            <option value="">Semua status</option>
            {["belum_diverval", "draft", "menunggu_kelurahan", "menunggu_kecamatan", "perlu_perbaikan", "disetujui", "ditolak"].map((s) => (
              <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
            ))}
          </select>
          <button className={BTN_SM_PRIMARY} aria-label="Cari" data-testid="verval-search-btn"><Search className="h-4 w-4" /></button>
        </form>
        {err && <p className="mt-3 rounded bg-rose-50 p-2 text-xs text-rose-800" data-testid="verval-error">{err}</p>}
        {!list ? <p className="mt-4 text-sm text-slate-500"><Loader2 className="mr-1 inline h-4 w-4 animate-spin" />Memuat…</p> : (
          <ul className="mt-3 divide-y divide-slate-100" data-testid="verval-sasaran-list">
            {list.items.map((s: any) => (
              <li key={s.dtsen_ref}>
                <Link to={`/verval/sasaran/${s.dtsen_ref}`} className={`flex items-center justify-between gap-3 rounded-[10px] px-2 py-3 hover:bg-slate-50 ${FR}`} data-testid="verval-sasaran-item">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-slate-900">
                      {s.kepala_keluarga || "(tanpa nama)"} <UjiBadge show={s.data_uji} />
                      {(s.warga_baru || s.jenis_verval === "warga_baru") && (
                        <span className="ml-1.5 inline-flex items-center rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-[#117A69] ring-1 ring-[#117A69]/30">Warga Baru</span>
                      )}
                    </p>
                    <p className="truncate text-xs text-slate-600">{s.alamat} · {s.kelurahan} · RW {s.rw || "-"} / RT {s.rt || "-"}</p>
                    <p className="text-[11px] text-slate-500">KK {s.no_kk}{s.nik ? ` · NIK ${s.nik}` : " · NIK belum diisi"} · {DASAR_LABEL[s.dasar_akses] || s.dasar_akses}</p>
                  </div>
                  <StatusBadge status={s.status_verval} />
                </Link>
              </li>
            ))}
            {!list.items.length && <li className="py-6 text-center text-sm text-slate-500">Tidak ada sasaran untuk filter ini.</li>}
          </ul>
        )}
      </Card>
    </div>
  );
}

/* =================================================================== Formulir Verval */
const STEPS = ["Data & instruksi", "Formulir Verval", "Foto", "Lokasi GPS", "Tinjau & kirim"];

export function VervalForm() {
  const { ref = "" } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [d, setD] = useState<any>(null);
  const [rec, setRec] = useState<any>(null);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [identitas, setIdentitas] = useState<any>({
    no_kk: "", nik: "", kepala_keluarga: "", alamat: "",
    rw: "", rt: "", jumlah_anggota_keluarga: "", desil_usulan: "",
  });
  const [ind, setInd] = useState<Record<string, { kesesuaian?: string; kondisi_riil?: string; catatan?: string }>>({});
  const [anggota, setAnggota] = useState<any[]>([]);
  const [kesimpulan, setKesimpulan] = useState<{ pilihan?: string; catatan?: string }>({});
  const [catatan, setCatatan] = useState("");
  const [cfg, setCfg] = useState<any>(null);

  const load = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([api.get(`/verval/sasaran/${ref}`), api.get("/verval/konfigurasi")]);
      setD(s.data); setCfg(c.data);
      const baseSas = s.data.sasaran || {};
      if (s.data.record) {
        const r = s.data.record;
        const idl = r.identitas_lapangan || r.warga_baru || {};
        setRec(r);
        setIdentitas({
          no_kk: idl.no_kk || baseSas.no_kk || "",
          nik: idl.nik || baseSas.nik || "",
          kepala_keluarga: idl.kepala_keluarga || baseSas.kepala_keluarga || "",
          alamat: idl.alamat || baseSas.alamat || "",
          rw: idl.rw || baseSas.rw || r.rw || "",
          rt: idl.rt || baseSas.rt || r.rt || "",
          jumlah_anggota_keluarga: String(idl.jumlah_anggota_keluarga ?? baseSas.jumlah_anggota_keluarga ?? ""),
          desil_usulan: String(idl.desil_usulan ?? baseSas.desil_nasional ?? ""),
        });
        setInd(r.indikator || {});
        setAnggota(r.anggota_rentan || []);
        setKesimpulan(r.kesimpulan || {});
        setCatatan(r.catatan_umum || "");
      } else {
        setIdentitas({
          no_kk: baseSas.no_kk || "",
          nik: baseSas.nik || "",
          kepala_keluarga: baseSas.kepala_keluarga || "",
          alamat: baseSas.alamat || "",
          rw: baseSas.rw || "",
          rt: baseSas.rt || "",
          jumlah_anggota_keluarga: String(baseSas.jumlah_anggota_keluarga ?? ""),
          desil_usulan: String(baseSas.desil_nasional ?? ""),
        });
      }
    } catch (e) { setErr(errMsg(e)); }
  }, [ref]);
  useEffect(() => { load(); }, [load]);

  const isWargaBaru = Boolean(rec?.jenis_verval === "warga_baru" || d?.sasaran?.warga_baru);
  const isOwner = !rec || !user?.id || rec.operator_id === String(user.id);
  const editable = Boolean(rec && isOwner && ["draft", "perlu_perbaikan"].includes(rec.status));

  /** Validasi Form Verval sisi klien (sama dengan backend). */
  const kekuranganForm = useMemo((): string[] => {
    const out: string[] = [];
    const nikDigits = String(identitas.nik || "").replace(/\D/g, "");
    const kkDigits = String(identitas.no_kk || "").replace(/\D/g, "");
    if (isWargaBaru) {
      if (kkDigits.length !== 16) out.push("Nomor KK warga baru wajib 16 digit");
      if (nikDigits.length !== 16) out.push("NIK warga baru wajib 16 digit");
      if ((identitas.kepala_keluarga || "").trim().length < 2) out.push("Nama Kepala Keluarga wajib diisi");
      if ((identitas.alamat || "").trim().length < 3) out.push("Alamat rumah wajib diisi");
      if (!String(identitas.rw || "").trim() || !String(identitas.rt || "").trim()) out.push("RW dan RT wajib diisi");
    } else if (nikDigits && nikDigits.length !== 16) {
      out.push("NIK yang diisi wajib 16 digit angka");
    }
    (cfg?.indikator || []).forEach((i: any) => {
      const v = ind[i.key] || {};
      if (!isWargaBaru && !v.kesesuaian) out.push(`${i.label} — kolom Kesesuaian belum diisi`);
      if (!v.kondisi_riil) out.push(`${i.label} — kolom Kondisi Riil Lapangan belum diisi`);
      const perlu = (!isWargaBaru && INDIKATOR_PERLU_CATATAN.has(v.kesesuaian || ""))
        || INDIKATOR_PERLU_CATATAN.has(v.kondisi_riil || "");
      if (perlu && !(v.catatan || "").trim()) out.push(`${i.label} — catatan verifikator wajib diisi`);
    });
    if (!kesimpulan?.pilihan) out.push("Kesimpulan Verval belum dipilih (Bagian IV)");
    else {
      const sel = (cfg?.kesimpulan || []).find((k: any) => k.key === kesimpulan.pilihan);
      if (sel?.wajib_catatan && !(kesimpulan.catatan || "").trim())
        out.push(`Catatan wajib untuk kesimpulan '${sel.label}'`);
    }
    return out;
  }, [identitas, ind, kesimpulan, cfg, isWargaBaru]);
  const formLengkap = kekuranganForm.length === 0;

  const mulai = async () => {
    setBusy(true);
    try {
      const r = await api.post("/verval/records", { dtsen_ref: ref, client_uuid: clientUuidFor(ref) });
      setRec(r.data); setInd(r.data.indikator || {}); setStep(0); toast.success("Draft Verval dibuat");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  const identitasPayload = () => ({
    no_kk: String(identitas.no_kk || "").replace(/\D/g, "").slice(0, 16),
    nik: String(identitas.nik || "").replace(/\D/g, "").slice(0, 16),
    kepala_keluarga: identitas.kepala_keluarga || "",
    alamat: identitas.alamat || "",
    rw: String(identitas.rw || "").replace(/\D/g, ""),
    rt: String(identitas.rt || "").replace(/\D/g, ""),
    jumlah_anggota_keluarga: identitas.jumlah_anggota_keluarga ? Number(identitas.jumlah_anggota_keluarga) : undefined,
    desil_usulan: identitas.desil_usulan ? Number(identitas.desil_usulan) : null,
  });

  const simpan = async (extra: any = {}, silent = false) => {
    if (!rec || !editable) return rec;
    try {
      const r = await api.put(`/verval/records/${rec.id}`, {
        identitas_lapangan: identitasPayload(),
        indikator: ind,
        anggota_rentan: anggota,
        kesimpulan,
        catatan_umum: catatan,
        ...extra,
      });
      setRec(r.data);
      if (extra.gps) umumkanPerubahanPeta();
      if (!silent) toast.success("Tersimpan sebagai draft");
      return r.data;
    } catch (e) { toast.error(errMsg(e)); return null; }
  };

  const kirim = async () => {
    setBusy(true); setErr("");
    try {
      const saved = await simpan({}, true);
      if (!saved) { setBusy(false); return; }
      const r = await api.post(`/verval/records/${rec.id}/kirim`);
      setRec(r.data); localStorage.removeItem(`verval_cu_${ref}`);
      toast.success("Hasil Verval dikirim ke Kelurahan");
    } catch (e) { setErr(errMsg(e)); toast.error("Belum dapat dikirim"); } finally { setBusy(false); }
  };

  if (err && !d) return <div className="mx-auto max-w-2xl"><Card><p className="text-sm text-rose-800" data-testid="verval-error">{err}</p><Link to="/verval" className={`${BTN_SM} mt-3`}>Kembali</Link></Card></div>;
  if (!d) return <p className="p-6 text-sm text-slate-500"><Loader2 className="mr-1 inline h-4 w-4 animate-spin" />Memuat…</p>;
  const s = d.sasaran;

  return (
    <div className="mx-auto max-w-2xl space-y-4 pb-24" data-testid="verval-form">
      <button type="button" onClick={() => navigate("/verval")} className={BTN_SM} data-testid="verval-back"><ChevronLeft className="h-4 w-4" /> Daftar sasaran</button>
      <Card>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#117A69]">
              {isWargaBaru ? "Pendaftaran Warga Baru" : "Sasaran DTSEN"} <UjiBadge show={s.data_uji} />
            </p>
            <p className="font-head text-lg font-extrabold text-slate-900" data-testid="verval-sasaran-nama">{identitas.kepala_keluarga || s.kepala_keluarga}</p>
            <p className="text-xs text-slate-600">{identitas.alamat || s.alamat} · {s.kelurahan}, Kec. {s.kecamatan} · RW {identitas.rw || s.rw || "-"} / RT {identitas.rt || s.rt || "-"}</p>
            <p className="text-[11px] text-slate-500">
              No. KK {identitas.no_kk || s.no_kk} · {identitas.nik ? `NIK ${identitas.nik}` : "NIK belum diisi"} · {identitas.jumlah_anggota_keluarga || s.jumlah_anggota_keluarga || "-"} anggota · {DASAR_LABEL[s.dasar_akses] || s.dasar_akses}
            </p>
          </div>
          {rec && <StatusBadge status={rec.status} testid="verval-status" />}
        </div>
      </Card>

      {!rec ? (
        <Card>
          <h2 className="text-sm font-bold">Sebelum memulai</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-700">
            <li>Datangi rumah warga dan cocokkan Nama Kepala Keluarga, No. KK, NIK, RT/RW, serta kondisi ekonomi riil.</li>
            <li>Foto rumah <b>wajib dijepret langsung dari kamera aplikasi web</b> (sistem mencetak watermark geotag koordinat, waktu, wilayah, dan petugas — tanpa NIK).</li>
            <li>Target akurasi GPS <b>≤ {cfg?.gps_max_akurasi_m ?? 30} m</b>; bila di lorong padat sinyal sulit, tersedia opsi geser pin manual dengan alasan.</li>
            <li>Alur berjenjang: dikirim ke <b>Kelurahan</b> untuk diperiksa tahap 1, lalu diteruskan ke <b>Kecamatan</b> untuk persetujuan akhir dan pembaruan data aktif sistem (data awal DTSEN tetap disimpan sebagai pembanding).</li>
          </ul>
          <button type="button" className={`${BTN_PRIMARY} mt-4 w-full`} onClick={mulai} disabled={busy} data-testid="verval-mulai">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4" />} Mulai Verval
          </button>
        </Card>
      ) : (
        <>
          {rec.status === "perlu_perbaikan" && (rec.review_catatan || rec.kelurahan_catatan) && (
            <p className="rounded-[12px] bg-orange-50 p-3 text-xs text-orange-900 ring-1 ring-orange-200" data-testid="verval-catatan-perbaikan">
              <b>Perlu perbaikan:</b> {rec.review_catatan || rec.kelurahan_catatan}
            </p>
          )}
          {editable ? (
            <>
              <nav className="flex gap-1 overflow-x-auto" aria-label="Langkah Verval">
                {STEPS.map((t, i) => {
                  const locked = (i === 2 || i === 3 || i === 4) && !formLengkap;
                  return (
                    <button key={t} type="button"
                      onClick={() => { if (locked) { toast.warning("Selesaikan Formulir Verval terlebih dahulu"); return; } simpan({}, true); setStep(i); }}
                      disabled={locked}
                      data-testid={`verval-step-${i}`}
                      aria-disabled={locked}
                      className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-bold ${FR} ${step === i ? "bg-[#117A69] text-white" : locked ? "bg-slate-100 text-slate-400 cursor-not-allowed" : "bg-white text-slate-700 ring-1 ring-slate-200"}`}>
                      {locked && <Lock className="mr-0.5 inline h-3 w-3" />}
                      {i + 1}. {t}
                    </button>
                  );
                })}
              </nav>
              {step === 0 && <LangkahData d={d} cfg={cfg} />}
              {step === 1 && <LangkahFormulir d={d} cfg={cfg} isWargaBaru={isWargaBaru}
                                              identitas={identitas} setIdentitas={setIdentitas}
                                              ind={ind} setInd={setInd}
                                              anggota={anggota} setAnggota={setAnggota}
                                              kesimpulan={kesimpulan} setKesimpulan={setKesimpulan}
                                              catatan={catatan} setCatatan={setCatatan}
                                              kekurangan={kekuranganForm} />}
              {step === 2 && <LangkahFoto rec={rec} setRec={setRec} cfg={cfg} />}
              {step === 3 && <LangkahGps rec={rec} cfg={cfg} simpan={simpan} />}
              {step === 4 && <LangkahTinjau rec={rec} isWargaBaru={isWargaBaru} identitas={identitas} ind={ind} anggota={anggota} kesimpulan={kesimpulan} cfg={cfg} err={err} busy={busy} kirim={kirim} kekuranganForm={kekuranganForm} />}
              <div className="fixed inset-x-0 bottom-0 z-40 flex gap-2 border-t border-slate-200 bg-white p-3 md:static md:border-0 md:bg-transparent md:p-0">
                <button type="button" className={`${BTN_SECONDARY} flex-1`} onClick={() => simpan()} data-testid="verval-simpan-draft">Simpan draft</button>
                {step < 4 && <button type="button" className={`${BTN_PRIMARY} flex-1`}
                  disabled={step === 1 && !formLengkap}
                  onClick={() => {
                    if (step === 1 && !formLengkap) { toast.warning("Lengkapi formulir sebelum melanjutkan"); return; }
                    simpan({}, true); setStep(step + 1);
                  }} data-testid="verval-lanjut">
                  {step === 1 && !formLengkap ? <><Lock className="h-4 w-4" /> Form belum lengkap</> : "Lanjut"}
                </button>}
              </div>
            </>
          ) : <TandaTerima rec={rec} />}
        </>
      )}
    </div>
  );
}

function LangkahData({ d, cfg }: any) {
  return (
    <Card data-testid="verval-langkah-data">
      <h2 className="text-sm font-bold">Data DTSEN minimum untuk pemeriksaan</h2>
      <p className="mt-1 text-[11px] text-amber-800">{cfg?.indikator_sumber}</p>
      <dl className="mt-3 space-y-2 text-xs">
        {(cfg?.indikator || []).map((i: any) => (
          <div key={i.key} className="flex flex-col border-b border-dashed border-slate-200 pb-2"><dt className="font-semibold text-slate-700">{i.label}</dt><dd><DtsenNilai vals={d.dtsen?.[i.key]} /></dd></div>
        ))}
      </dl>
    </Card>
  );
}

/** Koordinat tempat foto diambil (GPS perangkat atau metadata EXIF). */
export function FotoKoordinat({ gps, className = "" }: { gps?: any; className?: string }) {
  if (!gps || gps.lat == null || gps.lng == null) {
    return <p className={`truncate text-slate-400 ${className}`} data-testid="verval-foto-koordinat-kosong"><MapPin className="mr-0.5 inline h-3 w-3" />Tanpa koordinat</p>;
  }
  const sumber = gps.sumber === "exif_foto" ? "EXIF" : "GPS";
  return (
    <p className={`truncate font-semibold text-[#0f5f52] ${className}`} title={`Koordinat ${sumber}`} data-testid="verval-foto-koordinat">
      <MapPin className="mr-0.5 inline h-3 w-3" />{Number(gps.lat).toFixed(5)}, {Number(gps.lng).toFixed(5)}
      {gps.akurasi_m != null ? ` ±${Math.round(gps.akurasi_m)} m` : ` · ${sumber}`}
    </p>
  );
}

function LangkahFoto({ rec, setRec, cfg }: any) {
  const [antrean, setAntrean] = useState<any[]>([]);
  const [jenis, setJenis] = useState("rumah_depan");
  const [camOpen, setCamOpen] = useState(false);
  const [camReady, setCamReady] = useState(false);
  const [camErr, setCamErr] = useState("");
  const [facing, setFacing] = useState<"environment" | "user">("environment");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const pos = useRef<any>(null);
  const [posLive, setPosLive] = useState<any>(null);
  const [posGalat, setPosGalat] = useState("");

  useEffect(() => {
    if (!navigator.geolocation) { setPosGalat("Perangkat tidak mendukung GPS."); return; }
    const id = navigator.geolocation.watchPosition(
      (p) => { pos.current = p.coords; setPosLive({ lat: p.coords.latitude, lng: p.coords.longitude, akurasi_m: Math.round(p.coords.accuracy * 10) / 10 }); setPosGalat(""); },
      (e) => setPosGalat(e.code === 1 ? "Izin lokasi ditolak — aktifkan izin lokasi agar geotag foto terekam." : "Sinyal GPS belum tersedia."),
      { enableHighAccuracy: true, maximumAge: 5000 });
    return () => navigator.geolocation.clearWatch(id);
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => { try { t.stop(); } catch { /* noop */ } });
      streamRef.current = null;
    }
    if (videoRef.current) {
      try { (videoRef.current as any).srcObject = null; } catch { /* noop */ }
    }
    setCamReady(false);
  }, []);

  useEffect(() => () => stopCamera(), [stopCamera]);

  const startCamera = useCallback(async (mode: "environment" | "user") => {
    stopCamera();
    setCamErr("");
    if (!window.isSecureContext) {
      setCamErr("Kamera web langsung memerlukan koneksi HTTPS (atau localhost).");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setCamErr("Peramban ini tidak mendukung kamera web langsung (getUserMedia). Gunakan Chrome/Safari versi terbaru.");
      return;
    }
    setCamOpen(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: mode }, width: { ideal: 1280 }, height: { ideal: 960 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCamReady(true);
    } catch (e: any) {
      const name = e?.name || "";
      setCamErr(
        name === "NotAllowedError" || name === "PermissionDeniedError"
          ? "Izin kamera ditolak. Aktifkan izin kamera pada pengaturan peramban lalu coba lagi."
          : name === "NotFoundError"
            ? "Kamera tidak ditemukan pada perangkat ini."
            : "Gagal membuka kamera perangkat. Tutup aplikasi lain yang memakai kamera lalu coba lagi.",
      );
      stopCamera();
    }
  }, [stopCamera]);

  const unggah = async (item: any) => {
    setAntrean((a) => a.map((x) => (x.cid === item.cid ? { ...x, status: "mengunggah", galat: "" } : x)));
    const fd = new FormData();
    fd.append("file", item.file);
    fd.append("client_foto_id", item.cid);
    fd.append("jenis", item.jenis);
    fd.append("diambil_at", item.diambil_at);
    fd.append("sumber_kamera", "kamera_web_langsung");
    if (item.coords) {
      fd.append("lat", String(item.coords.latitude));
      fd.append("lng", String(item.coords.longitude));
      fd.append("akurasi_m", String(item.coords.accuracy));
    }
    try {
      const r = await api.post(`/verval/records/${rec.id}/foto`, fd);
      const upd: any = { ...rec, foto: r.data.foto, foto_count: r.data.foto.length };
      if (r.data.gps_record) upd.gps = r.data.gps_record;
      setRec(upd);
      umumkanPerubahanPeta();
      setAntrean((a) => a.filter((x) => x.cid !== item.cid));
      const terakhir = (r.data.foto || []).slice(-1)[0];
      const g = terakhir?.gps_saat_foto;
      toast[r.data.duplikat ? "info" : "success"](r.data.duplikat ? "Foto sudah tersimpan sebelumnya"
        : g ? `Foto kamera tersimpan · watermark geotag (${Number(g.lat).toFixed(5)}, ${Number(g.lng).toFixed(5)})` : "Foto kamera terunggah dengan watermark wilayah & waktu");
    } catch (e) {
      setAntrean((a) => a.map((x) => (x.cid === item.cid ? { ...x, status: "gagal", galat: errMsg(e) } : x)));
    }
  };

  const jepret = () => {
    const vid = videoRef.current;
    if (!vid || !vid.videoWidth || !vid.videoHeight) { toast.error("Kamera belum siap"); return; }
    const canvas = document.createElement("canvas");
    canvas.width = vid.videoWidth;
    canvas.height = vid.videoHeight;
    const ctx2d = canvas.getContext("2d");
    if (!ctx2d) { toast.error("Gagal memproses tangkapan kamera"); return; }
    ctx2d.drawImage(vid, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) { toast.error("Gagal menyimpan hasil jepretan"); return; }
      if (blob.size > (cfg?.max_foto_mb || 8) * 1048576) {
        toast.error(`Ukuran foto melebihi ${cfg?.max_foto_mb || 8} MB`);
        return;
      }
      const file = new File([blob], `geotag-${Date.now()}.jpg`, { type: "image/jpeg" });
      const item = { cid: newId(), file, jenis, diambil_at: new Date().toISOString(), coords: pos.current, status: "antre", preview: URL.createObjectURL(blob) };
      setAntrean((a) => [...a, item]);
      unggah(item);
      stopCamera();
      setCamOpen(false);
    }, "image/jpeg", 0.88);
  };

  const hapus = async (fid: string) => {
    try { const r = await api.delete(`/verval/records/${rec.id}/foto/${fid}`); setRec({ ...rec, foto: r.data.foto, foto_count: r.data.foto.length }); }
    catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <Card data-testid="verval-langkah-foto">
      <h2 className="text-sm font-bold">Foto Rumah Langsung via Kamera Web</h2>
      <p className="mt-1 text-xs text-slate-600">
        Minimal {cfg?.min_foto || 1} foto, maksimal {cfg?.max_foto_per_verval || 6}. <b>Wajib jepret langsung dari kamera aplikasi</b> (galeri/WA dinonaktifkan).
        Sistem otomatis mencetak <b>watermark geotag</b> (koordinat, waktu WITA, wilayah, petugas — tanpa NIK) di gambar foto dan menyinkronkannya ke peta.
      </p>
      <p className={`mt-2 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${posLive ? "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200" : "bg-amber-50 text-amber-900 ring-1 ring-amber-200"}`} data-testid="verval-foto-posisi">
        <MapPin className="h-3 w-3" />
        {posLive ? `Posisi saat ini: ${posLive.lat.toFixed(6)}, ${posLive.lng.toFixed(6)} (±${posLive.akurasi_m} m)` : posGalat || "Mencari posisi GPS…"}
      </p>

      <div className="mt-3 flex flex-wrap gap-2 sm:flex-nowrap">
        <select className={`${INPUT} w-full sm:max-w-[180px]`} value={jenis} onChange={(e) => setJenis(e.target.value)} data-testid="verval-jenis-foto">
          {(cfg?.jenis_foto || []).map((j: string) => <option key={j} value={j}>{j.replace(/_/g, " ")}</option>)}
        </select>
        {!camOpen ? (
          <button type="button" className={`${BTN_SM_PRIMARY} w-full flex-1 sm:w-auto`} onClick={() => startCamera(facing)} data-testid="verval-buka-kamera">
            <Camera className="h-4 w-4" /> Buka Kamera &amp; Ambil Foto
          </button>
        ) : (
          <button type="button" className={`${BTN_SECONDARY} w-full flex-1 sm:w-auto`} onClick={() => { stopCamera(); setCamOpen(false); }} data-testid="verval-tutup-kamera">
            <X className="h-4 w-4" /> Tutup Kamera
          </button>
        )}
      </div>

      {camErr && (
        <p className="mt-3 flex gap-2 rounded-[10px] bg-rose-50 p-2.5 text-xs text-rose-800 ring-1 ring-rose-200" data-testid="verval-kamera-error">
          <TriangleAlert className="h-4 w-4 shrink-0" /> {camErr}
        </p>
      )}

      {camOpen && (
        <div className="mt-3 overflow-hidden rounded-[14px] bg-[#232F3E] p-2 text-white" data-testid="verval-kamera-box">
          <div className="relative aspect-[4/3] w-full overflow-hidden rounded-[10px] bg-black">
            <video ref={videoRef} playsInline muted autoPlay className="h-full w-full object-cover" data-testid="verval-kamera-video" />
            {!camReady && (
              <div className="absolute inset-0 grid place-items-center text-xs text-slate-200">
                <span><Loader2 className="mr-1 inline h-4 w-4 animate-spin" />Membuka kamera…</span>
              </div>
            )}
          </div>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <button type="button" onClick={() => { const nx = facing === "environment" ? "user" : "environment"; setFacing(nx); startCamera(nx); }}
              className={`inline-flex min-h-10 items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold hover:bg-white/20 ${FR}`}
              data-testid="verval-ganti-kamera">
              <SwitchCamera className="h-4 w-4" /> Putar Kamera
            </button>
            <button type="button" disabled={!camReady} onClick={jepret}
              className={`inline-flex min-h-10 items-center gap-1.5 rounded-full bg-[#6FE3CF] px-5 py-2 text-xs font-extrabold text-[#232F3E] hover:bg-[#8FEBDB] disabled:opacity-50 ${FR}`}
              data-testid="verval-jepret-foto">
              <Camera className="h-4 w-4" /> Jepret Foto
            </button>
          </div>
        </div>
      )}

      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid="verval-foto-grid">
        {(rec.foto || []).map((f: any) => (
          <figure key={f.id} className="relative overflow-hidden rounded-[10px] ring-1 ring-slate-200">
            <img src={fotoUrl(f.id)} alt={`Foto ${f.jenis}`} className="h-28 w-full object-cover" />
            <figcaption className="bg-white px-2 py-1 text-[10px]">
              <div className="flex items-center justify-between"><span><CheckCircle2 className="mr-0.5 inline h-3 w-3 text-emerald-600" />{f.jenis.replace(/_/g, " ")}</span>
                <button type="button" onClick={() => hapus(f.id)} aria-label="Hapus foto" className="text-rose-700" data-testid="verval-hapus-foto"><Trash2 className="h-3.5 w-3.5" /></button></div>
              <FotoKoordinat gps={f.gps_saat_foto} />
            </figcaption>
          </figure>
        ))}
        {antrean.map((a) => (
          <figure key={a.cid} className="relative overflow-hidden rounded-[10px] ring-1 ring-slate-200" data-testid="verval-foto-antrean">
            <img src={a.preview} alt="Foto menunggu unggah" className="h-28 w-full object-cover opacity-60" />
            <figcaption className="bg-white px-2 py-1 text-[10px]">
              {a.status === "gagal" ? (
                <span className="text-rose-700">Gagal: {a.galat} <button type="button" className="font-bold underline" onClick={() => unggah(a)} data-testid="verval-ulang-unggah"><RefreshCw className="inline h-3 w-3" /> Ulangi</button></span>
              ) : <span><Upload className="mr-0.5 inline h-3 w-3 animate-pulse" />Mengunggah…</span>}
            </figcaption>
          </figure>
        ))}
      </div>
    </Card>
  );
}

function PinManualMap({ center, onChange }: { center: { lat: number; lng: number }; onChange: (c: { lat: number; lng: number }) => void }) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!elRef.current || mapRef.current) return;
    ensureLeafletSafe();
    const map = L.map(elRef.current, { center: [center.lat, center.lng], zoom: 17 });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);
    const marker = L.marker([center.lat, center.lng], { draggable: true }).addTo(map);
    marker.on("dragend", () => {
      const p = marker.getLatLng();
      onChangeRef.current({ lat: Number(p.lat.toFixed(6)), lng: Number(p.lng.toFixed(6)) });
    });
    map.on("click", (e: L.LeafletMouseEvent) => {
      marker.setLatLng(e.latlng);
      onChangeRef.current({ lat: Number(e.latlng.lat.toFixed(6)), lng: Number(e.latlng.lng.toFixed(6)) });
    });
    mapRef.current = map;
    markerRef.current = marker;
    return () => {
      safeRemoveMap(mapRef.current);
      mapRef.current = null;
      markerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (markerRef.current) {
      markerRef.current.setLatLng([center.lat, center.lng]);
    }
  }, [center.lat, center.lng]);

  return <div ref={elRef} className="h-64 w-full overflow-hidden rounded-[12px] border border-slate-200" data-testid="verval-pin-manual-map" />;
}

function LangkahGps({ rec, cfg, simpan }: any) {
  const [live, setLive] = useState<any>(null);
  const [state, setState] = useState<string>("idle");
  const [galat, setGalat] = useState("");
  const watch = useRef<number | null>(null);
  const batas = cfg?.gps_max_akurasi_m ?? 30;
  const g = rec.gps || {};
  const [manualOpen, setManualOpen] = useState(g.status_gps === "pin_manual");
  const [manualPos, setManualPos] = useState<{ lat: number; lng: number }>({
    lat: g.lat ?? -5.147665,
    lng: g.lng ?? 119.432732,
  });
  const [alasanManual, setAlasanManual] = useState(g.alasan_manual || "");

  const stop = () => { if (watch.current !== null) navigator.geolocation.clearWatch(watch.current); watch.current = null; };
  useEffect(() => stop, []);

  const mulai = () => {
    setGalat("");
    if (!window.isSecureContext) { setState("error"); setGalat("Akses lokasi memerlukan HTTPS."); return; }
    if (!navigator.geolocation) { setState("error"); setGalat("Perangkat/peramban tidak mendukung GPS."); simpan({ gps: { izin: "tidak_diketahui", galat: "tidak_didukung" } }, true); return; }
    setState("mencari");
    watch.current = navigator.geolocation.watchPosition(
      (p) => {
        const pt = { lat: p.coords.latitude, lng: p.coords.longitude, akurasi_m: Math.round(p.coords.accuracy * 10) / 10, waktu: new Date(p.timestamp).toISOString() };
        setLive(pt);
        setManualPos((prev) => (g.status_gps === "pin_manual" ? prev : { lat: pt.lat, lng: pt.lng }));
      },
      async (e) => {
        stop(); setState("error");
        const denied = e.code === 1;
        setGalat(denied ? "Izin lokasi ditolak. Aktifkan izin lokasi untuk situs ini di pengaturan peramban." : e.code === 3 ? "Waktu pencarian GPS habis. Coba di area terbuka atau gunakan pin manual di peta." : "Sinyal GPS tidak tersedia.");
        await simpan({ gps: { izin: denied ? "denied" : "granted", galat: e.message?.slice(0, 180) || String(e.code) } }, true);
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 60000 },
    );
  };

  const gunakan = async () => {
    if (!live) return;
    const r = await simpan({ gps: { lat: live.lat, lng: live.lng, akurasi_m: live.akurasi_m, diambil_at: live.waktu, izin: "granted", sumber: "browser_geolocation" } }, true);
    if (r) { stop(); setState("idle"); toast[r.gps.status_gps === "memenuhi" ? "success" : "warning"](GPS_LABEL[r.gps.status_gps]); }
  };

  const simpanPinManual = async () => {
    if (alasanManual.trim().length < 5) {
      toast.error("Isi alasan penyesuaian pin manual minimal 5 karakter");
      return;
    }
    const r = await simpan({
      gps: {
        lat: manualPos.lat,
        lng: manualPos.lng,
        akurasi_m: live?.akurasi_m ?? null,
        diambil_at: new Date().toISOString(),
        izin: live ? "granted" : "prompt",
        sumber: "pin_manual",
        alasan_manual: alasanManual.trim(),
        gps_asal: live || null,
      },
    }, true);
    if (r) {
      stop();
      setState("idle");
      toast.success("Titik pin manual tersimpan");
    }
  };

  const ok = live && live.akurasi_m <= batas;
  return (
    <Card data-testid="verval-langkah-gps">
      <h2 className="text-sm font-bold">Rekam lokasi GPS</h2>
      <p className="mt-1 text-xs text-slate-600">
        Target akurasi GPS <b>≤ {batas} m</b>. Bila berada di lorong padat atau GPS perangkat terus meleset di atas {batas} m, gunakan opsi <b>Pin Manual di Peta</b> beserta alasannya agar pengiriman tetap berjalan lancar.
      </p>
      <div className={`mt-3 rounded-[12px] p-3 text-xs ring-1 ${g.status_gps === "memenuhi" || g.status_gps === "pin_manual" ? "bg-emerald-50 ring-emerald-200" : "bg-slate-50 ring-slate-200"}`} data-testid="verval-gps-tersimpan">
        <p className="font-bold">Tersimpan: {GPS_LABEL[g.status_gps] || "-"}</p>
        {g.lat != null && <p>{g.lat.toFixed(6)}, {g.lng.toFixed(6)}{g.akurasi_m != null ? ` · ±${g.akurasi_m} m` : ""} · {fmtWaktu(g.diambil_at)}</p>}
        {g.status_gps === "pin_manual" && g.alasan_manual && <p className="mt-0.5 text-amber-900">Alasan manual: {g.alasan_manual}</p>}
        {g.galat && <p className="text-rose-700">{g.galat}</p>}
      </div>
      {state === "mencari" && (
        <div className={`mt-3 rounded-[12px] p-3 text-sm ring-1 ${ok ? "bg-emerald-50 ring-emerald-300" : "bg-amber-50 ring-amber-300"}`} data-testid="verval-gps-live" aria-live="polite">
          {live ? <>
            <p className="font-extrabold">Akurasi saat ini: ±{live.akurasi_m} m {ok ? "· memenuhi" : `· melebihi batas ${batas} m`}</p>
            <p className="text-xs">{live.lat.toFixed(6)}, {live.lng.toFixed(6)}</p>
            {!ok && <p className="mt-1 text-xs">Bisa tunggu di area terbuka atau langsung gunakan tombol <b>Pin Manual di Peta</b> di bawah.</p>}
          </> : <p><Loader2 className="mr-1 inline h-4 w-4 animate-spin" />Mencari sinyal GPS…</p>}
        </div>
      )}
      {galat && <p className="mt-3 flex gap-2 rounded bg-rose-50 p-2 text-xs text-rose-800" data-testid="verval-gps-error"><TriangleAlert className="h-4 w-4 shrink-0" />{galat}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {state !== "mencari"
          ? <button type="button" className={BTN_SM_PRIMARY} onClick={mulai} data-testid="verval-gps-mulai"><Crosshair className="h-4 w-4" /> Mulai rekam GPS</button>
          : <>
            <button type="button" className={BTN_SM_PRIMARY} onClick={gunakan} disabled={!live} data-testid="verval-gps-gunakan"><MapPin className="h-4 w-4" /> Simpan lokasi GPS{live && !ok ? " (belum memenuhi)" : ""}</button>
            <button type="button" className={BTN_SM} onClick={() => { stop(); setState("idle"); }} data-testid="verval-gps-batal">Berhenti</button>
          </>}
        <button type="button" className={BTN_SM} onClick={() => setManualOpen((v: boolean) => !v)} data-testid="verval-gps-manual-toggle">
          <MapPin className="h-4 w-4" /> {manualOpen ? "Tutup pin manual" : `Sesuaikan pin manual di peta (bila > ${batas} m)`}
        </button>
      </div>

      {manualOpen && (
        <div className="mt-3 space-y-2 rounded-[12px] border border-slate-200 bg-slate-50 p-3" data-testid="verval-gps-manual-panel">
          <p className="text-xs font-bold text-slate-800">Geser pin merah atau klik lokasi rumah pada peta:</p>
          <PinManualMap center={manualPos} onChange={setManualPos} />
          <p className="text-[11px] font-mono text-slate-600">Titik terpilih: {manualPos.lat.toFixed(6)}, {manualPos.lng.toFixed(6)}</p>
          <Field label="Alasan penyesuaian manual (wajib, minimal 5 karakter)">
            <input className={INPUT} placeholder="Contoh: Sinyal GPS di lorong padat meleset di atas 30 m"
              value={alasanManual} onChange={(e) => setAlasanManual(e.target.value)} data-testid="verval-gps-manual-alasan" />
          </Field>
          <button type="button" className={BTN_SM_PRIMARY} onClick={simpanPinManual} data-testid="verval-gps-manual-simpan">
            <MapPin className="h-4 w-4" /> Simpan titik pin manual
          </button>
        </div>
      )}
    </Card>
  );
}

function LangkahFormulir({ d, cfg, isWargaBaru, identitas, setIdentitas, ind, setInd, anggota, setAnggota, kesimpulan, setKesimpulan, catatan, setCatatan, kekurangan }: any) {
  const setItem = (k: string, patch: any) =>
    setInd({ ...ind, [k]: { kesesuaian: "", kondisi_riil: "", catatan: "", ...(ind[k] || {}), ...patch } });

  const kondisiOptionsFor = (hub: string) =>
    (cfg?.kondisi_rentan && cfg.kondisi_rentan[hub]) || [];

  const addAnggota = () => setAnggota([...(anggota || []), {
    id: newId(), nik: "", nama: "", status_hubungan: "", kondisi_rentan: [], rekomendasi_opd: "", catatan: "",
  }]);
  const updateAnggota = (idx: number, patch: any) => {
    const next = [...anggota];
    next[idx] = { ...next[idx], ...patch };
    if (patch.status_hubungan && patch.status_hubungan !== anggota[idx].status_hubungan) {
      next[idx].kondisi_rentan = [];
      next[idx].rekomendasi_opd = "";
    }
    setAnggota(next);
  };
  const hapusAnggota = (idx: number) => setAnggota(anggota.filter((_: any, i: number) => i !== idx));

  const toggleKondisi = (idx: number, key: string, opd: string) => {
    const kr: string[] = anggota[idx].kondisi_rentan || [];
    const next = kr.includes(key) ? kr.filter((x) => x !== key) : [...kr, key];
    const rek = anggota[idx].rekomendasi_opd?.trim();
    updateAnggota(idx, { kondisi_rentan: next, rekomendasi_opd: rek || opd });
  };

  return (
    <div className="space-y-3" data-testid="verval-langkah-formulir">
      {/* Status ringkas */}
      <Card>
        <div className="flex items-start gap-3">
          <ClipboardCheck className="mt-0.5 h-5 w-5 shrink-0 text-[#117A69]" />
          <div>
            <h2 className="text-sm font-bold">Form Verval Resmi</h2>
            <p className="mt-1 text-[11px] text-slate-600">
              Lengkapi identitas lapangan (NIK &amp; RT/RW) dan 3 bagian formulir berikut sebelum mengambil foto &amp; GPS.
            </p>
            <p className="mt-1 text-[11px] text-amber-800">{cfg?.indikator_sumber}</p>
          </div>
        </div>
      </Card>

      {/* Bagian I-B: Identitas Lapangan (NIK & RT/RW) */}
      <Card data-testid="verval-identitas-lapangan">
        <h3 className="text-sm font-bold">I-B. Identitas Lapangan (NIK, No. KK &amp; RT/RW)</h3>
        <p className="mt-1 text-[11px] text-slate-500">Isi/perbaiki NIK (16 digit), RW, RT, atau nama &amp; alamat sesuai KTP/KK saat di rumah warga.</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <Field label="NIK Kepala Keluarga (16 digit)">
            <input className={INPUT} inputMode="numeric" maxLength={16} placeholder="7371..."
              value={identitas.nik || ""}
              onChange={(e) => setIdentitas({ ...identitas, nik: e.target.value.replace(/\D/g, "").slice(0, 16) })}
              data-testid="verval-id-nik" />
          </Field>
          <Field label="Nomor KK (16 digit)">
            <input className={INPUT} inputMode="numeric" maxLength={16}
              value={identitas.no_kk || ""}
              onChange={(e) => setIdentitas({ ...identitas, no_kk: e.target.value.replace(/\D/g, "").slice(0, 16) })}
              data-testid="verval-id-nokk" />
          </Field>
          <Field label="Nama Kepala Keluarga">
            <input className={INPUT} value={identitas.kepala_keluarga || ""}
              onChange={(e) => setIdentitas({ ...identitas, kepala_keluarga: e.target.value })}
              data-testid="verval-id-nama" />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="RW">
              <input className={INPUT} inputMode="numeric" value={identitas.rw || ""}
                onChange={(e) => setIdentitas({ ...identitas, rw: e.target.value.replace(/\D/g, "").slice(0, 4) })}
                data-testid="verval-id-rw" />
            </Field>
            <Field label="RT">
              <input className={INPUT} inputMode="numeric" value={identitas.rt || ""}
                onChange={(e) => setIdentitas({ ...identitas, rt: e.target.value.replace(/\D/g, "").slice(0, 4) })}
                data-testid="verval-id-rt" />
            </Field>
          </div>
          <div className="sm:col-span-2">
            <Field label="Alamat Rumah">
              <input className={INPUT} value={identitas.alamat || ""}
                onChange={(e) => setIdentitas({ ...identitas, alamat: e.target.value })}
                data-testid="verval-id-alamat" />
            </Field>
          </div>
          <Field label="Jumlah Anggota Keluarga">
            <input type="number" min={1} max={50} className={INPUT} value={identitas.jumlah_anggota_keluarga || ""}
              onChange={(e) => setIdentitas({ ...identitas, jumlah_anggota_keluarga: e.target.value })}
              data-testid="verval-id-anggota" />
          </Field>
          <Field label="Usulan Desil Ekonomi Riil (1–10, opsional)">
            <input type="number" min={1} max={10} className={INPUT} placeholder="1 = sangat miskin … 10 = mampu"
              value={identitas.desil_usulan || ""}
              onChange={(e) => setIdentitas({ ...identitas, desil_usulan: e.target.value })}
              data-testid="verval-id-desil" />
          </Field>
        </div>
      </Card>

      {/* Bagian II: 11 variabel */}
      <Card>
        <h3 className="text-sm font-bold">II. Data Keluarga &amp; Status Sosial Ekonomi</h3>
        <p className="mt-1 text-[11px] text-slate-500">
          {isWargaBaru ? "Isi kondisi riil lapangan untuk keluarga yang baru didaftarkan." : "Bandingkan data DTSEN pre-printed dengan kondisi riil di lapangan."}
        </p>
        <div className="mt-3 space-y-3">
          {(cfg?.indikator || []).map((i: any) => {
            const v = ind[i.key] || {};
            const perlu = (!isWargaBaru && INDIKATOR_PERLU_CATATAN.has(v.kesesuaian || ""))
              || INDIKATOR_PERLU_CATATAN.has(v.kondisi_riil || "");
            return (
              <fieldset key={i.key} className="rounded-[12px] p-3 ring-1 ring-slate-200" data-testid={`verval-ind-${i.key}`}>
                <legend className="flex items-center gap-2 px-1 text-xs font-bold text-slate-900">
                  {i.label}
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                    Target OPD: {i.opd}
                  </span>
                </legend>
                {!isWargaBaru && <p className="text-[11px] text-slate-600">Data DTSEN: <DtsenNilai vals={d.dtsen?.[i.key]} /></p>}
                <div className={`mt-2 grid gap-3 ${isWargaBaru ? "" : "sm:grid-cols-2"}`}>
                  {!isWargaBaru && (
                    <div>
                      <p className="text-[11px] font-semibold text-slate-700">Kesesuaian (DTSEN)</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {i.kesesuaian.map((opt: string) => (
                          <button key={opt} type="button" aria-pressed={v.kesesuaian === opt}
                            onClick={() => setItem(i.key, { kesesuaian: opt })}
                            data-testid={`verval-ind-${i.key}-kes-${opt}`}
                            className={`min-h-9 rounded-[10px] px-2 text-[11px] font-bold ${FR} ${v.kesesuaian === opt ? "bg-[#232F3E] text-white" : "bg-white text-slate-700 ring-1 ring-slate-200"}`}>
                            {KESESUAIAN_LABEL[opt] || opt}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  <div>
                    <p className="text-[11px] font-semibold text-slate-700">Kondisi Riil Lapangan</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {i.kondisi_riil.map((opt: string) => (
                        <button key={opt} type="button" aria-pressed={v.kondisi_riil === opt}
                          onClick={() => setItem(i.key, { kondisi_riil: opt })}
                          data-testid={`verval-ind-${i.key}-riil-${opt}`}
                          className={`min-h-9 rounded-[10px] px-2 text-[11px] font-bold ${FR} ${v.kondisi_riil === opt ? "bg-[#117A69] text-white" : "bg-white text-slate-700 ring-1 ring-slate-200"}`}>
                          {KONDISI_RIIL_LABEL[opt] || opt}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                {perlu && (
                  <textarea className={`${INPUT} mt-2`} rows={2}
                    placeholder="Catatan verifikator (wajib bila ada perbedaan / kondisi tidak layak)"
                    value={v.catatan || ""} onChange={(e) => setItem(i.key, { catatan: e.target.value })}
                    data-testid={`verval-ind-${i.key}-catatan`} />
                )}
              </fieldset>
            );
          })}
        </div>
      </Card>

      {/* Bagian III: Penapisan individu rentan */}
      <Card>
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold">III. Penapisan Individu Rentan</h3>
            <p className="mt-1 text-[11px] text-slate-500">Tambahkan anggota keluarga yang teridentifikasi rentan (opsional, boleh kosong).</p>
          </div>
          <button type="button" onClick={addAnggota} className={BTN_SM_PRIMARY} data-testid="verval-anggota-tambah">
            <UserPlus className="h-4 w-4" /> Tambah anggota
          </button>
        </div>
        {(anggota || []).length === 0 && (
          <p className="mt-3 rounded-[10px] bg-slate-50 p-3 text-xs text-slate-500">Belum ada entri anggota.</p>
        )}
        <div className="mt-3 space-y-3" data-testid="verval-anggota-list">
          {(anggota || []).map((a: any, idx: number) => {
            const opts = kondisiOptionsFor(a.status_hubungan);
            return (
              <fieldset key={a.id} className="rounded-[12px] p-3 ring-1 ring-slate-200" data-testid={`verval-anggota-${idx}`}>
                <legend className="flex items-center justify-between gap-2 px-1 text-xs font-bold">
                  Anggota #{idx + 1}
                  <button type="button" onClick={() => hapusAnggota(idx)} className="text-rose-700 hover:text-rose-900"
                    data-testid={`verval-anggota-hapus-${idx}`} aria-label="Hapus anggota">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </legend>
                <div className="grid gap-2 sm:grid-cols-2">
                  <Field label="NIK (16 digit)">
                    <input className={INPUT} inputMode="numeric" maxLength={16}
                      value={a.nik || ""} onChange={(e) => updateAnggota(idx, { nik: e.target.value.replace(/[^0-9]/g, "").slice(0, 16) })}
                      data-testid={`verval-anggota-nik-${idx}`} />
                  </Field>
                  <Field label="Nama lengkap">
                    <input className={INPUT} value={a.nama || ""} onChange={(e) => updateAnggota(idx, { nama: e.target.value })}
                      data-testid={`verval-anggota-nama-${idx}`} />
                  </Field>
                  <Field label="Status hubungan">
                    <select className={INPUT} value={a.status_hubungan || ""}
                      onChange={(e) => updateAnggota(idx, { status_hubungan: e.target.value })}
                      data-testid={`verval-anggota-hub-${idx}`}>
                      <option value="">Pilih…</option>
                      {(cfg?.status_hubungan || []).map((h: any) => <option key={h.key} value={h.key}>{h.label}</option>)}
                    </select>
                  </Field>
                  <Field label="Rekomendasi program OPD">
                    <input className={INPUT} value={a.rekomendasi_opd || ""}
                      onChange={(e) => updateAnggota(idx, { rekomendasi_opd: e.target.value })}
                      placeholder="Isi otomatis dari kondisi rentan"
                      data-testid={`verval-anggota-opd-${idx}`} />
                  </Field>
                </div>
                {opts.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[11px] font-semibold text-slate-700">Kondisi rentan terdeteksi</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {opts.map((k: any) => (
                        <button key={k.key} type="button" aria-pressed={(a.kondisi_rentan || []).includes(k.key)}
                          onClick={() => toggleKondisi(idx, k.key, k.opd)}
                          data-testid={`verval-anggota-${idx}-kr-${k.key}`}
                          className={`min-h-9 rounded-[10px] px-2 text-[11px] font-bold ${FR} ${(a.kondisi_rentan || []).includes(k.key) ? "bg-rose-600 text-white" : "bg-white text-slate-700 ring-1 ring-slate-200"}`}>
                          {k.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </fieldset>
            );
          })}
        </div>
      </Card>

      {/* Bagian IV: Kesimpulan */}
      <Card>
        <h3 className="text-sm font-bold">IV. Kesimpulan Hasil Verifikasi & Validasi</h3>
        <p className="mt-1 text-[11px] text-slate-500">Pilih salah satu kesimpulan untuk rumah tangga ini.</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Kesimpulan Verval">
          {(cfg?.kesimpulan || []).map((k: any) => {
            const aktif = kesimpulan.pilihan === k.key;
            return (
              <button key={k.key} type="button" role="radio" aria-checked={aktif}
                onClick={() => setKesimpulan({ ...kesimpulan, pilihan: k.key })}
                data-testid={`verval-kesimpulan-${k.key}`}
                className={`min-h-14 rounded-[12px] p-3 text-left text-xs ${FR} ${aktif ? "bg-[#117A69] text-white ring-2 ring-[#117A69]" : "bg-white text-slate-700 ring-1 ring-slate-200"}`}>
                <p className="font-extrabold">{k.label} {k.wajib_catatan && <span className={aktif ? "text-amber-200" : "text-amber-700"}>*</span>}</p>
                <p className={`mt-0.5 text-[10px] ${aktif ? "text-emerald-50" : "text-slate-500"}`}>{k.deskripsi}</p>
              </button>
            );
          })}
        </div>
        {kesimpulan.pilihan && (() => {
          const sel = (cfg?.kesimpulan || []).find((x: any) => x.key === kesimpulan.pilihan);
          return (
            <div className="mt-3">
              <Field label={`Catatan${sel?.wajib_catatan ? " (wajib)" : " (opsional)"}`}>
                <textarea className={INPUT} rows={2} value={kesimpulan.catatan || ""}
                  onChange={(e) => setKesimpulan({ ...kesimpulan, catatan: e.target.value })}
                  data-testid="verval-kesimpulan-catatan" />
              </Field>
            </div>
          );
        })()}
      </Card>

      <Card>
        <Field label="Catatan umum (opsional)">
          <textarea className={INPUT} rows={3} value={catatan} onChange={(e) => setCatatan(e.target.value)}
            data-testid="verval-catatan-umum" />
        </Field>
      </Card>

      {kekurangan?.length > 0 && (
        <Card className="bg-amber-50 ring-amber-200">
          <p className="flex items-center gap-2 text-xs font-bold text-amber-900">
            <TriangleAlert className="h-4 w-4" /> Formulir belum lengkap — Foto/GPS terkunci
          </p>
          <ul className="mt-2 list-disc space-y-0.5 pl-5 text-xs text-amber-900" data-testid="verval-kekurangan-form">
            {kekurangan.map((k: string) => <li key={k}>{k}</li>)}
          </ul>
        </Card>
      )}
    </div>
  );
}

function LangkahTinjau({ rec, isWargaBaru, identitas, ind, anggota, kesimpulan, cfg, err, busy, kirim, kekuranganForm }: any) {
  const kurang: string[] = [...(kekuranganForm || [])];
  if ((rec.foto || []).length < (cfg?.min_foto || 1)) kurang.push("Foto belum diunggah");
  const gpsOk = rec.gps?.status_gps === "memenuhi" || (
    rec.gps?.status_gps === "pin_manual" && rec.gps?.lat != null && (rec.gps?.alasan_manual || "").trim().length >= 5
  );
  if (!gpsOk && !cfg?.izinkan_kirim_tanpa_gps) kurang.push(`Lokasi GPS belum memenuhi akurasi ≤ ${cfg?.gps_max_akurasi_m} m (gunakan pin manual beralasan bila sinyal sulit)`);

  const kesLabel = kesimpulan?.pilihan ? (KESIMPULAN_LABEL[kesimpulan.pilihan] || kesimpulan.pilihan) : "—";
  return (
    <Card data-testid="verval-langkah-tinjau">
      <h2 className="text-sm font-bold">Tinjau sebelum mengirim {isWargaBaru ? "(Warga Baru)" : ""}</h2>
      <ul className="mt-2 space-y-1 text-xs">
        <li>Identitas: <b>{identitas.kepala_keluarga || "-"}</b> · No. KK {identitas.no_kk || "-"} · NIK {identitas.nik || "belum diisi"} · RW {identitas.rw || "-"}/RT {identitas.rt || "-"}</li>
        <li>Foto kamera + watermark: <b>{(rec.foto || []).length}</b> terunggah</li>
        <li>GPS: <b>{GPS_LABEL[rec.gps?.status_gps] || "-"}</b>{rec.gps?.akurasi_m != null ? ` (±${rec.gps.akurasi_m} m)` : ""}{rec.gps?.alasan_manual ? ` · ${rec.gps.alasan_manual}` : ""}</li>
        <li>Kesimpulan: <b>{kesLabel}</b>{kesimpulan?.catatan ? ` · ${kesimpulan.catatan}` : ""}</li>
        <li>Anggota rentan: <b>{(anggota || []).length}</b> entri</li>
      </ul>
      <details className="mt-3 rounded-[10px] bg-slate-50 p-2">
        <summary className="cursor-pointer text-xs font-bold">Ringkasan Variabel (11)</summary>
        <ul className="mt-2 space-y-1 text-[11px]">
          {(cfg?.indikator || []).map((i: any) => {
            const v = ind[i.key] || {};
            return (
              <li key={i.key}>
                <b>{i.label}:</b> {!isWargaBaru && (v.kesesuaian ? `DTSEN=${v.kesesuaian} · ` : "— · ")}{v.kondisi_riil ? `Riil=${v.kondisi_riil}` : "—"}
                {v.catatan ? <span className="block pl-3 text-slate-600">{v.catatan}</span> : null}
              </li>
            );
          })}
        </ul>
      </details>
      {kurang.length > 0 && <ul className="mt-3 list-disc space-y-0.5 rounded bg-amber-50 p-3 pl-6 text-xs text-amber-900" data-testid="verval-kekurangan">{kurang.map((k) => <li key={k}>{k}</li>)}</ul>}
      {err && <p className="mt-3 rounded bg-rose-50 p-2 text-xs text-rose-800" data-testid="verval-kirim-error">{err}</p>}
      <button type="button" className={`${BTN_PRIMARY} mt-4 w-full`} disabled={busy || kurang.length > 0} onClick={kirim} data-testid="verval-kirim">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Kirim ke Kelurahan
      </button>
    </Card>
  );
}

function TandaTerima({ rec }: any) {
  return (
    <Card data-testid="verval-tanda-terima">
      <p className="flex items-center gap-2 text-sm font-bold text-emerald-800"><CheckCircle2 className="h-5 w-5" /> {rec.status === "menunggu_kelurahan" ? "Terkirim — menunggu pemeriksaan Kelurahan" : `Status: ${rec.status.replace(/_/g, " ")}`}</p>
      {rec.tanda_terima && <p className="mt-1 text-xs">Nomor tanda terima: <b data-testid="verval-nomor-tanda-terima">{rec.tanda_terima}</b> · {fmtWaktu(rec.submitted_at)}</p>}
      {rec.kelurahan_catatan && <p className="mt-2 rounded bg-slate-50 p-2 text-xs">Catatan Kelurahan ({rec.kelurahan_reviewed_by}): {rec.kelurahan_catatan}</p>}
      {rec.review_catatan && <p className="mt-2 rounded bg-slate-50 p-2 text-xs">Catatan Kecamatan ({rec.reviewed_by}): {rec.review_catatan}</p>}
      <h3 className="mt-4 text-xs font-bold uppercase text-slate-500">Riwayat</h3>
      <ol className="mt-1 space-y-1 text-xs" data-testid="verval-riwayat">
        {(rec.riwayat || []).map((r: any) => <li key={r.id}>{fmtWaktu(r.waktu)} · <b>{r.aksi}</b> {r.dari_status ? `${r.dari_status} → ` : ""}{r.ke_status} · {r.oleh}{r.catatan ? ` · ${r.catatan}` : ""}</li>)}
      </ol>
    </Card>
  );
}
