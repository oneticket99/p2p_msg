# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 bot 의 prompt injection / jailbreak heuristic detector — 사이클 81.

memory `project_bot_framework.md` (A) 고객센터 봇 의 보안 layer 의 추가 hardening.
cycle 74 의 system role 클라이언트 차단 (서버 영역 의 reject) 의 직후 layer —
user content 의 안 의 의도된 system instruction override 시도 detection.

본 module 범위
-------------
- ``JailbreakSignal`` Enum (NONE / SUSPICIOUS / BLOCKED)
- ``JailbreakMatch`` frozen dataclass — matched pattern + context
- ``JailbreakResult`` frozen dataclass — signal + reasons + matches
- ``detect(text)`` — Korean + English heuristic pattern detection
- 한국어 + 영어 의 jailbreak phrase 누계 8 영역

본 cycle 의 범위 외 (별개 cycle):
- LLM-as-judge (응답 의 LLM 의 의 detection)
- 학습 기반 classifier (BERT + RoBERTa 의 fine-tune)
- semantic similarity (embedding 의 jailbreak prompt 의 의 cosine)
- 다국어 confirm (중국어 + 일본어 + 스페인어 + 의 phrase 누적)
- 적응 패턴 learn (false positive feedback loop)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Final, List, Tuple


class JailbreakSignal(Enum):
    """detection 결과 신호 — caller 의 차단 의사결정 의 base."""

    NONE = "none"  # 의도된 시도 부재
    SUSPICIOUS = "suspicious"  # 약 match — 1건 + log + 허용 (warn)
    BLOCKED = "blocked"  # 강 match — 즉시 차단 (error)


# 약 match → SUSPICIOUS, 강 match → BLOCKED 의 threshold
_SUSPICIOUS_THRESHOLD: Final[int] = 1
_BLOCKED_THRESHOLD: Final[int] = 2


@dataclass(frozen=True, slots=True)
class JailbreakMatch:
    """단일 pattern match 의 상세 — debugging + log + caller 의 reason 의 base.

    Attributes
    ----------
    category : str
        pattern category (예: "instruction_override" / "role_hijack" / "system_leak").
    pattern : str
        matched regex pattern (raw string).
    match_text : str
        실 매치 된 텍스트 의 일부 (snippet — 첫 80 char 의 cap).
    severity : int
        가중치 (1 = 약 + 2 = 강). 합산 score 의 의 신호 결정.
    """

    category: str
    pattern: str
    match_text: str
    severity: int


@dataclass(frozen=True, slots=True)
class JailbreakResult:
    """detect() 의 응답 — caller 의 의 단일 entry.

    Attributes
    ----------
    signal : JailbreakSignal
        NONE / SUSPICIOUS / BLOCKED.
    matches : list[JailbreakMatch]
        match 의 누계 list (비어 있을 수 있음).
    score : int
        severity 의 합산.
    """

    signal: JailbreakSignal
    matches: List[JailbreakMatch] = field(default_factory=list)
    score: int = 0


