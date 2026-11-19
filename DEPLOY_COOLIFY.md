# Panduan Deploy ke Coolify — SIDATA Bappeda Kota Makassar

Domain yang dipakai:

| Layanan | Domain |
|---|---|
| Aplikasi | `https://trirara.my.id` (+ `https://www.trirara.my.id`) |
| GUI database (phpMyAdmin) | `https://db.trirara.my.id` |

VPS: `103.89.2.162` · Database: MariaDB 11.8 (resource Coolify)

---

## 0. Ringkasan arsitektur

```
                    Cloudflare DNS (A record, DNS only)
                                  │
                                  ▼
                        VPS 103.89.2.162
                    ┌───────────────────────┐
                    │   Coolify Proxy (Traefik)  │  <- HTTPS / Let's Encrypt
                    └──────────┬────────┬───────┘
         trirara.my.id │        │ db.trirara.my.id
                       ▼        ▼
         ┌───────────────────┐  ┌────────────┐
         │  Aplikasi SIDATA  │  │ phpMyAdmin │
         │  (Dockerfile)     │  │ (Compose)  │
         │  React + FastAPI  │  └─────┬──────┘
         └────────┬─────────┘        │
                  └────────┬────────────┘
                           ▼
                 ┌──────────────────────┐
                 │  MariaDB 11.8         │
                 │  host internal:       │
                 │  56kbk4g5d8cv3hpo...  │  port 3306
                 │  publik: :7890        │
                 └──────────────────────┘
```

Aplikasi berjalan **satu kontainer** yang menyajikan React **dan** API `/api`
sekaligus — jadi tidak ada masalah CORS dan cukup satu domain.

---

## 1. DNS (Cloudflare)

Anda sudah punya 2 record. Tambahkan **satu lagi** untuk phpMyAdmin:

| Name | Type | Content | Proxy status | TTL |
|---|---|---|---|---|
| `trirara.my.id` | A | `103.89.2.162` | DNS only | Auto | (sudah ada) |
| `www` | A | `103.89.2.162` | DNS only | Auto | (sudah ada) |
| **`db`** | **A** | **`103.89.2.162`** | **DNS only** | **Auto** | **← tambahkan** |

> Biarkan **DNS only** (awan abu-abu) sampai HTTPS Let's Encrypt di Coolify
> berhasil diterbitkan. Setelah itu boleh diaktifkan proxy (awan oranye) bila mau.
> Kalau proxy Cloudflare dinyalakan terlalu awal, penerbitan sertifikat bisa gagal.

---

## 2. Deploy Aplikasi

### 2.1 Buat resource

1. Coolify → pilih Project → **+ New** → **Public/Private Repository**
2. Pilih repo GitHub: `gunturg131197-design/Bappeda`, branch `main`
3. **Build Pack**: pilih **Dockerfile**
4. **Dockerfile Location**: `/Dockerfile`
5. **Base Directory**: `/`
6. **Port Exposes**: `8000`

### 2.2 Domain

**Domains** → isi:

```
https://trirara.my.id
```

Aktifkan juga:
- **Generate SSL certificate**: ON
- **Redirect www to non-www** (atau tambahkan `https://www.trirara.my.id` sebagai domain kedua)

### 2.3 Environment Variables

**Environment Variables** → aktifkan *Developer view* → paste seluruh blok berikut:

> **Nilai asli semua kredensial ada di `deploy/production.env`** (berkas itu
> sengaja **tidak** di-commit ke GitHub). Ganti setiap `<...>` di dokumen ini
> dengan nilai dari berkas tersebut, atau salin langsung dari sana.

```env
DB_HOST=103.89.2.162
DB_PORT=7890
DB_DATABASE=default
DB_USERNAME=mariadb
DB_PASSWORD=<DB_PASSWORD>

PORT=8000
HOST=0.0.0.0
WEB_CONCURRENCY=2
TZ=Asia/Makassar
FRONTEND_BUILD_DIR=/srv/frontend/build
IMPORT_UPLOAD_DIR=/srv/data_upload/_uploads   # tidak dipakai lagi oleh Import Wizard (berkas disimpan di MariaDB)
IMPORT_MAX_UPLOAD_MB=100                    # opsional, batas ukuran unggahan Import Wizard

JWT_SECRET=<JWT_SECRET>

ADMIN_EMAIL=admin@bappeda.makassarkota.go.id
ADMIN_PASSWORD=<ADMIN_PASSWORD>

COOKIE_SECURE=true
COOKIE_SAMESITE=lax
CORS_ORIGINS=https://trirara.my.id,https://www.trirara.my.id

EMERGENT_LLM_KEY=<EMERGENT_LLM_KEY>
```

