# plan.md — GeoTag Verval DTSEN + Restrukturisasi Role (Petugas/Operator/Verifikator) + Scoping Wilayah + Sinkronisasi Foto/GPS ke Semua Peta

## 1) Objectives
- **Status saat ini (sudah ada):** Modul GeoTag‑Verval DTSEN **aktif & siap operasional** untuk role `operator_rt_rw`.
  - Routing, Sidebar, RBAC dasar, integrasi peta (`VervalMapLayer` di `InklusiMap`), dan Google basemap Leaflet: **selesai**.
  - **P0 Form Verval Komprehensif (resmi)**: **selesai** (11 variabel + penapisan individu + kesimpulan) dengan **alur ketat**: **Formulir → Foto → GPS → Kirim**.
  - Backend verval: upload foto sudah menerima **GPS saat foto** (`lat/lng/akurasi_m`) dan menyimpan ke `verval_foto.gps_saat_foto`.
  - Layer peta verval sudah ada:
    - `/api/verval/peta` mengembalikan **mode titik** (operator/reviewer) atau **agregat** (role internal lain).

- **Objective baru (fase lanjutan sekarang): Restrukturisasi role & pembatasan wilayah (RBAC + scoping)**
  1. **Petugas** (baru/diubah): ditentukan berdasar **Kelurahan + RW/RT** dan hanya dapat mengakses:
     - Data yang tampil di publik
     - Form pengisian **Verval + GeoTag (foto + koordinat)**
  2. **Operator**:
     - **Satu-satunya yang dapat membuat akun petugas** (di halaman `/kelola-petugas`)
     - Akses data **dibatasi hanya kecamatan masing-masing** (tidak bisa lihat wilayah lain)
  3. **Verifikator**:
     - Hanya bisa melihat data sesuai wilayah (kecamatan) masing-masing
  4. **Sinkronisasi GeoTag**:
     - Foto petugas/operator menampilkan koordinat saat foto di UI
     - Setelah upload, data foto+koordinat tersimpan dan **muncul/sinkron** di seluruh peta yang relevan:
       - `InklusiMap` (Peta Sosial & Peta Kemiskinan)
       - `PetaGIS`/peta bangunan (via `engine.setOverlay`/overlay layer)
       - `KoordinatGIS`

- **Objective lanjutan (tetap, setelah fase scoping stabil):**
  - **P1:** Peta Bangunan GeoTag — membuka hasil Verval langsung dari peta bangunan.
  - **P2:** Panel Operator Harian — ringkasan harian progres Verval.

## 2) Implementation Steps

### Phase 1 — V1 App Development: Routing & Sidebar Wiring (Core Access) ✅ SELESAI
**User stories**
1. Operator RT/RW dapat membuka “Verval DTSEN → Operator” dan melihat sasaran.
2. Operator RT/RW dapat membuka detail sasaran dan membuat draft.
3. Verifikator/Admin Bappeda dapat membuka “Verval DTSEN → Review”.
4. Admin/Superadmin/Admin Bappeda dapat membuka “Verval DTSEN → Penugasan”.
5. Role non‑berwenang tidak melihat menu dan tidak dapat akses route.

**Langkah implementasi (realisasi)**
- Route React Router di `frontend/src/App.js`:
  - `/verval` (beranda operator)
  - `/verval/sasaran/:ref` (form operator)
  - `/verval/review` (review)
  - `/verval/penugasan` (penugasan)
- RBAC route guarding:
  - Operator: `operator_rt_rw`
  - Reviewer: `verifikator`, `admin_bappeda` (+ `admin/superadmin`)
  - Penugasan: `superadmin`, `admin`, `admin_bappeda`
- Sidebar submenu “Verval DTSEN” + dukungan title untuk `/verval/sasaran/:ref`.

**Hasil verifikasi**
- Sudah diuji via E2E agent (iteration_19): role gating dan navigasi berjalan.

