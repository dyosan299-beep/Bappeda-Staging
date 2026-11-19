from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import re
import logging
import hashlib
import uuid
import time
from datetime import datetime, timezone

from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from bsonlite import ObjectId
import io
import json

import auth as authmod
import seed_data as seed
import report as report_mod
import verval as verval_mod
import export_excel as excel_mod
import rumah as rumah_mod
import sosial as sosial_mod
import ai_assistant as ai_assistant_mod
import llm_hostlinku
import peta_dasar as peta_dasar_mod
import import_wizard as import_wizard_mod
import inklusi as inklusi_mod
import inklusi_extra as inklusi_extra_mod
import inklusi_cerita as inklusi_cerita_mod
import matriks as matriks_mod
import musrenbang as musrenbang_mod
import notifier
import data_manage as data_manage_mod
import ringkasan_mingguan as ringkasan_mod
import scope as scope_mod
from mariadb_store import MariaDocStore, DuplicateKeyError

# ---------------- Database: MariaDB (Coolify-friendly env vars) ----------------
db = MariaDocStore.from_env()
# Provider AI tunggal: Hostlinku (HOSTLINKU_API_KEY). Bila kunci belum diisi,
# kontainer tetap hidup dan hanya fitur AI yang mengembalikan galat jelas.

# Cookie auth dapat disesuaikan lingkungan (single-origin di Docker vs cross-origin di preview)
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() in ("1", "true", "yes")
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax").lower()

# ---------------- Keamanan: CORS & pembatasan login ----------------
# Wildcard TIDAK dipakai untuk permintaan berkredensial. Bila CORS_ORIGINS kosong
# atau berisi "*", hanya origin pengembangan lokal yang diizinkan; deployment
# produksi wajib mengisi origin eksplisit (lihat DEPLOY_COOLIFY.md).
_cors_mentah = (os.environ.get("CORS_ORIGINS") or "").strip()
CORS_ORIGINS = [o.strip() for o in _cors_mentah.split(",") if o.strip() and o.strip() != "*"]
CORS_WILDCARD_DIMINTA = "*" in [o.strip() for o in _cors_mentah.split(",")]
APP_ENV = (os.environ.get("APP_ENV") or "development").strip().lower()
LINGKUNGAN_DEV = APP_ENV in ("dev", "development", "local")
if not CORS_ORIGINS and LINGKUNGAN_DEV:
    # Hanya untuk pengembangan lokal (frontend CRA di :3000).
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

LOGIN_MAX_ATTEMPTS = max(3, int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5") or 5))
LOGIN_WINDOW_SECONDS = max(60, int(os.environ.get("LOGIN_WINDOW_SECONDS", "900") or 900))
LOGIN_LOCK_SECONDS = max(60, int(os.environ.get("LOGIN_LOCK_SECONDS", "900") or 900))

# Header keamanan (praktik BSSN/ISO 27001; CSP ketat untuk halaman HTML).
HEADER_KEAMANAN = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(self), camera=(self), microphone=(self)",
    "Cross-Origin-Opener-Policy": "same-origin-allow-popups",
    "X-Permitted-Cross-Domain-Policies": "none",
}
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://maps.googleapis.com https://maps.gstatic.com; "
    "worker-src 'self' blob:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' https:"
    + (" http://localhost:8001 http://127.0.0.1:8001" if LINGKUNGAN_DEV else "") + "; "
    "frame-src 'self' https://www.youtube-nocookie.com https://player.vimeo.com https://www.google.com; "
    "frame-ancestors 'self'; base-uri 'self'; form-action 'self'; object-src 'none'"
)
NO_STORE_PREFIX = (
    "/api/auth/", "/api/sosial/households", "/api/inklusi/stunting/children",
    "/api/admin/", "/api/audit-log", "/api/users",
)

app = FastAPI(title="Sistem Intelijen Data Bappeda Kota Makassar")
api_router = APIRouter(prefix="/api")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bappeda")

if CORS_WILDCARD_DIMINTA:
    logger.warning("CORS_ORIGINS berisi '*': wildcard tidak dipakai untuk permintaan "
                   "berkredensial. Isi origin eksplisit, mis. https://domain.go.id")

if llm_hostlinku.tersedia():
    logger.info("Provider AI: Hostlinku (%s) aktif untuk AI Assistant & Analisa AI; "
                "TTS memakai suara browser", llm_hostlinku.DEFAULT_MODEL)
else:
    logger.warning("HOSTLINKU_API_KEY belum diisi - fitur AI Assistant & Analisa AI tidak aktif "
                   "(fitur lain tetap berjalan normal)")


# ---------------- Models ----------------
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    name: str
    wilayah: Optional[str] = ""
    role: Optional[str] = "petugas"


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class RegionUpdate(BaseModel):
    kemiskinan_ekstrim_kk: Optional[int] = Field(None, ge=0)
    stunting_anak: Optional[int] = Field(None, ge=0)
    anak_jalanan: Optional[int] = Field(None, ge=0)
    ats: Optional[int] = Field(None, ge=0)
    disabilitas: Optional[int] = Field(None, ge=0)
    kemiskinan_persen: Optional[float] = Field(None, ge=0, le=100)


class AIAnalyzeInput(BaseModel):
    kategori: str  # kemiskinan | stunting | anak_jalanan | ats | disabilitas
    wilayah: Optional[str] = None  # opsional: nama kecamatan


class TTSInput(BaseModel):
    text: str
    voice: Optional[str] = "alloy"
    kecepatan: Optional[str] = "normal"  # normal | slow | slower


class AIReportInput(BaseModel):
    kategori: str
    wilayah: Optional[str] = None
    hasil: str


class KelurahanUpdate(BaseModel):
    kemiskinan_ekstrim_kk: Optional[int] = Field(None, ge=0)
    stunting_anak: Optional[int] = Field(None, ge=0)
    anak_jalanan: Optional[int] = Field(None, ge=0)
    ats: Optional[int] = Field(None, ge=0)
    disabilitas: Optional[int] = Field(None, ge=0)
    kemiskinan_persen: Optional[float] = Field(None, ge=0, le=100)


