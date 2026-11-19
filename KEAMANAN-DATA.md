# Keamanan dan Pelindungan Data Pribadi — PETA INKLUSI

Dokumen ini memetakan kontrol keamanan PETA INKLUSI (Bappeda Kota Makassar)
terhadap standar yang berlaku di Indonesia. Sifatnya **pemetaan kepatuhan dan
bukti kontrol**, bukan sertifikasi. Diperbarui 26 Oktober 2026.

---

## 1. Dasar hukum dan standar acuan

| Acuan | Relevansi |
|---|---|
| **UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)** | Dasar utama: hak subjek data, dasar pemrosesan, kewajiban keamanan, notifikasi kebocoran, petugas PDP, transfer lintas negara |
| **PP No. 71 Tahun 2019 tentang Penyelenggaraan Sistem dan Transaksi Elektronik** | Kewajiban penyelenggara sistem elektronik lingkup publik: keamanan, integritas, kerahasiaan, dan akuntabilitas |
| **UU No. 23 Tahun 2006 jo. UU No. 24 Tahun 2013 tentang Administrasi Kependudukan** | NIK, nomor KK, dan data kependudukan hanya boleh diakses pihak berwenang untuk tujuan sah |
| **UU No. 14 Tahun 2008 tentang Keterbukaan Informasi Publik** | Data pribadi dikecualikan dari informasi publik; yang dibuka hanya agregat |
| **UU No. 1 Tahun 2024 (perubahan UU ITE)** | Pertanggungjawaban sistem elektronik dan data |
| **Perpres No. 95 Tahun 2018 (SPBE)** | Tata kelola sistem pemerintahan berbasis elektronik, termasuk keamanan informasi |
| **Perpres No. 39 Tahun 2019 (Satu Data Indonesia)** | Kualitas, standar, dan tata kelola data pemerintah |
| **Peraturan BSSN No. 8 Tahun 2020 tentang Sistem Pengamanan dalam Penyelenggaraan Sistem Elektronik (SPSE)** | Manajemen keamanan sistem elektronik |
| **SNI ISO/IEC 27001:2022** | Kerangka Sistem Manajemen Keamanan Informasi (ISMS) |

---

## 2. Klasifikasi data

| Kelas | Contoh dalam sistem | Perlakuan |
|---|---|---|
| **Data pribadi umum** | Nama, NIK, nomor KK, alamat, tanggal lahir, jenis kelamin, nama orang tua | Hanya untuk staf berwenang; masking untuk peran non-sensitif; audit setiap akses identitas |
| **Data pribadi spesifik** | Data kesehatan (stunting, disabilitas), data anak, status PBI/keuangan | Perlindungan lebih tinggi; akses terbatas; tidak pernah tampil di endpoint publik |
| **Data agregat** | Jumlah KK miskin, jumlah balita stunting per wilayah, total disabilitas | Boleh ditampilkan publik tanpa identitas; tetap dijaga dari re-identifikasi |
| **Data program/anggaran** | Matriks OPPKPKE, program ATS, program stunting | Publik/internal sesuai peran; bukan data pribadi |

Prinsip yang diterapkan: **legalitas, pembatasan tujuan, minimalisasi, akurasi,
pembatasan retensi, keamanan, dan akuntabilitas** (UU PDP Pasal 16–20, 35).

---

## 3. Dasar pemrosesan dan transparansi

- Pemrosesan data warga untuk perencanaan pembangunan, verifikasi DTSEN, dan
  program perlindungan sosial berlandaskan **tugas pemerintahan/legal obligation**
  (UU PDP Pasal 20), bukan sekadar persetujuan.
- Data yang dikumpulkan dibatasi pada yang diperlukan untuk program.
- Halaman publik hanya menampilkan **agregat**; data individu tidak diekspos.
- Pendaftaran akun petugas/NGO memerlukan persetujuan admin dan verifikasi wilayah.

---

## 4. Kontrol keamanan yang sudah diterapkan

### 4.1 Akses dan otorisasi

| Kontrol | Implementasi |
|---|---|
| RBAC + least privilege | 13 peran di `frontend/src/constants/roles.js` dan penjagaan rute/endpoint di backend |
| Pembatasan wilayah | `backend/scope.py`; operator/petugas hanya kecamatan/kelurahan tugasnya |
| Masking data pribadi | `mask_household` (nama, KK, alamat), `mask_name`/`mask_address` untuk data balita |
| Data individu wajib login | `/api/sosial/households*` dan `/api/inklusi/stunting/children` menolak pengguna anonim |
| Audit akses identitas | Setiap akses data sensitif dicatat di `audit_logs` (pengguna, waktu, filter, jumlah) |
| Ekspor terkendali | `/api/export/excel` wajib login dan dicatat di audit |