### Phase 2 — Google Maps Basemap via Leaflet (No Rewrite) ✅ SELESAI
**User stories**
1. User internal dapat memilih basemap Google (Road/Satellite/Hybrid).
2. Jika API key kosong, fallback ke OSM.
3. Tidak ada crash pada unmount/StrictMode.

**Langkah implementasi (realisasi)**
- `InklusiMap.tsx` memuat API key dari `GET /api/map/config`.
- Basemap layers: OpenStreetMap + Google Road/Satellite/Hybrid via Leaflet TileLayer.
- Bugfix Leaflet control: guard cancel + cleanup.

### Phase 3 — Integrasi `VervalMapLayer` ke Peta Utama ✅ SELESAI
**User stories**
1. Operator RT/RW melihat mode titik (data sendiri).
2. Reviewer melihat titik + tautan ke review.
3. Role internal lain melihat agregat kelurahan.

**Langkah implementasi (realisasi)**
- `VervalMapLayer` dirender di `InklusiMap.tsx` ketika map siap dan bukan `publicMode`.
- Mode data ditentukan backend via `GET /api/verval/peta` (`titik|agregat|none`).

### Phase 4 — Testing E2E (Frontend perspective) ✅ SELESAI
**User stories**
1. Operator dapat membuat draft dan menjalankan alur UI Verval.
2. Reviewer dapat akses review.
3. Admin dapat akses penugasan.
4. Peta + basemap + layer Verval stabil.

**Langkah implementasi (realisasi)**
- `testing_agent_v3` dijalankan.
- Hasil: sukses (iteration_19/20).

---

### Phase 5 — P0: Form Verval Komprehensif (mengacu PDF) ✅ SELESAI
**Target utama:** Operator RT/RW wajib menyelesaikan form komprehensif sebelum GeoTag (foto/GPS).

**Realisasi ringkas**
- Backend:
  - `verval_config.py` + `verval.py` sudah enforce **strict gating**: upload foto `/records/{rid}/foto` ditolak **422** bila formulir belum lengkap.
  - `verval_foto` menyimpan `gps_saat_foto` jika dikirim dari frontend.
- Frontend:
  - `VervalOperator.tsx` step menjadi 5 langkah + validasi kekurangan.

**Testing (realisasi)**
- Backend pytest pass.
- E2E form komprehensif lulus (iteration_20).

---

### Phase 6 — P0.5: Restrukturisasi Role Verval & GeoTag + Scoping Wilayah ✅ SELESAI (iteration_22: backend 36/36, frontend 100%)
Fase ini mengganti/menambah RBAC agar sesuai kebutuhan produksi: petugas dibuat operator, serta semua role ter-scope wilayah.

#### 6.1 User stories
1. **Kelola petugas**:
   - Operator dapat membuat akun **petugas**.
   - Petugas wajib punya atribut wilayah: **kecamatan + kelurahan + RW + RT**.
   - Superadmin **tidak membuat akun petugas** (opsional: masih boleh buat role lain).
2. **Pembatasan akses**:
   - Operator & verifikator hanya dapat melihat data sesuai kecamatan masing-masing.
   - Petugas hanya dapat melihat data sesuai kelurahan/RW/RT yang ditetapkan.
3. **Akses fitur petugas**:
   - Petugas hanya melihat menu/route: **Dashboard Publik + Verval/GeoTag**.
4. **GeoTag foto + koordinat**:
   - Saat petugas mengambil foto, koordinat tampil di UI (GPS perangkat; fallback EXIF bila ada).
   - Setelah upload, koordinat tersimpan & mempengaruhi layer GeoTag di semua peta.

#### 6.2 Backend — perubahan yang direncanakan
**A) Tambah field user untuk granular scope**
- `users` document ditambah field:
  - `kecamatan`, `kelurahan`, `kode_kelurahan` (opsional), `rw`, `rt` (string/list)
  - tetap simpan `wilayah` untuk kompatibilitas UI lama (mis. kecamatan).

