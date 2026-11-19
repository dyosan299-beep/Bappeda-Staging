"""Impor data PETA INKLUSI dari berkas sumber resmi.

1. PDF "DATA STUNTING KEC MAKASSAR DAN TALLO.pdf"  -> koleksi `stunting_children`
   (data balita stunting per anak; data pribadi DIMASKING di API untuk non-admin).
2. DOCX "Matriks Musrenbang Tematik 26 November 2025.docx" -> koleksi `musrenbang_usulan`.

Berkas sumber TIDAK di-commit ke Git (berisi data pribadi). Letakkan di:
    /app/data_upload/inklusi/   (atau atur env INKLUSI_DATA_DIR)
Lalu jalankan:  cd /app/backend && python inklusi_import.py [--stunting] [--musrenbang]
"""
from __future__ import annotations

import argparse
import asyncio
import difflib
import os
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from inklusi import norm_wil  # noqa: E402
from mariadb_store import MariaDocStore  # noqa: E402

DATA_DIR = Path(os.environ.get("INKLUSI_DATA_DIR", "/app/data_upload/inklusi"))
now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

# Ejaan kelurahan pada berkas sumber yang berbeda dengan master PETA_DASAR.
ALIAS_KELURAHAN = {
    "BARA BARAYA SELAAN": "BARA BARAYA SELATAN",
    "MACCINI": "MACCINI",
}


def umur_bulan(tgl: str, ref: date) -> Optional[int]:
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", tgl or "")
    if not m:
        return None
    try:
        d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None
    return max(0, (ref.year - d.year) * 12 + ref.month - d.month - (1 if ref.day < d.day else 0))


def kelompok_umur(bln: Optional[int]) -> str:
    if bln is None:
        return "Tidak diketahui"
    if bln < 12:
        return "0-11 bulan"
    if bln < 24:
        return "12-23 bulan"
    if bln < 36:
        return "24-35 bulan"
    if bln < 48:
        return "36-47 bulan"
    if bln < 60:
        return "48-59 bulan"
    return "≥ 60 bulan"


HEADER_NAMA = {"NAMA", "NAMA BALITA", "NAMA ANAK"}


def extract_stunting_rows(source: Any) -> List[List[str]]:
    """Baca seluruh baris tabel dari PDF stunting (path atau bytes). Sinkron (pdfplumber)."""
    import io
    import pdfplumber

    src = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else str(source)
    rows: List[List[str]] = []
    with pdfplumber.open(src) as pdf:
        for pg in pdf.pages:
            for tb in pg.extract_tables():
                for r in tb:
                    if not r:
                        continue
                    first = (r[0] or "").strip().lower().rstrip(".")
                    second = (r[1] if len(r) > 1 else "") or ""
                    if first == "no" or second.replace("\n", " ").strip().upper() in HEADER_NAMA:
                        continue
                    rows.append([(c or "").replace("\n", " ").strip() for c in r])
    return rows


ORTU_MIRIP = 0.85  # ambang kemiripan nama orang tua untuk anak bernama sama
STUNTING_NS = uuid.UUID("6f1c2a7e-3b7d-4c55-9a8e-5d1f0b2c9e41")