class AdminCreateUser(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    name: str
    wilayah: Optional[str] = ""
    role: Optional[str] = "petugas"
    # Khusus petugas (ditentukan per RT/RW kelurahan)
    kelurahan: Optional[str] = ""
    rw: Optional[str] = ""
    rt: Optional[list] = None


class StatusUpdate(BaseModel):
    status: str  # active | inactive | pending


class AdminUpdateUser(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    wilayah: Optional[str] = None
    role: Optional[str] = None
    kelurahan: Optional[str] = None
    rw: Optional[str] = None
    rt: Optional[list] = None


class ResetPasswordInput(BaseModel):
    password: str = Field(min_length=10, max_length=128)


class ReviewInput(BaseModel):
    note: Optional[str] = ""


# ---------------- Auth dependency ----------------
# ---------------- Role helpers ----------------
SUPERADMIN_ROLES = ("superadmin", "admin")           # admin = legacy
INPUT_ROLES = ("operator",)                           # boleh input data wilayah (masuk verifikasi)
VERIFIER_ROLES = ("verifikator", "admin_bappeda")
# Peran (final):
#   superadmin/admin -> Super Admin (kelola operator/verifikator/pimpinan; TIDAK membuat petugas)
#   operator         -> Operator Kecamatan: membuat & mengelola akun PETUGAS di kecamatannya,
#                       input data wilayahnya; hanya melihat data kecamatannya
#   verifikator      -> memeriksa data/Verval hanya kecamatannya (wilayah="Kota Makassar" = seluruh kota)
#   petugas          -> Petugas lapangan RT/RW (dibuat operator): hanya data publik + Verval & GeoTag
#   pimpinan -> read-only, admin_opd -> Admin OPD, viewer -> hanya baca (akun lama tetap berlaku)
WRITER_ROLES = SUPERADMIN_ROLES + VERIFIER_ROLES + INPUT_ROLES + (
    "admin_opd", "operator_kecamatan", "operator_kelurahan")
ALL_ROLES = WRITER_ROLES + ("pimpinan", "viewer")
# Operator RT/RW (GeoTag-Verval DTSEN, akun lama) & Petugas: BUKAN penulis data umum; hanya modul Verval.
OPERATOR_RTRW_ROLE = "operator_rt_rw"
PETUGAS_ROLE = "petugas"
MANAGEABLE_ROLES = ("petugas", "operator", "verifikator", "pimpinan", "superadmin", "ngo", OPERATOR_RTRW_ROLE)
# Peran yang boleh dibuat/diubah oleh superadmin (petugas HANYA oleh operator)
SUPERADMIN_CREATABLE = tuple(r for r in MANAGEABLE_ROLES if r != PETUGAS_ROLE)
WILAYAH_REQUIRED_ROLES = ("operator", "petugas")      # wajib kecamatan


# API yang boleh diakses peran NGO (least privilege). NGO TIDAK boleh mengakses data
# individu (rumah tangga, anak stunting), impor, administrasi, maupun verifikasi.
NGO_ALLOWED_PREFIXES = (
    "/api/auth/", "/api/inquiries", "/api/public/", "/api/inklusi/map/", "/api/inklusi/stunting/stats",
    "/api/inklusi/musrenbang", "/api/geo/", "/api/peta-dasar/", "/api/stats/", "/api/trends/",
    "/api/sosial/overview", "/api/wilayah/", "/api/analisis/prioritas", "/api/disabilitas/overview",
    "/api/stunting/overview", "/api/rad/overview", "/api/regions", "/api/kelurahan", "/api/categories",
    "/api/disability", "/api/ats", "/api/pmks", "/api/inklusi/laporan/",
)


# API yang boleh diakses Operator RT/RW (least privilege). Data rumah tangga dibatasi
# lagi di endpoint (hanya sasaran yang ditugaskan).
OPERATOR_RTRW_ALLOWED_PREFIXES = (
    "/api/auth/", "/api/verval/", "/api/sosial/households", "/api/geo/", "/api/inklusi/map/",
    "/api/public/", "/api/wilayah/", "/api/peta-dasar/", "/api/map/config", "/api/tts",
)

# API yang boleh diakses PETUGAS (least privilege): data yang tampil di publik + modul Verval/GeoTag.
PETUGAS_ALLOWED_PREFIXES = tuple(p for p in OPERATOR_RTRW_ALLOWED_PREFIXES if p != "/api/sosial/households") + (
    "/api/stats/", "/api/trends/", "/api/regions", "/api/kelurahan", "/api/categories",
    "/api/disability", "/api/ats", "/api/pmks", "/api/sosial/overview", "/api/disabilitas/overview",
    "/api/stunting/overview", "/api/rad/overview", "/api/inklusi/stunting/stats", "/api/a11y/",
)


async def current_user(request: Request):
    user = await authmod.get_current_user(request, db)
    if user.get("status", "active") != "active":
        raise HTTPException(status_code=403, detail="Akun tidak aktif")
    if user.get("role") == "ngo" and not request.url.path.startswith(NGO_ALLOWED_PREFIXES):
        raise HTTPException(status_code=403, detail="Peran NGO tidak berwenang mengakses data ini")
    if user.get("role") == OPERATOR_RTRW_ROLE and not request.url.path.startswith(OPERATOR_RTRW_ALLOWED_PREFIXES):
        raise HTTPException(status_code=403, detail="Operator RT/RW hanya dapat mengakses modul GeoTag-Verval")
    if user.get("role") == PETUGAS_ROLE and not request.url.path.startswith(PETUGAS_ALLOWED_PREFIXES):
        raise HTTPException(status_code=403, detail="Petugas hanya dapat mengakses data publik serta modul Verval & GeoTag")
    return user


async def optional_user(request: Request) -> Optional[dict]:
    """Pengguna login bila ada (untuk endpoint publik yang perlu scoping wilayah)."""
    try:
        return await authmod.get_current_user(request, db)
    except HTTPException:
        return None


async def admin_user(request: Request):
    user = await authmod.get_current_user(request, db)
    if user.get("role") not in SUPERADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Akses khusus superadmin")
    return user


async def user_manager(request: Request):
    """Boleh mengelola akun: superadmin (semua peran kecuali petugas) & operator (petugas kecamatannya)."""
    user = await authmod.get_current_user(request, db)
    if user.get("status", "active") != "active":
        raise HTTPException(status_code=403, detail="Akun tidak aktif")
    if user.get("role") in SUPERADMIN_ROLES:
        return user
    if user.get("role") == "operator":
        if not scope_mod.kecamatan_scope(user):
            raise HTTPException(status_code=403, detail="Akun operator belum memiliki wilayah kecamatan")
        return user
    raise HTTPException(status_code=403, detail="Akses khusus superadmin / operator kecamatan")


async def verifikator_user(request: Request):
    user = await authmod.get_current_user(request, db)
    if user.get("role") not in SUPERADMIN_ROLES + VERIFIER_ROLES:
        raise HTTPException(status_code=403, detail="Akses khusus verifikator/superadmin")
    return user


async def editor_user(request: Request):
    """Boleh menambah/mengubah data rumah: superadmin, petugas, operator."""
    user = await authmod.get_current_user(request, db)
    if user.get("role") not in SUPERADMIN_ROLES + INPUT_ROLES:
        raise HTTPException(status_code=403, detail="Akses khusus petugas/operator/superadmin")
    return user


async def writer_user(request: Request):
    """Boleh menambah/mengubah data terintegrasi (input manual & impor).

    Mencakup Super Admin, Admin Bappeda, Admin OPD, dan seluruh operator.
    Peran Pimpinan & Viewer hanya dapat membaca.
    """
    user = await authmod.get_current_user(request, db)
    if user.get("role") not in WRITER_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Peran Anda hanya dapat melihat data (tidak berwenang mengubah)")
    return user


def _set_auth_cookies(response: Response, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=COOKIE_SECURE,
                        samesite=COOKIE_SAMESITE, max_age=43200, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=COOKIE_SECURE,
                        samesite=COOKIE_SAMESITE, max_age=604800, path="/")


# ---------------- Auth routes ----------------
@api_router.post("/auth/register")
async def register(inp: RegisterInput, response: Response):
    email = inp.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    authmod.validate_password(inp.password)
    # Registrasi publik selalu sebagai petugas berstatus 'pending' (menunggu persetujuan admin).
    doc = {
        "email": email, "password_hash": authmod.hash_password(inp.password),
        "name": inp.name, "role": "petugas", "wilayah": inp.wilayah or "",
        "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return {"message": "Registrasi berhasil. Akun Anda menunggu persetujuan admin Bappeda sebelum dapat digunakan.",
            "status": "pending"}


class NgoRegisterInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=128)
    organisasi: str = Field(..., min_length=2, max_length=160)
    telepon: str = Field(..., min_length=6, max_length=20)
    alamat_organisasi: str = Field("", max_length=500)


@api_router.post("/auth/register-ngo")
async def register_ngo(inp: NgoRegisterInput, request: Request):
    email = inp.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    authmod.validate_password(inp.password)
    strip = lambda s: re.sub(r"<[^>]*>", "", s or "").strip()  # noqa: E731
    await db.users.insert_one({
        "email": email, "password_hash": authmod.hash_password(inp.password),
        "name": strip(inp.name), "role": "ngo", "organisasi": strip(inp.organisasi),
        "telepon": strip(inp.telepon), "alamat_organisasi": strip(inp.alamat_organisasi),
        "wilayah": "Kota Makassar", "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await inklusi_mod.audit(db, {"email": email, "role": "ngo"}, "register_ngo", "users", email,
                            {"organisasi": inp.organisasi}, request)
    return {"message": "Pendaftaran NGO berhasil. Akun akan aktif setelah diverifikasi admin.",
            "status": "pending"}


# ---------------- Auth routes ----------------
def _ip_klien(request: Request) -> str:
    return (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "?"))


async def _cek_kunci_login(key: str) -> dict:
    """Tolak login bila pasangan IP+email sedang terkunci (anti brute force)."""
    rec = await db.login_attempts.find_one({"key": key}) or {}
    sekarang = time.time()
    terkunci = float(rec.get("locked_until") or 0)
    if terkunci > sekarang:
        sisa = max(1, int(terkunci - sekarang))
        raise HTTPException(status_code=429,
                            detail=f"Terlalu banyak percobaan masuk. Coba lagi dalam {sisa} detik.")
    if rec and sekarang - float(rec.get("first_at") or sekarang) > LOGIN_WINDOW_SECONDS:
        await db.login_attempts.delete_one({"key": key})
        return {}
    return rec


async def _catat_gagal_login(key: str, rec: dict) -> None:
    sekarang = time.time()
    n = int(rec.get("attempts") or 0) + 1
    upd = {"key": key, "attempts": n,
           "first_at": rec.get("first_at") or sekarang, "last_at": sekarang}
    if n >= LOGIN_MAX_ATTEMPTS:
        upd["locked_until"] = sekarang + LOGIN_LOCK_SECONDS
    await db.login_attempts.update_one({"key": key}, {"$set": upd}, upsert=True)


@api_router.post("/auth/login")
async def login(inp: LoginInput, response: Response, request: Request):
    email = inp.email.lower()
    kunci = f"{_ip_klien(request)}|{email}"
    rec = await _cek_kunci_login(kunci)
    user = await db.users.find_one({"email": email})
    if not user:
        # Tetap jalankan bcrypt agar waktu respons serupa dengan akun yang ada
        # (mencegah penyerang menebak email terdaftar).
        authmod.verify_password(inp.password, authmod.DUMMY_HASH)
        await _catat_gagal_login(kunci, rec)
        await inklusi_mod.audit(db, {"email": email}, "login", "auth", email, "kredensial salah",
                                request, status="gagal")
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    if not authmod.verify_password(inp.password, user["password_hash"]):
        await _catat_gagal_login(kunci, rec)
        await inklusi_mod.audit(db, {"email": email}, "login", "auth", email, "kredensial salah",
                                request, status="gagal")
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    await db.login_attempts.delete_one({"key": kunci})
    status = user.get("status", "active")
    if status == "pending":
        raise HTTPException(status_code=403, detail="Akun Anda masih menunggu persetujuan admin Bappeda.")
    if status != "active":
        raise HTTPException(status_code=403, detail="Akun Anda dinonaktifkan. Hubungi admin Bappeda.")
    uid = str(user["_id"])
    access = authmod.create_access_token(uid, email, user["role"])
    refresh = authmod.create_refresh_token(uid)
    _set_auth_cookies(response, access, refresh)
    await inklusi_mod.audit(db, user, "login", "auth", email, None, request)
    return {"id": uid, "email": email, "name": user["name"], "role": user["role"],
            "wilayah": user.get("wilayah", ""), "organisasi": user.get("organisasi", ""),
            "kelurahan": user.get("kelurahan", ""), "rw": user.get("rw", ""), "rt": user.get("rt") or []}


@api_router.post("/auth/logout")
async def logout(response: Response, request: Request):
    try:
        u = await authmod.get_current_user(request, db)
        await inklusi_mod.audit(db, u, "logout", "auth", u.get("email", ""), None, request)
    except HTTPException:
        pass
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Berhasil keluar"}


@api_router.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return user


# ---------------- Admin: Kelola Petugas ----------------
def _serialize_user(u):
    return {
        "id": str(u["_id"]),
        "email": u["email"],
        "name": u.get("name", ""),
        "role": u.get("role", "petugas"),
        "wilayah": u.get("wilayah", ""), "organisasi": u.get("organisasi", ""),
        "kelurahan": u.get("kelurahan", ""), "kode_kelurahan": u.get("kode_kelurahan", ""),
        "rw": u.get("rw", ""), "rt": u.get("rt") or [],
        "status": u.get("status", "active"),
        "created_at": u.get("created_at"),
        "created_by": u.get("created_by", ""),
    }


def _norm_rt_rw(v) -> str:
    s = re.sub(r"[^0-9]", "", str(v or ""))
    return str(int(s)) if s else ""


def _rt_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, str):
        v = re.split(r"[,\s;/]+", v)
    out = []
    for x in v:
        n = _norm_rt_rw(x)
        if n and n not in out:
            out.append(n)
    return sorted(out, key=int)


