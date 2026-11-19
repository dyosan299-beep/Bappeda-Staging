"""ETL impor & normalisasi data SIDATA.

Sumber (dari /app/data_upload/Bahan Website Ibu Kabid):
1. DTSEN per kelurahan (Kec. Makassar) & per kecamatan (Kec. Tallo) — 28 kolom.
2. Rekap data disabilitas per kelurahan (Kec. Tallo & Kec. Makassar).
3. Data disabilitas Dinkes (per SKPD/kecamatan, jenis kelamin, ragam, usia).
4. Matriks Kegiatan Stunting 2025-2027 (SKPD/program/kegiatan/sub kegiatan/anggaran).
5. Matriks RAD Penyandang Disabilitas 2025-2030.
6. Batas wilayah kelurahan (hasil konversi PETA_DASAR.gdb -> GeoJSON).

Prinsip:
- Struktur database TIDAK mengikuti nama file (master terpusat + tabel relasional).
- Baris mentah tetap disimpan (`raw_imports`) untuk audit.
- Setiap proses impor tercatat di `import_batches`, masalah data di `data_quality_issues`.
- Idempotent: menjalankan ulang tidak menduplikasi (dedupe kunci alami).

Jalankan: cd /app/backend && python etl_import.py [--reset]
"""
from __future__ import annotations

import asyncio
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from mariadb_store import MariaDocStore  # noqa: E402
import scoring  # noqa: E402
import dtsen_ref  # noqa: E402

DATA_DIR = Path(os.environ.get("DATA_UPLOAD_DIR", "/app/data_upload/Bahan Website Ibu Kabid"))
EXTRA_FILES = [Path("/app/data_upload/stunting.xlsx"), Path("/app/data_upload/rad_pd.xlsx")]
GEOJSON_PATH = ROOT / "assets" / "geo" / "kelurahan_makassar.geojson"

DTSEN_COLUMNS = [
    "nomor_kartu_keluarga", "kode_provinsi", "provinsi", "kode_kabupaten_kota",
    "kabupaten_kota", "kode_kecamatan", "kecamatan", "kode_kelurahan_desa",
    "kelurahan_desa", "alamat", "jumlah_anggota_keluarga", "nama_anggota_keluarga",
    "desil_nasional", "pbi_nas", "pbi_pemda", "status_kepemilikan_rumah",
    "jenis_lantai_terluas", "luas_lantai", "jenis_dinding_terluas",
    "jenis_atap_terluas", "sumber_air_minum_utama", "sumber_penerangan_utama",
    "daya_terpasang", "fasilitas_bab", "jenis_kloset", "pembuangan_akhir_tinja",
    "aset_tidak_bergerak_lahan_lainnya", "aset_tidak_bergerak_rumah_lainnya",
]

HOUSING_FIELDS = [
    "status_kepemilikan_rumah", "jenis_lantai_terluas", "luas_lantai",
    "jenis_dinding_terluas", "jenis_atap_terluas", "sumber_air_minum_utama",
    "sumber_penerangan_utama", "daya_terpasang", "fasilitas_bab", "jenis_kloset",
    "pembuangan_akhir_tinja", "aset_tidak_bergerak_lahan_lainnya",
    "aset_tidak_bergerak_rumah_lainnya",
]

# Field DTSEN yang berisi KODE numerik. Arti kode tidak ditebak oleh sistem:
# nilainya diekstrak dari data lalu diberi label oleh administrator.
CODED_FIELDS: Dict[str, str] = {
    "desil_nasional": "Desil Nasional",
    "pbi_nas": "PBI Nasional",
    "pbi_pemda": "PBI Pemerintah Daerah",
    "status_kepemilikan_rumah": "Status Kepemilikan Rumah",
    "jenis_lantai_terluas": "Jenis Lantai Terluas",
    "jenis_dinding_terluas": "Jenis Dinding Terluas",
    "jenis_atap_terluas": "Jenis Atap Terluas",
    "sumber_air_minum_utama": "Sumber Air Minum Utama",
    "sumber_penerangan_utama": "Sumber Penerangan Utama",
    "daya_terpasang": "Daya Terpasang",
    "fasilitas_bab": "Fasilitas BAB",
    "jenis_kloset": "Jenis Kloset",
    "pembuangan_akhir_tinja": "Pembuangan Akhir Tinja",
    "aset_tidak_bergerak_lahan_lainnya": "Aset Tidak Bergerak — Lahan Lainnya",
    "aset_tidak_bergerak_rumah_lainnya": "Aset Tidak Bergerak — Rumah Lainnya",
}


now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731


