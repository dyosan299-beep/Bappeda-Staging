# SIDATA Bappeda Kota Makassar

> **Sistem Intelijen Data Sosial** — platform perencanaan berbasis data untuk
> Badan Perencanaan Pembangunan Daerah (Bappeda) Kota Makassar.

[![Stack](https://img.shields.io/badge/stack-React%20%2B%20FastAPI%20%2B%20MariaDB-DC2626)](#2-tech-stack)
[![Deploy](https://img.shields.io/badge/deploy-Coolify%20%2F%20Dockerfile-2563EB)](./DEPLOY_COOLIFY.md)

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

SIDATA adalah satu pintu bagi Bappeda Kota Makassar untuk **memantau, memverifikasi,
dan menganalisa data sosial** di 15 kecamatan dan 153 kelurahan.

### Masalah yang diselesaikan

Data kemiskinan, stunting, anak tidak sekolah (ATS), anak jalanan, dan disabilitas
sebelumnya tersebar dalam banyak berkas Excel dari tiap kelurahan/kecamatan.
Akibatnya perencanaan program lambat, angkanya tidak sinkron, dan tidak ada jejak
siapa mengubah apa.

### Fungsi utama

| Fitur | Penjelasan |
|---|---|
| **Dashboard real-time** | 6 kartu KPI, tren kemiskinan vs target RPJMD, tren stunting (EPPGBM & SSGI), grafik per kecamatan, tren anak jalanan, komposisi ragam disabilitas, tabel PMKS. Auto-refresh 30 detik. |
| **Peta wilayah (choropleth)** | Polygon 15 kecamatan diwarnai gradasi sesuai nilai kategori terpilih, garis batas berbeda warna, klik wilayah untuk zoom + detail, panel peringkat. |
| **Analisa AI** | Rekomendasi program pemerintah per kategori & wilayah, dihasilkan Gemini 2.5 Flash dari data nyata di database, dikirim streaming (SSE) sehingga muncul progresif. |
| **Riwayat & perbandingan analisa** | Setiap analisa disimpan otomatis; bisa dibuka kembali, dibandingkan 2 hasil berdampingan, diunduh PDF, atau dihapus. |
| **Aksesibilitas** | Mode **disabilitas buta** (suara perangkat lewat Web Speech API + kontrol kecepatan, perbesar teks, kontras tinggi) dan mode **disabilitas tuli** (penyajian visual/teks penuh). |
| **Input data berbasis peran** | Petugas/operator hanya boleh mengubah wilayahnya sendiri. |
| **Alur verifikasi** | Perubahan dari petugas/operator masuk antrean → verifikator menyetujui/menolak → baru diterapkan ke data resmi. Superadmin menerapkan langsung. |
| **Kelola pengguna** | Superadmin membuat/mengedit/menghapus akun, mengatur peran, mengubah status, dan me-reset kata sandi. |
| **Laporan** | Ekspor PDF berkop resmi (2 logo: Kota Makassar & Bappeda) dan ekspor Excel 2 sheet (kecamatan & kelurahan). |
| **Akses publik** | Masyarakat dapat membaca dashboard, peta, data disabilitas, dan analisa AI tanpa login. |

### Kategori data yang dikelola

`kemiskinan_ekstrim_kk` · `stunting_anak` · `anak_jalanan` · `ats` · `disabilitas` · `kemiskinan_persen`

---

## 2. Tech Stack

### Frontend

| Komponen | Pilihan | Catatan |
|---|---|---|
| Framework | **React 19** | Create React App di-override dengan **craco** (`craco.config.js`) |
| Routing | **react-router-dom 7** | Semua rute didefinisikan di `src/App.js` |
| Styling | **Tailwind CSS 3** | Token warna & tema di `src/index.css` + `tailwind.config.js` |
| Komponen UI | **shadcn/ui** (46 komponen) | Ada di `src/components/ui/`, dibangun di atas Radix UI |
| Ikon | **lucide-react** | |
| Grafik | **Recharts 3** | Dashboard & rekap |
| Peta | **Leaflet 1.9** + **Google Maps JavaScript API** | Leaflet via CDN di `public/index.html`; Google Maps dipakai otomatis bila `GOOGLE_MAPS_API_KEY` terisi di backend |
| HTTP client | **axios** | Satu instance terpusat di `src/lib/api.js` (`withCredentials: true`) |
| Markdown | **marked** | Merender hasil analisa AI |
| Animasi | **framer-motion** | |
| Notifikasi | **sonner** + `hooks/use-toast.js` | |
| Alias import | `@/` → `src/` | Diatur di `craco.config.js` & `jsconfig.json` |

### Backend

| Komponen | Pilihan | Catatan |
|---|---|---|
| Framework | **FastAPI 0.110** | Semua endpoint di bawah `APIRouter(prefix="/api")` |
| Server | **Uvicorn** | Port dari env `PORT` (default 8000) |
| Validasi | **Pydantic v2** | Model input di bagian atas `server.py` |
| Laporan | **reportlab** (PDF), **openpyxl** (Excel) | |
| AI | **emergentintegrations** → `LlmChat` | Model `gemini/gemini-2.5-flash`, streaming SSE |
| TTS | **Web Speech API** di perangkat (frontend) | `speechSynthesis`, suara `id-ID` bawaan perangkat |
| TTS server (opsional) | **emergentintegrations** → `OpenAITextToSpeech` | Model `tts-1`, di-cache di database; **nonaktif**, aktifkan dengan `REACT_APP_TTS_SERVER=1` |

### Database

| Komponen | Pilihan |
|---|---|
| DBMS | **MariaDB 11.8** (MySQL-compatible) |
| Driver | **aiomysql** (async, connection pool) |
| Pola penyimpanan | **Document store di atas SQL** — lihat penjelasan di bawah |

> **Penting — cara data disimpan.**
> Project ini semula memakai MongoDB. Saat migrasi ke MariaDB, dibuat lapisan
> `backend/mariadb_store.py` yang menyediakan API bergaya Motor/PyMongo
> (`find_one`, `insert_one`, `update_one`, `find().sort().to_list()`, dst.)
> namun menulis ke MariaDB.
>
> Setiap "collection" menjadi satu tabel `doc_<nama>` dengan bentuk:
>
> ```sql
> CREATE TABLE `doc_users` (
>   `_id` VARCHAR(64) NOT NULL PRIMARY KEY,   -- 24 karakter hex, mirip ObjectId
>   `doc` LONGTEXT NOT NULL,                  -- dokumen JSON
>   `k_email` VARCHAR(255) AS (JSON_VALUE(`doc`,'$.email')) PERSISTENT,
>   UNIQUE KEY `idx_email` (`k_email`)
> ) ENGINE=InnoDB;
> ```
>
> Filter diterjemahkan ke `JSON_VALUE(doc,'$.field') = ?`, dan field yang sering
> dicari mendapat **generated column PERSISTENT + index** (didaftarkan di
> `INDEXED_FIELDS` pada `mariadb_store.py`). Ini membuat migrasi tidak menyentuh
> logika bisnis sama sekali, sekaligus tetap memakai MariaDB asli.

**Tabel yang dipakai**

| Tabel | Isi |
|---|---|
| `doc_users` | Akun pengguna (email unik, hash bcrypt, peran, wilayah, status) |
| `doc_regions` | 15 kecamatan beserta angka tiap kategori |
| `doc_kelurahan` | 153 kelurahan beserta angka tiap kategori |
| `doc_data_changes` | Antrean usulan perubahan (pending/approved/rejected) |
| `doc_ai_analyses` | Riwayat hasil analisa AI |
| `doc_tts_cache` | Cache audio TTS (biner disimpan base64 di dalam JSON) |

### Auth

| Aspek | Implementasi |
|---|---|
| Metode | **JWT HS256** (`pyjwt`), rahasia dari env `JWT_SECRET` |
| Penyimpanan token | **httpOnly cookie** — `access_token` (12 jam) & `refresh_token` (7 hari) |
| Fallback | Header `Authorization: Bearer <token>` juga diterima (memudahkan pengujian) |
| Hash kata sandi | **bcrypt** |
| Atribut cookie | Diatur env `COOKIE_SECURE` & `COOKIE_SAMESITE` (satu origin → `lax`; lintas domain → `none`) |
| Seeding | `auth.seed_admin()` bersifat **idempotent**, dijalankan tiap startup |

### Storage

Project ini **tidak memakai object storage eksternal** (tidak ada S3/GCS).

| Jenis berkas | Lokasi |
|---|---|
| Logo & gambar laporan | `backend/assets/` — dibaca langsung oleh `report.py` saat membuat PDF |
| GeoJSON batas kecamatan | `frontend/src/constants/makassar_geo.json` — di-bundle ke build |
| PDF & Excel | **Dihasilkan on-the-fly** ke memori (`io.BytesIO`) lalu dikirim sebagai `StreamingResponse`. Tidak ditulis ke disk. |
| Audio TTS | Di-cache sebagai base64 di tabel `doc_tts_cache` |

> Konsekuensi: container **stateless** — aman di-restart/scale, tidak butuh volume
> persisten. Satu-satunya state ada di MariaDB.

---

## 3. Folder Structure

```
/
├── Dockerfile                  # Multi-stage: build React -> venv Python -> image produksi ramping
├── .dockerignore               # Cegah node_modules/.git/.env masuk build context
├── .env.example                # Daftar semua environment variable (template kosong)
├── docker-compose.yml          # Uji coba lokal: app + MariaDB sekali jalan
├── DEPLOY_COOLIFY.md           # Panduan deploy langkah demi langkah ke Coolify
├── README.md                   # Dokumen ini
│
├── deploy/                     # Berkas bantu deployment
│   ├── phpmyadmin-compose.yaml #   GUI database (phpMyAdmin) untuk Coolify
│   └── production.env          #   Env produksi terisi (DIABAIKAN GIT - berisi rahasia)
│
├── backend/                    # ============ API FastAPI ============
│   ├── server.py               # Titik masuk: model Pydantic, seluruh endpoint /api,
│   │                           #   middleware CORS, startup/shutdown, penyajian SPA
│   ├── mariadb_store.py        # Lapisan data MariaDB bergaya Motor (baca bagian Tech Stack)
│   ├── bsonlite.py             # Pengganti ringan bson.ObjectId (agar bebas dependensi MongoDB)
│   ├── auth.py                 # Hash kata sandi, terbitkan/verifikasi JWT, seed akun idempotent
│   ├── seed_data.py            # Data awal: 15 kecamatan, 153 kelurahan, tren, meta kategori
│   ├── report.py               # Pembuat PDF (kop resmi 2 logo, tabel, ringkasan)
│   ├── export_excel.py         # Pembuat Excel 2 sheet (kecamatan & kelurahan)
│   ├── terbilang.py            # Ubah angka -> kata Indonesia (agar TTS jelas)
│   ├── assets/                 # Logo Kota Makassar & Bappeda untuk kop laporan
│   ├── tests/                  # Pytest backend
│   ├── requirements.txt        # Dependensi lengkap (termasuk tooling dev)
│   ├── requirements-prod.txt   # Dependensi ramping khusus image Docker
│   └── .env                    # Rahasia lokal (TIDAK di-commit)
│
├── frontend/                   # ============ Aplikasi React ============
│   ├── craco.config.js         # Override CRA: alias @/, watch options, plugin
│   ├── tailwind.config.js      # Tema, warna, font, animasi
│   ├── components.json         # Konfigurasi generator shadcn/ui
│   ├── public/index.html       # Shell HTML, Google Fonts, CDN Leaflet
│   └── src/
│       ├── index.js            # Bootstrap React
│       ├── App.js              # Definisi seluruh rute + provider global
│       ├── App.css, index.css  # Style global & token tema Tailwind
│       │
│       ├── pages/              # Satu berkas = satu halaman/rute
│       │   ├── Landing.js      #   / .............. halaman publik
│       │   ├── Login.js        #   /login ......... masuk petugas
│       │   ├── Dashboard.js    #   /dashboard ..... KPI & grafik
│       │   ├── MapView.js      #   /peta .......... choropleth Leaflet
│       │   ├── AIAnalysis.js   #   /analisa-ai .... analisa AI streaming
│       │   ├── Disabilitas.js  #   /aksesibilitas . fitur disabilitas buta/tuli
│       │   ├── DataEntry.js    #   /input-data .... input petugas/operator
│       │   ├── Verifikasi.js   #   /verifikasi .... antrean persetujuan
│       │   ├── Rekap.js        #   /rekap ......... tabel & unduhan laporan
│       │   └── KelolaPetugas.js#   /kelola-petugas  manajemen pengguna
│       │
│       ├── components/         # Komponen yang dipakai lintas halaman
│       │   ├── Layout.js       #   Header, navigasi, lonceng notifikasi, badge verifikasi
│       │   ├── PageTabs.js     #   Tab halaman (pola WAI-ARIA) untuk hub Laporan & Impor
│       │   ├── AccessibilityBar.js # Bilah aksesibilitas global (paling atas)
│       │   ├── Speak.js        #   Tombol "Bacakan" (memicu TTS)
│       │   ├── KpiCard.js      #   Kartu KPI dashboard
│       │   ├── AIHistory.js    #   Daftar riwayat analisa + bandingkan 2 hasil
│       │   └── ui/             #   46 komponen shadcn/ui (JANGAN diedit manual)
│       │
│       ├── context/            # State global via React Context
│       │   ├── AuthContext.js  #   user, login(), logout(), loading
│       │   └── AccessibilityContext.js # mode disabilitas buta/tuli, TTS, kecepatan suara
│       │
│       ├── hooks/use-toast.js  # Hook notifikasi toast
│       ├── lib/
│       │   ├── api.js          #   SATU-SATUNYA tempat base URL API ditentukan
│       │   ├── ttsBrowser.js   #   Mesin suara perangkat (aman untuk iOS/Android)
│       │   └── utils.js        #   Helper `cn()` untuk menggabung className
│       └── constants/
│           ├── menu.js           # Susunan 9 kelompok menu (sumber tunggal navigasi)
│           ├── roles.js          # Himpunan peran untuk menu & penjaga rute
│           ├── makassar_geo.json # GeoJSON batas 15 kecamatan (kode wilayah 73.71)
│           └── testIds/          # Konstanta data-testid untuk pengujian
│
├── memory/                     # Memori proyek untuk AI agent
│   ├── PRD.md                  #   Kebutuhan produk & riwayat fitur
│   └── test_credentials.md     #   Kredensial uji (DIABAIKAN GIT)
│
├── tests/, test_reports/       # Artefak pengujian otomatis
└── design_guidelines.json      # Panduan desain (warna, tipografi, spasi)
```

### Direktori yang tidak boleh diubah sembarangan

| Path | Alasan |
|---|---|
| `frontend/src/components/ui/` | Hasil generate shadcn/ui. Untuk kustomisasi, buat wrapper baru di `components/`. |
| `backend/.env`, `frontend/.env` | Hanya **tambahkan** baris baru. Jangan menulis ulang seluruh isinya. |
| `frontend/src/constants/makassar_geo.json` | Data batas wilayah resmi. |
| `backend/assets/` | Logo resmi untuk kop laporan. |

---

## 4. Data Flow

### 4.1 Alur baca (contoh: memuat Dashboard)

```
Browser
  │  komponen Dashboard.js dirender
  ▼
api.get("/stats/overview")                      src/lib/api.js (axios, withCredentials)
  │  GET https://<domain>/api/stats/overview
  ▼
Reverse proxy (Traefik/Coolify)                 route /api/* -> kontainer
  ▼
FastAPI  api_router (prefix "/api")              backend/server.py
  │  handler async overview()
  ▼
db.regions.find().to_list(100)                   backend/mariadb_store.py
  │  diterjemahkan menjadi:
  │  SELECT `_id`,`doc` FROM `doc_regions`
  ▼
MariaDB (aiomysql pool)
  │  baris dikembalikan
  ▼
JSON di kolom `doc` di-parse -> dict Python (`_id` disuntikkan kembali)
  ▼
Handler menjumlahkan angka -> dict respons
  ▼
FastAPI mengembalikan JSON
  ▼
Dashboard menyimpan ke state -> Recharts merender grafik
```

### 4.2 Alur autentikasi

```
Login.js  ──POST /api/auth/login──▶  cari doc_users berdasarkan email (index k_email)
                                     verifikasi bcrypt
                                     tolak bila status != active
                                     terbitkan JWT akses + refresh
                                     Set-Cookie httpOnly (secure/samesite dari env)
         ◀──────── data user ───────

AuthContext  ──GET /api/auth/me──▶  cookie dibaca -> JWT diverifikasi
(saat aplikasi dimuat)               ambil user dari doc_users berdasarkan _id
                                     buang password_hash lalu kembalikan

Endpoint terlindungi memakai FastAPI Depends:
  current_user      -> siapa pun yang sudah login
  verifikator_user  -> verifikator atau superadmin (403 jika bukan)
  admin_user        -> superadmin saja (403 jika bukan)
```

### 4.3 Alur tulis + verifikasi (inti tata kelola data)

```
         ┌── peran = superadmin ──────────────────────────────────────┐
         │                                                            │
DataEntry.js                                                          ▼
  PUT /api/kelurahan/{id}   ──▶  cek wewenang   ──▶   langsung UPDATE doc_kelurahan
         │                                             lalu _recompute_region()
         │                                             (jumlahkan kelurahan -> kecamatan)
         │                                                    ──▶ {"status":"applied"}
         │
         └── peran = petugas / operator ──▶ wilayah harus cocok, jika tidak 403
                                            │
                                            ▼
                       INSERT doc_data_changes  {status:"pending", changes, before,
                                                 submitted_by, submitted_at}
                                            ──▶ {"status":"pending", change_id}

Verifikasi.js (peran verifikator/superadmin)
  GET  /api/verifikasi?status=pending   ──▶  daftar antrean
  POST /api/verifikasi/{id}/approve     ──▶  _apply_change() menulis ke tabel tujuan
                                             + _recompute_region()
                                             + tandai approved, reviewed_by, reviewed_at
  POST /api/verifikasi/{id}/reject      ──▶  tandai rejected + catatan (data TIDAK berubah)

Layout.js menampilkan badge dari GET /api/verifikasi/count
            dan lonceng dari GET /api/admin/pending-count (pendaftaran menunggu)
```

### 4.4 Alur analisa AI (SSE streaming)

```
AIAnalysis.js
  fetch("/api/ai/analyze", POST {kategori, wilayah})
         ▼
_build_data_summary()  ──▶  baca doc_regions + konstanta di seed_data.py
         ▼                   (prompt selalu memakai ANGKA NYATA, tanpa data palsu)
LlmChat(gemini/gemini-2.5-flash).stream_message()
         ▼
untuk setiap TextDelta:  yield  'data: {"delta":"..."}\n\n'
         ▼
Frontend membaca stream, menambah teks, merender markdown secara progresif
         ▼
setelah StreamDone:  INSERT doc_ai_analyses {id, kategori, wilayah, hasil, ringkasan}
                     yield 'data: {"done":true}\n\n'
         ▼
AIHistory.js memuat GET /api/ai/history  (bandingkan 2 hasil / unduh PDF / hapus)
```

### 4.5 Alur Text-to-Speech (aksesibilitas disabilitas buta)

Jalur utama adalah **mesin suara perangkat** lewat Web Speech API (`speechSynthesis`),
bukan server. Ini disengaja: iOS/iPadOS hanya mengizinkan ucapan pertama bila `speak()`
dipanggil di dalam gestur pengguna, sehingga permintaan jaringan di depannya membuat suara
tidak berbunyi di perangkat seluler.

```
Tombol Bacakan / SpeakMini / perintah suara
         ▼
AccessibilityContext.speak()            (sinkron — tanpa await)
         ▼
lib/ttsBrowser.js
  potongTeks():  pecah menjadi potongan <= 160 karakter pada batas kalimat
         ▼
speechSynthesis.speak()  ──▶  suara `id-ID` perangkat
  onend ──▶ potongan berikutnya (dirangkai satu per satu)
  onerror / watchdog 3 detik ──▶ panel menampilkan "Suara belum berbunyi" + Coba lagi
```

Catatan perangkat:

| Hal | Perilaku |
|---|---|
| Suara Bahasa Indonesia | Harus terpasang di perangkat. Bila tidak ada, panel menampilkan petunjuk pemasangan. |
| Gestur pengguna | Ketukan pertama pada tombol langsung memulai suara; sesi audio dibuka pada interaksi pertama. |
| Jeda / Lanjutkan | Jeda menghentikan ucapan lalu melanjutkan dari potongan terakhir (Chrome Android tidak mendukung `pause()` dengan benar). |
| Latar belakang | Bila sistem menghentikan suara saat aplikasi ditinggalkan, status tidak tertahan di “Membacakan…”. |

`POST /api/tts` (audio OpenAI yang di-cache di `doc_tts_cache`) masih ada di backend tetapi
**nonaktif** — endpoint menjawab 503. Untuk memakainya lagi, hidupkan server TTS lalu set
`REACT_APP_TTS_SERVER=1` pada frontend.

```
POST /api/tts {text, voice}   (hanya bila REACT_APP_TTS_SERVER=1)
         ▼
_clean_for_tts():  buang emoji, URL, markdown
                   terbilang.expand_numbers():  "13.334" -> "tiga belas ribu tiga ratus tiga puluh empat"
         ▼
kunci cache = sha256(text|voice|tts-1|mp3)
         ▼
doc_tts_cache ada?  ── ya ──▶  ambil audio (base64 -> bytes)
         │ tidak
         ▼
OpenAITextToSpeech(tts-1) ──▶ bytes mp3 ──▶ INSERT doc_tts_cache
         ▼
StreamingResponse audio/mpeg  ──▶  <audio> di browser
```

### 4.6 Alur permintaan di produksi (satu kontainer)

```
https://trirara.my.id/dashboard        https://trirara.my.id/api/regions
            │                                      │
            ▼                                      ▼
   Reverse proxy Coolify  ────────────────────────────────
            │
            ▼
   Uvicorn (PORT, default 8000)
            │
     ┌──────┴───────────────────────────────┐
     ▼                                      ▼
  api_router prefix "/api"          SPAStaticFiles("/")
  (didaftarkan LEBIH DULU,          menyajikan /srv/frontend/build
   jadi selalu menang)              path tak dikenal -> index.html
                                    (agar rute React Router jalan)
```

---

## 5. Coding Conventions

### 5.1 Bahasa

| Konteks | Bahasa |
|---|---|
| Teks yang dilihat pengguna, pesan error API | **Bahasa Indonesia** formal pemerintahan |
| Komentar & dokumentasi | **Bahasa Indonesia** |
| Nama variabel, fungsi, endpoint | **Bahasa Inggris**, kecuali istilah domain yang tidak punya padanan pas: `kelurahan`, `kecamatan`, `wilayah`, `verifikasi`, `petugas`, `terbilang`, `rekap` |

### 5.2 Penamaan berkas

| Jenis | Aturan | Contoh |
|---|---|---|
| Halaman React | `PascalCase.js` di `src/pages/` | `KelolaPetugas.js` |
| Komponen React | `PascalCase.js` di `src/components/` | `AccessibilityBar.js` |
| Komponen shadcn/ui | `kebab-case.jsx` di `src/components/ui/` | `dropdown-menu.jsx` |
| Context | `PascalCaseContext.js` | `AuthContext.js` |
| Hook | `use-kebab-case.js` | `use-toast.js` |
| Helper / lib | `camelCase.js` atau kata tunggal | `api.js`, `utils.js` |
| Modul Python | `snake_case.py` | `mariadb_store.py`, `export_excel.py` |

### 5.3 Konvensi backend (Python)

```python
# 1. Model Pydantic: PascalCase, diakhiri peran datanya. Semua di bagian atas server.py.
class KelurahanUpdate(BaseModel):
    ats: Optional[int] = Field(None, ge=0)          # selalu beri batasan validasi

# 2. Endpoint: SELALU lewat api_router (prefix "/api"), path kebab/snake,
#    nama fungsi snake_case dan deskriptif.
@api_router.put("/kelurahan/{kel_id}")
async def update_kelurahan(kel_id: str, inp: KelurahanUpdate,
                           user: dict = Depends(current_user)):
    ...

# 3. Helper privat diawali garis bawah.
def _clean_updates(inp): ...
async def _recompute_region(kecamatan_nama: str, editor: str): ...

# 4. Otorisasi lewat Depends, JANGAN cek peran manual di dalam handler.
async def admin_only(admin: dict = Depends(admin_user)): ...

# 5. Error selalu HTTPException dengan detail berbahasa Indonesia.
raise HTTPException(status_code=403, detail="Anda tidak berwenang mengubah data kecamatan ini")

# 6. Serializer: buang `_id`, sajikan sebagai `id` string.
def _serialize_region(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc

# 7. Waktu SELALU UTC dalam format ISO string.
datetime.now(timezone.utc).isoformat()

# 8. Konfigurasi SELALU dari environment, jangan pernah di-hardcode.
os.environ["JWT_SECRET"]                    # wajib ada -> gagal cepat bila lupa diisi
os.environ.get("COOKIE_SAMESITE", "none")   # opsional -> ada default
```

**Aturan wajib backend**

1. Setiap endpoint **harus** berada di bawah prefix `/api` (reverse proxy me-rute berdasarkan ini).
2. Server **harus** bind ke `0.0.0.0` dan port dari env `PORT`.
3. Semua operasi database lewat `db.<collection>` dari `mariadb_store` — jangan tulis SQL mentah di `server.py`.
4. Menambah field yang sering difilter? Daftarkan di `INDEXED_FIELDS` (`mariadb_store.py`) agar dapat index.
5. Seeding harus **idempotent** (aman dijalankan berulang tiap startup).
6. **Jangan pernah** mengembalikan `password_hash` ke klien.
7. Operator filter/update yang didukung store: `$ne`, `$exists`, `$in`, `$nin`, `$gt(e)`, `$lt(e)`, `$regex`, `$set`, `$unset`, `$inc`. Butuh yang lain? Tambahkan di `Collection._where()` / `_apply_update()`.

### 5.4 Konvensi frontend (React)

```jsx
// 1. Function component + named export untuk komponen, default export untuk halaman.
export default function Dashboard() { ... }

// 2. Import SELALU pakai alias "@/", jangan "../../".
import api, { API } from "@/lib/api";
import { Button } from "@/components/ui/button";

// 3. Semua panggilan API lewat instance axios terpusat.
const { data } = await api.get("/regions");            // BENAR
// axios.get("http://localhost:8001/api/regions")      // SALAH: URL di-hardcode

// 4. Untuk streaming / unduhan berkas, pakai fetch dengan konstanta API.
const res = await fetch(`${API}/ai/analyze`, { method: "POST", credentials: "include", ... });

// 5. State: camelCase; boolean diawali is/has/show.
const [loading, setLoading] = useState(true);
const [showCompare, setShowCompare] = useState(false);

// 6. Tangani SEMUA state: loading, kosong, error, sukses.
if (loading) return <Skeleton />;
if (error)   return <ErrorState onRetry={load} />;
if (!rows.length) return <EmptyState />;

// 7. Setiap elemen interaktif WAJIB punya data-testid (kebab-case).
<Button data-testid="btn-approve-change" onClick={approve}>Setujui</Button>

// 8. Pesan error dari API selalu dilewatkan formatApiErrorDetail
//    (FastAPI bisa mengirim detail berupa string ATAU array validasi).
import { formatApiErrorDetail } from "@/lib/api";
toast.error(formatApiErrorDetail(e.response?.data?.detail));

// 9. Gabungkan className dengan cn(), jangan template string manual.
import { cn } from "@/lib/utils";
<div className={cn("rounded-xl border p-4", active && "ring-2 ring-red-600")} />
```

**Aturan wajib frontend**

1. `src/lib/api.js` adalah **satu-satunya** tempat base URL API ditentukan. Jangan pernah membaca `process.env.REACT_APP_BACKEND_URL` di berkas lain.
2. **Jangan pernah** hardcode URL atau localhost.
3. Kirim kredensial pada setiap request (`withCredentials` di axios, `credentials: "include"` di fetch) — auth memakai cookie.
4. **Jangan** menggunakan latar transparan dengan teks gelap; selalu tentukan warna latar eksplisit (pengguna bisa memakai tema gelap/terang OS).
5. Semua warna & font mengikuti token Tailwind di `index.css` / `design_guidelines.json`. Warna aksen utama: merah `#DC2626`.
6. Sembunyikan menu berdasarkan peran **dan** tetap batasi di backend (jangan hanya di UI).
7. Konten baru wajib bisa dibacakan TTS bila relevan (bungkus dengan `<Speak>`).

### 5.5 Style & format

| | Python | JavaScript |
|---|---|---|
| Indentasi | 4 spasi | 2 spasi |
| Panjang baris | ~100 karakter | ~100 karakter |
| Kutip | `"` ganda | `"` ganda |
| Linter | `ruff` / `flake8` | `eslint` (react-hooks) |
| Formatter | `black`, `isort` | bawaan CRA |

### 5.6 Nama environment variable

`SCREAMING_SNAKE_CASE`. Variabel database mengikuti **format standar Coolify**:
`DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`.
Setiap variabel baru **wajib** didokumentasikan di `.env.example`.

**Runtime vs build-time \u2014 penting untuk dipahami**

| Variabel | Sifat | Catatan |
|---|---|---|
| Semua variabel backend (`DB_*`, `JWT_SECRET`, `PORT`, dst.) | **runtime** | Dibaca `os.environ` saat aplikasi berjalan. Cukup diisi di Coolify. |
| `REACT_APP_BACKEND_URL` | **build-time** | Dibakukan ke dalam bundel JavaScript saat `yarn build`. Mengisinya sebagai environment variable runtime **tidak berefek** \u2014 harus lewat *build argument*. |

Project ini adalah **React (CRA + craco), bukan Next.js**, jadi tidak ada
`NEXT_PUBLIC_*`. Pada image produksi `REACT_APP_BACKEND_URL` sengaja **kosong**
sehingga `src/lib/api.js` memakai base URL relatif `/api` \u2014 frontend dan API
berada pada satu origin, sehingga tidak perlu variabel \"public base URL\" apa pun.

**Konfigurasi database menerima dua bentuk**

```env
# Bentuk A - variabel terpisah (format standar Coolify, disarankan)
DB_HOST=103.89.2.162
DB_PORT=7890
DB_DATABASE=default
DB_USERNAME=mariadb
DB_PASSWORD=rahasia

# Bentuk B - satu connection string (opsional)
DATABASE_URL=mysql://mariadb:rahasia@103.89.2.162:7890/default
```

Aturan resolusi ada di `MariaDocStore.from_env()`: nilai dari `DATABASE_URL`
(atau `DB_URL` / `MYSQL_URL`) dipakai untuk mengisi bagian yang **kosong**, dan
variabel `DB_*` yang diisi eksplisit selalu **menang**.

---

## 6. Menjalankan Secara Lokal

### Prasyarat

- **Python 3.11** — disamakan dengan `Dockerfile`. Versi yang lebih baru belum tentu
  punya wheel siap pakai untuk seluruh dependensi (pandas, pdfplumber, dll).
- **Node.js 20+** (teruji pada 24.x) dan **Yarn 1.x**. Bila `yarn` tidak ada di PATH,
  pakai `corepack yarn` — corepack sudah ikut terpasang bersama Node.
- **MariaDB 10.6+ / MySQL 8+** yang bisa diakses.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows (Git Bash): .venv/Scripts/activate
pip install -r requirements-prod.txt

# Butuh pytest/linter? gunakan requirements-dev.txt (menambahkan pytest, black,
# flake8, isort, mypy di atas requirements-prod.txt).
# JANGAN pakai requirements.txt untuk dev: isinya freeze lengkap platform Emergent
# yang menyertakan wheel privat (litellm dari customer-assets.emergentagent.com)
# dan emergentintegrations, sehingga bisa gagal di luar platform tersebut.

cp .env.example .env             # template khusus dev lokal
# Isi minimal: DB_*, JWT_SECRET, ADMIN_PASSWORD. LLM/Google Maps/SMTP opsional.

uvicorn server:app --reload --port 8001
```

> **Wajib untuk lokal: `COOKIE_SECURE=false`** (sudah diset di
> `backend/.env.example`). Default di kode adalah `true`, dan dengan `secure=true`
> cookie sesi tidak dikirim browser lewat `http://localhost` — login tampak berhasil
> tetapi setiap request berikutnya 401.
>
> **Jangan set `HOST=localhost`.** Di Windows, `localhost` bisa resolve ke `::1`
> sehingga server hanya mendengarkan IPv6 dan `http://127.0.0.1:8001` tidak bisa
> dibuka. Gunakan `HOST=127.0.0.1` (atau `0.0.0.0` bila ingin diakses dari LAN).
>
> Start pertama butuh **sekitar 60 detik** (import pandas + google-genai). Uvicorn
> baru membuka port setelah import selesai — jangan dianggap crash.

Saat pertama kali start, aplikasi otomatis membuat tabel `doc_*`, meng-seed
15 kecamatan + 153 kelurahan, dan membuat akun superadmin.

### Frontend

```bash
cd frontend
corepack yarn install            # atau: yarn install
cp .env.example .env
# frontend/.env -> REACT_APP_BACKEND_URL=http://localhost:8001

corepack yarn start              # http://localhost:3000
```

> **Jangan salin `WDS_SOCKET_PORT=443`** dari `frontend/.env.example` ke `.env`
> lokal. Nilai itu untuk proxy platform Emergent dan membuat HMR gagal di lokal.
>
> Bila `yarn start` gagal dengan `Cannot find module '...'`, cache Yarn kemungkinan
> korup (pernah terjadi setelah instalasi terputus). Bersihkan lalu ulangi:
> `corepack yarn cache clean && rm -rf node_modules && corepack yarn install`.

> Kosongkan `REACT_APP_BACKEND_URL` bila frontend dan API berada pada origin yang
> sama (seperti pada image Docker produksi).

### Sekali jalan dengan Docker

```bash
docker compose up --build   # aplikasi + MariaDB -> http://localhost:8000
```

---

## 7. Referensi API

Semua path diawali `/api`.

### Autentikasi

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| POST | `/auth/register` | publik | Daftar (selalu jadi `petugas` berstatus `pending`) |
| POST | `/auth/login` | publik | Masuk, mengeset cookie httpOnly |
| POST | `/auth/logout` | publik | Hapus cookie |
| GET | `/auth/me` | login | Profil pengguna saat ini |

### Data wilayah

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| GET | `/regions` | publik | 15 kecamatan |
| GET | `/regions/{id}` | publik | Detail satu kecamatan |
| PUT | `/regions/{id}` | petugas+ | Ubah data (superadmin langsung, lainnya masuk verifikasi) |
| GET | `/regions/{id}/kelurahan` | publik | Kelurahan dalam satu kecamatan |
| GET | `/kelurahan?kecamatan=` | publik | Daftar kelurahan (opsional difilter) |
| PUT | `/kelurahan/{id}` | petugas+ | Ubah data kelurahan |

### Statistik & konstanta

| Method | Path | Fungsi |
|---|---|---|
| GET | `/stats/overview` | Total agregat untuk kartu KPI |
| GET | `/trends/poverty` | Tren kemiskinan + target RPJMD |
| GET | `/trends/stunting` | Tren stunting EPPGBM vs SSGI |
| GET | `/disability` | Rincian disabilitas (ragam, pendidikan, pekerjaan) |
| GET | `/ats` | Ringkasan anak tidak sekolah |
| GET | `/pmks` | Data PMKS |
| GET | `/categories` | Metadata kategori (label, field, unit, warna) |

### Matriks dan Musrenbang

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| GET | `/matriks/kategori` | login | Rekap kemiskinan, stunting, ATS, anak jalanan per kecamatan |
| GET | `/matriks/oppkpke?semester=&tahun=` | login | Evaluasi OPPKPKE per semester |
| GET | `/matriks/ats-program?tahun=` | login | Program dan anggaran ATS 2025–2027 |
| GET | `/matriks/disabilitas?tahun=` | login | Monev kegiatan disabilitas lintas OPD |
| GET | `/matriks/{jenis}/template` | penulis | Unduh template Excel |
| POST | `/matriks/{jenis}/import` | penulis | Impor (mengganti isi matriks) |
| GET | `/musrenbang` | login | Usulan + program/anggaran Musrenbang Tematik |

### Verifikasi

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| GET | `/verifikasi?status=` | verifikator+ | Daftar usulan perubahan |
| GET | `/verifikasi/count` | verifikator+ | Jumlah usulan pending (badge) |
| POST | `/verifikasi/{id}/approve` | verifikator+ | Setujui & terapkan |
| POST | `/verifikasi/{id}/reject` | verifikator+ | Tolak + catatan |

### Manajemen pengguna

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| GET | `/admin/users` | superadmin | Daftar pengguna |
| POST | `/admin/users` | superadmin | Buat pengguna |
| PATCH | `/admin/users/{id}` | superadmin | Ubah nama/email/peran/wilayah |
| PATCH | `/admin/users/{id}/status` | superadmin | active / inactive / pending |
| POST | `/admin/users/{id}/reset-password` | superadmin | Atur ulang kata sandi |
| DELETE | `/admin/users/{id}` | superadmin | Hapus pengguna |
| GET | `/admin/pending-count` | superadmin | Jumlah pendaftaran menunggu (lonceng) |

### AI, TTS & laporan

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| POST | `/ai/analyze` | publik | Analisa program (SSE streaming) |
| GET | `/ai/history` | publik | Riwayat analisa |
| GET | `/ai/history/{id}` | publik | Detail satu analisa |
| DELETE | `/ai/history/{id}` | login | Hapus riwayat |
| POST | `/tts` | publik | Audio mp3 (di-cache) |
| POST | `/report/ai` | publik | PDF hasil analisa |
| GET | `/report/dashboard` | publik | PDF ringkasan dashboard |
| GET | `/export/excel` | publik | Excel 2 sheet |
| GET | `/health` | publik | Healthcheck (memeriksa MariaDB) |

---

## 8. Peran & Wewenang

| Peran | Wewenang |
|---|---|
| **superadmin** | Akses penuh. Perubahan data langsung diterapkan. Mengelola semua pengguna. |
| **petugas** | Input data **wilayahnya sendiri** → masuk antrean verifikasi. |
| **operator** | Sama seperti petugas. |
| **verifikator** | Menyetujui/menolak usulan perubahan data. |
| **pimpinan** | Read-only + mengunduh laporan & analisa. Tidak boleh input data atau kelola pengguna. |
| **publik** | Read-only dashboard, peta, analisa, aksesibilitas. |

> `admin` adalah peran lama; saat startup otomatis dimigrasikan menjadi `superadmin`.

Kredensial contoh (di-seed idempotent) ada di `memory/test_credentials.md`.

---

## 9. Deployment

Panduan langkah demi langkah: **[DEPLOY_COOLIFY.md](./DEPLOY_COOLIFY.md)**

Ringkasnya:

- **Build Pack**: Dockerfile (root repo)
- **Port**: dari env `PORT` (default 8000)
- **Healthcheck**: `GET /api/health`
- **Database**: MariaDB melalui `DB_HOST` / `DB_PORT` / `DB_DATABASE` / `DB_USERNAME` / `DB_PASSWORD` (atau satu baris `DATABASE_URL`)
- **GUI database**: phpMyAdmin \u2014 `deploy/phpmyadmin-compose.yaml`
- **Base URL publik**: tidak perlu env apa pun (frontend & API satu origin)
- **Stateless**: tidak butuh volume persisten

---

## 10. Catatan untuk AI Agent Berikutnya

Baca ini lebih dulu sebelum mengubah apa pun.

### Baca dulu

1. `memory/PRD.md` — kebutuhan produk & riwayat fitur yang sudah selesai.
2. `memory/test_credentials.md` — kredensial untuk menguji alur di balik login.
3. `design_guidelines.json` — token warna, tipografi, spasi.
4. Bagian [Coding Conventions](#5-coding-conventions) di dokumen ini.

### Jebakan yang sering terjadi

| Jebakan | Cara benar |
|---|---|
| Menulis SQL langsung di `server.py` | Pakai `db.<collection>` dari `mariadb_store` |
| Memakai operator MongoDB yang belum didukung store | Tambahkan dulu di `Collection._where()` / `_apply_update()` |
| Menambah field yang sering difilter tanpa index | Daftarkan di `INDEXED_FIELDS` |
| Membuat endpoint tanpa prefix `/api` | Reverse proxy tidak akan me-rutekannya |
| Hardcode URL backend di komponen | Selalu impor dari `@/lib/api` |
| Menulis ulang seluruh `.env` | Hanya **tambahkan** baris baru |
| Lupa `data-testid` | Pengujian otomatis akan gagal |
| Menampilkan `detail` error API mentah | Lewatkan `formatApiErrorDetail()` (detail bisa berupa array) |
| Menyimpan `datetime` object ke database | Simpan ISO string (`.isoformat()`) |
| Menambah fitur backend tanpa UI | Backend dan frontend harus selalu sepadan |
| Membuat data palsu/mock untuk demo | Semua angka harus berasal dari database atau `seed_data.py` |

### Menambah kategori data baru (contoh alur kerja)

1. `backend/seed_data.py` — tambahkan field ke `CATEGORY_FIELDS` dan entri di `CATEGORY_META`.
2. `backend/server.py` — tambahkan field ke `RegionUpdate` & `KelurahanUpdate`, dan konteks di `CATEGORY_CONTEXT`.
3. `backend/mariadb_store.py` — tambahkan ke `INDEXED_FIELDS` bila akan sering difilter.
4. Frontend — tampilkan di `Dashboard.js` (KPI/grafik), `MapView.js` (tombol kategori), `DataEntry.js` (form input), `Rekap.js` (tabel).
5. `backend/export_excel.py` & `report.py` — tambahkan kolom pada ekspor.
6. Perbarui `memory/PRD.md` dan bagian relevan di README ini.

### Menambah peran baru

1. Perbarui konstanta peran di `server.py` (`SUPERADMIN_ROLES`, `INPUT_ROLES`, `VERIFIER_ROLES`) dan daftar peran yang valid pada endpoint `/admin/users`.
2. Buat dependency `Depends` baru bila diperlukan.
3. Perbarui navigasi berbasis peran di `components/Layout.js` dan penjaga rute di `App.js`.
4. Perbarui tabel [Peran & Wewenang](#8-peran--wewenang).

### Sebelum menyatakan selesai

- [ ] `GET /api/health` mengembalikan `{"status":"ok"}`
- [ ] Tidak ada error di log backend maupun konsol browser
- [ ] Alur diuji untuk **setiap** peran terkait (superadmin, petugas, verifikator, pimpinan, publik)
- [ ] Setiap endpoint baru punya tampilan di frontend
- [ ] Elemen interaktif baru punya `data-testid`
- [ ] `frontend && yarn build` berhasil (tidak ada error impor)
- [ ] Variabel environment baru tercatat di `.env.example`
- [ ] `memory/PRD.md` diperbarui

---

<div align="center">

**Badan Perencanaan Pembangunan Daerah (Bappeda) Kota Makassar**
Sumber data: Kelurahan & Kecamatan se-Kota Makassar

</div>
