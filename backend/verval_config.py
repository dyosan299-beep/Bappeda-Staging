"""Konfigurasi modul GeoTag-Verval DTSEN.

Struktur formulir mengacu "Instrumen Verifikasi & Validasi Lapangan DTSEN"
Pemerintah Kota Makassar, terdiri atas 4 bagian:
  I.   Identitas Wilayah & Geospasial — otomatis dari DTSEN & GPS.
  II.  Data Keluarga & Status Sosial Ekonomi — 11 variabel (lihat INDIKATOR).
  III. Penapisan Individu Rentan — entri manual oleh operator.
  IV.  Kesimpulan Hasil Verval — pilih salah satu (6 opsi).

Operator RT/RW WAJIB menyelesaikan Bagian II, III, IV (form komprehensif)
sebelum dapat mengunggah foto dan merekam GPS, lalu mengirim hasil.
"""
from __future__ import annotations

import os

ROLE_OPERATOR = "operator_rt_rw"
# Pelaksana GeoTag-Verval di lapangan: Petugas RT/RW & Operator RT/RW.
OPERATOR_ROLES = (ROLE_OPERATOR, "petugas")
# Pemeriksa berjenjang 2 tahap: Kelurahan (tahap 1) -> Kecamatan (persetujuan akhir) + Admin/Bappeda.
KELURAHAN_REVIEWER_ROLES = ("operator_kelurahan",)
KECAMATAN_REVIEWER_ROLES = ("operator", "operator_kecamatan", "verifikator")
ADMIN_REVIEWER_ROLES = ("admin_bappeda", "superadmin", "admin")
REVIEWER_ROLES = KELURAHAN_REVIEWER_ROLES + KECAMATAN_REVIEWER_ROLES + ADMIN_REVIEWER_ROLES
# Hanya melihat hasil Verval (titik, foto, detail) tanpa memutuskan: pimpinan.
VIEWER_ROLES = ("pimpinan",)
HASIL_ROLES = REVIEWER_ROLES + VIEWER_ROLES
PENUGASAN_ADMIN_ROLES = ("superadmin", "admin", "admin_bappeda", "operator", "operator_kecamatan")
PETA_AGREGAT_ROLES = ("admin_opd", "viewer")

IZIN = {
    "ambil_foto_dan_kirim": list(OPERATOR_ROLES),
    "daftar_warga_baru": list(OPERATOR_ROLES),
    "lihat_foto": ["pemilik / Ketua RW wilayahnya", "Kelurahan wilayahnya", "Kecamatan wilayahnya", "Admin Bappeda / Superadmin / Pimpinan"],
    "lihat_koordinat_presisi": ["pemilik / Ketua RW wilayahnya", "Kelurahan wilayahnya", "Kecamatan wilayahnya", "Admin Bappeda / Superadmin / Pimpinan"],
    "lihat_identitas_rumah_tangga": [
        "petugas/RW (wilayahnya, detail lengkap untuk pencocokan NIK)",
        "Kelurahan (kelurahannya, detail lengkap)",
        "Kecamatan (kecamatannya, detail lengkap)",
        "Admin Bappeda / Superadmin (seluruh kota, detail lengkap)",
    ],
    "periksa_tahap_1_kelurahan": list(KELURAHAN_REVIEWER_ROLES),
    "setujui_akhir_verval": list(KECAMATAN_REVIEWER_ROLES + ADMIN_REVIEWER_ROLES),
    "kelola_penugasan": list(PENUGASAN_ADMIN_ROLES),
    "lihat_rekap_peta": list(PETA_AGREGAT_ROLES),
}

INDIKATOR_SUMBER = ("Formulir mengikuti Instrumen Verifikasi & Validasi Lapangan DTSEN "
                    "Pemerintah Kota Makassar — 11 variabel keluarga, penapisan individu rentan, "
                    "dan kesimpulan verifikasi.")

