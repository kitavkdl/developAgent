"""결정론적 REFUTED 게이트 (PRD N1, DB_SCHEMA.md §3 — 유일한 정확성 방어선).

LLM이 "이건 반례입니다"라고 선언해도 REFUTED가 되지 않는다.
falsifier_spec.required_match_fields({"scope":true,"metric":false,...})에서 true인
차원이 '전부' applicability_check의 해당 "<field>_match"에서 true일 때만
이 코드가 REFUTED를 조립한다. 사람 검수 단계가 설계상 없으므로(N2),
이 함수와 그 테스트(T2)가 오판정을 막는 전부다.

금지 사항 (DB_SCHEMA.md §3):
- LLM에게 최종 verdict_code를 생성하게 하지 말 것 — LLM은 boolean만 생성.
- 문자열 매칭만으로 REFUTED를 확정하지 말 것.
- evidence_link에 검색 결과에 없던 URL을 넣지 말 것 (N6).
"""
from __future__ import annotations

# falsifier 차원 (DB_SCHEMA.md falsifier_spec 초기값 표)
FALSIFIER_FIELDS = ("scope", "metric", "timeframe", "target_entity", "geography")

# 구조적으로 제3자 검증이 불가능한 claim_type (구축 요청 [D]) — 이 목록은
# claim_type 정의에 속하는 상수이지 검색 결과에 따라 달라지는 값이 아니므로
# 여기(게이트 코드)에 둔다. 반례를 실제로 찾으면 REFUTED는 그대로 유효하다.
NO_THIRD_PARTY_VERIFICATION_TYPES = {"SELF_REPORTED_PRIVATE_METRIC"}


def passes_refuted_gate(applicability_check: dict, required_match_fields: dict) -> bool:
    """required_match_fields에서 true인 차원 f가 전부 applicability_check[f+"_match"]에서
    true인가 (DB_SCHEMA.md §3의 assemble_verdict 조건과 동일).

    - 평가 결과에 필드가 없으면 false 간주 (fail-closed)
    - insufficient_access=true → 추측 기반 true 차단, 통과 불가
    - is_syndicated_copy=true → 독립 증거 아님, 단독 통과 불가
    """
    if applicability_check.get("insufficient_access"):
        return False
    if applicability_check.get("is_syndicated_copy"):
        return False
    return all(
        bool(applicability_check.get(f"{field}_match"))
        for field, required in required_match_fields.items()
        if required
    )


def assemble_verdict_code(candidates: list[dict], required_match_fields: dict,
                          any_search_succeeded: bool,
                          claim_type_code: str | None = None) -> tuple[str, dict | None]:
    """S6 ①: 판정 코드는 LLM 선언이 아니라 이 조건문이 결정한다.

    - 게이트 통과 candidate 존재 → REFUTED (그 candidate가 evidence)
    - 검색이 하나도 성공 못 함(프로바이더 장애) → PUBLIC_SUBSTANTIATION_NOT_FOUND
    - claim_type이 구조적으로 제3자 검증 불가능한 유형
      (NO_THIRD_PARTY_VERIFICATION_TYPES)이면, 검색은 성공했지만 반례를
      못 찾은 경우도 NOT_REFUTED가 아니라 PUBLIC_SUBSTANTIATION_NOT_FOUND —
      "이 쿼리들에서 못 찾았다"가 아니라 "확인할 공개 자료 자체가 구조적으로
      없다"가 더 정확한 진술이기 때문 (구축 요청 [D]).
    - 그 외 → NOT_REFUTED ("사실이다"가 아니라 "이 쿼리들에서 못 찾았다" — D-03)
    """
    for cand in candidates:
        if passes_refuted_gate(cand.get("applicability_check", {}), required_match_fields):
            return "REFUTED", cand
    if not any_search_succeeded or claim_type_code in NO_THIRD_PARTY_VERIFICATION_TYPES:
        return "PUBLIC_SUBSTANTIATION_NOT_FOUND", None
    return "NOT_REFUTED", None
