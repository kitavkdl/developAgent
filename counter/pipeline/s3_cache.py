"""S3. CACHE ROUTING — 결정론적. LLM 아님.                                    [검색 0]

▸ 왜 LLM이 아닌가: 재현 가능해야 하고, 캐시 판단은 판단이 아니라 규칙이다.
▸ 왜 S2 뒤: 카테고리가 확정돼야 매칭 파티션이 정해진다 (D-08).
▸ 왜 S4 앞: 캐시 히트면 S4~S6(가설·검색·판정)를 통째로 스킵한다 — 핵심 차별화 서사.

규칙 (ARCHITECTURE §1 S3):
  매칭 실패                          → MISS   (풀 검색)
  매칭 + needs_reverification=true   → REVERIFY (풀 검색)
  매칭 + TTL 이내                    → HIT    (캐시 즉시 반환)
  매칭 + TTL 초과 + 이의 없음        → DELTA  (date_from 지정 재검색)
                                       단, LINER 날짜필터 미지원이면 MISS로 축소
                                       (fresh/full 2-state — PRD §10-4, D-09)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..db import normalized_hash


def decide_cache_action(canonical: dict | None, *, now: datetime,
                        supports_date_filter: bool) -> tuple[str, str | None]:
    """반환: (decision, date_from) — 순수 함수로 분리해 결정론을 테스트로 증명 (B08)."""
    if canonical is None:
        return "MISS", None
    if canonical.get("needs_reverification"):
        return "REVERIFY", None
    verified_at = canonical["verified_at"]
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)
    expires = verified_at + timedelta(days=int(canonical["ttl_days"]))
    if now <= expires:
        return "HIT", None
    if supports_date_filter:
        return "DELTA", verified_at.date().isoformat()
    return "MISS", None  # 델타 서치 스코프 아웃 시 2-state 축소


def run_cache_check(claim: dict, category_id: int, embedding: list[float],
                    db, settings) -> tuple[str, str | None, dict | None]:
    """같은 industry_category 파티션 내에서만 canonical 매칭 (해시 우선, 벡터 보조)."""
    nhash = normalized_hash(claim["normalized_text"])
    canonical = db.find_canonical_by_hash(category_id, nhash)
    if canonical is None:
        canonical = db.find_canonical_by_vector(category_id, embedding,
                                                settings.canonical_threshold)
    decision, date_from = decide_cache_action(
        canonical, now=datetime.now(timezone.utc),
        supports_date_filter=settings.liner_supports_date_filter,
    )
    return decision, date_from, canonical
