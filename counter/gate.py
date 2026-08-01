"""결정론적 3단계 판정 게이트 (PRD N1 확장 — 유일한 정확성 방어선).

LLM이 "이건 반례/근거입니다"라고 선언해도 그 자체로 CONTRADICTED/CORROBORATED가
되지 않는다. falsifier_spec.required_match_fields({"scope":true,"metric":false,...})
에서 true인 차원이 '전부' applicability_check의 해당 "<field>_match"에서
true일 때만 — 그리고 방향(supports_claim)이 맞을 때만 — 이 코드가 판정을 조립한다.
사람 검수 단계가 설계상 없으므로(N2), 이 함수와 그 테스트(T2)가 오판정을 막는 전부다.

3단계 판정 (구축 요청 — 반례를 못 찾았다고 긍정적 결론을 내리지 않는다):
- CONTRADICTED  — 반박 근거 있음 (기존 REFUTED)
- CORROBORATED  — 뒷받침 근거 있음 (신규. supports_claim=true인 문서가 동일한
                  차원 게이트를 통과해야만 승격 — LLM 선언만으로는 안 됨)
- UNVERIFIED    — 반례도 뒷받침 근거도 못 찾음 (기존 NOT_REFUTED +
                  PUBLIC_SUBSTANTIATION_NOT_FOUND 통합). "참이다"도 "거짓이다"도
                  아니다 — 탐색 범위 내에서 판단을 유보한다는 뜻일 뿐이다. 검색
                  실패/구조적 검증 불가/단순 미발견은 모두 이 하나의 코드로
                  귀결되고, 세부 사유는 required_evidence_note/reasoning으로
                  별도 노출한다 (S6).

금지 사항 (DB_SCHEMA.md §3):
- LLM에게 최종 verdict_code를 생성하게 하지 말 것 — LLM은 boolean만 생성.
- 문자열 매칭만으로 CONTRADICTED/CORROBORATED를 확정하지 말 것.
- evidence_link에 검색 결과에 없던 URL을 넣지 말 것 (N6).
- UNVERIFIED를 "사실일 가능성이 있다" 같은 긍정 결론으로 포장하지 말 것.
"""
from __future__ import annotations

# falsifier 차원 (DB_SCHEMA.md falsifier_spec 초기값 표)
FALSIFIER_FIELDS = ("scope", "metric", "timeframe", "target_entity", "geography")

# 구조적으로 제3자 검증이 불가능한 claim_type (구축 요청 [D]) — 이 목록은
# claim_type 정의에 속하는 상수이지 검색 결과에 따라 달라지는 값이 아니므로
# 여기(게이트 코드)에 둔다. verdict_code 결정에는 더 이상 관여하지 않는다
# (검색 성공/실패, 구조적 검증 불가 여부와 무관하게 그 외 UNVERIFIED로
# 귀결) — 다만 S6이 required_evidence_note에 이 사유를 별도로 남긴다.
NO_THIRD_PARTY_VERIFICATION_TYPES = {"SELF_REPORTED_PRIVATE_METRIC"}


def _dims_pass(applicability_check: dict, required_match_fields: dict) -> bool:
    """required_match_fields에서 true인 차원 f가 전부 applicability_check[f+"_match"]에서
    true인가. 평가 결과에 필드가 없으면 false 간주 (fail-closed)."""
    return all(
        bool(applicability_check.get(f"{field}_match"))
        for field, required in required_match_fields.items()
        if required
    )


def passes_refuted_gate(applicability_check: dict, required_match_fields: dict) -> bool:
    """문서가 CONTRADICTED(반박) 후보로 통과하는가.

    - insufficient_access=true → 추측 기반 true 차단, 통과 불가
    - is_syndicated_copy=true → 독립 증거 아님, 단독 통과 불가
    - supports_claim=true → 방향이 반대(뒷받침)이므로 반박 후보에서 제외
    """
    if applicability_check.get("insufficient_access"):
        return False
    if applicability_check.get("is_syndicated_copy"):
        return False
    if applicability_check.get("supports_claim"):
        return False
    return _dims_pass(applicability_check, required_match_fields)


def passes_corroboration_gate(applicability_check: dict, required_match_fields: dict) -> bool:
    """문서가 CORROBORATED(뒷받침) 후보로 통과하는가 — 반박 게이트와 동일한
    차원 요건에 방향만 반대(supports_claim=true)로 요구한다. 자사 발표를
    재게재한 문서(is_syndicated_copy)는 독립적 뒷받침이 아니므로 여기서도
    동일하게 차단한다 — 그렇지 않으면 브랜드 자신의 홍보 문구 재게재만으로
    스스로를 "입증"하는 순환 논리가 생긴다.
    """
    if applicability_check.get("insufficient_access"):
        return False
    if applicability_check.get("is_syndicated_copy"):
        return False
    if not applicability_check.get("supports_claim"):
        return False
    return _dims_pass(applicability_check, required_match_fields)


def assemble_verdict_code(candidates: list[dict],
                          required_match_fields: dict) -> tuple[str, dict | None]:
    """S6 ①: 판정 코드는 LLM 선언이 아니라 이 조건문이 결정한다.

    - 반박 게이트를 통과하는 candidate 존재 → CONTRADICTED (그 candidate가 evidence)
    - (반박 없고) 뒷받침 게이트를 통과하는 candidate 존재 → CORROBORATED
    - 그 외 → UNVERIFIED ("사실이다"가 아니라 "이 쿼리들에서 반증도 근거도
      확인되지 않았다" — D-03)
    """
    for cand in candidates:
        if passes_refuted_gate(cand.get("applicability_check", {}), required_match_fields):
            return "CONTRADICTED", cand
    for cand in candidates:
        if passes_corroboration_gate(cand.get("applicability_check", {}), required_match_fields):
            return "CORROBORATED", cand
    return "UNVERIFIED", None
