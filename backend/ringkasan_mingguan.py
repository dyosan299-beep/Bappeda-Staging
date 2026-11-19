"""Ringkasan Mingguan Pimpinan PETA INKLUSI.

Email ringkasan otomatis setiap Senin 06.00 WITA (dijadwalkan lewat `.emergent/crons.yml`)
untuk akun Pimpinan & Admin. Isi:
  * Ringkasan per kecamatan: jumlah data Stunting, ATS, Disabilitas + data baru 7 hari terakhir.
  * Pembaruan inquiry NGO 7 hari terakhir (inquiry baru & perubahan status).

Endpoint:
  POST /api/cron/ringkasan-mingguan            -> dipanggil platform cron (Bearer WEBHOOK_CRON_SECRET)
  GET  /api/inklusi/ringkasan-mingguan/preview -> pratinjau data + HTML email (Admin/Pimpinan)
  POST /api/inklusi/ringkasan-mingguan/kirim   -> kirim manual sekarang (Admin)
  GET  /api/inklusi/ringkasan-mingguan/riwayat -> riwayat pengiriman (Admin/Pimpinan)
"""
from __future__ import annotations

import hmac
import html
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

import notifier
from inklusi import audit, norm_wil, _clean

logger = logging.getLogger("ringkasan_mingguan")
try:
    WITA = ZoneInfo("Asia/Makassar")
except Exception:  # noqa: BLE001 - image tanpa tzdata; WITA = UTC+8 tanpa DST
    WITA = timezone(timedelta(hours=8), "WITA")
RECIPIENT_ROLES = ("pimpinan", "superadmin", "admin", "admin_bappeda")
VIEW_ROLES = RECIPIENT_ROLES + ("verifikator",)
SEND_ROLES = ("superadmin", "admin", "admin_bappeda", "verifikator")
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
         "Oktober", "November", "Desember"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _tgl(d: datetime) -> str:
    w = d.astimezone(WITA)
    return f"{w.day} {BULAN[w.month - 1]} {w.year}"


def _int(v: Any) -> int:
    try:
        return int(float(v or 0))
    except (TypeError, ValueError):
        return 0


def fmt(n: Any) -> str:
    return f"{_int(n):,}".replace(",", ".")


def minggu_key(d: datetime) -> str:
    y, w, _ = d.astimezone(WITA).isocalendar()
    return f"{y}-W{w:02d}"


async def recipients(db) -> List[Dict[str, str]]:
    rows = await db.users.find({"role": {"$in": list(RECIPIENT_ROLES)}}).to_list(1000)
    out = [{"email": r["email"], "name": r.get("name") or "", "role": r.get("role")}
           for r in rows if r.get("email") and (r.get("status") or "active") == "active"]
    extra = [e.strip().lower() for e in os.environ.get("WEEKLY_SUMMARY_EXTRA_RECIPIENTS", "").split(",") if "@" in e]
    known = {o["email"].lower() for o in out}
    out += [{"email": e, "name": "", "role": "tambahan"} for e in extra if e not in known]
    return sorted(out, key=lambda x: (x["role"] != "pimpinan", x["email"]))


