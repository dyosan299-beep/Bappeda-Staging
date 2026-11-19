"""PETA INKLUSI - Matriks evaluasi dan program.

Tiga matriks dalam satu modul:

1. ``/matriks/kategori`` - kemiskinan ekstrem, stunting, ATS, dan anak jalanan per
   kecamatan. Dibaca dari koleksi ``regions`` (sumber yang sama dengan dashboard
   publik), sehingga angkanya selalu sinkron dengan fitur lain.
2. ``/matriks/oppkpke`` - matriks evaluasi OPPKPKE Semester 1. Kolom mengikuti
   kertas kerja resmi ``MATRIKS EVALUASI OPPKPKE``: strategi, OPD pelaksana,
   program, sub kegiatan, aktivitas real (langsung/tidak langsung/penunjang),
   alokasi anggaran, sumber pembiayaan, sifat bantuan, lokasi, sasaran, besaran
   manfaat, realisasi anggaran Semester 1 2025, total realisasi 2025, dan
   target 2026.
3. ``/matriks/ats-program`` - matriks program, kegiatan, dan anggaran ATS dengan
   kolom target/anggaran/realisasi/persentase untuk 2025 dan 2026 serta pagu 2027.

Dua matriks terakhir hanya berisi data yang diimpor dari berkas resmi; modul ini
tidak pernah mengarang angka. Impor bersifat atomik: bila ada baris bermasalah,
tidak ada satu pun baris yang disimpan, dan pesan galat menyebut nomor barisnya.
"""
from __future__ import annotations

import io
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

import seed_data as seed
from inklusi import _clean, audit

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

MAX_UPLOAD = 15 * 1024 * 1024
MAX_BARIS = 5000
TAHUN_ATS = (2025, 2026, 2027)

# ------------------------------------------------------------------ kontrak kolom
OPDKPKE_KOLOM = [
    "no", "strategi", "opd", "program", "sub_kegiatan",
    "aktivitas_langsung", "aktivitas_tidak_langsung", "aktivitas_penunjang",
    "anggaran", "sumber_pembiayaan", "sifat_bantuan", "lokasi", "jumlah_sasaran",
    "besaran_manfaat", "jenis_bantuan", "durasi",
    "realisasi_sem1_2025", "total_realisasi_2025", "target_2026",
]
ATS_KOLOM = [
    "no", "sasaran", "program", "kegiatan", "sub_kegiatan", "opd",
    "target_2025", "anggaran_2025", "realisasi_2025", "persen_2025",
    "target_2026", "anggaran_2026", "realisasi_2026", "persen_2026", "anggaran_2027",
]
DISABILITAS_KOLOM = [
    "no", "strategi", "target_capaian", "program", "kegiatan", "sub_kegiatan",
    "indikator", "output", "indikator_disabilitas", "hambatan", "satuan",
    "target_2025", "target_2026", "capaian_2025", "capaian_2026",
    "anggaran_2025", "anggaran_2026", "realisasi_2025", "realisasi_2026",
    "lokasi", "spesifik", "opd", "keterangan",
]

OPDKPKE_TEKS = [
    "strategi", "opd", "program", "sub_kegiatan",
    "aktivitas_langsung", "aktivitas_tidak_langsung", "aktivitas_penunjang",
    "sumber_pembiayaan", "sifat_bantuan", "lokasi", "jumlah_sasaran",
    "besaran_manfaat", "jenis_bantuan", "durasi", "target_2026",
]
OPDKPKE_ANGKA = ["anggaran", "realisasi_sem1_2025", "total_realisasi_2025"]
ATS_TEKS = ["sasaran", "program", "kegiatan", "sub_kegiatan", "opd", "target_2025", "target_2026"]
ATS_ANGKA = ["anggaran_2025", "realisasi_2025", "persen_2025",
             "anggaran_2026", "realisasi_2026", "persen_2026", "anggaran_2027"]
DISABILITAS_TEKS = [
    "strategi", "target_capaian", "program", "kegiatan", "sub_kegiatan",
    "indikator", "output", "indikator_disabilitas", "hambatan", "satuan",
    "target_2025", "target_2026", "capaian_2025", "capaian_2026",
    "lokasi", "spesifik", "opd", "keterangan",
]
DISABILITAS_ANGKA = ["anggaran_2025", "anggaran_2026", "realisasi_2025", "realisasi_2026"]

LABEL = {
    "no": "No",
    "strategi": "Strategi OPPKPKE",
    "opd": "Perangkat Daerah Pelaksana",
    "program": "Program",
    "sub_kegiatan": "Sub Kegiatan",
    "aktivitas_langsung": "Aktivitas Real - Langsung",
    "aktivitas_tidak_langsung": "Aktivitas Real - Tidak Langsung",
    "aktivitas_penunjang": "Aktivitas Real - Penunjang",
    "anggaran": "Alokasi Anggaran (Rp)",
    "sumber_pembiayaan": "Sumber Pembiayaan",
    "sifat_bantuan": "Sifat Bantuan",
    "lokasi": "Lokasi",
    "jumlah_sasaran": "Jumlah Sasaran Penerima Manfaat",
    "besaran_manfaat": "Besaran Manfaat",
    "jenis_bantuan": "Jenis Bantuan",
    "durasi": "Durasi Pemberian Bantuan",
    "realisasi_sem1_2025": "Realisasi Anggaran Semester 1 Tahun 2025 (Rp)",
    "total_realisasi_2025": "Total Realisasi Anggaran 2025 (Rp)",
    "target_2026": "Target 2026",
    "sasaran": "Sasaran/Permasalahan ATS",
    "kegiatan": "Kegiatan",
    "target_2025": "Target 2025",
    "anggaran_2025": "Anggaran 2025 (Rp) - Anggaran Perubahan",
    "realisasi_2025": "Realisasi Anggaran Tahun 2025 (Rp)",
    "persen_2025": "Persentase Capaian Tahun 2025 (%)",
    "anggaran_2026": "Anggaran 2026 (Rp)",
    "realisasi_2026": "Realisasi Anggaran Tahun 2026 (Rp) Semester 1",
    "persen_2026": "Persentase Capaian Tahun 2026 Semester 1 (%)",
    "anggaran_2027": "Anggaran 2027 (Rp)",
    "target_capaian": "Target Capaian",
    "indikator": "Indikator Capaian",
    "output": "Output Kegiatan",
    "indikator_disabilitas": "Indikator Capaian Terkait Penyandang Disabilitas",
    "hambatan": "Hambatan/Tantangan",
    "satuan": "Satuan",
    "capaian_2025": "Capaian Target 2025",
    "capaian_2026": "Capaian Target 2026",
    "spesifik": "Spesifik/Tidak Spesifik",
    "keterangan": "Keterangan",
}

