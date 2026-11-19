# syntax=docker/dockerfile:1.7
# =============================================================================
#  SIDATA Bappeda Kota Makassar - Image produksi (multi-stage)
#  Stack : React (CRA/craco) + FastAPI + MariaDB
#  Target: Coolify (Build Pack = Dockerfile)
#
#  Satu kontainer menyajikan:
#    - API  : /api/*        (FastAPI)
#    - Web  : /*            (hasil build React, dengan fallback SPA)
#
#  Port  : dibaca dari environment variable PORT (default 8000)
# =============================================================================

# -----------------------------------------------------------------------------
# STAGE 1 - Build frontend React
# -----------------------------------------------------------------------------
# Node 20 sudah EOL sejak April 2026. node:24-alpine memakai Node 24.22.1 dan
# tetap menyertakan yarn 1.22.22 (sama dengan "packageManager" di
# frontend/package.json), jadi `yarn install` di bawah tidak perlu diubah.
FROM node:24-alpine AS frontend-builder

WORKDIR /build

# Kosong = frontend memakai origin yang sama (request ke /api pada host Coolify).
# Isi hanya jika API dipisah ke domain lain, mis. https://api.domain.go.id
ARG REACT_APP_BACKEND_URL=""

COPY frontend/package.json frontend/yarn.lock ./

# Plugin visual-edits hanya dipakai saat dev di platform Emergent.
# Dibuang agar build produksi tidak bergantung pada registry eksternal.
RUN node -e "const fs=require('fs'),p=JSON.parse(fs.readFileSync('package.json','utf8'));\
if(p.devDependencies)delete p.devDependencies['@emergentbase/visual-edits'];\
fs.writeFileSync('package.json',JSON.stringify(p,null,2));"

# --production=false wajib: craco/tailwind/postcss ada di devDependencies.
RUN yarn install --production=false --ignore-optional --network-timeout 600000

COPY frontend/ ./

# Buang lagi setelah COPY (package.json asli tertimpa) supaya konsisten.
RUN node -e "const fs=require('fs'),p=JSON.parse(fs.readFileSync('package.json','utf8'));\
if(p.devDependencies)delete p.devDependencies['@emergentbase/visual-edits'];\
fs.writeFileSync('package.json',JSON.stringify(p,null,2));"

ENV CI=false \
    DISABLE_ESLINT_PLUGIN=true \
    GENERATE_SOURCEMAP=false \
    ENABLE_HEALTH_CHECK=false \
    NODE_OPTIONS=--max-old-space-size=3072 \
    REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}

RUN yarn build && test -f build/index.html


# -----------------------------------------------------------------------------
# STAGE 2 - Build dependensi Python ke dalam virtualenv terisolasi
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS backend-builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Toolchain kompilasi hanya ada di stage ini, tidak terbawa ke image final.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libjpeg-dev \
        libfreetype6-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements-prod.txt /tmp/requirements-prod.txt

# Index tambahan dipertahankan untuk kompatibilitas paket internal (tidak wajib).
RUN pip install --upgrade pip wheel setuptools \
    && pip install --no-cache-dir \
         --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
         -r /tmp/requirements-prod.txt \
    && find /opt/venv -name '__pycache__' -type d -prune -exec rm -rf {} + \
    && find /opt/venv -name '*.pyc' -delete


# -----------------------------------------------------------------------------
# STAGE 3 - Image produksi (final, ramping)
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS production

LABEL org.opencontainers.image.title="SIDATA Bappeda Kota Makassar" \
      org.opencontainers.image.description="Sistem Intelijen Data Sosial - FastAPI + React + MariaDB" \
      org.opencontainers.image.vendor="Bappeda Kota Makassar"

# Hanya library runtime (tanpa compiler) + curl untuk healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        libfreetype6 \
        curl \
        tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin --uid 10001 sidata

COPY --from=backend-builder /opt/venv /opt/venv

WORKDIR /srv

# Kode backend
COPY --chown=sidata:sidata backend/ /srv/backend/

# Hasil build React
COPY --from=frontend-builder --chown=sidata:sidata /build/build /srv/frontend/build

# Jangan pernah ikut sertakan .env ke dalam image (kredensial diisi di Coolify).
# Folder /srv/data_upload/_uploads = ruang kerja Import Wizard (unggahan Excel/CSV),
# harus writable oleh user non-root "sidata" yang menjalankan Uvicorn.
RUN rm -f /srv/backend/.env \
    && rm -rf /srv/backend/tests /srv/backend/__pycache__ /srv/backend/pytest.ini \
    && mkdir -p /srv/data_upload/_uploads \
    && chown -R sidata:sidata /srv/data_upload

# CORS_ORIGINS sengaja kosong: deployment satu-origin tidak memerlukan CORS.
# Bila frontend dan backend berbeda origin, isi dengan origin eksplisit
# (mis. https://peta.example.go.id) — JANGAN memakai "*".
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/srv/backend \
    TZ=Asia/Makassar \
    HOST=0.0.0.0 \
    PORT=8000 \
    FRONTEND_BUILD_DIR=/srv/frontend/build \
    IMPORT_UPLOAD_DIR=/srv/data_upload/_uploads \
    DB_PORT=3306 \
    APP_ENV=production \
    CORS_ORIGINS="" \
    COOKIE_SECURE=true \
    COOKIE_SAMESITE=lax \
    WEB_CONCURRENCY=2

USER sidata
WORKDIR /srv/backend

# Coolify meng-expose port dari variabel PORT.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=5 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/health" || exit 1

# exec + ${PORT} agar port benar-benar dapat diatur lewat environment variable.
CMD ["sh", "-c", "exec uvicorn server:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*' --no-server-header --timeout-keep-alive 65"]
