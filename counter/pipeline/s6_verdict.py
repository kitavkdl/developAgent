"""S6. VERDICT ASSEMBLY — 결정론적 + 2단 가드레일.

▸ 왜 마지막: 판정은 검색 결과(근거)가 존재한 뒤에만 나온다 (PRD N3).
순서 (ARCHITECTURE §1 S6):
  ① REFUTED 게이트 — LLM 선언이 아니라 코드 조건문 (PRD N1, counter/gate.py)
  ② 가드레일 1단 — LLM(luna)으로 법적 결론 어휘 1차 차단
  ③ 가드레일 2단 — 최종 JSON 정규식 금지어 검사 → 걸리면 재생성 1회 (counter/guardrail.py)
  ④ DB 기록 + 스트림 push
근거를 지어내지 않는다 (N6): evidence_link는 검색 결과에 실제 존재한 URL만.
DB의 chk_evidence_only_if_refuted 제약이 최후 방어선 (T9).
"""
from __future__ import annotations

from .. import prompts, schemas
from ..gate import assemble_verdict_code
from ..guardrail import SAFE_FALLBACK, contains_banned, guard
from .s5_search import _safe_date


def assemble_and_persist(*, claim: dict, route: str | None, category_id: int | None,
                         cache_decision: str, canonical: dict | None,
                         search_outcome: dict | None, required_match_fields: dict,
                         claim_type_row: dict | None, embedding: list[float] | None,
                         oai, db, settings, emitter, degraded_reason: str | None) -> dict:
    """FALSIFIABLE 클레임 1건의 판정 조립 → 기록. 반환: verdict row(dict)."""

    if cache_decision == "HIT" and canonical is not None:
        # 캐시 히트 — 재검색 없이 canonical의 판정을 재사용 (지연시간 차이가 데모 포인트)
        verdict_code = canonical["verdict_code"]
        evidence_link = canonical.get("evidence_link")
        evidence_date = canonical.get("evidence_date")
        evidence_quote = None
        executed_queries = canonical.get("executed_queries") or []
        explanation = canonical.get("explanation") or ""
        canonical_id = canonical["id"]
        db.bump_canonical_reuse(canonical_id)
    else:
        candidates = search_outcome["candidates"]
        # ① 결정론적 REFUTED 게이트 (N1)
        verdict_code, winning = assemble_verdict_code(
            candidates, required_match_fields, search_outcome["any_search_succeeded"]
        )
        evidence_link = winning["url"] if winning else None
        evidence_date = _safe_date(winning["published_date"]) if winning else None
        evidence_quote = winning["evidence_quote"] if winning else None
        executed_queries = search_outcome["executed_queries"]
        explanation = _make_explanation(
            claim=claim, verdict_code=verdict_code, winning=winning,
            executed_queries=executed_queries, oai=oai, settings=settings,
            emitter=emitter, degraded_reason=degraded_reason,
        )
        # canonical 축적 — 다음 유사 질문의 캐시/델타 기반 (PRD §6-3)
        canonical_id = None
        if category_id is not None and claim_type_row is not None:
            canonical_id = db.upsert_canonical(
                category_id=category_id, claim_type_code=claim["claim_type_code"],
                normalized_text=claim["normalized_text"], embedding=embedding,
                verdict_code=verdict_code, evidence_link=evidence_link,
                evidence_date=evidence_date, explanation=explanation,
                executed_queries=executed_queries,
                ttl_days=int(claim_type_row["default_ttl_days"]),
            )

    row = {
        "job_id": emitter.job_id,
        "claim_text": claim["claim_text"],
        "normalized_text": claim["normalized_text"],
        "claim_category": claim["claim_category"],
        "claim_type_code": claim.get("claim_type_code"),
        "industry_category_id": category_id,
        "route": route,
        "verdict_code": verdict_code,
        "evidence_link": evidence_link,
        "evidence_date": evidence_date,
        "evidence_quote": evidence_quote,
        "explanation": explanation,
        "executed_queries": __import__("json").dumps(executed_queries, ensure_ascii=False),
        "cache_decision": cache_decision,
        "canonical_id": canonical_id,
        "degraded_reason": degraded_reason,
    }
    verdict_id = db.insert_verdict(row)
    row["id"] = verdict_id
    emitter.emit("verdict.assembled", {
        "verdict_id": verdict_id, "claim_text": claim["claim_text"],
        "verdict_code": verdict_code, "evidence_link": evidence_link,
        "cache_decision": cache_decision, "executed_queries": executed_queries,
        "degraded_reason": degraded_reason,
    }, provider="app")
    return row


