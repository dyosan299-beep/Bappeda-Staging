# PRD — SIDATA Bappeda Kota Makassar

## Problem Statement (asli)
Aplikasi untuk Badan Perencanaan (Bappeda) Kota Makassar berisi: dashboard real-time data dari matriks (kemiskinan, stunting, ATS/anak tidak sekolah, anak jalanan), fitur mapping wilayah, fitur AI untuk analisa program pemerintah kota yang tepat berdasarkan data tiap kategori, serta fitur untuk penyandang disabilitas buta dan disabilitas tuli. Sumber data dari kelurahan & kecamatan Kota Makassar.

## User Choices
- AI analisa: Claude Sonnet 4.6 (Emergent Universal Key)
- TTS disabilitas buta: OpenAI TTS (fallback Web Speech browser)
- Peta: Leaflet + OpenStreetMap (marker per kecamatan)
- Auth: JWT (admin Bappeda + petugas kecamatan/kelurahan) + akses publik read-only

## Arsitektur
- Backend: FastAPI + MongoDB (motor). Routes prefix `/api`. Auth JWT via httpOnly cookies.
- AI: SSE streaming via emergentintegrations LlmChat (anthropic/claude-sonnet-4-6).
- TTS: emergentintegrations OpenAITextToSpeech (tts-1), cached di MongoDB.
- Frontend: React + Tailwind + shadcn, Recharts, Leaflet (CDN), marked untuk render markdown.
- Data seed dari matriks Excel yang diupload (15 kecamatan, tren kemiskinan/stunting, disabilitas, ATS, PMKS).

## Personas
- Admin Bappeda: melihat & mengubah data seluruh kecamatan, jalankan analisa AI.
- Petugas kecamatan/kelurahan: input/update data wilayahnya sendiri.
- Masyarakat: akses publik dashboard, peta, data disabilitas, analisa AI (read-only).
- Penyandang disabilitas buta/disabilitas tuli: fitur aksesibilitas khusus.

## Core Requirements (static)
1. Dashboard real-time (auto-refresh) semua kategori.
2. Peta wilayah interaktif 15 kecamatan.
3. Analisa program AI per kategori & per wilayah.
4. Aksesibilitas: TTS + teks besar + kontras tinggi (disabilitas buta); visual/teks penuh (disabilitas tuli).
5. Input data oleh petugas; auth berbasis peran.

## Implemented (2026-06)
- [x] Auth JWT (admin + petugas seed idempotent), scoping peran/wilayah pada PUT.
- [x] Dashboard: 6 KPI, tren kemiskinan+target RPJMD, tren stunting, bar per-kecamatan, tren anak jalanan, pie ragam disabilitas, tabel PMKS. Auto-refresh 30s.
- [x] Peta Leaflet: marker circle per kategori (5 kategori), detail wilayah, ranking.
- [x] Analisa AI streaming (SSE) Claude Sonnet 4.6, render markdown progresif, tombol Bacakan, error+retry inline.
- [x] Aksesibilitas: mode Disabilitas Buta (TTS OpenAI, perbesar teks, kontras) & Disabilitas Tuli (visual), data disabilitas lengkap. Bilah aksesibilitas global.
- [x] Input data wilayah (admin semua; petugas hanya wilayahnya).
- [x] Landing page publik.
- Testing: 36/36 backend pass, semua flow frontend pass (iteration_2).

## Update (2026-08) — Perbaikan & Role Lanjutan
- [x] Bug suara: angka dibaca sebagai kata (modul terbilang) + kontrol kecepatan; jauh lebih jelas.
- [x] Bug peta: scroll-wheel zoom tidak lagi membajak scroll halaman (aktif setelah klik peta).
- [x] Ekspor Excel (2 sheet: kecamatan & kelurahan) + tombol di Dashboard & Rekap.
- [x] Kop laporan PDF pakai 2 logo resmi (Kota Makassar kiri + Bappeda kanan).
- [x] Lonceng notifikasi superadmin (pendaftaran menunggu) + badge verifikator (usulan data menunggu).
- [x] Peta choropleth: garis batas beda warna tiap kecamatan (15 warna) + isian per kategori.
- [x] Role diperluas: **superadmin, petugas, operator, verifikator, pimpinan** (admin lama → superadmin).
- [x] Superadmin: kelola semua user (buat/edit/hapus + reset password langsung).
- [x] Alur verifikasi data: input petugas/operator masuk antrean → verifikator setujui/tolak → baru diterapkan ke data resmi. Superadmin langsung diterapkan.
- Testing: backend 28/28 + 24/24 + bug fixes lolos; UI verifikasi/rekap/peta diverifikasi via preview.

## Peran & Wewenang (final)
- superadmin: akses penuh + manajemen user (edit, reset password).
- petugas/operator: input data wilayah sendiri → status menunggu verifikasi.
- verifikator: menyetujui/menolak usulan perubahan data.
- pimpinan: read-only + unduh laporan & analisa.
- publik: read-only dashboard/peta/analisa/aksesibilitas.

## Backlog (P1/P2)
- P2: Data granular per-kelurahan untuk semua kategori (sebagian masih distribusi dari total kota).
- P2: Polygon batas kelurahan (choropleth level kelurahan).
- P2: Migrasi ke lifespan handlers; logging insert AI.

## Update (2026-08) — Lanjutan
- [x] AI diganti ke model hemat **gemini-2.5-flash** via Emergent (Universal Key di-refresh karena budget key lama habis).
- [x] TTS lebih lambat & jelas: kontrol "Kecepatan Suara" (Normal/Pelan/Sangat Pelan) di bilah aksesibilitas; memperlambat audio OpenAI (playbackRate + preservesPitch) & Web Speech rate.
- [x] Riwayat Analisa AI: auto-simpan tiap analisa (id uuid, label, ringkasan); endpoint list/detail/delete; UI riwayat + buka detail + **Bandingkan 2 hasil** side-by-side + unduh PDF + hapus.
- [x] Role **Pimpinan**: dibuat admin lewat Kelola Petugas; akses read + unduh laporan/analisa; tidak bisa input data / kelola user (dibatasi backend 403 & nav).
- [x] Peta **Choropleth**: polygon 15 kecamatan (sumber cahyadsn/wilayah_boundaries kode 73.71) diwarnai gradasi sesuai nilai + legenda; klik wilayah zoom+detail.
- Testing: 17/17 backend pass (iteration lanjutan). Frontend diverifikasi via screenshot preview.


