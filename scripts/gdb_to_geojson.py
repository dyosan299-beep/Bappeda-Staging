#!/usr/bin/env python3
"""Konversi PETA_DASAR.gdb (File Geodatabase ESRI, Data Penetapan Peta Dasar
Edisi 2021 - BIG) menjadi berkas GeoJSON terkompresi (gzip) yang dipakai
langsung oleh backend SIDATA.

Keluaran:
  backend/assets/geo/basemap/<layer_id>.geojson.gz   -> geometri tiap layer
  backend/assets/geo/basemap/manifest.json           -> metadata + gaya + legenda
  backend/assets/geo/basemap/stats.json              -> statistik (panjang/luas/jumlah)
  backend/assets/geo/kelurahan_makassar.geojson      -> diperbarui (+ LUAS_M2, SUMBER)

Prasyarat: paket `gdal-bin` (perintah ogr2ogr) terpasang.

Pemakaian:
  python scripts/gdb_to_geojson.py --gdb /app/data_upload/peta_dasar/PETA_DASAR.gdb
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "backend" / "assets" / "geo" / "basemap"
KELURAHAN_PATH = ROOT / "backend" / "assets" / "geo" / "kelurahan_makassar.geojson"
SUMBER_UTAMA = "Peta Dasar Kota Makassar Edisi 2021 (BIG) — PETA_DASAR.gdb"

EMPTY_VALUES = {"", " ", "-", "tidak ada", "Tidak Ada", "TIDAK ADA", "none", "None"}

# ---------------------------------------------------------------- konfigurasi
# Palet kelas penutup lahan (23 kelas pada berkas sumber)
PENUTUP_LAHAN_WARNA: Dict[str, str] = {
    "Permukiman": "#d97706",
    "Tempat Kegiatan": "#b45309",
    "Permukaan Diperkeras": "#a8a29e",
    "Jalan": "#78716c",
    "Tanah Terbuka": "#e7d3a1",
    "Semak Belukar": "#a3b18a",
    "Kebun Campuran": "#4d7c0f",
    "Hutan": "#166534",
    "RTH": "#22c55e",
    "Padang Golf": "#86efac",
    "Sawah": "#84cc16",
    "Tegalan": "#bef264",
    "Rawa": "#5eead4",
    "Tambak": "#67e8f9",
    "Kolam": "#38bdf8",
    "Danau": "#0ea5e9",
    "Waduk": "#0284c7",
    "Sungai": "#2563eb",
    "Kanal": "#3b82f6",
    "Saluran Air": "#60a5fa",
    "Laut": "#1d4ed8",
    "Pertambangan": "#7c2d12",
    "Tempat Penimbunan dan Pembuangan Sampah": "#57534e",
}

JALAN_WARNA: Dict[str, str] = {
    "Jalan Tol": "#7c3aed",
    "Jalan Arteri Primer": "#dc2626",
    "Jalan Arteri Sekunder": "#ea580c",
    "Jalan Kolektor Primer": "#d97706",
    "Jalan Kolektor Sekunder": "#f59e0b",
    "Jalan Lokal": "#0891b2",
    "Jalan Lingkungan": "#64748b",
    "Jalan Lainnya": "#94a3b8",
}

PERAIRAN_WARNA: Dict[str, str] = {
    "Sungai": "#2563eb",
    "Alur Sungai": "#3b82f6",
    "Kanal": "#0ea5e9",
    "Saluran Air": "#60a5fa",
    "Danau": "#0284c7",
    "Waduk": "#1d4ed8",
    "Kolam": "#38bdf8",
    "Rawa": "#5eead4",
    "Tambak": "#67e8f9",
    "Laut": "#1e40af",
}

BATAS_WARNA: Dict[str, str] = {
    "Batas Kabupaten": "#111827",
    "Batas Kecamatan": "#7c3aed",
    "Batas Kelurahan": "#f43f5e",
}

TOPONIMI_WARNA: Dict[str, str] = {
    "Peribadatan": "#16a34a",
    "Pendidikan dan IPTEK": "#2563eb",
    "Kesehatan": "#dc2626",
    "Sarana Kesehatan": "#f87171",
    "Pemerintahan": "#7c3aed",
    "Permukiman": "#d97706",
    "Pemakaman": "#57534e",
    "Pertahanan dan Keamanan": "#0f766e",
    "Transportasi": "#0891b2",
    "Perekonomian dan Perdagangan": "#ca8a04",
    "Sosial": "#db2777",
    "Toponim Pariwisata, Seni dan Budaya": "#e11d48",
    "Pariwisata, Seni, dan Budaya": "#e11d48",
}

LAYERS: List[Dict[str, Any]] = [
    {
        "id": "batas_kelurahan",
        "src": "BATAS_ADMINISTRASI_AR",
        "label": "Batas Kelurahan (poligon)",
        "grup": "Batas Administrasi",
        "tipe": "polygon",
        "fields": {"KELURAHAN": "kelurahan", "KECAMATAN": "kecamatan",
                   "KOTA": "kota", "PROVINSI": "provinsi", "SUMBER": "sumber",
                   "Shape_Area": "luas_m2"},
        "warna": "#f43f5e",
        "fill_opacity": 0.04,
        "weight": 1.2,
        "min_zoom": 0,
        "kategori_field": "kecamatan",
        "keterangan": "154 kelurahan resmi dalam 15 kecamatan Kota Makassar.",
    },
    {
        "id": "batas_administrasi_garis",
        "src": "BATAS_ADMINISTRASI_LN",
        "label": "Garis Batas Administrasi",
        "grup": "Batas Administrasi",
        "tipe": "line",
        "fields": {"JENIS": "jenis", "STATUS": "status", "REMARK": "remark",
                   "SUMBER": "sumber"},
        "warna": "#7c3aed",
        "weight": 1.6,
        "min_zoom": 0,
        "kategori_field": "jenis",
        "kategori_warna": BATAS_WARNA,
        "keterangan": "Batas kabupaten/kota, kecamatan, dan kelurahan (definitif & indikatif).",
    },
    {
        "id": "jalan_utama",
        "src": "TRANSPORTASI_LN",
        "label": "Jaringan Jalan Utama",
        "grup": "Transportasi",
        "tipe": "line",
        "fields": {"Jenis": "jenis", "Fungsi": "fungsi", "Nama": "nama",
                   "PANJANG": "panjang_m"},
        "filter": {"field": "fungsi",
                   "exclude": ["Jalan Lingkungan", "Jalan Lainnya"]},
        "warna": "#dc2626",
        "weight": 2.2,
        "min_zoom": 0,
        "kategori_field": "fungsi",
        "kategori_warna": JALAN_WARNA,
        "keterangan": "Jalan tol, arteri, kolektor, dan lokal.",
    },
    {
        "id": "jalan_lingkungan",
        "src": "TRANSPORTASI_LN",
        "label": "Jalan Lingkungan & Lainnya",
        "grup": "Transportasi",
        "tipe": "line",
        "fields": {"Jenis": "jenis", "Fungsi": "fungsi", "Nama": "nama",
                   "PANJANG": "panjang_m"},
        "filter": {"field": "fungsi",
                   "include": ["Jalan Lingkungan", "Jalan Lainnya"]},
        "warna": "#64748b",
        "weight": 1.1,
        "min_zoom": 15,
        "bbox_required": True,
        "kategori_field": "fungsi",
        "kategori_warna": JALAN_WARNA,
        "keterangan": "Jalan lingkungan permukiman (data padat, tampil pada zoom 15+).",
    },
    {
        "id": "badan_jalan",
        "src": "TRANSPORTASI_AR",
        "label": "Badan Jalan Utama (poligon)",
        "grup": "Transportasi",
        "tipe": "polygon",
        "fields": {"JENIS": "jenis", "FUNGSI": "fungsi", "NAMOBJ": "nama",
                   "Shape_Area": "luas_m2"},
        "warna": "#f97316",
        "fill_opacity": 0.55,
        "weight": 0.8,
        "min_zoom": 13,
        "kategori_field": "fungsi",
        "kategori_warna": JALAN_WARNA,
        "keterangan": "Badan jalan utama bernama dalam bentuk poligon.",
    },
    {
        "id": "jembatan",
        "src": "JEMBATAN_PT",
        "label": "Jembatan",
        "grup": "Transportasi",
        "tipe": "point",
        "fields": {"JENIS": "jenis", "NAMOBJ": "nama", "SUMBER": "sumber"},
        "warna": "#a16207",
        "min_zoom": 13,
        "kategori_field": "jenis",
        "keterangan": "96 titik jembatan hasil survei 2021.",
    },
    {
        "id": "perairan_area",
        "src": "PERAIRAN_AR",
        "label": "Perairan (poligon)",
        "grup": "Perairan",
        "tipe": "polygon",
        "fields": {"JENIS": "jenis", "NAMOBJ": "nama", "SUMBER": "sumber",
                   "Shape_Area": "luas_m2"},
        "warna": "#1d4ed8",
        "fill_opacity": 0.45,
        "weight": 0.9,
        "min_zoom": 0,
        "kategori_field": "jenis",
        "kategori_warna": PERAIRAN_WARNA,
        "keterangan": "Sungai, kanal, danau, waduk, rawa, tambak, dan laut.",
    },
    {
        "id": "perairan_garis",
        "src": "PERAIRAN_LN",
        "label": "Sungai & Kanal (garis)",
        "grup": "Perairan",
        "tipe": "line",
        "fields": {"JENIS": "jenis", "NAMOBJ": "nama", "SUMBER": "sumber"},
        "warna": "#2563eb",
        "weight": 1.8,
        "min_zoom": 0,
        "kategori_field": "jenis",
        "kategori_warna": PERAIRAN_WARNA,
        "keterangan": "Alur sungai, kanal, dan saluran air utama.",
    },
    {
        "id": "garis_pantai",
        "src": "GARISPANTAI_LN",
        "label": "Garis Pantai",
        "grup": "Perairan",
        "tipe": "line",
        "fields": {"NAMOBJ": "nama", "TIPGPN": "tipe", "THNSBDATA": "tahun_sumber"},
        "warna": "#0e7490",
        "weight": 2.0,
        "min_zoom": 0,
        "kategori_field": "nama",
        "keterangan": "Garis pantai dan garis penutup sungai (data 2016-2020).",
    },
    {
        "id": "garis_pantai_rencana",
        "src": "GARIS_PANTAI_RENCANA",
        "label": "Garis Pantai Rencana (reklamasi)",
        "grup": "Perairan",
        "tipe": "line",
        "fields": {},
        "warna": "#c026d3",
        "weight": 2.0,
        "dash": "6 4",
        "min_zoom": 0,
        "keterangan": "Rencana garis pantai (CPI/reklamasi) sesuai peta dasar.",
    },
    {
        "id": "kontur",
        "src": "KONTUR_LN",
        "label": "Kontur (interval 10 m)",
        "grup": "Topografi",
        "tipe": "line",
        "fields": {"ELEVASI": "elevasi", "INTERVAL_": "interval", "SUMBER": "sumber"},
        "warna": "#b45309",
        "weight": 0.9,
        "min_zoom": 13,
        "kategori_field": "elevasi",
        "keterangan": "Garis kontur ketinggian dari DEMNAS 2018 (TERRA-SAR).",
    },
    {
        "id": "penutup_lahan",
        "src": "PENUTUP_LAHAN_AR",
        "label": "Penutup Lahan",
        "grup": "Penutup Lahan",
        "tipe": "polygon",
        "fields": {"PENUTUP_LA": "kelas", "SUMBER": "sumber", "Shape_Area": "luas_m2"},
        "warna": "#475569",
        "fill_opacity": 0.45,
        "weight": 0.5,
        "min_zoom": 11,
        "kategori_field": "kelas",
        "kategori_warna": PENUTUP_LAHAN_WARNA,
        "keterangan": "23 kelas penutup lahan hasil interpretasi citra satelit 2021.",
    },
    {
        "id": "toponimi",
        "src": "TOPONIMI_PT",
        "label": "Toponimi / Fasilitas Umum",
        "grup": "Toponimi",
        "tipe": "point",
        "fields": {"KLSTPN": "klasifikasi", "FTYPE": "jenis", "NAMOBJ": "nama",
                   "LCODE": "kode", "FOTO": "foto", "SUMBER": "sumber"},
        "warna": "#0f766e",
        "min_zoom": 12,
        "kategori_field": "klasifikasi",
        "kategori_warna": TOPONIMI_WARNA,
        "tag_wilayah": True,
        "keterangan": "1.571 titik fasilitas umum (ibadah, pendidikan, kesehatan, pemerintahan, dll).",
    },
]


# ---------------------------------------------------------------- util umum
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm_name(value: Any) -> str:
    s = str(value or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9' -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_name(value: Any) -> str:
    s = str(value or "").strip()
    return re.sub(r"\s+", " ", s).title() if s else ""


def clean_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str):
        s = value.strip()
        return "" if s in EMPTY_VALUES else s
    return value


def haversine_m(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lon1, lat1 = a[0], a[1]
    lon2, lat2 = b[0], b[1]
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def line_length_m(geom: Dict[str, Any]) -> float:
    def one(coords: List[List[float]]) -> float:
        return sum(haversine_m(coords[i], coords[i + 1]) for i in range(len(coords) - 1))

    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "LineString":
        return one(c)
    if t == "MultiLineString":
        return sum(one(part) for part in c)
    return 0.0


def ring_area_m2(ring: List[List[float]]) -> float:
    if len(ring) < 4:
        return 0.0
    lat0 = sum(p[1] for p in ring) / len(ring)
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0] * kx, ring[i][1] * ky
        x2, y2 = ring[i + 1][0] * kx, ring[i + 1][1] * ky
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def polygon_area_m2(geom: Dict[str, Any]) -> float:
    def one(rings: List[List[List[float]]]) -> float:
        if not rings:
            return 0.0
        area = ring_area_m2(rings[0])
        for hole in rings[1:]:
            area -= ring_area_m2(hole)
        return max(0.0, area)

    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "Polygon":
        return one(c)
    if t == "MultiPolygon":
        return sum(one(part) for part in c)
    return 0.0


def geom_bbox(geom: Dict[str, Any]) -> Optional[List[float]]:
    xs: List[float] = []
    ys: List[float] = []

    def walk(node: Any):
        if isinstance(node, (int, float)):
            return
        if node and isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for child in node or []:
            walk(child)

    walk(geom.get("coordinates"))
    if not xs:
        return None
    return [min(xs), min(ys), max(xs), max(ys)]


def point_in_ring(x: float, y: float, ring: List[List[float]]) -> bool:
    inside = False
    n = len(ring)
    for i in range(n - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / ((y2 - y1) or 1e-12)
            if x < xin:
                inside = not inside
    return inside


def point_in_polygon(x: float, y: float, geom: Dict[str, Any]) -> bool:
    t = geom.get("type")
    parts = geom.get("coordinates") or []
    polys = [parts] if t == "Polygon" else parts if t == "MultiPolygon" else []
    for rings in polys:
        if not rings:
            continue
        if point_in_ring(x, y, rings[0]) and not any(
            point_in_ring(x, y, hole) for hole in rings[1:]
        ):
            return True
    return False


# ---------------------------------------------------------------- konversi
def run_ogr(gdb: Path, layer: str, dest: Path) -> None:
    cmd = [
        "ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:4326", "-dim", "XY",
        "-lco", "COORDINATE_PRECISION=6", "-skipfailures",
        str(dest), str(gdb), layer,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not dest.is_file():
        raise RuntimeError(f"ogr2ogr gagal untuk layer {layer}: {res.stderr[:400]}")


def map_props(raw: Dict[str, Any], fields: Dict[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for src, dst in fields.items():
        val = clean_value(raw.get(src))
        if dst.endswith("_m2") or dst == "panjang_m":
            try:
                val = round(float(val or 0), 2)
            except (TypeError, ValueError):
                val = 0.0
        out[dst] = val
    return out


def build_layer(cfg: Dict[str, Any], src_fc: Dict[str, Any],
                kel_index: Optional[List[Tuple[List[float], Dict[str, Any]]]] = None,
                ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Kembalikan (FeatureCollection bersih, statistik layer)."""
    flt = cfg.get("filter") or {}
    kategori_field = cfg.get("kategori_field")
    feats: List[Dict[str, Any]] = []
    per_kat: Dict[str, Dict[str, float]] = {}
    total_panjang = 0.0
    total_luas = 0.0

    for idx, f in enumerate(src_fc.get("features") or []):
        geom = f.get("geometry")
        if not geom or not geom.get("coordinates"):
            continue
        props = map_props(f.get("properties") or {}, cfg.get("fields") or {})

        if flt:
            val = str(props.get(flt["field"]) or "")
            if flt.get("include") and val not in flt["include"]:
                continue
            if flt.get("exclude") and val in flt["exclude"]:
                continue

        props["fid"] = f"{cfg['id']}-{idx + 1}"

        # tag wilayah untuk layer titik (toponimi)
        if cfg.get("tag_wilayah") and kel_index and geom.get("type") == "Point":
            x, y = float(geom["coordinates"][0]), float(geom["coordinates"][1])
            props["kelurahan"] = ""
            props["kecamatan"] = ""
            for bbox, kf in kel_index:
                if bbox[0] - 0.001 <= x <= bbox[2] + 0.001 and bbox[1] - 0.001 <= y <= bbox[3] + 0.001:
                    if point_in_polygon(x, y, kf["geometry"]):
                        props["kelurahan"] = kf["properties"].get("KELURAHAN", "")
                        props["kecamatan"] = kf["properties"].get("KECAMATAN", "")
                        break

        panjang = luas = 0.0
        if cfg["tipe"] == "line":
            panjang = line_length_m(geom)
            props["panjang_m"] = round(panjang, 1)
            total_panjang += panjang
        elif cfg["tipe"] == "polygon":
            luas = float(props.get("luas_m2") or 0) or polygon_area_m2(geom)
            props["luas_m2"] = round(luas, 1)
            total_luas += luas

        kat = str(props.get(kategori_field) or "Lainnya") if kategori_field else "Semua"
        bucket = per_kat.setdefault(kat, {"jumlah": 0, "panjang_m": 0.0, "luas_m2": 0.0})
        bucket["jumlah"] += 1
        bucket["panjang_m"] += panjang
        bucket["luas_m2"] += luas

        feats.append({"type": "Feature", "properties": props, "geometry": geom})

    fc = {"type": "FeatureCollection", "features": feats}
    bbox_all: Optional[List[float]] = None
    for f in feats:
        b = geom_bbox(f["geometry"])
        if not b:
            continue
        bbox_all = b if bbox_all is None else [
            min(bbox_all[0], b[0]), min(bbox_all[1], b[1]),
            max(bbox_all[2], b[2]), max(bbox_all[3], b[3]),
        ]
    fc["bbox"] = bbox_all

    stats = {
        "id": cfg["id"],
        "label": cfg["label"],
        "grup": cfg["grup"],
        "tipe": cfg["tipe"],
        "jumlah": len(feats),
        "panjang_km": round(total_panjang / 1000.0, 2) if total_panjang else 0.0,
        "luas_ha": round(total_luas / 10000.0, 2) if total_luas else 0.0,
        "per_kategori": [
            {
                "kategori": k,
                "jumlah": int(v["jumlah"]),
                "panjang_km": round(v["panjang_m"] / 1000.0, 2),
                "luas_ha": round(v["luas_m2"] / 10000.0, 2),
            }
            for k, v in sorted(per_kat.items(), key=lambda kv: -kv[1]["jumlah"])
        ],
    }
    return fc, stats


