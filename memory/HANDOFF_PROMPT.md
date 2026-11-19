# PROMPT LANJUTAN PENGEMBANGAN — SIDATA Bappeda Kota Makassar
> Salin seluruh isi blok di bawah ini ke chat workspace Emergent yang baru
> (setelah repo GitHub di-import ke workspace tersebut).

---

## PROMPT (copy-paste)

Lanjutkan pengembangan aplikasi **SIDATA — Sistem Informasi Data Terpadu Bappeda Kota
Makassar** dari kondisi terakhir di repository ini. **JANGAN membuat ulang dari nol** dan
**jangan mengubah desain/UI yang sudah ada** kecuali saya minta.

### 0. Baca dulu sebelum menulis kode
- `memory/PRD.md` — riwayat lengkap semua tahap yang sudah dikerjakan (paling penting).
- `test_result.md` — hasil pengujian tiap iterasi + protokol komunikasi testing agent.
- `memory/test_credentials.md` — akun uji tiap peran.
- `README.md` (lengkap) dan `DEPLOY_COOLIFY.md` (deploy ke VPS klien).

### 1. Arsitektur & tumpukan teknologi
- **Backend**: FastAPI (Python 3.11), semua route berprefix `/api`, jalan di `0.0.0.0:8001`
  via supervisor. Modul: `server.py` (auth, dashboard lama, AI analisa kategori, TTS, PDF,
  export Excel), `sosial.py` (DTSEN/disabilitas/stunting/RAD/geo/prioritas/audit),
  `rumah.py` (GIS polygon rumah), `ai_assistant.py` (AI data-aware), `etl_import.py`
  (ETL Excel → DB), `scoring.py` (skor kerentanan & prioritas), `auth.py` (JWT + seed user),
  `export_excel.py`, `report.py` (PDF reportlab), `terbilang.py` (angka → kata untuk TTS),
  `seed_data.py`, `mariadb_store.py`, `bsonlite.py`.
- **Database**: **MariaDB**, BUKAN MongoDB. `mariadb_store.py` adalah lapisan
  document-store bergaya Motor (`find_one`, `find().sort().skip().limit().to_list()`,
  `insert_one/many`, `update_one/many`, `find_one_and_update`, `delete_one/many`,
  `count_documents`, `create_index`). 1 koleksi = 1 tabel `doc_<nama>` dengan kolom
  `_id VARCHAR(64)` + `doc LONGTEXT` (JSON). Operator didukung:
  `$ne $exists $in $nin $gt $gte $lt $lte $regex $set $unset $inc`.
  Field yang sering difilter didaftarkan di `INDEXED_FIELDS` agar dapat generated column
  + index. **Selalu pakai UUID string sebagai `id`, jangan ObjectId.**
- **Frontend**: React 19 + CRACO + Tailwind + shadcn/ui + Recharts + Leaflet +
  Google Maps JS API (opsional) + `marked`. Halaman di `src/pages`, layout global
  `src/components/SidebarLayout.js`, klien HTTP `src/lib/api.js`.
- **AI**: `emergentintegrations.llm.chat.LlmChat` dengan `EMERGENT_LLM_KEY`.
  Model dipakai: **gpt-5.2 (default)** dan **claude-sonnet-4-6**, streaming SSE
  (`stream_message`, header `X-Accel-Buffering: no`). TTS: OpenAI `tts-1`.

### 2. Cara menghidupkan lingkungan (WAJIB, sering jadi sumber error)
MariaDB tidak tersedia default di container preview. Lakukan ini lebih dulu:
1. Pasang paket bila hilang: `apt-get update && apt-get install -y mariadb-server`.
2. Pastikan `PyMySQL` terpasang (dependensi aiomysql): sudah ada di `backend/requirements.txt`.
3. Daftarkan supervisor program dari berkas repo `deploy/supervisor-mariadb-dev.conf`
   → salin ke `/etc/supervisor/conf.d/mariadb-dev.conf`, lalu
   `supervisorctl reread && supervisorctl update && supervisorctl start mariadb-dev`.
   Script-nya: `scripts/start_mariadb_dev.sh` (datadir `/app/.data/mysql`,
   init idempotent `scripts/mariadb_init.sql`, DB `sidata`, user `sidata`/`sidata_dev_pw`).
4. `supervisorctl restart backend frontend`, lalu cek `curl localhost:8001/api/health`
   → harus `{"status":"ok","database":"mariadb"}`.
