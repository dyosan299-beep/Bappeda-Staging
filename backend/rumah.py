"""Modul data rumah / bangunan (GIS level bangunan) untuk SIDATA.

Menyediakan:
- Generator data demo polygon rumah (Kec. Tallo — Kaluku Bodoa dsk.)
- Router API: geojson, filter, statistik, CRUD, import GeoJSON, konfigurasi peta.

Catatan: penyimpanan memakai lapisan MariaDocStore (gaya dokumen) sehingga
`geometry` GeoJSON disimpan sebagai objek JSON di dalam dokumen.
"""
from __future__ import annotations

import math
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# ---------------------------------------------------------------- konstanta
KECAMATAN_DEMO = "Tallo"

FOTO_RUMAH = [
    "https://images.pexels.com/photos/25853807/pexels-photo-25853807.jpeg",
    "https://images.pexels.com/photos/34556594/pexels-photo-34556594.jpeg",
    "https://images.unsplash.com/photo-1643216120728-fa08e985b178",
    "https://images.pexels.com/photos/8840839/pexels-photo-8840839.jpeg",
    "https://images.unsplash.com/photo-1635864523067-3e9f2b4ffe81",
    "https://images.pexels.com/photos/6941504/pexels-photo-6941504.jpeg",
]

# Warna status (dipakai frontend, dikirim lewat /api/rumah/legend)
STATUS_LEGEND = [
    {"status": "hijau", "label": "Data lengkap / kondisi baik", "color": "#00C853"},
    {"status": "kuning", "label": "Perlu diverifikasi", "color": "#FFC107"},
    {"status": "merah", "label": "Bermasalah / tidak layak huni", "color": "#FF5252"},
]

NAMA_PEMILIK = [
    "KAHAR", "MUH. ARIF", "DAENG NAba", "HJ. SITTI AMINAH", "ABD. RAHMAN",
    "SYAMSUDDIN", "NURHAYATI", "BASO INTANG", "MUHAMMAD YUSUF", "SUARDI",
    "ANDI MAPPA", "HASNAH", "RUSLAN", "DG. TAYANG", "SAHARUDDIN",
    "MARWAH", "IRWAN SAPUTRA", "FATIMAH", "H. MUSTARI", "JUMARIAH",
    "SUDIRMAN", "ROSMINI", "ABD. HAMID", "SANGKALA", "SITTI RABIAH",
    "MUH. TAHIR", "NURLINA", "BAHARUDDIN", "ASMAWATI", "LA ODE ALI",
]

KELURAHAN_DEMO = [
    # nama kelurahan, titik acuan (lat, lng), daftar RW
    ("Kaluku Bodoa", -5.14770, 119.43270, ["1", "2", "3"]),
    ("Rappokalling", -5.14600, 119.43520, ["1", "2"]),
    ("Bunga Eja Beru", -5.14960, 119.43060, ["1"]),
]

PENGHASILAN = ["P1", "P2", "P3", "P4"]
BANTUAN = ["PKH", "BPNT", "BLT", "BSPS", "-"]
MUTU = ["A", "B", "C"]
STATUS_LAHAN = ["Milik", "Sewa", "Menumpang", "Milik Keluarga"]
KONDISI_JALAN = ["Layak Huni", "Tidak Layak Huni", "Perlu Perbaikan"]

M_PER_DEG_LAT = 111320.0


def _m_to_deg_lat(m: float) -> float:
    return m / M_PER_DEG_LAT


def _m_to_deg_lng(m: float, lat: float) -> float:
    return m / (M_PER_DEG_LAT * max(math.cos(math.radians(lat)), 0.1))


