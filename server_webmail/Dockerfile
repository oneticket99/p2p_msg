# SPDX-License-Identifier: GPL-3.0-or-later
# webmail backend Dockerfile — cycle 169.859 M3 skeleton
# 한글 주석: python:3.13-slim base — server/ 정합

FROM python:3.13-slim

WORKDIR /app

# 한글 주석: dependency 먼저 설치 — Docker layer cache 활용
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 한글 주석: 패키지 source — server_webmail/ 전수 복사
COPY . /app/server_webmail
ENV PYTHONPATH=/app

EXPOSE 8090

# 한글 주석: aiohttp web.run_app 직접 사용 (uvicorn 부재)
CMD ["python", "-m", "server_webmail.main"]
