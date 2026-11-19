"""Referensi stabil DTSEN untuk modul GeoTag-Verval.

Latar belakang (hasil audit):
- `households.id` adalah UUID yang DIBUAT ULANG setiap ETL `--reset`, sehingga tidak
  boleh dipakai sebagai satu-satunya relasi permanen.
- Aturan deduplikasi yang sudah dipakai ETL (`etl_import.py`) dan Import Wizard
  (`import_wizard.dedupe_key`) adalah `nomor_kartu_keluarga + kode_kelurahan`
  (Import Wizard: bila kode kosong dipakai nama kelurahan ternormalisasi).

Referensi stabil (`dtsen_ref`) = HMAC-SHA256(VERVAL_REF_SECRET, "<no_kk>|<wilayah>").
- Deterministik: rumah tangga yang sama menghasilkan ref yang sama setelah ETL reset.
- No. KK TIDAK tersimpan/terbaca dari ref (tidak dapat dibalik tanpa rahasia),
  sehingga ref aman dipakai di URL, log, dan relasi antar-tabel.
- Bila VERVAL_REF_SECRET diganti, seluruh ref berubah -> JANGAN diganti di produksi
  tanpa migrasi (lihat DEPLOY_COOLIFY.md bagian GeoTag-Verval).

RT/RW HANYA diambil dari kolom eksplisit berkas sumber (tidak pernah disimpulkan dari
teks alamat).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import unicodedata
from typing import Any, Optional

REF_PREFIX = "DR-"


def _norm_name(value: Any) -> str:
    s = str(value or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9' -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ref_secret() -> str:
    return (os.environ.get("VERVAL_REF_SECRET") or "").strip()


def kk_digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def wil_key(kode_kelurahan: Any, kelurahan: Any = "") -> str:
    kode = str(kode_kelurahan or "").strip()
    return kode if kode else "NAMA:" + _norm_name(kelurahan)


def make_ref(no_kk: Any, kode_kelurahan: Any, kelurahan: Any = "") -> Optional[str]:
    """Ref stabil; None bila rahasia belum dikonfigurasi atau No. KK kosong."""
    secret = ref_secret()
    kk = kk_digits(no_kk)
    if not secret or not kk:
        return None
    msg = f"{kk}|{wil_key(kode_kelurahan, kelurahan)}".encode()
    return REF_PREFIX + hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()[:40]


def ref_for_household(doc: dict) -> Optional[str]:
    return make_ref(doc.get("no_kk"), doc.get("kode_kelurahan"), doc.get("kelurahan"))


def norm_rt_rw(value: Any) -> str:
    """'001' -> '1', 'RW 02' -> '2', kosong -> ''. Hanya untuk kolom RT/RW eksplisit."""
    s = re.sub(r"\D", "", str(value or ""))
    return str(int(s)) if s else ""


def valid_ref(value: Any) -> bool:
    return bool(re.fullmatch(r"DR-[0-9a-f]{40}", str(value or "")))


async def backfill_refs(db, logger=None) -> int:
    """Isi `dtsen_ref` pada households yang belum punya (non-destruktif, idempoten)."""
    if not ref_secret():
        return 0
    n = 0
    while True:
        docs = await db.households.find({"dtsen_ref": {"$exists": False}}).limit(1000).to_list(1000)
        if not docs:
            break
        progressed = 0
        for d in docs:
            ref = ref_for_household(d)
            # ref None (KK kosong) -> tandai string kosong agar tidak diproses ulang
            await db.households.update_one({"id": d.get("id")}, {"$set": {"dtsen_ref": ref or ""}})
            n += 1
            progressed += 1
        if not progressed:
            break
    if logger and n:
        logger.info("Referensi DTSEN stabil diisi untuk %d rumah tangga", n)
    return n
