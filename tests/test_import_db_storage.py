"""Uji Import Wizard setelah penyimpanan berkas dipindah ke MariaDB (koleksi import_files).

Jalankan: python /app/tests/test_import_db_storage.py
"""
import io
import os
import random
import sys
import time

import requests
from openpyxl import Workbook

BASE = os.environ.get("TEST_BASE_URL", "https://deploy-live-26.preview.emergentagent.com") + "/api"
s = requests.Session()
ok_all = True


def check(name, cond, info=""):
    global ok_all
    ok_all &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + (f" — {info}" if info else ""))


r = s.post(f"{BASE}/auth/login", json={"email": "admin@bappeda.makassarkota.go.id",
                                       "password": os.environ.get("TEST_ADMIN_PASSWORD", "")})
check("login", r.status_code == 200)
# cookie secure -> kirim ulang manual untuk http localhost
tok = r.cookies.get("access_token") or next((c.value for c in r.cookies), None)
if tok:
    s.headers["Cookie"] = "; ".join(f"{c.name}={c.value}" for c in r.cookies)

# 1) XLSX kecil — gis_koordinat
wb = Workbook()
ws = wb.active
ws.title = "Koordinat"
ws.append(["Kelurahan", "Kecamatan", "Latitude", "Longitude", "Keterangan"])
ws.append(["Lariang Bangi", "Makassar", -5.1400, 119.4230, "uji db storage"])
ws.append(["Maradekaya", "Makassar", -5.1450, 119.4250, "uji db storage"])
ws.append(["", "", "abc", "", ""])  # baris kosong/invalid
buf = io.BytesIO()
wb.save(buf)
r = s.post(f"{BASE}/import/upload",
           files={"file": ("uji_koordinat.xlsx", buf.getvalue(),
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
check("upload xlsx", r.status_code == 200, r.text[:200] if r.status_code != 200 else "")
up = r.json()
sid = up["id"]
check("respon upload tanpa path/storage", "path" not in up and "storage" not in up)
check("preview terisi", up["sheets"][0]["rows"] >= 2 and up["sheets"][0]["preview"],
      f"rows={up['sheets'][0]['rows']}")

r = s.post(f"{BASE}/import/analyze", json={"session_id": sid, "jenis": "gis_koordinat"})
check("analyze", r.status_code == 200)
mapping = r.json()["sheets"][0]["mapping"]
check("mapping otomatis latitude/longitude", set(mapping.values()) >= {"kelurahan", "latitude", "longitude"},
      str(mapping))

r = s.post(f"{BASE}/import/validate", json={"session_id": sid, "jenis": "gis_koordinat",
                                            "mapping": mapping})
check("validate (baca berkas dari DB)", r.status_code == 200, r.text[:200] if r.status_code != 200 else
      f"total={r.json().get('total')} valid={r.json().get('valid')} error={r.json().get('error')}")

r = s.get(f"{BASE}/import/errors/{sid}?format=csv")
check("laporan error csv", r.status_code == 200)

r = s.post(f"{BASE}/import/execute", json={"session_id": sid, "jenis": "gis_koordinat",
                                           "mapping": mapping, "mode": "update",
                                           "lanjut_walau_error": True})
check("execute", r.status_code == 200, r.text[:200])
job_id = r.json().get("job_id")
job = {}
for _ in range(30):
    job = s.get(f"{BASE}/import/job/{job_id}").json()
    if job.get("status") in ("selesai", "gagal"):
        break
    time.sleep(1)
check("job selesai", job.get("status") == "selesai", job.get("pesan", ""))
batch_id = job.get("batch_id")

r = s.get(f"{BASE}/import/history")
check("riwayat memuat batch", any(b["id"] == batch_id for b in r.json()["items"]))
r = s.delete(f"{BASE}/import/batch/{batch_id}")
check("rollback batch", r.status_code == 200, r.text[:150])

# 2) CSV besar (> 2 MB → beberapa potongan)
lines = ["kelurahan,kecamatan,latitude,longitude,keterangan"]
pad = "x" * 180
for i in range(15000):
    lines.append(f"Kel {i},Kec {i % 15},{-5.1 - random.random() / 10:.6f},"
                 f"{119.4 + random.random() / 10:.6f},{pad}")
data = ("\n".join(lines)).encode()
check("ukuran csv > 2MB", len(data) > 2 * 1024 * 1024, f"{len(data) / 1e6:.1f} MB")
r = s.post(f"{BASE}/import/upload", files={"file": ("besar.csv", data, "text/csv")})
check("upload csv besar", r.status_code == 200, r.text[:200] if r.status_code != 200 else "")
sid2 = r.json()["id"]
check("jumlah baris csv besar", r.json()["total_rows"] == 15000, str(r.json()["total_rows"]))
r = s.post(f"{BASE}/import/analyze", json={"session_id": sid2, "jenis": "gis_koordinat"})
m2 = r.json()["sheets"][0]["mapping"]
r = s.post(f"{BASE}/import/validate", json={"session_id": sid2, "jenis": "gis_koordinat",
                                            "mapping": m2})
check("validate csv besar (rakit ulang multi-potongan)", r.status_code == 200 and r.json()["total"] == 15000,
      f"total={r.json().get('total')}" if r.status_code == 200 else r.text[:200])

# 3) Kasus negatif
r = s.post(f"{BASE}/import/upload", files={"file": ("x.txt", b"abc", "text/plain")})
check("tolak ekstensi .txt (422)", r.status_code == 422)
r = s.post(f"{BASE}/import/upload", files={"file": ("rusak.xlsx", b"bukan excel", "application/octet-stream")})
check("tolak xlsx rusak (422)", r.status_code == 422)
r = s.post(f"{BASE}/import/validate", json={"session_id": "tidak-ada", "jenis": "gis_koordinat",
                                            "mapping": {}})
check("sesi tidak ada (404)", r.status_code == 404)

print("\nHASIL:", "SEMUA LULUS" if ok_all else "ADA YANG GAGAL")
sys.exit(0 if ok_all else 1)
