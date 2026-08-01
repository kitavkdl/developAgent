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


TYPED_HYPOTHESIS_CLAIM_TYPES = {"SELF_REPORTED_PRIVATE_METRIC"}

# H1(자기모순) 최우선 — 이 유형에서 찾으면 나머지 유형의 조사 필요성 자체가
# 사라지므로 (구축 요청 [3단계]).
_TYPE_PRIORITY = {"SELF_CONTRADICTION": 0, "CEILING": 1, "DEFINITION_COLLAPSE": 2}

# 업종별 쿼리 레지스터 (구축 요청 [4단계]). 상장사/금융만 공시 어휘가 유효하고,
# 나머지(비상장 소비재 D2C가 대부분이며, 에이전트가 즉석 생성한 신규 카테고리도
# 마찬가지로 기본값은 이쪽)는 법정 공시 의무가 없어 그 어휘로 만든 쿼리가
# 구조적으로 실패한다.
PUBLIC_DISCLOSURE_CATEGORIES = {"FINANCE_FINTECH"}
FORBIDDEN_VOCAB_DEFAULT = ("공시", "사업보고서", "감사보고서", "DART", "IR자료")


def run_hypothesis(claim: dict, route: str, claim_type_row: dict, oai, settings,
                   emitter, *, delta_mode: bool, date_from: str | None,
                   subject: dict | None = None,
                   category: dict | None = None) -> tuple[list[dict], list[dict]]:
    """반환: (hypotheses, budget 내로 잘라낸 쿼리 목록 [{query_text, language}])

    subject(S1b에서 해소된 {brand, product, seller})가 있으면 프롬프트에
    알려주고, clamp_queries가 모든 쿼리에 브랜드명을 코드 레벨로 강제 삽입한다
    (LLM 선의에 맡기지 않음 — 구축 요청 [A]).

    SELF_REPORTED_PRIVATE_METRIC은 hypothesis_type(H1/H2/H3)을 강제하는
    별도 스키마를 쓰고, clamp_queries_diverse로 유형별 라운드로빈 선택을 한다
    (구축 요청 [B]).

    category(S2b 산업 분류 결과)가 있으면 프롬프트에 업종을 알려주고,
    금지 어휘(공시/사업보고서 등, 비상장 소비재엔 무의미)가 쿼리에 남으면
    1회 재생성 → 그래도 남으면 코드가 강제로 제거한다 (구축 요청 [C]/[4단계] —
    검증을 LLM 재량에만 맡기지 않는다)."""
    budget = compute_budget(int(claim_type_row["default_search_budget"]), delta_mode)
    brand = (subject or {}).get("brand")
    subject_line = ""
    if brand:
        subject_line = f"\n판매/서비스 주체: {brand}"
        if (subject or {}).get("product"):
            subject_line += f" (제품: {subject['product']})"
    category_line = ""
    if category:
        category_line = f"\n업종 카테고리: {category.get('label') or category.get('category_id')}"
    base_user = (
        f"클레임: {claim['claim_text']}\n"
        f"claim_type: {claim['claim_type_code']}\n"
        f"검증 경로: {route}\n"
        f"search_budget: {budget}"
        f"{subject_line}{category_line}"
        + (f"\n[델타 모드] {date_from} 이후의 신규 문서만 대상. 과거 증거는 이미 확보됨."
           if delta_mode else "")
    )
    typed = claim["claim_type_code"] in TYPED_HYPOTHESIS_CLAIM_TYPES
    schema = schemas.HYPOTHESIS_TYPED_SCHEMA if typed else schemas.HYPOTHESIS_SCHEMA
    schema_name = "hypothesis_typed" if typed else "hypothesis"

    def _generate(extra: str = "") -> tuple[list[dict], list[dict]]:
        result = oai.structured(
            model=settings.model_hypothesis, effort="high",
            system=prompts.HYPOTHESIS, user=base_user + extra,
            schema_name=schema_name, schema=schema,
            emitter=emitter, stage="S4_HYPOTHESIS",
        )
        hyps = result.get("hypotheses", [])
        qs = (clamp_queries_diverse(hyps, budget, required_token=brand) if typed
             else clamp_queries(hyps, budget, required_token=brand))
        return hyps, qs

    hypotheses, queries = _generate()

    category_id = (category or {}).get("category_id")
    violations = _forbidden_query_texts(queries, category_id)
    if violations:
        emitter.emit("hypothesis.vocab_violation", {"queries": violations, "attempt": 1})
        hypotheses, queries = _generate(
            "\n\n[재생성 사유] 이전 시도의 쿼리에 이 업종에 맞지 않는 어휘가 "
            "포함됐습니다 (예: 비상장 소비재인데 '공시'/'사업보고서' 사용). "
            "그런 어휘 없이 다시 생성하세요."
        )
        violations = _forbidden_query_texts(queries, category_id)
        if violations:
            # 재생성 후에도 위반 시 코드가 최종적으로 제거 — LLM 선의에 맡기지 않음.
            emitter.emit("hypothesis.vocab_violation", {"queries": violations, "attempt": 2})
            queries = _strip_forbidden_vocab(queries, category_id)

    if typed:
        distinct_types = sorted({h.get("hypothesis_type") for h in hypotheses
                                if h.get("hypothesis_type")})
        emitter.emit("hypothesis.diversity", {
            "distinct_types": distinct_types, "hypothesis_count": len(hypotheses),
        })
    return hypotheses, queries


