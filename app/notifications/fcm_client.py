# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 103~104 — Firebase Cloud Messaging client.

push.py 의 PushPayload → FCM Messaging API v1 send 의 실 binding.
firebase-admin SDK 미설치 환경 의 graceful fallback (is_available False
+ send 시 RuntimeError) — Phase 3 LLM provider 패턴 정합.

설계 결정
---------
- import firebase_admin 의 try/except — 미설치 환경 에서도 module import 의 무
  실패 보장. `_FIREBASE_AVAILABLE` 모듈 상수 의 True/False 분기.
- service-account.json 의 path = `FCM_CREDENTIAL_PATH` env 또는 caller 의 명시
  주입. Docker secret mount (`/run/secrets/fcm_service_account.json`)
  정합.
- send_silent_data + send_visible 의 2 API — push.py 의 format_*_payload
  결과 의 직접 forward.
- batch send — 의 별개 cycle (FCM 의 sendEachForMulticast 의 500 개 cap).

보안 의무
---------
- service-account.json = `secrets` 디렉토리 + chmod 600 + git ignore 의무.
- E2EE 정합 — payload 안 의 메시지 본문 절대 금지. silent = envelope_id
  wake-up signal 만. visible = generic alias + "새 메시지 1개" 만.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

from .push import Platform, PushPayload

log = logging.getLogger(__name__)


# firebase-admin SDK 의 import 시도 — graceful fallback
try:
    import firebase_admin  # type: ignore[import-untyped]
    from firebase_admin import credentials  # type: ignore[import-untyped]
    from firebase_admin import messaging  # type: ignore[import-untyped]

    _FIREBASE_AVAILABLE = True
except ImportError:
    _FIREBASE_AVAILABLE = False
    firebase_admin = None  # type: ignore[assignment]
    credentials = None  # type: ignore[assignment]
    messaging = None  # type: ignore[assignment]


_DEFAULT_CRED_ENV = "FCM_CREDENTIAL_PATH"
_DEFAULT_PROJECT_ID_ENV = "FCM_PROJECT_ID"


class FCMError(Exception):
    """FCM 호출 base 예외."""


class FCMUnavailableError(FCMError):
    """firebase-admin SDK 미설치 또는 인증 실패."""


class FCMInvalidTargetError(FCMError):
    """payload.target 의 platform != FCM 또는 push_token 부재."""


@dataclass
class FCMClient:
    """Firebase Cloud Messaging API v1 client wrapper.

    Parameters
    ----------
    credential_path : Optional[str]
        service-account.json 의 절대 경로. None 시 `FCM_CREDENTIAL_PATH`
        env 의 값 사용 (Docker secret mount default).
    project_id : Optional[str]
        Firebase 프로젝트 ID. None 시 `FCM_PROJECT_ID` env 사용.
    app_name : str
        firebase_admin app 식별자 (multi-tenant 회피 의 default "tootalk").
    """

    credential_path: Optional[str] = None
    project_id: Optional[str] = None
    app_name: str = "tootalk"

    def __post_init__(self) -> None:
        self._app: Optional[object] = None  # firebase_admin.App
        self._initialized: bool = False

    @classmethod
    def is_available(cls) -> bool:
        """firebase-admin SDK import 가용 여부."""

        return _FIREBASE_AVAILABLE

    def initialize(self) -> None:
        """firebase_admin app 의 lazy init.

        Raises
        ------
        FCMUnavailableError
            firebase-admin 미설치 또는 service-account.json 부재.
        """

        if not _FIREBASE_AVAILABLE:
            raise FCMUnavailableError(
                "firebase-admin SDK 미설치 — pip install firebase-admin>=7.0"
            )
        if self._initialized:
            return
        cred_path = self.credential_path or os.environ.get(_DEFAULT_CRED_ENV)
        if not cred_path:
            raise FCMUnavailableError(
                f"service-account.json 경로 부재 — {_DEFAULT_CRED_ENV} env 또는 "
                "credential_path 명시 주입 의무"
            )
        if not os.path.isfile(cred_path):
            raise FCMUnavailableError(f"service-account.json 부재 — {cred_path}")
        project_id = self.project_id or os.environ.get(_DEFAULT_PROJECT_ID_ENV)
        try:
            cred = credentials.Certificate(cred_path)
            options: Dict[str, str] = {}
            if project_id:
                options["projectId"] = project_id
            # 한글 주석: 이미 init 된 app 이 있으면 get_app, 부재 시 initialize_app
            try:
                self._app = firebase_admin.get_app(self.app_name)
            except ValueError:
                self._app = firebase_admin.initialize_app(
                    cred, options or None, name=self.app_name
                )
            self._initialized = True
            log.info(
                "FCM client init PASS — app=%s project_id=%s",
                self.app_name,
                project_id or "(SDK default)",
            )
        except Exception as e:
            raise FCMUnavailableError(f"firebase-admin init 실패 — {e}") from e

    def send(self, payload: PushPayload) -> str:
        """단일 push 전송 — FCM Messaging API v1 send.

        Parameters
        ----------
        payload : PushPayload
            push.py 의 format_silent_data_payload / format_visible_payload 산출.

        Returns
        -------
        str
            FCM message_id (성공 시).

        Raises
        ------
        FCMUnavailableError
            SDK 미설치 또는 init 실패.
        FCMInvalidTargetError
            target.platform != FCM 또는 push_token 부재.
        FCMError
            FCM 호출 실패 (network + auth + quota 등).
        """

        if payload.target.platform != Platform.FCM:
            raise FCMInvalidTargetError(
                f"FCM platform 의무 — 실 = {payload.target.platform.value}"
            )
        if not payload.target.push_token:
            raise FCMInvalidTargetError("FCM push_token 부재")
        if not self._initialized:
            self.initialize()

        message = messaging.Message(
            token=payload.target.push_token,
            data=payload.data or None,
            notification=(
                messaging.Notification(title=payload.title, body=payload.body)
                if payload.title or payload.body
                else None
            ),
            android=messaging.AndroidConfig(
                priority="high",
                collapse_key=payload.collapse_key,
            ),
        )
        try:
            message_id = messaging.send(message, app=self._app)
            log.info(
                "FCM send PASS — message_id=%s collapse=%s data_keys=%s",
                message_id,
                payload.collapse_key,
                list((payload.data or {}).keys()),
            )
            return message_id
        except Exception as e:
            log.error("FCM send FAIL — %s", e)
            raise FCMError(f"FCM send 실패 — {e}") from e


def from_env() -> FCMClient:
    """환경 변수 기반 FCMClient factory.

    `FCM_CREDENTIAL_PATH` + `FCM_PROJECT_ID` env 사용. 미설정 시 initialize
    호출 시점 의 FCMUnavailableError.
    """

    return FCMClient(
        credential_path=os.environ.get(_DEFAULT_CRED_ENV),
        project_id=os.environ.get(_DEFAULT_PROJECT_ID_ENV),
    )
