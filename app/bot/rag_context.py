# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 bot RAG context layer — 사이클 68.

memory `project_bot_framework.md` (A) 투네이션 고객센터 봇 의 RAG context 의
실 layer — FAQ + 정책 문서 의 retrieval. cycle 66 `customer_service_bot` 의
system prompt 의 외 의 추가 context injection.

본 cycle 범위
-------------
- ``FAQEntry`` frozen dataclass — id + topic + question + answer + tags
- ``RAGStore`` Protocol — search(query, top_k) async / sync
- ``KeywordRAGStore`` — substring + token overlap 의 simple ranking (no deps)
- ``EmbeddingRAGStore`` placeholder — sentence-transformers + cosine sim 의 별개 cycle
- ``build_default_toonation_faq`` — 5 영역 의 default 10 entry
- ``compose_rag_context`` — query → top-k entry → prompt-ready 의 context string

본 cycle 의 범위 외 (별개 cycle):
- sentence-transformers / OpenAI embeddings / 의 실 vector store
- FAISS / Chroma / pgvector 의 외부 의존
- 정책 markdown 의 chunk + embedding pipeline
- 의미 검색 의 ranking + rerank model
"""

from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Final, List, Optional, Protocol, Sequence, Tuple

# default top-k — caller 의 권장 max
_DEFAULT_TOP_K: Final[int] = 3
# stopwords 의 minimal Korean + English (token overlap 의 noise 제거)
_STOPWORDS: Final[frozenset] = frozenset(
    {
        "의", "은", "는", "이", "가", "을", "를", "에", "과", "와", "도", "만",
        "the", "a", "an", "is", "of", "to", "for", "and", "or",
    }
)


@dataclass(frozen=True, slots=True)
class FAQEntry:
    """단일 FAQ entry — RAG store 의 base record.

    Attributes
    ----------
    id : str
        고유 식별자 (예: "donate-001").
    topic : str
        5 영역 (donation / payout / obs / fraud / refund).
    question : str
        FAQ 의 의 question 텍스트.
    answer : str
        모범 답변 — bot reply 의 base.
    tags : tuple[str, ...]
        token match 의 추가 keywords (frozen 의무).
    """

    id: str
    topic: str
    question: str
    answer: str
    tags: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("id 빈 문자열 불가")
        if not self.topic:
            raise ValueError("topic 빈 문자열 불가")
        if not self.question:
            raise ValueError("question 빈 문자열 불가")
        if not self.answer:
            raise ValueError("answer 빈 문자열 불가")


class RAGStore(Protocol):
    """RAG store interface — substring 또는 embedding 등 의 backend 통일."""

    def search(self, query: str, top_k: int = _DEFAULT_TOP_K) -> List[FAQEntry]:
        """query 의 의 top-k FAQ entry 반환."""
        ...

    def add(self, entry: FAQEntry) -> None:
        """entry 추가."""
        ...

    def size(self) -> int:
        """저장 entry 수."""
        ...


def _tokenize(text: str) -> List[str]:
    """간단 token split — whitespace + lowercase + stopword 제거."""

    tokens = [t.lower() for t in text.split() if t]
    return [t for t in tokens if t not in _STOPWORDS]


def _score_entry(query_tokens: List[str], entry: FAQEntry) -> float:
    """token overlap + substring boost — 단순 ranking.

    Returns
    -------
    float
        0.0 ~ 1.0 의 score. substring 의 query 발견 = +0.5 boost.
    """

    if not query_tokens:
        return 0.0
    # token overlap = question + tags 의 token 의 set intersection
    haystack = set(_tokenize(entry.question))
    for tag in entry.tags:
        haystack.update(_tokenize(tag))
    overlap = sum(1 for t in query_tokens if t in haystack)
    base_score = overlap / max(1, len(query_tokens))
    # substring boost
    q_lower = " ".join(query_tokens)
    if q_lower and q_lower in entry.question.lower():
        base_score += 0.5
    return min(1.0, base_score)


class KeywordRAGStore:
    """substring + token overlap 의 simple RAG store — no dependencies.

    Parameters
    ----------
    entries : Sequence[FAQEntry] | None
        초기 entry list. None = 빈 store.
    """

    def __init__(self, entries: Optional[Sequence[FAQEntry]] = None) -> None:
        self._entries: List[FAQEntry] = list(entries or [])

    def add(self, entry: FAQEntry) -> None:
        """entry 추가 — 동일 id 존재 시 ValueError."""

        for existing in self._entries:
            if existing.id == entry.id:
                raise ValueError(f"id 중복 — {entry.id} 이미 등록")
        self._entries.append(entry)

    def size(self) -> int:
        return len(self._entries)

    def search(
        self, query: str, top_k: int = _DEFAULT_TOP_K
    ) -> List[FAQEntry]:
        """query → top-k FAQEntry 의 score DESC 정렬.

        Notes
        -----
        score 0 = 제외. tie = 의 입력 순서 보존.
        """

        if top_k <= 0:
            raise ValueError(f"top_k 양수 의무 — {top_k}")
        if not query:
            return []
        q_tokens = _tokenize(query)
        scored = [
            (_score_entry(q_tokens, e), idx, e)
            for idx, e in enumerate(self._entries)
        ]
        # score > 0 만 + DESC score + ASC idx (tie 안정)
        filtered = [(s, i, e) for s, i, e in scored if s > 0]
        filtered.sort(key=lambda x: (-x[0], x[1]))
        return [e for _, _, e in filtered[:top_k]]


class Embedder(Protocol):
    """텍스트 → 벡터 backend abstraction.

    실 구현 후보 — sentence-transformers + OpenAI text-embedding-3 + Anthropic
    Voyage. 본 layer 의 caller 의 DI 의 sync 호출 + List[float] 반환 의 통일.

    Notes
    -----
    동기 호출 의무 — async 의 별개 cycle. 차원 (dim) 의 일관성 의무 — store 의
    entries 간 동일 차원.
    """

    def embed(self, text: str) -> List[float]:
        """단일 텍스트 → 벡터."""
        ...

    def dim(self) -> int:
        """벡터 차원."""
        ...


class MockEmbedder:
    """deterministic hash-based embedder — 테스트 + 의 baseline.

    실 모델 의존성 부재 의 환경 의 cosine sim layer 단독 검증 용. tokenize 의
    소문자화 + stopword 제거 + 각 token 의 hash → dim slot 의 누적 + L2
    normalize.

    Parameters
    ----------
    dim_value : int
        벡터 차원 (default 16). 양수 의무.
    """

    def __init__(self, dim_value: int = 16) -> None:
        if dim_value <= 0:
            raise ValueError(f"dim_value 양수 의무 — {dim_value}")
        self._dim = dim_value

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self._dim
        if not text:
            return vec
        tokens = _tokenize(text)
        for tok in tokens:
            slot = hash(tok) % self._dim
            vec[slot] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    def dim(self) -> int:
        return self._dim


class CachedEmbedder:
    """Embedder Protocol wrapper — OrderedDict 기반 LRU cache.

    동일 텍스트 의 embed 호출 의 중복 회피 — sentence-transformers + OpenAI
    embedding API 의 호출 비용 의 절감 + 응답 지연 회피.

    Parameters
    ----------
    embedder : Embedder
        wrapping target — 실 embed 의 backend (MockEmbedder + sentence-transformers).
    max_cache : int
        LRU cache 의 최대 entry 수 (default 256 + 양수 의무).

    Attributes
    ----------
    hits : int
        cache hit 횟수 (instrumentation).
    misses : int
        cache miss 횟수.

    Notes
    -----
    thread-safety 미보장 — async 의 single event loop 의 가정. multi-thread
    환경 의 별개 cycle 의 lock 의무. 텍스트 의 strip + lowercase 의 normalize
    부재 — caller 가 의무.
    """

    def __init__(self, embedder: "Embedder", max_cache: int = 256) -> None:
        if max_cache <= 0:
            raise ValueError(f"max_cache 양수 의무 — {max_cache}")
        self._embedder = embedder
        self._max_cache = max_cache
        self._cache: "OrderedDict[str, List[float]]" = OrderedDict()
        self.hits: int = 0
        self.misses: int = 0

    def embed(self, text: str) -> List[float]:
        """text → 벡터 — cache hit 시 즉시 반환 + miss 시 backend 호출 + LRU 갱신."""

        cached = self._cache.get(text)
        if cached is not None:
            # LRU update — 최근 사용 의 위치 의 끝 이동
            self._cache.move_to_end(text)
            self.hits += 1
            return cached
        self.misses += 1
        vec = self._embedder.embed(text)
        self._cache[text] = vec
        if len(self._cache) > self._max_cache:
            # 가장 오래된 entry 의 evict (FIFO end)
            self._cache.popitem(last=False)
        return vec

    def dim(self) -> int:
        return self._embedder.dim()

    def size(self) -> int:
        """현 cache 의 entry 수."""

        return len(self._cache)

    def reset_stats(self) -> None:
        """hits + misses counter 의 0 reset (clear cache 부재)."""

        self.hits = 0
        self.misses = 0

    def clear(self) -> None:
        """cache + stats 의 전수 reset."""

        self._cache.clear()
        self.reset_stats()


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """벡터 a + b 의 cosine similarity.

    Returns
    -------
    float
        [-1.0, 1.0] range. 차원 mismatch / 빈 벡터 → ValueError.
    """

    if len(a) != len(b):
        raise ValueError(
            f"차원 mismatch — len(a)={len(a)} len(b)={len(b)}"
        )
    if not a:
        raise ValueError("빈 벡터 불가")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingRAGStore:
    """Embedder backend 기반 RAG store — cosine sim ranking.

    Parameters
    ----------
    embedder : Embedder
        텍스트 → 벡터 backend (MockEmbedder + sentence-transformers + OpenAI 등).
    entries : Sequence[FAQEntry] | None
        초기 entry list. 모든 entry 의 question 의 embed 가 add 시 의 사전 계산.

    Notes
    -----
    실 vector store (FAISS / Chroma / pgvector) 의 별개 cycle. 본 cycle = 의 in-memory
    cosine sim 의 baseline. n < 1000 의 entry 의 의 linear scan 적합.
    """

    def __init__(
        self,
        embedder: Embedder,
        entries: Optional[Sequence[FAQEntry]] = None,
    ) -> None:
        self._embedder = embedder
        self._entries: List[FAQEntry] = []
        self._vectors: List[List[float]] = []
        for entry in entries or []:
            self.add(entry)

    def add(self, entry: FAQEntry) -> None:
        """entry 추가 — id 중복 차단 + question 의 embed 의 사전 계산.

        tags + question 결합 텍스트 embed = retrieval recall 향상.
        """

        for existing in self._entries:
            if existing.id == entry.id:
                raise ValueError(f"id 중복 — {entry.id} 이미 등록")
        text_for_embed = entry.question
        if entry.tags:
            text_for_embed = f"{entry.question} {' '.join(entry.tags)}"
        vec = self._embedder.embed(text_for_embed)
        if len(vec) != self._embedder.dim():
            raise ValueError(
                f"embedder dim mismatch — entry={len(vec)} dim={self._embedder.dim()}"
            )
        self._entries.append(entry)
        self._vectors.append(vec)

    def size(self) -> int:
        return len(self._entries)

    def search(
        self, query: str, top_k: int = _DEFAULT_TOP_K
    ) -> List[FAQEntry]:
        """query → top-k FAQEntry 의 cosine sim DESC 정렬.

        Notes
        -----
        sim 0 = 제외. tie = 입력 순서 안정 유지.
        """

        if top_k <= 0:
            raise ValueError(f"top_k 양수 의무 — {top_k}")
        if not query or not self._entries:
            return []
        q_vec = self._embedder.embed(query)
        scored: List[Tuple[float, int, FAQEntry]] = []
        for idx, (entry, vec) in enumerate(zip(self._entries, self._vectors)):
            sim = cosine_similarity(q_vec, vec)
            if sim > 0:
                scored.append((sim, idx, entry))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [e for _, _, e in scored[:top_k]]


def build_default_toonation_faq() -> List[FAQEntry]:
    """투네이션 default FAQ 10 entry — 5 영역 × 2.

    실 service 의 FAQ markdown 의 import 의 별개 cycle (별개 doc 의 chunk +
    embedding pipeline). 본 cycle = minimal seed.
    """

    return [
        FAQEntry(
            id="donate-001",
            topic="donation",
            question="후원 결제 수단 의 종류?",
            answer="카드 / 토스 / 카카오페이 / 계좌이체 의 4 종 의 결제 수단 지원.",
            tags=("후원", "결제", "카드", "토스", "카카오페이"),
        ),
        FAQEntry(
            id="donate-002",
            topic="donation",
            question="후원 메시지 의 화면 표시 정책?",
            answer="후원 메시지 = OBS 위젯 의 의 화면 overlay 의 의 표시. 욕설 필터 자동 적용.",
            tags=("후원", "메시지", "OBS", "위젯", "표시"),
        ),
        FAQEntry(
            id="payout-001",
            topic="payout",
            question="정산 주기 + 수수료?",
            answer="정산 주기 = 매주 화요일. 수수료 = 10%. 세금계산서 = 분기 마감.",
            tags=("정산", "주기", "수수료", "세금"),
        ),
        FAQEntry(
            id="payout-002",
            topic="payout",
            question="정산 보류 사유?",
            answer="정산 보류 = 사기 신고 진행 중 또는 미인증 계좌 + 신원 인증 미완료.",
            tags=("정산", "보류", "사기", "인증"),
        ),
        FAQEntry(
            id="obs-001",
            topic="obs",
            question="OBS 위젯 URL 발급 방법?",
            answer="설정 → 위젯 → URL 발급 클릭 + OBS 의 browser source 의 URL 의 붙여넣기.",
            tags=("OBS", "위젯", "URL", "발급", "browser source"),
        ),
        FAQEntry(
            id="obs-002",
            topic="obs",
            question="OBS 위젯 의 transparent + chroma key?",
            answer="위젯 = 의 default transparent (alpha 채널 지원). chroma key 의 부재 권장.",
            tags=("OBS", "위젯", "transparent", "chroma", "투명"),
        ),
        FAQEntry(
            id="fraud-001",
            topic="fraud",
            question="무단 결제 신고 절차?",
            answer="고객센터 → 사기 신고 → 결제 내역 첨부. 24시간 응답 의무 + 환급 진행.",
            tags=("사기", "신고", "무단", "결제", "환급"),
        ),
        FAQEntry(
            id="fraud-002",
            topic="fraud",
            question="도용 후원 환급 기간?",
            answer="도용 후원 = 신고 직후 정산 보류 + 1주 의 조사 + 환급 의 처리.",
            tags=("도용", "후원", "환급", "조사"),
        ),
        FAQEntry(
            id="refund-001",
            topic="refund",
            question="환불 정책 의 일자 한도?",
            answer="환불 = 7일 내 + 미정산 후원 의 한도. 정산 완료 후 = 사기 신고 의 의 별개 절차.",
            tags=("환불", "7일", "미정산", "한도"),
        ),
        FAQEntry(
            id="refund-002",
            topic="refund",
            question="환불 신청 양식 의 의무 정보?",
            answer="환불 신청 = 후원 ID + 사유 + 결제 영수증 의 3 항목 의무.",
            tags=("환불", "신청", "양식", "영수증"),
        ),
    ]


def compose_rag_context(
    query: str,
    store: RAGStore,
    top_k: int = _DEFAULT_TOP_K,
) -> str:
    """query → top-k entry → prompt-ready context string.

    Returns
    -------
    str
        "# 참고 FAQ\\n\\n- Q: ...\\n  A: ...\\n\\n..." 의 markdown.
        빈 결과 = 빈 string.
    """

    entries = store.search(query, top_k=top_k)
    if not entries:
        return ""
    lines = ["# 참고 FAQ", ""]
    for e in entries:
        lines.append(f"- Q: {e.question}")
        lines.append(f"  A: {e.answer}")
        lines.append("")
    return "\n".join(lines)
