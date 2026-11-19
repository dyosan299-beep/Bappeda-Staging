# Snippet audit overflow responsif (dipakai dengan screenshot tool / Playwright).
# Menghitung: horizontal overflow dokumen, overflow area <main>, dan elemen
# teratas yang keluar dari batas kanan viewport/area konten.
AUDIT_JS = """() => {
 const vw = document.documentElement.clientWidth;
 const main = document.querySelector('[data-testid=main-content]') || document.querySelector('#konten');
 const bound = main ? Math.min(vw, main.getBoundingClientRect().right) : vw;
 const res = {sw: document.documentElement.scrollWidth, vw, path: location.pathname};
 if (main) res.m = main.scrollWidth + '/' + main.clientWidth;
 const offenders = [];
 document.querySelectorAll('body *').forEach(el => {
   const r = el.getBoundingClientRect();
   if (r.width < 2 || r.height < 2) return;
   if (getComputedStyle(el).visibility === 'hidden') return;
   const b = (main && main.contains(el)) ? bound : vw;
   if (r.right > b + 1) {
     let p = el.parentElement, clipped = false;
     while (p && p !== document.body && p !== main) {
       if (getComputedStyle(p).overflowX !== 'visible' && p.getBoundingClientRect().right <= b + 1) { clipped = true; break; }
       p = p.parentElement; }
     if (!clipped) offenders.push(el);
   }
 });
 const set = new Set(offenders);
 const top = offenders.filter(el => { let p = el.parentElement; while (p) { if (set.has(p)) return false; p = p.parentElement; } return true; });
 res.off = top.slice(0, 3).map(el => { const r = el.getBoundingClientRect(); return el.tagName.toLowerCase() + '[' + (el.getAttribute('data-testid') || '') + '] ' + (typeof el.className === 'string' ? el.className : '').slice(0, 90) + ' w' + Math.round(r.width) + ' r' + Math.round(r.right); });
 return res;
}"""

ROUTES = ["/", "/publik", "/publik/peta-sosial", "/publik/peta-kemiskinan", "/tentang", "/flow-sistem",
          "/dashboard", "/peta-sosial", "/peta-kemiskinan", "/peta-dasar", "/gis-koordinat", "/disabilitas",
          "/data-stunting", "/data-ats", "/sosial", "/rumah-tangga", "/peta-rumah", "/ngo/inquiry", "/ngo/inquiry/baru",
          "/program", "/prioritas", "/stunting", "/rad", "/bantuan", "/ai-assistant", "/analisa-ai", "/laporan-wilayah",
          "/rekap", "/input-data", "/verifikasi", "/verval/review", "/verval/penugasan", "/impor", "/administrasi",
          "/master-kode", "/kelola-petugas", "/role-permission", "/audit-log", "/ringkasan-mingguan",
          "/notifikasi-email", "/aksesibilitas-bisindo", "/aksesibilitas", "/dashboard-lama"]
