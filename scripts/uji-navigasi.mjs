/**
 * Uji navigasi PETA INKLUSI terhadap build produksi.
 *
 *   node scripts/uji-navigasi.mjs                 # rute publik saja
 *   node scripts/uji-navigasi.mjs --peran=superadmin
 *
 * Skrip menyalakan server statis sementara untuk `frontend/build` dengan:
 *  - fallback SPA (semua rute → index.html),
 *  - `GET /api/auth/me` tiruan sesuai `--peran` (tanpa menyentuh basis data),
 *  - endpoint `/api/*` lain dibalas 404 JSON.
 *
 * Dengan `--peran`, skrip membuka aplikasi di dalam iframe lalu menelusuri
 * seluruh item sidebar: memastikan 9 kelompok tampil, setiap tujuan menu dapat
 * dibuka, judul halaman sesuai label menu, serta tab pada hub Laporan dan
 * Impor & Kualitas Data berfungsi.
 */
import { execFile } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdtempSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join } from "node:path";
import { promisify } from "node:util";
import { pathToFileURL } from "node:url";

const AKAR = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const BUILD = join(AKAR, "frontend", "build");
const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const jalankan = promisify(execFile);

const argPeranAwal = (process.argv.find((a) => a.startsWith("--peran=")) || "").split("=")[1];
const modeAxe = process.argv.includes("--axe");
const argPeran = argPeranAwal || (modeAxe ? "superadmin" : "");
const PERAN = {
  superadmin: { id: "uji-1", name: "Uji Superadmin", email: "uji@example.go.id", role: "superadmin", status: "active", wilayah: "Kota Makassar" },
  verifikator: { id: "uji-2", name: "Uji Verifikator", email: "verifikator@example.go.id", role: "verifikator", status: "active", wilayah: "Tallo" },
  petugas: { id: "uji-3", name: "Uji Petugas", email: "petugas@example.go.id", role: "petugas", status: "active", wilayah: "Tallo", kelurahan: "Buloa", rw: "01", rt: ["01"] },
  ngo: { id: "uji-4", name: "Uji NGO", email: "ngo@example.go.id", role: "ngo", status: "active", organisasi: "Yayasan Uji" },
};

const MIME = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
  ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg", ".webp": "image/webp", ".ico": "image/x-icon", ".woff": "font/woff",
  ".woff2": "font/woff2", ".ttf": "font/ttf", ".map": "application/json", ".txt": "text/plain",
};

// Data tiruan khusus halaman Matriks supaya tabel benar-benar ikut diaudit axe.
const MATRIKS_KATEGORI = {
  sumber: "Matriks Kemiskinan, Stunting, ATS dan Anak Jalanan - Bappeda Kota Makassar",
  jumlah_kecamatan: 2,
  items: [
    { kecamatan: "Mariso", jumlah_kelurahan: 9, kemiskinan_ekstrim_kk: 500, kemiskinan_persen: 6.2, stunting_anak: 120, ats: 720, anak_jalanan: 6, disabilitas: 190 },
    { kecamatan: "Tallo", jumlah_kelurahan: 15, kemiskinan_ekstrim_kk: 2907, kemiskinan_persen: 8.6, stunting_anak: 316, ats: 2240, anak_jalanan: 12, disabilitas: 610 },
  ],
  total: { kecamatan: "TOTAL", jumlah_kelurahan: 24, kemiskinan_ekstrim_kk: 3407, kemiskinan_persen: null, stunting_anak: 436, ats: 2960, anak_jalanan: 18, disabilitas: 800 },
};

