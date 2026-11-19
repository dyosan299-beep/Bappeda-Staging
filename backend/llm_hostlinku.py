"""Klien Hostlinku (gateway AI kompatibel OpenAI) untuk fitur AI SIDATA.

Dokumentasi: https://docs.hostlinku.com/docs/chat-completions

Variabel lingkungan:
  HOSTLINKU_API_KEY     wajib untuk mengaktifkan provider ini (sk-...)
  HOSTLINKU_BASE_URL    default https://api.hostlinku.com/v1
  HOSTLINKU_MODEL       slug model default, default deepseek-v4-1-flash
  HOSTLINKU_MAX_TOKENS  batas token output, default 4000
                        (model DeepSeek V4 adalah model *reasoning*: token berpikir
                        ikut terhitung di max_tokens, jadi jangan terlalu kecil)

Catatan kompatibilitas Hostlinku yang penting:
  * Skema body ketat - field di luar daftar resmi dibuang, jadi tidak ada cara
    mematikan mode reasoning lewat parameter. Chunk `delta.reasoning_content`
    (proses berpikir) sengaja TIDAK diteruskan ke pengguna; hanya `delta.content`.
  * Error envelope: {"status":"error","error":{"code":"...","message":"..."}}.
  * Stream ditutup dengan `data: [DONE]`; bila gagal di tengah dikirim event
    {"error": {...}} tanpa [DONE].
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

logger = logging.getLogger("bappeda.hostlinku")

BASE_URL = (os.environ.get("HOSTLINKU_BASE_URL") or "https://api.hostlinku.com/v1").strip().rstrip("/")
API_KEY = (os.environ.get("HOSTLINKU_API_KEY") or "").strip()
DEFAULT_MODEL = (os.environ.get("HOSTLINKU_MODEL") or "deepseek-v4-1-flash").strip()
try:
    MAX_TOKENS = int(os.environ.get("HOSTLINKU_MAX_TOKENS") or 4000)
except ValueError:
    MAX_TOKENS = 4000

# Katalog cadangan (dipakai hanya bila GET /v1/models gagal / belum ter-cache).
MODELS: List[Dict[str, str]] = [
    {"id": "deepseek-v4-1-flash", "provider": "hostlinku",
     "label": "DeepSeek V4.1 Flash",
     "catatan": "Hemat biaya, penalaran baik - default"},
    {"id": "deepseek-v4-pro", "provider": "hostlinku",
     "label": "DeepSeek V4 Pro",
     "catatan": "Lebih kuat, biaya ~4x Flash"},
    {"id": "qwen3-6-plus", "provider": "hostlinku",
     "label": "Qwen3.6 Plus",
     "catatan": "Alternatif cepat tanpa reasoning panjang"},
]

# Cache katalog dari GET /v1/models (TTL detik) agar dropdown UI cepat & hemat request.
try:
    KATALOG_TTL = int(os.environ.get("HOSTLINKU_MODELS_TTL") or 600)
except ValueError:
    KATALOG_TTL = 600
_katalog_cache: Dict[str, Any] = {"ts": 0.0, "items": []}


_BRAND = {"gpt": "GPT", "glm": "GLM", "deepseek": "DeepSeek", "qwen": "Qwen", "minimax": "MiniMax",
          "kimi": "Kimi", "mimo": "MiMo", "claude": "Claude", "gemini": "Gemini", "llama": "Llama",
          "mistral": "Mistral", "grok": "Grok", "o1": "o1", "o3": "o3", "o4": "o4", "nova": "Nova"}


def _label_dari_slug(slug: str) -> str:
    """'deepseek-v4-1-flash' -> 'DeepSeek V4.1 Flash', 'gpt-5-6-luna' -> 'GPT 5.6 Luna',
    'qwen3-6-plus' -> 'Qwen3.6 Plus', 'kimi-k2-6' -> 'Kimi K2.6'."""
    import re
    out: List[str] = []
    for tok in [t for t in slug.split("-") if t]:
        low = tok.lower()
        if tok.isdigit() and out and re.search(r"\d$", out[-1]):
            out[-1] = f"{out[-1]}.{tok}"            # angka setelah angka -> versi bertitik
            continue
        m = re.fullmatch(r"([a-z]+)(\d+)", low)      # qwen3 / v4 / k2 / m3
        if m and m.group(1) in _BRAND:
            out.append(f"{_BRAND[m.group(1)]}{m.group(2)}")
        elif m and len(m.group(1)) == 1:
            out.append(tok.upper())
        elif low in _BRAND:
            out.append(_BRAND[low])
        else:
            out.append(tok[:1].upper() + tok[1:])
    return " ".join(out)


def _format_harga(p: Optional[Dict[str, Any]]) -> str:
    if not p or p.get("input") is None:
        return "harga tidak tersedia"
    try:
        return f"${float(p['input']):.2f} / ${float(p.get('output') or 0):.2f} per 1M token"
    except (TypeError, ValueError):
        return "harga tidak tersedia"


def _normalisasi_model(m: Dict[str, Any]) -> Dict[str, Any]:
    caps = [c for c in (m.get("capabilities") or []) if isinstance(c, str)]
    tag = []
    if "reasoning" in caps:
        tag.append("reasoning")
    if "vision" in caps:
        tag.append("vision")
    if "tool-calling" in caps or "function-calling" in caps:
        tag.append("tools")
    harga = _format_harga(m.get("pricing"))
    ctx = m.get("context_window")
    ctx_txt = f"konteks {int(ctx) // 1000}k" if isinstance(ctx, (int, float)) and ctx else ""
    catatan = " · ".join(x for x in (harga, ctx_txt, ", ".join(tag)) if x)
    return {
        "id": m.get("id", ""),
        "provider": "hostlinku",
        "label": _label_dari_slug(m.get("id", "")),
        "catatan": catatan,
        "harga_input": (m.get("pricing") or {}).get("input"),
        "harga_output": (m.get("pricing") or {}).get("output"),
        "context_window": ctx,
        "capabilities": caps,
    }


async def katalog_model(paksa: bool = False) -> List[Dict[str, Any]]:
    """Semua model yang tersedia untuk API key ini (GET /v1/models), ter-cache.

    Urutan: default dulu, lalu termurah (harga input+output) ke termahal.
    Bila request gagal dan cache kosong -> kembalikan katalog cadangan MODELS.
    """
    import time
    now = time.time()
    if not paksa and _katalog_cache["items"] and now - _katalog_cache["ts"] < KATALOG_TTL:
        return _katalog_cache["items"]
    if not API_KEY:
        return list(MODELS)
    try:
        mentah = await list_models()
    except Exception as e:  # noqa: BLE001
        logger.warning("Gagal mengambil katalog model Hostlinku: %s", str(e)[:200])
        return _katalog_cache["items"] or list(MODELS)
    items = [_normalisasi_model(m) for m in mentah if m.get("id")]

    def _kunci(m: Dict[str, Any]):
        total = (m.get("harga_input") or 0) + (m.get("harga_output") or 0)
        return (0 if m["id"] == DEFAULT_MODEL else 1, total, m["id"])
    items.sort(key=_kunci)
    for m in items:
        if m["id"] == DEFAULT_MODEL:
            m["catatan"] = "default · " + m["catatan"]
    _katalog_cache.update(ts=now, items=items)
    return items


class HostlinkuError(Exception):
    """Error dari gateway Hostlinku dengan pesan yang sudah dibahasakan."""

    def __init__(self, message: str, code: str = "", status: int = 0):
        super().__init__(message)
        self.code = code
        self.status = status


def tersedia() -> bool:
    """True bila provider Hostlinku siap dipakai (API key terisi)."""
    return bool(API_KEY)


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json",
            "Accept": "application/json"}


_HINT = {
    401: "API key Hostlinku tidak valid/dicabut - periksa HOSTLINKU_API_KEY.",
    402: "Saldo Hostlinku tidak cukup - isi saldo di console.hostlinku.com.",
    403: "Saldo/limit API key Hostlinku tidak cukup - isi saldo di console.hostlinku.com.",
    404: "Slug model tidak ada di katalog Hostlinku - periksa HOSTLINKU_MODEL.",
    429: "Terlalu banyak permintaan ke Hostlinku - coba lagi sebentar.",
    503: "Model/provider di Hostlinku sedang gangguan - coba lagi atau pilih model lain.",
}


def _buat_error(status: int, body: Any) -> HostlinkuError:
    code, message = "", ""
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            code = str(err.get("code") or "")
            message = str(err.get("message") or "")
        elif isinstance(err, str):
            message = err
    elif isinstance(body, str):
        message = body[:300]
    hint = _HINT.get(status, "")
    teks = " ".join(p for p in (f"Hostlinku {status} {code}".strip(), message, hint) if p)
    return HostlinkuError(teks, code=code, status=status)


def _payload(messages: List[Dict[str, Any]], model: Optional[str], temperature: float,
             max_tokens: Optional[int], stream: bool) -> Dict[str, Any]:
    return {
        "model": (model or DEFAULT_MODEL).strip(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": int(max_tokens or MAX_TOKENS),
        "stream": stream,
    }


async def stream_chat(messages: List[Dict[str, Any]], model: Optional[str] = None,
                      temperature: float = 0.3, max_tokens: Optional[int] = None,
                      timeout: float = 180.0) -> AsyncIterator[str]:
    """Streaming SSE: yield potongan teks jawaban (tanpa reasoning_content)."""
    if not API_KEY:
        raise HostlinkuError("HOSTLINKU_API_KEY belum dikonfigurasi di server", code="NO_KEY", status=503)
    payload = _payload(messages, model, temperature, max_tokens, stream=True)
    tmo = httpx.Timeout(timeout, connect=20.0)
    async with httpx.AsyncClient(timeout=tmo) as client:
        async with client.stream("POST", f"{BASE_URL}/chat/completions",
                                 headers=_headers(), json=payload) as resp:
            if resp.status_code >= 400:
                raw = await resp.aread()
                try:
                    body = json.loads(raw.decode("utf-8", "replace"))
                except Exception:
                    body = raw.decode("utf-8", "replace")
                raise _buat_error(resp.status_code, body)
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and obj.get("error"):
                    raise _buat_error(resp.status_code, obj)
                for choice in obj.get("choices") or []:
                    delta = choice.get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content


async def complete(messages: List[Dict[str, Any]], model: Optional[str] = None,
                   temperature: float = 0.3, max_tokens: Optional[int] = None,
                   timeout: float = 180.0) -> Dict[str, Any]:
    """Non-streaming. Mengembalikan {"content", "model", "usage", "cost"}."""
    if not API_KEY:
        raise HostlinkuError("HOSTLINKU_API_KEY belum dikonfigurasi di server", code="NO_KEY", status=503)
    payload = _payload(messages, model, temperature, max_tokens, stream=False)
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=20.0)) as client:
        resp = await client.post(f"{BASE_URL}/chat/completions", headers=_headers(), json=payload)
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    if resp.status_code >= 400 or (isinstance(body, dict) and body.get("status") == "error"):
        raise _buat_error(resp.status_code, body)
    choice = (body.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    return {
        "content": msg.get("content") or "",
        "model": body.get("model"),
        "usage": body.get("usage"),
        "cost": (body.get("hostlinku") or {}).get("cost"),
        "finish_reason": choice.get("finish_reason"),
    }


async def list_models(timeout: float = 20.0) -> List[Dict[str, Any]]:
    """GET /v1/models - model yang tersedia untuk API key ini."""
    if not API_KEY:
        return []
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(f"{BASE_URL}/models", headers=_headers())
    body = resp.json()
    if resp.status_code >= 400:
        raise _buat_error(resp.status_code, body)
    return body.get("data") or []


async def cek_koneksi() -> Dict[str, Any]:
    """Diagnostik ringan untuk /api/ai/status (tanpa membocorkan key)."""
    info: Dict[str, Any] = {"provider": "hostlinku", "base_url": BASE_URL,
                            "model_default": DEFAULT_MODEL, "key_terisi": bool(API_KEY)}
    if not API_KEY:
        info["status"] = "nonaktif"
        return info
    try:
        models = await list_models()
        ids = {m.get("id") for m in models}
        info["status"] = "ok"
        info["jumlah_model"] = len(models)
        info["model_default_tersedia"] = DEFAULT_MODEL in ids
    except Exception as e:  # noqa: BLE001
        info["status"] = "gagal"
        info["pesan"] = str(e)[:300]
    return info
