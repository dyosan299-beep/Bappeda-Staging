"""Sinkronisasi angka wilayah dengan data resmi yang sudah masuk ke basis data.

Dipakai setelah impor DINKES disabilitas dan PDF balita stunting. Tanpa `--apply`
skrip hanya menampilkan rencana perubahan (dry-run) dan tidak menulis apa pun.

Sumber:
- disabilitas per kecamatan: koleksi `disability_opd_stats` (DINKES September 2026)
- disabilitas per kelurahan: koleksi `disability_region_stats` (Tallo & Makassar)
- stunting per kelurahan/kecamatan: koleksi `stunting_children` (PDF 2026)

Yang disinkronkan:
- `kelurahan.disabilitas` dan `kelurahan.stunting_anak` untuk 29 kelurahan
  (Tallo & Makassar); kelurahan tanpa kasus diset 0.
- `regions.disabilitas` untuk 15 kecamatan (DINKES).
- `regions.stunting_anak` untuk Tallo & Makassar.
- Penanda `*_otoritatif` agar `_recompute_region` tidak menimpa angka resmi.
"""
import argparse
import asyncio
import re
import sys
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(".env")
from mariadb_store import MariaDocStore  # noqa: E402

SEKARANG = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731
ALIAS_KEL = {"UJUNGPANDANG": "UJUNGPANDANGBARU"}
ALIAS_KEC = {"PANAKUKANG": "PANAKKUKANG"}


def kunci(v) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


def kunci_kec(v) -> str:
    s = re.sub(r"^KECAMATAN", "", kunci(v))
    return ALIAS_KEC.get(s, s)


def kunci_kel(v) -> str:
    s = kunci(v)
    return ALIAS_KEL.get(s, s)


