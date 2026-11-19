# Pemetaan Menu PETA INKLUSI

Dokumen ini mencatat penerapan **Rekomendasi Urutan Menu PETA INKLUSI Sesuai SOP**
(24 Oktober 2026) pada sistem yang sudah berjalan. Sumber tunggal susunan menu ada di
`frontend/src/constants/menu.js`; rute ada di `frontend/src/App.js`.

Pemeriksaan otomatis: `node scripts/cek-menu.mjs` (susunan kelompok, tujuan menu yang
punya rute, dan menu yang terlihat per peran).

---

## 1. Susunan yang dipakai

| # | Kelompok | Item menu | Rute | Keterangan |
|---|---|---|---|---|
| 01 | Ringkasan | Dashboard | `/dashboard` | Dipertahankan |
| 01 | | Dashboard Publik | `/publik` | Dipertahankan (tanpa login) |
| 01 | | Statistik Agregat (NGO) | `/ngo/statistik` | Dipertahankan |
| 02 | Petugas dan Wilayah Tugas | Validasi Akun Petugas | `/validasi-akun` | **Pintu masuk baru** ke modul akun yang sama, default filter *Menunggu persetujuan* |
| 02 | | Penugasan Operator | `/verval/penugasan` | Dipindahkan dari grup Verval |
| 03 | Pendataan Warga | Input Data | `/input-data` | Dinaikkan sebelum daftar kategori |
| 03 | | Data Rumah Tangga | `/rumah-tangga` | Diganti nama (dari "Rumah Tangga") |
| 03 | | Data Rumah/Bangunan | `/peta-rumah` | Diganti nama (dari "Rumah / Bangunan") |
| 03 | | Data Kemiskinan | `/sosial` | Diganti nama (dari "Kemiskinan & Sosial") |
| 03 | | Data Stunting | `/data-stunting` | Diganti nama (dari "Stunting") |
| 03 | | Data ATS | `/data-ats` | Diganti nama (dari "Anak Tidak Sekolah (ATS)") |
| 03 | | Data Disabilitas | `/disabilitas` | Diganti nama (dari "Disabilitas") |
| 04 | Verifikasi dan Pemutakhiran Data | Verval & GeoTag | `/verval` | Khusus petugas/operator RT-RW |
| 04 | | Verifikasi Data | `/verifikasi` | Dipertahankan |
| 04 | | Hasil Verifikasi Data | `/verval/review` | Diganti nama (dari "Hasil Verval") |
| 05 | Peta dan Kebutuhan Wilayah | Peta Sosial | `/peta-sosial` | Dipindahkan dari grup Peta |
| 05 | | Peta Kemiskinan | `/peta-kemiskinan` | Dipindahkan |
| 05 | | Peta Dasar & Fasilitas | `/peta-dasar` | Dipertahankan |
| 05 | | Prioritas Intervensi | `/prioritas` | Dipindahkan dari grup Program |
| 06 | Program dan Intervensi | Pengajuan Program NGO | `/ngo/inquiry` | Diganti nama (dari "Pengajuan NGO") |
| 06 | | Musrenbang Tematik | `/musrenbang` | **Menu baru**: usulan Musrenbang Tematik RKPD 2027 (4 kelompok) + program/anggaran usulan OPD |
| 06 | | Manajemen Program | `/program` | Dipertahankan |
| 06 | | Stunting: Program & Anggaran | `/stunting` | Dipertahankan |
| 06 | | RAD Disabilitas 2025–2030 | `/rad` | Dipertahankan |
| 06 | | Bantuan Sosial | `/bantuan` | Dipertahankan |
| 07 | Monitoring, Evaluasi dan Laporan | Matriks Evaluasi | `/matriks` | **Pintu masuk baru**: tab *Evaluasi OPPKPKE Semester 1*, *Kemiskinan, Stunting, ATS, Anak Jalanan*, *Program Kegiatan ATS*, dan *Matriks Disabilitas* |
| 07 | | Laporan | `/laporan` | **Pusat laporan**: tab *Rekap Data* + *Laporan Wilayah* |
| 07 | | Ringkasan Mingguan | `/ringkasan-mingguan` | Dipindahkan |
| 07 | | Analisis AI | `/analisa-ai` | Diganti nama (dari "Analisa Program AI") |
| 08 | Administrasi Sistem | Master Kode Referensi | `/master-kode` | Dipertahankan |
| 08 | | Titik Koordinat Kelurahan | `/gis-koordinat` | Dipindahkan dari grup Peta |
| 08 | | Impor & Kualitas Data | `/impor-kualitas` | **Pintu masuk gabungan**: tab *Impor Baru* + *Riwayat & Kualitas* |
| 08 | | Manajemen Pengguna | `/kelola-petugas` | Diganti nama (dari "Kelola Petugas") |
| 08 | | Peran & Hak Akses | `/role-permission` | Dipertahankan |
| 08 | | Audit Log | `/audit-log` | Diganti nama (dari "Log Audit") |
| 08 | | Notifikasi Email | `/notifikasi-email` | Dipertahankan |
| 09 | Bantuan dan Aksesibilitas | Asisten AI | `/ai-assistant` | Dipertahankan |
| 09 | | Panduan Alur Sistem | `/panduan-alur` | **Rute baru di dalam shell**; versi publik tetap di `/flow-sistem` |
| 09 | | Video BISINDO | `/aksesibilitas-bisindo` | Dipindahkan dari Administrasi |
| — | Pintasan tetap (kaki sidebar) | Mode Aksesibilitas | `/aksesibilitas` | Selalu di posisi sama (WCAG 3.2.6) |

