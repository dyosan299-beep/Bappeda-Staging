#!/usr/bin/env bash
# =============================================================================
#  Smoke test runtime — memastikan setiap halaman termuat TANPA error JavaScript.
#
#  Kenapa ini perlu:
#  `yarn build` yang hijau TIDAK menangkap error runtime seperti
#  "Cannot access 'pageTitle' before initialization" (TDZ) atau
#  "Cannot read properties of undefined". Bug seperti itu baru terlihat saat
#  halaman benar-benar dibuka di browser.
#
#  Tanpa dependency Node apa pun: hanya butuh Chrome/Chromium dan bash.
#
#  Pemakaian:
#      scripts/a11y-smoke.sh
#      BASE_URL=http://localhost:3000 scripts/a11y-smoke.sh
#      CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe" scripts/a11y-smoke.sh
#
#  Exit code 0 bila semua halaman bersih, 1 bila ada yang gagal.
# =============================================================================
set -uo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:3000}"
BUDGET="${BUDGET:-8000}"

# --- Cari Chrome ------------------------------------------------------------
if [ -z "${CHROME:-}" ]; then
  for kandidat in \
    "/c/Program Files/Google/Chrome/Application/chrome.exe" \
    "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
    "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
    google-chrome chromium chromium-browser google-chrome-stable; do
    if [ -x "$kandidat" ] || command -v "$kandidat" >/dev/null 2>&1; then
      CHROME="$kandidat"
      break
    fi
  done
fi

if [ -z "${CHROME:-}" ]; then
  echo "GAGAL: Chrome/Chromium tidak ditemukan. Set variabel CHROME." >&2
  exit 1
fi

# --- Halaman yang diuji -----------------------------------------------------
# Semua route di bawah dapat dimuat tanpa login. Route internal yang dijaga
# ProtectedRoute tetap diuji: shell-nya (SidebarLayout) dirender lebih dulu,
# jadi error pada shell tetap tertangkap.
ROUTES=(
  "/"
  "/login"
  "/publik"
  "/publik/peta-sosial"
  "/tentang"
  "/flow-sistem"
  "/aksesibilitas"
  "/bantuan"
  "/disabilitas"
  "/peta-sosial"
  "/kelola-petugas"
  "/verval"
  "/dashboard"
)

# Pola yang menandakan halaman gagal dirender.
POLA=(
  "Uncaught runtime errors"
  "before initialization"
  "Cannot read properties of"
  "is not a function"
)

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

gagal=0
total=0

echo "Base URL : $BASE_URL"
echo "Chrome   : $CHROME"
echo ""

for rute in "${ROUTES[@]}"; do
  total=$((total + 1))
  out="$TMP/halaman.html"

  "$CHROME" --headless=new --disable-gpu --no-sandbox --no-first-run \
    --user-data-dir="$TMP/prof" --virtual-time-budget="$BUDGET" \
    --dump-dom "${BASE_URL}${rute}" >"$out" 2>/dev/null

  masalah=""
  for pola in "${POLA[@]}"; do
    if grep -qF "$pola" "$out"; then
      masalah="${masalah}${pola}; "
    fi
  done

  # Halaman harus benar-benar menghasilkan DOM aplikasi.
  if ! grep -q 'id="root"' "$out"; then
    masalah="${masalah}DOM kosong (root tidak ada); "
  fi

  if [ -z "$masalah" ]; then
    printf "  OK    %s\n" "$rute"
  else
    printf "  GAGAL %s -> %s\n" "$rute" "$masalah"
    gagal=$((gagal + 1))
  fi
done

echo ""
if [ "$gagal" -eq 0 ]; then
  echo "LULUS: $total/$total halaman tanpa error runtime."
  exit 0
fi
echo "GAGAL: $gagal dari $total halaman bermasalah."
echo "Petunjuk: buka halaman terkait di browser dan lihat console."
exit 1