async def build_summary(db, akhir: Optional[datetime] = None) -> Dict[str, Any]:
    akhir = akhir or datetime.now(timezone.utc)
    mulai = akhir - timedelta(days=7)

    def baru(doc: Dict[str, Any]) -> bool:
        t = _parse(doc.get("created_at"))
        return bool(t and mulai <= t <= akhir)

    regions = await db.regions.find({}).to_list(100)
    kec: Dict[str, Dict[str, Any]] = {}
    for r in regions:
        kec[norm_wil(r.get("nama"))] = {"kecamatan": r.get("nama"), "stunting": 0, "stunting_baru": 0,
                                        "ats": 0, "ats_baru": 0, "disabilitas": 0, "disabilitas_baru": 0}

    def slot(nama: Any) -> Dict[str, Any]:
        k = norm_wil(nama) or "LAINNYA"
        if k not in kec:
            kec[k] = {"kecamatan": str(nama or "Lainnya").title(), "stunting": 0, "stunting_baru": 0,
                      "ats": 0, "ats_baru": 0, "disabilitas": 0, "disabilitas_baru": 0}
        return kec[k]

    # Stunting (per anak)
    for s in await db.stunting_children.find({}).to_list(200000):
        x = slot(s.get("kecamatan_norm") or s.get("kecamatan"))
        x["stunting"] += 1
        x["stunting_baru"] += 1 if baru(s) else 0

    # ATS (rekap kelurahan, tahun terbaru)
    ats_rows = await db.ats_kelurahan.find({}).to_list(100000)
    ats_tahun = max((_int(r.get("tahun")) for r in ats_rows), default=0) or None
    for r in ats_rows:
        if _int(r.get("tahun")) != ats_tahun:
            continue
        x = slot(r.get("kecamatan"))
        x["ats"] += _int(r.get("jumlah"))
        x["ats_baru"] += _int(r.get("jumlah")) if baru(r) else 0

    # Disabilitas (rekap wilayah, tahun terbaru)
    dis_rows = await db.disability_region_stats.find({}).to_list(100000)
    dis_tahun = max((_int(r.get("tahun")) for r in dis_rows), default=0) or None
    for r in dis_rows:
        if dis_tahun and _int(r.get("tahun")) != dis_tahun:
            continue
        x = slot(r.get("kecamatan_norm") or r.get("kecamatan"))
        x["disabilitas"] += _int(r.get("jumlah"))
        x["disabilitas_baru"] += _int(r.get("jumlah")) if baru(r) else 0

    items = sorted(kec.values(), key=lambda v: (-(v["stunting"] + v["ats"] + v["disabilitas"]), v["kecamatan"]))
    total = {k: sum(i[k] for i in items) for k in
             ("stunting", "stunting_baru", "ats", "ats_baru", "disabilitas", "disabilitas_baru")}

    # Inquiry NGO
    inq_baru: List[Dict[str, Any]] = []
    perubahan: List[Dict[str, Any]] = []
    per_status: Dict[str, int] = {}
    for q in await db.ngo_inquiries.find({}).to_list(20000):
        per_status[q.get("status") or "-"] = per_status.get(q.get("status") or "-", 0) + 1
        info = {"nomor": q.get("nomor"), "nama_ngo": q.get("nama_ngo") or q.get("user_name") or "-",
                "kategori": q.get("kategori") or "-", "kecamatan": q.get("kecamatan") or "-",
                "program": q.get("program_usulan") or "-"}
        if baru(q):
            inq_baru.append({**info, "status": q.get("status")})
        for h in q.get("riwayat") or []:
            t = _parse(h.get("waktu"))
            if t and mulai <= t <= akhir and h.get("status") != "SUBMITTED":
                perubahan.append({**info, "status": h.get("status"),
                                  "status_label": notifier.STATUS_LABEL.get(h.get("status"), h.get("status")),
                                  "oleh": h.get("peran") or "-", "catatan": (h.get("catatan") or "")[:160],
                                  "waktu": t.isoformat()})
    perubahan.sort(key=lambda p: p["waktu"], reverse=True)

    return {
        "periode": {"mulai": mulai.isoformat(), "akhir": akhir.isoformat(),
                    "label": f"{_tgl(mulai)} – {_tgl(akhir)}", "minggu": minggu_key(akhir)},
        "tahun_ats": ats_tahun, "tahun_disabilitas": dis_tahun,
        "per_kecamatan": items, "total": total,
        "inquiry": {"baru": inq_baru, "perubahan_status": perubahan[:50], "jumlah_perubahan": len(perubahan),
                    "per_status": [{"status": k, "label": notifier.STATUS_LABEL.get(k, k), "jumlah": v}
                                   for k, v in sorted(per_status.items(), key=lambda x: -x[1])],
                    "total": sum(per_status.values())},
        "dibuat_at": now_iso(),
    }


