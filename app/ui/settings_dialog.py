# SPDX-License-Identifier: GPL-3.0-or-later
"""설정 다이얼로그 — 사용자 환경 control 통합 UI.

Phase 2 사이클 40 진입 — 사이클 38~39 의 signature sound layer follow-up.
음소거 toggle + 볼륨 slider 0~100 → ``SoundPlayer.set_enabled`` /
``set_volume`` 즉시 반영. 추후 Phase 2~3 의 다른 설정 (테마 / 알림 /
백업 주기) 의 동일 dialog 의 section 으로 누적 의무.

설계 결정
---------
- ``SettingsState`` dataclass 분리 = GUI 부재 환경 의 logic 검증 가능
  (Mock player 주입 + helper 함수 의 unit test).
- 볼륨 UI = 0~100 정수 slider (Qt 표준), logic 의 0.0~1.0 float 변환은
  helper ``percent_to_volume`` / ``volume_to_percent`` 의 분리.
- ``apply_to_player`` = SettingsState → SoundPlayer 매핑 의무. dialog
  accept() 시 1회 호출 + 즉시 player 상태 반영.
- 영속 저장 = Phase 3 의 user_settings table 의 의무 (본 cycle 의 의무
  외 — env-only 폴백, dialog close 시 메모리 상태만 유지).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QLabel,
        QSlider,
        QVBoxLayout,
        QWidget,
    )
    from PyQt6.QtCore import QCoreApplication, Qt
    _QT_AVAILABLE = True
except ImportError:  # pragma: no cover - PyQt6 미설치 환경 폴백
    QCheckBox = None  # type: ignore[assignment, misc]
    QDialog = object  # type: ignore[assignment, misc]
    QDialogButtonBox = None  # type: ignore[assignment, misc]
    QFormLayout = None  # type: ignore[assignment, misc]
    QLabel = None  # type: ignore[assignment, misc]
    QSlider = None  # type: ignore[assignment, misc]
    QVBoxLayout = None  # type: ignore[assignment, misc]
    QWidget = None  # type: ignore[assignment, misc]
    Qt = None  # type: ignore[assignment, misc]
    QCoreApplication = None  # type: ignore[assignment, misc]
    _QT_AVAILABLE = False


# 한글 주석 — cycle 144 i18n production binding helper. PyQt6 부재 환경 의
# graceful fallback (raw source 반환).
def _tr(src: str) -> str:
    """MainWindow context 의 QCoreApplication.translate wrap."""

    if QCoreApplication is None:
        return src
    return QCoreApplication.translate("MainWindow", src)

from app.ui.sound_player import SoundPlayer, _clamp_volume

log = logging.getLogger(__name__)


@dataclass
class SettingsState:
    """다이얼로그 의 사용자 입력 스냅샷.

    Attributes
    ----------
    sound_enabled : bool
        시그니처 사운드 활성 여부.
    sound_volume : float
        0.0~1.0 범위. 본 dataclass 의무 단 GUI 의 0~100 integer 의
        ``percent_to_volume`` 변환 후 보관.
    """

    sound_enabled: bool
    sound_volume: float

    def __post_init__(self) -> None:
        """볼륨 범위 clamp — 외부 dirty input 방어."""

        self.sound_volume = _clamp_volume(self.sound_volume)


def percent_to_volume(percent: int) -> float:
    """0~100 정수 percent → 0.0~1.0 float 변환 + clamp.

    Parameters
    ----------
    percent : int
        slider 위젯 출력 정수 (0~100). 범위 외 = clamp.

    Returns
    -------
    float
        0.0~1.0 범위 float.
    """

    if percent < 0:
        return 0.0
    if percent > 100:
        return 1.0
    return percent / 100.0


def volume_to_percent(volume: float) -> int:
    """0.0~1.0 float → 0~100 정수 percent 변환 + clamp + round.

    Parameters
    ----------
    volume : float
        0.0~1.0 범위 float.

    Returns
    -------
    int
        반올림된 0~100 정수.
    """

    clamped = _clamp_volume(volume)
    return round(clamped * 100)


def apply_to_player(state: SettingsState, player: Optional[SoundPlayer]) -> bool:
    """``SettingsState`` 의 값을 ``SoundPlayer`` 에 적용.

    Parameters
    ----------
    state : SettingsState
        다이얼로그 의 의 입력 스냅샷.
    player : SoundPlayer | None
        반영 대상. None = no-op (graceful 폴백).

    Returns
    -------
    bool
        실 반영 = True, player 부재 = False.
    """

    if player is None:
        log.debug("SoundPlayer 부재 — apply_to_player skip")
        return False
    player.set_enabled(state.sound_enabled)
    player.set_volume(state.sound_volume)
    return True


def build_state_from_player(player: Optional[SoundPlayer]) -> SettingsState:
    """``SoundPlayer`` 현재 상태 → ``SettingsState`` 초기값.

    player None = 기본값 (enabled=True, volume=0.7) 폴백.
    """

    if player is None:
        return SettingsState(sound_enabled=True, sound_volume=0.7)
    return SettingsState(
        sound_enabled=player.enabled,
        sound_volume=player.volume,
    )


class SettingsDialog(QDialog):  # type: ignore[misc, valid-type]
    """사용자 설정 다이얼로그 (PyQt6 GUI).

    Phase 2 사이클 40 = sound section 만 노출. 추후 cycle 의 테마/알림/
    백업 등 section 의 누적 의무.

    초기값 = ``build_state_from_player`` 로 ``SoundPlayer`` 현재 상태 반영.
    accept() = ``apply_to_player`` 호출 + dialog close.
    """

    def __init__(
        self,
        sound_player: Optional[SoundPlayer] = None,
        parent: Optional["QWidget"] = None,
    ) -> None:
        if not _QT_AVAILABLE:
            raise RuntimeError("PyQt6 부재 — SettingsDialog 생성 불가")
        super().__init__(parent)
        self._sound_player = sound_player
        # 한글 주석 — "설정" .ts entry tr() (5 locale: Settings/設定/设置/設定/設定).
        self.setWindowTitle(f"TooTalk · {_tr('설정')}")
        self.setMinimumSize(720, 560)
        # 한글 주석 — cycle 169.57 회수 — 모든 dialog modal 강제 (사용자 directive)
        self.setModal(True)
        # cycle 169.250 — frameless modal + main embed (사용자 critique image #10 회수 — 별도 window 차단)
        from PyQt6.QtCore import Qt as _Qt
        self.setWindowFlags(
            _Qt.WindowType.Dialog
            | _Qt.WindowType.FramelessWindowHint
        )

        initial = build_state_from_player(sound_player)

        # 한글 주석 — cycle 169.52 회수 — SVG icon 변환 + tab West + label 한글 short
        from PyQt6.QtCore import QSize
        from PyQt6.QtWidgets import QTabWidget
        from app.ui._icons import load_icon
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget(self)
        self._tabs.setTabPosition(QTabWidget.TabPosition.West)
        self._tabs.setIconSize(QSize(20, 20))
        outer.addWidget(self._tabs, stretch=1)

        # 10 section build + SVG icon 변환
        tab_defs = [
            (self._build_account_tab(), "account", _tr("계정")),
            (self._build_privacy_tab(), "privacy", _tr("보안")),
            (self._build_notification_tab(initial), "notification", _tr("알림")),
            (self._build_data_tab(), "data", _tr("데이터")),
            (self._build_theme_tab(), "theme", _tr("테마")),
            (self._build_locale_tab(), "locale", _tr("언어")),
            (self._build_device_tab(), "device", _tr("디바이스")),
            (self._build_folder_tab(), "folder", _tr("폴더")),
            (self._build_advanced_tab(), "settings", _tr("고급")),
            (self._build_about_tab(), "info", _tr("정보")),
        ]
        for widget, icon_name, label in tab_defs:
            self._tabs.addTab(widget, load_icon(icon_name, size=20, color="#9ca3af"), label)

        # OK / 취소 버튼 (기존 sound binding 보존 — _on_accept 호출 chain)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)  # type: ignore[arg-type]
        buttons.rejected.connect(self.reject)  # type: ignore[arg-type]
        outer.addWidget(buttons)

    # ------------------------------------------------------------------
    # 10 section tab builders (cycle 153.5 신설)
    # ------------------------------------------------------------------

    def _build_account_tab(self) -> "QWidget":
        """cycle 169.255 — telegram align compact layout (사용자 critique image #15 회수).

        QFormLayout default = label-value vertical gap 大 → QVBoxLayout 안 stacked row pattern
        (label 12px gray + value 14px white 의 단일 pair). placeholder "cycle 154 entry" 폐기.
        """
        from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout
        from app.ui._avatar_helper import make_initial_pixmap
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # 한글 주석 — avatar (telegram align — center top of account tab)
        avatar_label = QLabel()
        avatar_label.setPixmap(make_initial_pixmap("guest", size=96))
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 한글 주석 — info rows (value bold + label subtitle)
        for label_text, value_widget in [
            (_tr("이메일"), QLabel("user@example.com")),
            (_tr("username"), QLabel("@username")),
        ]:
            self._build_setting_row(outer, label_text, value_widget)

        # 한글 주석 — bio textarea (separate row)
        bio_label = QLabel(_tr("bio"))
        bio_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        outer.addWidget(bio_label)
        bio = QTextEdit()
        bio.setMaximumHeight(80)
        bio.setPlaceholderText(_tr("자기소개"))
        outer.addWidget(bio)

        outer.addStretch(1)
        return w

    def _build_setting_row(self, layout, label_text: str, value_widget) -> None:
        """telegram align row — value (14px bold) 위 + label (12px gray) 아래.

        cycle 169.255 — QFormLayout 폐기 + 수동 stacked row.
        """
        from PyQt6.QtWidgets import QFrame, QVBoxLayout
        wrap = QFrame()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        if isinstance(value_widget, QLabel):
            value_widget.setStyleSheet("color: #e5e7eb; font-size: 14px; font-weight: 600;")
        v.addWidget(value_widget)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
        v.addWidget(lbl)
        layout.addWidget(wrap)

    def _build_privacy_tab(self) -> "QWidget":
        from PyQt6.QtWidgets import QSpinBox, QWidget
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 20, 20, 20)
        form.addRow(_tr("E2EE"), QLabel("✅ Signal Protocol 활성"))
        form.addRow(_tr("2FA"), QLabel(f"🟡 {_tr('Phase 2~3 entry')}"))
        form.addRow(_tr("jailbreak detector"), QCheckBox(_tr("활성")))
        idle = QSpinBox()
        idle.setRange(0, 1440)
        idle.setValue(60)
        form.addRow(_tr("자동 로그아웃 (분)"), idle)
        return w

    def _build_notification_tab(self, initial: SettingsState) -> "QWidget":
        from PyQt6.QtWidgets import QWidget
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 20, 20, 20)

        # 한글 주석 — 기존 sound binding 보존 — enabled_check + volume_slider 인스턴스 attribute
        self._enabled_check = QCheckBox(f"{_tr('메시지')} 수신 시 재생")
        self._enabled_check.setChecked(initial.sound_enabled)
        form.addRow(_tr("signature sound"), self._enabled_check)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(volume_to_percent(initial.sound_volume))
        self._volume_slider.setTickInterval(10)
        self._volume_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        form.addRow(_tr("볼륨 (0~100)"), self._volume_slider)

        form.addRow(_tr("그룹 알림"), QCheckBox(_tr("활성")))
        form.addRow(_tr("봇 알림"), QCheckBox(_tr("활성")))
        return w

    def _build_data_tab(self) -> "QWidget":
        from PyQt6.QtWidgets import QPushButton, QSpinBox, QWidget
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 20, 20, 20)
        cap = QSpinBox()
        cap.setRange(100, 10000)
        cap.setValue(2000)
        form.addRow(_tr("ChatView 메시지 cap"), cap)
        form.addRow(_tr("자동 다운로드 — cellular"), QCheckBox(_tr("활성")))
        form.addRow(_tr("자동 다운로드 — wifi"), QCheckBox(_tr("활성")))
        form.addRow(_tr("캐시 size"), QLabel("0 MB"))
        clear = QPushButton(_tr("캐시 삭제"))
        clear.setProperty("variant", "danger")
        form.addRow("", clear)
        return w

    def _build_theme_tab(self) -> "QWidget":
        from PyQt6.QtWidgets import QSpinBox, QWidget
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 20, 20, 20)
        try:
            from app.ui.theme_picker import ThemePicker
            form.addRow(_tr("테마 모드"), ThemePicker())
        except Exception:
            form.addRow(_tr("테마 모드"), QLabel("dark / light / auto"))
        form.addRow(_tr("말풍선 색상"), QLabel("Toonation primary #0066FF"))
        font_size = QSpinBox()
        font_size.setRange(10, 20)
        font_size.setValue(13)
        form.addRow(_tr("글꼴 크기"), font_size)
        return w

    def _build_locale_tab(self) -> "QWidget":
        from PyQt6.QtWidgets import QComboBox, QWidget
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 20, 20, 20)
        combo = QComboBox()
        for label, code in [
            ("한국어", "ko"),
            ("English", "en"),
            ("中文 (简体)", "zh-CN"),
            ("中文 (繁體)", "zh-TW"),
            ("日本語", "ja"),
        ]:
            combo.addItem(f"{label} ({code})", code)
        form.addRow(_tr("표시 언어"), combo)
        form.addRow(QLabel(_tr("5 locale 지원 — cycle 132~149 i18n binding")))
        return w

    def _build_device_tab(self) -> "QWidget":
        from PyQt6.QtWidgets import QPushButton, QWidget
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel(_tr("현 device — macOS Sonoma 14.5")))
        layout.addWidget(QLabel(_tr("등록 device 목록 (cycle 119 endpoint)")))
        layout.addStretch(1)
        revoke = QPushButton(_tr("다른 device 종료"))
        revoke.setProperty("variant", "danger")
        layout.addWidget(revoke)
        return w

    def _build_folder_tab(self) -> "QWidget":
        from PyQt6.QtWidgets import QWidget
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel(_tr("custom 폴더 + 자동 filter — Phase 5+ entry")))
        layout.addStretch(1)
        return w

    def _build_advanced_tab(self) -> "QWidget":
        from PyQt6.QtWidgets import QLineEdit, QWidget
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 20, 20, 20)
        form.addRow(_tr("server endpoint"), QLineEdit("114.207.112.73:8080"))
        form.addRow(_tr("STUN URL"), QLineEdit("stun:stun.l.google.com:19302"))
        form.addRow(_tr("네트워크 사용량"), QLabel("0 MB"))
        debug = QCheckBox(_tr("debug log 활성"))
        form.addRow(_tr("debug"), debug)
        return w

    def _build_about_tab(self) -> "QWidget":
        from PyQt6.QtWidgets import QPushButton, QWidget
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title = QLabel("TooTalk")
        title.setStyleSheet("color: #0066FF; font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        layout.addWidget(QLabel(_tr("친구와 직접 연결되는 P2P 메신저")))
        layout.addWidget(QLabel("v0.5.0-pre1"))
        layout.addWidget(QLabel("License: GPL-3.0-or-later"))
        layout.addWidget(QLabel(_tr("개발 = Toonation")))
        layout.addStretch(1)
        link = QPushButton(_tr("GitHub 저장소"))
        link.setProperty("variant", "ghost")
        link.setFlat(True)
        layout.addWidget(link)
        return w

    def current_state(self) -> SettingsState:
        """현재 위젯 값 → ``SettingsState`` 스냅샷."""

        return SettingsState(
            sound_enabled=self._enabled_check.isChecked(),
            sound_volume=percent_to_volume(self._volume_slider.value()),
        )

    def _on_accept(self) -> None:
        """OK 클릭 = state 적용 + dialog close."""

        state = self.current_state()
        apply_to_player(state, self._sound_player)
        self.accept()