# --------------------------------------------------------------- util
def norm_name(value: Any) -> str:
    """Normalisasi nama wilayah: kapital, spasi tunggal, tanpa tanda baca ganda."""
    s = str(value or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.replace("’", "'").replace("`", "'")
    s = re.sub(r"[^A-Z0-9' -]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def title_name(value: Any) -> str:
    s = norm_name(value)
    return " ".join(w.capitalize() if not w.isdigit() else w for w in s.split())


def clean_val(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if pd.isna(v) if not isinstance(v, (list, dict)) else False:
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    if hasattr(v, "item"):
        try:
            v = v.item()
        except Exception:
            pass
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        return v.strip()
    return v


def num(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        f = float(str(v).replace(",", "").replace(" ", ""))
        return f
    except (TypeError, ValueError):
        return None


def as_int(v: Any) -> Optional[int]:
    f = num(v)
    return int(f) if f is not None else None


# Label baris rekapitulasi pada matriks Excel (bukan data kegiatan).
LABEL_BARIS_TOTAL = {
    "total", "jumlah", "total anggaran", "jumlah anggaran", "total keseluruhan",
    "jumlah keseluruhan", "grand total", "sub total", "subtotal", "total pagu",
}


def _is_baris_total(*labels: Any) -> bool:
    """True bila salah satu sel label berisi kata rekapitulasi (mis. 'Total')."""
    for v in labels:
        if v in (None, ""):
            continue
        teks = re.sub(r"\s+", " ", str(v)).strip().strip(":").lower()
        if teks in LABEL_BARIS_TOTAL:
            return True
    return False



def centroid_of(geometry: Any) -> Optional[Any]:
    """Titik pusat (centroid) polygon terbesar pada geometry GeoJSON.

    Dihitung dengan rumus shoelace; dipakai untuk marker agregat kelurahan
    berdasarkan batas wilayah resmi (bukan koordinat karangan).
    """
    if isinstance(geometry, str):
        try:
            geometry = json.loads(geometry.replace("'", '"'))
        except Exception:  # noqa: BLE001
            return None
    if not isinstance(geometry, dict):
        return None
    tipe = geometry.get("type")
    coords = geometry.get("coordinates") or []
    rings: List[Any] = []
    if tipe == "Polygon":
        rings = [coords[0]] if coords else []
    elif tipe == "MultiPolygon":
        rings = [poly[0] for poly in coords if poly]
    elif tipe == "Point" and len(coords) >= 2:
        return (round(float(coords[1]), 6), round(float(coords[0]), 6))
    if not rings:
        return None
    terbaik = None
    for ring in rings:
        pts = [(float(p[0]), float(p[1])) for p in ring if isinstance(p, (list, tuple)) and len(p) >= 2]
        if len(pts) < 3:
            continue
        a = cx = cy = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            f = x1 * y2 - x2 * y1
            a += f
            cx += (x1 + x2) * f
            cy += (y1 + y2) * f
        if abs(a) < 1e-12:
            continue
        a *= 0.5
        cx /= (6 * a)
        cy /= (6 * a)
        if terbaik is None or abs(a) > terbaik[0]:
            terbaik = (abs(a), cy, cx)  # (luas, lat, lng)
    if terbaik is None:
        return None
    return (round(terbaik[1], 6), round(terbaik[2], 6))


# --------------------------------------------------------------- ETL utama
class Importer:
    def __init__(self, db: MariaDocStore, reset: bool = False):
        self.db = db
        self.reset = reset
        self.batches: List[Dict[str, Any]] = []
        self.issues: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}
        self.duplicate_files: List[Any] = []

    # ---------- infrastruktur
    async def add_issue(self, jenis: str, entitas: str, keterangan: str,
                        ref: Optional[str] = None, batch_id: Optional[str] = None,
                        sample: Any = None):
        self.issues.append({
            "id": str(uuid.uuid4()), "jenis": jenis, "entitas": entitas,
            "keterangan": keterangan, "ref": ref or "", "batch_id": batch_id or "",
            "sample": json.dumps(sample, default=str)[:500] if sample is not None else "",
            "status": "open", "created_at": now_iso(),
        })

    async def new_batch(self, filename: str, sheet: str, jenis: str) -> Dict[str, Any]:
        batch = {
            "id": str(uuid.uuid4()), "filename": filename, "sheet": sheet,
            "jenis": jenis, "user": "etl-script", "uploaded_at": now_iso(),
            "total_rows": 0, "inserted": 0, "updated": 0, "duplicate": 0,
            "failed": 0, "errors": [], "status": "success",
        }
        self.batches.append(batch)
        return batch

    async def flush(self, collection: str, docs: List[Dict[str, Any]], chunk: int = 500):
        for i in range(0, len(docs), chunk):
            await getattr(self.db, collection).insert_many(docs[i:i + chunk])

    async def reset_collections(self, names: List[str]):
        for n in names:
            await getattr(self.db, n).delete_many({})

    # ---------- 1. Master wilayah dari GeoJSON + DTSEN
    async def import_wilayah_geo(self):
        if not GEOJSON_PATH.is_file():
            await self.add_issue("file_tidak_ada", "geo",
                                 f"GeoJSON batas kelurahan tidak ditemukan: {GEOJSON_PATH}")
            return
        gj = json.loads(GEOJSON_PATH.read_text())
        batch = await self.new_batch(GEOJSON_PATH.name, "kelurahan", "geo_batas_wilayah")
        docs = []
        for f in gj.get("features", []):
            p = f.get("properties") or {}
            kel = title_name(p.get("KELURAHAN"))
            kec = title_name(p.get("KECAMATAN"))
            docs.append({
                "id": str(uuid.uuid4()),
                "kelurahan": kel, "kelurahan_norm": norm_name(kel),
                "kecamatan": kec, "kecamatan_norm": norm_name(kec),
                "kota": title_name(p.get("KOTA")), "provinsi": title_name(p.get("PROVINSI")),
                "geometry": f.get("geometry"),
                "sumber": "PETA_DASAR.gdb / BATAS_ADMINISTRASI_AR",
                "import_batch": batch["id"], "created_at": now_iso(),
            })
        await self.db.geo_kelurahan.delete_many({})
        await self.flush("geo_kelurahan", docs)
        batch.update({"total_rows": len(docs), "inserted": len(docs)})
        self.summary["geo_kelurahan"] = len(docs)

    # ---------- 2. DTSEN
    def dtsen_files(self) -> List[Path]:
        """Semua berkas Excel (termasuk subfolder, mis. 'PILAH DTSEN KEC. MAKASSAR').

        Berkas dengan isi identik (md5 sama) hanya diambil satu kali agar tidak
        menghasilkan data ganda — kasus nyata: 'untuk GIS_DTSEN KEC.TALLO_Kaluku
        Bodoa.xlsx' identik dengan 'Pilah DTSEN KEC TALLO.xlsx'.
        """
        files: List[Path] = []
        for pattern in ("*.xlsx", "**/*.xlsx", "*.xls", "**/*.xls"):
            for p in sorted(DATA_DIR.glob(pattern)):
                if p.name.startswith("~$") or "_arsip" in p.parts:
                    continue
                files.append(p)
        unik: List[Path] = []
        by_hash: Dict[str, Path] = {}
        for p in sorted(set(files)):
            try:
                h = hashlib.md5(p.read_bytes()).hexdigest()
            except Exception:  # noqa: BLE001
                unik.append(p)
                continue
            kembar = by_hash.get(h)
            if kembar is not None:
                self.duplicate_files.append((p, kembar))
                continue
            by_hash[h] = p
            unik.append(p)
        return unik

    async def dtsen_sheets(self) -> List[Any]:
        """Kumpulkan sheet DTSEN per berkas, lalu buang sheet yang isinya
        merupakan bagian (subset) dari sheet lain.

        Contoh nyata: sheet 'Kaluku Bodoa' (3.049 KK) seluruhnya sudah termuat
        pada sheet 'TALLO' (19.106 KK) di berkas yang sama.
        Keluaran: [(path, [(nama_sheet, DataFrame), ...]), ...]
        """
        for p, kembar in self.duplicate_files:
            await self.add_issue(
                "berkas_duplikat", "dtsen",
                f"Berkas '{p.name}' isinya identik dengan '{kembar.name}' "
                "(md5 sama) — berkas dilewati agar data tidak ganda.",
                ref=p.name)
        kandidat: List[Dict[str, Any]] = []
        for path in self.dtsen_files():
            try:
                xl = pd.ExcelFile(path)
            except Exception as e:  # noqa: BLE001
                await self.add_issue("file_gagal_dibaca", "dtsen", f"{path.name}: {e}")
                continue
            for sheet in xl.sheet_names:
                try:
                    df = xl.parse(sheet)
                except Exception as e:  # noqa: BLE001
                    await self.add_issue("sheet_gagal_dibaca", "dtsen",
                                         f"{path.name}/{sheet}: {e}")
                    continue
                cols = [str(c).strip().lower() for c in df.columns]
                if "nomor_kartu_keluarga" not in cols or "kode_kelurahan_desa" not in cols:
                    continue  # bukan sheet DTSEN
                df.columns = cols
                keys = set()
                for kk, kel in zip(df["nomor_kartu_keluarga"], df["kode_kelurahan_desa"]):
                    k = str(clean_val(kk) or "").strip()
                    if not k:
                        continue
                    keys.add(f"{k}|{str(as_int(clean_val(kel)) or '').strip()}")
                kandidat.append({"path": path, "sheet": sheet, "df": df, "keys": keys})

        kandidat.sort(key=lambda c: -len(c["keys"]))  # sheet induk (terbesar) lebih dulu
        dipakai: List[Dict[str, Any]] = []
        dilewati = 0
        for c in kandidat:
            induk = next((h for h in dipakai if c["keys"] and c["keys"] <= h["keys"]), None)
            if induk is not None:
                dilewati += 1
                await self.add_issue(
                    "sheet_duplikat", "dtsen",
                    f"Sheet '{c['sheet']}' ({c['path'].name}, {len(c['keys'])} KK) "
                    f"seluruhnya sudah termuat pada sheet '{induk['sheet']}' "
                    f"({induk['path'].name}) — sheet dilewati agar data tidak ganda.",
                    ref=f"{c['path'].name}/{c['sheet']}")
                continue
            dipakai.append(c)
        self.summary["sheet_dilewati"] = dilewati
        self.summary["berkas_duplikat"] = len(self.duplicate_files)

        grup: Dict[Path, List[Any]] = {}
        for c in dipakai:
            grup.setdefault(c["path"], []).append((c["sheet"], c["df"]))
        return [(p, sheets) for p, sheets in grup.items()]

    async def import_dtsen(self):
        seen_kk: Dict[str, str] = {}
        households: List[Dict[str, Any]] = []
        raws: List[Dict[str, Any]] = []
        members: List[Dict[str, Any]] = []
        villages: Dict[str, Dict[str, Any]] = {}
        districts: Dict[str, Dict[str, Any]] = {}
        cities: Dict[str, Dict[str, Any]] = {}
        provinces: Dict[str, Dict[str, Any]] = {}
        cfg = scoring.default_config()
        total_rows = 0

        for path, sheets in await self.dtsen_sheets():
            for sheet, df in sheets:
                cols = list(df.columns)
                batch = await self.new_batch(path.name, sheet, "dtsen")
                batch["total_rows"] = len(df)
                total_rows += len(df)
                missing = [c for c in DTSEN_COLUMNS if c not in cols]
                if missing:
                    await self.add_issue("kolom_hilang", "dtsen",
                                         f"{path.name}/{sheet}: kolom tidak ada: {', '.join(missing)}",
                                         batch_id=batch["id"])

                for rec in df.to_dict("records"):
                    row = {k: clean_val(v) for k, v in rec.items()}
                    kk = str(row.get("nomor_kartu_keluarga") or "").strip()
                    kode_kel = str(as_int(row.get("kode_kelurahan_desa")) or "").strip()
                    kel_name = title_name(row.get("kelurahan_desa"))
                    kec_name = title_name(row.get("kecamatan"))
                    kode_kec = str(as_int(row.get("kode_kecamatan")) or "").strip()
                    kode_kota = str(as_int(row.get("kode_kabupaten_kota")) or "").strip()
                    kode_prov = str(as_int(row.get("kode_provinsi")) or "").strip()

                    # simpan mentah untuk audit
                    raws.append({
                        "id": str(uuid.uuid4()), "jenis": "dtsen", "import_batch": batch["id"],
                        "file": path.name, "sheet": sheet, "row": row,
                        "created_at": now_iso(),
                    })

                    if not kk or not kode_kel:
                        batch["failed"] += 1
                        await self.add_issue("data_tidak_valid", "households",
                                             "Baris tanpa nomor KK / kode kelurahan",
                                             batch_id=batch["id"], sample=row)
                        continue

                    # master wilayah
                    if kode_prov:
                        provinces.setdefault(kode_prov, {
                            "id": kode_prov, "kode": kode_prov,
                            "nama": title_name(row.get("provinsi")), "created_at": now_iso()})
                    if kode_kota:
                        cities.setdefault(kode_kota, {
                            "id": kode_kota, "kode": kode_kota,
                            "nama": title_name(row.get("kabupaten_kota")),
                            "kode_provinsi": kode_prov, "created_at": now_iso()})
                    if kode_kec:
                        districts.setdefault(kode_kec, {
                            "id": kode_kec, "kode": kode_kec, "nama": kec_name,
                            "nama_norm": norm_name(kec_name), "kode_kabupaten_kota": kode_kota,
                            "created_at": now_iso()})
                    v = villages.setdefault(kode_kel, {
                        "id": kode_kel, "kode": kode_kel, "nama": kel_name,
                        "nama_norm": norm_name(kel_name), "kode_kecamatan": kode_kec,
                        "kecamatan": kec_name, "kode_kabupaten_kota": kode_kota,
                        "aliases": [], "created_at": now_iso()})
                    if norm_name(kel_name) != v["nama_norm"] and kel_name not in v["aliases"]:
                        v["aliases"].append(kel_name)
                        await self.add_issue(
                            "nama_wilayah_tidak_konsisten", "villages",
                            f"Kode {kode_kel} punya variasi nama: {v['nama']} vs {kel_name}",
                            ref=kode_kel, batch_id=batch["id"])

                    dedupe_key = f"{kk}|{kode_kel}"
                    if dedupe_key in seen_kk:
                        batch["duplicate"] += 1
                        await self.add_issue(
                            "duplikat", "households",
                            f"Nomor KK {scoring.mask_kk(kk)} sudah diimpor dari sumber lain",
                            ref=dedupe_key, batch_id=batch["id"])
                        continue
                    seen_kk[dedupe_key] = batch["id"]

                    score, level, factors, levels, perlu_validasi = scoring.score_household(row, cfg)
                    flags = scoring.summarize_levels(levels)
                    hid = str(uuid.uuid4())
                    doc: Dict[str, Any] = {
                        "id": hid,
                        "no_kk": kk,
                        "no_kk_mask": scoring.mask_kk(kk),
                        "kode_provinsi": kode_prov,
                        "provinsi": title_name(row.get("provinsi")),
                        "kode_kabupaten_kota": kode_kota,
                        "kabupaten_kota": title_name(row.get("kabupaten_kota")),
                        "kode_kecamatan": kode_kec,
                        "kecamatan": kec_name,
                        "kode_kelurahan": kode_kel,
                        "kelurahan": kel_name,
                        "alamat": row.get("alamat") or "",
                        "jumlah_anggota_keluarga": as_int(row.get("jumlah_anggota_keluarga")) or 0,
                        "kepala_keluarga": str(row.get("nama_anggota_keluarga") or "").strip(),
                        "desil_nasional": as_int(row.get("desil_nasional")),
                        "pbi_nas": as_int(row.get("pbi_nas")) or 0,
                        "pbi_pemda": as_int(row.get("pbi_pemda")) or 0,
                        "risk_score": score,
                        "risk_level": level,
                        "risk_factors": factors,
                        "indikator_level": levels,
                        "perlu_validasi": bool(perlu_validasi),
                        "source_file": path.name,
                        "source_sheet": sheet,
                        "import_batch": batch["id"],
                        "imported_at": now_iso(),
                    }
                    for f in HOUSING_FIELDS:
                        doc[f] = row.get(f)
                    # GeoTag-Verval (aditif): RT/RW hanya bila ada kolom eksplisit di sumber,
                    # referensi stabil no_kk+kode_kelurahan (tidak berubah walau UUID baru)
                    rt, rw = dtsen_ref.norm_rt_rw(row.get("rt")), dtsen_ref.norm_rt_rw(row.get("rw"))
                    if rt or rw:
                        doc.update({"rt": rt, "rw": rw, "rt_rw_sumber": "kolom_berkas_sumber"})
                    ref = dtsen_ref.make_ref(kk, kode_kel, kel_name)
                    if ref:
                        doc["dtsen_ref"] = ref
                    doc.update(flags)
                    households.append(doc)
                    batch["inserted"] += 1

                    nama = doc["kepala_keluarga"]
                    if nama:
                        members.append({
                            "id": str(uuid.uuid4()), "household_id": hid, "no_kk": kk,
                            "nama": nama, "peran": "Kepala Keluarga",
                            "kode_kelurahan": kode_kel, "import_batch": batch["id"],
                            "created_at": now_iso(),
                        })

        await self.reset_collections(["households", "household_members", "villages",
                                      "districts", "cities", "provinces"])
        await self.db.raw_imports.delete_many({"jenis": "dtsen"})
        await self.flush("households", households)
        await self.flush("household_members", members)
        await self.flush("villages", list(villages.values()))
        await self.flush("districts", list(districts.values()))
        await self.flush("cities", list(cities.values()))
        await self.flush("provinces", list(provinces.values()))
        await self.flush("raw_imports", raws, chunk=300)
        self.summary["dtsen_rows"] = total_rows
        self.summary["households"] = len(households)
        self.summary["household_members"] = len(members)
        self.summary["villages"] = len(villages)
        self.summary["districts"] = len(districts)

    # ---------- 3. Disabilitas
    async def import_disabilitas(self):
        region_docs: List[Dict[str, Any]] = []
        opd_docs: List[Dict[str, Any]] = []

        # a. rekap per kelurahan
        p = DATA_DIR / "DATA DISABILITAS_KEC.TALLO_Kec.MAKASSAR.xlsx"
        if p.is_file():
            batch = await self.new_batch(p.name, "Sheet1", "disabilitas_wilayah")
            df = pd.read_excel(p, sheet_name=0, header=None)
            batch["total_rows"] = len(df)
            kec_current = ""
            for _, r in df.iterrows():
                vals = [clean_val(v) for v in list(r)]
                while len(vals) < 4:
                    vals.append(None)
                no, kec, kel, jml = vals[0], vals[1], vals[2], vals[3]
                if isinstance(kec, str) and kec.strip() and str(kec).upper() not in ("KECAMATAN",):
                    kec_current = title_name(kec)
                if not kel or (isinstance(kel, str) and not kel.strip()):
                    continue
                if str(kel).strip().upper() == "KELURAHAN":
                    continue
                total = as_int(jml)
                if total is None:
                    continue
                region_docs.append({
                    "id": str(uuid.uuid4()), "kecamatan": kec_current,
                    "kecamatan_norm": norm_name(kec_current),
                    "kelurahan": title_name(kel), "kelurahan_norm": norm_name(kel),
                    "jumlah": total, "tahun": 2026,
                    "sumber": p.name, "import_batch": batch["id"], "created_at": now_iso(),
                })
                batch["inserted"] += 1

        # b. rekap Dinkes per SKPD/kecamatan (ragam, jenis kelamin, usia)
        p2 = DATA_DIR / "PERMINTAAN DATA DISABILITAS DINKES SEPTEMBER 2026.xlsx"
        if p2.is_file():
            batch = await self.new_batch(p2.name, "Sheet2", "disabilitas_ragam")
            df = pd.read_excel(p2, sheet_name="Sheet2", header=None)
            batch["total_rows"] = len(df)
            for _, r in df.iterrows():
                vals = [clean_val(v) for v in list(r)]
                while len(vals) < 14:
                    vals.append(None)
                no, skpd = vals[0], vals[1]
                if not isinstance(skpd, str) or not skpd.strip():
                    continue
                if skpd.strip().upper() in ("SKPD", "JUMLAH", "TOTAL"):
                    continue
                nama_skpd = str(skpd).strip()
                kec = title_name(re.sub(r"^Kecamatan\s+", "", nama_skpd, flags=re.I))
                doc = {
                    "id": str(uuid.uuid4()), "skpd": nama_skpd,
                    "kecamatan": kec if nama_skpd.lower().startswith("kecamatan") else "",
                    "kecamatan_norm": norm_name(kec) if nama_skpd.lower().startswith("kecamatan") else "",
                    "laki_laki": as_int(vals[2]) or 0,
                    "perempuan": as_int(vals[3]) or 0,
                    "memilih_untuk_tidak_menjawab": as_int(vals[4]) or 0,
                    "ragam": {
                        "Fisik": as_int(vals[5]) or 0,
                        "Ganda": as_int(vals[6]) or 0,
                        "Intelektual": as_int(vals[7]) or 0,
                        "Mental": as_int(vals[8]) or 0,
                        "Sensorik Pendengaran": as_int(vals[9]) or 0,
                        "Sensorik Penglihatan": as_int(vals[10]) or 0,
                    },
                    "usia_dibawah_18": as_int(vals[11]) or 0,
                    "usia_18_59": as_int(vals[12]) or 0,
                    "tahun": 2026, "sumber": p2.name,
                    "import_batch": batch["id"], "created_at": now_iso(),
                }
                doc["total"] = doc["laki_laki"] + doc["perempuan"] + doc["memilih_untuk_tidak_menjawab"]
                opd_docs.append(doc)
                batch["inserted"] += 1

        await self.reset_collections(["disability_region_stats", "disability_opd_stats"])
        await self.flush("disability_region_stats", region_docs)
        await self.flush("disability_opd_stats", opd_docs)
        self.summary["disability_region_stats"] = len(region_docs)
        self.summary["disability_opd_stats"] = len(opd_docs)
        await self.add_issue(
            "data_belum_tersedia", "disability_profiles",
            "Data individu penyandang disabilitas (nama/usia/ragam per orang) belum ada "
            "pada file yang diunggah; hanya tersedia rekap agregat per wilayah & SKPD.")

    # ---------- 4. Matriks Stunting
    async def import_stunting(self):
        path = next((p for p in EXTRA_FILES if "stunting" in p.name.lower() and p.is_file()), None)
        if path is None:
            cand = list(DATA_DIR.glob("*Stunting*.xlsx"))
            path = cand[0] if cand else None
        if path is None:
            await self.add_issue("file_tidak_ada", "stunting", "File matriks stunting tidak ditemukan")
            return
        batch = await self.new_batch(path.name, "Sheet1", "stunting")
        try:
            df = pd.read_excel(path, sheet_name=0, header=None)
        except Exception as e:  # noqa: BLE001
            await self.add_issue("file_gagal_dibaca", "stunting",
                                 f"{path.name}: {e}", batch_id=batch["id"])
            return
        batch["total_rows"] = len(df)

        programs: Dict[str, Dict[str, Any]] = {}
        activities: Dict[str, Dict[str, Any]] = {}
        subs: List[Dict[str, Any]] = []
        opds: Dict[str, Dict[str, Any]] = {}
        budgets: List[Dict[str, Any]] = []
        indicators: List[Dict[str, Any]] = []

        cur = {"no": None, "skpd": None, "program": None, "kegiatan": None}
        baris_total = 0
        for _, r in df.iterrows():
            vals = [clean_val(v) for v in list(r)]
            while len(vals) < 9:
                vals.append(None)
            no, skpd, program, kegiatan, sub, indikator, a2025, a2026, t2027 = vals[:9]
            if isinstance(no, str) and no.strip().upper() == "NO":
                continue
            if isinstance(skpd, str) and skpd.strip().upper() == "NAMA SKPD":
                continue
            if not any([sub, indikator, a2025, a2026, t2027]) and not program:
                continue
            # Baris rekapitulasi ("Total"/"Jumlah") pada akhir matriks bukan sub kegiatan;
            # bila ikut terbaca, anggaran akan terhitung dua kali.
            if _is_baris_total(sub, indikator, skpd, program, kegiatan):
                baris_total += 1
                continue
            if no is not None:
                cur["no"] = no
            if skpd:
                cur["skpd"] = str(skpd).strip()
            if program:
                cur["program"] = str(program).strip()
            if kegiatan:
                cur["kegiatan"] = str(kegiatan).strip()
            if not sub and not indikator:
                continue
            if not cur["skpd"]:
                continue

            opd_key = norm_name(cur["skpd"])
            opd = opds.setdefault(opd_key, {
                "id": str(uuid.uuid4()), "nama": cur["skpd"], "nama_norm": opd_key,
                "jenis": "OPD", "created_at": now_iso()})
            prog_key = f"{opd_key}|{norm_name(cur['program'])}"
            prog = programs.setdefault(prog_key, {
                "id": str(uuid.uuid4()), "nama": cur["program"] or "-", "opd_id": opd["id"],
                "opd": opd["nama"], "created_at": now_iso()})
            act_key = f"{prog_key}|{norm_name(cur['kegiatan'])}"
            act = activities.setdefault(act_key, {
                "id": str(uuid.uuid4()), "nama": cur["kegiatan"] or "-",
                "program_id": prog["id"], "program": prog["nama"],
                "opd_id": opd["id"], "opd": opd["nama"], "created_at": now_iso()})

            sub_id = str(uuid.uuid4())
            anggaran_2025 = num(a2025) or 0.0
            anggaran_2026 = num(a2026) or 0.0
            subs.append({
                "id": sub_id, "nomor": cur["no"], "nama": str(sub or "-").strip(),
                "activity_id": act["id"], "kegiatan": act["nama"],
                "program_id": prog["id"], "program": prog["nama"],
                "opd_id": opd["id"], "opd": opd["nama"],
                "indikator": str(indikator or "").strip(),
                "anggaran_2025": anggaran_2025, "anggaran_2026": anggaran_2026,
                "target_2027": clean_val(t2027),
                "import_batch": batch["id"], "created_at": now_iso(),
            })
            if indikator:
                indicators.append({
                    "id": str(uuid.uuid4()), "subactivity_id": sub_id,
                    "nama": str(indikator).strip(), "opd": opd["nama"],
                    "program": prog["nama"], "created_at": now_iso()})
            for tahun, nilai in (("2025", anggaran_2025), ("2026", anggaran_2026)):
                budgets.append({
                    "id": str(uuid.uuid4()), "subactivity_id": sub_id, "tahun": tahun,
                    "nilai": nilai, "opd": opd["nama"], "program": prog["nama"],
                    "created_at": now_iso()})
            batch["inserted"] += 1

        await self.reset_collections(["stunting_programs", "stunting_activities",
                                      "stunting_subactivities", "stunting_indicators",
                                      "stunting_budgets"])
        # OPD master digabung (stunting + RAD)
        for coll, docs in (("stunting_programs", list(programs.values())),
                           ("stunting_activities", list(activities.values())),
                           ("stunting_subactivities", subs),
                           ("stunting_indicators", indicators),
                           ("stunting_budgets", budgets)):
            await self.flush(coll, docs)
        await self.upsert_opd(list(opds.values()))
        self.summary["stunting_subactivities"] = len(subs)
        self.summary["stunting_programs"] = len(programs)
        self.summary["stunting_activities"] = len(activities)
        self.summary["stunting_anggaran_2025"] = sum(s["anggaran_2025"] for s in subs)
        self.summary["stunting_anggaran_2026"] = sum(s["anggaran_2026"] for s in subs)
        if baris_total:
            self.summary["stunting_baris_total_dilewati"] = baris_total

    async def upsert_opd(self, docs: List[Dict[str, Any]]):
        for d in docs:
            existing = await self.db.opd.find_one({"nama_norm": d["nama_norm"]})
            if existing is None:
                await self.db.opd.insert_one(d)

    # ---------- 5. Matriks RAD Penyandang Disabilitas
    @staticmethod
    def _is_rad_filename(stem: str) -> bool:
        """RAD sebagai kata utuh saja.

        Penting: pola lama `*RAD*` ikut menangkap berkas DTSEN kelurahan seperti
        "MARADEKAYA.xlsx" / "MARADEKAYA SELATAN.xlsx" sehingga ETL gagal.
        """
        low = stem.lower()
        if "matriks_rad" in low or "matriks rad" in low:
            return True
        return bool(re.search(r"(?:^|[^a-z])rad(?:[^a-z]|$)", low))

    def rad_candidates(self) -> List[Path]:
        cands = [p for p in EXTRA_FILES if "rad" in p.name.lower() and p.is_file()]
        for p in sorted(DATA_DIR.glob("*.xlsx")):
            if p.name.startswith("~$"):
                continue
            if self._is_rad_filename(p.stem):
                cands.append(p)
        return cands

    async def import_rad(self):
        path = None
        sheet = None
        for cand in self.rad_candidates():
            try:
                names = pd.ExcelFile(cand).sheet_names
            except Exception as e:  # noqa: BLE001
                await self.add_issue("file_gagal_dibaca", "rad", f"{cand.name}: {e}")
                continue
            target = next((s for s in names if "2025-2030" in str(s)), None)
            if target:
                path, sheet = cand, target
                break
        if path is None:
            await self.add_issue(
                "file_tidak_ada", "rad",
                "File matriks RAD (sheet '2025-2030') tidak ditemukan pada folder data.")
            return
        batch = await self.new_batch(path.name, sheet, "rad_disabilitas")
        try:
            df = pd.read_excel(path, sheet_name=sheet, header=None)
        except Exception as e:  # noqa: BLE001
            await self.add_issue("sheet_gagal_dibaca", "rad",
                                 f"{path.name}/{sheet}: {e}", batch_id=batch["id"])
            return
        batch["total_rows"] = len(df)
        tahun_cols = {10: "2025", 11: "2026", 12: "2027", 13: "2028", 14: "2029", 15: "2030"}

        strategies: List[Dict[str, Any]] = []
        items: List[Dict[str, Any]] = []
        yearly: List[Dict[str, Any]] = []
        monitoring: List[Dict[str, Any]] = []
        cur_sasaran = ""
        cur_kebijakan = ""

        for _, r in df.iterrows():
            vals = [clean_val(v) for v in list(r)]
            while len(vals) < 16:
                vals.append(None)
            c0 = str(vals[0] or "").strip()
            if c0.lower().startswith("strategi implementasi"):
                continue
            has_program = bool(vals[2]) or bool(vals[3]) or bool(vals[4])
            if c0 and not has_program:
                low = c0.lower()
                if low.startswith("sasaran strategis"):
                    cur_sasaran = c0
                    strategies.append({
                        "id": str(uuid.uuid4()), "jenis": "sasaran_strategis", "nama": c0,
                        "parent": "", "import_batch": batch["id"], "created_at": now_iso()})
                elif low.startswith("kebijakan"):
                    cur_kebijakan = c0
                    strategies.append({
                        "id": str(uuid.uuid4()), "jenis": "kebijakan", "nama": c0,
                        "parent": cur_sasaran, "import_batch": batch["id"],
                        "created_at": now_iso()})
                continue
            if not has_program:
                continue

            item_id = str(uuid.uuid4())
            targets = {}
            for idx, tahun in tahun_cols.items():
                v = num(vals[idx])
                targets[tahun] = v
                if v is not None:
                    yearly.append({
                        "id": str(uuid.uuid4()), "item_id": item_id, "tahun": tahun,
                        "target": v, "satuan": str(vals[9] or "").strip(),
                        "created_at": now_iso()})
            items.append({
                "id": item_id,
                "sasaran_strategis": cur_sasaran,
                "kebijakan": cur_kebijakan,
                "strategi_implementasi": c0,
                "target_capaian": str(vals[1] or "").strip(),
                "program": str(vals[2] or "").strip(),
                "kegiatan": str(vals[3] or "").strip(),
                "sub_kegiatan": str(vals[4] or "").strip(),
                "indikator_capaian": str(vals[5] or "").strip(),
                "output_kegiatan": str(vals[6] or "").strip(),
                "indikator_disabilitas": str(vals[7] or "").strip(),
                "hambatan": str(vals[8] or "").strip(),
                "satuan": str(vals[9] or "").strip(),
                "targets": targets,
                "opd": "",  # tidak eksplisit pada sheet ini
                "import_batch": batch["id"], "created_at": now_iso(),
            })
            monitoring.append({
                "id": str(uuid.uuid4()), "item_id": item_id, "status": "Belum Dimulai",
                "progress": 0, "catatan": "", "dokumen": "", "penanggung_jawab": "",
                "updated_at": now_iso(),
            })
            batch["inserted"] += 1

        await self.reset_collections(["rad_strategies", "rad_items", "rad_yearly_targets",
                                      "rad_monitoring"])
        await self.flush("rad_strategies", strategies)
        await self.flush("rad_items", items)
        await self.flush("rad_yearly_targets", yearly)
        await self.flush("rad_monitoring", monitoring)
        self.summary["rad_items"] = len(items)
        self.summary["rad_strategies"] = len(strategies)
        await self.add_issue(
            "perlu_validasi", "rad_items",
            "Kolom OPD/penanggung jawab tidak tersedia pada sheet RAD '2025-2030 (baru)'. "
            "Nilai dibiarkan kosong dan perlu dilengkapi lewat menu Monitoring.")

    # ---------- 6. Agregasi & integrasi
    async def build_aggregates(self):
        households = await self.db.households.find({}).to_list(200000)
        villages = {v["kode"]: v for v in await self.db.villages.find({}).to_list(1000)}
        dis_region = await self.db.disability_region_stats.find({}).to_list(1000)
        dis_by_kel = {}
        for d in dis_region:
            dis_by_kel[d.get("kelurahan_norm")] = dis_by_kel.get(d.get("kelurahan_norm"), 0) + int(d.get("jumlah") or 0)

        vstats: Dict[str, Dict[str, Any]] = {}
        for h in households:
            kode = h.get("kode_kelurahan")
            v = vstats.setdefault(kode, {
                "id": kode, "kode_kelurahan": kode,
                "kelurahan": h.get("kelurahan"), "kecamatan": h.get("kecamatan"),
                "kode_kecamatan": h.get("kode_kecamatan"),
                "total_households": 0, "total_individu": 0,
                "per_desil": {}, "per_risk": {}, "pbi_nas": 0, "pbi_pemda": 0,
                "rumah_rentan": 0, "sanitasi_tidak_layak": 0, "air_rentan": 0,
                "hunian_rentan": 0, "listrik_rentan": 0, "perlu_validasi": 0,
                "sum_risk": 0.0, "updated_at": now_iso(),
            })
            v["total_households"] += 1
            v["total_individu"] += int(h.get("jumlah_anggota_keluarga") or 0)
            d = str(h.get("desil_nasional") or "-")
            v["per_desil"][d] = v["per_desil"].get(d, 0) + 1
            lvl = h.get("risk_level") or "rendah"
            v["per_risk"][lvl] = v["per_risk"].get(lvl, 0) + 1
            v["pbi_nas"] += 1 if int(h.get("pbi_nas") or 0) == 1 else 0
            v["pbi_pemda"] += 1 if int(h.get("pbi_pemda") or 0) == 1 else 0
            v["rumah_rentan"] += 1 if h.get("rumah_rentan") else 0
            v["sanitasi_tidak_layak"] += 1 if h.get("sanitasi_rentan") else 0
            v["air_rentan"] += 1 if h.get("air_rentan") else 0
            v["hunian_rentan"] += 1 if h.get("hunian_rentan") else 0
            v["listrik_rentan"] += 1 if h.get("listrik_rentan") else 0
            v["perlu_validasi"] += 1 if h.get("perlu_validasi") else 0
            v["sum_risk"] += float(h.get("risk_score") or 0)

        for v in vstats.values():
            n = max(v["total_households"], 1)
            v["avg_risk"] = round(v["sum_risk"] / n, 2)
            v["desil_1_2"] = int(v["per_desil"].get("1", 0)) + int(v["per_desil"].get("2", 0))
            v["persen_desil_1_2"] = round(v["desil_1_2"] * 100.0 / n, 2)
            v["persen_rumah_rentan"] = round(v["rumah_rentan"] * 100.0 / n, 2)
            v["prioritas_tinggi"] = int(v["per_risk"].get("sangat_tinggi", 0)) + \
                int(v["per_risk"].get("tinggi", 0))
            v["disabilitas"] = dis_by_kel.get(norm_name(v["kelurahan"]), 0)
            # skor prioritas wilayah (0-100)
            v["skor_prioritas"] = round(min(100.0, (
                0.40 * v["avg_risk"]
                + 0.25 * v["persen_desil_1_2"]
                + 0.20 * v["persen_rumah_rentan"]
                + 0.15 * min(100.0, v["disabilitas"] / 5.0)
            )), 2)
            v.pop("sum_risk", None)
            geo = await self.db.geo_kelurahan.find_one({"kelurahan_norm": norm_name(v["kelurahan"])})
            v["punya_batas_wilayah"] = bool(geo)
            if not geo:
                await self.add_issue(
                    "kode_wilayah_tidak_sesuai", "geo_kelurahan",
                    f"Kelurahan '{v['kelurahan']}' (kode {v['kode_kelurahan']}) tidak "
                    "ditemukan pada batas wilayah GeoJSON — perlu pencocokan manual.",
                    ref=v["kode_kelurahan"])

        dstats: Dict[str, Dict[str, Any]] = {}
        for v in vstats.values():
            kode_kec = v["kode_kecamatan"]
            d = dstats.setdefault(kode_kec, {
                "id": kode_kec, "kode_kecamatan": kode_kec, "kecamatan": v["kecamatan"],
                "total_households": 0, "total_individu": 0, "per_desil": {},
                "per_risk": {}, "pbi_nas": 0, "pbi_pemda": 0, "rumah_rentan": 0,
                "sanitasi_tidak_layak": 0, "air_rentan": 0, "hunian_rentan": 0,
                "disabilitas": 0, "jumlah_kelurahan": 0, "sum_risk": 0.0,
                "updated_at": now_iso(),
            })
            d["jumlah_kelurahan"] += 1
            for key in ("total_households", "total_individu", "pbi_nas", "pbi_pemda",
                        "rumah_rentan", "sanitasi_tidak_layak", "air_rentan",
                        "hunian_rentan", "disabilitas"):
                d[key] += v.get(key, 0)
            for dk, dv in v["per_desil"].items():
                d["per_desil"][dk] = d["per_desil"].get(dk, 0) + dv
            for rk, rv in v["per_risk"].items():
                d["per_risk"][rk] = d["per_risk"].get(rk, 0) + rv
            d["sum_risk"] += v["avg_risk"] * v["total_households"]

        for d in dstats.values():
            n = max(d["total_households"], 1)
            d["avg_risk"] = round(d["sum_risk"] / n, 2)
            d["desil_1_2"] = int(d["per_desil"].get("1", 0)) + int(d["per_desil"].get("2", 0))
            d["persen_desil_1_2"] = round(d["desil_1_2"] * 100.0 / n, 2)
            d["persen_rumah_rentan"] = round(d["rumah_rentan"] * 100.0 / n, 2)
            d.pop("sum_risk", None)

        await self.reset_collections(["village_stats", "district_stats"])
        await self.flush("village_stats", list(vstats.values()))
        await self.flush("district_stats", list(dstats.values()))
        self.summary["village_stats"] = len(vstats)
        self.summary["district_stats"] = len(dstats)

    # ---------- 6. Master kode referensi (arti kode diisi administrator)
    async def extract_kode_referensi(self):
        """Ekstrak seluruh nilai kode yang benar-benar ADA di data DTSEN.

        Arti kode TIDAK ditebak: label dibiarkan kosong agar administrator
        mengisinya dari halaman Master Kode. Label yang sudah pernah diisi
        tidak akan tertimpa saat ETL dijalankan ulang.
        """
        households = await self.db.households.find({}).to_list(200000)
        hitung: Dict[str, Dict[str, int]] = {}
        for h in households:
            for f in CODED_FIELDS:
                v = h.get(f)
                if v is None or str(v).strip() == "" or str(v).lower() in ("none", "nan"):
                    kode = "(kosong)"
                else:
                    iv = as_int(v)
                    kode = str(iv) if iv is not None else str(v).strip()
                hitung.setdefault(f, {})
                hitung[f][kode] = hitung[f].get(kode, 0) + 1

        lama = {d["id"]: d for d in await self.db.kode_referensi.find({}).to_list(5000)}
        docs: List[Dict[str, Any]] = []
        for f, nilai in hitung.items():
            for kode, jumlah in sorted(nilai.items(), key=lambda x: (len(x[0]), x[0])):
                _id = f"{f}::{kode}"
                sebelum = lama.get(_id) or {}
                docs.append({
                    "id": _id,
                    "field": f,
                    "field_label": CODED_FIELDS[f],
                    "kode": kode,
                    "label": sebelum.get("label") or "",
                    "keterangan": sebelum.get("keterangan") or "",
                    "jumlah_data": jumlah,
                    "sumber": "ekstraksi_dtsen",
                    "updated_at": now_iso(),
                    "updated_by": sebelum.get("updated_by") or "",
                })
        await self.reset_collections(["kode_referensi"])
        await self.flush("kode_referensi", docs)
        self.summary["kode_referensi"] = len(docs)
        belum = len([d for d in docs if not d["label"]])
        if belum:
            await self.add_issue(
                "kode_belum_didefinisikan", "kode_referensi",
                f"{belum} kode DTSEN belum memiliki keterangan arti. Isi pada menu "
                "Administrasi → Master Kode Referensi agar tampil sebagai teks di "
                "dashboard, tabel, dan detail data.")

    # ---------- 7. Titik koordinat kelurahan (centroid batas wilayah resmi)
    async def build_gis_locations(self):
        """Isi `gis_locations` dari titik pusat polygon kelurahan resmi (BIG).

        Koordinat TIDAK dikarang: nilainya dihitung dari batas wilayah resmi
        (Peta Dasar Kota Makassar Edisi 2021, BIG). Titik yang sudah disunting
        manual oleh operator (sumber = 'manual') tidak ditimpa.
        """
        geos = await self.db.geo_kelurahan.find({}).to_list(1000)
        by_norm = {g.get("kelurahan_norm"): g for g in geos}
        manual = {d.get("kelurahan_norm"): d for d in
                  await self.db.gis_locations.find({"sumber": "manual"}).to_list(1000)}
        vstats = await self.db.village_stats.find({}).to_list(1000)
        docs: List[Dict[str, Any]] = []
        tanpa_geo = 0
        for v in vstats:
            norm = norm_name(v.get("kelurahan"))
            if norm in manual:
                docs.append(manual[norm])
                continue
            g = by_norm.get(norm)
            if not g:
                tanpa_geo += 1
                continue
            titik = centroid_of(g.get("geometry"))
            if not titik:
                tanpa_geo += 1
                continue
            lat, lng = titik
            docs.append({
                "id": str(uuid.uuid4()),
                "kelurahan": v.get("kelurahan"),
                "kelurahan_norm": norm,
                "kecamatan": v.get("kecamatan"),
                "kode_kelurahan": v.get("kode_kelurahan"),
                "latitude": lat,
                "longitude": lng,
                "sumber": "centroid_batas_wilayah_big",
                "keterangan": "Titik pusat polygon batas kelurahan resmi (BIG 2021)",
                "luas_ha": g.get("luas_ha"),
                "updated_at": now_iso(),
            })
        await self.reset_collections(["gis_locations"])
        await self.flush("gis_locations", docs)
        self.summary["gis_locations"] = len(docs)
        if tanpa_geo:
            await self.add_issue(
                "koordinat_belum_tersedia", "gis_locations",
                f"{tanpa_geo} kelurahan belum memiliki titik koordinat karena batas "
                "wilayahnya tidak ditemukan — dapat diisi manual pada menu GIS.")

    # ---------- jalankan semua
    async def run(self):
        await self.db.connect()
        await self.db.ping()
        cfg = await self.db.scoring_config.find_one({"id": "default"})
        if cfg is None:
            await self.db.scoring_config.insert_one(scoring.default_config())
        await self.db.data_quality_issues.delete_many({})
        await self.db.import_batches.delete_many({})

        # Tiap tahap diisolasi: kegagalan satu berkas tidak boleh menggagalkan
        # seluruh proses impor (dicatat sebagai isu kualitas data).
        steps = [
            ("geo", self.import_wilayah_geo),
            ("dtsen", self.import_dtsen),
            ("disabilitas", self.import_disabilitas),
            ("stunting", self.import_stunting),
            ("rad", self.import_rad),
        ]
        for nama, fn in steps:
            try:
                await fn()
            except Exception as e:  # noqa: BLE001
                await self.add_issue("tahap_gagal", nama,
                                     f"Tahap impor '{nama}' gagal: {type(e).__name__}: {e}")
                print(f"[PERINGATAN] tahap {nama} gagal: {e}")
        await self.build_aggregates()
        for nama, fn in (("kode_referensi", self.extract_kode_referensi),
                         ("gis_locations", self.build_gis_locations)):
            try:
                await fn()
            except Exception as e:  # noqa: BLE001
                await self.add_issue("tahap_gagal", nama,
                                     f"Tahap '{nama}' gagal: {type(e).__name__}: {e}")
                print(f"[PERINGATAN] tahap {nama} gagal: {e}")

        await self.flush("import_batches", self.batches)
        await self.flush("data_quality_issues", self.issues, chunk=300)
        self.summary["import_batches"] = len(self.batches)
        self.summary["data_quality_issues"] = len(self.issues)
        await self.db.close()
        return self.summary


async def main():
    reset = "--reset" in sys.argv
    db = MariaDocStore.from_env()
    imp = Importer(db, reset=reset)
    summary = await imp.run()
    print("=== RINGKASAN IMPOR ===")
    for k, v in summary.items():
        print(f"{k}: {v}")
    kinds: Dict[str, int] = {}
    for i in imp.issues:
        kinds[i["jenis"]] = kinds.get(i["jenis"], 0) + 1
    print("=== DATA QUALITY ===")
    for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f"{k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
