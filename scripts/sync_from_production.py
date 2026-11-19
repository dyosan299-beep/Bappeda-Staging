"""Salin data dari database MariaDB produksi ke database lokal/preview (SATU ARAH, BACA SAJA).

- Produksi hanya dibaca (SELECT). Tidak ada perintah tulis ke produksi.
- Setiap tabel `doc_*` di lokal DIKOSONGKAN lalu diisi ulang dengan `_id` + `doc`
  dari produksi. Kolom index (generated column `k_*`) dihitung ulang otomatis oleh MariaDB lokal.
- Tabel lokal yang tidak ada di produksi dibiarkan apa adanya.

Pemakaian (kredensial TIDAK ditulis di kode):
    PROD_DATABASE_URL='mysql://user:pass@host:port/dbname' \
        python /app/scripts/sync_from_production.py [--only households,users] [--dry-run]

Database tujuan diambil dari backend/.env (DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD).
Hentikan backend dulu (`supervisorctl stop backend`) agar seeding tidak berjalan di tengah proses.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import pymysql
from dotenv import load_dotenv

BATCH = 2000
DDL = """CREATE TABLE IF NOT EXISTS `{t}` (
    `_id` VARCHAR(64) NOT NULL,
    `doc` LONGTEXT NOT NULL,
    PRIMARY KEY (`_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""


def connect_url(url: str):
    u = urlparse(url)
    return pymysql.connect(host=u.hostname, port=u.port or 3306, user=unquote(u.username or ""),
                           password=unquote(u.password or ""), database=(u.path or "/").lstrip("/"),
                           charset="utf8mb4", connect_timeout=20, read_timeout=600)


def connect_local():
    load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")
    return pymysql.connect(host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT") or 3306),
                           user=os.environ["DB_USERNAME"], password=os.environ["DB_PASSWORD"],
                           database=os.environ["DB_DATABASE"], charset="utf8mb4", autocommit=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="daftar koleksi dipisah koma (tanpa prefix doc_)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    url = os.environ.get("PROD_DATABASE_URL", "").strip()
    if not url:
        print("PROD_DATABASE_URL belum diisi", file=sys.stderr)
        return 2
    src = connect_url(url)
    dst = connect_local()
    only = {f"doc_{x.strip()}" for x in args.only.split(",") if x.strip()}

    with src.cursor() as c:
        c.execute("SELECT table_name FROM information_schema.tables "
                  "WHERE table_schema = DATABASE() AND table_name LIKE 'doc\\_%' ORDER BY table_name")
        tables = [r[0] for r in c.fetchall()]
    if only:
        tables = [t for t in tables if t in only]

    total_rows = 0
    t0 = time.time()
    for t in tables:
        with src.cursor() as c:
            c.execute(f"SELECT COUNT(*) FROM `{t}`")
            n = int(c.fetchone()[0])
        if args.dry_run:
            print(f"{t:<34} {n:>8} baris (dry-run)")
            continue
        with dst.cursor() as d:
            d.execute(DDL.format(t=t))
            d.execute(f"DELETE FROM `{t}`")
        copied = 0
        with src.cursor(pymysql.cursors.SSCursor) as c:
            c.execute(f"SELECT `_id`, `doc` FROM `{t}`")
            while True:
                rows = c.fetchmany(BATCH)
                if not rows:
                    break
                with dst.cursor() as d:
                    d.executemany(f"INSERT INTO `{t}` (`_id`, `doc`) VALUES (%s, %s)", rows)
                copied += len(rows)
        dst.commit()
        total_rows += copied
        status = "OK" if copied == n else f"SELISIH (sumber {n})"
        print(f"{t:<34} {copied:>8} baris  {status}", flush=True)

    print(f"\nSelesai: {len(tables)} tabel, {total_rows} baris, {time.time() - t0:.0f} detik")
    src.close()
    dst.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
