"""S3. CACHE ROUTING — 결정론적. LLM 아님. (DB_SCHEMA.md §2 route_cache 그대로)

▸ 왜 LLM이 아닌가: 재현 가능해야 하고, 캐시 판단은 판단이 아니라 규칙이다.
▸ 왜 S2 뒤: 카테고리가 확정돼야 매칭 파티션이 정해진다 (D-08).
▸ 왜 S4 앞: 캐시 히트면 S4~S6(가설·검색·판정)를 통째로 스킵한다.

규칙:
  매칭 실패                              → MISS    (풀 검색)
  매칭 + last_searched_at이 TTL 이내     → HIT     (재검색 없이 즉시 응답)
  매칭 + TTL 초과                        → DELTA   (date_from=last_searched_at)
                                           단, LINER 날짜필터 미지원이면 풀 검색으로 축소
                                           (fresh/full 2-state — PRD §10-4, M4)

사람 피드백(agree/dispute) 기반 REVERIFY는 제거됨 — 목표가 사람 큐레이션이
아니라 입력을 받는 대로 DB에 축적하는 것이므로, 캐시 무효화는 오직 TTL(시간
간극)로만 결정한다.

last_seen_at(조회 시각) vs last_searched_at(실제 검색 시각)을 혼동하지 말 것 —
캐시로만 서빙되면 last_seen_at만 갱신되고, 그 간극이 델타 서치를 트리거한다.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..db import normalized_hash


def decide_cache_action(canonical: dict | None, *, ttl_days: int, now: datetime,
                        supports_date_filter: bool) -> tuple[str, str | None]:
    """반환: (decision, date_from) — 순수 함수로 분리해 결정론을 테스트로 증명 (B08)."""
    if canonical is None:
        return "MISS", None
    last_searched = canonical.get("last_searched_at")
    if last_searched is not None:
        if last_searched.tzinfo is None:
            last_searched = last_searched.replace(tzinfo=timezone.utc)
        if (now - last_searched).days <= ttl_days:
            return "HIT", None
        if supports_date_filter:
            return "DELTA", last_searched.date().isoformat()
    return "MISS", None  # 검색 이력 없음 또는 델타 스코프 아웃 → 풀 검색


def run_cache_check(claim: dict, category_id: str, embedding: list[float],
                    ttl_days: int, db, settings) -> tuple[str, str | None, dict | None]:
    """같은 industry_category 파티션 내에서만 canonical 매칭 (해시 우선, 벡터 보조)."""
    claim_hash = normalized_hash(claim["normalized_text"])
    canonical = db.find_canonical_by_hash(category_id, claim_hash)
    if canonical is None:
        canonical = db.find_canonical_by_vector(category_id, embedding,
                                                settings.canonical_threshold)
    if canonical is not None:
        db.touch_canonical_seen(canonical["canonical_id"])  # member_count++, last_seen_at
    decision, date_from = decide_cache_action(
        canonical, ttl_days=ttl_days, now=datetime.now(timezone.utc),
        supports_date_filter=settings.liner_supports_date_filter,
    )
    if decision == "HIT":
        db.bump_canonical_reuse(canonical["canonical_id"])
    return decision, date_from, canonical
