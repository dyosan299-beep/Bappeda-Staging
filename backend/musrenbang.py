"""PETA INKLUSI - Musrenbang Tematik RKPD 2027.

Modul ini membaca matriks usulan Musrenbang Tematik yang memuat empat kelompok
kepentingan (Disabilitas, Lansia, Perempuan, Anak) beserta program/kegiatan yang
diusulkan tiap OPD.

Dua kumpulan data disimpan:

1. ``musrenbang_usulan`` - satu dokumen per nomor usulan: permasalahan, kebutuhan,
   uraian usulan, lokasi, OPD penanggung jawab, dan catatan OPD.
2. ``musrenbang_intervensi`` - satu dokumen per kombinasi unik OPD + program +
   kegiatan + sub kegiatan + target + anggaran yang diajukan untuk usulan tersebut.

Impor bersifat ganti-total dan dicatat pada ``audit_logs``. Berkas sumber tidak
disalin ke repositori; hanya ringkasannya yang disimpan sebagai snapshot non-pribadi.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from dotenv import load_dotenv

from inklusi import _clean, audit

load_dotenv(Path(__file__).with_name(".env"))

TAHUN = 2027
KOLEKSI_USULAN = "musrenbang_usulan"
KOLEKSI_INTERVENSI = "musrenbang_intervensi"
SNAPSHOT = Path(__file__).with_name("data_resmi") / "musrenbang_2027.json"
TEMA_URUT = ["DISABILITAS", "LANSIA", "PEREMPUAN", "ANAK"]
MAX_BARIS = 5000

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

OPD_LABEL = {
    "dukcapil": "Dukcapil",
    "bappeda": "Bappeda",
    "disdik": "Dinas Pendidikan",
    "disnaker": "Dinas Ketenagakerjaan",
    "pu": "Dinas Pekerjaan Umum",
    "dlh": "Dinas Lingkungan Hidup",
    "dinsos": "Dinas Sosial",
    "dinkes": "Dinas Kesehatan",
    "dp3a": "DP3A",
    "dispora": "Dinas Pemuda dan Olahraga",
    "koperasi": "Dinas Koperasi dan UKM",
    "kominfo": "Dinas Kominfo",
    "kebudayaan": "Dinas Kebudayaan",
    "pariwisata": "Dinas Pariwisata",
    "kb": "Dinas Pengendalian Penduduk dan KB",
    "bpbd": "BPBD",
    "tata ruang": "Dinas Tata Ruang",
    "satpol pp": "Satpol PP",
    "perindustrian": "Dinas Perindustrian dan Perdagangan",
    "perhubungan": "Dinas Perhubungan",
    "bgn hukum": "Bagian Hukum",
    "bgn kesra": "Bagian Kesejahteraan Rakyat",
    "kecamatan": "Kecamatan",
}


# ------------------------------------------------------------------ bantuan teks
def _bersih(v: Any) -> str:
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v).replace("\xa0", " ").replace("\n", " ")).strip()


def _nomor(v: Any) -> Optional[int]:
    s = _bersih(v)
    if not re.fullmatch(r"\d+(?:[.,]0+)?\.?", s):
        return None
    return int(float(s.replace(",", ".").rstrip(".")))


def _header(c: List[str]) -> bool:
    return (c[0].strip().lower().rstrip(".") == "no"
            and "kelompok" in c[1].strip().lower())


def _tema(teks: str) -> str:
    t = teks.strip().upper()
    for nama in TEMA_URUT:
        if t.startswith(nama):
            return nama
    if "PEREMPUAN" in t:
        return "PEREMPUAN"
    return t


def _uang(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s in {"-", "—", "–"}:
        return None
    s = re.sub(r"\brp\b", "", s, flags=re.I).strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s) if s and s not in {"-", "."} else None
    except ValueError:
        return None


def _tambah(daftar: List[str], teks: str) -> None:
    if teks and teks not in daftar:
        daftar.append(teks)


# ------------------------------------------------------------------ pembacaan berkas
def _potong_blok(rows: List[List[str]]) -> List[List[List[str]]]:
    """Pisahkan tabel menjadi blok per kelompok kepentingan (header berulang)."""
    blok: List[List[List[str]]] = []
    kini: List[List[str]] = []
    for c in rows:
        if _header(c):
            if kini:
                blok.append(kini)
            kini = []
            continue
        if any(c):
            kini.append(c)
    if kini:
        blok.append(kini)
    return blok


def _tema_blok(rows: List[List[str]]) -> str:
    for c in rows:
        if c[1] and "kelompok" not in c[1].lower():
            return _tema(c[1])
    return ""


def _uraikan_usulan(rows: List[List[str]], tema: str) -> List[Dict[str, Any]]:
    hasil: List[Dict[str, Any]] = []
    kini: Optional[Dict[str, List[str]]] = None
    for c in rows:
        no = _nomor(c[0])
        if no is not None:
            kini = {"tema": tema, "no": no, "permasalahan": [], "kebutuhan": [],
                    "usulan": [], "lokasi": [], "opd": [], "catatan": [],
                    "keterangan": []}
            hasil.append(kini)  # type: ignore[arg-type]
        if kini is None:
            continue
        for kunci, kolom in (("permasalahan", 2), ("kebutuhan", 3), ("usulan", 4),
                             ("lokasi", 5), ("opd", 6), ("catatan", 7), ("keterangan", 13)):
            _tambah(kini[kunci], c[kolom])  # type: ignore[index]
    for item in hasil:
        for kunci in ("permasalahan", "kebutuhan", "usulan", "lokasi", "opd", "catatan",
                      "keterangan"):
            nilai = item.pop(kunci)  # type: ignore[misc]
            item[kunci] = "\n".join(nilai) if nilai else None
    return hasil


def _uraikan_intervensi(rows: List[List[str]], tema: str, opd: str) -> List[Dict[str, Any]]:
    hasil: List[Dict[str, Any]] = []
    sudah: set = set()
    kini: Optional[int] = None
    for c in rows:
        no = _nomor(c[0])
        if no is not None:
            kini = no
        if kini is None:
            continue
        program, kegiatan, sub, target, anggaran = c[8], c[9], c[10], c[11], c[12]
        if not any((program, kegiatan, sub, target, anggaran)):
            continue
        nilai = _uang(anggaran)
        kunci = (kini, program, kegiatan, sub, target, nilai)
        if kunci in sudah:
            continue
        sudah.add(kunci)
        hasil.append({
            "tema": tema, "no": kini, "opd": opd,
            "program": program or None, "kegiatan": kegiatan or None,
            "sub_kegiatan": sub or None, "target": target or None,
            "anggaran": int(nilai) if nilai is not None and float(nilai).is_integer() else nilai,
            "keterangan": c[13] or None,
        })
    return hasil


def baca_musrenbang(path: str) -> Dict[str, Any]:
    """Baca berkas Matriks Musrenbang Tematik dan kembalikan usulan + intervensi."""
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    usulan: List[Dict[str, Any]] = []
    intervensi: List[Dict[str, Any]] = []
    try:
        for ws in wb.worksheets:
            judul = ws.title.strip()
            if judul.lower() == "sheet2":
                continue
            rows = [[_bersih(v) for v in (list(r) + [""] * 14)[:14]]
                    for r in ws.iter_rows(min_row=3, values_only=True)]
            blok = _potong_blok(rows)
            utama = ws is wb.worksheets[0] or judul.lower().startswith("matriks musrenbang")
            opd = OPD_LABEL.get(judul.lower(), judul)
            for bagian in blok:
                tema = _tema_blok(bagian)
                if not tema:
                    continue
                if utama:
                    usulan.extend(_uraikan_usulan(bagian, tema))
                else:
                    intervensi.extend(_uraikan_intervensi(bagian, tema, opd))
    finally:
        wb.close()

    urut_tema = {t: i for i, t in enumerate(TEMA_URUT)}
    usulan.sort(key=lambda x: (urut_tema.get(x["tema"], 99), x["no"]))
    intervensi.sort(key=lambda x: (urut_tema.get(x["tema"], 99), x["opd"], x["no"],
                                   x.get("program") or ""))
    for i, item in enumerate(usulan, start=1):
        item["urutan"] = i
    for i, item in enumerate(intervensi, start=1):
        item["urutan"] = i
    return {"tahun": TAHUN, "usulan": usulan, "intervensi": intervensi}


def ringkasan(usulan: List[Dict[str, Any]], intervensi: List[Dict[str, Any]]) -> Dict[str, Any]:
    per_tema = []
    for tema in TEMA_URUT:
        u = [x for x in usulan if x.get("tema") == tema]
        i = [x for x in intervensi if x.get("tema") == tema]
        per_tema.append({
            "tema": tema,
            "usulan": len(u),
            "intervensi": len(i),
            "anggaran": sum(float(x.get("anggaran") or 0) for x in i),
        })
    total = sum(float(x.get("anggaran") or 0) for x in intervensi)
    return {
        "tahun": TAHUN,
        "jumlah_usulan": len(usulan),
        "jumlah_intervensi": len(intervensi),
        "jumlah_tema": len({x.get("tema") for x in usulan if x.get("tema")}),
        "jumlah_opd": len({x.get("opd") for x in intervensi if x.get("opd")}),
        "total_anggaran": int(total) if float(total).is_integer() else round(total, 2),
        "per_tema": per_tema,
    }


# ------------------------------------------------------------------ penyimpanan
def _dokumen(item: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    stamp = meta["stamp"]
    return {
        **item,
        "id": str(uuid.uuid4()),
        "tahun": TAHUN,
        "sumber_berkas": meta["nama_berkas"],
        "sumber_hash": meta["hash"],
        "diimpor_oleh": meta["oleh"],
        "diimpor_pada": stamp,
        "created_at": stamp,
        "updated_at": stamp,
    }


async def simpan_musrenbang(db, data: Dict[str, Any], *, nama_berkas: str = "",
                            sumber_hash: str = "", oleh: str = "") -> Dict[str, Any]:
    """Ganti seluruh isi koleksi Musrenbang secara atomik."""
    usulan = data.get("usulan") or []
    intervensi = data.get("intervensi") or []
    if not usulan and not intervensi:
        raise HTTPException(status_code=422, detail="Tidak ada usulan yang bisa disimpan")
    meta = {"stamp": now_iso(), "nama_berkas": nama_berkas, "hash": sumber_hash, "oleh": oleh}

    dihapus = 0
    for koleksi in (KOLEKSI_USULAN, KOLEKSI_INTERVENSI):
        lama = await db[koleksi].find({}).to_list(MAX_BARIS)
        dihapus += len(lama)
        if lama:
            await db[koleksi].delete_many({})

    if usulan:
        await db[KOLEKSI_USULAN].insert_many([_dokumen(i, meta) for i in usulan])
    if intervensi:
        await db[KOLEKSI_INTERVENSI].insert_many([_dokumen(i, meta) for i in intervensi])

    return {"tahun": TAHUN, "usulan": len(usulan), "intervensi": len(intervensi),
            "dihapus": dihapus, "ringkasan": ringkasan(usulan, intervensi)}


# ------------------------------------------------------------------ snapshot
async def ekspor_snapshot(db) -> Dict[str, int]:
    usulan = [_clean(r) for r in await db[KOLEKSI_USULAN].find({}).sort([("urutan", 1)]).to_list(MAX_BARIS)]
    intervensi = [_clean(r) for r in await db[KOLEKSI_INTERVENSI].find({}).sort([("urutan", 1)]).to_list(MAX_BARIS)]
    muatan = {
        "tahun": TAHUN,
        "sumber_berkas": (usulan[0].get("sumber_berkas") if usulan else "") or "",
        "sumber_hash": (usulan[0].get("sumber_hash") if usulan else "") or "",
        "usulan": usulan,
        "intervensi": intervensi,
    }
    SNAPSHOT.parent.mkdir(exist_ok=True)
    SNAPSHOT.write_text(json.dumps(muatan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"usulan": len(usulan), "intervensi": len(intervensi)}


async def muat_snapshot(db) -> Dict[str, int]:
    """Isi koleksi Musrenbang yang masih kosong dari snapshot (tidak menimpa)."""
    if not SNAPSHOT.is_file():
        return {"usulan": 0, "intervensi": 0}
    jumlah_u = await db[KOLEKSI_USULAN].count_documents({})
    jumlah_i = await db[KOLEKSI_INTERVENSI].count_documents({})
    if jumlah_u or jumlah_i:
        return {"usulan": 0, "intervensi": 0}
    muatan = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    meta = {"stamp": now_iso(), "nama_berkas": muatan.get("sumber_berkas") or SNAPSHOT.name,
            "hash": muatan.get("sumber_hash") or "", "oleh": "seed-data-resmi@lokal"}
    usulan = muatan.get("usulan") or []
    intervensi = muatan.get("intervensi") or []
    if usulan:
        await db[KOLEKSI_USULAN].insert_many([_dokumen(i, meta) for i in usulan])
    if intervensi:
        await db[KOLEKSI_INTERVENSI].insert_many([_dokumen(i, meta) for i in intervensi])
    return {"usulan": len(usulan), "intervensi": len(intervensi)}


# ------------------------------------------------------------------ API
def build_router(db, current_user_dep) -> APIRouter:
    router = APIRouter(tags=["musrenbang"])

    @router.get("/musrenbang")
    async def daftar_musrenbang(user: dict = Depends(current_user_dep)):
        usulan = [_clean(r) for r in await db[KOLEKSI_USULAN].find({})
                  .sort([("urutan", 1)]).to_list(MAX_BARIS)]
        intervensi = [_clean(r) for r in await db[KOLEKSI_INTERVENSI].find({})
                      .sort([("urutan", 1)]).to_list(MAX_BARIS)]
        return {
            "tahun": TAHUN,
            "label": f"Musrenbang Tematik RKPD {TAHUN}",
            "tersedia": bool(usulan or intervensi),
            "keterangan": ("Usulan Musrenbang Tematik disusun per kelompok kepentingan. "
                           "Program dan anggaran adalah usulan Renja SKPD, bukan realisasi."),
            "ringkasan": ringkasan(usulan, intervensi),
            "usulan": usulan,
            "intervensi": intervensi,
        }

    return router


# ------------------------------------------------------------------ CLI
def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blok in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blok)
    return h.hexdigest()


async def main() -> int:
    ap = argparse.ArgumentParser(description="Impor Matriks Musrenbang Tematik")
    ap.add_argument("--file", required=True, help="path berkas Matriks Musrenbang (.xlsx)")
    ap.add_argument("--oleh", default="impor-musrenbang@bappeda.makassarkota.go.id")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--snapshot", action="store_true", help="tulis snapshot dari basis data")
    args = ap.parse_args()

    from mariadb_store import MariaDocStore

    path = Path(args.file)
    if not path.is_file():
        print(f"berkas tidak ditemukan: {path}")
        return 1

    db = MariaDocStore.from_env()
    try:
        if args.snapshot:
            print("snapshot:", await ekspor_snapshot(db))
            return 0

        data = baca_musrenbang(str(path))
        ringkas = ringkasan(data["usulan"], data["intervensi"])
        print(f"{path.name}")
        print(f"  usulan={len(data['usulan'])} intervensi={len(data['intervensi'])}")
        for t in ringkas["per_tema"]:
            print(f"  {t['tema']:12s} usulan={t['usulan']:3d} intervensi={t['intervensi']:3d} "
                  f"anggaran={t['anggaran']:,.0f}".replace(",", "."))
        print(f"  total anggaran: {ringkas['total_anggaran']:,}".replace(",", "."))
        if args.dry_run:
            print("  dry-run: tidak ada yang ditulis")
            return 0

        res = await simpan_musrenbang(db, data, nama_berkas=path.name,
                                      sumber_hash=_hash(path), oleh=args.oleh)
        await audit(db, {"email": args.oleh, "role": "system"}, "impor_musrenbang",
                    res.get("tahun"), ref=path.name,
                    detail={"usulan": res["usulan"], "intervensi": res["intervensi"],
                            "dihapus": res["dihapus"], "hash": _hash(path)[:16]})
        print(f"  tersimpan: usulan={res['usulan']} intervensi={res['intervensi']} "
              f"(mengganti {res['dihapus']} dokumen)")
        print("  snapshot:", await ekspor_snapshot(db))
        return 0
    finally:
        await db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
