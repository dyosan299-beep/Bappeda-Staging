import os
"""Uji end-to-end alur tulis aplikasi di atas MariaDB."""
import json
import subprocess

BASE = "http://localhost:8001/api"


def rq(method, path, data=None, cookie="admin.txt", save=None, raw=False):
    cmd = ["curl", "-s", "-b", cookie]
    if save:
        cmd += ["-c", save]
    cmd += ["-X", method, BASE + path]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    out = subprocess.run(cmd, capture_output=True).stdout
    if raw:
        return out
    try:
        return json.loads(out)
    except Exception:
        return {"_raw": out[:200].decode("utf-8", "ignore")}


ok = fail = 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"[OK]   {label} {extra}")
    else:
        fail += 1
        print(f"[FAIL] {label} {extra}")


# 1. Login semua peran
rq("POST", "/auth/login", {"email": "admin@bappeda.makassarkota.go.id",
                           "password": os.environ.get("TEST_ADMIN_PASSWORD", "")}, save="admin.txt")
r = rq("POST", "/auth/login", {"email": "petugas.tallo@makassarkota.go.id",
                               "password": os.environ.get("TEST_PETUGAS_PASSWORD", "")}, save="petugas.txt")
check("Login petugas", r.get("role") == "petugas", r.get("wilayah", ""))
r = rq("POST", "/auth/login", {"email": "verifikator@bappeda.makassarkota.go.id",
                               "password": os.environ.get("TEST_VERIFIKATOR_PASSWORD", "")}, save="verif.txt")
check("Login verifikator", r.get("role") == "verifikator")

# 2. Superadmin update region -> langsung diterapkan
regions = rq("GET", "/regions")
tallo = next(x for x in regions if x["nama"] == "Tallo")
r = rq("PUT", f"/regions/{tallo['id']}", {"stunting_anak": 777})
check("Superadmin update region applied", r.get("status") == "applied",
      str(r.get("region", {}).get("stunting_anak")))
again = next(x for x in rq("GET", "/regions") if x["nama"] == "Tallo")
check("Nilai tersimpan di MariaDB", again["stunting_anak"] == 777, str(again["stunting_anak"]))

# 3. Petugas update kelurahan wilayahnya -> masuk antrean verifikasi
kels = rq("GET", "/kelurahan?kecamatan=Tallo", cookie="petugas.txt")
check("Kelurahan Tallo terbaca", len(kels) > 0, f"{len(kels)} kelurahan")
kel = kels[0]
r = rq("PUT", f"/kelurahan/{kel['id']}", {"ats": 42}, cookie="petugas.txt")
check("Petugas -> status pending", r.get("status") == "pending", str(r.get("change_id"))[:8])
change_id = r.get("change_id")

# 4. Petugas dilarang mengubah wilayah lain
other = next(k for k in rq("GET", "/kelurahan") if k["kecamatan"] != "Tallo")
r = rq("PUT", f"/kelurahan/{other['id']}", {"ats": 1}, cookie="petugas.txt")
check("Petugas ditolak di wilayah lain", "tidak berwenang" in str(r.get("detail", "")).lower())

# 5. Verifikator melihat & menyetujui
pend = rq("GET", "/verifikasi?status=pending", cookie="verif.txt")
check("Antrean verifikasi terisi", any(x["id"] == change_id for x in pend), f"{len(pend)} usulan")
cnt = rq("GET", "/verifikasi/count", cookie="verif.txt")
check("Hitung pending", cnt.get("pending", 0) >= 1, str(cnt))
r = rq("POST", f"/verifikasi/{change_id}/approve", {}, cookie="verif.txt")
check("Approve berhasil", "disetujui" in str(r.get("message", "")).lower(), str(r))
kel_after = next(k for k in rq("GET", "/kelurahan?kecamatan=Tallo") if k["id"] == kel["id"])
check("Perubahan diterapkan ke kelurahan", kel_after["ats"] == 42, str(kel_after["ats"]))

# 6. Tolak usulan
r = rq("PUT", f"/kelurahan/{kel['id']}", {"ats": 99}, cookie="petugas.txt")
cid2 = r.get("change_id")
r = rq("POST", f"/verifikasi/{cid2}/reject", {"note": "Data belum valid"}, cookie="verif.txt")
check("Reject berhasil", "ditolak" in str(r.get("message", "")).lower())
kel_after = next(k for k in rq("GET", "/kelurahan?kecamatan=Tallo") if k["id"] == kel["id"])
check("Data tidak berubah setelah reject", kel_after["ats"] == 42, str(kel_after["ats"]))

