"""Snapshot data resmi NON-PRIBADI untuk PETA INKLUSI.

Berkas di ``data_resmi/`` memuat matriks OPPKPKE, Program ATS, monev kegiatan
disabilitas, dan usulan Musrenbang Tematik yang sudah diimpor dari kertas kerja
resmi. Tujuannya agar deployment baru tetap memiliki data tersebut tanpa perlu
menyalin berkas sumber yang sensitif.

Yang TIDAK pernah diekspor: `households`, `stunting_children`, `users`,
`audit_logs`, dan koleksi lain yang memuat data pribadi.

Pemakaian:
    python snapshot_data_resmi.py --export   # tulis JSON dari basis data
    python snapshot_data_resmi.py --load     # isi koleksi yang masih kosong
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

import matriks  # noqa: E402
from mariadb_store import MariaDocStore  # noqa: E402

DATA_DIR = Path(__file__).with_name("data_resmi")
FILES = {
    "oppkpke": "oppkpke_2026_semester1.json",
    "ats-program": "ats_program_2025_2027.json",
    "disabilitas": "disabilitas_monev_2026.json",
}
KOLEKSI = {"oppkpke": "oppkpke_items", "ats-program": "ats_program_items",
          "disabilitas": "disabilitas_items"}
META_BUKAN_ISI = {"_id", "id", "created_at", "updated_at", "diimpor_oleh", "diimpor_pada"}


def _path(jenis: str) -> Path:
    return DATA_DIR / FILES[jenis]


async def ekspor(db, jenis: Optional[str] = None) -> Dict[str, int]:
    DATA_DIR.mkdir(exist_ok=True)
    hasil: Dict[str, int] = {}
    for j, nama in FILES.items():
        if jenis and j != jenis:
            continue
        if j == "oppkpke":
            rows = await db[KOLEKSI[j]].find({"semester": 1, "tahun": 2026}) \
                .sort("no", 1).to_list(5000)
        else:
            rows = await db[KOLEKSI[j]].find({}).sort("no", 1).to_list(5000)
        items = []
        sumber_berkas = ""
        sumber_hash = ""
        for r in rows:
            sumber_berkas = sumber_berkas or str(r.get("sumber_berkas") or "")
            sumber_hash = sumber_hash or str(r.get("sumber_hash") or "")
            items.append({k: v for k, v in r.items() if k not in META_BUKAN_ISI})
        muatan: Dict[str, Any] = {"jenis": j, "sumber_berkas": sumber_berkas,
                                  "sumber_hash": sumber_hash, "items": items}
        if j == "oppkpke":
            muatan.update({"semester": 1, "tahun": 2026})
        else:
            muatan["tahun"] = 2026
        _path(j).write_text(json.dumps(muatan, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        hasil[j] = len(items)
    return hasil


async def muat_matriks(db, hanya: Optional[tuple] = None) -> Dict[str, int]:
    """Isi koleksi matriks yang masih kosong dari snapshot (tidak menimpa data)."""
    hasil: Dict[str, int] = {}
    for j in FILES:
        if hanya and j not in hanya:
            continue
        if await db[KOLEKSI[j]].count_documents({}) > 0:
            hasil[j] = 0
            continue
        p = _path(j)
        if not p.is_file():
            hasil[j] = 0
            continue
        muatan = json.loads(p.read_text(encoding="utf-8"))
        res = await matriks.simpan_matriks(
            db, j, muatan.get("items") or [],
            nama_berkas=muatan.get("sumber_berkas") or p.name,
            sumber_hash=muatan.get("sumber_hash") or "",
            oleh="seed-data-resmi@lokal",
            semester=muatan.get("semester") if j == "oppkpke" else None,
            tahun=muatan.get("tahun") if j == "oppkpke" else 2026,
        )
        hasil[j] = res["diimpor"]
    return hasil


async def main() -> int:
    ap = argparse.ArgumentParser(description="Snapshot data resmi non-pribadi")
    ap.add_argument("--export", action="store_true", help="tulis JSON dari basis data")
    ap.add_argument("--load", action="store_true", help="isi koleksi yang masih kosong")
    ap.add_argument("--jenis", choices=sorted(FILES), help="batasi ke satu jenis")
    args = ap.parse_args()
    if not args.export and not args.load:
        ap.error("pilih --export atau --load")

    db = MariaDocStore.from_env()
    try:
        if args.export:
            hasil = await ekspor(db, args.jenis)
            print("diekspor:", hasil)
        else:
            hasil = await muat_matriks(db, (args.jenis,) if args.jenis else None)
            print("dimuat (0 = dilewati karena sudah berisi):", hasil)
    finally:
        await db.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
