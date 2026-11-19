"""PETA INKLUSI — 4 kategori (Disabilitas, Stunting, ATS, Kemiskinan), dashboard publik,
NGO Inquiry, dashboard admin, masking data pribadi & audit log.

Pola: build_router(db, current_user_dep, writer_dep, admin_dep) -> APIRouter.
Endpoint /public/* TANPA login dan HANYA mengembalikan data agregat.
"""
from __future__ import annotations

import base64
import io
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field, field_validator

import notifier
import seed_data

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

# ------------------------------------------------------------------ peran
SUPER_ROLES = ("superadmin", "admin")
ADMIN_ROLES = SUPER_ROLES + ("verifikator", "admin_bappeda", "pimpinan")
OPERATOR_ROLES = ("petugas", "operator", "operator_kecamatan", "operator_kelurahan", "admin_opd")
STAFF_ROLES = ADMIN_ROLES + OPERATOR_ROLES
SENSITIVE_ROLES = SUPER_ROLES + ("verifikator", "admin_bappeda")  # boleh lihat data asli
PROCESS_ROLES = SUPER_ROLES + ("verifikator", "admin_bappeda") + OPERATOR_ROLES  # proses inquiry


def role_group(role: Optional[str]) -> str:
    if role in SUPER_ROLES:
        return "Super Admin"
    if role in ADMIN_ROLES:
        return "Admin"
    if role in OPERATOR_ROLES:
        return "Operator"
    if role == "ngo":
        return "NGO"
    return "Public"


# ------------------------------------------------------------------ util
def norm_wil(value: Any) -> str:
    """Normalisasi nama wilayah agar konsisten antar dataset (master PETA_DASAR)."""
    s = str(value or "").strip().upper().replace("-", " ")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def mask_nik(v: Any) -> str:
    s = re.sub(r"\D", "", str(v or ""))
    return f"{s[:4]}{'*' * max(0, len(s) - 8)}{s[-4:]}" if len(s) >= 8 else ("*" * len(s))


def mask_email(v: Any) -> str:
    s = str(v or "")
    if "@" not in s:
        return s
    user, dom = s.split("@", 1)
    return f"{user[:2]}{'*' * max(2, len(user) - 2)}@{dom}"


def mask_phone(v: Any) -> str:
    s = re.sub(r"[^\d+]", "", str(v or ""))
    return f"{s[:4]}{'*' * max(0, len(s) - 6)}{s[-2:]}" if len(s) >= 6 else ("*" * len(s))


def mask_name(v: Any) -> str:
    parts = str(v or "").split()
    return " ".join(p[0] + "*" * max(2, len(p) - 1) for p in parts) if parts else "-"


def mask_address(v: Any) -> str:
    s = str(v or "")
    return (s[:6] + "…") if len(s) > 6 else ("*" * len(s))


def _clean(d: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {k: v for k, v in (d or {}).items() if k != "_id"}


def client_info(request: Optional[Request]) -> Dict[str, str]:
    if not request:
        return {}
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "")
    return {"ip": ip, "user_agent": (request.headers.get("user-agent") or "")[:160]}


async def audit(db, user: Optional[Dict[str, Any]], aksi: str, entitas: str, ref: str = "",
                detail: Any = None, request: Optional[Request] = None, status: str = "sukses"):
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "user": (user or {}).get("email") or "anonim",
        "role": (user or {}).get("role") or "public", "aksi": aksi, "entitas": entitas,
        "ref": ref, "detail": str(detail)[:1500] if detail is not None else "",
        "status": status, **client_info(request), "created_at": now_iso(),
    })


# ------------------------------------------------------------------ inquiry
KATEGORI = ["Disabilitas", "Stunting", "ATS", "Kemiskinan", "Lintas kategori"]
STATUS_FLOW = ["SUBMITTED", "UNDER_REVIEW", "VERIFICATION", "APPROVED", "NEED_REVISION",
               "REJECTED", "PROGRAM_IMPLEMENTATION", "MONITORING", "COMPLETED"]
TRANSISI = {
    "SUBMITTED": ["UNDER_REVIEW", "REJECTED"],
    "UNDER_REVIEW": ["VERIFICATION", "NEED_REVISION", "REJECTED"],
    "VERIFICATION": ["APPROVED", "NEED_REVISION", "REJECTED"],
    "NEED_REVISION": ["UNDER_REVIEW", "REJECTED"],
    "APPROVED": ["PROGRAM_IMPLEMENTATION"],
    "PROGRAM_IMPLEMENTATION": ["MONITORING"],
    "MONITORING": ["COMPLETED"],
    "REJECTED": [], "COMPLETED": [],
}
MAX_LAMPIRAN = 10 * 1024 * 1024
EXT_LAMPIRAN = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".jpg", ".jpeg", ".png")