**B) RBAC & endpoint management user**
- `server.py`
  - Tambah dependency baru:
    - `user_manager_dep`: `superadmin` **atau** `operator` (sesuai policy final)
    - `operator_dep`: khusus role `operator`
  - Aturan `/admin/users` disesuaikan:
    - Operator hanya dapat melihat/membuat petugas dalam kecamatan-nya.
    - Validasi: operator yang membuat petugas otomatis set `kecamatan` = kecamatan operator.
    - Superadmin/admin bisa kelola role lain, namun **dibatasi** untuk tidak membuat role petugas bila kebijakan mengharuskan demikian.

**C) Scoping wilayah global**
- Buat modul baru `backend/scope.py`:
  - Helper `kecamatan_scope(user)` dan helper filter query.
  - Daftar `SCOPED_ROLES = ("operator", "verifikator", "petugas", "operator_kecamatan", "operator_kelurahan")`.
- Middleware/guard:
  - Untuk role scoped, injeksi/paksakan filter kecamatan/kode_kecamatan pada endpoint yang rawan bocor lintas wilayah.
  - Cache pendek (mis. 60s) untuk mapping kode wilayah bila diperlukan.

**D) Integrasi ke modul verval**
- `verval_config.py`:
  - Perluas operator roles: `OPERATOR_ROLES = ("operator_rt_rw", "petugas")`.
- `verval.py`:
  - Untuk role `petugas`, penugasan tidak memakai `verval_penugasan`, tetapi **penugasan sintetis** dari profil user:
    - (kode_kelurahan + rw + rt)
    - dasar akses `wilayah_petugas`
  - Reviewer ter-scope kecamatan:
    - list/rekap `records` & `peta` hanya untuk kecamatan yang berwenang.
  - Foto:
    - Tambah fallback GPS dari EXIF bila memungkinkan (bila disetujui) atau minimal validasi/normalisasi koordinat.
    - Bila record belum punya `gps` dan foto punya `gps_saat_foto`, boleh isi `record.gps` otomatis (opsional) agar `peta` dapat menampilkan titik meski user belum menekan tab GPS.
  - Output `/verval/peta` diperluas (opsional):
    - sertakan ringkasan foto terakhir + koordinat untuk popup.

**E) Pengetatan akses data sensitif**
- `sosial.py`:
  - Ubah `household_allowed` agar `verifikator` tidak otomatis city-wide (harus ikut scope).
- `server.py`:
  - `NGO_ALLOWED_PREFIXES` tetap.
  - Tambahkan `PETUGAS_ALLOWED_PREFIXES` (least privilege):
    - `/api/public/`, `/api/verval/`, `/api/map/config`, `/api/tts` (opsional), dsb.

#### 6.3 Frontend — perubahan yang direncanakan
**A) Routing & Sidebar**
- `frontend/src/App.js`:
  - Definisikan roles baru untuk petugas vs operator RT/RW.
  - Tambahkan guard role petugas untuk mengakses `/verval` & `/verval/sasaran/:ref`.
- `SidebarLayout.js`:
  - Menu untuk petugas disederhanakan:
    - Dashboard Publik
    - Verval/GeoTag

**B) Halaman Kelola Petugas**
- `KelolaPetugas.js`:
  - Mode **Operator**:
    - hanya dapat membuat role `petugas`.
    - form wajib: kelurahan + RW + RT (dan kecamatan auto dari operator).
  - Mode **Superadmin**:
    - tidak ada opsi membuat petugas (bila policy final seperti requirement).

**C) UI Verval (petugas)**
- `VervalOperator.tsx`:
  - Tampilkan koordinat foto di daftar foto (dari `gps_saat_foto`).
  - Pastikan upload mengirim `lat/lng/akurasi_m` (sudah ada untuk operator_rt_rw).

**D) Sinkronisasi ke semua peta**
- `InklusiMap.tsx`: sudah memuat `VervalMapLayer`.
- Tambahan target:
  - `PetaGIS` (engine Google/Leaflet): tambahkan overlay GeoTag melalui `engine.setOverlay`.
  - `KoordinatGIS.tsx`: render `VervalMapLayer` atau layer khusus GeoTag yang memuat titik/foto.

