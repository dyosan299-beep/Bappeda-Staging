# Uji Aksesibilitas — PETA INKLUSI

Panduan uji manual untuk memverifikasi hasil pekerjaan aksesibilitas (WCAG 2.2 level AA).
Semua langkah di bawah dirancang agar bisa dijalankan tanpa alat berbayar.

> **Penting:** pemeriksaan otomatis hanya menangkap sebagian masalah. `axe` bisa
> mendeteksi kontras, nama aksesibel, dan struktur, tetapi **tidak bisa** menilai
> apakah alur masuk akal atau apakah pembaca layar membacakan sesuatu dengan urutan
> yang wajar. Uji manual tetap wajib sebelum dinyatakan selesai.

---

## 1. Yang sudah diotomatiskan

| Alat | Cakupan | Status terakhir |
|---|---|---|
| `scripts/a11y-smoke.sh` | 13 halaman dimuat tanpa error runtime | LULUS 13/13 |
| `axe-core` WCAG 2.0–2.2 A/AA | 5 halaman publik @ 1280px dan 375px | 0 violation |
| `scripts/uji-navigasi.mjs --axe` | Dashboard, Mode Aksesibilitas, Laporan, Impor & Kualitas Data @ 1280px & 375px | 0 violation |
| `scripts/cek-menu.mjs` | Susunan 9 kelompok, 42 item menu, rute tujuan, dan hak akses per peran | LULUS |
| `scripts/uji-navigasi.mjs --peran=…` | Seluruh item sidebar dapat dibuka per peran (superadmin, verifikator, petugas, ngo) + tab hub | LULUS |
| `yarn build` | Kompilasi produksi | sukses |

Menjalankan smoke test (butuh dev server atau build yang disajikan):

```bash
./scripts/a11y-smoke.sh
# atau terhadap server lain:
BASE_URL=https://peta-inklusi.makassarkota.go.id ./scripts/a11y-smoke.sh
```

Menjalankan pemeriksaan navigasi (memakai build + API tiruan, tidak menyentuh basis data):

```bash
cd frontend && yarn build && cd ..
node scripts/cek-menu.mjs
node scripts/uji-navigasi.mjs                    # rute publik
node scripts/uji-navigasi.mjs --axe              # audit axe halaman baru
node scripts/uji-navigasi.mjs --peran=superadmin # telusuri seluruh menu
node scripts/uji-navigasi.mjs --peran=ngo
```

Menjalankan axe tanpa menambah dependency permanen:

```bash
npx --yes @axe-core/cli http://localhost:3000 --tags wcag2a,wcag2aa,wcag21aa,wcag22aa
```

**Halaman yang belum diaudit otomatis:** semua halaman di balik login
(`/dashboard`, `/disabilitas`, `/kelola-petugas`, `/verval`, `/impor`, peta internal).
Perlu satu sesi login untuk mengauditnya.

---

## 2. Uji keyboard (tanpa mouse)

Lakukan di Chrome/Edge. Jangan menyentuh mouse sama sekali.

| # | Langkah | Hasil yang diharapkan |
|---|---|---|
| 1 | Buka halaman mana pun, tekan **Tab** sekali | Muncul tautan **"Lewati ke konten utama"** di kiri atas. Fokus terlihat jelas (cincin amber). |
| 2 | Tekan **Enter** pada tautan itu | Fokus pindah ke area konten, bukan ke menu. |
| 3 | Tab terus melewati menu | Setiap item menu menampilkan cincin fokus. Item aktif ditandai garis kiri putih + teks tebal, **bukan hanya warna**. |
| 4 | Di kotak **Cari menu**, ketik "petugas" | Daftar menyempit; jumlah hasil diumumkan. Tekan **Esc** → kotak kosong. |
| 5 | Perkecil jendela < 1024px, tab ke tombol menu, tekan **Enter** | Menu terbuka; fokus **masuk** ke dalam menu. |
| 6 | Tekan **Esc** | Menu tertutup; fokus **kembali** ke tombol menu. |
| 7 | Di Kelola Petugas, tab ke tombol ikon hapus, tekan **Enter** | Muncul dialog konfirmasi. **Esc** menutup dialog dan fokus kembali ke tombol hapus. |
| 8 | Buka dialog Edit, tekan Tab berkali-kali | Fokus **tidak keluar** dari dialog (focus trap). Esc menutup. |
| 9 | Buka `/disabilitas`, tab ke bawah setiap grafik | Ada tombol **"Tampilkan tabel data"**; Enter membuka tabel. |
| 10 | Di halaman peta, fokuskan peta lalu tekan **panah** | Peta bergeser. Tombol zoom berlabel "Perbesar peta"/"Perkecil peta". |
| 11 | Di `/login`, klik **Masuk** dengan form kosong | Muncul ringkasan error + pesan per kolom; fokus pindah ke kolom pertama yang salah. |

