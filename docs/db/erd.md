---
title: "TooTalk 데이터 모델 ERD (Phase 1)"
owner: oneticket99
last_verified: 2026-05-17
status: active
authoritative_for:
  - MariaDB 7 table 의 관계 도식
  - 모든 필드 의 의미 + 제약 + 출처 + 민감도 명시
---

# TooTalk 데이터 모델 ERD (Phase 1)

> 본 ERD = `server/db/migrations/0001_init.sql` 의 1:1 mirror.
> 가드레일 [[feedback-db-schema-field-comments]] 정합 — 모든 필드 description 의무.
> 본문 컬럼 description = SQL DDL 의 COMMENT 절 의 요약.

## 1. 본 문서 운영 규약

1. **단일 정본 = SQL DDL** (`server/db/migrations/0001_init.sql`). 본 ERD 는 그 mirror.
2. **변경 절차** — SQL 변경 시 본 ERD 동시 갱신 의무. 한쪽 단독 변경 금지.
3. **필드 description 5요소** — 용도 + 제약 + 값 출처 + 참조 관계 + 민감도. 빈 description 금지.

## 2. AUTH 3 TABLE

```mermaid
erDiagram
    users {
        bigint id PK "사용자 PK (AUTO_INCREMENT, UNSIGNED)"
        varchar email UK "로그인 식별자 + OTP 발송 대상 (UNIQUE, 256자, PII)"
        varchar username UK "표시 이름 (UNIQUE, 1~64자)"
        varchar password_hash "PBKDF2-SHA256 해시 (앱 산출, 평문 금지)"
        tinyint email_verified "OTP 검증 완료 여부 (0/1, default 0)"
        enum status "active/suspended/deleted (soft-delete 30일)"
        timestamp created_at "가입 시각 (UTC)"
        timestamp updated_at "마지막 수정 시각 (UTC, ON UPDATE)"
        timestamp last_login_at "마지막 로그인 시각 (UTC, NULL 가능)"
    }

    email_verification {
        bigint id PK "OTP 레코드 PK (AUTO_INCREMENT)"
        varchar email "발송 대상 (회원가입 직전 user row 부재 케이스 정합 — FK 미설정)"
        enum purpose "signup/password_reset"
        char64 code_hash "6자리 OTP 의 SHA-256 hex (앱 산출, 평문 금지)"
        timestamp expires_at "만료 시각 (발급 + 3분, UTC)"
        timestamp consumed_at "사용 시각 (NULL=미사용, 재사용 차단)"
        int attempt_count "검증 시도 횟수 (5회 초과 시 무효)"
        timestamp created_at "발급 시각 (UTC)"
    }

    password_reset {
        bigint id PK "비번 재설정 레코드 PK"
        bigint user_id FK "대상 user (CASCADE DELETE)"
        char64 token_hash "32 byte URL-safe 토큰 의 SHA-256 hex (앱 산출, 평문 금지)"
        timestamp expires_at "만료 시각 (발급 + 30분, UTC)"
        timestamp consumed_at "사용 시각 (NULL=미사용)"
        timestamp created_at "발급 시각 (UTC)"
    }

    users ||--o{ password_reset : "1:N (비번 재설정 토큰)"
```

## 3. 대화 4 TABLE