def _strip_tags(v: Any) -> Any:
    """Validasi input: buang tag HTML untuk mencegah XSS tersimpan."""
    if isinstance(v, str):
        return re.sub(r"<[^>]*>", "", v).strip()
    return v


class InquiryInput(BaseModel):
    nama_ngo: str = Field(..., min_length=2, max_length=160)
    nama_pic: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    telepon: str = Field(..., min_length=6, max_length=20)
    organisasi: str = Field("", max_length=160)
    alamat_organisasi: str = Field("", max_length=500)
    kategori: str
    kecamatan: str = Field(..., min_length=2, max_length=80)
    kelurahan: str = Field("", max_length=80)
    statistik_wilayah: Dict[str, Any] = Field(default_factory=dict)
    permasalahan: str = Field(..., min_length=10, max_length=4000)
    deskripsi_kebutuhan: str = Field(..., min_length=10, max_length=4000)
    program_usulan: str = Field(..., min_length=3, max_length=2000)
    target_penerima: str = Field(..., min_length=3, max_length=500)
    jumlah_penerima: int = Field(..., ge=1, le=10_000_000)
    durasi_bulan: int = Field(..., ge=1, le=120)
    estimasi_anggaran: Optional[float] = Field(None, ge=0)
    catatan: str = Field("", max_length=2000)

    @field_validator("kategori")
    @classmethod
    def _kat(cls, v):
        if v not in KATEGORI:
            raise ValueError(f"Kategori harus salah satu dari: {', '.join(KATEGORI)}")
        return v

    @field_validator("telepon")
    @classmethod
    def _tel(cls, v):
        if not re.fullmatch(r"\+?[0-9 ()-]{6,20}", v):
            raise ValueError("Nomor telepon tidak valid")
        return v

    @field_validator("nama_ngo", "nama_pic", "organisasi", "alamat_organisasi", "kecamatan", "kelurahan",
                     "permasalahan", "deskripsi_kebutuhan", "program_usulan", "target_penerima", "catatan")
    @classmethod
    def _xss(cls, v):
        return _strip_tags(v)


class StatusInput(BaseModel):
    status: str
    catatan: str = Field("", max_length=2000)

    @field_validator("catatan")
    @classmethod
    def _xss(cls, v):
        return _strip_tags(v)


