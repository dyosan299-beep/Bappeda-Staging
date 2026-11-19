"""Uji kontrol keamanan PETA INKLUSI terhadap server yang berjalan.

    python uji_keamanan.py --base http://127.0.0.1:8001

Memeriksa:
- header keamanan & CSP pada halaman HTML,
- endpoint data pribadi menolak pengguna anonim,
- ekspor Excel wajib login,
- proteksi CSRF (Origin lintas situs ditolak),
- pembatasan percobaan login (429 setelah batas),
- kebijakan kata sandi,
- endpoint publik tidak memuat kunci data pribadi,
- CORS tidak membuka wildcard untuk origin asing.

Skrip membuat satu kunci `login_attempts` sementara lalu menghapusnya.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv(".env")
from mariadb_store import MariaDocStore  # noqa: E402

gagal: list[str] = []


def cek(nama: str, lulus: bool, info: str = "") -> None:
    print(f"{'PASS' if lulus else 'FAIL'}  {nama}" + (f"  [{info}]" if info else ""))
    if not lulus:
        gagal.append(nama)


async def bersihkan(email: str) -> None:
    try:
        db = MariaDocStore.from_env()
        await db.login_attempts.delete_many({"key": {"$regex": re.escape(email)}})
        await db.close()
    except Exception as e:  # noqa: BLE001
        print(f"  (catatan) pembersihan login_attempts gagal: {type(e).__name__}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8001")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    c = httpx.Client(base_url=base, timeout=30.0)
    email = f"uji.keamanan.{int(time.time())}@example.com"
    sandi_salah = "SalahSekali2026"

    # 1. Header keamanan pada respons API
    r = c.get("/api/auth/me")
    cek("auth/me menolak anonim", r.status_code == 401, str(r.status_code))
    wajib = {"x-content-type-options": "nosniff", "x-frame-options": "SAMEORIGIN"}
    for k, v in wajib.items():
        cek(f"header {k}", (r.headers.get(k) or "") == v, r.headers.get(k) or "tidak ada")
    cek("header referrer-policy", bool(r.headers.get("referrer-policy")),
        r.headers.get("referrer-policy") or "tidak ada")
    cek("header permissions-policy", bool(r.headers.get("permissions-policy")),
        r.headers.get("permissions-policy") or "tidak ada")
    cek("auth/me cache-control no-store",
        "no-store" in (r.headers.get("cache-control") or ""), r.headers.get("cache-control") or "-")

    # 2. Data pribadi & ekspor wajib login
    cek("sosial/households menolak anonim",
        c.get("/api/sosial/households").status_code == 401)
    cek("inklusi/stunting/children menolak anonim",
        c.get("/api/inklusi/stunting/children").status_code == 401)
    cek("export/excel menolak anonim",
        c.get("/api/export/excel").status_code == 401)

    # 3. CSRF: Origin asing ditolak, origin sendiri diizinkan
    evil = c.post("/api/auth/login", json={"email": email, "password": sandi_salah},
                  headers={"Origin": "https://jahat.example"})
    cek("login dari origin asing ditolak (CSRF)", evil.status_code == 403, str(evil.status_code))
    sah = c.post("/api/auth/login", json={"email": email, "password": sandi_salah},
                 headers={"Origin": "http://localhost:3000"})
    cek("login dari origin aplikasi diproses", sah.status_code == 401, str(sah.status_code))

    # 4. Rate limit (LOGIN_MAX_ATTEMPTS default 5)
    status = [sah.status_code]
    for _ in range(5):
        r = c.post("/api/auth/login", json={"email": email, "password": sandi_salah},
                   headers={"Origin": "http://localhost:3000"})
        status.append(r.status_code)
    cek("brute force dibatasi (429)", status[-1] == 429, str(status))

    # 5. Kebijakan kata sandi
    pendek = c.post("/api/auth/register",
                    json={"email": f"pendek.{int(time.time())}@example.com",
                          "password": "Pendek1", "name": "Uji"})
    cek("kata sandi < 10 karakter ditolak", pendek.status_code == 422, str(pendek.status_code))
    lemah = c.post("/api/auth/register",
                   json={"email": f"lemah.{int(time.time())}@example.com",
                         "password": "abcdefghij", "name": "Uji"})
    cek("kata sandi tanpa angka ditolak", lemah.status_code == 422, str(lemah.status_code))

    # 6. Endpoint publik tidak memuat kunci data pribadi
    pub = c.get("/api/public/summary")
    teks = pub.text.lower()
    bocor = [k for k in ("no_kk", "nama_ortu", "nik", "tgl_lahir", "alamat") if f'"{k}"' in teks]
    cek("public/summary tanpa kunci data pribadi", pub.status_code == 200 and not bocor,
        ", ".join(bocor) or "bersih")

    # 7. CORS tidak wildcard untuk origin asing
    asing = c.get("/api/regions", headers={"Origin": "https://jahat.example"})
    cek("CORS origin asing tanpa izin", not asing.headers.get("access-control-allow-origin"),
        asing.headers.get("access-control-allow-origin") or "tidak ada")
    lokal = c.get("/api/regions", headers={"Origin": "http://localhost:3000"})
    cek("CORS origin aplikasi diizinkan",
        lokal.headers.get("access-control-allow-origin") == "http://localhost:3000",
        lokal.headers.get("access-control-allow-origin") or "tidak ada")

    # 8. CSP pada halaman HTML (bila build frontend tersedia)
    html = c.get("/")
    if "text/html" in (html.headers.get("content-type") or ""):
        cek("CSP halaman HTML", "default-src" in (html.headers.get("content-security-policy") or ""),
            (html.headers.get("content-security-policy") or "tidak ada")[:50])
    else:
        print("  (catatan) build frontend tidak tersedia; CSP HTML tidak diuji")

    asyncio.run(bersihkan(email))
    print("\n" + ("LULUS" if not gagal else f"GAGAL: {', '.join(gagal)}"))
    return 0 if not gagal else 1


if __name__ == "__main__":
    sys.exit(main())