## Update (2026-09) — Migrasi ke MariaDB + Deployment Coolify (VPS sendiri)

Konteks: klien membeli VPS (`103.89.2.162`) dan ingin aplikasi berjalan mandiri
di Coolify dengan database **MariaDB**, bukan MongoDB.

- [x] **Migrasi MongoDB → MariaDB 11.8** tanpa mengubah logika bisnis.
  - Ditambahkan `backend/mariadb_store.py`: lapisan document-store bergaya Motor
    (`find_one`, `find().sort().to_list()`, `insert_one/many`, `update_one/many`,
    `find_one_and_update`, `delete_one/many`, `count_documents`, `create_index`)
    yang menulis ke MariaDB.
  - Skema: 1 collection = 1 tabel `doc_<nama>` (`_id VARCHAR(64)` + `doc LONGTEXT` JSON),
    filter diterjemahkan ke `JSON_VALUE(doc,'$.field')`, field yang sering
    difilter mendapat **generated column PERSISTENT + index** (`INDEXED_FIELDS`).
  - Operator didukung: `$ne $exists $in $nin $gt $gte $lt $lte $regex` dan
    `$set $unset $inc`.
  - Nilai biner (audio TTS) di-encode base64 di dalam JSON — round-trip diuji utuh.
  - Ditambahkan `backend/bsonlite.py` sebagai pengganti `bson.ObjectId`
    (24-hex, kompatibel dengan data & kode lama). Dependensi `motor`/`pymongo`
    tidak lagi dibutuhkan.
  - Driver: `aiomysql` dengan connection pool (`pool_recycle=280`).
- [x] Konfigurasi database format **standar Coolify**: `DB_HOST`, `DB_PORT`,
      `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`. Mendukung juga `DATABASE_URL`
      (opsional) — variabel `DB_*` eksplisit menimpa nilai dari URL.
- [x] **Port dari env `PORT`** (default 8000) + `HOST`, blok `__main__` uvicorn
      dengan `proxy_headers`.
- [x] **Satu kontainer menyajikan frontend + API**: `SPAStaticFiles` (fallback ke
      `index.html`) di-mount pada `/` setelah `api_router`, direktori dari
      `FRONTEND_BUILD_DIR`. `src/lib/api.js` kini fallback ke origin yang sama bila
      `REACT_APP_BACKEND_URL` kosong → tidak perlu env base URL publik.
- [x] Cookie auth dapat dikonfigurasi: `COOKIE_SECURE`, `COOKIE_SAMESITE`
      (satu origin → `lax`; lintas domain → `none`).
- [x] Endpoint baru **`GET /api/health`** (memeriksa MariaDB) untuk healthcheck
      Coolify/Docker + handler `DuplicateKeyError` → HTTP 400.
- [x] Script eksternal `assets.emergent.sh` dihapus dari `public/index.html`
      (aplikasi berdiri sendiri di domain klien).
- [x] **Dockerfile multi-stage** di root: `frontend-builder` (node:20-alpine,
      build React) → `backend-builder` (venv + toolchain kompilasi) →
      `production` (python:3.11-slim, non-root user `sidata`, tanpa compiler,
      HEALTHCHECK, `EXPOSE 8000`). Ditambah `backend/requirements-prod.txt` ramping.
- [x] `.dockerignore` (blokir `node_modules`, `.git`, semua `.env`, build artefak,
      berkas dev/test), `.env.example`, `docker-compose.yml` (uji lokal + MariaDB).
- [x] `deploy/phpmyadmin-compose.yaml` — GUI database phpMyAdmin untuk
      subdomain `db.trirara.my.id`; `deploy/production.env` (di-gitignore) berisi
      env produksi terisi untuk aplikasi & phpMyAdmin.
- [x] `README.md` ditulis ulang lengkap (overview, tech stack, struktur folder,
      data flow, coding conventions, referensi API, catatan untuk AI agent
      berikutnya) + `DEPLOY_COOLIFY.md` panduan langkah demi langkah.
- Domain produksi: aplikasi `https://trirara.my.id` (+`www`), GUI DB
  `https://db.trirara.my.id`.
- Testing: POC MariaDB lulus; **28/28** skenario alur tulis/baca lulus
  (`test_mariadb_flows.py`); testing agent: **backend 27/27 (100%)**,
  **frontend 98%**, migrasi MariaDB divalidasi end-to-end.


## Test Credentials
Lihat /app/memory/test_credentials.md

## Update (2026-09) — MODUL PETA baru: GIS level bangunan (polygon rumah)

Permintaan klien: modul PETA dibuat ulang menjadi dashboard GIS interaktif
(bukan mockup) dengan Google Maps JS API + polygon rumah dari GeoJSON.
Pilihan user: (1b) Google Maps API key BELUM ada → sementara basemap ESRI/OSM,
(2b/3b) data demo dulu + input manual, (4b) mengganti total modul Peta lama
(choropleth kecamatan Leaflet dihapus), (5b) sidebar seluruh aplikasi diganti.

- [x] Backend `backend/rumah.py`: koleksi `rumah` (id uuid, pemilik, jumlah_orang,
      no_kk, rt, rw, kelurahan, kecamatan, penghasilan, bantuan, tahun_bangunan,
      dinding, atap, lantai, sanitasi, air, status_lahan, jalan, keterangan, luas,
      kondisi, status hijau/kuning/merah, foto_url, lat, lng, geometry GeoJSON) +
      `map_config` (center/zoom/basemap dari DB).
      Endpoint: GET/PUT /api/map/config, GET /api/rumah/geojson (+filter kelurahan/rw/status,
      bbox), /api/rumah/filters, /api/rumah/stats, /api/rumah/legend, GET /api/rumah,
      GET/POST/PUT/DELETE /api/rumah{/id}, POST /api/rumah/import-geojson.
      Seed demo idempotent 144 polygon (Kaluku Bodoa 72, Rappokalling 48, Bunga Eja Beru 24).
      Warna polygon TIDAK di-hardcode: berasal dari field `status`.
