"""Lapisan penyimpanan dokumen di atas MariaDB/MySQL.

Menyediakan API bergaya Motor (subset yang dipakai aplikasi) sehingga logika
bisnis di `server.py` / `auth.py` tidak perlu diubah, namun seluruh data kini
tersimpan di MariaDB.

Skema: satu tabel per "collection" -> `doc_<nama>` dengan kolom
  `_id`  VARCHAR(64) PRIMARY KEY
  `doc`  LONGTEXT (JSON)
ditambah kolom generated PERSISTENT + index untuk field yang sering difilter.

Operator filter yang didukung: kesamaan langsung, $ne, $exists, $in, $nin,
$gt, $gte, $lt, $lte, $regex. Operator update: $set, $unset, $inc.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import aiomysql

from bsonlite import ObjectId

logger = logging.getLogger("bappeda.mariadb")

TABLE_PREFIX = "doc_"

# Field yang diberi kolom generated + index (mempercepat filter & sort).
INDEXED_FIELDS: Dict[str, List[Tuple[str, bool]]] = {
    # collection: [(field, unique), ...]
    "users": [("email", True), ("status", False), ("role", False), ("created_at", False)],
    "regions": [("nama", False), ("created_at", False)],
    "kelurahan": [("kecamatan", False), ("nama", False)],
    "data_changes": [("id", True), ("status", False), ("submitted_at", False)],
    "ai_analyses": [("id", True), ("kategori", False), ("wilayah", False), ("created_at", False)],
    "tts_cache": [],
    "rumah": [("id", True), ("kelurahan", False), ("rw", False), ("status", False),
              ("kecamatan", False), ("kode", False)],
    "map_config": [("id", True)],
    # --- GeoTag-Verval DTSEN (Operator RT/RW) ---
    "verval_records": [("id", True), ("dtsen_ref", False), ("operator_id", False), ("status", False),
                       ("kode_kelurahan", False), ("client_uuid", False), ("updated_at", False)],
    "verval_foto": [("id", True), ("record_id", False), ("client_foto_id", False), ("sha256", False),
                    ("status", False)],
    "verval_riwayat": [("id", True), ("record_id", False), ("waktu", False)],
    "verval_penugasan": [("id", True), ("user_id", False), ("status", False), ("kode_kelurahan", False)],
    "verval_sasaran": [("id", True), ("user_id", False), ("dtsen_ref", False), ("status", False)],
    # --- data sosial DTSEN & master wilayah ---
    "households": [("id", True), ("no_kk", False), ("kode_kelurahan", False),
                   ("kode_kecamatan", False), ("desil_nasional", False),
                   ("risk_level", False), ("pbi_nas", False), ("pbi_pemda", False),
                   ("dtsen_ref", False), ("rw", False), ("data_uji", False)],
    "household_members": [("id", True), ("household_id", False), ("no_kk", False)],
    "villages": [("id", True), ("kode_kecamatan", False), ("nama_norm", False)],
    "districts": [("id", True), ("nama_norm", False)],
    "cities": [("id", True)],
    "provinces": [("id", True)],
    "village_stats": [("id", True), ("kode_kecamatan", False), ("kelurahan", False)],
    "district_stats": [("id", True)],
    "geo_kelurahan": [("id", True), ("kelurahan_norm", False), ("kecamatan_norm", False)],
    "peta_dasar_layers": [("id", True), ("grup", False)],
    "import_sessions": [("id", True), ("status", False), ("created_at", False)],
    "import_jobs": [("id", True), ("status", False), ("created_at", False)],
    # PETA INKLUSI
    "stunting_children": [("id", True), ("kecamatan_norm", False), ("kelurahan_norm", False),
                          ("status_tbu", False), ("jk", False)],
    "ngo_inquiries": [("id", True), ("status", False), ("user_email", False), ("kategori", False),
                      ("created_at", False)],
    "inquiry_files": [("id", True), ("file_id", False)],
    "musrenbang_usulan": [("id", True), ("kelompok", False)],
    # potongan berkas unggahan Import Wizard (disimpan di DB, bukan di disk)
    "import_files": [("id", True), ("session_id", False), ("seq", False)],
    "gis_locations": [("id", True), ("kelurahan_norm", False), ("kecamatan", False)],
    "kode_referensi": [("id", True), ("field", False)],
    "fasilitas_umum": [("id", True), ("klasifikasi", False), ("kelurahan_norm", False),
                       ("kecamatan_norm", False)],
    "scoring_config": [("id", True)],
    # --- disabilitas ---
    "disability_region_stats": [("id", True), ("kelurahan_norm", False), ("kecamatan_norm", False)],
    "disability_opd_stats": [("id", True), ("skpd", False)],
    # --- stunting ---
    "opd": [("id", True), ("nama_norm", False)],
    "stunting_programs": [("id", True), ("opd", False)],
    "stunting_activities": [("id", True), ("program_id", False), ("opd", False)],
    "stunting_subactivities": [("id", True), ("activity_id", False), ("opd", False),
                               ("program_id", False)],
    "stunting_indicators": [("id", True), ("subactivity_id", False)],
    "stunting_budgets": [("id", True), ("subactivity_id", False), ("tahun", False)],
    # --- RAD disabilitas ---
    "rad_strategies": [("id", True), ("jenis", False)],
    "rad_items": [("id", True), ("program", False)],
    "rad_yearly_targets": [("id", True), ("item_id", False), ("tahun", False)],
    "rad_monitoring": [("id", True), ("item_id", False), ("status", False)],
    # --- audit & kualitas data ---
    "import_batches": [("id", True), ("jenis", False), ("uploaded_at", False)],
    "data_quality_issues": [("id", True), ("jenis", False), ("entitas", False),
                            ("status", False)],
    "raw_imports": [("id", True), ("jenis", False), ("import_batch", False)],
    "audit_logs": [("id", True), ("user", False), ("action", False), ("aksi", False), ("created_at", False)],
}


# --------------------------------------------------------------------------
# Serialisasi JSON (mendukung bytes & datetime)
# --------------------------------------------------------------------------
def _json_default(obj):
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return {"$b64": base64.b64encode(bytes(obj)).decode("ascii")}
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Tipe tidak dapat diserialisasi: {type(obj)!r}")


def _json_hook(d: dict):
    if len(d) == 1 and "$b64" in d and isinstance(d["$b64"], str):
        try:
            return base64.b64decode(d["$b64"])
        except Exception:
            return d
    return d


def _dumps(doc: dict) -> str:
    return json.dumps(doc, default=_json_default, ensure_ascii=False)


def _loads(raw: str) -> dict:
    return json.loads(raw, object_hook=_json_hook)


def _scalar(value):
    """Normalisasi nilai untuk dibandingkan dengan hasil JSON_VALUE (teks)."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _path(field: str) -> str:
    safe = field.replace("'", "").replace("\\", "")
    return "$." + safe


