---
title: "TooTalk 영속화 DB 마이그레이션 정본 (MariaDB)"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# MIGRATION_MARIADB.md — TooTalk(p2p_msg) MariaDB 마이그레이션 정본

> 본 문서는 TooTalk(코드명 `p2p_msg`) 의 **영속화 백엔드(MariaDB) 스키마·마이그레이션 절차·환경변수·백업/복구·history** 를 한 곳에 모은 운영 문서다.
> 새 DB 모델·컬럼·인덱스가 추가되거나 변경될 때 본 문서가 `Structure.md` §11 ERD 와 함께 **동시 갱신** 되어야 한다 ([정본 §N 3](CLAUDE_HARNESS_IMPORTANT.md)).
> 정본 정합: [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) §N 3 (DB 모델 추가 시 tables 배열 FK 순서) · §E (`.env` 하드코딩 금지) · §K (루트 18 동결 — 본 문서 포함).
> 요구사항 정본: [Specification.md](Specification.md) FR-05 (메시지 영속화 MariaDB) · AC-05-1~4.
> 스키마 ERD 정본: [Structure.md §11](Structure.md).

---

## 1. 문서 목적

본 문서는 다음 4가지에 한 번에 답한다.

1. **어떤 DB 를 쓰는가** — MariaDB 10.11 LTS (사용자 directive 2026-05-17, SQLite 미사용).
2. **테이블 추가/변경 순서가 어떻게 되는가** — `tables` 배열 FK 순서 정본 (§2).
3. **DDL 본문이 어떻게 생겼는가** — 4 테이블 MariaDB 호환 InnoDB · utf8mb4 (§3·§4).
4. **마이그레이션을 어떤 도구로 실행하는가** — 후보 비교 + 결정 보류 (§5).

본 문서는 [Specification.md FR-05](Specification.md) (영속화 요구사항) 와 [Structure.md §11](Structure.md) (ERD) 의 **단일 진실 공급원**이다. 본 시점 스키마 정의 코드 (`app/db/`) 는 미생성 단계이며, 본 문서와 `Structure.md` §11 도식이 코드보다 앞선다 (M1 — Document First).

정본 §N 3 인용:

> 새 DB 모델 추가 시: `MIGRATION_MARIADB.md` tables 배열에 **FK 순서로** 삽입 + `Structure.md` ERD 갱신.

---

## 2. tables 배열 — FK 순서 정본

본 절은 정본 §N 3 의 "FK 순서로 삽입" 규약을 본 저장소 4 테이블에 구체화한 것이다. DDL 적용 순서·`DROP TABLE` 역순·테스트 fixture seed 순서가 모두 본 배열을 따른다.

```yaml
# MIGRATION_MARIADB.md — tables FK 순서 정본 (2026-05-17 시점)
tables:
  - users                # 의존 없음 (auth 루트, 사용자 directive 2026-05-17)
  - email_verification   # 의존 없음 (email 참조 — string 매칭, FK 없음)
  - password_reset       # FK: password_reset.user_id → users.id
  - rooms                # 의존 없음 (대화 루트)
  - peers                # FK: peers.room_id → rooms.id
  - file_meta            # 의존 없음 (messages.file_meta_id 가 본 테이블을 가리킴)
  - messages             # FK: messages.room_id → rooms.id
                         #     messages.sender_peer_id → peers.id
                         #     messages.file_meta_id → file_meta.id
```

### 2.1 순서 근거

| 순서 | 테이블 | 외래키 의존 |
|---|---|---|
| 1 | `users` | 없음 — auth 루트 (사용자 directive 2026-05-17 회원가입 도입) |
| 2 | `email_verification` | 없음 — email 의 string 매칭 (FK 없음) |
| 3 | `password_reset` | `user_id` → `users.id` (CASCADE) |
| 4 | `rooms` | 없음 — 대화 루트 |
| 5 | `peers` | `room_id` → `rooms.id` (CASCADE) |
| 6 | `file_meta` | 없음 — `messages` 가 본 테이블을 참조 (이미지·파일 옵션) |
| 7 | `messages` | `room_id` → `rooms.id` · `sender_peer_id` → `peers.id` · `file_meta_id` → `file_meta.id` (NULL 허용) |

