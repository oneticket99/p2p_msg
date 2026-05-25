# SPDX-License-Identifier: GPL-3.0-or-later
"""in-app overlay 모달 헬퍼 — nested dialog(self ≠ MainWindow)용 (cycle 169.838 신설).

사용자 directive: 앱의 모든 dialog 는 메인 레이아웃 안 in-app overlay 모달이어야 한다
(새창 허용 = 원격 데스크탑 제어 상대화면 창 1개뿐). MainWindow mixin 의 dialog 는
``self._exec_dialog_centered`` 를 직접 호출하면 되지만, dialog 내부에서 sub-dialog 를
여는 경우(contacts/settings sub-dialog 등) ``self`` 가 MainWindow 가 아니므로 parent
체인을 walk 해 ``_exec_dialog_centered`` 보유 위젯(MainWindow)을 찾아 위임한다.
미발견 환경(부모 트리에 MainWindow 부재)에서는 기존 ``.exec()`` 로 graceful 폴백.
"""

from __future__ import annotations

from typing import Any


def exec_modal(dialog: Any, opener: Any) -> int:
    """``dialog`` 를 in-app overlay 모달로 실행한다.

    Parameters
    ----------
    dialog : QDialog
        실행할 dialog.
    opener : QWidget
        dialog 를 연 위젯(보통 ``self``). 이 위젯의 parent 체인서 MainWindow 의
        ``_exec_dialog_centered`` 를 탐색한다.

    Returns
    -------
    int
        dialog 의 accept/reject 결과 코드.
    """
    # 한글 주석 — parent 체인 walk: _exec_dialog_centered(= MainWindow) 발견 시 위임
    widget = opener
    while widget is not None:
        if hasattr(widget, "_exec_dialog_centered"):
            return widget._exec_dialog_centered(dialog)
        widget = widget.parent() if hasattr(widget, "parent") else None
    # 한글 주석 — MainWindow 미발견(테스트/독립 실행 등) 시 별도 윈도우 폴백
    return dialog.exec()
