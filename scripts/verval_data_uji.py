"""Data UJI sintetis untuk modul GeoTag-Verval (HANYA preview/pengujian).

Perintah:
  python scripts/verval_data_uji.py seed            # buat data UJI (idempoten)
  python scripts/verval_data_uji.py hapus           # hapus HANYA data bertanda UJI
  python scripts/verval_data_uji.py simulasi-reset  # tiru ETL --reset: UUID households UJI diganti
  python scripts/verval_data_uji.py info

Pengaman:
- Wajib env VERVAL_IZINKAN_DATA_UJI=true (jangan aktifkan di produksi).
- Semua rumah tangga UJI: data_uji=true, source_file="UJI_SINTETIS_VERVAL", No. KK diawali 9999
  (bukan kode provinsi valid), kode kelurahan diawali 99 (bukan kode resmi). Nama kelurahan
  memakai nama poligon asli HANYA agar penanda tampil di peta.
- Penghapusan memfilter source_file=UJI_SINTETIS_VERVAL / domain email UJI + peran operator_rt_rw;
  data lain tidak disentuh. (Catatan: filter boolean pada mariadb_store tidak cocok karena
  JSON_VALUE mengembalikan "1" untuk true, sehingga penanda string yang dipakai.)
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
import auth as authmod  # noqa: E402
import dtsen_ref  # noqa: E402
import verval_storage  # noqa: E402
from mariadb_store import MariaDocStore  # noqa: E402

UJI_DOMAIN = "@uji-verval.example.com"
# Password untuk akun UJI sintetis WAJIB di‑set via env agar tidak ada secret di repo.
UJI_PASSWORD = os.environ.get("VERVAL_UJI_PASSWORD")
if not UJI_PASSWORD:
    raise SystemExit(
        "VERVAL_UJI_PASSWORD belum di‑set. Isi variabel lingkungan tersebut "
        "(contoh: export VERVAL_UJI_PASSWORD=...) sebelum menjalankan skrip ini."
    )
SOURCE = "UJI_SINTETIS_VERVAL"
now = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

KEL = {  # kode UJI (99...) -> nama poligon asli & kecamatan
    "9900000001": ("Kaluku Bodoa", "Tallo", "9900001"),
    "9900000002": ("Buloa", "Tallo", "9900001"),
    "9900000003": ("Karunrung", "Rappocini", "9900002"),
}
# (no_kk, kode_kel, rt, rw, kepala)
RUMAH = [
    ("9999000000000101", "9900000001", "1", "2", "UJI KELUARGA SATU"),
    ("9999000000000102", "9900000001", "3", "2", "UJI KELUARGA DUA"),
    ("9999000000000103", "9900000001", "4", "2", "UJI KELUARGA TIGA (RT DI LUAR PENUGASAN)"),
    ("9999000000000104", "9900000001", "", "", "UJI KELUARGA EMPAT (TANPA RT/RW)"),
    ("9999000000000201", "9900000002", "1", "1", "UJI KELUARGA LIMA"),
    ("9999000000000301", "9900000003", "2", "5", "UJI KELUARGA ENAM"),
]
OPERATORS = [
    ("op.rtrw.a" + UJI_DOMAIN, "UJI Operator RT/RW A (Kaluku Bodoa RW 2)", "Tallo"),
    ("op.rtrw.b" + UJI_DOMAIN, "UJI Operator RT/RW B (Buloa RW 1)", "Tallo"),
    ("op.rtrw.c" + UJI_DOMAIN, "UJI Operator RT/RW C (tanpa penugasan)", "Rappocini"),
]


def guard():
    if (os.environ.get("VERVAL_IZINKAN_DATA_UJI") or "").lower() not in ("1", "true", "yes"):
        sys.exit("Ditolak: set VERVAL_IZINKAN_DATA_UJI=true (HANYA lingkungan preview/pengujian).")
    if not dtsen_ref.ref_secret():
        sys.exit("VERVAL_REF_SECRET belum diatur.")


def hh_doc(no_kk, kode, rt, rw, nama):
    kel, kec, kode_kec = KEL[kode]
    d = {"id": str(uuid.uuid4()), "no_kk": no_kk, "no_kk_mask": no_kk[:4] + "********" + no_kk[-4:],
         "kode_kecamatan": kode_kec, "kecamatan": kec, "kode_kelurahan": kode, "kelurahan": kel,
         "alamat": f"Jl. Uji Sintetis No. {no_kk[-2:]}", "jumlah_anggota_keluarga": 4,
         "kepala_keluarga": nama, "desil_nasional": None, "pbi_nas": 0, "pbi_pemda": 0,
         "risk_score": 0, "risk_level": "rendah", "risk_factors": [], "perlu_validasi": False,
         "jenis_lantai_terluas": 2, "luas_lantai": 36, "jenis_dinding_terluas": 1, "jenis_atap_terluas": 3,
         "sumber_air_minum_utama": 4, "sumber_penerangan_utama": 1, "daya_terpasang": 2,
         "fasilitas_bab": 1, "jenis_kloset": 1, "pembuangan_akhir_tinja": 1,
         "source_file": SOURCE, "source_sheet": "UJI", "import_batch": "UJI", "imported_at": now(),
         "data_uji": True, "dtsen_ref": dtsen_ref.make_ref(no_kk, kode, kel)}
    if rt or rw:
        d.update({"rt": rt, "rw": rw, "rt_rw_sumber": "kolom_berkas_sumber"})
    return d


async def seed(db):
    for no_kk, kode, rt, rw, nama in RUMAH:
        if not await db.households.find_one({"no_kk": no_kk, "kode_kelurahan": kode}):
            await db.households.insert_one(hh_doc(no_kk, kode, rt, rw, nama))
    ids = {}
    for email, name, wil in OPERATORS:
        u = await db.users.find_one({"email": email})
        if not u:
            await db.users.insert_one({"email": email, "password_hash": authmod.hash_password(UJI_PASSWORD),
                                       "name": name, "role": "operator_rt_rw", "wilayah": wil,
                                       "status": "active", "data_uji": True, "created_at": now()})
            u = await db.users.find_one({"email": email})
        ids[email] = str(u["_id"])
    pen = [("op.rtrw.a", "9900000001", "2", ["1", "3"]), ("op.rtrw.b", "9900000002", "1", [])]
    for who, kode, rw, rts in pen:
        uid = ids[who + UJI_DOMAIN]
        if not await db.verval_penugasan.find_one({"user_id": uid, "kode_kelurahan": kode, "status": "aktif"}):
            kel, kec, kode_kec = KEL[kode]
            await db.verval_penugasan.insert_one({
                "id": str(uuid.uuid4()), "user_id": uid, "operator_email": who + UJI_DOMAIN,
                "kode_kecamatan": kode_kec, "kecamatan": kec, "kode_kelurahan": kode, "kelurahan": kel,
                "rw": rw, "rt": rts, "lintas_wilayah": False, "dasar_penugasan": "UJI", "berlaku_mulai": None,
                "berlaku_sampai": None, "catatan": "Penugasan data UJI", "status": "aktif",
                "ditetapkan_oleh": "skrip-uji", "created_at": now(), "data_uji": True})
    print("seed selesai:", {"households_uji": await db.households.count_documents({"source_file": SOURCE}),
                            "operator_uji": len(ids), "password_operator_uji": "(lihat VERVAL_UJI_PASSWORD / test_credentials.md)"})


async def hapus(db):
    hh = await db.households.find({"source_file": SOURCE}).to_list(1000)
    refs = [h.get("dtsen_ref") for h in hh if h.get("dtsen_ref")]
    users = await db.users.find({"email": {"$regex": "uji-verval\\.example\\.com$"}}).to_list(100)
    uids = [str(u["_id"]) for u in users]
    recs = await db.verval_records.find({"dtsen_ref": {"$in": refs or ["-"]}}).to_list(10000)
    recs += [r for r in await db.verval_records.find({"operator_id": {"$in": uids or ["-"]}}).to_list(10000)
             if r["id"] not in {x["id"] for x in recs}]
    rids = [r["id"] for r in recs]
    fotos = await db.verval_foto.find({"record_id": {"$in": rids or ["-"]}}).to_list(10000)
    for f in fotos:
        verval_storage.delete(f.get("path") or "")
    n = {
        "verval_foto": (await db.verval_foto.delete_many({"record_id": {"$in": rids or ["-"]}})).deleted_count,
        "verval_riwayat": (await db.verval_riwayat.delete_many({"record_id": {"$in": rids or ["-"]}})).deleted_count,
        "verval_records": (await db.verval_records.delete_many({"id": {"$in": rids or ["-"]}})).deleted_count,
        "verval_sasaran": (await db.verval_sasaran.delete_many({"user_id": {"$in": uids or ["-"]}})).deleted_count,
        "verval_penugasan": (await db.verval_penugasan.delete_many({"user_id": {"$in": uids or ["-"]}})).deleted_count,
        "households": (await db.households.delete_many({"source_file": SOURCE})).deleted_count,
        "users": (await db.users.delete_many({"email": {"$regex": "uji-verval\\.example\\.com$"}, "role": "operator_rt_rw"})).deleted_count,
    }
    print("hapus data UJI:", n)


async def simulasi_reset(db):
    """Tiru ETL --reset untuk data UJI: dokumen dihapus & dibuat ulang dengan UUID baru."""
    for h in await db.households.find({"source_file": SOURCE}).to_list(1000):
        old = h["id"]
        await db.households.delete_many({"id": old})
        h.pop("_id", None)
        h["id"] = str(uuid.uuid4())
        h.pop("dtsen_ref", None)  # ETL lama belum menulis ref -> diisi ulang lewat backfill
        await db.households.insert_one(h)
    n = await dtsen_ref.backfill_refs(db)
    print("simulasi reset selesai; ref diisi ulang:", n)


async def main():
    guard()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"
    db = MariaDocStore.from_env()
    await db.connect()
    try:
        if cmd == "seed":
            await seed(db)
        elif cmd == "hapus":
            await hapus(db)
        elif cmd == "simulasi-reset":
            await simulasi_reset(db)
        else:
            print({"households_uji": await db.households.count_documents({"source_file": SOURCE}),
                   "households_total": await db.households.count_documents({})})
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