# 7. CRUD user oleh superadmin
r = rq("POST", "/admin/users", {"email": "uji.pimpinan@bappeda.go.id", "password": "Uji123456",
                                "name": "Uji Pimpinan", "role": "pimpinan", "wilayah": "Kota Makassar"})
uid = r.get("id")
check("Buat user", bool(uid), r.get("role", ""))
dup = rq("POST", "/admin/users", {"email": "uji.pimpinan@bappeda.go.id", "password": "Uji123456",
                                  "name": "Dobel", "role": "petugas"})
check("Email duplikat ditolak", "terdaftar" in str(dup.get("detail", "")).lower(), str(dup)[:60])
r = rq("PATCH", f"/admin/users/{uid}", {"name": "Uji Pimpinan Edit", "role": "verifikator"})
check("Edit user", r.get("name") == "Uji Pimpinan Edit" and r.get("role") == "verifikator")
r = rq("PATCH", f"/admin/users/{uid}/status", {"status": "inactive"})
check("Ubah status user", r.get("status") == "inactive")
r = rq("POST", f"/admin/users/{uid}/reset-password", {"password": "BaruLagi123"})
check("Reset password", "diatur ulang" in str(r.get("message", "")).lower())
r = rq("POST", "/auth/login", {"email": "uji.pimpinan@bappeda.go.id", "password": "BaruLagi123"})
check("Login user nonaktif ditolak", "dinonaktifkan" in str(r.get("detail", "")).lower(), str(r)[:60])
rq("PATCH", f"/admin/users/{uid}/status", {"status": "active"})
r = rq("POST", "/auth/login", {"email": "uji.pimpinan@bappeda.go.id", "password": "BaruLagi123"})
check("Login pakai password baru", r.get("role") == "verifikator")
r = rq("DELETE", f"/admin/users/{uid}")
check("Hapus user", "dihapus" in str(r.get("message", "")).lower())

# 8. Registrasi publik -> pending
rq("DELETE", "/admin/users/none")
r = rq("POST", "/auth/register", {"email": "daftar.uji@makassarkota.go.id",
                                  "password": "Daftar123", "name": "Pendaftar Uji", "wilayah": "Mariso"})
check("Registrasi publik pending", r.get("status") == "pending", str(r.get("message", ""))[:40])
pc = rq("GET", "/admin/pending-count")
check("Lonceng superadmin menghitung pending", pc.get("pending", 0) >= 1, str(pc))
users = rq("GET", "/admin/users")
newu = next((u for u in users if u["email"] == "daftar.uji@makassarkota.go.id"), None)
if newu:
    rq("DELETE", f"/admin/users/{newu['id']}")
    print("[OK]   Bersihkan user pendaftaran uji")

# 9. TTS (round-trip biner via MariaDB cache)
audio1 = rq("POST", "/tts", {"text": "Kemiskinan ekstrim 13.334 kepala keluarga."}, raw=True)
check("TTS menghasilkan audio", len(audio1) > 5000, f"{len(audio1)} byte")
audio2 = rq("POST", "/tts", {"text": "Kemiskinan ekstrim 13.334 kepala keluarga."}, raw=True)
check("TTS cache MariaDB identik (biner utuh)", audio1 == audio2 and len(audio2) > 5000,
      f"{len(audio2)} byte")

# 10. Riwayat AI tersimpan di MariaDB
hist = rq("GET", "/ai/history")
check("Endpoint riwayat AI", isinstance(hist, list), f"{len(hist) if isinstance(hist, list) else '?'} item")

# 11. Laporan
pdf = rq("GET", "/report/dashboard", raw=True)
check("PDF dashboard", pdf[:4] == b"%PDF", f"{len(pdf)} byte")
xlsx = rq("GET", "/export/excel", raw=True)
check("Excel ekspor", xlsx[:2] == b"PK", f"{len(xlsx)} byte")

# 12. Kembalikan data yang diubah
rq("PUT", f"/regions/{tallo['id']}", {"stunting_anak": tallo["stunting_anak"]})
print(f"\n=== HASIL: {ok} LULUS / {fail} GAGAL ===")