# ---------------------------------------------------------------- Bagian II
# 11 variabel. Tiap variabel punya:
#   - key          : identifier internal
#   - label        : nama variabel di form
#   - dtsen_fields : field pada koleksi households yang menjadi acuan DTSEN
#   - kesesuaian   : opsi perbandingan terhadap data DTSEN pre-printed
#   - kondisi_riil : opsi kondisi riil lapangan
#   - opd          : OPD target rekomendasi (informasi untuk reviewer)
INDIKATOR = [
    {"key": "no_kk", "label": "Nomor Kartu Keluarga (KK)",
     "dtsen_fields": ["no_kk"], "kesesuaian": ["sesuai", "beda"],
     "kondisi_riil": ["sesuai", "beda"], "opd": "Dukcapil"},
    {"key": "nama_krt", "label": "Nama Kepala Keluarga (KRT)",
     "dtsen_fields": ["kepala_keluarga", "nama_kepala_keluarga"],
     "kesesuaian": ["sesuai", "beda"], "kondisi_riil": ["sesuai", "beda"],
     "opd": "Dukcapil"},
    {"key": "jumlah_anggota", "label": "Jumlah Anggota Keluarga",
     "dtsen_fields": ["jumlah_anggota_keluarga"],
     "kesesuaian": ["sesuai", "beda"], "kondisi_riil": ["sesuai", "beda"],
     "opd": "Dinsos"},
    {"key": "status_desil", "label": "Status Desil Nasional",
     "dtsen_fields": ["desil", "desil_nasional"],
     "kesesuaian": ["tetap", "graduasi"], "kondisi_riil": ["tetap", "graduasi"],
     "opd": "Bappeda"},
    {"key": "pbi_jkn", "label": "Kepesertaan PBI JKN / BPJS",
     "dtsen_fields": ["pbi_nas", "pbi_pemda", "kepesertaan_jkn"],
     "kesesuaian": ["aktif", "non_aktif"], "kondisi_riil": ["aktif", "non_aktif"],
     "opd": "Dinkes"},
    {"key": "pln", "label": "ID Pelanggan PLN & Daya Listrik",
     "dtsen_fields": ["id_pelanggan_pln", "daya_terpasang"],
     "kesesuaian": ["sesuai", "beda"], "kondisi_riil": ["sesuai", "beda"],
     "opd": "Kemensos"},
    {"key": "kepemilikan_rumah", "label": "Status Kepemilikan Rumah",
     "dtsen_fields": ["status_kepemilikan_bangunan", "status_kepemilikan"],
     "kesesuaian": ["sesuai", "beda"], "kondisi_riil": ["sesuai", "beda"],
     "opd": "Disperkim"},
    {"key": "fisik_rumah", "label": "Kondisi Fisik Atap, Dinding, Lantai",
     "dtsen_fields": ["jenis_atap_terluas", "jenis_dinding_terluas", "jenis_lantai_terluas"],
     "kesesuaian": ["rlh", "rtlh"], "kondisi_riil": ["layak", "tidak_layak"],
     "opd": "Disperkim (RTLH)"},
    {"key": "air_minum", "label": "Sumber Air Minum Utama",
     "dtsen_fields": ["sumber_air_minum_utama"],
     "kesesuaian": ["layak", "tidak_layak"], "kondisi_riil": ["layak", "tidak_layak"],
     "opd": "Dinkes / PU"},
    {"key": "sanitasi", "label": "Fasilitas BAB & Tangki Septik",
     "dtsen_fields": ["fasilitas_bab", "pembuangan_akhir_tinja"],
     "kesesuaian": ["babs", "odf"], "kondisi_riil": ["babs", "odf"],
     "opd": "Dinkes / PU"},
    {"key": "aset_pekerjaan", "label": "Aset Usaha / Pekerjaan KRT",
     "dtsen_fields": ["pekerjaan_krt", "pekerjaan_kepala_keluarga"],
     "kesesuaian": ["butuh_pelatihan", "cukup"], "kondisi_riil": ["pelatihan", "modal", "cukup"],
     "opd": "Disnaker / Diskop"},
]

# Opsi non-default (yang mengindikasikan perbedaan / masalah) → catatan wajib
INDIKATOR_PERLU_CATATAN = {
    "beda", "graduasi", "non_aktif", "rtlh", "tidak_layak", "babs", "butuh_pelatihan",
    "pelatihan", "modal",
}

# ---------------------------------------------------------------- Bagian III
STATUS_HUBUNGAN = (
    {"key": "kepala_keluarga", "label": "Kepala Keluarga"},
    {"key": "istri", "label": "Istri / Pasangan"},
    {"key": "anak_usia_sekolah", "label": "Anak Usia Sekolah"},
    {"key": "balita_ibu_hamil", "label": "Balita / Ibu Hamil"},
    {"key": "lansia_disabilitas", "label": "Lansia / Disabilitas"},
    {"key": "lainnya", "label": "Lainnya"},
)

# Opsi kondisi rentan yang relevan per status hubungan (multiselect).
KONDISI_RENTAN = {
    "kepala_keluarga": [
        {"key": "menganggur", "label": "Menganggur", "opd": "Disnaker (Jamsostek)"},
        {"key": "pekerja_rentan", "label": "Pekerja Rentan", "opd": "Disnaker (Jamsostek)"},
    ],
    "istri": [
        {"key": "pelaku_usaha_mikro", "label": "Pelaku Usaha Mikro / Pra-Koperasi",
         "opd": "Diskop UKM (Bantuan Modal)"},
    ],
    "anak_usia_sekolah": [
        {"key": "bersekolah", "label": "Bersekolah", "opd": "Disdik (PIP)"},
        {"key": "putus_sekolah", "label": "Putus Sekolah", "opd": "Disdik (Beasiswa / PIP)"},
    ],
    "balita_ibu_hamil": [
        {"key": "risiko_stunting", "label": "Risiko Stunting", "opd": "Dinkes / DPPKB (PMT)"},
        {"key": "gizi_kurang", "label": "Gizi Kurang", "opd": "Dinkes / DPPKB (PMT)"},
    ],
    "lansia_disabilitas": [
        {"key": "ragam_disabilitas", "label": "Ragam Disabilitas",
         "opd": "Dinsos (Alat Bantu / Bansos)"},
        {"key": "ppks", "label": "PPKS (Pemerlu Pelayanan Kesejahteraan Sosial)",
         "opd": "Dinsos (Alat Bantu / Bansos)"},
    ],
    "lainnya": [],
}

