---
title: "Adoption Roadmap — TooTalk 도입·확장 로드맵"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# Adoption Roadmap

> TooTalk 사용자 채택 시나리오 + Phase 1~5 단계별 도입 전략.
> [PLANS.md](../../PLANS.md) 의 큰 비전 + [docs/assessments/productization.md](../assessments/productization.md) 의 시장 포지셔닝 옵션 정합.

---

## 1. 목적

본 로드맵은 단순 기능 일정표가 아닌 **사용자 채택 단계별 전략** 정의:

- 누구 (페르소나) → 언제 (Phase) → 어떻게 (배포 방식) → 왜 (가치 제안) 명문화
- 각 Phase 의 진입·종료 기준 (DoD) + KPI 측정 가능 기준
- Phase 진행 시 [docs/exec-plans/active/](../exec-plans/active/) 의 동기 갱신

---

## 2. 페르소나 ↔ Phase 매트릭스

[PRODUCT_SENSE.md](../../PRODUCT_SENSE.md) 페르소나 P1~P4 와 Phase 매핑:

| 페르소나 | 진입 Phase | 핵심 기능 의존 | 진입 트리거 |
|---|---|---|---|
| P4 데모 운영자 (`oneticket99`) | Phase 1 | 1:1 채팅 + 파일전송 + MariaDB 영속화 | 코드 진입 후 즉시 |
| P3 임시 협업 | Phase 2 | 그룹 채팅 (3~5인) + 세션 종료 의 정리 | E2EE 미적용 가능 |
| P2 가족 사진 | Phase 3 | 모바일 prototype + 푸시 알림 | 모바일 client 필수 |
| P1 보안 민감 팀 | Phase 4 | E2EE + 자체 호스팅 docker-compose + audit log | E2EE 완성 후 |

---

## 3. Phase 별 도입 전략

### 3.1 Phase 1 — 단일 사용자 dogfooding (2026-06-30 목표)

- **타겟**: P4 (저장소 owner)
- **범위**: 1:1 채팅 · 이미지/파일 전송 · MariaDB 영속화 · macOS+Windows 빌드
- **배포**: GitHub Release zip + 사용자 직접 다운로드
- **DoD**:
  - macOS ↔ Windows 의 양방향 텍스트 + 이미지 + 파일 송수신 회귀 PASS
  - PyInstaller zip 의 첫 실행 가능
  - CI 3 workflow GREEN
  - 9 정책 + 8 운영 문서 frontmatter `status: active`
- **KPI**:
  - dogfooding 의 1주 누계 메시지 100건 + 파일 10건
  - 크래시 0건
  - 시그널링 재연결 (95p) ≤ 5초

### 3.2 Phase 2 — 소규모 closed beta (2026-09-30 목표)

- **타겟**: P3 임시 협업 (5~10 사용자 직접 초대)
- **범위**: + 그룹 채팅 3~5인 + 자동 업데이트 + 보안 hardening (시그널링 TLS + rate-limit)
- **배포**: GitHub Release + 사용자 초대 링크 + 자체 docker-compose 번들
- **DoD**:
  - 그룹 채팅 5인 동시 접속 + 메시지 round-trip ≤ 500ms
  - 시그널링 서버 TLS + JWT 인증 활성
  - 카오스 시나리오 (정전 / NAT 재할당 / 디스크 가득) PASS
- **KPI**:
  - DAU ≥ 5 / WAU ≥ 10
  - 1주 retention ≥ 60%
  - 사용자 NPS ≥ 30

### 3.3 Phase 3 — E2EE + 모바일 prototype + **원격 제어 차별화** (2027-03-31 목표)

- **타겟**: P2 가족 사진 + P5 라이브 크리에이터 + P6 기술 도움 제공자 (사용자 directive 2026-05-17 차별화)
- **범위**:
  - libsignal-protocol 통합 + iOS/Android prototype + 푸시 알림
  - **원격 데스크탑 제어** (친구간 1:1, 패턴 A 도움 + 패턴 B 제어) — [[project-phase2-remote-control-differentiator]] 정합
  - WebRTC video track 추가 (현 DataChannel 외)
  - 화면 캡처 + 입력 주입 OS 별 어댑터 (macOS pyobjc + Windows pywinauto)
  - 명시 수락 모달 + 긴급 ESC + 친구 추가 사전 의무 + 감사 로그
- **배포**: TestFlight + Google Play closed track + Toonation 크리에이터 베타 초대
- **DoD**:
  - E2EE Signal Protocol 통합 PASS (외부 audit 권장)
  - 모바일 ↔ 데스크탑 양방향 메시지 송수신 PASS
  - 푸시 알림 (FCM + APNs) 의 retention 영향 measurement
  - **원격 제어 패턴 A + B 양방향 PASS** (P5 ↔ P6 OBS 설정 시나리오 dogfooding)
  - **권한 모델 PASS** (명시 수락 + 긴급 ESC + 감사 로그)