def mask_inquiry(d: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    d = _clean(d)
    d.pop("lampiran_data", None)
    own = d.get("user_email") == user.get("email")
    if not own and user.get("role") not in SENSITIVE_ROLES:
        d["email"] = mask_email(d.get("email"))
        d["telepon"] = mask_phone(d.get("telepon"))
        d["user_email"] = mask_email(d.get("user_email"))
        d["data_masked"] = True
    return d


# ------------------------------------------------------------------ router
def build_router(db, current_user_dep, writer_dep, admin_dep) -> APIRouter:
    router = APIRouter(tags=["inklusi"])

    async def staff_dep(user: dict = Depends(current_user_dep)):
        if user.get("role") not in STAFF_ROLES:
            raise HTTPException(status_code=403, detail="Akses khusus Operator/Admin")
        return user

    async def process_dep(user: dict = Depends(current_user_dep)):
        if user.get("role") not in PROCESS_ROLES:
            raise HTTPException(status_code=403, detail="Peran Anda tidak berwenang memproses inquiry")
        return user

    # ---------------------------------------------------------- agregat per kategori
    async def _regions() -> List[Dict[str, Any]]:
        return [_clean(r) for r in await db.regions.find({}).to_list(100)]

    async def _geo_index() -> Dict[str, Dict[str, Any]]:
        return {norm_wil(g.get("kelurahan")): g for g in await db.geo_kelurahan.find({}).to_list(500)}

    async def kategori_data(kategori: str, level: str) -> Dict[str, Any]:
        regs = await _regions()
        kec_field = {"disabilitas": "disabilitas", "stunting": "stunting_anak", "ats": "ats",
                     "kemiskinan": "kemiskinan_ekstrim_kk"}[kategori]
        kec_items = [{"kecamatan": r["nama"], "kecamatan_norm": norm_wil(r["nama"]),
                      "value": int(r.get(kec_field) or 0),
                      "detail": {"kemiskinan_persen": r.get("kemiskinan_persen")} if kategori == "kemiskinan" else {}}
                     for r in regs]
        sumber_kec = {
            "disabilitas": "Rekap disabilitas per kecamatan (Matriks Bappeda)",
            "stunting": "Rekap anak stunting per kecamatan (Matriks Bappeda)",
            "ats": "Rekap Anak Tidak Sekolah per kecamatan (Matriks ATS)",
            "kemiskinan": "KK kemiskinan ekstrem per kecamatan (Matriks Kemiskinan)",
        }[kategori]
        out: Dict[str, Any] = {"kategori": kategori, "level": level, "sumber": sumber_kec,
                               "total": sum(i["value"] for i in kec_items)}
        if level == "kecamatan":
            out["items"] = sorted(kec_items, key=lambda x: -x["value"])
            out["satuan"] = {"disabilitas": "orang", "stunting": "anak", "ats": "anak", "kemiskinan": "KK"}[kategori]
            return out
        # ---- kelurahan
        items: Dict[str, Dict[str, Any]] = {}
        geo = await _geo_index()

        def slot(kel_norm: str, kel: str, kec: str) -> Dict[str, Any]:
            g = geo.get(kel_norm) or {}
            return items.setdefault(kel_norm, {
                "kelurahan": g.get("kelurahan") or kel, "kelurahan_norm": kel_norm,
                "kecamatan": g.get("kecamatan") or kec, "kecamatan_norm": norm_wil(g.get("kecamatan") or kec),
                "value": 0, "detail": {}})

        if kategori == "disabilitas":
            for d in await db.disability_region_stats.find({}).to_list(2000):
                s = slot(norm_wil(d.get("kelurahan")), d.get("kelurahan"), d.get("kecamatan"))
                s["value"] += int(d.get("jumlah") or 0)
                s["detail"]["tahun"] = d.get("tahun")
            out["sumber"] = "Data disabilitas per kelurahan (Kec. Tallo & Kec. Makassar)"
            out["satuan"] = "orang"
        elif kategori == "stunting":
            for c in await db.stunting_children.find({}).to_list(20000):
                if not c.get("kelurahan_norm"):
                    continue
                s = slot(c["kelurahan_norm"], c.get("kelurahan"), c.get("kecamatan"))
                s["value"] += 1
                det = s["detail"]
                det["laki_laki"] = det.get("laki_laki", 0) + (c.get("jk") == "L")
                det["perempuan"] = det.get("perempuan", 0) + (c.get("jk") == "P")
                det["sangat_pendek"] = det.get("sangat_pendek", 0) + (c.get("status_tbu") == "Sangat Pendek")
                det["pendek"] = det.get("pendek", 0) + (c.get("status_tbu") == "Pendek")
            out["sumber"] = "Data balita stunting 2026 (Kec. Makassar & Kec. Tallo)"
            out["satuan"] = "anak"
        elif kategori == "kemiskinan":
            for v in await db.village_stats.find({}).to_list(2000):
                s = slot(norm_wil(v.get("kelurahan")), v.get("kelurahan"), v.get("kecamatan") or "")
                s["value"] = int(v.get("desil_1_2") or 0)
                s["detail"] = {k: v.get(k) for k in (
                    "total_households", "total_individu", "desil_1_2", "persen_desil_1_2", "pbi_nas",
                    "pbi_pemda", "rumah_rentan", "sanitasi_tidak_layak", "air_rentan", "hunian_rentan",
                    "listrik_rentan", "avg_risk", "skor_prioritas", "prioritas_tinggi")}
            out["sumber"] = "DTSEN — rumah tangga desil 1-2 per kelurahan (Kec. Makassar & Kec. Tallo)"
            out["satuan"] = "KK desil 1-2"
        else:  # ats — dari impor Excel per kelurahan (tahun terbaru)
            rows = await db.ats_kelurahan.find({}).to_list(50000)
            out["satuan"] = "anak"
            if rows:
                tahun = max(int(r.get("tahun") or 0) for r in rows)
                for r in rows:
                    if int(r.get("tahun") or 0) != tahun:
                        continue
                    s = slot(r.get("kelurahan_norm") or norm_wil(r.get("kelurahan")), r.get("kelurahan"), r.get("kecamatan"))
                    s["value"] += int(r.get("jumlah") or 0)
                    det = s["detail"]
                    det["tahun"] = tahun
                    det["laki_laki"] = det.get("laki_laki", 0) + int(r.get("laki_laki") or 0)
                    det["perempuan"] = det.get("perempuan", 0) + int(r.get("perempuan") or 0)
                    jj = str(r.get("jenjang") or "-").upper()
                    det[f"jenjang_{jj}"] = det.get(f"jenjang_{jj}", 0) + int(r.get("jumlah") or 0)
                out["sumber"] = f"Impor data ATS per kelurahan (tahun {tahun})"
                out["tahun"] = tahun
            else:
                out["sumber"] = "Belum ada data ATS tingkat kelurahan"
                out["catatan"] = ("Data ATS saat ini hanya tersedia per kecamatan. Silakan impor data ATS "
                                  "per kelurahan melalui menu Data ATS agar peta kelurahan terisi.")
        out["items"] = sorted(items.values(), key=lambda x: -x["value"])
        out["total_kelurahan_data"] = sum(1 for i in out["items"] if i["value"] > 0)
        out["total"] = sum(i["value"] for i in out["items"]) if out["items"] else out["total"]
        return out

    async def stunting_breakdown(filter_: Dict[str, Any]) -> Dict[str, Any]:
        rows = await db.stunting_children.find(filter_).to_list(20000)

        def count(key):
            c: Dict[str, int] = {}
            for r in rows:
                c[str(r.get(key) or "-")] = c.get(str(r.get(key) or "-"), 0) + 1
            return [{"kategori": k, "jumlah": v} for k, v in sorted(c.items(), key=lambda x: -x[1])]
        urut = ["0-11 bulan", "12-23 bulan", "24-35 bulan", "36-47 bulan", "48-59 bulan", "≥ 60 bulan", "Tidak diketahui"]
        umur = sorted(count("kelompok_umur"), key=lambda x: urut.index(x["kategori"]) if x["kategori"] in urut else 99)
        jk = [{"kategori": "Laki-laki" if i["kategori"] == "L" else "Perempuan" if i["kategori"] == "P" else "-",
               "jumlah": i["jumlah"]} for i in count("jk")]
        return {"total": len(rows), "per_kecamatan": count("kecamatan"), "per_kelurahan": count("kelurahan"),
                "kelompok_umur": umur, "jenis_kelamin": jk, "status_tbu": count("status_tbu"),
                "per_puskesmas": count("puskesmas"), "tahun": 2026}

    # ---------------------------------------------------------- PUBLIC (tanpa login, agregat)
    @router.get("/public/summary")
    async def public_summary():
        regs = await _regions()
        tot = lambda f: sum(int(r.get(f) or 0) for r in regs)  # noqa: E731
        n_kel = await db.kelurahan.count_documents({})
        n_hh = await db.households.count_documents({})
        vstats = await db.village_stats.find({}).to_list(2000)
        return {
            "kategori": {
                "disabilitas": {"total": tot("disabilitas"), "satuan": "orang",
                                "sumber": "Rekap per kecamatan (Matriks Bappeda)"},
                "stunting": {"total": tot("stunting_anak"), "satuan": "anak",
                             "terdata_by_name": await db.stunting_children.count_documents({}),
                             "sumber": "Rekap per kecamatan (Matriks Bappeda)"},
                "ats": {"total": int(seed_data.ATS["ringkasan"]["ats_total"]), "satuan": "anak", "sumber": "Matriks ATS",
                        "total_rincian_kecamatan": tot("ats"),
                        "catatan": "Total kota menurut Matriks ATS; jumlah rincian per kecamatan dapat berbeda."},
                "kemiskinan": {"total": tot("kemiskinan_ekstrim_kk"), "satuan": "KK miskin ekstrem",
                               "persen_kota": seed_data.POVERTY_TREND[-1]["persen"],
                               "sumber": "Matriks Kemiskinan & BPS"},
            },
            "wilayah": {"kecamatan": len(regs), "kelurahan": n_kel},
            "dtsen": {"rumah_tangga": n_hh, "individu": sum(int(v.get("total_individu") or 0) for v in vstats),
                      "kelurahan_terdata": len(vstats)},
            "per_kecamatan": [{"kecamatan": r["nama"], "disabilitas": r.get("disabilitas", 0),
                               "stunting": r.get("stunting_anak", 0), "ats": r.get("ats", 0),
                               "kemiskinan": r.get("kemiskinan_ekstrim_kk", 0),
                               "kemiskinan_persen": r.get("kemiskinan_persen")} for r in regs],
            "tren": {"kemiskinan": seed_data.POVERTY_TREND, "stunting": seed_data.STUNTING_TREND,
                     "ats": seed_data.ATS["per_tahun"], "disabilitas": seed_data.DISABILITY["total_per_tahun"]},
            "disabilitas_ragam": seed_data.DISABILITY["ragam"],
            "catatan": "Seluruh angka merupakan data agregat. Data pribadi tidak ditampilkan.",
            "diperbarui": now_iso(),
        }

    @router.get("/public/map/{kategori}")
    async def public_map(kategori: str, level: str = Query("kecamatan", pattern="^(kecamatan|kelurahan)$")):
        if kategori not in ("disabilitas", "stunting", "ats", "kemiskinan"):
            raise HTTPException(status_code=404, detail="Kategori tidak dikenal")
        data = await kategori_data(kategori, level)
        if kategori == "kemiskinan" and level == "kelurahan":  # publik: indikator agregat saja
            for i in data["items"]:
                i["detail"] = {k: i["detail"].get(k) for k in ("total_households", "desil_1_2", "persen_desil_1_2",
                                                              "pbi_nas", "pbi_pemda", "rumah_rentan")}
        return data

    @router.get("/public/stunting/breakdown")
    async def public_stunting_breakdown(kecamatan: Optional[str] = None, kelurahan: Optional[str] = None):
        f: Dict[str, Any] = {}
        if kecamatan:
            f["kecamatan_norm"] = norm_wil(kecamatan)
        if kelurahan:
            f["kelurahan_norm"] = norm_wil(kelurahan)
        data = await stunting_breakdown(f)
        data.pop("per_puskesmas", None)
        return data

    @router.get("/public/ats")
    async def public_ats():
        regs = await _regions()
        return {"per_kecamatan": sorted([{"kecamatan": r["nama"], "jumlah": r.get("ats", 0)} for r in regs],
                                        key=lambda x: -x["jumlah"]),
                "per_tahun": seed_data.ATS["per_tahun"], "ringkasan": seed_data.ATS["ringkasan"],
                "catatan": "Distribusi kelurahan, umur, dan jenis kelamin belum tersedia."}

    @router.get("/public/wilayah")
    async def public_wilayah():
        geo = await db.geo_kelurahan.find({}).to_list(500)
        kec: Dict[str, List[str]] = {}
        for g in geo:
            kec.setdefault(g.get("kecamatan"), []).append(g.get("kelurahan"))
        return {"kota": "Kota Makassar", "kecamatan": [
            {"nama": k, "kelurahan": sorted(v)} for k, v in sorted(kec.items())]}

    # ---------------------------------------------------------- DATA (login)
    @router.get("/inklusi/map/{kategori}")
    async def inklusi_map(kategori: str, level: str = Query("kecamatan", pattern="^(kecamatan|kelurahan)$"),
                          user: dict = Depends(current_user_dep)):
        if kategori not in ("disabilitas", "stunting", "ats", "kemiskinan"):
            raise HTTPException(status_code=404, detail="Kategori tidak dikenal")
        return await kategori_data(kategori, level)

    @router.get("/inklusi/stunting/children")
    async def stunting_children(request: Request, q: Optional[str] = None, kecamatan: Optional[str] = None,
                                kelurahan: Optional[str] = None, status: Optional[str] = None,
                                jk: Optional[str] = None, page: int = Query(1, ge=1),
                                size: int = Query(25, ge=1, le=200), user: dict = Depends(staff_dep)):
        f: Dict[str, Any] = {}
        if kecamatan:
            f["kecamatan_norm"] = norm_wil(kecamatan)
        if kelurahan:
            f["kelurahan_norm"] = norm_wil(kelurahan)
        if status:
            f["status_tbu"] = status
        if jk in ("L", "P"):
            f["jk"] = jk
        if q:
            f["nama"] = {"$regex": re.escape(q[:60]), "$options": "i"}
        total = await db.stunting_children.count_documents(f)
        rows = await db.stunting_children.find(f).sort("kelurahan", 1).skip((page - 1) * size).limit(size).to_list(size)
        allow = user.get("role") in SENSITIVE_ROLES
        items = []
        for r in rows:
            d = _clean(r)
            if not allow:
                d.update({"nama": mask_name(d.get("nama")), "nama_ortu": mask_name(d.get("nama_ortu")),
                          "alamat": mask_address(d.get("alamat")), "tgl_lahir": "**/**/" + str(d.get("tgl_lahir", ""))[-4:],
                          "data_masked": True})
            items.append(d)
        if allow:
            await audit(db, user, "lihat_data_sensitif", "stunting_children", "",
                        {"filter": {k: str(v) for k, v in f.items()}, "page": page, "jumlah": len(items)}, request)
        return {"total": total, "page": page, "size": size, "pages": max(1, -(-total // size)),
                "masked": not allow, "items": items}

    @router.get("/inklusi/stunting/stats")
    async def stunting_stats(kecamatan: Optional[str] = None, user: dict = Depends(current_user_dep)):
        return await stunting_breakdown({"kecamatan_norm": norm_wil(kecamatan)} if kecamatan else {})

    @router.get("/inklusi/musrenbang")
    async def musrenbang(kelompok: Optional[str] = None, q: Optional[str] = None,
                         user: dict = Depends(current_user_dep)):
        f: Dict[str, Any] = {}
        if kelompok:
            f["kelompok"] = kelompok
        if q:
            f["permasalahan"] = {"$regex": re.escape(q[:60]), "$options": "i"}
        rows = [_clean(r) for r in await db.musrenbang_usulan.find(f).to_list(1000)]
        kel: Dict[str, int] = {}
        for r in await db.musrenbang_usulan.find({}).to_list(1000):
            kel[r.get("kelompok") or "-"] = kel.get(r.get("kelompok") or "-", 0) + 1
        return {"total": len(rows), "items": rows, "kelompok": [{"kelompok": k, "jumlah": v} for k, v in kel.items()]}

    # ---------------------------------------------------------- NGO INQUIRY
    @router.post("/inquiries")
    async def create_inquiry(inp: InquiryInput, request: Request, user: dict = Depends(current_user_dep)):
        if user.get("role") not in ("ngo",) + PROCESS_ROLES:
            raise HTTPException(status_code=403, detail="Hanya akun NGO yang dapat mengajukan inquiry")
        n = await db.ngo_inquiries.count_documents({})
        doc = {
            "id": str(uuid.uuid4()), "nomor": f"INQ-{datetime.now().year}-{n + 1:04d}",
            **inp.model_dump(), "status": "SUBMITTED", "user_email": user.get("email"),
            "user_name": user.get("name"), "lampiran": [],
            "riwayat": [{"status": "SUBMITTED", "oleh": user.get("email"), "peran": role_group(user.get("role")),
                         "catatan": "Inquiry diajukan", "waktu": now_iso()}],
            "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.ngo_inquiries.insert_one(dict(doc))
        await audit(db, user, "create_inquiry", "ngo_inquiries", doc["id"],
                    {"nomor": doc["nomor"], "kategori": inp.kategori, "wilayah": f"{inp.kecamatan}/{inp.kelurahan}"}, request)
        return mask_inquiry(doc, user)

    @router.get("/inquiries")
    async def list_inquiries(status: Optional[str] = None, kategori: Optional[str] = None,
                             kecamatan: Optional[str] = None, q: Optional[str] = None,
                             page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                             user: dict = Depends(current_user_dep)):
        f: Dict[str, Any] = {}
        if user.get("role") == "ngo":
            f["user_email"] = user.get("email")  # NGO hanya melihat miliknya
        elif user.get("role") not in STAFF_ROLES:
            raise HTTPException(status_code=403, detail="Tidak berwenang")
        if status:
            f["status"] = status
        if kategori:
            f["kategori"] = kategori
        if kecamatan:
            f["kecamatan"] = kecamatan
        if q:
            f["nama_ngo"] = {"$regex": re.escape(q[:60]), "$options": "i"}
        total = await db.ngo_inquiries.count_documents(f)
        rows = await db.ngo_inquiries.find(f).sort("created_at", -1).skip((page - 1) * size).limit(size).to_list(size)
        return {"total": total, "page": page, "pages": max(1, -(-total // size)),
                "items": [mask_inquiry(r, user) for r in rows], "status_flow": STATUS_FLOW, "kategori": KATEGORI}

    async def _get_inquiry(iid: str, user: dict) -> Dict[str, Any]:
        d = await db.ngo_inquiries.find_one({"id": iid})
        if not d:
            raise HTTPException(status_code=404, detail="Inquiry tidak ditemukan")
        if user.get("role") == "ngo" and d.get("user_email") != user.get("email"):
            raise HTTPException(status_code=404, detail="Inquiry tidak ditemukan")
        if user.get("role") not in STAFF_ROLES + ("ngo",):
            raise HTTPException(status_code=403, detail="Tidak berwenang")
        return d

    @router.get("/inquiries/meta")
    async def inquiry_meta(user: dict = Depends(current_user_dep)):
        return {"kategori": KATEGORI, "status_flow": STATUS_FLOW, "transisi": TRANSISI}

    @router.get("/inquiries/{iid}")
    async def get_inquiry(iid: str, user: dict = Depends(current_user_dep)):
        d = await _get_inquiry(iid, user)
        out = mask_inquiry(d, user)
        out["transisi_berikut"] = TRANSISI.get(d.get("status"), []) if user.get("role") in PROCESS_ROLES else []
        return out

    @router.put("/inquiries/{iid}")
    async def revise_inquiry(iid: str, inp: InquiryInput, request: Request, user: dict = Depends(current_user_dep)):
        d = await _get_inquiry(iid, user)
        if d.get("user_email") != user.get("email"):
            raise HTTPException(status_code=403, detail="Hanya pengaju yang dapat merevisi inquiry")
        if d.get("status") not in ("SUBMITTED", "NEED_REVISION"):
            raise HTTPException(status_code=409, detail="Inquiry hanya dapat diubah saat SUBMITTED atau NEED_REVISION")
        riwayat = d.get("riwayat") or []
        baru = "UNDER_REVIEW" if d.get("status") == "NEED_REVISION" else "SUBMITTED"
        riwayat.append({"status": baru, "oleh": user.get("email"), "peran": role_group(user.get("role")),
                        "catatan": "Inquiry direvisi oleh pengaju", "waktu": now_iso()})
        await db.ngo_inquiries.update_one({"id": iid}, {"$set": {**inp.model_dump(), "status": baru,
                                                                  "riwayat": riwayat, "updated_at": now_iso()}})
        await audit(db, user, "update_inquiry", "ngo_inquiries", iid, {"status_baru": baru}, request)
        return mask_inquiry(await db.ngo_inquiries.find_one({"id": iid}), user)

    @router.patch("/inquiries/{iid}/status")
    async def change_status(iid: str, inp: StatusInput, request: Request, user: dict = Depends(process_dep)):
        d = await _get_inquiry(iid, user)
        lama = d.get("status")
        if inp.status not in TRANSISI.get(lama, []):
            raise HTTPException(status_code=422, detail=f"Status tidak dapat diubah dari {lama} ke {inp.status}")
        if inp.status in ("NEED_REVISION", "REJECTED") and len(inp.catatan) < 5:
            raise HTTPException(status_code=422, detail="Catatan wajib diisi untuk permintaan revisi/penolakan")
        riwayat = (d.get("riwayat") or []) + [{"status": inp.status, "oleh": user.get("email"),
                                                "peran": role_group(user.get("role")),
                                                "catatan": inp.catatan, "waktu": now_iso()}]
        await db.ngo_inquiries.update_one({"id": iid}, {"$set": {"status": inp.status, "riwayat": riwayat,
                                                                  "updated_at": now_iso()}})
        aksi = {"APPROVED": "approve_inquiry", "REJECTED": "reject_inquiry"}.get(inp.status, "update_status_inquiry")
        await audit(db, user, aksi, "ngo_inquiries", iid,
                    {"nomor": d.get("nomor"), "dari": lama, "ke": inp.status, "catatan": inp.catatan}, request)
        # ---- notifikasi email ke NGO (email kontak inquiry + email akun pengaju)
        notif_status = "tidak_dikirim"
        try:
            mail = notifier.inquiry_status_email(d, inp.status, inp.catatan, role_group(user.get("role")),
                                                 notifier.base_url_from_request(request))
            res = await notifier.queue_email(db, [d.get("email"), d.get("user_email")], mail["subject"],
                                             mail["text"], mail["html"], jenis="inquiry_status", ref=iid)
            notif_status = res.get("status", "gagal")
        except Exception as e:  # noqa: BLE001
            notif_status = "gagal"
            await audit(db, user, "email_gagal", "email_outbox", iid, str(e), request, status="gagal")
        riwayat[-1]["email"] = notif_status
        await db.ngo_inquiries.update_one({"id": iid}, {"$set": {"riwayat": riwayat}})
        out = mask_inquiry(await db.ngo_inquiries.find_one({"id": iid}), user)
        out["transisi_berikut"] = TRANSISI.get(inp.status, [])
        out["notifikasi_email"] = notif_status
        return out

    @router.post("/inquiries/{iid}/lampiran")
    async def upload_lampiran(iid: str, request: Request, file: UploadFile = File(...),
                              user: dict = Depends(current_user_dep)):
        d = await _get_inquiry(iid, user)
        if d.get("user_email") != user.get("email") and user.get("role") not in PROCESS_ROLES:
            raise HTTPException(status_code=403, detail="Tidak berwenang")
        nama = (file.filename or "lampiran").split("/")[-1][:120]
        if not nama.lower().endswith(EXT_LAMPIRAN):
            raise HTTPException(status_code=422, detail="Format lampiran: PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, JPG/PNG")
        data = await file.read(MAX_LAMPIRAN + 1)
        if len(data) > MAX_LAMPIRAN:
            raise HTTPException(status_code=413, detail="Ukuran lampiran maksimal 10 MB")
        if not data:
            raise HTTPException(status_code=422, detail="Lampiran kosong")
        fid = str(uuid.uuid4())
        # disimpan di MariaDB (potongan base64) — tidak bergantung disk server
        for seq, start in enumerate(range(0, len(data), 2 * 1024 * 1024)):
            await db.inquiry_files.insert_one({"id": f"{fid}-{seq:03d}", "file_id": fid, "inquiry_id": iid,
                                               "seq": seq, "data": base64.b64encode(data[start:start + 2 * 1024 * 1024]).decode()})
        meta = {"id": fid, "nama": nama, "ukuran": len(data), "tipe": file.content_type or "",
                "oleh": user.get("email"), "waktu": now_iso()}
        await db.ngo_inquiries.update_one({"id": iid}, {"$set": {"lampiran": (d.get("lampiran") or []) + [meta]}})
        await audit(db, user, "upload_lampiran_inquiry", "ngo_inquiries", iid, {"nama": nama}, request)
        return meta

    @router.get("/inquiries/{iid}/lampiran/{fid}")
    async def download_lampiran(iid: str, fid: str, user: dict = Depends(current_user_dep)):
        d = await _get_inquiry(iid, user)
        meta = next((m for m in d.get("lampiran") or [] if m.get("id") == fid), None)
        if not meta:
            raise HTTPException(status_code=404, detail="Lampiran tidak ditemukan")
        parts = await db.inquiry_files.find({"file_id": fid}).sort("seq", 1).to_list(100)
        data = b"".join(base64.b64decode(p["data"]) for p in parts)
        safe = re.sub(r'[^A-Za-z0-9._ -]', "_", meta["nama"])
        return StreamingResponse(io.BytesIO(data), media_type=meta.get("tipe") or "application/octet-stream",
                                 headers={"Content-Disposition": f'attachment; filename="{safe}"'})

    # ---------------------------------------------------------- DASHBOARD ADMIN
    @router.get("/inklusi/admin/overview")
    async def admin_overview(user: dict = Depends(staff_dep)):
        regs = await _regions()
        tot = lambda f: sum(int(r.get(f) or 0) for r in regs)  # noqa: E731
        inq = await db.ngo_inquiries.find({}).to_list(5000)
        per_status: Dict[str, int] = {s: 0 for s in STATUS_FLOW}
        per_kat: Dict[str, int] = {}
        for i in inq:
            per_status[i.get("status")] = per_status.get(i.get("status"), 0) + 1
            per_kat[i.get("kategori")] = per_kat.get(i.get("kategori"), 0) + 1
        pending = per_status.get("SUBMITTED", 0)
        diproses = sum(per_status.get(s, 0) for s in ("UNDER_REVIEW", "VERIFICATION", "NEED_REVISION", "APPROVED",
                                                        "PROGRAM_IMPLEMENTATION", "MONITORING"))
        logs = await db.audit_logs.find({}).sort("created_at", -1).limit(12).to_list(12)
        return {
            "totals": {"disabilitas": tot("disabilitas"), "stunting": tot("stunting_anak"), "ats": tot("ats"),
                       "kemiskinan": tot("kemiskinan_ekstrim_kk"),
                       "stunting_by_name": await db.stunting_children.count_documents({}),
                       "rumah_tangga_dtsen": await db.households.count_documents({})},
            "ngo": {"total": await db.users.count_documents({"role": "ngo"}),
                    "aktif": await db.users.count_documents({"role": "ngo", "status": "active"}),
                    "menunggu": await db.users.count_documents({"role": "ngo", "status": "pending"})},
            "inquiry": {"total": len(inq), "pending": pending, "diproses": diproses,
                        "selesai": per_status.get("COMPLETED", 0), "ditolak": per_status.get("REJECTED", 0),
                        "per_status": [{"status": k, "jumlah": v} for k, v in per_status.items()],
                        "per_kategori": [{"kategori": k, "jumlah": v} for k, v in per_kat.items()]},
            "per_kecamatan": [{"kecamatan": r["nama"], "disabilitas": r.get("disabilitas", 0),
                               "stunting": r.get("stunting_anak", 0), "ats": r.get("ats", 0),
                               "kemiskinan": r.get("kemiskinan_ekstrim_kk", 0)} for r in regs],
            "audit_terbaru": [{k: v for k, v in _clean(x).items() if k in ("user", "role", "aksi", "entitas", "status",
                                                                         "created_at", "ip")} for x in logs],
        }

    @router.get("/inklusi/audit-logs")
    async def audit_logs(aksi: Optional[str] = None, user_email: Optional[str] = Query(None, alias="user"),
                         page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200),
                         user: dict = Depends(current_user_dep)):
        if user.get("role") not in SENSITIVE_ROLES:
            raise HTTPException(status_code=403, detail="Akses khusus Admin/Super Admin")
        f: Dict[str, Any] = {}
        if aksi:
            f["aksi"] = aksi
        if user_email:
            f["user"] = {"$regex": re.escape(user_email[:60]), "$options": "i"}
        total = await db.audit_logs.count_documents(f)
        rows = await db.audit_logs.find(f).sort("created_at", -1).skip((page - 1) * size).limit(size).to_list(size)
        return {"total": total, "page": page, "pages": max(1, -(-total // size)), "items": [_clean(r) for r in rows]}

    return router
