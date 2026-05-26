# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk(p2p_msg) DB repositories — 테이블별 CRUD layer (server data 계층, 정본 §E).
#
# 본 디렉토리 = SQL DDL 과 1:1 mapping 되는 repository module 모음.
# 각 module 은 connection pool 을 dependency injection 으로 받아(첫 인자) raw SQL 을 캡슐화하고,
# 상위(API handler)가 SQL 을 직접 알지 못하게 격리한다. 모든 SQL 은 parameterized(injection 차단).
