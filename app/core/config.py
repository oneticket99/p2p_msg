"""환경변수 로딩 + ``Config`` dataclass.

정본 §E 규약: 설정값은 ``.env`` 또는 DB 상수 테이블로만 관리 (하드코딩
금지). 본 모듈은 저장소 루트의 ``.env`` 파일을 ``python-dotenv`` 로
로딩한 뒤 ``os.environ`` 에서 값을 읽어 ``Config`` dataclass 에 채워
반환한다.

무효 값(빈 문자열, 잘못된 정수) 은 안전한 기본값으로 폴백한다 — 디스플레이용
``.env.example`` 의 명세를 기본값으로 채택.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Final

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 의존성 미설치 환경 폴백
    def load_dotenv(*_args, **_kwargs) -> bool:  # type: ignore[no-redef]
        """``python-dotenv`` 미설치 환경 폴백 — ``.env`` 무시하고 진행."""

        return False


log = logging.getLogger(__name__)


# 기본값 — ``.env.example`` 과 일치
_DEFAULT_SIGNAL_HOST: Final[str] = "114.207.112.73"
_DEFAULT_SIGNAL_PORT: Final[int] = 8765
_DEFAULT_SIGNAL_SCHEME: Final[str] = "ws"
_DEFAULT_STUN_URL: Final[str] = "stun:stun.l.google.com:19302"
_DEFAULT_USER_NICKNAME: Final[str] = "guest"
_DEFAULT_LOG_LEVEL: Final[str] = "INFO"
# MariaDB 영속화 DB (사용자 directive 2026-05-17 — SQLite 회수)
_DEFAULT_DB_HOST: Final[str] = "127.0.0.1"
_DEFAULT_DB_PORT: Final[int] = 3306
_DEFAULT_DB_USER: Final[str] = "tootalk"
_DEFAULT_DB_PASS: Final[str] = ""
_DEFAULT_DB_NAME: Final[str] = "tootalk"
_DEFAULT_MEDIA_CACHE_DIR: Final[str] = "./media_cache"


@dataclass(frozen=True, slots=True)
class Config:
    """애플리케이션 환경 설정 스냅샷.

    Attributes
    ----------
    signal_host, signal_port, signal_scheme : str/int/str
        시그널링 서버 접속 정보. ``signaling_url`` 프로퍼티로 합성 URL 노출.
    stun_url : str
        WebRTC ICE 수집용 STUN 서버 URL.
    turn_url, turn_username, turn_credential : str
        선택. 비어 있으면 TURN 사용 안 함.
    user_nickname : str
        클라이언트 표시명 — Phase 1 데모용. 정식 인증은 추후 키 페어로 대체.
    log_level : str
        ``DEBUG`` / ``INFO`` / ``WARNING`` / ``ERROR`` / ``CRITICAL``.
    db_host, db_port, db_user, db_pass, db_name : str/int/str/str/str
        MariaDB 영속화 DB 접속 정보 (사용자 directive 2026-05-17).
        ``asyncmy`` 드라이버 경유 접속. ``db_dsn`` 프로퍼티로 합성 DSN 노출.
    media_cache_dir : str
        이미지/파일 캐시 디렉토리.
    """

    signal_host: str
    signal_port: int
    signal_scheme: str
    stun_url: str
    turn_url: str
    turn_username: str
    turn_credential: str
    user_nickname: str
    log_level: str
    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_name: str
    media_cache_dir: str

    @property
    def signaling_url(self) -> str:
        """``ws://host:port/ws`` 형태의 시그널링 WebSocket URL."""

        return f"{self.signal_scheme}://{self.signal_host}:{self.signal_port}/ws"

    @property
    def db_dsn(self) -> str:
        """``mysql://user:pass@host:port/name`` 형태의 MariaDB DSN.

        ``asyncmy.connect`` 또는 SQLAlchemy 의 사용. 비밀번호 빈 값은 ``:``
        생략하지 않고 그대로 노출 — DB 접속 라이브러리가 해석.
        """

        return (
            f"mysql://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


# ---------------------------------------------------------------------------
# 환경변수 → Config 변환 헬퍼
# ---------------------------------------------------------------------------


def _env_str(key: str, default: str) -> str:
    """``os.environ`` 에서 문자열 값을 읽되 빈 문자열은 default 로 폴백."""

    raw = os.environ.get(key, "")
    if raw is None or raw.strip() == "":
        return default
    return raw.strip()


def _env_int(key: str, default: int) -> int:
    """``os.environ`` 에서 정수 값을 읽되 변환 실패 시 default 로 폴백."""

    raw = os.environ.get(key, "")
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        log.warning(
            "환경변수 %s 정수 변환 실패 — raw=%r → 기본값 %d 사용",
            key,
            raw,
            default,
        )
        return default


def _normalize_scheme(raw: str) -> str:
    """``ws`` / ``wss`` 외 값은 ``ws`` 로 폴백 (정본 시그널링 서버 README §2)."""

    lowered = raw.lower()
    if lowered in {"ws", "wss"}:
        return lowered
    log.warning("SIGNAL_SERVER_WS_SCHEME=%r 무효 — 'ws' 로 폴백", raw)
    return "ws"


def _normalize_log_level(raw: str) -> str:
    """허용된 로그 레벨이 아니면 ``INFO`` 로 폴백."""

    upper = raw.upper()
    if upper in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        return upper
    log.warning("LOG_LEVEL=%r 무효 — 'INFO' 로 폴백", raw)
    return "INFO"


# ---------------------------------------------------------------------------
# public — load_config
# ---------------------------------------------------------------------------


def load_config(dotenv_path: str | None = None) -> Config:
    """``.env`` 를 로딩하여 ``Config`` 인스턴스를 반환.

    Parameters
    ----------
    dotenv_path : str | None
        명시적 ``.env`` 경로. None 이면 ``python-dotenv`` 기본 탐색
        (현재 디렉토리부터 상위로 탐색).

    Returns
    -------
    Config
        모든 필드가 채워진 frozen dataclass.
    """

    load_dotenv(dotenv_path=dotenv_path, override=False)

    config = Config(
        signal_host=_env_str("SIGNAL_SERVER_HOST", _DEFAULT_SIGNAL_HOST),
        signal_port=_env_int("SIGNAL_SERVER_WS_PORT", _DEFAULT_SIGNAL_PORT),
        signal_scheme=_normalize_scheme(
            _env_str("SIGNAL_SERVER_WS_SCHEME", _DEFAULT_SIGNAL_SCHEME)
        ),
        stun_url=_env_str("STUN_URL", _DEFAULT_STUN_URL),
        turn_url=_env_str("TURN_URL", ""),
        turn_username=_env_str("TURN_USERNAME", ""),
        turn_credential=_env_str("TURN_CREDENTIAL", ""),
        user_nickname=_env_str("USER_NICKNAME", _DEFAULT_USER_NICKNAME),
        log_level=_normalize_log_level(_env_str("LOG_LEVEL", _DEFAULT_LOG_LEVEL)),
        db_host=_env_str("DB_HOST", _DEFAULT_DB_HOST),
        db_port=_env_int("DB_PORT", _DEFAULT_DB_PORT),
        db_user=_env_str("DB_USER", _DEFAULT_DB_USER),
        db_pass=_env_str("DB_PASS", _DEFAULT_DB_PASS),
        db_name=_env_str("DB_NAME", _DEFAULT_DB_NAME),
        media_cache_dir=_env_str("MEDIA_CACHE_DIR", _DEFAULT_MEDIA_CACHE_DIR),
    )

    log.debug(
        "Config 로딩 완료 — signaling=%s stun=%s nickname=%s",
        config.signaling_url,
        config.stun_url,
        config.user_nickname,
    )
    return config