# ---------------------------------------------------------------- Bagian IV
KESIMPULAN = (
    {"key": "ditemukan_sesuai",
     "label": "Ditemukan & Sesuai",
     "deskripsi": "Layak menerima intervensi bantuan sosial / ekonomi.",
     "wajib_catatan": False},
    {"key": "perubahan_karakteristik",
     "label": "Ditemukan & Perubahan Karakteristik",
     "deskripsi": "Data aset / sosial ekonomi diperbarui.",
     "wajib_catatan": True},
    {"key": "pindah_domisili",
     "label": "Pindah Domisili",
     "deskripsi": "Tidak lagi berdomisili di kelurahan/kecamatan ini.",
     "wajib_catatan": True},
    {"key": "meninggal_dunia",
     "label": "Meninggal Dunia",
     "deskripsi": "Seluruh anggota / individu bersangkutan wafat.",
     "wajib_catatan": True},
    {"key": "tidak_ditemukan",
     "label": "Tidak Ditemukan",
     "deskripsi": "Alamat tidak ada / warga tidak dikenal setelah konfirmasi RT/RW.",
     "wajib_catatan": True},
    {"key": "graduasi_mandiri",
     "label": "Graduasi Mandiri",
     "deskripsi": "Kondisi ekonomi telah mandiri / sejahtera; tidak layak di Desil 1-5.",
     "wajib_catatan": True},
)

# ---------------------------------------------------------------- Status alur
STATUS = ("draft", "menunggu_kelurahan", "menunggu_kecamatan", "perlu_perbaikan", "disetujui", "ditolak", "terkirim")
STATUS_TERBUKA = ("draft", "menunggu_kelurahan", "menunggu_kecamatan", "terkirim", "perlu_perbaikan")
STATUS_DAPAT_DIUBAH = ("draft", "perlu_perbaikan")
KEPUTUSAN_KELURAHAN = ("teruskan_kecamatan", "perlu_perbaikan", "ditolak")
KEPUTUSAN_KECAMATAN = ("disetujui", "perlu_perbaikan", "ditolak")
KEPUTUSAN_REVIEW = ("teruskan_kecamatan", "disetujui", "ditolak", "perlu_perbaikan")

GPS_STATUS = ("memenuhi", "pin_manual", "akurasi_rendah", "izin_ditolak", "tidak_tersedia", "belum_direkam")
JENIS_FOTO = ("rumah_depan", "rumah_samping", "objek_pendukung", "lainnya")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name) or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


def gps_max_akurasi_m() -> float:
    return _env_float("VERVAL_GPS_MAX_AKURASI_M", 30.0)


def izinkan_kirim_tanpa_gps() -> bool:
    return (os.environ.get("VERVAL_IZINKAN_KIRIM_TANPA_GPS") or "").lower() in ("1", "true", "yes")


def max_foto_mb() -> int:
    return _env_int("VERVAL_MAX_FOTO_MB", 8)


def max_foto_per_record() -> int:
    return _env_int("VERVAL_MAX_FOTO_PER_VERVAL", 6)


def min_foto() -> int:
    return max(1, _env_int("VERVAL_MIN_FOTO", 1))


def public_config() -> dict:
    return {
        "indikator": INDIKATOR,
        "indikator_sumber": INDIKATOR_SUMBER,
        "indikator_perlu_catatan": list(INDIKATOR_PERLU_CATATAN),
        "status_hubungan": list(STATUS_HUBUNGAN),
        "kondisi_rentan": {k: v for k, v in KONDISI_RENTAN.items()},
        "kesimpulan": list(KESIMPULAN),
        "status": list(STATUS),
        "keputusan_kelurahan": list(KEPUTUSAN_KELURAHAN),
        "keputusan_kecamatan": list(KEPUTUSAN_KECAMATAN),
        "izinkan_pin_manual": True,
        "jenis_foto": list(JENIS_FOTO),
        "gps_max_akurasi_m": gps_max_akurasi_m(),
        "izinkan_kirim_tanpa_gps": izinkan_kirim_tanpa_gps(),
        "max_foto_mb": max_foto_mb(),
        "max_foto_per_verval": max_foto_per_record(),
        "min_foto": min_foto(),
        "izin": IZIN,
    }
