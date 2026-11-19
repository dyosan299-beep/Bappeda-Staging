"""Skoring kerentanan sosial rumah tangga (DTSEN) — dapat dikonfigurasi Admin.

Prinsip:
- Kode kategori DTSEN dipetakan ke tingkat kondisi: baik / sedang / rentan.
- Kode yang belum jelas TIDAK dianggap rentan, melainkan ditandai
  `perlu_validasi` agar data mentah tetap dipertahankan (sesuai permintaan).
- Bobot & ambang batas disimpan di koleksi `scoring_config` (dokumen id="default")
  sehingga bisa diubah Admin tanpa mengubah kode.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------- default config
# level: 0 = baik, 1 = sedang, 2 = rentan
DEFAULT_CODE_MAPS: Dict[str, Dict[str, List[int]]] = {
    # lantai: 1 marmer/granit, 2 keramik, 3 parket/vinil, 4 ubin/tegel/teraso,
    # 5 kayu kualitas tinggi, 6 semen/bata merah, 7 bambu, 8 kayu kualitas rendah, 9 tanah
    "jenis_lantai_terluas": {"baik": [1, 2, 3], "sedang": [4, 5, 6], "rentan": [7, 8, 9]},
    # dinding: 1 tembok, 2 plesteran anyaman, 3 kayu/papan, 4 anyaman bambu,
    # 5 batang kayu, 6 bambu
    "jenis_dinding_terluas": {"baik": [1], "sedang": [2, 3], "rentan": [4, 5, 6]},
    # atap: 1 beton, 2 genteng, 3 seng, 4 asbes, 5 bambu, 6 kayu/sirap, 7 jerami/ijuk/daun
    "jenis_atap_terluas": {"baik": [1, 2], "sedang": [3, 4], "rentan": [5, 6, 7]},
    # air minum: 1 air kemasan, 2 isi ulang, 3 ledeng/PDAM, 4 sumur bor/pompa,
    # 5 sumur terlindung, 6 sumur tak terlindung, 7 mata air terlindung,
    # 8 mata air tak terlindung, 9 air permukaan/sungai, 10 air hujan
    "sumber_air_minum_utama": {"baik": [1, 2, 3], "sedang": [4, 5, 7], "rentan": [6, 8, 9, 10]},
    # penerangan: 1 listrik PLN dengan meter, 2 PLN tanpa meter, 3 non-PLN, 4 bukan listrik
    "sumber_penerangan_utama": {"baik": [1], "sedang": [2, 3], "rentan": [4]},
    # fasilitas BAB: 1 sendiri, 2 bersama, 3 umum, 4 MCK komunal, 5 lainnya, 6 tidak ada
    "fasilitas_bab": {"baik": [1], "sedang": [2, 4], "rentan": [3, 5, 6]},
    # kloset: 1 leher angsa, 2 plengsengan, 3 cemplung/cubluk, 4 tidak pakai kloset
    "jenis_kloset": {"baik": [1], "sedang": [2], "rentan": [3, 4]},
    # tinja: 1 tangki septik, 2 IPAL, 3 kolam/sawah/sungai, 4 lubang tanah,
    # 5 pantai/tanah lapang, 6 lainnya
    "pembuangan_akhir_tinja": {"baik": [1, 2], "sedang": [4], "rentan": [3, 5, 6]},
    # kepemilikan rumah: 1 milik sendiri, 2 kontrak/sewa, 3 bebas sewa,
    # 4 dinas, 5 lainnya
    "status_kepemilikan_rumah": {"baik": [1], "sedang": [2, 3, 4], "rentan": [5]},
}

DEFAULT_WEIGHTS: Dict[str, float] = {
    "desil": 30.0,                     # desil 1 = bobot penuh
    "pbi": 5.0,                        # penerima PBI (indikasi miskin terdata)
    "luas_lantai_per_kapita": 10.0,    # < 7,2 m2/jiwa = rentan (SPM rumah layak)
    "jenis_lantai_terluas": 10.0,
    "jenis_dinding_terluas": 10.0,
    "jenis_atap_terluas": 8.0,
    "sumber_air_minum_utama": 10.0,
    "fasilitas_bab": 6.0,
    "jenis_kloset": 5.0,
    "pembuangan_akhir_tinja": 6.0,
    "sumber_penerangan_utama": 5.0,
    "status_kepemilikan_rumah": 5.0,
    "aset": -5.0,                      # punya aset lain -> mengurangi skor
}

DEFAULT_THRESHOLDS: Dict[str, float] = {
    "sangat_tinggi": 65.0,
    "tinggi": 50.0,
    "sedang": 35.0,
}

LEVEL_LABELS = {
    "sangat_tinggi": "Prioritas Sangat Tinggi",
    "tinggi": "Prioritas Tinggi",
    "sedang": "Prioritas Sedang",
    "rendah": "Prioritas Rendah",
}

FIELD_LABEL = {
    "jenis_lantai_terluas": "Lantai",
    "jenis_dinding_terluas": "Dinding",
    "jenis_atap_terluas": "Atap",
    "sumber_air_minum_utama": "Air minum",
    "sumber_penerangan_utama": "Penerangan",
    "fasilitas_bab": "Fasilitas BAB",
    "jenis_kloset": "Kloset",
    "pembuangan_akhir_tinja": "Pembuangan tinja",
    "status_kepemilikan_rumah": "Kepemilikan rumah",
}

# kelompok indikator untuk KPI dashboard
SANITASI_FIELDS = ["fasilitas_bab", "jenis_kloset", "pembuangan_akhir_tinja"]
HUNIAN_FIELDS = ["jenis_lantai_terluas", "jenis_dinding_terluas", "jenis_atap_terluas"]

LUAS_PER_KAPITA_MIN = 7.2


def default_config() -> Dict[str, Any]:
    return {
        "id": "default",
        "weights": dict(DEFAULT_WEIGHTS),
        "thresholds": dict(DEFAULT_THRESHOLDS),
        "code_maps": {k: {lvl: list(v) for lvl, v in m.items()}
                      for k, m in DEFAULT_CODE_MAPS.items()},
        "luas_per_kapita_min": LUAS_PER_KAPITA_MIN,
        "catatan": ("Pemetaan kode mengikuti kodifikasi umum DTSEN/Regsosek. "
                    "Kode di luar daftar ditandai 'perlu validasi' dan tidak "
                    "dihitung sebagai rentan."),
    }


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def code_level(field: str, value: Any, code_maps: Dict[str, Dict[str, List[int]]]) -> str:
    """Kembalikan 'baik' | 'sedang' | 'rentan' | 'perlu_validasi'."""
    code = _to_int(value)
    if code is None:
        return "perlu_validasi"
    mapping = code_maps.get(field) or {}
    for level in ("baik", "sedang", "rentan"):
        if code in (mapping.get(level) or []):
            return level
    return "perlu_validasi"


def score_household(doc: Dict[str, Any], config: Optional[Dict[str, Any]] = None
                    ) -> Tuple[float, str, List[str], Dict[str, str], bool]:
    """Hitung skor risiko rumah tangga.

    Return: (skor 0-100, level, daftar faktor, level per indikator, perlu_validasi)
    """
    cfg = config or default_config()
    weights: Dict[str, float] = {**DEFAULT_WEIGHTS, **(cfg.get("weights") or {})}
    thresholds: Dict[str, float] = {**DEFAULT_THRESHOLDS, **(cfg.get("thresholds") or {})}
    code_maps = {**DEFAULT_CODE_MAPS, **(cfg.get("code_maps") or {})}
    luas_min = float(cfg.get("luas_per_kapita_min") or LUAS_PER_KAPITA_MIN)

    score = 0.0
    factors: List[str] = []
    levels: Dict[str, str] = {}
    perlu_validasi = False

    # 1. Desil nasional (1 paling miskin)
    desil = _to_int(doc.get("desil_nasional"))
    if desil is not None and desil > 0:
        w = weights.get("desil", 30.0)
        frac = max(0.0, min(1.0, (6 - desil) / 5.0)) if desil <= 5 else 0.0
        score += w * frac
        if desil <= 2:
            factors.append(f"Desil nasional {desil} (kelompok termiskin)")
        elif desil <= 3:
            factors.append(f"Desil nasional {desil}")
    else:
        perlu_validasi = True

    # 2. PBI (penerima bantuan iuran JKN)
    pbi_nas = _to_int(doc.get("pbi_nas")) or 0
    pbi_pemda = _to_int(doc.get("pbi_pemda")) or 0
    if pbi_nas == 1 or pbi_pemda == 1:
        score += weights.get("pbi", 5.0)
        factors.append("Terdaftar PBI JKN" + (" (Nasional)" if pbi_nas == 1 else " (Pemda)"))

    # 3. Luas lantai per kapita
    luas = doc.get("luas_lantai")
    jml = _to_int(doc.get("jumlah_anggota_keluarga")) or 0
    try:
        luas_f = float(luas) if luas not in (None, "") else None
    except (TypeError, ValueError):
        luas_f = None
    if luas_f and jml > 0:
        per_kapita = luas_f / jml
        w = weights.get("luas_lantai_per_kapita", 10.0)
        if per_kapita < luas_min:
            score += w
            factors.append(f"Luas hunian {per_kapita:.1f} m²/jiwa (< {luas_min} m²/jiwa)")
        elif per_kapita < luas_min * 1.5:
            score += w * 0.5
    else:
        perlu_validasi = True

    # 4. Indikator kondisi hunian, air, sanitasi, listrik, kepemilikan
    for field in list(FIELD_LABEL.keys()):
        lvl = code_level(field, doc.get(field), code_maps)
        levels[field] = lvl
        w = weights.get(field, 0.0)
        if lvl == "rentan":
            score += w
            factors.append(f"{FIELD_LABEL[field]} kategori rentan (kode {doc.get(field)})")
        elif lvl == "sedang":
            score += w * 0.4
        elif lvl == "perlu_validasi":
            perlu_validasi = True

    # 5. Aset lain (kode 1 = memiliki) mengurangi skor
    aset_lahan = _to_int(doc.get("aset_tidak_bergerak_lahan_lainnya"))
    aset_rumah = _to_int(doc.get("aset_tidak_bergerak_rumah_lainnya"))
    if aset_lahan == 1 or aset_rumah == 1:
        score += weights.get("aset", -5.0)
        factors.append("Memiliki aset tidak bergerak lainnya")

    score = max(0.0, min(100.0, score))
    if score >= thresholds.get("sangat_tinggi", 65):
        level = "sangat_tinggi"
    elif score >= thresholds.get("tinggi", 50):
        level = "tinggi"
    elif score >= thresholds.get("sedang", 35):
        level = "sedang"
    else:
        level = "rendah"

    return round(score, 2), level, factors, levels, perlu_validasi


def summarize_levels(levels: Dict[str, str]) -> Dict[str, bool]:
    """Ringkasan indikator rentan untuk KPI dashboard."""
    sanitasi_rentan = any(levels.get(f) == "rentan" for f in SANITASI_FIELDS)
    hunian_rentan = any(levels.get(f) == "rentan" for f in HUNIAN_FIELDS)
    air_rentan = levels.get("sumber_air_minum_utama") == "rentan"
    listrik_rentan = levels.get("sumber_penerangan_utama") == "rentan"
    return {
        "sanitasi_rentan": sanitasi_rentan,
        "hunian_rentan": hunian_rentan,
        "air_rentan": air_rentan,
        "listrik_rentan": listrik_rentan,
        "rumah_rentan": hunian_rentan or sanitasi_rentan or air_rentan,
    }


def mask_kk(no_kk: Any) -> str:
    s = str(no_kk or "").strip()
    if len(s) < 8:
        return "*" * len(s)
    return s[:4] + "*" * (len(s) - 8) + s[-4:]