- [x] Frontend TypeScript (tsconfig ditambahkan, jsconfig dihapus; typescript 5.9,
      @googlemaps/js-api-loader v2, @types/google.maps, @types/leaflet).
      `src/features/peta/`: types.ts, basemaps.ts, api.ts, googleEngine.ts (Google Maps
      roadmap/satellite/hybrid + ESRI ImageMapType), leafletEngine.ts (ESRI Imagery,
      ESRI Imagery+label, OSM) di balik antarmuka `MapEngine` yang sama, RumahPopup.tsx.
      Mesin dipilih otomatis: Google bila `GOOGLE_MAPS_API_KEY` (backend .env) terisi,
      selain itu ESRI/OSM. Halaman `src/pages/PetaGIS.tsx` (route /peta):
      polygon dari GeoJSON, klik polygon → highlight + popup putih (foto + semua field +
      tombol Tutup), legenda status yang bisa dipakai memfilter, pemilih basemap,
      zoom in/out, reset, fullscreen, filter Kelurahan/RW/Terapkan (portal ke header).
- [x] `src/pages/DataRumah.tsx` (route /peta-rumah): tabel + form tambah/edit/hapus
      (polygon dibuat otomatis dari lat/lng + luas) + impor GeoJSON (superadmin).
- [x] `src/pages/Bantuan.tsx` (route /bantuan): rekap penerima bantuan dari data rumah.
- [x] `components/SidebarLayout.js`: sidebar putih 240px (Dashboard, Peta, Peta Rumah,
      Data, Bantuan, Laporan + grup "Lainnya": Verifikasi, Analisa AI, Aksesibilitas,
      Kelola User) + header dengan slot filter; halaman /peta full-bleed.
      `components/Layout.js` & `pages/MapView.js` dihapus.
- [x] Lingkungan preview: MariaDB dijalankan supervisor (`/app/scripts/start_mariadb_dev.sh`)
      dengan datadir persisten `/app/.data/mysql` + init SQL idempotent; startup backend
      punya retry koneksi DB 10x.
- Testing: backend 44/44 lolos.

### Backlog modul peta
- Google Maps aktif setelah klien mengisi GOOGLE_MAPS_API_KEY (kode sudah siap).
- Impor data polygon rumah asli (GeoJSON/SHP) menggantikan data demo.
- Menggambar polygon langsung di peta (drawing tools) untuk input lapangan.

## Update (2026-09-09) — Pemulihan Lingkungan + AI Assistant Data-Aware

Konteks: storage container ter-reset. Datadir MariaDB `/app/.data/mysql` dan folder
berkas sumber `/app/data_upload/` (DTSEN, disabilitas, stunting, RAD) HILANG.

### Tahap 0 — Pemulihan lingkungan (selesai)
- [x] MariaDB 10.11 dipasang ulang; ditambahkan program supervisor `mariadb-dev`
      (`/etc/supervisor/conf.d/mariadb-dev.conf`) agar DB otomatis hidup saat container resume.
- [x] `PyMySQL>=1.1.1` ditambahkan ke `backend/requirements.txt` (dependensi aiomysql yang hilang).
- [x] Seed dasar kembali otomatis: 15 kecamatan, 153 kelurahan, 144 polygon rumah demo,
      4 akun peran (kredensial ditulis ke `/app/memory/test_credentials.md`).
- [ ] Data hasil ETL (households 29.213 dsb.) menunggu unggahan ulang berkas Excel dari klien.

### Tahap 1 — Pengujian backend modul sosial/stunting/RAD/geo/prioritas (selesai)
- [x] 77 skenario diuji; ditemukan 1 bug KRITIS: `/api/admin/import-summary`,
      `/admin/import-batches`, `/admin/data-quality`, `/admin/data-quality/summary`
      terbuka tanpa autentikasi → diperbaiki dengan `Depends(admin_dep)`.
- [x] Sisanya lolos: tidak ada 500 saat koleksi kosong, validasi parameter benar (422),
      masking data pribadi benar (petugas/operator/anonim = masked, superadmin/verifikator = penuh).

### Tahap 2 — AI Analytics data-aware (selesai)
- [x] `backend/ai_assistant.py`: konteks jawaban dibangun langsung dari DB
      (village_stats, district_stats, stunting_subactivities, rad_items, disability_*,
      rumah, opd, regions) sesuai kata kunci pertanyaan + fokus wilayah.
- [x] Struktur jawaban dipaksakan lewat system prompt: **Ringkasan Analisis, Data Pendukung,
      Faktor Utama, Program Terkait, Rekomendasi, Tingkat Prioritas** + larangan mengarang angka
      (wajib menyatakan "belum tersedia" bila koleksi kosong).
- [x] Referensi data internal dikirim sebagai event SSE pertama (`refs`: sumber, label,
      jumlah baris, endpoint) dan ditampilkan sebagai panel yang bisa dibuka.
- [x] Model dapat dipilih saat runtime: **gpt-5.2 (default)** dan **claude-sonnet-4-6**
      via EMERGENT_LLM_KEY (key di-refresh). Model tak dikenal fallback ke gpt-5.2.
- [x] Multi-turn: `ai_chat_sessions` + `ai_chat_messages`, riwayat 6 pesan terakhir
      disuntikkan ke prompt. Endpoint: GET /ai/models, /ai/suggestions, /ai/data-context (auth),
      POST /ai/ask (SSE), GET /ai/chat-sessions, GET/DELETE /ai/chat/{session_id}.
- [x] Frontend `src/pages/AIAssistant.js` (route `/ai-assistant`, menu "AI Assistant"):
      chat streaming, pemilih model, fokus wilayah, chip contoh pertanyaan, panel
      Referensi Data Internal, riwayat sesi (buka/hapus), unduh PDF, tombol Bacakan (TTS).