- **KPI**:
  - 모바일 사용자 ≥ 30% 비중
  - 30일 retention ≥ 50%
  - E2EE audit 의 critical issue 0
  - **원격 제어 세션 성공률 ≥ 95%** (네트워크 환경 정합)
  - **원격 제어 세션 평균 길이 ≥ 15분** (1회 OBS 설정 도움 추정)

### 3.4 Phase 4 — Enterprise/B2B 진입 (2027-09-30 목표)

- **타겟**: P1 보안 민감 팀 (선택된 기업 5~10곳)
- **범위**: + 자체 호스팅 docker-compose enterprise + SSO/SAML + audit log + admin console
- **배포**: Helm chart + 온프레미스 설치 가이드 + 24/7 지원 (옵션)
- **DoD**:
  - 자체 호스팅 의 5 기업 PoC 완료
  - SOC2 Type 1 또는 등가 audit 통과
  - admin console 의 사용자/방/메시지 관리 모두 동작
- **KPI**:
  - 유료 enterprise 고객 1+
  - 단일 호스트 의 동시 100 사용자 지원
  - admin operation 의 99.9% SLA

### 3.5 Phase 5 — 시장 확장 + 수익화 (2028-03-31 목표)

- **타겟**: P1~P4 모든 페르소나 + 신규 시장 (Toonation 통합 / 파트너 B2B / OSS 커뮤니티)
- **범위**: + 그룹 화상 (SFU) + 분산 시그널링 (libp2p) + WASM PWA + Pro 유료 플랜
- **배포**: SaaS + 자체 호스팅 + Whitelabel SDK
- **DoD**:
  - 그룹 화상 8인 동시 PASS
  - PWA 의 install 마찰 0 + 모바일 web push 정합
  - Pro 유료 전환율 ≥ 5%
- **KPI**:
  - MAU ≥ 10K
  - ARR ≥ $50K
  - Churn ≤ 5%/월

---

## 4. 시장 포지셔닝 옵션 ↔ Phase 매핑

[docs/assessments/productization.md](../assessments/productization.md) §4 옵션 4종 매핑:

| 옵션 | Phase 진입 | 결정 기준 |
|---|---|---|
| 옵션 A (OSS 자체 호스팅) | Phase 3~4 | E2EE + 모바일 완성 후 OSS 의 매력 발생 |
| 옵션 B (Toonation 내부 통신) | Phase 1~2 | 가장 빠른 ROI 검증 가능 — **현 시점 권장 ★★★★☆** |
| 옵션 C (P2P 파일 특화) | Phase 2 pivot | 메신저 표면 제거 + 파일 UX 집중 |
| 옵션 D (Whitelabel SDK) | Phase 5+ | SaaS API 의 외부 판매 |

---

## 5. Phase 진입 차단점 (현 시점 2026-05-17 누계)

| Phase | 차단점 | 해소 방법 | 담당 |
|---|---|---|---|
| Phase 1 → 2 | 코드 미진입 (스켈레톤 단계) | WebRTC DataChannel 연결 + MariaDB 영속화 코드 작성 | Claude (코드 spawn) + 사용자 (GO) |
| Phase 1 → 2 | self-hosted runner 미등록 | docs/references/ci-self-hosted-setup.md 절차 따라 등록 | 사용자 직접 |
| Phase 2 → 3 | 라이선스 미확정 | OSS / 상용 분기 결정 | 사용자 직접 |
| Phase 3 → 4 | E2EE 미통합 | libsignal-protocol Python bindings 도입 | Claude + 사용자 (검토) |
| Phase 4 → 5 | enterprise audit 미수행 | SOC2 Type 1 의 외부 컨설팅 | 사용자 (예산 결정) |

---

## 6. 본 로드맵 갱신 절차

본 문서 변경 시:

1. `docs/policies/adoption-roadmap.md` 본 파일 직접 수정
2. `last_verified` 필드 갱신
3. Phase 의 DoD 또는 KPI 변경 시 [docs/exec-plans/active/](../exec-plans/active/) 동기 갱신 의무
4. `tools/doc-lint.sh` 5 검사 통과
5. `README.md` 변경 이력 1줄 prepend + `History.md` 역순 prepend
6. `SKIP_PREPUSH=1 git push origin main`

---

## 7. 참조

- 정본: [CLAUDE_HARNESS_IMPORTANT.md](../../CLAUDE_HARNESS_IMPORTANT.md)
- 정책: [PLANS.md](../../PLANS.md) · [PRODUCT_SENSE.md](../../PRODUCT_SENSE.md) · [QUALITY_SCORE.md](../../QUALITY_SCORE.md)
- 평가 snapshot: [docs/assessments/productization.md](../assessments/productization.md) · [docs/assessments/vibe-coding.md](../assessments/vibe-coding.md)
- 실행계획: [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](../exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)
- 관련 정책: [doc-gardening.md](doc-gardening.md) · [execution-harness.md](execution-harness.md)