def persist_puffery(*, claim: dict, oai, db, settings, emitter) -> dict:
    """PUFFERY — 검색 tool_call 0건으로 종료하는 경로 (PRD N4).
    NOT_A_CLAIM은 판정 계약(4값) 대상이 아니므로 verdict row를 만들지 않는다."""
    verdict_code = "PUFFERY"
    explanation = _make_explanation(claim=claim, verdict_code="PUFFERY", winning=None,
                                    executed_queries=[], oai=oai, settings=settings,
                                    emitter=emitter, degraded_reason=None)
    row = {
        "job_id": emitter.job_id,
        "claim_text": claim["claim_text"],
        "normalized_text": claim["normalized_text"],
        "claim_category": claim["claim_category"],
        "claim_type_code": None,
        "industry_category_id": None,
        "route": None,
        "verdict_code": verdict_code,
        "evidence_link": None,
        "evidence_date": None,
        "evidence_quote": None,
        "explanation": explanation,
        "executed_queries": "[]",
        "cache_decision": "SKIP",
        "canonical_id": None,
        "degraded_reason": None,
    }
    verdict_id = db.insert_verdict(row)
    row["id"] = verdict_id
    emitter.emit("verdict.assembled", {
        "verdict_id": verdict_id, "claim_text": claim["claim_text"],
        "verdict_code": verdict_code, "cache_decision": "SKIP",
        "tool_calls": 0,
    }, provider="app")
    return row


def _make_explanation(*, claim, verdict_code, winning, executed_queries, oai, settings,
                      emitter, degraded_reason) -> str:
    """REPORTER(LLM) → 가드레일 1단(LLM) → 2단(정규식). 실패 시 결정론적 템플릿 폴백 —
    설명 생성이 죽어도 판정은 이미 확정돼 있고 파이프라인은 종료돼야 한다."""
    def _template() -> str:
        n = len(executed_queries)
        if verdict_code == "REFUTED" and winning:
            return (f"기준(범주·지표·시점)을 전부 충족하는 반례 문서가 확인되었습니다: "
                    f"{winning['url']} (발행일: {winning['published_date'] or '미상'}). "
                    f"실행한 쿼리 {n}개는 화면에 표시됩니다.")
        if verdict_code == "PUBLIC_SUBSTANTIATION_NOT_FOUND":
            reason = f" ({degraded_reason})" if degraded_reason else ""
            return (f"검색 실행이 정상적으로 완료되지 못해 공개된 범위에서 근거가 "
                    f"확인되지 않았습니다{reason}. 실행 시도한 쿼리 {n}개를 확인하세요.")
        if verdict_code == "PUFFERY":
            return ("검증 가능한 사실 주장이 아니어서 검색을 실행하지 않았습니다. "
                    "주관적 표현은 참·거짓을 따질 대상이 아닙니다.")
        return (f"이 주장이 사실임을 확인한 것이 아닙니다. 저희가 실행한 {n}개 쿼리 "
                f"범위에서 기준을 충족하는 반례를 찾지 못했습니다.")

    try:
        user = (
            f"클레임: {claim['claim_text']}\n"
            f"확정된 verdict: {verdict_code}\n"
            f"실행 쿼리 ({len(executed_queries)}개): {executed_queries}\n"
            + (f"반례 문서: {winning['url']} / 발행일 {winning['published_date']} / "
               f"인용: {winning['evidence_quote']}\n" if winning else "")
            + (f"참고 (부분 증거로 종료): {degraded_reason}\n" if degraded_reason else "")
        )
        report = oai.structured(
            model=settings.model_reporter, effort="medium",
            system=prompts.REPORTER, user=user,
            schema_name="reporter", schema=schemas.REPORTER_SCHEMA,
            emitter=emitter, stage="S6_REPORTER",
        )

        # ② 가드레일 1단: LLM으로 법적 결론 어휘 1차 차단
        try:
            flag = oai.structured(
                model=settings.model_guardrail, effort="none",
                system=prompts.COMMON_RULES
                + "\n다음 텍스트에 법적 결론 어휘(허위/거짓/위법/사기/불법/처벌 류)가 "
                  "포함되어 있는지만 판정합니다.",
                user=report.get("explanation", ""),
                schema_name="guardrail", schema=schemas.GUARDRAIL_SCHEMA,
                emitter=emitter, stage="S6_GUARDRAIL_LLM",
            )
            if flag.get("contains_banned_vocabulary"):
                report["explanation"] = _template()
        except Exception:
            pass  # 1단이 죽어도 2단(코드)이 있다

        # ③ 가드레일 2단: 정규식 — 걸리면 재생성 1회, 그래도 걸리면 정적 안전 문구
        def _regen(_payload: dict) -> dict:
            return {"explanation": _template(), "executed_queries": executed_queries}

        guarded = guard({"explanation": report.get("explanation", ""),
                         "executed_queries": executed_queries}, _regen)
        text = guarded["explanation"]
        return text if not contains_banned({"e": text}) else SAFE_FALLBACK
    except Exception:
        return _template()
