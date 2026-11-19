"""Konversi angka ke kata Bahasa Indonesia (terbilang) untuk kejelasan TTS."""
import re

SATUAN = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan",
          "sembilan", "sepuluh", "sebelas"]


def _terbilang(n: int) -> str:
    n = int(n)
    if n < 0:
        return "minus " + _terbilang(-n)
    if n < 12:
        return SATUAN[n] if n > 0 else "nol"
    if n < 20:
        return _terbilang(n - 10) + " belas"
    if n < 100:
        return _terbilang(n // 10) + " puluh" + ((" " + _terbilang(n % 10)) if n % 10 else "")
    if n < 200:
        return "seratus" + ((" " + _terbilang(n - 100)) if n > 100 else "")
    if n < 1000:
        return _terbilang(n // 100) + " ratus" + ((" " + _terbilang(n % 100)) if n % 100 else "")
    if n < 2000:
        return "seribu" + ((" " + _terbilang(n - 1000)) if n > 1000 else "")
    if n < 1_000_000:
        return _terbilang(n // 1000) + " ribu" + ((" " + _terbilang(n % 1000)) if n % 1000 else "")
    if n < 1_000_000_000:
        return _terbilang(n // 1_000_000) + " juta" + ((" " + _terbilang(n % 1_000_000)) if n % 1_000_000 else "")
    if n < 1_000_000_000_000:
        return _terbilang(n // 1_000_000_000) + " miliar" + ((" " + _terbilang(n % 1_000_000_000)) if n % 1_000_000_000 else "")
    return _terbilang(n // 1_000_000_000_000) + " triliun" + ((" " + _terbilang(n % 1_000_000_000_000)) if n % 1_000_000_000_000 else "")


def _digits_spoken(s: str) -> str:
    # baca digit desimal satu per satu: "6" -> "enam", "05" -> "nol lima"
    words = []
    for ch in s:
        words.append("nol" if ch == "0" else SATUAN[int(ch)])
    return " ".join(words)


def _replace(match: re.Match) -> str:
    token = match.group(0)
    percent = token.endswith("%")
    core = token[:-1] if percent else token
    # pisahkan desimal (koma) — format Indonesia: titik = ribuan, koma = desimal
    if "," in core:
        int_part, dec_part = core.split(",", 1)
    else:
        int_part, dec_part = core, ""
    int_clean = int_part.replace(".", "")
    if not int_clean.isdigit():
        return token
    try:
        words = _terbilang(int(int_clean))
    except Exception:
        return token
    if dec_part and dec_part.isdigit():
        words += " koma " + _digits_spoken(dec_part)
    if percent:
        words += " persen"
    return words


# angka dengan pemisah ribuan/desimal dan opsional persen
_NUM_RE = re.compile(r"\d[\d.]*(?:,\d+)?%?")


def expand_numbers(text: str) -> str:
    text = text.replace("Rp", "rupiah ")
    return _NUM_RE.sub(_replace, text)
