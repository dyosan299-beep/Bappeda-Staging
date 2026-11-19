"""POC: uji koneksi MariaDB VPS Coolify + operasi dasar dokumen JSON.

Kredensial dibaca dari environment (atau backend/.env), tidak di-hardcode.
Jalankan:  cd backend && python ../test_core_mariadb.py
"""
import asyncio, json, os, base64
from pathlib import Path

import aiomysql
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "backend" / ".env")

CFG = dict(
    host=os.environ.get("DB_HOST", "127.0.0.1"),
    port=int(os.environ.get("DB_PORT") or 3306),
    user=os.environ.get("DB_USERNAME", "root"),
    password=os.environ.get("DB_PASSWORD", ""),
    db=os.environ.get("DB_DATABASE", "default"),
    autocommit=True, charset="utf8mb4",
)


async def main():
    conn = await aiomysql.connect(**CFG)
    cur = await conn.cursor()
    await cur.execute("SELECT VERSION()")
    print("[OK] Versi MariaDB:", (await cur.fetchone())[0])

    await cur.execute("""
        CREATE TABLE IF NOT EXISTS poc_docs (
            `_id` VARCHAR(64) NOT NULL,
            `doc` LONGTEXT NOT NULL,
            PRIMARY KEY (`_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("[OK] CREATE TABLE")

    await cur.execute("DELETE FROM poc_docs")
    doc = {"email": "admin@bappeda.go.id", "role": "superadmin", "nested": {"a": 1},
           "audio": {"$b64": base64.b64encode(b"\x00\x01biner").decode()}}
    await cur.execute("INSERT INTO poc_docs (`_id`,`doc`) VALUES (%s,%s)",
                      ("aabbccddeeff001122334455", json.dumps(doc)))
    print("[OK] INSERT")

    await cur.execute("SELECT `_id`,`doc` FROM poc_docs WHERE JSON_VALUE(`doc`,'$.email')=%s",
                      ("admin@bappeda.go.id",))
    row = await cur.fetchone()
    print("[OK] JSON_VALUE filter ->", row[0], json.loads(row[1])["role"])

    await cur.execute("UPDATE poc_docs SET `doc`=JSON_SET(`doc`,'$.role',%s) WHERE `_id`=%s",
                      ("pimpinan", "aabbccddeeff001122334455"))
    await cur.execute("SELECT JSON_VALUE(`doc`,'$.role') FROM poc_docs")
    print("[OK] JSON_SET update ->", (await cur.fetchone())[0])

    await cur.execute("SELECT COUNT(*) FROM poc_docs WHERE JSON_EXISTS(`doc`,'$.role')")
    print("[OK] JSON_EXISTS count ->", (await cur.fetchone())[0])

    try:
        await cur.execute("ALTER TABLE poc_docs ADD COLUMN `k_email` VARCHAR(255) "
                          "AS (JSON_VALUE(`doc`,'$.email')) PERSISTENT")
        await cur.execute("ALTER TABLE poc_docs ADD UNIQUE KEY `uq_k_email` (`k_email`)")
        print("[OK] Generated column + UNIQUE index")
    except Exception as e:
        print("[INFO] index:", e)

    try:
        await cur.execute("INSERT INTO poc_docs (`_id`,`doc`) VALUES (%s,%s)",
                          ("111122223333444455556666", json.dumps({"email": "admin@bappeda.go.id"})))
        print("[FAIL] duplikat email seharusnya ditolak")
    except Exception as e:
        print("[OK] UNIQUE email menolak duplikat:", type(e).__name__)

    await cur.execute("SELECT `doc` FROM poc_docs WHERE `_id`=%s", ("aabbccddeeff001122334455",))
    back = json.loads((await cur.fetchone())[0])
    raw = base64.b64decode(back["audio"]["$b64"])
    print("[OK] Round-trip biner:", raw == b"\x00\x01biner")

    await cur.execute("DROP TABLE poc_docs")
    print("[OK] Bersih. SEMUA POC MARIADB LULUS.")
    await cur.close()
    conn.close()


asyncio.run(main())
