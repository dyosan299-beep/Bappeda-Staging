"""API modul PETA DASAR — layer dasar Kota Makassar hasil ekstraksi
PETA_DASAR.gdb (Data Penetapan Peta Dasar Edisi 2021, BIG).

Geometri disimpan sebagai berkas GeoJSON terkompresi gzip di
`backend/assets/geo/basemap/` (dibuat oleh `scripts/gdb_to_geojson.py`)
sehingga cepat disajikan dan ikut terbawa ke image Docker.

Ringkasan statistik & daftar fasilitas umum (toponimi) juga di-seed ke database
agar dapat dikutip oleh AI Assistant dan halaman statistik.

Semua endpoint di-mount pada prefix /api oleh server.py.
"""
from __future__ import annotations

import gzip
import json
import re
import unicodedata
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

ROOT = Path(__file__).parent
BASEMAP_DIR = ROOT / "assets" / "geo" / "basemap"
MANIFEST_PATH = BASEMAP_DIR / "manifest.json"
STATS_PATH = BASEMAP_DIR / "stats.json"

MAX_CACHED_LAYERS = 4
MAX_FEATURES = 40000

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731


def norm_name(value: Any) -> str:
    s = str(value or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9' -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------- cache berkas
_manifest_cache: Dict[str, Any] = {"mtime": 0.0, "data": None}
_stats_cache: Dict[str, Any] = {"mtime": 0.0, "data": None}
_layer_cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()


def _read_json(path: Path) -> Any:
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    return json.loads(path.read_text())


def load_manifest() -> Dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        return {"generated_at": None, "sumber": "", "layers": []}
    mtime = MANIFEST_PATH.stat().st_mtime
    if _manifest_cache["data"] is None or _manifest_cache["mtime"] != mtime:
        _manifest_cache["data"] = _read_json(MANIFEST_PATH)
        _manifest_cache["mtime"] = mtime
    return _manifest_cache["data"] or {"layers": []}


def load_stats() -> Dict[str, Any]:
    if not STATS_PATH.is_file():
        return {"generated_at": None, "sumber": "", "layers": []}
    mtime = STATS_PATH.stat().st_mtime
    if _stats_cache["data"] is None or _stats_cache["mtime"] != mtime:
        _stats_cache["data"] = _read_json(STATS_PATH)
        _stats_cache["mtime"] = mtime
    return _stats_cache["data"] or {"layers": []}


def layer_meta(layer_id: str) -> Optional[Dict[str, Any]]:
    for lyr in load_manifest().get("layers") or []:
        if lyr.get("id") == layer_id:
            return lyr
    return None


def _geom_bbox(geom: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
    xs: List[float] = []
    ys: List[float] = []

    def walk(node: Any):
        if not node:
            return
        if isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for child in node:
            walk(child)

    try:
        walk(geom.get("coordinates"))
    except (TypeError, IndexError):
        return None
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def load_layer(layer_id: str) -> Dict[str, Any]:
    """Muat layer (dengan indeks bbox per fitur) memakai cache LRU sederhana."""
    if layer_id in _layer_cache:
        _layer_cache.move_to_end(layer_id)
        return _layer_cache[layer_id]

    meta = layer_meta(layer_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Layer '{layer_id}' tidak dikenal")
    path = BASEMAP_DIR / str(meta.get("file") or "")
    if not path.is_file():
        raise HTTPException(status_code=404,
                            detail=f"Berkas layer '{layer_id}' belum tersedia di server")
    fc = _read_json(path)
    feats = fc.get("features") or []
    entry = {
        "meta": meta,
        "features": feats,
        "bboxes": [_geom_bbox(f.get("geometry") or {}) for f in feats],
        "bbox": fc.get("bbox"),
    }
    _layer_cache[layer_id] = entry
    _layer_cache.move_to_end(layer_id)
    while len(_layer_cache) > MAX_CACHED_LAYERS:
        _layer_cache.popitem(last=False)
    return entry


def _parse_bbox(value: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not value:
        return None
    parts = [p.strip() for p in str(value).split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=422,
                            detail="Parameter bbox harus 'minLng,minLat,maxLng,maxLat'")
    try:
        minx, miny, maxx, maxy = (float(p) for p in parts)
    except ValueError:
        raise HTTPException(status_code=422, detail="Parameter bbox harus berupa angka")
    if minx > maxx or miny > maxy:
        raise HTTPException(status_code=422, detail="Urutan nilai bbox tidak valid")
    return (minx, miny, maxx, maxy)


def _intersects(a: Optional[Tuple[float, float, float, float]],
                b: Tuple[float, float, float, float]) -> bool:
    if a is None:
        return True
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


# --------------------------------------------------------------- seeding DB
async def seed_peta_dasar(db) -> Dict[str, int]:
    """Simpan ringkasan layer & daftar fasilitas umum (toponimi) ke database.

    Idempotent: hanya menulis ulang bila jumlah dokumen berbeda dari berkas
    sumber (misal setelah konversi ulang GDB)."""
    hasil = {"peta_dasar_layers": 0, "fasilitas_umum": 0, "geo_kelurahan": 0}

    # batas kelurahan resmi (dipakai choropleth Peta Sosial) — juga di-seed di sini
    # supaya peta tetap tampil walau ETL Excel belum dijalankan.
    kel_path = ROOT / "assets" / "geo" / "kelurahan_makassar.geojson"
    if kel_path.is_file():
        kel_fc = _read_json(kel_path)
        kel_feats = kel_fc.get("features") or []
        if kel_feats and await db.geo_kelurahan.count_documents({}) != len(kel_feats):
            docs = []
            for f in kel_feats:
                p = f.get("properties") or {}
                docs.append({
                    "id": str(uuid.uuid4()),
                    "kelurahan": p.get("KELURAHAN") or "",
                    "kelurahan_norm": norm_name(p.get("KELURAHAN")),
                    "kecamatan": p.get("KECAMATAN") or "",
                    "kecamatan_norm": norm_name(p.get("KECAMATAN")),
                    "kota": p.get("KOTA") or "", "provinsi": p.get("PROVINSI") or "",
                    "luas_m2": p.get("LUAS_M2") or 0, "luas_ha": p.get("LUAS_HA") or 0,
                    "geometry": f.get("geometry"),
                    "sumber": p.get("SUMBER") or "PETA_DASAR.gdb / BATAS_ADMINISTRASI_AR",
                    "created_at": now_iso(),
                })
            await db.geo_kelurahan.delete_many({})
            for i in range(0, len(docs), 100):
                await db.geo_kelurahan.insert_many(docs[i:i + 100])
            hasil["geo_kelurahan"] = len(docs)

    stats = load_stats()
    layers = stats.get("layers") or []
    if layers:
        existing = await db.peta_dasar_layers.count_documents({})
        if existing != len(layers):
            await db.peta_dasar_layers.delete_many({})
            docs = []
            for s in layers:
                docs.append({
                    "id": s.get("id"),
                    "label": s.get("label"),
                    "grup": s.get("grup"),
                    "tipe": s.get("tipe"),
                    "jumlah": int(s.get("jumlah") or 0),
                    "panjang_km": float(s.get("panjang_km") or 0),
                    "luas_ha": float(s.get("luas_ha") or 0),
                    "per_kategori": s.get("per_kategori") or [],
                    "sumber": stats.get("sumber") or "",
                    "created_at": now_iso(),
                })
            if docs:
                await db.peta_dasar_layers.insert_many(docs)
            hasil["peta_dasar_layers"] = len(docs)

    # fasilitas umum dari layer toponimi
    meta = layer_meta("toponimi")
    if meta:
        path = BASEMAP_DIR / str(meta.get("file") or "")
        if path.is_file():
            existing = await db.fasilitas_umum.count_documents({})
            target = int(meta.get("jumlah") or 0)
            if existing != target:
                fc = _read_json(path)
                docs = []
                for f in fc.get("features") or []:
                    p = f.get("properties") or {}
                    coords = (f.get("geometry") or {}).get("coordinates") or [None, None]
                    docs.append({
                        "id": str(uuid.uuid4()),
                        "fid": p.get("fid"),
                        "nama": p.get("nama") or "",
                        "jenis": p.get("jenis") or "",
                        "klasifikasi": p.get("klasifikasi") or "",
                        "kode": p.get("kode") or "",
                        "kelurahan": p.get("kelurahan") or "",
                        "kelurahan_norm": norm_name(p.get("kelurahan")),
                        "kecamatan": p.get("kecamatan") or "",
                        "kecamatan_norm": norm_name(p.get("kecamatan")),
                        "lng": coords[0], "lat": coords[1],
                        "sumber": p.get("sumber") or "",
                        "created_at": now_iso(),
                    })
                await db.fasilitas_umum.delete_many({})
                for i in range(0, len(docs), 500):
                    await db.fasilitas_umum.insert_many(docs[i:i + 500])
                hasil["fasilitas_umum"] = len(docs)
    return hasil


# --------------------------------------------------------------- router
def build_router(db, current_user_dep, editor_dep, admin_dep) -> APIRouter:
    router = APIRouter(prefix="/peta-dasar", tags=["peta-dasar"])

    @router.get("/layers")
    async def list_layers():
        """Daftar layer peta dasar beserta gaya, legenda, dan statistiknya."""
        man = load_manifest()
        stats_by_id = {s.get("id"): s for s in (load_stats().get("layers") or [])}
        layers = []
        for lyr in man.get("layers") or []:
            item = dict(lyr)
            st = stats_by_id.get(lyr.get("id")) or {}
            item["panjang_km"] = st.get("panjang_km", 0)
            item["luas_ha"] = st.get("luas_ha", 0)
            item["per_kategori"] = st.get("per_kategori", [])
            layers.append(item)
        grup: List[str] = []
        for lyr in layers:
            if lyr.get("grup") and lyr["grup"] not in grup:
                grup.append(lyr["grup"])
        return {
            "generated_at": man.get("generated_at"),
            "sumber": man.get("sumber"),
            "kota": man.get("kota", "Makassar"),
            "grup": grup,
            "total_layer": len(layers),
            "layers": layers,
        }

    @router.get("/stats")
    async def layer_stats():
        """Statistik lengkap tiap layer (jumlah fitur, panjang km, luas ha)."""
        return load_stats()

    @router.get("/ringkasan")
    async def ringkasan():
        """KPI ringkas peta dasar untuk halaman statistik."""
        stats = load_stats()
        by_id = {s.get("id"): s for s in stats.get("layers") or []}

        def val(layer_id: str, field: str, default: float = 0) -> float:
            return float((by_id.get(layer_id) or {}).get(field) or default)

        penutup = (by_id.get("penutup_lahan") or {}).get("per_kategori") or []
        top_penutup = sorted(penutup, key=lambda x: -float(x.get("luas_ha") or 0))[:8]
        jalan_kat = ((by_id.get("jalan_utama") or {}).get("per_kategori") or []) + \
                    ((by_id.get("jalan_lingkungan") or {}).get("per_kategori") or [])
        toponimi_kat = (by_id.get("toponimi") or {}).get("per_kategori") or []
        return {
            "sumber": stats.get("sumber"),
            "generated_at": stats.get("generated_at"),
            "luas_kota_ha": val("batas_kelurahan", "luas_ha"),
            "jumlah_kelurahan": int(val("batas_kelurahan", "jumlah")),
            "panjang_jalan_km": round(val("jalan_utama", "panjang_km") +
                                      val("jalan_lingkungan", "panjang_km"), 2),
            "panjang_jalan_utama_km": val("jalan_utama", "panjang_km"),
            "panjang_jalan_lingkungan_km": val("jalan_lingkungan", "panjang_km"),
            "panjang_sungai_kanal_km": val("perairan_garis", "panjang_km"),
            "panjang_garis_pantai_km": val("garis_pantai", "panjang_km"),
            "panjang_batas_administrasi_km": val("batas_administrasi_garis", "panjang_km"),
            "luas_perairan_ha": val("perairan_area", "luas_ha"),
            "jumlah_jembatan": int(val("jembatan", "jumlah")),
            "jumlah_toponimi": int(val("toponimi", "jumlah")),
            "jumlah_kontur": int(val("kontur", "jumlah")),
            "jumlah_penutup_lahan": int(val("penutup_lahan", "jumlah")),
            "penutup_lahan_teratas": top_penutup,
            "jalan_per_fungsi": sorted(jalan_kat, key=lambda x: -float(x.get("panjang_km") or 0)),
            "toponimi_per_klasifikasi": sorted(toponimi_kat,
                                               key=lambda x: -int(x.get("jumlah") or 0)),
        }

    @router.get("/layer/{layer_id}")
    async def get_layer(layer_id: str,
                        bbox: Optional[str] = Query(None,
                                                    description="minLng,minLat,maxLng,maxLat"),
                        kategori: Optional[str] = Query(None,
                                                        description="Filter kategori, pisahkan dengan koma"),
                        limit: int = Query(MAX_FEATURES, ge=1, le=MAX_FEATURES)):
        """GeoJSON satu layer peta dasar (opsional dipotong bbox & kategori)."""
        entry = load_layer(layer_id)
        meta = entry["meta"]
        box = _parse_bbox(bbox)
        if meta.get("bbox_required") and box is None:
            raise HTTPException(
                status_code=422,
                detail=(f"Layer '{layer_id}' padat ({meta.get('jumlah')} fitur); "
                        "parameter bbox wajib diisi"))
        kats = {k.strip().lower() for k in (kategori or "").split(",") if k.strip()}
        kat_field = meta.get("kategori_field")

        feats: List[Dict[str, Any]] = []
        truncated = False
        for f, fb in zip(entry["features"], entry["bboxes"]):
            if box is not None and not _intersects(fb, box):
                continue
            if kats and kat_field:
                if str((f.get("properties") or {}).get(kat_field) or "").lower() not in kats:
                    continue
            if len(feats) >= limit:
                truncated = True
                break
            feats.append(f)

        return {
            "type": "FeatureCollection",
            "id": layer_id,
            "label": meta.get("label"),
            "tipe": meta.get("tipe"),
            "warna": meta.get("warna"),
            "fill_opacity": meta.get("fill_opacity", 0.35),
            "weight": meta.get("weight"),
            "dash": meta.get("dash"),
            "kategori_field": kat_field,
            "kategori_warna": meta.get("kategori_warna") or {},
            "sumber": meta.get("sumber"),
            "count": len(feats),
            "total": meta.get("jumlah"),
            "truncated": truncated,
            "bbox": entry.get("bbox"),
            "features": feats,
        }

    # ------------------------------------------------------ fasilitas umum
    @router.get("/fasilitas")
    async def fasilitas(search: Optional[str] = None,
                        klasifikasi: Optional[str] = None,
                        jenis: Optional[str] = None,
                        kelurahan: Optional[str] = None,
                        kecamatan: Optional[str] = None,
                        page: int = Query(1, ge=1),
                        page_size: int = Query(25, ge=1, le=200)):
        """Pencarian fasilitas umum / toponimi (masjid, sekolah, puskesmas, dll)."""
        try:
            entry = load_layer("toponimi")
        except HTTPException:
            return {"total": 0, "page": page, "page_size": page_size, "items": [],
                    "filters": {"klasifikasi": [], "jenis": [], "kecamatan": []}}
        s = norm_name(search) if search else ""
        rows: List[Dict[str, Any]] = []
        for f in entry["features"]:
            p = f.get("properties") or {}
            if klasifikasi and norm_name(p.get("klasifikasi")) != norm_name(klasifikasi):
                continue
            if jenis and norm_name(p.get("jenis")) != norm_name(jenis):
                continue
            if kelurahan and norm_name(p.get("kelurahan")) != norm_name(kelurahan):
                continue
            if kecamatan and norm_name(p.get("kecamatan")) != norm_name(kecamatan):
                continue
            if s and s not in norm_name(p.get("nama")) and s not in norm_name(p.get("jenis")):
                continue
            coords = (f.get("geometry") or {}).get("coordinates") or [None, None]
            rows.append({
                "fid": p.get("fid"), "nama": p.get("nama"), "jenis": p.get("jenis"),
                "klasifikasi": p.get("klasifikasi"), "kelurahan": p.get("kelurahan"),
                "kecamatan": p.get("kecamatan"), "kode": p.get("kode"),
                "lng": coords[0], "lat": coords[1], "sumber": p.get("sumber"),
            })
        rows.sort(key=lambda r: (r["kecamatan"] or "", r["kelurahan"] or "", r["nama"] or ""))
        total = len(rows)
        start = (page - 1) * page_size
        items = rows[start:start + page_size]

        all_props = [f.get("properties") or {} for f in entry["features"]]
        opts = lambda field: sorted({str(p.get(field) or "") for p in all_props} - {""})  # noqa: E731
        return {
            "total": total, "page": page, "page_size": page_size,
            "total_page": max(1, (total + page_size - 1) // page_size),
            "items": items,
            "filters": {
                "klasifikasi": opts("klasifikasi"),
                "jenis": opts("jenis"),
                "kecamatan": opts("kecamatan"),
                "kelurahan": opts("kelurahan"),
            },
            "sumber": load_manifest().get("sumber"),
        }

    @router.get("/fasilitas/rekap")
    async def fasilitas_rekap(kecamatan: Optional[str] = None,
                              level: str = Query("kelurahan", pattern="^(kelurahan|kecamatan)$")):
        """Rekap jumlah fasilitas umum per wilayah dan per klasifikasi."""
        try:
            entry = load_layer("toponimi")
        except HTTPException:
            return {"level": level, "klasifikasi": [], "rows": [], "total": 0}
        key = "kelurahan" if level == "kelurahan" else "kecamatan"
        rows: Dict[str, Dict[str, Any]] = {}
        klas: Dict[str, int] = {}
        total = 0
        for f in entry["features"]:
            p = f.get("properties") or {}
            if kecamatan and norm_name(p.get("kecamatan")) != norm_name(kecamatan):
                continue
            wil = str(p.get(key) or "(di luar batas)")
            k = str(p.get("klasifikasi") or "Lainnya")
            row = rows.setdefault(wil, {"wilayah": wil,
                                        "kecamatan": p.get("kecamatan") or "",
                                        "total": 0, "per_klasifikasi": {}})
            row["total"] += 1
            row["per_klasifikasi"][k] = row["per_klasifikasi"].get(k, 0) + 1
            klas[k] = klas.get(k, 0) + 1
            total += 1
        out = sorted(rows.values(), key=lambda r: -r["total"])
        return {
            "level": level,
            "total": total,
            "klasifikasi": [{"kategori": k, "jumlah": v}
                            for k, v in sorted(klas.items(), key=lambda kv: -kv[1])],
            "rows": out,
            "sumber": load_manifest().get("sumber"),
        }

    return router