JENIS: Dict[str, Dict[str, Any]] = {
    "oppkpke": {
        "label": "Evaluasi OPPKPKE",
        "koleksi": "oppkpke_items",
        "columns": OPDKPKE_KOLOM,
        "teks": OPDKPKE_TEKS,
        "angka": OPDKPKE_ANGKA,
        "wajib": ["opd"],
        "wajib_salah_satu": ["program", "sub_kegiatan"],
        "periode": ["semester", "tahun"],
        "nama_berkas": "template_matriks_oppkpke.xlsx",
        "petunjuk": [
            "MATRIKS EVALUASI OPPKPKE - PETA INKLUSI",
            "",
            "1. Isi lembar MATRIKS. Satu baris = satu sub kegiatan yang dievaluasi.",
            "2. Kolom wajib: opd. Isi juga program atau sub_kegiatan.",
            "3. Kolom aktivitas real boleh berupa angka atau uraian (mis. '48 kali kegiatan').",
            "4. Kolom angka: anggaran, realisasi_sem1_2025, total_realisasi_2025.",
            "   Gunakan angka tanpa pemisah ribuan, atau format Indonesia (1.250.000).",
            "5. Semester dan tahun tidak diisi di berkas: gunakan pilihan Semester/Tahun",
            "   pada halaman Matriks sebelum mengunggah.",
            "6. Impor akan MENGGANTI seluruh baris untuk semester/tahun yang dipilih.",
            "7. Jangan mengubah nama kolom pada baris pertama; sistem membacanya sebagai kunci.",
            "8. Data disimpan hanya bila seluruh baris valid.",
            "",
            "Padanan nama kolom resmi: lihat lembar REFERENSI.",
        ],
    },
    "ats-program": {
        "label": "Program Kegiatan ATS",
        "koleksi": "ats_program_items",
        "columns": ATS_KOLOM,
        "teks": ATS_TEKS,
        "angka": ATS_ANGKA,
        "wajib": ["opd"],
        "wajib_salah_satu": ["program", "sub_kegiatan"],
        "periode": [],
        "nama_berkas": "template_matriks_program_ats.xlsx",
        "petunjuk": [
            "MATRIKS PROGRAM, KEGIATAN DAN ANGGARAN ATS (ANAK TIDAK SEKOLAH) - PETA INKLUSI",
            "",
            "1. Isi lembar MATRIKS. Satu baris = satu program/kegiatan penanganan ATS.",
            "2. Kolom wajib: opd. Isi juga program atau sub_kegiatan.",
            "3. target_2025 dan target_2026 boleh berupa uraian capaian.",
            "4. Kolom angka: anggaran, realisasi, dan persen capaian untuk 2025/2026,",
            "   serta anggaran_2027. Boleh memakai format Indonesia (1.250.000).",
            "5. Impor akan MENGGANTI seluruh isi matriks program ATS dengan isi berkas.",
            "6. Jangan mengubah nama kolom pada baris pertama; sistem membacanya sebagai kunci.",
            "7. Data disimpan hanya bila seluruh baris valid.",
            "",
            "Padanan nama kolom resmi: lihat lembar REFERENSI.",
        ],
    },
    "disabilitas": {
        "label": "Matriks Disabilitas",
        "koleksi": "disabilitas_items",
        "columns": DISABILITAS_KOLOM,
        "teks": DISABILITAS_TEKS,
        "angka": DISABILITAS_ANGKA,
        "wajib": ["opd"],
        "wajib_salah_satu": ["program", "kegiatan", "sub_kegiatan"],
        "periode": [],
        "nama_berkas": "template_matriks_disabilitas.xlsx",
        "petunjuk": [
            "MATRIKS MONITORING DAN EVALUASI KEGIATAN DISABILITAS - PETA INKLUSI",
            "",
            "1. Isi lembar MATRIKS. Satu baris = satu sub kegiatan yang berpihak pada",
            "   penyandang disabilitas.",
            "2. Kolom wajib: opd. Isi juga program atau sub_kegiatan.",
            "3. Kolom target dan capaian boleh berupa uraian (mis. '2 Orang', '1 Laporan').",
            "4. Kolom angka: anggaran_2025, anggaran_2026, realisasi_2025, realisasi_2026.",
            "   Boleh memakai format Indonesia (1.250.000).",
            "5. Impor akan MENGGANTI seluruh isi matriks disabilitas dengan isi berkas.",
            "6. Jangan mengubah nama kolom pada baris pertama; sistem membacanya sebagai kunci.",
            "7. Data disimpan hanya bila seluruh baris valid.",
            "",
            "Padanan nama kolom resmi: lihat lembar REFERENSI.",
        ],
    },
}