const MATRIKS_OPPKPKE = {
  jenis: "oppkpke", label: "Evaluasi OPPKPKE", tersedia: true,
  periode: { semester: 1, tahun: 2026 },
  items: [
    { id: "m1", no: 1, strategi: "Pengurangan beban pengeluaran masyarakat", opd: "Dinas Kependudukan dan Pencatatan Sipil", program: "Program Pendaftaran Penduduk", sub_kegiatan: "Pendataan Penduduk Non Permanen", aktivitas_langsung: "12 kali", aktivitas_tidak_langsung: "-", aktivitas_penunjang: "-", anggaran: 12544640, sumber_pembiayaan: "APBD", sifat_bantuan: "Layanan langsung", lokasi: "Tallo, Tamalate, Panakkukang", jumlah_sasaran: "120 Orang", besaran_manfaat: "Rp 350.000/orang", jenis_bantuan: "Kepemilikan dokumen kependudukan", durasi: "12 bulan", realisasi_sem1_2025: 3000000, total_realisasi_2025: 12453300, target_2026: "120 Orang", semester: 1, tahun: 2026 },
    { id: "m2", no: 2, strategi: "Penghapusan kantong-kantong kemiskinan", opd: "Dinas Sosial", program: "Program Rehabilitasi Sosial", sub_kegiatan: "Penyediaan Permakanan", aktivitas_langsung: "48 kali", aktivitas_tidak_langsung: "0", aktivitas_penunjang: "0", anggaran: 50000000, sumber_pembiayaan: "APBD", sifat_bantuan: "Pemberian bantuan permakanan", lokasi: "Kota Makassar", jumlah_sasaran: "150 orang", besaran_manfaat: "Rp 20.000/hari", jenis_bantuan: "Permakanan", durasi: "6 bulan", realisasi_sem1_2025: 40000000, total_realisasi_2025: 45000000, target_2026: "150 Orang", semester: 1, tahun: 2026 },
  ],
  ringkasan: {
    jumlah_kegiatan: 2, jumlah_opd: 2, jumlah_program: 2,
    total_anggaran: 62544640, total_realisasi_sem1_2025: 43000000,
    total_realisasi_2025: 57453300, periode: { semester: 1, tahun: 2026 }, diperbarui: null,
  },
};

const MATRIKS_ATS = {
  jenis: "ats-program", label: "Program Kegiatan ATS", tersedia: true,
  periode: { tahun: 2026 }, tahun_tersedia: [2025, 2026, 2027],
  items: [
    { id: "a1", no: 1, sasaran: "Meningkatnya satuan pendidikan SD/MI berpihak pada ATS", program: "Program Pengelolaan Pendidikan", kegiatan: "Pengelolaan Pendidikan Sekolah Dasar", sub_kegiatan: "Pengembangan kompetensi guru dan kepala sekolah", opd: "Dinas Pendidikan", target_2025: "50% satuan pendidikan", anggaran_2025: 2500000000, realisasi_2025: 2350000000, persen_2025: 94.0, target_2026: "50% satuan pendidikan", anggaran_2026: 6659661500, realisasi_2026: 1684300000, persen_2026: 25.29, anggaran_2027: null, serapan_2025: 94.0, serapan_2026: 25.29 },
    { id: "a2", no: 2, sasaran: "ATS teridentifikasi dan kembali ke layanan pendidikan", program: "Program Pengelolaan Pendidikan", kegiatan: "Pengelolaan Pendidikan Nonformal Kesetaraan", sub_kegiatan: "Kampanye sadar pendidikan berbasis shelter warga", opd: "Dinas Pendidikan", target_2025: "32 satuan pendidikan", anggaran_2025: 488051880, realisasi_2025: 422626058, persen_2025: 86.6, target_2026: "32 satuan pendidikan", anggaran_2026: 8452091200, realisasi_2026: 281403256, persen_2026: 3.33, anggaran_2027: null, serapan_2025: 86.6, serapan_2026: 3.33 },
  ],
  ringkasan: {
    jumlah_program: 2, jumlah_opd: 1, tahun: 2026,
    anggaran: 15111752700, realisasi: 1965703256, serapan_persen: 13.01,
    per_tahun: {
      "2025": { anggaran: 2988051880, realisasi: 2772626058, serapan_persen: 92.79 },
      "2026": { anggaran: 15111752700, realisasi: 1965703256, serapan_persen: 13.01 },
      "2027": { anggaran: 0, realisasi: null, serapan_persen: null },
    },
    periode: { tahun: 2026 }, diperbarui: null,
  },
};

