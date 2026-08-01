"""결정론적 REFUTED 게이트 (PRD N1 — 불가침 규칙, 유일한 정확성 방어선).

LLM이 "이건 반례입니다"라고 선언해도 REFUTED가 되지 않는다.
falsifier_spec.required_match_fields에서 true로 지정된 필드가 '전부' true일 때만
이 코드가 REFUTED를 조립한다. 사람 검수 단계가 설계상 없으므로(N2),
이 함수와 그 테스트(T2)가 오판정을 막는 전부다.
"""
from __future__ import annotations

MATCH_FIELDS = ("scope_match", "metric_match", "timeframe_match", "target_match")


def passes_refuted_gate(applicability_check: dict, required_match_fields: dict) -> bool:
    """required_match_fields에서 true인 필드가 전부 applicability_check에서 true인가.

    - 평가 결과에 필드가 아예 없으면 false로 간주 (fail-closed)
    - insufficient_access=true인 평가는 게이트를 통과할 수 없음 (추측 기반 true 차단)
    - is_syndicated_copy=true는 독립 증거가 아니므로 단독으로는 통과 불가
    """
    if applicability_check.get("insufficient_access"):
        return False
    if applicability_check.get("is_syndicated_copy"):
        return False
    return all(
        bool(applicability_check.get(field))
        for field, required in required_match_fields.items()
        if required
    )


def assemble_verdict_code(candidates: list[dict], required_match_fields: dict,
                          any_search_succeeded: bool) -> tuple[str, dict | None]:
    """S6 ①: 판정 코드는 LLM 선언이 아니라 이 조건문이 결정한다.

    - 게이트 통과 candidate 존재 → REFUTED (그 candidate가 evidence)
    - 검색이 하나도 성공 못 함(프로바이더 장애) → PUBLIC_SUBSTANTIATION_NOT_FOUND
    - 그 외 → NOT_REFUTED ("사실이다"가 아니라 "이 쿼리들에서 못 찾았다" — D-03)
    """
    for cand in candidates:
        if passes_refuted_gate(cand.get("applicability_check", {}), required_match_fields):
            return "REFUTED", cand
    if not any_search_succeeded:
        return "PUBLIC_SUBSTANTIATION_NOT_FOUND", None
    return "NOT_REFUTED", None