_ALIAS = {
    # OPPKPKE
    "no": "no", "nomor": "no",
    "strategi": "strategi", "strategi_oppkpke": "strategi",
    "opd": "opd", "perangkat_daerah_pelaksana": "opd", "nama_opd": "opd", "instansi": "opd",
    "program": "program", "nama_program": "program",
    "sub_kegiatan": "sub_kegiatan", "subkegiatan": "sub_kegiatan", "sub_keg": "sub_kegiatan",
    "aktivitas_langsung": "aktivitas_langsung", "aktivitas_real_langsung": "aktivitas_langsung",
    "langsung": "aktivitas_langsung",
    "aktivitas_tidak_langsung": "aktivitas_tidak_langsung",
    "aktivitas_real_tidak_langsung": "aktivitas_tidak_langsung", "tidak_langsung": "aktivitas_tidak_langsung",
    "aktivitas_penunjang": "aktivitas_penunjang", "aktivitas_real_penunjang": "aktivitas_penunjang",
    "penunjang": "aktivitas_penunjang",
    "anggaran": "anggaran", "alokasi_anggaran": "anggaran", "alokasi_anggaran_rp": "anggaran",
    "pagu": "anggaran", "pagu_anggaran": "anggaran",
    "sumber_pembiayaan": "sumber_pembiayaan",
    "sifat_bantuan": "sifat_bantuan",
    "lokasi": "lokasi",
    "jumlah_sasaran": "jumlah_sasaran", "jumlah_sasaran_penerima_manfaat": "jumlah_sasaran",
    "besaran_manfaat": "besaran_manfaat",
    "jenis_bantuan": "jenis_bantuan",
    "durasi": "durasi", "durasi_pemberian_bantuan": "durasi",
    "realisasi_sem1_2025": "realisasi_sem1_2025",
    "realisasi_anggaran_semester_1_tahun_2025_rp": "realisasi_sem1_2025",
    "realisasi_anggaran_semester_1_2025": "realisasi_sem1_2025",
    "total_realisasi_2025": "total_realisasi_2025",
    "total_realisasi_anggaran_2025_rp": "total_realisasi_2025",
    "total": "total_realisasi_2025",
    "target_2026": "target_2026",
    # ATS
    "sasaran": "sasaran", "sasaran_permasalahan_ats": "sasaran",
    "kegiatan": "kegiatan", "nama_kegiatan": "kegiatan",
    "sub_kegiatan_uraian": "sub_kegiatan", "uraian": "sub_kegiatan",
    "opd_penanggung_jawab": "opd", "penanggung_jawab": "opd",
    "target_2025": "target_2025",
    "anggaran_2025": "anggaran_2025", "anggaran_2025_rp_anggaran_perubahan": "anggaran_2025",
    "anggaran_2025_rp": "anggaran_2025",
    "realisasi_2025": "realisasi_2025", "realisasi_anggaran_tahun_2025_rp": "realisasi_2025",
    "persen_2025": "persen_2025", "persentase_capaian_tahun_2025": "persen_2025",
    "persentase_capaian_2025": "persen_2025",
    "anggaran_2026": "anggaran_2026", "anggaran_2026_rp": "anggaran_2026",
    "realisasi_2026": "realisasi_2026",
    "realisasi_anggaran_tahun_2026_rp_semester_1": "realisasi_2026",
    "realisasi_anggaran_2026_semester_1": "realisasi_2026",
    "persen_2026": "persen_2026",
    "persentase_capaian_tahun_2026_isemester_1": "persen_2026",
    "persentase_capaian_tahun_2026_semester_1": "persen_2026",
    "persentase_capaian_2026_semester_1": "persen_2026",
    "anggaran_2027": "anggaran_2027", "anggaran_2027_rp": "anggaran_2027",
    # DISABILITAS (matriks monev kegiatan)
    "strategi_implementasi": "strategi",
    "target_capaian": "target_capaian",
    "indikator_capaian": "indikator",
    "output_kegiatan": "output",
    "indikator_capaian_terkait_penyandang_disabilitas": "indikator_disabilitas",
    "indikator_capaian_terkait_penyandang_disabilitas_d": "indikator_disabilitas",
    "hambatan_tantangan": "hambatan",
    "target_kegiatan_2025": "target_2025", "target_kegiatan_tahun_2025": "target_2025",
    "target_kegiatan_2026": "target_2026", "target_kegiatan_tahun_2026": "target_2026",
    "capaian_target_2025": "capaian_2025", "capaian_target_tahun_2025": "capaian_2025",
    "capaian_target_2026": "capaian_2026", "capaian_target_tahun_2026": "capaian_2026",
    "alokasi_anggaran_2025": "anggaran_2025", "alokasi_anggaran_tahun_2025": "anggaran_2025",
    "alokasi_anggaran_2026": "anggaran_2026", "alokasi_anggaran_tahun_2026": "anggaran_2026",
    "realisasi_anggaran_2025": "realisasi_2025", "realisasi_anggaran_tahun_2025": "realisasi_2025",
    "realisasi_anggaran_2026": "realisasi_2026", "realisasi_anggaran_tahun_2026": "realisasi_2026",
    "spesifik_tidak_spesifik": "spesifik",
    "perangkat_daerah_penanggung_jawab": "opd",
    "perangkat_daerah_penanggungjawab": "opd",
    "perangkat_daerah": "opd",
    "keterangan": "keterangan",
}