- Testing: backend 34/35 lolos (1 catatan minor: GET /ai/chat/{id-terhapus} balas 200 kosong).

### Sisa rencana (permintaan klien)
- Tahap 3: Halaman Import Data mandiri (upload Excel, preview, mapping kolom, validasi,
  insert/update, riwayat impor) + Data Quality Center (merge duplikat, review manual,
  export error report). Dataset: DTSEN, stunting, RAD, rekap disabilitas, rumah/GeoJSON.
- Tahap 4: Export Excel/PDF/CSV di semua dashboard mengikuti filter aktif.
- Tahap 5: RBAC 7 peran (Super Admin, Admin Bappeda, Admin OPD, Operator Kecamatan,
  Operator Kelurahan, Pimpinan, Viewer) + audit log + masking (No. KK, NIK, nama, alamat).
  Pemetaan peran lama: superadmin→Super Admin, verifikator→Admin Bappeda,
  petugas→Operator Kecamatan, operator→Operator Kelurahan, pimpinan→Pimpinan.

### Impor data ulang (2026-09-09) — data asli klien masuk kembali
Klien mengunggah 4 berkas (1 duplikat identik diarsipkan):
`Pilah DTSEN KEC TALLO.xlsx` (sheet TALLO + Kaluku Bodoa),
`DATA DISABILITAS_KEC.TALLO_Kec.MAKASSAR.xlsx`,
`PERMINTAAN DATA DISABILITAS DINKES SEPTEMBER 2026.xlsx`,
`Salinan MATRIKS_RAD_PD_OPD Dinas (4).xlsx`.
Berkas `untuk GIS_DTSEN KEC.TALLO_Kaluku Bodoa.xlsx` **identik (md5 sama)** dengan berkas
DTSEN Tallo → dipindah ke `/app/data_upload/_arsip` agar tidak menghasilkan duplikat palsu.

Hasil `python etl_import.py --reset`:
- geo_kelurahan 154 (dari GeoJSON yang ter-commit), dtsen_rows 22.155,
  households **19.106**, household_members 19.106, villages 15, districts 1 (**Tallo**),
  disability_region_stats 24, disability_opd_stats 15, rad_items **77**, rad_strategies 25,
  village_stats 15, district_stats 1, import_batches 6, data_quality_issues 3.052
  (3.049 duplikat KK).
- KPI: individu 71.139, PBI Nasional 13.169, PBI Pemda 4.690, desil 1-2 6.545 (34,26%),
  rumah rentan 1.703 (8,91%), sanitasi tidak layak 1.248, air rentan 73, hunian rentan 473,
  skor kerentanan rata-rata 31,32. Prioritas #1 **Kaluku Bodoa** (skor 30,73).
- **Berkas STUNTING belum dikirim** → koleksi `stunting_*` tetap kosong (tercatat sebagai
  issue `file_tidak_ada`); dashboard Stunting & bagian "Program OPD Relevan → Stunting"
  di halaman Prioritas masih nol. Menunggu `stunting.xlsx` / matriks konvergensi stunting.
- Cakupan wilayah baru **hanya Kecamatan Tallo** (sebelumnya 2 kecamatan/29.213 KK).
  Perlu berkas DTSEN kecamatan lain untuk cakupan penuh 15 kecamatan.
- Testing: **backend 122/122 lolos** (angka acuan cocok semua; masking, filter, paginasi,
  ranking, RAD monitoring + audit log, data quality, regresi, AI Assistant data-aware).

### Tambahan data (2026-09-09, batch 2) — 4 kelurahan Kec. Makassar
Klien mengunggah `BARA-BARAY.xlsx` (985 baris), `BARA-BARAYA SELATAN.xlsx` (1.095),
`BARA-BARAYA TIMUR.xlsx` (814), `BARA-BARAYA UTARA.xlsx` (865) — semuanya sheet DTSEN
28 kolom, Kec. MAKASSAR. Berkas `~$MARADEKAYA SELATAN.xlsx` adalah lock file Excel
(bukan data) → tidak dipakai; berkas MARADEKAYA SELATAN aslinya belum dikirim.

Hasil `etl_import.py --reset` kumulatif:
- dtsen_rows 25.914 → households **22.865**, individu **84.841**,
  villages **19**, districts **2** (Tallo 19.106 KK / 15 kelurahan; Makassar 3.759 KK / 4 kelurahan).
- PBI Nasional 15.737, PBI Pemda 5.483, desil 1-2 7.719 (33,76%), rumah rentan 1.870 (8,18%),
  sanitasi tidak layak 1.333, air rentan 83, hunian rentan 560, skor kerentanan rata-rata 31,21.
- geo_kelurahan 154 dengan **19 kelurahan sudah punya data** (semua nama cocok dengan GeoJSON,
  tidak ada issue `kode_wilayah_tidak_sesuai`).
- data_quality_issues tetap 3.052 (3.049 duplikat KK dari sheet DTSEN Tallo).
- Prioritas #1 masih Kaluku Bodoa (30,73); Kec. Makassar rata-rata skor 30,61.
- Diverifikasi via screenshot: Dashboard Sosial (22.865 KK, 2 kecamatan, 19 kelurahan) dan
  Peta Sosial (legenda "19 dari 154 kelurahan memiliki data DTSEN").

### Tambahan data (2026-09-09, batch 3) — 5 kelurahan Kec. Makassar
`BARANA.xlsx` (862), `LARIANG BANGI.xlsx` (225), `MACCINI GUSUNG.xlsx` (1.504),
`MACCINI PARANG.xlsx` (1.023), `MACCINI.xlsx` (748). Semua sheet DTSEN 28 kolom, Kec. MAKASSAR.
Nama "LARIANGBANGI" (tanpa spasi) tetap cocok dengan GeoJSON via `norm_name` -> tidak ada
issue `kode_wilayah_tidak_sesuai`.

Kumulatif setelah `etl_import.py --reset`:
- dtsen_rows 30.276 -> households **27.227**, individu **100.081**,
  villages **24**, districts 2 (Tallo 19.106 KK / 15 kelurahan; Makassar **8.121 KK / 9 kelurahan**).
