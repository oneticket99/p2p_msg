# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk(p2p_msg) 서버 DB 패키지 — MariaDB asyncmy pool + repositories + migrations.
#
# 본 디렉토리 = 시그널링 서버 의 영속화 layer.
# 디렉토리 구성:
#   migrations/ — SQL DDL append-only migration set
#   connection.py — asyncmy pool wrapper + 환경변수 의 의 의 의 의 의 의 의 의 설정 의 의 의 로딩
#   repositories/ — table 별 CRUD layer (Phase 1 = users + email_verification + password_reset + rooms + peers + file_meta + messages)
