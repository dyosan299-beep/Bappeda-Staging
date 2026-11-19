"""Modul IMPORT WIZARD — impor data Excel/CSV melalui antarmuka aplikasi.

Alur: Upload -> Baca sheet -> Mapping kolom -> Validasi -> Preview -> Impor (batch)
      -> Ringkasan + unduh laporan error.

Jenis dataset yang didukung: dtsen (rumah tangga), disabilitas, rad, gis_koordinat.
Data ditulis ke koleksi yang SUDAH dipakai dashboard (households, disability_region_stats,
rad_items) agar seluruh dashboard existing langsung mengikuti, plus gis_locations.

Semua endpoint di-mount pada prefix /api oleh server.py.
"""
from __future__ import annotations

import asyncio
import base64
import csv
import difflib
import io
import json
import math
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pydantic import BaseModel, Field

import etl_import as etl
import scoring
import dtsen_ref  # noqa: E402

# Berkas unggahan disimpan di database (koleksi `import_files`) dalam potongan
# base64 agar tidak bergantung pada disk/volume server. Ukuran potongan dijaga
# jauh di bawah `max_allowed_packet` MariaDB (default 16 MB).
FILE_CHUNK_BYTES = 2 * 1024 * 1024
MAX_UPLOAD_BYTES = int(os.environ.get("IMPORT_MAX_UPLOAD_MB", "100")) * 1024 * 1024
PREVIEW_ROWS = 20
MAX_ISSUES_STORED = 5000
DEFAULT_CHUNK = 500

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731