# ------------------------------------------------------------------ bantuan angka
def _angka(v: Any) -> Optional[float]:
    """Ubah isi sel menjadi angka; None bila sel kosong.

    Menerima format Indonesia (1.250.000,50), format mesin (1250000.5), awalan
    "Rp", dan tanda persen. Nilai akuntansi dalam kurung dianggap negatif.
    """
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in {"-", "—", "–"} or s.lower() in {"nan", "none"}:
        return None
    negatif = s.startswith("(") and s.endswith(")")
    s = re.sub(r"\brp\b", "", s, flags=re.I)
    s = s.strip("()").replace("%", "")
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s or s in {"-", ".", ","}:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1 or re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        f = float(s)
    except ValueError:
        raise ValueError(f"'{v}' bukan angka")
    return -f if negatif else f


def _bulat(v: Any, default: Optional[int] = None) -> Optional[int]:
    f = _angka(v)
    if f is None:
        return default
    if f != int(f):
        raise ValueError(f"'{v}' harus bilangan bulat")
    return int(f)


def _rapikan_angka(f: Optional[float]) -> Optional[Any]:
    if f is None:
        return None
    return int(f) if float(f).is_integer() else round(f, 2)


def _persen(pembilang: Any, penyebut: Any) -> Optional[float]:
    try:
        p, q = float(pembilang), float(penyebut)
    except (TypeError, ValueError):
        return None
    if not q:
        return None
    return round(p / q * 100, 2)


def _jumlah(items: List[Dict[str, Any]], field: str) -> Any:
    nilai = [i.get(field) for i in items if isinstance(i.get(field), (int, float))]
    if not nilai:
        return 0
    total = sum(nilai)
    return int(total) if float(total).is_integer() else round(total, 2)


# ------------------------------------------------------------------ konfigurasi jenis
def _cfg(jenis: str) -> Dict[str, Any]:
    cfg = JENIS.get(jenis)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Jenis matriks '{jenis}' tidak dikenal")
    return cfg


def _teks(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none", "-"}:
        return None
    return s[:2000]


# ------------------------------------------------------------------ pembacaan berkas
def _normal_header(h: Any) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(h or "").strip().lower()).strip("_")
    return _ALIAS.get(key, key)


