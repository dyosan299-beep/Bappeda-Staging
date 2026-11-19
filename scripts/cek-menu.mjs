/**
 * Pemeriksa konsistensi navigasi PETA INKLUSI.
 *
 *   node scripts/cek-menu.mjs
 *
 * Memastikan:
 *  1. Susunan 9 kelompok menu sesuai dokumen "Urutan Menu PETA INKLUSI" bagian 2.
 *  2. Setiap tujuan menu benar-benar punya rute di frontend/src/App.js.
 *  3. Tidak ada tujuan ganda dalam satu kelompok untuk satu peran.
 *  4. Setiap peran hanya melihat menu yang diizinkan (tidak ada kebocoran hak akses).
 *
 * Berkas ini hanya membaca sumber; tidak menyentuh basis data.
 */
import { copyFileSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const AKAR = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const SRC = join(AKAR, "frontend", "src");
const tmp = mkdtempSync(join(tmpdir(), "cek-menu-"));

// Salin sebagai .mjs agar Node memperlakukannya sebagai ESM (paket ini bukan type=module).
writeFileSync(join(tmp, "roles.mjs"), readFileSync(join(SRC, "constants", "roles.js"), "utf8"));
writeFileSync(
  join(tmp, "menu.mjs"),
  readFileSync(join(SRC, "constants", "menu.js"), "utf8").replace('from "./roles.js"', 'from "./roles.mjs"'),
);

const { MENU, UTILITY_ITEMS, menuDatar, judulHalaman } = await import(pathToFileURL(join(tmp, "menu.mjs")).href);

const HARAP = [
  "Ringkasan",
  "Petugas dan Wilayah Tugas",
  "Pendataan Warga",
  "Verifikasi dan Pemutakhiran Data",
  "Peta dan Kebutuhan Wilayah",
  "Program dan Intervensi",
  "Monitoring, Evaluasi dan Laporan",
  "Administrasi Sistem",
  "Bantuan dan Aksesibilitas",
];

const appJs = readFileSync(join(SRC, "App.js"), "utf8");
const rute = new Set([...appJs.matchAll(/path="([^"]+)"/g)].map((m) => m[1]));

let gagal = 0;
const cek = (nama, lulus, info = "") => {
  if (!lulus) gagal += 1;
  console.log(`${lulus ? "PASS" : "FAIL"}  ${nama}${info ? `  [${info}]` : ""}`);
};

// 1. Susunan kelompok
cek("jumlah kelompok = 9", MENU.length === 9, `ditemukan ${MENU.length}`);
MENU.forEach((g, i) => cek(`kelompok ${i + 1} = "${HARAP[i]}"`, g.label === HARAP[i], g.label));

// 2. Tujuan menu punya rute
const semuaItem = [...MENU.flatMap((g) => g.items), ...UTILITY_ITEMS];
const tujuan = [...new Set(semuaItem.map((n) => n.to))];
const tanpaRute = tujuan.filter((t) => !rute.has(t));
cek("semua tujuan menu punya rute", tanpaRute.length === 0, tanpaRute.join(", ") || "lengkap");
cek("seluruh menu lama terpetakan (>= 37)", semuaItem.length >= 37, `${semuaItem.length} item`);

// 3. Duplikat dalam satu kelompok (untuk peran yang sama)
const PERAN = ["superadmin", "admin", "verifikator", "admin_bappeda", "operator", "pimpinan",
  "admin_opd", "operator_kecamatan", "operator_kelurahan", "viewer", "petugas", "operator_rt_rw", "ngo"];

let duplikat = [];
PERAN.forEach((role) => {
  MENU.forEach((g) => {
    const terlihat = g.items.filter((n) => !n.roles || n.roles.includes(role));
    const to = terlihat.map((n) => n.to);
    const ganda = to.filter((t, i) => to.indexOf(t) !== i);
    if (ganda.length) duplikat.push(`${role}/${g.label}: ${ganda.join(",")}`);
  });
});
cek("tidak ada tujuan ganda per peran", duplikat.length === 0, duplikat.join(" | ") || "bersih");

// 4. Hak akses per peran
const HARAP_PERAN = {
  verifikator: ["Dashboard", "Verifikasi Data", "Hasil Verifikasi Data", "Peran & Hak Akses", "Audit Log", "Video BISINDO"],
  operator: ["Input Data", "Validasi Akun Petugas", "Manajemen Pengguna", "Titik Koordinat Kelurahan"],
  pimpinan: ["Dashboard", "Laporan", "Ringkasan Mingguan", "Prioritas Intervensi"],
  ngo: ["Peta Sosial", "Peta Kemiskinan", "Status Pengajuan Saya", "Ajukan Pengajuan", "Laporan", "Statistik Agregat"],
  operator_rt_rw: ["Verval & GeoTag"],
  petugas: ["Verval & GeoTag"],
};
Object.entries(HARAP_PERAN).forEach(([role, wajib]) => {
  const label = menuDatar({ role }).map((n) => n.label);
  const hilang = wajib.filter((w) => !label.includes(w));
  cek(`menu ${role} lengkap`, hilang.length === 0, hilang.join(", ") || `${label.length} item`);
});

// 5. Peran terbatas tidak bocor ke menu internal
const bocor = menuDatar({ role: "operator_rt_rw" }).filter((n) => n.to !== "/verval" && n.to !== "/publik");
cek("operator_rt_rw tidak melihat menu internal lain", bocor.length === 0, bocor.map((n) => n.label).join(", ") || "bersih");
const ngoInternal = menuDatar({ role: "ngo" }).filter((n) => !n.to.startsWith("/ngo") && !["/laporan", "/publik"].includes(n.to));
cek("ngo tidak melihat menu internal", ngoInternal.length === 0, ngoInternal.map((n) => n.label).join(", ") || "bersih");

// 6. Judul halaman turunan
cek("judul /rekap = Laporan", judulHalaman("/rekap", { role: "admin" }) === "Laporan");
cek("judul /validasi-akun", judulHalaman("/validasi-akun", { role: "admin" }) === "Validasi Akun Petugas");
cek("judul /verval/sasaran/x", judulHalaman("/verval/sasaran/abc", { role: "petugas" }) === "Formulir Verval DTSEN");

console.log(`\n${gagal === 0 ? "LULUS" : `GAGAL: ${gagal} pemeriksaan`} — ${semuaItem.length} item menu, ${tujuan.length} tujuan unik.`);
process.exit(gagal === 0 ? 0 : 1);