def _kunci(v: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


def kunci_anak(nama: Any, ortu: Any) -> str:
    """Identitas balita: nama anak + nama orang tua (dinormalisasi). Anak kembar tetap berbeda (nama beda)."""
    return f"{_kunci(nama)}|{_kunci(ortu)}"


def id_anak(kunci: str) -> str:
    """ID deterministik -> dipakai juga sebagai primary key MariaDB, sehingga baris ganda ditolak DB."""
    return str(uuid.uuid5(STUNTING_NS, kunci))


def _skor_lengkap(d: Dict[str, Any]) -> int:
    return (3 if d.get("kelurahan_norm") else 0) + (2 if d.get("umur_bulan") is not None else 0) + len(d.get("alamat") or "")


async def build_stunting_docs(db, rows: List[List[str]], filename: str, batch: str) -> Dict[str, Any]:
    """Ubah baris PDF menjadi dokumen `stunting_children` unik (belum disimpan).

    Duplikat = nama anak + nama orang tua sama. Dari baris ganda dipertahankan yang datanya paling lengkap.
    """
    from inklusi import mask_name

    geo = await db.geo_kelurahan.find({}).to_list(500)
    kel_idx = {norm_wil(g.get("kelurahan")): g for g in geo}
    ref = date(2026, 1, 1)  # data tahun 2026 (judul berkas)
    unik: Dict[str, Dict[str, Any]] = {}
    duplikat: List[Dict[str, Any]] = []
    dilewati = 0
    for r in rows:
        if len(r) < 9 or not r[1]:
            dilewati += 1
            continue
        no, nama, jk, tgl, ortu, pkm, kel, alamat, tbu = r[:9]
        kel_n = ALIAS_KELURAHAN.get(norm_wil(kel), norm_wil(kel))
        g = kel_idx.get(kel_n)
        if not g:  # fallback: nama puskesmas = nama kelurahan (mis. KALUKU BODOA)
            g = kel_idx.get(norm_wil(pkm))
            if g:
                kel_n = norm_wil(g.get("kelurahan"))
        bln = umur_bulan(tgl, ref)
        status = "Sangat Pendek" if "sangat" in tbu.lower() else ("Pendek" if tbu else "Tidak diketahui")
        k = kunci_anak(nama, ortu)
        cid = id_anak(k)
        d = {
            "_id": cid, "id": cid, "kunci_anak": k, "no_urut": no.rstrip("."), "nama": nama.title(),
            "jk": "L" if jk.upper().startswith("L") else ("P" if jk.upper().startswith("P") else "-"),
            "tgl_lahir": tgl, "umur_bulan": bln, "kelompok_umur": kelompok_umur(bln),
            "nama_ortu": ortu, "puskesmas": pkm.title(),
            "kelurahan": (g or {}).get("kelurahan") or (kel.title() if kel else "Tidak diketahui"),
            "kelurahan_asli": kel,
            "kelurahan_norm": kel_n if g else "",
            "kecamatan": (g or {}).get("kecamatan") or "Tidak diketahui",
            "kecamatan_norm": norm_wil((g or {}).get("kecamatan")),
            "alamat": alamat, "status_tbu": status, "tahun": 2026,
            "sumber": filename, "import_batch": batch, "created_at": now_iso(),
        }
        # cari anak yang sama: nama anak identik + nama orang tua identik/mirip (salah ketik, mis. CINDI/CINDY)
        lama_key = k if k in unik else next(
            (kk for kk, dd in unik.items() if kk.split("|")[0] == _kunci(nama) and
             difflib.SequenceMatcher(None, kk.split("|")[1], _kunci(ortu)).ratio() >= ORTU_MIRIP), None)
        if lama_key is None:
            unik[k] = d
            continue
        lama = unik[lama_key]
        pakai, buang = (d, lama) if _skor_lengkap(d) > _skor_lengkap(lama) else (lama, d)
        del unik[lama_key]
        unik[pakai["kunci_anak"]] = pakai
        beda = [f"{lbl} {buang.get(f) or '-'} vs {pakai.get(f) or '-'}" for f, lbl in
                (("tgl_lahir", "tgl lahir"), ("status_tbu", "TB/U"), ("jk", "JK")) if buang.get(f) != pakai.get(f)]
        if _kunci(buang.get("nama_ortu")) != _kunci(pakai.get("nama_ortu")):
            beda.append("ejaan nama orang tua")
        duplikat.append({"nama": mask_name(pakai["nama"]), "kelurahan": pakai["kelurahan"],
                         "no_dipakai": pakai["no_urut"], "no_dibuang": buang["no_urut"],
                         "keterangan": "Identik" if not beda else "Berbeda: " + "; ".join(beda)})
    docs = list(unik.values())
    # kelurahan kosong/tak dikenal: simpulkan KECAMATAN dari puskesmas bila seluruh anak puskesmas itu
    # berada di satu kecamatan (kelurahan tetap "Tidak diketahui")
    pkm_kec: Dict[str, set] = {}
    for d in docs:
        if d["kecamatan_norm"]:
            pkm_kec.setdefault(_kunci(d["puskesmas"]), set()).add(d["kecamatan"])
    for d in docs:
        if not d["kecamatan_norm"]:
            kc = pkm_kec.get(_kunci(d["puskesmas"])) or set()
            if len(kc) == 1:
                d["kecamatan"] = next(iter(kc))
                d["kecamatan_norm"] = norm_wil(d["kecamatan"])
                d["catatan"] = "Kelurahan kosong/tidak dikenal di berkas; kecamatan disimpulkan dari puskesmas"
    kel_tidak_cocok: Dict[str, int] = {}
    for d in docs:
        if not d["kelurahan_norm"]:
            kk = d.get("kelurahan_asli") or "(kosong)"
            kel_tidak_cocok[kk] = kel_tidak_cocok.get(kk, 0) + 1
    return {"docs": docs, "baris": len(rows), "dilewati": dilewati, "duplikat": duplikat,
            "kelurahan_tidak_cocok": sum(kel_tidak_cocok.values()),
            "daftar_tidak_cocok": [{"kelurahan": k, "jumlah": v} for k, v in
                                   sorted(kel_tidak_cocok.items(), key=lambda x: -x[1])]}


_SAVE_LOCK = asyncio.Lock()


async def save_stunting_docs(db, docs: List[Dict[str, Any]], filename: str, batch: str, total_rows: int,
                             tidak_cocok: int, oleh: str = "cli") -> int:
    """Ganti seluruh isi `stunting_children` dengan dokumen unik baru + catat batch impor.

    Aman terhadap klik ganda: dikunci per proses, dedup ulang per `_id`, dan primary key menolak baris ganda.
    """
    async with _SAVE_LOCK:
        bersih: Dict[str, Dict[str, Any]] = {}
        for d in docs:
            k = d.get("kunci_anak") or kunci_anak(d.get("nama"), d.get("nama_ortu"))
            cid = id_anak(k)
            bersih[cid] = {**{x: y for x, y in d.items() if x != "_id"}, "_id": cid, "id": cid, "kunci_anak": k}
        await db.stunting_children.delete_many({})
        rows = list(bersih.values())
        for i in range(0, len(rows), 200):
            await db.stunting_children.insert_many([dict(r) for r in rows[i:i + 200]])
        await db.import_batches.insert_one({
            "id": batch, "filename": filename, "jenis": "stunting_anak", "sumber": "inklusi_import",
            "total_rows": total_rows, "inserted": len(rows), "failed": 0, "status": "success",
            "uploaded_by": oleh, "uploaded_at": now_iso(),
            "catatan": f"{tidak_cocok} baris kelurahan tidak cocok master; {len(docs) - len(rows)} duplikat dibuang saat simpan"})
        return len(rows)


async def import_stunting(db, path: Path) -> Dict[str, Any]:
    rows = extract_stunting_rows(path)
    batch = str(uuid.uuid4())
    res = await build_stunting_docs(db, rows, path.name, batch)
    await save_stunting_docs(db, res["docs"], path.name, batch, res["baris"], res["kelurahan_tidak_cocok"])
    return {"baris": res["baris"], "diimpor": len(res["docs"]), "duplikat_dibuang": len(res["duplikat"]),
            "kelurahan_tidak_cocok": res["kelurahan_tidak_cocok"]}


async def import_musrenbang(db, path: Path) -> Dict[str, Any]:
    import docx

    d = docx.Document(str(path))
    docs = []
    for t in d.tables:
        for r in t.rows[1:]:
            c = [x.text.strip() for x in r.cells]
            if len(c) < 8 or not (c[1] or c[2]):
                continue
            docs.append({
                "id": str(uuid.uuid4()), "no": c[0].rstrip("."),
                "kelompok": c[1].strip().title(), "permasalahan": c[2], "kebutuhan": c[3],
                "usulan_kegiatan": c[4], "lokasi": c[5], "opd": c[6], "catatan_opd": c[7],
                "sumber": path.name, "tanggal_musrenbang": "2025-11-26", "created_at": now_iso(),
            })
    await db.musrenbang_usulan.delete_many({})
    if docs:
        await db.musrenbang_usulan.insert_many(docs)
    return {"diimpor": len(docs)}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stunting", action="store_true")
    ap.add_argument("--musrenbang", action="store_true")
    a = ap.parse_args()
    semua = not (a.stunting or a.musrenbang)
    db = MariaDocStore.from_env()
    if semua or a.stunting:
        p = next(DATA_DIR.glob("*STUNTING*.pdf"), None)
        print("stunting:", await import_stunting(db, p) if p else f"berkas PDF tidak ada di {DATA_DIR}")
    if semua or a.musrenbang:
        p = next(DATA_DIR.glob("*Musrenbang*.docx"), None)
        print("musrenbang:", await import_musrenbang(db, p) if p else f"berkas DOCX tidak ada di {DATA_DIR}")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
