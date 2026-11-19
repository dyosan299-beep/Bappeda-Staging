"""Seed data untuk Sistem Intelijen Data Bappeda Kota Makassar.
Data diambil dari Matriks Kemiskinan, Stunting, ATS, dan Anak Jalanan Kota Makassar.
Nilai per-kecamatan untuk sebagian kategori merupakan distribusi berbasis data agregat kota.
"""

# 15 Kecamatan Kota Makassar dengan koordinat pusat & jumlah kelurahan
REGIONS = [
    {"nama": "Mariso", "lat": -5.1580, "lng": 119.4090, "kelurahan": 9,
     "kemiskinan_ekstrim_kk": 500, "stunting_anak": 120, "anak_jalanan": 6, "ats": 720, "disabilitas": 306, "kemiskinan_persen": 6.2,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Mamajang", "lat": -5.1650, "lng": 119.4230, "kelurahan": 13,
     "kemiskinan_ekstrim_kk": 350, "stunting_anak": 95, "anak_jalanan": 4, "ats": 640, "disabilitas": 127, "kemiskinan_persen": 4.1,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Tamalate", "lat": -5.1900, "lng": 119.4350, "kelurahan": 11,
     "kemiskinan_ekstrim_kk": 2348, "stunting_anak": 260, "anak_jalanan": 11, "ats": 1980, "disabilitas": 422, "kemiskinan_persen": 7.4,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Rappocini", "lat": -5.1680, "lng": 119.4460, "kelurahan": 11,
     "kemiskinan_ekstrim_kk": 800, "stunting_anak": 437, "anak_jalanan": 8, "ats": 1420, "disabilitas": 474, "kemiskinan_persen": 5.0,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Makassar", "lat": -5.1360, "lng": 119.4230, "kelurahan": 14,
     "kemiskinan_ekstrim_kk": 1391, "stunting_anak": 166, "anak_jalanan": 14, "ats": 1180, "disabilitas": 288, "kemiskinan_persen": 6.0,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026",
     "stunting_anak_otoritatif": True, "stunting_anak_sumber": "Data balita stunting 2026 (PDF)"},
    {"nama": "Ujung Pandang", "lat": -5.1400, "lng": 119.4090, "kelurahan": 10,
     "kemiskinan_ekstrim_kk": 216, "stunting_anak": 18, "anak_jalanan": 9, "ats": 420, "disabilitas": 69, "kemiskinan_persen": 2.9,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Wajo", "lat": -5.1200, "lng": 119.4110, "kelurahan": 8,
     "kemiskinan_ekstrim_kk": 22, "stunting_anak": 25, "anak_jalanan": 3, "ats": 360, "disabilitas": 136, "kemiskinan_persen": 3.2,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Bontoala", "lat": -5.1290, "lng": 119.4230, "kelurahan": 12,
     "kemiskinan_ekstrim_kk": 600, "stunting_anak": 217, "anak_jalanan": 7, "ats": 780, "disabilitas": 215, "kemiskinan_persen": 5.5,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Ujung Tanah", "lat": -5.1080, "lng": 119.4180, "kelurahan": 9,
     "kemiskinan_ekstrim_kk": 750, "stunting_anak": 140, "anak_jalanan": 8, "ats": 690, "disabilitas": 120, "kemiskinan_persen": 6.8,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Kepulauan Sangkarrang", "lat": -5.0670, "lng": 119.3330, "kelurahan": 3,
     "kemiskinan_ekstrim_kk": 100, "stunting_anak": 110, "anak_jalanan": 1, "ats": 240, "disabilitas": 431, "kemiskinan_persen": 8.1,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Tallo", "lat": -5.1100, "lng": 119.4450, "kelurahan": 15,
     "kemiskinan_ekstrim_kk": 2907, "stunting_anak": 284, "anak_jalanan": 12, "ats": 2240, "disabilitas": 938, "kemiskinan_persen": 8.6,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026",
     "stunting_anak_otoritatif": True, "stunting_anak_sumber": "Data balita stunting 2026 (PDF)"},
    {"nama": "Panakkukang", "lat": -5.1550, "lng": 119.4550, "kelurahan": 11,
     "kemiskinan_ekstrim_kk": 1000, "stunting_anak": 233, "anak_jalanan": 6, "ats": 1360, "disabilitas": 152, "kemiskinan_persen": 4.6,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Manggala", "lat": -5.1650, "lng": 119.4900, "kelurahan": 8,
     "kemiskinan_ekstrim_kk": 950, "stunting_anak": 288, "anak_jalanan": 5, "ats": 1290, "disabilitas": 146, "kemiskinan_persen": 5.2,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Biringkanaya", "lat": -5.0900, "lng": 119.5100, "kelurahan": 11,
     "kemiskinan_ekstrim_kk": 1100, "stunting_anak": 441, "anak_jalanan": 5, "ats": 1560, "disabilitas": 692, "kemiskinan_persen": 4.8,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
    {"nama": "Tamalanrea", "lat": -5.1200, "lng": 119.4900, "kelurahan": 8,
     "kemiskinan_ekstrim_kk": 300, "stunting_anak": 328, "anak_jalanan": 3, "ats": 396, "disabilitas": 655, "kemiskinan_persen": 3.5,
     "disabilitas_otoritatif": True, "disabilitas_sumber": "DINKES September 2026"},
]

# Tren tingkat kemiskinan kota (2021-2025) + target RPJMD
POVERTY_TREND = [
    {"tahun": 2021, "persen": 4.82, "penduduk_miskin_ribu": 76.90},
    {"tahun": 2022, "persen": 4.58, "penduduk_miskin_ribu": 71.83},
    {"tahun": 2023, "persen": 5.07, "penduduk_miskin_ribu": 80.32},
    {"tahun": 2024, "persen": 4.97, "penduduk_miskin_ribu": 79.53},
    {"tahun": 2025, "persen": 4.43, "penduduk_miskin_ribu": 71.53},
]
POVERTY_TARGET = [
    {"tahun": 2025, "target_persen": 4.43, "label": "Baseline 2025"},
    {"tahun": 2026, "target_persen": 3.78, "label": "Target 2026"},
    {"tahun": 2027, "target_persen": 3.40, "label": "Target 2027"},
    {"tahun": 2028, "target_persen": 3.28, "label": "Target 2028"},
    {"tahun": 2029, "target_persen": 3.15, "label": "Target 2029"},
]

# Tren stunting kota (2022-2025)
STUNTING_TREND = [
    {"tahun": 2022, "eppgbm_persen": 4.80, "ssgi_persen": 18.4, "keluarga_berisiko": 249956, "jumlah_balita": 148074, "diintervensi": 148074},
    {"tahun": 2023, "eppgbm_persen": 3.73, "ssgi_persen": 25.6, "keluarga_berisiko": 28098, "jumlah_balita": 81952, "diintervensi": 81952},
    {"tahun": 2024, "eppgbm_persen": 3.10, "ssgi_persen": 22.9, "keluarga_berisiko": 37460, "jumlah_balita": 86653, "diintervensi": 86653},
    {"tahun": 2025, "eppgbm_persen": 2.29, "ssgi_persen": 22.9, "keluarga_berisiko": 34000, "jumlah_balita": 84000, "diintervensi": 82000},
]

# Disabilitas Kota Makassar 2025 (total 5.171 orang)
DISABILITY = {
    "total_per_tahun": [
        {"tahun": 2022, "jumlah": 2082},
        {"tahun": 2024, "jumlah": 1171},
        {"tahun": 2025, "jumlah": 5171},
    ],
    "jenis_kelamin": [
        {"kategori": "Laki-laki", "jumlah": 2612},
        {"kategori": "Perempuan", "jumlah": 2558},
    ],
    "pendidikan": [
        {"kategori": "Perguruan Tinggi (S2-S3)", "jumlah": 14},
        {"kategori": "Perguruan Tinggi (D1-S1)", "jumlah": 127},
        {"kategori": "SMA/SMK/MA", "jumlah": 846},
        {"kategori": "SMP/MTs", "jumlah": 561},
        {"kategori": "SD/MI", "jumlah": 1763},
        {"kategori": "Tidak Sekolah", "jumlah": 1860},
    ],
    "ragam": [
        {"kategori": "Disabilitas Fisik", "jumlah": 2179},
        {"kategori": "Disabilitas Ganda", "jumlah": 634},
        {"kategori": "Disabilitas Intelektual", "jumlah": 326},
        {"kategori": "Disabilitas Mental", "jumlah": 527},
        {"kategori": "Sensorik Pendengaran (Disabilitas Tuli)", "jumlah": 780},
        {"kategori": "Sensorik Penglihatan (Disabilitas Buta)", "jumlah": 725},
    ],
    "nik": [
        {"kategori": "KTP Makassar", "jumlah": 4509},
        {"kategori": "KTP Luar Makassar", "jumlah": 257},
        {"kategori": "Tidak Memiliki KTP", "jumlah": 405},
    ],
    "pekerjaan_ringkas": [
        {"kategori": "Bekerja", "jumlah": 653},
        {"kategori": "Tidak Bekerja", "jumlah": 4518},
    ],
}

# Anak Tidak Sekolah (ATS)
ATS = {
    "per_tahun": [
        {"tahun": 2022, "ats_sd": 1798, "ats_smp": 751, "kembali_sekolah": 78},
        {"tahun": 2023, "ats_sd": 1812, "ats_smp": 1654, "kembali_sekolah": 0},
    ],
    "ringkasan": {"total_bpb": 24979, "total_do": 4121, "total_ltm": 5025, "ats_laki": 18996, "ats_total": 15276},
}

# PMKS (Penyandang Masalah Kesejahteraan Sosial) termasuk Anak Jalanan
PMKS = [
    {"indikator": "Anak Jalanan", "y2022": 501, "y2023": 349, "y2024": 99, "y2025": 102},
    {"indikator": "Gelandangan", "y2022": 194, "y2023": 88, "y2024": 51, "y2025": 88},
    {"indikator": "ODGJ", "y2022": 126, "y2023": None, "y2024": 0, "y2025": None},
    {"indikator": "Lansia Terlantar", "y2022": 39, "y2023": None, "y2024": 71, "y2025": None},
    {"indikator": "GEPENG (Gelandangan & Pengemis)", "y2022": 194, "y2023": None, "y2024": 80, "y2025": None},
]

CATEGORY_META = {
    "kemiskinan": {"label": "Kemiskinan", "field": "kemiskinan_ekstrim_kk", "unit": "KK", "warna": "#DC2626"},
    "stunting": {"label": "Stunting", "field": "stunting_anak", "unit": "anak", "warna": "#D97706"},
    "anak_jalanan": {"label": "Anak Jalanan / PMKS", "field": "anak_jalanan", "unit": "jiwa", "warna": "#4338CA"},
    "ats": {"label": "Anak Tidak Sekolah", "field": "ats", "unit": "anak", "warna": "#C026D3"},
    "disabilitas": {"label": "Disabilitas", "field": "disabilitas", "unit": "orang", "warna": "#047857"},
}

# Data numerik per kelurahan
CATEGORY_FIELDS = ["kemiskinan_ekstrim_kk", "stunting_anak", "anak_jalanan", "ats", "disabilitas"]

# Daftar kelurahan resmi per kecamatan Kota Makassar
KELURAHAN_NAMES = {
    "Mariso": ["Bontorannu", "Kampung Buyang", "Kunjung Mae", "Lette", "Mario", "Mariso", "Mattoangin", "Panambungan", "Tamarunang"],
    "Mamajang": ["Baji Mappakasunggu", "Bonto Biraeng", "Bonto Lebang", "Karang Anyar", "Labuang Baji", "Mamajang Dalam", "Mamajang Luar", "Mandala", "Maricaya Selatan", "Pa'batang", "Parang", "Sambung Jawa", "Tamparang Keke"],
    "Tamalate": ["Balang Baru", "Barombong", "Bongaya", "Bonto Duri", "Jongaya", "Maccini Sombala", "Mangasa", "Mannuruki", "Pa'baeng-baeng", "Parang Tambung", "Tanjung Merdeka"],
    "Rappocini": ["Ballaparang", "Banta-Bantaeng", "Bonto Makkio", "Buakana", "Gunung Sari", "Karunrung", "Kassi-Kassi", "Mappala", "Minasa Upa", "Rappocini", "Tidung"],
    "Makassar": ["Bara-Baraya", "Bara-Baraya Selatan", "Bara-Baraya Timur", "Bara-Baraya Utara", "Barana", "Lariang Bangi", "Maccini", "Maccini Gusung", "Maccini Parang", "Maradekaya", "Maradekaya Selatan", "Maradekaya Utara", "Maricaya", "Maricaya Baru"],
    "Ujung Pandang": ["Baru", "Bulogading", "Lae-Lae", "Lajangiru", "Losari", "Maloku", "Mangkura", "Pisang Selatan", "Pisang Utara", "Sawerigading"],
    "Wajo": ["Butung", "Ende", "Malimongan", "Malimongan Tua", "Mampu", "Melayu", "Melayu Baru", "Pattunuang"],
    "Bontoala": ["Baraya", "Bontoala", "Bontoala Parang", "Bontoala Tua", "Bunga Ejaya", "Gaddong", "Layang", "Malimongan Baru", "Parang Layang", "Timungan Lompoa", "Tompo Balang", "Wajo Baru"],
    "Ujung Tanah": ["Camba Berua", "Cambaya", "Gusung", "Pattingalloang", "Pattingalloang Baru", "Tabaringan", "Tamalabba", "Totaka", "Ujung Tanah"],
    "Kepulauan Sangkarrang": ["Barrang Caddi", "Barrang Lompo", "Kodingareng"],
    "Tallo": ["Buloa", "Bunga Eja Beru", "Kalukuang", "Kaluku Bodoa", "Lakkang", "La'latang", "Lembo", "Pannampu", "Rappojawa", "Rappokalling", "Suangga", "Tallo", "Tammua", "Ujung Pandang Baru", "Wala-Walaya"],
    "Panakkukang": ["Karampuang", "Karuwisi", "Karuwisi Utara", "Masale", "Pampang", "Panaikang", "Pandang", "Paropo", "Sinrijala", "Tamamaung", "Tello Baru"],
    "Manggala": ["Antang", "Bangkala", "Batua", "Biring Romang", "Bitowa", "Borong", "Manggala", "Tamangapa"],
    "Biringkanaya": ["Bakung", "Berua", "Bulurokeng", "Daya", "Katimbang", "Laikang", "Pai", "Paccerakkang", "Sudiang", "Sudiang Raya", "Untia"],
    "Tamalanrea": ["Bira", "Buntusu", "Kapasa", "Kapasa Raya", "Parangloe", "Tamalanrea", "Tamalanrea Indah", "Tamalanrea Jaya"],
}

# Nilai resmi per kelurahan (DINKES September 2026 dan PDF balita 2026).
# Hanya kelurahan dengan rincian resmi; sisanya memakai distribusi agregat.
KELURAHAN_OVERRIDES = {
    ("Makassar", "Bara-Baraya"): {"disabilitas": 76, "stunting_anak": 3},
    ("Makassar", "Bara-Baraya Selatan"): {"disabilitas": 0, "stunting_anak": 2},
    ("Makassar", "Bara-Baraya Timur"): {"disabilitas": 0, "stunting_anak": 9},
    ("Makassar", "Bara-Baraya Utara"): {"disabilitas": 0, "stunting_anak": 23},
    ("Makassar", "Barana"): {"disabilitas": 48, "stunting_anak": 7},
    ("Makassar", "Lariang Bangi"): {"disabilitas": 20, "stunting_anak": 0},
    ("Makassar", "Maccini"): {"disabilitas": 11, "stunting_anak": 13},
    ("Makassar", "Maccini Gusung"): {"disabilitas": 16, "stunting_anak": 27},
    ("Makassar", "Maccini Parang"): {"disabilitas": 1, "stunting_anak": 17},
    ("Makassar", "Maradekaya"): {"disabilitas": 56, "stunting_anak": 9},
    ("Makassar", "Maradekaya Selatan"): {"disabilitas": 0, "stunting_anak": 1},
    ("Makassar", "Maradekaya Utara"): {"disabilitas": 0, "stunting_anak": 1},
    ("Makassar", "Maricaya"): {"disabilitas": 6, "stunting_anak": 11},
    ("Makassar", "Maricaya Baru"): {"disabilitas": 54, "stunting_anak": 43},
    ("Tallo", "Buloa"): {"disabilitas": 25, "stunting_anak": 3},
    ("Tallo", "Bunga Eja Beru"): {"disabilitas": 36, "stunting_anak": 31},
    ("Tallo", "Kaluku Bodoa"): {"disabilitas": 292, "stunting_anak": 110},
    ("Tallo", "Kalukuang"): {"disabilitas": 22, "stunting_anak": 1},
    ("Tallo", "La'latang"): {"disabilitas": 12, "stunting_anak": 2},
    ("Tallo", "Lakkang"): {"disabilitas": 36, "stunting_anak": 1},
    ("Tallo", "Lembo"): {"disabilitas": 31, "stunting_anak": 52},
    ("Tallo", "Pannampu"): {"disabilitas": 181, "stunting_anak": 64},
    ("Tallo", "Rappojawa"): {"disabilitas": 20, "stunting_anak": 7},
    ("Tallo", "Rappokalling"): {"disabilitas": 117, "stunting_anak": 3},
    ("Tallo", "Suangga"): {"disabilitas": 21, "stunting_anak": 0},
    ("Tallo", "Tallo"): {"disabilitas": 78, "stunting_anak": 1},
    ("Tallo", "Tammua"): {"disabilitas": 26, "stunting_anak": 2},
    ("Tallo", "Ujung Pandang Baru"): {"disabilitas": 24, "stunting_anak": 0},
    ("Tallo", "Wala-Walaya"): {"disabilitas": 17, "stunting_anak": 6},
}


def _distribute(total, n, seed_val):
    """Bagi bilangan bulat `total` ke `n` bagian dengan bobot deterministik."""
    if n <= 0:
        return []
    weights = [((i * 7 + seed_val * 3) % 5) + 3 for i in range(n)]  # 3..7
    s = sum(weights)
    parts = [total * w // s for w in weights]
    rem = total - sum(parts)
    i = 0
    while rem > 0:
        parts[i % n] += 1
        rem -= 1
        i += 1
    return parts


def build_kelurahan_docs():
    """Bangun dokumen kelurahan dengan nilai terdistribusi dari agregat kecamatan."""
    docs = []
    for ridx, region in enumerate(REGIONS):
        names = KELURAHAN_NAMES.get(region["nama"], [])
        n = len(names)
        dist = {f: _distribute(int(region.get(f, 0)), n, ridx + fi + 1)
                for fi, f in enumerate(CATEGORY_FIELDS)}
        base_persen = region.get("kemiskinan_persen", 0)
        for i, name in enumerate(names):
            delta = (((i * 13 + ridx * 7) % 15) - 7) / 10.0  # -0.7..+0.7
            persen = round(max(0.1, base_persen + delta), 2)
            doc = {"nama": name, "kecamatan": region["nama"], "kemiskinan_persen": persen}
            for f in CATEGORY_FIELDS:
                doc[f] = dist[f][i]
            doc.update(KELURAHAN_OVERRIDES.get((region["nama"], name), {}))
            docs.append(doc)
    return docs