async def main(apply: bool) -> int:
    db = MariaDocStore.from_env()
    try:
        kelurahan = await db["kelurahan"].find({}).to_list(1000)
        regions = await db["regions"].find({}).to_list(100)
        dis_kel_rows = await db["disability_region_stats"].find({}).to_list(2000)
        dis_kec_rows = await db["disability_opd_stats"].find({}).to_list(500)
        stunting = await db["stunting_children"].find({}).to_list(30000)

        dis_kel = {}
        for r in dis_kel_rows:
            dis_kel[(kunci_kec(r.get("kecamatan")), kunci_kel(r.get("kelurahan")))] = int(r.get("jumlah") or 0)
        dis_kec = {kunci_kec(r.get("skpd")): int(r.get("total") or 0) for r in dis_kec_rows}
        st_kel, st_kec = {}, {}
        for r in stunting:
            kk, kl = kunci_kec(r.get("kecamatan")), kunci_kel(r.get("kelurahan"))
            st_kec[kk] = st_kec.get(kk, 0) + 1
            if kl and kunci(r.get("kelurahan")) != "TIDAKDIKETAHUI":
                st_kel[(kk, kl)] = st_kel.get((kk, kl), 0) + 1

        fokus = {"TALLO", "MAKASSAR"}
        kel_fokus = [k for k in kelurahan
                     if kunci_kec(k.get("kecamatan")) in fokus]
        print(f"kelurahan fokus: {len(kel_fokus)} | kecamatan resmi: {len(dis_kec)}")

        # ---------------- validasi sumber
        gagal = False
        for kec_key, nama in (("TALLO", "Tallo"), ("MAKASSAR", "Makassar")):
            total_dis = sum(v for (kc, _), v in dis_kel.items() if kc == kec_key)
            n_kel = len([k for k in kel_fokus if kunci_kec(k.get("kecamatan")) == kec_key])
            print(f"  {nama}: disabilitas kelurahan={total_dis:,} vs DINKES={dis_kec.get(kec_key, 0):,} "
                  f"| stunting total={st_kec.get(kec_key, 0):,} (kelurahan={sum(v for (kc,_),v in st_kel.items() if kc==kec_key):,}) "
                  f"| kelurahan={n_kel}")
            if total_dis != dis_kec.get(kec_key, 0):
                print(f"    ! total disabilitas kelurahan tidak sama dengan DINKES untuk {nama}")
                gagal = True
        hilang = [k for k in ("TALLO", "MAKASSAR") if k not in dis_kec]
        if hilang:
            print("  ! DINKES tidak memuat:", hilang)
            gagal = True
        if set(dis_kec) - {kunci_kec(r.get("nama")) for r in regions}:
            print("  ! kode kecamatan DINKES tak dikenal:",
                  sorted(set(dis_kec) - {kunci_kec(r.get("nama")) for r in regions}))
            gagal = True
        if gagal:
            print("validasi gagal; tidak ada yang ditulis")
            return 1

        # ---------------- rencana perubahan
        rencana_kel = []
        for k in kel_fokus:
            kk, kl = kunci_kec(k.get("kecamatan")), kunci_kel(k.get("nama"))
            baru_dis = dis_kel.get((kk, kl), 0)
            baru_st = st_kel.get((kk, kl), 0)
            lama_dis, lama_st = int(k.get("disabilitas") or 0), int(k.get("stunting_anak") or 0)
            if (baru_dis, baru_st) != (lama_dis, lama_st):
                rencana_kel.append((k, lama_dis, baru_dis, lama_st, baru_st))

        rencana_reg = []
        for r in regions:
            kk = kunci_kec(r.get("nama"))
            baru_dis = dis_kec.get(kk)
            baru_st = st_kec.get(kk) if kk in fokus else None
            lama_dis, lama_st = int(r.get("disabilitas") or 0), int(r.get("stunting_anak") or 0)
            if baru_dis is not None and baru_dis != lama_dis:
                rencana_reg.append((r, "disabilitas", lama_dis, baru_dis))
            if baru_st is not None and baru_st != lama_st:
                rencana_reg.append((r, "stunting_anak", lama_st, baru_st))

        print(f"\nkelurahan berubah: {len(rencana_kel)}")
        for k, ld, nd, ls, ns in rencana_kel:
            print(f"  {k.get('kecamatan'):9} | {k.get('nama'):22} | disabilitas {ld:4}->{nd:4} | stunting {ls:3}->{ns:3}")
        print(f"\nkecamatan berubah: {len(rencana_reg)}")
        for r, f, lama, baru in rencana_reg:
            print(f"  {r.get('nama'):22} | {f:14} {lama:>10,} -> {baru:>10,}")

        if not apply:
            print("\nmode periksa: tidak ada yang ditulis (gunakan --apply)")
            return 0

        # ---------------- tulis
        stempel = SEKARANG()
        for k, _, nd, _, ns in rencana_kel:
            await db["kelurahan"].update_one({"_id": k["_id"]}, {"$set": {
                "disabilitas": nd, "stunting_anak": ns,
                "updated_at": stempel, "updated_by": "Sinkronisasi data resmi 2026",
            }})
        for r, field, _, baru in rencana_reg:
            set_ = {field: baru, f"{field}_sumber": (
                "DINKES September 2026" if field == "disabilitas" else "Data balita stunting 2026 (PDF)"),
                f"{field}_otoritatif": True, "updated_at": stempel,
                "updated_by": "Sinkronisasi data resmi 2026"}
            await db["regions"].update_one({"_id": r["_id"]}, {"$set": set_})

        await db["audit_logs"].insert_one({
            "id": str(uuid.uuid4()), "user": "sinkronisasi-resmi@bappeda.makassarkota.go.id",
            "role": "system", "aksi": "sinkronisasi_wilayah", "entitas": "kelurahan+regions",
            "ref": "DINKES September 2026 + PDF stunting 2026",
            "detail": str({"kelurahan": len(rencana_kel), "kecamatan": len(rencana_reg),
                           "disabilitas_kecamatan": len(dis_kec),
                           "stunting_tallo": st_kec.get("TALLO"),
                           "stunting_makassar": st_kec.get("MAKASSAR")}),
            "status": "sukses", "created_at": stempel,
        })
        print(f"\nselesai: {len(rencana_kel)} kelurahan dan {len(rencana_reg)} field kecamatan diperbarui")
        return 0
    finally:
        await db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Sinkronisasi angka wilayah dengan data resmi")
    ap.add_argument("--apply", action="store_true", help="tulis perubahan (tanpa ini hanya dry-run)")
    sys.exit(asyncio.run(main(ap.parse_args().apply)))
