"""S4. REFUTATION HYPOTHESIS — "이 주장을 깨려면 무엇이 존재해야 하는가".      [검색 0]

▸ 이 단계가 Pipeline Architecture 25%의 심장. 세컨드 화면에 에이전트의 추론이
  쿼리 형태로 그대로 읽힌다.
▸ 왜 S3 뒤: 캐시 히트면 이 비싼 단계(gpt-5.6-sol, high effort)를 아예 실행하지 않는다.
▸ 왜 S5 앞: 검색이 먼저 계획되고, 판정은 그 결과 안에서만 나온다 (PRD N3 —
  LLM이 먼저 답을 만들고 검색이 구색 맞추는 구조 금지).

검색 예산 (ARCHITECTURE §3): claim_type.default_search_budget에서 읽는다. 하드코딩 금지.
델타 모드는 절반 (이미 과거 증거가 있으므로). LLM이 예산을 넘겨 생성해도
코드가 잘라낸다 — 예산 준수를 LLM 선의에 맡기지 않는다.
"""
from __future__ import annotations

import math

from .. import prompts, schemas


def run_hypothesis(claim: dict, route: str, claim_type_row: dict, oai, settings,
                   emitter, *, delta_mode: bool, date_from: str | None) -> tuple[list[dict], list[dict]]:
    """반환: (hypotheses, budget 내로 잘라낸 쿼리 목록 [{query_text, language}])"""
    budget = compute_budget(int(claim_type_row["default_search_budget"]), delta_mode)
    user = (
        f"클레임: {claim['claim_text']}\n"
        f"claim_type: {claim['claim_type_code']}\n"
        f"검증 경로: {route}\n"
        f"search_budget: {budget}"
        + (f"\n[델타 모드] {date_from} 이후의 신규 문서만 대상. 과거 증거는 이미 확보됨."
           if delta_mode else "")
    )
    result = oai.structured(
        model=settings.model_hypothesis, effort="high",
        system=prompts.HYPOTHESIS, user=user,
        schema_name="hypothesis", schema=schemas.HYPOTHESIS_SCHEMA,
        emitter=emitter, stage="S4_HYPOTHESIS",
    )
    hypotheses = result.get("hypotheses", [])
    return hypotheses, clamp_queries(hypotheses, budget)


def compute_budget(default_budget: int, delta_mode: bool) -> int:
    return max(1, math.ceil(default_budget / 2)) if delta_mode else default_budget


def clamp_queries(hypotheses: list[dict], budget: int) -> list[dict]:
    """가설 순서대로 쿼리를 모으되 총 예산 초과분은 버린다 (B09 게이트: 예산 초과 안 함)."""
    queries: list[dict] = []
    for h in hypotheses:
        for q in h.get("queries", []):
            if len(queries) >= budget:
                return queries
            if q.get("query_text"):
                queries.append({"query_text": q["query_text"],
                                "language": q.get("language", "ko"),
                                "hypothesis": h.get("hypothesis")})
    return queries
