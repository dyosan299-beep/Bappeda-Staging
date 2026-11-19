"""AI Assistant data-aware untuk SIDATA Bappeda Kota Makassar.

Menjawab pertanyaan bebas pengguna DENGAN MEMBACA DATABASE (bukan halusinasi):
wilayah prioritas, faktor penyebab kerentanan, perbandingan anggaran stunting
2025 vs 2026, OPD relevan, RAD disabilitas, dan data rumah/GIS.

Struktur jawaban yang dipaksakan lewat system prompt:
  1. Ringkasan Analisis
  2. Data Pendukung
  3. Faktor Utama
  4. Program Terkait
  5. Rekomendasi
  6. Tingkat Prioritas
plus daftar "Referensi Data Internal" yang dikirim terpisah sebagai metadata SSE.

Semua endpoint di-mount pada prefix /api oleh server.py.
"""
from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import llm_hostlinku

logger = logging.getLogger("bappeda.ai")

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

# ----------------------------------------------------------------- model
# Provider tunggal: Hostlinku (gateway OpenAI-compatible, HOSTLINKU_API_KEY).
MODELS: List[Dict[str, str]] = list(llm_hostlinku.MODELS)
MODEL_BY_ID = {m["id"]: m for m in MODELS}
# alias agar penulisan bebas tetap dikenali (termasuk nama model lama -> default)
MODEL_ALIAS = {
    "deepseek": "deepseek-v4-1-flash", "deepseek-v4.1-flash": "deepseek-v4-1-flash",
    "deepseek-4.1": "deepseek-v4-1-flash", "deepseek-flash": "deepseek-v4-1-flash",
    "deepseek-pro": "deepseek-v4-pro", "qwen": "qwen3-6-plus",
    # nama model lama (Emergent) dipetakan ke default agar sesi lama tetap jalan
    "gpt-5.2": "deepseek-v4-1-flash", "gpt5.2": "deepseek-v4-1-flash", "gpt": "deepseek-v4-1-flash",
    "claude-sonnet-4-6": "deepseek-v4-pro", "claude": "deepseek-v4-pro", "sonnet": "deepseek-v4-pro",
}


def _hitung_default_model() -> str:
    """Default: AI_DEFAULT_MODEL bila diisi, else HOSTLINKU_MODEL."""
    pilihan = (os.environ.get("AI_DEFAULT_MODEL") or "").strip()
    pilihan = MODEL_ALIAS.get(pilihan.lower(), pilihan)
    return pilihan or llm_hostlinku.DEFAULT_MODEL


DEFAULT_MODEL = _hitung_default_model()


def provider_tersedia(provider: str = "hostlinku") -> bool:
    return provider == "hostlinku" and llm_hostlinku.tersedia()


def model_tersedia() -> List[Dict[str, str]]:
    """Katalog cadangan (sinkron); daftar lengkap diambil async via katalog_model()."""
    return [m for m in MODELS if provider_tersedia(m["provider"])]


async def resolve_model_async(model_id: Optional[str]) -> Dict[str, Any]:
    """Pilih model dari katalog Hostlinku (dinamis). Slug tak dikenal -> default."""
    key = (model_id or DEFAULT_MODEL).strip()
    key = MODEL_ALIAS.get(key.lower(), key)
    katalog = await llm_hostlinku.katalog_model()
    by_id = {m["id"]: m for m in katalog}
    if key in by_id:
        return by_id[key]
    if key in MODEL_BY_ID:
        return MODEL_BY_ID[key]
    return by_id.get(DEFAULT_MODEL) or MODEL_BY_ID.get(DEFAULT_MODEL) or \
        {"id": DEFAULT_MODEL, "provider": "hostlinku", "label": DEFAULT_MODEL, "catatan": ""}


def resolve_model(model_id: Optional[str]) -> Dict[str, str]:
    """Versi sinkron (katalog cadangan) - dipertahankan untuk kompatibilitas."""
    key = (model_id or DEFAULT_MODEL).strip()
    key = MODEL_ALIAS.get(key.lower(), key)
    return MODEL_BY_ID.get(key) or {"id": key, "provider": "hostlinku", "label": key, "catatan": ""}