def render_email(s: Dict[str, Any], nama: str = "", base_url: str = "") -> Dict[str, str]:
    e = html.escape
    p, t, iq = s["periode"], s["total"], s["inquiry"]
    subject = f"[PETA INKLUSI] Ringkasan Mingguan Pimpinan — {p['label']}"
    sapaan = f"Yth. {nama}," if nama else "Yth. Bapak/Ibu Pimpinan,"

    def plus(n: int) -> str:
        return f" (+{fmt(n)})" if n else ""

    # ---------- teks biasa
    lines = [sapaan, "", f"Berikut ringkasan data PETA INKLUSI periode {p['label']}.", "",
             "RINGKASAN KOTA MAKASSAR",
             f"- Anak stunting tercatat : {fmt(t['stunting'])}{plus(t['stunting_baru'])} data baru",
             f"- Anak tidak sekolah (ATS){' ' + str(s['tahun_ats']) if s['tahun_ats'] else ''}: {fmt(t['ats'])}{plus(t['ats_baru'])}",
             f"- Penyandang disabilitas{' ' + str(s['tahun_disabilitas']) if s['tahun_disabilitas'] else ''}: {fmt(t['disabilitas'])}{plus(t['disabilitas_baru'])}",
             "", "PER KECAMATAN (Stunting | ATS | Disabilitas)"]
    for i in s["per_kecamatan"]:
        lines.append(f"- {i['kecamatan']}: {fmt(i['stunting'])}{plus(i['stunting_baru'])} | "
                     f"{fmt(i['ats'])}{plus(i['ats_baru'])} | {fmt(i['disabilitas'])}{plus(i['disabilitas_baru'])}")
    lines += ["", "INQUIRY NGO (7 HARI TERAKHIR)",
              f"- Inquiry baru: {len(iq['baru'])}", f"- Perubahan status: {iq['jumlah_perubahan']}"]
    for c in iq["perubahan_status"][:15]:
        lines.append(f"  • {c['nomor']} ({c['nama_ngo']}, Kec. {c['kecamatan']}) → {c['status_label']}")
    if base_url:
        lines += ["", f"Buka dashboard: {base_url.rstrip('/')}/dashboard"]
    lines += ["", "Salam,", "Tim PETA INKLUSI — Bappeda Kota Makassar",
              "(Email ini dikirim otomatis setiap Senin pukul 06.00 WITA.)"]

    # ---------- HTML
    def kartu(label: str, nilai: int, tambah: int, warna: str) -> str:
        tb = (f"<div style='font-size:12px;color:#117A69;font-weight:bold'>+{fmt(tambah)} minggu ini</div>"
              if tambah else "<div style='font-size:12px;color:#94a3b8'>tidak ada data baru</div>")
        return (f"<td style='width:33%;padding:6px'><div style='border:1px solid #e2e8f0;border-top:4px solid {warna};"
                f"border-radius:8px;padding:12px'><div style='font-size:11px;color:#64748b;font-weight:bold;"
                f"text-transform:uppercase'>{e(label)}</div><div style='font-size:24px;font-weight:800;color:#232F3E'>"
                f"{fmt(nilai)}</div>{tb}</div></td>")

    def sel(n: int, b: int) -> str:
        badge = f" <span style='color:#117A69;font-size:11px;font-weight:bold'>+{fmt(b)}</span>" if b else ""
        return f"<td style='padding:6px 8px;text-align:right;border-top:1px solid #eef2f6'>{fmt(n)}{badge}</td>"

    rows = "".join(
        f"<tr><td style='padding:6px 8px;border-top:1px solid #eef2f6'>{e(str(i['kecamatan']))}</td>"
        f"{sel(i['stunting'], i['stunting_baru'])}{sel(i['ats'], i['ats_baru'])}"
        f"{sel(i['disabilitas'], i['disabilitas_baru'])}</tr>" for i in s["per_kecamatan"])
    chg = "".join(
        f"<tr><td style='padding:6px 8px;border-top:1px solid #eef2f6'><b>{e(str(c['nomor']))}</b><br>"
        f"<span style='color:#64748b;font-size:12px'>{e(c['nama_ngo'])} · Kec. {e(c['kecamatan'])}</span></td>"
        f"<td style='padding:6px 8px;border-top:1px solid #eef2f6'>{e(c['kategori'])}</td>"
        f"<td style='padding:6px 8px;border-top:1px solid #eef2f6'><span style='background:#E6FAF6;color:#117A69;"
        f"padding:2px 8px;border-radius:999px;font-weight:bold;font-size:12px'>{e(str(c['status_label']))}</span></td></tr>"
        for c in iq["perubahan_status"][:15]) or (
        "<tr><td colspan='3' style='padding:10px 8px;color:#94a3b8'>Tidak ada perubahan status inquiry minggu ini.</td></tr>")
    baru_html = "".join(
        f"<li>{e(str(b['nomor']))} — {e(b['nama_ngo'])} ({e(b['kategori'])}, Kec. {e(b['kecamatan'])})</li>"
        for b in iq["baru"][:10])
    btn = (f"<p style='margin:20px 0 4px'><a href='{e(base_url.rstrip('/'))}/dashboard' style='background:#117A69;"
           f"color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:bold'>Buka Dashboard PETA INKLUSI</a></p>"
           if base_url else "")
    th = "padding:6px 8px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase"
    body_html = f"""<div style="font-family:Arial,sans-serif;max-width:680px;margin:auto;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;color:#0f172a">
<div style="background:#232F3E;padding:18px 22px">
<div style="color:#6FE3CF;font-weight:bold;font-size:18px">PETA INKLUSI <span style="color:#cbd5e1;font-size:12px;font-weight:normal">Bappeda Kota Makassar</span></div>
<div style="color:#fff;font-size:15px;margin-top:6px;font-weight:bold">Ringkasan Mingguan Pimpinan</div>
<div style="color:#cbd5e1;font-size:12px">Periode {e(p['label'])}</div></div>
<div style="padding:20px 22px">
<p>{e(sapaan)}</p><p>Berikut ringkasan perkembangan data inklusi sosial Kota Makassar selama 7 hari terakhir.</p>
<table style="width:100%;border-collapse:collapse"><tr>
{kartu('Anak stunting', t['stunting'], t['stunting_baru'], '#117A69')}
{kartu('ATS' + (' ' + str(s['tahun_ats']) if s['tahun_ats'] else ''), t['ats'], t['ats_baru'], '#F4B63A')}
{kartu('Disabilitas' + (' ' + str(s['tahun_disabilitas']) if s['tahun_disabilitas'] else ''), t['disabilitas'], t['disabilitas_baru'], '#232F3E')}
</tr></table>
<h3 style="font-size:15px;color:#232F3E;margin:22px 0 6px">Ringkasan per kecamatan</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr style="background:#f8fafc">
<th style="{th}">Kecamatan</th><th style="{th};text-align:right">Stunting</th><th style="{th};text-align:right">ATS</th><th style="{th};text-align:right">Disabilitas</th></tr></thead>
<tbody>{rows}</tbody></table>
<p style="font-size:11px;color:#94a3b8;margin-top:4px">Angka hijau (+n) = data baru yang masuk selama periode ini.</p>
<h3 style="font-size:15px;color:#232F3E;margin:22px 0 6px">Pembaruan inquiry NGO</h3>
<p style="margin:0 0 8px;font-size:13px"><b>{len(iq['baru'])}</b> inquiry baru · <b>{iq['jumlah_perubahan']}</b> perubahan status · total <b>{fmt(iq['total'])}</b> inquiry</p>
{f"<ul style='font-size:13px;margin:0 0 8px;padding-left:18px'>{baru_html}</ul>" if baru_html else ""}
<table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr style="background:#f8fafc">
<th style="{th}">Inquiry</th><th style="{th}">Kategori</th><th style="{th}">Status baru</th></tr></thead><tbody>{chg}</tbody></table>
{btn}
<p style="font-size:12px;color:#94a3b8;margin-top:18px">Email ini dikirim otomatis oleh PETA INKLUSI setiap Senin pukul 06.00 WITA, mohon tidak membalas.</p>
</div></div>"""
    return {"subject": subject, "text": "\n".join(lines), "html": body_html}