### 4.2 Autentikasi dan sesi

| Kontrol | Implementasi |
|---|---|
| Hash kata sandi | bcrypt (`backend/auth.py`) |
| Kebijakan kata sandi | minimal 10 karakter, harus huruf + angka, menolak kata sandi umum |
| Anti brute force | maksimal 5 percobaan per IP+email per 15 menit; kunci 15 menit (`login_attempts`) |
| Anti user-enumeration | bcrypt tiruan dijalankan saat email tidak ditemukan |
| Token | JWT HS256, kedaluwarsa 8 jam (`ACCESS_TOKEN_HOURS`), memuat `iat`/`jti` |
| Cookie | `HttpOnly`, `Secure` (produksi), `SameSite=Lax` (dapat diatur) |
| Logout | Menghapus cookie akses dan refresh |

### 4.3 Proteksi aplikasi

| Kontrol | Implementasi |
|---|---|
| CSRF | Permintaan `POST/PUT/PATCH/DELETE` dicek `Origin`/`Referer`; origin asing ditolak 403 |
| CORS | Allowlist eksplisit; wildcard `*` tidak dipakai untuk permintaan berkredensial |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `X-Permitted-Cross-Domain-Policies` |
| CSP | `default-src 'self'` + allowlist Google Maps, unpkg (Leaflet), Google Fonts, YouTube/Vimeo |
| HSTS | Dikirim saat permintaan melalui HTTPS |
| Cache data pribadi | `Cache-Control: no-store` pada auth, rumah tangga, balita, admin, audit |
| Integritas aset CDN | Leaflet 1.9.4 memakai Subresource Integrity (SRI) |
| Header server | Uvicorn dijalankan dengan `--no-server-header` pada image produksi |

### 4.4 Infrastruktur dan operasi

| Kontrol | Status |
|---|---|
| TLS/HTTPS | Wajib di reverse proxy produksi (Coolify/Nginx); HSTS aktif saat HTTPS |
| Rahasia | `JWT_SECRET`, `DB_PASSWORD`, `ADMIN_PASSWORD`, kunci AI/Maps hanya di env; `.env` tidak di-commit |
| Tanpa password default | `auth.seed_admin` tidak membuat akun bila `ADMIN_PASSWORD` kosong |
| Database | MariaDB terpusat; akses dibatasi kredensial aplikasi |
| Log aplikasi | Uvicorn mencatat metode/path/status, bukan isi data pribadi |
| Snapshot data | `backend/data_resmi/` hanya memuat matriks program/anggaran; koleksi berisi data pribadi tidak pernah diekspor |
| Backup | Tanggung jawab operasional (harus terenkripsi dan diuji restore) |

---

## 5. Hak subjek data (UU PDP Pasal 5–13)

| Hak | Mekanisme |
|---|---|
| Informasi dan transparansi | Halaman publik hanya agregat; dokumentasi ini dan `DATA-SUMBER.md` |
| Akses data | Permohonan melalui kanal resmi Bappeda; admin menelusuri `households`/`stunting_children` dengan audit |
| Koreksi | Alur Verval/Verifikasi Data dan penyuntingan data wilayah |
| Penghapusan | Dilakukan oleh admin setelah verifikasi dasar hukum dan persetujuan Pengendali |
| Penarikan persetujuan | Untuk data yang dasarnya persetujuan (mis. foto cerita dampak) |
| Keberatan atas pemrosesan | Diajukan ke Pengendali/Petugas PDP |

Permohonan diverifikasi identitasnya, dicatat, dan diselesaikan sesuai tenggat
UU PDP. **Petugas Pelindungan Data Pribadi (DPO)** ditetapkan melalui keputusan
Kepala Bappeda (UU PDP Pasal 52–54) dan menjadi kontak resmi permohonan.

---

## 6. Retensi dan pemusnahan

| Data | Masa simpan | Tindakan |
|---|---|---|
| Data individu DTSEN/balita | Selama diperlukan untuk verifikasi dan program; ditinjau setiap tahun | Dihapus atau dianonimkan setelah tidak diperlukan, kecuali diwajibkan arsip |
| Audit log | Mengikuti Jadwal Retensi Arsip (JRA) Bappeda; minimal selama periode audit | Diarsipkan/dihapus sesuai JRA |
| Data agregat | Tidak dibatasi | Tetap sebagai statistik pembangunan |
| Berkas impor sementara | Maksimal 30 hari | Dibersihkan dari `data_upload/_uploads` |