- PBI Nasional 18.834, PBI Pemda 6.315, desil 1-2 9.078 (33,34%), rumah rentan 2.268 (8,33%),
  sanitasi tidak layak 1.616, air rentan 94, hunian rentan 680, skor kerentanan rata-rata 31,09.
- geo_kelurahan 154, **24 kelurahan sudah punya data** (min skor 16,51 = Lariangbangi,
  max 30,73 = Kaluku Bodoa). data_quality_issues tetap 3.052.

### Tambahan data (2026-09-09, batch 4) — 5 kelurahan Kec. Makassar + PERBAIKAN BUG ETL
Berkas: `MARADEKAY UTARAA.xlsx` (288), `MARADEKAYA.xlsx` (458),
`MARADEKAYAA SELATANN.xlsx` (117), `MARICAYA.xlsx` (251), `MARICAYAA BARU.xlsx` (872)
— disimpan dengan nama rapi (MARADEKAYA UTARA / MARADEKAYA SELATAN / MARICAYA BARU).

**BUG DITEMUKAN & DIPERBAIKI di `backend/etl_import.py`:**
- Pola pencarian berkas RAD `DATA_DIR.glob("*RAD*.xlsx")` ikut menangkap berkas DTSEN
  "MA**RAD**EKAYA*.xlsx" → `pd.read_excel(sheet_name="2025-2030 (baru)")` melempar
  `ValueError: Worksheet named '2025-2030 (baru)' not found` dan **seluruh ETL gagal**.
- Perbaikan: (1) `_is_rad_filename()` mencocokkan "rad" sebagai kata utuh (regex
  `(?:^|[^a-z])rad(?:[^a-z]|$)`) atau "matriks_rad"; (2) `rad_candidates()` memilih
  berkas yang benar-benar punya sheet mengandung "2025-2030" (nama sheet dideteksi
  dinamis, tidak lagi hardcode); (3) pembacaan stunting & RAD dibungkus try/except
  dengan pencatatan isu; (4) `run()` mengisolasi tiap tahap impor sehingga kegagalan
  satu berkas dicatat sebagai isu `tahap_gagal` tanpa menggagalkan seluruh proses.

Kumulatif setelah `etl_import.py --reset` (sudah setara dataset asli sebelum reset container):
- dtsen_rows 32.262 → households **29.213**, individu **106.863**,
  villages **29**, districts 2 (Tallo 19.106 KK / 15 kelurahan; Makassar **10.107 KK / 14 kelurahan**).
- PBI Nasional 20.239, PBI Pemda 6.679, desil 1-2 9.694 (33,18%), rumah rentan 2.493 (8,53%),
  sanitasi tidak layak 1.808, air rentan 99, hunian rentan 713, skor kerentanan rata-rata 31,00.
- RAD kembali normal: 77 item, 7 sasaran strategis, 18 kebijakan, 28 program, 33 kegiatan.
- geo_kelurahan 154 dengan **29 kelurahan berdata** (skor 14,06–30,73).
- data_quality_issues 3.052 (3.049 duplikat KK). Stunting masih kosong (berkas belum dikirim).

## Update (2026-09-09) — MODUL PETA DASAR (ekstraksi PETA_DASAR.gdb) + pemulihan lingkungan

Klien mengunggah `PETA_DASAR.gdb.zip` (isi sebenarnya **RAR** berisi File Geodatabase ESRI,
CRS UTM 50S / EPSG:32750, sumber *Data Penetapan Peta Dasar Kota Makassar Edisi 2021, BIG*).
Permintaan: "extract file di atas dan sinkronkan pada aplikasi saat ini".
Pilihan user: (1a) semua 11 layer baru, (2a) simpan sebagai GeoJSON gzip di `backend/assets`,
(3a) panel layer di 2 halaman peta + halaman statistik `/peta-dasar`, (4a) toponimi dikaitkan
ke analisa (rekap per wilayah + dapat dikutip AI Assistant).

### Tahap 0 — pemulihan lingkungan (container ter-reset lagi)
- [x] MariaDB dipasang ulang; **paket .deb kini di-cache ke `/app/.data/deb`** (16 MB) sehingga
      `scripts/start_mariadb_dev.sh` dapat memasang ulang sendiri saat container resume.
- [x] `gdal-bin` + `libarchive-tools` (bsdtar) dipasang untuk ekstraksi/konversi
      (`7z`/`unrar` gagal pada RAR5; **bsdtar berhasil**).
- [x] Data hasil ETL DTSEN (households dll.) HILANG lagi karena `/app/data_upload` ikut ter-reset
      → koleksi sosial kosong (bukan bug). Menunggu unggahan ulang berkas Excel klien.

### Tahap 1 — konversi GDB → aset GeoJSON
- [x] Skrip baru `scripts/gdb_to_geojson.py` (ogr2ogr → WGS84, presisi 6 desimal, kolom Shape_*
      dibuang, atribut dinormalisasi ke huruf kecil, panjang/luas dihitung sendiri
      (haversine & shoelace), titik toponimi ditandai kelurahan/kecamatan via point-in-polygon).
- [x] Keluaran `backend/assets/geo/basemap/` (total ± 3,5 MB gzip): `manifest.json` (gaya,
      legenda kategori, min_zoom, bbox_required), `stats.json`, dan 13 berkas `<id>.geojson.gz`:
      batas_kelurahan 154, batas_administrasi_garis 440, jalan_utama 980,
      jalan_lingkungan 25.965, badan_jalan 86, jembatan 96, perairan_area 19,
      perairan_garis 81, garis_pantai 53, garis_pantai_rencana 11, kontur 1.817,
      penutup_lahan 2.993 (23 kelas), toponimi 1.571.
- [x] `backend/assets/geo/kelurahan_makassar.geojson` diperbarui dari sumber resmi
      (154 kelurahan + `LUAS_M2`/`LUAS_HA` + `SUMBER`). Total luas 17.758,32 ha (177,6 km²).