async def _kode_kelurahan_for(kecamatan: str, kelurahan: str) -> str:
    """Kode kelurahan (BPS) dari data DTSEN bila tersedia (untuk pencocokan sasaran Verval)."""
    if not kelurahan:
        return ""
    pola = {"$regex": f"^\\s*{re.escape(kelurahan.strip())}\\s*$", "$options": "i"}
    for coll in ("households", "village_stats"):
        try:
            d = await getattr(db, coll).find_one({"kelurahan": pola, "kode_kelurahan": {"$exists": True}})
        except Exception:  # noqa: BLE001
            continue
        if d and d.get("kode_kelurahan") and scope_mod.same_kecamatan(kecamatan, d.get("kecamatan")):
            return str(d["kode_kelurahan"])
    return ""


async def _kelurahan_valid(kecamatan: str, kelurahan: str) -> bool:
    docs = await db.kelurahan.find({"kecamatan": kecamatan}).to_list(200)
    if not docs:
        return True  # master belum ada -> jangan blokir
    target = scope_mod.norm(kelurahan)
    return any(scope_mod.norm(d.get("nama")) == target for d in docs)


def _is_operator(u: dict) -> bool:
    return u.get("role") == "operator"


async def _target_in_scope(manager: dict, user_id: str) -> dict:
    """Operator hanya boleh menyentuh akun PETUGAS di kecamatannya."""
    target = await db.users.find_one({"_id": _oid(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
    if _is_operator(manager):
        if target.get("role") != PETUGAS_ROLE or not scope_mod.same_kecamatan(
                scope_mod.kecamatan_scope(manager), target.get("wilayah")):
            raise HTTPException(status_code=403, detail="Operator hanya dapat mengelola akun petugas di kecamatannya")
    return target


@api_router.get("/admin/users")
async def admin_list_users(admin: dict = Depends(user_manager)):
    users = await db.users.find().sort("created_at", -1).to_list(1000)
    if _is_operator(admin):
        kec = scope_mod.kecamatan_scope(admin)
        users = [u for u in users if u.get("role") == PETUGAS_ROLE
                 and scope_mod.same_kecamatan(kec, u.get("wilayah"))]
    return [_serialize_user(u) for u in users]


@api_router.get("/admin/users/kelurahan")
async def admin_kelurahan_options(admin: dict = Depends(user_manager)):
    """Daftar kelurahan (per kecamatan) untuk formulir petugas; operator hanya kecamatannya."""
    kec = scope_mod.kecamatan_scope(admin) if _is_operator(admin) else None
    q = {"kecamatan": kec} if kec else {}
    docs = await db.kelurahan.find(q).sort("nama", 1).to_list(500)
    return [{"kecamatan": d.get("kecamatan"), "nama": d.get("nama")} for d in docs]


@api_router.post("/admin/users")
async def admin_create_user(inp: AdminCreateUser, admin: dict = Depends(user_manager)):
    email = inp.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    authmod.validate_password(inp.password)
    role = inp.role or PETUGAS_ROLE
    if role not in MANAGEABLE_ROLES:
        raise HTTPException(status_code=400, detail="Peran tidak valid")
    wilayah = (inp.wilayah or "").strip()
    doc = {
        "email": email, "password_hash": authmod.hash_password(inp.password),
        "name": inp.name.strip(), "role": role, "wilayah": wilayah,
        "status": "active", "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin.get("email"),
    }
    if _is_operator(admin):
        if role != PETUGAS_ROLE:
            raise HTTPException(status_code=403, detail="Operator hanya dapat membuat akun Petugas")
        doc["wilayah"] = scope_mod.kecamatan_scope(admin)  # kecamatan operator (dipaksa)
    elif role == PETUGAS_ROLE:
        raise HTTPException(status_code=403, detail="Akun Petugas hanya dapat dibuat oleh Operator kecamatan terkait")
    elif role in WILAYAH_REQUIRED_ROLES and not wilayah:
        raise HTTPException(status_code=422, detail="Wilayah (kecamatan) wajib diisi untuk peran ini")
    elif role == "verifikator" and not wilayah:
        doc["wilayah"] = "Kota Makassar"
    elif role in ("pimpinan", "superadmin", "ngo") and not wilayah:
        doc["wilayah"] = "Kota Makassar"

    if role == PETUGAS_ROLE:
        kel = (inp.kelurahan or "").strip()
        rw = _norm_rt_rw(inp.rw)
        if not kel or not rw:
            raise HTTPException(status_code=422, detail="Petugas wajib memiliki Kelurahan dan RW")
        if not await _kelurahan_valid(doc["wilayah"], kel):
            raise HTTPException(status_code=422, detail=f"Kelurahan '{kel}' tidak ada di Kecamatan {doc['wilayah']}")
        doc.update({"kelurahan": kel, "rw": rw, "rt": _rt_list(inp.rt),
                    "kode_kelurahan": await _kode_kelurahan_for(doc["wilayah"], kel)})
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    await inklusi_mod.audit(db, admin, "buat_user", "users", str(res.inserted_id),
                            {"email": email, "role": role, "wilayah": doc.get("wilayah"),
                             "kelurahan": doc.get("kelurahan"), "rw": doc.get("rw"), "rt": doc.get("rt")})
    return _serialize_user(doc)


@api_router.patch("/admin/users/{user_id}/status")
async def admin_set_status(user_id: str, inp: StatusUpdate, admin: dict = Depends(user_manager)):
    if inp.status not in ("active", "inactive", "pending"):
        raise HTTPException(status_code=400, detail="Status tidak valid")
    if str(admin["id"]) == user_id:
        raise HTTPException(status_code=400, detail="Tidak dapat mengubah status akun sendiri")
    await _target_in_scope(admin, user_id)
    res = await db.users.find_one_and_update(
        {"_id": _oid(user_id)}, {"$set": {"status": inp.status}}, return_document=True)
    await inklusi_mod.audit(db, admin, "ubah_status_user", "users", user_id, {"status": inp.status})
    if not res:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
    scope_mod.invalidate(user_id)
    return _serialize_user(res)


@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin: dict = Depends(user_manager)):
    if str(admin["id"]) == user_id:
        raise HTTPException(status_code=400, detail="Tidak dapat menghapus akun sendiri")
    await _target_in_scope(admin, user_id)
    res = await db.users.delete_one({"_id": _oid(user_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
    await inklusi_mod.audit(db, admin, "hapus_user", "users", user_id, None)
    scope_mod.invalidate(user_id)
    return {"message": "Pengguna dihapus"}


@api_router.patch("/admin/users/{user_id}")
async def admin_update_user(user_id: str, inp: AdminUpdateUser, admin: dict = Depends(user_manager)):
    target = await _target_in_scope(admin, user_id)
    updates = {}
    if inp.name is not None:
        updates["name"] = inp.name.strip()
    if inp.role is not None and inp.role != target.get("role"):
        if inp.role not in MANAGEABLE_ROLES:
            raise HTTPException(status_code=400, detail="Peran tidak valid")
        if _is_operator(admin):
            raise HTTPException(status_code=403, detail="Operator tidak dapat mengubah peran akun")
        if inp.role == PETUGAS_ROLE:
            raise HTTPException(status_code=403, detail="Peran Petugas hanya dapat ditetapkan oleh Operator kecamatan")
        if str(admin["id"]) == user_id and inp.role not in SUPERADMIN_ROLES:
            raise HTTPException(status_code=400, detail="Tidak dapat menurunkan peran akun sendiri")
        updates["role"] = inp.role
        await inklusi_mod.audit(db, admin, "ubah_peran_user", "users", user_id, {"role": inp.role})
    role_final = updates.get("role", target.get("role"))
    if inp.wilayah is not None:
        if _is_operator(admin):
            pass  # kecamatan petugas selalu kecamatan operator
        else:
            wil = inp.wilayah.strip()
            if role_final in WILAYAH_REQUIRED_ROLES and not wil:
                raise HTTPException(status_code=422, detail="Wilayah (kecamatan) wajib diisi untuk peran ini")
            updates["wilayah"] = wil or "Kota Makassar"
    if role_final == PETUGAS_ROLE:
        kec = scope_mod.kecamatan_scope(admin) if _is_operator(admin) else updates.get("wilayah", target.get("wilayah"))
        kel = inp.kelurahan.strip() if inp.kelurahan is not None else target.get("kelurahan", "")
        rw = _norm_rt_rw(inp.rw) if inp.rw is not None else target.get("rw", "")
        if inp.kelurahan is not None or inp.rw is not None or inp.rt is not None or "wilayah" in updates:
            if not kel or not rw:
                raise HTTPException(status_code=422, detail="Petugas wajib memiliki Kelurahan dan RW")
            if not await _kelurahan_valid(kec, kel):
                raise HTTPException(status_code=422, detail=f"Kelurahan '{kel}' tidak ada di Kecamatan {kec}")
            updates.update({"kelurahan": kel, "rw": rw,
                            "rt": _rt_list(inp.rt) if inp.rt is not None else (target.get("rt") or []),
                            "kode_kelurahan": await _kode_kelurahan_for(kec, kel)})
    if inp.email is not None:
        email = inp.email.lower()
        dup = await db.users.find_one({"email": email, "_id": {"$ne": _oid(user_id)}})
        if dup:
            raise HTTPException(status_code=400, detail="Email sudah digunakan pengguna lain")
        updates["email"] = email
    if not updates:
        raise HTTPException(status_code=400, detail="Tidak ada perubahan")
    res = await db.users.find_one_and_update(
        {"_id": _oid(user_id)}, {"$set": updates}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
    scope_mod.invalidate(user_id)
    return _serialize_user(res)


@api_router.post("/admin/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, inp: ResetPasswordInput, admin: dict = Depends(user_manager)):
    await _target_in_scope(admin, user_id)
    authmod.validate_password(inp.password)
    await db.users.update_one(
        {"_id": _oid(user_id)},
        {"$set": {"password_hash": authmod.hash_password(inp.password)}})
    await inklusi_mod.audit(db, admin, "reset_password_user", "users", user_id, None)
    return {"message": "Kata sandi berhasil diatur ulang"}


# ---------------- Data routes (publik untuk read) ----------------
def _oid(region_id: str) -> ObjectId:
    try:
        return ObjectId(region_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Kecamatan tidak ditemukan")


def _serialize_region(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc


@api_router.get("/regions")
async def get_regions(user: Optional[dict] = Depends(optional_user)):
    regions = await db.regions.find().to_list(100)
    regions = scope_mod.filter_docs(user, regions, "nama")
    return [_serialize_region(r) for r in regions]


@api_router.get("/regions/{region_id}")
async def get_region(region_id: str):
    r = await db.regions.find_one({"_id": _oid(region_id)})
    if not r:
        raise HTTPException(status_code=404, detail="Kecamatan tidak ditemukan")
    return _serialize_region(r)


def _clean_updates(inp):
    return {k: v for k, v in inp.model_dump().items() if v is not None}


async def _create_pending_change(target_type, target, changes, user):
    kec = target.get("nama") if target_type == "region" else target.get("kecamatan")
    before = {k: target.get(k) for k in changes}
    doc = {
        "id": str(uuid.uuid4()),
        "target_type": target_type,
        "target_id": str(target["_id"]),
        "target_nama": target.get("nama"),
        "kecamatan": kec,
        "changes": changes,
        "before": before,
        "status": "pending",
        "submitted_by": user["name"],
        "submitted_by_id": user["id"],
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
        "note": "",
    }
    await db.data_changes.insert_one(doc)
    return doc


@api_router.put("/regions/{region_id}")
async def update_region(region_id: str, inp: RegionUpdate, user: dict = Depends(current_user)):
    target = await db.regions.find_one({"_id": _oid(region_id)})
    if not target:
        raise HTTPException(status_code=404, detail="Kecamatan tidak ditemukan")
    role = user.get("role")
    if role in SUPERADMIN_ROLES:
        pass  # superadmin menerapkan langsung
    elif role in INPUT_ROLES:
        if (user.get("wilayah") or "").lower() != target.get("nama", "").lower():
            raise HTTPException(status_code=403, detail="Anda tidak berwenang mengubah data kecamatan ini")
    else:
        raise HTTPException(status_code=403, detail="Peran Anda tidak berwenang menginput data")
    updates = _clean_updates(inp)
    if not updates:
        raise HTTPException(status_code=400, detail="Tidak ada perubahan")
    if role in SUPERADMIN_ROLES:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        updates["updated_by"] = user["name"]
        res = await db.regions.find_one_and_update(
            {"_id": _oid(region_id)}, {"$set": updates}, return_document=True)
        return {"status": "applied", "region": _serialize_region(res)}
    change = await _create_pending_change("region", target, updates, user)
    return {"status": "pending",
            "message": "Perubahan dikirim untuk verifikasi. Data akan tampil setelah disetujui verifikator.",
            "change_id": change["id"]}


# ---------------- Kelurahan ----------------
def _serialize_kel(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc


@api_router.get("/kelurahan")
async def get_kelurahan(kecamatan: Optional[str] = None):
    q = {"kecamatan": kecamatan} if kecamatan else {}
    items = await db.kelurahan.find(q).sort("nama", 1).to_list(500)
    return [_serialize_kel(k) for k in items]


@api_router.get("/regions/{region_id}/kelurahan")
async def region_kelurahan(region_id: str):
    r = await db.regions.find_one({"_id": _oid(region_id)})
    if not r:
        raise HTTPException(status_code=404, detail="Kecamatan tidak ditemukan")
    items = await db.kelurahan.find({"kecamatan": r["nama"]}).sort("nama", 1).to_list(500)
    return [_serialize_kel(k) for k in items]


async def _recompute_region(kecamatan_nama: str, editor: str):
    kels = await db.kelurahan.find({"kecamatan": kecamatan_nama}).to_list(500)
    if not kels:
        return
    agg = {f: sum(int(k.get(f, 0)) for k in kels) for f in seed.CATEGORY_FIELDS}
    existing = await db.regions.find_one({"nama": kecamatan_nama})
    if existing:
        # Field yang sudah ditetapkan dari sumber resmi (mis. DINKES) tidak boleh
        # ditimpa oleh penjumlahan kelurahan yang mungkin belum lengkap.
        for f in seed.CATEGORY_FIELDS:
            if existing.get(f"{f}_otoritatif"):
                agg.pop(f, None)
    persens = [k.get("kemiskinan_persen") for k in kels if k.get("kemiskinan_persen") is not None]
    if persens:
        agg["kemiskinan_persen"] = round(sum(persens) / len(persens), 2)
    agg["updated_at"] = datetime.now(timezone.utc).isoformat()
    agg["updated_by"] = editor
    await db.regions.update_one({"nama": kecamatan_nama}, {"$set": agg})


@api_router.put("/kelurahan/{kel_id}")
async def update_kelurahan(kel_id: str, inp: KelurahanUpdate, user: dict = Depends(current_user)):
    target = await db.kelurahan.find_one({"_id": _oid(kel_id)})
    if not target:
        raise HTTPException(status_code=404, detail="Kelurahan tidak ditemukan")
    role = user.get("role")
    if role in SUPERADMIN_ROLES:
        pass
    elif role in INPUT_ROLES:
        if (user.get("wilayah") or "").lower() != target.get("kecamatan", "").lower():
            raise HTTPException(status_code=403, detail="Anda tidak berwenang mengubah data kelurahan ini")
    else:
        raise HTTPException(status_code=403, detail="Peran Anda tidak berwenang menginput data")
    updates = _clean_updates(inp)
    if not updates:
        raise HTTPException(status_code=400, detail="Tidak ada perubahan")
    if role in SUPERADMIN_ROLES:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        updates["updated_by"] = user["name"]
        res = await db.kelurahan.find_one_and_update(
            {"_id": _oid(kel_id)}, {"$set": updates}, return_document=True)
        await _recompute_region(target["kecamatan"], user["name"])
        return {"status": "applied", "kelurahan": _serialize_kel(res)}
    change = await _create_pending_change("kelurahan", target, updates, user)
    return {"status": "pending",
            "message": "Perubahan dikirim untuk verifikasi. Data akan tampil setelah disetujui verifikator.",
            "change_id": change["id"]}


# ---------------- Verifikasi Data ----------------
def _serialize_change(doc):
    doc.pop("_id", None)
    return doc


async def _apply_change(change):
    updates = dict(change["changes"])
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates["updated_by"] = change["submitted_by"]
    try:
        oid = ObjectId(change["target_id"])
    except Exception:
        return
    if change["target_type"] == "region":
        await db.regions.update_one({"_id": oid}, {"$set": updates})
    else:
        await db.kelurahan.update_one({"_id": oid}, {"$set": updates})
        await _recompute_region(change.get("kecamatan", ""), change["submitted_by"])


@api_router.get("/verifikasi")
async def list_changes(status: Optional[str] = None, user: dict = Depends(verifikator_user)):
    q = {"status": status} if status else {}
    items = await db.data_changes.find(q).sort("submitted_at", -1).to_list(300)
    items = scope_mod.filter_docs(user, items, "kecamatan")  # verifikator hanya kecamatannya
    return [_serialize_change(x) for x in items]


@api_router.get("/verifikasi/count")
async def count_pending_changes(user: dict = Depends(verifikator_user)):
    items = await db.data_changes.find({"status": "pending"}).to_list(1000)
    return {"pending": len(scope_mod.filter_docs(user, items, "kecamatan"))}


@api_router.post("/verifikasi/{change_id}/approve")
async def approve_change(change_id: str, user: dict = Depends(verifikator_user)):
    change = await db.data_changes.find_one({"id": change_id})
    if not change:
        raise HTTPException(status_code=404, detail="Usulan perubahan tidak ditemukan")
    scope_mod.pastikan_kecamatan(user, change.get("kecamatan"))
    if change["status"] != "pending":
        raise HTTPException(status_code=400, detail="Usulan sudah diproses")
    await _apply_change(change)
    await db.data_changes.update_one({"id": change_id}, {"$set": {
        "status": "approved", "reviewed_by": user["name"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }})
    return {"message": "Perubahan disetujui dan diterapkan"}


@api_router.post("/verifikasi/{change_id}/reject")
async def reject_change(change_id: str, inp: ReviewInput, user: dict = Depends(verifikator_user)):
    change = await db.data_changes.find_one({"id": change_id})
    if not change:
        raise HTTPException(status_code=404, detail="Usulan perubahan tidak ditemukan")
    scope_mod.pastikan_kecamatan(user, change.get("kecamatan"))
    if change["status"] != "pending":
        raise HTTPException(status_code=400, detail="Usulan sudah diproses")
    await db.data_changes.update_one({"id": change_id}, {"$set": {
        "status": "rejected", "reviewed_by": user["name"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(), "note": inp.note or "",
    }})
    return {"message": "Perubahan ditolak"}


@api_router.get("/stats/overview")
async def overview():
    regions = await db.regions.find().to_list(100)
    total_kk = sum(r.get("kemiskinan_ekstrim_kk", 0) for r in regions)
    total_stunting = sum(r.get("stunting_anak", 0) for r in regions)
    total_aj = sum(r.get("anak_jalanan", 0) for r in regions)
    total_ats = sum(r.get("ats", 0) for r in regions)
    total_dis = sum(r.get("disabilitas", 0) for r in regions)
    total_kelurahan = sum(r.get("kelurahan", 0) for r in regions)
    return {
        "jumlah_kecamatan": len(regions),
        "jumlah_kelurahan": total_kelurahan,
        "kemiskinan_ekstrim_kk": total_kk,
        "stunting_anak": total_stunting,
        "anak_jalanan": total_aj,
        "ats": total_ats,
        "disabilitas": total_dis,
        "kemiskinan_persen_terkini": seed.POVERTY_TREND[-1]["persen"],
        "penduduk_miskin_ribu": seed.POVERTY_TREND[-1]["penduduk_miskin_ribu"],
    }


@api_router.get("/trends/poverty")
async def poverty_trend():
    return {"tren": seed.POVERTY_TREND, "target": seed.POVERTY_TARGET}


@api_router.get("/trends/stunting")
async def stunting_trend():
    return {"tren": seed.STUNTING_TREND}


@api_router.get("/disability")
async def disability():
    return seed.DISABILITY


@api_router.get("/ats")
async def ats():
    return seed.ATS


@api_router.get("/pmks")
async def pmks():
    return {"data": seed.PMKS}


@api_router.get("/categories")
async def categories():
    return seed.CATEGORY_META


# ---------------- AI Analysis (Claude Sonnet 4.6) ----------------
CATEGORY_CONTEXT = {
    "kemiskinan": "kemiskinan dan kemiskinan ekstrim (jumlah KK miskin per kecamatan, persentase kemiskinan kota, target RPJMD)",
    "stunting": "stunting balita (EPPGBM, SSGI, keluarga berisiko, jumlah balita, intervensi)",
    "anak_jalanan": "anak jalanan dan PMKS (gelandangan, ODGJ, lansia terlantar, GEPENG)",
    "ats": "anak tidak sekolah (ATS jenjang SD & SMP, drop out, anak kembali ke sekolah)",
    "disabilitas": "penyandang disabilitas termasuk disabilitas buta (sensorik penglihatan) dan disabilitas tuli (sensorik pendengaran), tingkat pendidikan, status pekerjaan, dan kepemilikan NIK",
}


async def _build_data_summary(kategori: str, wilayah: Optional[str]):
    regions = await db.regions.find().to_list(100)
    meta = seed.CATEGORY_META.get(kategori, {})
    field = meta.get("field", "")
    rows = []
    for r in regions:
        if wilayah and r["nama"].lower() != wilayah.lower():
            continue
        rows.append(f"- {r['nama']}: {r.get(field, 0)} {meta.get('unit','')} ({r.get('kelurahan',0)} kelurahan)")
    summary = "\n".join(rows)
    extra = ""
    if kategori == "kemiskinan":
        extra = f"\nTarget RPJMD: {seed.POVERTY_TARGET}"
    elif kategori == "stunting":
        extra = f"\nTren stunting kota: {seed.STUNTING_TREND}"
    elif kategori == "disabilitas":
        extra = f"\nRagam disabilitas: {seed.DISABILITY['ragam']}\nPekerjaan: {seed.DISABILITY['pekerjaan_ringkas']}"
    elif kategori == "anak_jalanan":
        extra = f"\nData PMKS: {seed.PMKS}"
    elif kategori == "ats":
        extra = f"\nRingkasan ATS: {seed.ATS}"
    return summary + extra


@api_router.post("/ai/analyze")
async def ai_analyze(inp: AIAnalyzeInput):
    if inp.kategori not in CATEGORY_CONTEXT:
        raise HTTPException(status_code=400, detail="Kategori tidak dikenal")
    data_summary = await _build_data_summary(inp.kategori, inp.wilayah)
    fokus = f" khusus untuk Kecamatan {inp.wilayah}" if inp.wilayah else " untuk seluruh Kota Makassar"

    system_message = (
        "Anda adalah analis kebijakan senior di Badan Perencanaan Pembangunan Daerah (Bappeda) "
        "Kota Makassar. Anda memberikan rekomendasi program pemerintah yang tepat, konkret, "
        "berbasis data, dan sesuai konteks pemerintahan daerah Indonesia. Gunakan Bahasa Indonesia "
        "formal pemerintahan. Jawaban terstruktur dengan heading markdown, ringkas dan padat."
    )
    prompt = (
        f"Berikut data {CATEGORY_CONTEXT[inp.kategori]}{fokus}:\n\n{data_summary}\n\n"
        "Buatkan analisa dan rekomendasi program dengan struktur:\n"
        "## Ringkasan Situasi\n(2-3 kalimat kondisi berdasarkan data)\n\n"
        "## Wilayah Prioritas\n(sebutkan kecamatan yang paling perlu intervensi + alasan angka)\n\n"
        "## Rekomendasi Program Prioritas\n(3-4 program konkret: nama program, sasaran, OPD/dinas penanggung jawab)\n\n"
        "## Indikator Keberhasilan\n(indikator terukur untuk monitoring)\n\n"
        "PENTING: Jawaban ringkas dan padat, maksimal sekitar 450 kata."
    )

    if not llm_hostlinku.tersedia():
        raise HTTPException(status_code=503,
                            detail="HOSTLINKU_API_KEY belum dikonfigurasi di server")
    model_dipakai = llm_hostlinku.DEFAULT_MODEL

    async def _stream_teks():
        messages = [{"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}]
        async for delta in llm_hostlinku.stream_chat(messages):
            yield delta

    async def event_generator():
        chunks = []
        try:
            async for delta in _stream_teks():
                chunks.append(delta)
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        except Exception as e:
            logger.exception("AI analyze error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return
        full = "".join(chunks)
        try:
            await db.ai_analyses.insert_one({
                "id": str(uuid.uuid4()),
                "kategori": inp.kategori,
                "kategori_label": seed.CATEGORY_META.get(inp.kategori, {}).get("label", inp.kategori),
                "wilayah": inp.wilayah or "Kota Makassar",
                "hasil": full,
                "model": model_dipakai,
                "ringkasan": full[:180].replace("\n", " ").strip(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            logger.exception("Gagal menyimpan riwayat analisa AI")
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------- Riwayat Analisa AI ----------------
def _serialize_analysis(doc, include_full=False):
    out = {
        "id": doc.get("id") or str(doc.get("_id")),
        "kategori": doc.get("kategori"),
        "kategori_label": doc.get("kategori_label") or seed.CATEGORY_META.get(doc.get("kategori", ""), {}).get("label", doc.get("kategori")),
        "wilayah": doc.get("wilayah", "Kota Makassar"),
        "ringkasan": doc.get("ringkasan") or (doc.get("hasil", "")[:180]),
        "created_at": doc.get("created_at"),
    }
    if include_full:
        out["hasil"] = doc.get("hasil", "")
    return out


@api_router.get("/ai/history")
async def ai_history(kategori: Optional[str] = None, wilayah: Optional[str] = None, limit: int = 100):
    q = {}
    if kategori:
        q["kategori"] = kategori
    if wilayah:
        q["wilayah"] = wilayah
    items = await db.ai_analyses.find(q).sort("created_at", -1).to_list(min(limit, 300))
    return [_serialize_analysis(x) for x in items]


@api_router.get("/ai/history/{item_id}")
async def ai_history_detail(item_id: str):
    doc = await db.ai_analyses.find_one({"id": item_id})
    if not doc:
        try:
            doc = await db.ai_analyses.find_one({"_id": ObjectId(item_id)})
        except Exception:
            doc = None
    if not doc:
        raise HTTPException(status_code=404, detail="Riwayat analisa tidak ditemukan")
    return _serialize_analysis(doc, include_full=True)


@api_router.delete("/ai/history/{item_id}")
async def ai_history_delete(item_id: str, user: dict = Depends(current_user)):
    res = await db.ai_analyses.delete_one({"id": item_id})
    if res.deleted_count == 0:
        try:
            res = await db.ai_analyses.delete_one({"_id": ObjectId(item_id)})
        except Exception:
            pass
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Riwayat analisa tidak ditemukan")
    return {"message": "Riwayat analisa dihapus"}


# ---------------- Text-to-Speech (OpenAI TTS) untuk disabilitas buta ----------------
# Dibuat lazy agar kunci LLM yang belum diisi tidak menggagalkan import modul (startup kontainer).
_tts_engine = None


def _get_tts_engine():
    """TTS server (OpenAI via Emergent) sudah dilepas; Hostlinku belum menyediakan
    endpoint audio. Frontend otomatis beralih ke suara browser (speechSynthesis)
    saat endpoint ini menjawab 503."""
    raise HTTPException(
        status_code=503,
        detail="TTS server nonaktif - gunakan suara browser (speechSynthesis)")


def _clean_for_tts(text: str) -> str:
    import re
    try:
        import emoji
        text = emoji.replace_emoji(text, replace="")
    except Exception:
        pass
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"[*_#>~|]", "", text)
    # Ubah angka menjadi kata (terbilang) agar pembacaan jelas, mis. "13.334" -> "tiga belas ribu tiga ratus tiga puluh empat"
    try:
        import terbilang
        text = terbilang.expand_numbers(text)
    except Exception:
        logger.exception("Gagal ekspansi angka TTS")
    return re.sub(r"\s+", " ", text).strip()


# Model utama: gpt-4o-mini-tts (lafal Bahasa Indonesia paling jelas, bisa diarahkan lewat instruksi).
# Cadangan: tts-1-hd (kualitas tinggi) bila model utama gagal.
TTS_MODEL = "gpt-4o-mini-tts"
TTS_FALLBACK_MODEL = "tts-1-hd"
_TTS_TEMPO = {
    "normal": "Gunakan tempo bicara normal seperti penyiar berita, tidak terburu-buru dan tidak diperlambat.",
    "slow": "Gunakan tempo sedikit lebih pelan dari normal, tetap mengalir alami.",
    "slower": "Gunakan tempo pelan dan sabar, beri jeda lebih panjang antar kalimat.",
}
_TTS_SPEED = {"normal": 1.0, "slow": 0.85, "slower": 0.72}


def _tts_instruksi(kecepatan: str) -> str:
    return (
        "Anda adalah penyiar layanan publik Pemerintah Kota Makassar yang membacakan informasi untuk "
        "warga disabilitas buta. Bacakan dalam Bahasa Indonesia baku dengan lafal dan artikulasi yang sangat jelas, "
        "setiap suku kata terdengar utuh, intonasi ramah dan tenang. "
        + _TTS_TEMPO.get(kecepatan, _TTS_TEMPO["normal"])
        + " Beri jeda singkat pada koma dan jeda yang jelas pada titik. Ucapkan angka, persen, dan nama "
        "wilayah dengan tegas dan jelas. Jangan menambah atau mengubah kata."
    )


@api_router.post("/tts")
async def tts(inp: TTSInput):
    text = _clean_for_tts(inp.text)[:4000]
    if not text:
        raise HTTPException(status_code=400, detail="Teks kosong")
    kec = inp.kecepatan if inp.kecepatan in _TTS_TEMPO else "normal"
    voice = inp.voice or "alloy"
    key = hashlib.sha256(f"{text}|{voice}|{TTS_MODEL}|{kec}|v3|mp3".encode()).hexdigest()
    cached = await db.tts_cache.find_one({"_id": key})
    if cached:
        audio = cached["audio"]
    else:
        engine = _get_tts_engine()
        try:
            audio = await engine.generate_speech(text=text, model=TTS_MODEL, voice=voice,
                                                 speed=_TTS_SPEED.get(kec, 1.0),
                                                 instructions=_tts_instruksi(kec))
        except Exception:
            logger.exception("TTS %s gagal, mencoba %s", TTS_MODEL, TTS_FALLBACK_MODEL)
            try:
                audio = await engine.generate_speech(text=text, model=TTS_FALLBACK_MODEL, voice=voice,
                                                     speed=_TTS_SPEED.get(kec, 1.0))
            except Exception as e:
                logger.exception("TTS error")
                raise HTTPException(status_code=502, detail=f"Gagal membuat audio: {e}")
        await db.tts_cache.insert_one({"_id": key, "audio": audio,
                                       "created_at": datetime.now(timezone.utc).isoformat()})
    return StreamingResponse(io.BytesIO(audio), media_type="audio/mpeg",
                             headers={"Cache-Control": "public, max-age=31536000"})


# ---------------- Laporan PDF resmi Bappeda ----------------
@api_router.post("/report/ai")
async def report_ai(inp: AIReportInput):
    if not inp.hasil.strip():
        raise HTTPException(status_code=400, detail="Tidak ada isi laporan")
    label = seed.CATEGORY_META.get(inp.kategori, {}).get("label", inp.kategori)
    wilayah = inp.wilayah or "Kota Makassar"
    pdf = report_mod.build_ai_report(label, wilayah, inp.hasil)
    fname = f"Laporan_Analisa_{inp.kategori}_{wilayah}".replace(" ", "_") + ".pdf"
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@api_router.get("/report/dashboard")
async def report_dashboard():
    ov = await overview()
    regions = await db.regions.find().to_list(100)
    regions = [_serialize_region(r) for r in regions]
    pdf = report_mod.build_dashboard_report(
        ov, regions,
        {"tren": seed.POVERTY_TREND, "target": seed.POVERTY_TARGET},
        seed.STUNTING_TREND, seed.PMKS, seed.DISABILITY,
    )
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": 'attachment; filename="Ringkasan_Dashboard_Bappeda_Makassar.pdf"'})


@api_router.get("/export/excel")
async def export_excel(user: dict = Depends(current_user)):
    regions = await db.regions.find().to_list(100)
    kelurahan = await db.kelurahan.find().to_list(1000)
    regions = [_serialize_region(r) for r in regions]
    kelurahan = [_serialize_kel(k) for k in kelurahan]
    data = excel_mod.build_data_excel(regions, kelurahan)
    await inklusi_mod.audit(db, user, "export_excel", "regions+kelurahan", "",
                            {"kecamatan": len(regions), "kelurahan": len(kelurahan)})
    fname = "Data_Sosial_Kota_Makassar.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@api_router.get("/admin/pending-count")
async def admin_pending_count(admin: dict = Depends(user_manager)):
    docs = await db.users.find({"status": "pending"}).to_list(1000)
    if _is_operator(admin):
        kec = scope_mod.kecamatan_scope(admin)
        docs = [u for u in docs if u.get("role") == PETUGAS_ROLE and scope_mod.same_kecamatan(kec, u.get("wilayah"))]
    return {"pending": len(docs)}


@api_router.get("/")
async def root():
    return {"message": "Sistem Intelijen Data Bappeda Kota Makassar - API aktif"}


@api_router.get("/health")
async def health():
    """Healthcheck untuk Coolify / Docker: memastikan MariaDB terjangkau."""
    info = db.info_koneksi()
    try:
        await db.ping()
        return {
            "status": "ok",
            "database": "mariadb",
            "koneksi": info,
            "catatan": (
                f"Variabel {', '.join(info['env_warisan_diabaikan'])} diabaikan (sisa template "
                "MongoDB); aman dihapus dari environment."
                if info.get("env_warisan_diabaikan") else None),
        }
    except Exception as e:
        logger.exception("Healthcheck gagal")
        raise HTTPException(
            status_code=503,
            detail={
                "pesan": f"Database tidak siap: {e}",
                "koneksi": info,
                "petunjuk": db.diagnosa_error(e),
            })

# Modul PETA / data rumah (GIS level bangunan)
api_router.include_router(rumah_mod.build_router(db, current_user, editor_user, admin_user))

# Modul data sosial DTSEN, disabilitas, stunting, RAD, GIS choropleth, audit data
api_router.include_router(sosial_mod.build_router(db, current_user, editor_user, admin_user))

# Modul AI Assistant data-aware (menjawab dari basis data)
api_router.include_router(ai_assistant_mod.build_router(db, current_user, editor_user, admin_user))

# Modul PETA DASAR (layer dasar Kota Makassar dari PETA_DASAR.gdb)
api_router.include_router(peta_dasar_mod.build_router(db, current_user, editor_user, admin_user))

# Modul IMPORT WIZARD (unggah Excel/CSV -> mapping -> validasi -> preview -> impor)
api_router.include_router(import_wizard_mod.build_router(db, current_user, writer_user, admin_user))
api_router.include_router(inklusi_mod.build_router(db, current_user, writer_user, admin_user))
api_router.include_router(inklusi_extra_mod.build_router(db, current_user, writer_user, admin_user))
api_router.include_router(inklusi_cerita_mod.build_router(db, current_user, writer_user, admin_user))

# Modul MATRIKS (evaluasi OPPKPKE, kategori kemiskinan/stunting/ATS/anak jalanan,
# program kegiatan ATS, template & impor Excel)
api_router.include_router(matriks_mod.build_router(db, current_user, writer_user))
api_router.include_router(musrenbang_mod.build_router(db, current_user))

# Modul PENGELOLAAN DATA (input manual, ubah, hapus, master kode, koordinat GIS)
api_router.include_router(data_manage_mod.build_router(db, current_user, editor_user, admin_user))

api_router.include_router(ringkasan_mod.build_router(db, current_user))

# Modul GEOTAG-VERVAL DTSEN (khusus Operator RT/RW + pemeriksa verifikator/admin_bappeda)
api_router.include_router(verval_mod.build_router(db, current_user))
app.include_router(api_router)


@app.exception_handler(DuplicateKeyError)
async def _duplicate_key_handler(request: Request, exc: DuplicateKeyError):
    return JSONResponse(status_code=400, content={"detail": "Data sudah ada (duplikat)"})

# Scoping wilayah: paksa filter kecamatan pada query GET /api/* untuk operator/verifikator/petugas
app.add_middleware(scope_mod.WilayahScopeMiddleware, db=db, jwt_secret_getter=authmod.get_jwt_secret)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)


def _asal_diizinkan(request: Request) -> bool:
    """Cek Origin/Referer untuk mencegah CSRF pada permintaan yang mengubah data."""
    origin = (request.headers.get("origin") or "").strip()
    host = (request.headers.get("host") or "").strip()
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip() \
        or request.url.scheme
    diizinkan = set(CORS_ORIGINS)
    if host:
        diizinkan.add(f"{proto}://{host}")
    if origin:
        return origin in diizinkan
    referer = (request.headers.get("referer") or "").strip()
    if referer:
        return any(referer == a or referer.startswith(a + "/") for a in diizinkan)
    # Klien non-browser (cURL/server) tidak mengirim Origin/Referer.
    return True


@app.middleware("http")
async def middleware_keamanan(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} \
            and request.url.path.startswith("/api/"):
        if not _asal_diizinkan(request):
            return JSONResponse(status_code=403,
                                content={"detail": "Permintaan lintas situs ditolak"})

    response = await call_next(request)
    for nama, nilai in HEADER_KEAMANAN.items():
        response.headers.setdefault(nama, nilai)
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip() \
        or request.url.scheme
    if proto == "https":
        response.headers.setdefault("Strict-Transport-Security",
                                    "max-age=31536000; includeSubDomains")
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers.setdefault("Content-Security-Policy", CSP)
    if any(request.url.path.startswith(p) for p in NO_STORE_PREFIX):
        response.headers["Cache-Control"] = "no-store"
    if "server" in response.headers:
        del response.headers["server"]
    return response


@app.on_event("startup")
async def startup():
    # Tunggu database siap (mis. MariaDB baru start di container preview)
    import asyncio
    last_err = None
    for attempt in range(1, 11):
        try:
            await db.connect()
            await db.ping()
            last_err = None
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("Database belum siap (percobaan %d/10): %s", attempt, e)
            try:
                await db.close()
            except Exception:
                pass
            await asyncio.sleep(3)
    if last_err is not None:
        raise last_err
    await db.users.create_index("email", unique=True)
    await authmod.seed_admin(db)
    # Seed regions (idempotent)
    if await db.regions.count_documents({}) == 0:
        docs = []
        for r in seed.REGIONS:
            d = dict(r)
            d["created_at"] = datetime.now(timezone.utc).isoformat()
            docs.append(d)
        await db.regions.insert_many(docs)
        logger.info("Seeded %d kecamatan", len(docs))
    # Seed kelurahan (idempotent)
    if await db.kelurahan.count_documents({}) == 0:
        kdocs = seed.build_kelurahan_docs()
        for d in kdocs:
            d["created_at"] = datetime.now(timezone.utc).isoformat()
        if kdocs:
            await db.kelurahan.insert_many(kdocs)
            logger.info("Seeded %d kelurahan", len(kdocs))
    # Seed matriks resmi non-pribadi (snapshot) bila koleksi masih kosong.
    try:
        import snapshot_data_resmi as snapshot_mod
        hasil = await snapshot_mod.muat_matriks(db)
        if any(hasil.values()):
            logger.info("Seed matriks resmi: %s", hasil)
    except Exception as e:  # noqa: BLE001
        logger.warning("Seed matriks resmi dilewati: %s", e)
    # Seed Musrenbang Tematik (snapshot non-pribadi) bila koleksi masih kosong.
    try:
        hasil_musrenbang = await musrenbang_mod.muat_snapshot(db)
        if any(hasil_musrenbang.values()):
            logger.info("Seed Musrenbang Tematik: %s", hasil_musrenbang)
    except Exception as e:  # noqa: BLE001
        logger.warning("Seed Musrenbang dilewati: %s", e)
    # Seed data rumah (polygon bangunan) + konfigurasi peta (idempotent)
    seeded_rumah = await rumah_mod.seed_rumah(db)
    if seeded_rumah:
        logger.info("Seeded %d polygon rumah", seeded_rumah)
    await rumah_mod.seed_map_config(db)
    # Seed ringkasan layer peta dasar + fasilitas umum/toponimi (idempotent)
    try:
        seeded_geo = await peta_dasar_mod.seed_peta_dasar(db)
        if any(seeded_geo.values()):
            logger.info("Seeded peta dasar: %s", seeded_geo)
    except Exception as e:  # noqa: BLE001
        logger.warning("Seed peta dasar dilewati: %s", e)
    # GeoTag-Verval: referensi DTSEN stabil (latar belakang) + cek penyimpanan foto
    try:
        await verval_mod.startup(db, logger)
    except Exception as e:  # noqa: BLE001
        logger.warning("Startup Verval dilewati: %s", type(e).__name__)
    # Kirim email notifikasi yang tertunda (mis. SMTP baru dikonfigurasi)
    try:
        res = await notifier.flush_pending(db)
        if res.get("diproses"):
            logger.info("Email tertunda diproses: %s", res)
    except Exception as e:  # noqa: BLE001
        logger.warning("Flush email tertunda gagal: %s", e)


@app.on_event("shutdown")
async def shutdown_db_client():
    await db.close()


# ---------------- Penyajian frontend (build React) untuk deployment 1 kontainer ----------------
class SPAStaticFiles(StaticFiles):
    """StaticFiles dengan fallback ke index.html agar rute React Router tetap jalan."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except Exception:
            index = Path(self.directory) / "index.html"
            if index.is_file():
                return FileResponse(index)
            raise


FRONTEND_BUILD_DIR = Path(
    os.environ.get("FRONTEND_BUILD_DIR", str(ROOT_DIR.parent / "frontend" / "build")))

if (FRONTEND_BUILD_DIR / "index.html").is_file():
    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_BUILD_DIR), html=True), name="frontend")
    logger.info("Menyajikan frontend statis dari %s", FRONTEND_BUILD_DIR)
else:
    logger.info("Build frontend tidak ditemukan di %s - mode API saja", FRONTEND_BUILD_DIR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT") or 8000),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
