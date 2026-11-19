"""Impor matriks resmi OPPKPKE dan Program Kegiatan ATS ke basis data.

Dipakai untuk memasukkan berkas kertas kerja resmi (layout OPPKPKE / ATS) tanpa
menyalin isinya ke dalam repositori. Berkas sumber tetap di tempatnya.

Contoh:
    python matriks_resmi.py --oppkpke "path/OPPKPKE.xlsx" --semester 1 --tahun 2026
    python matriks_resmi.py --ats "path/Program_ATS.xlsx"
    python matriks_resmi.py --oppkpke ... --ats ... --dry-run

Keamanan:
- hanya membaca berkas yang diberikan lewat argumen;
- tidak mencetak isi sel (hanya jumlah baris dan total anggaran);
- transaksi bersifat ganti-periode dan dicatat pada `audit_logs`;
- hash SHA-256 berkas sumber disimpan pada setiap dokumen untuk jejak integritas.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from inklusi import audit  # noqa: E402
from mariadb_store import MariaDocStore  # noqa: E402
import matriks  # noqa: E402

JENIS_FILE = {"oppkpke": "oppkpke", "ats": "ats-program", "disabilitas": "disabilitas"}


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blok in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blok)
    return h.hexdigest()


def _ringkas(items: List[Dict[str, Any]], jenis: str) -> Dict[str, Any]:
    if jenis == "oppkpke":
        return {
            "baris": len(items),
            "total_anggaran": matriks._jumlah(items, "anggaran"),
            "total_realisasi_sem1_2025": matriks._jumlah(items, "realisasi_sem1_2025"),
            "total_realisasi_2025": matriks._jumlah(items, "total_realisasi_2025"),
            "opd": len({i.get("opd") for i in items if i.get("opd")}),
        }
    if jenis == "disabilitas":
        anggaran = matriks._jumlah(items, "anggaran_2025")
        realisasi = matriks._jumlah(items, "realisasi_2025")
        return {
            "baris": len(items),
            "anggaran_2025": anggaran,
            "realisasi_2025": realisasi,
            "serapan_2025": matriks._persen(realisasi, anggaran),
            "anggaran_2026": matriks._jumlah(items, "anggaran_2026"),
            "realisasi_2026": matriks._jumlah(items, "realisasi_2026"),
            "opd": len({i.get("opd") for i in items if i.get("opd")}),
        }
    return {
        "baris": len(items),
        "anggaran_2025": matriks._jumlah(items, "anggaran_2025"),
        "realisasi_2025": matriks._jumlah(items, "realisasi_2025"),
        "anggaran_2026": matriks._jumlah(items, "anggaran_2026"),
        "realisasi_2026": matriks._jumlah(items, "realisasi_2026"),
        "opd": len({i.get("opd") for i in items if i.get("opd")}),
    }


async def _proses(db, args, jenis: str, path: Path) -> bool:
    pembaca = {
        "oppkpke": matriks.baca_oppkpke_resmi,
        "ats": matriks.baca_ats_resmi,
        "disabilitas": matriks.baca_disabilitas_monev,
    }[jenis]
    items, meta = pembaca(str(path))
    print(f"\n[{jenis}] {path.name}")
    print(f"  dibaca={meta['baris_dibaca']} valid={meta['valid']} dilewati={meta['dilewati']}")
    print(f"  ringkasan: {_ringkas(items, jenis)}")
    if meta["errors"]:
        print("  BARIS BERMASALAH (impor dibatalkan):")
        for e in meta["errors"][:20]:
            print(f"   baris {e['baris']}: {e['pesan']}")
        return False
    if not items:
        print("  tidak ada baris valid")
        return False
    if args.dry_run:
        print("  mode dry-run: tidak ada yang ditulis")
        return True

    res = await matriks.simpan_matriks(
        db, JENIS_FILE[jenis], items,
        nama_berkas=path.name, sumber_hash=_hash(path), oleh=args.oleh,
        semester=args.semester if jenis == "oppkpke" else None,
        tahun=args.tahun,
    )
    await audit(db, {"email": args.oleh, "role": "system"}, "impor_matriks_resmi",
                res["label"], ref=path.name,
                detail={"diimpor": res["diimpor"], "dihapus": res["dihapus"],
                        "periode": res["periode"], "hash": _hash(path)[:16]})
    print(f"  tersimpan: {res['diimpor']} baris (mengganti {res['dihapus']}) "
          f"periode {res['periode']}")

    # verifikasi baca-ulang dari basis data
    if jenis == "oppkpke":
        rows = await db["oppkpke_items"].find({"semester": args.semester,
                                               "tahun": args.tahun}).to_list(5000)
    elif jenis == "disabilitas":
        rows = await db["disabilitas_items"].find({}).to_list(5000)
    else:
        rows = await db["ats_program_items"].find({}).to_list(5000)
    print(f"  verifikasi DB: {len(rows)} baris | ringkasan {_ringkas(rows, jenis)}")
    return len(rows) == len(items)


async def main() -> int:
    ap = argparse.ArgumentParser(description="Impor matriks resmi PETA INKLUSI")
    ap.add_argument("--oppkpke", help="path berkas MATRIKS EVALUASI OPPKPKE (.xlsx)")
    ap.add_argument("--ats", help="path berkas Matriks Program Kegiatan ATS (.xlsx)")
    ap.add_argument("--disabilitas", help="path berkas Matriks Monev Kegiatan Disabilitas (.xlsx)")
    ap.add_argument("--semester", type=int, default=1, choices=(1, 2))
    ap.add_argument("--tahun", type=int, default=2026)
    ap.add_argument("--oleh", default="impor-resmi@bappeda.makassarkota.go.id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.oppkpke and not args.ats and not args.disabilitas:
        ap.error("isi minimal salah satu: --oppkpke, --ats, atau --disabilitas")

    db = MariaDocStore.from_env()
    ok = True
    try:
        for jenis, path_str in (("oppkpke", args.oppkpke), ("ats", args.ats),
                                ("disabilitas", args.disabilitas)):
            if not path_str:
                continue
            path = Path(path_str)
            if not path.is_file():
                print(f"berkas tidak ditemukan: {path}")
                ok = False
                continue
            ok = await _proses(db, args, jenis, path) and ok
    finally:
        await db.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
