"""Pembatasan wilayah (scoping) per peran.

Aturan:
- superadmin/admin/pimpinan/admin_opd/viewer : seluruh Kota Makassar.
- operator & verifikator                      : hanya KECAMATAN pada field `wilayah`
                                                (kosong / "Kota Makassar" = seluruh kota, hanya
                                                untuk akun lama / verifikator kota).
- petugas                                     : KECAMATAN (`wilayah`) + KELURAHAN + RW/RT
                                                (lihat verval.py: penugasan dari profil).

Modul ini juga menyediakan middleware ASGI yang MEMAKSA parameter query
`kecamatan`, `kode_kecamatan`, dan `wilayah` pada seluruh request GET /api/*
untuk pengguna ter-scope, sehingga endpoint daftar/rekap yang memakai filter
tersebut otomatis hanya mengembalikan data kecamatan pengguna.
"""
from __future__ import annotations

import re
import time
import unicodedata
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode

import jwt

SCOPED_ROLES = ("operator", "verifikator", "petugas", "operator_kecamatan", "operator_kelurahan")
CITY_WIDE_VALUES = ("", "kota makassar", "semua", "seluruh kota makassar")

# Nama parameter query yang dipaksa untuk pengguna ter-scope
PARAM_NAMA = ("kecamatan", "wilayah")
PARAM_KODE = ("kode_kecamatan",)


def norm(value: Any) -> str:
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return re.sub(r"^(kec|kecamatan|kel|kelurahan)\s+", "", s)


def kecamatan_scope(user: Optional[dict]) -> Optional[str]:
    """Nama kecamatan yang membatasi pengguna, atau None bila seluruh kota."""
    if not user:
        return None
    if (user.get("role") or "") not in SCOPED_ROLES:
        return None
    wil = (user.get("wilayah") or "").strip()
    if wil.lower() in CITY_WIDE_VALUES:
        return None
    return wil


def same_kecamatan(scope: Optional[str], nama: Any) -> bool:
    """True bila tidak ada pembatasan atau nama kecamatan sama (abaikan huruf besar/kecil)."""
    if not scope:
        return True
    return norm(scope) == norm(nama)


def pastikan_kecamatan(user: dict, nama: Any, pesan: str = "") -> None:
    from fastapi import HTTPException
    sc = kecamatan_scope(user)
    if sc and not same_kecamatan(sc, nama):
        raise HTTPException(status_code=403, detail=pesan or f"Anda hanya berwenang atas Kecamatan {sc}")


def filter_docs(user: Optional[dict], docs, field: str = "kecamatan"):
    """Saring list dokumen berdasarkan kecamatan pengguna (tanpa pembatasan -> apa adanya)."""
    sc = kecamatan_scope(user)
    if not sc:
        return docs
    return [d for d in docs if same_kecamatan(sc, (d or {}).get(field))]


# cache uid -> (waktu, kecamatan, kode_kecamatan); dibersihkan saat akun diubah
_CACHE: Dict[str, Tuple[float, Optional[str], Optional[str]]] = {}


def invalidate(uid: Optional[str] = None) -> None:
    if uid:
        _CACHE.pop(str(uid), None)
    else:
        _CACHE.clear()


class WilayahScopeMiddleware:
    """Middleware ASGI murni: paksa filter kecamatan pada query string GET /api/* untuk
    pengguna ter-scope. Pengguna/peran lain tidak tersentuh."""

    def __init__(self, app, db, jwt_secret_getter, ttl: int = 60):
        self.app = app
        self.db = db
        self.secret = jwt_secret_getter
        self.ttl = ttl

    async def _resolve(self, uid: str) -> Tuple[Optional[str], Optional[str]]:
        hit = _CACHE.get(uid)
        now = time.time()
        if hit and now - hit[0] < self.ttl:
            return hit[1], hit[2]
        kec: Optional[str] = None
        kode: Optional[str] = None
        try:
            from bsonlite import ObjectId
            u = await self.db.users.find_one({"_id": ObjectId(uid)})
            kec = kecamatan_scope(u) if u else None
            if kec:
                kode = await kode_kecamatan(self.db, kec)
        except Exception:  # noqa: BLE001
            kec, kode = None, None
        _CACHE[uid] = (now, kec, kode)
        return kec, kode

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") != "GET" \
                or not scope.get("path", "").startswith("/api/"):
            return await self.app(scope, receive, send)
        token = _token_from_scope(scope)
        if not token:
            return await self.app(scope, receive, send)
        try:
            payload = jwt.decode(token, self.secret(), algorithms=["HS256"])
        except jwt.PyJWTError:
            return await self.app(scope, receive, send)
        if payload.get("type") != "access" or payload.get("role") not in SCOPED_ROLES:
            return await self.app(scope, receive, send)
        kec, kode = await self._resolve(str(payload.get("sub")))
        if not kec:
            return await self.app(scope, receive, send)
        qs = [(k, v) for k, v in parse_qsl(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True)
              if k not in PARAM_NAMA + PARAM_KODE]
        qs += [(k, kec) for k in PARAM_NAMA]
        if kode:
            qs += [(k, kode) for k in PARAM_KODE]
        scope = dict(scope)
        scope["query_string"] = urlencode(qs).encode("latin-1")
        return await self.app(scope, receive, send)


def _token_from_scope(scope) -> Optional[str]:
    cookie_hdr = ""
    auth_hdr = ""
    for k, v in scope.get("headers") or []:
        if k == b"cookie":
            cookie_hdr = v.decode("latin-1")
        elif k == b"authorization":
            auth_hdr = v.decode("latin-1")
    m = re.search(r"(?:^|;\s*)access_token=([^;]+)", cookie_hdr)
    if m:
        return m.group(1)
    if auth_hdr.startswith("Bearer "):
        return auth_hdr[7:]
    return None


async def kode_kecamatan(db, nama: str) -> Optional[str]:
    """Cari kode kecamatan (BPS) dari data yang pernah diimpor; None bila belum ada."""
    pola = {"$regex": f"^\\s*{re.escape(str(nama).strip())}\\s*$", "$options": "i"}
    for coll in ("district_stats", "village_stats", "households"):
        try:
            d = await getattr(db, coll).find_one({"kecamatan": pola, "kode_kecamatan": {"$exists": True}})
        except Exception:  # noqa: BLE001
            continue
        if d and d.get("kode_kecamatan"):
            return str(d["kode_kecamatan"])
    return None
