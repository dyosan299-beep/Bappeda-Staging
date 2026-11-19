"""Pengganti ringan `bson.ObjectId` agar proyek tidak lagi bergantung pada MongoDB.

ID tetap berupa 24 karakter hex sehingga semua kode & data lama tetap kompatibel.
"""
import os
import re
import time
import threading

_HEX24 = re.compile(r"^[0-9a-fA-F]{24}$")
_counter_lock = threading.Lock()
_counter = int.from_bytes(os.urandom(3), "big")
_machine = os.urandom(5)


class InvalidId(ValueError):
    """Dibangkitkan bila string bukan ObjectId hex 24 karakter yang sah."""


def _generate() -> str:
    global _counter
    with _counter_lock:
        _counter = (_counter + 1) % 0xFFFFFF
        cnt = _counter
    return (
        int(time.time()).to_bytes(4, "big").hex()
        + _machine.hex()
        + cnt.to_bytes(3, "big").hex()
    )


class ObjectId:
    """Identifier 24-hex yang API-nya kompatibel dengan bson.ObjectId (subset)."""

    __slots__ = ("_id",)

    def __init__(self, oid=None):
        if oid is None:
            self._id = _generate()
            return
        if isinstance(oid, ObjectId):
            self._id = oid._id
            return
        if isinstance(oid, bytes):
            if len(oid) == 12:
                self._id = oid.hex()
                return
            oid = oid.decode("utf-8", "ignore")
        oid = str(oid)
        if not _HEX24.match(oid):
            raise InvalidId(f"'{oid}' bukan ObjectId yang sah (butuh 24 karakter hex)")
        self._id = oid.lower()

    @staticmethod
    def is_valid(oid) -> bool:
        try:
            ObjectId(oid)
            return True
        except Exception:
            return False

    def __str__(self):
        return self._id

    def __repr__(self):
        return f"ObjectId('{self._id}')"

    def __eq__(self, other):
        if isinstance(other, ObjectId):
            return self._id == other._id
        if isinstance(other, str):
            return self._id == other.lower()
        return NotImplemented

    def __hash__(self):
        return hash(self._id)
