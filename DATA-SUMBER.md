# Sumber Data dan Hasil Audit — PETA INKLUSI

Dokumen ini mencatat berkas sumber resmi yang dipakai sistem, hasil pemeriksaan
kecocokan angka, serta aturan keamanan datanya. Diperbarui 26 Oktober 2026.

Prinsip yang dipakai:

1. **Tidak mengarang angka.** Matriks yang belum punya sumber resmi dibiarkan
   kosong dan hanya bisa diisi lewat impor.
2. **Berkas mentah tidak disalin ke repositori.** Impor membaca berkas di tempat
   asalnya; yang tersimpan di basis data hanya angka agregat (kecuali data balita
   yang memang dibutuhkan fitur, dengan masking dan pembatasan peran).
3. **Data individu tidak pernah ditampilkan ke publik.** Endpoint rumah tangga
   dan balita mewajibkan login staf, menyamarkan nama/KK/alamat untuk peran
   non-sensitif, dan mencatat akses identitas pada `audit_logs`.
4. **Impor bersifat atomik.** Bila satu baris bermasalah, tidak ada baris yang
   disimpan.

Pemetaan kontrol keamanan ke UU PDP, PP 71/2019, UU Adminduk, SPBE, BSSN, dan
ISO/IEC 27001 ada di [`KEAMANAN-DATA.md`](KEAMANAN-DATA.md).

---

## 1. Hasil audit per sumber

| Sumber | Cakupan | Tujuan di sistem | Hasil |
|---|---|---|---|
| DTSEN Kec. Tallo + Pilah DTSEN Kec. Makassar | 29.213 KK, 106.863 jiwa, 29 kelurahan | `households`, `village_stats` (Data Kemiskinan) | **100% sama per kelurahan** (0 selisih) |
| Surat DINKES September 2026 (disabilitas) | 5.171 orang, 15 kecamatan | `disability_opd_stats`, `regions.disabilitas` | **Sama** dengan total per kecamatan |
| Rekap disabilitas per kelurahan Tallo & Makassar | 1.226 orang (938 + 288) | `disability_region_stats`, `kelurahan.disabilitas` | **Sama**; 5 kelurahan Makassar bernilai 0 sesuai total resmi |
| PDF Data Balita Stunting 2026 | 452 baris terbaca, 450 balita unik (2 duplikat) | `stunting_children`, `kelurahan.stunting_anak` | **Sama**; 1 balita belum terpetakan kelurahan |
| Matriks Kegiatan Stunting 2025–2027 | 49 sub kegiatan, 23 OPD | `stunting_programs/activities/subactivities` | **Sama** dengan isi basis data |
| Matriks Evaluasi OPPKPKE Semester 1 2026 | 68 kegiatan, 39 OPD | `oppkpke_items` | **Diimpor & terverifikasi** |
| Matriks Program, Kegiatan & Anggaran ATS | 17 program, 11 OPD | `ats_program_items` | **Diimpor & terverifikasi** |
| Matriks Monev Kegiatan Disabilitas | 87 baris → 61 baris unik, 21 OPD | `disabilitas_items` | **Diimpor & terverifikasi** |
| Matriks Musrenbang Tematik RKPD 2027 | 64 usulan (4 kelompok), 11 intervensi | `musrenbang_usulan`, `musrenbang_intervensi` | **Diimpor & terverifikasi** |
| Matriks kemiskinan/stunting/ATS/anak jalanan (kota) | deret 2021–2025 + target RPJMD | acuan pembanding | Dipakai sebagai pembanding; bukan tabel per kecamatan |

### Angka kunci yang tersimpan

- **OPPKPKE Semester 1 2026**: 68 kegiatan · 39 OPD ·
  anggaran Rp213.914.294.961 · realisasi Semester 1 2025 Rp77.347.658.086 ·
  total realisasi 2025 Rp79.174.126.109.
- **Program ATS**: 17 program · 11 OPD · anggaran 2025 Rp2.988.051.880
  (realisasi Rp2.772.626.058) · anggaran 2026 Rp15.111.752.700
  (realisasi Semester 1 Rp1.965.703.256).
- **Disabilitas**: 5.171 orang (L 2.612 · P 2.558 · 1 memilih tidak menjawab).
- **Stunting 2026**: 450 balita (Tallo 284 · Makassar 166) di 27 kelurahan.
- **DTSEN**: 29.213 KK · 106.863 jiwa · 9.694 KK desil 1–2.
- **Monev Disabilitas**: 61 kegiatan · 21 OPD · anggaran 2025 Rp132.697.780.968
  (realisasi Rp10.004.192.555, 7,54%) · anggaran 2026 Rp264.834.535.959
  (realisasi Rp7.478.840.305).