def norm_name(value: Any) -> str:
    s = str(value or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9' -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_col(value: Any) -> str:
    s = str(value or "").strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def clean_cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    if isinstance(v, str):
        return v.strip()
    return v


def as_int(v: Any) -> Optional[int]:
    s = str(clean_cell(v)).replace(".", "").replace(",", "").strip()
    if s in ("", "-"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def as_num(v: Any) -> Optional[float]:
    s = str(clean_cell(v)).replace(",", ".").strip()
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------- skema target
class TargetField(dict):
    pass


def F(name: str, label: str, tipe: str = "text", required: bool = False,
      synonyms: Optional[List[str]] = None, section: str = "Umum",
      keterangan: str = "", contoh: Any = "") -> Dict[str, Any]:
    return {"name": name, "label": label, "tipe": tipe, "required": required,
            "synonyms": synonyms or [], "section": section,
            "keterangan": keterangan, "contoh": contoh}


DTSEN_FIELDS: List[Dict[str, Any]] = [
    F("nomor_kartu_keluarga", "Nomor Kartu Keluarga", "text", True,
      ["no_kk", "nokk", "kk", "nomor_kk", "no_kartu_keluarga"], "Identitas Keluarga",
      "16 digit, disimpan tersamarkan untuk peran non-sensitif", "7371010101010001"),
    F("kode_provinsi", "Kode Provinsi", "text", False, ["kd_provinsi", "kodeprov"], "Identitas Wilayah", contoh="73"),
    F("provinsi", "Provinsi", "text", False, ["nama_provinsi", "prov"], "Identitas Wilayah", contoh="Sulawesi Selatan"),
    F("kode_kabupaten_kota", "Kode Kabupaten/Kota", "text", False,
      ["kode_kabkota", "kd_kabupaten_kota", "kode_kab_kota"], "Identitas Wilayah", contoh="7371"),
    F("kabupaten_kota", "Kabupaten/Kota", "text", False, ["kabkota", "kab_kota", "kota"], "Identitas Wilayah", contoh="Kota Makassar"),
    F("kode_kecamatan", "Kode Kecamatan", "text", False, ["kd_kecamatan", "kodekec"], "Identitas Wilayah", contoh="737107"),
    F("kecamatan", "Kecamatan", "text", False, ["nama_kecamatan", "kec"], "Identitas Wilayah", contoh="Tallo"),
    F("kode_kelurahan_desa", "Kode Kelurahan/Desa", "text", False,
      ["kode_kelurahan", "kd_kelurahan", "kode_desa", "kodekel"], "Identitas Wilayah", contoh="7371071001"),
    F("kelurahan_desa", "Kelurahan/Desa", "text", True,
      ["kelurahan", "nama_kelurahan", "desa", "kel"], "Identitas Wilayah", contoh="Kaluku Bodoa"),
    F("rt", "RT", "text", False, ["no_rt", "nomor_rt", "rt_domisili"], "Identitas Wilayah",
      "Opsional. Isi hanya bila tersedia sebagai kolom pada berkas sumber; TIDAK disimpulkan dari alamat", "001"),
    F("rw", "RW", "text", False, ["no_rw", "nomor_rw", "rw_domisili"], "Identitas Wilayah",
      "Opsional. Isi hanya bila tersedia sebagai kolom pada berkas sumber; TIDAK disimpulkan dari alamat", "002"),
    F("alamat", "Alamat", "text", False, ["alamat_lengkap", "address"], "Identitas Keluarga"),
    F("jumlah_anggota_keluarga", "Jumlah Anggota Keluarga", "int", False,
      ["jml_anggota_keluarga", "jumlah_art", "jml_art"], "Identitas Keluarga", contoh=4),
    F("nama_anggota_keluarga", "Nama Kepala/Anggota Keluarga", "text", False,
      ["nama", "nama_kepala_keluarga", "kepala_keluarga"], "Identitas Keluarga"),
    F("desil_nasional", "Desil Nasional", "int", False, ["desil", "desil_nas"],
      "Status Sosial", "Nilai 1-10", 1),
    F("pbi_nas", "PBI Nasional", "int", False, ["pbi_nasional", "pbi_jkn"], "Status Sosial", "0 atau 1", 1),
    F("pbi_pemda", "PBI Pemda", "int", False, ["pbi_daerah", "pbi_pemerintah_daerah"], "Status Sosial", "0 atau 1", 0),
    F("status_kepemilikan_rumah", "Status Kepemilikan Rumah", "kode", False,
      ["status_rumah", "kepemilikan_rumah"], "Kondisi Rumah", contoh=1),
    F("jenis_lantai_terluas", "Jenis Lantai Terluas", "kode", False, ["jenis_lantai", "lantai"], "Kondisi Rumah", contoh=2),
    F("luas_lantai", "Luas Lantai (m2)", "num", False, ["luas", "luas_lantai_m2"], "Kondisi Rumah", contoh=48),
    F("jenis_dinding_terluas", "Jenis Dinding Terluas", "kode", False, ["jenis_dinding", "dinding"], "Kondisi Rumah", contoh=1),
    F("jenis_atap_terluas", "Jenis Atap Terluas", "kode", False, ["jenis_atap", "atap"], "Kondisi Rumah", contoh=3),
    F("sumber_air_minum_utama", "Sumber Air Minum Utama", "kode", False, ["sumber_air", "air_minum"], "Infrastruktur Dasar", contoh=4),
    F("sumber_penerangan_utama", "Sumber Penerangan Utama", "kode", False, ["penerangan", "sumber_listrik"], "Infrastruktur Dasar", contoh=1),
    F("daya_terpasang", "Daya Terpasang", "kode", False, ["daya", "daya_listrik"], "Infrastruktur Dasar", contoh=2),
    F("fasilitas_bab", "Fasilitas BAB", "kode", False, ["fasilitas_buang_air", "bab"], "Infrastruktur Dasar", contoh=1),
    F("jenis_kloset", "Jenis Kloset", "kode", False, ["kloset"], "Infrastruktur Dasar", contoh=1),
    F("pembuangan_akhir_tinja", "Pembuangan Akhir Tinja", "kode", False, ["pembuangan_tinja", "tinja"], "Infrastruktur Dasar", contoh=1),
    F("aset_tidak_bergerak_lahan_lainnya", "Aset Lahan Lainnya", "kode", False, ["aset_lahan"], "Aset", contoh=0),
    F("aset_tidak_bergerak_rumah_lainnya", "Aset Rumah Lainnya", "kode", False, ["aset_rumah"], "Aset", contoh=0),
]

DISABILITAS_FIELDS: List[Dict[str, Any]] = [
    F("kecamatan", "Kecamatan", "text", True, ["kec", "nama_kecamatan", "skpd"], "Wilayah", contoh="Tallo"),
    F("kelurahan", "Kelurahan", "text", False, ["kel", "nama_kelurahan", "desa"], "Wilayah", contoh="Kaluku Bodoa"),
    F("tahun", "Tahun Data", "int", False, ["thn", "periode"], "Wilayah", contoh=2026),
    F("laki_laki", "Jenis Kelamin Laki-Laki", "int", False, ["jenis_kelamin_laki_laki", "lk", "laki"], "Jenis Kelamin", contoh=458),
    F("perempuan", "Jenis Kelamin Perempuan", "int", False, ["jenis_kelamin_perempuan", "pr"], "Jenis Kelamin", contoh=480),
    F("usia_dibawah_18", "Usia di bawah 18", "int", False, ["usia_dibawah_18", "usia_anak", "usia_18_kebawah"], "Kelompok Usia", contoh=98),
    F("usia_18_59", "Usia 18-59", "int", False, ["usia_produktif"], "Kelompok Usia", contoh=840),
    F("usia_60_keatas", "Usia 60 ke atas", "int", False, ["usia_lansia", "usia_60"], "Kelompok Usia", contoh=0),
    F("fisik", "Ragam Fisik", "int", False, [], "Ragam Disabilitas", contoh=303),
    F("ganda", "Ragam Ganda", "int", False, [], "Ragam Disabilitas", contoh=110),
    F("intelektual", "Ragam Intelektual", "int", False, [], "Ragam Disabilitas", contoh=38),
    F("mental", "Ragam Mental", "int", False, [], "Ragam Disabilitas", contoh=57),
    F("sensorik_pendengaran", "Sensorik Pendengaran", "int", False, ["pendengaran", "rungu", "tuli"], "Ragam Disabilitas", contoh=220),
    F("sensorik_penglihatan", "Sensorik Penglihatan", "int", False,
      ["sensorik_pengelihatan", "penglihatan", "netra", "buta"], "Ragam Disabilitas", contoh=210),
    F("total", "Total", "int", False, ["jumlah", "jumlah_total"], "Ringkasan", contoh=938),
    F("sumber", "Sumber Data", "text", False, ["instansi", "opd"], "Ringkasan", contoh="Dinkes 2026"),
]

RAD_FIELDS: List[Dict[str, Any]] = [
    F("strategi_implementasi", "Strategi Implementasi", "text", False, ["strategi"], "Perencanaan"),
    F("target_capaian", "Target Capaian", "text", False, ["target"], "Perencanaan"),
    F("program", "Program", "text", False, [], "Perencanaan"),
    F("kegiatan", "Kegiatan", "text", True, [], "Perencanaan"),
    F("sub_kegiatan", "Sub Kegiatan", "text", False, ["subkegiatan"], "Perencanaan"),
    F("indikator_capaian", "Indikator Capaian", "text", False, ["indikator"], "Indikator"),
    F("output_kegiatan", "Output Kegiatan", "text", False, ["output"], "Indikator"),
    F("indikator_capaian_terkait_disabilitas", "Indikator Terkait Disabilitas", "text", False,
      ["indikator_disabilitas"], "Indikator"),
    F("hambatan_tantangan", "Hambatan / Tantangan", "text", False, ["hambatan", "tantangan"], "Indikator"),
    F("satuan_target_kegiatan", "Satuan Target", "text", False, ["satuan"], "Target & Anggaran"),
    F("target_2023", "Target 2023", "num", False, [], "Target & Anggaran"),
    F("target_2024", "Target 2024", "num", False, [], "Target & Anggaran"),
    F("target_2025", "Target 2025", "num", False, [], "Target & Anggaran"),
    F("target_2026", "Target 2026", "num", False, [], "Target & Anggaran"),
    F("anggaran_2023", "Anggaran 2023", "num", False, [], "Target & Anggaran"),
    F("anggaran_2024", "Anggaran 2024", "num", False, [], "Target & Anggaran"),
    F("anggaran_2025", "Anggaran 2025", "num", False, [], "Target & Anggaran"),
    F("anggaran_2026", "Anggaran 2026", "num", False, [], "Target & Anggaran"),
    F("lokasi", "Lokasi", "text", False, [], "Pelaksana"),
    F("spesifik_tidak_spesifik", "Spesifik / Tidak Spesifik", "text", False, ["spesifik"], "Pelaksana"),
    F("perangkat_daerah_penanggung_jawab", "Perangkat Daerah Penanggung Jawab", "text", False,
      ["opd", "skpd", "perangkat_daerah", "penanggung_jawab"], "Pelaksana"),
    F("keterangan", "Keterangan", "text", False, ["catatan"], "Pelaksana"),
]

GIS_FIELDS: List[Dict[str, Any]] = [
    F("kelurahan", "Kelurahan", "text", True, ["nama_kelurahan", "kelurahan_desa"], "Wilayah"),
    F("kecamatan", "Kecamatan", "text", False, ["nama_kecamatan"], "Wilayah"),
    F("kode_kelurahan", "Kode Kelurahan", "text", False, ["kode_kelurahan_desa"], "Wilayah"),
    F("latitude", "Latitude", "num", True, ["lat", "lintang", "y"], "Koordinat", "-90 s.d. 90", -5.1121),
    F("longitude", "Longitude", "num", True, ["lng", "lon", "bujur", "x"], "Koordinat", "-180 s.d. 180", 119.4423),
    F("keterangan", "Keterangan", "text", False, ["catatan"], "Koordinat"),
]

DATASETS: Dict[str, Dict[str, Any]] = {
    "dtsen": {"label": "DTSEN Keluarga / Rumah Tangga", "fields": DTSEN_FIELDS,
              "collection": "households", "kunci": "nomor_kartu_keluarga + kode/nama kelurahan"},
    "disabilitas": {"label": "Data Penyandang Disabilitas", "fields": DISABILITAS_FIELDS,
                    "collection": "disability_region_stats", "kunci": "kecamatan + kelurahan + tahun"},
    "rad": {"label": "Matriks RAD Penyandang Disabilitas", "fields": RAD_FIELDS,
            "collection": "rad_items", "kunci": "OPD + program + kegiatan + sub kegiatan"},
    "gis_koordinat": {"label": "Koordinat GIS Kelurahan", "fields": GIS_FIELDS,
                      "collection": "gis_locations", "kunci": "kelurahan"},
}


def detect_dataset(columns: List[str], filename: str = "") -> str:
    cols = {norm_col(c) for c in columns}
    fn = norm_col(filename)
    skor = {}
    for jenis, cfg in DATASETS.items():
        names = set()
        for f in cfg["fields"]:
            names.add(norm_col(f["name"]))
            names.update(norm_col(s) for s in f["synonyms"])
        skor[jenis] = len(cols & names)
    best = max(skor, key=lambda k: skor[k])
    if skor[best] == 0:
        if "disabilitas" in fn:
            return "disabilitas"
        if "rad" in fn:
            return "rad"
        return "dtsen"
    return best


def suggest_mapping(columns: List[str], jenis: str) -> Tuple[Dict[str, str], List[str]]:
    fields = DATASETS[jenis]["fields"]
    lookup: Dict[str, str] = {}
    for f in fields:
        lookup[norm_col(f["name"])] = f["name"]
        for s in f["synonyms"]:
            lookup[norm_col(s)] = f["name"]
    mapping: Dict[str, str] = {}
    dipakai: set = set()
    for col in columns:
        key = norm_col(col)
        target = lookup.get(key)
        if not target:
            dekat = difflib.get_close_matches(key, list(lookup.keys()), n=1, cutoff=0.82)
            if dekat:
                target = lookup[dekat[0]]
        if target and target not in dipakai:
            mapping[str(col)] = target
            dipakai.add(target)
    belum = [f["name"] for f in fields if f["name"] not in dipakai]
    return mapping, belum


# --------------------------------------------------------------- baca berkas
def detect_header_row(df: pd.DataFrame, max_scan: int = 12) -> int:
    """Cari baris header pada sheet yang memiliki judul/baris kosong di atas."""
    best_idx, best_score = 0, -1.0
    for i in range(min(max_scan, len(df))):
        row = [clean_cell(v) for v in df.iloc[i].tolist()]
        terisi = [v for v in row if str(v) != ""]
        if len(terisi) < 2:
            continue
        teks = sum(1 for v in terisi if isinstance(v, str))
        score = len(terisi) + teks * 0.5
        if score > best_score:
            best_score, best_idx = score, i
    return best_idx


class SourceFile:
    """Berkas unggahan di memori (bytes + nama) — pengganti path di disk."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data
        self.suffix = Path(name).suffix.lower()
        self.stem = Path(name).stem

    def stream(self) -> io.BytesIO:
        return io.BytesIO(self.data)


def read_sheet(src: SourceFile, sheet: Optional[str], header_row: int = 0) -> pd.DataFrame:
    if src.suffix == ".csv":
        return pd.read_csv(src.stream(), header=header_row, dtype=str, keep_default_na=False,
                           encoding_errors="ignore")
    return pd.read_excel(src.stream(), sheet_name=sheet, header=header_row, dtype=str,
                         keep_default_na=False)


def describe_file(src: SourceFile) -> List[Dict[str, Any]]:
    """Ringkasan tiap sheet: nama, jumlah baris/kolom, kolom, preview."""
    out: List[Dict[str, Any]] = []
    if src.suffix == ".csv":
        raw = pd.read_csv(src.stream(), header=None, dtype=str, keep_default_na=False,
                          encoding_errors="ignore")
        sheets = [(src.stem, raw)]
    else:
        book = pd.read_excel(src.stream(), sheet_name=None, header=None, dtype=str,
                             keep_default_na=False)
        sheets = list(book.items())
    for name, raw in sheets:
        if raw is None or raw.empty:
            out.append({"name": str(name), "rows": 0, "cols": 0, "header_row": 0,
                        "columns": [], "preview": [], "kosong": True})
            continue
        hr = detect_header_row(raw)
        header = [str(clean_cell(v)) or f"Kolom {i + 1}"
                  for i, v in enumerate(raw.iloc[hr].tolist())]
        body = raw.iloc[hr + 1:]
        # buang kolom & baris yang benar-benar kosong
        preview: List[Dict[str, Any]] = []
        for _, r in body.head(PREVIEW_ROWS).iterrows():
            vals = [clean_cell(v) for v in r.tolist()]
            if all(str(v) == "" for v in vals):
                continue
            preview.append({header[i]: (vals[i] if i < len(vals) else "")
                            for i in range(len(header))})
        jumlah_baris = int(sum(1 for _, r in body.iterrows()
                               if any(str(clean_cell(v)) != "" for v in r.tolist())))
        out.append({"name": str(name), "rows": jumlah_baris, "cols": len(header),
                    "header_row": hr, "columns": header, "preview": preview,
                    "kosong": jumlah_baris == 0})
    return out


# --------------------------------------------------------------- validasi
def _kode_str(v: Any) -> str:
    s = str(clean_cell(v))
    if s.endswith(".0"):
        s = s[:-2]
    return s


def normalize_row(jenis: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """Ubah nilai mentah (sudah dimap ke nama field target) menjadi nilai bersih."""
    out: Dict[str, Any] = {}
    for f in DATASETS[jenis]["fields"]:
        name = f["name"]
        val = clean_cell(raw.get(name))
        if f["tipe"] == "int":
            out[name] = as_int(val)
        elif f["tipe"] == "num":
            out[name] = as_num(val)
        elif f["tipe"] == "kode":
            out[name] = _kode_str(val)
        else:
            out[name] = str(val) if val != "" else ""
    return out


def validate_row(jenis: str, row: Dict[str, Any], raw: Dict[str, Any],
                 kel_index: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Kembalikan (errors, warnings) untuk satu baris."""
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    def err(kolom: str, pesan: str, nilai: Any = ""):
        errors.append({"kolom": kolom, "pesan": pesan, "nilai": str(nilai)[:80]})

    def warn(kolom: str, pesan: str, nilai: Any = ""):
        warnings.append({"kolom": kolom, "pesan": pesan, "nilai": str(nilai)[:80]})

    for f in DATASETS[jenis]["fields"]:
        name, val = f["name"], row.get(f["name"])
        if f["required"] and (val is None or str(val).strip() == ""):
            err(name, f"Kolom wajib '{f['label']}' kosong")
        if f["tipe"] in ("int", "num") and val is None and str(clean_cell(raw.get(name))) != "":
            err(name, f"Nilai '{f['label']}' bukan angka yang valid", raw.get(name))

    if jenis == "dtsen":
        kk = re.sub(r"\D", "", str(row.get("nomor_kartu_keluarga") or ""))
        if kk and len(kk) != 16:
            warn("nomor_kartu_keluarga", f"Nomor KK bukan 16 digit ({len(kk)} digit)", kk)
        desil = row.get("desil_nasional")
        if desil is not None and not (1 <= int(desil) <= 10):
            err("desil_nasional", "Desil nasional harus bernilai 1-10", desil)
        for pf in ("pbi_nas", "pbi_pemda"):
            v = row.get(pf)
            if v is not None and int(v) not in (0, 1):
                err(pf, f"Nilai {pf} harus 0 atau 1", v)
        jml = row.get("jumlah_anggota_keluarga")
        if jml is not None and (jml < 0 or jml > 30):
            warn("jumlah_anggota_keluarga", "Jumlah anggota keluarga di luar rentang wajar (0-30)", jml)
        luas = row.get("luas_lantai")
        if luas is not None and luas <= 0:
            warn("luas_lantai", "Luas lantai tidak wajar (<= 0)", luas)
        kel_norm = norm_name(row.get("kelurahan_desa"))
        kode_kel = _kode_str(row.get("kode_kelurahan_desa"))
        if kel_norm and kel_norm not in kel_index:
            warn("kelurahan_desa", "Nama kelurahan tidak ditemukan pada batas wilayah resmi "
                                   "(data tetap dapat diimpor)", row.get("kelurahan_desa"))
        if kode_kel and not kode_kel.isdigit():
            warn("kode_kelurahan_desa", "Kode kelurahan bukan angka", kode_kel)

    if jenis == "disabilitas":
        total = row.get("total")
        ragam = sum(int(row.get(k) or 0) for k in
                    ("fisik", "ganda", "intelektual", "mental",
                     "sensorik_pendengaran", "sensorik_penglihatan"))
        if total and ragam and total != ragam:
            warn("total", f"Total ({total}) tidak sama dengan jumlah ragam disabilitas ({ragam})", total)
        jk = int(row.get("laki_laki") or 0) + int(row.get("perempuan") or 0)
        if total and jk and total != jk:
            warn("total", f"Total ({total}) tidak sama dengan laki-laki + perempuan ({jk})", total)
        if not total and not ragam and not jk:
            warn("total", "Baris tidak memuat angka apa pun")

    if jenis == "gis_koordinat":
        lat, lng = row.get("latitude"), row.get("longitude")
        if lat is not None and not (-90 <= lat <= 90):
            err("latitude", "Latitude harus antara -90 dan 90", lat)
        if lng is not None and not (-180 <= lng <= 180):
            err("longitude", "Longitude harus antara -180 dan 180", lng)

    if jenis == "rad":
        if not str(row.get("program") or "") and not str(row.get("kegiatan") or ""):
            err("kegiatan", "Program dan Kegiatan tidak boleh kosong bersamaan")

    return errors, warnings


def dedupe_key(jenis: str, row: Dict[str, Any]) -> str:
    if jenis == "dtsen":
        kk = re.sub(r"\D", "", str(row.get("nomor_kartu_keluarga") or ""))
        wil = _kode_str(row.get("kode_kelurahan_desa")) or norm_name(row.get("kelurahan_desa"))
        return f"{kk}|{wil}"
    if jenis == "disabilitas":
        return f"{norm_name(row.get('kecamatan'))}|{norm_name(row.get('kelurahan'))}|{row.get('tahun') or ''}"
    if jenis == "rad":
        return "|".join(norm_name(row.get(k)) for k in
                        ("perangkat_daerah_penanggung_jawab", "program", "kegiatan", "sub_kegiatan"))
    if jenis == "gis_koordinat":
        return norm_name(row.get("kelurahan"))
    return json.dumps(row, sort_keys=True, default=str)


# --------------------------------------------------------------- ke dokumen DB
def to_document(jenis: str, row: Dict[str, Any], batch_id: str, cfg: Dict[str, Any],
                sumber: Dict[str, str]) -> Dict[str, Any]:
    if jenis == "dtsen":
        kk = re.sub(r"\D", "", str(row.get("nomor_kartu_keluarga") or ""))
        kel = etl.title_name(row.get("kelurahan_desa"))
        kec = etl.title_name(row.get("kecamatan"))
        src = {
            "desil_nasional": row.get("desil_nasional"),
            "pbi_nas": row.get("pbi_nas") or 0,
            "pbi_pemda": row.get("pbi_pemda") or 0,
        }
        for f in etl.HOUSING_FIELDS:
            src[f] = row.get(f)
        score, level, factors, levels, perlu = scoring.score_household(src, cfg)
        flags = scoring.summarize_levels(levels)
        doc: Dict[str, Any] = {
            "no_kk": kk, "no_kk_mask": scoring.mask_kk(kk),
            "kode_provinsi": _kode_str(row.get("kode_provinsi")),
            "provinsi": etl.title_name(row.get("provinsi")),
            "kode_kabupaten_kota": _kode_str(row.get("kode_kabupaten_kota")),
            "kabupaten_kota": etl.title_name(row.get("kabupaten_kota")),
            "kode_kecamatan": _kode_str(row.get("kode_kecamatan")),
            "kecamatan": kec,
            "kode_kelurahan": _kode_str(row.get("kode_kelurahan_desa")),
            "kelurahan": kel,
            "alamat": row.get("alamat") or "",
            "jumlah_anggota_keluarga": row.get("jumlah_anggota_keluarga") or 0,
            "kepala_keluarga": row.get("nama_anggota_keluarga") or "",
            "desil_nasional": row.get("desil_nasional"),
            "pbi_nas": row.get("pbi_nas") or 0,
            "pbi_pemda": row.get("pbi_pemda") or 0,
            "risk_score": score, "risk_level": level, "risk_factors": factors,
            "indikator_level": levels, "perlu_validasi": bool(perlu),
            "source_file": sumber.get("file", ""), "source_sheet": sumber.get("sheet", ""),
            "import_batch": batch_id, "imported_at": now_iso(),
        }
        # RT/RW hanya dari kolom eksplisit berkas (GeoTag-Verval); tidak dari teks alamat
        rt, rw = dtsen_ref.norm_rt_rw(row.get("rt")), dtsen_ref.norm_rt_rw(row.get("rw"))
        if rt or rw:
            doc.update({"rt": rt, "rw": rw, "rt_rw_sumber": "kolom_berkas_impor"})
        ref = dtsen_ref.make_ref(kk, doc["kode_kelurahan"], kel)
        if ref:
            doc["dtsen_ref"] = ref
        for f in etl.HOUSING_FIELDS:
            doc[f] = row.get(f)
        doc.update(flags)
        return doc

    if jenis == "disabilitas":
        total = row.get("total")
        if not total:
            total = sum(int(row.get(k) or 0) for k in
                        ("fisik", "ganda", "intelektual", "mental",
                         "sensorik_pendengaran", "sensorik_penglihatan")) or \
                    (int(row.get("laki_laki") or 0) + int(row.get("perempuan") or 0))
        kec = etl.title_name(row.get("kecamatan"))
        kel = etl.title_name(row.get("kelurahan"))
        return {
            "kecamatan": kec, "kecamatan_norm": norm_name(kec),
            "kelurahan": kel, "kelurahan_norm": norm_name(kel),
            "tahun": row.get("tahun") or datetime.now().year,
            "jumlah": int(total or 0), "total": int(total or 0),
            "laki_laki": row.get("laki_laki") or 0, "perempuan": row.get("perempuan") or 0,
            "usia_dibawah_18": row.get("usia_dibawah_18") or 0,
            "usia_18_59": row.get("usia_18_59") or 0,
            "usia_60_keatas": row.get("usia_60_keatas") or 0,
            "fisik": row.get("fisik") or 0, "ganda": row.get("ganda") or 0,
            "intelektual": row.get("intelektual") or 0, "mental": row.get("mental") or 0,
            "sensorik_pendengaran": row.get("sensorik_pendengaran") or 0,
            "sensorik_penglihatan": row.get("sensorik_penglihatan") or 0,
            "sumber": row.get("sumber") or sumber.get("file", ""),
            "import_batch": batch_id, "created_at": now_iso(),
        }

    if jenis == "rad":
        targets = {str(t): row.get(f"target_{t}") for t in (2023, 2024, 2025, 2026)}
        anggaran = {str(t): row.get(f"anggaran_{t}") for t in (2023, 2024, 2025, 2026)}
        return {
            "strategi_implementasi": row.get("strategi_implementasi") or "",
            "target_capaian": row.get("target_capaian") or "",
            "program": row.get("program") or "", "kegiatan": row.get("kegiatan") or "",
            "sub_kegiatan": row.get("sub_kegiatan") or "",
            "indikator_capaian": row.get("indikator_capaian") or "",
            "output_kegiatan": row.get("output_kegiatan") or "",
            "indikator_disabilitas": row.get("indikator_capaian_terkait_disabilitas") or "",
            "hambatan": row.get("hambatan_tantangan") or "",
            "satuan": row.get("satuan_target_kegiatan") or "",
            "targets": targets, "anggaran": anggaran,
            "target_2023": row.get("target_2023"), "target_2024": row.get("target_2024"),
            "target_2025": row.get("target_2025"), "target_2026": row.get("target_2026"),
            "anggaran_2023": row.get("anggaran_2023"), "anggaran_2024": row.get("anggaran_2024"),
            "anggaran_2025": row.get("anggaran_2025"), "anggaran_2026": row.get("anggaran_2026"),
            "lokasi": row.get("lokasi") or "",
            "spesifik": row.get("spesifik_tidak_spesifik") or "",
            "opd": row.get("perangkat_daerah_penanggung_jawab") or "",
            "keterangan": row.get("keterangan") or "",
            "import_batch": batch_id, "created_at": now_iso(),
        }

    # gis_koordinat
    kel = etl.title_name(row.get("kelurahan"))
    return {
        "kelurahan": kel, "kelurahan_norm": norm_name(kel),
        "kecamatan": etl.title_name(row.get("kecamatan")),
        "kode_kelurahan": _kode_str(row.get("kode_kelurahan")),
        "latitude": row.get("latitude"), "longitude": row.get("longitude"),
        "keterangan": row.get("keterangan") or "",
        "sumber": sumber.get("file", ""), "import_batch": batch_id,
        "updated_at": now_iso(),
    }


DB_FILTER = {
    "dtsen": lambda r: {"no_kk": re.sub(r"\D", "", str(r.get("nomor_kartu_keluarga") or "")),
                        "kode_kelurahan": _kode_str(r.get("kode_kelurahan_desa"))},
    "disabilitas": lambda r: {"kecamatan_norm": norm_name(r.get("kecamatan")),
                              "kelurahan_norm": norm_name(r.get("kelurahan"))},
    "rad": lambda r: {"program": r.get("program") or "", "kegiatan": r.get("kegiatan") or "",
                      "sub_kegiatan": r.get("sub_kegiatan") or ""},
    "gis_koordinat": lambda r: {"kelurahan_norm": norm_name(r.get("kelurahan"))},
}


# --------------------------------------------------------------- helper baca sesi
def _sheet_meta(sess: Dict[str, Any], sheet: str) -> Dict[str, Any]:
    for s in sess.get("sheets") or []:
        if s.get("name") == sheet:
            return s
    raise HTTPException(status_code=404, detail=f"Sheet '{sheet}' tidak ada pada berkas")


def iter_mapped_rows(src: SourceFile, sheet_meta: Dict[str, Any], mapping: Dict[str, str],
                     jenis: str):
    """Hasilkan (nomor_baris_excel, raw_by_target, normalized_row)."""
    df = read_sheet(src, sheet_meta["name"] if src.suffix != ".csv" else None,
                    header_row=int(sheet_meta.get("header_row") or 0))
    kolom_asli = {str(c): c for c in df.columns}
    pakai = {src: tgt for src, tgt in mapping.items() if src in kolom_asli and tgt}
    offset = int(sheet_meta.get("header_row") or 0) + 2  # baris data pertama pada Excel
    for i, (_, r) in enumerate(df.iterrows()):
        raw = {}
        kosong = True
        for src, tgt in pakai.items():
            v = clean_cell(r[kolom_asli[src]])
            raw[tgt] = v
            if str(v) != "":
                kosong = False
        if kosong:
            continue
        yield offset + i, raw, normalize_row(jenis, raw)


# --------------------------------------------------------------- template & laporan
def build_template() -> bytes:
    wb = Workbook()
    head_fill = PatternFill("solid", fgColor="1F3864")
    head_font = Font(color="FFFFFF", bold=True, size=10)
    urutan = [("DTSEN", "dtsen"), ("DISABILITAS", "disabilitas"),
              ("RAD_DISABILITAS", "rad"), ("GIS_KOORDINAT", "gis_koordinat")]
    for idx, (nama_sheet, jenis) in enumerate(urutan):
        ws = wb.active if idx == 0 else wb.create_sheet()
        ws.title = nama_sheet
        fields = DATASETS[jenis]["fields"]
        for c, f in enumerate(fields, start=1):
            cell = ws.cell(row=1, column=c, value=f["name"])
            cell.fill = head_fill
            cell.font = head_font
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
            ws.column_dimensions[cell.column_letter].width = max(14, min(30, len(f["name"]) + 4))
        for baris in range(2, 4):
            for c, f in enumerate(fields, start=1):
                ws.cell(row=baris, column=c, value=f.get("contoh") or "")
        ws.freeze_panes = "A2"

    ws = wb.create_sheet("PETUNJUK PENGISIAN")
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 38
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 46
    baris = 1
    ws.cell(row=baris, column=1, value="PETUNJUK PENGISIAN TEMPLATE IMPOR SIDATA").font = Font(bold=True, size=13)
    baris += 2
    for teks in [
        "1. Jangan mengubah/menghapus baris pertama (nama kolom) pada setiap sheet.",
        "2. Hapus 2 baris contoh sebelum mengunggah berkas.",
        "3. Kolom bertanda WAJIB harus terisi, baris yang kosong akan dilewati.",
        "4. Nilai berkode (mis. jenis lantai) diisi angka sesuai daftar kode DTSEN, arti kode "
        "dapat dikonfigurasi administrator pada menu Kode Referensi.",
        "5. Satu berkas boleh memuat beberapa sheet; saat impor Anda dapat memilih sheet.",
        "6. Nomor Kartu Keluarga wajib 16 digit dan dipakai sebagai kunci anti-duplikat.",
    ]:
        ws.cell(row=baris, column=1, value=teks)
        baris += 1
    baris += 1
    for nama_sheet, jenis in urutan:
        ws.cell(row=baris, column=1, value=f"SHEET {nama_sheet}").font = Font(bold=True)
        baris += 1
        for judul, col in (("Nama kolom", 1), ("Keterangan", 2), ("Wajib", 3), ("Contoh / catatan", 4)):
            c = ws.cell(row=baris, column=col, value=judul)
            c.font = head_font
            c.fill = head_fill
        baris += 1
        for f in DATASETS[jenis]["fields"]:
            ws.cell(row=baris, column=1, value=f["name"])
            ws.cell(row=baris, column=2, value=f["label"])
            ws.cell(row=baris, column=3, value="WAJIB" if f["required"] else "opsional")
            ws.cell(row=baris, column=4, value=f.get("keterangan") or str(f.get("contoh") or ""))
            baris += 1
        baris += 1
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_error_report(sess: Dict[str, Any]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "LAPORAN ERROR"
    judul = ["Sheet", "Baris Excel", "Tingkat", "Kolom", "Pesan", "Nilai"]
    for c, t in enumerate(judul, start=1):
        cell = ws.cell(row=1, column=c, value=t)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="B91C1C")
    lebar = [18, 12, 10, 28, 70, 26]
    for i, w in enumerate(lebar, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    r = 2
    for issue in sess.get("issues") or []:
        ws.cell(row=r, column=1, value=issue.get("sheet"))
        ws.cell(row=r, column=2, value=issue.get("baris"))
        ws.cell(row=r, column=3, value=issue.get("tingkat"))
        ws.cell(row=r, column=4, value=issue.get("kolom"))
        ws.cell(row=r, column=5, value=issue.get("pesan"))
        ws.cell(row=r, column=6, value=issue.get("nilai"))
        r += 1
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------- model input
class AnalyzeInput(BaseModel):
    session_id: str
    jenis: Optional[str] = None


class ValidateInput(BaseModel):
    session_id: str
    jenis: str
    sheets: List[str] = Field(default_factory=list)
    mapping: Dict[str, str] = Field(default_factory=dict)


class ExecuteInput(ValidateInput):
    mode: str = "update"           # skip | update | update_changed
    chunk_size: int = DEFAULT_CHUNK
    lanjut_walau_error: bool = True


# --------------------------------------------------------------- router
def build_router(db, current_user_dep, editor_dep, admin_dep) -> APIRouter:
    router = APIRouter(prefix="/import", tags=["import"])

    async def _kel_index() -> Dict[str, Dict[str, Any]]:
        rows = await db.geo_kelurahan.find({}).to_list(500)
        return {r.get("kelurahan_norm"): r for r in rows if r.get("kelurahan_norm")}

    async def _audit(user: Dict[str, Any], aksi: str, entitas: str, ref: str, detail: Any):
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()), "user": user.get("email"), "role": user.get("role"),
            "aksi": aksi, "entitas": entitas, "ref": ref,
            "detail": json.dumps(detail, default=str)[:1500], "created_at": now_iso(),
        })

    # ---------------------------------------------------------------- skema
    @router.get("/datasets")
    async def datasets(user: dict = Depends(current_user_dep)):
        return {"datasets": [
            {"jenis": j, "label": c["label"], "collection": c["collection"],
             "kunci_duplikat": c["kunci"],
             "fields": [{k: v for k, v in f.items() if k != "synonyms"} for f in c["fields"]]}
            for j, c in DATASETS.items()]}

    @router.get("/template")
    async def template(user: dict = Depends(current_user_dep)):
        data = build_template()
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="Template_Impor_SIDATA.xlsx"'})

    # ---------------------------------------------------------------- berkas (DB)
    async def _save_file(session_id: str, data: bytes):
        """Simpan berkas ke koleksi `import_files` dalam potongan base64."""
        docs = []
        for seq, start in enumerate(range(0, len(data), FILE_CHUNK_BYTES)):
            docs.append({
                "id": f"{session_id}-{seq:05d}", "session_id": session_id, "seq": seq,
                "data": base64.b64encode(data[start:start + FILE_CHUNK_BYTES]).decode("ascii"),
                "created_at": now_iso(),
            })
        for d in docs:  # satu per satu agar paket SQL tetap kecil
            await db.import_files.insert_one(d)

    async def _load_file(sess: Dict[str, Any]) -> Optional[SourceFile]:
        """Rakit ulang berkas dari DB; None bila sudah tidak tersedia."""
        chunks = await db.import_files.find({"session_id": sess["id"]}) \
            .sort("seq", 1).to_list(100000)
        if not chunks:
            return None
        data = b"".join(base64.b64decode(c["data"]) for c in chunks)
        return SourceFile(sess.get("filename") or f"berkas{sess.get('ext', '')}", data)

    async def _file_exists(session_id: str) -> bool:
        return await db.import_files.count_documents({"session_id": session_id}) > 0

    # ---------------------------------------------------------------- upload
    @router.post("/upload")
    async def upload(file: UploadFile = File(...), user: dict = Depends(editor_dep)):
        ext = Path(file.filename or "").suffix.lower()
        if ext not in (".xlsx", ".xls", ".csv"):
            raise HTTPException(status_code=422,
                                detail="Format berkas harus .xlsx, .xls, atau .csv")
        session_id = str(uuid.uuid4())
        nama = Path(file.filename or "").name or f"berkas{ext}"
        buf = bytearray()
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            buf.extend(chunk)
            if len(buf) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413,
                                    detail=f"Ukuran berkas melebihi batas "
                                           f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
        data = bytes(buf)
        ukuran = len(data)
        if not ukuran:
            raise HTTPException(status_code=422, detail="Berkas kosong")
        src = SourceFile(nama, data)
        try:
            sheets = describe_file(src)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=422,
                                detail=f"Berkas tidak dapat dibaca: {type(e).__name__}. "
                                       "Pastikan berkas Excel/CSV tidak rusak dan tidak terproteksi.")
        await _save_file(session_id, data)
        kolom_pertama = next((s["columns"] for s in sheets if s["columns"]), [])
        jenis = detect_dataset(kolom_pertama, nama)
        doc = {
            "id": session_id, "filename": nama, "storage": "db",
            "size": ukuran, "ext": ext, "jenis_terdeteksi": jenis,
            "sheets": sheets, "total_rows": sum(s["rows"] for s in sheets),
            "user": user.get("email"), "status": "diunggah", "created_at": now_iso(),
        }
        await db.import_sessions.insert_one(dict(doc))
        return {k: v for k, v in doc.items() if k not in ("storage", "_id")}

    @router.post("/analyze")
    async def analyze(inp: AnalyzeInput, user: dict = Depends(editor_dep)):
        sess = await db.import_sessions.find_one({"id": inp.session_id})
        if not sess:
            raise HTTPException(status_code=404, detail="Sesi impor tidak ditemukan")
        jenis = inp.jenis or sess.get("jenis_terdeteksi") or "dtsen"
        if jenis not in DATASETS:
            raise HTTPException(status_code=422, detail=f"Jenis dataset '{jenis}' tidak dikenal")
        hasil = []
        for s in sess.get("sheets") or []:
            mapping, belum = suggest_mapping(s.get("columns") or [], jenis)
            wajib_belum = [f["name"] for f in DATASETS[jenis]["fields"]
                           if f["required"] and f["name"] in belum]
            hasil.append({
                "sheet": s["name"], "rows": s["rows"], "columns": s.get("columns") or [],
                "mapping": mapping, "belum_terpetakan": belum,
                "wajib_belum_terpetakan": wajib_belum,
                "siap": len(wajib_belum) == 0 and s["rows"] > 0,
            })
        return {"session_id": inp.session_id, "jenis": jenis,
                "label": DATASETS[jenis]["label"],
                "kunci_duplikat": DATASETS[jenis]["kunci"],
                "fields": [{k: v for k, v in f.items() if k != "synonyms"}
                           for f in DATASETS[jenis]["fields"]],
                "sheets": hasil}

    # ---------------------------------------------------------------- validasi
    @router.post("/validate")
    async def validate(inp: ValidateInput, user: dict = Depends(editor_dep)):
        sess = await db.import_sessions.find_one({"id": inp.session_id})
        if not sess:
            raise HTTPException(status_code=404, detail="Sesi impor tidak ditemukan")
        if inp.jenis not in DATASETS:
            raise HTTPException(status_code=422, detail="Jenis dataset tidak dikenal")
        src = await _load_file(sess)
        if src is None:
            raise HTTPException(status_code=410, detail="Berkas unggahan sudah tidak tersedia, silakan unggah ulang")
        sheets = inp.sheets or [s["name"] for s in sess.get("sheets") or [] if s["rows"] > 0]
        kel_index = await _kel_index()
        issues: List[Dict[str, Any]] = []
        preview: List[Dict[str, Any]] = []
        ringkasan: List[Dict[str, Any]] = []
        keys_seen: Dict[str, Tuple[str, int]] = {}
        total = valid = warning = error = duplikat_internal = 0

        for sheet in sheets:
            meta = _sheet_meta(sess, sheet)
            s_total = s_valid = s_warn = s_err = s_dup = 0
            for baris, raw, row in iter_mapped_rows(src, meta, inp.mapping, inp.jenis):
                s_total += 1
                errs, warns = validate_row(inp.jenis, row, raw, kel_index)
                key = dedupe_key(inp.jenis, row)
                if key in keys_seen:
                    s_dup += 1
                    warns.append({"kolom": "-",
                                  "pesan": f"Duplikat di dalam berkas (sama dengan baris "
                                           f"{keys_seen[key][1]} sheet {keys_seen[key][0]})",
                                  "nilai": key[:60]})
                else:
                    keys_seen[key] = (sheet, baris)
                for tingkat, daftar in (("error", errs), ("warning", warns)):
                    for it in daftar:
                        if len(issues) < MAX_ISSUES_STORED:
                            issues.append({"sheet": sheet, "baris": baris, "tingkat": tingkat,
                                           **it})
                if errs:
                    s_err += 1
                elif warns:
                    s_warn += 1
                else:
                    s_valid += 1
                if len(preview) < PREVIEW_ROWS:
                    preview.append({"sheet": sheet, "baris": baris,
                                    "status": "error" if errs else ("warning" if warns else "valid"),
                                    **{k: v for k, v in row.items() if v not in (None, "")}})
            ringkasan.append({"sheet": sheet, "total": s_total, "valid": s_valid,
                              "warning": s_warn, "error": s_err, "duplikat_internal": s_dup})
            total += s_total
            valid += s_valid
            warning += s_warn
            error += s_err
            duplikat_internal += s_dup

        # duplikat terhadap database
        duplikat_db = 0
        if inp.jenis == "dtsen":
            existing = {f"{h.get('no_kk')}|{h.get('kode_kelurahan') or norm_name(h.get('kelurahan'))}"
                        for h in await db.households.find({}).to_list(200000)}
            duplikat_db = sum(1 for k in keys_seen if k in existing)
        elif inp.jenis == "disabilitas":
            existing = {f"{d.get('kecamatan_norm')}|{d.get('kelurahan_norm')}|{d.get('tahun') or ''}"
                        for d in await db.disability_region_stats.find({}).to_list(5000)}
            duplikat_db = sum(1 for k in keys_seen if k in existing)
        elif inp.jenis == "gis_koordinat":
            existing = {g.get("kelurahan_norm") for g in await db.gis_locations.find({}).to_list(1000)}
            duplikat_db = sum(1 for k in keys_seen if k in existing)

        await db.import_sessions.update_one({"id": inp.session_id}, {"$set": {
            "status": "tervalidasi", "jenis": inp.jenis, "mapping": inp.mapping,
            "sheets_dipilih": sheets, "issues": issues,
            "validasi": {"total": total, "valid": valid, "warning": warning, "error": error,
                         "duplikat_internal": duplikat_internal, "duplikat_db": duplikat_db,
                         "per_sheet": ringkasan},
            "validated_at": now_iso()}})
        return {"session_id": inp.session_id, "jenis": inp.jenis, "total": total,
                "valid": valid, "warning": warning, "error": error,
                "duplikat_internal": duplikat_internal, "duplikat_db": duplikat_db,
                "per_sheet": ringkasan, "issues": issues[:200],
                "issues_total": len(issues), "preview": preview,
                "punya_laporan_error": bool(issues)}

    @router.get("/errors/{session_id}")
    async def error_report(session_id: str, format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
                           user: dict = Depends(editor_dep)):
        sess = await db.import_sessions.find_one({"id": session_id})
        if not sess:
            raise HTTPException(status_code=404, detail="Sesi impor tidak ditemukan")
        issues = sess.get("issues") or []
        if format == "csv":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["sheet", "baris_excel", "tingkat", "kolom", "pesan", "nilai"])
            for it in issues:
                w.writerow([it.get("sheet"), it.get("baris"), it.get("tingkat"),
                            it.get("kolom"), it.get("pesan"), it.get("nilai")])
            return StreamingResponse(io.BytesIO(buf.getvalue().encode("utf-8-sig")),
                                     media_type="text/csv",
                                     headers={"Content-Disposition":
                                              f'attachment; filename="laporan_error_{session_id[:8]}.csv"'})
        data = build_error_report(sess)
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition":
                     f'attachment; filename="laporan_error_{session_id[:8]}.xlsx"'})

    # ---------------------------------------------------------------- eksekusi
    async def _run_import(job_id: str, sess: Dict[str, Any], inp: ExecuteInput,
                          user: Dict[str, Any]):
        jenis = inp.jenis
        coll_name = DATASETS[jenis]["collection"]
        coll = getattr(db, coll_name)
        src = await _load_file(sess)
        sheets = inp.sheets or sess.get("sheets_dipilih") or \
            [s["name"] for s in sess.get("sheets") or [] if s["rows"] > 0]
        cfg = await db.scoring_config.find_one({}) or scoring.default_config()
        kel_index = await _kel_index()
        batch = {
            "id": str(uuid.uuid4()), "filename": sess.get("filename"),
            "sheet": ", ".join(sheets), "jenis": jenis, "user": user.get("email"),
            "uploaded_at": now_iso(), "total_rows": 0, "inserted": 0, "updated": 0,
            "duplicate": 0, "failed": 0, "errors": [], "status": "berjalan",
            "mode": inp.mode, "sumber": "wizard",
        }
        await db.import_batches.insert_one(dict(batch))
        stat = {"processed": 0, "inserted": 0, "updated": 0, "skipped": 0, "failed": 0}
        total_perkiraan = sum(_sheet_meta(sess, s)["rows"] for s in sheets)
        await db.import_jobs.update_one({"id": job_id}, {"$set": {
            "status": "berjalan", "total": total_perkiraan, "batch_id": batch["id"],
            "started_at": now_iso()}})

        buffer_insert: List[Dict[str, Any]] = []
        keys_batch: set = set()
        errors_sample: List[Dict[str, Any]] = []

        async def flush_insert():
            if buffer_insert:
                await coll.insert_many(list(buffer_insert))
                buffer_insert.clear()

        try:
            if src is None:
                raise RuntimeError("Berkas unggahan sudah tidak tersedia")
            for sheet in sheets:
                meta = _sheet_meta(sess, sheet)
                for baris, raw, row in iter_mapped_rows(src, meta, inp.mapping, jenis):
                    stat["processed"] += 1
                    errs, _warns = validate_row(jenis, row, raw, kel_index)
                    if errs:
                        stat["failed"] += 1
                        if len(errors_sample) < 200:
                            errors_sample.append({"sheet": sheet, "baris": baris,
                                                  "pesan": errs[0]["pesan"]})
                        if not inp.lanjut_walau_error:
                            raise RuntimeError(f"Baris {baris}: {errs[0]['pesan']}")
                        continue
                    key = dedupe_key(jenis, row)
                    if key in keys_batch:
                        stat["skipped"] += 1
                        continue
                    keys_batch.add(key)
                    doc = to_document(jenis, row, batch["id"], cfg,
                                      {"file": sess.get("filename", ""), "sheet": sheet})
                    filt = {k: v for k, v in DB_FILTER[jenis](row).items() if v not in (None, "")}
                    lama = await coll.find_one(filt) if filt else None
                    if lama:
                        if inp.mode == "skip":
                            stat["skipped"] += 1
                        else:
                            upd = dict(doc)
                            upd.pop("id", None)
                            if inp.mode == "update_changed":
                                upd = {k: v for k, v in upd.items()
                                       if v not in (None, "", 0) and lama.get(k) != v}
                            if upd:
                                upd["updated_at"] = now_iso()
                                upd["import_batch"] = batch["id"]
                                await coll.update_one({"id": lama.get("id")}, {"$set": upd})
                                stat["updated"] += 1
                            else:
                                stat["skipped"] += 1
                    else:
                        doc["id"] = str(uuid.uuid4())
                        buffer_insert.append(doc)
                        stat["inserted"] += 1
                        if len(buffer_insert) >= max(50, min(2000, inp.chunk_size)):
                            await flush_insert()
                    if stat["processed"] % 200 == 0:
                        await db.import_jobs.update_one({"id": job_id}, {"$set": {
                            **stat, "updated_at": now_iso()}})
                        await asyncio.sleep(0)
            await flush_insert()

            # anggota keluarga untuk DTSEN (nama kepala keluarga)
            if jenis == "dtsen":
                anggota = []
                for h in await db.households.find({"import_batch": batch["id"]}).to_list(100000):
                    if h.get("kepala_keluarga"):
                        anggota.append({"id": str(uuid.uuid4()), "household_id": h.get("id"),
                                        "no_kk": h.get("no_kk"), "nama": h.get("kepala_keluarga"),
                                        "peran": "Kepala Keluarga",
                                        "kode_kelurahan": h.get("kode_kelurahan"),
                                        "import_batch": batch["id"], "created_at": now_iso()})
                for i in range(0, len(anggota), 500):
                    await db.household_members.insert_many(anggota[i:i + 500])

            # hitung ulang agregat & statistik wilayah
            if jenis in ("dtsen", "disabilitas"):
                runner = etl.Importer(db)
                await runner.build_aggregates()

            await db.import_batches.update_one({"id": batch["id"]}, {"$set": {
                "total_rows": stat["processed"], "inserted": stat["inserted"],
                "updated": stat["updated"], "duplicate": stat["skipped"],
                "failed": stat["failed"], "errors": errors_sample[:50],
                "status": "success" if stat["failed"] == 0 else "partial",
                "finished_at": now_iso()}})
            await db.import_jobs.update_one({"id": job_id}, {"$set": {
                **stat, "status": "selesai", "errors": errors_sample[:50],
                "finished_at": now_iso(),
                "pesan": f"Impor selesai: {stat['inserted']} baru, {stat['updated']} diperbarui, "
                         f"{stat['skipped']} dilewati, {stat['failed']} gagal"}})
            await db.import_sessions.update_one({"id": sess["id"]},
                                                {"$set": {"status": "terimpor"}})
            await _audit(user, "import_excel", coll_name, batch["id"],
                         {"jenis": jenis, "berkas": sess.get("filename"), "mode": inp.mode, **stat})
        except Exception as e:  # noqa: BLE001
            await db.import_jobs.update_one({"id": job_id}, {"$set": {
                **stat, "status": "gagal", "finished_at": now_iso(),
                "pesan": f"Impor dihentikan: {e}"}})
            await db.import_batches.update_one({"id": batch["id"]}, {"$set": {
                "status": "failed", "failed": stat["failed"] + 1,
                "errors": errors_sample[:50] + [{"pesan": str(e)[:200]}],
                "finished_at": now_iso()}})

    @router.post("/execute")
    async def execute(inp: ExecuteInput, user: dict = Depends(editor_dep)):
        sess = await db.import_sessions.find_one({"id": inp.session_id})
        if not sess:
            raise HTTPException(status_code=404, detail="Sesi impor tidak ditemukan")
        if inp.jenis not in DATASETS:
            raise HTTPException(status_code=422, detail="Jenis dataset tidak dikenal")
        if inp.mode not in ("skip", "update", "update_changed"):
            raise HTTPException(status_code=422,
                                detail="Mode harus skip, update, atau update_changed")
        if not await _file_exists(inp.session_id):
            raise HTTPException(status_code=410, detail="Berkas unggahan sudah tidak tersedia")
        job_id = str(uuid.uuid4())
        await db.import_jobs.insert_one({
            "id": job_id, "session_id": inp.session_id, "jenis": inp.jenis,
            "user": user.get("email"), "status": "menunggu", "total": 0, "processed": 0,
            "inserted": 0, "updated": 0, "skipped": 0, "failed": 0,
            "pesan": "Menyiapkan impor…", "created_at": now_iso()})
        asyncio.create_task(_run_import(job_id, sess, inp, user))
        return {"job_id": job_id, "status": "menunggu"}

    @router.get("/job/{job_id}")
    async def job_status(job_id: str, user: dict = Depends(current_user_dep)):
        job = await db.import_jobs.find_one({"id": job_id})
        if not job:
            raise HTTPException(status_code=404, detail="Proses impor tidak ditemukan")
        job.pop("_id", None)
        total = int(job.get("total") or 0)
        job["persen"] = round(min(100, (int(job.get("processed") or 0) / total * 100)), 1) if total else 0
        return job

    @router.get("/history")
    async def history(limit: int = Query(50, ge=1, le=200),
                      user: dict = Depends(current_user_dep)):
        batches = await db.import_batches.find({}).sort("uploaded_at", -1).to_list(limit)
        for b in batches:
            b.pop("_id", None)
        return {"total": len(batches), "items": batches}

    @router.delete("/batch/{batch_id}")
    async def rollback(batch_id: str, user: dict = Depends(admin_dep)):
        batch = await db.import_batches.find_one({"id": batch_id})
        if not batch:
            raise HTTPException(status_code=404, detail="Batch impor tidak ditemukan")
        jenis = batch.get("jenis") or ""
        peta = {"dtsen": ["households", "household_members"],
                "disabilitas": ["disability_region_stats"],
                "rad": ["rad_items"], "gis_koordinat": ["gis_locations"]}
        targets = peta.get(jenis) or []
        if not targets:
            raise HTTPException(status_code=422,
                                detail=f"Batch jenis '{jenis}' tidak dapat dibatalkan otomatis")
        dihapus = 0
        for name in targets:
            coll = getattr(db, name)
            jml = await coll.count_documents({"import_batch": batch_id})
            if jml:
                await coll.delete_many({"import_batch": batch_id})
                dihapus += jml
        if jenis in ("dtsen", "disabilitas"):
            runner = etl.Importer(db)
            await runner.build_aggregates()
        await db.import_batches.update_one({"id": batch_id}, {"$set": {
            "status": "dibatalkan", "rolled_back_at": now_iso(),
            "rolled_back_by": user.get("email")}})
        await _audit(user, "rollback_import", ", ".join(targets), batch_id,
                     {"dihapus": dihapus, "jenis": jenis})
        return {"batch_id": batch_id, "dihapus": dihapus, "status": "dibatalkan"}

    return router