### 2.2 적용 순서 규약

- **CREATE/INSERT 순서**: 위 배열 그대로 (1 → 4).
- **DROP/DELETE 순서**: 위 배열 역순 (4 → 1). FK 위배 회피.
- **테스트 fixture seed**: 위 배열 그대로. `rooms` 1행 → `peers` N행 → `file_meta` M행 → `messages` K행.
- **마이그레이션 도구 (§5)** 가 본 순서를 자동 보장할 수 있어야 한다 — Alembic 의 `op.create_table` 호출 순서, 자체 SQL 의 파일명 prefix(`001_rooms.sql` · `002_peers.sql` · `003_file_meta.sql` · `004_messages.sql`) 가 본 절에 일치.

---

## 3. DDL — 7 테이블 (MariaDB 호환 InnoDB · utf8mb4)

본 절의 DDL 은 MariaDB 10.11 LTS 호환 InnoDB · `utf8mb4_unicode_ci` 콜레이션 기준이다. [Structure.md §11](Structure.md) ERD 와 1:1 정합한다.

### 3.0 `users` (auth 루트 — 사용자 directive 2026-05-17)

```sql
CREATE TABLE users (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  email VARCHAR(254) NOT NULL UNIQUE,
  username VARCHAR(32) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  nickname VARCHAR(64) DEFAULT NULL,
  avatar_url VARCHAR(512) DEFAULT NULL,
  verified TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_users_email (email),
  INDEX idx_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3.0a `email_verification` (OTP 3분)

```sql
CREATE TABLE email_verification (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  email VARCHAR(254) NOT NULL,
  otp_code CHAR(6) NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  expires_at DATETIME NOT NULL,
  consumed_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_email_verif_email_expires (email, expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3.0b `password_reset` (UUID4 + 30분 유효)

```sql
CREATE TABLE password_reset (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  reset_token CHAR(36) NOT NULL UNIQUE,
  expires_at DATETIME NOT NULL,
  consumed_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_password_reset_user_id
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  INDEX idx_password_reset_token (reset_token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3.1 `rooms`

```sql
CREATE TABLE rooms (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  room_uuid CHAR(36) NOT NULL UNIQUE,
  name VARCHAR(128) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_rooms_uuid (room_uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3.2 `peers`

```sql
CREATE TABLE peers (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  room_id BIGINT UNSIGNED NOT NULL,
  peer_uuid CHAR(36) NOT NULL,
  nickname VARCHAR(64) NULL,
  last_seen BIGINT UNSIGNED NULL,
  CONSTRAINT fk_peers_room_id
    FOREIGN KEY (room_id) REFERENCES rooms(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  UNIQUE KEY uq_peers_room_peer (room_id, peer_uuid),
  INDEX idx_peers_last_seen (last_seen)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3.3 `file_meta`

```sql
CREATE TABLE file_meta (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  file_id CHAR(32) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  size BIGINT UNSIGNED NOT NULL,
  mime VARCHAR(128) NOT NULL,
  sha256 CHAR(64) NOT NULL,
  thumbnail_base64 MEDIUMTEXT NULL,
  received_path VARCHAR(1024) NULL,
  status ENUM('pending','transferring','done','failed') NOT NULL DEFAULT 'pending',
  INDEX idx_file_meta_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3.4 `messages`

```sql
CREATE TABLE messages (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  room_id BIGINT UNSIGNED NOT NULL,
  sender_peer_id BIGINT UNSIGNED NOT NULL,
  ts BIGINT UNSIGNED NOT NULL,
  type ENUM('text','image','file','system') NOT NULL,
  body TEXT NULL,
  msg_uuid CHAR(36) NOT NULL UNIQUE,
  file_meta_id BIGINT UNSIGNED NULL,
  acked_at BIGINT UNSIGNED NULL,
  CONSTRAINT fk_messages_room_id
    FOREIGN KEY (room_id) REFERENCES rooms(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_messages_sender_peer_id
    FOREIGN KEY (sender_peer_id) REFERENCES peers(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_messages_file_meta_id
    FOREIGN KEY (file_meta_id) REFERENCES file_meta(id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  INDEX idx_messages_room_ts (room_id, ts),
  INDEX idx_messages_file_meta (file_meta_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 3.5 확장 테이블 — 18 테이블 (마이그레이션 0002~0016)

> 본 절은 §3 핵심 7 테이블 이후 Phase 2~5 에서 추가된 18 확장 테이블의 정합 목록이다.
> **DDL + 필드 COMMENT 5요소(용도/제약/출처/참조/민감도) 정본 = `server/db/migrations/0002~0016*.sql`** 파일이며 (drift 회피 위해 본 절은 `CREATE TABLE` 시그니처 + 용도 + 정본 file 참조만 둔다).
> `tools/check_migration_tables.py --strict` 의 doc ⊇ SQL 역방향 검증 통과 기준 = 본 절의 25 테이블 전수 등재.

```sql
-- 0002_devices.sql — 사용자 멀티 디바이스 등록 + revoke/last_seen 추적
CREATE TABLE devices ( /* DDL 정본: server/db/migrations/0002_devices.sql */ );

-- 0003_user_activity.sql — 세션 추적 + 활동 로그 (마케팅 통계, IP 90일 retention)
CREATE TABLE user_sessions ( /* DDL 정본: server/db/migrations/0003_user_activity.sql */ );
CREATE TABLE user_activity_log ( /* DDL 정본: server/db/migrations/0003_user_activity.sql */ );

-- 0004_emoji_packs.sql — 이모지 팩 공개 디렉토리 + 팩 아이템 (DMCA phash)
CREATE TABLE emoji_packs ( /* DDL 정본: server/db/migrations/0004_emoji_packs.sql */ );
CREATE TABLE emoji_pack_items ( /* DDL 정본: server/db/migrations/0004_emoji_packs.sql */ );

-- 0005_bot_escalations.sql — 봇 → 사람 에스컬레이션 큐
CREATE TABLE bot_escalations ( /* DDL 정본: server/db/migrations/0005_bot_escalations.sql */ );

-- 0006_app_versions.sql — 자동 업데이트 릴리스 버전 메타 (macOS arm64 + win x64)
CREATE TABLE app_versions ( /* DDL 정본: server/db/migrations/0006_app_versions.sql */ );

-- 0007_friends.sql — 친구 관계 (accepted/pending/blocked status)
CREATE TABLE friends ( /* DDL 정본: server/db/migrations/0007_friends.sql */ );

-- 0008_message_reactions.sql — 메시지 이모지 리액션 (user × message × emoji)
CREATE TABLE message_reactions ( /* DDL 정본: server/db/migrations/0008_message_reactions.sql */ );

-- 0009_folders.sql — 채팅 폴더 + 폴더 내 chat 매핑 + 폴더 초대 링크
CREATE TABLE folders ( /* DDL 정본: server/db/migrations/0009_folders.sql */ );
CREATE TABLE folder_chats ( /* DDL 정본: server/db/migrations/0009_folders.sql */ );
CREATE TABLE folder_invites ( /* DDL 정본: server/db/migrations/0009_folders.sql */ );

-- 0012_bots.sql — 봇 등록 + 봇 API 토큰 (BotFather 등가)
CREATE TABLE bots ( /* DDL 정본: server/db/migrations/0012_bots.sql */ );
CREATE TABLE bot_tokens ( /* DDL 정본: server/db/migrations/0012_bots.sql */ );

-- 0013_device_tokens.sql — push 알림 토큰 (APNs/FCM)
CREATE TABLE device_tokens ( /* DDL 정본: server/db/migrations/0013_device_tokens.sql */ );

-- 0014_read_states.sql — 방별 읽음 상태 (last_read_message_id)
CREATE TABLE read_states ( /* DDL 정본: server/db/migrations/0014_read_states.sql */ );

-- 0015_user_contacts.sql — 사용자 연락처 (전화번호 매칭)
CREATE TABLE user_contacts ( /* DDL 정본: server/db/migrations/0015_user_contacts.sql */ );

-- 0016_streaming_oauth_tokens.sql — streaming 플랫폼 OAuth 토큰 (chzzk/kick/twitch, 최후순위)
CREATE TABLE streaming_oauth_tokens ( /* DDL 정본: server/db/migrations/0016_streaming_oauth_tokens.sql */ );
```

> 참고: 0010_user_profile_fields.sql + 0011_user_nickname_field.sql 은 `users` ALTER 마이그레이션(신규 테이블 부재)이라 본 목록 제외.

---

## 4. 인덱스·제약 정의

본 절은 §3 DDL 의 인덱스·제약을 한 표로 요약한다. [Structure.md §11.1](Structure.md) 와 1:1 정합.

| 테이블 | 인덱스/제약 | 종류 | 목적 |
|---|---|---|---|
| `rooms` | `UNIQUE(room_uuid)` | 유니크 | 시그널링 JOIN 값 충돌 방지 |
| `rooms` | `idx_rooms_uuid` | 보조 인덱스 | UUID 조회 가속 |
| `peers` | `fk_peers_room_id` | FK CASCADE | room 삭제 시 동반 정리 |
| `peers` | `uq_peers_room_peer (room_id, peer_uuid)` | 복합 유니크 | 동일 방 peer 중복 방지 |
| `peers` | `idx_peers_last_seen` | 보조 인덱스 | GC·재접속 시 last_seen 조회 |
| `file_meta` | `UNIQUE(file_id)` | 유니크 | FILE_META.file_id 충돌 차단 |
| `file_meta` | `idx_file_meta_status` | 보조 인덱스 | 진행 중·실패 파일 조회 |
| `messages` | `UNIQUE(msg_uuid)` | 유니크 | DataChannel msg_id idempotency |
| `messages` | `fk_messages_room_id` | FK CASCADE | room 삭제 시 메시지 동반 정리 |
| `messages` | `fk_messages_sender_peer_id` | FK RESTRICT | 발신자 무결성 (peer 삭제 차단) |
| `messages` | `fk_messages_file_meta_id` | FK SET NULL | 첨부 정리 시 메시지 본문 보존 |
| `messages` | `idx_messages_room_ts (room_id, ts)` | 복합 인덱스 | ChatView 시간순 조회 (AC-05-2) |
| `messages` | `idx_messages_file_meta` | 보조 인덱스 | JOIN file_meta 가속 |

### 4.1 NULL · 기본값 정책

| 컬럼 | NULL/기본값 | 정책 |
|---|---|---|
| `rooms.created_at` | `DEFAULT CURRENT_TIMESTAMP` | 생성 시점 자동 |
| `peers.nickname` | NULL 허용 | 닉네임 미설정 허용 |
| `peers.last_seen` | NULL 허용 | PEER_LEFT 시점만 채움 |
| `messages.body` | NULL 허용 | `type=text`·`system` 한정으로 채움. `image`·`file` 은 NULL |
| `messages.file_meta_id` | NULL 허용 | `type=image`·`file` 한정으로 채움 |
| `messages.acked_at` | NULL 허용 | 송신자만 ACK 수신 시점 채움 |
| `file_meta.thumbnail_base64` | NULL 허용 | `mime` 가 `image/*` 일 때만 채움 |
| `file_meta.received_path` | NULL 허용 | 수신자만 채움 (송신자 NULL) |
| `file_meta.status` | `DEFAULT 'pending'` | 전이: `pending` → `transferring` → `done`/`failed` |

---

## 5. 마이그레이션 도구 후보 비교 (결정 보류)

본 절은 마이그레이션 도구 선정을 위한 후보 3종 비교다. **본 시점 결정 보류** — Phase 1 후반 (사용자 directive 시점) 에 본 표를 갱신하여 1종으로 확정한다.

### 5.1 비교 표

| 항목 | Alembic | yoyo-migrations | 자체 SQL |
|---|---|---|---|
| 언어/실행 | Python · `alembic upgrade head` | Python · `yoyo apply` | Bash + `mysql` CLI |
| 의존성 | `alembic` + `SQLAlchemy` (FR-05 스키마 코드와 동반) | `yoyo-migrations` 단독 | 추가 의존 0 |
| revision 추적 | `alembic_version` 1행 (단일 head) | `_yoyo_log` · `_yoyo_migration` 테이블 | 본 문서 §10 history 표 수기 |
| auto-gen | `op.create_table()` 자동 비교 (SQLAlchemy 모델 → DDL) | 없음 — SQL 파일 수기 작성 | 없음 — SQL 파일 수기 작성 |
| 다운그레이드 | `downgrade()` 함수 작성 시 가능 | `rollback` 스텝 작성 시 가능 | 별도 `*_rollback.sql` 수기 |
| 본 저장소 적합도 | SQLAlchemy 사용 시 ◎ · 단독 SQL 시 △ | SQLAlchemy 미사용 시 ◎ | Phase 1 MVP 한정 ◎ · 장기 △ |
| 학습 비용 | 중 (head·branch·merge 개념) | 낮음 (파일 순서대로 apply) | 매우 낮음 |
| CI 통합 | `alembic upgrade head` + `--sql` 사전 검토 | `yoyo apply --batch` | `mysql < file.sql` |

### 5.2 결정 보류 사유

- `app/db/` 디렉터리·`app/core/storage.py` 가 아직 미생성 ([Structure.md §13](Structure.md)) — SQLAlchemy 채택 여부 자체가 미정.
- Phase 1 MVP (FR-05 영속화) 우선순위는 "테이블 4종 정상 생성·복원" 이며, 도구 선정은 Phase 1 후반·Phase 2 의 다중 머신 배포 단계에서 본격화된다.
- 본 결정은 [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) Task #16 (`db_init.py`) 의 후속으로 추적한다.

### 5.3 잠정 진행 방침 (결정 전까지)

- Phase 1 초반: `tools/db_init.py` (예정) 가 §3 DDL 4종을 **순서대로 실행** (FK 순서 그대로). 다운그레이드는 `DROP DATABASE tootalk_db; CREATE DATABASE tootalk_db;` 로 단순화 (개발 단계 한정).
- 본 문서 §10 history 표가 잠정 revision 추적기로 동작 — 도구 확정 후 자동화 도구의 revision 테이블과 정합화.

---

## 6. 마이그레이션 절차 — 변경 시점 동시 갱신 의무

본 절은 정본 §N 3 의 "DB 모델 추가 시 본 문서 + Structure.md ERD 갱신" 규약의 구체 절차다. M1(Document First) 순서를 엄수한다.

### 6.1 5단계 절차

```text
[DB 변경 요구사항 발생]
     │
     ▼
 ① 본 문서 갱신 (M1 — 코드 이전)
     ├── §2 tables 배열 FK 순서 삽입
     ├── §3 DDL 본문 추가/수정
     ├── §4 인덱스·제약 표 갱신
     └── §10 history 표 1행 prepend
     │
     ▼
 ② Structure.md §11 ERD 동시 갱신
     ├── §11 mermaid 도식 갱신
     ├── §11.1 인덱스 표 갱신
     └── §11.2 마이그레이션 정합 라인 동기화
     │
     ▼
 ③ Specification.md FR-05 정합 점검
     ├── AC-05-3 외래키 정합 위배 0건 정합
     └── 9.1 DB 환경변수 표 (변경 시) 갱신
     │
     ▼
 ④ 코드 작업 (M4 — 한글 주석 필수)
     ├── app/db/schema.py (예정) — SQLAlchemy 모델 또는 raw DDL
     └── tools/db_init.py (예정) — §2 FK 순서로 CREATE
     │
     ▼
 ⑤ README 변경 이력 prepend (M2) + 즉시 commit·push (M5)
```

### 6.2 금지 사항

- ②를 ①보다 먼저 수행 (Structure.md 만 갱신하고 본 문서를 미루는 행위).
- ④를 ①·② 보다 먼저 수행 (코드 우선 — M1 위반).
- §2 tables 배열을 FK 순서가 아닌 알파벳·생성 순으로 정렬 (정본 §N 3 위반).
- §10 history 표 prepend 누락 (history append 금지 — 항상 최신 상단).

### 6.3 단일 진실 공급원 (SSoT)

| 영역 | 정본 문서 |
|---|---|
| FK 순서 | 본 문서 §2 |
| DDL 본문 | 본 문서 §3 |
| ERD 시각화 | [Structure.md §11](Structure.md) |
| 요구사항 정합 | [Specification.md FR-05](Specification.md) |
| 환경변수 명세 | 본 문서 §7 (마스터) · Specification.md §9.1 (참조 사본) |

---

## 7. 환경변수 명세 표

본 절은 사용자 directive 2026-05-17 로 확정된 환경변수 5종의 마스터 정의다. 본 표가 SSoT 이며 [Specification.md §9.1](Specification.md) · [app/README.md §2](app/README.md) 는 본 표를 참조 인용한다.

| 키 | 기본값 | 데이터 형 | 설명 | 노출 정책 |
|---|---|---|---|---|
| `DB_HOST` | `127.0.0.1` | 문자열 | MariaDB 호스트 (IP 또는 hostname) | 평문 가능 |
| `DB_PORT` | `3306` | 정수 | MariaDB TCP 포트 | 평문 가능 |
| `DB_USER` | `tootalk` | 문자열 | MariaDB 접속 사용자 | 평문 가능 |
| `DB_PASS` | (시크릿 — `<PLACEHOLDER>`) | 문자열 | MariaDB 접속 비밀번호 | **평문 저장·로그 출력 금지**. GitHub Actions Secrets 분리. 본 문서·이슈·PR 본문에 실값 노출 금지 |
| `DB_NAME` | `tootalk_db` | 문자열 | TooTalk 전용 스키마 | 평문 가능 |

### 7.1 `.env` 예시 (실값 금지 — placeholder)

```dotenv
# TooTalk MariaDB 접속 환경변수 — 실값 금지, 본 파일은 .gitignore 대상
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=tootalk
DB_PASS=<PLACEHOLDER>
DB_NAME=tootalk_db
```

### 7.2 노출 규약

- 본 문서·`Specification.md`·`Structure.md`·README·이슈·PR 본문에 `DB_PASS` 실값을 적지 않는다 (정본 §E 의 하드코딩 금지 + 시크릿 분리).
- `.env` 는 `.gitignore` 에 포함 — 본 시점 디렉토리 트리에 미커밋이며, [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) Task #16 이전에 `.gitignore` 항목 신설.
- CI/GitHub Actions: `secrets.DB_PASS` 로 주입. PR fork 환경에서 접근 차단.
- 빌드 산출물(zip) 안에 `.env` 미포함 ([Specification.md AC-08-3](Specification.md)).

---

## 8. 로컬 개발 인프라 — docker compose MariaDB

본 절은 Phase 1 후반에 도입 예정인 로컬 개발 인프라 후보다. **본 시점 결정 보류** — Phase 1 초반은 호스트 머신의 brew·apt 설치 MariaDB 를 가정한다.

### 8.1 docker compose 후보 (Phase 1 후반)

```yaml
# docker-compose.yml (예정 — Phase 1 후반)
version: "3.9"
services:
  mariadb:
    image: mariadb:10.11
    container_name: tootalk-mariadb
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: <PLACEHOLDER>
      MYSQL_DATABASE: tootalk_db
      MYSQL_USER: tootalk
      MYSQL_PASSWORD: <PLACEHOLDER>
    ports:
      - "3306:3306"
    volumes:
      - tootalk_db_data:/var/lib/mysql
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci

volumes:
  tootalk_db_data:
```

### 8.2 도입 판단 기준

| 시점 | 권장 | 사유 |
|---|---|---|
| Phase 1 초반 (FR-05 구현 진입 직전) | 호스트 brew/apt MariaDB | 단일 개발자·단일 머신·외부 의존 최소 |
| Phase 1 후반 (멀티 머신 검증 시작) | docker compose | 버전 일관성·삭제·재생성 용이 |
| Phase 2 (다중 머신 배포) | 호스트 패키지 또는 RDS 호환 | 운영 부담·백업 자동화 |

### 8.3 검증 명령 (도커 도입 후)

```bash
# 컨테이너 기동 + 환경변수 주입
docker compose up -d mariadb

# 접속 헬스체크 (placeholder 에 실값 주입)
mysql -h 127.0.0.1 -P 3306 -u tootalk -p"$DB_PASS" -e "SHOW DATABASES;"

# §3 DDL 4종 적용 (FK 순서 그대로)
mysql -h 127.0.0.1 -P 3306 -u tootalk -p"$DB_PASS" tootalk_db < migrations/001_rooms.sql
mysql -h 127.0.0.1 -P 3306 -u tootalk -p"$DB_PASS" tootalk_db < migrations/002_peers.sql
mysql -h 127.0.0.1 -P 3306 -u tootalk -p"$DB_PASS" tootalk_db < migrations/003_file_meta.sql
mysql -h 127.0.0.1 -P 3306 -u tootalk -p"$DB_PASS" tootalk_db < migrations/004_messages.sql
```

---

## 9. 백업·복구 — Phase 2 의 mysqldump 후크

본 절은 백업·복구 정책의 골격이다. **Phase 1 단계 백업은 수동** (개발자 책임), **Phase 2 단계 자동화 후크** 를 명문화한다.

### 9.1 Phase 1 — 수동 백업

```bash
# 전체 스키마 + 데이터 백업
mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" \
  --single-transaction \
  --routines \
  --triggers \
  --default-character-set=utf8mb4 \
  "$DB_NAME" > "backup-$(date +%Y%m%d-%H%M%S).sql"
```

### 9.2 Phase 2 — `mysqldump` 후크 (정책 명시)

| 후크 | 트리거 | 동작 | 보존 |
|---|---|---|---|
| `pre-migration` | 본 문서 §10 history 표 신규 row prepend 직전 | 자동 dump → `backups/pre-migration-<rev>-<ts>.sql` | 90일 |
| `daily-backup` | 매일 03:00 cron | 자동 dump → `backups/daily-<YYYYMMDD>.sql.gz` | 30일 |
| `pre-cutover` | Phase 2 단계 다중 머신 배포 cutover 직전 | 자동 dump + 체크섬 → 오프사이트 복제 | 영구 |

### 9.3 복구 절차

```bash
# 1) 신규 빈 스키마 생성
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" \
  -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2) 백업 파일 복원
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" \
  --default-character-set=utf8mb4 \
  "$DB_NAME" < backup-YYYYMMDD-HHMMSS.sql

# 3) 정합 검증
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" \
  -e "SELECT COUNT(*) FROM rooms; SELECT COUNT(*) FROM peers; SELECT COUNT(*) FROM file_meta; SELECT COUNT(*) FROM messages;"
```

### 9.4 금지

- `mysqldump` 실행 산출물(`.sql`·`.sql.gz`) 의 git 커밋 — `.gitignore` `backups/` 포함 의무.
- 백업 파일 본문에 평문 `DB_PASS` 노출 — 백업 명령은 `--password=` 대신 `-p"$DB_PASS"` 환경변수 인용 형태로만 작성.
- Phase 2 자동화 도입 이전의 정기 백업 의존 — Phase 1 단계의 데이터 손실은 개발 단계 비용으로 수용.

---

## 10. 마이그레이션 history 표 (예정 항목)

본 표는 §6 절차의 결과 — 모든 스키마 변경의 정본 history 다. **prepend 전용** (최신이 상단, History.md M3 규약과 동일 패턴).

| revision | 일시 | 변경 요약 | 영향 테이블 | 적용 도구 | 작성자 | 검증 |
|---|---|---|---|---|---|---|
| (예정 — 첫 신규 row 는 도구 확정 직후 prepend) | | | | | | |

### 10.1 row 형식 규약

- `revision`: 자체 SQL 도구 채택 시 `001`·`002`... 형식, Alembic 채택 시 hash (예: `a1b2c3d4`).
- `일시`: `YYYY-mm-dd HH:MM` (정본 §I 로그 형식과 정합).
- `변경 요약`: 1행 — 추가/수정/삭제 + 대상 테이블·컬럼.
- `영향 테이블`: §2 tables 배열의 부분집합.
- `적용 도구`: `Alembic` · `yoyo` · `mysql CLI` 중 §5 확정값.
- `작성자`: GitHub handle (예: `oneticket99`).
- `검증`: `Structure.md §11 ERD 동시 갱신 ✓` · `Specification.md FR-05 정합 ✓` 체크 마커.

### 10.2 prepend 의무

- 본 표의 신규 row 는 항상 헤더 직하단에 prepend (최신이 위).
- append 금지 — M3(History.md 역순) 규약을 본 표에 동일 적용.
- 행 수 상한 없음 (History.md 와 달리 마이그레이션 전수 보존).

### 10.3 도구 자동화 정합

§5 마이그레이션 도구 확정 후 본 표는 다음과 같이 동기화된다.

- **Alembic 채택 시**: `alembic_version` 1행 ↔ 본 표 최상단 1행 정합. `alembic history` 출력의 revision 그래프 와 본 표 1:1 매핑.
- **yoyo 채택 시**: `_yoyo_log` 테이블 ↔ 본 표 정합. 본 표가 사람 가독 정본·`_yoyo_log` 가 도구 정본.
- **자체 SQL 채택 시**: 본 표가 단일 정본. `tools/db_init.py` 의 적용 로그를 본 표에 수기 prepend.

---

## 11. 참조

### 11.1 정본·맵

- [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) §N 3 — 새 DB 모델 추가 시 본 문서 tables 배열 FK 순서 + Structure.md ERD 동시 갱신.
- [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) §E — `.env` / DB 상수 테이블 (하드코딩 금지).
- [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) §K — 루트 18 동결 (본 문서 포함).
- [AGENTS.md](AGENTS.md) — 저장소 전체 지도.

### 11.2 정합 운영 문서

- [Specification.md](Specification.md) FR-05 (영속화) · AC-05-1~4 · §9.1 DB 환경변수.
- [Structure.md](Structure.md) §11 ERD · §11.1 인덱스 정책 · §11.2 마이그레이션 정합.
- [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) Task #16 (`db_init.py`).

### 11.3 외부 참조

- MariaDB 10.11 LTS 공식 문서 — `https://mariadb.com/kb/en/mariadb-1011/`
- Alembic 공식 문서 — `https://alembic.sqlalchemy.org/`
- yoyo-migrations 공식 문서 — `https://ollycope.com/software/yoyo/`
- MariaDB `utf8mb4` 콜레이션 가이드 — `https://mariadb.com/kb/en/supported-character-sets-and-collations/`