# pattern catalog — (category, regex, severity)
# severity 1 = 약 + 2 = 강 (강 match 1개 = BLOCKED)
_PATTERNS: Final[Tuple[Tuple[str, str, int], ...]] = (
    # instruction override — system prompt 의 직접 override 시도
    ("instruction_override", r"ignore\s+(previous|prior|above|all)\s+instructions?", 2),
    ("instruction_override", r"disregard\s+(previous|prior|above|all)", 2),
    ("instruction_override", r"forget\s+(previous|prior|everything)", 2),
    ("instruction_override", r"이전\s*지시\s*(무시|잊)", 2),
    ("instruction_override", r"앞의?\s*(지시|명령|규칙)\s*(무시|잊)", 2),
    # role hijack — assistant / system 의 role 의 클라이언트 의 의 강제 전환
    ("role_hijack", r"you\s+are\s+now\s+(?:a|an|the)?", 2),
    ("role_hijack", r"act\s+as\s+(?:a|an|the)?", 1),
    ("role_hijack", r"pretend\s+(?:to\s+be|you'?re)", 2),
    ("role_hijack", r"당신은\s*이제\s*[가-힣\w]", 2),
    ("role_hijack", r"\b(DAN|jailbroken|dev\s*mode|developer\s*mode)\b", 2),
    # system leak — system prompt 의 의 contents 의 leak 시도
    ("system_leak", r"(show|reveal|display|print|repeat)\s+(\w+\s+){0,2}(system\s+)?(prompt|instructions|rules)", 2),
    ("system_leak", r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions|rules)", 1),
    ("system_leak", r"시스템\s*프롬프트\s*(보여|공개|출력)", 2),
    # delimiter injection — 의도된 system / user role marker
    ("delimiter_injection", r"\[\s*(system|assistant)\s*\]\s*[:=]?", 2),
    ("delimiter_injection", r"<\s*\|?(system|im_start|im_end)\|?\s*>", 2),
    ("delimiter_injection", r"###\s*(system|assistant)\s*###", 2),
    # privilege escalation — 권한 상승 시도
    ("privilege_escalation", r"(grant|give|enable)\s+(me\s+)?(admin|root|sudo)", 2),
    ("privilege_escalation", r"unrestricted\s+mode", 1),
    ("privilege_escalation", r"bypass\s+(safety|filter|guardrail)", 2),
    # info exfiltration — API key + secret + credential + PII 의도된 추출
    # 영문 reveal/expose/leak/show/print/dump → credential 키워드
    ("info_exfiltration", r"(reveal|expose|leak|show|print|dump|return)\s+(\w+\s+){0,3}(api[\s_-]?key|secret|password|passwd|token|credential)", 2),
    ("info_exfiltration", r"api[\s_-]?key\s*[:=]\s*\S+", 1),
    # 환경 변수 + dotenv 추출 시도
    ("info_exfiltration", r"(show|print|reveal|dump|cat)\s+(\w+\s+){0,2}(env|environment|dotenv|\.env)\s*(file|var|variable)?", 2),
    ("info_exfiltration", r"(os\.environ|process\.env|getenv)\s*\[\s*['\"]?[\w]+", 2),
    # JWT + Bearer token 추출
    ("info_exfiltration", r"(reveal|expose|show|print)\s+(\w+\s+){0,2}(bearer|jwt|access[\s_-]?token|refresh[\s_-]?token)", 2),
    # SSH / private key 추출
    ("info_exfiltration", r"(reveal|expose|show|cat|read)\s+(\w+\s+){0,2}(private[\s_-]?key|ssh[\s_-]?key|id_rsa|id_ed25519)", 2),
    ("info_exfiltration", r"-----BEGIN\s+(RSA\s+|EC\s+|OPENSSH\s+)?(PRIVATE|ENCRYPTED)\s+KEY", 2),
    # DB connection string 추출
    ("info_exfiltration", r"(reveal|expose|show|print|dump)\s+(\w+\s+){0,2}(database|db|mysql|postgres|mariadb|mongo)\s*(password|credential|connection)", 2),
    ("info_exfiltration", r"(mysql|postgres|postgresql|mongodb|mariadb)://[^@\s]+:[^@\s]+@", 2),
    # Korean equivalents — credential 노출 시도
    ("info_exfiltration", r"(비밀번호|패스워드|암호|키|토큰|시크릿|크리덴셜)[를을은는이가]?\s*(알려|공개|출력|보여|드러내|노출|반환)", 2),
    ("info_exfiltration", r"(api[\s_-]?key|access[\s_-]?token|secret[\s_-]?key)[를을은는이가]?\s*(알려|공개|출력|보여|드러내|노출)", 2),
    ("info_exfiltration", r"환경[\s_]*변수[를을은는이가]?\s*(알려|공개|출력|보여|드러내|노출|반환)", 2),
    # PII — 주민등록번호 + 카드번호 + 전화번호 추출 시도
    ("info_exfiltration", r"(주민(등록)?번호|주민번호|카드번호|계좌번호|전화번호|이메일)[를을은는이가]?\s*(알려|공개|출력|보여|드러내|노출)", 2),
    ("info_exfiltration", r"\b\d{6}[-\s]?[1-4]\d{6}\b", 2),
    # SQL injection 시도 — '; DROP TABLE / UNION SELECT
    ("info_exfiltration", r"(;\s*(DROP|TRUNCATE|DELETE|UPDATE)\s+TABLE|UNION\s+SELECT|OR\s+1\s*=\s*1)", 2),
    # Shell command injection — credential 파일 cat
    ("info_exfiltration", r"(cat|less|more|head|tail)\s+(/etc/(passwd|shadow|hosts)|~?/?\.ssh/|~?/?\.aws/credentials|~?/?\.config/)", 2),
)


# pre-compile patterns — case-insensitive 의무
_COMPILED: Final[List[Tuple[str, "re.Pattern[str]", int]]] = [
    (cat, re.compile(pat, re.IGNORECASE), sev) for cat, pat, sev in _PATTERNS
]


def detect(text: str) -> JailbreakResult:
    """user content → JailbreakResult 의 heuristic detection.

    Parameters
    ----------
    text : str
        사용자 입력 텍스트. 빈 문자열 = NONE 즉시 반환.

    Returns
    -------
    JailbreakResult
        signal (NONE/SUSPICIOUS/BLOCKED) + matches + score.

    Notes
    -----
    threshold — score 0 = NONE + score 1 = SUSPICIOUS + score ≥ 2 = BLOCKED.
    matches 의 첫 80자 snippet 의 cap — log 의 hygiene + content 의 fully echo 차단.
    """

    if not text:
        return JailbreakResult(signal=JailbreakSignal.NONE)
    matches: List[JailbreakMatch] = []
    score = 0
    for category, pattern, severity in _COMPILED:
        m = pattern.search(text)
        if m is None:
            continue
        snippet = m.group(0)
        if len(snippet) > 80:
            snippet = snippet[:80] + "..."
        matches.append(
            JailbreakMatch(
                category=category,
                pattern=pattern.pattern,
                match_text=snippet,
                severity=severity,
            )
        )
        score += severity
    if score == 0:
        signal = JailbreakSignal.NONE
    elif score >= _BLOCKED_THRESHOLD:
        signal = JailbreakSignal.BLOCKED
    else:
        signal = JailbreakSignal.SUSPICIOUS
    return JailbreakResult(signal=signal, matches=matches, score=score)


def is_blocked(text: str) -> bool:
    """편의 helper — detect 의 BLOCKED 만 True 반환."""

    return detect(text).signal == JailbreakSignal.BLOCKED


def summarize_categories(result: JailbreakResult) -> List[str]:
    """matches 의 category 의 unique list — log + monitoring 의 의 dimension.

    예: BLOCKED + [instruction_override, role_hijack, system_leak] → 3 dimension.
    """

    seen: List[str] = []
    for m in result.matches:
        if m.category not in seen:
            seen.append(m.category)
    return seen