---

## 3. Uji pembaca layar — NVDA (Windows, gratis)

Unduh: https://www.nvaccess.org/download/ — jalankan dengan Chrome.

| # | Langkah | Hasil yang diharapkan |
|---|---|---|
| 1 | Muat halaman, tekan **Insert+Down** (baca semua) | Membacakan judul halaman, lalu `h1` yang sama dengan judul tab. Tidak ada menu yang dibacakan dua kali. |
| 2 | Tekan **H** berulang | Berpindah antar-heading berurutan (h1 → h2 → h3), tidak melompat. |
| 3 | Tekan **D** berulang | Berpindah antar-landmark: "banner", "navigation", "main", "content information" (footer). |
| 4 | Fokus ke lonceng notifikasi | Dibacakan nama + jumlah, mis. "Kelola petugas — 3 akun menunggu persetujuan, tombol". |
| 5 | Munculkan notifikasi (mis. simpan berhasil) | Pesan dibacakan otomatis tanpa memindahkan fokus. |
| 6 | Buka dialog Hapus petugas | Dibacakan judul dialog, nama akun, dan akibatnya; fokus berada di dalam dialog. |
| 7 | Di tabel Kelola Petugas (desktop) | Dibacakan nama kolom saat berpindah sel. |
| 8 | Kecilkan ke < 768px, ulangi tabel | Setiap sel dibacakan beserta labelnya ("Nama: Budi"). |

## 4. Uji pembaca layar — TalkBack (Android, gratis)

Aktifkan: Setelan → Aksesibilitas → TalkBack, lalu buka Chrome.

| # | Langkah | Hasil yang diharapkan |
|---|---|---|
| 1 | Geser satu jari ke kanan berurutan | Urutan fokus mengikuti visual: skip link → header → menu → konten. |
| 2 | Buka menu hamburger (dua kali ketuk) | Menu terbuka, fokus pindah ke tombol tutup di dalam menu. |
| 3 | Geser ke tombol ikon hapus | Dibacakan "Hapus petugas {nama}, tombol". |
| 4 | Di grafik, ketuk tombol "Tampilkan tabel data" | Tabel terbuka dan bisa dibaca per sel. |
| 5 | Di peta, gunakan tombol zoom | Tombol dibacakan "Perbesar peta". |
| 6 | Putar perangkat ke landscape | Tata letak menyesuaikan; tidak ada konten terpotong. |

---

## 5. Uji suara di perangkat (Android, iPad, tablet)

Suara memakai mesin TTS bawaan perangkat lewat Web Speech API. Karena itu perangkat
**wajib punya data suara Bahasa Indonesia**; tanpa itu `speak()` tidak menghasilkan bunyi.
Panel aksesibilitas → tab **Tampilan** menampilkan nama suara yang terpakai, atau peringatan
bila suara Bahasa Indonesia belum ada.

Menyiapkan perangkat:

| Perangkat | Langkah memasang suara Indonesia |
|---|---|
| Android | Setelan → Sistem → Bahasa & masukan → Output teks-ke-ucapan → Mesin sintesis Google → Pasang data suara → Bahasa Indonesia |
| iPad / iPhone | Setelan → Aksesibilitas → Konten yang Diucapkan → Suara → Indonesia |
| Tablet Windows | Setelan → Waktu & bahasa → Bahasa → Indonesia → pasang paket suara |