#### 6.4 Testing (fase ini)
- Tambah seed data uji:
  - `households` minimal beberapa baris pada 1 kecamatan (mis. Rappocini) + RT/RW + kode_kelurahan.
- Skenario tes:
  1. Operator membuat petugas → petugas login.
  2. Petugas hanya melihat sasaran dalam kelurahan/RW/RT.
  3. Petugas upload foto + koordinat → muncul pada `/api/verval/peta`.
  4. Verifikator scoped hanya melihat record kecamatan-nya.
  5. Coba akses data kecamatan lain → 403/404.

---

### Phase 7 — P1: Peta Bangunan GeoTag (buka hasil Verval dari peta bangunan) ⏳ BELUM DIMULAI
**User stories**
1. Reviewer/admin dapat membuka peta bangunan dan klik bangunan untuk membuka daftar/hasil Verval terkait.
2. Operator/petugas dapat melihat keterkaitan rumah yang sedang diverval dengan representasi bangunan jika mapping tersedia.

**Implementasi (bergantung data geometri bangunan)**
- Minimal: entry-point UI dari peta bangunan untuk membuka `/verval/review` dengan filter wilayah.
- Penuh: butuh mapping bangunan ↔ `household_id`/`dtsen_ref`.

**Testing**
- Uji klik popup/sidepanel dari peta bangunan membuka halaman review yang tepat.

---

### Phase 8 — P2: Panel Operator Harian (ringkasan progres) ⏳ BELUM DIMULAI
**User stories**
1. Operator/petugas melihat ringkasan harian: draft/terkirim/disetujui/ditolak/perlu_perbaikan.
2. Admin/verifikator melihat progres per operator/petugas (opsional).

**Implementasi**
- Backend: endpoint agregasi (mis. `/api/verval/ringkasan-harian`) per role dan scope.
- Frontend: widget di Dashboard sesuai role.

**Testing**
- Unit test backend agregasi.
- E2E: panel tampil dan angka konsisten dengan data seeded.

## 3) Next Actions (Immediate)
**Prioritas sesuai kebutuhan user terbaru:**
1. **Phase 6 SELESAI** (role petugas/operator/verifikator, scoping wilayah, hasil Verval untuk superadmin & pimpinan, foto+koordinat sinkron ke semua peta).
2. Lanjut sesuai arahan user:
   - **Phase 7 (P1):** Peta Bangunan GeoTag.
   - **Phase 8 (P2):** Panel Operator Harian.

## 4) Success Criteria
✅ Terpenuhi (Phase 1–5):
- Routing/sidebar/RBAC aktif.
- Google basemap Leaflet aktif.
- `VervalMapLayer` tampil dan stabil.
- Form Verval Resmi Komprehensif:
  - 11 variabel + penapisan individu manual + kesimpulan 6 opsi.
  - Strict gating: Foto/GPS/Tinjau terkunci sebelum form lengkap.
  - Backend memblok upload foto sebelum form lengkap.
- Testing: iteration_19/20 lulus.

⬜ Target fase baru (Phase 6):
- Operator dapat membuat akun petugas berbasis kelurahan/RW/RT.
- Petugas hanya bisa akses data publik + modul Verval/GeoTag.
- Operator & verifikator hanya bisa melihat data kecamatan masing-masing.
- Petugas hanya melihat sasaran kelurahan/RW/RT-nya.
- Foto+koordinat yang diupload tersimpan dan tampil konsisten pada:
  - `InklusiMap` layer GeoTag
  - `PetaGIS` overlay GeoTag
  - `KoordinatGIS`
- Tidak ada kebocoran data lintas wilayah (uji negatif menghasilkan 403/404).

⬜ Target berikutnya (Phase 7–8):
- Peta Bangunan menyediakan entry-point cepat ke hasil Verval.
- Dashboard menyediakan panel ringkasan harian progres operator/petugas.
