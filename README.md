# PETA INKLUSI — Bappeda Kota Makassar

> **Sistem Intelijen & Pemetaan Data Inklusi Sosial** — platform perencanaan, verifikasi lapangan, dan pemetaan berbasis data untuk Badan Perencanaan Pembangunan Daerah (Bappeda) Kota Makassar.

[![Stack](https://img.shields.io/badge/stack-React%20%2B%20FastAPI%20%2B%20MariaDB-117A69)](#2-tech-stack)
[![Deploy](https://img.shields.io/badge/deploy-Coolify%20%2F%20Dockerfile-232F3E)](./DEPLOY_COOLIFY.md)

---

## Daftar Isi

1. [Overview Project](#1-overview-project)
2. [Tech Stack](#2-tech-stack)
3. [Folder Structure](#3-folder-structure)
4. [Data Flow](#4-data-flow)
5. [Coding Conventions](#5-coding-conventions)
6. [Menjalankan Secara Lokal](#6-menjalankan-secara-lokal)
7. [Referensi API](#7-referensi-api)
8. [Peran & Wewenang](#8-peran--wewenang)
9. [Deployment](#9-deployment)
10. [Catatan untuk AI Agent Berikutnya](#10-catatan-untuk-ai-agent-berikutnya)

---

## 1. Overview Project

**PETA INKLUSI** (sebelumnya *SIDATA*) adalah platform satu pintu bagi Bappeda Kota Makassar untuk **memantau, memverifikasi di lapangan, memetakan, dan menganalisa data sosial inklusif** di 15 kecamatan dan 153 kelurahan Kota Makassar.

### Masalah yang diselesaikan

Data kemiskinan (DTSEN), stunting, anak tidak sekolah (ATS), anak jalanan, disabilitas, serta kelayakan rumah/bangunan sebelumnya tersebar di berbagai berkas Excel terpisah. Platform ini menyatukan data induk DTSEN, alur Verval & GeoTag berjenjang dari RT/RW hingga Kecamatan, kolaborasi program NGO, serta ringkasan otomatis agar perencanaan program tepat sasaran dan teraudit.

### Fungsi utama

| Fitur | Penjelasan |
|---|---|
| **Dashboard real-time & publik** | KPI kota, tren kemiskinan vs target RPJMD, tren stunting (EPPGBM & SSGI), grafik per kecamatan/kelurahan, PMKS, serta dashboard informasi umum (`/publik`) tanpa login. |
| **Data Rumah Tangga DTSEN** | Daftar rumah tangga DTSEN lengkap dengan penyamaran (masking) sesuai peran, skor kerentanan (`scoring.py`), filter kecamatan/kelurahan/desil/prioritas, serta ekspor Excel/CSV. |
| **Verval & GeoTag Lapangan v2** | Verifikasi lapangan **2 tahap** (`RT/RW -> Kelurahan -> Kecamatan`), kamera live browser (`getUserMedia`, tanpa unggah galeri), cetak watermark foto tanpa NIK/nama warga, hapus metadata EXIF GPS, target GPS 30 meter + pin manual beralasan, pendaftaran warga baru, dan sinkronisasi data aktif dengan menjaga snapshot asli `dtsen_awal`. |
| **Peta Sosial, Kemiskinan, Rumah & Peta Dasar** | Peta choropleth kecamatan/kelurahan, layer titik foto GeoTag Verval (`VervalMapLayer`), peta bangunan, serta fasilitas umum dari GeoJSON lokal (`peta_dasar.py`) **tanpa perlu API Google Maps berbayar**. |
| **Stunting, ATS, Disabilitas & RAD** | Modul program/anggaran stunting lintas OPD, anak tidak sekolah, ragam disabilitas, serta monitoring RAD Disabilitas 2025–2030. |
| **Matriks, Musrenbang & Program NGO** | Rekap matriks OPPKPKE/ATS/disabilitas, Musrenbang Tematik, serta portal pengajuan program oleh NGO dengan notifikasi email/audit. |
| **Analisa AI & Asisten AI** | Rekomendasi program & tanya jawab berbasis angka nyata di database via Hostlinku (`deepseek-v4-1-flash`), dikirim streaming (SSE). |
| **Aksesibilitas** | Mode dukungan netra/baca layar (Web Speech API perangkat), kontrol ukuran teks, kontras tinggi, BISINDO, serta fokus keyboard WCAG. |
| **Manajemen pengguna berjenjang** | Superadmin mengelola akun kota/Kecamatan/Kelurahan; **Operator Kecamatan** mengelola akun **Petugas RT/RW & Kelurahan** dan penugasan wilayah di kecamatannya sendiri. |
| **Laporan resmi & Audit Log** | Ekspor PDF berkop resmi (Kota Makassar & Bappeda), Excel, ringkasan mingguan pimpinan, serta jejak audit seluruh aksi penting. |

### Kategori data wilayah yang dikelola

`kemiskinan_ekstrim_kk` · `stunting_anak` · `anak_jalanan` · `ats` · `disabilitas` · `kemiskinan_persen`

---

## 2. Tech Stack

### Frontend

| Komponen | Pilihan | Catatan |
|---|---|---|
| Framework | **React 19** (TypeScript + JavaScript) | Create React App di-override dengan **craco** (`craco.config.js`) |
| Routing | **react-router-dom 7** | Seluruh rute didefinisikan di `src/App.js` |
| Styling | **Tailwind CSS 3** | Palet **PETA INKLUSI**: Navy `#232F3E`, Teal `#117A69`, Mint `#6FE3CF` di `src/index.css` & `tailwind.config.js` |
| Komponen UI | **shadcn/ui** (46 komponen) | Ada di `src/components/ui/`, dibangun di atas Radix UI |
| Ikon | **lucide-react** | |
| Grafik | **Recharts 3** | Dashboard, tren, dan statistik |
| Peta | **Leaflet 1.9** (OSM & ESRI Imagery/Hybrid gratis) | Berjalan penuh tanpa API key; Google Maps API bersifat opsional jika `GOOGLE_MAPS_API_KEY` diisi |
| HTTP client | **axios** | Satu instance terpusat di `src/lib/api.js` (`withCredentials: true`) |
| Markdown & Animasi | **marked**, **framer-motion** | Merender analisa AI & transisi UI |
| Notifikasi | **sonner** + `hooks/use-toast.js` | |
| Alias import | `@/` → `src/` | Diatur di `craco.config.js`, `tsconfig.json` & `jsconfig.json` |

### Backend

| Komponen | Pilihan | Catatan |
|---|---|---|
| Framework | **FastAPI 0.110** | Semua endpoint di bawah `APIRouter(prefix="/api")` |
| Server | **Uvicorn** | Port dari env `PORT` (default `8000`) |
| Validasi | **Pydantic v2** | Model input di masing-masing modul router & `server.py` |
| Gambar & Laporan | **Pillow** (watermark + strip EXIF JPEG), **reportlab** (PDF), **openpyxl** (Excel) | |
| AI | **Hostlinku gateway** (`llm_hostlinku.py`) | Gateway OpenAI-compatible (default `deepseek-v4-1-flash`), streaming SSE |
| TTS | **Web Speech API** di perangkat (frontend) | `speechSynthesis` suara `id-ID`; endpoint `POST /api/tts` di server berstatus nonaktif (`503`) |

### Database

| Komponen | Pilihan |
|---|---|
| DBMS | **MariaDB 11.8** (MySQL-compatible) |
| Driver | **aiomysql** (async connection pool) |
| Pola penyimpanan | **Document store di atas SQL** (`backend/mariadb_store.py`) |

> **Penting — cara data disimpan.**
> `backend/mariadb_store.py` menyediakan antarmuka koleksi bergaya Motor/PyMongo (`find_one`, `insert_one`, `update_one`, `find().sort().to_list()`, dll.) di atas tabel SQL MariaDB bernama `doc_<nama>`, dengan generated column `PERSISTENT` + index untuk field yang sering difilter (didaftarkan pada `INDEXED_FIELDS` di `mariadb_store.py`).

**Tabel `doc_*` utama yang dipakai**

| Tabel | Isi |
|---|---|
| `doc_users` | Akun pengguna (email unik, hash bcrypt, peran, wilayah/kelurahan/RW/RT, status) |
| `doc_households`, `doc_household_members` | Data induk rumah tangga & anggota keluarga DTSEN (termasuk snapshot `dtsen_awal`) |
| `doc_village_stats`, `doc_district_stats` | Rekap statistik per kelurahan (153) & kecamatan (15) |
| `doc_regions`, `doc_kelurahan`, `doc_geo_kelurahan` | Data wilayah agregat & geometri GeoJSON kelurahan |
| `doc_verval_records`, `doc_verval_foto`, `doc_verval_riwayat` | Dokumen Verval GeoTag, metadata foto ber-watermark, & jejak audit 2 tahap |
| `doc_verval_penugasan`, `doc_verval_sasaran` | Penugasan wilayah RT/RW & penetapan KK sasaran petugas |
| `doc_rumah`, `doc_map_config`, `doc_peta_dasar_layers` | Data bangunan/rumah, konfigurasi basemap, & layer peta dasar |
| `doc_data_changes`, `doc_audit_logs` | Antrean perubahan wilayah umum & log audit aktivitas sistem |
| `doc_stunting_children`, `doc_rad_*`, `doc_disability_*` | Data stunting by-name, monitoring RAD disabilitas, & statistik disabilitas |
| `doc_ngo_inquiries`, `doc_musrenbang_usulan`, `doc_scoring_config` | Pengajuan program NGO, Musrenbang tematik, & konfigurasi skoring kerentanan |
| `doc_ai_analyses`, `doc_import_batches`, `doc_data_quality_issues` | Riwayat analisa AI, batch impor data resmi, & pemantauan kualitas data |

### Storage

| Jenis berkas | Lokasi & Sifat |
|---|---|
| **Foto GeoTag Verval (ber-watermark)** | Disimpan di disk persisten pada `VERVAL_STORAGE_DIR` (mis. `/srv/verval`), disajikan lewat `GET /api/verval/foto/{fid}` setelah cek izin wilayah/peran. |
| Logo & aset laporan | `backend/assets/` dan `backend/assets/geo/basemap/` — terbawa di image container. |
| Data impor & potongan unggahan | Disimpan di MariaDB (`doc_import_files`, `doc_inquiry_files`) agar aman saat container restart. |
| PDF & Excel | Dihasilkan on-the-fly ke memori (`io.BytesIO`) dan dikirim via `StreamingResponse`. |

> **Catatan Deployment:** Karena modul **Verval & GeoTag** menyimpan foto rumah ber-watermark ke `VERVAL_STORAGE_DIR`, container aplikasi **membutuhkan persistent volume** pada Coolify (mis. mount `/srv/verval`) agar foto tidak hilang saat redeploy/restart.

---

## 3. Folder Structure

```text
/
├── Dockerfile                        # Multi-stage: build React -> Python 3.11 -> image produksi
├── .dockerignore                     # Cegah node_modules/.git/.env masuk build context
├── .env.example                      # Template variabel environment Coolify / produksi
├── docker-compose.yml                # Uji coba lokal: app + MariaDB
├── DEPLOY_COOLIFY.md                 # Panduan deploy langkah demi langkah ke Coolify
├── README.md                         # Dokumen ini
│
├── backend/                          # ============ API FastAPI ============
│   ├── server.py                     # Entrypoint: FastAPI app, auth middleware, /admin/users, penyajian SPA
│   ├── auth.py                       # Hash bcrypt, JWT cookie/Bearer, seed superadmin idempotent
│   ├── mariadb_store.py              # Lapisan koleksi di atas MariaDB + INDEXED_FIELDS
│   ├── scope.py                      # Pembatasan wilayah (Kecamatan / Kelurahan / RT-RW) & middleware
│   ├── verval.py                     # Router /api/verval/*: 2-tahap review, warga baru, pin manual, sync DTSEN
│   ├── verval_config.py              # Konfigurasi Verval (11 indikator, peran tahap 1/2, batas GPS 30m)
│   ├── verval_storage.py             # Simpan foto Verval, hapus EXIF GPS, & cetak watermark JPEG
│   ├── dtsen_ref.py                  # Generator referensi HMAC stabil DTSEN (VERVAL_REF_SECRET)
│   ├── sosial.py                     # Router /api/sosial/*, /wilayah/*, stunting/RAD/audit logs, masking PII
│   ├── data_manage.py                # CRUD rumah tangga, hitung ulang agregat (refresh_agregat_for), ekspor DTSEN
│   ├── scoring.py                    # Perhitungan risk_score & tingkat prioritas rumah tangga
│   ├── peta_dasar.py                 # Layer peta dasar & fasilitas umum GeoJSON
│   ├── rumah.py                      # Peta bangunan / rumah & /api/map/config
│   ├── llm_hostlinku.py              # Klien streaming LLM Hostlinku (DeepSeek / Qwen)
│   ├── inklusi.py, inklusi_extra.py  # Modul PETA INKLUSI (NGO inquiry, ringkasan, cerita)
│   ├── matriks.py, musrenbang.py     # Matriks program & Musrenbang tematik
│   ├── report.py, export_excel.py    # Ekspor PDF resmi & Excel
│   ├── assets/                       # Logo Makassar/Bappeda & GeoJSON peta dasar
│   ├── tests/
│   │   └── test_verval_v2.py         # Suite pytest terisolasi FakeDB untuk Verval & GeoTag v2
│   ├── requirements-prod.txt         # Dependensi produksi Docker
│   ├── .env.example                  # Template dev lokal
│   └── .env                          # Konfigurasi lokal (DIABAIKAN GIT)
│
├── frontend/                         # ============ Aplikasi React ============
│   ├── craco.config.js               # Override CRA: alias @/ & webpack config
│   ├── tailwind.config.js            # Tema warna & tipografi
│   ├── public/index.html             # Shell HTML & CDN Leaflet
│   └── src/
│       ├── index.js, App.js          # Bootstrap & definisi seluruh rute terproteksi
│       ├── constants/
│       │   ├── menu.js               # Sumber tunggal navigasi 9 kelompok menu
│       │   ├── roles.js              # Himpunan peran menu & penjaga rute
│       │   └── makassar_geo.json     # GeoJSON batas 15 kecamatan
│       ├── features/
│       │   ├── data/roles.ts         # Matriks label & hak baca/tulis/sensitif di frontend
│       │   ├── peta/basemaps.ts      # Spesifikasi OSM, ESRI Satellite/Hybrid gratis + fallback Google
│       │   ├── verval/
│       │   │   ├── api.ts            # Konstanta label/warna status Verval 2 tahap & pin manual
│       │   │   ├── ui.tsx            # Komponen UI kartu/badge/perbandingan DTSEN
│       │   │   └── VervalMapLayer.tsx# Layer titik foto GeoTag Verval pada peta Leaflet
│       │   └── inklusi/              # InklusiMap, Inquiry NGO, RingkasanMingguan
│       ├── components/
│       │   ├── SidebarLayout.js      # Shell sidebar, header, notifikasi & badge antrean
│       │   ├── AccessibilityBar.js   # Bilah aksesibilitas netra/tuli
│       │   └── ui/                   # Komponen shadcn/ui (jangan edit manual)
│       └── pages/                    # Halaman per rute (/dashboard, /verval, /verval/review,
│                                     #   /verval/penugasan, /kelola-petugas, /rumah-tangga,
│                                     #   /peta-sosial, /peta-kemiskinan, /peta-rumah, dll.)
│
└── tests/                            # Pengujian integrasi tambahan (test_verval_geotag.py)
```

---

## 4. Data Flow

### 4.1 Alur Autentikasi & Pembatasan Wilayah

```text
Login.js  ──POST /api/auth/login──▶  cek doc_users (email + bcrypt + status=active)
                                     terbitkan JWT access (12j) + refresh (7h)
                                     Set-Cookie httpOnly (COOKIE_SECURE / COOKIE_SAMESITE)

Permintaan API berikutnya ──▶ Auth middleware + WilayahScopeMiddleware (scope.py)
                              • operator / operator_kecamatan -> dipaksa scope Kecamatannya
                              • operator_kelurahan            -> dipaksa scope Kelurahannya
                              • petugas / operator_rt_rw      -> dipaksa whitelist endpoint & wilayah
```

### 4.2 Alur Verval & GeoTag 2 Tahap (RT/RW -> Kelurahan -> Kecamatan)

```text
1. Petugas RT/RW (/verval)
   • Jika kolom RT/RW DTSEN masih kosong, otomatis mendapat akses warga se-Kelurahan
     (mode kelurahan_tanpa_rtrw) dengan No. KK tampil utuh untuk pencocokan NIK.
   • Dapat mendaftarkan warga belum terdata lewat POST /api/verval/warga-baru.
   • Isi NIK/RT/RW/Desil (identitas_lapangan) + 11 indikator + kesimpulan.
   • Wajib jepret kamera live browser (getUserMedia), target GPS <= 30 m atau pin manual
     dalam batas Kota Makassar disertai alasan wajib.
   • Foto diproses verval_storage.py: strip EXIF GPS + cetak watermark (tanpa NIK/nama warga).
   • Kirim -> status menjadi `menunggu_kelurahan`.

2. Kelurahan — Pemeriksaan Tahap 1 (/verval/review)
   • Memeriksa foto ber-watermark, titik lokasi, NIK, & perbandingan 11 indikator.
   • Keputusan: `teruskan_kecamatan` (`menunggu_kecamatan`), `perlu_perbaikan`, atau `ditolak`.
   • Diblokir (HTTP 403) jika mencoba melakukan persetujuan akhir (`disetujui`).

3. Kecamatan / Admin Bappeda / Superadmin — Persetujuan Akhir (/verval/review)
   • Keputusan `disetujui` menjalankan _terapkan_hasil_verval():
     - Menyimpan snapshot nilai asli ke `households.dtsen_awal` (sekali saja, tidak ditimpa).
     - Memperbarui `households` (NIK, RT/RW, kondisi, lat/lng, risk_score via scoring.py)
       atau menambahkan dokumen baru untuk Warga Baru.
     - Menyinkronkan `household_members`, `village_stats`, & `district_stats` (refresh_agregat_for).
     - Titik lokasi Verval tampil pada layer GeoTag peta dan tabel /rumah-tangga.
```

### 4.3 Alur Analisa AI (SSE Streaming)

```text
AIAnalysis.js ──POST /api/ai/analyze──▶ server.py kumpulkan ringkasan angka nyata dari DB
                                        ▼
                                 llm_hostlinku.py (model default: deepseek-v4-1-flash)
                                        ▼
                                 stream SSE `data: {"delta": "..."}` -> simpan doc_ai_analyses
```

### 4.4 Alur Permintaan di Produksi / Staging (Satu Kontainer)

```text
https://peta-inklusi.makassarkota.go.id/*  (atau staging.bappedapeta.warunggamer.com)
            │
            ▼
   Reverse proxy Coolify / Traefik
            │
            ▼
   Uvicorn (PORT, default 8000)
     ├── /api/*  ──▶ api_router FastAPI (server.py, verval.py, sosial.py, dll.)
     └── /*      ──▶ SPAStaticFiles("/") menyajikan /srv/frontend/build -> fallback index.html
```

---

## 5. Coding Conventions

### 5.1 Bahasa & Penamaan
- **UI, pesan error API, & komentar**: Bahasa Indonesia formal pemerintahan.
- **Variabel/fungsi/endpoint**: Bahasa Inggris atau istilah domain baku (`kelurahan`, `kecamatan`, `wilayah`, `verifikasi`, `verval`, `petugas`, `terbilang`).
- **Frontend**: `src/pages/` memakai `PascalCase.js`/`.tsx`, komponen `shadcn/ui` di `src/components/ui/` jangan diubah langsung, selalu impor API dari `@/lib/api`, dan tampilkan error via `formatApiErrorDetail()`.
- **Tema warna**: Navy `#232F3E`, Teal utama `#117A69`, dan aksen Mint `#6FE3CF` (hindari merah untuk elemen non-peringatan).

### 5.2 Backend (Python)
1. Semua endpoint wajib berada di bawah prefix `/api`.
2. Operasi database melalui `db.<collection>` (`mariadb_store.py`); field yang sering difilter didaftarkan di `INDEXED_FIELDS`.
3. Operator query didukung: kesamaan langsung, `$ne`, `$exists`, `$in`, `$nin`, `$gt(e)`, `$lt(e)`, `$regex`, `$set`, `$unset`, `$inc` (**tidak** mendukung `$or`).
4. Jangan pernah mengembalikan `password_hash` ke klien.
5. Waktu disimpan dalam ISO UTC (`datetime.now(timezone.utc).isoformat()`); format waktu pada watermark foto dikonversi ke WITA (`Asia/Makassar`).

### 5.3 Environment Variables & Sifat Build-Time vs Runtime

| Variabel | Sifat | Catatan |
|---|---|---|
| Semua variabel backend (`DB_*`, `JWT_SECRET`, `VERVAL_*`, `HOSTLINKU_*`, `PORT`) | **Runtime** | Dibaca saat server start/berjalan di Coolify atau `backend/.env`. |
| `REACT_APP_BACKEND_URL` | **Build-time** | Dibekukan saat `yarn build`. Pada deployment satu domain, **kosongkan** agar memakai path relatif `/api`. |

Template lengkap tersedia di [.env.example](file:///c:/DyoDev/BappedaMakasar/Bappeda-main/.env.example) (Coolify/produksi) dan [backend/.env.example](file:///c:/DyoDev/BappedaMakasar/Bappeda-main/backend/.env.example) (dev lokal).

---

## 6. Menjalankan Secara Lokal

### Prasyarat
- **Python 3.11+** (image produksi memakai Python 3.11).
- **Node.js 20+** dan **Yarn 1.x**.
- **MariaDB 10.6+ / MySQL 8+**.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements-prod.txt

cp .env.example .env             # Sesuaikan DB_*, JWT_SECRET, VERVAL_REF_SECRET, VERVAL_STORAGE_DIR
uvicorn server:app --reload --host 127.0.0.1 --port 8001
```

> **Perhatian keamanan database lokal:** Pastikan `DB_HOST` di `backend/.env` mengarah ke database dev/staging Anda — jangan arahkan ke database produksi saat menguji alur tulis.
>
> **Cookie & Host lokal:** Gunakan `COOKIE_SECURE=false` dan `HOST=127.0.0.1` saat mengakses via `http://localhost`.

### Frontend

```bash
cd frontend
yarn install
cp .env.example .env             # REACT_APP_BACKEND_URL=http://localhost:8001
yarn start                       # http://localhost:3000 (atau set PORT=15000)
```

### Menjalankan Pengujian Backend Terisolasi (FakeDB)

Modul Verval & GeoTag v2 memiliki suite uji in-memory tanpa menyentuh MariaDB nyata di `backend/tests/test_verval_v2.py` (6 skenario: fallback kelurahan tanpa RT/RW, watermark JPEG & strip EXIF, batas GPS 30m + pin manual, alur 2 tahap & pelestarian `dtsen_awal`, warga baru, serta scoping Kecamatan):

```bash
cd backend
pytest -o required_plugins= -o addopts= tests/test_verval_v2.py -v
```

---

## 7. Referensi API

Semua endpoint berawalan `/api`.

### Autentikasi & Pengguna

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| POST | `/auth/login`, `/auth/logout`, `/auth/register` | publik | Login httpOnly cookie, logout, & pendaftaran |
| GET | `/auth/me` | login | Profil pengguna aktif |
| GET, POST | `/admin/users` | superadmin / Kecamatan | Daftar & buat akun (`Kecamatan` hanya mengelola `petugas` & `operator_kelurahan` wilayahnya) |
| PATCH, DELETE | `/admin/users/{id}` | superadmin / Kecamatan | Ubah data atau hapus akun dalam cakupan wilayahnya |
| PATCH, POST | `/admin/users/{id}/status`, `/reset-password` | superadmin / Kecamatan | Ubah status (`active`/`inactive`/`pending`) & reset sandi |

### Data Sosial & Rumah Tangga DTSEN

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| GET | `/sosial/overview`, `/sosial/ranking` | login | Rekap indikator sosial & peringkat kelurahan/kecamatan |
| GET | `/sosial/households`, `/sosial/households/{id}` | login | Daftar & detail rumah tangga DTSEN (masking PII & filter wilayah otomatis via `scope.py`) |
| GET, PUT | `/sosial/scoring-config` | login / admin | Lihat & atur bobot perhitungan `risk_score` |
| GET | `/wilayah/summary`, `/wilayah/kelurahan`, `/geo/kelurahan` | publik / login | Ringkasan wilayah & GeoJSON batas kelurahan |

### Verval & GeoTag DTSEN v2 (`/api/verval/*`)

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| GET | `/verval/konfigurasi`, `/verval/saya` | login | Konfigurasi form 11 indikator, batas GPS (`30 m`), & hak akses peran |
| GET | `/verval/sasaran`, `/verval/sasaran/{ref}` | RT/RW (`petugas`/`operator_rt_rw`) | Daftar KK sasaran (termasuk fallback kelurahan bila RT/RW DTSEN kosong) |
| POST | `/verval/warga-baru` | RT/RW | Daftarkan keluarga belum terdata ke antrean Verval wilayahnya |
| POST, GET, PUT | `/verval/records`, `/verval/records/{rid}` | sesuai wilayah & peran | Buat draf, baca daftar/detail (Ketua RW dapat memantau RT di RW-nya), & simpan isian |
| POST, DELETE | `/verval/records/{rid}/foto`, `/foto/{fid}` | RT/RW pemilik draf | Unggah foto kamera live (watermark + strip EXIF GPS; mendukung `pin_manual` + alasan) |
| GET | `/verval/foto/{fid}` | pemilik / RW / Kel / Kec / Bappeda | Ambil berkas foto JPEG ber-watermark |
| POST | `/verval/records/{rid}/kirim` | RT/RW | Kirim laporan lapangan -> status `menunggu_kelurahan` |
| POST | `/verval/records/{rid}/review` | Kel (tahap 1) / Kec & Bappeda (akhir) | Keputusan `teruskan_kecamatan`, `perlu_perbaikan`, `ditolak`, atau `disetujui` (sync sistem + jaga `dtsen_awal`) |
| GET, POST | `/verval/operator`, `/wilayah-dtsen`, `/penugasan`, `/sasaran-kk` | Kecamatan / Bappeda / Superadmin | Kelola petugas wilayah & penugasan sasaran KK |
| GET | `/verval/peta` | login | Titik GeoTag untuk layer `VervalMapLayer` (detail foto/koordinat untuk peran berwenang, agregat untuk OPD/viewer) |

### Endpoint Domain Lainnya
- **Data Wilayah & Verifikasi Umum**: `/regions*`, `/kelurahan*`, `/verifikasi*`
- **Peta Dasar, Rumah & Laporan**: `/peta-dasar/*`, `/map/config`, `/report/*`, `/export/excel`, `/dtsen/export`
- **Program Inklusi & AI**: `/matriks/*`, `/musrenbang`, `/stunting/*`, `/rad/*`, `/ngo/*`, `/ai/analyze`, `/ai/history*`, `/health`

---

## 8. Peran & Wewenang

| Peran | Label UI | Wewenang Utama |
|---|---|---|
| `superadmin` (`admin`) | Superadmin | Akses penuh seluruh kota, konfigurasi sistem, kelola akun kota/Kecamatan/Kelurahan, penugasan & ACC akhir Verval. |
| `admin_bappeda` | Admin Bappeda | Akses data lengkap seluruh Kota Makassar, penugasan Verval, analisa/laporan, & ACC akhir Verval. |
| `operator`, `operator_kecamatan` | Kecamatan | Akun terpadu tingkat kecamatan: kelola akun `Petugas RT/RW` & `Kelurahan` di kecamatannya, atur penugasan Verval, input data wilayah, serta **ACC akhir Verval** wilayahnya. |
| `verifikator` | Verifikator | Memeriksa perubahan data & menyetujui/menolak Verval dalam cakupan wilayahnya. |
| `operator_kelurahan` | Kelurahan | **Pemeriksa Verval tahap 1** di kelurahannya (`teruskan_kecamatan`, `perlu_perbaikan`, `ditolak`; diblokir dari ACC akhir `disetujui`), melihat detail rumah tangga & foto wilayahnya. |
| `petugas`, `operator_rt_rw` | Petugas RT/RW | Akses lapangan (`Dashboard Publik` + `Verval & GeoTag`): survey KK sasaran, foto rumah live kamera, pin manual, daftar warga baru (Ketua RW dapat memantau progres RT dalam RW & kelurahan yang sama). |
| `pimpinan` | Pimpinan | Memantau dashboard, laporan, & hasil Verval (read-only). |
| `admin_opd` | Admin OPD | Mengelola data/program OPD terkait; tampilan peta Verval bersifat rekap agregat. |
| `viewer` | Viewer | Akses baca statistik & rekap agregat tanpa NIK/No. KK rinci. |
| `ngo` | NGO | Mengajukan dan memantau proposal program inklusi (/ngo/inquiry) & peta agregat. |
| publik (tanpa login) | Publik | Akses terbatas pada beranda, `/publik`, peta sosial/kemiskinan agregat, dan halaman tentang. |

---

## 9. Deployment

Panduan lengkap ada di **[DEPLOY_COOLIFY.md](./DEPLOY_COOLIFY.md)**.

Ringkasan konfigurasi Coolify:
- **Build Pack**: `Dockerfile` (root repo).
- **Port**: dari env `PORT` (default `8000`).
- **Healthcheck**: `GET /api/health`.
- **Database**: MariaDB melalui `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD` (atau `DATABASE_URL`).
- **Volume Persisten (Wajib untuk Verval)**: Mount volume permanen ke direktori `VERVAL_STORAGE_DIR` (mis. `/srv/verval`) agar berkas foto ber-watermark tetap aman saat container redeploy.
- **Env Wajib Verval**: `VERVAL_REF_SECRET` (64 hex acak — **jangan diubah** setelah data Verval berjalan karena menjadi kunci referensi stabil `dtsen_ref`), `VERVAL_STORAGE_DIR=/srv/verval`, `VERVAL_GPS_MAX_AKURASI_M=30`.
- **Base URL Frontend**: Kosongkan `REACT_APP_BACKEND_URL` saat build produksi karena frontend & API dilayani satu origin oleh Uvicorn.

---

## 10. Catatan untuk AI Agent Berikutnya

1. **Jangan tulis SQL mentah** di router jika bisa memakai `db.<collection>` (`mariadb_store.py`), dan ingat store ini **tidak** mendukung operator `$or`.
2. **Menambah / mengubah peran**: sinkronkan di backend (`server.py`, `scope.py`, `verval_config.py`, `sosial.py`, `data_manage.py`) sekaligus di frontend (`constants/roles.js`, `constants/menu.js`, `features/data/roles.ts`, `components/SidebarLayout.js`, `App.js`).
3. **Menjaga integritas data DTSEN awal**: perubahan Verval yang disetujui Kecamatan hanya mengubah dokumen aktif setelah menyimpan baseline ke `households.dtsen_awal`, lalu wajib memanggil `refresh_agregat_for(db, kode_kelurahan, kode_kecamatan)` untuk menyinkronkan statistik.
4. **Keamanan & Pengujian**: selalu uji modul Verval memakai tes terisolasi `backend/tests/test_verval_v2.py` (`FakeDB`) atau server staging terpisah — **jangan** pernah menjalankan skrip tulis terhadap database produksi.
5. **Checklist verifikasi sebelum selesai**:
   - `GET /api/health` mengembalikan `{"status":"ok"}`.
   - `pytest -o required_plugins= -o addopts= tests/test_verval_v2.py -v` lulus tanpa error.
   - `frontend && yarn build` berhasil (`exit code 0`).
   - Variabel env baru tercatat di `.env.example`.

---

<div align="center">

**Badan Perencanaan Pembangunan Daerah (Bappeda) Kota Makassar**
Sistem PETA INKLUSI — Sumber data DTSEN & Verval Lapangan Kota Makassar

</div>