const MATRIKS_DISABILITAS = {
  jenis: "disabilitas", label: "Matriks Disabilitas", tersedia: true, tahun: 2026,
  kolom: [],
  items: [
    { id: "d1", opd: "Dinas Sosial", program: "Program Rehabilitasi Sosial", sub_kegiatan: "Penyediaan Kebutuhan dasar PPKS", strategi: "Menyelenggarakan pendataan Penyandang Disabilitas", target_capaian: "Tersedianya data pilah nasional", indikator: "jumlah disabilitas terlantar yang terpenuhi", output: "memenuhi kebutuhan dasar disabilitas terlantar", indikator_disabilitas: "jumlah ketersediaan data terpilah disabilitas", hambatan: "Belum adanya sistem integrasi data", satuan: "orang", target_2025: "170", target_2026: "170", capaian_2025: "170", capaian_2026: null, anggaran_2025: 2491024088, anggaran_2026: 2491024088, realisasi_2025: 500000000, realisasi_2026: 0, lokasi: "KOTA MAKASSAR", spesifik: "Spesifik", keterangan: "Alokasi memenuhi 5 kebutuhan", serapan_2025: 20.07, serapan_2026: 0 },
    { id: "d2", opd: "Dinas Kesehatan", program: "Program Pemenuhan Upaya Kesehatan Perorangan", sub_kegiatan: "Pengelolaan Jaminan Kesehatan Masyarakat", strategi: "Meningkatkan akses layanan kesehatan", target_capaian: "Terlayaninya peserta JKN", indikator: "Jumlah peserta JKN", output: "Terlayaninya peserta", indikator_disabilitas: "Persentase penyandang disabilitas terlayani", hambatan: null, satuan: "orang", target_2025: "5726", target_2026: "17178", capaian_2025: "5726", capaian_2026: null, anggaran_2025: 102154321600, anggaran_2026: 120000000000, realisasi_2025: 9000000000, realisasi_2026: 1000000000, lokasi: "Makassar", spesifik: "Tidak spesifik", keterangan: null, serapan_2025: 8.81, serapan_2026: 0.83 },
  ],
  ringkasan: {
    jumlah_kegiatan: 2, jumlah_opd: 2, jumlah_program: 2, tahun: 2026,
    anggaran_2025: 104645345688, realisasi_2025: 9500000000, serapan_2025: 9.08,
    anggaran_2026: 122491024088, realisasi_2026: 1000000000, serapan_2026: 0.82,
    diperbarui: null,
  },
};

