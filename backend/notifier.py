"""Notifikasi email (SMTP) PETA INKLUSI.

Setiap email dicatat di koleksi `email_outbox` (MariaDB) dengan status:
  - "terkirim"        : berhasil dikirim lewat SMTP
  - "belum_terkirim"  : SMTP belum dikonfigurasi -> akan dikirim otomatis saat kredensial tersedia
  - "gagal"           : SMTP dikonfigurasi tetapi pengiriman gagal (dapat dikirim ulang)

Konfigurasi .env (backend):
  SMTP_HOST, SMTP_PORT (465 = SSL, 587 = STARTTLS), SMTP_USER, SMTP_PASSWORD,
  SMTP_FROM (mis. "PETA INKLUSI <noreply@makassarkota.go.id>"), SMTP_SECURITY (ssl|starttls|none, opsional),
  APP_PUBLIC_URL (opsional; dipakai untuk tautan di email)
"""
from __future__ import annotations

import asyncio
import html
import logging
import os
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from typing import Any, Dict, List, Optional

logger = logging.getLogger("notifier")
now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

STATUS_LABEL = {
    "SUBMITTED": "Diajukan", "UNDER_REVIEW": "Ditinjau", "VERIFICATION": "Verifikasi",
    "APPROVED": "Disetujui", "NEED_REVISION": "Perlu Revisi", "REJECTED": "Ditolak",
    "PROGRAM_IMPLEMENTATION": "Implementasi Program", "MONITORING": "Monitoring", "COMPLETED": "Selesai",
}


def smtp_config() -> Dict[str, Any]:
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587") or 587)
    sec = (os.environ.get("SMTP_SECURITY") or ("ssl" if port == 465 else "starttls")).lower()
    return {
        "host": host, "port": port, "security": sec,
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from": os.environ.get("SMTP_FROM", "").strip() or os.environ.get("SMTP_USER", "").strip(),
    }


def smtp_ready() -> bool:
    c = smtp_config()
    return bool(c["host"] and c["from"])


def public_status() -> Dict[str, Any]:
    c = smtp_config()
    return {"configured": smtp_ready(), "host": c["host"] or None, "port": c["port"] if c["host"] else None,
            "security": c["security"] if c["host"] else None, "from": c["from"] or None}