| # | Langkah | Hasil yang diharapkan |
|---|---|---|
| 1 | Ketuk widget **Aksesibilitas** → tab **Tampilan** | Muncul baris “Suara perangkat: … (id-ID)”. Bila belum ada, muncul petunjuk memasang suara. |
| 2 | Ketuk **Coba suara** | Suara Bahasa Indonesia berbunyi tanpa jeda jaringan. |
| 3 | Tab **Disabilitas Buta** → **Bacakan Halaman** | Suara mulai **pada ketukan pertama** (bukan ketukan kedua) dan status berubah ke “Membacakan…”. |
| 4 | Ketuk **Jeda**, lalu **Lanjutkan** | Suara berhenti, lalu melanjutkan dari bagian yang tertunda. |
| 5 | Ketuk **Berhenti** | Suara berhenti dan status kembali “Siap”. |
| 6 | Tekan tombol kunci layar saat halaman dibacakan, lalu buka lagi | Status tidak tertahan di “Membacakan…”. |
| 7 | Matikan volume / aktifkan mode senyap, lalu Bacakan lagi | Muncul peringatan “Suara belum berbunyi” + tombol **Coba bacakan lagi**. |
| 8 | Putar perangkat ke landscape | Panel dan subtitle menyesuaikan, tidak ada teks terpotong. |

Catatan: iOS/iPadOS mewajibkan pemutaran suara dimulai dari sentuhan pengguna. Bila suara
tetap tidak keluar, ketuk **Coba bacakan lagi** pada peringatan yang muncul.

---

## 6. Zoom 400% dan 200%

| # | Langkah | Hasil yang diharapkan |
|---|---|---|
| 1 | Chrome, jendela 1280px, tekan **Ctrl+** sampai zoom 400% | Tidak ada scroll horizontal pada konten biasa. Peta dan tabel besar boleh bergulir sendiri. |
| 2 | Zoom 200% di `/login` | Semua tombol bisa dibaca dan ditekan; tidak ada teks terpotong. |
| 3 | Perbesar teks saja (Firefox: View → Zoom → Zoom Text Only, 200%) | Tidak ada teks yang keluar dari wadahnya. |

## 7. Text spacing (WCAG 1.4.12)

Buka DevTools → Console di halaman mana pun, tempel:

```js
const s = document.createElement('style');
s.textContent = `body, body * {
  line-height: 1.5 !important;
  letter-spacing: 0.12em !important;
  word-spacing: 0.16em !important;
}
p { margin-bottom: 2em !important; }`;
document.head.appendChild(s);
```

Hasil yang diharapkan: tidak ada teks yang terpotong atau tumpang tindih.

## 8. Mode kontras tinggi

| # | Langkah | Hasil yang diharapkan |
|---|---|---|
| 1 | Windows: Alt+Kiri+Shift+PrintScreen (High Contrast) | Semua teks terbaca; border input tetap terlihat; fokus terlihat. |
| 2 | Aplikasi: klik widget hijau → tab Tampilan → aktifkan **Kontras Tinggi** | Sama seperti di atas, dan setelan tersimpan setelah refresh. |
| 3 | Aktifkan **Teks Ekstra Besar** di widget | Tidak ada label kecil yang tertinggal; tabel dan menu tetap terbaca. |

---

## 9. Yang masih perlu keputusan produk (bukan bug)

| Hal | Status | Catatan |
|---|---|---|
| Halaman Bantuan/Kontak | Belum ada | `/bantuan` adalah **Bantuan Sosial**, bukan panduan. WCAG 3.2.6 belum sepenuhnya terpenuhi. |
| Peringatan timeout sesi | Belum ada | Cookie 12 jam; WCAG 2.2.1 menyarankan peringatan + opsi perpanjang. |
| Tooltip grafik di layar sentuh | Alternatif tabel tersedia | Brief meminta panel tetap di bawah grafik; saat ini datanya diakses lewat "Tampilkan tabel data". |
| Tabel selain Kelola Petugas | Belum pola kartu | `.table-cards` baru dipakai di Kelola Petugas. Tabel lain masih bergulir horizontal di dalam wadahnya. |
| Konfigurasi ESLint | Belum ada | `eslint-plugin-jsx-a11y` sudah terpasang tetapi tidak dikonfigurasi, jadi tidak ada lint aksesibilitas otomatis. |

---

## 10. Melaporkan temuan

Saat menemukan masalah, catat: **halaman**, **langkah reproduksi**, **alat** (keyboard/NVDA/TalkBack/zoom),
dan **kriteria WCAG** yang dilanggar bila diketahui. Contoh:

> `/kelola-petugas` — Tab ke tombol hapus pada baris kedua — NVDA 2024.4 — fokus hilang
> setelah dialog ditutup — WCAG 2.4.3 (Focus Order).