- **Musrenbang Tematik 2027**: 64 usulan (Disabilitas 28 · Lansia 10 · Perempuan 15 ·
  Anak 11) · 11 intervensi dari 3 OPD · anggaran usulan Rp176.440.000.

---

## 2. Sinkronisasi angka wilayah

Untuk dua kecamatan yang punya rincian resmi (Tallo & Makassar),
`kelurahan.disabilitas` dan `kelurahan.stunting_anak` diganti dengan angka sumber.
`regions.disabilitas` untuk **15 kecamatan** memakai rekap DINKES.

Field yang berasal dari sumber resmi diberi penanda `disabilitas_otoritatif` /
`stunting_anak_otoritatif` beserta `*_sumber`. `_recompute_region` tidak menimpa
field bertanda tersebut, sehingga angka resmi tidak turun kembali saat ada
penyuntingan kelurahan.

### Selisih yang diketahui (bukan kesalahan impor)

| Hal | Angka | Penjelasan |
|---|---|---|
| 1 balita Tallo tanpa kelurahan | 284 vs 283 | Puskesmas "Jumpandang Baru" mencakup 5 kelurahan, jadi tidak bisa disimpulkan otomatis; tetap dihitung pada angka kecamatan |
| ATS Kota Makassar | 15.168 vs 15.276 di matriks kota | Selisih 108 berasal dari distribusi ATS per kelurahan Tallo (2.132) yang lebih rendah dari angka kecamatan sebelumnya (2.240); tidak ada rincian resmi per kelurahan untuk dikoreksi |
| Kemiskinan ekstrem per kecamatan | 13.334 KK | Masih rekap lama. DTSEN menyediakan **desil 1–2** untuk Tallo & Makassar (9.694 KK) dengan metrik berbeda, sehingga tidak dicampur ke kolom "kemiskinan ekstrem" |
| Disabilitas 13 kecamatan lain | total 5.171 | Angka kecamatan resmi; rincian per kelurahan belum tersedia sehingga peta kelurahan hanya terisi untuk Tallo & Makassar |

---

## 3. Impor ulang matriks resmi

```bash
cd backend
python matriks_resmi.py \
  --oppkpke "/path/MATRIKS EVALUASI OPPKPKE ....xlsx" \
  --ats "/path/Matriks_Program_Kegiatan_ATS.xlsx" \
  --semester 1 --tahun 2026
```

Tambahkan `--dry-run` untuk memeriksa jumlah baris dan total tanpa menulis.
Setiap berkas menghasilkan hash SHA-256 yang disimpan pada dokumen
(`sumber_hash`) sebagai jejak integritas, dan satu entri `audit_logs`
(`impor_matriks_resmi`).

Berkas monev disabilitas dan Musrenbang memiliki perintah tersendiri:

```bash
cd backend
python matriks_resmi.py --disabilitas "/path/matriks monev keg disabilitas.xlsx"
python musrenbang.py --file "/path/Matriks Musrenbang Tematik ....xlsx"
```

Monev disabilitas dibaca dari 23 lembar OPD (lembar GABUNGAN dilewati). Baris dengan
nilai keuangan identik digabung agar anggaran tidak terhitung ganda; nama OPD
diseragamkan (mis. “Dinkes” → “Dinas Kesehatan”). Musrenbang memisahkan **usulan**
(naratif per nomor) dan **intervensi** (program/kegiatan/anggaran per OPD).

Di aplikasi, unggahan manual memakai template dari tombol **Unduh Template Excel**
pada halaman Matriks. Kolom template mengikuti nama kolom resmi (lihat lembar
`REFERENSI` di dalam berkas).

Snapshot non-pribadi hasil impor tersimpan di `backend/data_resmi/` (68 kegiatan
OPPKPKE dan 17 program ATS). Snapshot dimuat otomatis saat start **hanya bila**
koleksi `oppkpke_items`/`ats_program_items` masih kosong, dan dapat dimuat manual:

```bash
cd backend
python snapshot_data_resmi.py --load    # isi koleksi yang kosong
python snapshot_data_resmi.py --export  # tulis ulang snapshot dari basis data
```

Seed wilayah (`regions`/`kelurahan`) juga sudah memuat angka resmi DINKES dan
stunting 2026, sehingga deployment baru tidak kembali ke nilai lama.

---

## 4. Pemeriksaan cepat

```bash
# struktur menu & rute
node scripts/cek-menu.mjs

# 13 halaman tanpa error runtime
bash scripts/a11y-smoke.sh

# audit axe seluruh tab Matriks
node scripts/uji-navigasi.mjs --axe

# telusuri semua menu per peran
node scripts/uji-navigasi.mjs --peran=superadmin
```

Verifikasi angka sumber terhadap basis data dilakukan dengan membandingkan
agregat per kelurahan (KK, jiwa, desil 1–2, disabilitas, stunting) — bukan dengan
menyalin data individu.