#### Kenapa TIDAK ada `DATABASE_URL`?

Aplikasi ini membaca variabel **terpisah** (`DB_HOST`, `DB_PORT`, `DB_DATABASE`,
`DB_USERNAME`, `DB_PASSWORD`) sesuai format standar Coolify \u2014 jadi `DATABASE_URL`
**tidak wajib**.

Namun sejak versi ini, `DATABASE_URL` **juga didukung** kalau Anda lebih suka satu
baris. Boleh dipakai sebagai pengganti 5 variabel di atas:

```env
DATABASE_URL=mysql://mariadb:<DB_PASSWORD>@103.89.2.162:7890/default
```

Aturannya: variabel `DB_*` yang **tetap diisi** akan **menimpa** nilai dari
`DATABASE_URL` (berguna untuk menambal satu bagian saja, mis. hanya `DB_HOST`).
Skema yang diterima: `mysql://`, `mariadb://`, `mysql+aiomysql://`, `mysql+pymysql://`.

#### Kenapa TIDAK ada env \"public base URL\"?

Karena frontend project ini adalah **React (CRA + craco), bukan Next.js** \u2014 jadi
tidak ada `NEXT_PUBLIC_*`. Padanannya adalah `REACT_APP_BACKEND_URL`, dan variabel
itu bersifat **build-time** (nilainya dibakukan ke dalam bundel JavaScript saat
`yarn build`), bukan runtime. Menaruhnya di Environment Variables Coolify tidak
akan berefek apa pun.

Di Dockerfile, `REACT_APP_BACKEND_URL` sengaja dibiarkan **kosong**. Akibatnya
`src/lib/api.js` menghasilkan base URL relatif `/api`, sehingga browser memanggil
`https://trirara.my.id/api/...` \u2014 domain yang sama dengan halamannya. Ini yang
membuat tidak perlu CORS, tidak perlu domain API terpisah, dan tidak perlu env
base URL.

> Baru perlu diisi bila suatu saat API dipisah ke domain lain. Caranya lewat
> **build argument** (bukan environment variable):
> Coolify \u2192 resource \u2192 **Build** \u2192 Build Arguments \u2192
> `REACT_APP_BACKEND_URL=https://api.trirara.my.id`, lalu set
> `COOKIE_SAMESITE=none` dan tambahkan domain frontend ke `CORS_ORIGINS`.

#### Jika aplikasi gagal konek ke database

Log menampilkan `Can't connect to MySQL server`. Coba hostname internal Coolify
(syarat: app berada di project yang sama dengan MariaDB):

```env
DB_HOST=56kbk4g5d8cv3hpoknojoa4g
DB_PORT=3306
```

### 2.4 Healthcheck

**Health Checks** → aktifkan:

| Kolom | Nilai |
|---|---|
| Path | `/api/health` |
| Port | `8000` |
| Interval | `30` |
| Timeout | `10` |
| Retries | `5` |
| Start period | `45` |

(Dockerfile juga sudah memuat `HEALTHCHECK` bawaan.)

### 2.5 Deploy

Klik **Deploy**. Build pertama memakan waktu ~5–10 menit
(build React + install dependensi Python).

Indikator berhasil di log:

```
INFO:bappeda.mariadb:Terhubung ke MariaDB ...
INFO:bappeda:Seeded 15 kecamatan
INFO:bappeda:Seeded 153 kelurahan
INFO:bappeda:Menyajikan frontend statis dari /srv/frontend/build
INFO:     Application startup complete.
```

### 2.6 Verifikasi

```bash
curl https://trirara.my.id/api/health
# {"status":"ok","database":"mariadb"}

curl -s https://trirara.my.id/api/stats/overview | head -c 200
```

Lalu buka `https://trirara.my.id` di browser dan login sebagai superadmin.

---

## 3. Deploy phpMyAdmin (GUI database)

### 3.1 Buat resource

Anda sudah punya resource **PhpMyAdmin** (Service) di project `production`.
Cukup isi environment variable-nya di langkah 3.2 dan set domain-nya.

Bila ingin membuat baru lewat Docker Compose:

1. Coolify → project → **+ New** → **Docker Compose**
2. Paste isi berkas **`deploy/phpmyadmin-compose.yaml`** dari repo ini
3. **Domains** → `https://db.trirara.my.id` → Generate SSL: ON