const MUSRENBANG = {
  tahun: 2027, label: "Musrenbang Tematik RKPD 2027", tersedia: true,
  ringkasan: {
    tahun: 2027, jumlah_usulan: 2, jumlah_intervensi: 2, jumlah_tema: 2, jumlah_opd: 2,
    total_anggaran: 21000000,
    per_tema: [
      { tema: "DISABILITAS", usulan: 1, intervensi: 1, anggaran: 2000000 },
      { tema: "PEREMPUAN", usulan: 1, intervensi: 1, anggaran: 19000000 },
    ],
  },
  usulan: [
    { id: "u1", tema: "DISABILITAS", no: 1, permasalahan: "Tidak tersedia JBI (Juru Bahasa Isyarat) di kegiatan PEMKOT", kebutuhan: "Ragam Disabilitas Tuli", usulan: "Penganggaran JBI", lokasi: "Semua Kegiatan OPD/SKPD", opd: "BAPPEDA dan Semua OPD/SKPD", catatan: "Sesuai visi misi Pemkot Makassar", keterangan: null, urutan: 1 },
    { id: "u2", tema: "PEREMPUAN", no: 1, permasalahan: "Isu kekeringan untuk perempuan pesisir", kebutuhan: "Akses air bersih", usulan: "Penyediaan tandon air", lokasi: "Kecamatan Tallo", opd: "DLH, BPBD", catatan: null, keterangan: null, urutan: 2 },
  ],
  intervensi: [
    { id: "i1", tema: "DISABILITAS", no: 1, opd: "Bappeda", program: "PROGRAM KOORDINASI DAN SINKRONISASI PERENCANAAN PEMBANGUNAN DAERAH", kegiatan: "Koordinasi Perencanaan Bidang Pemerintahan", sub_kegiatan: "Koordinasi Pelaksanaan Sinergitas dan Harmonisasi Perencanaan", target: "2 Org", anggaran: 2000000, keterangan: null, urutan: 1 },
    { id: "i2", tema: "PEREMPUAN", no: 1, opd: "Dinas Lingkungan Hidup", program: "Program Pengelolaan Sampah", kegiatan: "Pengelolaan Sampah", sub_kegiatan: "Penyediaan TPS", target: "1 unit", anggaran: 19000000, keterangan: null, urutan: 2 },
  ],
};