- [x] Angka kunci: panjang jalan 2.499,17 km (utama 341,08 km), sungai/kanal 187,3 km,
      garis pantai 72,64 km, batas administrasi 375,63 km, perairan 2.468,65 ha,
      penutup lahan terluas Permukiman 6.637 ha lalu Tempat Kegiatan 3.349 ha.

### Tahap 2 — backend `backend/peta_dasar.py`
- [x] Endpoint publik read-only: `GET /api/peta-dasar/layers`, `/stats`, `/ringkasan`,
      `/layer/{id}?bbox=&kategori=&limit=`, `/fasilitas` (search/klasifikasi/jenis/kelurahan/
      kecamatan/paginasi), `/fasilitas/rekap?level=kelurahan|kecamatan`.
      Cache LRU 4 layer + indeks bbox per fitur; layer padat (`jalan_lingkungan`) WAJIB bbox (422).
- [x] Seed idempotent saat startup: `peta_dasar_layers` (13), `fasilitas_umum` (1.571 titik
      lengkap kelurahan/kecamatan), `geo_kelurahan` (154 — kini terisi tanpa perlu ETL Excel,
      sehingga Peta Sosial tetap tampil).
- [x] `INDEXED_FIELDS` ditambah untuk 2 koleksi baru; router didaftarkan di `server.py`.
- [x] AI Assistant: topik kata kunci `peta_dasar` + blok konteks (panjang jalan per fungsi,
      perairan, penutup lahan terluas, rekap fasilitas umum per klasifikasi & wilayah fokus)
      dengan referensi `peta_dasar_layers` / `fasilitas_umum`.

### Tahap 3 — frontend
- [x] `features/peta/`: `basemapTypes.ts`, `basemapApi.ts`, `useBasemapLayers.ts` (lazy-load,
      cache, muat ulang otomatis mengikuti bbox untuk layer padat, aturan min_zoom),
      `leafletOverlay.ts` (pane khusus zIndex 380 → tetap di bawah polygon rumah/choropleth,
      tooltip + popup atribut), `BasemapLayerPanel.tsx` (checkbox bergrup + legenda kategori
      + jumlah fitur tampil + tombol nonaktifkan).
- [x] `MapEngine` diperluas: `setOverlay`, `removeOverlay`, `getBounds` — diimplementasikan di
      `leafletEngine.ts` dan `googleEngine.ts` (google.maps.Data + InfoWindow).
- [x] Panel layer dipasang di **/peta (Peta Rumah)** dan **/peta-sosial**; halaman baru
      **/peta-dasar** ("Peta Dasar & Fasilitas"): 6 KPI, grafik panjang jalan per fungsi,
      penutup lahan terluas, pie fasilitas per klasifikasi, tabel daftar layer, rekap fasilitas
      per kecamatan/kelurahan, dan pencarian fasilitas umum (filter + paginasi).
      Menu sidebar baru pada grup "Peta / GIS".
- Testing: **backend 92/92 lolos** (testing agent); UI diverifikasi via screenshot
  (halaman /peta-dasar, layer jalan utama di Peta Sosial, penutup lahan + jalan lingkungan
  bbox di Peta Rumah).

### Catatan
- Berkas sumber `.gdb` disimpan di `/app/data_upload/peta_dasar/` (folder ini **gitignored**);
  aset hasil konversi ikut ter-commit sehingga aplikasi tidak bergantung pada berkas sumber.
- Menjalankan ulang konversi: `python scripts/gdb_to_geojson.py --gdb <path .gdb>` (butuh `gdal-bin`).

## Sesi 2026-09-27 — Import ulang repo ke workspace baru
- Repo `gunturg131197-design/Bappeda` (HEAD `29c6f16`) disalin ke /app; `.env` preview dipertahankan.
- MariaDB 10.11 dipasang + supervisor `mariadb-dev` aktif; cache .deb di `/app/.data/deb`.
- `backend/.env` ditambah DB_*, JWT_SECRET, ADMIN_*, EMERGENT_LLM_KEY, COOKIE_*, GOOGLE_MAPS_API_KEY (kosong).
- `frontend/jsconfig.json` (sisa template) dihapus karena bentrok dengan `tsconfig.json`.
- Status: /api/health OK (mariadb), login 4 akun OK, dashboard tampil.
- Data ETL (households, stunting, RAD, disabilitas) KOSONG: berkas Excel di /app/data_upload tidak ada di repo.
- Import Wizard: penyimpanan berkas unggahan dipindah dari disk (`IMPORT_UPLOAD_DIR`) ke MariaDB
  (koleksi `import_files`, potongan base64 2 MB; parsing via BytesIO). Batas `IMPORT_MAX_UPLOAD_MB`
  (default 100). Uji: `python tests/test_import_db_storage.py` → 19/19 lulus.
- 27 Sep 2026: Data produksi (trirara.my.id, MariaDB 11.8) disalin SATU ARAH ke preview via
  `scripts/sync_from_production.py` (env `PROD_DATABASE_URL`, baca saja): 40 tabel doc_*, 61.757 baris
  (households 29.213, individu 106.863, stunting sub 49, RAD 77, rumah 288, users 6). Backup preview
  sebelum sinkron: `/app/.data/import/backup_preview_*.sql.gz`. Kredensial produksi TIDAK disimpan.
  Catatan: seed_admin mereset password admin lokal ke ADMIN_PASSWORD (.env) — hanya di preview.

## Update 2026-09 — Integrasi Frontend PETA INKLUSI (SELESAI)
- Routing App.js: publik (/, /publik, /publik/peta-sosial, /publik/peta-kemiskinan, /flow-sistem, /tentang),
  NGO (/ngo/inquiry, /ngo/inquiry/baru, /ngo/inquiry/:id, /ngo/inquiry/:id/revisi, /ngo/peta-sosial, /ngo/peta-kemiskinan, /ngo/statistik),
  internal (/peta-kemiskinan [menggantikan /peta], /data-stunting, /data-ats, /program, /role-permission, /audit-log, dst).