### 3.2 Environment Variables phpMyAdmin

```env
PMA_HOST=103.89.2.162
PMA_PORT=7890
PMA_ABSOLUTE_URI=https://db.trirara.my.id/
PMA_ARBITRARY=0
PMA_BLOWFISH_SECRET=<PMA_BLOWFISH_SECRET>
PMA_HIDE_PHP_VERSION=1
UPLOAD_LIMIT=512M
MEMORY_LIMIT=1G
MAX_EXECUTION_TIME=900
TZ=Asia/Makassar
```

> Ini memakai **IP publik VPS** (`103.89.2.162:7890`) — cara paling pasti berhasil
> dan sudah diuji. Bila ingin lebih cepat & tidak lewat internet, ganti ke
> hostname internal `PMA_HOST=56kbk4g5d8cv3hpoknojoa4g` dengan `PMA_PORT=3306`
> (syarat: resource berada di project yang sama dengan MariaDB).

### 3.3 Login phpMyAdmin

| Kolom | Nilai |
|---|---|
| Server | `103.89.2.162:7890` |
| Username | `mariadb` |
| Password | `<DB_PASSWORD>` |
| Database | `default` |

Tabel yang akan Anda lihat di database `default`:

| Tabel | Isi | Perkiraan baris |
|---|---|---|
| `doc_users` | Akun pengguna | 4+ |
| `doc_regions` | Kecamatan | 15 |
| `doc_kelurahan` | Kelurahan | 153 |
| `doc_data_changes` | Antrean verifikasi | bertambah |
| `doc_ai_analyses` | Riwayat analisa AI | bertambah |
| `doc_tts_cache` | Cache audio TTS | bertambah |

Data sesungguhnya ada di kolom `doc` (JSON). Contoh query:

```sql
-- Lihat data kecamatan dengan rapi
SELECT
  JSON_VALUE(doc,'$.nama')                  AS kecamatan,
  JSON_VALUE(doc,'$.kemiskinan_ekstrim_kk') AS kemiskinan_kk,
  JSON_VALUE(doc,'$.stunting_anak')         AS stunting,
  JSON_VALUE(doc,'$.ats')                   AS ats,
  JSON_VALUE(doc,'$.disabilitas')           AS disabilitas
FROM doc_regions
ORDER BY CAST(JSON_VALUE(doc,'$.kemiskinan_ekstrim_kk') AS UNSIGNED) DESC;

-- Lihat daftar pengguna
SELECT
  JSON_VALUE(doc,'$.email')   AS email,
  JSON_VALUE(doc,'$.name')    AS nama,
  JSON_VALUE(doc,'$.role')    AS peran,
  JSON_VALUE(doc,'$.wilayah') AS wilayah,
  JSON_VALUE(doc,'$.status')  AS status
FROM doc_users;

-- Antrean verifikasi yang masih menunggu
SELECT
  JSON_VALUE(doc,'$.target_nama')  AS wilayah,
  JSON_VALUE(doc,'$.submitted_by') AS pengusul,
  JSON_VALUE(doc,'$.submitted_at') AS waktu,
  JSON_EXTRACT(doc,'$.changes')    AS perubahan
FROM doc_data_changes
WHERE JSON_VALUE(doc,'$.status') = 'pending';
```

### 3.4 Keamanan phpMyAdmin

phpMyAdmin terbuka di internet adalah target favorit peretas. Minimal lakukan:

- `PMA_ARBITRARY=0` (sudah default di YAML — hanya boleh ke server yang ditentukan)
- Ganti `PMA_BLOWFISH_SECRET` dengan 32 karakter acak milik Anda
- Matikan resource phpMyAdmin saat tidak dipakai (Coolify → **Stop**)
- Pertimbangkan menutup port publik MariaDB `7890` setelah aplikasi memakai host internal

---

## 4. Cadangan (backup) database

```bash
# Ekspor
mysqldump -h 103.89.2.162 -P 7890 -u mariadb -p default > sidata-$(date +%F).sql

# Impor
mysql -h 103.89.2.162 -P 7890 -u mariadb -p default < sidata-2026-09-08.sql
```

Atau lewat Coolify → resource MariaDB → **Backups** → jadwalkan backup otomatis.

---

## 5. Setelah deploy berhasil