const GRUP_SOP = [
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

/** Kelompok yang seharusnya terlihat oleh satu peran, dihitung dari data menu. */
async function grupUntuk(role) {
  const tmp = mkdtempSync(join(tmpdir(), "uji-menu-"));
  const SRC = join(AKAR, "frontend", "src", "constants");
  writeFileSync(join(tmp, "roles.mjs"), readFileSync(join(SRC, "roles.js"), "utf8"));
  writeFileSync(join(tmp, "menu.mjs"),
    readFileSync(join(SRC, "menu.js"), "utf8").replace('from "./roles.js"', 'from "./roles.mjs"'));
  const { MENU, bolehLihat } = await import(pathToFileURL(join(tmp, "menu.mjs")).href);
  return MENU.filter((g) => g.items.some((i) => bolehLihat(i, { role }))).map((g) => g.label);
}

if (!existsSync(join(BUILD, "index.html"))) {
  console.error("Build belum ada. Jalankan: cd frontend && yarn build");
  process.exit(1);
}

let gagal = 0;
const cek = (nama, lulus, info = "") => {
  if (!lulus) gagal += 1;
  console.log(`${lulus ? "PASS" : "FAIL"}  ${nama}${info ? `  [${info}]` : ""}`);
};

/** Halaman harness: menelusuri sidebar di dalam iframe agar tetap hidup saat rute berpindah. */
const HARNESS = `<!doctype html><html><head><meta charset="utf-8"><title>nav</title></head>
<body style="margin:0;font:12px monospace">
<pre id="out">pending</pre>
<iframe id="f" src="/dashboard" style="width:1280px;height:900px;border:0"></iframe>
<script>
const out = document.getElementById('out');
const f = document.getElementById('f');
const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
const log = { grup: [], item: [], klik: [], tab: [], error: [] };
const doc = () => f.contentDocument;
async function siap(sel, n = 100) {
  for (let i = 0; i < n; i += 1) { const d = doc(); if (d && d.querySelector(sel)) return true; await tunggu(150); }
  return false;
}
(async () => {
  try {
    await tunggu(200);
    f.contentWindow.addEventListener('error', (e) => log.error.push('win: ' + (e && e.message)));
    f.contentWindow.addEventListener('unhandledrejection', (e) => log.error.push('reject: ' + (e && e.reason && e.reason.message)));
    const ketemu = await siap('[data-testid="sidebar-nav"]');
    if (!ketemu) {
      const dd = doc();
      const rt = dd && dd.getElementById('root');
      log.error.push('sidebar tidak ditemukan di ' + f.contentWindow.location.pathname
        + ' | judul=' + (dd ? dd.title : '?')
        + ' | root=' + (rt ? rt.innerText.trim().slice(0, 160) : 'null'));
    }
    const d0 = doc();
    log.grup = [...d0.querySelectorAll('[data-testid="sidebar-nav"] p')]
      .filter((p) => /uppercase/.test(p.className)).map((p) => p.textContent.trim());
    const items = [...d0.querySelectorAll('[data-testid^="nav-"]')]
      .map((a) => ({ tid: a.getAttribute('data-testid'), label: (a.textContent || '').trim(), href: a.getAttribute('href') }));
    log.item = items.map((i) => i.tid);
    for (const it of items) {
      if (it.href === '/publik') { log.klik.push({ tid: it.tid, skip: true }); continue; }
      const el = doc().querySelector('[data-testid="' + it.tid + '"]');
      if (!el) { log.klik.push({ tid: it.tid, miss: true }); continue; }
      el.click();
      await tunggu(650);
      const d = doc();
      const h1 = d.querySelector('h1');
      const root = d.getElementById('root');
      log.klik.push({ tid: it.tid, label: it.label, to: f.contentWindow.location.pathname,
        h1: h1 ? h1.textContent.trim() : '', isi: root ? root.innerText.trim().length : 0 });
      if (!d.querySelector('[data-testid="sidebar-nav"]')) {
        f.contentWindow.location.href = '/dashboard';
        await tunggu(1500);
      }
    }
    // Uji khusus halaman Matriks: tiga tab + tombol detail per baris.
    f.contentWindow.location.href = '/matriks';
    await tunggu(1800);
    log.matriks = {};
    for (const id of ['oppkpke', 'kategori', 'ats', 'disabilitas']) {
      const tab = doc().querySelector('[data-testid="page-tab-' + id + '"]');
      if (!tab) { log.matriks[id] = { miss: true }; continue; }
      tab.click();
      await tunggu(700);
      const panel = doc().querySelector('[role="tabpanel"]');
      const btn = doc().querySelector('[aria-controls*="detail-"]');
      let detail = '';
      if (btn) {
        btn.click();
        await tunggu(300);
        const row = doc().getElementById(btn.getAttribute('aria-controls'));
        detail = row ? row.innerText.trim() : '';
      }
      log.matriks[id] = { isi: panel ? panel.innerText.trim().length : 0, detail };
    }
    f.contentWindow.location.href = '/dashboard';
    await tunggu(1200);
    for (const hub of ['nav-laporan', 'nav-impor-kualitas']) {
      const el = doc().querySelector('[data-testid="' + hub + '"]');
      if (!el) { log.tab.push({ hub, miss: true }); continue; }
      el.click();
      await tunggu(800);
      const tabs = [...doc().querySelectorAll('[role="tablist"] [role="tab"]')];
      const panelAwalEl = doc().querySelector('[role="tabpanel"]');
      const panelAwalId = panelAwalEl ? panelAwalEl.id : '';
      let pindah = null;
      if (tabs.length > 1) {
        tabs[1].click();
        await tunggu(700);
        const aktif = doc().querySelector('[role="tab"][aria-selected="true"]');
        const panelBaru = doc().querySelector('[role="tabpanel"]');
        pindah = { label: aktif ? aktif.textContent.trim() : '', panel: panelBaru ? panelBaru.id : '', isi: panelBaru ? panelBaru.innerText.trim().length : 0 };
      }
      log.tab.push({ hub, jumlah: tabs.length, label: tabs.map((t) => t.textContent.trim()), panelAwal: panelAwalId, pindah });
    }
  } catch (e) {
    log.error.push(String(e && e.message ? e.message : e));
  }
  out.textContent = 'HASIL' + JSON.stringify(log);
})();
</script></body></html>`;

/** Harness axe: menyuntikkan axe-core ke dalam iframe lalu mengaudit halamannya. */
const HARNESS_AXE = `<!doctype html><html><head><meta charset="utf-8"><title>axe</title></head>
<body style="margin:0;font:12px monospace">
<pre id="out">pending</pre>
<script>
const q = new URLSearchParams(location.search);
const path = q.get('p') || '/';
const lebar = Number(q.get('w') || 1280);
const out = document.getElementById('out');
const f = document.createElement('iframe');
f.src = path; f.style.width = lebar + 'px'; f.style.height = '900px'; f.style.border = '0';
document.body.appendChild(f);
const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  try {
    await new Promise((r) => { f.onload = r; });
    const d = f.contentDocument, w = f.contentWindow;
    for (let i = 0; i < 60 && !d.querySelector('h1'); i += 1) await tunggu(150);
    await new Promise((resolve, reject) => {
      if (w.axe) return resolve();
      const s = d.createElement('script'); s.src = '/axe.min.js';
      s.onload = resolve; s.onerror = reject; d.head.appendChild(s);
    });
    await tunggu(500);
    const res = await w.axe.run(d, { include: [['body']],
      // Toast hanya muncul karena kegagalan jaringan pada uji ini, bukan bagian halaman.
      exclude: [['[data-sonner-toaster]'], ['[data-sonner-toast]']],
      runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice'] } });
    out.textContent = 'AXE' + JSON.stringify({
      path, lebar, h1: (d.querySelector('h1') || {}).textContent || '',
      violations: res.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, target: v.nodes[0] && v.nodes[0].target.join(' '),
        nodes: v.nodes.slice(0, 3).map((n) => ({ html: String(n.html || '').slice(0, 200), fail: String(n.failureSummary || '').slice(0, 200) })) })),
    });
  } catch (e) {
    out.textContent = 'AXE' + JSON.stringify({ path, error: String(e && e.message ? e.message : e) });
  }
})();
</script></body></html>`;

const server = createServer((req, res) => {
  const url = decodeURIComponent((req.url || "/").split("?")[0]);

  if (url === "/axe.min.js") {
    res.writeHead(200, { "Content-Type": "text/javascript; charset=utf-8" });
    res.end(readFileSync(join(AKAR, "frontend", "node_modules", "axe-core", "axe.min.js")));
    return;
  }
  if (url === "/__axe.html") {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(HARNESS_AXE);
    return;
  }
  if (url === "/__nav.html") {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(HARNESS);
    return;
  }
  if (url === "/api/auth/me") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(PERAN[argPeran] || {}));
    return;
  }
  const FIKSTUR = {
    "/api/matriks/kategori": MATRIKS_KATEGORI,
    "/api/matriks/oppkpke": MATRIKS_OPPKPKE,
    "/api/matriks/ats-program": MATRIKS_ATS,
    "/api/matriks/disabilitas": MATRIKS_DISABILITAS,
    "/api/musrenbang": MUSRENBANG,
  };
  if (FIKSTUR[url]) {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(FIKSTUR[url]));
    return;
  }
  if (url.startsWith("/api/")) {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "tidak tersedia pada uji navigasi" }));
    return;
  }

  let file = join(BUILD, url);
  if (!existsSync(file) || statSync(file).isDirectory()) file = join(BUILD, "index.html");
  try {
    res.writeHead(200, { "Content-Type": MIME[extname(file)] || "application/octet-stream" });
    res.end(readFileSync(file));
  } catch {
    res.writeHead(500).end("gagal membaca berkas");
  }
});

