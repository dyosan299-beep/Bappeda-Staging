import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Camera, CheckCircle2, ChevronLeft, ClipboardCheck, Crosshair, Loader2, Lock, MapPin, Plus, RefreshCw, Search, Send, Trash2, TriangleAlert, Upload, UserPlus } from "lucide-react";
import { api, clientUuidFor, DASAR_LABEL, errMsg, fmtWaktu, fotoUrl, GPS_LABEL, HUBUNGAN_LABEL, INDIKATOR_PERLU_CATATAN, KESESUAIAN_LABEL, KESIMPULAN_LABEL, KONDISI_RIIL_LABEL, newId } from "@/features/verval/api";
import { Card, DtsenNilai, Field, INPUT, StatusBadge, UjiBadge } from "@/features/verval/ui";
import { umumkanPerubahanPeta } from "@/features/verval/VervalMapLayer";
import { BTN_PRIMARY, BTN_SECONDARY, BTN_SM, BTN_SM_PRIMARY, FR } from "@/features/a11y/ui";

/* =================================================================== Beranda operator */
export function VervalBeranda() {
  const [info, setInfo] = useState<any>(null);
  const [list, setList] = useState<any>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setErr("");
    api.get("/verval/sasaran", { params: { search: q || undefined, status: status || undefined, size: 100 } })
      .then((r) => setList(r.data)).catch((e) => { setErr(errMsg(e)); setList({ items: [] }); });
  }, [q, status]);
  useEffect(() => { api.get("/verval/saya").then((r) => setInfo(r.data)).catch((e) => setErr(errMsg(e))); }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="mx-auto max-w-3xl space-y-4" data-testid="verval-beranda">
      <section className="rounded-[16px] p-4 text-white shadow-sm" style={{ backgroundColor: "#232F3E" }} data-testid="verval-ringkasan">
        <p className="text-[11px] font-bold uppercase tracking-wider text-[#6FE3CF]">GeoTag · Verval DTSEN</p>
        <p className="font-head text-xl font-extrabold">Daftar Sasaran Pemeriksaan</p>
        <p className="mt-1 text-xs text-slate-300">Hanya rumah tangga dalam wilayah (Kelurahan · RW/RT) Anda yang ditampilkan.</p>
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
          <div className="mt-3 grid grid-cols-3 gap-2 text-center sm:grid-cols-5">
            {[["Sasaran", info.jumlah_sasaran], ["Draft", info.per_status?.draft || 0], ["Terkirim", info.per_status?.terkirim || 0],
              ["Perbaikan", info.per_status?.perlu_perbaikan || 0], ["Disetujui", info.per_status?.disetujui || 0]].map(([l, v]) => (
              <div key={l as string} className="rounded-[10px] bg-white/10 p-2"><p className="text-lg font-extrabold">{v as any}</p><p className="text-[10px] text-slate-300">{l}</p></div>
            ))}
          </div>
        )}
      </section>

      <Card>
        <form className="flex flex-wrap gap-2 sm:flex-nowrap" onSubmit={(e) => { e.preventDefault(); load(); }}>
          <input className={`${INPUT} min-w-[160px] flex-1`} placeholder="Cari nama kepala keluarga / alamat" value={q} onChange={(e) => setQ(e.target.value)} data-testid="verval-search" />
          <select className={`${INPUT} w-auto max-w-[170px] flex-1 sm:flex-none`} value={status} onChange={(e) => setStatus(e.target.value)} data-testid="verval-filter-status">
            <option value="">Semua status</option>
            {["belum_diverval", "draft", "terkirim", "perlu_perbaikan", "disetujui", "ditolak"].map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
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
                    <p className="truncate text-sm font-bold text-slate-900">{s.kepala_keluarga || "(tanpa nama)"} <UjiBadge show={s.data_uji} /></p>
                    <p className="truncate text-xs text-slate-600">{s.alamat} · {s.kelurahan} · RW {s.rw || "-"} / RT {s.rt || "-"}</p>
                    <p className="text-[11px] text-slate-500">KK {s.no_kk} · {DASAR_LABEL[s.dasar_akses] || s.dasar_akses}</p>
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
  const [d, setD] = useState<any>(null);
  const [rec, setRec] = useState<any>(null);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ind, setInd] = useState<Record<string, { kesesuaian?: string; kondisi_riil?: string; catatan?: string }>>({});
  const [anggota, setAnggota] = useState<any[]>([]);
  const [kesimpulan, setKesimpulan] = useState<{ pilihan?: string; catatan?: string }>({});
  const [catatan, setCatatan] = useState("");
  const [cfg, setCfg] = useState<any>(null);

  const load = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([api.get(`/verval/sasaran/${ref}`), api.get("/verval/konfigurasi")]);
      setD(s.data); setCfg(c.data);
      if (s.data.record) {
        setRec(s.data.record);
        setInd(s.data.record.indikator || {});
        setAnggota(s.data.record.anggota_rentan || []);
        setKesimpulan(s.data.record.kesimpulan || {});
        setCatatan(s.data.record.catatan_umum || "");
      }
    } catch (e) { setErr(errMsg(e)); }
  }, [ref]);
  useEffect(() => { load(); }, [load]);

  const editable = rec && ["draft", "perlu_perbaikan"].includes(rec.status);

  /** Validasi Form Verval sisi klien (sama dengan backend). */
  const kekuranganForm = useMemo((): string[] => {
    const out: string[] = [];
    (cfg?.indikator || []).forEach((i: any) => {
      const v = ind[i.key] || {};
      if (!v.kesesuaian) out.push(`${i.label} — kolom Kesesuaian belum diisi`);
      if (!v.kondisi_riil) out.push(`${i.label} — kolom Kondisi Riil Lapangan belum diisi`);
      const perlu = INDIKATOR_PERLU_CATATAN.has(v.kesesuaian || "") || INDIKATOR_PERLU_CATATAN.has(v.kondisi_riil || "");
      if (perlu && !(v.catatan || "").trim()) out.push(`${i.label} — catatan verifikator wajib diisi`);
    });
    if (!kesimpulan?.pilihan) out.push("Kesimpulan Verval belum dipilih (Bagian IV)");
    else {
      const sel = (cfg?.kesimpulan || []).find((k: any) => k.key === kesimpulan.pilihan);
      if (sel?.wajib_catatan && !(kesimpulan.catatan || "").trim())
        out.push(`Catatan wajib untuk kesimpulan '${sel.label}'`);
    }
    return out;
  }, [ind, kesimpulan, cfg]);
  const formLengkap = kekuranganForm.length === 0;

  const mulai = async () => {
    setBusy(true);
    try {
      const r = await api.post("/verval/records", { dtsen_ref: ref, client_uuid: clientUuidFor(ref) });
      setRec(r.data); setInd(r.data.indikator || {}); setStep(0); toast.success("Draft Verval dibuat");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  const simpan = async (extra: any = {}, silent = false) => {
    if (!rec || !editable) return rec;
    try {
      const r = await api.put(`/verval/records/${rec.id}`, {
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
      await simpan({}, true);
      const r = await api.post(`/verval/records/${rec.id}/kirim`);
      setRec(r.data); localStorage.removeItem(`verval_cu_${ref}`);
      toast.success("Hasil Verval terkirim");
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
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#117A69]">Sasaran DTSEN <UjiBadge show={s.data_uji} /></p>
            <p className="font-head text-lg font-extrabold text-slate-900" data-testid="verval-sasaran-nama">{s.kepala_keluarga}</p>
            <p className="text-xs text-slate-600">{s.alamat} · {s.kelurahan}, Kec. {s.kecamatan} · RW {s.rw || "-"} / RT {s.rt || "-"}</p>
            <p className="text-[11px] text-slate-500">No. KK {s.no_kk} (tersamar) · {s.jumlah_anggota_keluarga ?? "-"} anggota · {DASAR_LABEL[s.dasar_akses]}</p>
          </div>
          {rec && <StatusBadge status={rec.status} testid="verval-status" />}
        </div>
      </Card>

      {!rec ? (
        <Card>
          <h2 className="text-sm font-bold">Sebelum memulai</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-700">
            <li>Datangi rumah sasaran dan perkenalkan diri sesuai prosedur Verval.</li>
            <li>Foto & GPS adalah <b>bukti pendukung</b>; tidak otomatis membuktikan data DTSEN benar.</li>
            <li>Hasil Anda tidak mengubah data DTSEN; diperiksa oleh Verifikator / Admin Bappeda.</li>
          </ul>
          <button type="button" className={`${BTN_PRIMARY} mt-4 w-full`} onClick={mulai} disabled={busy} data-testid="verval-mulai">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4" />} Mulai Verval
          </button>
        </Card>
      ) : (
        <>
          {rec.status === "perlu_perbaikan" && rec.review_catatan && (
            <p className="rounded-[12px] bg-orange-50 p-3 text-xs text-orange-900 ring-1 ring-orange-200" data-testid="verval-catatan-perbaikan"><b>Perlu perbaikan:</b> {rec.review_catatan}</p>
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
              {step === 1 && <LangkahFormulir d={d} cfg={cfg} ind={ind} setInd={setInd}
                                              anggota={anggota} setAnggota={setAnggota}
                                              kesimpulan={kesimpulan} setKesimpulan={setKesimpulan}
                                              catatan={catatan} setCatatan={setCatatan}
                                              kekurangan={kekuranganForm} />}
              {step === 2 && <LangkahFoto rec={rec} setRec={setRec} cfg={cfg} />}
              {step === 3 && <LangkahGps rec={rec} cfg={cfg} simpan={simpan} />}
              {step === 4 && <LangkahTinjau rec={rec} ind={ind} anggota={anggota} kesimpulan={kesimpulan} cfg={cfg} err={err} busy={busy} kirim={kirim} kekuranganForm={kekuranganForm} />}
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
  const inputRef = useRef<HTMLInputElement | null>(null);
  const pos = useRef<any>(null);
  const [posLive, setPosLive] = useState<any>(null);
  const [posGalat, setPosGalat] = useState("");
  useEffect(() => {
    if (!navigator.geolocation) { setPosGalat("Perangkat tidak mendukung GPS; koordinat akan dibaca dari metadata foto bila ada."); return; }
    const id = navigator.geolocation.watchPosition(
      (p) => { pos.current = p.coords; setPosLive({ lat: p.coords.latitude, lng: p.coords.longitude, akurasi_m: Math.round(p.coords.accuracy * 10) / 10 }); setPosGalat(""); },
      (e) => setPosGalat(e.code === 1 ? "Izin lokasi ditolak — koordinat foto akan dibaca dari metadata foto (EXIF) bila ada." : "Sinyal GPS belum tersedia."),
      { enableHighAccuracy: true, maximumAge: 5000 });
    return () => navigator.geolocation.clearWatch(id);
  }, []);

  const unggah = async (item: any) => {
    setAntrean((a) => a.map((x) => (x.cid === item.cid ? { ...x, status: "mengunggah", galat: "" } : x)));
    const fd = new FormData();
    fd.append("file", item.file);
    fd.append("client_foto_id", item.cid);
    fd.append("jenis", item.jenis);
    fd.append("diambil_at", item.diambil_at);
    if (item.coords) { fd.append("lat", String(item.coords.latitude)); fd.append("lng", String(item.coords.longitude)); fd.append("akurasi_m", String(item.coords.accuracy)); }
    try {
      const r = await api.post(`/verval/records/${rec.id}/foto`, fd);
      const upd: any = { ...rec, foto: r.data.foto, foto_count: r.data.foto.length };
      if (r.data.gps_record) upd.gps = r.data.gps_record; // koordinat record otomatis dari foto -> sinkron ke peta
      setRec(upd);
      umumkanPerubahanPeta();
      setAntrean((a) => a.filter((x) => x.cid !== item.cid));
      const terakhir = (r.data.foto || []).slice(-1)[0];
      const g = terakhir?.gps_saat_foto;
      toast[r.data.duplikat ? "info" : "success"](r.data.duplikat ? "Foto sudah tersimpan sebelumnya (tidak digandakan)"
        : g ? `Foto terunggah · koordinat ${Number(g.lat).toFixed(5)}, ${Number(g.lng).toFixed(5)} tersimpan & disinkronkan ke peta` : "Foto terunggah (tanpa koordinat)");
    } catch (e) {
      setAntrean((a) => a.map((x) => (x.cid === item.cid ? { ...x, status: "gagal", galat: errMsg(e) } : x)));
    }
  };

  const pilih = (files: FileList | null) => {
    Array.from(files || []).forEach((file) => {
      if (file.size > (cfg?.max_foto_mb || 8) * 1048576) { toast.error(`Ukuran foto melebihi ${cfg?.max_foto_mb || 8} MB`); return; }
      const item = { cid: newId(), file, jenis, diambil_at: new Date().toISOString(), coords: pos.current, status: "antre", preview: URL.createObjectURL(file) };
      setAntrean((a) => [...a, item]);
      unggah(item);
    });
    if (inputRef.current) inputRef.current.value = "";
  };

  const hapus = async (fid: string) => {
    try { const r = await api.delete(`/verval/records/${rec.id}/foto/${fid}`); setRec({ ...rec, foto: r.data.foto, foto_count: r.data.foto.length }); }
    catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <Card data-testid="verval-langkah-foto">
      <h2 className="text-sm font-bold">Foto rumah / objek</h2>
      <p className="mt-1 text-xs text-slate-600">Minimal {cfg?.min_foto || 1} foto, maksimal {cfg?.max_foto_per_verval || 6}. Koordinat saat foto diambil ikut tersimpan dan otomatis tampil di seluruh peta sistem. Foto diproses ulang di server (metadata dibuang) dan hanya dapat dibuka oleh pihak berwenang.</p>
      <p className={`mt-2 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${posLive ? "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200" : "bg-amber-50 text-amber-900 ring-1 ring-amber-200"}`} data-testid="verval-foto-posisi">
        <MapPin className="h-3 w-3" />
        {posLive ? `Posisi saat ini: ${posLive.lat.toFixed(6)}, ${posLive.lng.toFixed(6)} (±${posLive.akurasi_m} m)` : posGalat || "Mencari posisi GPS…"}
      </p>
      <div className="mt-3 flex flex-wrap gap-2 sm:flex-nowrap">
        <select className={`${INPUT} w-full sm:max-w-[180px]`} value={jenis} onChange={(e) => setJenis(e.target.value)} data-testid="verval-jenis-foto">
          {(cfg?.jenis_foto || []).map((j: string) => <option key={j} value={j}>{j.replace(/_/g, " ")}</option>)}
        </select>
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden" onChange={(e) => pilih(e.target.files)} data-testid="verval-foto-input" />
        <button type="button" className={`${BTN_SM_PRIMARY} w-full flex-1 sm:w-auto`} onClick={() => inputRef.current?.click()} data-testid="verval-ambil-foto"><Camera className="h-4 w-4" /> Ambil / pilih foto</button>
      </div>
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

function LangkahGps({ rec, cfg, simpan }: any) {
  const [live, setLive] = useState<any>(null);
  const [state, setState] = useState<string>("idle");
  const [galat, setGalat] = useState("");
  const watch = useRef<number | null>(null);
  const batas = cfg?.gps_max_akurasi_m ?? 5;

  const stop = () => { if (watch.current !== null) navigator.geolocation.clearWatch(watch.current); watch.current = null; };
  useEffect(() => stop, []);

  const mulai = () => {
    setGalat("");
    if (!window.isSecureContext) { setState("error"); setGalat("Akses lokasi memerlukan HTTPS."); return; }
    if (!navigator.geolocation) { setState("error"); setGalat("Perangkat/peramban tidak mendukung GPS."); simpan({ gps: { izin: "tidak_diketahui", galat: "tidak_didukung" } }, true); return; }
    setState("mencari");
    watch.current = navigator.geolocation.watchPosition(
      (p) => setLive({ lat: p.coords.latitude, lng: p.coords.longitude, akurasi_m: Math.round(p.coords.accuracy * 10) / 10, waktu: new Date(p.timestamp).toISOString() }),
      async (e) => {
        stop(); setState("error");
        const denied = e.code === 1;
        setGalat(denied ? "Izin lokasi ditolak. Aktifkan izin lokasi untuk situs ini di pengaturan peramban." : e.code === 3 ? "Waktu pencarian GPS habis. Coba di area terbuka." : "Sinyal GPS tidak tersedia.");
        await simpan({ gps: { izin: denied ? "denied" : "granted", galat: e.message?.slice(0, 180) || String(e.code) } }, true);
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 60000 },
    );
  };

  const gunakan = async () => {
    if (!live) return;
    const r = await simpan({ gps: { lat: live.lat, lng: live.lng, akurasi_m: live.akurasi_m, diambil_at: live.waktu, izin: "granted" } }, true);
    if (r) { stop(); setState("idle"); toast[r.gps.status_gps === "memenuhi" ? "success" : "warning"](GPS_LABEL[r.gps.status_gps]); }
  };

  const g = rec.gps || {};
  const ok = live && live.akurasi_m <= batas;
  return (
    <Card data-testid="verval-langkah-gps">
      <h2 className="text-sm font-bold">Rekam lokasi GPS</h2>
      <p className="mt-1 text-xs text-slate-600">Target akurasi ≤ <b>{batas} m</b>. Koordinat adalah posisi perangkat saat pemeriksaan dan <b>tidak</b> otomatis menandai lokasi rumah sebagai terverifikasi.</p>
      <div className={`mt-3 rounded-[12px] p-3 text-xs ring-1 ${g.status_gps === "memenuhi" ? "bg-emerald-50 ring-emerald-200" : "bg-slate-50 ring-slate-200"}`} data-testid="verval-gps-tersimpan">
        <p className="font-bold">Tersimpan: {GPS_LABEL[g.status_gps] || "-"}</p>
        {g.lat != null && <p>{g.lat.toFixed(6)}, {g.lng.toFixed(6)} · ±{g.akurasi_m} m · {fmtWaktu(g.diambil_at)}</p>}
        {g.galat && <p className="text-rose-700">{g.galat}</p>}
      </div>
      {state === "mencari" && (
        <div className={`mt-3 rounded-[12px] p-3 text-sm ring-1 ${ok ? "bg-emerald-50 ring-emerald-300" : "bg-amber-50 ring-amber-300"}`} data-testid="verval-gps-live" aria-live="polite">
          {live ? <>
            <p className="font-extrabold">Akurasi saat ini: ±{live.akurasi_m} m {ok ? "· memenuhi" : `· menunggu ≤ ${batas} m`}</p>
            <p className="text-xs">{live.lat.toFixed(6)}, {live.lng.toFixed(6)}</p>
            {!ok && <p className="mt-1 text-xs">Tips: berdiri di area terbuka, aktifkan mode lokasi akurasi tinggi, tunggu beberapa detik.</p>}
          </> : <p><Loader2 className="mr-1 inline h-4 w-4 animate-spin" />Mencari sinyal GPS…</p>}
        </div>
      )}
      {galat && <p className="mt-3 flex gap-2 rounded bg-rose-50 p-2 text-xs text-rose-800" data-testid="verval-gps-error"><TriangleAlert className="h-4 w-4 shrink-0" />{galat}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {state !== "mencari"
          ? <button type="button" className={BTN_SM_PRIMARY} onClick={mulai} data-testid="verval-gps-mulai"><Crosshair className="h-4 w-4" /> Mulai rekam GPS</button>
          : <>
            <button type="button" className={BTN_SM_PRIMARY} onClick={gunakan} disabled={!live} data-testid="verval-gps-gunakan"><MapPin className="h-4 w-4" /> Simpan lokasi ini{live && !ok ? " (belum memenuhi)" : ""}</button>
            <button type="button" className={BTN_SM} onClick={() => { stop(); setState("idle"); }} data-testid="verval-gps-batal">Berhenti</button>
          </>}
      </div>
      {!cfg?.izinkan_kirim_tanpa_gps && <p className="mt-2 text-[11px] text-slate-500">Kebijakan saat ini: hasil tidak dapat dikirim sebelum lokasi memenuhi target akurasi. Draft tetap tersimpan dan dapat dilanjutkan.</p>}
    </Card>
  );
}

function LangkahFormulir({ d, cfg, ind, setInd, anggota, setAnggota, kesimpulan, setKesimpulan, catatan, setCatatan, kekurangan }: any) {
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
            <h2 className="text-sm font-bold">Form Verval Resmi (3 bagian)</h2>
            <p className="mt-1 text-[11px] text-slate-600">
              Isi form berikut sebelum mengambil foto & GPS. Foto/GPS akan terkunci sampai form dinyatakan lengkap.
            </p>
            <p className="mt-1 text-[11px] text-amber-800">{cfg?.indikator_sumber}</p>
          </div>
        </div>
      </Card>

      {/* Bagian II: 11 variabel */}
      <Card>
        <h3 className="text-sm font-bold">II. Data Keluarga & Status Sosial Ekonomi</h3>
        <p className="mt-1 text-[11px] text-slate-500">Bandingkan data DTSEN pre-printed dengan kondisi riil di lapangan.</p>
        <div className="mt-3 space-y-3">
          {(cfg?.indikator || []).map((i: any) => {
            const v = ind[i.key] || {};
            const perlu = INDIKATOR_PERLU_CATATAN.has(v.kesesuaian || "") || INDIKATOR_PERLU_CATATAN.has(v.kondisi_riil || "");
            return (
              <fieldset key={i.key} className="rounded-[12px] p-3 ring-1 ring-slate-200" data-testid={`verval-ind-${i.key}`}>
                <legend className="flex items-center gap-2 px-1 text-xs font-bold text-slate-900">
                  {i.label}
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                    Target OPD: {i.opd}
                  </span>
                </legend>
                <p className="text-[11px] text-slate-600">Data DTSEN: <DtsenNilai vals={d.dtsen?.[i.key]} /></p>
                <div className="mt-2 grid gap-3 sm:grid-cols-2">
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

function LangkahTinjau({ rec, ind, anggota, kesimpulan, cfg, err, busy, kirim, kekuranganForm }: any) {
  const kurang: string[] = [...(kekuranganForm || [])];
  if ((rec.foto || []).length < (cfg?.min_foto || 1)) kurang.push("Foto belum diunggah");
  if (rec.gps?.status_gps !== "memenuhi" && !cfg?.izinkan_kirim_tanpa_gps) kurang.push(`Lokasi GPS belum memenuhi akurasi ≤ ${cfg?.gps_max_akurasi_m} m`);

  const kesLabel = kesimpulan?.pilihan ? (KESIMPULAN_LABEL[kesimpulan.pilihan] || kesimpulan.pilihan) : "—";
  return (
    <Card data-testid="verval-langkah-tinjau">
      <h2 className="text-sm font-bold">Tinjau sebelum mengirim</h2>
      <ul className="mt-2 space-y-1 text-xs">
        <li>Foto: <b>{(rec.foto || []).length}</b> terunggah</li>
        <li>GPS: <b>{GPS_LABEL[rec.gps?.status_gps] || "-"}</b>{rec.gps?.akurasi_m != null ? ` (±${rec.gps.akurasi_m} m)` : ""}</li>
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
                <b>{i.label}:</b> {v.kesesuaian ? `DTSEN=${v.kesesuaian}` : "—"} · {v.kondisi_riil ? `Riil=${v.kondisi_riil}` : "—"}
                {v.catatan ? <span className="block pl-3 text-slate-600">{v.catatan}</span> : null}
              </li>
            );
          })}
        </ul>
      </details>
      {kurang.length > 0 && <ul className="mt-3 list-disc space-y-0.5 rounded bg-amber-50 p-3 pl-6 text-xs text-amber-900" data-testid="verval-kekurangan">{kurang.map((k) => <li key={k}>{k}</li>)}</ul>}
      {err && <p className="mt-3 rounded bg-rose-50 p-2 text-xs text-rose-800" data-testid="verval-kirim-error">{err}</p>}
      <button type="button" className={`${BTN_PRIMARY} mt-4 w-full`} disabled={busy || kurang.length > 0} onClick={kirim} data-testid="verval-kirim">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Kirim hasil Verval
      </button>
    </Card>
  );
}

function TandaTerima({ rec }: any) {
  return (
    <Card data-testid="verval-tanda-terima">
      <p className="flex items-center gap-2 text-sm font-bold text-emerald-800"><CheckCircle2 className="h-5 w-5" /> {rec.status === "terkirim" ? "Hasil Verval terkirim" : `Status: ${rec.status.replace(/_/g, " ")}`}</p>
      {rec.tanda_terima && <p className="mt-1 text-xs">Nomor tanda terima: <b data-testid="verval-nomor-tanda-terima">{rec.tanda_terima}</b> · {fmtWaktu(rec.submitted_at)}</p>}
      {rec.review_catatan && <p className="mt-2 rounded bg-slate-50 p-2 text-xs">Catatan pemeriksa: {rec.review_catatan}</p>}
      <h3 className="mt-4 text-xs font-bold uppercase text-slate-500">Riwayat</h3>
      <ol className="mt-1 space-y-1 text-xs" data-testid="verval-riwayat">
        {(rec.riwayat || []).map((r: any) => <li key={r.id}>{fmtWaktu(r.waktu)} · <b>{r.aksi}</b> {r.dari_status ? `${r.dari_status} → ` : ""}{r.ke_status} · {r.oleh}{r.catatan ? ` · ${r.catatan}` : ""}</li>)}
      </ol>
    </Card>
  );
}