async def run_summary(db, sumber: str, oleh: str = "sistem", run_id: Optional[str] = None,
                      to: Optional[List[str]] = None) -> Dict[str, Any]:
    run_id = run_id or str(uuid.uuid4())
    try:
        s = await build_summary(db)
        penerima = await recipients(db)
        if to:
            penerima = [p for p in penerima if p["email"].lower() in {x.lower() for x in to}] or \
                       [{"email": x, "name": "", "role": "manual"} for x in to]
        base = os.environ.get("APP_PUBLIC_URL", "").strip()
        hasil = {"terkirim": 0, "belum_terkirim": 0, "gagal": 0}
        for p in penerima:
            mail = render_email(s, p.get("name") or "", base)
            res = await notifier.queue_email(db, [p["email"]], mail["subject"], mail["text"], mail["html"],
                                             jenis="ringkasan_mingguan", ref=s["periode"]["minggu"])
            hasil[res.get("status")] = hasil.get(res.get("status"), 0) + 1
        upd = {"status": "selesai", "penerima": [p["email"] for p in penerima], "hasil": hasil,
               "periode": s["periode"], "selesai_at": now_iso()}
    except Exception as ex:  # noqa: BLE001
        logger.exception("Ringkasan mingguan gagal")
        upd = {"status": "gagal", "error": str(ex)[:500], "selesai_at": now_iso()}
    await db.weekly_summary_runs.update_one({"id": run_id}, {"$set": upd})
    return {"id": run_id, **upd}