await new Promise((r) => server.listen(0, "127.0.0.1", r));
const port = server.address().port;

async function dump(pathname) {
  const profil = mkdtempSync(join(tmpdir(), "uji-nav-"));
  const { stdout } = await jalankan(CHROME, [
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
    "--virtual-time-budget=45000", `--user-data-dir=${profil}`, "--dump-dom", `http://127.0.0.1:${port}${pathname}`,
  ], { encoding: "utf8", timeout: 180000, maxBuffer: 48 * 1024 * 1024 });
  return stdout;
}

if (modeAxe) {
  // ---------- Mode audit axe ----------
  const rute = [
    ["/aksesibilitas", 1280], ["/dashboard", 1280],
    ["/laporan", 1280], ["/laporan", 375],
    ["/matriks", 1280], ["/matriks", 375],
    ["/matriks?tab=kategori", 1280], ["/matriks?tab=kategori", 375],
    ["/matriks?tab=ats", 1280], ["/matriks?tab=ats", 375],
    ["/matriks?tab=disabilitas", 1280], ["/matriks?tab=disabilitas", 375],
    ["/musrenbang", 1280], ["/musrenbang", 375],
    ["/impor-kualitas", 1280], ["/impor-kualitas", 375],
    ["/administrasi", 1280],
    ["/administrasi", 375],
    ["/impor", 1280],
    ["/impor", 375],
  ];
  for (const [p, w] of rute) {
    let html = "";
    try {
      html = await dump(`/__axe.html?p=${encodeURIComponent(p)}&w=${w}`);
    } catch (e) {
      cek(`${p} @${w}px dapat diaudit`, false, String(e.message || e).slice(0, 90));
      continue;
    }
    const cocok = /AXE(\{[\s\S]*?\})<\/pre>/.exec(html || "");
    if (!cocok) { cek(`${p} @${w}px hasil axe terbaca`, false); continue; }
    const hasil = JSON.parse(cocok[1]);
    if (hasil.error) { cek(`${p} @${w}px axe berjalan`, false, hasil.error.slice(0, 120)); continue; }
    const jumlah = hasil.violations.length;
    // Toast "Gagal memuat..." hanya muncul karena API tiruan membalas 404 pada uji ini.
    const nyata = hasil.violations.filter((v) => !(v.nodes && v.nodes.length && v.nodes.every((n) => /Gagal memuat/.test(n.html))));
    cek(`axe ${p} @${w}px tanpa pelanggaran`, nyata.length === 0,
      nyata.map((v) => `${v.id}(${v.n}) → ${v.target}${v.nodes && v.nodes[0] ? ` :: ${v.nodes[0].html}` : ""}`).join(" | ")
        || `h1="${(hasil.h1 || "").trim()}"${jumlah > nyata.length ? ` · ${jumlah - nyata.length} toast error diabaikan` : ""}`);
  }
  server.close();
  console.log(`\n${gagal === 0 ? "LULUS" : `GAGAL: ${gagal} pemeriksaan`}.`);
  process.exit(gagal === 0 ? 0 : 1);
}

