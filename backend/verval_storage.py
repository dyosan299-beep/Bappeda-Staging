"""Penyimpanan foto GeoTag-Verval pada volume persisten (VERVAL_STORAGE_DIR).

- Foto BARU modul ini disimpan di direktori volume persisten Coolify (bukan filesystem
  container stateless). Bila VERVAL_STORAGE_DIR belum dikonfigurasi/ tidak dapat ditulis,
  unggahan DITOLAK (503) — tidak ada fallback diam-diam ke disk container.
- Pola `story_files` (foto Cerita Dampak di MariaDB) TIDAK diubah/dipindahkan.
- Validasi: batas ukuran, hanya JPEG/PNG/WEBP, verifikasi Pillow, perlindungan
  decompression bomb, re-encode JPEG (membuang EXIF & payload tersisip), nama file acak
  (UUID) bukan nama dari klien, penulisan atomik, SHA-256 untuk integritas & dedup.
- Path selalu di-resolve dan wajib berada di dalam direktori dasar (anti path traversal).
"""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}
MAX_PIXELS = 40_000_000
MAX_SIDE = 2048


class StorageError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def base_dir() -> Optional[Path]:
    raw = (os.environ.get("VERVAL_STORAGE_DIR") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_absolute() else None


def status() -> dict:
    b = base_dir()
    if b is None:
        return {"terkonfigurasi": False, "dapat_ditulis": False,
                "pesan": "VERVAL_STORAGE_DIR belum diatur (wajib path absolut ke volume persisten)"}
    try:
        b.mkdir(parents=True, exist_ok=True)
        probe = b / f".probe-{uuid.uuid4().hex}"
        probe.write_bytes(b"ok")
        probe.unlink()
        usage = shutil.disk_usage(b)
        return {"terkonfigurasi": True, "dapat_ditulis": True,
                "ruang_kosong_mb": int(usage.free / 1048576), "pesan": "Penyimpanan siap"}
    except Exception as e:  # noqa: BLE001
        return {"terkonfigurasi": True, "dapat_ditulis": False,
                "pesan": f"Direktori tidak dapat ditulis: {type(e).__name__}"}



def exif_gps(data: bytes) -> Optional[dict]:
    """Baca koordinat GPS dari metadata EXIF foto asli (sebelum dibuang saat re-encode).

    Dipakai sebagai cadangan bila perangkat tidak mengirim koordinat saat unggah.
    Return {"lat","lng","diambil_at"} atau None.
    """
    try:
        im = Image.open(io.BytesIO(data))
        exif = im.getexif()
        gps = exif.get_ifd(0x8825) if exif else None
        if not gps:
            return None

        def _deg(v):
            d, m, s = (float(x) for x in v)
            return d + m / 60.0 + s / 3600.0

        lat = _deg(gps[2]) * (-1 if str(gps.get(1, "N")).upper().startswith("S") else 1)
        lng = _deg(gps[4]) * (-1 if str(gps.get(3, "E")).upper().startswith("W") else 1)
        if not (-90 <= lat <= 90 and -180 <= lng <= 180) or (lat == 0 and lng == 0):
            return None
        waktu = ""
        try:
            tgl = str(gps.get(29) or "")  # GPSDateStamp YYYY:MM:DD
            jam = gps.get(7)              # GPSTimeStamp (h, m, s)
            if tgl and jam:
                waktu = f"{tgl.replace(':', '-')}T{int(float(jam[0])):02d}:{int(float(jam[1])):02d}:{int(float(jam[2])):02d}Z"
            elif exif.get(0x0132):
                waktu = str(exif.get(0x0132))
        except Exception:  # noqa: BLE001
            waktu = ""
        return {"lat": round(lat, 7), "lng": round(lng, 7), "diambil_at": waktu}
    except Exception:  # noqa: BLE001
        return None


def _load_font(size: int):
    for name in (
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arialbd.ttf",
        "arial.ttf",
    ):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:  # noqa: BLE001
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _apply_watermark(im: Image.Image, lines: List[str]) -> Image.Image:
    clean_lines = [str(x).strip() for x in (lines or []) if str(x or "").strip()]
    if not clean_lines:
        return im
    base = im.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_size = max(13, min(28, int(im.width * 0.022)))
    if im.height < 200:
        font_size = max(10, min(font_size, max(10, im.height // (len(clean_lines) + 2))))
    font = _load_font(font_size)
    line_h = int(font_size * 1.38)
    pad_y = max(6, int(font_size * 0.65))
    pad_x = max(10, int(font_size * 0.85))
    bar_h = min(im.height, pad_y * 2 + line_h * len(clean_lines))
    y0 = max(0, im.height - bar_h)
    draw.rectangle([(0, y0), (im.width, im.height)], fill=(20, 30, 44, 195))
    stripe_w = min(6, max(3, im.width // 60))
    draw.rectangle([(0, y0), (stripe_w, im.height)], fill=(111, 227, 207, 255))
    text_x = stripe_w + pad_x
    for idx, line in enumerate(clean_lines):
        color = (111, 227, 207, 255) if idx == 0 else (255, 255, 255, 255)
        draw.text((text_x, y0 + pad_y + idx * line_h), line, fill=color, font=font)
    return Image.alpha_composite(base, overlay).convert("RGB")


def process_image(data: bytes, max_mb: int, watermark_lines: Optional[List[str]] = None) -> Tuple[bytes, int, int]:
    if not data:
        raise StorageError(400, "Berkas foto kosong")
    if len(data) > max_mb * 1024 * 1024:
        raise StorageError(413, f"Ukuran foto melebihi {max_mb} MB")
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = (probe.format or "").upper()
        probe.verify()
    except Image.DecompressionBombError:
        raise StorageError(400, "Resolusi foto terlalu besar")
    except Exception:
        raise StorageError(400, "Berkas bukan gambar yang valid")
    if fmt not in ALLOWED_FORMATS:
        raise StorageError(415, "Format foto harus JPEG, PNG, atau WEBP")
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        if watermark_lines:
            im = _apply_watermark(im, watermark_lines)
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=85, optimize=True)  # metadata EXIF tidak ikut
        return out.getvalue(), im.width, im.height
    except StorageError:
        raise
    except Exception:
        raise StorageError(400, "Foto tidak dapat diproses")


def _safe_path(rel: str) -> Path:
    b = base_dir()
    if b is None:
        raise StorageError(503, "Penyimpanan foto Verval belum dikonfigurasi")
    full = (b / rel).resolve()
    if not str(full).startswith(str(b.resolve()) + os.sep):
        raise StorageError(400, "Path berkas tidak valid")
    return full


def save(record_id: str, data: bytes) -> Tuple[str, str]:
    """Simpan bytes JPEG hasil proses. Return (path_relatif, sha256)."""
    st = status()
    if not st["dapat_ditulis"]:
        raise StorageError(503, "Penyimpanan foto Verval belum siap: " + st["pesan"])
    sha = hashlib.sha256(data).hexdigest()
    safe_rec = "".join(c for c in record_id if c.isalnum() or c == "-")[:64]
    rel = f"{safe_rec[:2]}/{safe_rec}/{uuid.uuid4().hex}.jpg"
    full = _safe_path(rel)
    full.parent.mkdir(parents=True, exist_ok=True)
    tmp = full.with_suffix(".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, full)
    try:
        os.chmod(full, 0o640)
    except OSError:
        pass
    return rel, sha


def read(rel: str) -> bytes:
    full = _safe_path(rel)
    if not full.is_file():
        raise StorageError(404, "Berkas foto tidak ditemukan pada penyimpanan")
    return full.read_bytes()


def delete(rel: str) -> None:
    try:
        full = _safe_path(rel)
        if full.is_file():
            full.unlink()
    except StorageError:
        pass


def verify(rel: str, sha: str) -> str:
    """'ok' | 'hilang' | 'rusak' — dipakai skrip verifikasi backup/restore."""
    try:
        data = read(rel)
    except StorageError:
        return "hilang"
    return "ok" if hashlib.sha256(data).hexdigest() == sha else "rusak"