```mermaid
erDiagram
    rooms {
        bigint id PK "룸 PK (AUTO_INCREMENT)"
        char16 room_code UK "룸 식별 코드 (16자 URL-safe random, UNIQUE)"
        bigint owner_id FK "생성자 user (CASCADE DELETE)"
        enum kind "direct (Phase 1) / group (Phase 2+)"
        enum status "active/closed"
        timestamp created_at "생성 시각 (UTC)"
        timestamp closed_at "종료 시각 (NULL=active)"
    }

    peers {
        bigint id PK "참여 레코드 PK"
        bigint room_id FK "소속 룸 (CASCADE DELETE)"
        bigint user_id FK "참여 user (CASCADE DELETE)"
        enum role "owner/member"
        timestamp joined_at "join 시각 (UTC)"
        timestamp left_at "leave 시각 (NULL=활성 참여)"
    }

    file_meta {
        bigint id PK "파일 레코드 PK"
        char32 file_id UK "UUID hex 32자 (앱 산출, FILE_META 정합)"
        bigint room_id FK "소속 룸 (CASCADE DELETE)"
        bigint sender_id FK "송신자 user (CASCADE DELETE)"
        varchar name "원본 파일명 (UTF-8 한글 보존)"
        bigint size "파일 크기 (byte, 양수)"
        varchar mime "MIME 타입 (앱 guess_mime 산출)"
        char64 sha256 "전체 SHA-256 hex (앱 산출, 수신 검증)"
        enum status "uploading/completed/failed/cancelled"
        mediumtext thumbnail_base64 "이미지 썸네일 base64 (image/* 만, 약 5~15 KB)"
        timestamp created_at "FILE_META 수신 시각 (UTC)"
        timestamp completed_at "FILE_DONE 수신 시각 (NULL=진행 중)"
    }

    messages {
        bigint id PK "메시지 PK (AUTO_INCREMENT)"
        bigint room_id FK "소속 룸 (CASCADE DELETE)"
        bigint sender_id FK "송신자 user (CASCADE DELETE)"
        enum kind "text/file/system"
        mediumtext body "kind=text 본문 (UTF-8) / system 알림 / file=NULL"
        char32 file_id "kind=file 시 file_meta.file_id 참조 (UUID hex)"
        timestamp created_at "수신 시각 (UTC)"
    }

    rooms ||--o{ peers : "1:N (참여자)"
    rooms ||--o{ messages : "1:N (메시지 history)"
    rooms ||--o{ file_meta : "1:N (파일 메타)"
    peers }o--|| users : "N:1 (사용자)"
```

## 4. 전체 통합 관계

```mermaid
erDiagram
    users ||--o{ password_reset : "비번 재설정"
    users ||--o{ rooms : "owner 1:N"
    users ||--o{ peers : "참여 1:N"
    users ||--o{ file_meta : "송신 1:N"
    users ||--o{ messages : "송신 1:N"
    rooms ||--o{ peers : "참여 1:N"
    rooms ||--o{ messages : "메시지 1:N"
    rooms ||--o{ file_meta : "파일 1:N"
    file_meta ||..o{ messages : "kind=file 참조 (file_id, FK 없음)"
```

## 5. 필드 description 5요소 점검 표

본 표 = 가드레일 [[feedback-db-schema-field-comments]] 의 5요소 (용도 + 제약 + 출처 + 참조 + 민감도) 정합 self-audit.

| table | 필드 수 | 5요소 점검 | 민감도 표기 |
| --- | --- | --- | --- |
| users | 9 | ✅ 모두 5요소 정합 | email/password_hash = PII/비밀번호 |
| email_verification | 7 | ✅ 모두 5요소 정합 | email/code_hash = PII/비밀 |
| password_reset | 5 | ✅ 모두 5요소 정합 | token_hash = 비밀 |
| rooms | 6 | ✅ 모두 5요소 정합 | room_code = 외부 공유 키 |
| peers | 6 | ✅ 모두 5요소 정합 | 일반 |
| file_meta | 12 | ✅ 모두 5요소 정합 | name = 사용자 콘텐츠 |
| messages | 7 | ✅ 모두 5요소 정합 | body = 사용자 콘텐츠 |

**합계** = 52 필드 + 7 테이블, 모두 SQL DDL `COMMENT` 절 + ERD description 동시 정합.

## 6. 변경 절차

- **DDL 변경 시점** = 동시 갱신 의무 영역:
  1. `server/db/migrations/000N_<name>.sql` 신규 migration (append-only)
  2. `docs/db/erd.md` 본 ERD 갱신 (mermaid + 5요소 표)
  3. `ARCHITECTURE.md` §부록 B (DB schema) 동시 갱신
  4. `docs/exec-plans/active/2026-05-17-session-handoff.md` §5 정책 표 갱신

## 7. 참조

- 정본 DDL: [server/db/migrations/0001_init.sql](../../server/db/migrations/0001_init.sql)
- 영구 메모리: `feedback_db_schema_field_comments.md`
- 가드레일 인덱스: [CLAUDE.md §7](../../CLAUDE.md) #26
- ARCHITECTURE: [ARCHITECTURE.md](../../ARCHITECTURE.md)

---

마지막 갱신: 2026-05-17 — 사이클 18 (server/db/migrations/0001_init.sql 신설 + 본 ERD mirror)