1. **Login** ke `https://trirara.my.id/login` sebagai superadmin.
2. **Segera ganti kata sandi** akun contoh (`petugas.tallo@...`,
   `operator.rappocini@...`, `verifikator@...`) lewat menu **Kelola Petugas**,
   atau hapus akun yang tidak dipakai.
3. Periksa **saldo Emergent Universal Key** bila fitur Analisa AI / suara
   tidak berjalan (Profile → Manage plan → Universal Key → Add Balance).
4. Aktifkan **backup otomatis** MariaDB di Coolify.

---

## 6. Pemecahan masalah

| Gejala | Penyebab & solusi |
|---|---|
| Build gagal saat `yarn install` | Jaringan VPS lambat. Coba deploy ulang; `--network-timeout 600000` sudah dipasang. |
| Build gagal: *out of memory* | VPS RAM kecil. Tambah swap, atau turunkan `NODE_OPTIONS=--max-old-space-size` di Dockerfile. |
| `Can't connect to MySQL server` | Ganti `DB_HOST=103.89.2.162` & `DB_PORT=7890`. |
| Halaman putih, konsol 404 aset | Build React gagal. Cek log tahap `frontend-builder`. |
| Login sukses tapi langsung logout | Cookie tidak tersimpan. Pastikan `COOKIE_SECURE=true` **dan** situs diakses lewat HTTPS. Bila API beda domain, pakai `COOKIE_SAMESITE=none`. |
| 502 Bad Gateway | Kontainer belum siap / healthcheck gagal. Cek `PORT=8000` dan **Port Exposes** = `8000`. |
| `ModuleNotFoundError: No module named 'pandas'` | Dependensi produksi kurang. `pandas`, `numpy`, `openpyxl`, `xlrd` **wajib** ada di `backend/requirements-prod.txt` (dipakai `import_wizard.py` / ETL Excel). Sudah diperbaiki; pastikan deploy memakai commit terbaru dan bukan cache image lama (**Redeploy → Force rebuild without cache**). |
| Impor Excel gagal *permission denied* | Folder unggahan tidak writable oleh user non-root `sidata`. Pastikan `IMPORT_UPLOAD_DIR=/srv/data_upload/_uploads`; bila memakai persistent storage Coolify, mount volume ke `/srv/data_upload` lalu set owner ke UID `10001`. |
| Analisa AI error | `EMERGENT_LLM_KEY` kosong atau saldo habis. |
| Tombol suara tidak berbunyi | Suara memakai mesin TTS perangkat. Pastikan data suara **Bahasa Indonesia** terpasang (Android: Setelan → Bahasa & masukan → Output teks-ke-ucapan; iPad: Setelan → Aksesibilitas → Konten yang Diucapkan → Suara), volume tidak nol, dan mode senyap mati. Panel Aksesibilitas → tab Tampilan menampilkan nama suara yang terpakai. |
| Sertifikat SSL gagal | Matikan proxy Cloudflare (jadikan **DNS only**), deploy ulang, baru nyalakan lagi. |

Lihat log: Coolify → resource → tab **Logs**.


## Catatan: penyimpanan berkas Import Wizard
Sejak 27 Sep 2026 berkas Excel/CSV yang diunggah lewat Import Wizard disimpan di MariaDB
(tabel `doc_import_files`, dipotong per 2 MB base64) — bukan di folder `/srv/data_upload/_uploads`.
Volume `/srv/data_upload` tidak lagi wajib untuk Import Wizard, dan berkas ikut ter-backup
bersama database. Batas ukuran unggahan diatur lewat `IMPORT_MAX_UPLOAD_MB` (default 100).
Pastikan `max_allowed_packet` MariaDB >= 16M (nilai default).

## 7. Pembaruan PETA INKLUSI — env var & keamanan (wajib dibaca sebelum redeploy)

**Env var baru/opsional** (lengkapnya lihat `.env.example`):

| Variabel | Wajib | Keterangan |
|---|---|---|
| `ADMIN_PASSWORD` | **Ya** | Tidak ada lagi password default di kode. Bila kosong, akun superadmin tidak dibuat/diubah. |
| `JWT_SECRET` | **Ya** | `openssl rand -hex 48` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_SECURITY` | Tidak | Notifikasi email status pengajuan NGO. Bila kosong, email hanya diantrikan. |
| `APP_PUBLIC_URL` | Tidak | Tautan di email, mis. `https://trirara.my.id` |
| `GOOGLE_MAPS_API_KEY` | Tidak | Kunci **Maps JavaScript API**, disajikan ke frontend lewat `GET /api/map/config`. Bila kosong, peta memakai Leaflet/ESRI/OSM. Pembatasan kunci: lihat §7.1. |
| `SEED_DEMO_USERS` | Tidak | **Biarkan kosong/false di produksi.** Hanya untuk preview. |