5. Jangan pernah menjalankan uvicorn/npm sendiri; pakai supervisor & yarn.
6. `backend/.env` butuh: `DB_HOST/DB_PORT/DB_DATABASE/DB_USERNAME/DB_PASSWORD`,
   `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `EMERGENT_LLM_KEY`,
   `CORS_ORIGINS`, `GOOGLE_MAPS_API_KEY` (boleh kosong).
   `frontend/.env` butuh `REACT_APP_BACKEND_URL`. **Jangan hardcode URL/port di kode.**

### 3. Kondisi data saat ini (PENTING)
- Seed otomatis saat backend start: 15 kecamatan, 153 kelurahan, 144 polygon rumah demo,
  4 akun peran (superadmin, petugas, operator, verifikator).
- Koleksi hasil ETL **masih kosong** bila berkas sumber belum diunggah:
  `households`, `household_members`, `village_stats`, `district_stats`, `geo_kelurahan`,
  `disability_region_stats`, `disability_opd_stats`, `stunting_subactivities`,
  `stunting_programs`, `stunting_activities`, `rad_items`, `rad_strategies`,
  `raw_imports`, `import_batches`, `data_quality_issues`, `opd`.
- Cara mengisi: taruh berkas Excel di `/app/data_upload/Bahan Website Ibu Kabid`
  (plus `/app/data_upload/stunting.xlsx` dan `/app/data_upload/rad_pd.xlsx`), lalu
  `cd /app/backend && python etl_import.py --reset`.
  Angka acuan hasil ETL sebelumnya: households 29.213, individu 106.863, villages 29,
  districts 2 (Makassar & Tallo), geo_kelurahan 154, stunting sub kegiatan 50
  (anggaran 2025 = 113.335.267.540; 2026 = 53.575.923.108), rad_items 77,
  disability_region 24 / opd 15, data_quality_issues 25.206.
- Semua endpoint sudah tahan kondisi data kosong (tidak 500) dan AI akan menyatakan
  "data belum tersedia" — jangan dianggap bug.

### 4. Fitur yang SUDAH selesai (jangan diulang)
- Auth JWT httpOnly cookie + seed user idempotent; peran: `superadmin`, `petugas`,
  `operator`, `verifikator`, `pimpinan`; alur verifikasi usulan data.
- Dashboard kota (KPI, tren kemiskinan/stunting, ATS, PMKS, disabilitas), auto-refresh.
- Dashboard Sosial DTSEN, Data Rumah Tangga (masking data pribadi), Prioritas Intervensi,
  Dashboard Disabilitas, RAD 2025-2030 + monitoring, Program & Anggaran Stunting.
- Peta Sosial choropleth kelurahan (154 polygon) & Peta Rumah level bangunan
  (Google Maps bila ada API key, fallback ESRI/OSM) + halaman Data Rumah/Bangunan.
- Halaman Administrasi: ringkasan impor, riwayat batch, isu kualitas data, audit log.
- Aksesibilitas disabilitas buta/disabilitas tuli: TTS OpenAI + modul `terbilang`, kontras tinggi,
  perbesar teks, kontrol kecepatan suara.
- Export Excel 2 sheet + laporan PDF berkop 2 logo; riwayat & pembandingan analisa AI.
- **AI Assistant data-aware** (`/ai-assistant`, `backend/ai_assistant.py`): jawaban
  dibangun dari DB, struktur wajib **Ringkasan Analisis, Data Pendukung, Faktor Utama,
  Program Terkait, Rekomendasi, Tingkat Prioritas** + panel Referensi Data Internal
  (event SSE pertama berisi `refs`), pemilih model gpt-5.2/claude-sonnet-4-6,
  multi-turn (`ai_chat_sessions`/`ai_chat_messages`), unduh PDF, tombol Bacakan.
- Migrasi MongoDB → MariaDB, Dockerfile multi-stage, siap deploy Coolify di VPS klien
  (domain `trirara.my.id`, GUI DB `db.trirara.my.id`).

### 5. Yang HARUS dikerjakan berikutnya (urut, uji tiap tahap sebelum lanjut)

**Tahap 3 — Halaman Import Data mandiri + Data Quality Center**
- Upload Excel/CSV lewat UI (chunked upload, progres detail), simpan berkas ke lokasi
  persisten, **preview** 20 baris pertama, **mapping kolom** (kolom berkas → field target,
  ingat template mapping per jenis dataset), **validasi** (tipe data, wajib isi, duplikat
  no_kk, kode wilayah tak dikenal), pilihan **insert / update (upsert)**, ringkasan hasil
  (total baris, masuk, duplikat, gagal) dan **riwayat impor** (bisa rollback per batch).
- Dataset yang wajib didukung: DTSEN rumah tangga, stunting/anggaran, RAD disabilitas,
  rekap disabilitas, data rumah/GeoJSON.
- Data Quality Center: penggabungan (merge) duplikat, antrean review manual
  (setujui/tolak/koreksi), **export laporan error** (Excel/CSV).
- Manfaatkan ulang logika `etl_import.py` (jangan tulis parser baru dari nol).

**Tahap 4 — Export Excel/PDF/CSV di semua dashboard mengikuti filter aktif**
- Setiap dashboard (Sosial, Rumah Tangga, Prioritas, Disabilitas, Stunting, RAD, Peta,
  Bantuan) punya tombol export yang mengirim filter yang sedang aktif ke backend.
- Excel via openpyxl (`export_excel.py`), PDF via reportlab (`report.py`, tetap pakai kop
  2 logo), CSV streaming. Data pribadi tetap tersamarkan sesuai peran pengunduh.

**Tahap 5 — RBAC lengkap + audit log + data masking**
- 7 peran: **Super Admin, Admin Bappeda, Admin OPD, Operator Kecamatan,
  Operator Kelurahan, Pimpinan, Viewer**.
- Pemetaan peran lama (akun lama HARUS tetap bisa login):
  `superadmin → Super Admin`, `verifikator → Admin Bappeda`,
  `petugas → Operator Kecamatan`, `operator → Operator Kelurahan`,
  `pimpinan → Pimpinan`; tambah peran baru **Admin OPD** & **Viewer**.
- Matriks izin per modul (lihat/tambah/ubah/hapus/verifikasi/impor/export/kelola user),
  pembatasan wilayah (kecamatan/kelurahan sendiri) dan pembatasan OPD untuk Admin OPD.
- Audit log seluruh aksi tulis (`audit_logs`: user, aksi, entitas, ref, detail, waktu)
  + halaman audit dengan filter & export.
- **Data masking** untuk peran non-sensitif: **No. KK, NIK, nama lengkap, alamat lengkap**.
  Yang boleh melihat data asli: Super Admin & Admin Bappeda (dan operator hanya untuk
  wilayahnya sendiri bila saya konfirmasi kemudian).

### 6. Aturan kerja yang wajib dipatuhi
- Bahasa antarmuka & pesan: **Bahasa Indonesia formal pemerintahan**. Balas chat ke saya
  dalam Bahasa Indonesia.
- Ikuti pola kode yang ada: modul backend memakai pola
  `build_router(db, current_user_dep, editor_dep, admin_dep)` lalu didaftarkan di
  `server.py` via `api_router.include_router(...)`.
- Semua route backend berprefix `/api`; frontend hanya memanggil lewat
  `REACT_APP_BACKEND_URL`; jangan sentuh nilai `.env` yang sudah ada.
- Tambahkan `data-testid` pada elemen interaktif baru (dipakai testing agent).
- Update `test_result.md` **sebelum** memanggil testing agent, uji **backend dulu**
  dengan `deep_testing_backend_v2`, dan **tanya saya dulu** sebelum pengujian frontend.
- Perbarui `memory/PRD.md` di akhir tiap tahap.
- Jangan pakai MongoDB/motor/pymongo lagi. Jangan pakai ObjectId. Jangan `git push` sendiri.
- Laporkan di akhir tiap tahap: **apa yang selesai, apa yang diuji, apa yang belum bisa
  diintegrasikan**.

### 7. Akun uji
| Peran | Email | Password |
|---|---|---|
| superadmin | admin@bappeda.makassarkota.go.id | <TEST_ADMIN_PASSWORD> |
| petugas (Tallo) | petugas.tallo@makassarkota.go.id | <TEST_PETUGAS_PASSWORD> |
| operator (Rappocini) | operator.rappocini@makassarkota.go.id | <TEST_OPERATOR_PASSWORD> |
| verifikator | verifikator@bappeda.makassarkota.go.id | <TEST_VERIFIKATOR_PASSWORD> |

**Mulai dari Tahap 3.** Sebelum menulis kode, hidupkan MariaDB seperti langkah bagian 2,
pastikan `/api/health` OK, lalu konfirmasikan rencana Tahap 3 ke saya (termasuk daftar
endpoint baru dan bentuk UI-nya) sebelum eksekusi.

---