def write_gz(path: Path, data: Dict[str, Any]) -> int:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    with gzip.open(path, "wb", compresslevel=9) as fh:
        fh.write(raw)
    return path.stat().st_size


def update_kelurahan_geojson(src_fc: Dict[str, Any]) -> int:
    """Perbarui berkas batas kelurahan resmi (dipakai ETL & choropleth)."""
    feats = []
    for f in src_fc.get("features") or []:
        p = f.get("properties") or {}
        geom = f.get("geometry")
        if not geom:
            continue
        luas = float(p.get("Shape_Area") or 0) or polygon_area_m2(geom)
        feats.append({
            "type": "Feature",
            "properties": {
                "PROVINSI": title_name(p.get("PROVINSI")),
                "KOTA": title_name(p.get("KOTA")),
                "KECAMATAN": title_name(p.get("KECAMATAN")),
                "KELURAHAN": title_name(p.get("KELURAHAN")),
                "SUMBER": clean_value(p.get("SUMBER")) or SUMBER_UTAMA,
                "LUAS_M2": round(luas, 1),
                "LUAS_HA": round(luas / 10000.0, 2),
            },
            "geometry": geom,
        })
    out = {
        "type": "FeatureCollection",
        "name": "batas_kelurahan_makassar",
        "sumber": SUMBER_UTAMA,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": feats,
    }
    KELURAHAN_PATH.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False))
    return len(feats)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gdb", default="/app/data_upload/peta_dasar/PETA_DASAR.gdb",
                    help="Path direktori File Geodatabase (.gdb)")
    ap.add_argument("--only", default="", help="Hanya proses layer_id tertentu (dipisah koma)")
    args = ap.parse_args()

    gdb = Path(args.gdb)
    if not gdb.exists():
        print(f"[GAGAL] GDB tidak ditemukan: {gdb}", file=sys.stderr)
        return 2
    if shutil.which("ogr2ogr") is None:
        print("[GAGAL] ogr2ogr tidak tersedia. Pasang paket gdal-bin.", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    tmpdir = Path(tempfile.mkdtemp(prefix="gdb2gj-"))
    cache: Dict[str, Dict[str, Any]] = {}

    def load_src(layer: str) -> Dict[str, Any]:
        if layer not in cache:
            dest = tmpdir / f"{layer}.geojson"
            run_ogr(gdb, layer, dest)
            cache[layer] = json.loads(dest.read_text())
        return cache[layer]

    # 1) batas kelurahan resmi + indeks untuk penandaan wilayah titik
    adm = load_src("BATAS_ADMINISTRASI_AR")
    jumlah_kel = update_kelurahan_geojson(adm)
    print(f"[OK] backend/assets/geo/kelurahan_makassar.geojson diperbarui ({jumlah_kel} kelurahan)")
    kel_index = [(geom_bbox(f["geometry"]) or [0, 0, 0, 0], f)
                 for f in adm.get("features") or [] if f.get("geometry")]

    manifest_layers: List[Dict[str, Any]] = []
    stats_all: List[Dict[str, Any]] = []

    for cfg in LAYERS:
        if only and cfg["id"] not in only:
            continue
        try:
            src_fc = load_src(cfg["src"])
        except RuntimeError as exc:
            print(f"[LEWAT] {cfg['id']}: {exc}", file=sys.stderr)
            continue
        fc, stats = build_layer(cfg, src_fc, kel_index)
        fname = f"{cfg['id']}.geojson.gz"
        size = write_gz(OUT_DIR / fname, fc)
        stats_all.append(stats)
        manifest_layers.append({
            "id": cfg["id"],
            "label": cfg["label"],
            "grup": cfg["grup"],
            "tipe": cfg["tipe"],
            "file": fname,
            "jumlah": stats["jumlah"],
            "ukuran_bytes": size,
            "bbox": fc.get("bbox"),
            "warna": cfg.get("warna", "#334155"),
            "fill_opacity": cfg.get("fill_opacity", 0.35),
            "weight": cfg.get("weight", 1.2),
            "dash": cfg.get("dash"),
            "min_zoom": cfg.get("min_zoom", 0),
            "bbox_required": bool(cfg.get("bbox_required")),
            "kategori_field": cfg.get("kategori_field"),
            "kategori_warna": cfg.get("kategori_warna") or {},
            "keterangan": cfg.get("keterangan", ""),
            "sumber": SUMBER_UTAMA,
            "aktif_default": cfg["id"] in ("batas_kelurahan",),
        })
        print(f"[OK] {cfg['id']:26s} {stats['jumlah']:6d} fitur  "
              f"{size/1024:8.1f} KB  panjang {stats['panjang_km']:9.2f} km  "
              f"luas {stats['luas_ha']:10.2f} ha")

    manifest = {
        "generated_at": now_iso(),
        "sumber": SUMBER_UTAMA,
        "kota": "Makassar",
        "crs": "EPSG:4326",
        "layers": manifest_layers,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False))
    (OUT_DIR / "stats.json").write_text(
        json.dumps({"generated_at": now_iso(), "sumber": SUMBER_UTAMA,
                    "layers": stats_all}, indent=1, ensure_ascii=False))
    print(f"[OK] manifest.json & stats.json ditulis ke {OUT_DIR}")
    shutil.rmtree(tmpdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