**Tabel baru** (dibuat otomatis & aman saat start, tidak mengubah tabel lama): `doc_program_stories`, `doc_story_files`, serta tabel ATS kelurahan & antrean email. Tidak ada migrasi destruktif.

**Checklist keamanan pasca-deploy:**
1. Password default lama (`admin@…`, `petugas.tallo@…`, `operator.rappocini@…`, `verifikator@…`) pernah tercantum di repo/halaman login. **Ganti password semua akun tersebut** (atau nonaktifkan akun demo) melalui menu Kelola Petugas, dan set `ADMIN_PASSWORD` baru di Coolify.
2. Pastikan `COOKIE_SECURE=true` dan `CORS_ORIGINS` berisi domain produksi (bukan `*`).
3. Jalankan `python backend/uji_keamanan.py --base https://domain-anda` untuk memeriksa header,
   CSRF, rate limit login, proteksi data pribadi, dan CORS. Pemetaan kepatuhan UU PDP,
   PP 71/2019, dan ISO 27001 ada di [`KEAMANAN-DATA.md`](KEAMANAN-DATA.md).

### 7.1 Kunci Google Maps

Kunci disimpan **hanya di backend** (`GOOGLE_MAPS_API_KEY`) lalu disajikan ke browser lewat
`GET /api/map/config`. Frontend memakai Google Maps bila kunci ada, dan otomatis kembali ke
basemap ESRI/OSM bila kunci ditolak untuk domain tersebut.

**API yang perlu diaktifkan di Google Cloud Console** (project yang sama dengan kunci):

| API | Wajib | Dipakai untuk |
|---|---|---|
| **Maps JavaScript API** | Ya | `/peta-kemiskinan` tab Bangunan/Rumah (`googleEngine.ts`) |
| **Maps Tiles API** | Tidak | Layer Google di peta Leaflet (Peta Sosial/Kemiskinan tab Wilayah) |
| Maps Static API / Geocoding API | Tidak | Tidak dipakai aplikasi ini |

Pastikan **billing aktif** pada project — Maps JavaScript API menolak permintaan tanpa
penagihan, meski kuota gratis bulanan tersedia.

**Pembatasan kunci (wajib):**

1. *Application restrictions* → **HTTP referrers**, isi:
   - `https://<domain-produksi>/*`
   - `http://localhost:3000/*` dan `http://127.0.0.1:3000/*` (untuk pengembangan)
2. *API restrictions* → **Restrict key**, centang hanya API pada tabel di atas.

Bila kunci tidak mengizinkan domain yang sedang dibuka, Google mengirim
`RefererNotAllowedMapError`; aplikasi menampilkan catatan “Google Maps tidak dapat dimuat
untuk alamat ini” dan tetap menampilkan peta dengan basemap alternatif (tidak blank).

**Status kunci per 25 Oktober 2026:** kunci yang dipasang pada `backend/.env` terverifikasi
**berfungsi dari `file://` (tanpa referrer)**. Artinya pembatasan HTTP referrer **belum ada** —
siapa pun yang memegang kunci dapat memakainya dan tagihannya masuk ke project Anda.
Sebelum aplikasi dipublikasikan:

1. Buka <https://console.cloud.google.com/apis/credentials> → pilih kunci tersebut.
2. Terapkan pembatasan pada bagian *Application restrictions* dan *API restrictions* di atas.
3. **Rotasi kunci** (Create new key → hapus yang lama) karena kunci lama sudah tersebar
   di riwayat percakapan dan berkas lokal.
4. Perbarui `GOOGLE_MAPS_API_KEY` di `backend/.env` (dev) dan di environment Coolify (produksi).

Untuk compose lokal, variabel ini sudah diteruskan ke container aplikasi
(`docker-compose.yml` → `GOOGLE_MAPS_API_KEY`). Deploy Coolify memakai Dockerfile, jadi isi
variabelnya di menu **Environment Variables** layanan aplikasi.

Kunci browser selalu dapat dilihat publik; **jangan** memakai kunci ini untuk API sisi server
(Geocoding/Places/Directions dari backend) tanpa pembatasan IP terpisah.
3. Backup database sebelum redeploy (lihat bagian 4).