def _col_expr(field: str) -> str:
    if field == "_id":
        return "`_id`"
    return f"JSON_VALUE(`doc`,'{_path(field)}')"


def _parse_db_url(url: str) -> Dict[str, str]:
    """Pecah connection string MySQL/MariaDB menjadi bagian-bagiannya.

    Contoh yang didukung:
      mysql://user:pass@host:3306/nama_db
      mysql+aiomysql://user:pass@host/nama_db
      mariadb://user:pass@host:7890/default?charset=utf8mb4
    """
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme.split("+")[0] not in ("mysql", "mariadb"):
        logger.warning("Skema DATABASE_URL '%s' bukan mysql/mariadb - tetap dicoba",
                       parsed.scheme)
    return {
        "host": parsed.hostname or "",
        "port": str(parsed.port or ""),
        "database": (parsed.path or "").lstrip("/"),
        "user": unquote(parsed.username) if parsed.username else "",
        "password": unquote(parsed.password) if parsed.password else "",
    }


# --------------------------------------------------------------------------
# Hasil operasi (meniru pymongo result objects)
# --------------------------------------------------------------------------
class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id
        self.acknowledged = True


class InsertManyResult:
    def __init__(self, inserted_ids):
        self.inserted_ids = inserted_ids
        self.acknowledged = True