def norm_name(value: Any) -> str:
    s = str(value or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9' -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def rp(v: Any) -> str:
    try:
        n = float(v or 0)
    except (TypeError, ValueError):
        return "Rp0"
    return "Rp" + f"{n:,.0f}".replace(",", ".")


def pct(part: Any, total: Any) -> float:
    try:
        t = float(total or 0)
        if t <= 0:
            return 0.0
        return round(float(part or 0) * 100.0 / t, 2)
    except (TypeError, ValueError):
        return 0.0


SYSTEM_PROMPT = """Anda adalah AI Analis Perencanaan Pembangunan di Bappeda Kota Makassar.
Anda HANYA boleh menjawab berdasarkan BLOK DATA INTERNAL yang diberikan pada tiap
pertanyaan (berasal langsung dari basis data SIDATA). Aturan wajib:

1. JANGAN mengarang angka. Setiap angka yang Anda tulis harus ada di blok data.
   Bila data yang diminta tidak ada di blok data, katakan secara jelas
   "data tersebut belum tersedia di basis data SIDATA" lalu jelaskan data terdekat
   yang tersedia.
2. Selalu sebutkan nama wilayah/OPD persis seperti pada data.
3. Bahasa Indonesia formal pemerintahan, ringkas, padat, tanpa basa-basi.
4. Angka rupiah ditulis lengkap dengan pemisah titik (contoh: Rp113.335.267.540).
5. Jawaban WAJIB memakai struktur heading markdown berikut, dengan urutan ini,
   tanpa menambah atau mengurangi heading:

## Ringkasan Analisis
(2-4 kalimat inti jawaban atas pertanyaan)

## Data Pendukung
(daftar poin berisi angka konkret dari blok data; sertakan nama kolektif sumber,
misal "agregat kelurahan (village_stats)")

## Faktor Utama
(3-5 poin faktor penyebab/pendorong berdasarkan indikator pada data:
kerentanan rumah, sanitasi, air minum, listrik, desil kesejahteraan, disabilitas, dll.)

## Program Terkait
(program/kegiatan/sub kegiatan beserta OPD penanggung jawab dan pagu anggaran bila
tersedia pada data; bila tidak ada, tulis "Belum ada program terkait pada data yang tersedia")

## Rekomendasi
(3-5 rekomendasi tindakan konkret, terukur, dan realistis untuk Pemerintah Kota Makassar)

## Tingkat Prioritas
(satu dari: SANGAT TINGGI / TINGGI / SEDANG / RENDAH, ditulis tebal, diikuti 1-2
kalimat alasan berbasis angka)

Maksimal sekitar 600 kata.
"""


class AskInput(BaseModel):
    question: str = Field(..., min_length=3, max_length=1200)
    session_id: Optional[str] = None
    model: Optional[str] = None
    wilayah: Optional[str] = None


# --------------------------------------------------------------- context
KEYWORDS = {
    "wilayah": ["wilayah", "prioritas", "kelurahan", "kecamatan", "daerah", "lokasi",
                "peta", "ranking", "urutan", "terparah", "tertinggi", "mana"],
    "faktor": ["faktor", "penyebab", "kenapa", "mengapa", "akar masalah", "kerentanan",
               "sanitasi", "air", "listrik", "rumah", "hunian", "desil", "kemiskinan",
               "miskin", "rentan"],
    "stunting": ["stunting", "anggaran", "pagu", "budget", "2025", "2026", "gizi",
                 "balita", "konvergensi", "apbd"],
    "disabilitas": ["disabilitas", "tunanetra", "tunarungu", "disabilitas buta",
                    "disabilitas tuli", "buta", "tuli", "low vision", "difabel",
                    "penyandang", "rad", "inklusi"],
    "rad": ["rad", "rencana aksi", "monitoring", "target", "strategi", "kebijakan"],
    "opd": ["opd", "dinas", "skpd", "perangkat daerah", "instansi", "badan", "siapa"],
    "rumah": ["rumah", "bangunan", "polygon", "gis", "bantuan", "rtlh"],
    "peta_dasar": ["peta dasar", "peta", "spasial", "gis", "jalan", "infrastruktur",
                   "jembatan", "sungai", "kanal", "drainase", "banjir", "garis pantai",
                   "penutup lahan", "tata ruang", "rth", "ruang terbuka", "permukiman",
                   "sawah", "tambak", "kontur", "topografi", "luas wilayah", "toponimi",
                   "fasilitas", "fasilitas umum", "masjid", "sekolah", "puskesmas",
                   "kantor lurah", "sarana", "aksesibilitas fisik"],
}


def _wants(q: str, topic: str) -> bool:
    return any(k in q for k in KEYWORDS[topic])


async def build_context(db, question: str, wilayah: Optional[str] = None
                        ) -> Tuple[str, List[Dict[str, Any]]]:
    """Susun blok data internal + daftar referensi berdasarkan isi pertanyaan."""
    q = (question or "").lower()
    refs: List[Dict[str, Any]] = []
    blocks: List[str] = []

    def ref(sumber: str, label: str, jumlah: Any, endpoint: str):
        refs.append({"sumber": sumber, "label": label, "jumlah": jumlah, "endpoint": endpoint})

    wil_norm = norm_name(wilayah) if wilayah else ""

    # ---- blok dasar: profil kota (selalu disertakan)
    districts = await db.district_stats.find({}).to_list(100)
    villages = await db.village_stats.find({}).to_list(2000)
    total_hh = sum(int(d.get("total_households") or 0) for d in districts)
    total_ind = sum(int(d.get("total_individu") or 0) for d in districts)
    if villages:
        blocks.append(
            "### PROFIL DATA SOSIAL (DTSEN, agregat)\n"
            f"- Jumlah kecamatan berdata: {len(districts)}\n"
            f"- Jumlah kelurahan berdata: {len(villages)}\n"
            f"- Total rumah tangga: {total_hh}\n"
            f"- Total individu: {total_ind}\n"
        )
        ref("village_stats", "Agregat kerentanan per kelurahan", len(villages), "/api/sosial/ranking")
        ref("district_stats", "Agregat kerentanan per kecamatan", len(districts), "/api/sosial/overview")
    else:
        blocks.append(
            "### PROFIL DATA SOSIAL (DTSEN, agregat)\n"
            "- BELUM ADA DATA: koleksi village_stats/district_stats masih kosong "
            "(data DTSEN belum diimpor).\n")

    # ---- wilayah prioritas
    if villages and (_wants(q, "wilayah") or _wants(q, "faktor") or wil_norm):
        rows = sorted(villages, key=lambda v: float(v.get("skor_prioritas") or 0), reverse=True)
        if wil_norm:
            match = [v for v in rows if wil_norm in norm_name(v.get("kelurahan"))
                     or wil_norm in norm_name(v.get("kecamatan"))]
            rows = match or rows
        lines = []
        for v in rows[:12]:
            lines.append(
                f"- {v.get('kelurahan')} (Kec. {v.get('kecamatan')}): "
                f"skor prioritas {v.get('skor_prioritas')}, KK {v.get('total_households')}, "
                f"rata2 risiko {v.get('avg_risk')}, desil 1-2 {v.get('desil_1_2')} "
                f"({v.get('persen_desil_1_2')}%), rumah rentan {v.get('rumah_rentan')} "
                f"({v.get('persen_rumah_rentan')}%), sanitasi tidak layak "
                f"{v.get('sanitasi_tidak_layak')}, air rentan {v.get('air_rentan')}, "
                f"hunian rentan {v.get('hunian_rentan')}, disabilitas {v.get('disabilitas')}, "
                f"prioritas tinggi/sangat tinggi {v.get('prioritas_tinggi')}")
        blocks.append("### WILAYAH PRIORITAS (12 teratas menurut skor_prioritas 0-100)\n"
                      + "\n".join(lines) + "\n\nCatatan metode skor prioritas: "
                      "0,40*rata2 risiko + 0,25*%desil 1-2 + 0,20*%rumah rentan + "
                      "0,15*indeks disabilitas.\n")
        # rekap per kecamatan
        dl = []
        for d in sorted(districts, key=lambda x: float(x.get("avg_risk") or 0), reverse=True):
            dl.append(f"- Kec. {d.get('kecamatan')}: KK {d.get('total_households')}, "
                      f"kelurahan {d.get('jumlah_kelurahan')}, rata2 risiko {d.get('avg_risk')}, "
                      f"desil 1-2 {d.get('desil_1_2')} ({d.get('persen_desil_1_2')}%), "
                      f"rumah rentan {d.get('rumah_rentan')} ({d.get('persen_rumah_rentan')}%), "
                      f"disabilitas {d.get('disabilitas')}")
        if dl:
            blocks.append("### REKAP PER KECAMATAN\n" + "\n".join(dl) + "\n")

    # ---- faktor penyebab (agregat kota)
    if villages and (_wants(q, "faktor") or _wants(q, "wilayah")):
        agg = {k: sum(int(v.get(k) or 0) for v in villages) for k in
               ("rumah_rentan", "sanitasi_tidak_layak", "air_rentan", "hunian_rentan",
                "listrik_rentan", "perlu_validasi", "pbi_nas", "pbi_pemda", "disabilitas")}
        per_desil: Dict[str, int] = {}
        per_risk: Dict[str, int] = {}
        for v in villages:
            for k, val in (v.get("per_desil") or {}).items():
                per_desil[str(k)] = per_desil.get(str(k), 0) + int(val or 0)
            for k, val in (v.get("per_risk") or {}).items():
                per_risk[str(k)] = per_risk.get(str(k), 0) + int(val or 0)
        blocks.append(
            "### FAKTOR KERENTANAN TINGKAT KOTA (dari indikator DTSEN)\n"
            f"- Rumah tidak layak/rentan: {agg['rumah_rentan']} KK ({pct(agg['rumah_rentan'], total_hh)}%)\n"
            f"- Sanitasi tidak layak: {agg['sanitasi_tidak_layak']} KK ({pct(agg['sanitasi_tidak_layak'], total_hh)}%)\n"
            f"- Sumber air rentan: {agg['air_rentan']} KK ({pct(agg['air_rentan'], total_hh)}%)\n"
            f"- Hunian rentan (kepadatan/luas per kapita): {agg['hunian_rentan']} KK ({pct(agg['hunian_rentan'], total_hh)}%)\n"
            f"- Listrik rentan: {agg['listrik_rentan']} KK ({pct(agg['listrik_rentan'], total_hh)}%)\n"
            f"- Penerima PBI Nasional: {agg['pbi_nas']} KK; PBI Pemda: {agg['pbi_pemda']} KK\n"
            f"- Anggota keluarga disabilitas (rekap wilayah): {agg['disabilitas']}\n"
            f"- Sebaran desil nasional: {json.dumps(per_desil, ensure_ascii=False)}\n"
            f"- Sebaran tingkat risiko: {json.dumps(per_risk, ensure_ascii=False)}\n"
            f"- Data perlu validasi: {agg['perlu_validasi']} KK\n")

    # ---- stunting & anggaran
    if _wants(q, "stunting") or _wants(q, "opd"):
        subs = await db.stunting_subactivities.find({}).to_list(5000)
        if subs:
            t25 = sum(float(s.get("anggaran_2025") or 0) for s in subs)
            t26 = sum(float(s.get("anggaran_2026") or 0) for s in subs)
            per_opd: Dict[str, Dict[str, float]] = {}
            for s in subs:
                o = per_opd.setdefault(s.get("opd") or "-", {"a25": 0.0, "a26": 0.0, "n": 0})
                o["a25"] += float(s.get("anggaran_2025") or 0)
                o["a26"] += float(s.get("anggaran_2026") or 0)
                o["n"] += 1
            lines = []
            for name, o in sorted(per_opd.items(), key=lambda x: -x[1]["a25"])[:15]:
                delta = o["a26"] - o["a25"]
                lines.append(
                    f"- {name}: 2025 {rp(o['a25'])} → 2026 {rp(o['a26'])} "
                    f"(selisih {rp(delta)}, {pct(delta, o['a25'] or 1)}%), {int(o['n'])} sub kegiatan")
            top = sorted(subs, key=lambda s: -float(s.get("anggaran_2025") or 0))[:10]
            tl = [f"- {s.get('nama')} | Program: {s.get('program')} | OPD: {s.get('opd')} | "
                  f"2025 {rp(s.get('anggaran_2025'))} | 2026 {rp(s.get('anggaran_2026'))} | "
                  f"indikator: {s.get('indikator') or '-'}" for s in top]
            blocks.append(
                "### ANGGARAN PENANGANAN STUNTING (matriks konvergensi)\n"
                f"- Jumlah sub kegiatan: {len(subs)}; jumlah OPD: {len(per_opd)}\n"
                f"- TOTAL ANGGARAN 2025: {rp(t25)}\n"
                f"- TOTAL ANGGARAN 2026: {rp(t26)}\n"
                f"- SELISIH 2026 vs 2025: {rp(t26 - t25)} ({pct(t26 - t25, t25 or 1)}%)\n"
                "- Rincian per OPD (urut pagu 2025):\n" + "\n".join(lines) +
                "\n- 10 sub kegiatan dengan pagu 2025 terbesar:\n" + "\n".join(tl) + "\n")
            ref("stunting_subactivities", "Sub kegiatan & anggaran stunting 2025-2026",
                len(subs), "/api/stunting/overview")
        else:
            blocks.append("### ANGGARAN PENANGANAN STUNTING\n- BELUM ADA DATA: koleksi "
                          "stunting_subactivities masih kosong.\n")

    # ---- disabilitas
    if _wants(q, "disabilitas"):
        region = await db.disability_region_stats.find({}).to_list(1000)
        opd_dis = await db.disability_opd_stats.find({}).to_list(200)
        if region or opd_dis:
            per_kec: Dict[str, int] = {}
            for r in region:
                per_kec[r.get("kecamatan") or "-"] = per_kec.get(r.get("kecamatan") or "-", 0) \
                    + int(r.get("jumlah") or 0)
            ragam: Dict[str, int] = {}
            for o in opd_dis:
                for k, v in (o.get("ragam") or {}).items():
                    ragam[k] = ragam.get(k, 0) + int(v or 0)
            top_kel = sorted(region, key=lambda r: -int(r.get("jumlah") or 0))[:10]
            blocks.append(
                "### DATA DISABILITAS\n"
                f"- Total tercatat pada rekap wilayah: {sum(per_kec.values())}\n"
                f"- Per kecamatan: {json.dumps(per_kec, ensure_ascii=False)}\n"
                f"- Ragam disabilitas (rekap SKPD): {json.dumps(ragam, ensure_ascii=False)}\n"
                "- 10 kelurahan terbanyak: " + "; ".join(
                    f"{r.get('kelurahan')} ({r.get('kecamatan')}) {r.get('jumlah')}"
                    for r in top_kel) + "\n"
                f"- Jumlah SKPD pelapor: {len(opd_dis)}\n")
            ref("disability_region_stats", "Rekap disabilitas per wilayah", len(region),
                "/api/disabilitas/overview")
        else:
            blocks.append("### DATA DISABILITAS\n- BELUM ADA DATA pada koleksi "
                          "disability_region_stats/disability_opd_stats.\n")

    # ---- RAD disabilitas
    if _wants(q, "rad") or _wants(q, "disabilitas"):
        items = await db.rad_items.find({}).to_list(2000)
        if items:
            monitor = {m.get("item_id"): m for m in await db.rad_monitoring.find({}).to_list(2000)}
            tahun: Dict[str, float] = {}
            for it in items:
                for t, v in (it.get("targets") or {}).items():
                    if v is not None:
                        tahun[t] = tahun.get(t, 0.0) + float(v)
            status: Dict[str, int] = {}
            for it in items:
                st = (monitor.get(it.get("id")) or {}).get("status") or "Belum Dimulai"
                status[st] = status.get(st, 0) + 1
            sample = [f"- {it.get('program') or '-'} / {it.get('kegiatan') or '-'}: "
                      f"indikator {it.get('indikator_capaian') or '-'}, target "
                      f"{json.dumps(it.get('targets') or {}, ensure_ascii=False)}"
                      for it in items[:10]]
            blocks.append(
                "### RAD PENYANDANG DISABILITAS 2025-2030\n"
                f"- Jumlah item: {len(items)}\n"
                f"- Total target per tahun: {json.dumps(tahun, ensure_ascii=False)}\n"
                f"- Status monitoring: {json.dumps(status, ensure_ascii=False)}\n"
                "- Contoh item:\n" + "\n".join(sample) + "\n")
            ref("rad_items", "Item Rencana Aksi Daerah disabilitas", len(items), "/api/rad/overview")
        else:
            blocks.append("### RAD PENYANDANG DISABILITAS\n- BELUM ADA DATA pada koleksi rad_items.\n")

    # ---- data rumah / GIS
    if _wants(q, "rumah"):
        rumah = await db.rumah.find({}).to_list(20000)
        if rumah:
            st: Dict[str, int] = {}
            bantuan: Dict[str, int] = {}
            for r in rumah:
                st[r.get("status") or "-"] = st.get(r.get("status") or "-", 0) + 1
                b = str(r.get("bantuan") or "Tidak ada")
                bantuan[b] = bantuan.get(b, 0) + 1
            blocks.append(
                "### DATA RUMAH (GIS level bangunan)\n"
                f"- Jumlah bangunan terpetakan: {len(rumah)}\n"
                f"- Sebaran status kondisi: {json.dumps(st, ensure_ascii=False)}\n"
                f"- Sebaran bantuan diterima: {json.dumps(dict(list(bantuan.items())[:12]), ensure_ascii=False)}\n")
            ref("rumah", "Polygon rumah terpetakan", len(rumah), "/api/rumah/stats")

    # ---- peta dasar (infrastruktur & fasilitas umum dari PETA_DASAR.gdb)
    if _wants(q, "peta_dasar") or _wants(q, "wilayah"):
        layers = await db.peta_dasar_layers.find({}).to_list(50)
        if layers:
            by_id = {str(l.get("id")): l for l in layers}

            def lval(lid: str, field: str) -> Any:
                return (by_id.get(lid) or {}).get(field) or 0

            penutup = (by_id.get("penutup_lahan") or {}).get("per_kategori") or []
            top_penutup = sorted(penutup, key=lambda x: -float(x.get("luas_ha") or 0))[:8]
            jalan = (by_id.get("jalan_utama") or {}).get("per_kategori") or []
            blocks.append(
                "### PETA DASAR KOTA MAKASSAR (Edisi 2021, BIG — 13 layer spasial)\n"
                f"- Luas wilayah administrasi: {lval('batas_kelurahan', 'luas_ha')} ha "
                f"({lval('batas_kelurahan', 'jumlah')} kelurahan)\n"
                f"- Panjang jalan utama: {lval('jalan_utama', 'panjang_km')} km; "
                f"jalan lingkungan: {lval('jalan_lingkungan', 'panjang_km')} km\n"
                f"- Jalan utama per fungsi (km): "
                f"{json.dumps({j.get('kategori'): j.get('panjang_km') for j in jalan}, ensure_ascii=False)}\n"
                f"- Sungai/kanal: {lval('perairan_garis', 'panjang_km')} km; "
                f"luas perairan: {lval('perairan_area', 'luas_ha')} ha; "
                f"garis pantai: {lval('garis_pantai', 'panjang_km')} km\n"
                f"- Jembatan: {lval('jembatan', 'jumlah')} titik\n"
                f"- Penutup lahan terluas (ha): "
                f"{json.dumps({p.get('kategori'): p.get('luas_ha') for p in top_penutup}, ensure_ascii=False)}\n")
            ref("peta_dasar_layers", "Statistik layer peta dasar (PETA_DASAR.gdb)",
                len(layers), "/api/peta-dasar/stats")

        fas = await db.fasilitas_umum.find({}).to_list(5000)
        if fas:
            if wil_norm:
                fokus = [f for f in fas if wil_norm in norm_name(f.get("kelurahan"))
                         or wil_norm in norm_name(f.get("kecamatan"))]
            else:
                fokus = fas
            per_klas: Dict[str, int] = {}
            per_jenis: Dict[str, int] = {}
            for f in fokus:
                k = str(f.get("klasifikasi") or "Lainnya")
                per_klas[k] = per_klas.get(k, 0) + 1
                j = str(f.get("jenis") or "Lainnya")
                per_jenis[j] = per_jenis.get(j, 0) + 1
            top_jenis = dict(sorted(per_jenis.items(), key=lambda kv: -kv[1])[:12])
            lingkup = f"wilayah fokus ({wilayah})" if wil_norm and fokus else "seluruh kota"
            blocks.append(
                f"### FASILITAS UMUM / TOPONIMI ({lingkup})\n"
                f"- Total titik fasilitas: {len(fokus)} dari {len(fas)} titik kota\n"
                f"- Per klasifikasi: {json.dumps(per_klas, ensure_ascii=False)}\n"
                f"- Jenis terbanyak: {json.dumps(top_jenis, ensure_ascii=False)}\n")
            ref("fasilitas_umum", "Titik fasilitas umum/toponimi peta dasar",
                len(fas), "/api/peta-dasar/fasilitas")

    # ---- OPD
    if _wants(q, "opd"):
        opds = await db.opd.find({}).to_list(500)
        if opds:
            blocks.append("### DAFTAR OPD TERCATAT\n" + "; ".join(
                str(o.get("nama") or o.get("skpd") or "-") for o in opds[:40]) + "\n")
            ref("opd", "Daftar OPD", len(opds), "/api/stunting/overview")

    # ---- data lama (matriks kota) sebagai pelengkap
    regions = await db.regions.find({}).to_list(100)
    if regions and (_wants(q, "faktor") or _wants(q, "wilayah") or _wants(q, "stunting")):
        rl = [f"- {r.get('nama')}: KK kemiskinan ekstrim {r.get('kemiskinan_ekstrim_kk', 0)}, "
              f"persentase kemiskinan {r.get('kemiskinan_persen', 0)}%, balita stunting "
              f"{r.get('stunting_anak', 0)}, ATS {r.get('ats', 0)}, anak jalanan "
              f"{r.get('anak_jalanan', 0)}, disabilitas {r.get('disabilitas', 0)}, "
              f"{r.get('kelurahan', 0)} kelurahan" for r in regions]
        blocks.append("### MATRIKS KOTA PER KECAMATAN (15 kecamatan, sumber dashboard SIDATA)\n"
                      + "\n".join(rl) + "\n")
        ref("regions", "Matriks kota per kecamatan", len(regions), "/api/stats/overview")

    if not refs:
        ref("kosong", "Tidak ada koleksi data yang relevan/berisi untuk pertanyaan ini", 0, "-")

    return "\n".join(blocks), refs


# --------------------------------------------------------------- router
def build_router(db, current_user_dep, editor_dep, admin_dep) -> APIRouter:
    router = APIRouter(tags=["ai-assistant"])

    async def optional_user(request: Request) -> Optional[dict]:
        try:
            return await current_user_dep(request)
        except Exception:
            return None

    @router.get("/ai/models")
    async def list_models(refresh: bool = Query(False)):
        """Semua model yang tersedia untuk API key Hostlinku (GET /v1/models, cache 10 menit)."""
        if not llm_hostlinku.tersedia():
            return {"default": DEFAULT_MODEL, "items": [], "provider": "hostlinku", "aktif": False}
        items = await llm_hostlinku.katalog_model(paksa=refresh)
        default = DEFAULT_MODEL if any(m["id"] == DEFAULT_MODEL for m in items) \
            else (items[0]["id"] if items else DEFAULT_MODEL)
        return {"default": default, "items": items, "total": len(items),
                "provider": "hostlinku", "aktif": True}

    @router.get("/ai/status")
    async def ai_status(user: dict = Depends(current_user_dep)):
        """Diagnostik provider AI (tanpa membocorkan API key)."""
        return {
            "default_model": DEFAULT_MODEL,
            "hostlinku": await llm_hostlinku.cek_koneksi(),
        }

    @router.get("/ai/suggestions")
    async def suggestions():
        return {"items": [
            "Kelurahan mana yang paling prioritas untuk intervensi kemiskinan dan apa alasannya?",
            "Apa faktor utama penyebab kerentanan rumah tangga di Kecamatan Tallo?",
            "Bandingkan anggaran penanganan stunting 2025 dan 2026, apa implikasinya?",
            "OPD mana yang paling relevan menangani stunting beserta pagu anggarannya?",
            "Bagaimana sebaran penyandang disabilitas dan program RAD yang menanganinya?",
            "Wilayah mana yang paling butuh perbaikan sanitasi dan air minum?",
        ]}

    @router.get("/ai/data-context")
    async def data_context(q: str = Query(..., min_length=3),
                           wilayah: Optional[str] = None,
                           user: dict = Depends(current_user_dep)):
        """Pratinjau blok data internal yang akan dikirim ke model (untuk audit)."""
        ctx, refs = await build_context(db, q, wilayah)
        return {"pertanyaan": q, "panjang_konteks": len(ctx), "referensi": refs,
                "konteks": ctx}

    async def _history_text(session_id: str, limit: int = 6) -> str:
        docs = await db.ai_chat_messages.find({"session_id": session_id}) \
            .sort("created_at", -1).to_list(limit)
        docs = list(reversed(docs))
        if not docs:
            return ""
        lines = []
        for d in docs:
            role = "PENGGUNA" if d.get("role") == "user" else "ASISTEN"
            content = str(d.get("content") or "")
            lines.append(f"{role}: {content[:900]}")
        return "\n".join(lines)

    @router.post("/ai/ask")
    async def ai_ask(inp: AskInput, request: Request):
        user = await optional_user(request)
        model = await resolve_model_async(inp.model)
        if not provider_tersedia(model["provider"]):
            raise HTTPException(status_code=503,
                                detail="HOSTLINKU_API_KEY belum dikonfigurasi di server")
        session_id = inp.session_id or str(uuid.uuid4())
        question = inp.question.strip()

        ctx, refs = await build_context(db, question, inp.wilayah)
        history = await _history_text(session_id)

        await db.ai_chat_messages.insert_one({
            "id": str(uuid.uuid4()), "session_id": session_id, "role": "user",
            "content": question, "created_at": now_iso(),
            "user": (user or {}).get("email"), "model": model["id"],
        })
        try:
            existing = await db.ai_chat_sessions.find_one({"id": session_id})
            if existing is None:
                await db.ai_chat_sessions.insert_one({
                    "id": session_id, "judul": question[:80],
                    "created_at": now_iso(), "updated_at": now_iso(),
                    "user": (user or {}).get("email"), "jumlah_pesan": 1})
            else:
                await db.ai_chat_sessions.update_one(
                    {"id": session_id},
                    {"$set": {"updated_at": now_iso()},
                     "$inc": {"jumlah_pesan": 1}})
        except Exception:
            logger.exception("Gagal mencatat sesi chat AI")

        prompt_parts = [
            "=== BLOK DATA INTERNAL SIDATA (satu-satunya sumber angka yang boleh dipakai) ===",
            ctx or "(tidak ada data relevan)",
            "=== AKHIR BLOK DATA ===",
        ]
        if history:
            prompt_parts += ["", "Riwayat percakapan sebelumnya (untuk konteks lanjutan):", history]
        prompt_parts += ["", f"PERTANYAAN PENGGUNA: {question}", "",
                         "Jawab memakai struktur enam heading yang telah ditentukan."]
        prompt = "\n".join(prompt_parts)

        async def _stream_jawaban():
            """Streaming teks jawaban dari Hostlinku (tanpa reasoning_content)."""
            messages = [{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}]
            async for delta in llm_hostlinku.stream_chat(messages, model=model["id"]):
                yield delta

        async def event_generator():
            yield f"data: {json.dumps({'session_id': session_id, 'model': model['id'], 'provider': model['provider'], 'refs': refs}, ensure_ascii=False)}\n\n"
            chunks: List[str] = []
            try:
                async for delta in _stream_jawaban():
                    chunks.append(delta)
                    yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
            except Exception as e:  # kuota habis / jaringan / model tidak dikenal
                logger.exception("AI ask error")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                return
            full = "".join(chunks)
            msg_id = str(uuid.uuid4())
            try:
                await db.ai_chat_messages.insert_one({
                    "id": msg_id, "session_id": session_id, "role": "assistant",
                    "content": full, "refs": refs, "model": model["id"],
                    "created_at": now_iso(), "user": (user or {}).get("email"),
                })
                await db.ai_chat_sessions.update_one(
                    {"id": session_id},
                    {"$set": {"updated_at": now_iso(), "ringkasan": full[:200]},
                     "$inc": {"jumlah_pesan": 1}})
                await db.ai_analyses.insert_one({
                    "id": msg_id, "kategori": "assistant",
                    "kategori_label": "AI Assistant (data-aware)",
                    "wilayah": inp.wilayah or "Kota Makassar",
                    "pertanyaan": question, "hasil": full,
                    "ringkasan": (question[:160]).replace("\n", " ").strip(),
                    "model": model["id"], "created_at": now_iso(),
                })
            except Exception:
                logger.exception("Gagal menyimpan pesan AI")
            yield f"data: {json.dumps({'done': True, 'message_id': msg_id}, ensure_ascii=False)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache",
                                          "X-Accel-Buffering": "no"})

    @router.get("/ai/chat-sessions")
    async def chat_sessions(limit: int = Query(50, ge=1, le=200)):
        docs = await db.ai_chat_sessions.find({}).sort("updated_at", -1).to_list(limit)
        return {"total": len(docs), "items": [
            {k: v for k, v in d.items() if k != "_id"} for d in docs]}

    @router.get("/ai/chat/{session_id}")
    async def chat_detail(session_id: str):
        docs = await db.ai_chat_messages.find({"session_id": session_id}) \
            .sort("created_at", 1).to_list(200)
        sess = await db.ai_chat_sessions.find_one({"id": session_id})
        return {"session_id": session_id,
                "judul": (sess or {}).get("judul"),
                "items": [{k: v for k, v in d.items() if k != "_id"} for d in docs]}

    @router.delete("/ai/chat/{session_id}")
    async def chat_delete(session_id: str, user: dict = Depends(current_user_dep)):
        await db.ai_chat_messages.delete_many({"session_id": session_id})
        res = await db.ai_chat_sessions.delete_one({"id": session_id})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Sesi chat tidak ditemukan")
        return {"message": "Sesi chat dihapus"}

    return router
