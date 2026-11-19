"""Modul GeoTag - Verifikasi & Validasi (Verval) DTSEN.

Aturan utama: aksi operasional GeoTag (ambil foto, rekam GPS, kirim Verval) HANYA untuk
peran `operator_rt_rw` yang memiliki penugasan aktif, dan hanya atas sasaran DTSEN di
wilayah penugasannya (atau KK sasaran yang ditetapkan admin, tercatat & teraudit).

Relasi permanen memakai `dtsen_ref` (lihat dtsen_ref.py), bukan UUID households.
Hasil Verval TIDAK pernah mengubah data sumber DTSEN (households).
Seluruh endpoint di-mount pada prefix /api oleh server.py.
"""
from __future__ import annotations

import math
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

import dtsen_ref as dref
import verval_config as cfg
import verval_storage as storage
import scope as scope_mod
from inklusi import audit

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731
SENSITIVE_ROLES = ("superadmin", "admin", "admin_bappeda", "verifikator")


def _clean(d: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {k: v for k, v in (d or {}).items() if k != "_id"}


def _mask_kk(kk: Any) -> str:
    s = dref.kk_digits(kk)
    return (s[:4] + "*" * max(len(s) - 8, 0) + s[-4:]) if len(s) >= 8 else "****"


def _today() -> str:
    return date.today().isoformat()


def _bersih(v: Any, n: int = 1000) -> str:
    s = re.sub(r"<[^>]*>", "", str(v or "")).strip()
    return s[:n]


# ============================================================ cakupan wilayah operator
def penugasan_profil(user: dict) -> Optional[dict]:
    """Penugasan yang melekat pada profil PETUGAS (kecamatan + kelurahan + RW + RT) — dibuat
    oleh operator kecamatan saat akun dibuat. Tidak perlu penugasan terpisah."""
    if user.get("role") != "petugas":
        return None
    rw = dref.norm_rt_rw(user.get("rw"))
    kel = (user.get("kelurahan") or "").strip()
    if not rw or not kel:
        return None
    return {"id": f"profil:{user.get('id')}", "user_id": str(user.get("id")), "status": "aktif",
            "kecamatan": user.get("wilayah") or "", "kelurahan": kel,
            "kode_kelurahan": str(user.get("kode_kelurahan") or ""), "kelurahan_norm": scope_mod.norm(kel),
            "kecamatan_norm": scope_mod.norm(user.get("wilayah")),
            "rw": rw, "rt": [dref.norm_rt_rw(r) for r in (user.get("rt") or []) if dref.norm_rt_rw(r)],
            "lintas_wilayah": False, "dasar_penugasan": "Profil petugas RT/RW (ditetapkan operator kecamatan)",
            "berlaku_mulai": None, "berlaku_sampai": None, "sumber": "profil"}


def _kel_cocok(hh: dict, p: dict) -> bool:
    """Rumah tangga berada di kelurahan penugasan (cocok kode, atau nama bila kode tak tersedia)."""
    kode_p = str(p.get("kode_kelurahan") or "")
    kode_h = str(hh.get("kode_kelurahan") or "")
    if kode_p and kode_h:
        return kode_p == kode_h
    if p.get("kelurahan_norm"):
        if scope_mod.norm(hh.get("kelurahan")) != p["kelurahan_norm"]:
            return False
        return not p.get("kecamatan_norm") or scope_mod.norm(hh.get("kecamatan")) == p["kecamatan_norm"]
    return False


async def operator_scope(db, user: dict) -> Tuple[List[dict], Dict[str, dict]]:
    """Penugasan aktif & berlaku + KK sasaran aktif milik operator/petugas."""
    uid = str(user.get("id"))
    today = _today()
    pens = []
    prof = penugasan_profil(user)
    if prof:
        pens.append(prof)
    for p in await db.verval_penugasan.find({"user_id": uid, "status": "aktif"}).to_list(500):
        if p.get("berlaku_mulai") and p["berlaku_mulai"] > today:
            continue
        if p.get("berlaku_sampai") and p["berlaku_sampai"] < today:
            continue
        pens.append(p)
    sas = {}
    for s in await db.verval_sasaran.find({"user_id": uid, "status": "aktif"}).to_list(5000):
        if s.get("berlaku_sampai") and s["berlaku_sampai"] < today:
            continue
        sas[s.get("dtsen_ref")] = s
    return pens, sas


def dasar_akses(hh: dict, pens: List[dict], sas: Dict[str, dict]) -> Optional[dict]:
    """Return keterangan dasar akses bila rumah tangga berada dalam kewenangan operator."""
    ref = hh.get("dtsen_ref")
    if ref and ref in sas:
        s = sas[ref]
        return {"jenis": "lintas_wilayah" if s.get("lintas_wilayah") else "sasaran_admin",
                "id": s.get("id")}
    rw = dref.norm_rt_rw(hh.get("rw"))
    rt = dref.norm_rt_rw(hh.get("rt"))
    if not rw:  # tanpa RW eksplisit hanya dapat diakses lewat penetapan KK sasaran
        return None
    for p in pens:
        if not _kel_cocok(hh, p):
            continue
        if rw != p.get("rw"):
            continue
        rts = p.get("rt") or []
        if rts and rt not in rts:
            continue
        jenis = "wilayah_petugas" if p.get("sumber") == "profil" else (
            "lintas_wilayah" if p.get("lintas_wilayah") else "penugasan_rt_rw")
        return {"jenis": jenis, "id": p.get("id")}
    return None


async def operator_households(db, user: dict) -> List[Tuple[dict, dict]]:
    pens, sas = await operator_scope(db, user)
    out: Dict[str, Tuple[dict, dict]] = {}
    seen_q = set()
    for p in pens:
        if p.get("kode_kelurahan"):
            q = {"kode_kelurahan": str(p["kode_kelurahan"])}
        elif p.get("kelurahan"):
            q = {"kelurahan": {"$regex": f"^\\s*{re.escape(str(p['kelurahan']).strip())}\\s*$", "$options": "i"}}
        else:
            continue
        key = repr(sorted(q.items(), key=lambda kv: kv[0]))
        if key in seen_q:
            continue
        seen_q.add(key)
        for hh in await db.households.find(q).to_list(20000):
            da = dasar_akses(hh, pens, sas)
            if da and hh.get("dtsen_ref"):
                out[hh["dtsen_ref"]] = (hh, da)
    refs = [r for r in sas if r and r not in out]
    if refs:
        for hh in await db.households.find({"dtsen_ref": {"$in": refs}}).to_list(len(refs) + 10):
            da = dasar_akses(hh, pens, sas)
            if da:
                out[hh["dtsen_ref"]] = (hh, da)
    return list(out.values())


async def household_by_ref(db, ref: str) -> dict:
    docs = await db.households.find({"dtsen_ref": ref}).to_list(3)
    if not docs:
        raise HTTPException(status_code=404, detail="Data DTSEN tidak ditemukan atau di luar kewenangan")
    if len(docs) > 1:
        raise HTTPException(status_code=409, detail="Referensi DTSEN ganda (No. KK + kelurahan sama). "
                                                    "Laporkan ke admin untuk penelusuran data.")
    return docs[0]


# ============================================================ model input
class PenugasanIn(BaseModel):
    user_id: str
    kode_kelurahan: str = Field(..., min_length=1, max_length=20)
    rw: str = Field(..., min_length=1, max_length=5)
    rt: List[str] = []
    lintas_wilayah: bool = False
    dasar_penugasan: str = Field("", max_length=300)
    berlaku_mulai: Optional[str] = None
    berlaku_sampai: Optional[str] = None
    catatan: str = Field("", max_length=500)


class SasaranIn(BaseModel):
    user_id: str
    household_id: Optional[str] = None
    dtsen_ref: Optional[str] = None
    dasar_penugasan: str = Field("", max_length=300)
    berlaku_sampai: Optional[str] = None
    catatan: str = Field("", max_length=500)


class CabutIn(BaseModel):
    alasan: str = Field(..., min_length=3, max_length=500)


class RecordCreate(BaseModel):
    dtsen_ref: str
    client_uuid: str = Field(..., min_length=8, max_length=64)


class GpsIn(BaseModel):
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    akurasi_m: Optional[float] = Field(None, ge=0, le=100000)
    diambil_at: Optional[str] = None
    izin: str = Field("tidak_diketahui", max_length=30)  # granted|denied|prompt|tidak_diketahui
    galat: str = Field("", max_length=200)


class RecordUpdate(BaseModel):
    indikator: Optional[Dict[str, Dict[str, Any]]] = None
    anggota_rentan: Optional[List[Dict[str, Any]]] = None
    kesimpulan: Optional[Dict[str, Any]] = None
    catatan_umum: Optional[str] = Field(None, max_length=2000)
    gps: Optional[GpsIn] = None
    alasan_tanpa_gps: Optional[str] = Field(None, max_length=500)
    versi: Optional[int] = None

    @field_validator("indikator")
    @classmethod
    def _cek_ind(cls, v):
        if v is None:
            return v
        allowed = {i["key"]: i for i in cfg.INDIKATOR}
        out: Dict[str, Dict[str, Any]] = {}
        for k, item in v.items():
            if k not in allowed:
                raise ValueError(f"Variabel tidak dikenal: {k}")
            spec = allowed[k]
            kes = ((item or {}).get("kesesuaian") or "").strip() or None
            riil = ((item or {}).get("kondisi_riil") or "").strip() or None
            if kes is not None and kes not in spec["kesesuaian"]:
                raise ValueError(f"Nilai kesesuaian '{kes}' tidak valid untuk {k}")
            if riil is not None and riil not in spec["kondisi_riil"]:
                raise ValueError(f"Nilai kondisi riil '{riil}' tidak valid untuk {k}")
            out[k] = {
                "kesesuaian": kes,
                "kondisi_riil": riil,
                "catatan": _bersih((item or {}).get("catatan"), 500),
            }
        return out

    @field_validator("anggota_rentan")
    @classmethod
    def _cek_ang(cls, v):
        if v is None:
            return v
        if len(v) > 50:
            raise ValueError("Jumlah anggota keluarga melebihi batas (50)")
        allowed_hub = {h["key"] for h in cfg.STATUS_HUBUNGAN}
        out: List[Dict[str, Any]] = []
        seen_ids = set()
        for raw in v:
            if not isinstance(raw, dict):
                raise ValueError("Entri anggota harus berupa objek")
            hub = (raw.get("status_hubungan") or "").strip()
            if hub and hub not in allowed_hub:
                raise ValueError(f"Status hubungan tidak dikenal: {hub}")
            kr = raw.get("kondisi_rentan") or []
            if not isinstance(kr, list):
                raise ValueError("kondisi_rentan harus list")
            kr_valid = {k["key"] for k in cfg.KONDISI_RENTAN.get(hub, [])}
            kr_clean = [str(x) for x in kr if str(x) in kr_valid]
            nik = re.sub(r"[^0-9]", "", str(raw.get("nik") or ""))[:16]
            aid = (raw.get("id") or "").strip() or str(uuid.uuid4())
            if aid in seen_ids:
                raise ValueError("ID anggota ganda dalam satu entri")
            seen_ids.add(aid)
            out.append({
                "id": aid[:40],
                "nik": nik,
                "nama": _bersih(raw.get("nama"), 150),
                "status_hubungan": hub or None,
                "kondisi_rentan": kr_clean,
                "rekomendasi_opd": _bersih(raw.get("rekomendasi_opd"), 200),
                "catatan": _bersih(raw.get("catatan"), 500),
            })
        return out

    @field_validator("kesimpulan")
    @classmethod
    def _cek_kes(cls, v):
        if v is None:
            return v
        allowed = {k["key"] for k in cfg.KESIMPULAN}
        pil = (v.get("pilihan") or "").strip() or None
        if pil is not None and pil not in allowed:
            raise ValueError(f"Pilihan kesimpulan tidak dikenal: {pil}")
        return {
            "pilihan": pil,
            "catatan": _bersih(v.get("catatan"), 1000),
        }



class ReviewIn(BaseModel):
    keputusan: str
    catatan: str = Field("", max_length=2000)


# ============================================================ router
def build_router(db, current_user_dep) -> APIRouter:
    router = APIRouter(prefix="/verval", tags=["verval"])

    def need_ref_secret():
        if not dref.ref_secret():
            raise HTTPException(status_code=503, detail="Modul Verval belum dikonfigurasi (VERVAL_REF_SECRET)")

    async def operator_dep(request: Request) -> dict:
        user = await current_user_dep(request)
        if user.get("role") not in cfg.OPERATOR_ROLES:
            await audit(db, user, "verval_akses_ditolak", "verval", request.url.path,
                        "peran bukan petugas/operator_rt_rw", request, status="ditolak")
            raise HTTPException(status_code=403, detail="Fitur GeoTag hanya untuk Petugas / Operator RT/RW yang berwenang")
        if user.get("role") == "petugas" and not penugasan_profil(user):
            raise HTTPException(status_code=403, detail="Akun petugas belum memiliki Kelurahan & RW. Hubungi operator kecamatan.")
        need_ref_secret()
        return user

    async def reviewer_dep(request: Request) -> dict:
        user = await current_user_dep(request)
        if user.get("role") not in cfg.REVIEWER_ROLES:
            raise HTTPException(status_code=403, detail="Pemeriksaan Verval khusus Verifikator / Admin Bappeda / Superadmin")
        return user

    def in_scope(rec: dict, user: dict) -> bool:
        """Verifikator kecamatan hanya melihat hasil Verval di kecamatannya."""
        return scope_mod.same_kecamatan(scope_mod.kecamatan_scope(user), rec.get("kecamatan"))

    def scope_query(user: dict, q: Dict[str, Any]) -> Dict[str, Any]:
        sc = scope_mod.kecamatan_scope(user)
        if sc:
            q["kecamatan"] = {"$regex": f"^\\s*{re.escape(sc)}\\s*$", "$options": "i"}
        return q

    async def penugasan_admin_dep(request: Request) -> dict:
        user = await current_user_dep(request)
        if user.get("role") not in cfg.PENUGASAN_ADMIN_ROLES:
            raise HTTPException(status_code=403, detail="Pengelolaan penugasan khusus Super Admin / Admin Bappeda")
        need_ref_secret()
        return user

    async def kode_labels() -> Dict[str, str]:
        fields = [f for i in cfg.INDIKATOR for f in i["dtsen_fields"]]
        docs = await db.kode_referensi.find({"field": {"$in": fields}}).to_list(5000)
        return {d["id"]: d.get("label") or "" for d in docs if d.get("id")}

    def dtsen_values(hh: dict, labels: Dict[str, str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for ind in cfg.INDIKATOR:
            vals = []
            for f in ind["dtsen_fields"]:
                v = hh.get(f)
                if v is None or v == "":
                    continue
                lab = labels.get(f"{f}::{v}")
                vals.append({"field": f, "nilai": v, "label": lab or ""})
            out[ind["key"]] = vals
        return out

    def hh_view(hh: dict, full: bool) -> Dict[str, Any]:
        d = {
            "dtsen_ref": hh.get("dtsen_ref"), "household_id": hh.get("id"),
            "kecamatan": hh.get("kecamatan"), "kode_kecamatan": hh.get("kode_kecamatan"),
            "kelurahan": hh.get("kelurahan"), "kode_kelurahan": hh.get("kode_kelurahan"),
            "rt": hh.get("rt") or "", "rw": hh.get("rw") or "",
            "alamat": hh.get("alamat") or "", "kepala_keluarga": hh.get("kepala_keluarga") or "",
            "jumlah_anggota_keluarga": hh.get("jumlah_anggota_keluarga"),
            "no_kk": hh.get("no_kk") if full else _mask_kk(hh.get("no_kk")),
            "no_kk_tersamar": not full, "data_uji": bool(hh.get("data_uji")),
        }
        return d

    async def riwayat(record_id: str, user: dict, aksi: str, dari: Optional[str], ke: Optional[str],
                      catatan: str = ""):
        await db.verval_riwayat.insert_one({
            "id": str(uuid.uuid4()), "record_id": record_id, "aksi": aksi, "dari_status": dari,
            "ke_status": ke, "oleh": user.get("email"), "role": user.get("role"),
            "catatan": _bersih(catatan, 1000), "waktu": now_iso()})

    def can_view_record(rec: dict, user: dict) -> bool:
        if user.get("role") in cfg.HASIL_ROLES:
            if not in_scope(rec, user):
                return False
            return rec.get("status") != "draft" or rec.get("operator_id") == str(user.get("id"))
        return user.get("role") in cfg.OPERATOR_ROLES and rec.get("operator_id") == str(user.get("id"))

    async def get_record(rid: str, user: dict) -> dict:
        rec = await db.verval_records.find_one({"id": rid})
        if not rec or not can_view_record(rec, user):
            raise HTTPException(status_code=404, detail="Data Verval tidak ditemukan atau di luar kewenangan")
        return rec

    async def own_open_record(rid: str, user: dict) -> Tuple[dict, dict]:
        rec = await get_record(rid, user)
        if rec.get("operator_id") != str(user.get("id")):
            raise HTTPException(status_code=404, detail="Data Verval tidak ditemukan atau di luar kewenangan")
        # kewenangan dicek ulang setiap aksi (penugasan bisa dicabut kapan saja)
        pens, sas = await operator_scope(db, user)
        hh = await household_by_ref(db, rec["dtsen_ref"])
        if not dasar_akses(hh, pens, sas):
            raise HTTPException(status_code=403, detail="Penugasan Anda untuk sasaran ini sudah tidak berlaku")
        return rec, hh

    async def foto_list(rid: str) -> List[dict]:
        docs = await db.verval_foto.find({"record_id": rid, "status": "aktif"}).sort("diterima_at", 1).to_list(50)
        return [{k: d.get(k) for k in ("id", "jenis", "diambil_at", "diterima_at", "ukuran", "lebar",
                                       "tinggi", "sha256", "gps_saat_foto", "client_foto_id")} for d in docs]

    async def record_out(rec: dict, user: dict, with_hh: bool = True) -> Dict[str, Any]:
        out = _clean(rec)
        out["foto"] = await foto_list(rec["id"])
        out["riwayat"] = [_clean(r) for r in await db.verval_riwayat.find({"record_id": rec["id"]})
                          .sort("waktu", 1).to_list(200)]
        if with_hh:
            docs = await db.households.find({"dtsen_ref": rec["dtsen_ref"]}).to_list(2)
            if len(docs) == 1:
                full = user.get("role") in cfg.HASIL_ROLES
                out["sasaran"] = hh_view(docs[0], full)
                out["dtsen"] = dtsen_values(docs[0], await kode_labels())
                out["household_id_terkini"] = docs[0].get("id")
            else:
                out["sasaran"] = None
                out["catatan_relasi"] = ("Rumah tangga dengan referensi ini belum ada pada data DTSEN "
                                         "terkini (mis. setelah impor ulang)" if not docs else
                                         "Referensi DTSEN ganda, perlu penelusuran admin")
        return out

    # ------------------------------------------------------------ konfigurasi
    @router.get("/konfigurasi")
    async def konfigurasi(user: dict = Depends(current_user_dep)):
        role = user.get("role")
        if role not in (*cfg.OPERATOR_ROLES, *cfg.HASIL_ROLES, *cfg.PENUGASAN_ADMIN_ROLES, *cfg.PETA_AGREGAT_ROLES):
            raise HTTPException(status_code=403, detail="Tidak berwenang")
        out = cfg.public_config()
        out["peran"] = role
        out["dapat_geotag"] = role in cfg.OPERATOR_ROLES
        out["dapat_review"] = role in cfg.REVIEWER_ROLES
        out["dapat_lihat_hasil"] = role in cfg.HASIL_ROLES
        out["scope_kecamatan"] = scope_mod.kecamatan_scope(user)
        if role == "petugas":
            prof = penugasan_profil(user)
            out["wilayah_petugas"] = {k: prof.get(k) for k in ("kecamatan", "kelurahan", "rw", "rt")} if prof else None
        out["dapat_kelola_penugasan"] = role in cfg.PENUGASAN_ADMIN_ROLES
        out["modul_siap"] = bool(dref.ref_secret())
        if role in cfg.PENUGASAN_ADMIN_ROLES:
            out["penyimpanan"] = storage.status()
            out["households_tanpa_ref"] = await db.households.count_documents({"dtsen_ref": {"$exists": False}})
        return out

    # ------------------------------------------------------------ operator: sasaran
    @router.get("/saya")
    async def saya(user: dict = Depends(operator_dep)):
        pens, sas = await operator_scope(db, user)
        items = await operator_households(db, user)
        recs = await db.verval_records.find({"operator_id": str(user["id"])}).to_list(20000)
        per_status: Dict[str, int] = {}
        for r in recs:
            per_status[r["status"]] = per_status.get(r["status"], 0) + 1
        return {
            "penugasan": [{k: p.get(k) for k in ("id", "kecamatan", "kelurahan", "kode_kelurahan", "rw", "rt",
                                                  "lintas_wilayah", "dasar_penugasan", "berlaku_mulai",
                                                  "berlaku_sampai")} for p in pens],
            "jumlah_sasaran_khusus": len(sas), "jumlah_sasaran": len(items),
            "per_status": per_status, "config": cfg.public_config(),
        }

    @router.get("/sasaran")
    async def sasaran_saya(search: Optional[str] = None, status: Optional[str] = None,
                           page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                           user: dict = Depends(operator_dep)):
        items = await operator_households(db, user)
        recs = {}
        for r in await db.verval_records.find({"operator_id": str(user["id"])}).sort("updated_at", -1).to_list(20000):
            recs.setdefault(r["dtsen_ref"], r)
        rows = []
        s = (search or "").strip().upper()
        for hh, da in items:
            if s and s not in str(hh.get("kepala_keluarga") or "").upper() and s not in str(hh.get("alamat") or "").upper():
                continue
            r = recs.get(hh["dtsen_ref"])
            st = r["status"] if r else "belum_diverval"
            if status and st != status:
                continue
            v = hh_view(hh, False)
            v.update({"dasar_akses": da["jenis"], "status_verval": st, "record_id": r["id"] if r else None,
                      "updated_at": r.get("updated_at") if r else None})
            rows.append(v)
        rows.sort(key=lambda x: (x["status_verval"] != "perlu_perbaikan", x["status_verval"] != "draft",
                                 x["kelurahan"] or "", int(x["rw"] or 0), int(x["rt"] or 0), x["kepala_keluarga"]))
        total = len(rows)
        start = (page - 1) * size
        return {"total": total, "page": page, "pages": max(1, math.ceil(total / size)), "items": rows[start:start + size]}

    @router.get("/sasaran/{ref}")
    async def sasaran_detail(ref: str, request: Request, user: dict = Depends(operator_dep)):
        if not dref.valid_ref(ref):
            raise HTTPException(status_code=404, detail="Data DTSEN tidak ditemukan atau di luar kewenangan")
        pens, sas = await operator_scope(db, user)
        hh = await household_by_ref(db, ref)
        da = dasar_akses(hh, pens, sas)
        if not da:
            await audit(db, user, "verval_akses_lintas_ditolak", "verval", ref, "di luar penugasan", request, "ditolak")
            raise HTTPException(status_code=404, detail="Data DTSEN tidak ditemukan atau di luar kewenangan")
        await audit(db, user, "verval_buka_sasaran", "verval", ref, da["jenis"], request)
        open_rec = None
        for r in await db.verval_records.find({"dtsen_ref": ref}).sort("updated_at", -1).to_list(50):
            if r.get("status") in cfg.STATUS_TERBUKA and r.get("operator_id") == str(user["id"]):
                open_rec = r
                break
        v = hh_view(hh, False)
        v["dasar_akses"] = da["jenis"]
        return {"sasaran": v, "dtsen": dtsen_values(hh, await kode_labels()),
                "record": await record_out(open_rec, user, with_hh=False) if open_rec else None}

    # ------------------------------------------------------------ operator: record
    @router.post("/records")
    async def buat_record(inp: RecordCreate, request: Request, user: dict = Depends(operator_dep)):
        uid = str(user["id"])
        # idempoten: client_uuid yang sama -> record yang sama
        same = await db.verval_records.find_one({"operator_id": uid, "client_uuid": inp.client_uuid})
        if same:
            return await record_out(same, user)
        pens, sas = await operator_scope(db, user)
        hh = await household_by_ref(db, inp.dtsen_ref) if dref.valid_ref(inp.dtsen_ref) else None
        da = dasar_akses(hh, pens, sas) if hh else None
        if not da:
            await audit(db, user, "verval_akses_lintas_ditolak", "verval", inp.dtsen_ref, "buat record", request, "ditolak")
            raise HTTPException(status_code=404, detail="Data DTSEN tidak ditemukan atau di luar kewenangan")
        for r in await db.verval_records.find({"dtsen_ref": inp.dtsen_ref}).to_list(100):
            if r.get("status") in cfg.STATUS_TERBUKA:
                if r.get("operator_id") == uid:
                    return await record_out(r, user)
                raise HTTPException(status_code=409, detail="Sasaran ini sedang diverval oleh operator lain")
        rec = {
            "id": str(uuid.uuid4()), "client_uuid": inp.client_uuid, "dtsen_ref": inp.dtsen_ref,
            "household_id_saat_verval": hh.get("id"),
            "kode_kecamatan": hh.get("kode_kecamatan"), "kecamatan": hh.get("kecamatan"),
            "kode_kelurahan": hh.get("kode_kelurahan"), "kelurahan": hh.get("kelurahan"),
            "rt": dref.norm_rt_rw(hh.get("rt")), "rw": dref.norm_rt_rw(hh.get("rw")),
            "operator_id": uid, "operator_email": user.get("email"), "operator_nama": user.get("name"),
            "dasar_akses": da, "status": "draft",
            "indikator": {}, "anggota_rentan": [], "kesimpulan": {"pilihan": None, "catatan": ""},
            "catatan_umum": "",
            "gps": {"status_gps": "belum_direkam"}, "foto_count": 0, "versi": 1,
            "data_uji": bool(hh.get("data_uji")),
            "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.verval_records.insert_one(rec)
        await riwayat(rec["id"], user, "buat_draft", None, "draft")
        await audit(db, user, "verval_buat_draft", "verval", rec["id"], inp.dtsen_ref, request)
        return await record_out(rec, user)

    @router.get("/records")
    async def list_records(status: Optional[str] = None, kode_kelurahan: Optional[str] = None,
                           page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=100),
                           user: dict = Depends(current_user_dep)):
        role = user.get("role")
        q: Dict[str, Any] = {}
        if role in cfg.OPERATOR_ROLES:
            q["operator_id"] = str(user["id"])
        elif role in cfg.HASIL_ROLES:
            q["status"] = {"$ne": "draft"}
            scope_query(user, q)
        else:
            raise HTTPException(status_code=403, detail="Tidak berwenang melihat daftar Verval")
        if status:
            if status not in cfg.STATUS:
                raise HTTPException(status_code=400, detail="Status tidak valid")
            if role in cfg.HASIL_ROLES and status == "draft":
                return {"total": 0, "page": 1, "pages": 1, "items": []}
            q["status"] = status
        if kode_kelurahan:
            q["kode_kelurahan"] = str(kode_kelurahan)
        total = await db.verval_records.count_documents(q)
        docs = await db.verval_records.find(q).sort("updated_at", -1).skip((page - 1) * size).limit(size).to_list(size)
        keys = ("id", "status", "kecamatan", "kelurahan", "rt", "rw", "operator_email", "operator_nama",
                "foto_count", "submitted_at", "updated_at", "reviewed_at", "data_uji", "dtsen_ref")
        items = []
        for d in docs:
            it = {k: d.get(k) for k in keys}
            it["status_gps"] = (d.get("gps") or {}).get("status_gps")
            items.append(it)
        return {"total": total, "page": page, "pages": max(1, math.ceil(total / size)), "items": items}

    @router.get("/records/{rid}")
    async def detail_record(rid: str, request: Request, user: dict = Depends(current_user_dep)):
        rec = await get_record(rid, user)
        if user.get("role") in cfg.HASIL_ROLES:
            await audit(db, user, "verval_lihat_detail", "verval", rid, "identitas & koordinat", request)
        return await record_out(rec, user)

    @router.put("/records/{rid}")
    async def ubah_record(rid: str, inp: RecordUpdate, request: Request, user: dict = Depends(operator_dep)):
        rec, _hh = await own_open_record(rid, user)
        if rec["status"] not in cfg.STATUS_DAPAT_DIUBAH:
            raise HTTPException(status_code=409, detail=f"Data berstatus '{rec['status']}' tidak dapat diubah")
        if inp.versi is not None and inp.versi != rec.get("versi"):
            raise HTTPException(status_code=409, detail="Data telah diperbarui di perangkat lain. Muat ulang.")
        upd: Dict[str, Any] = {}
        if inp.indikator is not None:
            merged = dict(rec.get("indikator") or {})
            merged.update(inp.indikator)
            upd["indikator"] = merged
        if inp.anggota_rentan is not None:
            upd["anggota_rentan"] = inp.anggota_rentan
        if inp.kesimpulan is not None:
            prev = dict(rec.get("kesimpulan") or {})
            prev.update({k: v for k, v in inp.kesimpulan.items() if v is not None or k == "pilihan"})
            upd["kesimpulan"] = {"pilihan": prev.get("pilihan"), "catatan": prev.get("catatan") or ""}
        if inp.catatan_umum is not None:
            upd["catatan_umum"] = _bersih(inp.catatan_umum, 2000)
        if inp.alasan_tanpa_gps is not None:
            upd["alasan_tanpa_gps"] = _bersih(inp.alasan_tanpa_gps, 500)
        if inp.gps is not None:
            g = inp.gps
            batas = cfg.gps_max_akurasi_m()
            if g.lat is not None and g.lng is not None and g.akurasi_m is not None:
                st = "memenuhi" if g.akurasi_m <= batas else "akurasi_rendah"
            elif g.izin == "denied":
                st = "izin_ditolak"
            else:
                st = "tidak_tersedia"
            upd["gps"] = {"lat": g.lat, "lng": g.lng, "akurasi_m": g.akurasi_m,
                          "diambil_at": _bersih(g.diambil_at, 40), "izin": _bersih(g.izin, 30),
                          "galat": _bersih(g.galat, 200), "status_gps": st, "batas_akurasi_m": batas,
                          "sumber": "browser_geolocation", "diterima_at": now_iso(),
                          # koordinat perangkat = lokasi pengambilan, BUKAN lokasi rumah terverifikasi
                          "terverifikasi": False}
        if not upd:
            return await record_out(rec, user)
        upd["updated_at"] = now_iso()
        upd["versi"] = int(rec.get("versi") or 1) + 1
        await db.verval_records.update_one({"id": rid}, {"$set": upd})
        await audit(db, user, "verval_ubah_draft", "verval", rid, ",".join(k for k in upd if k not in ("updated_at", "versi")), request)
        return await record_out(await db.verval_records.find_one({"id": rid}), user)

    def _formulir_lengkap(rec: dict) -> List[str]:
        """Validasi Form Verval (Bagian II + III + IV). Return list masalah (kosong = lengkap)."""
        masalah: List[str] = []
        ind = rec.get("indikator") or {}
        for i in cfg.INDIKATOR:
            item = ind.get(i["key"]) or {}
            kes = item.get("kesesuaian")
            riil = item.get("kondisi_riil")
            if not kes:
                masalah.append(f"Variabel '{i['label']}' — kolom Kesesuaian belum diisi")
            if not riil:
                masalah.append(f"Variabel '{i['label']}' — kolom Kondisi Riil Lapangan belum diisi")
            perlu = (kes in cfg.INDIKATOR_PERLU_CATATAN) or (riil in cfg.INDIKATOR_PERLU_CATATAN)
            if perlu and not (item.get("catatan") or "").strip():
                masalah.append(f"Variabel '{i['label']}' — catatan verifikator wajib diisi")
        kes = rec.get("kesimpulan") or {}
        pil = kes.get("pilihan")
        if not pil:
            masalah.append("Kesimpulan Verval belum dipilih (Bagian IV)")
        else:
            for k in cfg.KESIMPULAN:
                if k["key"] == pil and k.get("wajib_catatan") and not (kes.get("catatan") or "").strip():
                    masalah.append(f"Catatan wajib untuk kesimpulan '{k['label']}'")
        # Anggota rentan boleh kosong, namun jika diisi harus valid (sudah divalidasi di pydantic).
        return masalah

    @router.post("/records/{rid}/foto")
    async def unggah_foto(rid: str, request: Request, file: UploadFile = File(...),
                          client_foto_id: str = Form(...), jenis: str = Form("rumah_depan"),
                          diambil_at: str = Form(""), lat: Optional[float] = Form(None),
                          lng: Optional[float] = Form(None), akurasi_m: Optional[float] = Form(None),
                          user: dict = Depends(operator_dep)):
        rec, _hh = await own_open_record(rid, user)
        if rec["status"] not in cfg.STATUS_DAPAT_DIUBAH:
            raise HTTPException(status_code=409, detail="Foto hanya dapat ditambahkan pada draft / perlu perbaikan")
        kurang = _formulir_lengkap(rec)
        if kurang:
            raise HTTPException(status_code=422, detail={
                "msg": "Form Verval wajib diselesaikan sebelum mengunggah foto",
                "masalah": kurang,
            })
        cid = _bersih(client_foto_id, 64)
        if len(cid) < 8:
            raise HTTPException(status_code=400, detail="client_foto_id tidak valid")
        existing = await db.verval_foto.find_one({"record_id": rid, "client_foto_id": cid})
        if existing and existing.get("status") == "aktif":
            return {"duplikat": True, "foto": await foto_list(rid)}
        if jenis not in cfg.JENIS_FOTO:
            raise HTTPException(status_code=400, detail="Jenis foto tidak valid")
        aktif = await db.verval_foto.count_documents({"record_id": rid, "status": "aktif"})
        if aktif >= cfg.max_foto_per_record():
            raise HTTPException(status_code=400, detail=f"Maksimal {cfg.max_foto_per_record()} foto per Verval")
        raw = await file.read(cfg.max_foto_mb() * 1024 * 1024 + 1)
        exif = storage.exif_gps(raw)  # dibaca SEBELUM re-encode (EXIF dibuang saat disimpan)
        try:
            data, w, h = storage.process_image(raw, cfg.max_foto_mb())
        except storage.StorageError as e:
            await audit(db, user, "verval_unggah_foto_gagal", "verval", rid, e.detail, request, "gagal")
            raise HTTPException(status_code=e.status, detail=e.detail)
        import hashlib
        sha = hashlib.sha256(data).hexdigest()
        if await db.verval_foto.find_one({"record_id": rid, "sha256": sha, "status": "aktif"}):
            return {"duplikat": True, "foto": await foto_list(rid)}
        try:
            rel, sha = storage.save(rid, data)
        except storage.StorageError as e:
            await audit(db, user, "verval_unggah_foto_gagal", "verval", rid, e.detail, request, "gagal")
            raise HTTPException(status_code=e.status, detail=e.detail)
        gps_foto = None
        if lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180:
            gps_foto = {"lat": lat, "lng": lng, "akurasi_m": akurasi_m, "sumber": "gps_perangkat"}
        elif exif:
            gps_foto = {"lat": exif["lat"], "lng": exif["lng"], "akurasi_m": None, "sumber": "exif_foto"}
            if not diambil_at and exif.get("diambil_at"):
                diambil_at = exif["diambil_at"]
        await db.verval_foto.insert_one({
            "id": str(uuid.uuid4()), "record_id": rid, "client_foto_id": cid, "sha256": sha, "path": rel,
            "ukuran": len(data), "lebar": w, "tinggi": h, "mime": "image/jpeg", "jenis": jenis,
            "diambil_at": _bersih(diambil_at, 40), "diterima_at": now_iso(), "gps_saat_foto": gps_foto,
            "operator_id": str(user["id"]), "status": "aktif", "data_uji": bool(rec.get("data_uji"))})
        n = await db.verval_foto.count_documents({"record_id": rid, "status": "aktif"})
        upd_rec: Dict[str, Any] = {"foto_count": n, "updated_at": now_iso()}
        # Sinkron ke peta: bila record belum punya koordinat, pakai koordinat foto ini
        g_lama = rec.get("gps") or {}
        if gps_foto and g_lama.get("lat") is None:
            batas = cfg.gps_max_akurasi_m()
            ak = gps_foto.get("akurasi_m")
            st = "memenuhi" if (ak is not None and ak <= batas) else "akurasi_rendah"
            upd_rec["gps"] = {"lat": gps_foto["lat"], "lng": gps_foto["lng"], "akurasi_m": ak,
                              "diambil_at": _bersih(diambil_at, 40), "izin": "granted" if ak is not None else "tidak_diketahui",
                              "galat": "", "status_gps": st, "batas_akurasi_m": batas,
                              "sumber": "foto_" + gps_foto["sumber"], "diterima_at": now_iso(), "terverifikasi": False}
        await db.verval_records.update_one({"id": rid}, {"$set": upd_rec})
        await audit(db, user, "verval_unggah_foto", "verval", rid,
                    f"{jenis} {len(data)}B gps={'ya' if gps_foto else 'tidak'}", request)
        return {"duplikat": False, "foto": await foto_list(rid), "gps_record": upd_rec.get("gps")}

    @router.delete("/records/{rid}/foto/{fid}")
    async def hapus_foto(rid: str, fid: str, request: Request, user: dict = Depends(operator_dep)):
        rec, _hh = await own_open_record(rid, user)
        if rec["status"] not in cfg.STATUS_DAPAT_DIUBAH:
            raise HTTPException(status_code=409, detail="Foto pada data terkirim tidak dapat dihapus")
        f = await db.verval_foto.find_one({"id": fid, "record_id": rid, "status": "aktif"})
        if not f:
            raise HTTPException(status_code=404, detail="Foto tidak ditemukan")
        # soft delete: berkas tetap ada untuk jejak audit; dibersihkan oleh kebijakan retensi
        await db.verval_foto.update_one({"id": fid}, {"$set": {"status": "dihapus", "dihapus_at": now_iso()}})
        n = await db.verval_foto.count_documents({"record_id": rid, "status": "aktif"})
        await db.verval_records.update_one({"id": rid}, {"$set": {"foto_count": n, "updated_at": now_iso()}})
        await audit(db, user, "verval_hapus_foto", "verval", rid, fid, request)
        return {"foto": await foto_list(rid)}

    @router.post("/records/{rid}/kirim")
    async def kirim(rid: str, request: Request, user: dict = Depends(operator_dep)):
        rec = await get_record(rid, user)
        if rec.get("operator_id") == str(user["id"]) and rec["status"] == "terkirim":
            return {"idempoten": True, **await record_out(rec, user)}  # kirim ulang tidak menggandakan
        rec, _hh = await own_open_record(rid, user)
        if rec["status"] not in cfg.STATUS_DAPAT_DIUBAH:
            raise HTTPException(status_code=409, detail=f"Status '{rec['status']}' tidak dapat dikirim")
        masalah: List[str] = []
        # 1) Form Verval komprehensif (Bagian II + III + IV)
        masalah += _formulir_lengkap(rec)
        # 2) Foto minimum
        nfoto = await db.verval_foto.count_documents({"record_id": rid, "status": "aktif"})
        if nfoto < cfg.min_foto():
            masalah.append(f"Minimal {cfg.min_foto()} foto harus berhasil diunggah")
        # 3) GPS sesuai kebijakan
        gps = rec.get("gps") or {}
        if gps.get("status_gps") != "memenuhi":
            if not cfg.izinkan_kirim_tanpa_gps():
                masalah.append(f"Lokasi GPS belum memenuhi akurasi ≤ {cfg.gps_max_akurasi_m():g} m "
                               f"(status: {gps.get('status_gps') or 'belum_direkam'})")
            elif not rec.get("alasan_tanpa_gps"):
                masalah.append("Alasan wajib diisi bila mengirim tanpa GPS yang memenuhi akurasi")
        if masalah:
            raise HTTPException(status_code=422, detail={"msg": "Data belum lengkap untuk dikirim", "masalah": masalah})
        dari = rec["status"]
        upd = {"status": "terkirim", "submitted_at": now_iso(), "updated_at": now_iso(),
               "versi": int(rec.get("versi") or 1) + 1,
               "tanda_terima": f"VV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{rid[:8].upper()}"}
        await db.verval_records.update_one({"id": rid, "status": dari}, {"$set": upd})
        await riwayat(rid, user, "kirim", dari, "terkirim")
        await audit(db, user, "verval_kirim", "verval", rid, upd["tanda_terima"], request)
        return {"idempoten": False, **await record_out(await db.verval_records.find_one({"id": rid}), user)}

    # ------------------------------------------------------------ foto (terotorisasi)
    @router.get("/foto/{fid}")
    async def lihat_foto(fid: str, request: Request, user: dict = Depends(current_user_dep)):
        f = await db.verval_foto.find_one({"id": fid})
        if not f:
            raise HTTPException(status_code=404, detail="Foto tidak ditemukan")
        rec = await db.verval_records.find_one({"id": f.get("record_id")})
        if not rec or not can_view_record(rec, user):
            await audit(db, user, "verval_lihat_foto_ditolak", "verval", fid, "", request, "ditolak")
            raise HTTPException(status_code=404, detail="Foto tidak ditemukan")
        try:
            data = storage.read(f["path"])
        except storage.StorageError as e:
            raise HTTPException(status_code=e.status, detail=e.detail)
        await audit(db, user, "verval_lihat_foto", "verval", fid, rec["id"], request)
        return Response(content=data, media_type="image/jpeg",
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    # ------------------------------------------------------------ review
    @router.post("/records/{rid}/review")
    async def review(rid: str, inp: ReviewIn, request: Request, user: dict = Depends(reviewer_dep)):
        if inp.keputusan not in cfg.KEPUTUSAN_REVIEW:
            raise HTTPException(status_code=400, detail="Keputusan tidak valid")
        rec = await get_record(rid, user)
        if rec["status"] != "terkirim":
            raise HTTPException(status_code=409, detail=f"Hanya data berstatus 'terkirim' yang dapat diperiksa (saat ini '{rec['status']}')")
        if rec.get("operator_id") == str(user["id"]):
            raise HTTPException(status_code=403, detail="Pemeriksa tidak boleh memeriksa hasil Verval sendiri")
        if inp.keputusan in ("ditolak", "perlu_perbaikan") and len(inp.catatan.strip()) < 5:
            raise HTTPException(status_code=422, detail="Catatan pemeriksaan wajib (min. 5 karakter) untuk keputusan ini")
        upd = {"status": inp.keputusan, "reviewed_by": user.get("email"), "reviewed_at": now_iso(),
               "review_catatan": _bersih(inp.catatan, 2000), "updated_at": now_iso(),
               "versi": int(rec.get("versi") or 1) + 1}
        await db.verval_records.update_one({"id": rid, "status": "terkirim"}, {"$set": upd})
        await riwayat(rid, user, "review", "terkirim", inp.keputusan, inp.catatan)
        await audit(db, user, f"verval_review_{inp.keputusan}", "verval", rid, "", request)
        # Catatan: keputusan ini TIDAK mengubah data sumber DTSEN (households).
        return await record_out(await db.verval_records.find_one({"id": rid}), user)

    # ------------------------------------------------------------ penugasan (admin)
    async def operator_user(user_id: str) -> dict:
        from bsonlite import ObjectId
        try:
            u = await db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            u = None
        if not u or u.get("role") not in cfg.OPERATOR_ROLES:
            raise HTTPException(status_code=400, detail="Pengguna harus berperan Petugas / Operator RT/RW")
        if u.get("status", "active") != "active":
            raise HTTPException(status_code=400, detail="Akun operator tidak aktif")
        return u

    def _tgl(v: Optional[str], nama: str) -> Optional[str]:
        if not v:
            return None
        try:
            return date.fromisoformat(str(v)[:10]).isoformat()
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Format {nama} harus YYYY-MM-DD")

    @router.get("/operator")
    async def daftar_operator(admin: dict = Depends(penugasan_admin_dep)):
        docs = await db.users.find({"role": {"$in": list(cfg.OPERATOR_ROLES)}}).to_list(2000)
        return {"items": [{"id": str(d["_id"]), "email": d.get("email"), "name": d.get("name"), "role": d.get("role"),
                           "wilayah": d.get("wilayah"), "kelurahan": d.get("kelurahan"), "rw": d.get("rw"),
                           "rt": d.get("rt") or [], "status": d.get("status")} for d in docs]}

    @router.get("/wilayah-dtsen")
    async def wilayah_dtsen(admin: dict = Depends(penugasan_admin_dep)):
        """Daftar kelurahan + RW/RT yang tercatat EKSPLISIT pada data DTSEN (bukan dari alamat)."""
        docs = await db.households.find({}).to_list(200000)
        agg: Dict[str, Dict[str, Any]] = {}
        for h in docs:
            k = str(h.get("kode_kelurahan") or "")
            if not k:
                continue
            a = agg.setdefault(k, {"kode_kelurahan": k, "kelurahan": h.get("kelurahan"), "kecamatan": h.get("kecamatan"),
                                   "total_kk": 0, "kk_dengan_rt_rw": 0, "rw": {}})
            a["total_kk"] += 1
            rw, rt = dref.norm_rt_rw(h.get("rw")), dref.norm_rt_rw(h.get("rt"))
            if rw:
                a["kk_dengan_rt_rw"] += 1
                a["rw"].setdefault(rw, set())
                if rt:
                    a["rw"][rw].add(rt)
        items = []
        for a in agg.values():
            a["rw"] = [{"rw": r, "rt": sorted(v, key=int)} for r, v in sorted(a["rw"].items(), key=lambda x: int(x[0]))]
            items.append(a)
        items.sort(key=lambda x: (x["kecamatan"] or "", x["kelurahan"] or ""))
        return {"items": items, "catatan": "RT/RW hanya dari kolom eksplisit impor DTSEN. KK tanpa RT/RW "
                                           "harus ditetapkan sebagai KK sasaran oleh admin."}

    @router.get("/penugasan")
    async def list_penugasan(user_id: Optional[str] = None, admin: dict = Depends(penugasan_admin_dep)):
        q: Dict[str, Any] = {"user_id": user_id} if user_id else {}
        docs = await db.verval_penugasan.find(q).sort("created_at", -1).to_list(2000)
        sas = await db.verval_sasaran.find(q).sort("created_at", -1).to_list(5000)
        return {"penugasan": [_clean(d) for d in docs], "sasaran": [_clean(s) for s in sas]}

    @router.post("/penugasan")
    async def buat_penugasan(inp: PenugasanIn, request: Request, admin: dict = Depends(penugasan_admin_dep)):
        op = await operator_user(inp.user_id)
        contoh = await db.households.find_one({"kode_kelurahan": str(inp.kode_kelurahan)})
        if not contoh:
            raise HTTPException(status_code=400, detail="Kode kelurahan tidak ditemukan pada data DTSEN")
        rw = dref.norm_rt_rw(inp.rw)
        if not rw:
            raise HTTPException(status_code=422, detail="RW wajib berupa angka")
        rts = sorted({dref.norm_rt_rw(r) for r in inp.rt if dref.norm_rt_rw(r)}, key=int)
        mulai, sampai = _tgl(inp.berlaku_mulai, "berlaku_mulai"), _tgl(inp.berlaku_sampai, "berlaku_sampai")
        wil_op = (op.get("wilayah") or "").strip().lower()
        lintas = inp.lintas_wilayah or bool(wil_op and wil_op not in ("kota makassar",)
                                            and wil_op not in (str(contoh.get("kecamatan") or "").lower(),
                                                               str(contoh.get("kelurahan") or "").lower()))
        if lintas and (len(inp.dasar_penugasan.strip()) < 5 or not sampai):
            raise HTTPException(status_code=422, detail="Penugasan lintas wilayah wajib mencantumkan dasar penugasan (mis. nomor SK) dan tanggal berakhir")
        dup = [p for p in await db.verval_penugasan.find({"user_id": inp.user_id, "status": "aktif",
                                                           "kode_kelurahan": str(inp.kode_kelurahan)}).to_list(200)
               if p.get("rw") == rw and (p.get("rt") or []) == rts]
        if dup:
            raise HTTPException(status_code=409, detail="Penugasan yang sama sudah aktif")
        doc = {"id": str(uuid.uuid4()), "user_id": inp.user_id, "operator_email": op.get("email"),
               "kode_kecamatan": contoh.get("kode_kecamatan"), "kecamatan": contoh.get("kecamatan"),
               "kode_kelurahan": str(inp.kode_kelurahan), "kelurahan": contoh.get("kelurahan"),
               "rw": rw, "rt": rts, "lintas_wilayah": lintas, "dasar_penugasan": _bersih(inp.dasar_penugasan, 300),
               "berlaku_mulai": mulai, "berlaku_sampai": sampai, "catatan": _bersih(inp.catatan, 500),
               "status": "aktif", "ditetapkan_oleh": admin.get("email"), "created_at": now_iso()}
        await db.verval_penugasan.insert_one(doc)
        await audit(db, admin, "verval_penugasan_buat", "verval_penugasan", doc["id"],
                    f"{op.get('email')} kel {doc['kode_kelurahan']} RW {rw} RT {rts or 'semua'} lintas={lintas}", request)
        return _clean(doc)

    @router.post("/penugasan/{pid}/cabut")
    async def cabut_penugasan(pid: str, inp: CabutIn, request: Request, admin: dict = Depends(penugasan_admin_dep)):
        p = await db.verval_penugasan.find_one({"id": pid, "status": "aktif"})
        if not p:
            raise HTTPException(status_code=404, detail="Penugasan aktif tidak ditemukan")
        await db.verval_penugasan.update_one({"id": pid}, {"$set": {
            "status": "dicabut", "dicabut_oleh": admin.get("email"), "dicabut_at": now_iso(),
            "alasan_cabut": _bersih(inp.alasan, 500)}})
        await audit(db, admin, "verval_penugasan_cabut", "verval_penugasan", pid, inp.alasan, request)
        return {"ok": True}

    @router.post("/sasaran-kk")
    async def tetapkan_sasaran(inp: SasaranIn, request: Request, admin: dict = Depends(penugasan_admin_dep)):
        op = await operator_user(inp.user_id)
        hh = None
        if inp.household_id:
            hh = await db.households.find_one({"id": inp.household_id})
        elif inp.dtsen_ref and dref.valid_ref(inp.dtsen_ref):
            hh = await household_by_ref(db, inp.dtsen_ref)
        if not hh:
            raise HTTPException(status_code=404, detail="Rumah tangga DTSEN tidak ditemukan")
        ref = hh.get("dtsen_ref") or dref.ref_for_household(hh)
        if not ref:
            raise HTTPException(status_code=400, detail="Rumah tangga tanpa No. KK tidak dapat dijadikan sasaran")
        if not hh.get("dtsen_ref"):
            await db.households.update_one({"id": hh["id"]}, {"$set": {"dtsen_ref": ref}})
        await household_by_ref(db, ref)  # pastikan tidak ganda
        if await db.verval_sasaran.find_one({"user_id": inp.user_id, "dtsen_ref": ref, "status": "aktif"}):
            raise HTTPException(status_code=409, detail="KK ini sudah menjadi sasaran operator tersebut")
        pens = [p for p in await db.verval_penugasan.find({"user_id": inp.user_id, "status": "aktif"}).to_list(500)]
        dalam_wilayah = any(str(p.get("kode_kelurahan")) == str(hh.get("kode_kelurahan")) for p in pens)
        lintas = not dalam_wilayah
        sampai = _tgl(inp.berlaku_sampai, "berlaku_sampai")
        if lintas and len(inp.dasar_penugasan.strip()) < 5:
            raise HTTPException(status_code=422, detail="KK di luar kelurahan penugasan operator: wajib mencantumkan dasar penugasan lintas wilayah")
        doc = {"id": str(uuid.uuid4()), "user_id": inp.user_id, "operator_email": op.get("email"),
               "dtsen_ref": ref, "household_id_saat_penetapan": hh.get("id"),
               "kode_kelurahan": hh.get("kode_kelurahan"), "kelurahan": hh.get("kelurahan"),
               "kecamatan": hh.get("kecamatan"), "no_kk_tersamar": _mask_kk(hh.get("no_kk")),
               "lintas_wilayah": lintas, "dasar_penugasan": _bersih(inp.dasar_penugasan, 300),
               "berlaku_sampai": sampai, "catatan": _bersih(inp.catatan, 500), "status": "aktif",
               "ditetapkan_oleh": admin.get("email"), "created_at": now_iso()}
        await db.verval_sasaran.insert_one(doc)
        await audit(db, admin, "verval_sasaran_tetapkan", "verval_sasaran", doc["id"],
                    f"{op.get('email')} ref {ref} lintas={lintas}", request)
        return _clean(doc)

    @router.post("/sasaran-kk/{sid}/cabut")
    async def cabut_sasaran(sid: str, inp: CabutIn, request: Request, admin: dict = Depends(penugasan_admin_dep)):
        s = await db.verval_sasaran.find_one({"id": sid, "status": "aktif"})
        if not s:
            raise HTTPException(status_code=404, detail="Sasaran aktif tidak ditemukan")
        await db.verval_sasaran.update_one({"id": sid}, {"$set": {
            "status": "dicabut", "dicabut_oleh": admin.get("email"), "dicabut_at": now_iso(),
            "alasan_cabut": _bersih(inp.alasan, 500)}})
        await audit(db, admin, "verval_sasaran_cabut", "verval_sasaran", sid, inp.alasan, request)
        return {"ok": True}

    @router.post("/sinkron-referensi")
    async def sinkron_referensi(request: Request, admin: dict = Depends(penugasan_admin_dep)):
        n = await dref.backfill_refs(db)
        await audit(db, admin, "verval_sinkron_referensi", "households", "", f"{n} diisi", request)
        return {"diisi": n}

    # ------------------------------------------------------------ peta (satu sumber untuk 2 peta)
    @router.get("/peta")
    async def peta(user: dict = Depends(current_user_dep)):
        """Satu sumber lapisan GeoTag untuk SEMUA peta (Peta Sosial, Peta Kemiskinan, Peta Bangunan,
        Titik Koordinat). Titik = koordinat GPS record; bila belum ada, koordinat foto pertama."""
        role = user.get("role")
        info_bangunan = {"tersedia": False, "alasan": (
            "Polygon pada Peta Bangunan adalah DATA DEMO dengan No. KK acak sehingga TIDAK dihubungkan "
            "dengan GeoTag/DTSEN. Integrasi spasial menunggu sumber geometri bangunan resmi yang "
            "memiliki identitas terverifikasi.")}
        base = {"sumber": "verval_records + verval_foto (satu sumber untuk seluruh peta)",
                "integrasi_bangunan": info_bangunan, "batas_akurasi_m": cfg.gps_max_akurasi_m(),
                "scope_kecamatan": scope_mod.kecamatan_scope(user)}
        if role in cfg.OPERATOR_ROLES or role in cfg.HASIL_ROLES:
            if role in cfg.OPERATOR_ROLES:
                q: Dict[str, Any] = {"operator_id": str(user["id"])}
            else:
                q = scope_query(user, {"status": {"$ne": "draft"}})
            docs = await db.verval_records.find(q).to_list(20000)
            ids = [d["id"] for d in docs]
            foto_by_rec: Dict[str, List[dict]] = {}
            if ids:
                for f in await db.verval_foto.find({"record_id": {"$in": ids}, "status": "aktif"}).to_list(100000):
                    foto_by_rec.setdefault(f["record_id"], []).append(f)
            titik = []
            features = []
            for d in docs:
                fotos = sorted(foto_by_rec.get(d["id"], []), key=lambda f: f.get("diterima_at") or "")
                g = d.get("gps") or {}
                lat, lng, ak, sumber = g.get("lat"), g.get("lng"), g.get("akurasi_m"), g.get("sumber") or "gps_record"
                if lat is None or lng is None:
                    for f in fotos:  # cadangan: koordinat foto
                        gf = f.get("gps_saat_foto") or {}
                        if gf.get("lat") is not None and gf.get("lng") is not None:
                            lat, lng, ak, sumber = gf["lat"], gf["lng"], gf.get("akurasi_m"), "foto"
                            break
                if lat is None or lng is None:
                    continue
                foto_items = [{"id": f["id"], "jenis": f.get("jenis"), "diambil_at": f.get("diambil_at"),
                               "gps": f.get("gps_saat_foto")} for f in fotos]
                t = {"id": d["id"], "lat": lat, "lng": lng, "akurasi_m": ak, "sumber_koordinat": sumber,
                     "status_gps": g.get("status_gps"), "status": d.get("status"),
                     "kelurahan": d.get("kelurahan"), "kecamatan": d.get("kecamatan"),
                     "rw": d.get("rw"), "rt": d.get("rt"), "foto_count": len(fotos), "foto": foto_items,
                     "dtsen_ref": d.get("dtsen_ref"), "operator_nama": d.get("operator_nama"),
                     "kesimpulan": (d.get("kesimpulan") or {}).get("pilihan"),
                     "updated_at": d.get("updated_at"), "data_uji": bool(d.get("data_uji"))}
                titik.append(t)
                features.append({"type": "Feature", "id": d["id"],
                                 "geometry": {"type": "Point", "coordinates": [lng, lat]},
                                 "properties": {
                                     "nama": "GeoTag Verval DTSEN" + (" (DATA UJI)" if t["data_uji"] else ""),
                                     "status_verval": d.get("status"), "kelurahan": d.get("kelurahan"),
                                     "kecamatan": d.get("kecamatan"),
                                     "rw_rt": f"RW {d.get('rw') or '-'} / RT {d.get('rt') or '-'}",
                                     "gps": f"{lat:.6f}, {lng:.6f}" + (f" (±{ak:g} m)" if ak is not None else ""),
                                     "foto": len(fotos), "waktu": d.get("updated_at"), "record_id": d["id"],
                                     "sumber": "GeoTag petugas/operator"}})
            geojson = {"type": "FeatureCollection", "features": features, "count": len(features)}
            return {**base, "mode": "titik", "titik": titik, "total": len(titik), "geojson": geojson,
                    "peran_reviewer": role in cfg.REVIEWER_ROLES, "peran_hasil": role in cfg.HASIL_ROLES,
                    "peran_pelaksana": role in cfg.OPERATOR_ROLES}
        if role in cfg.PETA_AGREGAT_ROLES:
            docs = await db.verval_records.find(scope_query(user, {"status": {"$ne": "draft"}})).to_list(20000)
            agg: Dict[str, Dict[str, Any]] = {}
            for d in docs:
                k = str(d.get("kode_kelurahan") or d.get("kelurahan"))
                a = agg.setdefault(k, {"kode_kelurahan": d.get("kode_kelurahan"), "kelurahan": d.get("kelurahan"),
                                       "kecamatan": d.get("kecamatan"), "total": 0, "per_status": {}, "dengan_gps": 0})
                a["total"] += 1
                a["per_status"][d["status"]] = a["per_status"].get(d["status"], 0) + 1
                if (d.get("gps") or {}).get("status_gps") == "memenuhi":
                    a["dengan_gps"] += 1
            return {**base, "mode": "agregat", "kelurahan": list(agg.values()), "total": len(docs),
                    "catatan": "Peran Anda hanya melihat rekap per kelurahan (tanpa titik, foto, atau identitas)."}
        raise HTTPException(status_code=403, detail="Tidak berwenang melihat lapisan GeoTag")

    return router


async def startup(db, logger) -> None:
    """Dipanggil saat startup: isi referensi stabil (latar belakang) & laporkan status penyimpanan."""
    import asyncio
    st = storage.status()
    if not st["dapat_ditulis"]:
        logger.warning("Verval: penyimpanan foto belum siap (%s)", st["pesan"])
    if not dref.ref_secret():
        logger.warning("Verval: VERVAL_REF_SECRET belum diatur - modul GeoTag-Verval nonaktif")
        return

    async def _bg():
        try:
            await dref.backfill_refs(db, logger)
        except Exception as e:  # noqa: BLE001
            logger.warning("Verval: pengisian referensi DTSEN gagal: %s", type(e).__name__)
    asyncio.create_task(_bg())