if (!argPeran) {
  // ---------- Mode rute publik ----------
  const rute = [["/", []], ["/login", []], ["/publik", []], ["/tentang", []], ["/flow-sistem", ["Flow Sistem PETA INKLUSI"]], ["/aksesibilitas", ["Aksesibilitas"]]];
  for (const [r, wajib] of rute) {
    let html = "";
    try {
      html = await dump(r);
    } catch (e) {
      cek(`${r} dapat dibuka`, false, String(e.message || e).slice(0, 80));
      continue;
    }
    const kosong = /id="root"[^>]*>\s*<\/div>/.test(html);
    cek(`${r} merender aplikasi`, !kosong);
    if (kosong) continue;
    wajib.forEach((w) => cek(`${r} memuat "${w}"`, html.includes(w)));
  }
} else {
  // ---------- Mode per peran ----------
  cek(`peran ${argPeran} dikenal`, !!PERAN[argPeran]);
  let html = "";
  try {
    html = await dump("/__nav.html");
  } catch (e) {
    cek("harness navigasi berjalan", false, String(e.message || e).slice(0, 120));
  }
  const cocok = /HASIL(\{[\s\S]*?\})<\/pre>/.exec(html || "");
  cek("hasil navigasi terbaca", !!cocok);
  if (cocok) {
    const hasil = JSON.parse(cocok[1]);
    const galatNyata = hasil.error.filter((e) => !/status code 404/.test(e));
    cek("tidak ada error runtime di halaman", galatNyata.length === 0, galatNyata.join(" | ") || `${hasil.error.length} kegagalan jaringan mock diabaikan`);

    const grup = hasil.grup.filter((g) => g);
    const harap = await grupUntuk(argPeran);
    cek(`kelompok menu ${argPeran} sesuai (${harap.length})`, grup.length === harap.length, `${grup.length}: ${grup.join(" / ")}`);
    harap.forEach((g, i) => cek(`kelompok ${i + 1} = "${g}"`, grup[i] === g, grup[i]));
    const urutanBenar = JSON.stringify(grup) === JSON.stringify(harap);
    cek("urutan kelompok sesuai SOP", urutanBenar);
    const diLuarSop = grup.filter((g) => !GRUP_SOP.includes(g));
    cek("tidak ada kelompok di luar SOP", diLuarSop.length === 0, diLuarSop.join(", ") || "bersih");

    const klik = hasil.klik.filter((k) => !k.skip);
    const gagalBuka = klik.filter((k) => k.miss || !k.isi || k.isi < 100);
    cek("semua menu dapat dibuka", gagalBuka.length === 0, gagalBuka.map((k) => `${k.tid}(${k.isi || 0})`).join(", ") || `${klik.length} menu`);

    const tanpaH1 = klik.filter((k) => !k.h1);
    cek("setiap halaman punya h1", tanpaH1.length === 0, tanpaH1.map((k) => k.tid).join(", ") || "lengkap");

    const judulSalah = klik.filter((k) => k.h1 && k.label && k.h1.toLowerCase() !== k.label.toLowerCase());
    cek("judul header sesuai label menu", judulSalah.length === 0,
      judulSalah.map((k) => `${k.tid}: "${k.h1}" != "${k.label}"`).join(" | ") || "cocok");

    // Tab hanya bisa diuji tuntas pada peran yang melihat kedua tab.
    if (argPeran === "superadmin") {
      hasil.tab.forEach((t) => {
        cek(`${t.hub}: tab tersedia`, !t.miss && t.jumlah >= 2, t.miss ? "menu tidak ada" : `${t.jumlah} tab: ${(t.label || []).join(" + ")}`);
        if (t.pindah) {
          cek(`${t.hub}: pindah tab berfungsi`, t.pindah.isi > 20 && t.pindah.panel !== t.panelAwal,
            `${t.pindah.label} → ${t.pindah.panel} (${t.pindah.isi} huruf)`);
        }
      });

      const matriks = hasil.matriks || {};
      ["oppkpke", "kategori", "ats", "disabilitas"].forEach((id) => {
        const m = matriks[id] || {};
        cek(`matriks/${id}: tab tampil`, !m.miss && m.isi > 50, `${m.isi || 0} huruf`);
      });
      cek("matriks/oppkpke: detail baris terbuka",
        /strategi/i.test((matriks.oppkpke || {}).detail || ""),
        ((matriks.oppkpke || {}).detail || "").slice(0, 60));
      cek("matriks/ats: detail baris terbuka",
        /sasaran|target/i.test((matriks.ats || {}).detail || ""),
        ((matriks.ats || {}).detail || "").slice(0, 60));
      cek("matriks/disabilitas: detail baris terbuka",
        /target|indikator|opd/i.test((matriks.disabilitas || {}).detail || ""),
        ((matriks.disabilitas || {}).detail || "").slice(0, 60));
    }
  }
}

server.close();
console.log(`\n${gagal === 0 ? "LULUS" : `GAGAL: ${gagal} pemeriksaan`}.`);
process.exit(gagal === 0 ? 0 : 1);