- /dashboard sesuai peran: Admin -> AdminOverview, NGO -> /ngo/inquiry, lainnya -> dashboard lama.
- Route internal dijaga ProtectedRoute (NGO diarahkan ke /ngo/inquiry).
- Sidebar & Login di-rebrand PETA INKLUSI; Login punya tab Masuk / Daftar NGO / Daftar Petugas (/login?mode=ngo&next=...).
- "Peta Rumah (Bangunan)" -> "Peta Kemiskinan" (tab Bangunan sebagai indikator pendukung).
- Kelola User menampilkan organisasi NGO; admin menyetujui NGO pending.
- Testing: iteration_6.json — backend 33/33, frontend 100%.

## Update 2026-09 — Fitur lanjutan (SELESAI, iteration_7: backend 25/25; UI diverifikasi manual)
- ATS per kelurahan: template Excel (GET /api/inklusi/ats/template), pratinjau+validasi (POST /api/inklusi/ats/preview),
  simpan (POST /api/inklusi/ats/commit mode ganti_tahun|tambah), riwayat & rollback (/api/inklusi/ats/batches). Peta ATS kelurahan memakai tahun terbaru.
  Koleksi: ats_kelurahan, ats_import_batches. UI: /data-ats.
- Notifikasi email NGO (backend/notifier.py): tiap PATCH status inquiry -> email_outbox. SMTP via env SMTP_HOST/PORT/USER/PASSWORD/FROM
  (+SMTP_SECURITY, APP_PUBLIC_URL). BELUM DIKONFIGURASI (user kirim kredensial nanti) -> status "belum_terkirim", dikirim otomatis saat startup setelah .env diisi.
  UI admin: /notifikasi-email (kirim ulang, email tes).
- Laporan PDF 1 halaman per kelurahan (reportlab): GET /api/inklusi/laporan/kelurahan (login saja, termasuk NGO). UI: /laporan-wilayah + tombol di peta internal.
- Galeri Program Selesai publik: GET /api/public/program-selesai (nama NGO disamarkan, nama program tampil). UI: /publik & landing.
- Data uji dibersihkan (inquiry TEST, batch ATS TEST, outbox).

## Update 2026-09 — Cerita Dampak Program (SELESAI, iteration_8: backend 95% [hanya kendala alat uji], frontend 100%)
- backend/inklusi_cerita.py: NGO pemilik mengisi cerita (ringkasan, realisasi penerima, maks 3 testimoni, persetujuan wajib) saat inquiry MONITORING/COMPLETED;
  maks 5 foto (diperkecil 1600px, EXIF/GPS dihapus, disimpan di MariaDB `story_files`). Status: menunggu_review -> admin publikasikan/tolak (+email NGO).
  Publik (/api/public/program-selesai & /api/public/cerita-foto/{id}) hanya jika dipublikasikan & inquiry COMPLETED.
- UI: panel di detail inquiry (form NGO / review admin), galeri publik (foto sampul, kutipan, dialog "Baca cerita dampak"), daftar cerita di /program.
- Data uji dibersihkan.

## Update 2026-10-07 — Redesign UI Aksesibilitas & tombol aksi publik (SELESAI, iteration_16: frontend 100%)
- Token tombol bersama `features/a11y/ui.ts`; SpeakMini (ikon/pill), ChartA11y, EasyRead, MapDataTable, dialog Bantuan/Transkrip, header publik, hero Beranda, kartu /publik, kontrol peta InklusiMap dirapikan.
- Tema & fitur tetap; data-testid lama dipertahankan (baru: a11y-help-done, a11y-transcript-close, <chart>-a11y-block).
- Berikutnya: ringkasan mingguan pimpinan → export ikut filter → Import Data & Data Quality Center → salin data DTSEN produksi.
- 2026-10-07: Suara TTS lebih jelas (gpt-4o-mini-tts + instruksi lafal Indonesia, fallback tts-1-hd, voice alloy) dan tempo bawaan Normal; `kecepatan` dikirim ke /api/tts.
- 2026-10-07: Manual Book (PDF+DOCX, 61 hlm), Presentasi (15 slide) & SOP Penginputan Data (17 slide) PPTX dibuat via scripts/manual/.


## Ringkasan Mingguan Pimpinan (Selesai)
- Backend `backend/ringkasan_mingguan.py`: build_summary (per kecamatan Stunting/ATS/Disabilitas + data baru 7 hari, inquiry NGO baru & perubahan status), render_email (HTML Teal/Navy), kirim per penerima via notifier.queue_email (jenis `ringkasan_mingguan`).
- Endpoint: POST /api/cron/ringkasan-mingguan (Bearer WEBHOOK_CRON_SECRET, idempoten per run_id & per minggu ISO), GET /api/inklusi/ringkasan-mingguan/preview, POST /kirim, GET /riwayat. Koleksi `weekly_summary_runs`.
- Jadwal `.emergent/crons.yml`: "0 6 * * 1" Asia/Makassar (Senin 06.00 WITA).
- Penerima: user aktif role pimpinan/superadmin/admin/admin_bappeda + WEEKLY_SUMMARY_EXTRA_RECIPIENTS.
- Frontend `/ringkasan-mingguan` (RingkasanMingguan.tsx), menu "Ringkasan Mingguan".
- SMTP kantor BELUM diisi -> email masuk antrean `belum_terkirim`, terkirim otomatis setelah SMTP_* diisi & backend restart.