def _forbidden_query_texts(queries: list[dict], category_id: str | None) -> list[str]:
    if category_id in PUBLIC_DISCLOSURE_CATEGORIES:
        return []
    return [q["query_text"] for q in queries
           if any(bad in q["query_text"] for bad in FORBIDDEN_VOCAB_DEFAULT)]


def _strip_forbidden_vocab(queries: list[dict], category_id: str | None) -> list[dict]:
    if category_id in PUBLIC_DISCLOSURE_CATEGORIES:
        return queries
    cleaned = []
    for q in queries:
        text = q["query_text"]
        for bad in FORBIDDEN_VOCAB_DEFAULT:
            text = text.replace(bad, "")
        text = " ".join(text.split())  # 제거로 생긴 중복 공백 정리
        cleaned.append({**q, "query_text": text})
    return cleaned


def compute_budget(default_budget: int, delta_mode: bool) -> int:
    return max(1, math.ceil(default_budget / 2)) if delta_mode else default_budget


def clamp_queries(hypotheses: list[dict], budget: int,
                  required_token: str | None = None) -> list[dict]:
    """가설 순서대로 쿼리를 모으되 총 예산 초과분은 버린다 (B09 게이트: 예산 초과 안 함).
    required_token(해소된 판매주체명)이 있으면 모든 쿼리에 강제 포함시킨다 —
    LLM이 빠뜨려도 코드가 보장한다 (구축 요청 [A])."""
    queries: list[dict] = []
    for h in hypotheses:
        for q in h.get("queries", []):
            if len(queries) >= budget:
                return queries
            text = q.get("query_text")
            if not text:
                continue
            if required_token and required_token not in text:
                text = f"{required_token} {text}"
            queries.append({"query_text": text, "language": q.get("language", "ko"),
                            "hypothesis": h.get("hypothesis")})
    return queries


def clamp_queries_diverse(hypotheses: list[dict], budget: int,
                          required_token: str | None = None) -> list[dict]:
    """hypothesis_type이 다른 가설들의 쿼리를 라운드로빈(SELF_CONTRADICTION
    최우선 순서)으로 뽑아, 예산 내에서 최대한 서로 다른 유형이 실행되게
    한다 — 한 가설이 표현만 바꿔 예산을 독식하는 것을 방지 (구축 요청 [B]).
    required_token은 clamp_queries와 동일하게 모든 쿼리에 강제 삽입한다."""
    ordered = sorted(hypotheses,
                     key=lambda h: _TYPE_PRIORITY.get(h.get("hypothesis_type"), 99))
    queues = [(h, [q for q in h.get("queries", []) if q.get("query_text")])
             for h in ordered]

    queries: list[dict] = []
    while len(queries) < budget and any(qlist for _, qlist in queues):
        for h, qlist in queues:
            if len(queries) >= budget:
                break
            if not qlist:
                continue
            q = qlist.pop(0)
            text = q["query_text"]
            if required_token and required_token not in text:
                text = f"{required_token} {text}"
            queries.append({"query_text": text, "language": q.get("language", "ko"),
                            "hypothesis": h.get("hypothesis"),
                            "hypothesis_type": h.get("hypothesis_type")})
    return queries
