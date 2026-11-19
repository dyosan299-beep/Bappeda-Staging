"""Seed data UJI (data_uji=True) rumah tangga DTSEN untuk menguji alur Petugas -> Verval -> GeoTag.

Idempoten: rumah tangga uji dikenali dari import_batch == "uji-verval".
Jalankan: cd /app/backend && python /app/tests/seed_verval_demo.py
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")

import dtsen_ref as dref  # noqa: E402
import mariadb_store  # noqa: E402

ROWS = [
    # kecamatan, kelurahan, kode_kel, rw, rt, no_kk, kepala, alamat, anggota, desil, lat, lng
    ("Rappocini", "Gunung Sari", "7371031001", "1", "1", "7371030101010001", "Andi Baso", "Jl. Sultan Alauddin Lr. 1 No. 3", 4, 1, -5.1735, 119.4345),
    ("Rappocini", "Gunung Sari", "7371031001", "1", "2", "7371030101010002", "Hasnah Dg. Ngai", "Jl. Sultan Alauddin Lr. 2 No. 7", 5, 2, -5.1741, 119.4351),
    ("Rappocini", "Gunung Sari", "7371031001", "1", "3", "7371030101010003", "Syamsuddin", "Jl. Minasa Upa Blok A No. 12", 3, 1, -5.1748, 119.4358),
    ("Rappocini", "Gunung Sari", "7371031001", "2", "1", "7371030101020001", "Rosmini", "Jl. Mannuruki II No. 5", 6, 3, -5.1752, 119.4330),
    ("Rappocini", "Gunung Sari", "7371031001", "2", "4", "7371030101020002", "Muh. Tahir", "Jl. Mannuruki II No. 9", 2, 2, -5.1758, 119.4336),
    ("Rappocini", "Karunrung", "7371031002", "1", "1", "7371030102010001", "Nurhayati", "Jl. Tidung Raya No. 20", 4, 1, -5.1690, 119.4420),
    ("Rappocini", "Karunrung", "7371031002", "3", "2", "7371030102030001", "Abd. Rahman", "Jl. Tidung X No. 2", 5, 4, -5.1702, 119.4431),
    ("Tallo", "Buloa", "7371091001", "1", "1", "7371090101010001", "Daeng Tompo", "Jl. Tinumbu Lr. 5 No. 1", 7, 1, -5.1060, 119.4380),
    ("Tallo", "Buloa", "7371091001", "2", "2", "7371090101020001", "Sitti Aminah", "Jl. Tinumbu Lr. 7 No. 4", 3, 2, -5.1068, 119.4392),
]


async def main():
    db = mariadb_store.MariaDocStore.from_env()
    await db.connect()
    n = 0
    for kec, kel, kode_kel, rw, rt, kk, kepala, alamat, anggota, desil, lat, lng in ROWS:
        if await db.households.find_one({"no_kk": kk, "kode_kelurahan": kode_kel}):
            continue
        doc = {
            "id": str(uuid.uuid4()), "no_kk": kk, "no_kk_mask": kk[:4] + "********" + kk[-4:],
            "kepala_keluarga": kepala, "alamat": alamat,
            "kecamatan": kec, "kode_kecamatan": kode_kel[:6], "kelurahan": kel, "kode_kelurahan": kode_kel,
            "rt": rt, "rw": rw, "jumlah_anggota_keluarga": anggota, "desil": desil,
            "status_rumah": "milik_sendiri", "lat": lat, "lng": lng,
            "data_uji": True, "sumber_input": "seed-uji", "import_batch": "uji-verval",
            "created_at": datetime.now(timezone.utc).isoformat(), "created_by": "seed",
        }
        doc["dtsen_ref"] = dref.make_ref(kk, kode_kel, kel)
        await db.households.insert_one(doc)
        n += 1
    total = await db.households.count_documents({"import_batch": "uji-verval"})
    print(f"ditambahkan={n} total_uji={total}")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
