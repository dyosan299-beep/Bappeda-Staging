"""Autentikasi JWT (email + password) untuk Bappeda Kota Makassar."""
import os
import re
import uuid
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request
from bsonlite import ObjectId

JWT_ALGORITHM = "HS256"
PASSWORD_MIN = max(10, int(os.environ.get("PASSWORD_MIN_LENGTH", "10") or 10))

# Hash tiruan untuk menyamakan waktu respons saat email tidak ditemukan,
# sehingga penyerang tidak bisa menebak akun dari selisih waktu (user enumeration).
DUMMY_HASH = bcrypt.hashpw(b"dummy-password-tidak-dipakai", bcrypt.gensalt(rounds=10)).decode()

_KATA_SANDI_UMUM = {
    "password", "password123", "password2026", "12345678", "123456789", "1234567890",
    "qwerty123", "admin123", "admin12345", "makassar", "makassar123", "bappeda",
    "bappeda123", "petaiklusi", "petainklusi", "indonesia", "rahasia123", "welcome123",
}


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def validate_password(password: str) -> str:
    """Kebijakan kata sandi minimum (UU PDP ps. 35 & praktik BSSN/ISO 27001)."""
    pw = str(password or "")
    if len(pw) < PASSWORD_MIN:
        raise HTTPException(status_code=422, detail=f"Kata sandi minimal {PASSWORD_MIN} karakter")
    if len(pw) > 128:
        raise HTTPException(status_code=422, detail="Kata sandi maksimal 128 karakter")
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        raise HTTPException(status_code=422, detail="Kata sandi harus memuat huruf dan angka")
    if pw.strip().lower() in _KATA_SANDI_UMUM:
        raise HTTPException(status_code=422, detail="Kata sandi terlalu umum; gunakan kombinasi lain")
    return pw


def create_access_token(user_id: str, email: str, role: str) -> str:
    jam = max(1, int(os.environ.get("ACCESS_TOKEN_HOURS", "8") or 8))
    sekarang = datetime.now(timezone.utc)
    payload = {
        "sub": user_id, "email": email, "role": role,
        "iat": sekarang, "jti": str(uuid.uuid4()),
        "exp": sekarang + timedelta(hours=jam), "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def _extract_token(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    return token


async def get_current_user(request: Request, db) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Belum terautentikasi")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM],
                             options={"require": ["exp", "sub", "type"]})
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Tipe token tidak valid")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Pengguna tidak ditemukan")
        user["id"] = str(user["_id"])
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token kedaluwarsa")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token tidak valid")


async def seed_admin(db):
    """Seed/perbarui akun superadmin dari env (idempotent).

    Keamanan: TIDAK ada password default di kode. Bila ADMIN_PASSWORD kosong,
    akun admin tidak dibuat dan password akun yang sudah ada tidak diubah.
    Akun contoh per peran hanya di-seed bila SEED_DEMO_USERS=true
    (khusus lingkungan pengembangan/preview) dan password-nya diambil dari env.
    """
    import logging
    log = logging.getLogger("bappeda.auth")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@bappeda.makassarkota.go.id").lower()
    admin_password = (os.environ.get("ADMIN_PASSWORD") or "").strip()
    existing = await db.users.find_one({"email": admin_email})
    if not admin_password:
        log.warning("ADMIN_PASSWORD tidak diatur - seed/sinkronisasi password superadmin dilewati")
    if existing is None:
        if admin_password:
            await db.users.insert_one({
                "email": admin_email, "password_hash": hash_password(admin_password),
                "name": "Super Admin Bappeda", "role": "superadmin", "wilayah": "Kota Makassar",
                "status": "active", "created_at": datetime.now(timezone.utc).isoformat(),
            })
    else:
        upd = {}
        if admin_password and not verify_password(admin_password, existing["password_hash"]):
            upd["password_hash"] = hash_password(admin_password)
        if existing.get("status") != "active":
            upd["status"] = "active"
        if existing.get("role") in (None, "admin"):
            upd["role"] = "superadmin"
        if upd:
            await db.users.update_one({"email": admin_email}, {"$set": upd})

    # Migrasi: semua role lama "admin" menjadi "superadmin"
    await db.users.update_many({"role": "admin"}, {"$set": {"role": "superadmin"}})

    # Seed contoh akun tiap peran (idempotent) - HANYA bila SEED_DEMO_USERS=true
    if (os.environ.get("SEED_DEMO_USERS") or "").strip().lower() in ("1", "true", "yes"):
        samples = [
            ("petugas.tallo@makassarkota.go.id", "DEMO_PETUGAS_PASSWORD", "Petugas Kecamatan Tallo", "petugas", "Tallo"),
            ("operator.rappocini@makassarkota.go.id", "DEMO_OPERATOR_PASSWORD", "Operator Kecamatan Rappocini", "operator", "Rappocini"),
            ("verifikator@bappeda.makassarkota.go.id", "DEMO_VERIFIKATOR_PASSWORD", "Verifikator Data Bappeda", "verifikator", "Kota Makassar"),
        ]
        for email, pw_env, name, role, wilayah in samples:
            pw = (os.environ.get(pw_env) or "").strip()
            doc = await db.users.find_one({"email": email})
            if doc is None:
                if not pw:
                    continue
                await db.users.insert_one({
                    "email": email, "password_hash": hash_password(pw),
                    "name": name, "role": role, "wilayah": wilayah,
                    "status": "active", "created_at": datetime.now(timezone.utc).isoformat(),
                })
            elif doc.get("status") != "active":
                await db.users.update_one({"email": email}, {"$set": {"status": "active"}})

    # Pastikan semua user lama punya field status
    await db.users.update_many({"status": {"$exists": False}}, {"$set": {"status": "active"}})
