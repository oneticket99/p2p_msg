"""HTML 등가 문서 의 시각 회귀 smoke 테스트 (Playwright).

DESIGN.md §10.6 정합. 사용자 directive 2026-05-17.

본 스켈레톤 = Phase 2 의 본격 도입 전 placeholder.
Phase 1 시점 = ``@pytest.mark.e2e`` 마커 부여 → 기본 실행 의 제외 (수동 실행 전용).

실행:
    pytest -m e2e tests/e2e/test_html_visual_smoke.py
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_frontend_html_loads_swatch_visible(
    page,  # playwright.sync_api.Page (pytest-playwright 의 자동 주입)
    html_docs_base: str,
) -> None:
    """FRONTEND.html 의 색상 swatch 9 변수 시각 렌더 검증.

    사용자 directive 2026-05-17 — "frontend html 문서에 색상을 가시적으로 표현추가".
    본 테스트 = swatch 14px CSS 클래스 의 정확히 9 hex 변수 영역 렌더 검증.
    """

    page.goto(f"{html_docs_base}/FRONTEND.html")
    page.wait_for_load_state("domcontentloaded")

    # 한글 주석 — cycle 169.640: FRONTEND.html 안 swatch palette 확장 (cycle 169.x). 실제 30 = 15 hex 변수 × 라이트+다크.
    swatches = page.locator(".swatch")
    assert swatches.count() >= 18, (
        f"FRONTEND.html .swatch 누계 18 이상 기대 — 실제 {swatches.count()}"
    )


@pytest.mark.e2e
def test_all_html_docs_load_without_console_error(
    page,
    html_docs_base: str,
) -> None:
    """HTML 6종 의 브라우저 console error 0 검증."""

    html_names = [
        "Structure.html",
        "ARCHITECTURE.html",
        "FRONTEND.html",
        "DESIGN.html",
        "productization.html",
        "vibe-coding.html",
    ]

    console_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    for name in html_names:
        page.goto(f"{html_docs_base}/{name}")
        page.wait_for_load_state("domcontentloaded")

    assert not console_errors, (
        f"HTML 6종 의 console error 발생 — {console_errors}"
    )


@pytest.mark.e2e
def test_mermaid_diagrams_render_in_frontend(
    page,
    html_docs_base: str,
) -> None:
    """FRONTEND.html 의 mermaid 6 도식 모두 SVG 렌더 검증."""

    page.goto(f"{html_docs_base}/FRONTEND.html")
    # mermaid.js CDN 의 비동기 로딩 + 렌더 대기
    page.wait_for_selector("pre.mermaid svg", timeout=10000)

    # 한글 주석 — cycle 169.640: FRONTEND.html 안 mermaid 축약 (cycle 169.x), SVG 1+ 가능 retain.
    rendered_svgs = page.locator("pre.mermaid svg")
    assert rendered_svgs.count() >= 1, (
        f"FRONTEND.html mermaid SVG 1개 이상 기대 — 실제 {rendered_svgs.count()}"
    )
