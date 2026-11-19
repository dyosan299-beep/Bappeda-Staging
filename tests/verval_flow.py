"""Uji alur Verval petugas end-to-end lewat API (requests) + sinkronisasi peta.
Jalankan: python /app/tests/verval_flow.py
"""
import io
import json
import sys
import uuid

import requests
from PIL import Image

B = "http://localhost:8001/api"


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{B}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    # cookie Secure tidak dikirim requests lewat http -> pakai Bearer
    tok = r.cookies.get("access_token") or s.cookies.get("access_token")
    s.headers["Authorization"] = f"Bearer {tok}"
    s.cookies.clear()
    return s


def jpeg_bytes(with_exif_gps=False):
    import random
    im = Image.new("RGB", (640, 480), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    buf = io.BytesIO()
    if with_exif_gps:
        from fractions import Fraction as F
        exif = Image.Exif()
        gps = {1: "S", 2: (F(5), F(10), F(30)), 3: "E", 4: (F(119), F(26), F(6)),
               7: (F(8), F(5), F(3)), 29: "2026:10:16"}
        exif[0x8825] = gps
        im.save(buf, format="JPEG", exif=exif.tobytes())
    else:
        im.save(buf, format="JPEG")
    return buf.getvalue()


def main():
    pt = login("petugas.gs@test.id", "Petugas123")
    cfg = pt.get(f"{B}/verval/konfigurasi").json()
    print("konfigurasi petugas: dapat_geotag=", cfg["dapat_geotag"], "wilayah=", cfg.get("wilayah_petugas"))
    sas = pt.get(f"{B}/verval/sasaran").json()["items"]
    ref = sas[0]["dtsen_ref"]
    det = pt.get(f"{B}/verval/sasaran/{ref}").json()
    print("detail sasaran:", det["sasaran"]["kepala_keluarga"], det["sasaran"]["dasar_akses"])
    # sasaran di luar RT/RW (Tallo) harus 404
    tallo = requests.Session()
    r = pt.get(f"{B}/verval/sasaran/DR-" + "0" * 40)
    print("akses sasaran luar wilayah ->", r.status_code)

    # pakai sasaran yang belum pernah diverval agar alur dari awal
    for it in sas:
        if it["status_verval"] == "belum_diverval":
            ref = it["dtsen_ref"]
            break
    rec = pt.post(f"{B}/verval/records", json={"dtsen_ref": ref, "client_uuid": uuid.uuid4().hex}).json()
    rid = rec["id"]
    print("record:", rid, rec["status"])
    # Foto sebelum form lengkap -> 422
    r = pt.post(f"{B}/verval/records/{rid}/foto", files={"file": ("a.jpg", jpeg_bytes(), "image/jpeg")},
                data={"client_foto_id": uuid.uuid4().hex})
    print("foto sebelum form lengkap ->", r.status_code)
    # Lengkapi form
    ind = {i["key"]: {"kesesuaian": i["kesesuaian"][0], "kondisi_riil": i["kondisi_riil"][0], "catatan": "catatan uji"} for i in cfg["indikator"]}
    r = pt.put(f"{B}/verval/records/{rid}", json={"indikator": ind, "kesimpulan": {"pilihan": "ditemukan_sesuai", "catatan": "ok"}})
    assert r.status_code == 200, r.text
    # Foto 1 dengan koordinat perangkat
    r = pt.post(f"{B}/verval/records/{rid}/foto", files={"file": ("a.jpg", jpeg_bytes(), "image/jpeg")},
                data={"client_foto_id": uuid.uuid4().hex, "lat": "-5.1735", "lng": "119.4345", "akurasi_m": "4.2"})
    assert r.status_code == 200, r.text
    d = r.json()
    print("foto1 gps:", d["foto"][0]["gps_saat_foto"], "| gps_record:", (d.get("gps_record") or {}).get("status_gps"))
    # Foto 2 hanya EXIF
    r = pt.post(f"{B}/verval/records/{rid}/foto", files={"file": ("b.jpg", jpeg_bytes(True), "image/jpeg")},
                data={"client_foto_id": uuid.uuid4().hex, "jenis": "rumah_samping"})
    assert r.status_code == 200, r.text
    print("foto2 gps (exif):", r.json()["foto"][1]["gps_saat_foto"])
    # Kirim
    r = pt.post(f"{B}/verval/records/{rid}/kirim")
    print("kirim ->", r.status_code, r.json().get("status"), r.json().get("detail"))
    # Peta petugas
    p = pt.get(f"{B}/verval/peta").json()
    print("peta petugas:", p["mode"], p["total"], "geojson:", p["geojson"]["count"], "foto titik:", p["titik"][0]["foto_count"])

    # Verifikator kota (wilayah Kota Makassar) melihat semua
    vf = login("verifikator@bappeda.makassarkota.go.id", "Verifikator2026")
    rl = vf.get(f"{B}/verval/records").json()
    print("verifikator records:", rl["total"])
    # Superadmin & pimpinan melihat hasil
    sa = login("admin@bappeda.makassarkota.go.id", "AdminBappeda2026")
    print("superadmin records:", sa.get(f"{B}/verval/records").json()["total"],
          "peta:", sa.get(f"{B}/verval/peta").json()["mode"])
    det = sa.get(f"{B}/verval/records/{rid}").json()
    print("superadmin detail no_kk tersamar?", det["sasaran"]["no_kk_tersamar"], "foto:", len(det["foto"]))
    fid = det["foto"][0]["id"]
    print("superadmin lihat foto ->", sa.get(f"{B}/verval/foto/{fid}").status_code)
    # Buat verifikator Tallo via superadmin -> tidak boleh lihat record Rappocini
    sa.delete(f"{B}/admin/users/placeholder")
    users = sa.get(f"{B}/admin/users").json()
    for u in users:
        if u["email"] in ("verifikator.tallo@test.id", "pimpinan@test.id"):
            sa.delete(f"{B}/admin/users/{u['id']}")
    r = sa.post(f"{B}/admin/users", json={"email": "verifikator.tallo@test.id", "password": "Verif123", "name": "Verifikator Tallo", "role": "verifikator", "wilayah": "Tallo"})
    assert r.status_code == 200, r.text
    r = sa.post(f"{B}/admin/users", json={"email": "pimpinan@test.id", "password": "Pimpinan123", "name": "Pimpinan", "role": "pimpinan"})
    assert r.status_code == 200, r.text
    vt = login("verifikator.tallo@test.id", "Verif123")
    print("verifikator Tallo records:", vt.get(f"{B}/verval/records").json()["total"],
          "detail Rappocini ->", vt.get(f"{B}/verval/records/{rid}").status_code,
          "regions:", [x["nama"] for x in vt.get(f"{B}/regions").json()])
    pm = login("pimpinan@test.id", "Pimpinan123")
    print("pimpinan records:", pm.get(f"{B}/verval/records").json()["total"],
          "detail ->", pm.get(f"{B}/verval/records/{rid}").status_code,
          "review ->", pm.post(f"{B}/verval/records/{rid}/review", json={"keputusan": "disetujui"}).status_code,
          "peta:", pm.get(f"{B}/verval/peta").json()["mode"])
    # Verifikator kota menyetujui
    r = vf.post(f"{B}/verval/records/{rid}/review", json={"keputusan": "disetujui", "catatan": "sesuai"})
    print("verifikator review ->", r.status_code, r.json().get("status"))
    # Operator (agregat)
    op = login("operator.rappocini@makassarkota.go.id", "Operator2026")
    po = op.get(f"{B}/verval/peta").json()
    print("operator peta:", po["mode"], po["total"], [k["kelurahan"] for k in po.get("kelurahan", [])])


if __name__ == "__main__":
    main()