class UpdateResult:
    def __init__(self, matched, modified, upserted_id=None):
        self.matched_count = matched
        self.modified_count = modified
        self.upserted_id = upserted_id
        self.acknowledged = True


class DeleteResult:
    def __init__(self, deleted):
        self.deleted_count = deleted
        self.acknowledged = True


class DuplicateKeyError(Exception):
    pass


# --------------------------------------------------------------------------
# Cursor
# --------------------------------------------------------------------------
class Cursor:
    def __init__(self, collection: "Collection", filt: Optional[dict]):
        self._collection = collection
        self._filter = filt or {}
        self._sort: List[Tuple[str, int]] = []
        self._limit: Optional[int] = None
        self._skip = 0

    def sort(self, key_or_list, direction: int = 1):
        if isinstance(key_or_list, str):
            self._sort.append((key_or_list, direction))
        else:
            for k, d in key_or_list:
                self._sort.append((k, d))
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def skip(self, n: int):
        self._skip = n
        return self

    async def to_list(self, length: Optional[int] = None):
        limit = self._limit if self._limit is not None else length
        return await self._collection._query(self._filter, self._sort, limit, self._skip)

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for row in await self.to_list(None):
            yield row


# --------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------
class Collection:
    def __init__(self, store: "MariaDocStore", name: str):
        self._store = store
        self.name = name
        self.table = f"{TABLE_PREFIX}{name}"

    # ---------- helper SQL ----------
    def _where(self, filt: Optional[dict]) -> Tuple[str, list]:
        if not filt:
            return "", []
        clauses: List[str] = []
        params: List[Any] = []
        for field, cond in filt.items():
            col = _col_expr(field)
            if isinstance(cond, dict) and cond and all(k.startswith("$") for k in cond):
                for op, val in cond.items():
                    if op == "$ne":
                        clauses.append(f"({col} IS NULL OR {col} <> %s)")
                        params.append(_scalar(val))
                    elif op == "$exists":
                        if field == "_id":
                            clauses.append("1=1" if val else "1=0")
                        elif val:
                            clauses.append(f"JSON_EXISTS(`doc`,'{_path(field)}')")
                        else:
                            clauses.append(f"NOT JSON_EXISTS(`doc`,'{_path(field)}')")
                    elif op in ("$in", "$nin"):
                        vals = list(val) or [None]
                        ph = ",".join(["%s"] * len(vals))
                        neg = "NOT " if op == "$nin" else ""
                        clauses.append(f"{col} {neg}IN ({ph})")
                        params.extend(_scalar(v) for v in vals)
                    elif op in ("$gt", "$gte", "$lt", "$lte"):
                        sym = {"$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<="}[op]
                        clauses.append(f"{col} {sym} %s")
                        params.append(_scalar(val))
                    elif op == "$regex":
                        # $options "i" -> PCRE inline flag (?i) (MariaDB >= 10.0.5 memakai PCRE)
                        flags = "".join(c for c in str(cond.get("$options") or "") if c in "imsx")
                        clauses.append(f"{col} REGEXP %s")
                        params.append((f"(?{flags})" if flags else "") + str(val))
                    elif op == "$options":
                        if "$regex" not in cond:
                            raise NotImplementedError("$options hanya boleh dipakai bersama $regex")
                    else:
                        raise NotImplementedError(f"Operator filter belum didukung: {op}")
            else:
                value = _scalar(cond)
                if value is None:
                    clauses.append(f"({col} IS NULL OR {col} = 'null')")
                else:
                    clauses.append(f"{col} = %s")
                    params.append(value)
        return " WHERE " + " AND ".join(clauses), params

    def _order(self, sort: List[Tuple[str, int]]) -> str:
        if not sort:
            return ""
        parts = []
        for field, direction in sort:
            parts.append(f"{_col_expr(field)} {'DESC' if direction < 0 else 'ASC'}")
        return " ORDER BY " + ", ".join(parts)

    async def _query(self, filt, sort, limit, skip=0) -> List[dict]:
        await self._store._ensure_table(self.name)
        where, params = self._where(filt)
        sql = f"SELECT `_id`,`doc` FROM `{self.table}`{where}{self._order(sort)}"
        if limit:
            sql += f" LIMIT {int(limit)}"
            if skip:
                sql += f" OFFSET {int(skip)}"
        elif skip:
            sql += f" LIMIT 18446744073709551615 OFFSET {int(skip)}"
        rows = await self._store._fetchall(sql, params)
        out = []
        for _id, raw in rows:
            doc = _loads(raw)
            doc["_id"] = _id
            out.append(doc)
        return out

    # ---------- API publik ----------
    def find(self, filt: Optional[dict] = None, *args, **kwargs) -> Cursor:
        return Cursor(self, filt)

    async def find_one(self, filt: Optional[dict] = None, *args, **kwargs) -> Optional[dict]:
        rows = await self._query(filt, [], 1)
        return rows[0] if rows else None

    async def count_documents(self, filt: Optional[dict] = None) -> int:
        await self._store._ensure_table(self.name)
        where, params = self._where(filt)
        rows = await self._store._fetchall(
            f"SELECT COUNT(*) FROM `{self.table}`{where}", params)
        return int(rows[0][0]) if rows else 0

    async def insert_one(self, doc: dict) -> InsertOneResult:
        await self._store._ensure_table(self.name)
        body = dict(doc)
        _id = body.pop("_id", None)
        _id = str(_id) if _id is not None else str(ObjectId())
        try:
            await self._store._execute(
                f"INSERT INTO `{self.table}` (`_id`,`doc`) VALUES (%s,%s)",
                [_id, _dumps(body)])
        except aiomysql.IntegrityError as e:
            raise DuplicateKeyError(str(e)) from e
        doc["_id"] = _id
        return InsertOneResult(_id)

    async def insert_many(self, docs: List[dict]) -> InsertManyResult:
        await self._store._ensure_table(self.name)
        rows, ids = [], []
        for doc in docs:
            body = dict(doc)
            _id = body.pop("_id", None)
            _id = str(_id) if _id is not None else str(ObjectId())
            ids.append(_id)
            rows.append((_id, _dumps(body)))
        if rows:
            try:
                await self._store._executemany(
                    f"INSERT INTO `{self.table}` (`_id`,`doc`) VALUES (%s,%s)", rows)
            except aiomysql.IntegrityError as e:
                raise DuplicateKeyError(str(e)) from e
        return InsertManyResult(ids)

    @staticmethod
    def _apply_update(doc: dict, update: dict) -> dict:
        new = dict(doc)
        plain = {k: v for k, v in update.items() if not k.startswith("$")}
        if plain and not any(k.startswith("$") for k in update):
            plain["_id"] = doc.get("_id")
            return plain
        for op, payload in update.items():
            if op == "$set":
                new.update(payload)
            elif op == "$unset":
                for k in payload:
                    new.pop(k, None)
            elif op == "$inc":
                for k, amount in payload.items():
                    new[k] = (new.get(k) or 0) + amount
            elif op == "$setOnInsert":
                continue
            else:
                raise NotImplementedError(f"Operator update belum didukung: {op}")
        return new

    async def _write_doc(self, _id: str, doc: dict):
        body = {k: v for k, v in doc.items() if k != "_id"}
        try:
            await self._store._execute(
                f"UPDATE `{self.table}` SET `doc`=%s WHERE `_id`=%s", [_dumps(body), _id])
        except aiomysql.IntegrityError as e:
            raise DuplicateKeyError(str(e)) from e

    async def update_one(self, filt: dict, update: dict, upsert: bool = False) -> UpdateResult:
        target = await self.find_one(filt)
        if target is None:
            if upsert:
                base = {k: v for k, v in (filt or {}).items() if not isinstance(v, dict)}
                res = await self.insert_one(self._apply_update(base, update))
                return UpdateResult(0, 0, res.inserted_id)
            return UpdateResult(0, 0)
        new_doc = self._apply_update(target, update)
        await self._write_doc(str(target["_id"]), new_doc)
        return UpdateResult(1, 1)

    async def update_many(self, filt: dict, update: dict) -> UpdateResult:
        targets = await self._query(filt, [], None)
        for target in targets:
            new_doc = self._apply_update(target, update)
            await self._write_doc(str(target["_id"]), new_doc)
        return UpdateResult(len(targets), len(targets))

    async def find_one_and_update(self, filt: dict, update: dict,
                                  return_document: bool = True, **kwargs) -> Optional[dict]:
        target = await self.find_one(filt)
        if target is None:
            return None
        new_doc = self._apply_update(target, update)
        await self._write_doc(str(target["_id"]), new_doc)
        new_doc["_id"] = target["_id"]
        return new_doc if return_document else target

    async def replace_one(self, filt: dict, doc: dict, upsert: bool = False) -> UpdateResult:
        target = await self.find_one(filt)
        if target is None:
            if upsert:
                res = await self.insert_one(doc)
                return UpdateResult(0, 0, res.inserted_id)
            return UpdateResult(0, 0)
        await self._write_doc(str(target["_id"]), doc)
        return UpdateResult(1, 1)

    async def delete_one(self, filt: dict) -> DeleteResult:
        target = await self.find_one(filt)
        if target is None:
            return DeleteResult(0)
        await self._store._execute(
            f"DELETE FROM `{self.table}` WHERE `_id`=%s", [str(target["_id"])])
        return DeleteResult(1)

    async def delete_many(self, filt: dict) -> DeleteResult:
        await self._store._ensure_table(self.name)
        where, params = self._where(filt)
        affected = await self._store._execute(
            f"DELETE FROM `{self.table}`{where}", params)
        return DeleteResult(affected)

    async def create_index(self, keys, unique: bool = False, **kwargs):
        await self._store._ensure_table(self.name)
        fields = [keys] if isinstance(keys, str) else [k for k, _ in keys]
        for field in fields:
            await self._store._ensure_indexed_column(self.name, field, unique)
        return "_".join(fields) + "_idx"


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------
class MariaDocStore:
    """Titik masuk utama: `db.users`, `db.regions`, ... seperti objek database Motor."""

    def __init__(self, **conn_kwargs):
        self._conn_kwargs = conn_kwargs
        self._pool: Optional[aiomysql.Pool] = None
        self._collections: Dict[str, Collection] = {}
        self._ready: set = set()

    # ---------- koneksi ----------
    @classmethod
    def from_env(cls) -> "MariaDocStore":
        """Bangun konfigurasi koneksi dari environment variables.

        Prioritas:
        1. `DATABASE_URL` (atau `DB_URL` / `MYSQL_URL`) bila diisi, mis.
           `mysql://user:pass@host:3306/nama_db`
           Skema yang diterima: mysql, mysql+aiomysql, mysql+pymysql, mariadb.
        2. Variabel terpisah format standar Coolify:
           `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`.

        Variabel terpisah yang diisi eksplisit tetap menimpa nilai dari URL,
        sehingga mudah menambal satu bagian saja (mis. hanya `DB_HOST`).
        """
        def _env(name: str) -> str:
            # Bersihkan spasi & tanda kutip yang sering ikut tertempel saat
            # menyalin nilai dari UI Coolify / file .env.
            raw = (os.environ.get(name) or "").strip()
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
                raw = raw[1:-1].strip()
            return raw

        host = _env("DB_HOST")
        port = _env("DB_PORT")
        database = _env("DB_DATABASE")
        user = _env("DB_USERNAME")
        password = _env("DB_PASSWORD")
        sumber: List[str] = []

        # Toleransi: DB_HOST diisi URL lengkap (mysql://user:pass@host:port/db)
        # atau "host:port" - pecah otomatis alih-alih gagal diam-diam.
        if "://" in host:
            parsed = _parse_db_url(host)
            host = parsed["host"]
            port = port or parsed["port"]
            database = database or parsed["database"]
            user = user or parsed["user"]
            password = password or parsed["password"]
            sumber.append("DB_HOST (berisi URL, dipecah otomatis)")
        elif host.count(":") == 1 and host.rsplit(":", 1)[1].isdigit():
            host, port_dari_host = host.rsplit(":", 1)
            port = port or port_dari_host
            sumber.append("DB_HOST (format host:port)")

        url_var = next((n for n in ("DATABASE_URL", "DB_URL", "MYSQL_URL") if _env(n)), "")
        if url_var:
            parsed = _parse_db_url(_env(url_var))
            host = host or parsed["host"]
            port = port or parsed["port"]
            database = database or parsed["database"]
            user = user or parsed["user"]
            password = password or parsed["password"]
            sumber.append(url_var)
        if any(_env(n) for n in ("DB_HOST", "DB_PORT", "DB_DATABASE", "DB_USERNAME", "DB_PASSWORD")):
            sumber.insert(0, "DB_HOST/DB_PORT/DB_DATABASE/DB_USERNAME/DB_PASSWORD")

        # Variabel warisan template platform lama (MongoDB) - TIDAK dipakai.
        legacy = [n for n in ("MONGO_URL", "DB_NAME") if os.environ.get(n)]
        if legacy:
            logger.warning(
                "Variabel %s DIABAIKAN: aplikasi memakai MariaDB (DB_HOST/DB_PORT/"
                "DB_DATABASE/DB_USERNAME/DB_PASSWORD atau DATABASE_URL). Aman dihapus.",
                ", ".join(legacy))

        cfg = dict(
            host=host or "127.0.0.1",
            port=int(port or 3306),
            db=database or "default",
            user=user or "root",
            password=password,
            charset="utf8mb4",
            autocommit=True,
        )
        logger.info("Konfigurasi MariaDB: %s@%s:%s/%s (sumber: %s)",
                    cfg["user"], cfg["host"], cfg["port"], cfg["db"],
                    ", ".join(sumber) or "default")
        store = cls(**cfg)
        store.config_info = {
            "user": cfg["user"],
            "host": cfg["host"],
            "port": cfg["port"],
            "database": cfg["db"],
            "password_terisi": bool(password),
            "password_panjang": len(password),
            "sumber_env": sumber or ["default (tidak ada env DB_* terisi)"],
            "env_warisan_diabaikan": legacy,
        }
        return store

    def info_koneksi(self) -> Dict[str, Any]:
        """Ringkasan konfigurasi koneksi TANPA password (untuk /api/health)."""
        info = dict(getattr(self, "config_info", None) or {})
        if not info:
            info = {
                "user": self._conn_kwargs.get("user"),
                "host": self._conn_kwargs.get("host"),
                "port": self._conn_kwargs.get("port"),
                "database": self._conn_kwargs.get("db"),
                "password_terisi": bool(self._conn_kwargs.get("password")),
            }
        info["target"] = f"{info.get('user')}@{info.get('host')}:{info.get('port')}/{info.get('database')}"
        return info

    @staticmethod
    def diagnosa_error(exc: BaseException) -> str:
        """Petunjuk perbaikan dalam Bahasa Indonesia berdasarkan error koneksi."""
        pesan = str(exc)
        kode = getattr(exc, "args", [None])[0] if getattr(exc, "args", None) else None
        if kode == 1045 or "Access denied" in pesan:
            return ("Username/password DITOLAK oleh MariaDB (error 1045). Cek DB_USERNAME & "
                    "DB_PASSWORD harus sama dengan 'Normal user'/'Normal user password' pada "
                    "resource MariaDB di Coolify. Catatan: bila password di UI Coolify diubah "
                    "SETELAH database pertama kali berjalan, password di dalam DB tetap yang lama. "
                    "Variabel MONGO_URL tidak berpengaruh (diabaikan).")
        if kode == 1049 or "Unknown database" in pesan:
            return ("Nama database tidak ada (error 1049). Samakan DB_DATABASE dengan "
                    "'Initial database' pada resource MariaDB (umumnya 'default').")
        if kode == 2003 or "Can't connect" in pesan or "Connection refused" in pesan \
                or "Name or service not known" in pesan or "nodename nor servname" in pesan \
                or "Temporary failure in name resolution" in pesan:
            return ("Host/port tidak terjangkau (error 2003). Bila memakai hostname internal "
                    "(uuid resource) pastikan aplikasi & database berada di project/environment "
                    "Coolify yang sama dan opsi 'Connect To Predefined Network' aktif, lalu pakai "
                    "DB_PORT=3306. Bila memakai IP publik, pastikan 'Make it publicly available' "
                    "aktif dan DB_PORT = public port.")
        if "timed out" in pesan.lower():
            return "Koneksi timeout: periksa firewall / port mapping ke MariaDB."
        return "Periksa DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD."

    async def connect(self, minsize: int = 1, maxsize: int = 10):
        if self._pool is None:
            self._pool = await aiomysql.create_pool(
                minsize=minsize, maxsize=maxsize, pool_recycle=280,
                **self._conn_kwargs)
            logger.info("Terhubung ke MariaDB %s:%s/%s",
                        self._conn_kwargs.get("host"), self._conn_kwargs.get("port"),
                        self._conn_kwargs.get("db"))
        return self

    async def close(self):
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def _acquire(self):
        if self._pool is None:
            await self.connect()
        return self._pool.acquire()

    async def _fetchall(self, sql: str, params=None):
        if self._pool is None:
            await self.connect()
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params or [])
                return await cur.fetchall()

    async def _execute(self, sql: str, params=None) -> int:
        if self._pool is None:
            await self.connect()
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params or [])
                return cur.rowcount

    async def _executemany(self, sql: str, rows) -> int:
        if self._pool is None:
            await self.connect()
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(sql, rows)
                return cur.rowcount

    # ---------- skema ----------
    async def _ensure_table(self, name: str):
        if name in self._ready:
            return
        table = f"{TABLE_PREFIX}{name}"
        rows = await self._fetchall(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", [table])
        if not rows or int(rows[0][0]) == 0:
            await self._execute(
                f"""CREATE TABLE IF NOT EXISTS `{table}` (
                        `_id` VARCHAR(64) NOT NULL,
                        `doc` LONGTEXT NOT NULL,
                        PRIMARY KEY (`_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            logger.info("Tabel `%s` dibuat", table)
        self._ready.add(name)
        for field, unique in INDEXED_FIELDS.get(name, []):
            await self._ensure_indexed_column(name, field, unique)

    async def _ensure_indexed_column(self, name: str, field: str, unique: bool):
        if field == "_id":
            return
        table = f"{TABLE_PREFIX}{name}"
        col = f"k_{field}"
        rows = await self._fetchall(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            [table, col])
        if not rows or int(rows[0][0]) == 0:
            try:
                await self._execute(
                    f"ALTER TABLE `{table}` ADD COLUMN `{col}` VARCHAR(255) "
                    f"AS (JSON_VALUE(`doc`,'{_path(field)}')) PERSISTENT")
            except Exception as e:  # pragma: no cover
                logger.warning("Gagal menambah kolom %s.%s: %s", table, col, e)
                return
        idx = f"idx_{field}"
        rows = await self._fetchall(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s",
            [table, idx])
        if not rows or int(rows[0][0]) == 0:
            try:
                kind = "UNIQUE" if unique else ""
                await self._execute(
                    f"ALTER TABLE `{table}` ADD {kind} KEY `{idx}` (`{col}`)")
            except Exception as e:  # pragma: no cover
                logger.warning("Gagal membuat index %s.%s: %s", table, idx, e)

    async def ping(self) -> bool:
        rows = await self._fetchall("SELECT 1")
        return bool(rows)

    # ---------- akses collection ----------
    def get_collection(self, name: str) -> Collection:
        if name not in self._collections:
            self._collections[name] = Collection(self, name)
        return self._collections[name]

    def __getitem__(self, name: str) -> Collection:
        return self.get_collection(name)

    def __getattr__(self, name: str) -> Collection:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.get_collection(name)