## Sesi 2026-10-14 — Import ulang repo ke workspace baru (bappeda-live-demo)
- Repo `gunturg131197-design/Bappeda` HEAD `7c33da8` (Merge PR #6 ringkasan-mingguan-a11y-dokumentasi) disalin ke /app; `.env` preview dipertahankan (hanya ditambah baris).
- MariaDB 10.11 dipasang, supervisor `mariadb-dev` aktif, cache .deb (42 paket) di `/app/.data/deb`.
- `backend/requirements.txt`: pin `emergentintegrations` 0.2.0 -> 0.2.2 (0.2.0 konflik dengan litellm 1.80.0 di image baru).
- backend/.env ditambah DB_*, JWT_SECRET, ADMIN_*, EMERGENT_LLM_KEY, COOKIE_*, SEED_DEMO_USERS + DEMO_*_PASSWORD, WEBHOOK_CRON_SECRET.
- Status: /api/health OK (mariadb), 4 akun login OK, landing & dashboard tampil.
- Data ETL/produksi (households, individu, stunting, RAD) KOSONG di preview ini (butuh berkas Excel atau PROD_DATABASE_URL untuk scripts/sync_from_production.py).
- Smoke test iteration_18: backend 10/10, frontend semua alur utama lulus.
- Perbaikan kecil: duplikat key React di datalist pencarian InklusiMap (nama kecamatan = nama kelurahan, kini di-dedupe) dan tabel MapDataTable (components.tsx). Peringatan Recharts width(-1) saat render awal dibiarkan (tidak berdampak).

## Sesi 2026-10-16 — Import repo (HEAD b5eb51c) + Audit & Optimasi Responsif
- Repo HEAD `b5eb51c` (fix health MariaDB) disalin ke /app; `.env` platform dipertahankan (ditambah DB_*, JWT_SECRET, ADMIN_*, DEMO_*, VERVAL_REF_SECRET, VERVAL_STORAGE_DIR=/app/.data/verval, WEBHOOK_CRON_SECRET).
- MariaDB via supervisor `mariadb-dev`; `frontend/jsconfig.json` sisa template dihapus (bentrok dengan tsconfig.json repo).
- AI memakai Hostlinku (HOSTLINKU_API_KEY belum diisi -> fitur AI nonaktif, lainnya normal).
- Responsif (mobile-first, breakpoint Tailwind sm/md/lg/xl/2xl + min-[1920px]):
  - index.css: fondasi responsif (`.grid > * {min-width:0}`, box-sizing, 100dvh, input max-width, popup Leaflet <= viewport, target sentuh kontrol peta, `.table-scroll`).
  - SidebarLayout: drawer < 1024px (Esc menutup, aria-expanded/controls, invisible saat tertutup), statis >= 1024px, konten max 1680px di >= 1920px, ruang bawah untuk FAB aksesibilitas.
  - Komponen bersama: Panel/PageHeader (min-w-0, judul clamp, aksi wrap), Tabs (scroll horizontal), Dialog (max-h 100dvh, margin di HP, tombol tutup 40px), Sheet (lebar min(85vw,24rem)).
  - Peta: InklusiMap panel filter dapat diciutkan di HP, zoom ke kanan-atas, ResizeObserver -> invalidateSize; PetaGIS filter ke header hanya >= 1024px, legenda & panel layer dapat diciutkan di HP, engine.resize(); KoordinatGIS tinggi clamp.
  - Halaman: FlowSistem, Prioritas, Administrasi, AdminOverview, Rekap, Stunting, MasterKode, DataRumah, RumahTangga, RAD, InklusiPages, InklusiExtra, CeritaDampak, PetaKemiskinan, header publik/BrandLogo.
- Alat audit: `tests/responsive_audit.py` (+ `responsive_audit_snippet.py`, `responsive_shots.py`), dijalankan dgn venv playwright terpisah & Chrome sistem. Jangan jalankan paralel (rate-limit backend 429).
- Hasil uji: audit otomatis 43 rute x 15 viewport (320x568 .. 2560x1440, termasuk landscape 844x390 & 1180x820) = 0 overflow; zoom 200% (640x400) = 0; mode teks sangat besar (a11y-xlarge) 360 & 390 = 0 setelah perbaikan. testing_agent iteration_21: frontend 95% (temuan minor diverifikasi manual: backdrop OK, tab ringkasan OK, add-user OK, PetaGIS toggle OK); Flow Sistem: navigasi sticky di HP.
- Visual edit Login: judul & paragraf panel kiri diganti teks baru (Penguatan Perencanaan Pembangunan Inklusi ...).

## Update (2026-10) — Restrukturisasi Role Verval & GeoTag + Scoping Wilayah
- [x] **Petugas** (lapangan) ditentukan per **Kelurahan + RW (+RT)**; HANYA dapat dibuat oleh **Operator kecamatan** (superadmin ditolak 403). Fitur petugas: Dashboard Publik + Verval & GeoTag (foto + koordinat). API dibatasi `PETUGAS_ALLOWED_PREFIXES`.
- [x] **Operator**: Kelola Petugas kecamatannya (`/kelola-petugas`, API `/api/admin/users*` dep `user_manager`), hanya melihat data kecamatannya.
- [x] **Verifikator**: ter-scope kecamatan (`wilayah`; "Kota Makassar" = seluruh kota) untuk verifikasi data, households, hasil Verval.
- [x] **Scoping global** (`backend/scope.py`): middleware ASGI memaksa query `kecamatan`/`kode_kecamatan`/`wilayah` pada GET /api/* untuk operator/verifikator/petugas; `/regions`, `/verifikasi*`, `/verval/*` difilter eksplisit. Lencana wilayah di header.
- [x] **Verval**: `OPERATOR_ROLES=(operator_rt_rw, petugas)`; penugasan sintetis dari profil petugas (`dasar_akses=wilayah_petugas`). Hasil Verval dapat dilihat **superadmin & pimpinan** (`HASIL_ROLES`), keputusan hanya verifikator/admin_bappeda/superadmin.
- [x] **Foto + koordinat**: GPS perangkat saat foto; fallback **EXIF GPS** (dibaca sebelum re-encode). Bila record belum punya GPS, koordinat foto otomatis menjadi GPS record. Koordinat tampil di UI foto (petugas & review).
- [x] **Sinkron ke semua peta**: `/api/verval/peta` (titik + foto + geojson) dipakai InklusiMap (Peta Sosial/Kemiskinan), PetaGIS/Peta Bangunan (overlay engine Leaflet/Google, toggle di legenda), KoordinatGIS. Event `verval:peta-berubah` memuat ulang layer.
- Testing: tests/role_flow.sh, tests/verval_flow.py (alur petugas→foto→kirim→review, scoping verifikator/pimpinan).
