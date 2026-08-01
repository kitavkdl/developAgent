"""S2a. VERIFICATION ROUTER — SCIENTIFIC / GENERAL.                          [검색 0]

▸ 왜 분리: 학술 근거를 요구하는 주장과 일반 사실관계 주장은 깨는 방법 자체가 다르다
  (Scholar vs Web). 라우팅이 S4보다 앞이어야 S4가 '어떤 종류의 문서'를 가설로
  세울지 정할 수 있고, S5가 어떤 LINER 모델을 쓸지 정해진다.
▸ 안전장치 (P0): claim_type이 CLINICAL_COMPLETION이면 라우터 판단과 무관하게
  코드가 SCIENTIFIC으로 강제한다. 임상 주장이 Web 경로로 새면 검증이 무의미해진다.
"""
from __future__ import annotations

from .. import prompts, schemas


def run_router(claim: dict, oai, settings, emitter) -> dict:
    result = oai.structured(
        model=settings.model_router, effort="low",
        system=prompts.ROUTER,
        user=f"클레임: {claim['claim_text']}\nclaim_type: {claim['claim_type_code']}",
        schema_name="router", schema=schemas.ROUTER_SCHEMA,
        emitter=emitter, stage="S2A_ROUTER",
    )
    return apply_clinical_override(claim.get("claim_type_code"), result)


def apply_clinical_override(claim_type_code: str | None, router_output: dict) -> dict:
    """LLM 출력과 무관한 코드 레벨 강제 규칙 (ARCHITECTURE §4). 테스트 가능하도록 분리."""
    if claim_type_code == "CLINICAL_COMPLETION" and router_output.get("route") != "SCIENTIFIC":
        return {
            "route": "SCIENTIFIC",
            "reasoning": router_output.get("reasoning", "")
            + " [코드 강제: CLINICAL_COMPLETION은 항상 SCIENTIFIC]",
            "forced_by_code": True,
        }
    return {**router_output, "forced_by_code": False}