def _baca_tabel(content: bytes, filename: str, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    import pandas as pd

    name = (filename or "").lower()
    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False,
                         sep=None, engine="python")
    elif name.endswith((".xlsx", ".xls")):
        xl = pd.ExcelFile(io.BytesIO(content))
        sheet = "MATRIKS" if "MATRIKS" in xl.sheet_names else xl.sheet_names[0]
        df = xl.parse(sheet, dtype=str, keep_default_na=False)
    else:
        raise HTTPException(status_code=422, detail="Format berkas harus .xlsx atau .csv")

    df.columns = [_normal_header(c) for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    if "opd" not in df.columns:
        raise HTTPException(status_code=422,
                            detail="Kolom wajib tidak ditemukan: opd. Gunakan template resmi.")
    if not any(c in df.columns for c in cfg["wajib_salah_satu"]):
        raise HTTPException(status_code=422, detail=(
            "Kolom program atau sub_kegiatan tidak ditemukan. Gunakan template resmi."))
    return df.to_dict("records")


def _uraikan_baris(rows: List[Dict[str, Any]], cfg: Dict[str, Any]) -> Tuple[
        List[Dict[str, Any]], List[Dict[str, Any]], int]:
    valid: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    dilewati = 0

    for idx, raw in enumerate(rows, start=2):
        baris = {k: raw.get(k) for k in cfg["columns"]}
        if not any(_teks(v) for v in baris.values()):
            dilewati += 1
            continue
        try:
            for k in cfg["wajib"]:
                if not _teks(baris.get(k)):
                    raise ValueError(f"kolom '{k}' wajib diisi")
            if cfg["wajib_salah_satu"] and not any(_teks(baris.get(k)) for k in cfg["wajib_salah_satu"]):
                raise ValueError("isi program atau sub_kegiatan")
            item: Dict[str, Any] = {k: _teks(baris.get(k)) for k in cfg["teks"]}
            for k in cfg["angka"]:
                nilai = _rapikan_angka(_angka(baris.get(k)))
                if nilai is not None and nilai < 0:
                    raise ValueError(f"{k} tidak boleh negatif")
                item[k] = nilai
            item["no"] = _bulat(baris.get("no"))
        except ValueError as e:
            errors.append({"baris": idx, "pesan": str(e)})
            continue
        valid.append(item)
    return valid, errors, dilewati


# ------------------------------------------------------------------ pembacaan berkas resmi
def baca_oppkpke_resmi(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Baca kertas kerja resmi OPPKPKE (sheet MATRIKS GABUNGAN, header 3 baris)."""
    import pandas as pd

    df = pd.read_excel(path, sheet_name="MATRIKS GABUNGAN", header=None, dtype=object)
    if df.shape[0] < 6:
        raise ValueError("Lembar MATRIKS GABUNGAN tidak memuat baris data")
    body = df.iloc[4:, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 20]].copy()
    body.columns = OPDKPKE_KOLOM
    body = body[body["no"].notna()]
    items, errors, dilewati = _uraikan_baris(body.to_dict("records"), JENIS["oppkpke"])
    meta = {"baris_dibaca": len(body), "valid": len(items), "dilewati": dilewati,
            "errors": errors[:50], "sumber": "MATRIKS GABUNGAN"}
    return items, meta


def baca_ats_resmi(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Baca matriks resmi Program Kegiatan ATS (header baris ke-3)."""
    import pandas as pd

    df = pd.read_excel(path, header=None, dtype=object)
    if df.shape[0] < 5:
        raise ValueError("Berkas tidak memuat baris data")
    body = df.iloc[3:, :15].copy()
    body.columns = ATS_KOLOM
    body = body[pd.to_numeric(body["no"], errors="coerce").notna()]
    items, errors, dilewati = _uraikan_baris(body.to_dict("records"), JENIS["ats-program"])
    meta = {"baris_dibaca": len(body), "valid": len(items), "dilewati": dilewati,
            "errors": errors[:50], "sumber": "Sheet1"}
    return items, meta


def _uang(v: Any) -> Optional[float]:
    """Angka rupiah; keterangan dalam kurung diabaikan (mis. '301.960.904 (135.545.700)')."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s in {"-", "—", "–"}:
        return None
    s = s.split("(")[0]
    try:
        return _angka(s)
    except ValueError:
        digit = re.sub(r"[^\d]", "", s)
        return float(digit) if digit else None


OPD_ATURAN = [
    (("dukcapil", "kependudukan"), "Dukcapil"),
    (("bappeda", "perencanaan pembangunan daerah"), "Bappeda"),
    (("kesbangpol",), "Kesbangpol"),
    (("kesehatan", "dinkes"), "Dinas Kesehatan"),
    (("sosial", "dinsos"), "Dinas Sosial"),
    (("pendidikan", "disdik"), "Dinas Pendidikan"),
    (("ketenagakerjaan", "disnaker"), "Dinas Ketenagakerjaan"),
    (("pekerjaan umum",), "Dinas Pekerjaan Umum"),
    (("penanaman modal", "dpmptsp", "ptsp"), "DPMPTSP"),
    (("koperasi",), "Dinas Koperasi dan UKM"),
    (("perpustakaan",), "Dinas Perpustakaan"),
    (("perumahan",), "Dinas Perumahan"),
    (("pemberdayaan perempuan", "dp3a"), "DP3A"),
    (("pemuda", "olahraga"), "Dinas Pemuda dan Olahraga"),
    (("kebudayaan", "disbud"), "Dinas Kebudayaan"),
    (("komunikasi", "kominfo"), "Dinas Kominfo"),
    (("perhubungan", "dishub"), "Dinas Perhubungan"),
    (("bpbd",), "BPBD"),
    (("pengendalian penduduk",), "Dinas KB"),
    (("inspektorat",), "Inspektorat"),
    (("hukum",), "Bagian Hukum"),
    (("perindustrian", "perdagangan"), "Dinas Perindustrian dan Perdagangan"),
    (("kesejahteraan rakyat", "kesra"), "Bagian Kesejahteraan Rakyat"),
    (("lingkungan hidup", "dlh"), "Dinas Lingkungan Hidup"),
    (("tata ruang",), "Dinas Tata Ruang"),
    (("satpol",), "Satpol PP"),
    (("kecamatan",), "Kecamatan"),
]


def _opd_kanonik(nilai: str, lembar: str) -> str:
    """Satukan variasi nama OPD (mis. 'Dinkes' dan 'Dinas Kesehatan')."""
    def cocok(teks: str) -> Optional[str]:
        k = re.sub(r"[^a-z0-9 ]", " ", (teks or "").lower())
        k = re.sub(r"\s+", " ", k).strip()
        if not k:
            return None
        for kunci, nama in OPD_ATURAN:
            if any(x in k for x in kunci):
                return nama
        return None

    return cocok(nilai) or cocok(lembar) or (nilai or lembar).split(",")[0].strip()


def _gabung_disabilitas(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gabungkan baris dengan nilai keuangan identik (sel gabungan pada berkas sumber)."""
    kunci_fields = ("opd", "program", "kegiatan", "sub_kegiatan", "target_2025",
                    "target_2026", "anggaran_2025", "anggaran_2026",
                    "realisasi_2025", "realisasi_2026")
    teks_fields = ("strategi", "target_capaian", "indikator", "output",
                   "indikator_disabilitas", "hambatan", "satuan", "capaian_2025",
                   "capaian_2026", "lokasi", "spesifik", "keterangan")
    hasil: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    urut: List[Tuple[Any, ...]] = []
    for item in items:
        kunci = tuple(item.get(f) for f in kunci_fields)
        if kunci not in hasil:
            hasil[kunci] = dict(item)
            urut.append(kunci)
            continue
        dasar = hasil[kunci]
        for f in teks_fields:
            baru = item.get(f)
            lama = dasar.get(f)
            if baru and baru != lama:
                gabung = f"{lama}\n{baru}" if lama else str(baru)
                dasar[f] = gabung[:1900]
    keluaran: List[Dict[str, Any]] = []
    for i, kunci in enumerate(urut, start=1):
        dok = hasil[kunci]
        dok["no"] = i
        keluaran.append(dok)
    return keluaran


def baca_disabilitas_monev(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Baca matriks monev kegiatan disabilitas per OPD (24 lembar, header 2 baris)."""
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    items: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    dibaca = dilewati = 0
    sheets = 0
    try:
        for ws in wb.worksheets:
            if ws.title.strip().upper() == "GABUNGAN":
                continue
            rows = list(ws.iter_rows(values_only=True))
            mulai = None
            for i, r in enumerate(rows[:8]):
                if any(str(v or "").strip().lower().startswith("strategi implementasi") for v in r):
                    mulai = i + 2  # lewati baris header dan baris tahun
                    break
            if mulai is None:
                continue
            sheets += 1
            konteks = ""
            for r in rows[mulai:]:
                c = [re.sub(r"\s+", " ", str(v if v is not None else "").strip())
                     for v in (list(r) + [""] * 23)[:23]]
                if not any(c):
                    continue
                inti = any(c[i] for i in (2, 3, 4, 5))
                if not inti and c[0].lower().startswith(("sasaran strategis", "kebijakan")):
                    konteks = c[0]
                    continue
                if not inti:
                    dilewati += 1
                    continue
                dibaca += 1
                try:
                    opd = _opd_kanonik(c[20], ws.title)
                    item = {
                        "strategi": c[0] or konteks or None,
                        "target_capaian": c[1] or None,
                        "program": c[2] or None,
                        "kegiatan": c[3] or None,
                        "sub_kegiatan": c[4] or None,
                        "indikator": c[5] or None,
                        "output": c[6] or None,
                        "indikator_disabilitas": c[7] or None,
                        "hambatan": c[8] or None,
                        "satuan": c[9] or None,
                        "target_2025": c[10] or None,
                        "target_2026": c[11] or None,
                        "capaian_2025": c[12] or None,
                        "capaian_2026": c[13] or None,
                        "anggaran_2025": _rapikan_angka(_uang(c[14])),
                        "anggaran_2026": _rapikan_angka(_uang(c[15])),
                        "realisasi_2025": _rapikan_angka(_uang(c[16])),
                        "realisasi_2026": _rapikan_angka(_uang(c[17])),
                        "lokasi": c[18] or None,
                        "spesifik": c[19] or None,
                        "opd": opd or None,
                        "keterangan": c[21] or None,
                        "no": len(items) + 1,
                    }
                except ValueError as e:
                    errors.append({"baris": len(items) + 1, "pesan": str(e)})
                    continue
                items.append(item)
    finally:
        wb.close()
    digabung = len(items)
    items = _gabung_disabilitas(items)
    meta = {"baris_dibaca": dibaca, "valid": len(items), "dilewati": dilewati,
            "digabung": digabung - len(items), "errors": errors[:50],
            "sumber": f"{sheets} lembar OPD"}
    return items, meta


# ------------------------------------------------------------------ ringkasan
def _ringkasan_oppkpke(items: List[Dict[str, Any]], periode: Dict[str, Any]) -> Dict[str, Any]:
    diperbarui = max((str(i.get("updated_at") or i.get("created_at") or "") for i in items), default="")
    return {
        "jumlah_kegiatan": len(items),
        "jumlah_opd": len({str(i.get("opd") or "").strip().lower() for i in items if i.get("opd")}),
        "jumlah_program": len({str(i.get("program") or "").strip().lower() for i in items
                               if i.get("program")}),
        "total_anggaran": _jumlah(items, "anggaran"),
        "total_realisasi_sem1_2025": _jumlah(items, "realisasi_sem1_2025"),
        "total_realisasi_2025": _jumlah(items, "total_realisasi_2025"),
        "periode": periode,
        "diperbarui": diperbarui or None,
    }


def _ringkasan_ats(items: List[Dict[str, Any]], tahun: int) -> Dict[str, Any]:
    per_tahun = {}
    for th in TAHUN_ATS:
        anggaran = _jumlah(items, f"anggaran_{th}")
        realisasi = _jumlah(items, f"realisasi_{th}") if th != 2027 else 0
        per_tahun[str(th)] = {
            "anggaran": anggaran,
            "realisasi": realisasi if th != 2027 else None,
            "serapan_persen": _persen(realisasi, anggaran) if th != 2027 else None,
        }
    dipilih = per_tahun[str(tahun)]
    diperbarui = max((str(i.get("updated_at") or i.get("created_at") or "") for i in items), default="")
    return {
        "jumlah_program": len(items),
        "jumlah_opd": len({str(i.get("opd") or "").strip().lower() for i in items if i.get("opd")}),
        "tahun": tahun,
        "anggaran": dipilih["anggaran"],
        "realisasi": dipilih["realisasi"],
        "serapan_persen": dipilih["serapan_persen"],
        "per_tahun": per_tahun,
        "diperbarui": diperbarui or None,
    }


def _ringkasan_disabilitas(items: List[Dict[str, Any]], tahun: int) -> Dict[str, Any]:
    a25 = _jumlah(items, "anggaran_2025")
    r25 = _jumlah(items, "realisasi_2025")
    a26 = _jumlah(items, "anggaran_2026")
    r26 = _jumlah(items, "realisasi_2026")
    diperbarui = max((str(i.get("updated_at") or i.get("created_at") or "") for i in items), default="")
    return {
        "jumlah_kegiatan": len(items),
        "jumlah_opd": len({str(i.get("opd") or "").strip().lower() for i in items if i.get("opd")}),
        "jumlah_program": len({str(i.get("program") or "").strip().lower() for i in items
                               if i.get("program")}),
        "tahun": tahun,
        "anggaran_2025": a25,
        "realisasi_2025": r25,
        "serapan_2025": _persen(r25, a25),
        "anggaran_2026": a26,
        "realisasi_2026": r26,
        "serapan_2026": _persen(r26, a26),
        "diperbarui": diperbarui or None,
    }


def _item_keluar(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = _clean(doc)
    if "realisasi_2025" in d or "anggaran_2025" in d:
        d["serapan_2025"] = _persen(d.get("realisasi_2025"), d.get("anggaran_2025"))
        d["serapan_2026"] = _persen(d.get("realisasi_2026"), d.get("anggaran_2026"))
    return d


# ------------------------------------------------------------------ template Excel
def _buat_template(cfg: Dict[str, Any], jenis: str) -> StreamingResponse:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    lebar = {"no": 6, "strategi": 26, "opd": 26, "program": 30, "kegiatan": 30,
             "sub_kegiatan": 34, "aktivitas_langsung": 16, "aktivitas_tidak_langsung": 18,
             "aktivitas_penunjang": 16, "anggaran": 18, "sumber_pembiayaan": 18,
             "sifat_bantuan": 24, "lokasi": 26, "jumlah_sasaran": 24, "besaran_manfaat": 28,
             "jenis_bantuan": 26, "durasi": 20, "realisasi_sem1_2025": 20,
             "total_realisasi_2025": 20, "target_2026": 22, "sasaran": 30,
             "target_2025": 24, "realisasi_2025": 20, "persen_2025": 14,
             "anggaran_2025": 18, "anggaran_2026": 18, "realisasi_2026": 20,
             "persen_2026": 16, "anggaran_2027": 18}

    wb = Workbook()
    ws = wb.active
    ws.title = "MATRIKS"
    isi_kepala = PatternFill("solid", fgColor="232F3E")
    ws.append(cfg["columns"])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="6FE3CF")
        cell.fill = isi_kepala
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, kolom in enumerate(cfg["columns"], start=1):
        ws.column_dimensions[get_column_letter(i)].width = lebar.get(kolom, 18)
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 32

    akhir = 1000
    kolom_letter = {k: get_column_letter(i) for i, k in enumerate(cfg["columns"], start=1)}
    if cfg["angka"]:
        dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                            allow_blank=True, error="Isi dengan angka >= 0",
                            errorTitle="Nilai tidak valid")
        for k in cfg["angka"]:
            dv.add(f"{kolom_letter[k]}2:{kolom_letter[k]}{akhir}")
        ws.add_data_validation(dv)

    pt = wb.create_sheet("PETUNJUK")
    for line in cfg["petunjuk"]:
        pt.append([line])
    pt.column_dimensions["A"].width = 112
    pt["A1"].font = Font(bold=True, size=12)

    ref = wb.create_sheet("REFERENSI")
    ref.append(["Kolom template", "Nama kolom resmi"])
    for cell in ref[1]:
        cell.font = Font(bold=True, color="6FE3CF")
        cell.fill = isi_kepala
    for kolom in cfg["columns"]:
        ref.append([kolom, LABEL.get(kolom, kolom)])
    ref.column_dimensions["A"].width = 30
    ref.column_dimensions["B"].width = 62

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{cfg["nama_berkas"]}"'})


# ------------------------------------------------------------------ simpan (dipakai API & CLI)
async def simpan_matriks(db, jenis: str, items: List[Dict[str, Any]], *, nama_berkas: str = "",
                         sumber_hash: str = "", oleh: str = "", semester: Optional[int] = None,
                         tahun: Optional[int] = None) -> Dict[str, Any]:
    """Ganti isi matriks secara atomik dan kembalikan ringkasan penyimpanan."""
    cfg = _cfg(jenis)
    koleksi = db[cfg["koleksi"]]
    if jenis == "oppkpke":
        semester = 1 if semester is None else semester
        tahun = tahun or datetime.now().year
        if semester not in (1, 2):
            raise HTTPException(status_code=422, detail="Semester harus 1 atau 2")
        if not (2000 <= tahun <= 2100):
            raise HTTPException(status_code=422, detail="Tahun harus antara 2000 dan 2100")
        filt = {"semester": semester, "tahun": tahun}
        for item in items:
            item["semester"] = semester
            item["tahun"] = tahun
    else:
        tahun = tahun or 2026
        filt = {}
        for item in items:
            item["tahun"] = tahun

    dihapus = 0
    if filt:
        res = await koleksi.delete_many(filt)
        dihapus = getattr(res, "deleted_count", 0) or 0
    else:
        semua = await koleksi.find({}).to_list(MAX_BARIS)
        dihapus = len(semua)
        if semua:
            await koleksi.delete_many({})

    stamp = now_iso()
    docs = []
    for item in items:
        docs.append({
            **item,
            "id": str(uuid.uuid4()),
            "sumber_berkas": nama_berkas,
            "sumber_hash": sumber_hash,
            "diimpor_oleh": oleh,
            "diimpor_pada": stamp,
            "created_at": stamp,
            "updated_at": stamp,
        })
    if docs:
        await koleksi.insert_many(docs)

    periode = ({"semester": semester, "tahun": tahun} if jenis == "oppkpke" else {"tahun": tahun})
    return {"jenis": jenis, "label": cfg["label"], "nama_berkas": nama_berkas,
            "diimpor": len(docs), "dihapus": dihapus, "periode": periode}


# ------------------------------------------------------------------ router
def build_router(db, current_user_dep, writer_dep) -> APIRouter:
    router = APIRouter(tags=["matriks"])

    async def _regions() -> List[Dict[str, Any]]:
        rows = [_clean(r) for r in await db.regions.find({}).to_list(100)]
        if not rows:
            rows = [dict(r) for r in seed.REGIONS]
        return rows

    # ---------------------------------------------------------- 1. matriks kategori
    @router.get("/matriks/kategori")
    async def matriks_kategori(user: dict = Depends(current_user_dep)):
        regs = await _regions()
        items = [{
            "kecamatan": r.get("nama") or "",
            "jumlah_kelurahan": r.get("kelurahan"),
            "kemiskinan_ekstrim_kk": r.get("kemiskinan_ekstrim_kk"),
            "kemiskinan_persen": r.get("kemiskinan_persen"),
            "stunting_anak": r.get("stunting_anak"),
            "ats": r.get("ats"),
            "anak_jalanan": r.get("anak_jalanan"),
            "disabilitas": r.get("disabilitas"),
        } for r in regs]
        items.sort(key=lambda x: x["kecamatan"])
        total = {k: _jumlah(items, k) for k in
                 ("jumlah_kelurahan", "kemiskinan_ekstrim_kk", "stunting_anak", "ats",
                  "anak_jalanan", "disabilitas")}
        total["kecamatan"] = "TOTAL"
        total["kemiskinan_persen"] = None
        return {
            "sumber": "Matriks Kemiskinan, Stunting, ATS dan Anak Jalanan - Bappeda Kota Makassar",
            "satuan": {"kemiskinan_ekstrim_kk": "KK", "kemiskinan_persen": "%",
                       "stunting_anak": "anak", "ats": "anak", "anak_jalanan": "anak",
                       "disabilitas": "orang"},
            "jumlah_kecamatan": len(items),
            "items": items,
            "total": total,
        }

    # ---------------------------------------------------------- 2. matriks OPPKPKE
    @router.get("/matriks/oppkpke")
    async def matriks_oppkpke(semester: int = 1, tahun: Optional[int] = None,
                              user: dict = Depends(current_user_dep)):
        if semester not in (1, 2):
            raise HTTPException(status_code=422, detail="Semester harus 1 atau 2")
        tahun = tahun or datetime.now().year
        if not (2000 <= tahun <= 2100):
            raise HTTPException(status_code=422, detail="Tahun harus antara 2000 dan 2100")
        cfg = JENIS["oppkpke"]
        rows = await db[cfg["koleksi"]].find({"semester": semester, "tahun": tahun}) \
            .sort([("no", 1), ("opd", 1)]) \
            .to_list(MAX_BARIS)
        items = [_item_keluar(r) for r in rows]
        periode = {"semester": semester, "tahun": tahun}
        return {
            "jenis": "oppkpke",
            "label": cfg["label"],
            "tersedia": bool(items),
            "periode": periode,
            "kolom": [{"key": k, "label": LABEL.get(k, k)} for k in cfg["columns"]],
            "items": items,
            "ringkasan": _ringkasan_oppkpke(items, periode),
        }

    # ---------------------------------------------------------- 3. matriks program ATS
    @router.get("/matriks/ats-program")
    async def matriks_ats_program(tahun: int = 2026,
                                  user: dict = Depends(current_user_dep)):
        if tahun not in TAHUN_ATS:
            raise HTTPException(status_code=422, detail="Tahun harus 2025, 2026, atau 2027")
        cfg = JENIS["ats-program"]
        rows = await db[cfg["koleksi"]].find({}) \
            .sort([("no", 1), ("opd", 1)]) \
            .to_list(MAX_BARIS)
        items = [_item_keluar(r) for r in rows]
        return {
            "jenis": "ats-program",
            "label": cfg["label"],
            "tersedia": bool(items),
            "periode": {"tahun": tahun},
            "tahun_tersedia": list(TAHUN_ATS),
            "kolom": [{"key": k, "label": LABEL.get(k, k)} for k in cfg["columns"]],
            "items": items,
            "ringkasan": _ringkasan_ats(items, tahun),
        }

    # ---------------------------------------------------------- 4. matriks disabilitas
    @router.get("/matriks/disabilitas")
    async def matriks_disabilitas(tahun: int = 2026,
                                  user: dict = Depends(current_user_dep)):
        if not (2000 <= tahun <= 2100):
            raise HTTPException(status_code=422, detail="Tahun harus antara 2000 dan 2100")
        cfg = JENIS["disabilitas"]
        rows = await db[cfg["koleksi"]].find({}) \
            .sort([("opd", 1), ("no", 1)]) \
            .to_list(MAX_BARIS)
        items = [_item_keluar(r) for r in rows]
        return {
            "jenis": "disabilitas",
            "label": cfg["label"],
            "tersedia": bool(items),
            "tahun": tahun,
            "kolom": [{"key": k, "label": LABEL.get(k, k)} for k in cfg["columns"]],
            "items": items,
            "ringkasan": _ringkasan_disabilitas(items, tahun),
        }

    # ---------------------------------------------------------- unduh template
    @router.get("/matriks/{jenis}/template")
    async def matriks_template(jenis: str, user: dict = Depends(writer_dep)):
        cfg = _cfg(jenis)
        return _buat_template(cfg, jenis)

    # ---------------------------------------------------------- impor
    @router.post("/matriks/{jenis}/import")
    async def matriks_import(jenis: str, request: Request, file: UploadFile = File(...),
                             semester: Optional[int] = Query(None, ge=1, le=2),
                             tahun: Optional[int] = Query(None, ge=2000, le=2100),
                             user: dict = Depends(writer_dep)):
        cfg = _cfg(jenis)
        content = await file.read(MAX_UPLOAD + 1)
        if len(content) > MAX_UPLOAD:
            raise HTTPException(status_code=413, detail="Ukuran berkas maksimal 15 MB")
        if not content:
            raise HTTPException(status_code=422, detail="Berkas kosong")

        try:
            rows = _baca_tabel(content, file.filename or "", cfg)
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=422, detail=f"Berkas tidak dapat dibaca: {e}")

        if len(rows) > MAX_BARIS:
            raise HTTPException(status_code=422,
                                detail=f"Maksimal {MAX_BARIS:,} baris per berkas".replace(",", "."))

        valid, errors, dilewati = _uraikan_baris(rows, cfg)
        if errors:
            raise HTTPException(status_code=422, detail={
                "pesan": (f"{len(errors)} baris bermasalah. Perbaiki berkas lalu unggah ulang; "
                          "belum ada data yang disimpan."),
                "jumlah_error": len(errors),
                "errors": errors[:50],
            })
        if not valid:
            raise HTTPException(status_code=422, detail="Tidak ada baris data yang bisa diimpor")

        nama_berkas = (file.filename or "").strip()
        res = await simpan_matriks(db, jenis, valid, nama_berkas=nama_berkas,
                                   oleh=(user or {}).get("email") or "",
                                   semester=semester, tahun=tahun)
        res["dilewati"] = dilewati
        await audit(db, user, "impor_matriks", cfg["label"], ref=nama_berkas,
                    detail={"diimpor": res["diimpor"], "dihapus": res["dihapus"],
                            "periode": res["periode"]},
                    request=request)
        return res

    return router