Menu khusus NGO: *Status Pengajuan Saya* (`/ngo/inquiry`), *Ajukan Pengajuan*
(`/ngo/inquiry/baru`), *Peta Sosial* (`/ngo/peta-sosial`), *Peta Kemiskinan*
(`/ngo/peta-kemiskinan`).

**Matriks Evaluasi** menyatukan empat matriks dalam satu halaman:

- *Kemiskinan, Stunting, ATS, Anak Jalanan* — terisi otomatis dari koleksi `regions`
  (sumber yang sama dengan dashboard publik dan peta tematik), termasuk baris total.
- *Evaluasi OPPKPKE Semester 1* — angka berasal dari berkas resmi yang diimpor pengguna,
  bukan diisi sistem. Tersedia unduh template Excel, validasi baris, dan impor yang
  mengganti seluruh baris untuk semester/tahun yang sama.
- *Program Kegiatan ATS* — pola yang sama untuk program dan kegiatan penanganan ATS.
- *Matriks Disabilitas* — monev kegiatan lintas OPD: target/capaian 2025–2026, alokasi,
  dan realisasi. Baris dengan nilai keuangan identik digabung agar anggaran tidak
  terhitung ganda; rincian strategi, indikator, dan hambatan tersedia per baris.

Selama data resmi belum diunggah, kedua matriks terakhir menampilkan keadaan kosong
beserta petunjuk impor; tidak ada angka contoh yang ditampilkan sebagai data nyata.
Kolom OPPKPKE dan Program ATS mengikuti kertas kerja resmi (strategi, aktivitas real,
alokasi anggaran, realisasi 2025, target 2026; serta target/anggaran/realisasi 2025–2027
untuk ATS). Rincian sumber, hasil audit kecocokan angka, dan aturan keamanan data ada di
[`DATA-SUMBER.md`](DATA-SUMBER.md).

---

## 2. Menu lama yang digabung (rute lama tetap hidup)

| Fungsi lama | Pintu masuk baru | Rute lama |
|---|---|---|
| Rekap Data | Laporan → tab **Rekap Data** | `/rekap` |
| Laporan Wilayah (PDF) | Laporan → tab **Laporan Wilayah** | `/laporan-wilayah` |
| Impor Data (Wizard) | Impor & Kualitas Data → tab **Impor Baru** | `/impor` |
| Kualitas & Riwayat Impor | Impor & Kualitas Data → tab **Riwayat & Kualitas** | `/administrasi` |
| Flow Sistem | Bantuan → **Panduan Alur Sistem** | `/flow-sistem` (publik) |

Rute lama sengaja tidak dihapus agar bookmark, tautan notifikasi email, dan skrip uji
tetap berjalan. Judul header untuk rute lama dipetakan ke label baru.

---

## 3. Kebutuhan bertanda *tambahan* yang belum dibuat

Dokumen acuan menandai lima kebutuhan sebagai **tambahan/perluasan**. Empat di antaranya
belum punya model data dan alur di sistem ini, sehingga **tidak** dibuatkan menu agar tidak
ada tautan yang menyesatkan:

| Kebutuhan | Status | Alasan |
|---|---|---|
| Validasi Akun Petugas | **Tersedia** | Modul akun sudah punya antrean `pending` + aksi aktifkan; hanya diberi pintu masuk dan filter tersendiri |
| Data Individu dan Keluarga | Belum | Belum ada registri identitas individu/keluarga; kategori masih tersimpan agregat per wilayah |
| Usulan Pemutakhiran DTSEN | Belum | Belum ada tabel tiket usulan, penerusan manual, dan rekonsiliasi |
| Perpindahan Domisili | Belum | Belum ada riwayat domisili per individu |
| Verifikasi Hasil Intervensi | Belum | Belum ada laporan pelaksanaan per penerima yang dapat diperiksa Bappeda |

Sesuai dokumen acuan bagian 9, tahap penataan navigasi (tahap 2) dapat dirilis lebih dulu;
tahap 3–9 memerlukan penyesuaian model data dan sebaiknya dikerjakan bertahap agar tidak
mengubah makna data lama.

---

## 4. Hak akses

Menu disaring per peran, dan penjagaan rute tetap dilakukan di `App.js` (menyembunyikan
menu bukan pengamanan). Yang berubah hanya pengelompokan dan label — tidak ada peran yang
mendapat akses baru.

| Peran | Contoh menu yang terlihat |
|---|---|
| superadmin/admin | Seluruh kelompok 01–09 |
| verifikator | Dashboard, Verifikasi Data, Hasil Verifikasi Data, Peran & Hak Akses, Audit Log, Video BISINDO |
| operator | Input Data, Validasi Akun Petugas, Manajemen Pengguna, Titik Koordinat Kelurahan |
| pimpinan | Dashboard, Prioritas Intervensi, Laporan, Ringkasan Mingguan |
| admin_opd | Pendataan, Peta, Program, Laporan, Bantuan |
| operator_rt_rw / petugas | Dashboard Publik, Verval & GeoTag |
| ngo | Statistik Agregat, Peta Sosial, Peta Kemiskinan, Pengajuan Program, Laporan |

---

## 5. Cara memeriksa

```bash
node scripts/cek-menu.mjs        # susunan, rute, dan hak akses menu
bash scripts/a11y-smoke.sh       # 13 halaman tanpa error runtime
node scripts/uji-navigasi.mjs --axe               # audit axe (termasuk /matriks)
node scripts/uji-navigasi.mjs --peran=superadmin  # telusuri seluruh menu
```

Uji manual per peran: masuk, lalu periksa bahwa sidebar menampilkan 9 kelompok pada urutan
di atas, setiap item dapat dibuka, dan item di luar kewenangan tidak muncul. Untuk rute
lama (`/rekap`, `/laporan-wilayah`, `/impor`, `/administrasi`), pastikan tetap terbuka.