def rect_polygon(lat: float, lng: float, width_m: float, depth_m: float,
                 angle_deg: float = 0.0) -> Dict[str, Any]:
    """Bangun polygon GeoJSON persegi (footprint bangunan) di sekitar titik."""
    ang = math.radians(angle_deg)
    hw, hd = width_m / 2.0, depth_m / 2.0
    corners_m = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    ring = []
    for dx, dy in corners_m:
        rx = dx * math.cos(ang) - dy * math.sin(ang)
        ry = dx * math.sin(ang) + dy * math.cos(ang)
        ring.append([
            round(lng + _m_to_deg_lng(rx, lat), 7),
            round(lat + _m_to_deg_lat(ry), 7),
        ])
    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def polygon_centroid(geometry: Optional[Dict[str, Any]]):
    """Centroid sederhana (rata-rata titik) untuk Polygon / MultiPolygon."""
    if not geometry:
        return None, None
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    ring = None
    if gtype == "Polygon" and coords:
        ring = coords[0]
    elif gtype == "MultiPolygon" and coords and coords[0]:
        ring = coords[0][0]
    elif gtype == "Point" and coords:
        return coords[1], coords[0]
    if not ring:
        return None, None
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return round(sum(ys) / len(ys), 7), round(sum(xs) / len(xs), 7)


# ---------------------------------------------------------------- demo data
def build_demo_rumah() -> List[Dict[str, Any]]:
    """Hasilkan polygon rumah demo berbentuk blok permukiman padat."""
    rnd = random.Random(20250701)
    docs: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    counter = 0

    for kel_idx, (kelurahan, base_lat, base_lng, rws) in enumerate(KELURAHAN_DEMO):
        for rw_idx, rw in enumerate(rws):
            # setiap RW = 1 blok; blok digeser agar tidak bertumpuk
            blok_angle = rnd.choice([0, 8, -7, 15, -14, 22])
            blok_lat = base_lat + _m_to_deg_lat(-rw_idx * 90.0)
            blok_lng = base_lng + _m_to_deg_lng(rw_idx * 25.0, base_lat)
            rows, cols = 3, 8
            for r in range(rows):
                for c in range(cols):
                    counter += 1
                    width = round(rnd.uniform(6.0, 9.5), 2)
                    depth = round(rnd.uniform(9.0, 14.0), 2)
                    # posisi rumah dalam blok (baris berjajar + gang di antara baris)
                    off_x = c * 11.0
                    off_y = r * 26.0
                    ang = math.radians(blok_angle)
                    rx = off_x * math.cos(ang) - off_y * math.sin(ang)
                    ry = off_x * math.sin(ang) + off_y * math.cos(ang)
                    lat = blok_lat + _m_to_deg_lat(ry + rnd.uniform(-0.8, 0.8))
                    lng = blok_lng + _m_to_deg_lng(rx + rnd.uniform(-0.8, 0.8), base_lat)
                    geom = rect_polygon(lat, lng, width, depth, blok_angle + rnd.uniform(-3, 3))

                    dinding = rnd.choices(MUTU, weights=[6, 3, 2])[0]
                    atap = rnd.choices(MUTU, weights=[6, 3, 2])[0]
                    lantai = rnd.choices(MUTU, weights=[6, 3, 2])[0]
                    sanitasi = rnd.choices(MUTU, weights=[5, 3, 2])[0]
                    air = rnd.choices(MUTU, weights=[5, 3, 2])[0]
                    mutu = [dinding, atap, lantai, sanitasi, air]
                    jumlah_c = mutu.count("C")
                    verifikasi_pending = rnd.random() < 0.18

                    if jumlah_c >= 2:
                        status = "merah"
                        kondisi = "Tidak Layak Huni"
                    elif verifikasi_pending or jumlah_c == 1:
                        status = "kuning"
                        kondisi = "Perlu Perbaikan"
                    else:
                        status = "hijau"
                        kondisi = "Layak Huni"

                    pemilik = NAMA_PEMILIK[counter % len(NAMA_PEMILIK)]
                    docs.append({
                        "id": str(uuid.uuid4()),
                        "kode": f"RMH-{kel_idx + 1}{rw}-{counter:04d}",
                        "nama": pemilik,
                        "pemilik": pemilik,
                        "jumlah_orang": rnd.randint(1, 8),
                        "no_kk": f"7371{rnd.randint(10**11, 10**12 - 1)}",
                        "rt": str(rnd.randint(1, 6)),
                        "rw": rw,
                        "kelurahan": kelurahan,
                        "kecamatan": KECAMATAN_DEMO,
                        "penghasilan": rnd.choices(PENGHASILAN, weights=[3, 4, 4, 2])[0],
                        "bantuan": rnd.choices(BANTUAN, weights=[3, 3, 2, 1, 3])[0],
                        "tahun_bangunan": str(rnd.randint(1985, 2024)),
                        "dinding": dinding,
                        "atap": atap,
                        "lantai": lantai,
                        "sanitasi": sanitasi,
                        "air": air,
                        "status_lahan": rnd.choices(STATUS_LAHAN, weights=[5, 2, 2, 2])[0],
                        "jalan": rnd.choice(KONDISI_JALAN),
                        "keterangan": rnd.choice([
                            "Data survei lapangan 2025", "Menunggu verifikasi RW",
                            "Rumah tangga penerima bantuan", "Perlu bedah rumah",
                            "Data lengkap", "",
                        ]),
                        "luas": round(width * depth, 2),
                        "kondisi": kondisi,
                        "status": status,
                        "foto_url": FOTO_RUMAH[counter % len(FOTO_RUMAH)],
                        "lat": round(lat, 7),
                        "lng": round(lng, 7),
                        "geometry": geom,
                        "created_at": now,
                        "updated_at": now,
                    })
    return docs


