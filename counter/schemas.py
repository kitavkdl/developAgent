"""Structured Outputs용 JSON 스키마 (PROMPTS.md 출력 계약과 1:1).

strict 모드 요건: 모든 property는 required, additionalProperties=false.
스키마는 '구조'만 보장한다 — 내용의 사실성 검증은 코드 게이트(N1)가 한다.
"""

def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": props,
        "required": required if required is not None else list(props.keys()),
        "additionalProperties": False,
    }


_str = {"type": "string"}
_str_or_null = {"type": ["string", "null"]}
_bool = {"type": "boolean"}
_str_arr = {"type": "array", "items": {"type": "string"}}

INTAKE_SCHEMA = _obj({
    "brand_name": _str_or_null,
    "product_name": _str_or_null,
    "product_context": _str,
    "raw_lines": _str_arr,
    "observed_visual_claims": _str_arr,
    "uncertain_fragments": _str_arr,
    "is_advertisement": _bool,
    "ocr_failed": _bool,
})

TRIAGE_SCHEMA = _obj({
    "claims": {
        "type": "array",
        "items": _obj({
            "claim_text": _str,
            "normalized_text": _str,
            "claim_category": {"type": "string", "enum": ["FALSIFIABLE", "PUFFERY", "NOT_A_CLAIM"]},
            # 고정 vocabulary (PRD N5) — enum으로 스키마 레벨에서도 강제
            "claim_type_code": {
                "type": ["string", "null"],
                "enum": ["SUPERLATIVE_FIRST", "RANKING", "CLINICAL_COMPLETION",
                         "AI_PERFORMANCE", "GENERAL_FACTUAL", None],
            },
            "missing_comparator": _bool,
            "reasoning": _str,
        }),
    },
})

ROUTER_SCHEMA = _obj({
    "route": {"type": "string", "enum": ["SCIENTIFIC", "GENERAL"]},
    "reasoning": _str,
})

CATEGORY_LABEL_SCHEMA = _obj({
    "code": _str,
    "label_ko": _str,
})

HYPOTHESIS_SCHEMA = _obj({
    "hypotheses": {
        "type": "array",
        "items": _obj({
            "hypothesis": _str,
            "what_must_exist": _str,
            "queries": {
                "type": "array",
                "items": _obj({"query_text": _str, "language": _str}),
            },
        }),
    },
})

EVALUATOR_SCHEMA = _obj({
    "scope_match": _bool,
    "metric_match": _bool,
    "timeframe_match": _bool,
    "target_match": _bool,
    "evidence_quote": _str,
    "is_syndicated_copy": _bool,
    "insufficient_access": _bool,
    "reasoning": _str,
})

REPORTER_SCHEMA = _obj({
    "explanation": _str,
    "executed_queries": _str_arr,
})

GUARDRAIL_SCHEMA = _obj({
    "contains_banned_vocabulary": _bool,
    "reasoning": _str,
})
