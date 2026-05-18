# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk web + ws 공통 base image — Phase 4 Docker stack.
# 한글 주석: python:3.13-slim + server/requirements.txt + non-root + healthcheck.

FROM python:3.13-slim AS base

# 한글 주석: OS 패키지 (mariadb-client psql ping curl 등). cache layer 최소화.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && cp /usr/share/zoneinfo/Asia/Seoul /etc/localtime \
    && echo "Asia/Seoul" > /etc/timezone

# 한글 주석: non-root user 의무 — production 권한 격리
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd --gid ${APP_GID} app && \
    useradd --uid ${APP_UID} --gid ${APP_GID} --home /app --shell /bin/bash app

WORKDIR /app

# 한글 주석: requirements 먼저 install (cache friendly layer)
COPY --chown=app:app server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/server/requirements.txt

# 한글 주석: 앱 본문 copy
COPY --chown=app:app server /app/server
COPY --chown=app:app app /app/app

USER app

# 한글 주석: web (REST) + ws (signaling) 의 launcher 분기 의무 — ENV SIGNAL_SERVER_MODE 로 선택
# SIGNAL_SERVER_MODE=ws → server/signaling.py / 그 외 = server/main.py (REST)
EXPOSE 8080 8765

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -fsS http://localhost:8080/healthz || exit 1

CMD ["python", "-m", "server.main"]
