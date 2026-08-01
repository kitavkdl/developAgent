"""S1. CLAIM TRIAGE — FALSIFIABLE / PUFFERY / NOT_A_CLAIM 분류.              [검색 0]

▸ 왜 여기서 검색을 안 하는가: puffery에 검색을 태우면 비용 낭비이자 '그럴듯한 쓰레기'
  생성. 조기 종료 게이트이며 Prompt Quality 시연 지점.
▸ 왜 S0 뒤: 분류할 원문 문구가 S0에서 나온다.
▸ 왜 S2 앞: PUFFERY로 판정되면 여기서 종료 — 이후 단계(라우팅/분류/검색)의
  tool_call이 0건이어야 한다 (PRD N4). 이 단계를 뒤로 옮기면 N4가 깨진다.

claim_type은 고정 vocabulary (PRD N5) — 스키마 enum + 아래 코드 검증으로 이중 강제.
"""
from __future__ import annotations

from .. import prompts, schemas

FIXED_CLAIM_TYPES = {"SUPERLATIVE_FIRST", "RANKING", "CLINICAL_COMPLETION",
                     "AI_PERFORMANCE", "GENERAL_FACTUAL",
                     "SELF_REPORTED_PRIVATE_METRIC"}


def run_triage(intake_result: dict, oai, settings, emitter) -> list[dict]:
    lines = intake_result.get("raw_lines") or []
    visual = intake_result.get("observed_visual_claims") or []
    context = {
        "brand_name": intake_result.get("brand_name"),
        "product_name": intake_result.get("product_name"),
        "product_context": intake_result.get("product_context"),
    }
    user = (
        f"[제품 맥락] {context}\n"
        f"[광고 문구 목록] {lines}\n"
        f"[시각 요소 주장] {visual}"
    )
    result = oai.structured(
        model=settings.model_triage, effort="medium",
        system=prompts.TRIAGE, user=user,
        schema_name="triage", schema=schemas.TRIAGE_SCHEMA,
        emitter=emitter, stage="S1_TRIAGE",
    )
    claims = result.get("claims", [])
    # 고정 vocabulary 강제 (N5): 목록 밖 claim_type은 GENERAL_FACTUAL로 폴백 (fail-safe,
    # 검증은 계속 진행 — PUFFERY로 강등하면 검색이 아예 실행되지 않아 더 위험)
    for c in claims:
        if c["claim_category"] == "FALSIFIABLE" and c.get("claim_type_code") not in FIXED_CLAIM_TYPES:
            c["claim_type_code"] = "GENERAL_FACTUAL"
        if c["claim_category"] != "FALSIFIABLE":
            c["claim_type_code"] = None
    return claims