async def seed_rumah(db) -> int:
    """Seed idempotent: hanya mengisi bila koleksi masih kosong."""
    existing = await db.rumah.count_documents({})
    if existing:
        return 0
    docs = build_demo_rumah()
    if docs:
        await db.rumah.insert_many(docs)
    return len(docs)


async def seed_map_config(db) -> None:
    cfg = await db.map_config.find_one({"id": "default"})
    if cfg is None:
        await db.map_config.insert_one({
            "id": "default",
            "center_lat": -5.1477,
            "center_lng": 119.4327,
            "zoom": 18,
            "basemap": "google_hybrid",
            "kota": "Kota Makassar",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })


# ---------------------------------------------------------------- models
class RumahIn(BaseModel):
    nama: Optional[str] = None
    pemilik: str
    jumlah_orang: Optional[int] = Field(0, ge=0)
    no_kk: Optional[str] = ""
    rt: Optional[str] = ""
    rw: Optional[str] = ""
    kelurahan: str
    kecamatan: Optional[str] = KECAMATAN_DEMO
    penghasilan: Optional[str] = ""
    bantuan: Optional[str] = "-"
    tahun_bangunan: Optional[str] = ""
    dinding: Optional[str] = ""
    atap: Optional[str] = ""
    lantai: Optional[str] = ""
    sanitasi: Optional[str] = ""
    air: Optional[str] = ""
    status_lahan: Optional[str] = ""
    jalan: Optional[str] = ""
    keterangan: Optional[str] = ""
    luas: Optional[float] = Field(None, ge=0)
    kondisi: Optional[str] = ""
    status: Optional[str] = "kuning"
    foto_url: Optional[str] = ""
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    geometry: Optional[Dict[str, Any]] = None


class RumahUpdate(RumahIn):
    pemilik: Optional[str] = None  # type: ignore[assignment]
    kelurahan: Optional[str] = None  # type: ignore[assignment]


class MapConfigUpdate(BaseModel):
    center_lat: Optional[float] = Field(None, ge=-90, le=90)
    center_lng: Optional[float] = Field(None, ge=-180, le=180)
    zoom: Optional[int] = Field(None, ge=1, le=22)
    basemap: Optional[str] = None


class ImportGeoJSON(BaseModel):
    featureCollection: Dict[str, Any]
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    replace: Optional[bool] = False


VALID_STATUS = ("hijau", "kuning", "merah")