Penghapusan harus tercatat (data apa, kapan, oleh siapa, dasar hukumnya).

---

## 7. Penanganan insiden kebocoran

1. **Deteksi dan containment** — cabut sesi/kunci, blokir akses, simpan bukti log.
2. **Analisis** — tentukan jenis data, jumlah subjek, dampak, dan penyebab.
3. **Notifikasi** — sesuai UU PDP Pasal 46, beri tahu subjek data dan lembaga
   pengawas **paling lambat 3×24 jam** sejak diketahui, memuat data yang terdampak,
   waktu, dan upaya pemulihan.
4. **Pemulihan** — perbaiki akar masalah, rotasi kredensial, uji ulang.
5. **Dokumentasi** — catat kronologi, keputusan, dan pelajaran pada register insiden.

Kontak insiden: Petugas PDP Bappeda Kota Makassar dan admin sistem (kanal resmi
Bappeda). Jangan mengirim data pribadi melalui saluran yang tidak terenkripsi.

---

## 8. Pihak ketiga dan transfer lintas negara

| Pihak | Data | Catatan |
|---|---|---|
| Google Maps | Koordinat/titik peta | Jangan kirim nama/NIK/alamat lengkap; pertimbangkan tile on-prem untuk lokasi sensitif |
| Hostlinku (AI) | Pertanyaan pengguna dan ringkasan agregat | Jangan kirim data pribadi; tinjau perjanjian pemrosesan |
| SMTP/email | Nama dan email penerima | Gunakan TLS; batasi isi email |
| YouTube/Vimeo | Video BISINDO publik | Tanpa data warga |

Transfer ke luar Indonesia (UU PDP Pasal 55–56) hanya boleh bila ada tingkat
pelindungan yang setara atau perlindungan memadai. Mitigasi utama: **tidak
mengirim data pribadi** ke layanan eksternal.

---

## 9. Kesenjangan dan rencana perbaikan

| Prioritas | Kesenjangan | Rencana |
|---|---|---|
| Tinggi | MFA belum ada untuk admin | Tambahkan TOTP/WebAuthn untuk `superadmin`/`admin` |
| Tinggi | Enkripsi at-rest & backup belum diverifikasi | Aktifkan enkripsi disk/TDE MariaDB, backup terenkripsi, uji restore |
| Tinggi | DPIA belum disusun | Lakukan DPIA untuk data kesehatan, disabilitas, dan anak |
| Sedang | Retensi otomatis belum ada | Buat job pembersihan + register penghapusan |
| Sedang | Small-cell suppression | Sembunyikan sel <5 pada peta publik untuk mencegah re-identifikasi |
| Sedang | CSP masih memakai `unsafe-inline`/`unsafe-eval` | Migrasi ke nonce/hash setelah Google Maps & inline script dipisah |
| Sedang | Privacy notice & consent foto | Tambahkan pemberitahuan privasi dan persetujuan foto cerita dampak |
| Rendah | Log terpusat/SIEM | Kirim audit log ke penyimpanan append-only |
| Rendah | Uji penetrasi | Lakukan pentest tahunan oleh pihak independen |

---

## 10. Bukti pengujian

```bash
cd backend
python uji_keamanan.py --base http://127.0.0.1:8001
```

Memeriksa: header keamanan/CSP, penolakan akses anonim ke data pribadi, ekspor
wajib login, CSRF, rate limit, kebijakan kata sandi, endpoint publik tanpa kunci
data pribadi, dan CORS.

Hasil terakhir (26 Oktober 2026): **18/18 lulus**.

Pemeriksaan lain:

```bash
node scripts/cek-menu.mjs
bash scripts/a11y-smoke.sh
node scripts/uji-navigasi.mjs --axe
node scripts/uji-navigasi.mjs --peran=superadmin
```

---

## 11. Catatan

- Dokumen ini adalah **pemetaan kontrol**, bukan pernyataan sertifikasi ISO 27001
  atau audit kepatuhan independen.
- Status kepatuhan akhir tetap memerlukan penetapan DPO, DPIA, kebijakan retensi,
  perjanjian pemrosesan dengan pihak ketiga, dan audit berkala oleh Pengendali.
- Rincian sumber data dan hasil audit angka ada di [`DATA-SUMBER.md`](DATA-SUMBER.md).
