# Snapshot Data Resmi (Non-Pribadi)

Folder ini memuat salinan **data program/anggaran** hasil impor resmi agar
deployment baru tidak kehilangan angka ketika basis data masih kosong.

| Berkas | Isi | Jumlah | Sumber |
|---|---|---|---|
| `oppkpke_2026_semester1.json` | Matriks Evaluasi OPPKPKE Semester 1 2026 | 68 kegiatan, 39 OPD | Kertas kerja resmi OPPKPKE (diimpor 26 Okt 2026) |
| `ats_program_2025_2027.json` | Matriks Program, Kegiatan, dan Anggaran ATS | 17 program, 11 OPD | Matriks resmi Program ATS |
| `disabilitas_monev_2026.json` | Matriks monev kegiatan disabilitas per OPD | 61 kegiatan, 21 OPD | Berkas monev disabilitas (diimpor 27 Okt 2026) |
| `musrenbang_2027.json` | Usulan dan intervensi Musrenbang Tematik RKPD 2027 | 64 usulan, 11 intervensi | Matriks Musrenbang Tematik 26 Nov 2025 |

Angka kunci:

- OPPKPKE: anggaran Rp213.914.294.961; realisasi Semester 1 2025
  Rp77.347.658.086; total realisasi 2025 Rp79.174.126.109.
- Program ATS: 2025 Rp2.988.051.880 (realisasi Rp2.772.626.058);
  2026 Rp15.111.752.700 (realisasi Semester 1 Rp1.965.703.256).
- Monev Disabilitas: anggaran 2025 Rp132.697.780.968 (realisasi Rp10.004.192.555,
  7,54%); anggaran 2026 Rp264.834.535.959 (realisasi Rp7.478.840.305).
- Musrenbang Tematik 2027: 64 usulan pada 4 kelompok kepentingan; 11 intervensi
  dari 3 OPD dengan total anggaran usulan Rp176.440.000.

## Kenapa berkas lain tidak ada di sini?

`households`, `stunting_children`, `users`, `audit_logs`, dan koleksi lain yang
memuat data pribadi **tidak pernah** diekspor ke repositori. Data tersebut tetap
di basis data produksi dan dilindungi sesuai `KEAMANAN-DATA.md`.

Berkas sumber asli (DTSEN, PDF balita, DINKES) juga tidak disalin ke repo.

## Cara memakai

```bash
cd backend

# Menulis ulang snapshot dari basis data (hanya koleksi matriks)
python snapshot_data_resmi.py --export

# Mengisi koleksi yang masih kosong (tidak menimpa data yang sudah ada)
python snapshot_data_resmi.py --load

# Snapshot Musrenbang ditulis/dimuat melalui modulnya sendiri
python musrenbang.py --file "/path/Matriks Musrenbang Tematik.xlsx"   # impor + snapshot
python musrenbang.py --file "/path/berkas.xlsx" --snapshot             # hanya tulis snapshot
```

Saat aplikasi start, snapshot dimuat otomatis **hanya bila** koleksi
`oppkpke_items` atau `ats_program_items` masih kosong.

Setiap dokumen menyimpan `sumber_berkas` dan `sumber_hash` (SHA-256) sebagai
jejak integritas. Rincian audit lengkap ada di `../DATA-SUMBER.md`.