def build_router(db, current_user_dep) -> APIRouter:
    router = APIRouter(tags=["ringkasan-mingguan"])

    async def view_dep(user: dict = Depends(current_user_dep)):
        if user.get("role") not in VIEW_ROLES:
            raise HTTPException(status_code=403, detail="Akses khusus Pimpinan/Admin")
        return user

    async def send_dep(user: dict = Depends(current_user_dep)):
        if user.get("role") not in SEND_ROLES:
            raise HTTPException(status_code=403, detail="Akses khusus Admin/Super Admin")
        return user

    async def new_run(run_id: str, sumber: str, oleh: str) -> None:
        await db.weekly_summary_runs.insert_one({
            "id": run_id, "sumber": sumber, "oleh": oleh, "status": "berjalan",
            "minggu": minggu_key(datetime.now(timezone.utc)), "created_at": now_iso()})

    @router.post("/cron/ringkasan-mingguan")
    async def cron_ringkasan(request: Request, background: BackgroundTasks):
        # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
        secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
        auth = request.headers.get("authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if not secret or not token or not hmac.compare_digest(token, secret):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        try:
            env = await request.json()
            if not isinstance(env, dict):
                raise ValueError
        except Exception:  # noqa: BLE001
            return JSONResponse({"detail": "Body tidak valid"}, status_code=400)
        run_id = request.headers.get("x-webhook-id") or env.get("run_id") or str(uuid.uuid4())
        if await db.weekly_summary_runs.find_one({"id": run_id}):
            return {"accepted": True, "duplicate": True}
        minggu = minggu_key(datetime.now(timezone.utc))
        sudah = await db.weekly_summary_runs.find_one({"minggu": minggu, "sumber": "cron", "status": "selesai"})
        if sudah:
            return {"accepted": True, "duplicate": True, "minggu": minggu}
        await new_run(run_id, "cron", "jadwal")
        background.add_task(run_summary, db, "cron", "jadwal", run_id)
        return {"accepted": True, "run_id": run_id}

    @router.get("/inklusi/ringkasan-mingguan/preview")
    async def preview(user: dict = Depends(view_dep)):
        s = await build_summary(db)
        mail = render_email(s, user.get("name") or "", os.environ.get("APP_PUBLIC_URL", "").strip())
        return {"ringkasan": s, "email": mail, "penerima": await recipients(db), "smtp": notifier.public_status(),
                "jadwal": {"label": "Setiap Senin pukul 06.00 WITA", "cron": "0 6 * * 1", "zona": "Asia/Makassar"}}

    @router.post("/inklusi/ringkasan-mingguan/kirim")
    async def kirim(request: Request, user: dict = Depends(send_dep)):
        to: Optional[List[str]] = None
        try:
            body = await request.json()
            if isinstance(body, dict) and body.get("to"):
                to = [str(x).strip() for x in body["to"] if "@" in str(x)]
        except Exception:  # noqa: BLE001
            pass
        run_id = str(uuid.uuid4())
        await new_run(run_id, "manual", user.get("email", ""))
        res = await run_summary(db, "manual", user.get("email", ""), run_id, to)
        await audit(db, user, "kirim_ringkasan_mingguan", "weekly_summary_runs", run_id, res.get("hasil"), request)
        return res

    @router.get("/inklusi/ringkasan-mingguan/riwayat")
    async def riwayat(user: dict = Depends(view_dep)):
        rows = await db.weekly_summary_runs.find({}).sort("created_at", -1).limit(30).to_list(30)
        return {"items": [_clean(r) for r in rows]}

    return router
