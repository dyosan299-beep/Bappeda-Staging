#!/usr/bin/env bash
# Menjalankan MariaDB untuk lingkungan preview/pengembangan.
# - datadir diletakkan di /app/.data/mysql (volume persisten) agar data tidak
#   hilang saat container restart.
# - binari dipasang otomatis (dari cache .deb bila tersedia) bila hilang.
# - database & user dibuat idempotent via --init-file.
set -u

DATADIR="/app/.data/mysql"
DEB_CACHE="/app/.data/deb"
INIT_SQL="/app/scripts/mariadb_init.sql"

mkdir -p /run/mysqld "$DATADIR"

# pastikan user mysql ada
if ! id -u mysql >/dev/null 2>&1; then
  useradd -r -s /usr/sbin/nologin mysql || true
fi

# pastikan binari tersedia (apt di container ini tidak selalu persisten)
if [ ! -x /usr/sbin/mariadbd ]; then
  echo "[mariadb-dev] mariadbd tidak ditemukan, mencoba memasang ulang..."
  if ls "$DEB_CACHE"/*.deb >/dev/null 2>&1; then
    dpkg -i "$DEB_CACHE"/*.deb >/dev/null 2>&1 || apt-get -y -f install >/dev/null 2>&1
  fi
fi
if [ ! -x /usr/sbin/mariadbd ]; then
  apt-get update -qq >/dev/null 2>&1 && apt-get install -y -q mariadb-server >/dev/null 2>&1
fi
if [ ! -x /usr/sbin/mariadbd ]; then
  echo "[mariadb-dev] GAGAL: mariadbd tidak tersedia" >&2
  exit 1
fi

# inisialisasi datadir bila masih kosong
if [ ! -d "$DATADIR/mysql" ]; then
  echo "[mariadb-dev] Inisialisasi datadir baru di $DATADIR"
  mariadb-install-db --user=mysql --datadir="$DATADIR" \
    --auth-root-authentication-method=normal >/dev/null 2>&1 || \
    mysql_install_db --user=mysql --datadir="$DATADIR" >/dev/null 2>&1
fi

chown -R mysql:mysql /run/mysqld "$DATADIR" 2>/dev/null || true

exec /usr/sbin/mariadbd \
  --user=mysql \
  --datadir="$DATADIR" \
  --socket=/run/mysqld/mysqld.sock \
  --bind-address=127.0.0.1 \
  --port=3306 \
  --skip-name-resolve=0 \
  --init-file="$INIT_SQL"