def _send_sync(to: List[str], subject: str, body_text: str, body_html: str) -> None:
    c = smtp_config()
    msg = EmailMessage()
    name, addr = parseaddr(c["from"])
    msg["From"] = formataddr((name or "PETA INKLUSI", addr))
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")
    ctx = ssl.create_default_context()
    if c["security"] == "ssl":
        with smtplib.SMTP_SSL(c["host"], c["port"], context=ctx, timeout=20) as s:
            if c["user"]:
                s.login(c["user"], c["password"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(c["host"], c["port"], timeout=20) as s:
            if c["security"] == "starttls":
                s.starttls(context=ctx)
            if c["user"]:
                s.login(c["user"], c["password"])
            s.send_message(msg)


async def _deliver(db, doc: Dict[str, Any]) -> Dict[str, Any]:
    if not smtp_ready():
        upd = {"status": "belum_terkirim", "error": "SMTP belum dikonfigurasi", "updated_at": now_iso()}
    else:
        try:
            await asyncio.to_thread(_send_sync, doc["to"], doc["subject"], doc["body_text"], doc["body_html"])
            upd = {"status": "terkirim", "error": "", "sent_at": now_iso(), "updated_at": now_iso()}
        except Exception as e:  # noqa: BLE001
            logger.warning("Gagal kirim email %s: %s", doc.get("id"), e)
            upd = {"status": "gagal", "error": str(e)[:500], "updated_at": now_iso()}
    upd["attempts"] = int(doc.get("attempts") or 0) + 1
    await db.email_outbox.update_one({"id": doc["id"]}, {"$set": upd})
    doc.update(upd)
    return doc


async def queue_email(db, to: List[str], subject: str, body_text: str, body_html: str,
                      jenis: str = "umum", ref: str = "") -> Dict[str, Any]:
    to = sorted({t.strip().lower() for t in to if t and "@" in t})
    doc = {"id": str(uuid.uuid4()), "to": to, "subject": subject[:250], "body_text": body_text,
           "body_html": body_html, "jenis": jenis, "ref": ref, "status": "antri", "attempts": 0,
           "error": "", "created_at": now_iso(), "updated_at": now_iso()}
    await db.email_outbox.insert_one(dict(doc))
    if not to:
        await db.email_outbox.update_one({"id": doc["id"]}, {"$set": {"status": "gagal", "error": "Tanpa penerima"}})
        doc["status"] = "gagal"
        return doc
    return await _deliver(db, doc)


async def flush_pending(db, include_failed: bool = False, limit: int = 200) -> Dict[str, int]:
    """Kirim ulang email yang tertunda (dipanggil saat startup & oleh admin)."""
    if not smtp_ready():
        return {"diproses": 0, "terkirim": 0, "gagal": 0, "smtp": 0}
    statuses = ["belum_terkirim", "antri"] + (["gagal"] if include_failed else [])
    rows = await db.email_outbox.find({"status": {"$in": statuses}}).sort("created_at", 1).limit(limit).to_list(limit)
    ok = bad = 0
    for r in rows:
        r = {k: v for k, v in r.items() if k != "_id"}
        res = await _deliver(db, r)
        ok += res["status"] == "terkirim"
        bad += res["status"] != "terkirim"
    return {"diproses": len(rows), "terkirim": ok, "gagal": bad, "smtp": 1}


def inquiry_status_email(inq: Dict[str, Any], status_baru: str, catatan: str, oleh_peran: str,
                         base_url: str = "") -> Dict[str, str]:
    label = STATUS_LABEL.get(status_baru, status_baru)
    link = f"{base_url.rstrip('/')}/ngo/inquiry/{inq.get('id')}" if base_url else ""
    wilayah = f"{'Kel. ' + inq['kelurahan'] + ', ' if inq.get('kelurahan') else ''}Kec. {inq.get('kecamatan', '')}"
    subject = f"[PETA INKLUSI] Status inquiry {inq.get('nomor')} kini: {label}"
    nama = inq.get("nama_pic") or inq.get("user_name") or "Bapak/Ibu"
    lines = [
        f"Yth. {nama} ({inq.get('nama_ngo', '')}),", "",
        f"Status inquiry {inq.get('nomor')} telah diperbarui menjadi: {label}.", "",
        f"Program   : {inq.get('program_usulan', '')}",
        f"Kategori  : {inq.get('kategori', '')}",
        f"Wilayah   : {wilayah}",
        f"Diproses  : {oleh_peran}", "",
        "Catatan dari admin:", catatan.strip() or "-", "",
    ]
    if status_baru == "NEED_REVISION":
        lines.append("Silakan masuk ke PETA INKLUSI dan lakukan revisi inquiry sesuai catatan di atas.")
    if link:
        lines.append(f"Lihat detail: {link}")
    lines += ["", "Salam,", "Tim PETA INKLUSI — Bappeda Kota Makassar",
              "(Email ini dikirim otomatis, mohon tidak membalas.)"]
    text = "\n".join(lines)
    e = html.escape
    warna = {"APPROVED": "#117A69", "COMPLETED": "#232F3E", "REJECTED": "#B42318", "NEED_REVISION": "#B7791F"}.get(
        status_baru, "#117A69")
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0;color:#64748b'>{e(k)}</td><td style='padding:4px 0'><b>{e(str(v))}</b></td></tr>"
        for k, v in (("Nomor", inq.get("nomor")), ("Program", inq.get("program_usulan")),
                     ("Kategori", inq.get("kategori")), ("Wilayah", wilayah), ("Diproses oleh", oleh_peran)))
    btn = (f"<p style='margin:20px 0'><a href='{e(link)}' style='background:#117A69;color:#fff;padding:10px 18px;"
           f"border-radius:6px;text-decoration:none;font-weight:bold'>Lihat detail inquiry</a></p>") if link else ""
    body_html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">
<div style="background:#232F3E;color:#6FE3CF;padding:16px 20px;font-weight:bold;font-size:18px">PETA INKLUSI <span style="color:#cbd5e1;font-size:12px;font-weight:normal">Bappeda Kota Makassar</span></div>
<div style="padding:20px;color:#0f172a">
<p>Yth. {e(nama)} ({e(inq.get('nama_ngo', ''))}),</p>
<p>Status inquiry Anda telah diperbarui menjadi:</p>
<p><span style="background:{warna};color:#fff;padding:6px 14px;border-radius:999px;font-weight:bold">{e(label)}</span></p>
<table style="font-size:14px;margin-top:12px">{rows}</table>
<div style="margin-top:16px;padding:12px;background:#f1f5f9;border-left:4px solid {warna};border-radius:4px">
<div style="font-size:12px;color:#64748b;font-weight:bold;text-transform:uppercase">Catatan dari admin</div>
<div style="white-space:pre-line;margin-top:4px">{e(catatan.strip() or '-')}</div></div>
{"<p>Silakan masuk ke PETA INKLUSI dan lakukan revisi sesuai catatan di atas.</p>" if status_baru == "NEED_REVISION" else ""}
{btn}
<p style="font-size:12px;color:#94a3b8">Email ini dikirim otomatis oleh PETA INKLUSI, mohon tidak membalas.</p>
</div></div>"""
    return {"subject": subject, "text": text, "html": body_html}


def base_url_from_request(request: Optional[Any]) -> str:
    env = os.environ.get("APP_PUBLIC_URL", "").strip()
    if env:
        return env
    if request is None:
        return ""
    origin = request.headers.get("origin") or ""
    if origin:
        return origin
    ref = request.headers.get("referer") or ""
    if ref.startswith("http"):
        parts = ref.split("/")
        return "/".join(parts[:3])
    return ""
