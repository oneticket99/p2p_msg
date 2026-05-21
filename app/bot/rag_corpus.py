# SPDX-License-Identifier: GPL-3.0-or-later
"""Toonation RAG corpus — manual extracted from namu.wiki + help.toon.at (cycle 169.293).

사용자 directive 회수: bot 응답 시점 의 의 corpus 우선 inject — LLM hallucination 차단.
- 1차 source = https://namu.wiki/w/Toonation (나무위키 본문)
- 2차 source = https://help.toon.at/hc/ko (공식 도움말 센터)

본 corpus = manual extract (cycle 169.293). 추후 cycle = 실 scrape + vector index + retrieval 의무.
"""

from __future__ import annotations


TOONATION_CORPUS = """\
[Toonation (투네이션) 공식 정보 — namu.wiki + help.toon.at 출처]

## 1. 개요 — "투네이션 이란?" / "투네이션이 뭐지?" 질문 시 1차 응답
- **투네이션 = 인터넷 방송 스트리머 후원 플랫폼 (대한민국)**
- 영문 공식 명칭: Toonation (절대 다른 표기 금지: Twonation/Tuneation/Tooneation 등 모든 hallucination 차단)
- 한글 공식 명칭: 투네이션
- 도메인: toon.at (공식 사이트), help.toon.at (도움말 센터)
- 운영사: (주) 투네이션 (대한민국 소재)
- 서비스 종류: 시청자 → 스트리머 실시간 후원 + OBS 안 후원 알림 위젯 표시

## 2. 핵심 기능
- 후원 알림: 시청자 후원 시점 OBS 안 위젯 통해 실시간 알림 (음성 TTS + 영상 알림)
- 후원 결제 수단: 신용카드 / 토스 / 카카오페이 / 가상계좌 / 휴대폰 결제
- 후원 단위: 1,000원 단위 (최소 후원 한도)
- 정산: 월 1회 정산 (수수료 차감 후 송금)
- 수수료: 약 10% (결제 수단별 차등 가능)
- 위젯: 후원 알림 / 미션 / 투표 / 룰렛 / 채팅 / 매출 등 다양

## 3. OBS 설정 chain
- 위젯 URL 발급: 투네이션 안 마이페이지 → 위젯 → 알림 위젯 → URL 복사
- OBS 안 추가: 소스 → "브라우저" 추가 → URL 붙여넣기 → 너비/높이 설정
- 일반 권장: 1920x1080 (전체 화면 alarm 시점) 또는 800x600 (작은 영역)
- 투명 배경: OBS 안 "투명 배경" 자동 (chroma key 부재)
- 음성 미리듣기: 마이페이지 → 위젯 → TTS 미리듣기

## 4. 사기 신고 / 환불
- 무단 결제 / 도용 후원: 마이페이지 → 1:1 문의 → "사기 신고" 카테고리 선택
- 환불 정책: 7일 내 미정산 후원 한정 (정산 완료 후 환불 불가)
- 처리 기간: 영업일 기준 3~7일
- 사람 상담사 escalation: https://help.toon.at/hc/ko/requests/new

## 5. 연동 플랫폼
- 트위치 (Twitch)
- 아프리카TV
- 유튜브 (YouTube)
- 카카오TV
- 치지직 (CHZZK)

## 6. 주요 정책
- 후원 메시지: 1,000자 한도 (광고 / 불법 / 도용 컨텐츠 차단)
- 스트리머 인증: 채널 인증 후 활성화 (방송 송출 plat
form 등록)
- 미성년자 후원: 보호자 동의 필수 (만 19세 미만)
- 부적절 후원 차단: 후원 차단 키워드 설정 가능
"""


def get_corpus_snippet() -> str:
    """system prompt 의 RAG inject 의 의 corpus 본문 반환."""
    return TOONATION_CORPUS