_FIELDS = [
    "nama", "pemilik", "jumlah_orang", "no_kk", "rt", "rw", "kelurahan", "kecamatan",
    "penghasilan", "bantuan", "tahun_bangunan", "dinding", "atap", "lantai", "sanitasi",
    "air", "status_lahan", "jalan", "keterangan", "luas", "kondisi", "status",
    "foto_url", "lat", "lng",
]


def _clean(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Buang _id internal agar aman diserialisasi JSON."""
    out = {k: v for k, v in doc.items() if k != "_id"}
    return out


def _properties(doc: Dict[str, Any]) -> Dict[str, Any]:
    p = {k: doc.get(k) for k in _FIELDS}
    p["id"] = doc.get("id")
    p["kode"] = doc.get("kode", "")
    return p


def _normalize_status(value: Optional[str]) -> str:
    v = (value or "").strip().lower()
    alias = {
        "green": "hijau", "hijau": "hijau", "baik": "hijau", "lengkap": "hijau",
        "yellow": "kuning", "kuning": "kuning", "verifikasi": "kuning",
        "red": "merah", "merah": "merah", "bermasalah": "merah",
    }
    return alias.get(v, "kuning")


def _ensure_geometry(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Bila geometry tidak dikirim namun ada lat/lng, buat footprint dari luas."""
    geom = payload.get("geometry")
    lat, lng = payload.get("lat"), payload.get("lng")
    if not geom and lat is not None and lng is not None:
        luas = float(payload.get("luas") or 80.0)
        side = max(math.sqrt(max(luas, 4.0)), 2.0)
        payload["geometry"] = rect_polygon(float(lat), float(lng), side, side)
    elif geom and (lat is None or lng is None):
        c_lat, c_lng = polygon_centroid(geom)
        payload["lat"], payload["lng"] = c_lat, c_lng
    return payload


# ---------------------------------------------------------------- router
def build_router(db, current_user_dep, editor_dep, admin_dep) -> APIRouter:
    router = APIRouter(tags=["rumah"])

    async def _filter_from_query(kelurahan: Optional[str], rw: Optional[str],
                                 status: Optional[str]) -> Dict[str, Any]:
        q: Dict[str, Any] = {}
        if kelurahan and kelurahan.lower() not in ("semua", "all", ""):
            q["kelurahan"] = kelurahan
        if rw and rw.lower() not in ("semua", "all", ""):
            q["rw"] = str(rw)
        if status and status.lower() not in ("semua", "all", ""):
            q["status"] = status
        return q

    # ---------------- konfigurasi peta
    @router.get("/map/config")
    async def map_config():
        cfg = await db.map_config.find_one({"id": "default"}) or {}
        return {
            "center": {
                "lat": cfg.get("center_lat", -5.1477),
                "lng": cfg.get("center_lng", 119.4327),
            },
            "zoom": cfg.get("zoom", 18),
            "basemap": cfg.get("basemap", "google_hybrid"),
            "kota": cfg.get("kota", "Kota Makassar"),
            "google_maps_api_key": os.environ.get("GOOGLE_MAPS_API_KEY", ""),
            "google_maps_enabled": bool(os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()),
            "legend": STATUS_LEGEND,
        }

    @router.put("/map/config")
    async def update_map_config(payload: MapConfigUpdate, admin: dict = Depends(admin_dep)):
        upd = {k: v for k, v in payload.model_dump().items() if v is not None}
        if upd:
            upd["updated_at"] = datetime.now(timezone.utc).isoformat()
            await db.map_config.update_one({"id": "default"}, {"$set": upd})
        return await map_config()

    # ---------------- filter & statistik (harus sebelum /rumah/{rumah_id})
    @router.get("/rumah/filters")
    async def rumah_filters():
        docs = await db.rumah.find({}).to_list(20000)
        kel_map: Dict[str, set] = {}
        for d in docs:
            kel = d.get("kelurahan") or "-"
            kel_map.setdefault(kel, set()).add(str(d.get("rw") or "-"))
        kelurahan = sorted(kel_map.keys())
        return {
            "kelurahan": kelurahan,
            "rw_by_kelurahan": {k: sorted(v, key=lambda x: (len(x), x)) for k, v in kel_map.items()},
            "rw_all": sorted({rw for s in kel_map.values() for rw in s}, key=lambda x: (len(x), x)),
            "total": len(docs),
        }

    @router.get("/rumah/stats")
    async def rumah_stats(kelurahan: Optional[str] = None, rw: Optional[str] = None):
        q = await _filter_from_query(kelurahan, rw, None)
        docs = await db.rumah.find(q).to_list(20000)
        per_status = {"hijau": 0, "kuning": 0, "merah": 0}
        per_bantuan: Dict[str, int] = {}
        per_kelurahan: Dict[str, int] = {}
        total_jiwa = 0
        total_luas = 0.0
        for d in docs:
            per_status[_normalize_status(d.get("status"))] = \
                per_status.get(_normalize_status(d.get("status")), 0) + 1
            b = d.get("bantuan") or "-"
            per_bantuan[b] = per_bantuan.get(b, 0) + 1
            k = d.get("kelurahan") or "-"
            per_kelurahan[k] = per_kelurahan.get(k, 0) + 1
            total_jiwa += int(d.get("jumlah_orang") or 0)
            total_luas += float(d.get("luas") or 0)
        return {
            "total": len(docs),
            "per_status": per_status,
            "per_bantuan": per_bantuan,
            "per_kelurahan": per_kelurahan,
            "total_jiwa": total_jiwa,
            "total_luas": round(total_luas, 2),
            "legend": STATUS_LEGEND,
        }

    @router.get("/rumah/legend")
    async def rumah_legend():
        return {"legend": STATUS_LEGEND}

    @router.get("/rumah/geojson")
    async def rumah_geojson(kelurahan: Optional[str] = None, rw: Optional[str] = None,
                            status: Optional[str] = None,
                            limit: int = Query(5000, ge=1, le=20000)):
        q = await _filter_from_query(kelurahan, rw, status)
        docs = await db.rumah.find(q).to_list(limit)
        features = []
        min_lat = min_lng = 1e9
        max_lat = max_lng = -1e9
        for d in docs:
            geom = d.get("geometry")
            if not geom:
                continue
            features.append({
                "type": "Feature",
                "id": d.get("id"),
                "geometry": geom,
                "properties": _properties(d),
            })
            try:
                for lng, lat in geom.get("coordinates", [[]])[0]:
                    min_lat, max_lat = min(min_lat, lat), max(max_lat, lat)
                    min_lng, max_lng = min(min_lng, lng), max(max_lng, lng)
            except Exception:
                pass
        bbox = None
        if features and min_lat < 1e9:
            bbox = [min_lng, min_lat, max_lng, max_lat]
        return {"type": "FeatureCollection", "features": features,
                "bbox": bbox, "count": len(features)}

    @router.get("/rumah")
    async def list_rumah(kelurahan: Optional[str] = None, rw: Optional[str] = None,
                         status: Optional[str] = None, search: Optional[str] = None,
                         limit: int = Query(500, ge=1, le=5000)):
        q = await _filter_from_query(kelurahan, rw, status)
        docs = await db.rumah.find(q).to_list(20000)
        if search:
            s = search.lower()
            docs = [d for d in docs if s in str(d.get("pemilik", "")).lower()
                    or s in str(d.get("kode", "")).lower()
                    or s in str(d.get("no_kk", "")).lower()]
        docs = sorted(docs, key=lambda d: (d.get("kelurahan") or "", str(d.get("rw") or ""),
                                           d.get("kode") or ""))
        total = len(docs)
        items = [_clean({k: v for k, v in d.items() if k != "geometry"}) for d in docs[:limit]]
        return {"total": total, "items": items}

    @router.get("/rumah/{rumah_id}")
    async def get_rumah(rumah_id: str):
        doc = await db.rumah.find_one({"id": rumah_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Data rumah tidak ditemukan")
        return _clean(doc)

    @router.post("/rumah")
    async def create_rumah(payload: RumahIn, user: dict = Depends(editor_dep)):
        data = payload.model_dump()
        data["status"] = _normalize_status(data.get("status"))
        data = _ensure_geometry(data)
        if not data.get("nama"):
            data["nama"] = data.get("pemilik")
        now = datetime.now(timezone.utc).isoformat()
        count = await db.rumah.count_documents({})
        data.update({
            "id": str(uuid.uuid4()),
            "kode": f"RMH-M-{count + 1:04d}",
            "created_at": now,
            "updated_at": now,
            "created_by": user.get("email"),
        })
        await db.rumah.insert_one(data)
        return _clean(data)

    @router.put("/rumah/{rumah_id}")
    async def update_rumah(rumah_id: str, payload: RumahUpdate,
                           user: dict = Depends(editor_dep)):
        doc = await db.rumah.find_one({"id": rumah_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Data rumah tidak ditemukan")
        upd = {k: v for k, v in payload.model_dump().items() if v is not None}
        if "status" in upd:
            upd["status"] = _normalize_status(upd["status"])
        merged = {**doc, **upd}
        if upd.get("geometry") or (upd.get("lat") is not None and upd.get("lng") is not None):
            merged = _ensure_geometry({**merged, "geometry": upd.get("geometry") or (
                None if (upd.get("lat") is not None and upd.get("lng") is not None) else doc.get("geometry"))})
            upd["geometry"] = merged.get("geometry")
            upd["lat"], upd["lng"] = merged.get("lat"), merged.get("lng")
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        upd["updated_by"] = user.get("email")
        await db.rumah.update_one({"id": rumah_id}, {"$set": upd})
        fresh = await db.rumah.find_one({"id": rumah_id})
        return _clean(fresh or {})

    @router.delete("/rumah/{rumah_id}")
    async def delete_rumah(rumah_id: str, admin: dict = Depends(admin_dep)):
        doc = await db.rumah.find_one({"id": rumah_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Data rumah tidak ditemukan")
        await db.rumah.delete_one({"id": rumah_id})
        return {"deleted": rumah_id}

    @router.post("/rumah/import-geojson")
    async def import_geojson(payload: ImportGeoJSON, admin: dict = Depends(admin_dep)):
        fc = payload.featureCollection or {}
        feats = fc.get("features")
        if fc.get("type") == "Feature":
            feats = [fc]
        if not isinstance(feats, list) or not feats:
            raise HTTPException(status_code=400, detail="GeoJSON tidak memiliki features")
        if payload.replace:
            await db.rumah.delete_many({})
        now = datetime.now(timezone.utc).isoformat()
        docs = []
        base = await db.rumah.count_documents({})
        for i, f in enumerate(feats):
            props = {str(k).lower(): v for k, v in (f.get("properties") or {}).items()}
            geom = f.get("geometry")
            lat, lng = polygon_centroid(geom)
            luas = props.get("luas") or props.get("area")
            doc: Dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "kode": props.get("kode") or f"RMH-IMP-{base + i + 1:04d}",
                "geometry": geom,
                "lat": props.get("lat") or lat,
                "lng": props.get("lng") or lng,
                "created_at": now, "updated_at": now,
                "created_by": admin.get("email"),
            }
            for fld in _FIELDS:
                if fld in ("lat", "lng", "luas", "status"):
                    continue
                doc[fld] = props.get(fld, "")
            doc["kelurahan"] = doc.get("kelurahan") or payload.kelurahan or ""
            doc["kecamatan"] = doc.get("kecamatan") or payload.kecamatan or KECAMATAN_DEMO
            doc["nama"] = doc.get("nama") or doc.get("pemilik") or doc["kode"]
            doc["jumlah_orang"] = int(props.get("jumlah_orang") or 0)
            try:
                doc["luas"] = round(float(luas), 2) if luas is not None else None
            except (TypeError, ValueError):
                doc["luas"] = None
            doc["status"] = _normalize_status(props.get("status"))
            docs.append(doc)
        if docs:
            await db.rumah.insert_many(docs)
        return {"imported": len(docs), "total": await db.rumah.count_documents({})}

    return router
